# Smart Monitoring System v2.0 - Implementation Guide

## 🚀 Overview

This is a comprehensive upgrade of your Smart Monitoring System with advanced AI capabilities:

- **Advanced Face Detection**: Multi-scale detection, histogram equalization, close/far optimization
- **Enhanced Face Recognition**: Confidence calibration, spoofing detection, multi-person tracking
- **Sophisticated Behavior Analysis**: Sleep detection (3+ sec eye closure), idle detection, engagement scoring
- **Intelligent Alerts**: Non-blocking sound/voice alerts, SMS via Twilio, Email notifications
- **Comprehensive Database**: Complete event logging, behavior history, analytics
- **Real-time Dashboard**: Live video, statistics, behavioral heatmaps

---

## 📁 Module Architecture

### Core Modules

#### 1. **detection.py** - Advanced Face Detection
```python
from detection import FaceDetector, EyeDetector

# Initialize
detector = FaceDetector()
eye_detector = EyeDetector()

# Detect faces with adaptive mode
faces = detector.detect_with_adaptive_mode(frame)
# Returns: [{x, y, w, h, distance, center, area, confidence_estimate, mode}]

# Get face ROI
face_roi = detector.get_face_roi(frame, face_box)

# Detect eyes
eyes = eye_detector.detect_eyes(face_roi)

# Estimate eye closure
eye_status = eye_detector.estimate_eye_closure(face_roi)
# Returns: {eyes_detected, likely_closed, avg_variance, confidence}
```

**Features:**
- Histogram equalization for lighting conditions
- Multi-scale detection (balanced, close, far, strict, loose modes)
- IoU-based deduplication
- Adaptive mode selection

#### 2. **recognition.py** - Enhanced Face Recognition
```python
from recognition import FaceRecognizer, MultiPersonTracker

# Initialize
recognizer = FaceRecognizer(model_path='trainer/trainer.yml')
tracker = MultiPersonTracker(max_missing_frames=10)

# Recognize face
result = recognizer.recognize_face(face_roi, distance_estimate="medium")
# Returns: {status, name, id, raw_confidence, calibrated_confidence, threshold, passed_threshold}

# Add to history for verification
recognizer.add_to_history("John", confidence=85)

# Get consistency metrics
consistency = recognizer.get_recognition_consistency("John")
# Returns: {recognized_times, avg_confidence, consistency, std_dev}

# Check for spoofing
is_spoofing = recognizer.is_likely_spoofing("John", current_confidence=50)

# Update tracks
tracked_persons = tracker.update_tracks(detected_faces, recognition_results)
# Returns: [{track_id, face, recognition, status}]
```

**Features:**
- Distance-based confidence calibration
- Liveness detection based on confidence consistency
- Multi-person simultaneous tracking
- Face history for verification

#### 3. **behavior.py** - Advanced Behavior Analysis
```python
from behavior import BehaviorAnalyzer, PostureAnalyzer, EngagementAnalyzer

# Initialize
behavior_analyzer = BehaviorAnalyzer(
    sleep_threshold_seconds=3.0,
    idle_threshold_seconds=5.0
)
posture_analyzer = PostureAnalyzer()
engagement_analyzer = EngagementAnalyzer()

# Analyze behavior
result = behavior_analyzer.analyze_behavior(
    track_id=1,
    eye_status=eye_status,
    face_roi=face_roi,
    prev_face_roi=prev_frame_roi
)
# Returns: {behavior, eye_closure_duration, inactivity_duration, alert_triggered, ...}

# Estimate head pose
pose = posture_analyzer.estimate_head_pose(face_roi, face_box)
# Returns: {pose, horizontal_angle, vertical_angle, confidence}

# Calculate engagement
engagement = engagement_analyzer.calculate_engagement(
    track_id=1,
    behavior=result['behavior'],
    eye_closure_duration=result['eye_closure_duration'],
    inactivity_duration=result['inactivity_duration'],
    head_pose=pose
)
# Returns: {engagement_level, average_engagement, engagement_trend, engagement_category}
```

**Behavior States:**
- **Active**: Normal engagement, eyes open, motion detected
- **Idle**: ~5+ seconds inactivity, minimal motion
- **Sleeping**: ~3+ seconds eyes closed continuously

**Engagement Levels:**
- highly_engaged (80-100)
- engaged (60-79)
- neutral (40-59)
- disengaged (20-39)
- very_disengaged (0-19)

