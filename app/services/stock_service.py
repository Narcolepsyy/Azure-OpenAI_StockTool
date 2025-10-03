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
from app.utils.connection_pool import connection_pool
# New imports for concurrency and thread-safe caching
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from app.utils.circuit_breaker import circuit_breaker, CircuitBreakerError, get_circuit_breaker
from app.utils.cache_manager import get_cache_manager, CacheType
from app.utils.request_deduplication import get_deduplication_manager, deduplicate_sync
from app.utils.performance_monitor import get_performance_monitor, monitor_performance

from app.core.config import (
    TICKER_RE, QUOTE_CACHE_SIZE, QUOTE_TTL_SECONDS, 
    NEWS_CACHE_SIZE, NEWS_TTL_SECONDS, RISK_FREE_RATE, NEWS_USER_AGENT,
    # New config knobs
    ARTICLE_CACHE_SIZE, ARTICLE_TTL_SECONDS,
    NEWS_FETCH_MAX_WORKERS, RAG_MAX_WORKERS,
    RAG_STRATEGY, RAG_MAX_PER_ITEM,
)

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for performance optimization
_WHITESPACE_PATTERN = re.compile(r"\s+")
_NEWLINE_PATTERN = re.compile(r"\n")

# Centralized cache and monitoring managers
cache_manager = get_cache_manager()
dedup_manager = get_deduplication_manager()
performance_monitor = get_performance_monitor()
# Thread-safe cache wrapper to avoid lock contention
class ThreadSafeCache:
    """A thread-safe wrapper around TTLCache to reduce lock contention."""
    
    def __init__(self, maxsize: int, ttl: int):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.RLock()
    
    def get(self, key, default=None):
        """Get item from cache in a thread-safe manner."""
        try:
            with self._lock:
                return self._cache.get(key, default)
        except Exception:
            return default
    
    def set(self, key, value):
        """Set item in cache in a thread-safe manner."""
        try:
            with self._lock:
                self._cache[key] = value
        except Exception:
            pass
    
    def __contains__(self, key):
        """Check if key exists in cache."""
        try:
            with self._lock:
                return key in self._cache
        except Exception:
            return False

# Use thread-safe cache wrapper
ARTICLE_CACHE = ThreadSafeCache(maxsize=ARTICLE_CACHE_SIZE, ttl=ARTICLE_TTL_SECONDS)

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
    # Fix common confusion: map "1d" period to "5d" (minimum valid period)
    "1d": "5d", "1 day": "5d", "one day": "5d", "today": "5d", "daily": "5d"
}

_NL_INTERVAL_MAP = {
    "daily": "1d", "day": "1d", "1 day": "1d", "one day": "1d",
    "weekly": "1wk", "week": "1wk", "monthly": "1mo", "month": "1mo",
    "hourly": "1h", "hour": "1h",
}

# Known symbol aliases (index and localized names)
_ALIAS_MAP = {
    # Nikkei 225
    "^N225": "^N225",
    "N225": "^N225",
    "NI225": "^N225",
    "NIKKEI": "^N225",
    "NIKKEI225": "^N225",
    "NIKKEI 225": "^N225",
    "日経": "^N225",
    "日経平均": "^N225",
    "日経平均株価": "^N225",
    
    # TOPIX
    "^TPX": "^TPX",
    "TPX": "^TPX",
    "TOPIX": "^TPX",
    "東証": "^TPX",
    
    # Japanese Banking Sector - Map to TOPIX Banks or use representative banks ETF
    # Note: Yahoo Finance doesn't have direct Japanese banking sector indices
    # Using major Japanese bank ETF or representative banking stocks instead
    "地域銀行セクター指数": "1615.T",  # TOPIX Banks ETF (if available) or use major regional bank
    "銀行セクター指数": "1615.T", 
    "地域銀行指数": "8359.T",  # Use Hachijuni Bank as regional bank representative
    "銀行セクター": "8355.T",  # Use major bank as sector representative
    "日本銀行セクター": "8306.T",  # Mitsubishi UFJ as major bank representative
    "JAPANESE REGIONAL BANKS": "8359.T",
    "JAPANESE BANKS SECTOR": "8306.T",
    
    # Alternative regional bank representatives
    "地方銀行": "8359.T",
    "REGIONAL BANKS JP": "8359.T",
}

def _normalize_symbol(raw: Optional[str]) -> str:
    """Normalize various user inputs to a valid Yahoo Finance symbol.

    - Trims and uppercases ASCII letters; keeps caret if present.
    - Maps common aliases (e.g., N225, 日経平均) to ^N225.
    - Leaves other symbols unchanged except for whitespace and case.
    """
    s = (raw or "").strip()
    if not s:
        return s
    # Keep original for unicode matching; also build uppercase ascii variant
    s_upper = s.upper()
    # Direct alias hit first (handles Japanese keys)
    if s in _ALIAS_MAP:
        return _ALIAS_MAP[s]
    if s_upper in _ALIAS_MAP:
        return _ALIAS_MAP[s_upper]
    # If starts with caret already, just uppercase rest
    if s.startswith("^"):
        return "^" + s[1:].upper()
    # No alias: return uppercased string
    return s_upper

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

def _fill_missing_quarterly_earnings(symbol: str, quarterly_earnings_list: list) -> list:
    """Fill missing quarterly earnings by calculating from EPS data when available."""
    import math
    
    try:
        # Get financials to access EPS data
        financials = get_financials(symbol, freq="quarterly")
        income_statement = financials.get('income_statement', {})
        
        if not income_statement:
            return quarterly_earnings_list
        
        # Create a map of existing earnings data
        earnings_map = {}
        for item in quarterly_earnings_list:
            quarter = item.get('Quarter')
            earnings = item.get('Earnings')
            if quarter and earnings is not None and not (isinstance(earnings, float) and math.isnan(earnings)):
                earnings_map[quarter] = earnings
        
        # Check each period in financials and calculate missing earnings
        for date_str, period_data in income_statement.items():
            if not isinstance(period_data, dict):
                continue
                
            # Convert date to quarter format (YYYYQX)
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                quarter = f"{date_obj.year}Q{(date_obj.month-1)//3+1}"
            except:
                continue
            
            # Skip if we already have earnings data for this quarter
            if quarter in earnings_map:
                continue
            
            # Try to calculate earnings from EPS × shares
            eps = period_data.get('Diluted EPS') or period_data.get('Basic EPS')
            shares = period_data.get('Diluted Average Shares') or period_data.get('Basic Average Shares')
            
            if eps is not None and shares is not None and not math.isnan(eps) and not math.isnan(shares):
                calculated_earnings = eps * shares
                
                # Add calculated earnings to the list
                new_item = {'Quarter': quarter, 'Earnings': calculated_earnings}
                
                # Insert in correct chronological order (newest first)
                inserted = False
                for i, existing_item in enumerate(quarterly_earnings_list):
                    existing_quarter = existing_item.get('Quarter', '')
                    if existing_quarter < quarter:
                        quarterly_earnings_list.insert(i, new_item)
                        inserted = True
                        break
                
                if not inserted:
                    quarterly_earnings_list.append(new_item)
                    
                logger.info(f"Calculated missing earnings for {symbol} {quarter}: {calculated_earnings:,.0f} from EPS ({eps}) × shares ({shares:,.0f})")
        
        # Remove duplicates, keeping entries with valid earnings data
        seen_quarters = set()
        deduplicated_list = []
        
        for item in quarterly_earnings_list:
            quarter = item.get('Quarter')
            earnings = item.get('Earnings')
            
            if not quarter:
                continue
                
            if quarter not in seen_quarters:
                seen_quarters.add(quarter)
                deduplicated_list.append(item)
            elif earnings is not None and not (isinstance(earnings, float) and math.isnan(earnings)):
                # Replace existing entry if this one has valid earnings
                for i, existing in enumerate(deduplicated_list):
                    if existing.get('Quarter') == quarter:
                        existing_earnings = existing.get('Earnings')
                        if existing_earnings is None or (isinstance(existing_earnings, float) and math.isnan(existing_earnings)):
                            deduplicated_list[i] = item
                        break
        
        return deduplicated_list
        
    except Exception as e:
        logger.warning(f"Failed to fill missing quarterly earnings for {symbol}: {e}")
        return quarterly_earnings_list

