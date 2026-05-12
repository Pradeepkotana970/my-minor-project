# Enterprise System Integration & Deployment Guide

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Setup Environment

Create `.env` file:

```env
ENV=development
PORT=5000
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///attendance.db
TENANTS_DB=sqlite:///tenants.db
```

### 3. Run Application

```bash
python app_enterprise.py
```

The app will start at `http://localhost:5000`

### 4. Test Endpoints

```bash
# Health check
curl http://localhost:5000/api/v1/health

# Register new user
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }'
```

---

## Architecture Layers

### Layer 1: HTTP Request

```
Client Request (Browser, Mobile, API)
        ↓
HTTP Method + Headers + Body
```

### Layer 2: API Gateway

```
APIGateway.before_request()
  ├── Generate request ID
  ├── Extract org_id from headers
  ├── Store start time
  └── Log request info
        ↓
Flask Route Matching
```

### Layer 3: Security & Auth

```
@require_jwt_token decorator
  ├── Extract token from "Authorization" header
  ├── Verify JWT signature
  ├── Check token expiry
  ├── Load user info into g.user
  └── Continue if valid, reject if invalid
        ↓
@rate_limit decorator
  ├── Get client identifier (IP or API key)
  ├── Check token bucket
  ├── Allow request if tokens available
  └── Return 429 if rate limited
        ↓
@validate_json decorator
  ├── Check if request is JSON
  ├── Extract JSON data
  ├── Validate required fields present
  ├── Sanitize string inputs
  └── Store in g.request_json
```

### Layer 4: Business Logic

```
Your route handler function
  ├── Access g.user (authenticated user)
  ├── Access g.request_json (validated data)
  ├── Access g.org_id (organization)
  ├── Implement business logic
  └── Generate response
```

### Layer 5: Response Formatting

```
ResponseFormatter.success() or .error()
  ├── Add standard response structure
  ├── Include request ID
  ├── Include timestamp
  ├── Return JSON + status code
```

### Layer 6: Security Headers & Logging

```
app.after_request() middleware
  ├── SecurityHeaders.apply()
  │  └── Add X-Content-Type-Options, X-Frame-Options, etc.
  ├── CORS.handle_cors()
  │  └── Add CORS headers if origin allowed
  ├── gateway.log_request()
  │  └── Insert request data into logs table
  └── Return response
        ↓
HTTP Response to Client
```

---

## Module Interactions

### Authentication Flow

```python
USER REGISTRATION
  POST /api/v1/auth/register
    ↓
  RequestValidator.validate_json()  # Validate required fields
    ↓
  RequestValidator.validate_email()  # Validate email format
    ↓
  TenantManager.create_organization()  # Create org if needed
    ↓
  AuthenticationManager.create_user()  # Hash password & store
    ↓
  ResponseFormatter.success()  # Return user_id and org_id

USER LOGIN
  POST /api/v1/auth/login
    ↓
  RateLimiter.is_allowed()  # Check rate limit
    ↓
  AuthenticationManager.authenticate()  # Check credentials
    ├── Verify password hash
    ├── Check account lockout
    ├── Check 2FA requirement
    └── Generate JWT tokens if success
    ↓
  SecurityMonitor.log_suspicious_activity()  # Log failures
    ↓
  APIGateway.log_request()  # Log to audit trail
    ↓
  ResponseFormatter.success()  # Return access & refresh tokens
```

### Video Processing Pipeline

