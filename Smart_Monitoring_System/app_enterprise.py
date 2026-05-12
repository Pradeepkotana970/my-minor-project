"""
Enhanced Enterprise Flask Application
Integrates authentication, multi-tenancy, security, and monitoring
"""

import logging
import os
from flask import Flask, request, g, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

# Import enterprise modules
from authentication import AuthenticationManager, RBACManager
from api_security import (
    RateLimiter, RequestValidator, SecurityHeaders, CORSManager,
    APIKeyValidator, SecurityMonitor, require_api_key, require_jwt_token,
    rate_limit, validate_json
)
from api_gateway import APIGateway, ResponseFormatter, WebhookManager
from tenant_manager import TenantManager
from analytics import AdvancedAnalytics, ReportGenerator

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_EXPIRY'] = 3600  # 1 hour

# Initialize enterprise modules
auth_manager = AuthenticationManager()
gateway = APIGateway(app)
tenant_manager = TenantManager()
security_monitor = SecurityMonitor()
webhook_manager = WebhookManager()
rate_limiter = RateLimiter(default_requests=1000)

# CORS configuration
cors_manager = CORSManager(allowed_origins=['localhost', 'localhost:3000', '127.0.0.1'])


# ============= Authentication Routes =============

@app.route('/api/v1/auth/register', methods=['POST'])
@rate_limit(requests=5, window=3600)
@validate_json('username', 'email', 'password', 'full_name')
def register():
    """User registration"""
    try:
        data = g.request_json
        
        # Validate email
        if not RequestValidator.validate_email(data['email']):
            return ResponseFormatter.error("Invalid email format", "INVALID_EMAIL", 400)
        
        # Validate password strength
        if len(data['password']) < 8:
            return ResponseFormatter.error("Password must be at least 8 characters", "WEAK_PASSWORD", 400)
        
        # Get or create organization (for multi-tenant)
        org_name = request.headers.get('X-Org-Name', 'default')
        org_id = tenant_manager.create_organization(org_name, 'starter')
        
        # Create user
        user_id = auth_manager.create_user(
            org_id=org_id,
            username=data['username'],
            email=data['email'],
            password=data['password'],
            full_name=data['full_name'],
            role='user'
        )
        
        if not user_id:
            return ResponseFormatter.error("Failed to create user", "USER_CREATION_FAILED", 500)
        
        # Log event
        logger.info(f"New user registered: {data['username']} in org {org_id}")
        
        return ResponseFormatter.success(
            data={
                "user_id": user_id,
                "org_id": org_id,
                "message": "Registration successful. Please log in."
            },
            message="User registered successfully",
            status_code=201
        )
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return ResponseFormatter.error(str(e), "REGISTRATION_ERROR", 500)


@app.route('/api/v1/auth/login', methods=['POST'])
@rate_limit(requests=10, window=60)
@validate_json('username', 'password')
def login():
    """User login"""
    try:
        data = g.request_json
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        # Authenticate
        access_token, refresh_token = auth_manager.authenticate(
            username=data['username'],
            password=data['password'],
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if access_token == "2FA_REQUIRED":
            return ResponseFormatter.success(
                data={"mfa_required": True},
                message="2FA verification required",
                status_code=202
            )
        
        if not access_token:
            security_monitor.log_suspicious_activity(
                "failed_login",
                ip_address,
                f"Failed login attempt for {data['username']}",
                "warning"
            )
            return ResponseFormatter.error("Invalid credentials", "INVALID_CREDENTIALS", 401)
        
        return ResponseFormatter.success(
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer"
            },
            message="Login successful"
        )
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return ResponseFormatter.error(str(e), "LOGIN_ERROR", 500)


@app.route('/api/v1/auth/2fa/setup', methods=['POST'])
@require_jwt_token
def setup_2fa():
    """Setup 2FA for user"""
    try:
        user_id = g.user['user_id']
        
        # Generate 2FA setup
        twofa_data = auth_manager.setup_2fa(user_id)
        
        return ResponseFormatter.success(
            data=twofa_data,
            message="2FA setup initiated"
        )
    
    except Exception as e:
        logger.error(f"2FA setup error: {e}")
        return ResponseFormatter.error(str(e), "2FA_SETUP_ERROR", 500)


@app.route('/api/v1/auth/2fa/verify', methods=['POST'])
@rate_limit(requests=10, window=60)
@validate_json('user_id', 'totp_code')
def verify_2fa():
    """Verify 2FA code"""
    try:
        data = g.request_json
        
        if auth_manager.verify_2fa(data['user_id'], data['totp_code']):
            # Generate tokens after successful 2FA
            access_token = auth_manager._generate_access_token({
                'id': data['user_id'],
                'username': 'unknown',  # Would be retrieved from DB
                'email': 'unknown',
                'org_id': 'unknown',
                'role': 'user'
            })
            refresh_token = auth_manager._generate_refresh_token(data['user_id'])
            
            return ResponseFormatter.success(
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token
                },
                message="2FA verified"
            )
        
        return ResponseFormatter.error("Invalid 2FA code", "INVALID_2FA_CODE", 401)
    
    except Exception as e:
        logger.error(f"2FA verification error: {e}")
        return ResponseFormatter.error(str(e), "2FA_VERIFY_ERROR", 500)


