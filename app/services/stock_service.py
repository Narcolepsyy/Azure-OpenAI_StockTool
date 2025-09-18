"""Stock data tools and financial analysis services."""
import logging
import re
import yfinance as yf
import requests
import feedparser
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from urllib.parse import quote
from typing import Dict, Any, List, Optional
from cachetools import TTLCache

from app.core.config import (
    TICKER_RE, QUOTE_CACHE_SIZE, QUOTE_TTL_SECONDS, 
    NEWS_CACHE_SIZE, NEWS_TTL_SECONDS, RISK_FREE_RATE, NEWS_USER_AGENT
)

logger = logging.getLogger(__name__)

# Initialize caches
QUOTE_CACHE = TTLCache(maxsize=QUOTE_CACHE_SIZE, ttl=QUOTE_TTL_SECONDS)
NEWS_CACHE = TTLCache(maxsize=NEWS_CACHE_SIZE, ttl=NEWS_TTL_SECONDS)

# Natural language mappings for timeframes
_NL_PERIOD_MAP = {
    "past week": "5d", "last week": "5d", "previous week": "5d",
    "1 week": "5d", "one week": "5d", "7d": "5d", "five days": "5d",
    "5 days": "5d", "last 5 days": "5d", "past month": "1mo",
    "last month": "1mo", "1 month": "1mo", "one month": "1mo",
    "3 months": "3mo", "three months": "3mo", "6 months": "6mo",
    "six months": "6mo", "1 year": "1y", "one year": "1y",
    "2 years": "2y", "two years": "2y", "5 years": "5y",
    "five years": "5y", "10 years": "10y", "ten years": "10y",
    "ytd": "ytd", "year to date": "ytd", "all time": "max", "max": "max",
}

_NL_INTERVAL_MAP = {
    "daily": "1d", "day": "1d", "1 day": "1d", "one day": "1d",
    "weekly": "1wk", "week": "1wk", "monthly": "1mo", "month": "1mo",
    "hourly": "1h", "hour": "1h",
}

def _normalize_period(val: Optional[str]) -> str:
    """Normalize natural language period to yfinance format."""
    if not val:
        return "1mo"
    s = str(val).strip().lower()
    return _NL_PERIOD_MAP.get(s, s)

def _normalize_interval(val: Optional[str]) -> str:
    """Normalize natural language interval to yfinance format."""
    if not val:
        return "1d"
    s = str(val).strip().lower()
    return _NL_INTERVAL_MAP.get(s, s)

def _extract_article(url: str, timeout: int = 8, max_chars: int = 6000) -> Dict[str, Any]:
    """Fetch and extract the main article text from a URL."""
    if not (url or '').strip():
        return {"content": None}
    
    try:
        resp = requests.get(url, headers={"User-Agent": NEWS_USER_AGENT}, timeout=max(2, int(timeout)))
        resp.raise_for_status()
        html = resp.text or ""
    except Exception as e:
        return {"content": None, "error": f"fetch_failed: {e}"}

    # Try readability-lxml first
    try:
        from readability import Document
        doc = Document(html)
        title = doc.short_title() or None
        content_html = doc.summary(html_partial=True)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content_html or html, "lxml")
            text = soup.get_text(" ", strip=True)
        except Exception:
            text = re.sub(r"\s+", " ", (content_html or "").replace("\n", " "))
        text = (text or "").strip()
        if max_chars and isinstance(max_chars, int) and max_chars > 0 and len(text) > max_chars:
            text = text[:max_chars] + "..."
        if text:
            return {"title": title, "content": text}
    except Exception:
        pass

    # Fallback: BeautifulSoup plain text
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        # Remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text or "").strip()
        if max_chars and isinstance(max_chars, int) and 0 < max_chars < len(text):
            text = text[:max_chars] + "..."
        return {"content": text}
    except Exception as e:
        return {"content": None, "error": f"parse_failed: {e}"}