```python
PROCESS FRAME
  POST /api/v1/monitoring/process-frame
    ↓
  @require_jwt_token  # Verify user
    ↓
  @rate_limit(1000)  # Check rate limit
    ↓
  Detection.detect()  # Find faces
    ├── Apply CLAHE preprocessing
    ├── Use multi-scale detection
    ├── Deduplicate with IoU
    └── Return face regions
    ↓
  Recognition.recognize()  # Identify persons
    ├── Compare with known faces
    ├── Calibrate confidence (near/far)
    ├── Check for spoofing
    └── Return {person_id, confidence, name}
    ↓
  Behavior.analyze()  # Determine behavior
    ├── Detect eye closure (sleep)
    ├── Analyze motion (idle)
    ├── Calculate engagement score
    └── Return {state, confidence, engagement}
    ↓
  BehaviorEvent Logging  # Store to DB
    ↓
  AlertManager.check_alerts()  # Check if alert needed
    ├── Check alert type
    ├── Check cooldown
    ├── Trigger if needed
    └── Sound/Voice/SMS/Email
    ↓
  WebhookManager.trigger_webhook()  # Notify external systems
    ├── Find matching webhooks
    ├── Sign payload
    ├── POST to webhook URL
    └── Queue retry if failed
    ↓
  ResponseFormatter.success()  # Return results
```

### Analytics Pipeline

```python
GET /api/v1/analytics/engagement
  ↓
  @require_jwt_token  # Verify user
  ↓
  AdvancedAnalytics.get_engagement_insights()
    ├── Query behavior_events table
    ├── Calculate daily trends
    ├── Compare persons
    ├── Categorize engagement levels
    └── Return structured insights
  ↓
  ResponseFormatter.success()  # Return formatted response

GET /api/v1/reports/daily
  ↓
  ReportGenerator.generate_daily_report()
    ├── Query attendance data
    ├── Query alerts data
    ├── Query behavior data
    ├── Generate statistics
    ├── Create recommendations
    └── Return comprehensive report
  ↓
  WebhookManager.trigger_webhook()  # Notify if report ready
  ↓
  ResponseFormatter.success()  # Return report
```

---

## Database Schema Overview

### Tenant Database (`tenants.db`)

```
organizations
├── id (PK)
├── name
├── subscription_tier
├── license_key
├── storage_limit_gb
├── api_requests_limit
└── created_at

api_keys
├── id (PK)
├── org_id (FK)
├── key_name
├── key_hash
├── expires_at
└── created_at

subscriptions
├── org_id (PK, FK)
├── tier
├── monthly_cost
├── start_date
└── end_date

usage_metrics
├── org_id (FK)
├── date
├── frames_processed
├── api_calls
├── storage_used
└── alerts_triggered
```

### Authentication Database (`auth.db`)

```
users
├── id (PK)
├── org_id (FK)
├── username
├── email
├── password_hash
├── role
├── is_active
└── created_at

two_factor_auth
├── user_id (FK, PK)
├── secret_key
├── is_enabled
├── backup_codes
└── enabled_at

refresh_tokens
├── id (PK)
├── user_id (FK)
├── token_hash
├── expires_at
└── revoked

login_audit
├── id (PK)
├── user_id (FK)
├── username
├── ip_address
├── user_agent
├── status
└── timestamp
```

### Monitoring Database (`attendance_{org_id}.db`)

```
persons (from Phase 1)
├── id (PK)
├── org_id (FK)
├── name
├── encoding
└── added_date

attendance (from Phase 1)
├── id (PK)
├── person_id (FK)
├── entry_time
├── exit_time
└── org_id (FK)

behavior_events (from Phase 1)
├── id (PK)
├── person_id (FK)
├── event_type
├── timestamp
├── confidence
└── details (JSON)

alerts
├── id (PK)
├── person_id (FK)
├── alert_type
├── timestamp
├── acknowledged
└── acknowledgment_time

recognition_history (from Phase 1)
├── id (PK)
├── person_id (FK)
├── confidence
├── distance
└── timestamp

session_logs (from Phase 1)
├── id (PK)
├── start_time
├── end_time
├── frames_processed
└── alerts_triggered

statistics (from Phase 1)
├── date
├── total_persons
├── attendance_rate
├── avg_engagement
└── total_alerts
```

### API Gateway Database (`api_gateway.db`)

