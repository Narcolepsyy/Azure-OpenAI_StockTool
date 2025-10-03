"""
yfinance service for stock data, news, and trends.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


def get_stock_info(symbol: str, with_chart: bool = False) -> Dict:
    """
    Get comprehensive stock information using yfinance.
    
    Args:
        symbol: Stock symbol (e.g., '7203.T' for Toyota)
        with_chart: Include historical chart data with multiple timeframes
    
    Returns:
        Dict with stock info including price, trends, and fundamentals
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Get current price and changes
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        previous_close = info.get('previousClose')
        
        change = None
        percent_change = None
        if current_price and previous_close:
            change = current_price - previous_close
            percent_change = (change / previous_close) * 100
        
        result = {
            "symbol": symbol,
            "name": info.get('longName') or info.get('shortName'),
            "current_price": current_price,
            "previous_close": previous_close,
            "change": change,
            "percent_change": percent_change,
            "day_high": info.get('dayHigh'),
            "day_low": info.get('dayLow'),
            "open": info.get('open'),
            "volume": info.get('volume'),
            "market_cap": info.get('marketCap'),
            "pe_ratio": info.get('trailingPE'),
            "eps": info.get('trailingEps'),
            "dividend_yield": info.get('dividendYield'),
            "year_high": info.get('fiftyTwoWeekHigh'),
            "year_low": info.get('fiftyTwoWeekLow'),
            "shares_outstanding": info.get('sharesOutstanding'),
            "currency": info.get('currency', 'JPY'),
            "exchange": info.get('exchange'),
            "datetime": datetime.now().isoformat(),
            "timestamp": int(datetime.now().timestamp()),
            "source": "yfinance",
            "company_profile": {
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "website": info.get('website'),
                "description": info.get('longBusinessSummary'),
                "country": info.get('country'),
                "city": info.get('city'),
                "employees": info.get('fullTimeEmployees'),
                "phone": info.get('phone'),
                "address": info.get('address1')
            }
        }
        
        # Add chart data if requested
        if with_chart:
            chart_data = _get_chart_data(stock)
            result["chart"] = chart_data
        
        # Always include recent news (limit to 5 articles)
        try:
            news_articles = get_stock_news(symbol, limit=5)
            result["news"] = news_articles
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            result["news"] = []
        
        return result
    except Exception as e:
        logger.error(f"Error fetching stock info for {symbol}: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "source": "yfinance"
        }


def _get_chart_data(stock) -> Dict:
    """
    Get historical chart data with multiple timeframes.
    
    Args:
        stock: yfinance Ticker object
    
    Returns:
        Dict with chart data for multiple timeframes
    """
    try:
        ranges = []
        
        # Define timeframes
        timeframes = [
            {"key": "1d", "label": "1D", "period": "1d", "interval": "5m"},
            {"key": "5d", "label": "5D", "period": "5d", "interval": "15m"},
            {"key": "1mo", "label": "1M", "period": "1mo", "interval": "1d"},
            {"key": "3mo", "label": "3M", "period": "3mo", "interval": "1d"},
            {"key": "6mo", "label": "6M", "period": "6mo", "interval": "1d"},
            {"key": "1y", "label": "1Y", "period": "1y", "interval": "1d"},
            {"key": "5y", "label": "5Y", "period": "5y", "interval": "1wk"},
        ]
        
        for timeframe in timeframes:
            try:
                hist = stock.history(period=timeframe["period"], interval=timeframe["interval"])
                
                if not hist.empty:
                    # Convert to list of points
                    points = []
                    for timestamp, row in hist.iterrows():
                        points.append({
                            "time": timestamp.isoformat(),
                            "close": float(row['Close']) if not pd.isna(row['Close']) else None,
                            "open": float(row['Open']) if not pd.isna(row['Open']) else None,
                            "high": float(row['High']) if not pd.isna(row['High']) else None,
                            "low": float(row['Low']) if not pd.isna(row['Low']) else None,
                            "volume": int(row['Volume']) if not pd.isna(row['Volume']) else None,
                        })
                    
                    ranges.append({
                        "key": timeframe["key"],
                        "label": timeframe["label"],
                        "period": timeframe["period"],
                        "interval": timeframe["interval"],
                        "start": hist.index[0].isoformat() if len(hist) > 0 else None,
                        "end": hist.index[-1].isoformat() if len(hist) > 0 else None,
                        "points": points
                    })
            except Exception as e:
                logger.error(f"Error fetching {timeframe['key']} data: {e}")
                continue
        
        return {
            "ranges": ranges,
            "default_range": "1mo",
            "timezone": "Asia/Tokyo"
        }
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return {
            "ranges": [],
            "default_range": "1mo",
            "timezone": "Asia/Tokyo"
        }


