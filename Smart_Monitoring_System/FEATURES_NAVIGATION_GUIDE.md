# 🚀 Smart Monitoring System - Quick Navigation Guide

## 🌐 Access URLs

### Local Access
- **Dashboard**: http://localhost:5000
- **Registration**: http://localhost:5000/register
- **History**: http://localhost:5000/history  
- **Settings**: http://localhost:5000/settings
- **Behavioral Alerts**: http://localhost:5000/alerts
- **Video Feed**: http://localhost:5000/video

### Network Access (from other devices)
- **Dashboard**: http://192.168.51.29:5000
- **Registration**: http://192.168.51.29:5000/register
- **History**: http://192.168.51.29:5000/history
- **Settings**: http://192.168.51.29:5000/settings
- **Behavioral Alerts**: http://192.168.51.29:5000/alerts

---

## 📄 UI Pages Available

| Page | URL | Purpose | Features |
|------|-----|---------|----------|
| **Dashboard** | / | Main monitoring | Live video, stats, quick actions |
| **Register** | /register | Add new users | Upload or camera capture modes |
| **History** | /history | View records | Attendance with timestamps |
| **Settings** | /settings | Configure system | Alerts, reports, thresholds |
| **Alerts** | /alerts | Behavioral analysis | Alert history and statistics |

---

## 🔌 API Endpoints

### Authentication & Users
```
GET    /register                          - Registration page
POST   /register                          - Submit registration data
POST   /api/delete-user/<name>           - Delete user and data
POST   /train                             - Manually train model
```

### Attendance & Monitoring
```
GET    /stats                             - Get attendance statistics
GET    /api/attendance                    - Get attendance records
POST   /api/reset                         - Reset daily attendance
GET    /video                             - Video stream (MJPEG)
GET    /api/video_feed                    - Video feed alias
```

### Settings Management
```
GET    /api/settings                      - Get current settings
POST   /api/settings                      - Update settings
GET    /api/settings/load                 - Reload from file (auto on startup)
```

### Behavioral Analytics
```
GET    /api/behavioral_alerts             - Get alerts (with filters)
POST   /api/behavioral_alerts             - Record new alert
GET    /api/behavioral_stats              - Get statistics summary
```

---

## 🎮 Feature Access Quick Links

### For Administrators

**Setup & Configuration**
1. Register new students: `/register` → Choose Upload or Camera
2. Configure alerts: `/settings` → Enable/disable alerts
3. View statistics: `GET /stats` API
4. Manage users: `/history` → Delete option on each user

**Monitoring**
1. Live view: `/` (main dashboard)
2. See behavior trends: `/alerts` page
3. Check attendance: `/history` page
4. Export data: Use browser download on data tables

**Maintenance**
- Retrain model: `POST /train` API
- Reset attendance: `POST /api/reset` API
- Check video: GET `/video`

---

## 📊 Data Flows

### Registration Flow
```
User provides name/roll
         ↓
Choose upload OR camera
         ↓
Submit images to /register (POST)
         ↓
Backend saves to dataset/
         ↓
Auto-trains model
         ↓
Auto-marks attendance
         ↓
User registered ✅
```

### Monitoring Flow
```
Camera captures frame
         ↓
Face detection
         ↓
Face recognition (predict)
         ↓
If known person → Mark attendance
If unknown person → Save image to alerts/
         ↓
Store in CSV files
         ↓
Update real-time statistics
```

### Alert Recording Flow
```
Behavior detected (drowsy/sleep/etc)
         ↓
Create alert object
         ↓
POST /api/behavioral_alerts
         ↓
Store in memory (1000 limit)
         ↓
Apply setting filters (if enabled)
         ↓
Query via GET /api/behavioral_alerts
```

### Settings Flow
```
User updates setting on /settings
         ↓
JavaScript sends POST /api/settings
         ↓
Backend updates system_settings dict
         ↓
Auto-saves to settings.json
         ↓
Loads on app startup with load_settings()
```

---

## 🎨 Page Components

### Dashboard (/)
- Hero section with welcome message
- Live video feed from camera
- Statistics cards (Total, Present, Absent, %)
- Chart showing attendance trends
- Quick action buttons
- System status indicators

### Registration (/register)
- Dual tabs: Upload Images | Camera Capture
- **Upload tab**: Drag-drop area, file previews
- **Camera tab**: Live camera preview, capture button, photo grid
- Form fields: Name, Roll Number
- Progress indicator and success messages

### History (/history)
- Attendance table with columns
- Sort by date/name
- Delete user option
- Export button
- Search/filter capability
- Color-coded attendance status

### Settings (/settings)
- Alert System section with toggles
- Daily Report section (time, recipients)
- Behavioral Analysis section (thresholds)
- Recipient management (add/remove)
- Save button with confirmation

### Behavioral Alerts (/alerts)
- Statistics cards (Total, Drowsiness, Sleep, Yawn)
- Filter controls (Person, Type, Date)
- Data table with pagination
- Click row for details modal
- Responsive design for all screens

---

## 🔑 Important Files

### Configuration
- `settings.json` - System settings (auto-created)
- `students.csv` - Registered student list
- `attendance.csv` - Daily attendance records

