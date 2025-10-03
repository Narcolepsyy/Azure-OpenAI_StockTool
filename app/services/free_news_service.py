"""
Free News API service for market summary.
Uses multiple free sources: NewsAPI.org (free tier), GNews, and RSS feeds.
"""

import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
import feedparser

logger = logging.getLogger(__name__)

# Optional: NewsAPI.org free tier (100 requests/day)
# Get free key at: https://newsapi.org/
NEWSAPI_KEY = os.getenv("NEWSAPI_API_KEY", "")
NEWSAPI_BASE_URL = "https://newsapi.org/v2"

# Free RSS feeds (no API key needed)
FREE_RSS_FEEDS = {
    "financial": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Top News
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # Earnings
    ],
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ],
    "commodities": [
        "https://www.investing.com/rss/commodities.rss",
    ]
}


def fetch_newsapi_articles(query: str, limit: int = 20) -> List[Dict]:
    """
    Fetch news from NewsAPI.org (free tier: 100 requests/day).
    
    Args:
        query: Search query or category
        limit: Number of articles (max 100)
    
    Returns:
        List of article dictionaries
    """
    if not NEWSAPI_KEY:
        logger.info("NewsAPI key not configured, skipping")
        return []
    
    try:
        # Get articles from last 24 hours
        from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        params = {
            "apiKey": NEWSAPI_KEY,
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": min(limit, 100)
        }
        
        response = requests.get(
            f"{NEWSAPI_BASE_URL}/everything",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "ok":
            logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            return []
        
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title", ""),
                "content": article.get("description", ""),
                "source": article.get("source", {}).get("name", ""),
                "url": article.get("url", ""),
                "published": article.get("publishedAt", ""),
                "image": article.get("urlToImage", "")
            })
        
        logger.info(f"Fetched {len(articles)} articles from NewsAPI")
        return articles
        
    except requests.RequestException as e:
        logger.error(f"Error fetching from NewsAPI: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in NewsAPI: {e}")
        return []


def fetch_rss_feeds(category: str = "financial", limit: int = 10) -> List[Dict]:
    """
    Fetch news from free RSS feeds (no API key needed).
    
    Args:
        category: Category of feeds ("financial", "crypto", "commodities")
        limit: Max articles per feed
    
    Returns:
        List of article dictionaries
    """
    feeds = FREE_RSS_FEEDS.get(category, FREE_RSS_FEEDS["financial"])
    all_articles = []
    
    for feed_url in feeds:
        try:
            logger.info(f"Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:limit]:
                # Extract article data
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                
                # Clean HTML from summary if present
                if summary:
                    import re
                    summary = re.sub('<[^<]+?>', '', summary)
                    summary = summary[:500]  # Limit length
                
                article = {
                    "title": title,
                    "content": summary,
                    "source": feed.feed.get("title", "RSS Feed"),
                    "url": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "")),
                    "image": None
                }
                
                # Try to get image from media content
                if hasattr(entry, 'media_content') and entry.media_content:
                    article["image"] = entry.media_content[0].get('url')
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    article["image"] = entry.media_thumbnail[0].get('url')
                
                all_articles.append(article)
                
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {e}")
            continue
    
    logger.info(f"Fetched {len(all_articles)} articles from RSS feeds")
    return all_articles


def get_market_news(categories: List[str] = None, limit_per_category: int = 15) -> Dict[str, List[Dict]]:
    """
    Get market news from free sources organized by category.
    
    Args:
        categories: List of categories to fetch (default: all)
        limit_per_category: Max articles per category
    
    Returns:
        Dict mapping category to list of articles
    """
    if categories is None:
        categories = ["financial", "crypto", "commodities"]
    
    news_by_category = {}
    
    for category in categories:
        articles = []
        
        # Try NewsAPI first (if configured)
        if NEWSAPI_KEY:
            query_map = {
                "financial": "stock market OR S&P 500 OR Dow Jones",
                "crypto": "bitcoin OR cryptocurrency OR ethereum",
                "commodities": "gold OR oil OR commodities"
            }
            newsapi_articles = fetch_newsapi_articles(
                query_map.get(category, "market"),
                limit=limit_per_category
            )
            articles.extend(newsapi_articles)
        
        # Supplement with RSS feeds (always free)
        if len(articles) < limit_per_category:
            rss_articles = fetch_rss_feeds(category, limit_per_category)
            articles.extend(rss_articles)
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in articles:
            title_lower = article["title"].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_articles.append(article)
        
        news_by_category[category] = unique_articles[:limit_per_category]
    
    return news_by_category


def generate_summary_from_news(articles: List[Dict], section_title: str) -> Optional[Dict]:
    """
    Generate a formatted summary section from news articles.
    
    Args:
        articles: List of news articles
        section_title: Title for this section
    
    Returns:
        Dict with title, items, and source count
    """
    if not articles:
        return None
    
    items = []
    sources = set()
    
    for article in articles[:5]:  # Limit to top 5 articles
        title = article.get("title", "")
        content = article.get("content", "")
        source = article.get("source", "")
        url = article.get("url", "")
        
        if title:
            # Ensure content has reasonable length
            if len(content) > 300:
                content = content[:300] + "..."
            
            items.append({
                "title": title,
                "content": content or "No summary available.",
                "source": source,
                "url": url
            })
            
            if source:
                sources.add(source)
    
    if not items:
        return None
    
    return {
        "section_title": section_title,
        "items": items,
        "source_count": len(sources)
    }
