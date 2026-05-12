"""
User Authentication Module
Handles user registration, login, and OTP verification
"""

import os
import json
import csv
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# User database file paths
USERS_DB_FILE = 'users_database.json'
OTP_DB_FILE = 'otp_database.json'
SESSIONS_DB_FILE = 'sessions_database.json'

class UserDatabase:
    """Manages user authentication and storage"""
    
    @staticmethod
    def load_users() -> Dict:
        """Load all users from database"""
        if os.path.exists(USERS_DB_FILE):
            try:
                with open(USERS_DB_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def save_users(users: Dict):
        """Save users to database"""
        with open(USERS_DB_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(stored_hash: str, password: str) -> bool:
        """Verify password against stored hash"""
        return stored_hash == UserDatabase.hash_password(password)
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP"""
        return str(secrets.randbelow(1000000)).zfill(6)
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def register_user(email: str, password: str, name: str, 
                     user_id: str, phone: str) -> Tuple[bool, str]:
        """Register a new user"""
        try:
            email = email.lower().strip()
            
            # Validation
            if not email or not password or not name or not user_id or not phone:
                return False, "All fields are required"
            
            if len(password) < 6:
                return False, "Password must be at least 6 characters"
            
            if not email.count('@'):
                return False, "Invalid email format"
            
            users = UserDatabase.load_users()
            
            if email in users:
                return False, "Email already registered"
            
            if users.get(user_id, {}).get('user_id') == user_id:
                return False, "User ID already exists"
            
            # Create user
            users[email] = {
                'email': email,
                'password_hash': UserDatabase.hash_password(password),
                'name': name,
                'user_id': user_id,
                'phone': phone,
                'created_at': datetime.now().isoformat(),
                'face_registered': False,
                'is_verified': False,
                'otp_verified': False
            }
            
            UserDatabase.save_users(users)
            print(f"✅ User registered: {email}")
            return True, "Registration successful"
        
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False, f"Registration failed: {str(e)}"
    
    @staticmethod
    def login_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """Authenticate user login"""
        try:
            email = email.lower().strip()
            users = UserDatabase.load_users()
            
            if email not in users:
                return False, "Email not found", None
            
            user = users[email]
            
            if not UserDatabase.verify_password(user['password_hash'], password):
                return False, "Invalid password", None
            
            if not user.get('otp_verified'):
                return False, "Email not verified with OTP", None
            
            # Generate session token
            session_token = UserDatabase.generate_session_token()
            
            # Store session
            sessions = UserDatabase.load_sessions()
            sessions[session_token] = {
                'email': email,
                'name': user['name'],
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
            }
            UserDatabase.save_sessions(sessions)
            
            print(f"✅ User logged in: {email}")
            return True, "Login successful", {
                'session_token': session_token,
                'email': email,
                'name': user['name'],
                'user_id': user['user_id'],
                'face_registered': user.get('face_registered', False)
            }
        
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False, f"Login failed: {str(e)}", None
    
    @staticmethod
    def store_otp(phone: str, otp: str) -> bool:
        """Store OTP for phone verification"""
        try:
            otps = {}
            if os.path.exists(OTP_DB_FILE):
                with open(OTP_DB_FILE, 'r') as f:
                    otps = json.load(f)
            
            otps[phone] = {
                'otp': otp,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(minutes=10)).isoformat(),
                'attempts': 0
            }
            
            with open(OTP_DB_FILE, 'w') as f:
                json.dump(otps, f, indent=2)
            
            print(f"✅ OTP stored for {phone}: {otp}")
            return True
        except Exception as e:
            print(f"❌ OTP storage error: {e}")
            return False
    
    @staticmethod
    def verify_otp(phone: str, entered_otp: str) -> Tuple[bool, str]:
        """Verify entered OTP"""
        try:
            if not os.path.exists(OTP_DB_FILE):
                return False, "No OTP request found"
            
            with open(OTP_DB_FILE, 'r') as f:
                otps = json.load(f)
            
            if phone not in otps:
                return False, "No OTP found for this phone"
            
            otp_data = otps[phone]
            
            # Check expiry
            expires_at = datetime.fromisoformat(otp_data['expires_at'])
            if datetime.now() > expires_at:
                del otps[phone]
                with open(OTP_DB_FILE, 'w') as f:
                    json.dump(otps, f, indent=2)
                return False, "OTP expired"
            
            # Check attempts
            if otp_data['attempts'] >= 3:
                del otps[phone]
                with open(OTP_DB_FILE, 'w') as f:
                    json.dump(otps, f, indent=2)
                return False, "Too many attempts"
            
            # Verify OTP
            if otp_data['otp'] != entered_otp:
                otp_data['attempts'] += 1
                with open(OTP_DB_FILE, 'w') as f:
                    json.dump(otps, f, indent=2)
                return False, f"Invalid OTP ({3 - otp_data['attempts']} attempts remaining)"
            
            # OTP is correct
            del otps[phone]
            with open(OTP_DB_FILE, 'w') as f:
                json.dump(otps, f, indent=2)
            
            print(f"✅ OTP verified for {phone}")
            return True, "OTP verified successfully"
        
        except Exception as e:
            print(f"❌ OTP verification error: {e}")
            return False, f"Verification failed: {str(e)}"
    
    @staticmethod
    def mark_otp_verified(email: str) -> bool:
        """Mark user's OTP as verified"""
        try:
            users = UserDatabase.load_users()
            email = email.lower().strip()
            
            if email in users:
                users[email]['otp_verified'] = True
                UserDatabase.save_users(users)
                print(f"✅ OTP marked as verified for {email}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error marking OTP verified: {e}")
            return False
    
    @staticmethod
    def save_sessions(sessions: Dict):
        """Save sessions to database"""
        with open(SESSIONS_DB_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
    
    @staticmethod
    def load_sessions() -> Dict:
        """Load sessions from database"""
        if os.path.exists(SESSIONS_DB_FILE):
            try:
                with open(SESSIONS_DB_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def verify_session(session_token: str) -> Optional[Dict]:
        """Verify session token and return user data"""
        try:
            sessions = UserDatabase.load_sessions()
            
            if session_token not in sessions:
                return None
            
            session = sessions[session_token]
            
            # Check if session expired
            expires_at = datetime.fromisoformat(session['expires_at'])
            if datetime.now() > expires_at:
                del sessions[session_token]
                UserDatabase.save_sessions(sessions)
                return None
            
            return session
        except:
            return None
    
    @staticmethod
    def logout_user(session_token: str) -> bool:
        """Logout user by removing session"""
        try:
            sessions = UserDatabase.load_sessions()
            if session_token in sessions:
                del sessions[session_token]
                UserDatabase.save_sessions(sessions)
                print(f"✅ User logged out")
                return True
            return False
        except Exception as e:
            print(f"❌ Logout error: {e}")
            return False
    
    @staticmethod
    def mark_face_registered(email: str) -> bool:
        """Mark that user has registered their face"""
        try:
            users = UserDatabase.load_users()
            email = email.lower().strip()
            
            if email in users:
                users[email]['face_registered'] = True
                UserDatabase.save_users(users)
                print(f"✅ Face marked as registered for {email}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error marking face registered: {e}")
            return False
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user data by email"""
        try:
            users = UserDatabase.load_users()
            email = email.lower().strip()
            
            if email in users:
                user = users[email].copy()
                user.pop('password_hash', None)  # Don't return password
                return user
            return None
        except:
            return None
