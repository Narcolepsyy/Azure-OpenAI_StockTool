from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Callable
import os
import json
import re
import logging

# Load environment from .env if present
from dotenv import load_dotenv
load_dotenv()

# Azure OpenAI SDK (v1.x)
from openai import AzureOpenAI, NotFoundError

# Stock data helper
import yfinance as yf
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from cachetools import TTLCache

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("app")

# App metadata
app = FastAPI(
    title="AI Stocks Assistant API",
    version="0.2.0",
    description="FastAPI + Azure OpenAI tool-calling with stock tools (yfinance).",
)

# Parse allowed origins from env (comma-separated). Defaults to dev-friendly '*', tighten in prod.
_frontend_origins = os.getenv("FRONTEND_ORIGINS", "*")
allow_origins = [o.strip() for o in _frontend_origins.split(",") if o.strip()] or ["*"]

# CORS for local React dev server / configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend and React build (if present)
app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")
app.mount("/app", StaticFiles(directory="frontend/dist", html=True, check_dir=False), name="app")

# ---------- Caching & validation ----------
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,9}$")  # e.g., AAPL, MSFT, VOD.L, BRK.B
QUOTE_CACHE = TTLCache(maxsize=int(os.getenv("QUOTE_CACHE_SIZE", "1024")), ttl=int(os.getenv("QUOTE_TTL_SECONDS", "60")))

# ---------- Azure OpenAI setup ----------
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
# Note: Azure Chat Completions uses the deployment name as the `model` parameter
AZURE_OPENAI_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT",
    "gpt-4-1-nano-2025-04-14-ft-29b4e0314d9741f19687609578cc9d19",
)

_client: Optional[AzureOpenAI] = None

def get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
            raise RuntimeError(
                "Missing Azure OpenAI environment variables: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT"
            )
        _client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
    return _client


# ---------- Tools ----------

# Helpers to normalize natural language timeframe inputs
_NL_PERIOD_MAP = {
    "past week": "5d",
    "last week": "5d",
    "previous week": "5d",
    "1 week": "5d",
    "one week": "5d",
    "7d": "5d",  # yfinance doesn't support 7d period; use 5 trading days
    "five days": "5d",
    "5 days": "5d",
    "last 5 days": "5d",
    "past month": "1mo",
    "last month": "1mo",
    "1 month": "1mo",
    "one month": "1mo",
    "3 months": "3mo",
    "three months": "3mo",
    "6 months": "6mo",
    "six months": "6mo",
    "1 year": "1y",
    "one year": "1y",
    "2 years": "2y",
    "two years": "2y",
    "5 years": "5y",
    "five years": "5y",
    "10 years": "10y",
    "ten years": "10y",
    "ytd": "ytd",
    "year to date": "ytd",
    "all time": "max",
    "max": "max",
}

_NL_INTERVAL_MAP = {
    "daily": "1d",
    "day": "1d",
    "1 day": "1d",
    "one day": "1d",
    "weekly": "1wk",
    "week": "1wk",
    "monthly": "1mo",
    "month": "1mo",
    "hourly": "1h",
    "hour": "1h",
}

def _normalize_period(val: Optional[str]) -> str:
    if not val:
        return "1mo"
    s = str(val).strip().lower()
    return _NL_PERIOD_MAP.get(s, s)


def _normalize_interval(val: Optional[str]) -> str:
    if not val:
        return "1d"
    s = str(val).strip().lower()
    return _NL_INTERVAL_MAP.get(s, s)


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
        # Some tickers don't return info; surface minimal data
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
    """Return historical OHLCV for a ticker.

    - period: one of 5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max (natural language like 'past week' is mapped to 5d)
    - interval: one of 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo (natural language like 'daily' -> 1d)
    - limit: optional max number of rows to return (most recent)
    """
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
            # Skip malformed rows
            continue

    currency = None
    try:
        fi = getattr(t, "fast_info", None) or {}
        currency = fi.get("currency") if isinstance(fi, dict) else None
    except Exception:
        currency = None

    return {"symbol": sym, "currency": currency or "USD", "count": len(rows), "interval": itv, "period": p, "rows": rows, "source": "yfinance"}


def get_stock_news(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """Return recent news articles for a ticker using yfinance.

    - limit: max number of items to return (default 10)
    """
    sym = (symbol or "").strip().upper()
    if not sym or not TICKER_RE.match(sym):
        raise ValueError("invalid symbol; use letters/numbers with optional '.' or '-' (e.g., AAPL, VOD.L)")

    try:
        t = yf.Ticker(sym)
        news_raw = getattr(t, "news", None)
    except Exception as e:
        raise ValueError(f"failed to retrieve news for '{sym}': {e}")

    if not news_raw:
        return {"symbol": sym, "count": 0, "items": [], "source": "yfinance"}

    items: List[Dict[str, Any]] = []
    for n in news_raw[: max(1, int(limit))]:
        try:
            items.append(
                {
                    "uuid": n.get("uuid"),
                    "title": n.get("title"),
                    "publisher": n.get("publisher"),
                    "link": n.get("link"),
                    "published_at": n.get("providerPublishTime"),
                    "type": n.get("type"),
                    "related_tickers": n.get("relatedTickers"),
                    "thumbnail": (n.get("thumbnail") or {}).get("resolutions", [{}])[0].get("url"),
                }
            )
        except Exception:
            continue

    return {"symbol": sym, "count": len(items), "items": items, "source": "yfinance"}


# ---------- Tool schema (for Azure OpenAI) ----------

tools_spec = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "Get the latest close price for a stock ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g., AAPL, MSFT, GOOGL.",
                    }
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_profile",
            "description": "Get company profile details (name, sector, industry, website, summary).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_prices",
            "description": "Get historical OHLCV price data for a stock ticker symbol. Accepts natural language like 'past week' (maps to 5d) and 'daily' (maps to 1d).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."},
                    "period": {
                        "type": "string",
                        "description": "Time period (5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max)",
                        "default": "1mo",
                    },
                    "interval": {
                        "type": "string",
                        "description": "Sampling interval (1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo)",
                        "default": "1d",
                    },
                    "limit": {"type": "integer", "description": "Max number of recent rows to return."},
                    "auto_adjust": {"type": "boolean", "description": "If true, adjust prices for splits/dividends.", "default": False},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_news",
            "description": "Get recent news articles for a stock ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."},
                    "limit": {"type": "integer", "description": "Max number of news items to return.", "default": 10},
                },
                "required": ["symbol"],
            },
        },
    },
]

