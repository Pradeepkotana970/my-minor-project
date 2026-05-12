"""
Multi-Tenant Architecture & Organization Management
Enables multiple organizations (schools, offices) on single platform
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class TenantManager:
    """Manages multiple organizations/tenants"""
    
    def __init__(self, db_path: str = "tenants.db"):
        """Initialize tenant manager"""
        self.db_path = db_path
        self.init_database()
        logger.info("TenantManager initialized")
    
    @contextmanager
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize tenant database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Organizations/Tenants table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS organizations (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        type TEXT NOT NULL,
                        admin_email TEXT NOT NULL UNIQUE,
                        phone TEXT,
                        address TEXT,
                        city TEXT,
                        country TEXT,
                        subscription_tier TEXT DEFAULT 'starter',
                        license_key TEXT UNIQUE,
                        is_active INTEGER DEFAULT 1,
                        trial_expires TIMESTAMP,
                        storage_limit_gb INTEGER DEFAULT 10,
                        max_users INTEGER DEFAULT 50,
                        max_cameras INTEGER DEFAULT 2,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Organization admins
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS org_admins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        org_id TEXT NOT NULL,
                        admin_id TEXT NOT NULL UNIQUE,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        full_name TEXT,
                        is_active INTEGER DEFAULT 1,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (org_id) REFERENCES organizations(id)
                    )
                ''')
                
                # Organization settings
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS org_settings (
                        org_id TEXT PRIMARY KEY,
                        language TEXT DEFAULT 'en',
                        timezone TEXT DEFAULT 'UTC',
                        theme TEXT DEFAULT 'light',
                        enable_api_access INTEGER DEFAULT 1,
                        enable_2fa INTEGER DEFAULT 0,
                        enable_audit_logging INTEGER DEFAULT 1,
                        retention_days INTEGER DEFAULT 90,
                        backup_enabled INTEGER DEFAULT 1,
                        alert_email TEXT,
                        slack_webhook TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (org_id) REFERENCES organizations(id)
                    )
                ''')
                
                # API Keys per organization
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS api_keys (
                        id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        key_hash TEXT NOT NULL UNIQUE,
                        last_used TIMESTAMP,
                        created_by TEXT,
                        is_active INTEGER DEFAULT 1,
                        expires_at TIMESTAMP,
                        rate_limit INTEGER DEFAULT 1000,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (org_id) REFERENCES organizations(id)
                    )
                ''')
                
                # Subscription plans
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        org_id TEXT NOT NULL UNIQUE,
                        tier TEXT NOT NULL,
                        plan_name TEXT,
                        monthly_cost REAL,
                        billing_email TEXT,
                        payment_method TEXT,
                        billing_date INTEGER,
                        auto_renew INTEGER DEFAULT 1,
                        status TEXT DEFAULT 'active',
                        started_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (org_id) REFERENCES organizations(id)
                    )
                ''')
                
                # Usage metrics
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usage_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        org_id TEXT NOT NULL,
                        date DATE NOT NULL,
                        frames_processed INTEGER DEFAULT 0,
                        faces_detected INTEGER DEFAULT 0,
                        alerts_triggered INTEGER DEFAULT 0,
                        storage_used_gb REAL DEFAULT 0,
                        api_calls INTEGER DEFAULT 0,
                        active_users INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (org_id) REFERENCES organizations(id),
                        UNIQUE(org_id, date)
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_admin ON org_admins(org_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_key_org ON api_keys(org_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_org_date ON usage_metrics(org_id, date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscription_org ON subscriptions(org_id)')
                
                logger.info("Tenant database schema initialized")
        
        except Exception as e:
            logger.error(f"Error initializing tenant database: {e}")
            raise
    
    def create_organization(
        self,
        name: str,
        org_type: str,
        admin_email: str,
        admin_password: str,
        admin_name: str = None,
        phone: str = None,
        address: str = None,
        subscription_tier: str = "starter"
    ) -> Optional[str]:
        """
        Create new organization
        
        Args:
            name: Organization name
            org_type: Type (school, office, hospital, etc)
            admin_email: Admin email
            admin_password: Admin password (will be hashed)
            admin_name: Administrator name
            phone: Organization phone
            address: Organization address
            subscription_tier: Subscription tier (starter/professional/enterprise)
            
        Returns:
            Organization ID or None
        """
        try:
            org_id = str(uuid.uuid4())
            
            # Hash password
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash(admin_password)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create organization
                cursor.execute('''
                    INSERT INTO organizations (id, name, type, admin_email, phone, address, subscription_tier)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (org_id, name, org_type, admin_email, phone, address, subscription_tier))
                
                # Create admin user
                admin_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO org_admins (org_id, admin_id, email, password_hash, full_name)
                    VALUES (?, ?, ?, ?, ?)
                ''', (org_id, admin_id, admin_email, password_hash, admin_name or name))
                
                # Create default settings
                cursor.execute('''
                    INSERT INTO org_settings (org_id)
                    VALUES (?)
                ''', (org_id,))
                
                # Create subscription record
                cursor.execute('''
                    INSERT INTO subscriptions (org_id, tier, status, started_at, expires_at)
                    VALUES (?, ?, 'active', ?, ?)
                ''', (org_id, subscription_tier, datetime.now(), datetime.now() + timedelta(days=30)))
                
                logger.info(f"Created organization: {name} (ID: {org_id})")
                return org_id
        
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            return None
    
    def get_organization(self, org_id: str) -> Optional[Dict]:
        """Get organization details"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM organizations WHERE id = ?', (org_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting organization: {e}")
            return None
    
    def get_org_settings(self, org_id: str) -> Optional[Dict]:
        """Get organization settings"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM org_settings WHERE org_id = ?', (org_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting org settings: {e}")
            return None
    
    def update_org_settings(self, org_id: str, settings: Dict) -> bool:
        """Update organization settings"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                updates = []
                values = []
                
                for key, value in settings.items():
                    if key in ['language', 'timezone', 'theme', 'alert_email', 'slack_webhook', 'retention_days']:
                        updates.append(f"{key} = ?")
                        values.append(value)
                
                if not updates:
                    return False
                
                values.append(org_id)
                query = f"UPDATE org_settings SET {', '.join(updates)} WHERE org_id = ?"
                cursor.execute(query, values)
                
                logger.info(f"Updated settings for org: {org_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error updating org settings: {e}")
            return False
    
    def generate_api_key(
        self,
        org_id: str,
        name: str,
        created_by: str,
        expires_days: int = 365
    ) -> Optional[str]:
        """
        Generate API key for organization
        
        Args:
            org_id: Organization ID
            name: API key name
            created_by: User creating the key
            expires_days: Days until expiration
            
        Returns:
            API key string or None
        """
        try:
            import secrets
            from werkzeug.security import generate_password_hash
            
            # Generate random API key
            api_key = secrets.token_urlsafe(32)
            key_hash = generate_password_hash(api_key)
            key_id = str(uuid.uuid4())
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO api_keys (id, org_id, name, key_hash, created_by, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    key_id,
                    org_id,
                    name,
                    key_hash,
                    created_by,
                    datetime.now() + timedelta(days=expires_days)
                ))
                
                logger.info(f"Generated API key for org: {org_id}")
                return api_key
        
        except Exception as e:
            logger.error(f"Error generating API key: {e}")
            return None
    
    def verify_api_key(self, org_id: str, api_key: str) -> bool:
        """Verify API key"""
        try:
            from werkzeug.security import check_password_hash
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT key_hash, is_active, expires_at FROM api_keys
                    WHERE org_id = ? AND is_active = 1
                ''', (org_id,))
                
                keys = cursor.fetchall()
                
                for key_row in keys:
                    key_hash, is_active, expires_at = key_row
                    
                    # Check expiration
                    if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                        continue
                    
                    # Check password hash
                    if check_password_hash(key_hash, api_key):
                        # Update last used
                        cursor.execute('''
                            UPDATE api_keys SET last_used = ?
                            WHERE key_hash = ?
                        ''', (datetime.now(), key_hash))
                        return True
                
                return False
        
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return False
    
    def record_usage(
        self,
        org_id: str,
        frames_processed: int = 0,
        faces_detected: int = 0,
        alerts_triggered: int = 0,
        storage_used_gb: float = 0,
        api_calls: int = 0
    ) -> bool:
        """Record organization usage metrics"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if today's record exists
                cursor.execute('''
                    SELECT id FROM usage_metrics WHERE org_id = ? AND date = ?
                ''', (org_id, today))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute('''
                        UPDATE usage_metrics
                        SET frames_processed = frames_processed + ?,
                            faces_detected = faces_detected + ?,
                            alerts_triggered = alerts_triggered + ?,
                            storage_used_gb = storage_used_gb + ?,
                            api_calls = api_calls + ?
                        WHERE org_id = ? AND date = ?
                    ''', (frames_processed, faces_detected, alerts_triggered, storage_used_gb, api_calls, org_id, today))
                else:
                    # Create new record
                    cursor.execute('''
                        INSERT INTO usage_metrics
                        (org_id, date, frames_processed, faces_detected, alerts_triggered, storage_used_gb, api_calls)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (org_id, today, frames_processed, faces_detected, alerts_triggered, storage_used_gb, api_calls))
                
                return True
        
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            return False
    
    def get_usage_summary(self, org_id: str, days: int = 30) -> Dict:
        """Get organization usage summary"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT
                        SUM(frames_processed) as total_frames,
                        SUM(faces_detected) as total_faces,
                        SUM(alerts_triggered) as total_alerts,
                        SUM(storage_used_gb) as total_storage,
                        SUM(api_calls) as total_api_calls,
                        AVG(frames_processed) as avg_frames_per_day
                    FROM usage_metrics
                    WHERE org_id = ? AND date > ?
                ''', (org_id, cutoff_date))
                
                row = cursor.fetchone()
                
                if row:
                    return {
                        "total_frames": row[0] or 0,
                        "total_faces": row[1] or 0,
                        "total_alerts": row[2] or 0,
                        "total_storage_gb": row[3] or 0,
                        "total_api_calls": row[4] or 0,
                        "avg_frames_per_day": row[5] or 0
                    }
                
                return {}
        
        except Exception as e:
            logger.error(f"Error getting usage summary: {e}")
            return {}