def get_stock_quote(symbol: str) -> Dict[str, Any]:
    """Return latest close price and meta for a ticker using Yahoo Finance with TTL cache."""
    sym = (symbol or "").strip().upper()
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    # Cache hit
    if sym in QUOTE_CACHE:
        cached = QUOTE_CACHE[sym]
        logger.debug("cache hit for %s", sym)
        return cached

    ticker = yf.Ticker(sym)
    try:
        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)
    except Exception as e:
        raise ValueError(f"failed to retrieve data for '{sym}': {e}")

    if hist is None or hist.empty:
        raise ValueError(f"No price data found for symbol '{sym}'")

    last_row = hist.tail(1)
    close_val = float(last_row["Close"].iloc[0])

    currency = None
    try:
        fi = getattr(ticker, "fast_info", None) or {}
        currency = fi.get("currency") if isinstance(fi, dict) else None
    except Exception:
        currency = None

    result = {
        "symbol": sym,
        "price": round(close_val, 4),
        "currency": currency or "USD",
        "as_of": str(last_row.index[-1]),
        "source": "yfinance",
    }

    QUOTE_CACHE[sym] = result
    return result

def get_company_profile(symbol: str) -> Dict[str, Any]:
    """Return company profile details for a ticker using yfinance."""
    sym = (symbol or "").strip().upper()
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    t = yf.Ticker(sym)
    info: Dict[str, Any] = {}
    try:
        info = t.get_info() or {}
    except Exception as e:
        logger.debug("get_info failed for %s: %s", sym, e)
        info = {}

    fast = {}
    try:
        fast = getattr(t, "fast_info", None) or {}
    except Exception:
        fast = {}

    return {
        "symbol": sym,
        "longName": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
        "country": info.get("country"),
        "currency": (fast.get("currency") if isinstance(fast, dict) else None) or info.get("currency") or "USD",
        "summary": info.get("longBusinessSummary") or info.get("summary") or None,
        "source": "yfinance",
    }

def get_historical_prices(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
    limit: Optional[int] = None,
    auto_adjust: bool = False,
) -> Dict[str, Any]:
    """Return historical OHLCV for a ticker."""
    sym = (symbol or "").strip().upper()
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    allowed_periods = {"5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"}
    allowed_intervals = {"1m","2m","5m","15m","30m","60m","90m","1h","1d","5d","1wk","1mo","3mo"}

    # Normalize any natural language inputs before validation
    p = _normalize_period(period)
    itv = _normalize_interval(interval)

    if p not in allowed_periods:
        raise ValueError(f"invalid period: {period}")
    if itv not in allowed_intervals:
        raise ValueError(f"invalid interval: {interval}")

    t = yf.Ticker(sym)
    try:
        hist = t.history(period=p, interval=itv, auto_adjust=auto_adjust)
    except Exception as e:
        raise ValueError(f"failed to retrieve history for '{sym}': {e}")

    if hist is None or hist.empty:
        raise ValueError(f"No historical data found for symbol '{sym}'")

    if limit and isinstance(limit, int) and limit > 0:
        hist = hist.tail(limit)

    rows: List[Dict[str, Any]] = []
    for idx, row in hist.iterrows():
        try:
            rows.append({
                "date": str(idx),
                "open": float(row.get("Open")),
                "high": float(row.get("High")),
                "low": float(row.get("Low")),
                "close": float(row.get("Close")),
                "volume": int(row.get("Volume", 0)) if not (row.get("Volume") != row.get("Volume")) else None,  # handle NaN
            })
        except Exception:
            continue

    currency = None
    try:
        fi = getattr(t, "fast_info", None) or {}
        currency = fi.get("currency") if isinstance(fi, dict) else None
    except Exception:
        currency = None

    return {
        "symbol": sym, 
        "currency": currency or "USD", 
        "count": len(rows), 
        "interval": itv, 
        "period": p, 
        "rows": rows, 
        "source": "yfinance"
    }