def get_stock_news(symbol: str, limit: int = 5) -> List[Dict]:
    """
    Get news articles for a stock.
    
    Args:
        symbol: Stock symbol
        limit: Number of articles to return
    
    Returns:
        List of news articles
    """
    try:
        stock = yf.Ticker(symbol)
        news = stock.news
        
        articles = []
        for article in news[:limit]:
            # Handle new yfinance news structure (content nested)
            content = article.get('content', article)
            
            # Handle missing fields gracefully
            title = content.get('title') or content.get('headline', 'No title')
            
            # Handle provider/publisher
            provider = content.get('provider', {})
            publisher = provider.get('displayName') or content.get('publisher') or content.get('source', {}).get('name', 'Unknown')
            
            # Handle links
            canonical_url = content.get('canonicalUrl', {})
            click_through_url = content.get('clickThroughUrl', {})
            link = canonical_url.get('url') or click_through_url.get('url') or content.get('link') or content.get('url', '#')
            
            # Handle timestamp
            pub_date = content.get('pubDate') or content.get('providerPublishTime')
            if pub_date:
                if isinstance(pub_date, str):
                    published = pub_date
                else:
                    published = datetime.fromtimestamp(pub_date).isoformat()
            else:
                published = datetime.now().isoformat()
            
            # Handle thumbnail
            thumbnail = None
            thumbnail_obj = content.get('thumbnail')
            if thumbnail_obj:
                # Try resolutions first
                resolutions = thumbnail_obj.get('resolutions', [])
                if resolutions and len(resolutions) > 0:
                    # Get the first resolution (usually smallest)
                    thumbnail = resolutions[0].get('url')
                # Fallback to originalUrl
                if not thumbnail:
                    thumbnail = thumbnail_obj.get('originalUrl')
            
            articles.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "published": published,
                "thumbnail": thumbnail
            })
        
        return articles
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return []


def get_price_history(symbol: str, period: str = "1mo") -> Dict:
    """
    Get historical price data for trend analysis.
    
    Args:
        symbol: Stock symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    
    Returns:
        Dict with historical data and trend indicators
    """
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            return {"error": "No historical data available"}
        
        # Calculate trend indicators
        latest_price = hist['Close'].iloc[-1]
        period_start_price = hist['Close'].iloc[0]
        period_change = ((latest_price - period_start_price) / period_start_price) * 100
        
        # Simple moving averages
        sma_20 = hist['Close'].rolling(window=min(20, len(hist))).mean().iloc[-1]
        sma_50 = hist['Close'].rolling(window=min(50, len(hist))).mean().iloc[-1] if len(hist) >= 50 else None
        
        # Determine trend
        trend = "neutral"
        if sma_50:
            if latest_price > sma_20 > sma_50:
                trend = "strong_uptrend"
            elif latest_price > sma_20:
                trend = "uptrend"
            elif latest_price < sma_20 < sma_50:
                trend = "strong_downtrend"
            elif latest_price < sma_20:
                trend = "downtrend"
        
        return {
            "symbol": symbol,
            "period": period,
            "period_change_percent": period_change,
            "latest_price": latest_price,
            "period_high": hist['High'].max(),
            "period_low": hist['Low'].min(),
            "average_volume": hist['Volume'].mean(),
            "sma_20": sma_20,
            "sma_50": sma_50,
            "trend": trend,
            "data_points": len(hist)
        }
    except Exception as e:
        logger.error(f"Error fetching price history for {symbol}: {e}")
        return {"error": str(e)}


def get_japanese_market_movers(limit: int = 5) -> Dict:
    """
    Get top gainers/losers in Japanese market.
    
    Returns:
        Dict with top gainers and losers
    """
    try:
        # Major Nikkei 225 stocks
        major_stocks = [
            "7203.T",  # Toyota
            "6758.T",  # Sony
            "9984.T",  # SoftBank
            "8306.T",  # Mitsubishi UFJ
            "6861.T",  # Keyence
            "9433.T",  # KDDI
            "6902.T",  # Denso
            "7974.T",  # Nintendo
            "4063.T",  # Shin-Etsu Chemical
            "6367.T",  # Daikin
        ]
        
        movers = []
        for symbol in major_stocks:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                
                current = info.get('currentPrice') or info.get('regularMarketPrice')
                previous = info.get('previousClose')
                
                if current and previous:
                    change_percent = ((current - previous) / previous) * 100
                    movers.append({
                        "symbol": symbol,
                        "name": info.get('shortName'),
                        "price": current,
                        "change_percent": change_percent
                    })
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                continue
        
        # Separate gainers (positive change) and losers (negative change)
        gainers = [m for m in movers if m['change_percent'] > 0]
        losers = [m for m in movers if m['change_percent'] < 0]
        
        # Sort gainers descending (highest gain first)
        gainers.sort(key=lambda x: x['change_percent'], reverse=True)
        
        # Sort losers ascending (most negative first)
        losers.sort(key=lambda x: x['change_percent'])
        
        return {
            "gainers": gainers[:limit],
            "losers": losers[:limit]
        }
    except Exception as e:
        logger.error(f"Error fetching market movers: {e}")
        return {"error": str(e)}