### Data & Models
- `dataset/` - Face images for training
- `trainer/trainer.yml` - Face recognition model
- `trainer/labels.txt` - Student ID mappings
- `alerts/unknown_persons/` - Unknown face images

### Frontend
- `static/premium-elite.css` - Main styling
- `static/advanced-features.css` - Alert styling
- `templates/index_premium.html` - Dashboard
- `templates/register_advanced.html` - Registration
- `templates/history_premium.html` - History
- `templates/settings.html` - Settings
- `templates/alerts.html` - Behavioral alerts

### Backend
- `app.py` - Main Flask application
- `main.py` - Alternative entry point

---

## 💾 File Structure
```
Smart_Monitoring_System/
├── app.py                          # Main app with all routes
├── main.py                         # Alternate entry point
├── requirements.txt                # Python dependencies
├── settings.json                   # Settings file (auto-created)
├── students.csv                    # Student records
├── attendance.csv                  # Attendance logs
├── trainer/                        # ML models
│   ├── trainer.yml                # Face recognition model
│   └── labels.txt                 # Student IDs
├── dataset/                        # Face training images
├── alerts/                         # Alert storage
│   └── unknown_persons/           # Unknown faces
├── static/                         # Frontend assets
│   ├── premium-elite.css          # Main styles
│   ├── advanced-features.css      # Alert styles
│   └── style.css                  # Legacy styles
├── templates/                      # HTML pages
│   ├── index_premium.html         # Dashboard
│   ├── register_advanced.html     # Registration (dual-mode)
│   ├── history_premium.html       # History
│   ├── settings.html              # Settings
│   ├── alerts.html                # Behavioral alerts
│   └── ...                        # Other templates
└── kubernetes/                     # K8s deployment config
    └── monitoring-system.yaml
```

---

## ⚡ Quick Commands

### Start Application
```bash
python app.py
# or
python main.py
```

### Manual Model Training
```bash
curl -X POST http://localhost:5000/train
```

### Reset Daily Attendance
```bash
curl -X POST http://localhost:5000/api/reset
```

### Get Current Settings
```bash
curl http://localhost:5000/api/settings
```

### Get Behavioral Statistics
```bash
curl "http://localhost:5000/api/behavioral_stats"
```

### Filter Alerts by Person
```bash
curl "http://localhost:5000/api/behavioral_alerts?person=John"
```

### Delete User
```bash
curl -X POST http://localhost:5000/api/delete-user/johnsmith
```

---

## 🎯 Use Case Scenarios

### Scenario 1: School Attendance System
```
1. Register students at /register
2. Enable alerts in /settings  
3. Monitor students on main dashboard
4. View behavioral patterns in /alerts
5. Check attendance records in /history
6. Export attendance data daily
```

### Scenario 2: Office Monitoring
```
1. Register employees as "students"
2. Configure alert thresholds in /settings
3. Set up email/SMS notifications
4. View real-time dashboard
5. Generate daily behavioral reports
6. Track alertness throughout day
```

### Scenario 3: Test Proctoring
```
1. Register test takers at /register
2. Enable unknown person alerts
3. Monitor during exam
4. Record behavioral anomalies
5. Flag suspicious activity
6. Store evidence (images)
```

---

## 🔧 Troubleshooting

### Camera Not Working
```
1. Check browser camera permissions
2. Ensure no other app uses camera
3. Refresh page and try again
4. Try different browser (Chrome recommended)
```

### Face Recognition Low Accuracy
```
1. Register more images (8-10 minimum)
2. Capture from different angles
3. Ensure good lighting condition
4. Retrain model: POST /train
```

### Settings Not Persisting
```
1. Check settings.json file exists
2. Verify file permissions (readable/writable)
3. Restart application
4. Check browser localStorage
```

### High CPU/Memory Usage
```
1. Reduce video frame size in app.py
2. Close unnecessary browser tabs
3. Clear old alerts (limited to 1000)
4. Enable GPU acceleration if available
```

---

## 📊 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `/` | Opens dashboard |
| `R` | Go to registration |
| `H` | View history |
| `S` | Open settings |
| `A` | View behavioral alerts |
| `Tab` | Navigate form fields |
| `Enter` | Submit form |
| `Esc` | Close modals |

---

## 💡 Pro Tips

1. **Batch Registration**: Use camera mode to register multiple students quickly
2. **Backup Settings**: Manually backup `settings.json` before updates
3. **Model Performance**: Retrain model weekly for best accuracy
4. **Data Export**: Export attendance CSV daily for backup
5. **Filter Alerts**: Use date filters to analyze weekly patterns
6. **Unknown Persons**: Regularly check `alerts/unknown_persons/` for security
7. **Night Mode**: Browser dark mode available for low-light monitoring
8. **Mobile Check**: Test on mobile before deployment

---

## 📞 Support

For detailed documentation, see:
- `ADVANCED_FEATURES_GUIDE.md` - Complete feature reference
- `API_DOCUMENTATION.md` - Detailed API specs
- `DEPLOYMENT_GUIDE_PHASE4.md` - Deployment instructions
- `README.md` - General overview

---

**Last Updated**: 2024  
**Version**: 4.0  
**Status**: Production Ready ⭐

All features are working and ready to use!