def _extract_article(url: str, timeout: int = 8, max_chars: int = 6000) -> Dict[str, Any]:
    """Fetch and extract the main article text from a URL with caching.

    Caches successful extractions keyed by (url, max_chars) to avoid repeat network + parsing.
    """
    if not (url or '').strip():
        return {"content": None}

    key = ((url or '').strip(), int(max_chars) if isinstance(max_chars, int) else None)
    
    # Check cache first using thread-safe method
    if key in ARTICLE_CACHE:
        cached = ARTICLE_CACHE.get(key)
        if cached:
            # Return a shallow copy to avoid accidental mutation by callers
            return dict(cached) if isinstance(cached, dict) else cached

    try:
        session = connection_pool.get_sync_session()
        resp = session.get(url, headers={"User-Agent": NEWS_USER_AGENT}, timeout=max(2, int(timeout)))
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
            # Normalize whitespace without using get_text args flagged by linter
            raw = soup.get_text()
            text = _WHITESPACE_PATTERN.sub(" ", (raw or "")).strip()
        except Exception:
            text = _WHITESPACE_PATTERN.sub(" ", _NEWLINE_PATTERN.sub(" ", content_html or ""))
        text = (text or "").strip()
        if max_chars and isinstance(max_chars, int) and max_chars > 0 and len(text) > max_chars:
            text = text[:max_chars] + "..."
        if text:
            result = {"title": title, "content": text}
            # Cache the result using thread-safe method
            ARTICLE_CACHE.set(key, dict(result))
            return result
    except Exception:
        pass

    # Fallback: BeautifulSoup plain text
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        # Remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        raw = soup.get_text()
        text = _WHITESPACE_PATTERN.sub(" ", raw or "").strip()
        if max_chars and isinstance(max_chars, int) and 0 < max_chars < len(text):
            text = text[:max_chars] + "..."
        result = {"content": text}
        # Cache the result using thread-safe method
        ARTICLE_CACHE.set(key, dict(result))
        return result
    except Exception as e:
        return {"content": None, "error": f"parse_failed: {e}"}

def _safe_float(value: Any) -> Optional[float]:
    """Coerce a value to float if possible, guarding against NaN/inf."""
    try:
        if value is None:
            return None
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return None
        if isinstance(value, (int, np.integer)):
            return float(value)
        if isinstance(value, (np.floating,)):
            val = float(value)
            if np.isnan(val) or np.isinf(val):
                return None
            return val
        val = float(value)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    except Exception:
        return None

def _safe_int(value: Any) -> Optional[int]:
    """Coerce a value to int if possible, guarding against NaN."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, np.integer)):
            return int(value)
        if isinstance(value, (float, np.floating)):
            if np.isnan(value) or np.isinf(value):
                return None
            return int(round(float(value)))
        return int(value)
    except Exception:
        return None

def _to_timestamp_str(value: Any) -> Optional[str]:
    """Normalize timestamps to ISO 8601 strings with 'T' separator."""
    if value is None:
        return None
    try:
        if hasattr(value, "to_pydatetime"):
            dt = value.to_pydatetime()
        elif isinstance(value, datetime):
            dt = value
        else:
            return str(value)
        iso = dt.isoformat()
        return iso.replace(" ", "T")
    except Exception:
        try:
            return str(value)
        except Exception:
            return None

def _history_to_points(df: Optional[pd.DataFrame], limit: int = 600) -> List[Dict[str, Any]]:
    """Convert a historical DataFrame into a compact list of data points."""
    if df is None or df.empty:
        return []

    try:
        data = df.sort_index()
    except Exception:
        data = df

    length = len(data)
    if limit and length > limit:
        step = max(1, length // limit)
        data = data.iloc[::step]

    points: List[Dict[str, Any]] = []
    for idx, row in data.iterrows():
        close_val = _safe_float(row.get("Close"))
        if close_val is None:
            continue
        point = {
            "time": _to_timestamp_str(idx),
            "close": close_val,
        }
        open_val = _safe_float(row.get("Open"))
        high_val = _safe_float(row.get("High"))
        low_val = _safe_float(row.get("Low"))
        volume_val = _safe_int(row.get("Volume"))
        if open_val is not None:
            point["open"] = open_val
        if high_val is not None:
            point["high"] = high_val
        if low_val is not None:
            point["low"] = low_val
        if volume_val is not None:
            point["volume"] = volume_val
        points.append(point)

    return points

def _filter_by_start(df: Optional[pd.DataFrame], start: Optional[pd.Timestamp]) -> Optional[pd.DataFrame]:
    """Return subset of dataframe from start timestamp inclusive."""
    if df is None or df.empty or start is None:
        return df
    try:
        return df.loc[df.index >= start]
    except Exception:
        return df

def _build_price_chart(ticker: Any) -> Dict[str, Any]:
    """Build multi-range chart data for price visualization."""
    ranges: List[Dict[str, Any]] = []
    timezone_name: Optional[str] = None

    def _append_range(
        key: str,
        label: str,
        df: Optional[pd.DataFrame],
        period: str,
        interval: str,
        limit: int,
    ) -> None:
        nonlocal timezone_name
        if df is None or df.empty:
            return
        points = _history_to_points(df, limit=limit)
        if not points:
            return
        idx = getattr(df, "index", None)
        start = None
        end = None
        if idx is not None and len(idx) > 0:
            start = _to_timestamp_str(idx[0])
            end = _to_timestamp_str(idx[-1])
            if timezone_name is None:
                tz = getattr(idx, "tz", None)
                if tz is not None:
                    try:
                        timezone_name = getattr(tz, "zone", None) or tz.tzname(idx[-1])
                    except Exception:
                        timezone_name = None
        ranges.append({
            "key": key,
            "label": label,
            "period": period,
            "interval": interval,
            "start": start,
            "end": end,
            "points": points,
        })

    intraday = None
    try:
        intraday = ticker.history(period="5d", interval="5m", auto_adjust=False)
    except Exception:
        intraday = None

    if intraday is not None and not intraday.empty:
        try:
            intraday = intraday.sort_index()
            last_date = intraday.index[-1].date()
            same_day = intraday.loc[intraday.index.date == last_date]
        except Exception:
            same_day = intraday
        _append_range("1d", "1D", same_day, "1d", "5m", limit=400)
        _append_range("5d", "5D", intraday, "5d", "5m", limit=600)

    daily = None
    try:
        daily = ticker.history(period="1y", interval="1d", auto_adjust=False)
    except Exception:
        daily = None

    if daily is not None and not daily.empty:
        daily = daily.sort_index()
        last_idx = daily.index[-1]
        one_month_start = last_idx - pd.DateOffset(months=1)
        six_month_start = last_idx - pd.DateOffset(months=6)
        ytd_start = pd.Timestamp(year=last_idx.year, month=1, day=1, tz=last_idx.tz)

        _append_range("1m", "1M", _filter_by_start(daily, one_month_start), "1mo", "1d", limit=120)
        _append_range("6m", "6M", _filter_by_start(daily, six_month_start), "6mo", "1d", limit=180)
        _append_range("ytd", "YTD", _filter_by_start(daily, ytd_start), "ytd", "1d", limit=220)
        _append_range("1y", "1Y", daily, "1y", "1d", limit=260)

    five_year = None
    try:
        five_year = ticker.history(period="5y", interval="1wk", auto_adjust=False)
    except Exception:
        five_year = None

    if five_year is not None and not five_year.empty:
        five_year = five_year.sort_index()
        _append_range("5y", "5Y", five_year, "5y", "1wk", limit=260)

    max_hist = None
    try:
        max_hist = ticker.history(period="max", interval="1mo", auto_adjust=False)
    except Exception:
        max_hist = None

    if max_hist is not None and not max_hist.empty:
        max_hist = max_hist.sort_index()
        _append_range("max", "MAX", max_hist, "max", "1mo", limit=360)

    if not ranges:
        return {}

    default_key = "1d" if any(r.get("key") == "1d" for r in ranges) else ranges[0].get("key")
    chart: Dict[str, Any] = {
        "ranges": ranges,
        "default_range": default_key,
    }
    if timezone_name:
        chart["timezone"] = timezone_name
    return chart

@monitor_performance("stock_quote")
def get_stock_quote(symbol: str) -> Dict[str, Any]:
    """Return latest close price and meta for a ticker using Yahoo Finance with TTL cache."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    # Check cache first
    cached = cache_manager.get(CacheType.STOCK_QUOTES, sym)
    if cached is not None:
        logger.debug("cache hit for %s", sym)
        return cached

    ticker = yf.Ticker(sym)
    
    # Circuit breaker for Yahoo Finance API calls
    yf_breaker = get_circuit_breaker(
        "yahoo_finance_api",
        failure_threshold=5,
        recovery_timeout=120.0,
        expected_exception=(Exception,)
    )
    
    try:
        # Check if circuit breaker allows the call
        if yf_breaker.state.value == "open":
            raise CircuitBreakerError(f"Yahoo Finance API circuit breaker is open")
        
        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)
        # Record success manually for sync function
        yf_breaker._record_success()
    except Exception as e:
        # Record failure for circuit breaker
        yf_breaker._record_failure(e)
        raise ValueError(f"failed to retrieve data for '{sym}': {e}")

    if hist is None or hist.empty:
        raise ValueError(f"No price data found for symbol '{sym}'")

    last_row = hist.tail(1)
    close_val = _safe_float(last_row["Close"].iloc[0])
    if close_val is None:
        raise ValueError(f"invalid close price for symbol '{sym}'")

    as_of = _to_timestamp_str(last_row.index[-1])

    prev_close = None
    try:
        if len(hist) > 1:
            prev_close = _safe_float(hist["Close"].iloc[-2])
    except Exception:
        prev_close = None

    day_open = _safe_float(last_row["Open"].iloc[0])
    day_high = _safe_float(last_row["High"].iloc[0])
    day_low = _safe_float(last_row["Low"].iloc[0])
    volume = _safe_int(last_row["Volume"].iloc[0])

    currency = None
    try:
        fi = getattr(ticker, "fast_info", None) or {}
        currency = fi.get("currency") if isinstance(fi, dict) else None
    except Exception:
        currency = None

    info: Dict[str, Any] = {}
    try:
        info = ticker.get_info() or {}
    except Exception as info_err:
        logger.debug("get_info failed for %s: %s", sym, info_err)
        info = {}

    market_cap = _safe_int(info.get("marketCap"))
    shares_outstanding = _safe_int(info.get("sharesOutstanding"))
    year_high = _safe_float(info.get("fiftyTwoWeekHigh"))
    year_low = _safe_float(info.get("fiftyTwoWeekLow"))
    eps = _safe_float(info.get("trailingEps"))
    pe_ratio = _safe_float(info.get("trailingPE"))

    info_day_open = _safe_float(info.get("regularMarketOpen"))
    if info_day_open is not None:
        day_open = info_day_open
    info_day_low = _safe_float(info.get("dayLow"))
    if info_day_low is not None:
        day_low = info_day_low
    info_day_high = _safe_float(info.get("dayHigh"))
    if info_day_high is not None:
        day_high = info_day_high
    info_prev_close = _safe_float(info.get("regularMarketPreviousClose"))
    if info_prev_close is not None:
        prev_close = info_prev_close
    info_volume = _safe_int(info.get("regularMarketVolume"))
    if info_volume is not None:
        volume = info_volume

    if currency is None:
        currency = info.get("currency")

    change_abs = None
    change_pct = None
    if prev_close is not None and prev_close != 0:
        change_abs = close_val - prev_close
        change_pct = (change_abs / prev_close) * 100.0

    chart_data: Dict[str, Any] = {}
    try:
        chart_data = _build_price_chart(ticker)
    except Exception as chart_error:
        logger.debug("chart build failed for %s: %s", sym, chart_error)
        chart_data = {}

    result = {
        "symbol": sym,
        "price": round(close_val, 4),
        "currency": (currency or "USD"),
        "change": round(change_abs, 4) if change_abs is not None else None,
        "change_percent": round(change_pct, 4) if change_pct is not None else None,
        "previous_close": round(prev_close, 4) if prev_close is not None else None,
        "day_open": round(day_open, 4) if day_open is not None else None,
        "day_high": round(day_high, 4) if day_high is not None else None,
        "day_low": round(day_low, 4) if day_low is not None else None,
        "volume": volume,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "year_high": round(year_high, 4) if year_high is not None else None,
        "year_low": round(year_low, 4) if year_low is not None else None,
        "eps": round(eps, 4) if eps is not None else None,
        "pe_ratio": round(pe_ratio, 4) if pe_ratio is not None else None,
        "as_of": as_of,
        "source": "yfinance",
    }

    if chart_data:
        result["chart"] = chart_data

    cache_manager.set(CacheType.STOCK_QUOTES, sym, result)
    return result

