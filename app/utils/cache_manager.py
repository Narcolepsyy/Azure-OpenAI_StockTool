"""Centralized cache management system for the application."""
import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from cachetools import TTLCache
import json

logger = logging.getLogger(__name__)

class CacheType(Enum):
    """Types of caches available."""
    WEB_SEARCH = "web_search"
    STOCK_QUOTES = "stock_quotes"
    STOCK_NEWS = "stock_news"
    ARTICLE_CONTENT = "article_content"
    RAG_EMBEDDINGS = "rag_embeddings"
    USER_SESSIONS = "user_sessions"

@dataclass
class CacheConfig:
    """Configuration for a cache instance."""
    cache_type: CacheType
    max_size: int
    ttl_seconds: int
    enable_stats: bool = True
    description: str = ""

@dataclass
class CacheStats:
    """Statistics for a cache instance."""
    cache_type: CacheType
    max_size: int
    current_size: int
    ttl_seconds: int
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_access: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0
    
    @property
    def usage_percent(self) -> float:
        """Calculate cache usage percentage."""
        return (self.current_size / self.max_size) * 100 if self.max_size > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "cache_type": self.cache_type.value,
            "max_size": self.max_size,
            "current_size": self.current_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "usage_percent": self.usage_percent,
            "created_at": self.created_at.isoformat(),
            "last_access": self.last_access.isoformat() if self.last_access else None,
        }

