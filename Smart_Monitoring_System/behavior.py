"""
Advanced Behavior Detection Module
Analyzes drowsiness, inactivity, and engagement levels
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BehaviorAnalyzer:
    """Analyzes person's behavior including sleep, idle, and active states"""
    
    # Behavior states
    ACTIVE = "Active"
    IDLE = "Idle"
    SLEEPING = "Sleeping"
    
    def __init__(
        self,
        sleep_threshold_seconds: float = 3.0,
        idle_threshold_seconds: float = 5.0,
        motion_queue_size: int = 10
    ):
        """
        Initialize behavior analyzer
        
        Args:
            sleep_threshold_seconds: Seconds of eye closure before marking as sleeping
            idle_threshold_seconds: Seconds of inactivity before marking as idle
            motion_queue_size: Number of frames to track for motion detection
        """
        self.sleep_threshold = sleep_threshold_seconds
        self.idle_threshold = idle_threshold_seconds
        
        # Tracking per person
        self.person_state = {}  # {track_id: state_info}
        self.motion_history = {}  # {track_id: deque of motion values}
        self.motion_queue_size = motion_queue_size
        
        logger.info(f"BehaviorAnalyzer initialized (sleep: {sleep_threshold_seconds}s, idle: {idle_threshold_seconds}s)")
    
    def analyze_behavior(
        self,
        track_id: int,
        eye_status: Dict,
        face_roi: np.ndarray,
        prev_face_roi: Optional[np.ndarray] = None
    ) -> Dict:
        """
        Analyze person's behavior based on eyes and motion
        
        Args:
            track_id: Unique track ID
            eye_status: Eye closure detection result
            face_roi: Current face region of interest
            prev_face_roi: Previous frame face ROI for motion detection
            
        Returns:
            Behavior analysis result
        """
        if track_id not in self.person_state:
            self._initialize_person_state(track_id)
        
        state = self.person_state[track_id]
        
        # Update timestamp
        now = datetime.now()
        if state["last_update"] is None:
            state["last_update"] = now
        
        time_delta = (now - state["last_update"]).total_seconds()
        state["last_update"] = now
        
        # Detect motion
        motion_detected = self._detect_motion(track_id, face_roi, prev_face_roi)
        
        if motion_detected:
            state["inactivity_duration"] = 0.0
            state["last_motion_time"] = now
        else:
            state["inactivity_duration"] += time_delta
        
        # Analyze eye status
        eyes_detected = eye_status.get("eyes_detected", 0)
        likely_closed = eye_status.get("likely_closed", False)
        
        # Update eye closure tracking
        if likely_closed and eyes_detected == 0:
            if state["eye_closure_start"] is None:
                state["eye_closure_start"] = now
            
            eye_closure_duration = (now - state["eye_closure_start"]).total_seconds()
        else:
            eye_closure_duration = 0.0
            state["eye_closure_start"] = None
        
        # Determine behavior
        behavior = self._determine_behavior(
            eye_closure_duration,
            state["inactivity_duration"],
            motion_detected
        )
        
        state["current_behavior"] = behavior
        state["last_behavior_change"] = now if behavior != state["previous_behavior"] else state["last_behavior_change"]
        state["previous_behavior"] = behavior
        
        # Count consecutive frames in same state
        if behavior == state.get("last_recorded_behavior"):
            state["behavior_frame_count"] = state.get("behavior_frame_count", 0) + 1
        else:
            state["behavior_frame_count"] = 1
            state["last_recorded_behavior"] = behavior
        
        return {
            "track_id": track_id,
            "behavior": behavior,
            "eye_closure_duration": round(eye_closure_duration, 2),
            "inactivity_duration": round(state["inactivity_duration"], 2),
            "eyes_detected": eyes_detected,
            "motion_detected": motion_detected,
            "avg_motion": round(np.mean(self.motion_history[track_id]), 2) if self.motion_history[track_id] else 0,
            "behavior_confidence": self._get_behavior_confidence(behavior, eye_closure_duration, state["inactivity_duration"]),
            "behavior_frames": state["behavior_frame_count"],
            "alert_triggered": behavior in [self.SLEEPING, self.IDLE]
        }
    
    def _initialize_person_state(self, track_id: int):
        """Initialize tracking state for a person"""
        self.person_state[track_id] = {
            "current_behavior": self.ACTIVE,
            "previous_behavior": self.ACTIVE,
            "last_recorded_behavior": self.ACTIVE,
            "behavior_frame_count": 0,
            "eye_closure_start": None,
            "inactivity_duration": 0.0,
            "last_update": None,
            "last_motion_time": datetime.now(),
            "last_behavior_change": datetime.now()
        }
        self.motion_history[track_id] = deque(maxlen=self.motion_queue_size)
    
    def _detect_motion(
        self,
        track_id: int,
        current_roi: np.ndarray,
        prev_roi: Optional[np.ndarray]
    ) -> bool:
        """
        Detect motion between consecutive frames
        
        Args:
            track_id: Person's track ID
            current_roi: Current frame face ROI
            prev_roi: Previous frame face ROI
            
        Returns:
            True if motion detected
        """
        if prev_roi is None or current_roi is None:
            return False
        
        try:
            # Ensure same size for comparison
            if current_roi.shape != prev_roi.shape:
                return False
            
            # Convert to grayscale
            gray_curr = cv2.cvtColor(current_roi, cv2.COLOR_BGR2GRAY)
            gray_prev = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
            
            # Calculate optical flow or frame difference
            diff = cv2.absdiff(gray_curr, gray_prev)
            
            # Apply threshold
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            # Calculate motion intensity
            motion_pixels = np.count_nonzero(thresh)
            motion_intensity = motion_pixels / (gray_curr.shape[0] * gray_curr.shape[1])
            
            # Store in history
            if track_id not in self.motion_history:
                self.motion_history[track_id] = deque(maxlen=self.motion_queue_size)
            
            self.motion_history[track_id].append(motion_intensity)
            
            # Motion detected if intensity above threshold
            motion_threshold = 0.02  # 2% of face pixels
            detected = motion_intensity > motion_threshold
            
            return detected
        
        except Exception as e:
            logger.error(f"Error detecting motion: {e}")
            return False
    
    def _determine_behavior(
        self,
        eye_closure_duration: float,
        inactivity_duration: float,
        motion_detected: bool
    ) -> str:
        """
        Determine behavior state based on metrics
        
        Args:
            eye_closure_duration: Seconds of continuous eye closure
            inactivity_duration: Seconds of inactivity
            motion_detected: Whether motion is detected in current frame
            
        Returns:
            Behavior state string
        """
        # Sleeping: Eyes closed for threshold seconds
        if eye_closure_duration >= self.sleep_threshold:
            return self.SLEEPING
        
        # Idle: No motion for threshold seconds
        if inactivity_duration >= self.idle_threshold and not motion_detected:
            return self.IDLE
        
        # Active: Motion detected or partial eye closure
        return self.ACTIVE
    
    def _get_behavior_confidence(
        self,
        behavior: str,
        eye_closure_duration: float,
        inactivity_duration: float
    ) -> float:
        """
        Calculate confidence in behavior detection
        
        Args:
            behavior: Current behavior
            eye_closure_duration: Eye closure duration
            inactivity_duration: Inactivity duration
            
        Returns:
            Confidence score (0-1)
        """
        if behavior == self.SLEEPING:
            # Confidence increases with eye closure duration
            confidence = min(1.0, eye_closure_duration / self.sleep_threshold)
            return round(confidence, 2)
        
        elif behavior == self.IDLE:
            # Confidence increases with inactivity duration
            confidence = min(1.0, inactivity_duration / self.idle_threshold)
            return round(confidence, 2)
        
        else:  # ACTIVE
            # High confidence for active state when motion detected
            return 0.95 if eye_closure_duration < 0.5 else 0.7
    
    def get_person_state(self, track_id: int) -> Dict:
        """Get current state for a person"""
        if track_id not in self.person_state:
            return None
        return self.person_state[track_id].copy()
    
    def clear_person_state(self, track_id: int):
        """Clear state for a person (e.g., when track ends)"""
        if track_id in self.person_state:
            del self.person_state[track_id]
        if track_id in self.motion_history:
            del self.motion_history[track_id]