```
request_logs
├── id (PK)
├── timestamp
├── org_id (FK)
├── user_id (FK)
├── method
├── endpoint
├── status_code
├── response_time_ms
├── ip_address
└── user_agent

route_registry
├── id (PK)
├── path
├── method
├── handler
├── requires_auth
├── rate_limit
└── version
```

### Webhooks Database (`webhooks.db`)

```
webhooks
├── id (PK)
├── org_id (FK)
├── event_type
├── url
├── secret
├── is_active
└── created_at

webhook_deliveries
├── id (PK)
├── webhook_id (FK)
├── payload
├── status_code
├── retry_count
└── created_at
```

---

## Common Operations

### Adding a New Route

```python
@app.route('/api/v1/custom/endpoint', methods=['POST'])
@require_jwt_token  # Require authentication
@rate_limit(requests=100)  # Rate limiting
@validate_json('field1', 'field2')  # Input validation
def custom_endpoint():
    """
    Custom endpoint description
    
    Request:
        {"field1": "value1", "field2": "value2"}
    
    Response:
        {"status": "success", "data": {...}}
    """
    try:
        # Get authenticated user
        user = g.user  # {user_id, username, org_id, role, ...}
        
        # Get validated request data
        data = g.request_json
        
        # Your business logic
        result = process_data(data, user['org_id'])
        
        # Check permissions
        if user['role'] not in ['admin', 'manager']:
            return ResponseFormatter.error("Insufficient permissions", "FORBIDDEN", 403)
        
        # Return success
        return ResponseFormatter.success(
            data=result,
            message="Operation completed successfully"
        )
    
    except ValueError as e:
        return ResponseFormatter.error(str(e), "VALIDATION_ERROR", 400)
    except Exception as e:
        logger.error(f"Error: {e}")
        return ResponseFormatter.error(str(e), "INTERNAL_ERROR", 500)
```

### Creating a New Tenant

```python
# During user registration
org_id = tenant_manager.create_organization(
    name="Company Name",
    subscription_tier="professional"  # starter/professional/enterprise
)

# Or programmatically
from tenant_manager import TenantManager
manager = TenantManager()
org_id = manager.create_organization("New Org", "starter")
print(f"Created organization: {org_id}")
```

### Generating API Keys

```python
# For organization
api_key = tenant_manager.generate_api_key(
    org_id="org_123abc",
    key_name="Mobile App Key"
)
print(f"API Key: {api_key}")

# Use in requests
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("https://api.example.com/api/v1/endpoint", headers=headers)
```

### Triggering Alerts Programmatically

```python
from alerts import AlertManager

alerts = AlertManager(db_path="alerts_org_123.db")

# Trigger alert
alert_id = alerts.trigger_alert(
    person_id="person_456",
    alert_type="sleep",
    confidence=0.95
)

# Alert cooldown automatically applied
# Won't trigger same alert within cooldown period
```

### Querying Analytics

```python
from analytics import AdvancedAnalytics, ReportGenerator

analytics = AdvancedAnalytics("attendance_org_123.db")

# Get engagement insights
engagement = analytics.get_engagement_insights(org_id="org_123")
print(engagement)

# Get daily report
reporter = ReportGenerator("attendance_org_123.db")
report = reporter.generate_daily_report(org_id="org_123")
print(report)
```

---

## Monitoring & Maintenance

### Check Application Logs

```bash
# Tail logs
tail -f logs/app.log

# Search for errors
grep "ERROR" logs/app.log | tail -20

# Count requests
grep "GET\|POST\|PUT\|DELETE" logs/app.log | wc -l
```

### Monitor Database Size

```bash
# Check database sizes
ls -lh *.db

# Vacuum databases (optimize)
sqlite3 auth.db "VACUUM;"
sqlite3 tenants.db "VACUUM;"
sqlite3 attendance_org_123.db "VACUUM;"
```

### Check Rate Limiting

