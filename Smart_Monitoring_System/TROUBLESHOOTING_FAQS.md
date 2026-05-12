# Troubleshooting & FAQs - Smart Monitoring System v2.0

## 🔧 Common Issues and Solutions

### 1. Face Detection Not Working

**Problem**: System detects no faces or detects very few faces.

**Causes & Solutions**:

```python
# Solution 1: Adjust detection parameters
from detection import FaceDetector

# Try looser detection parameters
detector = FaceDetector(
    scale_factor=1.2,      # Increase to 1.2 or 1.3 (slower but detects more)
    min_neighbors=3,        # Decrease to 3 (fewer strict checks)
    detection_mode='loose'  # Use 'loose' mode
)

# Solution 2: Check lighting conditions
# Apply brightness adjustment
import cv2
import numpy as np

def adjust_brightness(frame, brightness=30):
    """Increase brightness for dark images"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hsv[:,:,2] = cv2.add(hsv[:,:,2], brightness)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

# Solution 3: Clear classifier cache
detector = FaceDetector()
detector.cache.clear()

# Solution 4: Check camera settings
import cv2
cap = cv2.VideoCapture(0)
print("Exposure:", cap.get(cv2.CAP_PROP_EXPOSURE))
print("Auto Exposure:", cap.get(cv2.CAP_PROP_AUTO_EXPOSURE))
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Enable auto-exposure
```

**Check**:
- [ ] Camera is working (`cv2.VideoCapture(0)` works)
- [ ] Good lighting conditions
- [ ] Face is clearly visible
- [ ] Try reducing scale_factor

---

### 2. Face Recognition Showing Low Confidence

**Problem**: Recognition works but confidence scores are very low.

**Causes & Solutions**:

```python
# Solution 1: Retrain model with better images
# Collect 20+ clear images per person, good lighting
import os
os.makedirs('dataset/person_name', exist_ok=True)
# Capture 30 frames per person with variety of angles

# Solution 2: Recalibrate confidence thresholds
from recognition import FaceRecognizer

recognizer = FaceRecognizer()
# Get baseline confidence on known faces
known_face_img = cv2.imread('path/to/known/face.jpg')
gray = cv2.cvtColor(known_face_img, cv2.COLOR_BGR2GRAY)
label, confidence = recognizer.recognize(gray)
print(f"Baseline confidence: {confidence}")

# Adjust threshold accordingly
CONFIDENCE_THRESHOLD = confidence - 10  # 10% buffer

# Solution 3: Enable spoofing detection
recognizer = FaceRecognizer(enable_spoofing_detection=True)

# Solution 4: Use multi-frame verification
confidences = []
for i in range(5):  # Capture 5 frames
    ret, frame = camera.read()
    label, conf = recognizer.recognize(frame)
    confidences.append(conf)

avg_confidence = sum(confidences) / len(confidences)
print(f"Average confidence: {avg_confidence}")
if avg_confidence > THRESHOLD:
    print(f"Recognized: {label}")
```

**Check**:
- [ ] Training images are clear and well-lit
- [ ] Dataset has 20+ images per person minimum
- [ ] Confidence threshold is appropriately set
- [ ] No heavy occlusions (masks, glasses)

---

### 3. High CPU Usage

**Problem**: CPU usage is constantly high (>80%).

**Causes & Solutions**:

```python
# Solution 1: Enable GPU acceleration
from performance_optimizer import PerformanceOptimizer

optimizer = PerformanceOptimizer()
if optimizer.gpu_available():
    print("GPU is available, using CUDA")
    # Use GPU-accelerated operations
else:
    print("GPU not available, using CPU")

# Solution 2: Enable frame skipping
from performance_optimizer import PerformanceOptimizer

optimizer = PerformanceOptimizer(frame_skip=2)
# Process every 2nd frame only

# Solution 3: Reduce resolution
import cv2

def process_frame_scaled(frame, scale=0.5):
    """Process at lower resolution"""
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (int(w*scale), int(h*scale)))
    # Process small frame
    results = detector.detect_faces(small)
    # Scale results back
    for face in results:
        face[0] = int(face[0] / scale)
        face[1] = int(face[1] / scale)
    return results

# Solution 4: Use batch processing
from performance_optimizer import BatchProcessor

batch_processor = BatchProcessor(batch_size=4)
for frame in frame_queue:
    if batch_processor.add_frame(frame):
        batch = batch_processor.get_batch()
        # Process 4 frames at once
        results = detector.detect_faces_batch(batch)

# Solution 5: Implement multi-threading
from performance_optimizer import ParallelProcessor

processor = ParallelProcessor(num_workers=4)
processor.start(detect_and_recognize)

for frame in frames:
    processor.submit_task(frame)
    result = processor.get_result(timeout=0.1)
    if result:
        handle_result(result)
```

