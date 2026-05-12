"""
API Security Module
Rate limiting, CORS, request validation, and security headers
"""

import logging
import hashlib
import time
from typing import Dict, Optional, Callable
from collections import defaultdict
from datetime import datetime, timedelta
import json
from functools import wraps
from flask import request, jsonify, g

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, default_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            default_requests: Default requests per window
            window_seconds: Time window in seconds
        """
        self.default_requests = default_requests
        self.window_seconds = window_seconds
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            "tokens": default_requests,
            "last_refill": time.time()
        })
    
    def is_allowed(self, identifier: str, requests: int = None) -> bool:
        """
        Check if request is allowed
        
        Args:
            identifier: Client identifier (IP, API key, user ID)
            requests: Override default requests limit
            
        Returns:
            True if allowed, False if rate limited
        """
        requests = requests or self.default_requests
        
        bucket = self.buckets[identifier]
        now = time.time()
        
        # Refill tokens
        time_passed = now - bucket["last_refill"]
        tokens_to_add = (time_passed / self.window_seconds) * requests
        
        bucket["tokens"] = min(requests, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now
        
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        
        return False
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining tokens for identifier"""
        bucket = self.buckets[identifier]
        now = time.time()
        
        time_passed = now - bucket["last_refill"]
        tokens = min(
            self.default_requests,
            bucket["tokens"] + (time_passed / self.window_seconds) * self.default_requests
        )
        
        return int(tokens)


class RequestValidator:
    """Request validation and sanitization"""
    
    @staticmethod
    def validate_json(data: Dict, required_fields: list) -> tuple[bool, Optional[str]]:
        """
        Validate JSON request
        
        Args:
            data: JSON data
            required_fields: List of required field names
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        for field in required_fields:
            if field not in data or data[field] is None:
                return False, f"Missing required field: {field}"
        
        return True, None
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input
        
        Args:
            value: String to sanitize
            max_length: Maximum length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return ""
        
        # Truncate
        value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Strip whitespace
        value = value.strip()
        
        return value
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_api_key_format(api_key: str) -> bool:
        """Validate API key format"""
        # Should be 'org_' prefix followed by hex characters
        return api_key.startswith('org_') and len(api_key) > 10


class SecurityHeaders:
    """Security headers middleware"""
    
    HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    @staticmethod
    def apply(response):
        """Apply security headers to response"""
        for header, value in SecurityHeaders.HEADERS.items():
            response.headers[header] = value
        return response


class CORSManager:
    """CORS handling"""
    
    def __init__(self, allowed_origins: list = None):
        """
        Initialize CORS manager
        
        Args:
            allowed_origins: List of allowed origins
        """
        self.allowed_origins = allowed_origins or ['localhost', '127.0.0.1']
    
    def handle_cors(self, response):
        """Add CORS headers to response"""
        origin = request.headers.get('Origin')
        
        if origin and any(allowed in origin for allowed in self.allowed_origins):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Max-Age'] = '3600'
        
        return response


class APIKeyValidator:
    """API Key validation"""
    
    # This would typically come from the TenantManager
    valid_keys = {}
    
    @staticmethod
    def validate_key(api_key: str) -> Optional[Dict]:
        """
        Validate API key
        
        Args:
            api_key: API key to validate
            
        Returns:
            API key info or None if invalid
        """
        if not RequestValidator.validate_api_key_format(api_key):
            return None
        
        # In production, would look up in database
        return APIKeyValidator.valid_keys.get(api_key)
    
    @staticmethod
    def get_from_request() -> Optional[str]:
        """Extract API key from request"""
        # Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # Check query parameter
        return request.args.get('api_key')


class SecurityMonitor:
    """Security event monitoring and logging"""
    
    def __init__(self):
        self.suspicious_events = defaultdict(list)
        self.blocked_ips = set()
    
    def log_suspicious_activity(
        self,
        event_type: str,
        identifier: str,
        details: str,
        severity: str = "warning"
    ):
        """
        Log suspicious activity
        
        Args:
            event_type: Type of suspicious activity
            identifier: Client identifier (IP, user ID, etc)
            details: Event details
            severity: Severity level (warning, critical)
        """
        timestamp = datetime.now()
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "details": details,
            "severity": severity
        }
        
        self.suspicious_events[identifier].append(event)
        
        # Log critical events
        if severity == "critical":
            logger.critical(f"SECURITY: {event_type} from {identifier} - {details}")
        else:
            logger.warning(f"SECURITY: {event_type} from {identifier} - {details}")
    
    def check_for_attacks(self, identifier: str) -> Optional[str]:
        """
        Check if identifier shows signs of attack
        
        Args:
            identifier: Client identifier
            
        Returns:
            Threat level or None if safe
        """
        events = self.suspicious_events.get(identifier, [])
        
        # Get events from last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_events = [e for e in events if e["timestamp"] > one_hour_ago]
        
        if len(recent_events) > 10:
            return "high"
        elif len(recent_events) > 5:
            return "medium"
        
        return None
    
    def block_ip(self, ip_address: str):
        """Block IP address temporarily"""
        self.blocked_ips.add(ip_address)
        logger.warning(f"Blocked IP: {ip_address}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips


class RequestSigner:
    """HMAC request signing for webhooks and API calls"""
    
    @staticmethod
    def sign_request(secret_key: str, payload: Dict) -> str:
        """
        Sign request payload
        
        Args:
            secret_key: Secret key for signing
            payload: Payload to sign
            
        Returns:
            HMAC signature
        """
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hashlib.sha256(
            f"{payload_str}{secret_key}".encode()
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def verify_signature(secret_key: str, payload: Dict, signature: str) -> bool:
        """
        Verify request signature
        
        Args:
            secret_key: Secret key for signing
            payload: Payload to verify
            signature: Signature to check
            
        Returns:
            True if signature is valid
        """
        expected_signature = RequestSigner.sign_request(secret_key, payload)
        return signature == expected_signature


# Decorators for Flask routes

def require_api_key(f):
    """Decorator to require API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = APIKeyValidator.get_from_request()
        
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401
        
        key_info = APIKeyValidator.validate_key(api_key)
        
        if not key_info:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Store in g for use in route
        g.api_key_info = key_info
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_jwt_token(f):
    """Decorator to require JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from authentication import AuthenticationManager
        
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        
        token = auth_header[7:]
        auth_manager = AuthenticationManager()
        payload = auth_manager.verify_token(token)
        
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        g.user = payload
        
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit(requests: int = 100, window: int = 60):
    """Decorator to apply rate limiting"""
    limiter = RateLimiter(requests, window)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = request.remote_addr
            
            if not limiter.is_allowed(identifier, requests):
                return jsonify({"error": "Rate limit exceeded"}), 429
            
            remaining = limiter.get_remaining(identifier)
            g.rate_limit_remaining = remaining
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def validate_json(*required_fields):
    """Decorator to validate JSON request"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            
            data = request.get_json()
            is_valid, error_msg = RequestValidator.validate_json(data, required_fields)
            
            if not is_valid:
                return jsonify({"error": error_msg}), 400
            
            g.request_json = data
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator
