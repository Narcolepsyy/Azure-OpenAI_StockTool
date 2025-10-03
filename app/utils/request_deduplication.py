"""Request deduplication system to prevent concurrent identical operations."""
import asyncio
import hashlib
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, Awaitable, Union, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RequestStatus(Enum):
    """Status of a deduplicated request."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class RequestInfo:
    """Information about a pending or completed request."""
    key: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RequestStatus = RequestStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    request_count: int = 1
    
    @property
    def duration_ms(self) -> Optional[int]:
        """Get request duration in milliseconds."""
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "request_count": self.request_count,
            "has_error": self.error is not None,
            "error_message": str(self.error) if self.error else None,
        }

class DeduplicationManager:
    """Manages request deduplication across the application."""
    
    def __init__(self, cleanup_interval: int = 300):  # 5 minutes
        """Initialize the deduplication manager.
        
        Args:
            cleanup_interval: How often to clean up completed requests (seconds)
        """
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_info: Dict[str, RequestInfo] = {}
        self._lock = asyncio.Lock()
        self._thread_lock = threading.RLock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        self._stats = {
            "total_requests": 0,
            "deduplicated_requests": 0,
            "active_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
        }
    
    def _generate_key(self, operation: str, **kwargs) -> str:
        """Generate a unique key for the request."""
        # Create a stable key from operation and parameters
        key_data = {"operation": operation, **kwargs}
        
        # Sort keys for consistency
        sorted_data = json.dumps(key_data, sort_keys=True, default=str)
        
        # Hash for fixed-length key
        return f"{operation}:{hashlib.sha256(sorted_data.encode()).hexdigest()[:16]}"
    
    def _cleanup_completed_requests(self) -> None:
        """Clean up old completed requests."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = datetime.now() - timedelta(seconds=self._cleanup_interval)
        
        # Find requests to clean up
        keys_to_remove = []
        for key, info in self._request_info.items():
            if (info.status != RequestStatus.PENDING and 
                info.completed_at and 
                info.completed_at < cutoff_time):
                keys_to_remove.append(key)
        
        # Remove old requests
        for key in keys_to_remove:
            self._request_info.pop(key, None)
            self._pending_requests.pop(key, None)
        
        self._last_cleanup = current_time
        
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} old requests")
    
    async def deduplicate_async(
        self, 
        operation: str,
        async_func: Callable[[], Awaitable[T]],
        **kwargs
    ) -> T:
        """Deduplicate an async operation.
        
        Args:
            operation: Name of the operation (e.g., 'web_search', 'stock_quote')
            async_func: The async function to execute
            **kwargs: Parameters used for generating the deduplication key
            
        Returns:
            The result of the operation
        """
        key = self._generate_key(operation, **kwargs)
        
        async with self._lock:
            # Clean up old requests periodically
            self._cleanup_completed_requests()
            
            # Check if request is already pending
            if key in self._pending_requests:
                existing_future = self._pending_requests[key]
                if existing_future and not existing_future.done():
                    # Increment request count
                    if key in self._request_info:
                        self._request_info[key].request_count += 1
                    
                    self._stats["deduplicated_requests"] += 1
                    logger.debug(f"Deduplicating request: {operation} (key: {key[:8]}...)")
                    
                    # Wait for the existing request to complete
                    return await existing_future
            
            # Create new request
            future = asyncio.Future()
            self._pending_requests[key] = future
            
            request_info = RequestInfo(
                key=key,
                started_at=datetime.now()
            )
            self._request_info[key] = request_info
            
            self._stats["total_requests"] += 1
            self._stats["active_requests"] = len(self._pending_requests)
        
        # Execute the function outside the lock
        try:
            logger.debug(f"Executing new request: {operation} (key: {key[:8]}...)")
            result = await async_func()
            
            # Update request info
            request_info.status = RequestStatus.COMPLETED
            request_info.completed_at = datetime.now()
            request_info.result = result
            
            # Complete the future
            if not future.done():
                future.set_result(result)
            
            self._stats["completed_requests"] += 1
            logger.debug(f"Completed request: {operation} in {request_info.duration_ms}ms")
            
            return result
            
        except Exception as e:
            # Update request info
            request_info.status = RequestStatus.FAILED
            request_info.completed_at = datetime.now()
            request_info.error = e
            
            # Fail the future
            if not future.done():
                future.set_exception(e)
            
            self._stats["failed_requests"] += 1
            logger.warning(f"Failed request: {operation} after {request_info.duration_ms}ms: {e}")
            
            raise
        
        finally:
            # Clean up the pending request
            async with self._lock:
                self._pending_requests.pop(key, None)
                self._stats["active_requests"] = len(self._pending_requests)
    
    def deduplicate_sync(
        self, 
        operation: str,
        func: Callable[[], T],
        **kwargs
    ) -> T:
        """Deduplicate a synchronous operation using thread-based deduplication.
        
        Args:
            operation: Name of the operation
            func: The function to execute
            **kwargs: Parameters used for generating the deduplication key
            
        Returns:
            The result of the operation
        """
        key = self._generate_key(operation, **kwargs)
        
        with self._thread_lock:
            # Clean up old requests
            self._cleanup_completed_requests()
            
            # Check if we have a recent completed request
            if key in self._request_info:
                info = self._request_info[key]
                if (info.status == RequestStatus.COMPLETED and 
                    info.completed_at and
                    datetime.now() - info.completed_at < timedelta(seconds=60)):  # 1 minute
                    
                    info.request_count += 1
                    self._stats["deduplicated_requests"] += 1
                    logger.debug(f"Using cached result for: {operation} (key: {key[:8]}...)")
                    return info.result
            
            # Execute new request
            request_info = RequestInfo(
                key=key,
                started_at=datetime.now()
            )
            self._request_info[key] = request_info
            self._stats["total_requests"] += 1
        
        try:
            logger.debug(f"Executing sync request: {operation} (key: {key[:8]}...)")
            result = func()
            
            # Update request info
            request_info.status = RequestStatus.COMPLETED
            request_info.completed_at = datetime.now()
            request_info.result = result
            
            self._stats["completed_requests"] += 1
            logger.debug(f"Completed sync request: {operation} in {request_info.duration_ms}ms")
            
            return result
            
        except Exception as e:
            # Update request info
            request_info.status = RequestStatus.FAILED
            request_info.completed_at = datetime.now()
            request_info.error = e
            
            self._stats["failed_requests"] += 1
            logger.warning(f"Failed sync request: {operation} after {request_info.duration_ms}ms: {e}")
            
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        with self._thread_lock:
            total = self._stats["total_requests"]
            deduplication_rate = (self._stats["deduplicated_requests"] / total) if total > 0 else 0.0
            
            return {
                **self._stats,
                "deduplication_rate": deduplication_rate,
                "pending_requests": len(self._pending_requests),
                "tracked_requests": len(self._request_info),
                "last_cleanup": self._last_cleanup,
            }
    
    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active requests."""
        with self._thread_lock:
            return {
                key: info.to_dict()
                for key, info in self._request_info.items()
                if info.status == RequestStatus.PENDING
            }
    
    def get_recent_requests(self, limit: int = 50) -> Dict[str, Dict[str, Any]]:
        """Get information about recent requests."""
        with self._thread_lock:
            # Sort by start time (most recent first)
            sorted_requests = sorted(
                self._request_info.items(),
                key=lambda x: x[1].started_at,
                reverse=True
            )
            
            return {
                key: info.to_dict()
                for key, info in sorted_requests[:limit]
            }
    
    def clear_completed(self) -> int:
        """Clear all completed requests and return the count."""
        with self._thread_lock:
            keys_to_remove = [
                key for key, info in self._request_info.items()
                if info.status != RequestStatus.PENDING
            ]
            
            for key in keys_to_remove:
                self._request_info.pop(key, None)
                self._pending_requests.pop(key, None)
            
            logger.info(f"Cleared {len(keys_to_remove)} completed requests")
            return len(keys_to_remove)

# Global deduplication manager instance
_deduplication_manager: Optional[DeduplicationManager] = None
_dedup_lock = threading.Lock()

def get_deduplication_manager() -> DeduplicationManager:
    """Get the global deduplication manager instance."""
    global _deduplication_manager
    
    if _deduplication_manager is None:
        with _dedup_lock:
            if _deduplication_manager is None:
                _deduplication_manager = DeduplicationManager()
    
    return _deduplication_manager

def reset_deduplication_manager() -> None:
    """Reset the global deduplication manager (for testing)."""
    global _deduplication_manager
    with _dedup_lock:
        _deduplication_manager = None

# Convenience decorators
def deduplicate_async(operation: str, **key_kwargs):
    """Decorator for async function deduplication."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs):
            # Combine key_kwargs with function kwargs for deduplication key
            dedup_kwargs = {**key_kwargs, **kwargs}
            
            async def execute():
                return await func(*args, **kwargs)
            
            return await get_deduplication_manager().deduplicate_async(
                operation=operation,
                async_func=execute,
                **dedup_kwargs
            )
        
        return wrapper
    return decorator

def deduplicate_sync(operation: str, **key_kwargs):
    """Decorator for sync function deduplication."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs):
            # Combine key_kwargs with function kwargs for deduplication key
            dedup_kwargs = {**key_kwargs, **kwargs}
            
            def execute():
                return func(*args, **kwargs)
            
            return get_deduplication_manager().deduplicate_sync(
                operation=operation,
                func=execute,
                **dedup_kwargs
            )
        
        return wrapper
    return decorator