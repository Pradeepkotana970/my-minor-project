"""
Performance Optimization Module
Implements GPU acceleration, frame skipping, caching, and multi-threading strategies
"""

import cv2
import numpy as np
import logging
import threading
import queue
from typing import Optional, Dict, List, Tuple
from collections import deque
import time

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Optimizes system performance through various strategies"""
    
    def __init__(
        self,
        enable_gpu: bool = True,
        frame_skip: int = 1,
        cache_size: int = 30,
        enable_threading: bool = True
    ):
        """
        Initialize performance optimizer
        
        Args:
            enable_gpu: Enable GPU acceleration if available
            frame_skip: Process every nth frame (1=all, 2=every 2nd)
            cache_size: Cache size for frame storage
            enable_threading: Enable multi-threading optimization
        """
        self.enable_gpu = enable_gpu
        self.frame_skip = frame_skip
        self.cache_size = cache_size
        self.enable_threading = enable_threading
        
        # GPU detection
        self.gpu_available = self._detect_gpu() if enable_gpu else False
        
        # Frame caching
        self.frame_cache = deque(maxlen=cache_size)
        self.detection_cache = {}
        
        # Threading
        self.frame_queue = queue.Queue(maxsize=5)
        self.result_queue = queue.Queue(maxsize=5)
        
        # Performance metrics
        self.fps_history = deque(maxlen=100)
        self.frame_times = deque(maxlen=100)
        
        logger.info(f"PerformanceOptimizer initialized (GPU: {self.gpu_available}, "
                   f"skip: {frame_skip}, threading: {enable_threading})")
    
    def _detect_gpu(self) -> bool:
        """Detect if GPU is available"""
        try:
            # Check OpenCV GPU support
            result = cv2.getBuildInformation()
            if 'CUDA' in result:
                logger.info("✅ CUDA GPU support detected")
                return True
            else:
                logger.warning("⚠️ GPU not available, using CPU")
                return False
        except Exception as e:
            logger.warning(f"Could not detect GPU: {e}")
            return False
    
    def should_process_frame(self, frame_number: int) -> bool:
        """
        Determine if frame should be processed based on skip strategy
        
        Args:
            frame_number: Current frame number
            
        Returns:
            True if frame should be processed
        """
        return frame_number % self.frame_skip == 0
    
    def optimize_frame(
        self,
        frame: np.ndarray,
        target_width: int = 640,
        target_height: int = 480
    ) -> np.ndarray:
        """
        Optimize frame for faster processing
        
        Args:
            frame: Input frame
            target_width: Target width
            target_height: Target height
            
        Returns:
            Optimized frame
        """
        try:
            # Resize for faster processing
            optimized = cv2.resize(frame, (target_width, target_height))
            
            # Optional: Convert to YUV for faster processing
            # optimized = cv2.cvtColor(optimized, cv2.COLOR_BGR2YUV)
            
            return optimized
        except Exception as e:
            logger.error(f"Error optimizing frame: {e}")
            return frame
    
    def cache_detection_result(
        self,
        face_id: str,
        detection_result: Dict,
        ttl_frames: int = 5
    ):
        """
        Cache detection result to avoid re-processing
        
        Args:
            face_id: Face identifier
            detection_result: Detection result
            ttl_frames: Time-to-live in frames
        """
        self.detection_cache[face_id] = {
            "result": detection_result,
            "timestamp": time.time(),
            "ttl": ttl_frames
        }
    
    def get_cached_detection(self, face_id: str) -> Optional[Dict]:
        """
        Get cached detection result if valid
        
        Args:
            face_id: Face identifier
            
        Returns:
            Cached result or None
        """
        if face_id not in self.detection_cache:
            return None
        
        cache_entry = self.detection_cache[face_id]
        
        # Check TTL
        if cache_entry["ttl"] <= 0:
            del self.detection_cache[face_id]
            return None
        
        # Decrease TTL
        cache_entry["ttl"] -= 1
        
        return cache_entry["result"]
    
    def clear_cache(self):
        """Clear all caches"""
        self.frame_cache.clear()
        self.detection_cache.clear()
    
    def measure_performance(self) -> Dict:
        """
        Measure current performance metrics
        
        Returns:
            Performance metrics dictionary
        """
        if not self.fps_history:
            return {
                "average_fps": 0,
                "max_fps": 0,
                "min_fps": 0,
                "frame_time_ms": 0
            }
        
        fps_values = list(self.fps_history)
        frame_times = list(self.frame_times)
        
        return {
            "average_fps": round(np.mean(fps_values), 1),
            "max_fps": round(max(fps_values), 1),
            "min_fps": round(min(fps_values), 1),
            "std_dev_fps": round(np.std(fps_values), 1),
            "average_frame_time_ms": round(np.mean(frame_times) * 1000, 2) if frame_times else 0,
            "gpu_available": self.gpu_available,
            "frame_skip": self.frame_skip,
            "cache_utilization": len(self.detection_cache)
        }
    
    def record_frame_time(self, frame_time: float):
        """Record frame processing time"""
        self.frame_times.append(frame_time)
        
        # Calculate FPS
        fps = 1.0 / frame_time if frame_time > 0 else 0
        self.fps_history.append(fps)


class ParallelProcessor:
    """Processes frames and detection in parallel threads"""
    
    def __init__(self, num_workers: int = 2):
        """
        Initialize parallel processor
        
        Args:
            num_workers: Number of worker threads
        """
        self.num_workers = num_workers
        self.input_queue = queue.Queue(maxsize=10)
        self.output_queue = queue.Queue(maxsize=10)
        self.workers = []
        self.running = False
        
        logger.info(f"ParallelProcessor initialized with {num_workers} workers")
    
    def start(self, process_function):
        """
        Start worker threads
        
        Args:
            process_function: Function to process items in parallel
        """
        self.running = True
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker,
                args=(process_function,),
                daemon=True,
                name=f"ProcessorWorker-{i}"
            )
            worker.start()
            self.workers.append(worker)
    
    def _worker(self, process_function):
        """Worker thread function"""
        while self.running:
            try:
                item = self.input_queue.get(timeout=1)
                if item is None:  # Poison pill
                    break
                
                result = process_function(item)
                self.output_queue.put(result)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def submit_task(self, task):
        """Submit task for processing"""
        try:
            self.input_queue.put(task, timeout=1)
            return True
        except queue.Full:
            logger.warning("Processor queue full, dropping task")
            return False
    
    def get_result(self, timeout: float = 1.0):
        """Get processed result"""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def stop(self):
        """Stop worker threads"""
        self.running = False
        
        # Send poison pills
        for _ in range(self.num_workers):
            try:
                self.input_queue.put(None, timeout=1)
            except queue.Full:
                pass
        
        # Wait for workers
        for worker in self.workers:
            worker.join(timeout=2)


class FrameRateController:
    """Controls frame rate to maintain target FPS"""
    
    def __init__(self, target_fps: int = 30):
        """
        Initialize frame rate controller
        
        Args:
            target_fps: Target frames per second
        """
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.last_frame_time = time.time()
        self.frame_count = 0
        
        logger.info(f"FrameRateController set to {target_fps} FPS")
    
    def wait_for_frame(self) -> float:
        """
        Wait to maintain target FPS
        
        Returns:
            Actual time since last frame
        """
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        # Sleep if we're ahead of schedule
        sleep_time = self.frame_interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
            elapsed = self.frame_interval
        
        self.last_frame_time = time.time()
        self.frame_count += 1
        
        return elapsed
    
    def reset(self):
        """Reset frame timer"""
        self.last_frame_time = time.time()
        self.frame_count = 0


class MemoryOptimizer:
    """Optimizes memory usage"""
    
    @staticmethod
    def enable_memory_optimization():
        """Enable memory optimization techniques"""
        try:
            import gc
            gc.enable()
            gc.set_threshold(700, 10, 10)
            logger.info("Memory optimization enabled")
        except Exception as e:
            logger.error(f"Error enabling memory optimization: {e}")
    
    @staticmethod
    def force_garbage_collection():
        """Force garbage collection"""
        try:
            import gc
            gc.collect()
        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")
    
    @staticmethod
    def get_memory_usage() -> Dict:
        """
        Get current memory usage
        
        Returns:
            Memory usage dictionary
        """
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return {}


class BatchProcessor:
    """Processes multiple frames as batch for efficiency"""
    
    def __init__(self, batch_size: int = 4):
        """
        Initialize batch processor
        
        Args:
            batch_size: Number of frames per batch
        """
        self.batch_size = batch_size
        self.frame_batch = []
        self.result_batch = []
        
        logger.info(f"BatchProcessor initialized with batch size {batch_size}")
    
    def add_frame(self, frame: np.ndarray) -> bool:
        """
        Add frame to batch
        
        Args:
            frame: Frame to add
            
        Returns:
            True if batch is ready
        """
        self.frame_batch.append(frame)
        return len(self.frame_batch) >= self.batch_size
    
    def get_batch(self) -> Optional[List[np.ndarray]]:
        """Get current batch if ready"""
        if len(self.frame_batch) >= self.batch_size:
            batch = self.frame_batch[:self.batch_size]
            self.frame_batch = self.frame_batch[self.batch_size:]
            return batch
        return None
    
    def batch_resize(self, frames: List[np.ndarray], size: Tuple[int, int]) -> np.ndarray:
        """
        Resize multiple frames as batch
        
        Args:
            frames: List of frames
            size: Target size (width, height)
            
        Returns:
            Stacked and resized frames
        """
        try:
            resized_frames = [cv2.resize(f, size) for f in frames]
            return np.stack(resized_frames, axis=0)
        except Exception as e:
            logger.error(f"Error in batch resize: {e}")
            return None
    
    def clear_batch(self):
        """Clear current batch"""
        self.frame_batch.clear()
        self.result_batch.clear()


class AdaptiveQualityScaler:
    """Automatically adjusts quality based on system load"""
    
    def __init__(
        self,
        min_quality: float = 0.5,
        max_quality: float = 1.0,
        target_fps: int = 30
    ):
        """
        Initialize quality scaler
        
        Args:
            min_quality: Minimum quality (0.5 = 50% resolution)
            max_quality: Maximum quality (1.0 = full resolution)
            target_fps: Target FPS to maintain
        """
        self.min_quality = min_quality
        self.max_quality = max_quality
        self.target_fps = target_fps
        self.current_quality = max_quality
        
        self.fps_history = deque(maxlen=30)
        self.adjustment_interval = 30  # Frames between adjustments
        self.frame_counter = 0
        
        logger.info(f"AdaptiveQualityScaler initialized (quality: {min_quality}-{max_quality})")
    
    def update_fps(self, current_fps: float):
        """Update FPS history for quality adjustment"""
        self.fps_history.append(current_fps)
        self.frame_counter += 1
        
        if self.frame_counter >= self.adjustment_interval:
            self._adjust_quality()
            self.frame_counter = 0
    
    def _adjust_quality(self):
        """Adjust quality based on FPS history"""
        if not self.fps_history:
            return
        
        avg_fps = np.mean(self.fps_history)
        
        if avg_fps < self.target_fps * 0.8:
            # FPS dropping, reduce quality
            self.current_quality = max(
                self.min_quality,
                self.current_quality - 0.1
            )
            logger.info(f"Reducing quality to {self.current_quality:.1%}")
        
        elif avg_fps > self.target_fps * 1.1:
            # FPS good, increase quality
            self.current_quality = min(
                self.max_quality,
                self.current_quality + 0.1
            )
            logger.info(f"Increasing quality to {self.current_quality:.1%}")
    
    def get_target_resolution(self, base_width: int, base_height: int) -> Tuple[int, int]:
        """
        Get target resolution based on current quality
        
        Args:
            base_width: Base width
            base_height: Base height
            
        Returns:
            Adjusted (width, height)
        """
        width = int(base_width * self.current_quality)
        height = int(base_height * self.current_quality)
        
        # Ensure even dimensions for video codecs
        width = width if width % 2 == 0 else width - 1
        height = height if height % 2 == 0 else height - 1
        
        return (width, height)