def get_stock_news(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """Return recent news articles for a ticker using yfinance with RSS fallback."""
    sym = (symbol or "").strip().upper()
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    # Serve from cache if available
    try:
        key = f"{sym}:{int(limit) if limit else 10}"
    except Exception:
        key = f"{sym}:10"
    if key in NEWS_CACHE:
        cached = NEWS_CACHE[key]
        try:
            if isinstance(cached, dict) and int(cached.get("count") or 0) == 0:
                del NEWS_CACHE[key]
            else:
                return cached
        except Exception:
            return cached

    items: List[Dict[str, Any]] = []
    # Primary: yfinance
    news_raw = None
    try:
        t = yf.Ticker(sym)
        news_raw = getattr(t, "news", None)
        if callable(news_raw):
            news_raw = news_raw()
    except Exception as e:
        logger.debug("yfinance news retrieval failed for %s: %s", sym, e)
        news_raw = None

    if news_raw:
        for n in news_raw[: max(1, int(limit))]:
            try:
                title = n.get("title") or n.get("headline")
                link = n.get("link") or n.get("url")
                publisher = n.get("publisher") or n.get("provider")
                ts = n.get("providerPublishTime") or n.get("published_at") or n.get("publishTime")
                if isinstance(ts, (int, float)):
                    try:
                        published_at = datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
                    except Exception:
                        published_at = str(ts)
                else:
                    published_at = str(ts) if ts else None

                thumb = None
                try:
                    if isinstance(n.get("thumbnail"), dict):
                        res = (n.get("thumbnail") or {}).get("resolutions") or []
                        if res:
                            thumb = res[0].get("url")
                except Exception:
                    thumb = None

                item = {
                    "uuid": n.get("uuid") or n.get("id"),
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "published_at": published_at,
                    "type": n.get("type") or "yfinance",
                    "related_tickers": n.get("relatedTickers") or n.get("related_tickers") or [sym],
                    "thumbnail": thumb,
                }
                if item["title"] and item["link"]:
                    items.append(item)
            except Exception:
                continue

    # Fallback: Yahoo Finance RSS if yfinance returned nothing
    if not items:
        try:
            from urllib.parse import urlparse
            rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote(sym)}&region=US&lang=en-US"
            feed = feedparser.parse(rss_url)
            for e in (feed.entries or [])[: max(1, int(limit))]:
                try:
                    title = getattr(e, "title", None)
                    link = getattr(e, "link", None)
                    publisher = None
                    try:
                        publisher = (getattr(getattr(e, "source", None), "title", None)) or getattr(e, "author", None)
                    except Exception:
                        publisher = None
                    if not publisher and link:
                        try:
                            netloc = urlparse(link).netloc
                            publisher = netloc.replace("www.", "") if netloc else None
                        except Exception:
                            publisher = None

                    published_at = None
                    try:
                        pp = getattr(e, "published_parsed", None)
                        if pp:
                            published_at = datetime(*pp[:6], tzinfo=timezone.utc).isoformat()
                        else:
                            published_at = getattr(e, "published", None)
                    except Exception:
                        published_at = getattr(e, "published", None)

                    thumb = None
                    try:
                        media = getattr(e, "media_thumbnail", None) or getattr(e, "media_content", None)
                        if isinstance(media, list) and media:
                            thumb = media[0].get("url")
                        elif isinstance(media, dict):
                            thumb = media.get("url")
                    except Exception:
                        thumb = None

                    item = {
                        "uuid": getattr(e, "id", None) or getattr(e, "guid", None),
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                        "published_at": published_at,
                        "type": "rss",
                        "related_tickers": [sym],
                        "thumbnail": thumb,
                    }
                    if item["title"] and item["link"]:
                        items.append(item)
                except Exception:
                    continue
        except Exception as e:
            logger.debug("RSS fallback failed for %s: %s", sym, e)

    result = {"symbol": sym, "count": len(items), "items": items, "source": "yfinance+rss" if news_raw else "rss"}
    try:
        if items:
            NEWS_CACHE[key] = result
    except Exception:
        pass
    return result

def get_augmented_news(
    symbol: str,
    limit: int = 10,
    include_full_text: bool = True,
    include_rag: bool = True,  # Changed from False to True to match tool config
    rag_k: int = 3,
    max_chars: int = 6000,
    timeout: int = 8,
) -> Dict[str, Any]:
    """Get news with full article text extraction."""
    from app.services.rag_service import rag_search  # Import here to avoid circular imports
    
    sym = (symbol or "").strip().upper()
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    key = f"aug:{sym}:{int(limit) if limit else 10}:{int(include_full_text)}:{int(include_rag)}:{int(rag_k)}:{int(max_chars)}"
    if key in NEWS_CACHE:
        return NEWS_CACHE[key]

    base = get_stock_news(sym, limit=limit)
    items = base.get("items", [])

    enriched: List[Dict[str, Any]] = []
    for it in items:
        try:
            entry = dict(it)
            link = (entry.get("link") or "").strip()
            if include_full_text and link:
                extra = _extract_article(link, timeout=timeout, max_chars=max_chars)
                if extra.get("title") and not entry.get("title"):
                    entry["title"] = extra.get("title")
                entry["content"] = extra.get("content")
                if extra.get("error"):
                    entry["content_error"] = extra.get("error")
            if include_rag:
                q = f"{sym} news: {entry.get('title') or ''}"
                try:
                    rs = rag_search(q, k=int(rag_k))
                except Exception as e:
                    rs = {"enabled": False, "error": str(e), "results": []}
                cleaned = []
                for r in (rs.get("results") or [])[: int(rag_k)]:
                    cleaned.append({
                        "text": (r.get("text") or "")[:1000],
                        "metadata": r.get("metadata"),
                        "score": r.get("score"),
                    })
                entry["rag"] = {
                    "enabled": rs.get("enabled", False),
                    "count": len(cleaned),
                    "results": cleaned,
                }
            enriched.append(entry)
        except Exception:
            continue

    result = {
        "symbol": sym,
        "count": len(enriched),
        "items": enriched,
        "source": base.get("source", "yfinance/rss"),
        "augmented": True,
    }
    NEWS_CACHE[key] = result
    return result