#### 4. **alerts.py** - Intelligent Alert System
```python
from alerts import AlertManager, SoundAlertPlayer, VoiceAlertGenerator

# Initialize
alert_manager = AlertManager(
    alert_cooldown_seconds=5,
    enable_sound=True,
    enable_voice=True,
    enable_sms=False,
    enable_email=False
)

# Setup callbacks
sound_player = SoundAlertPlayer('alert.wav')
alert_manager.set_sound_callback(sound_player.play_alert)

# Trigger alert
alert_manager.trigger_alert(
    person_name="John",
    alert_type="sleep",
    track_id=1,
    behavior_data={...}
)

# Setup SMS (requires Twilio)
from alerts import SMSAlertHandler
sms_handler = SMSAlertHandler(
    account_sid="YOUR_SID",
    auth_token="YOUR_TOKEN",
    from_number="+1234567890",
    to_numbers=["+9876543210"]
)
alert_manager.set_sms_callback(sms_handler.send_alert)

# Setup Email
from alerts import EmailAlertHandler
email_handler = EmailAlertHandler(
    sender_email="your@gmail.com",
    sender_password="app_password",
    recipient_emails=["admin@school.com"]
)
alert_manager.set_email_callback(email_handler.send_alert)
```

**Alert Types:**
- `AlertManager.ALERT_SLEEP` - Person is sleeping
- `AlertManager.ALERT_IDLE` - Person is inactive
- `AlertManager.ALERT_UNKNOWN` - Unknown person detected
- `AlertManager.ALERT_SUSPICIOUS` - Suspicious activity

#### 5. **database_enhanced.py** - Comprehensive Data Storage
```python
from database_enhanced import EnhancedDatabaseManager

# Initialize
db = EnhancedDatabaseManager('monitoring.db')

# Add person
person_id = db.add_person(
    external_id=1,
    name="John Doe",
    roll_number="E001",
    email="john@school.com",
    phone="+91234567890"
)

# Mark attendance
attendance_id = db.mark_checkin(
    name="John Doe",
    confidence_score=95.5,
    recognition_confidence=90.2,
    behavior="Active",
    distance_estimate="medium"
)

# Log behavior event
db.log_behavior_event(
    name="John Doe",
    event_type="sleeping",
    duration_seconds=5.2,
    eye_status="closed",
    head_pose="forward",
    engagement_level=15.0,
    motion_detected=False,
    confidence=0.95
)

# Log alert
db.log_alert(
    name="John Doe",
    alert_type="sleep",
    severity="HIGH",
    description="Person sleeping for 5+ seconds"
)

# Get analytics
behavior_summary = db.get_person_behavior_summary("John Doe", days=7)
daily_report = db.export_daily_report("2024-04-12")
```

---

## 🛠️ Configuration

### Edit `config.py` for your setup:

```python
# ========== CAMERA SETTINGS ==========
CAMERA_ID = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

# ========== FACE RECOGNITION ==========
CONFIDENCE_THRESHOLD = 70  # Lower = stricter
FACE_DETECTION_SCALE_FACTOR = 1.1
FACE_DETECTION_MIN_NEIGHBORS = 5

# ========== BEHAVIOR DETECTION ==========
SLEEP_THRESHOLD = 3.0  # Seconds of eye closure
IDLE_THRESHOLD = 5.0   # Seconds without motion

# ========== ALERTS ==========
ENABLE_ALERTS = True
ENABLE_SOUND_ALERTS = True
ENABLE_VOICE_ALERTS = False
ALERT_COOLDOWN_SECONDS = 5

# ========== DATABASE ==========
DATABASE_PATH = Base_DIR / 'monitoring.db'

# ========== SMS (Twilio) ==========
SMS_ENABLED = False
SMS_ACCOUNT_SID = "your-sid"
SMS_AUTH_TOKEN = "your-token"
SMS_FROM_NUMBER = "+1234567890"
SMS_TO_NUMBERS = ["+9876543210"]

# ========== EMAIL ==========
EMAIL_ENABLED = False
EMAIL_FROM = "your@gmail.com"
EMAIL_PASSWORD = "app-password"
ALERT_EMAIL_TO = ["admin@school.com"]
```

---

## ▶️ Running the System

### Option 1: Advanced Video Processing (Recommended)
```bash
python app_enhanced_v2.py
```

Features:
- Real-time multi-person detection and tracking
- Advanced behavior analysis
- Automatic alerts (sound/SMS/Email)
- Complete event logging
- FPS monitoring

### Option 2: Original Flask Web App
```bash
python app.py
# Visit http://localhost:5000
```

### Option 3: Training New Model
```bash
python train_model.py
```

---

## 📊 Database Schema

### Tables

1. **persons** - Registered people
   - id, external_id, name, roll_number, email, phone, photo_path, registration_date, is_active

2. **attendance** - Check-in/out records
   - id, person_id, name, check_in, check_out, duration_seconds, confidence_score, initial_behavior, final_behavior, distance_estimate

3. **behavior_events** - Behavior tracking
   - id, person_id, event_type (sleeping/idle/active), event_timestamp, duration_seconds, eye_status, head_pose, engagement_level, confidence

4. **alerts** - Alert history
   - id, person_id, alert_type (sleep/idle/unknown/suspicious), severity (LOW/MEDIUM/HIGH/CRITICAL), alert_timestamp, acknowledged

5. **recognition_history** - Confidence tracking
   - id, person_id, raw_confidence, calibrated_confidence, distance_estimate, frame_number

