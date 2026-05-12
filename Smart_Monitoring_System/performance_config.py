"""
Performance Configuration Module
Different profiles for various deployment scenarios
"""

from enum import Enum
from dataclasses import dataclass

class PerformanceProfile(Enum):
    """Performance profile configurations"""
    EDGE_DEVICE = "edge_device"           # Ultra-lightweight (Raspberry Pi, Jetson Nano)
    LIGHTWEIGHT = "lightweight"           # Laptop, single server
    BALANCED = "balanced"                 # Standard server
    HIGH_PERFORMANCE = "high_performance" # High-end server
    GPU_ACCELERATED = "gpu_accelerated"   # CUDA GPU server
    CLOUD = "cloud"                       # Cloud deployment (scalable)


@dataclass
class PerformanceConfig:
    """Performance configuration"""
    
    # Frame processing
    camera_width: int
    camera_height: int
    target_fps: int
    frame_skip: int
    
    # Detection
    detection_scale_factor: float
    min_neighbors: int
    min_face_size: tuple
    
    # Processing
    enable_gpu: bool
    batch_size: int
    num_workers: int
    cache_size: int
    
    # Quality control
    adaptive_quality: bool
    min_quality: float
    max_quality: float
    
    # Threading
    enable_parallel_processing: bool
    enable_memory_optimization: bool
    
    # Database
    db_batch_write: bool
    db_batch_size: int


def get_profile_config(profile: PerformanceProfile) -> PerformanceConfig:
    """
    Get performance configuration for a profile
    
    Args:
        profile: Performance profile
        
    Returns:
        PerformanceConfig instance
    """
    
    configs = {
        PerformanceProfile.EDGE_DEVICE: PerformanceConfig(
            camera_width=320,
            camera_height=240,
            target_fps=15,
            frame_skip=2,
            
            detection_scale_factor=1.2,
            min_neighbors=3,
            min_face_size=(30, 30),
            
            enable_gpu=False,
            batch_size=1,
            num_workers=1,
            cache_size=10,
            
            adaptive_quality=True,
            min_quality=0.3,
            max_quality=0.7,
            
            enable_parallel_processing=False,
            enable_memory_optimization=True,
            
            db_batch_write=True,
            db_batch_size=100
        ),
        
        PerformanceProfile.LIGHTWEIGHT: PerformanceConfig(
            camera_width=640,
            camera_height=480,
            target_fps=20,
            frame_skip=1,
            
            detection_scale_factor=1.15,
            min_neighbors=4,
            min_face_size=(25, 25),
            
            enable_gpu=False,
            batch_size=2,
            num_workers=2,
            cache_size=20,
            
            adaptive_quality=True,
            min_quality=0.5,
            max_quality=0.9,
            
            enable_parallel_processing=True,
            enable_memory_optimization=True,
            
            db_batch_write=True,
            db_batch_size=200
        ),
        
        PerformanceProfile.BALANCED: PerformanceConfig(
            camera_width=1280,
            camera_height=720,
            target_fps=25,
            frame_skip=1,
            
            detection_scale_factor=1.1,
            min_neighbors=5,
            min_face_size=(20, 20),
            
            enable_gpu=False,
            batch_size=4,
            num_workers=3,
            cache_size=30,
            
            adaptive_quality=False,
            min_quality=0.8,
            max_quality=1.0,
            
            enable_parallel_processing=True,
            enable_memory_optimization=True,
            
            db_batch_write=True,
            db_batch_size=500
        ),
        
        PerformanceProfile.HIGH_PERFORMANCE: PerformanceConfig(
            camera_width=1920,
            camera_height=1080,
            target_fps=30,
            frame_skip=1,
            
            detection_scale_factor=1.05,
            min_neighbors=6,
            min_face_size=(15, 15),
            
            enable_gpu=False,
            batch_size=8,
            num_workers=4,
            cache_size=50,
            
            adaptive_quality=False,
            min_quality=1.0,
            max_quality=1.0,
            
            enable_parallel_processing=True,
            enable_memory_optimization=False,
            
            db_batch_write=True,
            db_batch_size=1000
        ),
        
        PerformanceProfile.GPU_ACCELERATED: PerformanceConfig(
            camera_width=1920,
            camera_height=1080,
            target_fps=30,
            frame_skip=1,
            
            detection_scale_factor=1.05,
            min_neighbors=6,
            min_face_size=(15, 15),
            
            enable_gpu=True,
            batch_size=16,
            num_workers=4,
            cache_size=100,
            
            adaptive_quality=False,
            min_quality=1.0,
            max_quality=1.0,
            
            enable_parallel_processing=True,
            enable_memory_optimization=False,
            
            db_batch_write=True,
            db_batch_size=2000
        ),
        
        PerformanceProfile.CLOUD: PerformanceConfig(
            camera_width=1280,
            camera_height=720,
            target_fps=25,
            frame_skip=1,
            
            detection_scale_factor=1.1,
            min_neighbors=5,
            min_face_size=(20, 20),
            
            enable_gpu=True,
            batch_size=8,
            num_workers=8,
            cache_size=50,
            
            adaptive_quality=True,
            min_quality=0.6,
            max_quality=1.0,
            
            enable_parallel_processing=True,
            enable_memory_optimization=True,
            
            db_batch_write=True,
            db_batch_size=1000
        )
    }
    
    return configs.get(profile, configs[PerformanceProfile.BALANCED])


PROFILE_RECOMMENDATIONS = {
    PerformanceProfile.EDGE_DEVICE: """
    For Raspberry Pi, Jetson Nano, or similar edge devices
    - Ultra-low resolution (320x240)
    - Frame skipping (every 2nd frame)
    - Minimal GPU requirements
    - Heavy memory optimization
    - Best for: Single person monitoring, simple detection
    """,
    
    PerformanceProfile.LIGHTWEIGHT: """
    For laptops or single-core servers
    - Low resolution (640x480)
    - Some frame skipping
    - Parallel processing with 2 workers
    - Memory optimization enabled
    - Best for: Office monitoring, 1-5 people
    """,
    
    PerformanceProfile.BALANCED: """
    For standard servers or multi-core laptops
    - Full HD resolution (1280x720)
    - No frame skipping
    - Parallel processing with 3 workers
    - Good balance of speed and accuracy
    - Best for: Classroom monitoring, 10-20 people
    """,
    
    PerformanceProfile.HIGH_PERFORMANCE: """
    For high-end servers with many cores
    - 4K ready (1920x1080)
    - No frame skipping
    - Parallel processing with 4 workers
    - Maximum accuracy
    - Best for: Large installations, 50+ people
    """,
    
    PerformanceProfile.GPU_ACCELERATED: """
    For servers with NVIDIA CUDA GPU
    - 4K resolution (1920x1080)
    - GPU acceleration enabled
    - Large batch processing
    - Real-time multi-camera support
    - Best for: Enterprise scale, 100+ people
    """,
    
    PerformanceProfile.CLOUD: """
    For cloud deployments (AWS, Azure, Google Cloud)
    - Balanced performance and cost
    - Auto-scaling support
    - Adaptive quality based on load
    - Batch database writes
    - Best for: Scalable deployments
    """
}
