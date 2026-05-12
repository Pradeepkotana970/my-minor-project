"""
Advanced Multi-Scale Face Detection Module
Optimized for 0.3m to 10m+ distances with MediaPipe + OpenCV ensemble
"""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MultiScaleFaceDetector:
    """
    Ensemble detector combining:
    - MediaPipe FaceDetection (DNN-based, handles varying scales)
    - Haar Cascade (fallback for edge cases)
    - Dynamic preprocessing for different lighting conditions
    """
    
    def __init__(self):
        """Initialize multi-scale detector"""
        try:
            import mediapipe as mp
            self.mp_face_detection = mp.solutions.face_detection
            self.detector_far = self.mp_face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.3  # Far faces: very lenient
            )
            self.detector_close = self.mp_face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.4  # Close faces: balanced
            )
            self.use_mediapipe = True
            logger.info("✅ MultiScaleFaceDetector initialized with MediaPipe")
        except ImportError:
            logger.warning("⚠️ MediaPipe not available, using Haar Cascade fallback")
            self.use_mediapipe = False
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
        
        # Face size constraints
        self.min_face_size = 20      # 20px minimum
        self.max_face_size = 1200    # 1200px maximum
        self.min_face_ratio = 0.8    # Width/Height should be 0.8-1.2
        self.max_face_ratio = 1.2
    
    def preprocess_frame_enhanced(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhanced preprocessing for better detection in all conditions
        - Adaptive histogram equalization
        - Bilateral filtering (noise reduction)
        - Contrast enhancement
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Adaptive histogram equalization (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(10, 10))
            enhanced = clahe.apply(gray)
            
            # Bilateral filter: reduce noise while keeping edges sharp
            denoised = cv2.bilateralFilter(enhanced, 11, 75, 75)
            
            # Contrast enhancement
            alpha = 1.3  # Brightness
            beta = 10    # Contrast
            enhanced_contrast = cv2.convertScaleAbs(denoised, alpha=alpha, beta=beta)
            
            return enhanced_contrast
        except Exception as e:
            logger.error(f"❌ Preprocessing error: {e}")
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    def detect_faces_mediapipe(self, frame: np.ndarray, detect_mode: str = "auto") -> List[Dict]:
        """
        Detect faces using MediaPipe with automatic mode selection
        
        Args:
            frame: Input BGR frame
            detect_mode: 'auto', 'close', or 'far'
            
        Returns:
            List of detection dicts with keys: x1, y1, x2, y2, confidence, size, distance
        """
        detections = []
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape
            
            # Auto-select detector based on frame content
            if detect_mode == "auto":
                # Use both detectors for maximum coverage
                detectors = [self.detector_close, self.detector_far]
            elif detect_mode == "close":
                detectors = [self.detector_close]
            else:
                detectors = [self.detector_far]
            
            seen_faces = set()  # Avoid duplicates
            
            for detector in detectors:
                results = detector.process(rgb_frame)
                
                if results.detections:
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        
                        # Convert to absolute coordinates
                        x1 = int(max(0, bbox.xmin * w))
                        y1 = int(max(0, bbox.ymin * h))
                        x2 = int(min(w, (bbox.xmin + bbox.width) * w))
                        y2 = int(min(h, (bbox.ymin + bbox.height) * h))
                        
                        face_w = x2 - x1
                        face_h = y2 - y1
                        
                        # Validate face dimensions
                        if not self._validate_face_size(face_w, face_h):
                            continue
                        
                        # Avoid duplicate detections
                        face_key = (x1, y1, x2, y2)
                        if face_key in seen_faces:
                            continue
                        seen_faces.add(face_key)
                        
                        confidence = float(detection.score[0]) * 100
                        
                        # Estimate distance
                        avg_size = (face_w + face_h) / 2
                        size_ratio = avg_size / w
                        
                        if size_ratio > 0.5:
                            distance = "near"
                        elif size_ratio > 0.25:
                            distance = "medium"
                        elif size_ratio > 0.1:
                            distance = "far"
                        else:
                            distance = "extra_far"
                        
                        detections.append({
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "confidence": confidence,
                            "size": (face_w, face_h),
                            "distance": distance,
                            "face_roi": frame[y1:y2, x1:x2]
                        })
            
            return detections
            
        except Exception as e:
            logger.error(f"❌ MediaPipe detection error: {e}")
            return []
    
    def detect_faces_haar(self, frame: np.ndarray) -> List[Dict]:
        """
        Fallback Haar Cascade detection
        """
        detections = []
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # Multi-scale detection
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=4,
                minSize=(self.min_face_size, self.min_face_size),
                maxSize=(self.max_face_size, self.max_face_size)
            )
            
            for (x, y, face_w, face_h) in faces:
                if not self._validate_face_size(face_w, face_h):
                    continue
                
                x2, y2 = x + face_w, y + face_h
                size_ratio = ((face_w + face_h) / 2) / w
                
                if size_ratio > 0.5:
                    distance = "near"
                elif size_ratio > 0.25:
                    distance = "medium"
                elif size_ratio > 0.1:
                    distance = "far"
                else:
                    distance = "extra_far"
                
                # Estimate confidence based on contrast
                face_roi = gray[y:y2, x:x2]
                contrast = np.std(face_roi)
                confidence = min(100, 30 + (contrast / 255 * 50))  # 30-80%
                
                detections.append({
                    "x1": x,
                    "y1": y,
                    "x2": x2,
                    "y2": y2,
                    "confidence": confidence,
                    "size": (face_w, face_h),
                    "distance": distance,
                    "face_roi": frame[y:y2, x:x2]
                })
            
            return detections
            
        except Exception as e:
            logger.error(f"❌ Haar detection error: {e}")
            return []
    
    def detect_faces(self, frame: np.ndarray, enable_preprocessing: bool = True) -> List[Dict]:
        """
        Main detection interface with preprocessing
        """
        if enable_preprocessing:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        if self.use_mediapipe:
            return self.detect_faces_mediapipe(frame, detect_mode="auto")
        else:
            return self.detect_faces_haar(frame)
    
    def _validate_face_size(self, width: int, height: int) -> bool:
        """Validate face dimensions"""
        if width < self.min_face_size or height < self.min_face_size:
            return False
        if width > self.max_face_size or height > self.max_face_size:
            return False
        
        ratio = width / (height + 1e-5)  # Avoid division by zero
        if ratio < self.min_face_ratio or ratio > self.max_face_ratio:
            return False
        
        return True
    
    def detect_eyes(self, face_roi: np.ndarray, cascade: Optional[cv2.CascadeClassifier] = None) -> List[Tuple[int, int, int, int]]:
        """
        Detect eyes in face ROI
        """
        try:
            if cascade is None and not self.use_mediapipe:
                cascade = self.eye_cascade
            
            if cascade is None:
                return []
            
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
            eyes = cascade.detectMultiScale(gray_face, scaleFactor=1.1, minNeighbors=5, minSize=(10, 10))
            
            return list(eyes)
        except Exception as e:
            logger.error(f"❌ Eye detection error: {e}")
            return []
