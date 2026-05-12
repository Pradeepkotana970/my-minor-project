"""
Advanced Caching & Performance Optimization Module
Redis integration, intelligent caching, and query optimization
"""

import logging
import json
import hashlib
import time
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta
import redis
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """Centralized cache management with Redis and in-memory fallback"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", use_redis: bool = True):
        """
        Initialize cache manager
        
        Args:
            redis_url: Redis connection URL
            use_redis: Whether to use Redis (falls back to in-memory if unavailable)
        """
        self.redis_client = None
        self.use_redis = use_redis
        self.memory_cache: Dict[str, Dict] = {}  # Simple in-memory fallback
        
        if use_redis:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory cache: {e}")
                self.redis_client = None
    
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        try:
            # Try Redis first
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            
            # Fall back to memory cache
            if key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                
                # Check expiration
                if cache_entry.get("expires_at"):
                    if datetime.now() > cache_entry["expires_at"]:
                        del self.memory_cache[key]
                        return default
                
                return cache_entry["value"]
            
            return default
        
        except Exception as e:
            logger.error(f"Error getting cache {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        try:
            json_value = json.dumps(value)
            
            # Try Redis first
            if self.redis_client:
                self.redis_client.setex(key, ttl, json_value)
                return
            
            # Fall back to memory cache
            self.memory_cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl)
            }
        
        except Exception as e:
            logger.error(f"Error setting cache {key}: {e}")
    
    def delete(self, key: str):
        """Delete cache entry"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            
            self.memory_cache.pop(key, None)
        
        except Exception as e:
            logger.error(f"Error deleting cache {key}: {e}")
    
    def clear(self, pattern: str = "*"):
        """
        Clear cache entries matching pattern
        
        Args:
            pattern: Key pattern (e.g., "user:*", "analytics:*")
        """
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            # Memory cache - simple deletion by prefix
            prefix = pattern.replace("*", "")
            keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self.memory_cache[k]
        
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {
            "memory_cache_size": len(self.memory_cache),
            "using_redis": self.redis_client is not None
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")
                stats["redis_keys"] = self.redis_client.dbsize()
            except:
                pass
        
        return stats


class QueryOptimizer:
    """Optimize database queries with smart caching and indexing"""
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize query optimizer
        
        Args:
            cache_manager: CacheManager instance
        """
        self.cache = cache_manager
        self.query_stats: Dict[str, Dict] = {}
    
    def cached_query(self, cache_key: str, ttl: int = 3600):
        """
        Decorator for caching query results
        
        Args:
            cache_key: Cache key for result
            ttl: Time-to-live in seconds
            
        Example:
            @cached_query("analytics:engagement:org_123", ttl=300)
            def get_engagement_data(org_id):
                # Query logic
                return data
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Check cache first
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    # Record cache hit
                    self._record_query_stat(cache_key, "hit")
                    return cached_result
                
                # Execute query
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Cache result
                self.cache.set(cache_key, result, ttl)
                
                # Record stats
                self._record_query_stat(cache_key, "miss", execution_time)
                
                return result
            
            return wrapper
        
        return decorator
    
    def _record_query_stat(self, query_key: str, hit_type: str, execution_time: float = 0):
        """Record query statistics"""
        if query_key not in self.query_stats:
            self.query_stats[query_key] = {"hits": 0, "misses": 0, "total_time": 0}
        
        if hit_type == "hit":
            self.query_stats[query_key]["hits"] += 1
        else:
            self.query_stats[query_key]["misses"] += 1
            self.query_stats[query_key]["total_time"] += execution_time
    
    def get_query_stats(self) -> Dict:
        """Get query performance statistics"""
        stats = {}
        for query_key, data in self.query_stats.items():
            total = data["hits"] + data["misses"]
            hit_rate = (data["hits"] / total * 100) if total > 0 else 0
            
            stats[query_key] = {
                "total_queries": total,
                "cache_hit_rate": f"{hit_rate:.1f}%",
                "avg_execution_ms": (data["total_time"] / data["misses"] * 1000) if data["misses"] > 0 else 0
            }
        
        return stats


class ConnectionPool:
    """Manage database connection pool for concurrency"""
    
    def __init__(self, db_path: str, pool_size: int = 10, check_same_thread: bool = False):
        """
        Initialize connection pool
        
        Args:
            db_path: Database path
            pool_size: Number of connections in pool
            check_same_thread: SQLite thread safety
        """
        import sqlite3
        
        self.db_path = db_path
        self.pool_size = pool_size
        self.connections = []
        self.available = []
        self.lock = __import__('threading').Lock()
        
        # Initialize pool
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path, timeout=30, check_same_thread=check_same_thread)
            conn.row_factory = sqlite3.Row
            self.connections.append(conn)
            self.available.append(conn)
        
        logger.info(f"Connection pool initialized with {pool_size} connections")
    
    def get_connection(self, timeout: float = 5.0):
        """
        Get connection from pool
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Database connection
        """
        import time
        
        start_time = time.time()
        while True:
            with self.lock:
                if self.available:
                    return self.available.pop()
            
            if time.time() - start_time > timeout:
                raise TimeoutError("No available connections in pool")
            
            time.sleep(0.1)
    
    def release_connection(self, conn):
        """Release connection back to pool"""
        with self.lock:
            if conn in self.connections:
                self.available.append(conn)
    
    def close_all(self):
        """Close all connections in pool"""
        for conn in self.connections:
            conn.close()
        logger.info("All connections closed")


class MemoryCacheLayer:
    """In-memory caching layer for frequently accessed data"""
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize memory cache
        
        Args:
            max_size: Maximum number of cache entries
        """
        self.max_size = max_size
        self.cache: Dict[str, Dict] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = __import__('threading').Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get from memory cache"""
        with self.lock:
            if key in self.cache:
                # Update access time
                self.access_times[key] = time.time()
                entry = self.cache[key]
                
                # Check expiration
                if entry.get("expires_at"):
                    if time.time() > entry["expires_at"]:
                        del self.cache[key]
                        del self.access_times[key]
                        return None
                
                return entry["value"]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in memory cache"""
        with self.lock:
            # Evict LRU entry if cache full
            if len(self.cache) >= self.max_size:
                lru_key = min(self.access_times, key=self.access_times.get)
                del self.cache[lru_key]
                del self.access_times[lru_key]
            
            self.cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl
            }
            self.access_times[key] = time.time()


class BatchProcessor:
    """Batch process operations for efficiency"""
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        """
        Initialize batch processor
        
        Args:
            batch_size: Size of batch before processing
            flush_interval: Seconds before auto-flush
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batches: Dict[str, list] = {}
        self.processors: Dict[str, Callable] = {}
        self.last_flush: Dict[str, float] = {}
        self.lock = __import__('threading').Lock()
    
    def add_to_batch(self, batch_key: str, item: Any) -> bool:
        """
        Add item to batch
        
        Args:
            batch_key: Batch identifier
            item: Item to add
            
        Returns:
            True if batch was processed
        """
        with self.lock:
            if batch_key not in self.batches:
                self.batches[batch_key] = []
                self.last_flush[batch_key] = time.time()
            
            self.batches[batch_key].append(item)
            
            # Check if should flush
            if len(self.batches[batch_key]) >= self.batch_size:
                self.flush_batch(batch_key)
                return True
        
        return False
    
    def flush_batch(self, batch_key: str):
        """Process pending batch"""
        with self.lock:
            if batch_key not in self.batches or not self.batches[batch_key]:
                return
            
            items = self.batches[batch_key]
            
            # Call processor if registered
            if batch_key in self.processors:
                try:
                    self.processors[batch_key](items)
                except Exception as e:
                    logger.error(f"Error processing batch {batch_key}: {e}")
            
            # Clear batch
            self.batches[batch_key] = []
            self.last_flush[batch_key] = time.time()
    
    def register_processor(self, batch_key: str, processor: Callable):
        """
        Register batch processor function
        
        Args:
            batch_key: Batch identifier
            processor: Function to process batch (receives list of items)
        """
        self.processors[batch_key] = processor


class CompressionOptimizer:
    """Optimize data storage with compression"""
    
    @staticmethod
    def compress_data(data: Dict) -> str:
        """
        Compress data for storage
        
        Args:
            data: Data to compress
            
        Returns:
            Compressed data string
        """
        import gzip
        
        json_str = json.dumps(data)
        compressed = gzip.compress(json_str.encode())
        
        # Return as hex string for storage
        return compressed.hex()
    
    @staticmethod
    def decompress_data(compressed: str) -> Dict:
        """
        Decompress stored data
        
        Args:
            compressed: Compressed data string
            
        Returns:
            Original data dictionary
        """
        import gzip
        
        data = bytes.fromhex(compressed)
        decompressed = gzip.decompress(data).decode()
        
        return json.loads(decompressed)


class PerformanceMonitor:
    """Monitor application performance metrics"""
    
    def __init__(self):
        """Initialize performance monitor"""
        self.metrics: Dict[str, list] = {}
        self.lock = __import__('threading').Lock()
    
    def record_operation(self, operation_name: str, execution_time_ms: float, success: bool = True):
        """
        Record operation performance
        
        Args:
            operation_name: Name of operation
            execution_time_ms: Execution time in milliseconds
            success: Whether operation was successful
        """
        with self.lock:
            if operation_name not in self.metrics:
                self.metrics[operation_name] = []
            
            self.metrics[operation_name].append({
                "time_ms": execution_time_ms,
                "success": success,
                "timestamp": datetime.now()
            })
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        with self.lock:
            summary = {}
            
            for op_name, records in self.metrics.items():
                if not records:
                    continue
                
                times = [r["time_ms"] for r in records]
                successes = sum(1 for r in records if r["success"])
                
                summary[op_name] = {
                    "count": len(records),
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "success_rate": (successes / len(records)) * 100
                }
            
            return summary
    
    def get_bottlenecks(self) -> list[tuple]:
        """Identify performance bottlenecks"""
        summary = self.get_performance_summary()
        
        # Find slowest operations
        bottlenecks = sorted(
            [(op, data["avg_ms"]) for op, data in summary.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return bottlenecks[:10]  # Top 10 slowest