def get_company_profile(symbol: str) -> Dict[str, Any]:
    """Return company profile details for a ticker using yfinance."""
    sym = _normalize_symbol(symbol)
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
        "market_cap": info.get("marketCap"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "float_shares": info.get("floatShares"),
        "enterprise_value": info.get("enterpriseValue"),
        "book_value": info.get("bookValue"),
        "market_to_book": info.get("priceToBook"),
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
    sym = _normalize_symbol(symbol)
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
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    # Serve from cache if available
    try:
        key = f"{sym}:{int(limit) if limit else 10}"
    except Exception:
        key = f"{sym}:10"
    cached = cache_manager.get(CacheType.STOCK_NEWS, key)
    if cached is not None:
        try:
            if isinstance(cached, dict) and int(cached.get("count") or 0) == 0:
                cache_manager.delete(CacheType.STOCK_NEWS, key)
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
            # Prefer JP region/lang for Nikkei ^N225, otherwise default to US/en
            region = "JP" if sym == "^N225" else "US"
            lang = "ja-JP" if sym == "^N225" else "en-US"
            rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote(sym)}&region={region}&lang={lang}"
            # Fetch RSS with timeout and UA to avoid hanging
            try:
                session = connection_pool.get_sync_session()
                resp = session.get(rss_url, headers={"User-Agent": NEWS_USER_AGENT}, timeout=5)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
            except Exception:
                # As a last resort, try direct parse (may be slower)
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

    # Last-resort: Google News RSS for Nikkei if still empty
    if not items and sym == "^N225":
        try:
            # Japanese Google News for better coverage
            gnews_url = "https://news.google.com/rss/search?q=%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%20OR%20Nikkei%20225&hl=ja&gl=JP&ceid=JP:ja"
            session = connection_pool.get_sync_session()
            resp = session.get(gnews_url, headers={"User-Agent": NEWS_USER_AGENT}, timeout=5)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for e in (feed.entries or [])[: max(1, int(limit))]:
                try:
                    title = getattr(e, "title", None)
                    link = getattr(e, "link", None)
                    published_at = None
                    try:
                        pp = getattr(e, "published_parsed", None)
                        if pp:
                            published_at = datetime(*pp[:6], tzinfo=timezone.utc).isoformat()
                        else:
                            published_at = getattr(e, "published", None)
                    except Exception:
                        published_at = getattr(e, "published", None)

                    item = {
                        "uuid": getattr(e, "id", None) or getattr(e, "guid", None),
                        "title": title,
                        "publisher": None,
                        "link": link,
                        "published_at": published_at,
                        "type": "google-news-rss",
                        "related_tickers": [sym],
                        "thumbnail": None,
                    }
                    if item["title"] and item["link"]:
                        items.append(item)
                except Exception:
                    continue
        except Exception as e:
            logger.debug("Google News fallback failed for %s: %s", sym, e)

    result = {"symbol": sym, "count": len(items), "items": items, "source": "yfinance+rss" if news_raw else "rss"}
    try:
        if items:
            cache_manager.set(CacheType.STOCK_NEWS, key, result)
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
    """Get news with full article text extraction, parallelized and cached for speed."""
    from app.services.rag_service import rag_search  # Import here to avoid circular imports
    
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    key = f"aug:{sym}:{int(limit) if limit else 10}:{int(include_full_text)}:{int(include_rag)}:{int(rag_k)}:{int(max_chars)}"
    cached = cache_manager.get(CacheType.STOCK_NEWS, key)
    if cached is not None:
        return cached

    base = get_stock_news(sym, limit=limit)
    items = base.get("items", [])

    # Prepare baseline entries
    enriched: List[Dict[str, Any]] = [dict(it) for it in items]

    # Stage 1: Parallel article extraction
    if include_full_text:
        futures_map = {}
        with ThreadPoolExecutor(max_workers=max(1, int(NEWS_FETCH_MAX_WORKERS))) as executor:
            for idx, entry in enumerate(enriched):
                link = (entry.get("link") or "").strip()
                if not link:
                    continue
                futures_map[executor.submit(_extract_article, link, timeout=timeout, max_chars=max_chars)] = idx
            for fut in as_completed(futures_map):
                idx = futures_map[fut]
                try:
                    extra = fut.result()
                    if isinstance(extra, dict):
                        if extra.get("title") and not enriched[idx].get("title"):
                            enriched[idx]["title"] = extra.get("title")
                        enriched[idx]["content"] = extra.get("content")
                        if extra.get("error"):
                            enriched[idx]["content_error"] = extra.get("error")
                except Exception as e:
                    enriched[idx]["content_error"] = f"extract_exception: {e}"

    # Stage 2: RAG retrievals (strategy-based)
    if include_rag:
        strategy = (RAG_STRATEGY or "symbol").strip().lower()
        # Auto: use per-item when few items, otherwise one symbol query
        if strategy == "auto":
            strategy = "item" if len(enriched) <= max(1, int(RAG_MAX_PER_ITEM)) else "symbol"

        if strategy == "symbol":
            # One query for all items
            q = f"{sym} latest company news and updates"
            try:
                rs = rag_search(q, int(rag_k))
            except Exception as e:
                rs = {"enabled": False, "error": str(e), "results": []}
            cleaned = []
            for r in (rs.get("results") or [])[: int(rag_k)]:
                try:
                    cleaned.append({
                        "text": (r.get("text") or "")[:1000],
                        "metadata": r.get("metadata"),
                        "score": r.get("score"),
                    })
                except Exception:
                    continue
            for idx in range(len(enriched)):
                enriched[idx]["rag"] = {
                    "enabled": rs.get("enabled", False),
                    "count": len(cleaned),
                    "results": cleaned,
                }
        else:
            # Per-item, optionally cap to RAG_MAX_PER_ITEM
            rag_futures = {}
            with ThreadPoolExecutor(max_workers=max(1, int(RAG_MAX_WORKERS))) as executor:
                # Determine which indices to enrich (cap if configured)
                indices = list(range(len(enriched)))
                max_items = int(RAG_MAX_PER_ITEM) if RAG_MAX_PER_ITEM and RAG_MAX_PER_ITEM > 0 else len(indices)
                for idx in indices[:max_items]:
                    entry = enriched[idx]
                    title = (entry.get("title") or "").strip()
                    if not title:
                        enriched[idx]["rag"] = {"enabled": False, "count": 0, "results": []}
                        continue
                    q = f"{sym} news: {title}"
                    rag_futures[executor.submit(rag_search, q, int(rag_k))] = idx
                for fut in as_completed(rag_futures):
                    idx = rag_futures[fut]
                    try:
                        rs = fut.result()
                    except Exception as e:
                        rs = {"enabled": False, "error": str(e), "results": []}
                    cleaned = []
                    for r in (rs.get("results") or [])[: int(rag_k)]:
                        try:
                            cleaned.append({
                                "text": (r.get("text") or "")[:1000],
                                "metadata": r.get("metadata"),
                                "score": r.get("score"),
                            })
                        except Exception:
                            continue
                    enriched[idx]["rag"] = {
                        "enabled": rs.get("enabled", False),
                        "count": len(cleaned),
                        "results": cleaned,
                    }
                # For any remaining items not enriched (if capped), attach empty rag
                for idx in indices[max_items:]:
                    enriched[idx]["rag"] = {"enabled": False, "count": 0, "results": []}

    result = {
        "symbol": sym,
        "count": len(enriched),
        "items": enriched,
        "source": base.get("source", "yfinance/rss"),
        "augmented": True,
    }
    try:
        cache_manager.set(CacheType.STOCK_NEWS, key, result)
    except Exception:
        pass
    return result

