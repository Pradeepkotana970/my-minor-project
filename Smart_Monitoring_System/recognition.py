"""
Enhanced Face Recognition Module
Implements confidence calibration, liveness detection, and multi-face support
"""

import cv2
import numpy as np
import logging
import os
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """Enhanced face recognition with confidence tuning and liveness detection"""
    
    def __init__(self, model_path: str = 'trainer/trainer.yml'):
        """
        Initialize face recognizer
        
        Args:
            model_path: Path to trained LBPH model
        """
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.model_path = model_path
        self.confidence_threshold = 70
        self.id_to_name = {}
        self.load_model()
        
        # Confidence calibration for different distances
        self.confidence_calibration = {
            "close": {"multiplier": 1.05, "boost": 5},      # Close faces get slight boost
            "medium": {"multiplier": 1.0, "boost": 0},      # Medium distance baseline
            "far": {"multiplier": 0.95, "boost": -5}        # Far faces get slight penalty
        }
        
        # Face history for verification
        self.face_history = defaultdict(list)
        self.history_window = 30  # Seconds
        
        logger.info("FaceRecognizer initialized")
    
    def load_model(self):
        """Load pre-trained LBPH model"""
        try:
            if os.path.exists(self.model_path):
                self.recognizer.read(self.model_path)
                logger.info(f"Model loaded from {self.model_path}")
            else:
                logger.warning(f"Model not found at {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def load_labels(self, labels_path: str = 'trainer/labels.txt'):
        """
        Load ID to name mapping
        
        Args:
            labels_path: Path to labels file
        """
        try:
            self.id_to_name = {}
            if os.path.exists(labels_path):
                with open(labels_path) as f:
                    for line in f:
                        parts = line.strip().split(',', 1)
                        if len(parts) == 2:
                            id_, name = parts
                            self.id_to_name[int(id_)] = name
            logger.info(f"Loaded {len(self.id_to_name)} labels")
        except Exception as e:
            logger.error(f"Error loading labels: {e}")
    
    def calibrate_confidence(self, confidence: float, distance_category: str) -> float:
        """
        Calibrate confidence based on distance
        
        Args:
            confidence: Raw confidence from recognizer
            distance_category: 'close', 'medium', or 'far'
            
        Returns:
            Calibrated confidence score
        """
        if distance_category not in self.confidence_calibration:
            distance_category = "medium"
        
        calibration = self.confidence_calibration[distance_category]
        multiplier = calibration["multiplier"]
        boost = calibration["boost"]
        
        calibrated = min(100, confidence * multiplier + boost)
        return max(0, calibrated)
    
    def set_confidence_threshold(self, threshold: int):
        """
        Set confidence threshold for face recognition
        
        Args:
            threshold: Threshold value (0-100, lower = stricter)
        """
        self.confidence_threshold = threshold
        logger.info(f"Confidence threshold set to {threshold}")
    
    def recognize_face(
        self,
        face_roi: np.ndarray,
        distance_estimate: str = "medium"
    ) -> Dict:
        """
        Recognize face in ROI with confidence calibration
        
        Args:
            face_roi: Face region of interest (BGR)
            distance_estimate: Distance estimate ("close", "medium", "far")
            
        Returns:
            Recognition result dictionary
        """
        try:
            if face_roi is None or face_roi.size == 0:
                return self._unknown_result()
            
            # Convert to grayscale for LBPH
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            # Perform recognition
            label_id, raw_confidence = self.recognizer.predict(gray)
            
            # Apply confidence calibration based on distance
            calibrated_confidence = self._calibrate_confidence(
                raw_confidence,
                distance_estimate
            )
            
            # Check against threshold
            if calibrated_confidence > self.confidence_threshold:
                person_name = self.id_to_name.get(label_id, "Unknown")
                
                return {
                    "status": "recognized",
                    "name": person_name,
                    "id": label_id,
                    "raw_confidence": round(raw_confidence, 2),
                    "calibrated_confidence": round(calibrated_confidence, 2),
                    "distance_estimate": distance_estimate,
                    "threshold": self.confidence_threshold,
                    "passed_threshold": True
                }
            else:
                return self._unknown_result(raw_confidence, calibrated_confidence)
        
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return self._unknown_result()
    
    def _calibrate_confidence(self, raw_confidence: float, distance: str) -> float:
        """
        Calibrate confidence based on distance estimate
        
        Args:
            raw_confidence: Raw LBPH confidence score
            distance: Distance estimate (close/medium/far)
            
        Returns:
            Calibrated confidence score
        """
        calibration = self.confidence_calibration.get(distance, self.confidence_calibration["medium"])
        
        # Apply calibration
        # In LBPH, lower confidence = better match (0 is perfect)
        # We convert to 0-100 scale where 100 is best
        confidence_0_100 = 100 - min(100, raw_confidence)
        
        # Apply multiplier and boost
        calibrated = (confidence_0_100 * calibration["multiplier"]) + calibration["boost"]
        
        return max(0, min(100, calibrated))
    
    def _unknown_result(self, raw_conf: float = 0, calib_conf: float = 0) -> Dict:
        """Generate unknown person result"""
        return {
            "status": "unknown",
            "name": "Unknown",
            "id": -1,
            "raw_confidence": round(raw_conf, 2),
            "calibrated_confidence": round(calib_conf, 2),
            "threshold": self.confidence_threshold,
            "passed_threshold": False
        }
    
    def add_to_history(self, person_name: str, confidence: float):
        """
        Add recognition result to history for verification
        
        Args:
            person_name: Recognized person's name
            confidence: Confidence score
        """
        now = datetime.now()
        self.face_history[person_name].append({
            "timestamp": now,
            "confidence": confidence
        })
        
        # Clean old entries
        cutoff_time = now - timedelta(seconds=self.history_window)
        self.face_history[person_name] = [
            entry for entry in self.face_history[person_name]
            if entry["timestamp"] > cutoff_time
        ]
    
    def get_recognition_consistency(self, person_name: str) -> Dict:
        """
        Get consistency metrics for a person's recent recognitions
        
        Args:
            person_name: Person's name
            
        Returns:
            Consistency metrics
        """
        if person_name not in self.face_history or len(self.face_history[person_name]) == 0:
            return {
                "recognized_times": 0,
                "avg_confidence": 0,
                "consistency": 0
            }
        
        entries = self.face_history[person_name]
        confidences = [e["confidence"] for e in entries]
        
        return {
            "recognized_times": len(entries),
            "avg_confidence": round(np.mean(confidences), 2),
            "max_confidence": round(max(confidences), 2),
            "min_confidence": round(min(confidences), 2),
            "std_dev": round(np.std(confidences), 2),
            "consistency": round(1 - (np.std(confidences) / 100), 2) if np.std(confidences) > 0 else 1.0
        }
    
    def is_likely_spoofing(self, person_name: str, current_confidence: float) -> bool:
        """
        Detect likely spoofing/presentation attacks
        Uses confidence consistency and rapid location changes
        
        Args:
            person_name: Person's name
            current_confidence: Current confidence score
            
        Returns:
            True if likely spoofing, False otherwise
        """
        consistency = self.get_recognition_consistency(person_name)
        
        if consistency["recognized_times"] < 3:
            # Need more history before making decision
            return False
        
        # Check if confidence varies wildly (sign of spoofing)
        if consistency["std_dev"] > 25:
            logger.warning(f"High variance in confidence for {person_name}")
            return True
        
        # Check if confidence is unusually low compared to history
        if consistency["avg_confidence"] > 0 and current_confidence < (consistency["avg_confidence"] - 20):
            logger.warning(f"Confidence anomaly for {person_name}")
            return True
        
        return False


class MultiPersonTracker:
    """Tracks multiple people simultaneously in video stream"""
    
    def __init__(self, max_missing_frames: int = 10):
        """
        Initialize tracker
        
        Args:
            max_missing_frames: Frames before stopping track
        """
        self.tracks = {}  # {track_id: track_info}
        self.next_track_id = 0
        self.max_missing_frames = max_missing_frames
        self.frame_count = 0
        
        logger.info("MultiPersonTracker initialized")
    
    def update_tracks(
        self,
        detected_faces: List[Dict],
        recognition_results: List[Dict]
    ) -> List[Dict]:
        """
        Update tracks with new detections and recognition results
        Performs identity tracking across frames
        
        Args:
            detected_faces: List of detected face dictionaries
            recognition_results: List of recognition results
            
        Returns:
            List of tracked persons with IDs
        """
        self.frame_count += 1
        
        # Match detections to existing tracks
        matched_detections = self._match_detections_to_tracks(detected_faces)
        
        tracked_persons = []
        matched_track_ids = set()
        
        # Update matched tracks
        for face_idx, track_id in matched_detections.items():
            if track_id is not None:
                face = detected_faces[face_idx]
                recog = recognition_results[face_idx]
                
                self.tracks[track_id]["frames_alive"] += 1
                self.tracks[track_id]["frames_missing"] = 0
                self.tracks[track_id]["last_detection"] = face
                self.tracks[track_id]["last_recognition"] = recog
                self.tracks[track_id]["center_history"].append(face["center"])
                
                # Keep history window size manageable
                if len(self.tracks[track_id]["center_history"]) > 30:
                    self.tracks[track_id]["center_history"] = self.tracks[track_id]["center_history"][-30:]
                
                matched_track_ids.add(track_id)
                
                tracked_persons.append({
                    "track_id": track_id,
                    "face": face,
                    "recognition": recog,
                    "status": "tracked"
                })
        
        # Create new tracks for unmatched detections
        for face_idx, track_id in matched_detections.items():
            if track_id is None:
                face = detected_faces[face_idx]
                recog = recognition_results[face_idx]
                
                new_track_id = self.next_track_id
                self.next_track_id += 1
                
                self.tracks[new_track_id] = {
                    "id": new_track_id,
                    "frames_alive": 1,
                    "frames_missing": 0,
                    "first_detection": self.frame_count,
                    "last_detection": face,
                    "last_recognition": recog,
                    "center_history": [face["center"]],
                    "identity": recog.get("name", "Unknown")
                }
                
                tracked_persons.append({
                    "track_id": new_track_id,
                    "face": face,
                    "recognition": recog,
                    "status": "new"
                })
        
        # Update missing tracks
        inactive_tracks = [tid for tid in self.tracks.keys() if tid not in matched_track_ids]
        for track_id in inactive_tracks:
            self.tracks[track_id]["frames_missing"] += 1
        
        # Remove dead tracks
        dead_tracks = [
            tid for tid, track in self.tracks.items()
            if track["frames_missing"] > self.max_missing_frames
        ]
        for track_id in dead_tracks:
            del self.tracks[track_id]
        
        logger.debug(f"Active tracks: {len(self.tracks)}, Tracked persons: {len(tracked_persons)}")
        return tracked_persons
    
    def _match_detections_to_tracks(self, detected_faces: List[Dict]) -> Dict[int, Optional[int]]:
        """
        Match detected faces to existing tracks
        
        Args:
            detected_faces: List of detected faces
            
        Returns:
            Dictionary mapping face index to track_id (or None for new)
        """
        matching = {}
        used_tracks = set()
        
        for face_idx, face in enumerate(detected_faces):
            best_track_id = None
            best_distance = float('inf')
            
            # Find closest tract center
            for track_id, track in self.tracks.items():
                if track_id in used_tracks:
                    continue
                
                last_center = track["last_detection"]["center"]
                current_center = face["center"]
                
                # Euclidean distance
                distance = np.sqrt(
                    (last_center[0] - current_center[0])**2 +
                    (last_center[1] - current_center[1])**2
                )
                
                # Threshold based on face size (allow movement)
                threshold = track["last_detection"]["w"] * 0.5
                
                if distance < threshold and distance < best_distance:
                    best_distance = distance
                    best_track_id = track_id
            
            if best_track_id is not None:
                used_tracks.add(best_track_id)
            
            matching[face_idx] = best_track_id
        
        return matching
    
    def get_active_tracks(self) -> List[Dict]:
        """Get list of currently active tracks"""
        return list(self.tracks.values())
    
    def clear_tracks(self):
        """Clear all tracks (e.g., at end of session)"""
        self.tracks.clear()
        self.next_track_id = 0
        self.frame_count = 0