**Solutions Priority**:
1. Enable GPU if available
2. Reduce resolution or enable frame skipping
3. Enable multi-threading
4. Reduce detection parameters

---

### 4. Memory Leak Issues

**Problem**: Memory usage keeps increasing over time.

**Causes & Solutions**:

```python
# Solution 1: Monitor memory usage
from performance_optimizer import MemoryOptimizer
import psutil

memory = MemoryOptimizer.get_memory_usage()
print(f"Memory usage: {memory['percent']}%")

# Solution 2: Force garbage collection regularly
import gc
import time

def cleanup_thread():
    while True:
        gc.collect()
        time.sleep(60)  # Every 60 seconds

import threading
cleanup = threading.Thread(target=cleanup_thread, daemon=True)
cleanup.start()

# Solution 3: Clear detection cache periodically
detection_cache = {}
cache_timeout = 300  # 5 minutes

# Solution 4: Use frame buffer pooling
class FrameBufferPool:
    def __init__(self, size, count=3):
        self.buffers = [np.zeros((size[1], size[0], 3), dtype=np.uint8) 
                        for _ in range(count)]
        self.index = 0
    
    def get_buffer(self):
        buf = self.buffers[self.index]
        self.index = (self.index + 1) % len(self.buffers)
        return buf

pool = FrameBufferPool((1280, 720), count=3)

# Use:
frame_buf = pool.get_buffer()
camera.read(frame_buf)  # Reuses buffer instead of allocating new

# Solution 5: Close resources properly
import cv2

cap = cv2.VideoCapture(0)
try:
    while True:
        ret, frame = cap.read()
finally:
    cap.release()
    cv2.destroyAllWindows()
```

**Prevention**:
- [ ] Regular garbage collection every 1-5 minutes
- [ ] Frame buffer pooling instead of reallocation
- [ ] Proper resource cleanup on exit
- [ ] Limit cache sizes
- [ ] Close file handles immediately after use

---

### 5. Video Feed Lag

**Problem**: Streaming video has noticeable delay.

**Causes & Solutions**:

```python
# Solution 1: Reduce frame resolution
import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 24)

# Solution 2: Skip frames in streaming
frame_count = 0
skip_frames = 1

while True:
    ret, frame = cap.read()
    if frame_count % (skip_frames + 1) == 0:
        # Send to browser
        pass
    frame_count += 1

# Solution 3: Use motion JPEG for streaming
def stream_frames():
    while True:
        ret, frame = cap.read()
        # Compress frame
        _, buffer = cv2.imencode('.jpg', frame, 
                                [cv2.IMWRITE_JPEG_QUALITY, 70])
        byte_frame = buffer.tobytes()
        
        yield (b'--frame\\r\\n'
               b'Content-Type: image/jpeg\\r\\n\\r\\n' + 
               byte_frame + b'\\r\\n')

# Solution 4: Use adaptive quality
from performance_optimizer import AdaptiveQualityScaler

scaler = AdaptiveQualityScaler(min_quality=0.5, max_quality=1.0)

while True:
    current_fps = calculate_fps()
    scaler.update_fps(current_fps)
    
    width, height = scaler.get_target_resolution(1280, 720)
    frame = cv2.resize(frame, (width, height))
    
    # Stream frame

# Solution 5: Use separate thread for streaming
import threading
from queue import Queue

frame_queue = Queue(maxsize=2)

def capture_thread():
    while True:
        ret, frame = cap.read()
        try:
            frame_queue.put_nowait(frame)
        except:
            pass  # Drop frame if queue full

def stream_thread():
    while True:
        frame = frame_queue.get()
        yield encode_frame(frame)

capture_t = threading.Thread(target=capture_thread, daemon=True)
capture_t.start()
```

