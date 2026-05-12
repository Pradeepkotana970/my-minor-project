"""
Enhanced Database Module
Implements comprehensive data storage for attendance, behavior, and alerts
"""

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple
import config

logger = logging.getLogger(__name__)


class EnhancedDatabaseManager:
    """Manages SQLite database with comprehensive schema for monitoring system"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database manager
        
        Args:
            db_path: Path to database file
        """
        self.db_path = db_path or str(config.DATABASE_PATH)
        self.init_database()
        logger.info(f"Database initialized: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database with comprehensive schema"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Users/Persons table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS persons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        external_id INTEGER UNIQUE NOT NULL,
                        name TEXT NOT NULL UNIQUE,
                        roll_number TEXT UNIQUE,
                        email TEXT,
                        phone TEXT,
                        photo_path TEXT,
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1,
                        notes TEXT
                    )
                ''')
                
                # Attendance table with behavior
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        roll_number TEXT,
                        check_in TIMESTAMP NOT NULL,
                        check_out TIMESTAMP,
                        duration_seconds INTEGER,
                        confidence_score REAL,
                        recognition_confidence REAL,
                        initial_behavior TEXT,
                        final_behavior TEXT,
                        distance_estimate TEXT,
                        is_valid INTEGER DEFAULT 1,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (person_id) REFERENCES persons(id)
                    )
                ''')
                
                # Behavior events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS behavior_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        event_timestamp TIMESTAMP NOT NULL,
                        duration_seconds REAL,
                        eye_status TEXT,
                        head_pose TEXT,
                        engagement_level REAL,
                        motion_detected INTEGER,
                        inactivity_duration REAL,
                        confidence REAL,
                        details JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (person_id) REFERENCES persons(id)
                    )
                ''')
                
                # Alerts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_id INTEGER,
                        name TEXT,
                        alert_type TEXT NOT NULL,
                        severity TEXT DEFAULT 'MEDIUM',
                        description TEXT,
                        alert_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        image_path TEXT,
                        behavior_data JSON,
                        acknowledged INTEGER DEFAULT 0,
                        acknowledged_at TIMESTAMP,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (person_id) REFERENCES persons(id)
                    )
                ''')
                
                # Recognition history (for tracking confidence trends)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS recognition_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        raw_confidence REAL,
                        calibrated_confidence REAL,
                        distance_estimate TEXT,
                        frame_number INTEGER,
                        recognition_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (person_id) REFERENCES persons(id)
                    )
                ''')
                
                # Session logs
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS session_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        duration_seconds INTEGER,
                        total_frames_processed INTEGER DEFAULT 0,
                        total_faces_detected INTEGER DEFAULT 0,
                        unique_persons_detected INTEGER DEFAULT 0,
                        total_alerts_triggered INTEGER DEFAULT 0,
                        total_sleeping_events INTEGER DEFAULT 0,
                        total_idle_events INTEGER DEFAULT 0,
                        avg_detection_confidence REAL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Analytics/Statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        statistic_date DATE NOT NULL,
                        person_id INTEGER,
                        metric_type TEXT NOT NULL,
                        metric_name TEXT,
                        metric_value REAL,
                        details JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (person_id) REFERENCES persons(id)
                    )
                ''')
                
                # Create indexes for better query performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_person ON attendance(person_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(check_in)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_behavior_person ON behavior_events(person_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_behavior_type ON behavior_events(event_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_person ON alerts(person_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_recognition_person ON recognition_history(person_id)')
                
                logger.info("Database schema initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    # ========== PERSON MANAGEMENT ==========
    
    def add_person(
        self,
        external_id: int,
        name: str,
        roll_number: str = None,
        email: str = None,
        phone: str = None,
        photo_path: str = None
    ) -> int:
        """
        Add a person to database
        
        Args:
            external_id: External ID (e.g., from recognizer)
            name: Person's name
            roll_number: Roll number
            email: Email address
            phone: Phone number
            photo_path: Path to person's photo
            
        Returns:
            Internal database ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO persons (external_id, name, roll_number, email, phone, photo_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (external_id, name, roll_number, email, phone, photo_path))
                
                person_id = cursor.lastrowid
                logger.info(f"Added person: {name} (ID: {person_id})")
                return person_id
        except sqlite3.IntegrityError:
            logger.warning(f"Person already exists: {name}")
            return self.get_person_by_name(name)
        except Exception as e:
            logger.error(f"Error adding person: {e}")
            return None
    
    def get_person_by_name(self, name: str) -> int:
        """Get person ID by name"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM persons WHERE name = ?', (name,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting person: {e}")
            return None
    
    # ========== ATTENDANCE TRACKING ==========
    
    def mark_checkin(
        self,
        name: str,
        confidence_score: float = 0,
        recognition_confidence: float = 0,
        behavior: str = "Active",
        distance_estimate: str = "medium"
    ) -> int:
        """
        Mark person check-in
        
        Args:
            name: Person's name
            confidence_score: Overall confidence
            recognition_confidence: Face recognition confidence
            behavior: Initial behavior
            distance_estimate: Distance from camera
            
        Returns:
            Attendance record ID
        """
        try:
            person_id = self.get_person_by_name(name)
            if not person_id:
                logger.warning(f"Person not found: {name}")
                return None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO attendance 
                    (person_id, name, roll_number, check_in, confidence_score, 
                     recognition_confidence, initial_behavior, distance_estimate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    person_id,
                    name,
                    None,  # TODO: Get roll from person record
                    datetime.now(),
                    confidence_score,
                    recognition_confidence,
                    behavior,
                    distance_estimate
                ))
                
                record_id = cursor.lastrowid
                logger.info(f"Check-in marked for {name} (Record ID: {record_id})")
                return record_id
        except Exception as e:
            logger.error(f"Error marking check-in: {e}")
            return None
    
    def mark_checkout(self, attendance_id: int, final_behavior: str = "Active"):
        """Mark person check-out"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE attendance
                    SET check_out = ?, final_behavior = ?,
                        duration_seconds = CAST((julianday(check_out) - julianday(check_in)) * 86400 AS INTEGER)
                    WHERE id = ?
                ''', (datetime.now(), final_behavior, attendance_id))
                
                logger.info(f"Check-out marked for attendance ID: {attendance_id}")
        except Exception as e:
            logger.error(f"Error marking check-out: {e}")
    
    # ========== BEHAVIOR LOGGING ==========
    
    def log_behavior_event(
        self,
        name: str,
        event_type: str,
        duration_seconds: float = 0,
        eye_status: str = None,
        head_pose: str = None,
        engagement_level: float = 0,
        motion_detected: bool = False,
        inactivity_duration: float = 0,
        confidence: float = 0,
        details: Dict = None
    ) -> int:
        """
        Log a behavior event
        
        Args:
            name: Person's name
            event_type: Type of event (sleeping, idle, active, etc.)
            duration_seconds: Duration of event
            eye_status: Eye status
            head_pose: Head pose
            engagement_level: Engagement level (0-100)
            motion_detected: Whether motion was detected
            inactivity_duration: Inactivity duration
            confidence: Detection confidence
            details: Additional details as dict
            
        Returns:
            Event record ID
        """
        try:
            person_id = self.get_person_by_name(name)
            if not person_id:
                person_id = self.add_person(-1, name)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO behavior_events
                    (person_id, name, event_type, event_timestamp, duration_seconds,
                     eye_status, head_pose, engagement_level, motion_detected,
                     inactivity_duration, confidence, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    person_id,
                    name,
                    event_type,
                    datetime.now(),
                    duration_seconds,
                    eye_status,
                    head_pose,
                    engagement_level,
                    1 if motion_detected else 0,
                    inactivity_duration,
                    confidence,
                    json.dumps(details or {})
                ))
                
                event_id = cursor.lastrowid
                logger.debug(f"Behavior event logged: {name} - {event_type}")
                return event_id
        except Exception as e:
            logger.error(f"Error logging behavior event: {e}")
            return None
    
    # ========== ALERT LOGGING ==========
    
    def log_alert(
        self,
        name: str,
        alert_type: str,
        severity: str = "MEDIUM",
        description: str = None,
        image_path: str = None,
        behavior_data: Dict = None
    ) -> int:
        """
        Log an alert
        
        Args:
            name: Person's name
            alert_type: Type of alert
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
            description: Alert description
            image_path: Path to alert image
            behavior_data: Associated behavior data
            
        Returns:
            Alert record ID
        """
        try:
            person_id = self.get_person_by_name(name)
            if not person_id:
                person_id = self.add_person(-1, name)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts
                    (person_id, name, alert_type, severity, description, 
                     image_path, behavior_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    person_id,
                    name,
                    alert_type,
                    severity,
                    description,
                    image_path,
                    json.dumps(behavior_data or {})
                ))
                
                alert_id = cursor.lastrowid
                logger.info(f"Alert logged: {name} - {alert_type} ({severity})")
                return alert_id
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
            return None
    
    def acknowledge_alert(self, alert_id: int, notes: str = None):
        """Acknowledge an alert"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE alerts
                    SET acknowledged = 1, acknowledged_at = ?, notes = ?
                    WHERE id = ?
                ''', (datetime.now(), notes, alert_id))
                
                logger.info(f"Alert acknowledged: {alert_id}")
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
    
    # ========== ANALYTICS & REPORTING ==========
    
    def get_attendance_by_date(self, date: str) -> List[Dict]:
        """
        Get attendance for a specific date
        
        Args:
            date: Date string (YYYY-MM-DD)
            
        Returns:
            List of attendance records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM attendance
                    WHERE DATE(check_in) = ?
                    ORDER BY check_in
                ''', (date,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting attendance: {e}")
            return []
    
    def get_person_behavior_summary(self, name: str, days: int = 7) -> Dict:
        """
        Get behavior summary for a person
        
        Args:
            name: Person's name
            days: Number of days to look back
            
        Returns:
            Summary dictionary
        """
        try:
            person_id = self.get_person_by_name(name)
            if not person_id:
                return {}
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT event_type, COUNT(*) as count, AVG(duration_seconds) as avg_duration
                    FROM behavior_events
                    WHERE person_id = ? AND event_timestamp > ?
                    GROUP BY event_type
                ''', (person_id, cutoff_date))
                
                events = {row[0]: {"count": row[1], "avg_duration": row[2]} for row in cursor.fetchall()}
                
                return {
                    "name": name,
                    "period_days": days,
                    "events": events
                }
        except Exception as e:
            logger.error(f"Error getting behavior summary: {e}")
            return {}
    
    def get_unacknowledged_alerts(self, limit: int = 50) -> List[Dict]:
        """Get unacknowledged alerts"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM alerts
                    WHERE acknowledged = 0
                    ORDER BY alert_timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    def export_daily_report(self, date: str) -> Dict:
        """
        Generate daily report
        
        Args:
            date: Date string (YYYY-MM-DD)
            
        Returns:
            Report dictionary
        """
        try:
            attendance = self.get_attendance_by_date(date)
            
            report = {
                "date": date,
                "total_persons": len(set(r["name"] for r in attendance)),
                "total_checkins": len(attendance),
                "attendance_details": attendance
            }
            
            return report
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {}
