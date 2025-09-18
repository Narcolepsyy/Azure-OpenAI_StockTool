"""Response caching service for performance optimization."""
import hashlib
import logging
import re
from typing import Optional, Dict, Any, Tuple
from cachetools import TTLCache
from app.core.config import (
    ENABLE_RESPONSE_CACHE, RESPONSE_CACHE_TTL, SIMPLE_QUERY_CACHE_TTL,
    SIMPLE_QUERY_PATTERNS, FAST_MODEL_FOR_SIMPLE
)

logger = logging.getLogger(__name__)

# Response caches with different TTLs
_response_cache = TTLCache(maxsize=1000, ttl=RESPONSE_CACHE_TTL)
_simple_query_cache = TTLCache(maxsize=500, ttl=SIMPLE_QUERY_CACHE_TTL)

def _normalize_query(query: str) -> str:
    """Normalize query for cache key generation."""
    # Convert to lowercase, remove extra whitespace, normalize punctuation
    normalized = re.sub(r'\s+', ' ', query.lower().strip())
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
    return normalized

def _generate_cache_key(query: str, model: str, context_hash: Optional[str] = None) -> str:
    """Generate cache key for query."""
    normalized_query = _normalize_query(query)
    key_data = f"{normalized_query}|{model}"
    if context_hash:
        key_data += f"|{context_hash}"
    return hashlib.md5(key_data.encode()).hexdigest()

def _hash_context(messages: list) -> str:
    """Generate hash for conversation context."""
    # Only include recent system and user messages for context
    relevant_messages = []
    for msg in messages[-5:]:  # Last 5 messages only
        if msg.get("role") in {"system", "user"}:
            content = msg.get("content", "")[:200]  # First 200 chars
            relevant_messages.append(f"{msg['role']}:{content}")
    
    context_str = "|".join(relevant_messages)
    return hashlib.md5(context_str.encode()).hexdigest()[:8]

def is_simple_query(query: str) -> bool:
    """Check if query matches simple patterns that don't need complex processing."""
    # Guard: any news-like query should not be treated as simple
    try:
        ql = (query or "").lower()
        if any(k in ql for k in ("news", "headline", "headlines", "article", "articles")):
            return False
    except Exception:
        pass

    if not SIMPLE_QUERY_PATTERNS:
        return False
    
    for pattern in SIMPLE_QUERY_PATTERNS:
        if re.match(pattern, (query or "").strip()):
            return True
    return False

def is_stock_price_query(query: str) -> bool:
    """Detect stock price queries for fast processing."""
    patterns = [
        r'(?i).*(price|quote|trading|current).*\b([A-Z]{1,5})\b',
        r'(?i)\b([A-Z]{1,5})\b.*(price|quote|stock)',
        r'(?i)what.*(price|cost|trading).*(stock|share)',
    ]
    for pattern in patterns:
        if re.search(pattern, query):
            return True
    return False

def _is_news_like(query: str) -> bool:
    try:
        ql = (query or "").lower()
        return any(k in ql for k in ("news", "headline", "headlines", "article", "articles"))
    except Exception:
        return False

def get_cached_response(query: str, model: str, messages: list = None) -> Optional[Dict[str, Any]]:
    """Get cached response if available."""
    if not ENABLE_RESPONSE_CACHE:
        return None

    # Never serve cached responses for news-like prompts to avoid staleness
    if _is_news_like(query):
        return None

    try:
        # Check if it's a simple query first
        if is_simple_query(query):
            simple_key = _generate_cache_key(query, FAST_MODEL_FOR_SIMPLE)
            cached = _simple_query_cache.get(simple_key)
            if cached:
                logger.info(f"Cache hit for simple query: {query[:50]}...")
                return cached
        
        # Check regular cache with context
        context_hash = _hash_context(messages) if messages else None
        cache_key = _generate_cache_key(query, model, context_hash)
        cached = _response_cache.get(cache_key)
        
        if cached:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return cached
            
    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")
    
    return None

def cache_response(query: str, model: str, response: Dict[str, Any], messages: list = None):
    """Cache response for future use."""
    if not ENABLE_RESPONSE_CACHE:
        return

    # Skip caching for news-like prompts to keep content fresh
    if _is_news_like(query):
        return

    try:
        # Cache simple queries separately with longer TTL
        if is_simple_query(query):
            simple_key = _generate_cache_key(query, FAST_MODEL_FOR_SIMPLE)
            _simple_query_cache[simple_key] = response
            logger.debug(f"Cached simple query response: {query[:50]}...")
        
        # Cache regular response
        context_hash = _hash_context(messages) if messages else None
        cache_key = _generate_cache_key(query, model, context_hash)
        _response_cache[cache_key] = response
        logger.debug(f"Cached response: {query[:50]}...")
        
    except Exception as e:
        logger.warning(f"Cache storage failed: {e}")

def should_use_fast_model(query: str) -> Tuple[bool, str]:
    """Determine if query should use fast model for better performance."""
    if is_simple_query(query) or is_stock_price_query(query):
        return True, FAST_MODEL_FOR_SIMPLE
    return False, ""

def clear_cache():
    """Clear all caches."""
    _response_cache.clear()
    _simple_query_cache.clear()
    logger.info("Response caches cleared")

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return {
        "response_cache": {
            "size": len(_response_cache),
            "maxsize": _response_cache.maxsize,
            "ttl": _response_cache.ttl
        },
        "simple_query_cache": {
            "size": len(_simple_query_cache),
            "maxsize": _simple_query_cache.maxsize,
            "ttl": _simple_query_cache.ttl
        }
    }
