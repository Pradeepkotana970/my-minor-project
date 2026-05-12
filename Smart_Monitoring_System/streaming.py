"""
Real-time Streaming & WebSocket Module
Live video streaming, real-time updates, and event broadcasting
"""

import logging
import json
import asyncio
from typing import Dict, List, Set, Callable, Optional
from datetime import datetime
import threading
from queue import Queue, Empty
from enum import Enum
import base64

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Real-time event types"""
    FRAME_PROCESSED = "frame_processed"
    PERSON_DETECTED = "person_detected"
    BEHAVIOR_CHANGED = "behavior_changed"
    ALERT_TRIGGERED = "alert_triggered"
    ATTENDANCE_MARKED = "attendance_marked"
    ANOMALY_DETECTED = "anomaly_detected"
    PREDICTION_UPDATE = "prediction_update"
    STATISTICS_UPDATE = "statistics_update"


class StreamingServer:
    """WebSocket streaming server for real-time updates"""
    
    def __init__(self, max_clients: int = 100):
        """
        Initialize streaming server
        
        Args:
            max_clients: Maximum concurrent WebSocket clients
        """
        self.max_clients = max_clients
        self.clients: Dict[str, Dict] = {}  # client_id -> {org_id, user_id, filters, websocket}
        self.event_queue = Queue()
        self.event_handlers: Dict[EventType, List[Callable]] = {e: [] for e in EventType}
        self.lock = threading.Lock()
        
        logger.info(f"StreamingServer initialized (max {max_clients} clients)")
    
    def register_client(self, client_id: str, org_id: str, user_id: str, filters: Dict = None) -> bool:
        """
        Register new streaming client
        
        Args:
            client_id: Unique client identifier
            org_id: Organization ID
            user_id: User ID
            filters: Event filters (e.g., {"event_types": ["alert_triggered"]})
            
        Returns:
            True if registered successfully
        """
        with self.lock:
            if len(self.clients) >= self.max_clients:
                logger.warning(f"Max clients ({self.max_clients}) reached")
                return False
            
            self.clients[client_id] = {
                "org_id": org_id,
                "user_id": user_id,
                "filters": filters or {},
                "connected_at": datetime.now(),
                "events_received": 0
            }
            
            logger.info(f"Client registered: {client_id} ({org_id}/{user_id})")
            return True
    
    def unregister_client(self, client_id: str):
        """Unregister a streaming client"""
        with self.lock:
            if client_id in self.clients:
                client = self.clients.pop(client_id)
                logger.info(f"Client unregistered: {client_id} (received {client['events_received']} events)")
    
    def publish_event(self, event_type: EventType, data: Dict, org_id: str, user_id: str = None):
        """
        Publish event to all interested clients
        
        Args:
            event_type: Type of event
            data: Event data payload
            org_id: Organization ID
            user_id: Optional user ID for filtering
        """
        event = {
            "event_type": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "org_id": org_id,
            "user_id": user_id,
            "data": data
        }
        
        self.event_queue.put(event)
        
        # Broadcast to interested clients
        with self.lock:
            for client_id, client_info in self.clients.items():
                if client_info["org_id"] != org_id:
                    continue
                
                # Check filters
                if self._matches_filters(event_type, client_info.get("filters", {})):
                    client_info["events_received"] += 1
                    # In production, would use WebSocket here
                    logger.debug(f"Event published to {client_id}: {event_type.value}")
    
    def broadcast_frame(self, org_id: str, frame_base64: str, metadata: Dict):
        """
        Broadcast video frame to all clients in org
        
        Args:
            org_id: Organization ID
            frame_base64: Base64 encoded frame
            metadata: Frame metadata (timestamp, fps, size, etc)
        """
        event = {
            "event_type": "frame_update",
            "timestamp": datetime.now().isoformat(),
            "org_id": org_id,
            "data": {
                "frame": frame_base64,
                "metadata": metadata
            }
        }
        
        with self.lock:
            client_count = sum(1 for c in self.clients.values() if c["org_id"] == org_id)
            if client_count > 0:
                logger.debug(f"Broadcasting frame to {client_count} clients in {org_id}")
    
    def get_client_stats(self) -> Dict:
        """Get streaming server statistics"""
        with self.lock:
            org_count = len(set(c["org_id"] for c in self.clients.values()))
            total_events = sum(c["events_received"] for c in self.clients.values())
            
            return {
                "total_clients": len(self.clients),
                "organizations": org_count,
                "event_queue_size": self.event_queue.qsize(),
                "total_events_published": total_events,
                "max_capacity": self.max_clients,
                "usage_percent": (len(self.clients) / self.max_clients) * 100
            }
    
    @staticmethod
    def _matches_filters(event_type: EventType, filters: Dict) -> bool:
        """Check if event matches client filters"""
        if not filters:
            return True
        
        if "event_types" in filters:
            return event_type.value in filters["event_types"]
        
        return True


class LiveDashboardManager:
    """Manage live dashboard updates and metrics"""
    
    def __init__(self, streaming_server: StreamingServer):
        """
        Initialize live dashboard manager
        
        Args:
            streaming_server: StreamingServer instance
        """
        self.streaming = streaming_server
        self.metrics_cache: Dict[str, Dict] = {}
        self.update_interval = 5  # seconds
    
    def update_live_metrics(self, org_id: str, metrics: Dict):
        """
        Update and broadcast live metrics
        
        Args:
            org_id: Organization ID
            metrics: Live metrics dictionary
        """
        self.metrics_cache[org_id] = {
            "timestamp": datetime.now().isoformat(),
            "data": metrics
        }
        
        # Broadcast to clients
        self.streaming.publish_event(
            EventType.STATISTICS_UPDATE,
            metrics,
            org_id
        )
        
        logger.debug(f"Live metrics updated for {org_id}")
    
    def broadcast_alert(self, org_id: str, alert_data: Dict):
        """
        Broadcast alert to live dashboard
        
        Args:
            org_id: Organization ID
            alert_data: Alert information
        """
        self.streaming.publish_event(
            EventType.ALERT_TRIGGERED,
            alert_data,
            org_id
        )
        
        logger.info(f"Alert broadcast to {org_id}: {alert_data.get('alert_type')}")
    
    def broadcast_person_detected(self, org_id: str, person_data: Dict):
        """
        Broadcast person detection
        
        Args:
            org_id: Organization ID
            person_data: Person detection information
        """
        self.streaming.publish_event(
            EventType.PERSON_DETECTED,
            person_data,
            org_id
        )
    
    def broadcast_anomaly(self, org_id: str, anomaly_data: Dict):
        """
        Broadcast detected anomaly
        
        Args:
            org_id: Organization ID
            anomaly_data: Anomaly information
        """
        self.streaming.publish_event(
            EventType.ANOMALY_DETECTED,
            anomaly_data,
            org_id
        )
        
        logger.warning(f"Anomaly detected in {org_id}: {anomaly_data}")


class EventBuffer:
    """Buffer and batch events for efficient storage"""
    
    def __init__(self, batch_size: int = 100, flush_interval: int = 5):
        """
        Initialize event buffer
        
        Args:
            batch_size: Buffer size before auto-flush
            flush_interval: Seconds before auto-flush
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: List[Dict] = []
        self.lock = threading.Lock()
        self.flush_callbacks: List[Callable] = []
    
    def add_event(self, event: Dict) -> bool:
        """
        Add event to buffer
        
        Args:
            event: Event to add
            
        Returns:
            True if buffer flushed
        """
        with self.lock:
            self.buffer.append(event)
            
            if len(self.buffer) >= self.batch_size:
                self.flush()
                return True
        
        return False
    
    def flush(self):
        """Flush all buffered events"""
        with self.lock:
            if self.buffer:
                # Call registered callbacks
                for callback in self.flush_callbacks:
                    try:
                        callback(self.buffer)
                    except Exception as e:
                        logger.error(f"Error in flush callback: {e}")
                
                self.buffer = []
                logger.debug(f"Event buffer flushed")
    
    def register_callback(self, callback: Callable):
        """
        Register callback for flush events
        
        Args:
            callback: Function to call when buffer is flushed
        """
        self.flush_callbacks.append(callback)


