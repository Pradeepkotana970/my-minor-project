"""
Advanced Data Storage and Persistence Layer
Handles: SQLite database, CSV logs, JSON backups, real-time analytics
"""

import sqlite3
import csv
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class AdvancedDataStorage:
    """
    Multi-layer persistent storage:
    - SQLite database for structured data
    - CSV logs for historical records
    - JSON backups for recovery
    - Real-time statistics
    """
    
    def __init__(self, db_path: str = 'monitoring.db'):
        """Initialize storage layer"""
        self.db_path = db_path
        self.csv_attendance_path = 'logs/attendance.csv'
        self.csv_detections_path = 'logs/detections.csv'
        self.csv_behavior_path = 'logs/behavior.csv'
        self.backup_path = 'backups/'
        
        self._ensure_directories()
        self._initialize_database()
        
        logger.info("✅ AdvancedDataStorage initialized")
    
    def _ensure_directories(self):
        """Create required directories"""
        for directory in ['logs', 'backups', 'dataset', 'trainer', 'alerts']:
            os.makedirs(directory, exist_ok=True)
    
    def _initialize_database(self):
        """Initialize SQLite database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Persons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    face_id INTEGER UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    confidence_threshold REAL DEFAULT 70.0,
                    metadata TEXT
                )
            ''')
            
            # Attendance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    face_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence REAL,
                    distance TEXT,
                    status TEXT,
                    behavior_state TEXT,
                    attention_score REAL,
                    metadata TEXT,
                    FOREIGN KEY(person_id) REFERENCES persons(id)
                )
            ''')
            
            # Detections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    frame_number INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    face_count INTEGER,
                    registered_count INTEGER,
                    unknown_count INTEGER,
                    detection_data TEXT,
                    processing_time_ms REAL
                )
            ''')
            
            # Behavior events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS behavior_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    face_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    behavior_state TEXT,
                    attention_score REAL,
                    alert_level TEXT,
                    details TEXT,
                    FOREIGN KEY(person_id) REFERENCES persons(id)
                )
            ''')
            
            # Unknown persons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS unknown_persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    image_path TEXT,
                    detection_confidence REAL,
                    location TEXT,
                    reported BOOLEAN DEFAULT 0
                )
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    alert_type TEXT,
                    severity TEXT,
                    person_id INTEGER,
                    face_id INTEGER,
                    message TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    FOREIGN KEY(person_id) REFERENCES persons(id)
                )
            ''')
            
            # Session logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_end TIMESTAMP,
                    total_frames INTEGER,
                    fps REAL,
                    unique_persons INTEGER,
                    total_detections INTEGER,
                    notes TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_face_id ON attendance(face_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_behavior_timestamp ON behavior_events(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_unknown_timestamp ON unknown_persons(timestamp)')
            
            conn.commit()
            logger.info("✅ Database initialized")
    
    @contextmanager
    def get_connection(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ========== PERSONS MANAGEMENT ==========
    def register_person(self, face_id: int, name: str, email: str = None, 
                       phone: str = None, metadata: Dict = None) -> bool:
        """Register a new person"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO persons (face_id, name, email, phone, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (face_id, name, email, phone, json.dumps(metadata or {})))
                conn.commit()
                logger.info(f"✅ Registered person: {name} (face_id: {face_id})")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"⚠️ Person already registered: {name}")
            return False
        except Exception as e:
            logger.error(f"❌ Error registering person: {e}")
            return False
    
    def get_person(self, face_id: int) -> Optional[Dict]:
        """Get person information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM persons WHERE face_id = ?', (face_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Error getting person: {e}")
            return None
    
    # ========== ATTENDANCE TRACKING ==========
    def record_attendance(self, face_id: int, name: str, confidence: float, 
                         distance: str, behavior_state: str, attention_score: float,
                         metadata: Dict = None) -> bool:
        """Record attendance for a detected person"""
        try:
            person = self.get_person(face_id)
            person_id = person['id'] if person else None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO attendance 
                    (person_id, face_id, name, confidence, distance, status, 
                     behavior_state, attention_score, metadata)
                    VALUES (?, ?, ?, ?, ?, 'present', ?, ?, ?)
                ''', (person_id, face_id, name, confidence, distance, 
                      behavior_state, attention_score, json.dumps(metadata or {})))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error recording attendance: {e}")
            return False
    
    def log_attendance_csv(self, name: str, face_id: int, confidence: float,
                          behavior_state: str, status: str = "Present"):
        """Log attendance to CSV"""
        try:
            file_exists = os.path.exists(self.csv_attendance_path)
            with open(self.csv_attendance_path, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Timestamp', 'Name', 'Face_ID', 'Confidence', 'Behavior', 'Status'])
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    name,
                    face_id,
                    f"{confidence:.2f}%",
                    behavior_state,
                    status
                ])
        except Exception as e:
            logger.error(f"❌ Error logging to CSV: {e}")
    
    # ========== DETECTION LOGGING ==========
    def record_detection(self, frame_number: int, face_count: int, 
                        registered_count: int, detection_data: Dict, 
                        processing_time_ms: float) -> bool:
        """Record frame detection statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO detections 
                    (frame_number, face_count, registered_count, unknown_count, 
                     detection_data, processing_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (frame_number, face_count, registered_count, 
                      face_count - registered_count,
                      json.dumps(detection_data), processing_time_ms))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error recording detection: {e}")
            return False
    
    # ========== BEHAVIOR LOGGING ==========
    def record_behavior_event(self, face_id: int, name: str, behavior_state: str,
                             attention_score: float, alert_level: str, 
                             details: Dict = None) -> bool:
        """Record behavior change event"""
        try:
            person = self.get_person(face_id)
            person_id = person['id'] if person else None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO behavior_events 
                    (person_id, face_id, name, event_type, behavior_state, 
                     attention_score, alert_level, details)
                    VALUES (?, ?, ?, 'state_change', ?, ?, ?, ?)
                ''', (person_id, face_id, name, behavior_state, 
                      attention_score, alert_level, json.dumps(details or {})))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error recording behavior event: {e}")
            return False
    
    def log_behavior_csv(self, name: str, face_id: int, behavior_state: str,
                        attention_score: float, alert_level: str):
        """Log behavior to CSV"""
        try:
            file_exists = os.path.exists(self.csv_behavior_path)
            with open(self.csv_behavior_path, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Timestamp', 'Name', 'Face_ID', 'Behavior', 
                                   'Attention_Score', 'Alert_Level'])
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    name,
                    face_id,
                    behavior_state,
                    f"{attention_score:.1f}%",
                    alert_level
                ])
        except Exception as e:
            logger.error(f"❌ Error logging behavior to CSV: {e}")
    
    # ========== UNKNOWN PERSONS ==========
    def record_unknown_person(self, image_path: str, confidence: float) -> bool:
        """Record unknown person detection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO unknown_persons (image_path, detection_confidence)
                    VALUES (?, ?)
                ''', (image_path, confidence))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error recording unknown person: {e}")
            return False
    
    # ========== ANALYTICS ==========
    def get_daily_attendance(self, date: datetime = None) -> List[Dict]:
        """Get attendance for a specific date"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, face_id, COUNT(*) as check_ins, 
                           AVG(confidence) as avg_confidence,
                           AVG(attention_score) as avg_attention
                    FROM attendance
                    WHERE DATE(timestamp) = ?
                    GROUP BY face_id, name
                    ORDER BY check_ins DESC
                ''', (date_str,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error getting daily attendance: {e}")
            return []
    
    def get_behavior_summary(self, hours: int = 24) -> Dict:
        """Get behavior summary for last N hours"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get behavior events
                cursor.execute('''
                    SELECT behavior_state, COUNT(*) as count,
                           AVG(attention_score) as avg_attention
                    FROM behavior_events
                    WHERE timestamp > datetime('now', '-' || ? || ' hours')
                    GROUP BY behavior_state
                ''', (hours,))
                
                behaviors = {row['behavior_state']: {
                    'count': row['count'],
                    'avg_attention': row['avg_attention']
                } for row in cursor.fetchall()}
                
                # Get alerts
                cursor.execute('''
                    SELECT alert_type, severity, COUNT(*) as count
                    FROM alerts
                    WHERE timestamp > datetime('now', '-' || ? || ' hours')
                    GROUP BY alert_type, severity
                ''', (hours,))
                
                alerts = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'behaviors': behaviors,
                    'alerts': alerts,
                    'period_hours': hours
                }
        except Exception as e:
            logger.error(f"❌ Error getting behavior summary: {e}")
            return {}
    
    def get_statistics(self) -> Dict:
        """Get system-wide statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total registered
                cursor.execute('SELECT COUNT(*) as count FROM persons WHERE status = "active"')
                total_registered = cursor.fetchone()['count']
                
                # Today's attendance
                cursor.execute('''
                    SELECT COUNT(DISTINCT face_id) as count FROM attendance
                    WHERE DATE(timestamp) = DATE('now')
                ''')
                today_attendance = cursor.fetchone()['count']
                
                # Unknown persons detected
                cursor.execute('SELECT COUNT(*) as count FROM unknown_persons')
                unknown_detected = cursor.fetchone()['count']
                
                # Behavior alerts
                cursor.execute('''
                    SELECT COUNT(*) as count FROM alerts
                    WHERE severity = 'critical' AND resolved = 0
                ''')
                critical_alerts = cursor.fetchone()['count']
                
                return {
                    'total_registered': total_registered,
                    'today_attendance': today_attendance,
                    'unknown_persons': unknown_detected,
                    'critical_alerts': critical_alerts
                }
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return {}
    
    # ========== BACKUP ==========
    def backup_database(self) -> bool:
        """Create backup of database"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_path, f'backup_{timestamp}.db')
            
            with self.get_connection() as conn:
                conn.backup(sqlite3.connect(backup_file))
            
            logger.info(f"✅ Database backed up to {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Error backing up database: {e}")
            return False