# ============= Organization Management Routes =============

@app.route('/api/v1/organizations', methods=['POST'])
@require_jwt_token
@validate_json('name')
def create_organization():
    """Create new organization (admin only)"""
    try:
        if g.user['role'] != 'admin':
            return ResponseFormatter.error("Admin access required", "UNAUTHORIZED", 403)
        
        data = g.request_json
        
        org_id = tenant_manager.create_organization(data['name'], 'starter')
        
        if not org_id:
            return ResponseFormatter.error("Failed to create organization", "ORG_CREATION_FAILED", 500)
        
        return ResponseFormatter.success(
            data={"org_id": org_id, "name": data['name']},
            message="Organization created",
            status_code=201
        )
    
    except Exception as e:
        logger.error(f"Organization creation error: {e}")
        return ResponseFormatter.error(str(e), "ORG_ERROR", 500)


@app.route('/api/v1/organizations/<org_id>/settings', methods=['GET'])
@require_jwt_token
def get_org_settings(org_id):
    """Get organization settings"""
    try:
        # Verify user has access to this org
        if g.user['org_id'] != org_id and g.user['role'] != 'admin':
            return ResponseFormatter.error("Access denied", "FORBIDDEN", 403)
        
        settings = tenant_manager.get_org_settings(org_id)
        
        return ResponseFormatter.success(data=settings)
    
    except Exception as e:
        logger.error(f"Error fetching org settings: {e}")
        return ResponseFormatter.error(str(e), "SETTINGS_ERROR", 500)


@app.route('/api/v1/organizations/<org_id>/api-keys', methods=['POST'])
@require_jwt_token
@validate_json('name')
def create_api_key(org_id):
    """Create API key for organization"""
    try:
        if g.user['org_id'] != org_id or g.user['role'] != 'admin':
            return ResponseFormatter.error("Access denied", "FORBIDDEN", 403)
        
        data = g.request_json
        
        api_key = tenant_manager.generate_api_key(org_id, data['name'])
        
        if not api_key:
            return ResponseFormatter.error("Failed to create API key", "APIKEY_CREATION_FAILED", 500)
        
        return ResponseFormatter.success(
            data={"api_key": api_key},
            message="API key created",
            status_code=201
        )
    
    except Exception as e:
        logger.error(f"API key creation error: {e}")
        return ResponseFormatter.error(str(e), "APIKEY_ERROR", 500)


# ============= Analytics Routes =============

@app.route('/api/v1/analytics/engagement', methods=['GET'])
@require_jwt_token
def get_engagement_analytics():
    """Get engagement analytics"""
    try:
        org_id = g.user['org_id']
        
        analytics = AdvancedAnalytics(f"attendance_{org_id}.db")
        insights = analytics.get_engagement_insights(org_id)
        
        return ResponseFormatter.success(data=insights)
    
    except Exception as e:
        logger.error(f"Error fetching engagement analytics: {e}")
        return ResponseFormatter.error(str(e), "ANALYTICS_ERROR", 500)


@app.route('/api/v1/analytics/attendance', methods=['GET'])
@require_jwt_token
def get_attendance_analytics():
    """Get attendance analytics"""
    try:
        org_id = g.user['org_id']
        
        analytics = AdvancedAnalytics(f"attendance_{org_id}.db")
        insights = analytics.get_attendance_insights(org_id)
        
        return ResponseFormatter.success(data=insights)
    
    except Exception as e:
        logger.error(f"Error fetching attendance analytics: {e}")
        return ResponseFormatter.error(str(e), "ANALYTICS_ERROR", 500)


@app.route('/api/v1/analytics/alerts', methods=['GET'])
@require_jwt_token
def get_alert_analytics():
    """Get alert analytics"""
    try:
        org_id = g.user['org_id']
        
        analytics = AdvancedAnalytics(f"attendance_{org_id}.db")
        insights = analytics.get_alert_analytics(org_id)
        
        return ResponseFormatter.success(data=insights)
    
    except Exception as e:
        logger.error(f"Error fetching alert analytics: {e}")
        return ResponseFormatter.error(str(e), "ANALYTICS_ERROR", 500)


@app.route('/api/v1/analytics/predictions', methods=['GET'])
@require_jwt_token
def get_predictions():
    """Get predictive insights"""
    try:
        org_id = g.user['org_id']
        
        analytics = AdvancedAnalytics(f"attendance_{org_id}.db")
        insights = analytics.get_predictive_insights(org_id)
        
        return ResponseFormatter.success(data=insights)
    
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}")
        return ResponseFormatter.error(str(e), "ANALYTICS_ERROR", 500)