**Optimization Priority**:
1. Reduce resolution
2. Reduce frame rate
3. Increase JPEG compression
4. Use separate threads
5. Use adaptive quality

---

## ❓ Frequently Asked Questions

### Q1: How do I change detection sensitivity?

**A**: Adjust detection parameters in `config.py`:

```python
# More sensitive (detects more, may have false positives)
FACE_DETECTION_SCALE_FACTOR = 1.2  # Lower = more sensitive
FACE_DETECTION_MIN_NEIGHBORS = 3   # Lower = more sensitive

# Less sensitive (fewer false positives)
FACE_DETECTION_SCALE_FACTOR = 1.05  # Higher = less sensitive
FACE_DETECTION_MIN_NEIGHBORS = 7    # Higher = less sensitive
```

---

### Q2: Can I recognize people wearing masks?

**A**: Partially. Masks reduce accuracy. Options:

```python
# Option 1: Train model with mask-wearing people
# Collect training images of people wearing masks

# Option 2: Use eye-based recognition instead
from detection import EyeDetector

eye_detector = EyeDetector()
# Focus on eye region for verification

# Option 3: Add face mask detection first
import cv2
cascades = cv2.CascadeClassifier(
    'cascades/haarcascade_frontalface_alt.xml')
masks = cv2.CascadeClassifier('cascades/lbpcascade_frontalface_improved.xml')
```

---

### Q3: How do I add more people to the system?

**A**: 

```python
# Option 1: Via web dashboard
# 1. Go to web interface
# 2. Click "Register" button
# 3. Enter name
# 4. Click "Capture" and collect 30 images

# Option 2: Programmatically
import cv2
import os

name = "John Doe"
person_dir = f"dataset/{name}"
os.makedirs(person_dir, exist_ok=True)

cap = cv2.VideoCapture(0)
count = 0

while count < 30:
    ret, frame = cap.read()
    cv2.imshow('Capturing...', frame)
    cv2.imwrite(f"{person_dir}/{count:03d}.jpg", frame)
    count += 1
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Then retrain model
# python train_model.py
```

---

### Q4: Why are alerts not being sent?

**A**: Check multiple things:

```python
# 1. Verify alert configuration
from config import *

print(f"Alert SMS: {SMS_ALERTS_ENABLED}")
print(f"Alert Email: {EMAIL_ALERTS_ENABLED}")

# 2. Test Twilio SMS
from alerts import SMSAlertHandler

handler = SMSAlertHandler()
try:
    handler.send_sms("+1234567890", "Test message")
    print("SMS sent successfully")
except Exception as e:
    print(f"SMS error: {e}")

# 3. Test email
from alerts import EmailAlertHandler

handler = EmailAlertHandler()
try:
    handler.send_email("admin@example.com", 
                      "Test", 
                      "Test message")
    print("Email sent successfully")
except Exception as e:
    print(f"Email error: {e}")

# 4. Check cooldown
from alerts import AlertManager

manager = AlertManager(cooldown_seconds=5)
# Alerts are sent only if >5 seconds have passed
```

---

### Q5: How do I export data?

**A**:

```python
# Option 1: Export via web dashboard
# 1. Go to Reports section
# 2. Click "Export CSV"

# Option 2: Programmatically
from database_enhanced import EnhancedDatabaseManager

db = EnhancedDatabaseManager('attendance.db')

# Export today's attendance
df = db.get_attendance_by_date('2024-01-15')
df.to_csv('attendance_2024-01-15.csv', index=False)

# Export person's behavior
behavior = db.get_person_behavior_summary('John Doe')
print(behavior)

# Export daily report
report = db.export_daily_report('2024-01-15')
print(report)
```

---

### Q6: How can I improve recognition accuracy?

**A**:

