"""
Advanced Behavioral Analysis Module
Real-time behavior detection with 100% accuracy targeting
Includes: Active/Idle/Sleeping detection, Attention tracking, Anomaly detection
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from collections import deque
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class BehaviorState(Enum):
    """Behavior state enumeration"""
    ACTIVE = "Active"
    IDLE = "Idle"
    DROWSY = "Drowsy"
    SLEEPING = "Sleeping"
    LOOKING_AWAY = "Looking Away"
    DISTRACTED = "Distracted"


class AdvancedBehaviorAnalyzer:
    """
    Multi-method behavior analyzer:
    - Eye state tracking (open/closed)
    - Head pose estimation
    - Motion analysis
    - Face direction tracking
    - Attention level scoring
    """
    
    def __init__(self, window_size: int = 10):
        """
        Initialize behavior analyzer
        
        Args:
            window_size: Size of history window for stable decisions
        """
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # History tracking for state transitions
        self.behavior_history = deque(maxlen=window_size)
        self.eye_closure_start = None
        self.idle_start = None
        self.looking_away_start = None
        
        # Thresholds
        self.drowsiness_threshold = 2.0  # Seconds of eye closure
        self.sleep_threshold = 4.0       # Seconds of eye closure
        self.idle_threshold = 5.0        # Seconds of no motion
        self.looking_away_threshold = 3.0  # Seconds of not facing camera
        
        # Motion tracking
        self.prev_gray = None
        self.motion_history = deque(maxlen=30)
        self.motion_threshold = 50  # Pixel movement threshold
        
        # Face direction tracking
        self.face_center_history = deque(maxlen=20)
        
        logger.info("✅ AdvancedBehaviorAnalyzer initialized")
    
    def analyze_behavior(self, frame: np.ndarray, face_roi: np.ndarray, 
                        face_bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Comprehensive behavior analysis
        
        Args:
            frame: Full frame (for motion tracking)
            face_roi: Face region of interest
            face_bbox: (x1, y1, x2, y2) of face in frame
            
        Returns:
            Dict with behavior_state, confidence, details
        """
        analysis = {
            "state": BehaviorState.ACTIVE.value,
            "confidence": 0.0,
            "details": {},
            "attention_score": 100.0,  # 0-100%
            "alert_level": "normal",   # normal, caution, critical
            "flags": []
        }
        
        try:
            # 1. Eye state analysis
            eye_analysis = self._analyze_eyes(face_roi)
            analysis["details"]["eye_state"] = eye_analysis
            
            # 2. Head pose analysis
            pose_analysis = self._analyze_head_pose(face_roi, face_bbox)
            analysis["details"]["head_pose"] = pose_analysis
            
            # 3. Motion analysis
            motion_analysis = self._analyze_motion(frame, face_bbox)
            analysis["details"]["motion"] = motion_analysis
            
            # 4. Integrate analysis results
            final_state = self._integrate_analysis(eye_analysis, pose_analysis, motion_analysis)
            analysis["state"] = final_state.value
            
            # 5. Calculate attention score
            attention_score = self._calculate_attention_score(
                eye_analysis, pose_analysis, motion_analysis
            )
            analysis["attention_score"] = attention_score
            
            # 6. Determine alert level
            analysis["alert_level"] = self._determine_alert_level(final_state, attention_score)
            
            # 7. Collect flags
            analysis["flags"] = self._collect_flags(eye_analysis, pose_analysis, motion_analysis)
            
            # Add to history
            self.behavior_history.append(final_state)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Behavior analysis error: {e}")
            analysis["flags"].append(f"Analysis error: {str(e)}")
            return analysis
    
    def _analyze_eyes(self, face_roi: np.ndarray) -> Dict:
        """Analyze eye state"""
        analysis = {
            "eyes_detected": 0,
            "is_open": False,
            "closure_percentage": 0.0,
            "state": "unknown"
        }
        
        try:
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
            
            # Detect eyes
            eyes = self.eye_cascade.detectMultiScale(
                gray_face,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(15, 15)
            )
            
            analysis["eyes_detected"] = len(eyes)
            
            if len(eyes) >= 2:
                # Both eyes visible - person is awake and looking
                analysis["is_open"] = True
                analysis["state"] = "open"
                self.eye_closure_start = None
                
                # Calculate eye openness
                eye_area = sum(w * h for (x, y, w, h) in eyes)
                face_area = face_roi.shape[0] * face_roi.shape[1]
                analysis["closure_percentage"] = 0.0
                
            elif len(eyes) == 1:
                # One eye visible - person might be tired or turning
                analysis["is_open"] = True
                analysis["state"] = "partially_open"
                
                # Track closure time
                if self.eye_closure_start is None:
                    self.eye_closure_start = datetime.now()
                
                closure_time = (datetime.now() - self.eye_closure_start).total_seconds()
                analysis["closure_percentage"] = min(100, (closure_time / self.drowsiness_threshold) * 100)
                
            else:
                # No eyes detected - person might be sleeping or looking down
                analysis["is_open"] = False
                analysis["state"] = "closed"
                
                # Track closure time
                if self.eye_closure_start is None:
                    self.eye_closure_start = datetime.now()
                
                closure_time = (datetime.now() - self.eye_closure_start).total_seconds()
                analysis["closure_percentage"] = min(100, (closure_time / self.sleep_threshold) * 100)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Eye analysis error: {e}")
            return analysis
    
    def _analyze_head_pose(self, face_roi: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Dict:
        """Analyze head pose and direction"""
        analysis = {
            "facing_front": True,
            "yaw_angle": 0.0,      # Left-right rotation
            "pitch_angle": 0.0,    # Up-down rotation
            "confidence": 0.0
        }
        
        try:
            x1, y1, x2, y2 = face_bbox
            face_width = x2 - x1
            face_height = y2 - y1
            
            # Simple face center tracking
            face_center = ((x1 + x2) / 2, (y1 + y2) / 2)
            self.face_center_history.append(face_center)
            
            # Calculate stability
            if len(self.face_center_history) > 5:
                centers = list(self.face_center_history)
                variance = np.var(centers, axis=0)
                stability = 100 - min(100, np.sum(variance) / 100)
                analysis["confidence"] = stability
            
            # Detect features for pose
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
            edges = cv2.Canny(gray_face, 50, 150)
            
            # Estimate horizontal head position (yaw)
            left_half = edges[:, :edges.shape[1]//2]
            right_half = edges[:, edges.shape[1]//2:]
            
            left_intensity = np.sum(left_half)
            right_intensity = np.sum(right_half)
            
            if left_intensity + right_intensity > 0:
                ratio = left_intensity / (left_intensity + right_intensity + 1e-5)
                analysis["yaw_angle"] = (ratio - 0.5) * 90  # -45 to +45 degrees
                
                if abs(analysis["yaw_angle"]) > 30:
                    analysis["facing_front"] = False
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Head pose analysis error: {e}")
            return analysis
    
    def _analyze_motion(self, frame: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Dict:
        """Analyze motion in face region"""
        analysis = {
            "motion_detected": False,
            "motion_magnitude": 0.0,
            "movement_type": "static"  # static, slight, active, extreme
        }
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.prev_gray is None:
                self.prev_gray = gray
                return analysis
            
            # Calculate optical flow in face region
            x1, y1, x2, y2 = face_bbox
            face_region_prev = self.prev_gray[max(0, y1):min(self.prev_gray.shape[0], y2),
                                              max(0, x1):min(self.prev_gray.shape[1], x2)]
            face_region_curr = gray[max(0, y1):min(gray.shape[0], y2),
                                    max(0, x1):min(gray.shape[1], x2)]
            
            if face_region_prev.shape == face_region_curr.shape and face_region_prev.size > 0:
                diff = cv2.absdiff(face_region_prev, face_region_curr)
                motion_magnitude = np.mean(diff)
                
                analysis["motion_magnitude"] = motion_magnitude
                analysis["motion_detected"] = motion_magnitude > self.motion_threshold
                
                if motion_magnitude > 100:
                    analysis["movement_type"] = "extreme"
                elif motion_magnitude > 50:
                    analysis["movement_type"] = "active"
                elif motion_magnitude > 20:
                    analysis["movement_type"] = "slight"
                else:
                    analysis["movement_type"] = "static"
                
                self.motion_history.append(motion_magnitude)
            
            self.prev_gray = gray
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Motion analysis error: {e}")
            return analysis
    
    def _integrate_analysis(self, eye_analysis: Dict, pose_analysis: Dict, 
                            motion_analysis: Dict) -> BehaviorState:
        """Integrate all analysis into final behavior state"""
        
        # Sleeping: eyes closed for >sleep_threshold
        if not eye_analysis["is_open"] and eye_analysis["closure_percentage"] > 90:
            return BehaviorState.SLEEPING
        
        # Drowsy: eyes closed for >drowsiness_threshold but <sleep_threshold
        if not eye_analysis["is_open"] and eye_analysis["closure_percentage"] > 50:
            return BehaviorState.DROWSY
        
        # Looking away: not facing front
        if not pose_analysis["facing_front"]:
            return BehaviorState.LOOKING_AWAY
        
        # Idle: facing front but no motion
        if eye_analysis["is_open"] and not motion_analysis["motion_detected"]:
            if motion_analysis["movement_type"] == "static":
                return BehaviorState.IDLE
        
        # Active: eyes open and motion detected
        if eye_analysis["is_open"] and motion_analysis["motion_detected"]:
            return BehaviorState.ACTIVE
        
        # Default
        return BehaviorState.ACTIVE
    
    def _calculate_attention_score(self, eye_analysis: Dict, pose_analysis: Dict,
                                   motion_analysis: Dict) -> float:
        """Calculate attention score 0-100%"""
        score = 100.0
        
        # Reduce for closed eyes
        if not eye_analysis["is_open"]:
            score -= eye_analysis["closure_percentage"]
        
        # Reduce for not facing front
        if not pose_analysis["facing_front"]:
            score -= abs(pose_analysis["yaw_angle"]) / 90 * 30
        
        # Reduce for no motion
        if not motion_analysis["motion_detected"]:
            score -= 10
        
        return max(0, min(100, score))
    
    def _determine_alert_level(self, state: BehaviorState, attention_score: float) -> str:
        """Determine alert level"""
        if state in [BehaviorState.SLEEPING, BehaviorState.DROWSY]:
            return "critical"
        elif state == BehaviorState.LOOKING_AWAY:
            return "caution"
        elif attention_score < 30:
            return "critical"
        elif attention_score < 60:
            return "caution"
        else:
            return "normal"
    
    def _collect_flags(self, eye_analysis: Dict, pose_analysis: Dict, 
                       motion_analysis: Dict) -> List[str]:
        """Collect behavioral flags"""
        flags = []
        
        if eye_analysis["closure_percentage"] > 70:
            flags.append("Eyes closed")
        
        if not pose_analysis["facing_front"]:
            flags.append(f"Looking {'left' if pose_analysis['yaw_angle'] > 0 else 'right'}")
        
        if motion_analysis["movement_type"] == "extreme":
            flags.append("Excessive movement")
        elif motion_analysis["movement_type"] == "static":
            flags.append("No movement")
        
        return flags
    
    def reset(self):
        """Reset analyzer state"""
        self.behavior_history.clear()
        self.eye_closure_start = None
        self.idle_start = None
        self.looking_away_start = None
        self.prev_gray = None
        self.motion_history.clear()
        self.face_center_history.clear()
        logger.info("✅ Behavior analyzer reset")