def get_risk_assessment(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    rf_rate: Optional[float] = None,
    benchmark: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute risk metrics (volatility, Sharpe, max drawdown, VaR, beta) for a stock."""
    sym = (symbol or "").strip().upper()
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    hist = get_historical_prices(sym, period=period, interval=interval, auto_adjust=False)
    rows = hist.get("rows", [])
    if not rows or len(rows) < 3:
        return {
            "symbol": sym,
            "period": period,
            "interval": interval,
            "count": len(rows or []),
            "error": "insufficient data",
        }

    df = pd.DataFrame(rows)
    try:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        df = df.sort_values("date")
    except Exception:
        pass
    closes = pd.to_numeric(df["close"], errors="coerce").dropna()
    rets = closes.pct_change().dropna()

    if rets.empty:
        return {
            "symbol": sym,
            "period": period,
            "interval": interval,
            "count": len(rows or []),
            "error": "no returns computed",
        }

    # Daily metrics
    mean_daily = float(rets.mean())
    std_daily = float(rets.std(ddof=1)) if len(rets) > 1 else float("nan")
    TRADING_DAYS = 252.0
    vol_ann = float(std_daily * (TRADING_DAYS ** 0.5)) if std_daily == std_daily else None

    # Sharpe
    rf_annual = float(rf_rate) if rf_rate is not None else RISK_FREE_RATE
    rf_daily = rf_annual / TRADING_DAYS
    try:
        sharpe = ((mean_daily - rf_daily) / std_daily) * (TRADING_DAYS ** 0.5)
        sharpe_ratio = float(sharpe)
    except Exception:
        sharpe_ratio = None

    # Max drawdown
    cum = (1.0 + rets).cumprod()
    roll_max = cum.cummax()
    drawdown = (cum / roll_max) - 1.0
    try:
        max_dd = float(drawdown.min())
    except Exception:
        max_dd = None

    # Historical VaR at 95%
    try:
        var_95_daily = float(np.percentile(rets.values, 5))
    except Exception:
        var_95_daily = None

    # Beta vs benchmark
    beta = None
    bench_sym = None
    if (benchmark or "").strip():
        bench_sym = (benchmark or "").strip().upper()
        try:
            bhist = get_historical_prices(bench_sym, period=period, interval=interval, auto_adjust=False)
            brows = bhist.get("rows", [])
            if brows and len(brows) >= 3:
                bdf = pd.DataFrame(brows)
                try:
                    bdf["date"] = pd.to_datetime(bdf["date"], errors="coerce")
                    bdf = bdf.sort_values("date")
                except Exception:
                    pass
                bclose = pd.to_numeric(bdf["close"], errors="coerce").dropna()
                brets = bclose.pct_change().dropna()
                joined = pd.concat([rets.reset_index(drop=True), brets.reset_index(drop=True)], axis=1).dropna()
                joined.columns = ["asset", "bench"]
                if len(joined) > 1 and float(joined["bench"].var(ddof=1)) != 0.0:
                    cov = float(joined.cov().iloc[0, 1])
                    var_b = float(joined["bench"].var(ddof=1))
                    beta = cov / var_b
        except Exception:
            beta = None

    return {
        "symbol": sym,
        "period": period,
        "interval": interval,
        "count": int(len(rets)),
        "volatility_annualized": vol_ann,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_dd,
        "var_95_daily": var_95_daily,
        "beta": beta,
        "benchmark": bench_sym,
        "risk_free_rate": rf_annual,
        "source": "computed",
    }