class PostureAnalyzer:
    """Analyzes head pose and posture"""
    
    def __init__(self):
        """Initialize posture analyzer"""
        logger.info("PostureAnalyzer initialized")
    
    def estimate_head_pose(self, face_roi: np.ndarray, face_box: Dict) -> Dict:
        """
        Estimate head pose (forward, left, right, down, up)
        
        Args:
            face_roi: Face region of interest
            face_box: Face detection box with center
            
        Returns:
            Head pose estimation result
        """
        try:
            # Simple heuristic based on face landmarks if available
            # For now, use facial features distribution
            
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            # Calculate center of mass to detect tilt
            h, w = gray.shape
            
            # Find bright regions (likely face areas)
            _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
            moments = cv2.moments(thresh)
            
            if moments["m00"] == 0:
                return self._default_pose()
            
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
            
            # Calculate deviation from center
            center_x = w / 2
            center_y = h / 2
            
            deviation_x = (cx - center_x) / center_x
            deviation_y = (cy - center_y) / center_y
            
            # Classify pose
            pose = self._classify_pose(deviation_x, deviation_y)
            
            return {
                "pose": pose,
                "horizontal_angle": round(deviation_x * 45, 2),  # Rough angle estimate
                "vertical_angle": round(deviation_y * 45, 2),
                "confidence": 0.6
            }
        
        except Exception as e:
            logger.error(f"Error estimating head pose: {e}")
            return self._default_pose()
    
    def _classify_pose(self, dev_x: float, dev_y: float) -> str:
        """Classify head pose based on deviation"""
        threshold = 0.15
        
        if abs(dev_y) > threshold:
            if dev_y > 0:
                vertical = "down"
            else:
                vertical = "up"
        else:
            vertical = "forward"
        
        if abs(dev_x) > threshold:
            if dev_x > 0:
                horizontal = "left"
            else:
                horizontal = "right"
        else:
            horizontal = "forward"
        
        if horizontal == "forward" and vertical == "forward":
            return "forward"
        elif horizontal == "forward":
            return vertical
        elif vertical == "forward":
            return horizontal
        else:
            return f"{horizontal}_{vertical}"
    
    def _default_pose(self) -> Dict:
        """Return default pose result"""
        return {
            "pose": "forward",
            "horizontal_angle": 0.0,
            "vertical_angle": 0.0,
            "confidence": 0.0
        }