def get_risk_assessment(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    rf_rate: Optional[float] = None,
    benchmark: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute risk metrics (volatility, Sharpe, max drawdown, VaR, beta) for a stock."""
    sym = _normalize_symbol(symbol)
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
                    bdf["date"] = pd.to_datetime(bdf["date"], errors="coerce", utc=True)
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

def _analyze_sentiment_simple(text: str) -> str:
    """Simple sentiment analysis for Japanese/English financial news using keyword matching."""
    if not text:
        return "neutral"
    
    text_lower = text.lower()
    
    # Japanese positive keywords
    jp_positive = ["上昇", "急騰", "好調", "増加", "プラス", "回復", "改善", "成長", "拡大", "好材料", "買い"]
    # Japanese negative keywords  
    jp_negative = ["下落", "急落", "悪化", "減少", "マイナス", "低下", "縮小", "悪材料", "売り", "損失", "赤字"]
    
    # English positive keywords
    en_positive = ["rise", "surge", "gain", "up", "increase", "growth", "positive", "strong", "bullish", "buy", "improve"]
    # English negative keywords
    en_negative = ["fall", "drop", "decline", "down", "decrease", "loss", "negative", "weak", "bearish", "sell", "worsen"]
    
    positive_count = 0
    negative_count = 0
    
    # Count Japanese keywords
    for word in jp_positive:
        if word in text:
            positive_count += 1
    for word in jp_negative:
        if word in text:
            negative_count += 1
            
    # Count English keywords
    for word in en_positive:
        if word in text_lower:
            positive_count += 1
    for word in en_negative:
        if word in text_lower:
            negative_count += 1
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"

def get_nikkei_news_with_sentiment(limit: int = 5) -> Dict[str, Any]:
    """Get recent Nikkei 225 news headlines with 1-sentence summaries and sentiment analysis."""
    from app.services.openai_client import get_client_for_model
    
    try:
        # Fetch Nikkei news using existing infrastructure
        news_data = get_augmented_news("^N225", limit=limit, include_full_text=True, include_rag=False)
        items = news_data.get("items", [])
        
        if not items:
            return {
                "symbol": "^N225",
                "count": 0,
                "summaries": [],
                "error": "日経平均（N225）の最新ニュースヘッドラインが取得できませんでした"
            }
        
        # Process each news item
        processed_items = []
        
        for item in items[:limit]:
            title = item.get("title", "")
            content = item.get("content", "")
            publisher = item.get("publisher", "")
            published_at = item.get("published_at", "")
            
            # Create one-sentence summary
            summary_text = title
            if content and len(content) > len(title):
                # Use first sentence of content or truncate
                sentences = content.split("。")  # Japanese sentence delimiter
                if not sentences[0]:
                    sentences = content.split(".")  # English fallback
                if sentences and len(sentences[0].strip()) > 10:
                    summary_text = sentences[0].strip()
                    if not summary_text.endswith("。") and not summary_text.endswith("."):
                        summary_text += "。"
                else:
                    summary_text = content[:100] + "..." if len(content) > 100 else content
            
            # Analyze sentiment using both title and content
            full_text = f"{title} {content}"
            sentiment = _analyze_sentiment_simple(full_text)
            
            # Format sentiment in Japanese
            sentiment_jp = {
                "positive": "ポジティブ", 
                "negative": "ネガティブ", 
                "neutral": "ニュートラル"
            }.get(sentiment, "ニュートラル")
            
            processed_items.append({
                "title": title,
                "summary": summary_text,
                "sentiment": sentiment,
                "sentiment_jp": sentiment_jp,
                "publisher": publisher,
                "published_at": published_at[:10] if published_at else "",
                "link": item.get("link", "")
            })
        
        return {
            "symbol": "^N225",
            "count": len(processed_items),
            "summaries": processed_items,
            "source": "yfinance+sentiment"
        }
        
    except Exception as e:
        logger.error(f"Error fetching Nikkei news with sentiment: {e}")
        return {
            "symbol": "^N225", 
            "count": 0,
            "summaries": [],
            "error": f"ニュース取得エラー: {str(e)}"
        }

def get_financials(symbol: str, freq: str = "quarterly") -> Dict[str, Any]:
    """Get comprehensive financial statements (income statement, balance sheet, cash flow)."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    ticker = yf.Ticker(sym)
    
    try:
        # Get financial data based on frequency
        if freq.lower() in ["quarterly", "q"]:
            income_stmt = ticker.quarterly_financials
            balance_sheet = ticker.quarterly_balance_sheet
            cash_flow = ticker.quarterly_cashflow
        else:  # annual
            income_stmt = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow
        
        # Convert to dictionary format for JSON serialization
        def df_to_dict(df):
            if df is None or df.empty:
                return {}
            # Convert to dict with date strings as keys
            result = {}
            for col in df.columns:
                date_key = str(col.date()) if hasattr(col, 'date') else str(col)
                result[date_key] = {}
                for idx in df.index:
                    value = df.loc[idx, col]
                    if pd.notna(value):
                        result[date_key][str(idx)] = float(value) if isinstance(value, (int, float)) else str(value)
            return result
        
        currency = None
        try:
            fi = getattr(ticker, "fast_info", None) or {}
            currency = fi.get("currency") if isinstance(fi, dict) else None
        except Exception:
            currency = None

        return {
            "symbol": sym,
            "frequency": freq,
            "currency": currency or "USD",
            "income_statement": df_to_dict(income_stmt),
            "balance_sheet": df_to_dict(balance_sheet), 
            "cash_flow": df_to_dict(cash_flow),
            "source": "yfinance"
        }
        
    except Exception as e:
        return {
            "symbol": sym,
            "frequency": freq,
            "error": f"Failed to retrieve financials: {str(e)}",
            "source": "yfinance"
        }

def get_earnings_data(symbol: str) -> Dict[str, Any]:
    """Get earnings history, estimates, and calendar data."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    ticker = yf.Ticker(sym)
    
    try:
        # Get earnings data - use income_stmt instead of deprecated earnings
        # Extract Net Income from financial statements
        annual_income_stmt = ticker.financials
        quarterly_income_stmt = ticker.quarterly_financials
        
        # Convert income statements to earnings-like format
        earnings = None
        quarterly_earnings = None
        
        # Extract Net Income from annual financials
        if annual_income_stmt is not None and not annual_income_stmt.empty:
            try:
                # Look for Net Income row
                net_income_rows = [idx for idx in annual_income_stmt.index if 'net income' in str(idx).lower() or 'net earnings' in str(idx).lower()]
                if net_income_rows:
                    net_income_row = net_income_rows[0]
                    earnings_data = annual_income_stmt.loc[net_income_row]
                    # Convert to DataFrame with Year and Earnings columns
                    earnings = pd.DataFrame({
                        'Year': [col.year for col in earnings_data.index],
                        'Earnings': earnings_data.values
                    }).set_index('Year')
            except Exception:
                earnings = None
        
        # Extract Net Income from quarterly financials
        if quarterly_income_stmt is not None and not quarterly_income_stmt.empty:
            try:
                net_income_rows = [idx for idx in quarterly_income_stmt.index if 'net income' in str(idx).lower() or 'net earnings' in str(idx).lower()]
                if net_income_rows:
                    net_income_row = net_income_rows[0]
                    quarterly_data = quarterly_income_stmt.loc[net_income_row]
                    # Convert to DataFrame with Quarter and Earnings columns
                    quarterly_earnings = pd.DataFrame({
                        'Quarter': [f"{col.year}Q{(col.month-1)//3+1}" for col in quarterly_data.index],
                        'Earnings': quarterly_data.values
                    }).set_index('Quarter')
            except Exception:
                quarterly_earnings = None
        
        earnings_dates = ticker.earnings_dates
        
        def df_to_records(df):
            if df is None or df.empty:
                return []
            # Reset index and convert to records, handling date serialization
            df_copy = df.reset_index()
            # Convert datetime columns to strings for JSON serialization
            for col in df_copy.columns:
                if hasattr(df_copy[col].dtype, 'name') and 'datetime' in str(df_copy[col].dtype):
                    df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d')
                elif df_copy[col].dtype == 'object':
                    # Check if column contains datetime-like objects
                    try:
                        sample = df_copy[col].dropna().iloc[0] if len(df_copy[col].dropna()) > 0 else None
                        if hasattr(sample, 'strftime'):
                            df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
                    except:
                        pass
            return df_copy.to_dict('records')
        
        currency = None
        try:
            fi = getattr(ticker, "fast_info", None) or {}
            currency = fi.get("currency") if isinstance(fi, dict) else None
        except Exception:
            currency = None

        # Fill missing quarterly earnings by calculating from EPS data when available
        quarterly_earnings_list = df_to_records(quarterly_earnings)
        quarterly_earnings_list = _fill_missing_quarterly_earnings(sym, quarterly_earnings_list)

        return {
            "symbol": sym,
            "currency": currency or "USD",
            "annual_earnings": df_to_records(earnings),
            "quarterly_earnings": quarterly_earnings_list,
            "earnings_calendar": df_to_records(earnings_dates),
            "source": "yfinance"
        }
        
    except Exception as e:
        return {
            "symbol": sym,
            "error": f"Failed to retrieve earnings data: {str(e)}",
            "source": "yfinance"
        }

def get_analyst_recommendations(symbol: str) -> Dict[str, Any]:
    """Get analyst recommendations, price targets, and upgrades/downgrades."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    ticker = yf.Ticker(sym)
    
    try:
        recommendations = ticker.recommendations
        upgrades_downgrades = ticker.upgrades_downgrades
        
        def df_to_records(df):
            if df is None or df.empty:
                return []
            return df.reset_index().to_dict('records')
        
        # Get current price for context
        try:
            info = ticker.get_info()
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            target_high = info.get('targetHighPrice')
            target_low = info.get('targetLowPrice')
            target_mean = info.get('targetMeanPrice')
            target_median = info.get('targetMedianPrice')
            recommendation_mean = info.get('recommendationMean')
        except Exception:
            current_price = target_high = target_low = target_mean = target_median = recommendation_mean = None
        
        currency = None
        try:
            fi = getattr(ticker, "fast_info", None) or {}
            currency = fi.get("currency") if isinstance(fi, dict) else None
        except Exception:
            currency = None

        return {
            "symbol": sym,
            "currency": currency or "USD",
            "current_price": current_price,
            "price_targets": {
                "high": target_high,
                "low": target_low,
                "mean": target_mean,
                "median": target_median
            },
            "recommendation_mean": recommendation_mean,
            "recommendations_history": df_to_records(recommendations),
            "upgrades_downgrades": df_to_records(upgrades_downgrades),
            "source": "yfinance"
        }
        
    except Exception as e:
        return {
            "symbol": sym,
            "error": f"Failed to retrieve analyst data: {str(e)}",
            "source": "yfinance"
        }

def get_institutional_holders(symbol: str) -> Dict[str, Any]:
    """Get institutional and mutual fund holders data."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    ticker = yf.Ticker(sym)
    
    try:
        institutional_holders = ticker.institutional_holders
        mutualfund_holders = ticker.mutualfund_holders
        major_holders = ticker.major_holders
        
        def df_to_records(df):
            if df is None or df.empty:
                return []
            return df.to_dict('records')
        
        return {
            "symbol": sym,
            "institutional_holders": df_to_records(institutional_holders),
            "mutualfund_holders": df_to_records(mutualfund_holders),
            "major_holders": df_to_records(major_holders),
            "source": "yfinance"
        }
        
    except Exception as e:
        return {
            "symbol": sym,
            "error": f"Failed to retrieve holders data: {str(e)}",
            "source": "yfinance"
        }

def get_dividends_splits(symbol: str, period: str = "1y") -> Dict[str, Any]:
    """Get dividend and stock split history."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    ticker = yf.Ticker(sym)
    
    try:
        # Get dividend and split data
        dividends = ticker.dividends
        splits = ticker.splits
        
        # Filter by period if specified
        if period != "max":
            p = _normalize_period(period)
            try:
                end_date = pd.Timestamp.now()
                if p == "1y":
                    start_date = end_date - pd.DateOffset(years=1)
                elif p == "2y":
                    start_date = end_date - pd.DateOffset(years=2)
                elif p == "5y":
                    start_date = end_date - pd.DateOffset(years=5)
                elif p == "6mo":
                    start_date = end_date - pd.DateOffset(months=6)
                elif p == "3mo":
                    start_date = end_date - pd.DateOffset(months=3)
                elif p == "1mo":
                    start_date = end_date - pd.DateOffset(months=1)
                else:
                    start_date = None
                
                if start_date:
                    dividends = dividends[dividends.index >= start_date]
                    splits = splits[splits.index >= start_date]
            except Exception:
                pass  # Use all data if filtering fails
        
        def series_to_records(series):
            if series is None or series.empty:
                return []
            return [{"date": str(idx.date()), "value": float(val)} for idx, val in series.items()]
        
        currency = None
        try:
            fi = getattr(ticker, "fast_info", None) or {}
            currency = fi.get("currency") if isinstance(fi, dict) else None
        except Exception:
            currency = None

        return {
            "symbol": sym,
            "period": period,
            "currency": currency or "USD", 
            "dividends": series_to_records(dividends),
            "splits": series_to_records(splits),
            "dividend_count": len(dividends),
            "split_count": len(splits),
            "source": "yfinance"
        }
        
    except Exception as e:
        return {
            "symbol": sym,
            "period": period,
            "error": f"Failed to retrieve dividend/split data: {str(e)}",
            "source": "yfinance"
        }

def get_market_indices(region: str = "global") -> Dict[str, Any]:
    """Get major market indices data (S&P500, Nasdaq, Nikkei, etc.)."""
    
    # Define major indices by region
    indices_map = {
        "us": {
            "^GSPC": "S&P 500",
            "^IXIC": "NASDAQ Composite", 
            "^DJI": "Dow Jones Industrial Average",
            "^RUT": "Russell 2000"
        },
        "japan": {
            "^N225": "Nikkei 225",
            "^TPX": "TOPIX"
        },
        "europe": {
            "^FTSE": "FTSE 100",
            "^GDAXI": "DAX",
            "^FCHI": "CAC 40"
        },
        "asia": {
            "^HSI": "Hang Seng Index",
            "000001.SS": "Shanghai Composite",
            "^STI": "Straits Times Index",
            "^KOSPI": "KOSPI"
        },
        "global": {
            "^GSPC": "S&P 500",
            "^IXIC": "NASDAQ",
            "^DJI": "Dow Jones",
            "^N225": "Nikkei 225",
            "^FTSE": "FTSE 100",
            "^GDAXI": "DAX"
        }
    }
    
    region_lower = region.lower()
    if region_lower not in indices_map:
        region_lower = "global"
    
    indices = indices_map[region_lower]
    results = []
    
    for symbol, name in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current price
            hist = ticker.history(period="2d", interval="1d")
            if hist is None or hist.empty:
                continue
                
            latest = hist.tail(1)
            current_price = float(latest["Close"].iloc[0])
            
            # Calculate change from previous day
            change = None
            change_pct = None
            if len(hist) >= 2:
                previous = hist.iloc[-2]
                prev_close = float(previous["Close"])
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100
            
            # Get basic info
            currency = "USD"  # Most indices are in USD or local currency
            try:
                fi = getattr(ticker, "fast_info", None) or {}
                currency = fi.get("currency") if isinstance(fi, dict) else None
            except Exception:
                pass
            
            results.append({
                "symbol": symbol,
                "name": name,
                "price": round(current_price, 2),
                "change": round(change, 2) if change else None,
                "change_pct": round(change_pct, 2) if change_pct else None,
                "currency": currency or "USD",
                "as_of": str(latest.index[-1])
            })
            
        except Exception as e:
            logger.debug(f"Failed to get data for {symbol}: {e}")
            continue
    
    return {
        "region": region,
        "count": len(results),
        "indices": results,
        "source": "yfinance"
    }

def get_technical_indicators(symbol: str, period: str = "3mo", indicators: List[str] = None) -> Dict[str, Any]:
    """Calculate technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")
    
    # Default indicators if none specified
    if indicators is None:
        indicators = ["sma_20", "sma_50", "ema_12", "ema_26", "rsi_14", "macd", "bb_20"]
    
    # Auto-adjust period if too short for requested indicators
    max_period_needed = 0
    for indicator in indicators:
        if indicator.startswith(("sma_", "ema_", "bb_")):
            period_val = int(indicator.split("_")[1])
            max_period_needed = max(max_period_needed, period_val)
    
    # If period looks too short, auto-extend
    if max_period_needed >= 25 and period in ["1mo", "30d"]:
        period = "3mo"  # Auto-extend for better analysis
    
    try:
        # Get historical data
        hist_data = get_historical_prices(sym, period=period, interval="1d")
        rows = hist_data.get("rows", [])
        
        # Calculate minimum required days based on indicators
        min_required_days = 30  # Default minimum
        for indicator in indicators:
            if indicator.startswith("sma_") or indicator.startswith("ema_"):
                period_val = int(indicator.split("_")[1])
                min_required_days = max(min_required_days, period_val + 5)  # Add buffer
            elif indicator.startswith("bb_"):
                period_val = int(indicator.split("_")[1])
                min_required_days = max(min_required_days, period_val + 5)
        
        if len(rows) < min_required_days:
            # For Japanese users requesting short periods, suggest longer period
            suggested_period = "3mo" if period in ["1mo", "30d"] else "6mo"
            error_msg = f"データが不足しています（{len(rows)}日）。{min_required_days}日以上必要です。"
            if period in ["1mo", "30d"]:
                error_msg += f" より長い期間（{suggested_period}など）をお試しください。"
            
            return {
                "symbol": sym,
                "period": period,
                "actual_days": len(rows),
                "required_days": min_required_days,
                "suggested_period": suggested_period,
                "error": error_msg,
                "source": "yfinance"
            }
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        
        close_prices = df["close"].astype(float)
        high_prices = df["high"].astype(float)
        low_prices = df["low"].astype(float)
        volume = df["volume"].astype(float)
        
        results = {"symbol": sym, "period": period, "indicators": {}}
        
        for indicator in indicators:
            try:
                if indicator.startswith("sma_"):
                    period_val = int(indicator.split("_")[1])
                    sma = close_prices.rolling(window=period_val).mean()
                    results["indicators"][indicator] = {
                        "name": f"Simple Moving Average ({period_val})",
                        "current": float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None,
                        "values": [{"date": str(idx.date()), "value": float(val)} for idx, val in sma.dropna().tail(20).items()]
                    }
                
                elif indicator.startswith("ema_"):
                    period_val = int(indicator.split("_")[1])
                    ema = close_prices.ewm(span=period_val).mean()
                    results["indicators"][indicator] = {
                        "name": f"Exponential Moving Average ({period_val})",
                        "current": float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else None,
                        "values": [{"date": str(idx.date()), "value": float(val)} for idx, val in ema.dropna().tail(20).items()]
                    }
                
                elif indicator.startswith("rsi_"):
                    period_val = int(indicator.split("_")[1])
                    delta = close_prices.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=period_val).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=period_val).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    
                    current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
                    signal = "neutral"
                    if current_rsi:
                        if current_rsi > 70:
                            signal = "overbought"
                        elif current_rsi < 30:
                            signal = "oversold"
                    
                    results["indicators"][indicator] = {
                        "name": f"Relative Strength Index ({period_val})",
                        "current": current_rsi,
                        "signal": signal,
                        "values": [{"date": str(idx.date()), "value": float(val)} for idx, val in rsi.dropna().tail(20).items()]
                    }
                
                elif indicator == "macd":
                    ema_12 = close_prices.ewm(span=12).mean()
                    ema_26 = close_prices.ewm(span=26).mean()
                    macd_line = ema_12 - ema_26
                    signal_line = macd_line.ewm(span=9).mean()
                    histogram = macd_line - signal_line
                    
                    results["indicators"][indicator] = {
                        "name": "MACD (12,26,9)",
                        "current": {
                            "macd": float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None,
                            "signal": float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else None,
                            "histogram": float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else None
                        },
                        "values": [
                            {
                                "date": str(idx.date()),
                                "macd": float(macd_line.loc[idx]) if not pd.isna(macd_line.loc[idx]) else None,
                                "signal": float(signal_line.loc[idx]) if not pd.isna(signal_line.loc[idx]) else None,
                                "histogram": float(histogram.loc[idx]) if not pd.isna(histogram.loc[idx]) else None
                            }
                            for idx in macd_line.dropna().tail(20).index
                        ]
                    }
                
                elif indicator.startswith("bb_"):
                    period_val = int(indicator.split("_")[1])
                    sma = close_prices.rolling(window=period_val).mean()
                    std = close_prices.rolling(window=period_val).std()
                    upper_band = sma + (std * 2)
                    lower_band = sma - (std * 2)
                    
                    current_price = float(close_prices.iloc[-1])
                    current_upper = float(upper_band.iloc[-1]) if not pd.isna(upper_band.iloc[-1]) else None
                    current_lower = float(lower_band.iloc[-1]) if not pd.isna(lower_band.iloc[-1]) else None
                    
                    position = "middle"
                    if current_upper and current_lower:
                        if current_price > current_upper:
                            position = "above_upper"
                        elif current_price < current_lower:
                            position = "below_lower"
                    
                    results["indicators"][indicator] = {
                        "name": f"Bollinger Bands ({period_val},2)",
                        "current": {
                            "upper": current_upper,
                            "middle": float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None,
                            "lower": current_lower,
                            "position": position
                        },
                        "values": [
                            {
                                "date": str(idx.date()),
                                "upper": float(upper_band.loc[idx]) if not pd.isna(upper_band.loc[idx]) else None,
                                "middle": float(sma.loc[idx]) if not pd.isna(sma.loc[idx]) else None,
                                "lower": float(lower_band.loc[idx]) if not pd.isna(lower_band.loc[idx]) else None
                            }
                            for idx in sma.dropna().tail(20).index
                        ]
                    }
                    
            except Exception as e:
                logger.debug(f"Failed to calculate {indicator} for {sym}: {e}")
                continue

        # Check for Golden Cross (5-day SMA crossing above 25-day SMA)
        if "sma_5" in results["indicators"] and "sma_25" in results["indicators"]:
            try:
                sma5_values = results["indicators"]["sma_5"]["values"]
                sma25_values = results["indicators"]["sma_25"]["values"]
                
                if len(sma5_values) >= 2 and len(sma25_values) >= 2:
                    # Get last 2 days data for both SMAs
                    sma5_current = sma5_values[-1]["value"]
                    sma5_prev = sma5_values[-2]["value"]
                    sma25_current = sma25_values[-1]["value"]
                    sma25_prev = sma25_values[-2]["value"]
                    
                    # Check for golden cross (short MA crosses above long MA)
                    golden_cross = (sma5_prev <= sma25_prev and sma5_current > sma25_current)
                    # Check for death cross (short MA crosses below long MA)
                    death_cross = (sma5_prev >= sma25_prev and sma5_current < sma25_current)
                    
                    results["cross_analysis"] = {
                        "golden_cross": golden_cross,
                        "death_cross": death_cross,
                        "sma5_current": sma5_current,
                        "sma25_current": sma25_current,
                        "trend": "上昇トレンド" if sma5_current > sma25_current else "下降トレンド",
                        "analysis_jp": "ゴールデンクロス発生" if golden_cross else "デッドクロス発生" if death_cross else "クロス無し"
                    }
            except Exception as e:
                logger.debug(f"Failed to analyze crosses for {sym}: {e}")
        
        results["source"] = "yfinance+computed"
        return results
        
    except Exception as e:
        return {
            "symbol": sym,
            "period": period,
            "error": f"Failed to calculate technical indicators: {str(e)}",
            "source": "yfinance"
        }

def get_market_cap_details(symbol: str) -> Dict[str, Any]:
    """Get comprehensive market capitalization and valuation metrics for a stock."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    ticker = yf.Ticker(sym)
    
    try:
        info = ticker.get_info()
        
        # Get current price for calculations
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        # Market cap and share data
        market_cap = info.get('marketCap')
        shares_outstanding = info.get('sharesOutstanding')
        float_shares = info.get('floatShares')
        shares_short = info.get('sharesShort')
        short_ratio = info.get('shortRatio')
        
        # Enterprise value and debt
        enterprise_value = info.get('enterpriseValue')
        total_debt = info.get('totalDebt')
        total_cash = info.get('totalCash')
        
        # Valuation ratios
        pe_ratio = info.get('trailingPE')
        forward_pe = info.get('forwardPE')
        peg_ratio = info.get('pegRatio')
        price_to_book = info.get('priceToBook')
        price_to_sales = info.get('priceToSalesTrailing12Months')
        enterprise_to_revenue = info.get('enterpriseToRevenue')
        enterprise_to_ebitda = info.get('enterpriseToEbitda')
        
        # Calculate additional metrics
        calculated_market_cap = None
        if current_price and shares_outstanding:
            calculated_market_cap = current_price * shares_outstanding
            
        # Share statistics
        percent_held_by_insiders = info.get('heldByInsiders')
        percent_held_by_institutions = info.get('heldByInstitutions')
        
        # Format large numbers for readability
        def format_large_number(value):
            if value is None:
                return None
            if value >= 1e12:
                return f"{value/1e12:.2f}T"
            elif value >= 1e9:
                return f"{value/1e9:.2f}B"
            elif value >= 1e6:
                return f"{value/1e6:.2f}M"
            else:
                return value
        
        currency = None
        try:
            fi = getattr(ticker, "fast_info", None) or {}
            currency = fi.get("currency") if isinstance(fi, dict) else None
        except Exception:
            currency = None

        return {
            "symbol": sym,
            "currency": currency or "USD",
            "current_price": current_price,
            "market_cap": market_cap,
            "market_cap_formatted": format_large_number(market_cap),
            "calculated_market_cap": calculated_market_cap,
            "enterprise_value": enterprise_value,
            "enterprise_value_formatted": format_large_number(enterprise_value),
            "shares_data": {
                "shares_outstanding": shares_outstanding,
                "float_shares": float_shares,
                "shares_short": shares_short,
                "short_ratio": short_ratio,
                "percent_held_by_insiders": percent_held_by_insiders,
                "percent_held_by_institutions": percent_held_by_institutions
            },
            "debt_and_cash": {
                "total_debt": total_debt,
                "total_cash": total_cash,
                "net_debt": (total_debt - total_cash) if (total_debt and total_cash) else None
            },
            "valuation_ratios": {
                "pe_ratio": pe_ratio,
                "forward_pe": forward_pe,
                "peg_ratio": peg_ratio,
                "price_to_book": price_to_book,
                "price_to_sales": price_to_sales,
                "enterprise_to_revenue": enterprise_to_revenue,
                "enterprise_to_ebitda": enterprise_to_ebitda
            },
            "source": "yfinance"
        }
        
    except Exception as e:
        return {
            "symbol": sym,
            "error": f"Failed to retrieve market cap details: {str(e)}",
            "source": "yfinance"
        }

def check_golden_cross(symbol: str, short_period: int = 5, long_period: int = 25, period: str = "3mo") -> Dict[str, Any]:
    """Check for golden cross/death cross between two moving averages."""
    sym = _normalize_symbol(symbol)
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")
    
    # Ensure we have enough period for analysis
    min_days_needed = max(long_period * 2, 60)  # At least 60 trading days
    if period == "1mo":
        period = "3mo"  # Auto-extend
    
    try:
        indicators = [f"sma_{short_period}", f"sma_{long_period}"]
        result = get_technical_indicators(sym, period=period, indicators=indicators)
        
        if "error" in result:
            return result
        
        sma_short = result["indicators"].get(f"sma_{short_period}")
        sma_long = result["indicators"].get(f"sma_{long_period}")
        
        if not sma_short or not sma_long:
            return {
                "symbol": sym,
                "error": f"移動平均線の計算に失敗しました（{short_period}日・{long_period}日）",
                "source": "yfinance"
            }
        
        # Get recent values for cross detection
        short_values = sma_short["values"][-10:]  # Last 10 days
        long_values = sma_long["values"][-10:]
        
        crosses = []
        for i in range(1, min(len(short_values), len(long_values))):
            prev_short = short_values[i-1]["value"]
            prev_long = long_values[i-1]["value"]
            curr_short = short_values[i]["value"]
            curr_long = long_values[i]["value"]
            
            if prev_short <= prev_long and curr_short > curr_long:
                crosses.append({
                    "date": short_values[i]["date"],
                    "type": "golden_cross",
                    "type_jp": "ゴールデンクロス",
                    "description": f"{short_period}日線が{long_period}日線を上抜け"
                })
            elif prev_short >= prev_long and curr_short < curr_long:
                crosses.append({
                    "date": short_values[i]["date"],
                    "type": "death_cross", 
                    "type_jp": "デッドクロス",
                    "description": f"{short_period}日線が{long_period}日線を下抜け"
                })
        
        # Current status
        current_short = short_values[-1]["value"]
        current_long = long_values[-1]["value"]
        trend = "上昇傾向" if current_short > current_long else "下降傾向"
        
        return {
            "symbol": sym,
            "period": period,
            "short_ma": {
                "period": short_period,
                "current": current_short,
                "name": f"{short_period}日移動平均"
            },
            "long_ma": {
                "period": long_period,
                "current": current_long,
                "name": f"{long_period}日移動平均"
            },
            "current_trend": trend,
            "recent_crosses": crosses,
            "has_golden_cross": any(c["type"] == "golden_cross" for c in crosses[-3:]),  # Last 3 crosses
            "has_death_cross": any(c["type"] == "death_cross" for c in crosses[-3:]),
            "analysis_summary": f"直近のクロス: {len(crosses)}回, 現在のトレンド: {trend}",
            "source": "yfinance+computed"
        }
        
    except Exception as e:
        return {
            "symbol": sym,
            "error": f"ゴールデンクロス分析に失敗: {str(e)}",
            "source": "yfinance"
        }

def _get_japanese_banking_alternatives(symbol: str) -> List[str]:
    """Get alternative Japanese banking sector symbols when the requested one has insufficient data."""
    symbol_lower = symbol.lower()
    
    # Regional bank alternatives  
    if any(term in symbol_lower for term in ["地域", "地方", "regional"]):
        return [
            "8359.T",  # Hachijuni Bank (reliable data)
            "8365.T",  # Toyama Bank  
            "8334.T",  # Gunma Bank
            "8360.T",  # Yamanashi Chuo Bank
        ]
    
    # General banking sector alternatives
    if any(term in symbol_lower for term in ["銀行", "bank"]):
        return [
            "8306.T",  # Mitsubishi UFJ Financial Group
            "8316.T",  # Sumitomo Mitsui Financial Group  
            "8411.T",  # Mizuho Financial Group
            "8359.T",  # Hachijuni Bank (regional representative)
        ]
    
    return []

def calculate_correlation(
    symbol1: str,
    symbol2: str,
    period: str = "6mo",
    interval: str = "1d"
) -> Dict[str, Any]:
    """Calculate correlation coefficient between two stocks/indices based on daily returns."""
    sym1 = _normalize_symbol(symbol1)
    sym2 = _normalize_symbol(symbol2)
    
    if not sym1 or not TICKER_RE.match(sym1):
        raise ValueError(f"invalid symbol1: {symbol1}")
    if not sym2 or not TICKER_RE.match(sym2):
        raise ValueError(f"invalid symbol2: {symbol2}")
    
    try:
        # Get historical data for both symbols
        hist1 = get_historical_prices(sym1, period=period, interval=interval, auto_adjust=False)
        hist2 = get_historical_prices(sym2, period=period, interval=interval, auto_adjust=False)
        
        rows1 = hist1.get("rows", [])
        rows2 = hist2.get("rows", [])
        
        if len(rows1) < 10 or len(rows2) < 10:
            # Get alternative suggestions for Japanese banking sector
            alternatives2 = _get_japanese_banking_alternatives(symbol2)
            alternatives1 = _get_japanese_banking_alternatives(symbol1)
            
            all_suggestions = []
            if alternatives2:
                all_suggestions.extend([f"{alt} - {symbol2}の代替として" for alt in alternatives2[:3]])
            if alternatives1:  
                all_suggestions.extend([f"{alt} - {symbol1}の代替として" for alt in alternatives1[:2]])
            
            # Add general market alternatives
            if not all_suggestions:
                all_suggestions.extend([
                    "^N225 - 日経平均株価との相関",
                    "^TPX - TOPIX指数との相関", 
                    "8306.T - 主要銀行（三菱UFJ）との相関"
                ])
            
            error_msg = f"データが不足しているため、相関係数を算出できませんでした。\n取得データポイント: {sym1}={len(rows1)}, {sym2}={len(rows2)} (最低10必要)"
            
            if all_suggestions:
                error_msg += f"\n\n💡 代替案をお試しください:\n" + "\n".join(f"• {s}" for s in all_suggestions[:4])
            
            return {
                "symbol1": sym1,
                "symbol2": sym2, 
                "original_symbol1": symbol1,
                "original_symbol2": symbol2,
                "period": period,
                "interval": interval,
                "error": error_msg,
                "suggestions": all_suggestions[:4],
                "source": "yfinance"
            }
        
        # Convert to DataFrames and align dates
        df1 = pd.DataFrame(rows1)
        df2 = pd.DataFrame(rows2)
        
        df1["date"] = pd.to_datetime(df1["date"])
        df2["date"] = pd.to_datetime(df2["date"])
        
        df1 = df1.set_index("date").sort_index()
        df2 = df2.set_index("date").sort_index()
        
        # Get overlapping dates
        common_dates = df1.index.intersection(df2.index)
        if len(common_dates) < 10:
            return {
                "symbol1": sym1,
                "symbol2": sym2,
                "period": period,
                "interval": interval,
                "error": f"Insufficient overlapping data points (got {len(common_dates)})",
                "source": "yfinance"
            }
        
        # Filter to common dates and calculate returns
        df1_aligned = df1.loc[common_dates]
        df2_aligned = df2.loc[common_dates]
        
        # Calculate daily returns (percentage change)
        returns1 = pd.to_numeric(df1_aligned["close"]).pct_change().dropna()
        returns2 = pd.to_numeric(df2_aligned["close"]).pct_change().dropna()
        
        # Ensure same length
        min_len = min(len(returns1), len(returns2))
        if min_len < 5:
            return {
                "symbol1": sym1,
                "symbol2": sym2,
                "period": period,
                "interval": interval,
                "error": f"Insufficient return data for correlation (got {min_len} returns)",
                "source": "yfinance"
            }
        
        returns1 = returns1.tail(min_len)
        returns2 = returns2.tail(min_len)
        
        # Calculate correlation coefficient
        correlation = float(np.corrcoef(returns1, returns2)[0, 1])
        
        # Calculate additional statistics
        volatility1 = float(returns1.std() * (252 ** 0.5))  # Annualized volatility
        volatility2 = float(returns2.std() * (252 ** 0.5))
        
        # Get currency info
        currency1 = hist1.get("currency", "USD")
        currency2 = hist2.get("currency", "USD")
        
        # Interpret correlation strength
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            strength = "非常に強い" if correlation > 0 else "非常に強い負の"
        elif abs_corr >= 0.6:
            strength = "強い" if correlation > 0 else "強い負の"
        elif abs_corr >= 0.4:
            strength = "中程度の" if correlation > 0 else "中程度の負の"
        elif abs_corr >= 0.2:
            strength = "弱い" if correlation > 0 else "弱い負の"
        else:
            strength = "ほぼ無相関"
        
        return {
            "symbol1": sym1,
            "symbol2": sym2,
            "currency1": currency1,
            "currency2": currency2,
            "period": period,
            "interval": interval,
            "correlation_coefficient": round(correlation, 4),
            "correlation_strength": strength,
            "data_points": min_len,
            "date_range": {
                "start": str(common_dates[0].date()),
                "end": str(common_dates[-1].date())
            },
            "statistics": {
                "symbol1_volatility_annualized": round(volatility1, 4),
                "symbol2_volatility_annualized": round(volatility2, 4),
                "symbol1_mean_return": round(float(returns1.mean()), 6),
                "symbol2_mean_return": round(float(returns2.mean()), 6)
            },
            "interpretation": f"{sym1}と{sym2}の相関は{strength}相関（相関係数: {correlation:.4f}）",
            "source": "yfinance+computed"
        }
        
    except Exception as e:
        return {
            "symbol1": sym1,
            "symbol2": sym2,
            "period": period,
            "interval": interval,
            "error": f"Correlation calculation failed: {str(e)}",
            "source": "yfinance"
        }

def get_market_summary() -> Dict[str, Any]:
    """Get a comprehensive market summary including major indices and market status."""
    try:
        # Get major global indices
        global_indices = get_market_indices("global")
        
        # Calculate market sentiment based on index performance
        positive_count = 0
        negative_count = 0
        total_count = 0
        
        for index in global_indices.get("indices", []):
            change_pct = index.get("change_pct")
            if change_pct is not None:
                total_count += 1
                if change_pct > 0:
                    positive_count += 1
                elif change_pct < 0:
                    negative_count += 1
        
        market_sentiment = "neutral"
        if total_count > 0:
            if positive_count > negative_count:
                market_sentiment = "positive"
            elif negative_count > positive_count:
                market_sentiment = "negative"
        
        # Get current time for market status
        now = datetime.now()
        market_status = "closed"  # Simplified - could be enhanced with actual market hours
        if 9 <= now.hour <= 16:  # Rough market hours
            market_status = "open"
        
        return {
            "market_sentiment": market_sentiment,
            "market_status": market_status,
            "positive_indices": positive_count,
            "negative_indices": negative_count,
            "neutral_indices": total_count - positive_count - negative_count,
            "indices_summary": global_indices,
            "timestamp": now.isoformat(),
            "source": "yfinance+computed"
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get market summary: {str(e)}",
            "source": "yfinance"
        }
