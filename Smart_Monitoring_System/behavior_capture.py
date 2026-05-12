"""
Real-time Behavior Capture and Analysis Module
Captures user images from webcam and detects behavior states: Active, Dull, or Sleepy
"""

import cv2
import numpy as np
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime
from collections import deque
import base64
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class BehaviorCaptureAnalyzer:
    """Captures and analyzes real-time behavior from webcam"""
    
    # Behavior states
    ACTIVE = "Active"
    DULL = "Dull"
    DROWSY = "Drowsy"
    SLEEPY = "Sleepy"
    
    def __init__(self):
        """Initialize behavior capture analyzer"""
        self.cap = None
        self.current_frame = None
        self.behavior_history = deque(maxlen=30)  # Last 30 frames
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Behavior tracking
        self.frame_count = 0
        self.eye_blink_count = 0
        self.head_movement = deque(maxlen=10)
        self.last_frame_gray = None
        
        # Detection thresholds
        self.eye_closure_threshold = 0.3  # 30% of time eyes closed = sleepy
        self.motion_threshold = 1.2  # Lowered: very low motion = dull
        self.activity_threshold = 5.0  # Lowered: moderate motion = active
        
        logger.info("BehaviorCaptureAnalyzer initialized")
    
    def initialize_camera(self, camera_id: int = 0) -> bool:
        """
        Initialize camera capture
        
        Args:
            camera_id: Camera device ID (0 = default)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(camera_id)
            if not self.cap.isOpened():
                logger.error("Failed to open camera")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            logger.info("Camera initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture single frame from camera
        
        Returns:
            Frame array or None if capture failed
        """
        if self.cap is None:
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                return frame
            else:
                logger.warning("Failed to capture frame")
                return None
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None
    
    def detect_eyes(self, frame: np.ndarray) -> Tuple[int, bool]:
        """
        Detect eyes in frame and determine if closed
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple of (eyes_detected_count, eyes_likely_closed)
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            eyes_detected = 0
            eyes_closed = False
            
            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
                roi_color = frame[y:y+h, x:x+w]
                
                # Detect eyes in face region
                eyes = self.eye_cascade.detectMultiScale(roi_gray)
                eyes_detected = len(eyes)
                
                # Analyze eye closure based on darkness and size
                if eyes_detected == 0 or eyes_detected < 2:
                    # Eyes not fully visible or closed
                    roi_brightness = np.mean(roi_gray)
                    roi_contrast = np.std(roi_gray)
                    
                    # If dark and low contrast in eye region = likely closed
                    if roi_brightness < 100 and roi_contrast < 50:
                        eyes_closed = True
                else:
                    eyes_closed = False
            
            return eyes_detected, eyes_closed
        
        except Exception as e:
            logger.error(f"Error detecting eyes: {e}")
            return 0, False
    
    def detect_motion(self, frame: np.ndarray) -> float:
        """
        Detect motion/movement in frame
        
        Args:
            frame: Current frame
            
        Returns:
            Motion magnitude (0-100)
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.last_frame_gray is None:
                self.last_frame_gray = gray
                return 0.0
            
            # Calculate optical flow for motion detection
            flow = cv2.calcOpticalFlowFarneback(
                self.last_frame_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            
            # Calculate motion magnitude
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            motion = np.mean(mag)
            
            self.last_frame_gray = gray
            return float(motion)
        
        except Exception as e:
            logger.error(f"Error detecting motion: {e}")
            return 0.0
    
    def analyze_behavior_state(self, frame: np.ndarray) -> Dict:
        """
        Analyze current behavior state: Active, Dull, or Sleepy
        
        Args:
            frame: Input frame from camera
            
        Returns:
            Behavior analysis result
        """
        try:
            self.frame_count += 1
            
            # Detect eyes
            eyes_detected, eyes_closed = self.detect_eyes(frame)
            
            # Detect motion
            motion = self.detect_motion(frame)
            self.head_movement.append(motion)
            
            # Track eye blinks
            if eyes_closed:
                self.eye_blink_count += 1
            
            # Calculate metrics
            avg_motion = np.mean(list(self.head_movement)) if self.head_movement else 0
            eye_closure_ratio = min(self.eye_blink_count / max(self.frame_count, 1), 1.0)
            
            # Determine behavior state
            behavior_state = self._determine_state(
                eyes_detected, eyes_closed, avg_motion, eye_closure_ratio
            )
            
            # Store in history
            self.behavior_history.append(behavior_state)
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                eyes_detected, eyes_closed, avg_motion, eye_closure_ratio
            )
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "behavior": behavior_state,
                "confidence": confidence,
                "eyes_detected": eyes_detected,
                "eyes_closed": eyes_closed,
                "motion": float(avg_motion),
                "eye_closure_ratio": float(eye_closure_ratio),
                "frame_count": self.frame_count,
                "details": {
                    "current_motion": float(motion),
                    "avg_motion": float(avg_motion),
                    "motion_trend": "increasing" if len(self.head_movement) >= 2 and self.head_movement[-1] > self.head_movement[-2] else "decreasing"
                }
            }
            
            logger.info(f"Behavior detected: {behavior_state} (confidence: {confidence:.2f}%)")
            return result
        
        except Exception as e:
            logger.error(f"Error analyzing behavior: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "behavior": "Unknown",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _determine_state(
        self,
        eyes_detected: int,
        eyes_closed: bool,
        avg_motion: float,
        eye_closure_ratio: float
    ) -> str:
        """
        Determine behavior state based on metrics
        
        Args:
            eyes_detected: Number of eyes detected
            eyes_closed: Whether eyes are likely closed
            avg_motion: Average motion magnitude
            eye_closure_ratio: Ratio of frames with closed eyes
            
        Returns:
            Behavior state string
        """
        # SLEEPY: Eyes closed for long time
        if eyes_closed and eye_closure_ratio > 0.5:
            return self.SLEEPY
        
        # DROWSY: Eyes closed frequently but not permanently, or moderate closure ratio
        if eyes_closed or eye_closure_ratio > self.eye_closure_threshold:
            if avg_motion < self.motion_threshold:
                return self.SLEEPY
            else:
                return self.DROWSY
        
        # ACTIVE: Moderate to high motion
        if avg_motion > self.activity_threshold:
            return self.ACTIVE
        
        # DULL: Only if motion is extremely low and no significant activity
        if avg_motion < self.motion_threshold:
            # If eyes are wide open, maybe still ACTIVE (studying/reading)
            if eyes_detected >= 2 and not eyes_closed:
                return self.ACTIVE
            return self.DULL
        
        # Default to Active
        return self.ACTIVE
    
    def _calculate_confidence(
        self,
        eyes_detected: int,
        eyes_closed: bool,
        avg_motion: float,
        eye_closure_ratio: float
    ) -> float:
        """
        Calculate confidence score for behavior detection
        
        Args:
            eyes_detected: Number of eyes detected
            eyes_closed: Whether eyes are likely closed
            avg_motion: Average motion magnitude
            eye_closure_ratio: Ratio of frames with closed eyes
            
        Returns:
            Confidence score (0-100)
        """
        confidence = 50.0  # Base confidence
        
        # Eye detection improves confidence
        if eyes_detected >= 2:
            confidence += 20
        elif eyes_detected == 1:
            confidence += 10
        
        # Clear eye state improves confidence
        if eyes_closed or eye_closure_ratio > self.eye_closure_threshold:
            confidence += 15
        
        # Motion consistency improves confidence
        if len(self.head_movement) >= 10:
            motion_variance = np.std(list(self.head_movement))
            if motion_variance < 5:
                confidence += 15
        
        return min(confidence, 100.0)
    
    def get_frame_base64(self) -> Optional[str]:
        """
        Get current frame as base64 string
        
        Returns:
            Base64 encoded frame or None
        """
        if self.current_frame is None:
            return None
        
        try:
            _, buffer = cv2.imencode('.jpg', self.current_frame)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            return frame_b64
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    def get_behavior_summary(self) -> Dict:
        """
        Get summary of behavior over recent frames
        
        Returns:
            Behavior summary dictionary
        """
        if not self.behavior_history:
            return {"status": "No data"}
        
        # Count states
        states = {}
        for state in self.behavior_history:
            states[state] = states.get(state, 0) + 1
        
        # Determine dominant state
        dominant_state = max(states, key=states.get)
        
        return {
            "dominant_state": dominant_state,
            "frame_count": len(self.behavior_history),
            "state_distribution": states,
            "percentage": {
                state: (count / len(self.behavior_history) * 100)
                for state, count in states.items()
            }
        }
    
    def release_camera(self):
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
            logger.info("Camera released")
    
    def __del__(self):
        """Cleanup on object deletion"""
        self.release_camera()