6. **session_logs** - Session statistics
   - id, start_time, end_time, total_frames_processed, total_faces_detected, unique_persons_detected

7. **statistics** - Analytics data
   - id, statistic_date, person_id, metric_type, metric_value

---

## 🎯 Key Improvements Over v1.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| **Face Detection** | Basic Haar Cascade | Multi-scale with histogram equalization |
| **Lighting** | ❌ No adaptation | ✅ CLAHE preprocessing |
| **Close Distance** | ❌ Poor | ✅ Optimized multi-scale |
| **Multi-person** | Partial | ✅ Full simultaneous tracking with IDs |
| **Sleep Detection** | Frame-based | ✅ Time-window (3+ sec eye closure) |
| **Idle Detection** | Simple threshold | ✅ Motion + activity analysis |
| **Confidence** | Fixed threshold | ✅ Distance-calibrated, spoofing detection |
| **Alerts** | Sound only | ✅ Sound + Voice + SMS + Email |
| **Database** | CSV + Basic SQLite | ✅ Comprehensive schema with analytics |
| **Head Pose** | ❌ Not available | ✅ Estimated from facial features |
| **Engagement** | ❌ Not tracked | ✅ 0-100 scoring with trends |
| **Event Logging** | ❌ Basic | ✅ Complete behavior history |
| **Reporting** | ❌ Limited | ✅ Daily reports, behavior analysis, trends |

---

## 🚀 Integration Example

```python
from flask import Flask
from app_enhanced_v2 import SmartMonitoringSystem

app = Flask(__name__)
monitoring_system = SmartMonitoringSystem()

@app.route('/start_monitoring')
def start():
    """Start monitoring in background thread"""
    thread = threading.Thread(target=monitoring_system.run_video_loop, daemon=True)
    thread.start()
    return {"status": "monitoring started"}

@app.route('/api/active_tracks')
def get_tracks():
    """Get currently tracked persons"""
    tracks = monitoring_system.tracker.get_active_tracks()
    return {"tracks": tracks}

@app.route('/api/behavior/<name>')
def get_behavior(name):
    """Get person's behavior summary"""
    summary = monitoring_system.behavior_analyzer.get_person_state(name)
    return {"behavior": summary}

if __name__ == '__main__':
    app.run(debug=True)
```

---

## 🔧 Troubleshooting

### Poor Face Detection
- Increase `FACE_DETECTION_MIN_NEIGHBORS` to 4 (less strict)
- Reduce `FACE_DETECTION_SCALE_FACTOR` to 1.05 (more sensitive)
- Use "loose" mode in `detect_with_adaptive_mode()`

### High False Positives
- Increase `CONFIDENCE_THRESHOLD` to 75
- Increase `FACE_DETECTION_MIN_NEIGHBORS` to 6 (stricter)
- Enable spoofing detection

### Sleep/Idle Not Detecting
- Reduce `SLEEP_THRESHOLD` to 2.0 seconds
- Reduce `IDLE_THRESHOLD` to 3.0 seconds
- Check lighting conditions (ensure good illumination)

### Alert Not Triggering
- Check `ENABLE_ALERTS = True` in config
- Verify `ALERT_COOLDOWN_SECONDS` isn't too high
- Check alert callbacks are set correctly

---

## 📈 Performance Tips

1. **Frame Skipping**: Process every 2nd or 3rd frame
   ```python
   if self.frame_count % 2 == 0:
       process_frame()
   ```

2. **Resolution**: Use 640x480 instead of 1280x720 for faster processing

3. **Caching**: Cache face detection results for multi-model

4. **GPU Acceleration**: Use CUDA-enabled OpenCV
   ```bash
   pip install opencv-python-headless-gpu
   ```

5. **Threading**: Use background threads for alerts and database

---

## 🔐 Security Notes

1. **Change SECRET_KEY** in config.py for production
2. **Encrypt SMS tokens** and email passwords
3. **Use HTTPS** for Flask app
4. **Database backups** recommended daily
5. **Access control** - restrict /register endpoint
6. **Face image storage** - ensure GDPR compliance

---

## 📞 Support Features

### For Continuous Inactivity
- Log event after 10+ seconds
- Send SMS to parent after 15 seconds
- Email after 20 seconds

### For Sleep Detection
- Alert after 3 seconds eye closure
- Voice alert every 5 seconds if still sleeping
- SMS to parent after 10 seconds continuous sleep

### For Engagement Tracking
- Track hourly engagement score
- Generate daily engagement report
- Identify patterns across sessions

---

## 🎓 Next Steps

1. **Test with your students** - calibrate thresholds
2. **Add mobile app** - receive push notifications
3. **Integrate LMS** - sync attendance automatically
4. **Add analytics dashboard** - visualize trends
5. **Train custom model** - for better accuracy
6. **Deploy on cloud** - AWS/Google Cloud/Azure
7. **Add biometric verification** - fingerprint backup

---

## 📝 License & Credits

Built with OpenCV, Flask, and advanced AI techniques.
For production use, ensure compliance with privacy regulations.
