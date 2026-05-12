"""
Advanced Face Detection Module
Implements multi-scale detection with adaptive preprocessing for varying lighting and distances
"""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FaceDetector:
    """Advanced face detection with dynamic Mediapipe Deep Learning Engine"""
    
    def __init__(self, cascade_path: Optional[str] = None):
        """
        Initialize face detector with Mediapipe
        
        Args:
            cascade_path: Ignored, retained for backward compatibility
        """
        try:
            import mediapipe as mp
            self.mp_face_detection = mp.solutions.face_detection
            # model_selection=1 is optimized for faces farther than 2m, 0 for close
            self.detector_far = self.mp_face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.4
            )
            self.detector_close = self.mp_face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            )
            self.use_mediapipe = True
            logger.info("FaceDetector initialized with Deep Learning MediaPipe")
        except ImportError:
            logger.warning("Mediapipe not installed. Falling back to Haar cascades.")
            self.use_mediapipe = False
            if cascade_path is None:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Face size thresholds
        self.min_face_width = 20            
        self.max_face_width = 700           
    
    def preprocess_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess frame for better face detection
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray_equalized = clahe.apply(gray)
            denoised = cv2.bilateralFilter(gray_equalized, 9, 75, 75)
            
            return frame, denoised
        except Exception as e:
            logger.error(f"Error in preprocessing: {e}")
            return frame, cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    def detect_faces(self, frame: np.ndarray, mode: str = "balanced") -> List[Dict]:
        """
        Detect faces with high-accuracy deep learning
        
        Args:
            frame: Input BGR frame
            mode: Kept for compatibility. "close" uses model_selection=0, others use 1.
        """
        try:
            detected_faces = []
            
            if self.use_mediapipe:
                # Convert BGR to RGB for Mediapipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, _ = frame.shape
                
                # Pick model based on mode
                detector = self.detector_close if mode == "close" else self.detector_far
                results = detector.process(rgb_frame)
                
                if results.detections:
                    for detection in results.detections:
                        bboxC = detection.location_data.relative_bounding_box
                        x1 = int(bboxC.xmin * w)
                        y1 = int(bboxC.ymin * h)
                        w1 = int(bboxC.width * w)
                        h1 = int(bboxC.height * h)
                        
                        # Apply limits
                        x1, y1 = max(0, x1), max(0, y1)
                        if w1 < self.min_face_width or h1 < self.min_face_width: continue
                        
                        confidence_estimate = float(detection.score[0]) * 100
                        
                        avg_size = (w1 + h1) / 2
                        distance = "close" if avg_size > 200 else "medium" if avg_size > 100 else "far"
                        
                        detected_faces.append({
                            "x": int(x1), "y": int(y1), "w": int(w1), "h": int(h1),
                            "distance": distance,
                            "confidence_estimate": round(confidence_estimate, 2),
                            "center": (int(x1 + w1/2), int(y1 + h1/2)),
                            "area": int(w1 * h1),
                            "mode": mode
                        })
            else:
                # Fallback to legacy Haar
                _, gray = self.preprocess_frame(frame)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(self.min_face_width, self.min_face_width))
                for (fx, fy, fw, fh) in faces:
                    avg_size = (fw + fh) / 2
                    distance = "close" if avg_size > 200 else "medium" if avg_size > 100 else "far"
                    confidence_estimate = min(100, (avg_size / 300) * 100)
                    detected_faces.append({
                        "x": int(fx), "y": int(fy), "w": int(fw), "h": int(fh),
                        "distance": distance, "confidence_estimate": round(confidence_estimate, 2),
                        "center": (int(fx + fw/2), int(fy + fh/2)),
                        "area": int(fw * fh), "mode": mode
                    })
            
            return detected_faces
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def detect_with_adaptive_mode(self, frame: np.ndarray) -> List[Dict]:
        """
        With Mediapipe, we don't strictly need distinct modes as it is robust.
        We'll detect once using the far-model, which handles multi-scale natively.
        """
        try:
            faces = self.detect_faces(frame, mode="balanced")
            if not faces and self.use_mediapipe:
                # Try close model if far missed
                faces = self.detect_faces(frame, mode="close")
            return self._deduplicate_faces(faces) if faces else []
        except Exception as e:
            logger.error(f"Error in deep learning detection fallback: {e}")
            return []
    
    def _deduplicate_faces(self, faces: List[Dict], overlap_threshold: float = 0.5) -> List[Dict]:
        return faces  # Mediapipe rarely outputs extreme duplicates; return as-is or implement basic NMS if needed (kept simple for performance)
    
    def get_face_roi(self, frame: np.ndarray, face: Dict, padding: int = 10) -> Optional[np.ndarray]:
        try:
            x, y, w, h = face["x"], face["y"], face["w"], face["h"]
            x, y = max(0, x - padding), max(0, y - padding)
            w, h = min(frame.shape[1] - x, w + 2 * padding), min(frame.shape[0] - y, h + 2 * padding)
            return frame[y:y+h, x:x+w]
        except Exception as e:
            logger.error(f"Error extracting face ROI: {e}")
            return None


class EyeDetector:
    """Detects eyes within face region"""
    
    def __init__(self, cascade_path: Optional[str] = None):
        """
        Initialize eye detector
        
        Args:
            cascade_path: Path to eye cascade XML file
        """
        if cascade_path is None:
            cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
        
        self.eye_cascade = cv2.CascadeClassifier(cascade_path)
        logger.info("EyeDetector initialized")
    
    def detect_eyes(self, face_roi: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect eyes in face region
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            List of eye rectangles
        """
        try:
            if face_roi is None or face_roi.size == 0:
                return []
            
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            eyes = self.eye_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=10,
                minSize=(15, 15)
            )
            
            return list(eyes)
        except Exception as e:
            logger.error(f"Error detecting eyes: {e}")
            return []
    
    def estimate_eye_closure(self, face_roi: np.ndarray) -> Dict:
        """
        Estimate if eyes are closed
        Uses variance analysis on eye region
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            Dictionary with eye closure information
        """
        try:
            eyes = self.detect_eyes(face_roi)
            
            if len(eyes) == 0:
                return {
                    "eyes_detected": 0,
                    "likely_closed": True,
                    "confidence": 0.85
                }
            elif len(eyes) >= 2:
                # Eyes detected, check if they appear closed
                gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                
                # Calculate variance in eye regions
                variances = []
                for (ex, ey, ew, eh) in eyes:
                    eye_region = gray[ey:ey+eh, ex:ex+ew]
                    variance = np.var(eye_region)
                    variances.append(variance)
                
                avg_variance = np.mean(variances)
                
                # Lower variance suggests eyes are closed
                # Threshold: typically 100-200 for open eyes, <50 for closed
                threshold = 60
                likely_closed = avg_variance < threshold
                confidence = min(0.95, abs(avg_variance - threshold) / 100)
                
                return {
                    "eyes_detected": len(eyes),
                    "likely_closed": likely_closed,
                    "avg_variance": round(avg_variance, 2),
                    "confidence": round(confidence, 2)
                }
            else:
                # Only one eye detected (partial closure or angle)
                return {
                    "eyes_detected": 1,
                    "likely_closed": False,
                    "confidence": 0.5
                }
        
        except Exception as e:
            logger.error(f"Error estimating eye closure: {e}")
            return {
                "eyes_detected": 0,
                "likely_closed": True,
                "confidence": 0.0
            }
