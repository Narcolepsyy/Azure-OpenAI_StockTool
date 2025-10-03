"""Request deduplication cache for performance optimization."""
import hashlib
import time
from typing import Any, Optional, Dict
from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

# Cache for identical requests within a short time window (30 seconds)
# This prevents multiple users from making redundant API calls for trending queries
_REQUEST_CACHE: TTLCache = TTLCache(maxsize=500, ttl=30)

# Track in-flight requests to prevent duplicate processing
_IN_FLIGHT: Dict[str, float] = {}


def compute_request_hash(prompt: str, model: str, system_prompt: str = "") -> str:
    """
    Compute a hash for request deduplication.
    
    Args:
        prompt: User's input prompt
        model: Model being used
        system_prompt: System prompt if any
    
    Returns:
        16-character hex hash
    """
    content = f"{prompt.strip().lower()}:{model}:{system_prompt.strip()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def get_cached_response(prompt: str, model: str, system_prompt: str = "") -> Optional[Dict[str, Any]]:
    """
    Get cached response for identical request if available.
    
    Args:
        prompt: User's input prompt
        model: Model being used
        system_prompt: System prompt if any
    
    Returns:
        Cached response dict or None
    """
    try:
        cache_key = compute_request_hash(prompt, model, system_prompt)
        cached = _REQUEST_CACHE.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for request hash {cache_key}")
            return cached
        logger.debug(f"Cache MISS for request hash {cache_key}")
        return None
    except Exception as e:
        logger.warning(f"Failed to get cached response: {e}")
        return None


def cache_response(prompt: str, model: str, system_prompt: str, response: Dict[str, Any]) -> None:
    """
    Cache a response for future identical requests.
    
    Args:
        prompt: User's input prompt
        model: Model being used
        system_prompt: System prompt if any
        response: Response dict to cache
    """
    try:
        cache_key = compute_request_hash(prompt, model, system_prompt)
        _REQUEST_CACHE[cache_key] = response
        logger.debug(f"Cached response for hash {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache response: {e}")


def is_request_in_flight(prompt: str, model: str, system_prompt: str = "") -> bool:
    """
    Check if an identical request is currently being processed.
    
    Args:
        prompt: User's input prompt
        model: Model being used
        system_prompt: System prompt if any
    
    Returns:
        True if request is in-flight, False otherwise
    """
    try:
        cache_key = compute_request_hash(prompt, model, system_prompt)
        if cache_key in _IN_FLIGHT:
            # Check if the in-flight request is stale (> 60 seconds)
            if time.time() - _IN_FLIGHT[cache_key] < 60:
                return True
            else:
                # Remove stale entry
                del _IN_FLIGHT[cache_key]
        return False
    except Exception as e:
        logger.warning(f"Failed to check in-flight status: {e}")
        return False


def mark_request_in_flight(prompt: str, model: str, system_prompt: str = "") -> None:
    """
    Mark a request as being processed.
    
    Args:
        prompt: User's input prompt
        model: Model being used
        system_prompt: System prompt if any
    """
    try:
        cache_key = compute_request_hash(prompt, model, system_prompt)
        _IN_FLIGHT[cache_key] = time.time()
    except Exception as e:
        logger.warning(f"Failed to mark request in-flight: {e}")


def clear_request_in_flight(prompt: str, model: str, system_prompt: str = "") -> None:
    """
    Clear in-flight marker for a request.
    
    Args:
        prompt: User's input prompt
        model: Model being used
        system_prompt: System prompt if any
    """
    try:
        cache_key = compute_request_hash(prompt, model, system_prompt)
        _IN_FLIGHT.pop(cache_key, None)
    except Exception as e:
        logger.warning(f"Failed to clear in-flight marker: {e}")


def clear_caches() -> None:
    """Clear all caches. Useful for testing or manual cache invalidation."""
    _REQUEST_CACHE.clear()
    _IN_FLIGHT.clear()
    logger.info("Request caches cleared")