@app.route('/api/v1/reports/<report_type>', methods=['GET'])
@require_jwt_token
def get_report(report_type):
    """Get generated report"""
    try:
        if report_type not in ['daily', 'weekly', 'monthly']:
            return ResponseFormatter.error("Invalid report type", "INVALID_REPORT_TYPE", 400)
        
        org_id = g.user['org_id']
        
        report_generator = ReportGenerator(f"attendance_{org_id}.db")
        
        if report_type == 'daily':
            report = report_generator.generate_daily_report(org_id)
        elif report_type == 'weekly':
            report = report_generator.generate_weekly_report(org_id)
        else:
            report = report_generator.generate_monthly_report(org_id)
        
        return ResponseFormatter.success(data=report)
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return ResponseFormatter.error(str(e), "REPORT_ERROR", 500)


# ============= Gateway Utilities Routes =============

@app.route('/api/v1/gateway/logs', methods=['GET'])
@require_jwt_token
def get_request_logs():
    """Get API request logs"""
    try:
        if g.user['role'] != 'admin':
            return ResponseFormatter.error("Admin access required", "UNAUTHORIZED", 403)
        
        hours = request.args.get('hours', default=24, type=int)
        org_id = g.user['org_id']
        
        analytics = gateway.get_request_analytics(org_id, hours)
        
        return ResponseFormatter.success(data=analytics)
    
    except Exception as e:
        logger.error(f"Error fetching request logs: {e}")
        return ResponseFormatter.error(str(e), "LOG_ERROR", 500)


@app.route('/api/v1/webhooks', methods=['POST'])
@require_jwt_token
@validate_json('event_type', 'url')
def register_webhook():
    """Register webhook"""
    try:
        if g.user['role'] not in ['admin', 'manager']:
            return ResponseFormatter.error("Admin/Manager access required", "UNAUTHORIZED", 403)
        
        data = g.request_json
        org_id = g.user['org_id']
        
        webhook_id = webhook_manager.register_webhook(
            org_id=org_id,
            event_type=data['event_type'],
            url=data['url']
        )
        
        if not webhook_id:
            return ResponseFormatter.error("Failed to register webhook", "WEBHOOK_REG_FAILED", 500)
        
        return ResponseFormatter.success(
            data={"webhook_id": webhook_id},
            message="Webhook registered",
            status_code=201
        )
    
    except Exception as e:
        logger.error(f"Webhook registration error: {e}")
        return ResponseFormatter.error(str(e), "WEBHOOK_ERROR", 500)


# ============= Health Check & Status Routes =============

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return ResponseFormatter.success(
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "3.0-enterprise"
        }
    )


@app.route('/api/v1/status', methods=['GET'])
@require_jwt_token
def get_status():
    """Get application status"""
    try:
        org_id = g.user['org_id']
        
        status = {
            "org_id": org_id,
            "user_role": g.user['role'],
            "authenticated": True,
            "subscription": tenant_manager.get_subscription_tier(org_id),
            "api_rate_limit": "1000/hour",
            "timestamp": datetime.now().isoformat()
        }
        
        return ResponseFormatter.success(data=status)
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return ResponseFormatter.error(str(e), "STATUS_ERROR", 500)


# ============= Error Handlers =============

@app.errorhandler(400)
def bad_request(error):
    return ResponseFormatter.error("Bad Request", "BAD_REQUEST", 400)


@app.errorhandler(401)
def unauthorized(error):
    return ResponseFormatter.error("Unauthorized", "UNAUTHORIZED", 401)


@app.errorhandler(403)
def forbidden(error):
    return ResponseFormatter.error("Forbidden", "FORBIDDEN", 403)


@app.errorhandler(404)
def not_found(error):
    return ResponseFormatter.error("Resource not found", "NOT_FOUND", 404)


@app.errorhandler(429)
def rate_limit_exceeded(error):
    return ResponseFormatter.error("Rate limit exceeded", "RATE_LIMIT_EXCEEDED", 429)


@app.errorhandler(500)
def internal_error(error):
    return ResponseFormatter.error("Internal Server Error", "INTERNAL_ERROR", 500)


# ============= Middleware Registration =============

@app.after_request
def apply_security_headers(response):
    """Apply security headers to all responses"""
    response = SecurityHeaders.apply(response)
    response = cors_manager.handle_cors(response)
    return response


if __name__ == '__main__':
    logger.info("Starting Enterprise Smart Monitoring System v3.0")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")
    
    # Create some test data if needed
    app.config['JSON_SORT_KEYS'] = False
    
    # Run app
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('ENV', 'development') == 'development'
    )
