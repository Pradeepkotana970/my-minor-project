#!/usr/bin/env python3
"""
Smart Monitoring System - FCAE Enhancement Setup Script
Deploys all fixes and enhancements
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_status(status, message):
    """Print status message"""
    symbols = {
        "success": "✅",
        "error": "❌",
        "info": "ℹ️",
        "warning": "⚠️"
    }
    print(f"{symbols.get(status, '•')} {message}")

def backup_existing_files():
    """Backup existing files before making changes"""
    print_header("Creating Backups")
    
    files_to_backup = [
        'recognition.py',
        'detection.py',
        'behavior.py',
        'app.py',
        'config.py',
        'attendance.csv',
        'students.csv'
    ]
    
    backup_dir = f"backups/pre_enhancement_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    for file in files_to_backup:
        if os.path.exists(file):
            try:
                shutil.copy2(file, os.path.join(backup_dir, file))
                print_status("success", f"Backed up: {file}")
            except Exception as e:
                print_status("error", f"Failed to backup {file}: {e}")
    
    print_status("success", f"Backups saved to: {backup_dir}")
    return backup_dir

def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow',
        'mediapipe': 'mediapipe',
        'flask': 'Flask'
    }
    
    missing = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            print_status("success", f"{package} ✓")
        except ImportError:
            print_status("error", f"{package} ✗")
            missing.append(package)
    
    if missing:
        print_status("warning", f"Missing packages: {', '.join(missing)}")
        print("\nInstall missing packages with:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print_status("success", "All dependencies installed")
    return True

def create_directories():
    """Create required directories"""
    print_header("Creating Directories")
    
    directories = [
        'logs',
        'backups',
        'dataset',
        'trainer',
        'alerts',
        'alerts/unknown_persons'
    ]
    
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print_status("success", f"Created/verified: {dir_path}/")

def initialize_database():
    """Initialize database"""
    print_header("Initializing Database")
    
    try:
        from data_storage_enhanced import AdvancedDataStorage
        storage = AdvancedDataStorage()
        print_status("success", "Database initialized successfully")
        return True
    except Exception as e:
        print_status("error", f"Database initialization failed: {e}")
        return False

def validate_registration_module():
    """Validate recognition module"""
    print_header("Validating Recognition Module")
    
    try:
        from face_recognition_enhanced import EnhancedFaceRecognizer
        recognizer = EnhancedFaceRecognizer()
        print_status("success", "EnhancedFaceRecognizer loaded")
        
        from face_detection_enhanced import MultiScaleFaceDetector
        detector = MultiScaleFaceDetector()
        print_status("success", "MultiScaleFaceDetector loaded")
        
        from behavior_analysis_enhanced import AdvancedBehaviorAnalyzer
        analyzer = AdvancedBehaviorAnalyzer()
        print_status("success", "AdvancedBehaviorAnalyzer loaded")
        
        return True
    except Exception as e:
        print_status("error", f"Module validation failed: {e}")
        return False

def test_model_training():
    """Test model training capability"""
    print_header("Testing Model Training")
    
    dataset_path = 'dataset'
    
    # Check if dataset has images
    if os.path.exists(dataset_path):
        image_files = [f for f in os.listdir(dataset_path) 
                      if f.endswith(('.jpg', '.png', '.jpeg'))]
        print_status("info", f"Found {len(image_files)} training images")
        
        if len(image_files) > 0:
            print_status("success", "Dataset ready for training")
            return True
        else:
            print_status("warning", "No training images found")
            print("  → Register users first via /register endpoint")
            return True
    else:
        print_status("warning", "Dataset directory not found")
        print("  → Will be created on first registration")
        return True

def create_config_updates():
    """Create configuration updates file"""
    print_header("Creating Configuration Updates")
    
    config_updates = """
# Add these to config.py for enhanced recognition:

# Distance-based confidence thresholds
CONFIDENCE_NEAR = 75        # Close faces
CONFIDENCE_MEDIUM = 65      # Medium distance
CONFIDENCE_FAR = 55         # Far faces
CONFIDENCE_EXTRA_FAR = 45   # Very far faces

# Behavior analysis thresholds
DROWSINESS_THRESHOLD_SEC = 2.0
SLEEP_THRESHOLD_SEC = 4.0
IDLE_THRESHOLD_SEC = 5.0
MOTION_THRESHOLD_PIXELS = 50

# Data storage
DATABASE_PATH = 'monitoring.db'
CSV_LOGS_DIR = 'logs/'
BACKUP_DIR = 'backups/'
"""
    
    with open('CONFIG_UPDATES.txt', 'w') as f:
        f.write(config_updates)
    
    print_status("success", "Created CONFIG_UPDATES.txt")

def print_next_steps():
    """Print next steps"""
    print_header("Next Steps")
    
    print("""
1. Update your app.py with the new module imports:
   - from face_recognition_enhanced import EnhancedFaceRecognizer
   - from face_detection_enhanced import MultiScaleFaceDetector
   - from behavior_analysis_enhanced import AdvancedBehaviorAnalyzer
   - from data_storage_enhanced import AdvancedDataStorage

2. Replace registration and frame processing functions using the guide:
   → FCAE_FIX_AND_ENHANCEMENTS.md

3. Add configuration constants to config.py:
   → See CONFIG_UPDATES.txt

4. Test the system:
   → python app.py
   → Navigate to http://localhost:5000/register

5. Monitor logs:
   → logs/attendance.csv
   → logs/behavior.csv
   → logs/detections.csv

📚 Documentation:
   ✓ FCAE_FIX_AND_ENHANCEMENTS.md - Complete integration guide
   ✓ API_DOCUMENTATION.md - API endpoints
   ✓ TROUBLESHOOTING_FAQS.md - Common issues
""")

def main():
    """Main setup function"""
    print_header("Smart Monitoring System - Enhancement Setup")
    print("This script prepares your system for FCAE enhancements\n")
    
    # Run setup steps
    backup_dir = backup_existing_files()
    
    if not check_dependencies():
        print_status("warning", "Please install missing dependencies first")
        return False
    
    create_directories()
    
    if not initialize_database():
        print_status("warning", "Database initialization failed, continuing...")
    
    if not validate_registration_module():
        print_status("error", "Module validation failed!")
        print_status("info", f"Check backups in: {backup_dir}")
        return False
    
    test_model_training()
    create_config_updates()
    
    print_header("Setup Complete! ✅")
    
    print_next_steps()
    
    print_status("success", f"Backups saved to: {backup_dir}")
    print("\n" + "="*60)
    print("  You can now start the application with:")
    print("  python app.py")
    print("="*60 + "\n")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print_status("error", f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
