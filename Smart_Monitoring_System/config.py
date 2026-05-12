"""
Configuration file for Smart Monitoring System
Centralized settings for the entire application
"""

import os
from pathlib import Path

# ========== PATHS ==========
BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / 'dataset'
TRAINER_DIR = BASE_DIR / 'trainer'
ALERTS_DIR = BASE_DIR / 'alerts'
LOGS_DIR = BASE_DIR / 'logs'
DATABASE_PATH = BASE_DIR / 'monitoring.db'

# Create directories
for directory in [DATASET_DIR, TRAINER_DIR, ALERTS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# ========== CAMERA SETTINGS ==========
CAMERA_ID = 0  # Primary camera (0), fallback to 1
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30
CAMERA_RETRY_ATTEMPTS = 3

# ========== FACE RECOGNITION ==========
CONFIDENCE_THRESHOLD = 70  # Lower = stricter (0-100)
MIN_FACE_SIZE = (30, 30)
FACE_DETECTION_SCALE_FACTOR = 1.1  # Accuracy: 1.05-1.2 range
FACE_DETECTION_MIN_NEIGHBORS = 5  # More = stricter (3-10 range)
RECOGNITION_CONFIDENCE_CALIBRATION = True  # Use distance-based calibration

# ========== BEHAVIOR DETECTION ==========
MOTION_THRESHOLD = 1000
IDLE_THRESHOLD = 3  # seconds
SLEEP_THRESHOLD = 3.0  # seconds of eye closure before marking as sleeping
MULTIPLE_FACE_DETECTION = True  # Enable multi-face detection per frame
MAX_MISSING_FRAMES = 10  # Frames before stopping a track
MOTION_QUEUE_SIZE = 10  # Frames to track for motion detection

# ========== ATTENDANCE ==========
AUTO_MARK_ATTENDANCE = True
DUPLICATE_ATTENDANCE_HOURS = 24  # Prevent double marking within 24 hours
ATTENDANCE_FILE = BASE_DIR / 'attendance.csv'

# ========== LIVENESS DETECTION ==========
ENABLE_LIVENESS_CHECK = True
LIVENESS_THRESHOLD = 0.6  # Confidence score for liveness (0-1)
REQUIRED_MOTION_FRAMES = 5  # Frames to confirm liveness

# ========== ALERTS & NOTIFICATIONS ==========
ENABLE_ALERTS = True
ALERT_ON_IDLE = True
ALERT_ON_UNKNOWN = False
ALERT_ON_SUSPICIOUS = True
ALERT_COOLDOWN_SECONDS = 5  # Minimum seconds between alerts for same person
ALERT_SOUND_FILE = 'alert.wav'

# Sound alerts
ENABLE_SOUND_ALERTS = True
ENABLE_VOICE_ALERTS = False  # Enable text-to-speech alerts

# Email settings (configure as needed)
EMAIL_ENABLED = False
EMAIL_FROM = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"
ALERT_EMAIL_TO = ["admin@yourschool.com"]

# SMS settings (integrate with Twilio)
SMS_ENABLED = False
SMS_ACCOUNT_SID = "your-twilio-sid"
SMS_AUTH_TOKEN = "your-twilio-token"
SMS_FROM_NUMBER = "+1234567890"
SMS_TO_NUMBERS = ["+9876543210"]

# Firebase Cloud Messaging (for mobile push notifications)
FCM_ENABLED = False
FCM_SERVER_KEY = "your-firebase-server-key"

# ========== LOGGING ==========
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / 'system.log'
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_FILE_BACKUP_COUNT = 5

# ========== DATABASE ==========
DATABASE_POOL_SIZE = 5
DATABASE_TIMEOUT = 30

# ========== API SETTINGS ==========
API_HOST = '127.0.0.1'
API_PORT = 5000
DEBUG_MODE = True
SECRET_KEY = 'smart-monitoring-system-secret-key-change-in-production'

# ========== FRONTEND ==========
ITEMS_PER_PAGE = 20
TIMEZONE = 'UTC'
THEME_DARK = True

# ========== MODEL TRAINING ==========
TRAINING_TEST_SIZE = 0.2
TRAINING_RANDOM_STATE = 42
AUGMENTATION_ENABLED = True
AUGMENTATION_FACTOR = 3  # Create 3x more images per original

# ========== SECURITY ==========
MAX_LOGIN_ATTEMPTS = 5
SESSION_TIMEOUT = 3600  # 1 hour
PASSWORD_MIN_LENGTH = 8
REQUIRE_STRONG_PASSWORD = True

# ========== ADVANCED FEATURES ==========
ENABLE_DUPLICATE_DETECTION = True
ENABLE_FACE_MASK_DETECTION = False  # Set to True if mask detection model is available
ENABLE_EXPRESSION_DETECTION = False  # Detect emotions/expressions
ENABLE_AGE_GENDER_DETECTION = False  # Detect age and gender
ENABLE_MULTI_CAMERA_SUPPORT = False  # Support multiple cameras
ENABLE_CLOUD_BACKUP = False  # Backup to cloud storage

# ========== PERFORMANCE ==========
ENABLE_GPU = False  # Use GPU acceleration if available
FRAME_SKIP = 1  # Process every nth frame (1 = process every frame)
MAX_CONCURRENT_RECOGNITIONS = 4

print("Configuration loaded successfully!")
