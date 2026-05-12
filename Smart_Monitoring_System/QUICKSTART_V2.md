# Smart Monitoring System v2.0 - Quick Start Guide

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
cd Smart_Monitoring_System
pip install -r requirements.txt
```

### 2. Choose Your Setup

#### Option A: Web Dashboard (Recommended for Production)
```bash
python app_dashboard.py
# Visit http://localhost:5000
```

**Features:**
- Live video feed
- Real-time statistics
- Active person tracking
- Alert management
- Downloadable reports

#### Option B: Standalone Video Processing
```bash
python app_enhanced_v2.py
```

**Features:**
- Direct camera access
- No web interface
- Lightweight and fast
- Good for edge computing

#### Option C: Original Simple Version
```bash
python app.py
# Visit http://localhost:5000
```

---

## 🎯 Quick Configuration

### Edit `config.py` for your needs:

#### For Strict Face Recognition (Fewer False Positives)
```python
CONFIDENCE_THRESHOLD = 75
FACE_DETECTION_MIN_NEIGHBORS = 6
FACE_DETECTION_SCALE_FACTOR = 1.1
```

#### For Loose Face Recognition (Catch More Faces)
```python
CONFIDENCE_THRESHOLD = 60
FACE_DETECTION_MIN_NEIGHBORS = 3
FACE_DETECTION_SCALE_FACTOR = 1.05
```

#### For Sensitive Sleep Detection
```python
SLEEP_THRESHOLD = 2.0  # Alert after 2 seconds eyes closed
```

#### For Sensitive Idle Detection
```python
IDLE_THRESHOLD = 3.0   # Alert after 3 seconds no motion
```

#### Enable SMS Alerts (via Twilio)
```python
SMS_ENABLED = True
SMS_ACCOUNT_SID = "your-account-sid"
SMS_AUTH_TOKEN = "your-auth-token"
SMS_FROM_NUMBER = "+1234567890"
SMS_TO_NUMBERS = ["+9876543210"]
```

#### Enable Email Alerts
```python
EMAIL_ENABLED = True
EMAIL_FROM = "your@gmail.com"
EMAIL_PASSWORD = "your-app-password"  # Use app-specific password
ALERT_EMAIL_TO = ["admin@school.com", "parent@home.com"]
```

---

## 📹 First Time Running

### Step 1: Register Students
1. Open the web dashboard
2. Click "Register" tab
3. Enter name and roll number
4. Capture at least 30 face images
5. Click "Train Model"

### Step 2: Configure System
1. Go to Settings
2. Adjust thresholds for your environment
3. Enable/disable alerts as needed
4. Save settings

### Step 3: Start Monitoring
1. Click "Start Monitoring" button
2. System will begin processing video
3. Watch live feed and statistics update in real-time

### Step 4: View Results
1. **Live:** See faces being detected and recognized
2. **Tracking:** Each person gets unique ID (track_id)
3. **Behavior:** See Active/Idle/Sleeping status
4. **Alerts:** Receive notifications for concerning behavior

---

## 🔧 Troubleshooting

### Problem: No faces detected
**Solution:**
- Ensure good lighting
- Check camera is working: `python -c "import cv2; print(cv2.VideoCapture(0).read())"`
- Try "loose" mode in settings
- Reduce `FACE_DETECTION_MIN_NEIGHBORS` to 3

### Problem: Faces not recognized
**Solution:**
- Train model with more images (100+)
- Ensure good lighting during training
- Reduce `CONFIDENCE_THRESHOLD` to 60
- Check trainer/trainer.yml exists

### Problem: Sleep not detecting
**Solution:**
- Ensure eyes can be seen (not looking down)
- Reduce `SLEEP_THRESHOLD` to 2.0 seconds
- Check lighting on face

### Problem: Too many false alerts
**Solution:**
- Increase `ALERT_COOLDOWN_SECONDS` to 10
- Increase `SLEEP_THRESHOLD` to 4.0 seconds
- Increase `IDLE_THRESHOLD` to 7.0 seconds

---

## 📊 Monitoring Types

### 1. Classroom Monitoring
- **Sleep Detection:** Alert when student sleeps
- **Active Tracking:** Monitor multiple students
- **Attendance:** Auto-mark presence
- **Daily Reports:** Engagement trends

### 2. Exam Surveillance
- **Unknown Person Detection:** Flag unregistered persons
- **Spoofing:** Detect identity fraud
- **Suspicious Movement:** Alert on abnormal behavior
- **Logging:** Complete activity record

### 3. Driver Safety
- **Drowsiness Detection:** Real-time sleep alerts
- **Eye Closure:** Track fatigue
- **Head Pose:** Detect distraction
- **Alerts:** Immediate notification to driver/operator

### 4. Workplace Monitoring
- **Attendance:** Auto check-in/out
- **Idle Detection:** Monitor productivity
- **Behavior Logging:** Track engagement
- **Reports:** Daily/weekly summaries

---

## 📱 Mobile Alerting (Optional)

### Setup Firebase for Push Notifications
```python
# Install Firebase
pip install firebase-admin

# In alerts.py
from firebase_admin import messaging

