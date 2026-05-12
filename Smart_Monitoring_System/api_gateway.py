"""
API Gateway and Middleware
Central routing, request/response transformation, and request logging
"""

import logging
import time
import json
from typing import Callable, Dict, Optional
from functools import wraps
from flask import Flask, request, g, jsonify
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)


class APIGateway:
    """Central API Gateway for routing and middleware"""
    
    def __init__(self, app: Flask = None, db_path: str = "api_gateway.db"):
        """
        Initialize API Gateway
        
        Args:
            app: Flask application instance
            db_path: Path to database for storing request logs
        """
        self.app = app
        self.db_path = db_path
        self.request_log = []
        self.routes: Dict[str, Dict] = {}
        
        self.init_database()
        
        if app:
            self.init_app(app)
    
    def init_database(self):
        """Initialize gateway database"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Request logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    org_id TEXT,
                    user_id TEXT,
                    method TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    status_code INTEGER,
                    response_time_ms REAL,
                    request_size INT,
                    response_size INT,
                    error_message TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            ''')
            
            # Route registry
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS route_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    method TEXT NOT NULL,
                    handler TEXT NOT NULL,
                    requires_auth INTEGER DEFAULT 1,
                    rate_limit INT DEFAULT 100,
                    version TEXT DEFAULT 'v1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_request_logs_timestamp ON request_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_request_logs_org ON request_logs(org_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_request_logs_endpoint ON request_logs(endpoint)')
            
            conn.commit()
            conn.close()
            
            logger.info("API Gateway database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing API gateway database: {e}")
    
    def init_app(self, app: Flask):
        """Initialize with Flask app"""
        self.app = app
        
        # Register middleware
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        logger.info("API Gateway initialized with Flask app")
    
    def register_route(
        self,
        path: str,
        method: str = "GET",
        handler_name: str = None,
        requires_auth: bool = True,
        rate_limit: int = 100,
        version: str = "v1"
    ):
        """
        Register API route
        
        Args:
            path: Route path
            method: HTTP method
            handler_name: Handler function name
            requires_auth: Whether authentication is required
            rate_limit: Rate limit for this route
            version: API version
        """
        route_key = f"{method} {path}"
        
        self.routes[route_key] = {
            "path": path,
            "method": method,
            "handler": handler_name,
            "requires_auth": requires_auth,
            "rate_limit": rate_limit,
            "version": version
        }
        
        # Store in database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO route_registry
                (path, method, handler, requires_auth, rate_limit, version)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (path, method, handler_name, 1 if requires_auth else 0, rate_limit, version))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"Error registering route: {e}")
        
        logger.debug(f"Registered route: {method} {path}")
    
    def before_request(self):
        """Pre-request middleware"""
        # Store start time
        g.start_time = time.time()
        
        # Store request context
        g.request_id = self.generate_request_id()
        g.org_id = None
        g.user_id = None
        
        # Extract organization from header or API key
        org_id = request.headers.get('X-Org-ID')
        if org_id:
            g.org_id = org_id
        
        logger.debug(f"[{g.request_id}] {request.method} {request.path}")
    
    def after_request(self, response):
        """Post-request middleware"""
        # Calculate response time
        response_time_ms = (time.time() - g.start_time) * 1000
        
        # Log request
        self.log_request(
            method=request.method,
            endpoint=request.path,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            request_size=len(request.data) if request.data else 0,
            response_size=0 if getattr(response, 'direct_passthrough', False) else len(response.get_data()),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Add standard headers
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Response-Time'] = f"{response_time_ms:.2f}ms"
        
        return response
    
    def log_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        response_time_ms: float,
        request_size: int = 0,
        response_size: int = 0,
        error_message: str = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """Log API request"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO request_logs
                (org_id, user_id, method, endpoint, status_code, response_time_ms,
                 request_size, response_size, error_message, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                g.org_id,
                g.user_id,
                method,
                endpoint,
                status_code,
                response_time_ms,
                request_size,
                response_size,
                error_message,
                ip_address,
                user_agent
            ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"Error logging request: {e}")
    
    def get_request_analytics(self, org_id: str, hours: int = 24) -> Dict:
        """
        Get request analytics for organization
        
        Args:
            org_id: Organization ID
            hours: Number of hours to analyze
            
        Returns:
            Analytics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get requests from last N hours
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    AVG(response_time_ms) as avg_response_time,
                    MAX(response_time_ms) as max_response_time,
                    SUM(CASE WHEN status_code < 400 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status_code >= 400 AND status_code < 500 THEN 1 ELSE 0 END) as client_errors,
                    SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as server_errors
                FROM request_logs
                WHERE org_id = ? AND timestamp > datetime('now', '-' || ? || ' hours')
            ''', (org_id, hours))
            
            result = cursor.fetchone()
            
            # Get top endpoints
            cursor.execute('''
                SELECT endpoint, COUNT(*) as request_count, AVG(response_time_ms) as avg_time
                FROM request_logs
                WHERE org_id = ? AND timestamp > datetime('now', '-' || ? || ' hours')
                GROUP BY endpoint
                ORDER BY request_count DESC
                LIMIT 10
            ''', (org_id, hours))
            
            top_endpoints = [dict(row) for row in cursor.fetchall()]
            
            # Get error summary
            cursor.execute('''
                SELECT status_code, COUNT(*) as count
                FROM request_logs
                WHERE org_id = ? AND status_code >= 400
                  AND timestamp > datetime('now', '-' || ? || ' hours')
                GROUP BY status_code
            ''', (org_id, hours))
            
            error_summary = {str(row['status_code']): row['count'] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                "total_requests": result['total_requests'] or 0,
                "avg_response_time_ms": result['avg_response_time'] or 0,
                "max_response_time_ms": result['max_response_time'] or 0,
                "successful_requests": result['successful'] or 0,
                "client_errors": result['client_errors'] or 0,
                "server_errors": result['server_errors'] or 0,
                "top_endpoints": top_endpoints,
                "error_summary": error_summary
            }
        
        except Exception as e:
            logger.error(f"Error getting request analytics: {e}")
            return {}
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8]


class ResponseFormatter:
    """Standardize API responses"""
    
    @staticmethod
    def success(data: Dict = None, message: str = "Success", status_code: int = 200) -> tuple:
        """
        Format success response
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        request_id = g.get('request_id', 'unknown')
        
        return jsonify({
            "status": "success",
            "message": message,
            "data": data or {},
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }), status_code
    
    @staticmethod
    def error(message: str, error_code: str = None, status_code: int = 400, details: Dict = None) -> tuple:
        """
        Format error response
        
        Args:
            message: Error message
            error_code: Error code identifier
            status_code: HTTP status code
            details: Additional error details
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        request_id = g.get('request_id', 'unknown')
        
        return jsonify({
            "status": "error",
            "message": message,
            "error_code": error_code,
            "details": details or {},
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }), status_code
    
    @staticmethod
    def paginated(data: list, total: int, page: int = 1, page_size: int = 20) -> tuple:
        """
        Format paginated response
        
        Args:
            data: List of items
            total: Total number of items
            page: Current page number
            page_size: Items per page
            
        Returns:
            Tuple of (response_dict, 200)
        """
        request_id = g.get('request_id', 'unknown')
        
        total_pages = (total + page_size - 1) // page_size
        
        return jsonify({
            "status": "success",
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages
            },
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }), 200


class WebhookManager:
    """Manage webhooks for event notifications"""
    
    def __init__(self, db_path: str = "webhooks.db"):
        """Initialize webhook manager"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize webhooks database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Webhooks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webhooks (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    secret TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP
                )
            ''')
            
            # Webhook deliveries (for retry logic)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webhook_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    webhook_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status_code INTEGER,
                    retry_count INTEGER DEFAULT 0,
                    next_retry TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (webhook_id) REFERENCES webhooks(id)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_webhooks_org ON webhooks(org_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_deliveries_webhook ON webhook_deliveries(webhook_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("Webhook database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing webhook database: {e}")
    
    def register_webhook(
        self,
        org_id: str,
        event_type: str,
        url: str,
        secret: str = None
    ) -> Optional[str]:
        """
        Register webhook
        
        Args:
            org_id: Organization ID
            event_type: Event type to listen for
            url: Webhook URL
            secret: Secret for signing payloads
            
        Returns:
            Webhook ID or None
        """
        import uuid
        import secrets as sec
        
        webhook_id = f"webhook_{uuid.uuid4().hex[:12]}"
        secret = secret or sec.token_urlsafe(32)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO webhooks (id, org_id, event_type, url, secret)
                VALUES (?, ?, ?, ?, ?)
            ''', (webhook_id, org_id, event_type, url, secret))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Registered webhook: {webhook_id}")
            return webhook_id
        
        except Exception as e:
            logger.error(f"Error registering webhook: {e}")
            return None
    
    def trigger_webhook(self, org_id: str, event_type: str, payload: Dict):
        """
        Trigger webhooks for event
        
        Args:
            org_id: Organization ID
            event_type: Event type
            payload: Event payload
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM webhooks
                WHERE org_id = ? AND event_type = ? AND is_active = 1
            ''', (org_id, event_type))
            
            webhooks = cursor.fetchall()
            
            for webhook in webhooks:
                # Queue delivery in background
                self._queue_delivery(webhook, payload)
            
            conn.close()
        
        except Exception as e:
            logger.error(f"Error triggering webhooks: {e}")
    
    def _queue_delivery(self, webhook, payload: Dict):
        """Queue webhook delivery"""
        import json
        from requests import post
        
        try:
            # Sign payload
            from api_security import RequestSigner
            signature = RequestSigner.sign_request(webhook['secret'], payload)
            
            # Make request
            headers = {
                'X-Webhook-Signature': signature,
                'Content-Type': 'application/json'
            }
            
            response = post(webhook['url'], json=payload, headers=headers, timeout=10)
            
            logger.debug(f"Webhook delivery: {webhook['id']} -> {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error delivering webhook: {e}")
