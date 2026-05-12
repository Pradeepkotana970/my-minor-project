"""
Enhanced Smart Monitoring System - Main Application
Integrates advanced detection, recognition, behavior analysis, and alerts
"""

import logging
import os
import sys
import time
import cv2
import json
import csv
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules (ensure all modules are in same directory)
try:
    from detection import FaceDetector, EyeDetector
    from recognition import FaceRecognizer, MultiPersonTracker
    from behavior import BehaviorAnalyzer, PostureAnalyzer, EngagementAnalyzer
    from alerts import AlertManager, SoundAlertPlayer, VoiceAlertGenerator, NotificationLogger
    import config
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    sys.exit(1)


class SmartMonitoringSystem:
    """Main application class for enhanced monitoring system"""
    
    def __init__(self):
        """Initialize the monitoring system"""
        logger.info("=" * 60)
        logger.info("Initializing Smart Monitoring System v2.0")
        logger.info("=" * 60)
        
        # Initialize components
        self.face_detector = FaceDetector()
        self.eye_detector = EyeDetector()
        self.face_recognizer = FaceRecognizer()
        self.tracker = MultiPersonTracker(max_missing_frames=config.MAX_MISSING_FRAMES)
        self.behavior_analyzer = BehaviorAnalyzer(
            sleep_threshold_seconds=config.SLEEP_THRESHOLD,
            idle_threshold_seconds=config.IDLE_THRESHOLD
        )
        self.posture_analyzer = PostureAnalyzer()
        self.engagement_analyzer = EngagementAnalyzer()
        
        # Alert system
        self.alert_manager = AlertManager(
            alert_cooldown_seconds=config.ALERT_COOLDOWN_SECONDS,
            enable_sound=config.ENABLE_SOUND_ALERTS,
            enable_voice=config.ENABLE_VOICE_ALERTS,
            enable_sms=config.SMS_ENABLED,
            enable_email=config.EMAIL_ENABLED
        )
        
        # Setup alert callbacks
        self.sound_player = SoundAlertPlayer(config.ALERT_SOUND_FILE)
        self.alert_manager.set_sound_callback(self.sound_player.play_alert)
        
        if config.ENABLE_VOICE_ALERTS:
            self.voice_generator = VoiceAlertGenerator()
            self.alert_manager.set_voice_callback(self.voice_generator.speak_alert)
        
        self.notification_logger = NotificationLogger()
        
        # Camera and frame management
        self.camera = None
        self.current_frame = None
        self.prev_frame = None
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.fps = 0
        
        # Data storage
        self.session_data = {
            "start_time": datetime.now(),
            "frames_processed": 0,
            "total_faces_detected": 0,
            "unique_persons": set(),
            "attendance_records": []
        }
        
        # File paths
        self.attendance_file = Path(config.ATTENDANCE_FILE)
        
        # Load student data
        self.students = self._load_students()
        self.recognizer_labels = self._load_recognizer_labels()
        
        logger.info("Smart Monitoring System initialized successfully")
    
    def _load_students(self) -> Dict[str, str]:
        """Load student database"""
        students = {}
        if os.path.exists('students.csv'):
            try:
                with open('students.csv') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        students[row['Name']] = row['Roll']
                logger.info(f"Loaded {len(students)} students")
            except Exception as e:
                logger.error(f"Error loading students: {e}")
        return students
    
    def _load_recognizer_labels(self) -> Dict[int, str]:
        """Load recognizer ID to name mapping"""
        labels = {}
        self.face_recognizer.load_labels()
        return self.face_recognizer.id_to_name
    
    def initialize_camera(self, camera_id: int = 0) -> bool:
        """
        Initialize camera with error handling
        
        Args:
            camera_id: Camera device ID
            
        Returns:
            True if successful
        """
        try:
            self.camera = cv2.VideoCapture(camera_id)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Test camera
            ret, frame = self.camera.read()
            if ret and frame is not None:
                logger.info("✅ Camera initialized successfully")
                return True
            else:
                logger.error("❌ Camera test failed")
                return False
        except Exception as e:
            logger.error(f"❌ Error initializing camera: {e}")
            return False
    
    def release_camera(self):
        """Release camera resources"""
        if self.camera:
            self.camera.release()
            logger.info("Camera released")
    
    def process_frame(self) -> Optional[np.ndarray]:
        """
        Capture and process a single frame
        
        Returns:
            Processed frame or None
        """
        try:
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logger.warning("Failed to read frame from camera")
                return None
            
            self.frame_count += 1
            self.session_data["frames_processed"] += 1
            
            # Process frame
            frame = cv2.resize(frame, (1280, 720))
            
            # Detect faces
            detected_faces = self.face_detector.detect_with_adaptive_mode(frame)
            
            if len(detected_faces) > 0:
                self.session_data["total_faces_detected"] += len(detected_faces)
                logger.debug(f"Detected {len(detected_faces)} faces")
            
            # Process each detected face
            recognition_results = []
            behavior_results = []
            
            for face in detected_faces:
                # Extract face ROI
                face_roi = self.face_detector.get_face_roi(frame, face)
                
                if face_roi is None:
                    recognition_results.append({"status": "error"})
                    continue
                
                # Recognize face
                recog_result = self.face_recognizer.recognize_face(
                    face_roi,
                    distance_estimate=face["distance"]
                )
                recognition_results.append(recog_result)
                
                # Analyze behavior
                eye_status = self.eye_detector.estimate_eye_closure(face_roi)
                
                behavior_result = self.behavior_analyzer.analyze_behavior(
                    track_id=0,  # Will be updated by tracker
                    eye_status=eye_status,
                    face_roi=face_roi,
                    prev_face_roi=self.prev_frame[face["y"]:face["y"]+face["h"], 
                                                   face["x"]:face["x"]+face["w"]] if self.prev_frame is not None else None
                )
                behavior_results.append(behavior_result)
            
            # Update tracks
            tracked_persons = self.tracker.update_tracks(detected_faces, recognition_results)
            
            # Draw results on frame
            frame = self._draw_results(frame, detected_faces, recognition_results, behavior_results)
            
            # Update previous frame
            self.prev_frame = cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
            
            # Calculate and display FPS
            self._update_fps()
            self._draw_fps(frame)
            
            return frame
        
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return None
    
    def _draw_results(
        self,
        frame: np.ndarray,
        detected_faces: List[Dict],
        recognition_results: List[Dict],
        behavior_results: List[Dict]
    ) -> np.ndarray:
        """
        Draw detection and analysis results on frame
        
        Args:
            frame: Frame to draw on
            detected_faces: Detected faces
            recognition_results: Recognition results
            behavior_results: Behavior analysis results
            
        Returns:
            Annotated frame
        """
        try:
            for i, face in enumerate(detected_faces):
                x, y, w, h = face["x"], face["y"], face["w"], face["h"]
                
                # Get recognition result
                recog = recognition_results[i] if i < len(recognition_results) else {}
                behavior = behavior_results[i] if i < len(behavior_results) else {}
                
                # Determine color based on recognition status
                if recog.get("status") == "recognized":
                    color = (0, 255, 0)  # Green
                    person_name = recog.get("name", "Unknown")
                else:
                    color = (0, 0, 255)  # Red
                    person_name = "Unknown"
                
                # Draw face box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw name and confidence
                confidence = recog.get("calibrated_confidence", 0)
                label = f"{person_name} ({confidence:.1f}%)"
                cv2.putText(frame, label, (x, y - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Draw behavior
                behavior_text = behavior.get("behavior", "Unknown")
                color_behavior = (0, 255, 0) if behavior_text == "Active" else (0, 165, 255) if behavior_text == "Idle" else (0, 0, 255)
                cv2.putText(frame, behavior_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_behavior, 2)
                
                # Trigger alerts if needed
                if config.ENABLE_ALERTS:
                    if behavior_text == "Sleeping" and config.ALERT_ON_IDLE:
                        self.alert_manager.trigger_alert(
                            person_name=person_name,
                            alert_type="sleep",
                            behavior_data=behavior
                        )
                        self.notification_logger.log_alert(person_name, "sleep", behavior_data=behavior)
                    
                    elif behavior_text == "Idle" and config.ALERT_ON_IDLE:
                        self.alert_manager.trigger_alert(
                            person_name=person_name,
                            alert_type="idle",
                            behavior_data=behavior
                        )
                        self.notification_logger.log_alert(person_name, "idle", behavior_data=behavior)
            
            return frame
        
        except Exception as e:
            logger.error(f"Error drawing results: {e}")
            return frame
    
    def _update_fps(self):
        """Update FPS calculation"""
        if self.frame_count % 30 == 0:
            elapsed = time.time() - self.fps_start_time
            self.fps = 30 / elapsed if elapsed > 0 else 0
            self.fps_start_time = time.time()
    
    def _draw_fps(self, frame: np.ndarray):
        """Draw FPS on frame"""
        fps_text = f"FPS: {self.fps:.1f}"
        cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    def run_video_loop(self):
        """Run the main video processing loop"""
        logger.info("Starting video processing loop...")
        
        if not self.initialize_camera():
            logger.error("Failed to initialize camera")
            return False
        
        try:
            while True:
                # Process frame
                frame = self.process_frame()
                
                if frame is None:
                    continue
                
                # Display frame
                cv2.imshow('Smart Monitoring System', frame)
                
                # Check for exit key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Exiting video loop...")
                    break
            
            return True
        
        except Exception as e:
            logger.error(f"Error in video loop: {e}")
            return False
        
        finally:
            self.release_camera()
            cv2.destroyAllWindows()
            self._print_session_summary()
    
    def _print_session_summary(self):
        """Print session summary"""
        logger.info("=" * 60)
        logger.info("Session Summary")
        logger.info("=" * 60)
        logger.info(f"Frames Processed: {self.session_data['frames_processed']}")
        logger.info(f"Total Faces Detected: {self.session_data['total_faces_detected']}")
        logger.info(f"Unique Persons: {len(self.session_data['unique_persons'])}")
        logger.info(f"Session Duration: {datetime.now() - self.session_data['start_time']}")
        logger.info("=" * 60)
    
    def shutdown(self):
        """Shutdown system"""
        logger.info("Shutting down Smart Monitoring System...")
        self.release_camera()
        self.alert_manager.shutdown()
        cv2.destroyAllWindows()
        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    system = SmartMonitoringSystem()
    
    try:
        system.run_video_loop()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        system.shutdown()


if __name__ == "__main__":
    main()
