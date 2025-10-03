"""
Finnhub real-time stock data service with WebSocket support.
Free tier allows up to 60 API calls/minute and WebSocket connections.
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import finnhub

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute  # seconds between calls
        self.last_call_time = 0
        self.call_count = 0
        self.reset_time = time.time() + 60
    
    def wait_if_needed(self):
        """Block if necessary to respect rate limit."""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time >= self.reset_time:
            self.call_count = 0
            self.reset_time = current_time + 60
        
        # Check if we've hit the limit
        if self.call_count >= self.calls_per_minute:
            wait_time = self.reset_time - current_time
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.call_count = 0
                self.reset_time = time.time() + 60
        
        # Ensure minimum interval between calls
        time_since_last = current_time - self.last_call_time
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
        self.call_count += 1


class FinnhubService:
    """Service for Finnhub real-time stock data."""
    
    def __init__(self, api_key: str):
        """Initialize Finnhub client."""
        if not api_key:
            raise ValueError("Finnhub API key is required")
        
        self.api_key = api_key
        self.client = finnhub.Client(api_key=api_key)
        # Rate limiter: 60 calls/min = 1 call/sec, use 55 to be safe
        self.rate_limiter = RateLimiter(calls_per_minute=55)
        logger.info("Finnhub service initialized with rate limiting (55 calls/min)")
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current quote for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            Dict with current price, change, percent change, high, low, open, previous close
        """
        try:
            # Wait if needed to respect rate limit
            self.rate_limiter.wait_if_needed()
            
            quote = self.client.quote(symbol.upper())
            
            # Finnhub returns: c (current), h (high), l (low), o (open), pc (previous close)
            # d (change), dp (percent change), t (timestamp)
            return {
                "symbol": symbol.upper(),
                "current_price": quote.get("c"),
                "change": quote.get("d"),
                "percent_change": quote.get("dp"),
                "high": quote.get("h"),
                "low": quote.get("l"),
                "open": quote.get("o"),
                "previous_close": quote.get("pc"),
                "timestamp": quote.get("t"),
                "datetime": datetime.fromtimestamp(quote.get("t", 0)).isoformat() if quote.get("t") else None,
                "source": "finnhub"
            }
        except finnhub.FinnhubAPIException as e:
            if e.status_code == 429:
                logger.error(f"Rate limit exceeded for {symbol}. Waiting before retry...")
                # Return cached/error state instead of crashing
                return {
                    "symbol": symbol.upper(),
                    "error": "Rate limit exceeded. Please wait...",
                    "rate_limited": True,
                    "source": "finnhub"
                }
            logger.error(f"Finnhub API error fetching quote for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "error": str(e),
                "source": "finnhub"
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "error": str(e),
                "source": "finnhub"
            }
    
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """
        Get company profile information.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dict with company details (name, industry, market cap, etc.)
        """
        try:
            profile = self.client.company_profile2(symbol=symbol.upper())
            return {
                "symbol": symbol.upper(),
                "name": profile.get("name"),
                "country": profile.get("country"),
                "currency": profile.get("currency"),
                "exchange": profile.get("exchange"),
                "industry": profile.get("finnhubIndustry"),
                "ipo_date": profile.get("ipo"),
                "market_cap": profile.get("marketCapitalization"),
                "shares_outstanding": profile.get("shareOutstanding"),
                "logo": profile.get("logo"),
                "phone": profile.get("phone"),
                "weburl": profile.get("weburl"),
                "source": "finnhub"
            }
        except Exception as e:
            logger.error(f"Error fetching company profile for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "error": str(e),
                "source": "finnhub"
            }
    
    def get_company_news(self, symbol: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """
        Get company news articles.
        
        Args:
            symbol: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            List of news articles
        """
        try:
            news = self.client.company_news(symbol.upper(), _from=from_date, to=to_date)
            return [{
                "headline": article.get("headline"),
                "summary": article.get("summary"),
                "source": article.get("source"),
                "url": article.get("url"),
                "datetime": datetime.fromtimestamp(article.get("datetime", 0)).isoformat() if article.get("datetime") else None,
                "category": article.get("category"),
                "image": article.get("image")
            } for article in news]
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []
    
    def get_recommendation_trends(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get analyst recommendation trends.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            List of recommendation trends by period
        """
        try:
            trends = self.client.recommendation_trends(symbol.upper())
            return trends
        except Exception as e:
            logger.error(f"Error fetching recommendation trends for {symbol}: {e}")
            return []
    
    def get_price_target(self, symbol: str) -> Dict[str, Any]:
        """
        Get analyst price targets.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dict with target high, low, average, median
        """
        try:
            target = self.client.price_target(symbol.upper())
            return {
                "symbol": symbol.upper(),
                "target_high": target.get("targetHigh"),
                "target_low": target.get("targetLow"),
                "target_mean": target.get("targetMean"),
                "target_median": target.get("targetMedian"),
                "last_updated": target.get("lastUpdated"),
                "source": "finnhub"
            }
        except Exception as e:
            logger.error(f"Error fetching price target for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "error": str(e),
                "source": "finnhub"
            }
    
    def search_symbol(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for symbols.
        
        Args:
            query: Search query (company name or ticker)
            
        Returns:
            List of matching symbols
        """
        try:
            results = self.client.symbol_lookup(query)
            return [{
                "symbol": r.get("symbol"),
                "description": r.get("description"),
                "type": r.get("type"),
                "displaySymbol": r.get("displaySymbol")
            } for r in results.get("result", [])]
        except Exception as e:
            logger.error(f"Error searching symbols for {query}: {e}")
            return []


# Global instance (will be initialized on first use)
_finnhub_service: Optional[FinnhubService] = None


def get_finnhub_service(api_key: str) -> FinnhubService:
    """Get or create Finnhub service instance."""
    global _finnhub_service
    if _finnhub_service is None:
        _finnhub_service = FinnhubService(api_key)
    return _finnhub_service


def get_finnhub_quote(symbol: str, api_key: str) -> Dict[str, Any]:
    """Convenience function to get a quote."""
    service = get_finnhub_service(api_key)
    return service.get_quote(symbol)


def get_finnhub_company_profile(symbol: str, api_key: str) -> Dict[str, Any]:
    """Convenience function to get company profile."""
    service = get_finnhub_service(api_key)
    return service.get_company_profile(symbol)


def search_finnhub_symbols(query: str, api_key: str) -> List[Dict[str, Any]]:
    """Convenience function to search symbols."""
    service = get_finnhub_service(api_key)
    return service.search_symbol(query)
