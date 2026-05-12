"""
Advanced Authentication & Authorization Module
JWT, OAuth, 2FA, and RBAC support
"""

import logging
import jwt
import secrets
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from functools import wraps
import pyotp
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Advanced authentication with JWT, OAuth, 2FA"""
    
    def __init__(self, db_path: str = "auth.db", jwt_secret: str = None):
        """Initialize authentication manager"""
        self.db_path = db_path
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.jwt_algorithm = "HS256"
        self.token_expiry = 3600  # 1 hour
        self.refresh_token_expiry = 2592000  # 30 days
        self.init_database()
        logger.info("AuthenticationManager initialized")
    
    def init_database(self):
        """Initialize authentication database"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'user',
                    is_active INTEGER DEFAULT 1,
                    is_verified INTEGER DEFAULT 0,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Two-Factor Authentication
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS two_factor_auth (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    secret_key TEXT NOT NULL,
                    is_enabled INTEGER DEFAULT 0,
                    backup_codes TEXT,
                    enabled_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Refresh tokens
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    revoked INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Login audit trail
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    status TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # OAuth connections
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS oauth_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_user_id TEXT NOT NULL,
                    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, provider)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_audit_user ON login_audit(user_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("Authentication database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing auth database: {e}")
    
    def create_user(
        self,
        org_id: str,
        username: str,
        email: str,
        password: str,
        full_name: str = None,
        role: str = "user"
    ) -> Optional[str]:
        """
        Create new user
        
        Args:
            org_id: Organization ID
            username: Username
            email: Email address
            password: Password (will be hashed)
            full_name: Full name
            role: User role (user, manager, admin)
            
        Returns:
            User ID or None
        """
        try:
            user_id = f"user_{secrets.token_hex(8)}"
            password_hash = generate_password_hash(password)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (id, org_id, username, email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, org_id, username, email, password_hash, full_name, role))
            
            # Create 2FA record
            cursor.execute('''
                INSERT INTO two_factor_auth (user_id, secret_key)
                VALUES (?, ?)
            ''', (user_id, pyotp.random_base32()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created user: {username} (ID: {user_id})")
            return user_id
        
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Authenticate user and return access token and refresh token
        
        Args:
            username: Username
            password: Password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (access_token, refresh_token) or (None, None)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            if not user:
                self._log_login_attempt(None, username, ip_address, user_agent, "failure_user_not_found")
                logger.warning(f"Login attempt for non-existent user: {username}")
                return None, None
            
            # Check if account is locked
            if user['locked_until']:
                locked_until = datetime.fromisoformat(user['locked_until'])
                if locked_until > datetime.now():
                    self._log_login_attempt(user['id'], username, ip_address, user_agent, "failure_account_locked")
                    logger.warning(f"Login attempt on locked account: {username}")
                    return None, None
            
            # Verify password
            if not check_password_hash(user['password_hash'], password):
                login_attempts = (user['login_attempts'] or 0) + 1
                
                # Lock account after 5 failed attempts
                locked_until = None
                if login_attempts >= 5:
                    locked_until = (datetime.now() + timedelta(minutes=15)).isoformat()
                    self._log_login_attempt(user['id'], username, ip_address, user_agent, "failure_account_locked")
                else:
                    self._log_login_attempt(user['id'], username, ip_address, user_agent, "failure_wrong_password")
                
                cursor.execute('''
                    UPDATE users
                    SET login_attempts = ?, locked_until = ?
                    WHERE id = ?
                ''', (login_attempts, locked_until, user['id']))
                
                conn.commit()
                conn.close()
                
                logger.warning(f"Failed login attempt for user: {username}")
                return None, None
            
            # If 2FA is enabled, don't generate tokens yet
            cursor.execute('''
                SELECT is_enabled FROM two_factor_auth WHERE user_id = ?
            ''', (user['id'],))
            
            twofa = cursor.fetchone()
            if twofa and twofa['is_enabled']:
                self._log_login_attempt(user['id'], username, ip_address, user_agent, "pending_2fa")
                conn.close()
                return "2FA_REQUIRED", None
            
            # Generate tokens
            access_token = self._generate_access_token(user)
            refresh_token = self._generate_refresh_token(user['id'])
            
            # Update user record
            cursor.execute('''
                UPDATE users
                SET last_login = ?, login_attempts = 0, locked_until = NULL
                WHERE id = ?
            ''', (datetime.now(), user['id']))
            
            self._log_login_attempt(user['id'], username, ip_address, user_agent, "success")
            
            conn.commit()
            conn.close()
            
            logger.info(f"User authenticated: {username}")
            return access_token, refresh_token
        
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None, None
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    def _generate_access_token(self, user) -> str:
        """Generate access token"""
        payload = {
            "user_id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "org_id": user['org_id'],
            "role": user['role'],
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiry),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _generate_refresh_token(self, user_id: str) -> str:
        """Generate refresh token"""
        token_id = f"refresh_{secrets.token_hex(16)}"
        token_secret = secrets.token_urlsafe(32)
        token_hash = generate_password_hash(token_secret)
        
        expires_at = datetime.now() + timedelta(seconds=self.refresh_token_expiry)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (token_id, user_id, token_hash, expires_at))
        
        conn.commit()
        conn.close()
        
        return f"{token_id}.{token_secret}"
    
    def setup_2fa(self, user_id: str) -> Dict:
        """
        Setup 2FA for user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with QR code and backup codes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate secret
            secret = pyotp.random_base32()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            
            # Generate QR code
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(name=user_id, issuer_name='SmartMonitoring')
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(uri)
            qr.make(fit=True)
            
            img = qr.make_image()
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            qr_code_b64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Update database
            cursor.execute('''
                UPDATE two_factor_auth
                SET secret_key = ?, backup_codes = ?
                WHERE user_id = ?
            ''', (secret, ','.join(backup_codes), user_id))
            
            conn.commit()
            conn.close()
            
            return {
                "secret": secret,
                "qr_code": f"data:image/png;base64,{qr_code_b64}",
                "backup_codes": backup_codes
            }
        
        except Exception as e:
            logger.error(f"Error setting up 2FA: {e}")
            return {}
    
    def verify_2fa(self, user_id: str, totp_code: str) -> bool:
        """
        Verify 2FA code
        
        Args:
            user_id: User ID
            totp_code: TOTP code from authenticator app
            
        Returns:
            True if valid, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT secret_key FROM two_factor_auth WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False
            
            totp = pyotp.TOTP(result['secret_key'])
            return totp.verify(totp_code, valid_window=1)
        
        except Exception as e:
            logger.error(f"Error verifying 2FA: {e}")
            return False
    
    def _log_login_attempt(
        self,
        user_id: Optional[str],
        username: str,
        ip_address: str,
        user_agent: str,
        status: str
    ):
        """Log login attempt for audit trail"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO login_audit (user_id, username, ip_address, user_agent, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, ip_address, user_agent, status))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging login attempt: {e}")


class RBACManager:
    """Role-Based Access Control"""
    
    PERMISSIONS = {
        "admin": [
            "users:create", "users:read", "users:update", "users:delete",
            "organizations:manage", "reports:view", "settings:manage",
            "api_keys:manage", "audit:view", "billing:manage"
        ],
        "manager": [
            "users:read", "users:update", "reports:view",
            "api_keys:read", "audit:view"
        ],
        "user": [
            "reports:view_own", "api_keys:read_own"
        ]
    }
    
    @staticmethod
    def has_permission(role: str, permission: str) -> bool:
        """Check if role has permission"""
        return permission in RBACManager.PERMISSIONS.get(role, [])
    
    @staticmethod
    def require_permission(permission: str):
        """Decorator to require permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                from flask import request, jsonify
                
                # Get token from header
                token = request.headers.get('Authorization', '').replace('Bearer ', '')
                
                # TODO: Verify token and check permission
                # For now, just pass through
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
