# Real-time Behavior Detection - User Guide

## Overview
The Smart Monitoring System now includes **AI-powered real-time behavior detection** that analyzes user engagement and activities through webcam monitoring. It detects three behavioral states:

- **🟢 Active**: User is engaged with high movement and open eyes
- **🟡 Dull**: User is present but showing low engagement/movement
- **🔴 Sleepy**: User shows signs of drowsiness or eye closure

## Features

### 1. **Real-time Monitoring**
- Live webcam feed with continuous analysis
- ~30 FPS frame capture and processing
- Real-time behavior state detection

### 2. **Behavioral Metrics**
- **Motion Level**: Detects head and body movement
- **Eye Status**: Tracks eye opening/closure
- **Eyes Detected**: Counts visible eyes
- **Confidence Score**: Reliability of the detection

### 3. **Session Analytics**
- Tracks behavior distribution over session
- Shows percentage breakdown of states
- Generates actionable recommendations

### 4. **Smart Recommendations**
- Suggests breaks if drowsiness detected
- Recommends engagement activities for dull state
- Acknowledges excellent activity levels

## How to Use

### Step 1: Access the Interface
Navigate to:
```
http://localhost:5000/behavior-detection
```

### Step 2: Start Behavior Capture
1. Click **"START CAPTURE"** button
2. Allow camera access when prompted
3. System will begin analyzing your behavior in real-time

### Step 3: Monitor Results
- **Live Feed**: Watch your camera stream
- **Current State**: See your active behavioral state
- **Metrics Panel**: View detailed metrics
- **Session Report**: Track overall behavior distribution

### Step 4: Stop Capture
Click **"STOP CAPTURE"** when done. Camera will be safely released.

## API Endpoints

### 1. Start Behavior Capture
```bash
POST /api/v1/behavior/start-capture
Body: { "camera_id": 0 }
```

### 2. Analyze Single Frame
```bash
GET /api/v1/behavior/analyze-frame
Response: {
  "behavior": "Active|Dull|Sleepy",
  "confidence": 85.5,
  "motion": 15.2,
  "eyes_detected": 2,
  "eyes_closed": false,
  "eye_closure_ratio": 0.15,
  "frame": "base64_encoded_image"
}
```

### 3. Stream Behavior Analysis
```bash
GET /api/v1/behavior/stream
(Server-Sent Events stream)
```

### 4. Get Behavior Summary
```bash
GET /api/v1/behavior/summary
Response: {
  "dominant_state": "Active",
  "frame_count": 150,
  "state_distribution": {
    "Active": 100,
    "Dull": 40,
    "Sleepy": 10
  },
  "percentage": {
    "Active": 66.7,
    "Dull": 26.7,
    "Sleepy": 6.7
  }
}
```

### 5. Generate Behavior Report
```bash
POST /api/v1/behavior/report
Body: { "behavior_data": [...] }
Response: {
  "summary": {
    "total_frames_analyzed": 300,
    "active_percentage": 65.0,
    "dull_percentage": 25.0,
    "sleepy_percentage": 10.0
  },
  "health_status": "Good - User is mostly active",
  "recommendations": [...]
}
```

### 6. Stop Behavior Capture
```bash
POST /api/v1/behavior/stop-capture
```

## Technical Details

### Behavior Detection Algorithm
The system uses multiple CV techniques:

1. **Eye Detection**: OpenCV Haar Cascades for eye region detection
2. **Motion Analysis**: Optical flow computation for movement detection
3. **State Classification**:
   - SLEEPY: Eyes closed OR closure ratio > 30% AND low motion
   - DULL: Eyes open BUT low motion
   - ACTIVE: High motion AND eyes detected and open

### Confidence Scoring
- Base: 50%
- Eye detection bonus: +10-20%
- Clear eye state bonus: +15%
- Motion consistency bonus: +15%
- **Total: 0-100%**

### Performance
- Frame processing: ~33ms per frame (30 FPS)
- Motion detection: Optical flow based
- Eye status: Brightness + contrast analysis
- Low CPU footprint suitable for edge devices

## System Requirements

### Hardware
- Webcam/USB camera
- Minimum 2GB RAM
- 2+ CPU cores

### Software
- Python 3.8+
- OpenCV 4.13+
- Flask 3.1+

## Troubleshooting

### Issue: Camera not connecting
**Solution**: 
- Check camera is not in use by other apps
- Try different camera_id (0, 1, 2...)
- Verify browser camera permissions

### Issue: Inaccurate eye detection
**Solution**:
- Ensure proper lighting
- Position camera at eye level
- Clean camera lens

### Issue: High false positives
**Solution**:
- Adjust thresholds in BehaviorCaptureAnalyzer:
  - `eye_closure_threshold`: 0.3 (30%)
  - `motion_threshold`: 5.0
  - `activity_threshold`: 20.0

## Integration with Dashboard

The behavior detection integrates with your main dashboard:
- Real-time behavior data streams to connected clients
- Anomalies trigger alerts
- Session reports saved to database
- Historical behavior tracking enabled

## Examples

### Example 1: Monitor Student Engagement
```javascript
// Start monitoring
await fetch('/api/v1/behavior/start-capture', {method: 'POST'})

// Check engagement every 5 seconds
setInterval(async () => {
  const res = await fetch('/api/v1/behavior/analyze-frame')
  const data = await res.json()
  if(data.data.behavior === 'Sleepy') {
    alert('Student appears drowsy!')
  }
}, 5000)
```

### Example 2: Generate Hourly Report
```python
import requests

behavior_data = []
for i in range(1800):  # 60 minutes at 30 FPS
    res = requests.get('http://localhost:5000/api/v1/behavior/analyze-frame')
    behavior_data.append(res.json()['data'])

report = requests.post(
    'http://localhost:5000/api/v1/behavior/report',
    json={'behavior_data': behavior_data}
).json()

print(f"Active: {report['summary']['active_percentage']}%")
```

## Security & Privacy

- ✅ All processing done locally (no cloud upload)
- ✅ Images processed in-memory (not stored)
- ✅ Camera access requires explicit permission
- ✅ Base64 encoding for safe transmission
- ✅ HTTPS recommended for production

## Future Enhancements

- 🚀 Multi-person detection
- 🚀 Facial expression analysis
- 🚀 Attention span scoring
- 🚀 Fatigue prediction model
- 🚀 Integration with Slack/Teams for alerts
- 🚀 Historical trend analysis

## Support

For issues or feature requests, contact the development team or check:
- Logs: System logs in terminal
- Debug: Enable verbose logging in config
- API Docs: Check API_DOCUMENTATION.md

---

**Last Updated**: April 16, 2026  
**Version**: 1.0  
**Status**: Production Ready ✅
