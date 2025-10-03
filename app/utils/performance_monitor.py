"""Performance monitoring and metrics collection system."""
import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics collected."""
    RESPONSE_TIME = "response_time"
    REQUEST_COUNT = "request_count"
    ERROR_COUNT = "error_count"
    CACHE_HIT_RATE = "cache_hit_rate"
    THROUGHPUT = "throughput"
    CUSTOM = "custom"

@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "labels": self.labels,
        }

@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    name: str
    metric_type: MetricType
    count: int
    min_value: float
    max_value: float
    avg_value: float
    median_value: float
    percentile_95: float
    percentile_99: float
    last_value: float
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "count": self.count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "avg_value": self.avg_value,
            "median_value": self.median_value,
            "percentile_95": self.percentile_95,
            "percentile_99": self.percentile_99,
            "last_value": self.last_value,
            "last_updated": self.last_updated.isoformat(),
        }

class MetricsCollector:
    """Collects and manages performance metrics."""
    
    def __init__(self, max_points_per_metric: int = 1000):
        """Initialize metrics collector.
        
        Args:
            max_points_per_metric: Maximum data points to keep per metric
        """
        self.max_points = max_points_per_metric
        self._metrics: Dict[str, List[MetricPoint]] = {}
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
    def record_metric(
        self, 
        name: str, 
        value: Union[int, float], 
        metric_type: MetricType = MetricType.CUSTOM,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels for the metric
        """
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            
            point = MetricPoint(
                timestamp=datetime.now(),
                value=float(value),
                labels=labels or {}
            )
            
            self._metrics[name].append(point)
            
            # Keep only the latest points
            if len(self._metrics[name]) > self.max_points:
                self._metrics[name] = self._metrics[name][-self.max_points:]
            
            # Periodic cleanup
            self._periodic_cleanup()
    
    def record_response_time(
        self, 
        operation: str, 
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record response time for an operation."""
        self.record_metric(
            name=f"{operation}_response_time",
            value=duration_ms,
            metric_type=MetricType.RESPONSE_TIME,
            labels=labels
        )
    
    def record_request_count(
        self, 
        operation: str,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a request count."""
        self.record_metric(
            name=f"{operation}_request_count",
            value=1,
            metric_type=MetricType.REQUEST_COUNT,
            labels=labels
        )
    
    def record_error(
        self, 
        operation: str,
        error_type: str,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record an error occurrence."""
        error_labels = {"error_type": error_type}
        if labels:
            error_labels.update(labels)
            
        self.record_metric(
            name=f"{operation}_error_count",
            value=1,
            metric_type=MetricType.ERROR_COUNT,
            labels=error_labels
        )
    
    def record_cache_hit_rate(
        self, 
        cache_name: str, 
        hit_rate: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record cache hit rate."""
        self.record_metric(
            name=f"{cache_name}_cache_hit_rate",
            value=hit_rate,
            metric_type=MetricType.CACHE_HIT_RATE,
            labels=labels
        )
    
    def get_metric_summary(self, name: str) -> Optional[MetricSummary]:
        """Get summary statistics for a metric."""
        with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return None
            
            points = self._metrics[name]
            values = [p.value for p in points]
            
            if not values:
                return None
            
            # Calculate statistics
            sorted_values = sorted(values)
            count = len(values)
            
            return MetricSummary(
                name=name,
                metric_type=MetricType.CUSTOM,  # Could be inferred from name
                count=count,
                min_value=min(values),
                max_value=max(values),
                avg_value=statistics.mean(values),
                median_value=statistics.median(values),
                percentile_95=sorted_values[int(0.95 * count)] if count > 0 else 0,
                percentile_99=sorted_values[int(0.99 * count)] if count > 0 else 0,
                last_value=points[-1].value,
                last_updated=points[-1].timestamp,
            )
    
    def get_all_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Get summaries for all metrics."""
        with self._lock:
            summaries = {}
            for name in self._metrics:
                summary = self.get_metric_summary(name)
                if summary:
                    summaries[name] = summary.to_dict()
            return summaries
    
    def get_recent_points(
        self, 
        name: str, 
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get recent metric points."""
        with self._lock:
            if name not in self._metrics:
                return []
            
            points = self._metrics[name]
            
            # Filter by time
            if since:
                points = [p for p in points if p.timestamp >= since]
            
            # Apply limit
            if limit:
                points = points[-limit:]
            
            return [p.to_dict() for p in points]
    
    def get_metric_names(self) -> List[str]:
        """Get all metric names."""
        with self._lock:
            return list(self._metrics.keys())
    
    def clear_metric(self, name: str) -> bool:
        """Clear a specific metric."""
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                return True
            return False
    
    def clear_all_metrics(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
    
    def _periodic_cleanup(self) -> None:
        """Perform periodic cleanup of old data."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=24)  # Keep 24 hours
        
        for name, points in self._metrics.items():
            # Remove old points
            self._metrics[name] = [
                p for p in points 
                if p.timestamp >= cutoff_time
            ]
        
        self._last_cleanup = current_time

class PerformanceMonitor:
    """High-level performance monitoring with context managers."""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize performance monitor."""
        self.metrics = metrics_collector or MetricsCollector()
        self._active_operations: Dict[str, datetime] = {}
        self._lock = threading.RLock()
    
    def start_operation(self, operation: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Start monitoring an operation.
        
        Returns:
            Operation ID for tracking
        """
        operation_id = f"{operation}_{int(time.time() * 1000000)}"
        
        with self._lock:
            self._active_operations[operation_id] = datetime.now()
        
        # Record request count
        self.metrics.record_request_count(operation, labels)
        
        return operation_id
    
    def end_operation(
        self, 
        operation_id: str, 
        operation: str,
        success: bool = True,
        error_type: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """End monitoring an operation.
        
        Returns:
            Duration in milliseconds
        """
        end_time = datetime.now()
        
        with self._lock:
            start_time = self._active_operations.pop(operation_id, end_time)
        
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Record response time
        self.metrics.record_response_time(operation, duration_ms, labels)
        
        # Record errors if any
        if not success and error_type:
            self.metrics.record_error(operation, error_type, labels)
        
        return duration_ms
    
    def operation_context(
        self, 
        operation: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """Context manager for monitoring an operation."""
        return OperationContext(self, operation, labels)
    
    async def async_operation_context(
        self, 
        operation: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """Async context manager for monitoring an operation."""
        return AsyncOperationContext(self, operation, labels)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance monitoring statistics."""
        with self._lock:
            return {
                "active_operations": len(self._active_operations),
                "metrics_count": len(self.metrics.get_metric_names()),
                "metric_summaries": self.metrics.get_all_summaries(),
            }

class OperationContext:
    """Context manager for synchronous operation monitoring."""
    
    def __init__(
        self, 
        monitor: PerformanceMonitor, 
        operation: str,
        labels: Optional[Dict[str, str]] = None
    ):
        self.monitor = monitor
        self.operation = operation
        self.labels = labels
        self.operation_id = None
    
    def __enter__(self):
        self.operation_id = self.monitor.start_operation(self.operation, self.labels)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error_type = exc_type.__name__ if exc_type else None
        
        self.monitor.end_operation(
            self.operation_id,
            self.operation,
            success=success,
            error_type=error_type,
            labels=self.labels
        )

class AsyncOperationContext:
    """Async context manager for operation monitoring."""
    
    def __init__(
        self, 
        monitor: PerformanceMonitor, 
        operation: str,
        labels: Optional[Dict[str, str]] = None
    ):
        self.monitor = monitor
        self.operation = operation
        self.labels = labels
        self.operation_id = None
    
    async def __aenter__(self):
        self.operation_id = self.monitor.start_operation(self.operation, self.labels)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error_type = exc_type.__name__ if exc_type else None
        
        self.monitor.end_operation(
            self.operation_id,
            self.operation,
            success=success,
            error_type=error_type,
            labels=self.labels
        )

# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    
    if _performance_monitor is None:
        with _monitor_lock:
            if _performance_monitor is None:
                _performance_monitor = PerformanceMonitor()
    
    return _performance_monitor

def reset_performance_monitor() -> None:
    """Reset the global performance monitor (for testing)."""
    global _performance_monitor
    with _monitor_lock:
        _performance_monitor = None

# Convenience decorators
def monitor_performance(operation: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to monitor function performance."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                async with AsyncOperationContext(monitor, operation, labels):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                with OperationContext(monitor, operation, labels):
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator