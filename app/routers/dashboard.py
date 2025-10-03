"""
Dashboard API endpoints for real-time stock data.
Provides WebSocket streaming and REST endpoints for Finnhub integration.
"""
import asyncio
import json
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.finnhub_service import (
    get_finnhub_service,
    get_finnhub_quote,
    get_finnhub_company_profile,
    search_finnhub_symbols
)
from app.services import yfinance_service, alphavantage_service
from app.auth.dependencies import get_current_user
from app.models.database import User
from app.core.config import FINNHUB_API_KEY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class WatchlistRequest(BaseModel):
    """Request to add/remove symbols from watchlist."""
    symbols: List[str]


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Remaining: {len(self.active_connections)}")
    
    def subscribe(self, websocket: WebSocket, symbol: str):
        """Subscribe a connection to a symbol."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(symbol.upper())
            logger.info(f"Subscribed to {symbol.upper()}")
    
    def unsubscribe(self, websocket: WebSocket, symbol: str):
        """Unsubscribe a connection from a symbol."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(symbol.upper())
            logger.info(f"Unsubscribed from {symbol.upper()}")
    
    async def broadcast_quote(self, symbol: str, quote_data: dict):
        """Broadcast quote update to all subscribed connections."""
        disconnected = []
        for connection in self.active_connections:
            if symbol.upper() in self.subscriptions.get(connection, set()):
                try:
                    await connection.send_json({
                        "type": "quote_update",
                        "data": quote_data
                    })
                except Exception as e:
                    logger.error(f"Error sending to WebSocket: {e}")
                    disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time stock updates.
    
    Client sends:
    - {"action": "subscribe", "symbols": ["AAPL", "MSFT"]}
    - {"action": "unsubscribe", "symbols": ["AAPL"]}
    
    Server sends:
    - {"type": "quote_update", "data": {...}}
    - {"type": "error", "message": "..."}
    
    Rate limit: Free tier = 60 calls/min = 1 call/second
    Strategy: Update all symbols in sequence with delays
    """
    await manager.connect(websocket)
    
    # Background task to send periodic updates
    update_task = None
    
    try:
        # Start update loop
        async def send_updates():
            """
            Send updates for subscribed symbols with rate limiting.
            Free tier: 60 calls/min = 1 call/second
            Strategy: Cycle through symbols, 1.5 seconds between calls for safety
            """
            while True:
                try:
                    symbols = list(manager.subscriptions.get(websocket, set()))
                    if symbols and FINNHUB_API_KEY:
                        # Update one symbol at a time to respect rate limits
                        for symbol in symbols:
                            try:
                                quote = get_finnhub_quote(symbol, FINNHUB_API_KEY)
                                
                                # Check if rate limited
                                if quote.get("rate_limited"):
                                    logger.warning(f"Rate limited on {symbol}, skipping update cycle")
                                    await websocket.send_json({
                                        "type": "rate_limit_warning",
                                        "message": "Rate limit reached. Updates paused for 60 seconds."
                                    })
                                    # Wait full minute before trying again
                                    await asyncio.sleep(60)
                                    break
                                
                                await websocket.send_json({
                                    "type": "quote_update",
                                    "data": quote
                                })
                                # Wait 1.5 seconds between API calls (safe margin)
                                await asyncio.sleep(1.5)
                            except Exception as e:
                                logger.error(f"Error fetching quote for {symbol}: {e}")
                                # Still wait to avoid rapid retries
                                await asyncio.sleep(1.5)
                    else:
                        # No symbols subscribed, wait before checking again
                        await asyncio.sleep(2.0)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in update loop: {e}")
                    await asyncio.sleep(2.0)
        
        update_task = asyncio.create_task(send_updates())
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe":
                symbols = data.get("symbols", [])
                for symbol in symbols:
                    manager.subscribe(websocket, symbol)
                await websocket.send_json({
                    "type": "subscribed",
                    "symbols": symbols,
                    "message": f"Updates every {len(symbols)} seconds (1 symbol/sec rate limit)"
                })
            
            elif action == "unsubscribe":
                symbols = data.get("symbols", [])
                for symbol in symbols:
                    manager.unsubscribe(websocket, symbol)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "symbols": symbols
                })
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if update_task:
            update_task.cancel()
        manager.disconnect(websocket)


@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get current quote for a symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT)
        
    Returns:
        Current quote data including price, change, percent change, etc.
    """
    if not FINNHUB_API_KEY:
        raise HTTPException(status_code=503, detail="Finnhub API key not configured")
    
    try:
        quote = get_finnhub_quote(symbol, FINNHUB_API_KEY)
        if "error" in quote:
            raise HTTPException(status_code=400, detail=quote["error"])
        return quote
    except Exception as e:
        logger.error(f"Error fetching quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{symbol}")