# Map tool name to callable for execution
ToolFunc = Callable[..., Dict[str, Any]]
TOOL_REGISTRY: Dict[str, ToolFunc] = {
    "get_stock_quote": lambda **kw: get_stock_quote(symbol=kw.get("symbol", "")),
    "get_company_profile": lambda **kw: get_company_profile(symbol=kw.get("symbol", "")),
    "get_historical_prices": lambda **kw: get_historical_prices(
        symbol=kw.get("symbol", ""),
        period=kw.get("period", "1mo"),
        interval=kw.get("interval", "1d"),
        limit=kw.get("limit"),
        auto_adjust=kw.get("auto_adjust", False),
    ),
    "get_stock_news": lambda **kw: get_stock_news(symbol=kw.get("symbol", ""), limit=int(kw.get("limit", 10))),
}


# ---------- Request/response models ----------

class ChatRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = (
        "You are a helpful assistant. Use the stock tools when users ask about markets."
        " If users mention timeframes like 'past week' with daily candles, call get_historical_prices with period=5d and interval=1d."
    )
    deployment: Optional[str] = None  # Override AZURE_OPENAI_DEPLOYMENT if provided


class ChatResponse(BaseModel):
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


# ---------- Simple API key auth (optional) ----------
APP_API_KEY = os.getenv("APP_API_KEY", "").strip()

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """If APP_API_KEY is set, require matching X-API-Key header; otherwise allow."""
    if APP_API_KEY and (x_api_key or "").strip() != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------- Chat endpoint with iterative tool-calling ----------

@app.post("/chat", response_model=ChatResponse, tags=["api"], dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest):
    try:
        client = get_client()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Prefer .env deployment unless a real value is provided in the request
    raw_dep = (req.deployment or "").strip()
    if raw_dep.lower() in {"", "string", "none", "null", "<deployment>", "<your-deployment>", "default"}:
        model = AZURE_OPENAI_DEPLOYMENT
    else:
        model = raw_dep

    if not model:
        raise HTTPException(status_code=400, detail="Missing Azure OpenAI deployment. Set AZURE_OPENAI_DEPLOYMENT in .env or provide a valid 'deployment' in the request body.")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": req.system_prompt or ""},
        {"role": "user", "content": req.prompt},
    ]

    tool_results_accum: List[Dict[str, Any]] = []
    max_tool_rounds = int(os.getenv("MAX_TOOL_ROUNDS", "4"))
    rounds = 0

    try:
        while True:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools_spec,
                    tool_choice="auto",
                )
            except NotFoundError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Azure OpenAI deployment not found: '{model}'. Create a Chat Completions-capable deployment (e.g., gpt-4o-mini) and set AZURE_OPENAI_DEPLOYMENT or pass 'deployment' in the request.",
                )
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Azure OpenAI error: {str(e)}")

            msg = resp.choices[0].message

            # No tool calls -> final answer
            if not getattr(msg, "tool_calls", None):
                final_content = msg.content or ""
                return ChatResponse(content=final_content, tool_calls=tool_results_accum or None)

            # Guard against unbounded loops
            rounds += 1
            if rounds > max_tool_rounds:
                # Stop the loop and ask the model to answer with what it has
                messages.append({
                    "role": "system",
                    "content": "You've reached the maximum number of tool rounds. Provide the best possible answer with the available information.",
                })
                # One last turn without allowing tools
                try:
                    final = client.chat.completions.create(model=model, messages=messages)
                except Exception as e:
                    raise HTTPException(status_code=502, detail=f"Azure OpenAI error (final): {str(e)}")
                fmsg = final.choices[0].message
                return ChatResponse(content=fmsg.content or "", tool_calls=tool_results_accum or None)

            # Append assistant tool_call message
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
            messages.append(assistant_msg)

            # Execute tools
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if name in TOOL_REGISTRY:
                    try:
                        result = TOOL_REGISTRY[name](**args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Unknown tool: {name}"}

                tool_results_accum.append({"id": tc.id, "name": name, "result": result})

                # Add tool result message back to the model
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": json.dumps(result),
                    }
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")


# ---------- Direct stock endpoint (optional utility) ----------

@app.get("/stock/{symbol}", tags=["api"], dependencies=[Depends(require_api_key)])
async def stock(symbol: str):
    try:
        return get_stock_quote(symbol)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/news/{symbol}", tags=["api"], dependencies=[Depends(require_api_key)])
async def news(symbol: str, limit: int = 10):
    """Direct news endpoint."""
    try:
        return get_stock_news(symbol, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/healthz", tags=["ops"])  # liveness
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["ops"])  # readiness
async def readyz():
    return {
        "status": "ready",
        "azure_configured": bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")),
        "cache_size": len(QUOTE_CACHE),
    }
