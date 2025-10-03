"""
Sentiment caching service for AlphaVantage API with rate limiting.

AlphaVantage Free Tier Limits:
- 25 API calls per day
- 5 API calls per minute

Strategy:
- Cache sentiment data for 24 hours (SQLite)
- Batch fetch for popular stocks during off-peak
- Graceful fallback to neutral sentiment when quota exhausted
- Track daily API usage to prevent overuse
"""

import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Cache database location
CACHE_DB = Path("data/sentiment_cache.db")
CACHE_DB.parent.mkdir(parents=True, exist_ok=True)

# Thread-safe lock for database access
db_lock = threading.Lock()

# Daily API call limit
MAX_DAILY_CALLS = 25
CACHE_TTL_HOURS = 24


def _get_db_connection():
    """Get thread-safe database connection."""
    conn = sqlite3.connect(str(CACHE_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _init_database():
    """Initialize sentiment cache database."""
    with db_lock:
        conn = _get_db_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_cache (
                    symbol TEXT PRIMARY KEY,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    buzz_score REAL,
                    article_count INTEGER,
                    fetched_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    date TEXT PRIMARY KEY,
                    call_count INTEGER,
                    last_call_at TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Sentiment cache database initialized")
        finally:
            conn.close()


def get_daily_api_usage() -> Dict:
    """Get today's API usage statistics."""
    today = datetime.now().date().isoformat()
    
    with db_lock:
        conn = _get_db_connection()
        try:
            row = conn.execute(
                "SELECT call_count, last_call_at FROM api_usage WHERE date = ?",
                (today,)
            ).fetchone()
            
            if row:
                return {
                    "date": today,
                    "calls_used": row["call_count"],
                    "calls_remaining": MAX_DAILY_CALLS - row["call_count"],
                    "last_call": row["last_call_at"],
                    "quota_exhausted": row["call_count"] >= MAX_DAILY_CALLS
                }
            else:
                return {
                    "date": today,
                    "calls_used": 0,
                    "calls_remaining": MAX_DAILY_CALLS,
                    "last_call": None,
                    "quota_exhausted": False
                }
        finally:
            conn.close()


def increment_api_usage() -> bool:
    """
    Increment API usage counter.
    
    Returns:
        True if call is allowed, False if quota exhausted
    """
    today = datetime.now().date().isoformat()
    now = datetime.now().isoformat()
    
    with db_lock:
        conn = _get_db_connection()
        try:
            # Get current usage
            row = conn.execute(
                "SELECT call_count FROM api_usage WHERE date = ?",
                (today,)
            ).fetchone()
            
            if row:
                current_count = row["call_count"]
                if current_count >= MAX_DAILY_CALLS:
                    logger.warning(f"AlphaVantage API quota exhausted: {current_count}/{MAX_DAILY_CALLS}")
                    return False
                
                # Increment
                conn.execute(
                    "UPDATE api_usage SET call_count = call_count + 1, last_call_at = ? WHERE date = ?",
                    (now, today)
                )
            else:
                # First call today
                conn.execute(
                    "INSERT INTO api_usage (date, call_count, last_call_at) VALUES (?, 1, ?)",
                    (today, now)
                )
            
            conn.commit()
            return True
        finally:
            conn.close()


def get_cached_sentiment(symbol: str) -> Optional[Dict]:
    """
    Get cached sentiment data for a symbol.
    
    Returns:
        Sentiment dict if cache hit and not expired, None otherwise
    """
    with db_lock:
        conn = _get_db_connection()
        try:
            row = conn.execute(
                """
                SELECT sentiment_score, sentiment_label, buzz_score, 
                       article_count, fetched_at, expires_at
                FROM sentiment_cache 
                WHERE symbol = ? AND expires_at > ?
                """,
                (symbol, datetime.now().isoformat())
            ).fetchone()
            
            if row:
                logger.info(f"Cache HIT for {symbol} (age: {row['fetched_at']})")
                return {
                    "symbol": symbol,
                    "sentiment_score": row["sentiment_score"],
                    "sentiment_label": row["sentiment_label"],
                    "buzz_score": row["buzz_score"],
                    "article_count": row["article_count"],
                    "cached": True,
                    "fetched_at": row["fetched_at"]
                }
            else:
                logger.info(f"Cache MISS for {symbol}")
                return None
        finally:
            conn.close()


def save_sentiment_to_cache(symbol: str, sentiment_data: Dict):
    """
    Save sentiment data to cache with TTL.
    
    Args:
        symbol: Stock ticker
        sentiment_data: Dict with sentiment_score, sentiment_label, buzz_score
    """
    now = datetime.now()
    expires_at = now + timedelta(hours=CACHE_TTL_HOURS)
    
    with db_lock:
        conn = _get_db_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO sentiment_cache 
                (symbol, sentiment_score, sentiment_label, buzz_score, 
                 article_count, fetched_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    sentiment_data.get("sentiment_score", 0.0),
                    sentiment_data.get("sentiment_label", "Neutral"),
                    sentiment_data.get("buzz_score", 0.0),
                    sentiment_data.get("article_count", 0),
                    now.isoformat(),
                    expires_at.isoformat()
                )
            )
            conn.commit()
            logger.info(f"Cached sentiment for {symbol} (expires: {expires_at})")
        finally:
            conn.close()


def get_sentiment_with_fallback(symbol: str) -> Dict:
    """
    Get sentiment data with intelligent fallback.
    
    Priority:
    1. Check cache (24h TTL)
    2. Fetch from AlphaVantage if quota available
    3. Fallback to neutral sentiment
    
    Returns:
        Sentiment dict (always returns data, never fails)
    """
    # Try cache first
    cached = get_cached_sentiment(symbol)
    if cached:
        return cached
    
    # Check API quota
    usage = get_daily_api_usage()
    if usage["quota_exhausted"]:
        logger.warning(
            f"AlphaVantage quota exhausted ({usage['calls_used']}/{MAX_DAILY_CALLS}). "
            f"Using neutral sentiment for {symbol}"
        )
        return _get_neutral_sentiment(symbol)
    
    # Try to fetch fresh data
    try:
        from app.services.alphavantage_service import get_news_sentiment
        
        # Increment usage counter
        if not increment_api_usage():
            return _get_neutral_sentiment(symbol)
        
        # Fetch from API
        logger.info(f"Fetching fresh sentiment for {symbol} (quota: {usage['calls_remaining']}/25)")
        response = get_news_sentiment(tickers=[symbol], limit=50)
        
        if "feed" in response and len(response["feed"]) > 0:
            sentiment_data = _parse_sentiment_response(symbol, response)
            save_sentiment_to_cache(symbol, sentiment_data)
            return sentiment_data
        else:
            # API returned no data
            logger.warning(f"No sentiment data from API for {symbol}")
            return _get_neutral_sentiment(symbol)
            
    except Exception as e:
        logger.error(f"Error fetching sentiment for {symbol}: {e}")
        return _get_neutral_sentiment(symbol)


def _parse_sentiment_response(symbol: str, response: Dict) -> Dict:
    """Parse AlphaVantage sentiment response into aggregated metrics."""
    feed = response.get("feed", [])
    
    if not feed:
        return _get_neutral_sentiment(symbol)
    
    # Aggregate sentiment scores
    total_score = 0.0
    total_relevance = 0.0
    sentiment_counts = {"Bearish": 0, "Somewhat-Bearish": 0, "Neutral": 0, 
                       "Somewhat-Bullish": 0, "Bullish": 0}
    
    for article in feed:
        # Find ticker sentiment in article
        for ticker_sentiment in article.get("ticker_sentiment", []):
            if ticker_sentiment.get("ticker") == symbol:
                score = float(ticker_sentiment.get("ticker_sentiment_score", 0))
                relevance = float(ticker_sentiment.get("relevance_score", 0))
                label = ticker_sentiment.get("ticker_sentiment_label", "Neutral")
                
                # Weighted average by relevance
                total_score += score * relevance
                total_relevance += relevance
                sentiment_counts[label] = sentiment_counts.get(label, 0) + 1
    
    # Calculate aggregated metrics
    avg_sentiment = total_score / total_relevance if total_relevance > 0 else 0.0
    
    # Determine overall label
    max_label = max(sentiment_counts, key=sentiment_counts.get)
    
    # Calculate buzz score (article count normalized)
    buzz_score = min(len(feed) / 50.0, 1.0)  # Normalize to 0-1
    
    return {
        "symbol": symbol,
        "sentiment_score": round(avg_sentiment, 4),
        "sentiment_label": max_label,
        "buzz_score": round(buzz_score, 4),
        "article_count": len(feed),
        "cached": False,
        "fetched_at": datetime.now().isoformat()
    }


def _get_neutral_sentiment(symbol: str) -> Dict:
    """Return neutral sentiment as fallback."""
    return {
        "symbol": symbol,
        "sentiment_score": 0.0,
        "sentiment_label": "Neutral",
        "buzz_score": 0.0,
        "article_count": 0,
        "cached": False,
        "fallback": True
    }


def cleanup_expired_cache():
    """Remove expired cache entries."""
    with db_lock:
        conn = _get_db_connection()
        try:
            result = conn.execute(
                "DELETE FROM sentiment_cache WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            deleted = result.rowcount
            conn.commit()
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired sentiment cache entries")
        finally:
            conn.close()


def get_cache_statistics() -> Dict:
    """Get cache statistics for monitoring."""
    with db_lock:
        conn = _get_db_connection()
        try:
            # Count valid cache entries
            valid_count = conn.execute(
                "SELECT COUNT(*) as count FROM sentiment_cache WHERE expires_at > ?",
                (datetime.now().isoformat(),)
            ).fetchone()["count"]
            
            # Count expired
            expired_count = conn.execute(
                "SELECT COUNT(*) as count FROM sentiment_cache WHERE expires_at <= ?",
                (datetime.now().isoformat(),)
            ).fetchone()["count"]
            
            # Get API usage
            usage = get_daily_api_usage()
            
            return {
                "cache": {
                    "valid_entries": valid_count,
                    "expired_entries": expired_count,
                    "ttl_hours": CACHE_TTL_HOURS
                },
                "api": {
                    "daily_limit": MAX_DAILY_CALLS,
                    "used_today": usage["calls_used"],
                    "remaining_today": usage["calls_remaining"],
                    "quota_exhausted": usage["quota_exhausted"]
                }
            }
        finally:
            conn.close()


# Initialize database on module import
_init_database()


if __name__ == "__main__":
    # Test the caching system
    print("=== Sentiment Cache Service Test ===\n")
    
    # Get statistics
    stats = get_cache_statistics()
    print("Cache Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Test sentiment fetch
    print("\nTesting sentiment fetch for AAPL:")
    sentiment = get_sentiment_with_fallback("AAPL")
    print(json.dumps(sentiment, indent=2))
    
    # Test cache hit
    print("\nTesting cache hit (should be instant):")
    sentiment2 = get_sentiment_with_fallback("AAPL")
    print(json.dumps(sentiment2, indent=2))