class EngagementAnalyzer:
    """Analyzes engagement level and attention"""
    
    def __init__(self):
        """Initialize engagement analyzer"""
        self.engagement_scores = {}  # {track_id: [scores]}
        logger.info("EngagementAnalyzer initialized")
    
    def calculate_engagement(
        self,
        track_id: int,
        behavior: str,
        eye_closure_duration: float,
        inactivity_duration: float,
        head_pose: Dict
    ) -> Dict:
        """
        Calculate engagement level (0-100)
        
        Args:
            track_id: Person's track ID
            behavior: Current behavior state
            eye_closure_duration: Eye closure duration
            inactivity_duration: Inactivity duration
            head_pose: Head pose result
            
        Returns:
            Engagement analysis
        """
        score = 100.0
        
        # Initial score based on behavior
        if behavior == "Sleeping":
            score -= 100  # 0
        elif behavior == "Idle":
            score -= 30   # ~70
        else:
            score -= 5    # ~95
        
        # Adjust for eye factors
        if eye_closure_duration > 0:
            score -= min(30, eye_closure_duration * 10)
        
        # Adjust for inactivity
        if inactivity_duration > 0:
            score -= min(20, inactivity_duration * 2)
        
        # Adjust for head pose
        pose = head_pose.get("pose", "forward")
        if pose != "forward":
            score -= 5
        
        score = max(0, min(100, score))
        
        # Store score
        if track_id not in self.engagement_scores:
            self.engagement_scores[track_id] = deque(maxlen=300)  # Last 10 seconds at 30 FPS
        
        self.engagement_scores[track_id].append(score)
        
        # Calculate statistics
        scores = list(self.engagement_scores[track_id])
        
        return {
            "engagement_level": round(score, 1),
            "average_engagement": round(np.mean(scores), 1) if scores else 0,
            "engagement_trend": self._calculate_trend(scores),
            "engagement_category": self._categorize_engagement(score)
        }
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate engagement trend"""
        if len(scores) < 5:
            return "stable"
        
        recent = np.mean(scores[-5:])
        older = np.mean(scores[-20:-5])
        
        if recent > older + 5:
            return "improving"
        elif recent < older - 5:
            return "declining"
        else:
            return "stable"
    
    def _categorize_engagement(self, score: float) -> str:
        """Categorize engagement score"""
        if score >= 80:
            return "highly_engaged"
        elif score >= 60:
            return "engaged"
        elif score >= 40:
            return "neutral"
        elif score >= 20:
            return "disengaged"
        else:
            return "very_disengaged"