```bash
# Test rate limiting
for i in {1..150}; do
  curl -s http://localhost:5000/api/v1/health \
    -H "X-Forwarded-For: 192.168.1.1" \
    -o /dev/null
done

# Should see 429 Too Many Requests after limit
```

### Verify Security

```bash
# Check response headers
curl -i http://localhost:5000/api/v1/health

# Should see security headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# etc.
```

---

## Troubleshooting

### Issue: "Module not found" Error

```
ImportError: No module named 'pyotp'

Solution:
pip install -r requirements.txt
# OR
pip install pyotp qrcode PyJWT
```

### Issue: "Database is locked"

```
sqlite3.OperationalError: database is locked

Solution:
1. Ensure timeout=30 in sqlite3.connect()
2. Use context managers for connections
3. Reduce concurrent writes
4. Switch to PostgreSQL for production
```

### Issue: "Invalid token" on API requests

```
{"status": "error", "message": "Invalid or expired token"}

Solution:
1. Verify token included in Authorization header
2. Check token hasn't expired
3. Use correct Bearer format: "Bearer {token}"
4. Verify JWT_SECRET matches between requests
```

### Issue: "Rate limit exceeded"

```
{"status": "error", "message": "Rate limit exceeded"}

Solution:
1. Wait for token bucket to refill
2. Use API key for higher rate limit
3. Upgrade subscription tier
4. Implement request batching or caching
```

---

## Performance Optimization

### Database Optimization

```python
# Add indexes frequently queried columns
cursor.execute('CREATE INDEX idx_org_date ON request_logs(org_id, timestamp)')

# Batch inserts
values = [(v1, v2), (v3, v4), ...]
cursor.executemany('INSERT INTO table VALUES (?, ?)', values)

# Use PRAGMA for speed
cursor.execute('PRAGMA synchronous = NORMAL')  # Faster inserts
cursor.execute('PRAGMA journal_mode = WAL')  # Write-ahead logging
```

### API Optimization

```python
# Cache frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=128)
def get_org_settings(org_id):
    # Settings won't change frequently
    return tenant_manager.get_org_settings(org_id)

# Paginate large datasets
page = request.args.get('page', default=1, type=int)
page_size = 20
offset = (page - 1) * page_size

cursor.execute(
    'SELECT * FROM request_logs LIMIT ? OFFSET ?',
    (page_size, offset)
)
```

### Video Processing Optimization

```python
# Use frame skipping
frame_count = 0
SKIP_FRAMES = 2  # Process every 3rd frame

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    if frame_count % SKIP_FRAMES != 0:
        continue
    
    # Process frame (every 3rd frame)
    results = process_frame(frame)
```

---

## Next Steps

### Immediate (Week 1)
- [ ] Deploy to staging environment
- [ ] Configure SSL/TLS certificates
- [ ] Setup monitoring (Prometheus, Grafana)
- [ ] Test all authentication flows
- [ ] Load test the API

### Short-term (Week 2-4)
- [ ] Deploy to production
- [ ] Configure CDN for static assets
- [ ] Setup backup and recovery system
- [ ] Implement analytics dashboard
- [ ] Train support team

### Medium-term (Month 2-3)
- [ ] Develop mobile apps
- [ ] Implement OAuth integrations
- [ ] Advanced compliance features
- [ ] Real-time WebSocket support
- [ ] Machine learning predictions

### Long-term (Quarter 2+)
- [ ] Multi-region deployment
- [ ] Advanced visualization dashboards
- [ ] Integration marketplace
- [ ] API versioning strategy
- [ ] Community contributions

---

## Support Resources

- **Documentation**: See ENTERPRISE_ARCHITECTURE.md
- **API Reference**: See API_DOCUMENTATION.md
- **Error Codes**: Check ResponseFormatter error codes
- **Logs**: View application.log for debugging
- **Database**: sqlite3 CLI for inspection

---

**Last Updated**: January 2024  
**Version**: 3.0 Enterprise  
**Status**: Production Ready