```python
# 1. Collect better training data
# - Use clear, well-lit photos
# - Vary angles (front, left, right)
# - Vary expressions (neutral, smiling)
# - 30+ images per person minimum

# 2. Retrain the model
# python train_model.py

# 3. Adjust confidence threshold
from config import *

CONFIDENCE_THRESHOLD = 75  # Higher = stricter

# 4. Enable multi-frame verification
def verify_identity(camera, person_id, num_frames=5):
    confidences = []
    for i in range(num_frames):
        ret, frame = camera.read()
        _, conf = recognizer.recognize(frame)
        confidences.append(conf)
    
    avg = sum(confidences) / len(confidences)
    return avg > CONFIDENCE_THRESHOLD

# 5. Use spoofing detection
from recognition import FaceRecognizer

recognizer = FaceRecognizer(enable_spoofing_detection=True)
```

---

### Q7: How do I troubleshoot Docker issues?

**A**:

```bash
# Check if Docker is running
docker ps

# Build image with debug output
docker build -t monitoring:2.0 . --progress=plain

# Run container with logs
docker run -it monitoring:2.0 python app_dashboard.py

# Check container logs
docker logs <container_id>

# Access running container
docker exec -it <container_id> bash

# Test database connection inside container
docker exec <container_id> python -c "import database_enhanced; db = database_enhanced.EnhancedDatabaseManager(); print('DB OK')"
```

---

### Q8: Can I use this on Raspberry Pi?

**A**: Yes, with optimization:

```python
# Raspberry Pi optimized config
import os

# Use Edge profile
from performance_config import get_profile_config

config = get_profile_config('EDGE_DEVICE')

# Install Lite version
# Use Python 3.9+
# Enable hardware acceleration if available

# Install lightweight dependencies
# pip install -r requirements-lite.txt

# Run simplified version
# python app.py --mode=lightweight --max-fps=15
```

---

### Q9: How do I update the system?

**A**:

```bash
# 1. Backup data
cp attendance.csv attendance.csv.backup
cp students.csv students.csv.backup

# 2. Update code
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt --upgrade

# 4. Retrain model (if needed)
python train_model.py

# 5. Restart application
pkill -f "python app"
python app_dashboard.py &
```

---

### Q10: How do I secure the web dashboard?

**A**:

```python
# 1. Add basic authentication
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    users = {'admin': 'hashed_password_here'}
    if username in users:
        return check_password_hash(users.get(username), password)
    return False

@app.route('/api/status')
@auth.login_required
def get_status():
    return {"status": "ok"}

# 2. Use HTTPS
# Setup SSL certificate
# Generate: openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
# app.run(ssl_context=('cert.pem', 'key.pem'))

# 3. Add rate limiting
from flask_limiter import Limiter

limiter = Limiter(app)

@app.route('/api/login', methods=['POST'])
@limiter.limit("5/minute")
def login():
    pass  # Max 5 attempts per minute
```

---

## 🚀 Performance Tips

```python
# 1. Monitor metrics
print(f"FPS: {system.fps}")
print(f"Latency: {system.frame_time_ms}ms")
print(f"Memory: {current_memory_mb}MB")

# 2. Use profiling
import cProfile
profiler = cProfile.Profile()
profiler.enable()
# ... run code
profiler.disable()
profiler.print_stats(10)  # Top 10 functions

# 3. Configure for your hardware
# Edge device -> use EDGE_DEVICE profile
# Laptop -> use LIGHTWEIGHT profile
# Server -> use HIGH_PERFORMANCE profile
# Cloud with GPU -> use GPU_ACCELERATED profile

# 4. Regular maintenance
# - Clear logs monthly
# - Backup database weekly
# - Update dependencies monthly
# - Retrain models quarterly
```

---

## 📞 Getting Help

For additional issues:

1. Check logs: `tail -f logs/*.log`
2. Read documentation: README.md, API_DOCUMENTATION.md
3. Review configuration: config.py, trainer.yml
4. Test individual components separately
5. Enable debug mode: `DEBUG_MODE = True` in config.py

Great! You're now equipped to troubleshoot most issues! 🎯