async def get_profile(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get company profile for a symbol.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Company profile data
    """
    if not FINNHUB_API_KEY:
        raise HTTPException(status_code=503, detail="Finnhub API key not configured")
    
    try:
        profile = get_finnhub_company_profile(symbol, FINNHUB_API_KEY)
        if "error" in profile:
            raise HTTPException(status_code=400, detail=profile["error"])
        return profile
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_symbols(
    q: str = Query(..., description="Search query (company name or ticker)"),
    current_user: User = Depends(get_current_user)
):
    """
    Search for stock symbols.
    
    Args:
        q: Search query
        
    Returns:
        List of matching symbols
    """
    if not FINNHUB_API_KEY:
        raise HTTPException(status_code=503, detail="Finnhub API key not configured")
    
    try:
        results = search_finnhub_symbols(q, FINNHUB_API_KEY)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Check if dashboard service is available."""
    return {
        "status": "ok",
        "finnhub_configured": bool(FINNHUB_API_KEY),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/test")
async def test_endpoint():
    """Test endpoint without authentication for debugging."""
    return {
        "status": "ok",
        "finnhub_configured": bool(FINNHUB_API_KEY),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/jp/quote/{symbol}")
async def get_jp_quote(
    symbol: str,
    with_chart: bool = Query(False, description="Include chart data with multiple timeframes"),
    current_user: User = Depends(get_current_user)
):
    """
    Get quote for Japanese stock using yfinance.
    Symbol format: XXXX.T (e.g., 7203.T for Toyota)
    """
    try:
        info = yfinance_service.get_stock_info(symbol, with_chart=with_chart)
        if "error" in info:
            raise HTTPException(status_code=400, detail=info["error"])
        return info
    except Exception as e:
        logger.error(f"Error fetching JP quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jp/news/{symbol}")
async def get_jp_stock_news(
    symbol: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user)
):
    """
    Get news articles for a Japanese stock.
    """
    try:
        news = yfinance_service.get_stock_news(symbol, limit=limit)
        return {"symbol": symbol, "news": news}
    except Exception as e:
        logger.error(f"Error fetching JP news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jp/trend/{symbol}")
async def get_jp_stock_trend(
    symbol: str,
    period: str = Query("1mo", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    current_user: User = Depends(get_current_user)
):
    """
    Get price trend analysis for Japanese stock.
    """
    try:
        trend = yfinance_service.get_price_history(symbol, period=period)
        if "error" in trend:
            raise HTTPException(status_code=400, detail=trend["error"])
        return trend
    except Exception as e:
        logger.error(f"Error fetching JP trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jp/market-movers")
async def get_jp_market_movers(
    limit: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user)
):
    """
    Get top gainers and losers in Japanese market.
    """
    try:
        movers = yfinance_service.get_japanese_market_movers(limit=limit)
        if "error" in movers:
            raise HTTPException(status_code=400, detail=movers["error"])
        return movers
    except Exception as e:
        logger.error(f"Error fetching market movers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/sentiment")
async def get_news_sentiment(
    tickers: Optional[str] = Query(None, description="Comma-separated ticker symbols"),
    topics: Optional[str] = Query(None, description="Topics to filter"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Get news with sentiment analysis from Alpha Vantage.
    Note: Free tier limit is 25 requests per day.
    """
    try:
        ticker_list = tickers.split(",") if tickers else None
        news_data = alphavantage_service.get_news_sentiment(
            tickers=ticker_list,
            topics=topics,
            limit=limit
        )
        return news_data
    except Exception as e:
        logger.error(f"Error fetching news sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/top-movers")
async def get_market_top_movers(
    current_user: User = Depends(get_current_user)
):
    """
    Get top gainers, losers, and most actively traded stocks (US market).
    Uses AlphaVantage API.
    Note: Free tier limit is 25 requests per day.
    """
    try:
        movers = alphavantage_service.get_top_gainers_losers()
        if "error" in movers:
            raise HTTPException(status_code=400, detail=movers["error"])
        return movers
    except Exception as e:
        logger.error(f"Error fetching top movers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/status")
async def get_market_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get global market open/close status.
    Uses AlphaVantage API.
    Note: Free tier limit is 25 requests per day.
    """
    try:
        status = alphavantage_service.get_global_market_status()
        if "error" in status:
            raise HTTPException(status_code=400, detail=status["error"])
        return status
    except Exception as e:
        logger.error(f"Error fetching market status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/sentiment")
async def get_market_sentiment(
    current_user: User = Depends(get_current_user)
):
    """
    Get overall market sentiment based on recent news.
    Uses AlphaVantage NEWS_SENTIMENT API with general market topics.
    Returns aggregated sentiment and market status.
    """
    try:
        # Fetch general market news sentiment
        sentiment_data = alphavantage_service.get_news_sentiment(
            topics="economy_macro,financial_markets",
            limit=50
        )
        
        if "error" in sentiment_data:
            # Return cached/fallback data if API fails
            logger.warning(f"Sentiment API error: {sentiment_data['error']}")
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "confidence": "low",
                "market_status": "open",
                "last_updated": datetime.now().isoformat(),
                "error": sentiment_data["error"]
            }
        
        # Calculate aggregated sentiment from news articles
        articles = sentiment_data.get("feed", [])
        if not articles:
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "confidence": "low",
                "market_status": "unknown",
                "last_updated": datetime.now().isoformat()
            }
        
        # Aggregate sentiment scores
        total_score = 0.0
        total_relevance = 0.0
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        
        for article in articles:
            # Get overall sentiment from article
            overall_sentiment = article.get("overall_sentiment_score", 0)
            relevance = article.get("relevance_score", 0)
            
            # Weight by relevance
            total_score += float(overall_sentiment) * float(relevance)
            total_relevance += float(relevance)
            
            # Count sentiment types
            label = article.get("overall_sentiment_label", "neutral").lower()
            if "bullish" in label:
                bullish_count += 1
            elif "bearish" in label:
                bearish_count += 1
            else:
                neutral_count += 1
        
        # Calculate weighted average
        avg_sentiment = total_score / total_relevance if total_relevance > 0 else 0.0
        
        # Determine sentiment label
        if avg_sentiment > 0.15:
            sentiment_label = "bullish"
        elif avg_sentiment < -0.15:
            sentiment_label = "bearish"
        else:
            sentiment_label = "neutral"
        
        # Determine confidence based on article count and agreement
        article_count = len(articles)
        dominant_count = max(bullish_count, bearish_count, neutral_count)
        agreement_ratio = dominant_count / article_count if article_count > 0 else 0
        
        if article_count >= 30 and agreement_ratio > 0.6:
            confidence = "high"
        elif article_count >= 15 and agreement_ratio > 0.5:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "sentiment": sentiment_label,
            "sentiment_score": round(avg_sentiment, 3),
            "confidence": confidence,
            "article_count": article_count,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating market sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