class ThreadSafeCache:
    """Thread-safe wrapper for TTLCache with statistics."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache = TTLCache(maxsize=config.max_size, ttl=config.ttl_seconds)
        self._lock = threading.RLock()
        self._stats = CacheStats(
            cache_type=config.cache_type,
            max_size=config.max_size,
            current_size=0,
            ttl_seconds=config.ttl_seconds
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            try:
                value = self._cache[key]
                if self.config.enable_stats:
                    self._stats.hits += 1
                    self._stats.last_access = datetime.now()
                return value
            except KeyError:
                if self.config.enable_stats:
                    self._stats.misses += 1
                    self._stats.last_access = datetime.now()
                return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        with self._lock:
            old_size = len(self._cache)
            self._cache[key] = value
            new_size = len(self._cache)
            
            if self.config.enable_stats:
                self._stats.sets += 1
                self._stats.current_size = new_size
                self._stats.last_access = datetime.now()
                
                # Track evictions (size decreased after adding)
                if new_size < old_size + 1:
                    self._stats.evictions += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            try:
                del self._cache[key]
                if self.config.enable_stats:
                    self._stats.deletes += 1
                    self._stats.current_size = len(self._cache)
                    self._stats.last_access = datetime.now()
                return True
            except KeyError:
                return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            if self.config.enable_stats:
                self._stats.current_size = 0
                self._stats.last_access = datetime.now()
    
    def contains(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            return key in self._cache
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def keys(self) -> list:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            # Update current size
            self._stats.current_size = len(self._cache)
            return self._stats

class CentralizedCacheManager:
    """Centralized cache manager for the entire application."""
    
    def __init__(self):
        self._caches: Dict[CacheType, ThreadSafeCache] = {}
        self._lock = threading.RLock()
        self._initialized = False
    
    def initialize_default_caches(self) -> None:
        """Initialize default caches with standard configurations."""
        default_configs = [
            CacheConfig(
                cache_type=CacheType.WEB_SEARCH,
                max_size=200,
                ttl_seconds=1800,  # 30 minutes
                description="Web search results cache"
            ),
            CacheConfig(
                cache_type=CacheType.STOCK_QUOTES,
                max_size=500,
                ttl_seconds=300,  # 5 minutes
                description="Stock quote data cache"
            ),
            CacheConfig(
                cache_type=CacheType.STOCK_NEWS,
                max_size=300,
                ttl_seconds=900,  # 15 minutes
                description="Stock news articles cache"
            ),
            CacheConfig(
                cache_type=CacheType.ARTICLE_CONTENT,
                max_size=100,
                ttl_seconds=3600,  # 1 hour
                description="Full article content cache"
            ),
            CacheConfig(
                cache_type=CacheType.RAG_EMBEDDINGS,
                max_size=1000,
                ttl_seconds=7200,  # 2 hours
                description="RAG embeddings and search results cache"
            ),
            CacheConfig(
                cache_type=CacheType.USER_SESSIONS,
                max_size=1000,
                ttl_seconds=1800,  # 30 minutes
                description="User session data cache"
            ),
        ]
        
        for config in default_configs:
            self.add_cache(config)
        
        self._initialized = True
        logger.info(f"Initialized {len(self._caches)} default caches")
    
    def add_cache(self, config: CacheConfig) -> None:
        """Add a new cache instance."""
        with self._lock:
            if config.cache_type in self._caches:
                logger.warning(f"Cache {config.cache_type.value} already exists, replacing")
            
            self._caches[config.cache_type] = ThreadSafeCache(config)
            logger.info(
                f"Added cache {config.cache_type.value}: "
                f"size={config.max_size}, ttl={config.ttl_seconds}s"
            )
    
    def get_cache(self, cache_type: CacheType) -> Optional[ThreadSafeCache]:
        """Get a cache instance by type."""
        return self._caches.get(cache_type)
    
    def get(self, cache_type: CacheType, key: str) -> Optional[Any]:
        """Get value from a specific cache."""
        cache = self.get_cache(cache_type)
        if cache:
            return cache.get(key)
        return None
    
    def set(self, cache_type: CacheType, key: str, value: Any) -> bool:
        """Set value in a specific cache."""
        cache = self.get_cache(cache_type)
        if cache:
            cache.set(key, value)
            return True
        return False
    
    def delete(self, cache_type: CacheType, key: str) -> bool:
        """Delete key from a specific cache."""
        cache = self.get_cache(cache_type)
        if cache:
            return cache.delete(key)
        return False
    
    def clear_cache(self, cache_type: CacheType) -> bool:
        """Clear a specific cache."""
        cache = self.get_cache(cache_type)
        if cache:
            cache.clear()
            logger.info(f"Cleared cache: {cache_type.value}")
            return True
        return False
    
    def clear_all_caches(self) -> None:
        """Clear all caches."""
        with self._lock:
            for cache_type, cache in self._caches.items():
                cache.clear()
            logger.info("Cleared all caches")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        with self._lock:
            return {
                cache_type.value: cache.get_stats().to_dict()
                for cache_type, cache in self._caches.items()
            }
    
    def get_cache_stats(self, cache_type: CacheType) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific cache."""
        cache = self.get_cache(cache_type)
        if cache:
            return cache.get_stats().to_dict()
        return None
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics across all caches."""
        with self._lock:
            total_size = 0
            total_max_size = 0
            total_hits = 0
            total_misses = 0
            total_sets = 0
            
            for cache in self._caches.values():
                stats = cache.get_stats()
                total_size += stats.current_size
                total_max_size += stats.max_size
                total_hits += stats.hits
                total_misses += stats.misses
                total_sets += stats.sets
            
            total_requests = total_hits + total_misses
            overall_hit_rate = (total_hits / total_requests) if total_requests > 0 else 0.0
            
            return {
                "total_caches": len(self._caches),
                "total_size": total_size,
                "total_max_size": total_max_size,
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_sets": total_sets,
                "overall_hit_rate": overall_hit_rate,
                "usage_percent": (total_size / total_max_size * 100) if total_max_size > 0 else 0.0,
                "initialized": self._initialized,
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all caches."""
        with self._lock:
            healthy_caches = 0
            total_caches = len(self._caches)
            
            issues = []
            
            for cache_type, cache in self._caches.items():
                try:
                    # Test basic operations
                    test_key = f"__health_check__{int(time.time())}"
                    cache.set(test_key, "test_value")
                    retrieved = cache.get(test_key)
                    cache.delete(test_key)
                    
                    if retrieved == "test_value":
                        healthy_caches += 1
                    else:
                        issues.append(f"Cache {cache_type.value}: failed retrieval test")
                        
                except Exception as e:
                    issues.append(f"Cache {cache_type.value}: {str(e)}")
            
            is_healthy = healthy_caches == total_caches
            
            return {
                "healthy": is_healthy,
                "healthy_caches": healthy_caches,
                "total_caches": total_caches,
                "issues": issues,
                "timestamp": datetime.now().isoformat(),
            }

# Global cache manager instance
_cache_manager: Optional[CentralizedCacheManager] = None
_manager_lock = threading.Lock()

def get_cache_manager() -> CentralizedCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        with _manager_lock:
            if _cache_manager is None:
                _cache_manager = CentralizedCacheManager()
                _cache_manager.initialize_default_caches()
    
    return _cache_manager

def reset_cache_manager() -> None:
    """Reset the global cache manager (for testing)."""
    global _cache_manager
    with _manager_lock:
        _cache_manager = None