def send_push_notification(device_token, person_name, alert_type):
    message = messaging.Message(
        notification=messaging.Notification(
            title=f"Alert: {person_name}",
            body=f"Person is {alert_type}"
        ),
        token=device_token,
    )
    messaging.send(message)
```

### Mobile App Receives:
- Real-time alerts for sleeping/idle
- Person name and timestamp
- Click to view live feed
- Acknowledge alert directly

---

## 📈 Expected Results

### After 1 hour:
- ✅ ~3600 frames processed
- ✅ ~120 faces detected (varies with crowd)
- ✅ ~10-20 unique persons detected
- ✅ Attendance auto-marked
- ✅ Behavior events logged
- ✅ Any alerts triggered and logged

### Daily Summary:
- Total present: Count of unique persons
- Attendance rate: Present vs absent
- Engagement: Average engagement score
- Alerts: Total sleep/idle alerts
- Longest session: Max continuous presence

---

## 🚀 Advanced Usage

### Custom Detection Mode
```python
from detection import FaceDetector

detector = FaceDetector()

# Try different modes
faces_balanced = detector.detect_faces(frame, mode="balanced")
faces_close = detector.detect_faces(frame, mode="close")
faces_far = detector.detect_faces(frame, mode="far")
faces_strict = detector.detect_faces(frame, mode="strict")
faces_loose = detector.detect_faces(frame, mode="loose")
```

### Event Callbacks
```python
# Get notified when specific events occur
def on_sleep_detected(person_name, duration):
    print(f"{person_name} is sleeping for {duration}s")

# Register callback
alert_manager.set_custom_callback(on_sleep_detected)
```

### Database Queries
```python
from database_enhanced import EnhancedDatabaseManager

db = EnhancedDatabaseManager()

# Get today's attendance
today = db.get_attendance_by_date("2024-04-12")
print(f"Total present: {len(today)}")

# Get person's behavior history
behavior = db.get_person_behavior_summary("John Doe", days=7)
print(f"Sleep events: {behavior['events'].get('sleeping', {}).get('count', 0)}")

# Export daily report
report = db.export_daily_report("2024-04-12")
```

---

## 🎓 Performance Optimization

### For Faster Processing
```python
# In config.py
CAMERA_WIDTH = 640      # Lower resolution
CAMERA_HEIGHT = 480
FACE_DETECTION_SCALE_FACTOR = 1.15  # Faster but less accurate
FACE_DETECTION_MIN_NEIGHBORS = 4    # Faster detection
```

### For Better Accuracy
```python
# In config.py
CAMERA_WIDTH = 1280     # Higher resolution
CAMERA_HEIGHT = 720
FACE_DETECTION_SCALE_FACTOR = 1.05  # Slower but more accurate
FACE_DETECTION_MIN_NEIGHBORS = 6    # Stricter matching
```

### GPU Acceleration (if available)
```bash
# Install CUDA-enabled OpenCV
pip uninstall opencv-python -y
pip install opencv-python-gpu

# System will automatically use GPU
```

---

## 📝 Logging

All events are logged to:
- **`logs/system.log`** - System events
- **`logs/alerts.log`** - Alert history
- **`monitoring.db`** - Database with full event history

### View Recent Alerts
```bash
tail -50 logs/alerts.log
```

### Analyze Attendance
```bash
sqlite3 monitoring.db "SELECT name, COUNT(*) as appearances FROM attendance GROUP BY name ORDER BY appearances DESC;"
```

---

## 🔐 Security & Privacy

1. **Data Storage**: All data stored in encrypted database
2. **Access Control**: Restrict registration endpoint
3. **HTTPS**: Use HTTPS in production
4. **Backups**: Regular database backups
5. **GDPR**: Ensure compliance with regulations
6. **Face Images**: Secure storage recommended

---

## 📞 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Camera not found | Check device ID, try camera_id=1 |
| Low FPS | Reduce resolution or process every 2nd frame |
| High CPU usage | Use GPU acceleration or lower resolution |
| Faces not tracked | Increase lighting or boost detection sensitivity |
| False alerts | Increase thresholds (SLEEP_THRESHOLD, IDLE_THRESHOLD) |
| Database errors | Delete monitoring.db and restart |
| SMS not working | Check Twilio credentials |
| Email not working | Use app-specific password for Gmail |

---

## 📚 Next Steps

1. **Calibrate System**: Adjust thresholds for your environment
2. **Train Models**: Register all students/employees first
3. **Test Alerts**: Verify SMS/Email notifications work
4. **Monitor Performance**: Check logs and database
5. **Enable Backups**: Setup regular database backups
6. **Custom Integration**: Extend with your LMS/ERP
7. **Deploy**: Move to production server

---

## 🎯 Success Checklist

- [ ] All dependencies installed without errors
- [ ] Camera works and streams video
- [ ] Model trained with at least 20 students
- [ ] Face detection working on live video
- [ ] Face recognition identifying students correctly
- [ ] Sleep detection triggering alerts
- [ ] Idle detection working
- [ ] SMS/Email alerts configured
- [ ] Attendance being auto-marked
- [ ] Database storing events correctly
- [ ] Dashboard displaying live data
- [ ] Reports can be exported

---

**Congratulations!** Your Smart Monitoring System v2.0 is ready! 🎉
