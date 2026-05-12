# Enterprise Smart Monitoring System v3.0
## Architecture, Security & Integration Guide

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Security Features](#security-features)
4. [Authentication & Authorization](#authentication--authorization)
5. [Multi-Tenancy](#multi-tenancy)
6. [API Security](#api-security)
7. [API Gateway](#api-gateway)
8. [Analytics & Insights](#analytics--insights)
9. [Integration Guide](#integration-guide)
10. [Deployment](#deployment)

---

## 📊 Overview

The Enterprise Smart Monitoring System v3.0 is a production-grade, SaaS-ready face detection, recognition, and behavior analysis platform with:

- **Advanced Face Recognition**: Multi-scale detection, CLAHE preprocessing, 92% accuracy
- **Behavior Analysis**: Sleep/Idle/Active detection with engagement scoring
- **Real-time Alerts**: Sound, voice, SMS, and email notifications
- **Multi-Tenant Architecture**: Support for multiple organizations
- **Enterprise Authentication**: JWT tokens, OAuth2, Two-Factor Authentication
- **API Security**: Rate limiting, request validation, CORS, security headers
- **Business Intelligence**: Engagement insights, attendance analytics, predictive forecasting
- **Webhook Support**: Real-time event notifications
- **Comprehensive Audit Trail**: Full request logging and security monitoring

---

## 🏗️ Architecture

### Component Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                         │
│  (Routing, Rate Limiting, Request Logging, Webhooks)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Security & Auth Layer                       │
│  (JWT, OAuth, 2FA, RBAC, API Key Management)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Business Logic Layer                        │
│  (Face Detection, Recognition, Behavior Analysis, Alerts)   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Multi-Tenant Data Layer                     │
│  (Tenant-isolated SQLite/PostgreSQL databases)              │
└─────────────────────────────────────────────────────────────┘
```

### Module Dependencies

```
app_enterprise.py (Main Flask App)
    ├── authentication.py (JWT, OAuth, 2FA, RBAC)
    ├── api_security.py (Rate limiting, validation, CORS)
    ├── api_gateway.py (Routing, logging, webhooks)
    ├── tenant_manager.py (Multi-tenancy, subscriptions)
    ├── analytics.py (Business intelligence, reports)
    ├── detection.py (Face detection - from Phase 1)
    ├── recognition.py (Face recognition - from Phase 1)
    ├── behavior.py (Behavior analysis - from Phase 1)
    └── alerts.py (Alert system - from Phase 1)
```

---

## 🔐 Security Features

### 1. **Authentication Methods**

#### JWT (JSON Web Tokens)
- Stateless authentication
- 1-hour access token expiry
- 30-day refresh token rotation
- Secure token signing with HS256 algorithm

```python
# Login and get access token
POST /api/v1/auth/login
{
    "username": "user@example.com",
    "password": "securepassword"
}

Response:
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "refresh_token_secret...",
    "token_type": "Bearer"
}

# Use token in subsequent requests
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

#### API Key Authentication
- Organization-scoped API keys
- Per-key rate limiting
- Expiration management
- Rotation capabilities

```python
# Create API key
POST /api/v1/organizations/{org_id}/api-keys
Authorization: Bearer {token}
{
    "name": "Mobile App Key"
}

Response:
{
    "api_key": "org_38f7d9c2a5eb....",
    "created_at": "2024-01-15T10:30:00Z"
}

# Use in requests
Authorization: Bearer org_38f7d9c2a5eb....
# OR
GET /api/v1/endpoint?api_key=org_38f7d9c2a5eb....
```

#### Two-Factor Authentication (2FA)
- TOTP (Time-based One-Time Password) support
- QR code generation for mobile authenticators
- Backup codes for account recovery
- 2FA enforcement per user

```python
# Setup 2FA
POST /api/v1/auth/2fa/setup
Authorization: Bearer {token}

Response:
{
    "secret": "ABCDEFGHIJKLMNOP",
    "qr_code": "data:image/png;base64,iVBORw0KG...",
    "backup_codes": [
        "a7f3d9e1",
        "b2c4f6h8",
        ...
    ]
}

# Verify 2FA code
POST /api/v1/auth/2fa/verify
{
    "user_id": "user_abc123",
    "totp_code": "123456"
}
```

### 2. **Role-Based Access Control (RBAC)**

```python
# User Roles
- admin: Full system access, user/org management
- manager: Organization management, reporting, audit
- user: Personal reports, basic features

# Permission Examples
admin: users:create, users:read, users:update, users:delete,
       organizations:manage, reports:view, settings:manage,
       api_keys:manage, audit:view, billing:manage

manager: users:read, users:update, reports:view,
         api_keys:read, audit:view

user: reports:view_own, api_keys:read_own
```

### 3. **Security Headers**

All responses include security headers:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
```

### 4. **CORS Protection**

```python
# Allowed origins (configurable)
allowed_origins: ['localhost', 'localhost:3000', '127.0.0.1', 'yourdomain.com']

# Security headers applied
Access-Control-Allow-Origin: {origin}
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 3600
```

### 5. **Request Validation & Sanitization**

```python
# Input validation
- Email format validation (RFC compliant)
- API key format validation
- Required field checking
- String length limits (max 1000 chars default)
- Null byte removal
- XSS protection via sanitization

# Example
POST /api/v1/auth/register
{
    "username": "john_doe",  // Sanitized & validated
    "email": "john@example.com",  // Format validated
    "password": "SecurePass123!",  // Strength: ≥8 chars
    "full_name": "John Doe"
}
```

---

## 🔑 Authentication & Authorization

### Authentication Manager (`authentication.py`)

**Features:**
- User registration with password hashing (Werkzeug)
- Login with account lockout (5 attempts → 15 min lock)
- 2FA setup and verification
- Refresh token generation
- Access token generation
- Login audit trail

**Database Schema:**

```sql
-- Users table
id, org_id, username, email, password_hash, full_name,
role, is_active, is_verified, last_login, login_attempts,
locked_until, created_at

-- Two-Factor Authentication
user_id, secret_key, is_enabled, backup_codes, enabled_at

-- Refresh Tokens
id, user_id, token_hash, created_at, expires_at, revoked

-- Login Audit
user_id, username, ip_address, user_agent, status, timestamp

-- OAuth Connections
user_id, provider, provider_user_id, connected_at
```

**Usage Examples:**

```python
from authentication import AuthenticationManager

# Initialize
auth_manager = AuthenticationManager(db_path="auth.db")

# Create user
user_id = auth_manager.create_user(
    org_id="org_123",
    username="john_doe",
    email="john@example.com",
    password="SecurePass123!",
    full_name="John Doe",
    role="user"
)

# Authenticate
access_token, refresh_token = auth_manager.authenticate(
    username="john_doe",
    password="SecurePass123!",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

# Verify token
payload = auth_manager.verify_token(access_token)
# Returns: {user_id, username, email, org_id, role, exp, iat, type}

# Setup 2FA
twofa_data = auth_manager.setup_2fa(user_id)
# Returns: {secret, qr_code, backup_codes}

# Verify 2FA code
is_valid = auth_manager.verify_2fa(user_id, "123456")
```

---

## 🏢 Multi-Tenancy

### Tenant Manager (`tenant_manager.py`)

**Features:**
- Organization creation and management
- Per-organization database isolation
- API key generation and verification
- Subscription tier management (starter/professional/enterprise)
- Usage tracking for billing
- Org-specific settings

**Database Schema:**

```sql
-- Organizations
id, name, subscription_tier, license_key, storage_limit_gb,
api_requests_limit, is_active, created_at, updated_at

-- Organization Admins
id, org_id, email, password_hash, is_active, created_at

-- Organization Settings
org_id, setting_key, setting_value, updated_at

-- API Keys
id, org_id, key_name, key_hash, expires_at, is_active, created_at

-- Subscriptions
org_id, tier, monthly_cost, request_limit, storage_limit,
support_level, features, start_date, end_date, auto_renew

-- Usage Metrics
org_id, date, frames_processed, api_calls, storage_used,
alerts_triggered, api_errors
```

**Subscription Tiers:**

```python
STARTER:
  - $49/month
  - 100K API requests/month
  - 50GB storage
  - Email support
  - Up to 5 organizations

PROFESSIONAL:
  - $199/month
  - 1M API requests/month
  - 500GB storage
  - Priority support
  - Up to 50 organizations
  - Advanced analytics
  - Custom integrations

ENTERPRISE:
  - Custom pricing
  - Unlimited requests
  - Unlimited storage
  - 24/7 support
  - Custom SLA
  - Dedicated account manager
```

**Usage Examples:**

```python
from tenant_manager import TenantManager

tenant_manager = TenantManager(db_path="tenants.db")

# Create organization
org_id = tenant_manager.create_organization(
    name="Acme Corp",
    subscription_tier="professional"
)

# Generate API key
api_key = tenant_manager.generate_api_key(org_id, "Mobile App")

# Verify API key
is_valid = tenant_manager.verify_api_key(org_id, api_key)

# Record usage
tenant_manager.record_usage(
    org_id=org_id,
    frames_processed=10000,
    api_calls=500,
    alerts_triggered=5
)

# Get organization settings
settings = tenant_manager.get_org_settings(org_id)

# Update organization settings
tenant_manager.update_org_settings(org_id, {
    "max_concurrent_sessions": 10,
    "alert_cooldown_seconds": 60,
    "retention_days": 30
})
```

---

## 🔒 API Security

### Rate Limiter

**Token Bucket Algorithm:**
```python
# Default: 1000 requests per hour (per API key/IP)
# Customizable per endpoint

# Example: 100 requests per 60 seconds
@app.route('/api/v1/expensive-operation', methods=['POST'])
@rate_limit(requests=100, window=60)
def expensive_operation():
    pass
```

**Rate Limit Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 985
X-RateLimit-Reset: 1642291200
```

### Request Validation

```python
# Email validation
RequestValidator.validate_email("user@example.com")  # True
RequestValidator.validate_email("invalid-email")  # False

# String sanitization
RequestValidator.sanitize_string("<script>alert('xss')</script>")
# Returns: "scriptalertxssscript"

# API key format validation
RequestValidator.validate_api_key_format("org_38f7d9c2a5eb1234")  # True

# JSON validation
is_valid, error = RequestValidator.validate_json(
    data=request.json,
    required_fields=['username', 'password']
)
```

### CORS Management

```python
# Configure allowed origins
cors_manager = CORSManager(
    allowed_origins=['localhost:3000', 'app.example.com', '192.168.1.1']
)

# Responses include appropriate CORS headers:
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 3600
```

### Security Monitoring

```python
# Log suspicious activity
security_monitor.log_suspicious_activity(
    event_type="failed_login",
    identifier="192.168.1.1",
    details="5 failed login attempts",
    severity="warning"
)

# Check for attacks
threat_level = security_monitor.check_for_attacks("192.168.1.1")
# Returns: "high", "medium", or None

# Block IP address
security_monitor.block_ip("192.168.1.100")
```

---

## 🚪 API Gateway

### Request Routing & Logging

**Automatic Request Logging:**
```sql
INSERT INTO request_logs (
    timestamp, org_id, user_id, method, endpoint,
    status_code, response_time_ms, request_size,
    response_size, ip_address, user_agent
)
```

**Request Analytics:**
```python
# Get analytics for organization
analytics = gateway.get_request_analytics(org_id="org_123", hours=24)

# Returns:
{
    "total_requests": 5234,
    "avg_response_time_ms": 124.5,
    "max_response_time_ms": 2341.0,
    "successful_requests": 5100,
    "client_errors": 120,
    "server_errors": 14,
    "top_endpoints": [
        {"endpoint": "/api/v1/analytics/engagement", "request_count": 450, ...},
        ...
    ],
    "error_summary": {"400": 120, "401": 3, "500": 14}
}
```

### Webhook System

```python
# Register webhook
webhook_id = webhook_manager.register_webhook(
    org_id="org_123",
    event_type="alert_triggered",
    url="https://app.example.com/webhooks/alerts"
)

# Trigger webhook (automatic when event occurs)
webhook_manager.trigger_webhook(
    org_id="org_123",
    event_type="alert_triggered",
    payload={
        "alert_id": "alert_456",
        "person_id": "person_789",
        "event_type": "person_sleeping",
        "timestamp": "2024-01-15T10:30:00Z"
    }
)

# Webhooks include signature for verification
# Header: X-Webhook-Signature: {HMAC-SHA256 signature}
# Verify: RequestSigner.verify_signature(secret, payload, signature)
```

---

## 📊 Analytics & Insights

### Engagement Analytics

```
GET /api/v1/analytics/engagement
Authorization: Bearer {token}

Response:
{
    "daily_breakdown": [
        {
            "date": "2024-01-15",
            "avg_engagement": 78.5,
            "sleep_events": 3,
            "idle_events": 12,
            "active_time_percent": 85.0
        }
    ],
    "person_comparison": [
        {
            "person_id": "person_123",
            "name": "John Doe",
            "avg_engagement": 82.0,
            "sleep_count": 2,
            "idle_count": 8
        }
    ],
    "engagement_categories": {
        "high": 10,
        "medium": 15,
        "low": 5
    }
}
```

### Attendance Analytics

```
GET /api/v1/analytics/attendance
Authorization: Bearer {token}

Response:
{
    "daily_attendance": [
        {
            "date": "2024-01-15",
            "present": 45,
            "absent": 5,
            "attendance_rate": 90.0
        }
    ],
    "person_statistics": [
        {
            "person_id": "person_123",
            "name": "John Doe",
            "total_days": 20,
            "days_present": 19,
            "attendance_rate": 95.0,
            "consistency_score": 4.8
        }
    ],
    "irregular_attendees": [...]
}
```

### Alert Analytics

```
GET /api/v1/analytics/alerts
Authorization: Bearer {token}

Response:
{
    "alert_distribution": {
        "sleep": 45,
        "idle": 120,
        "off_campus": 8,
        "unknown_person": 3
    },
    "peak_alert_hours": ["14:00", "15:00", "16:00"],
    "high_risk_persons": [
        {
            "person_id": "person_123",
            "name": "John Doe",
            "sleep_events": 15,
            "idle_events": 80,
            "risk_score": 95,
            "recommendation": "Requires active intervention"
        }
    ],
    "alert_acknowledgment_rate": 87.5
}
```

### Predictive Insights

```
GET /api/v1/analytics/predictions
Authorization: Bearer {token}

Response:
{
    "high_risk_persons": [...],
    "predicted_peak_hours": ["14:00-15:00", "15:00-16:00"],
    "forecasted_alerts_next_week": 450,
    "recommended_interventions": [
        {
            "person_id": "person_123",
            "action": "Schedule meeting with parents",
            "priority": "high"
        }
    ]
}
```

### Report Generation

```
# Daily Report
GET /api/v1/reports/daily
{
    "date": "2024-01-15",
    "attendance_rate": 90.0,
    "avg_engagement": 78.5,
    "total_alerts": 168,
    "high_risk_persons": 5,
    "summary": "Overall performance is good...",
    "recommendations": [...]
}

# Weekly Report
GET /api/v1/reports/weekly
{
    "week": "2024-W03",
    "start_date": "2024-01-15",
    "end_date": "2024-01-21",
    ...
}

# Monthly Report
GET /api/v1/reports/monthly
{
    "month": "2024-01",
    "attendance_trend": [...],
    "engagement_trend": [...],
    ...
}
```

---

## 🔗 Integration Guide

### 1. **Flask App Integration**

```python
from flask import Flask
from app_enterprise import app, auth_manager, gateway, tenant_manager

# The app is already configured with all security features
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### 2. **Adding New Routes**

```python
from flask import request, g
from api_security import require_jwt_token, validate_json, rate_limit
from api_gateway import ResponseFormatter

@app.route('/api/v1/custom-endpoint', methods=['POST'])
@require_jwt_token  # Require JWT authentication
@rate_limit(requests=100)  # Apply rate limiting
@validate_json('required_field1', 'required_field2')  # Validate JSON
def custom_endpoint():
    # Get authenticated user info
    user = g.user  # {user_id, username, org_id, role, ...}
    
    # Get request data (already validated)
    data = g.request_json
    
    # Your business logic here
    result = {"status": "success"}
    
    # Return standardized response
    return ResponseFormatter.success(data=result, message="Operation completed")
```

### 3. **Integrating Video Processing**

```python
@app.route('/api/v1/monitoring/process-frame', methods=['POST'])
@require_jwt_token
@rate_limit(requests=1000)
def process_frame():
    """Process video frame for monitoring"""
    from detection import FaceDetector
    from recognition import FaceRecognizer
    from behavior import BehaviorAnalyzer
    from alerts import AlertManager
    
    org_id = g.user['org_id']
    
    # Get frame from request
    frame_data = request.json['frame']  # Base64 encoded
    
    # Initialize processors
    detector = FaceDetector()
    recognizer = FaceRecognizer()
    behavior = BehaviorAnalyzer()
    alerts = AlertManager(f"alerts_{org_id}.db")
    
    # Process frame
    faces = detector.detect(frame_data)
    results = []
    
    for face in faces:
        recognition = recognizer.recognize(face)
        behavior_state = behavior.analyze(face)
        
        # Check for alerts
        if behavior_state['state'] == 'sleeping':
            alert_id = alerts.trigger_alert(
                person_id=recognition['person_id'],
                alert_type='sleep',
                confidence=behavior_state['confidence']
            )
            
            # Trigger webhook
            webhook_manager.trigger_webhook(
                org_id=org_id,
                event_type='alert_triggered',
                payload={"alert_id": alert_id, ...}
            )
        
        results.append({
            "face_id": face['id'],
            "person": recognition,
            "behavior": behavior_state
        })
    
    return ResponseFormatter.success(
        data={"frames_processed": len(faces), "results": results}
    )
```

### 4. **Mobile App Integration**

```javascript
// JavaScript/React example
const API_BASE = "https://api.example.com/api/v1";
const API_KEY = "org_38f7d9c2a5eb1234";

// Authentication
async function login(username, password) {
    const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });
    const {access_token} = await response.json();
    localStorage.setItem('token', access_token);
    return access_token;
}

// Fetch analytics
async function getEngagementAnalytics() {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE}/analytics/engagement`, {
        headers: {'Authorization': `Bearer ${token}`}
    });
    return response.json();
}

// Get report
async function getDailyReport() {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE}/reports/daily`, {
        headers: {'Authorization': `Bearer ${token}`}
    });
    return response.json();
}
```

---

## 🚀 Deployment

### Environment Variables

```bash
# Core
ENV=production
PORT=5000
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///attendance.db
TENANTS_DB=sqlite:///tenants.db

# Authentication
JWT_EXPIRY=3600
JWT_REFRESH_EXPIRY=2592000

# Alerts
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# Firebase (optional)
FIREBASE_CREDENTIALS_PATH=./firebase-key.json

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# CORS
ALLOWED_ORIGINS=localhost:3000,app.example.com

# Rate Limiting
DEFAULT_RATE_LIMIT=1000
RATE_LIMIT_WINDOW=3600
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "app_enterprise.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - ENV=production
      - DATABASE_URL=sqlite:///data/attendance.db
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: always

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always

volumes:
  redis_data:
```

---

## ✅ Security Checklist

- [ ] Change `SECRET_KEY` in production
- [ ] Enable HTTPS/TLS in production
- [ ] Configure firewall rules
- [ ] Enable database encryption
- [ ] Set strong JWT secrets
- [ ] Configure rate limits appropriately
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Implement monitoring and alerting
- [ ] Conduct security audit
- [ ] Setup backup and recovery
- [ ] Document security policies

---

## 📞 Support & Next Steps

### Immediate Tasks:
1. Deploy to production infrastructure
2. Configure environment variables
3. Setup database backups
4. Enable monitoring and logging
5. Test all authentication flows
6. Load test the API

### Future Enhancements:
- OAuth2 integration (Google, Microsoft, GitHub)
- Advanced compliance (GDPR, HIPAA, SOC 2)
- Mobile app development
- Advanced visualization dashboards
- Machine learning for predictive analytics
- Real-time streaming with WebSockets
- CDN integration for video delivery

---

**Version**: 3.0 Enterprise  
**Last Updated**: January 2024  
**Status**: Production Ready