class BehaviorReportGenerator:
    """Generate behavior analysis reports"""
    
    @staticmethod
    def generate_report(behavior_data: list) -> Dict:
        """
        Generate comprehensive behavior report
        
        Args:
            behavior_data: List of behavior analysis results
            
        Returns:
            Comprehensive report dictionary
        """
        if not behavior_data:
            return {"error": "No behavior data provided"}
        
        # Initialize counters
        state_counts = {"Active": 0, "Dull": 0, "Drowsy": 0, "Sleepy": 0}
        total_frames = len(behavior_data)
        
        for data in behavior_data:
            behavior = data.get("behavior", "Unknown")
            if behavior in state_counts:
                state_counts[behavior] += 1
        
        # Calculate percentages
        percentages = {
            state: (count / total_frames * 100) if total_frames > 0 else 0
            for state, count in state_counts.items()
        }
        
        # Calculate averages
        avg_motion = np.mean([d.get("motion", 0) for d in behavior_data])
        avg_eye_closure = np.mean([d.get("eye_closure_ratio", 0) for d in behavior_data])
        
        return {
            "summary": {
                "total_frames_analyzed": total_frames,
                "active_percentage": percentages["Active"],
                "dull_percentage": percentages["Dull"],
                "drowsy_percentage": percentages["Drowsy"],
                "sleepy_percentage": percentages["Sleepy"],
                "average_motion": float(avg_motion),
                "average_eye_closure_ratio": float(avg_eye_closure)
            },
            "state_counts": state_counts,
            "health_status": BehaviorReportGenerator._determine_health_status(percentages),
            "recommendations": BehaviorReportGenerator._generate_recommendations(percentages, avg_eye_closure),
            "drawbacks": BehaviorReportGenerator._generate_drawbacks(percentages, avg_eye_closure)
        }
    
    @staticmethod
    def _determine_health_status(percentages: Dict) -> str:
        """Determine overall health/alertness status"""
        if percentages["Active"] > 70:
            return "Excellent - High engagement levels"
        elif percentages["Active"] > 50:
            return "Good - Normal activity levels"
        elif percentages["Drowsy"] > 20 or percentages["Sleepy"] > 10:
            return "Warning - High fatigue detected"
        elif percentages["Dull"] > 50:
            return "Needs Attention - Low engagement levels"
        else:
            return "Fair - Fluctuating activity"
    
    @staticmethod
    def _generate_recommendations(percentages: Dict, eye_closure: float) -> list:
        """Generate personalized improvement recommendations"""
        recommendations = []
        
        if percentages["Sleepy"] > 15 or percentages["Drowsy"] > 25:
            recommendations.append("Priority: Take a 15-minute power nap or break.")
            recommendations.append("Hydration: Drink a glass of cold water to boost alertness.")
            recommendations.append("Environment: Increase room brightness or improve ventilation.")
        
        if percentages["Dull"] > 40:
            recommendations.append("Engagement: Try to incorporate more interactive tasks.")
            recommendations.append("Movement: Stand up and stretch for 2 minutes every hour.")
            recommendations.append("Posture: Ensure your seating position is ergonomic.")
        
        if eye_closure > 0.4:
            recommendations.append("Eye Care: Follow the 20-20-20 rule (look 20 feet away for 20 seconds every 20 minutes).")
        
        if not recommendations:
            recommendations.append("Keep it up! Your activity levels are healthy.")
            recommendations.append("Maintain consistency in your current workflow.")
        
        return recommendations

    @staticmethod
    def _generate_drawbacks(percentages: Dict, eye_closure: float) -> list:
        """Identify drawbacks in the user's behavioral patterns"""
        drawbacks = []
        
        if percentages["Sleepy"] > 10:
            drawbacks.append("Critical Fatigue: Frequent periods of micro-sleep detected.")
        
        if percentages["Drowsy"] > 20:
            drawbacks.append("High Drowsiness: Frequent eye blinking indicates struggling to stay awake.")
        
        if percentages["Dull"] > 50:
            drawbacks.append("Sedentary Behavior: Extremely low physical movement for extended periods.")
        
        if eye_closure > 0.6:
            drawbacks.append("Eye Strain: Excessive eye closure ratio suggesting ocular fatigue.")
            
        if percentages["Active"] < 30:
            drawbacks.append("Low Productivity: Minimal 'Active' state recorded during the session.")
            
        if not drawbacks:
            drawbacks.append("No significant behavioral drawbacks detected.")
            
        return drawbacks
