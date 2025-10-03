"""
Alpha Vantage API service for news and market data.
Free tier: 25 requests per day
"""

import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


def get_news_sentiment(
    tickers: Optional[List[str]] = None,
    topics: Optional[str] = None,
    limit: int = 10
) -> Dict:
    """
    Get news and sentiment data from Alpha Vantage.
    
    Args:
        tickers: List of ticker symbols (e.g., ['7203.T', '6758.T'] for Japanese stocks)
        topics: Topics to filter (e.g., 'technology', 'earnings')
        limit: Number of articles to return (default: 10)
    
    Returns:
        Dict with news articles and sentiment data
    """
    if not ALPHA_VANTAGE_API_KEY:
        logger.warning("Alpha Vantage API key not configured")
        return {
            "feed": [],
            "error": "Alpha Vantage API key not configured"
        }
    
    try:
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": ALPHA_VANTAGE_API_KEY,
            "limit": limit
        }
        
        if tickers:
            # Alpha Vantage uses comma-separated tickers
            params["tickers"] = ",".join(tickers)
        
        if topics:
            params["topics"] = topics
        
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors
        if "Error Message" in data:
            logger.error(f"Alpha Vantage API error: {data['Error Message']}")
            return {"feed": [], "error": data["Error Message"]}
        
        if "Note" in data:
            # Rate limit message
            logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
            return {"feed": [], "error": "API rate limit reached (25 requests/day)"}
        
        return data
        
    except requests.RequestException as e:
        logger.error(f"Error fetching news from Alpha Vantage: {e}")
        return {"feed": [], "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in Alpha Vantage service: {e}")
        return {"feed": [], "error": str(e)}


def get_company_overview(symbol: str) -> Dict:
    """
    Get company fundamental data.
    
    Args:
        symbol: Stock symbol (e.g., '7203.T' for Toyota)
    
    Returns:
        Dict with company overview data
    """
    if not ALPHA_VANTAGE_API_KEY:
        return {"error": "Alpha Vantage API key not configured"}
    
    try:
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "Error Message" in data:
            logger.error(f"Alpha Vantage API error: {data['Error Message']}")
            return {"error": data["Error Message"]}
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching company overview: {e}")
        return {"error": str(e)}


def get_top_gainers_losers() -> Dict:
    """
    Get top gainers and losers in the US market.
    
    Returns:
        Dict with top gainers, losers, and most actively traded stocks
    """
    if not ALPHA_VANTAGE_API_KEY:
        logger.warning("Alpha Vantage API key not configured")
        return {"error": "Alpha Vantage API key not configured"}
    
    try:
        params = {
            "function": "TOP_GAINERS_LOSERS",
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if "Error Message" in data:
            logger.error(f"Alpha Vantage API error: {data['Error Message']}")
            return {"error": data["Error Message"]}
        
        if "Note" in data:
            logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
            return {"error": "API rate limit reached (25 requests/day)"}
        
        # Transform the data
        result = {
            "top_gainers": [],
            "top_losers": [],
            "most_actively_traded": [],
            "last_updated": data.get("last_updated", datetime.now().isoformat())
        }
        
        # Process top gainers (limit to top 5)
        for gainer in data.get("top_gainers", [])[:5]:
            try:
                result["top_gainers"].append({
                    "ticker": gainer.get("ticker"),
                    "price": float(gainer.get("price", 0)),
                    "change_amount": float(gainer.get("change_amount", 0)),
                    "change_percentage": gainer.get("change_percentage", "0%").replace("%", ""),
                    "volume": int(gainer.get("volume", 0))
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing gainer data: {e}")
                continue
        
        # Process top losers (limit to top 5)
        for loser in data.get("top_losers", [])[:5]:
            try:
                result["top_losers"].append({
                    "ticker": loser.get("ticker"),
                    "price": float(loser.get("price", 0)),
                    "change_amount": float(loser.get("change_amount", 0)),
                    "change_percentage": loser.get("change_percentage", "0%").replace("%", ""),
                    "volume": int(loser.get("volume", 0))
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing loser data: {e}")
                continue
        
        # Process most actively traded (limit to top 5)
        for active in data.get("most_actively_traded", [])[:5]:
            try:
                result["most_actively_traded"].append({
                    "ticker": active.get("ticker"),
                    "price": float(active.get("price", 0)),
                    "change_amount": float(active.get("change_amount", 0)),
                    "change_percentage": active.get("change_percentage", "0%").replace("%", ""),
                    "volume": int(active.get("volume", 0))
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing active stock data: {e}")
                continue
        
        return result
    except requests.RequestException as e:
        logger.error(f"Error fetching top gainers/losers: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error fetching top gainers/losers: {e}")
        return {"error": str(e)}


def get_global_market_status() -> Dict:
    """
    Get global market open/close status.
    
    Returns:
        Dict with market status for different regions
    """
    if not ALPHA_VANTAGE_API_KEY:
        logger.warning("Alpha Vantage API key not configured")
        return {"error": "Alpha Vantage API key not configured"}
    
    try:
        params = {
            "function": "MARKET_STATUS",
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "Error Message" in data:
            logger.error(f"Alpha Vantage API error: {data['Error Message']}")
            return {"error": data["Error Message"]}
        
        if "Note" in data:
            logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
            return {"error": "API rate limit reached (25 requests/day)"}
        
        markets = []
        for market in data.get("markets", []):
            markets.append({
                "market_type": market.get("market_type"),
                "region": market.get("region"),
                "primary_exchanges": market.get("primary_exchanges"),
                "local_open": market.get("local_open"),
                "local_close": market.get("local_close"),
                "current_status": market.get("current_status"),
                "notes": market.get("notes", "")
            })
        
        return {
            "markets": markets,
            "endpoint": data.get("endpoint", "Market Status")
        }
    except requests.RequestException as e:
        logger.error(f"Error fetching market status: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error fetching market status: {e}")
        return {"error": str(e)}


def search_symbol(keywords: str) -> List[Dict]:
    """
    Search for stock symbols using Alpha Vantage SYMBOL_SEARCH.
    Provides better, more comprehensive search results than Finnhub.
    
    Args:
        keywords: Search keywords (company name or ticker symbol)
    
    Returns:
        List of matching symbols with detailed information
    """
    if not ALPHA_VANTAGE_API_KEY:
        logger.warning("Alpha Vantage API key not configured")
        return []
    
    try:
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if "Error Message" in data:
            logger.error(f"Alpha Vantage API error: {data['Error Message']}")
            return []
        
        if "Note" in data:
            logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
            return []
        
        # Transform results to match frontend format
        results = []
        for match in data.get("bestMatches", []):
            results.append({
                "symbol": match.get("1. symbol", ""),
                "displaySymbol": match.get("1. symbol", ""),
                "description": match.get("2. name", ""),
                "type": match.get("3. type", "Equity"),
                "region": match.get("4. region", ""),
                "currency": match.get("8. currency", ""),
                "matchScore": match.get("9. matchScore", "0.0")
            })
        
        # Sort by match score (descending)
        results.sort(key=lambda x: float(x.get("matchScore", 0)), reverse=True)
        
        logger.info(f"Found {len(results)} results for '{keywords}'")
        return results
        
    except requests.RequestException as e:
        logger.error(f"Error searching symbols: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in symbol search: {e}")
        return []
