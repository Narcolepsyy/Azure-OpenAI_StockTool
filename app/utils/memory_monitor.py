"""Memory usage monitoring and limits for preventing unbounded growth."""
import logging
import psutil
import gc
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory usage statistics."""
    process_memory_mb: float
    system_memory_percent: float
    available_memory_mb: float
    gc_objects_count: int
    timestamp: datetime

class MemoryMonitor:
    """Monitor memory usage and enforce limits."""
    
    def __init__(self, 
                 max_memory_mb: int = 1024,  # 1GB default limit
                 warning_threshold_percent: float = 80.0,
                 check_interval_seconds: int = 60):
        self.max_memory_mb = max_memory_mb
        self.warning_threshold_percent = warning_threshold_percent
        self.check_interval_seconds = check_interval_seconds
        self._lock = threading.Lock()
        self._memory_history: List[MemoryStats] = []
        self._max_history = 100  # Keep last 100 readings
        self._last_cleanup = datetime.now()
        self._cleanup_interval = timedelta(minutes=10)
        
    def get_current_memory_usage(self) -> MemoryStats:
        """Get current memory usage statistics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return MemoryStats(
                process_memory_mb=memory_info.rss / 1024 / 1024,
                system_memory_percent=system_memory.percent,
                available_memory_mb=system_memory.available / 1024 / 1024,
                gc_objects_count=len(gc.get_objects()),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.warning(f"Failed to get memory stats: {e}")
            return MemoryStats(
                process_memory_mb=0.0,
                system_memory_percent=0.0,
                available_memory_mb=0.0,
                gc_objects_count=0,
                timestamp=datetime.now()
            )
    
    def record_memory_usage(self) -> MemoryStats:
        """Record current memory usage and maintain history."""
        stats = self.get_current_memory_usage()
        
        with self._lock:
            self._memory_history.append(stats)
            
            # Maintain history size limit
            if len(self._memory_history) > self._max_history:
                self._memory_history = self._memory_history[-self._max_history:]
        
        return stats
    
    def check_memory_limits(self) -> Dict[str, Any]:
        """Check if memory usage exceeds limits and return status."""
        stats = self.record_memory_usage()
        
        status = {
            "current_memory_mb": stats.process_memory_mb,
            "max_memory_mb": self.max_memory_mb,
            "memory_percent": (stats.process_memory_mb / self.max_memory_mb) * 100,
            "system_memory_percent": stats.system_memory_percent,
            "gc_objects": stats.gc_objects_count,
            "within_limits": True,
            "warnings": [],
            "actions_taken": []
        }
        
        # Check process memory limit
        if stats.process_memory_mb > self.max_memory_mb:
            status["within_limits"] = False
            status["warnings"].append(f"Process memory ({stats.process_memory_mb:.1f}MB) exceeds limit ({self.max_memory_mb}MB)")
        
        # Check warning threshold
        memory_percent = (stats.process_memory_mb / self.max_memory_mb) * 100
        if memory_percent > self.warning_threshold_percent:
            status["warnings"].append(f"Memory usage ({memory_percent:.1f}%) above warning threshold ({self.warning_threshold_percent}%)")
        
        # Check system memory
        if stats.system_memory_percent > 85.0:
            status["warnings"].append(f"System memory usage high ({stats.system_memory_percent:.1f}%)")
        
        # Auto-cleanup if needed
        if self._should_cleanup():
            gc_count = self.force_garbage_collection()
            status["actions_taken"].append(f"Forced garbage collection ({gc_count} objects collected)")
        
        return status
    
    def _should_cleanup(self) -> bool:
        """Determine if automatic cleanup should run."""
        return datetime.now() - self._last_cleanup > self._cleanup_interval
    
    def force_garbage_collection(self) -> int:
        """Force garbage collection and return number of objects collected."""
        try:
            before_count = len(gc.get_objects())
            collected = gc.collect()
            after_count = len(gc.get_objects())
            
            self._last_cleanup = datetime.now()
            
            logger.info(f"Garbage collection completed: {collected} cycles, {before_count - after_count} objects freed")
            return before_count - after_count
        except Exception as e:
            logger.warning(f"Garbage collection failed: {e}")
            return 0
    
    def get_memory_trends(self, minutes: int = 30) -> Dict[str, Any]:
        """Get memory usage trends for the specified time period."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_stats = [s for s in self._memory_history if s.timestamp >= cutoff_time]
        
        if not recent_stats:
            return {"error": "No recent memory data available"}
        
        memory_values = [s.process_memory_mb for s in recent_stats]
        gc_values = [s.gc_objects_count for s in recent_stats]
        
        return {
            "time_period_minutes": minutes,
            "samples": len(recent_stats),
            "memory_mb": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values),
                "current": memory_values[-1] if memory_values else 0,
                "trend": "increasing" if len(memory_values) > 1 and memory_values[-1] > memory_values[0] else "stable"
            },
            "gc_objects": {
                "min": min(gc_values),
                "max": max(gc_values),
                "avg": sum(gc_values) / len(gc_values),
                "current": gc_values[-1] if gc_values else 0
            }
        }
    
    def clear_history(self):
        """Clear memory usage history."""
        with self._lock:
            self._memory_history.clear()

# Global memory monitor instance
_memory_monitor: Optional[MemoryMonitor] = None

def get_memory_monitor(max_memory_mb: int = 1024) -> MemoryMonitor:
    """Get the global memory monitor instance."""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor(max_memory_mb=max_memory_mb)
    return _memory_monitor

# Memory-aware cache size calculator
def calculate_optimal_cache_size(base_size: int, memory_limit_mb: int = 1024) -> int:
    """Calculate optimal cache size based on available memory."""
    try:
        stats = get_memory_monitor().get_current_memory_usage()
        available_mb = min(stats.available_memory_mb, memory_limit_mb - stats.process_memory_mb)
        
        # Use at most 10% of available memory for caches
        cache_memory_budget = max(10, available_mb * 0.1)  # At least 10MB
        
        # Estimate ~1KB per cache entry average
        optimal_size = int((cache_memory_budget * 1024) / 1)  # 1KB per entry estimate
        
        # Stay within reasonable bounds
        return max(min(optimal_size, base_size * 2), base_size // 2)
    except Exception:
        return base_size  # Fallback to original size

# Memory pressure detection
def is_memory_pressure() -> bool:
    """Check if system is under memory pressure."""
    try:
        monitor = get_memory_monitor()
        stats = monitor.get_current_memory_usage()
        
        # Memory pressure indicators
        return (
            stats.system_memory_percent > 85.0 or  # System memory high
            stats.available_memory_mb < 100.0 or   # Less than 100MB available
            stats.process_memory_mb > monitor.max_memory_mb * 0.9  # Process near limit
        )
    except Exception:
        return False

# Context manager for memory-aware operations
class MemoryAwareContext:
    """Context manager that monitors memory usage during operations."""
    
    def __init__(self, operation_name: str, max_memory_mb: Optional[int] = None):
        self.operation_name = operation_name
        self.max_memory_mb = max_memory_mb
        self.start_stats = None
        self.end_stats = None
        
    def __enter__(self):
        self.start_stats = get_memory_monitor().record_memory_usage()
        logger.debug(f"Starting memory-aware operation: {self.operation_name} "
                    f"(initial memory: {self.start_stats.process_memory_mb:.1f}MB)")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_stats = get_memory_monitor().record_memory_usage()
        memory_delta = self.end_stats.process_memory_mb - self.start_stats.process_memory_mb
        
        logger.debug(f"Completed memory-aware operation: {self.operation_name} "
                    f"(memory delta: {memory_delta:+.1f}MB, final: {self.end_stats.process_memory_mb:.1f}MB)")
        
        if self.max_memory_mb and self.end_stats.process_memory_mb > self.max_memory_mb:
            logger.warning(f"Operation {self.operation_name} exceeded memory limit: "
                         f"{self.end_stats.process_memory_mb:.1f}MB > {self.max_memory_mb}MB")

def memory_aware_operation(operation_name: str, max_memory_mb: Optional[int] = None):
    """Decorator for memory-aware operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with MemoryAwareContext(operation_name, max_memory_mb):
                return func(*args, **kwargs)
        return wrapper
    return decorator