class MetricsCollector:
    """Collect and aggregate real-time metrics"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.metrics: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def record_metric(self, org_id: str, metric_name: str, value: any, tags: Dict = None):
        """
        Record a metric
        
        Args:
            org_id: Organization ID
            metric_name: Name of metric
            value: Metric value
            tags: Optional tags for filtering
        """
        with self.lock:
            if org_id not in self.metrics:
                self.metrics[org_id] = {}
            
            self.metrics[org_id][metric_name] = {
                "value": value,
                "timestamp": datetime.now(),
                "tags": tags or {}
            }
    
    def get_metrics(self, org_id: str, metric_prefix: str = None) -> Dict:
        """
        Get metrics for organization
        
        Args:
            org_id: Organization ID
            metric_prefix: Optional prefix to filter metrics
            
        Returns:
            Dictionary of metrics
        """
        with self.lock:
            org_metrics = self.metrics.get(org_id, {})
            
            if metric_prefix:
                org_metrics = {
                    k: v for k, v in org_metrics.items()
                    if k.startswith(metric_prefix)
                }
            
            return org_metrics
    
    def get_aggregated_metrics(self, org_id: str) -> Dict:
        """
        Get aggregated real-time metrics
        
        Args:
            org_id: Organization ID
            
        Returns:
            Aggregated metrics
        """
        org_metrics = self.get_metrics(org_id)
        
        aggregated = {}
        for metric_name, metric_data in org_metrics.items():
            if isinstance(metric_data["value"], (int, float)):
                aggregated[metric_name] = metric_data["value"]
        
        return aggregated


class StreamingAnalytics:
    """Analyze streaming events for patterns and insights"""
    
    def __init__(self, streaming_server: StreamingServer):
        """
        Initialize streaming analytics
        
        Args:
            streaming_server: StreamingServer instance
        """
        self.streaming = streaming_server
        self.event_counts: Dict[str, Dict[str, int]] = {}  # org_id -> {event_type -> count}
    
    def track_event(self, event_type: EventType, org_id: str):
        """
        Track event occurrence
        
        Args:
            event_type: Type of event
            org_id: Organization ID
        """
        if org_id not in self.event_counts:
            self.event_counts[org_id] = {}
        
        event_key = event_type.value
        self.event_counts[org_id][event_key] = self.event_counts[org_id].get(event_key, 0) + 1
    
    def get_event_summary(self, org_id: str) -> Dict:
        """
        Get event summary for organization
        
        Args:
            org_id: Organization ID
            
        Returns:
            Event statistics
        """
        return self.event_counts.get(org_id, {})
    
    def identify_trending_alerts(self, org_id: str, window_minutes: int = 30) -> List[Dict]:
        """
        Identify trending alerts in organization
        
        Args:
            org_id: Organization ID
            window_minutes: Time window for analysis
            
        Returns:
            List of trending alert types
        """
        event_summary = self.get_event_summary(org_id)
        
        # Filter to alert events
        alert_events = {
            k: v for k, v in event_summary.items()
            if 'alert' in k or 'anomaly' in k
        }
        
        # Sort by frequency
        trending = sorted(
            [{"event": k, "count": v} for k, v in alert_events.items()],
            key=lambda x: x["count"],
            reverse=True
        )
        
        return trending


class NotificationQueue:
    """Queue and manage real-time notifications"""
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize notification queue
        
        Args:
            max_queue_size: Maximum notifications to queue
        """
        self.queue = Queue(maxsize=max_queue_size)
        self.subscribers: Dict[str, Set[str]] = {}  # user_id -> {notification_channels}
    
    def subscribe(self, user_id: str, channel: str):
        """
        Subscribe user to notification channel
        
        Args:
            user_id: User ID
            channel: Channel name (e.g., "alert", "prediction", "attendance")
        """
        if user_id not in self.subscribers:
            self.subscribers[user_id] = set()
        
        self.subscribers[user_id].add(channel)
        logger.debug(f"User {user_id} subscribed to {channel}")
    
    def unsubscribe(self, user_id: str, channel: str):
        """Unsubscribe user from channel"""
        if user_id in self.subscribers:
            self.subscribers[user_id].discard(channel)
    
    def queue_notification(self, user_id: str, channel: str, notification: Dict) -> bool:
        """
        Queue notification for user
        
        Args:
            user_id: User ID
            channel: Channel name
            notification: Notification payload
            
        Returns:
            True if queued successfully
        """
        if user_id not in self.subscribers or channel not in self.subscribers[user_id]:
            return False
        
        try:
            self.queue.put_nowait({
                "user_id": user_id,
                "channel": channel,
                "notification": notification,
                "timestamp": datetime.now().isoformat()
            })
            return True
        except:
            logger.warning(f"Notification queue full for {user_id}")
            return False
    
    def get_notification(self, timeout: float = 1.0) -> Optional[Dict]:
        """
        Get next notification from queue
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Notification or None
        """
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return None
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
