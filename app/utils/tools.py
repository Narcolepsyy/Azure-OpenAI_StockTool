"""Tool registry and specifications for OpenAI function calling."""
from typing import Dict, Any, Callable, List
from app.services.stock_service import (
    get_stock_quote, get_company_profile, get_historical_prices,
    get_stock_news, get_augmented_news, get_risk_assessment
)
from app.services.rag_service import rag_search

# Tool specifications for OpenAI function calling
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
    {
        "type": "function",
        "function": {
            "name": "get_augmented_news",
            "description": "Get recent news enriched with full article text and optional RAG context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."},
                    "limit": {"type": "integer", "default": 10},
                    "include_full_text": {"type": "boolean", "default": True},
                    "include_rag": {"type": "boolean", "default": True},
                    "rag_k": {"type": "integer", "default": 3},
                    "max_chars": {"type": "integer", "default": 6000},
                    "timeout": {"type": "integer", "default": 8}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_assessment",
            "description": "Compute risk metrics (volatility, Sharpe, max drawdown, VaR, beta) for a stock based on historical prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."},
                    "period": {"type": "string", "description": "Time period for history (5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max)", "default": "1y"},
                    "interval": {"type": "string", "description": "Sampling interval (1d,1wk,1mo, etc.)", "default": "1d"},
                    "rf_rate": {"type": "number", "description": "Annual risk-free rate (decimal). Defaults to env RISK_FREE_RATE.", "default": None},
                    "benchmark": {"type": "string", "description": "Optional benchmark symbol for beta (e.g., SPY)."}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": "Retrieve top-k knowledge base chunks relevant to the user query for grounding answers (RAG).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query to retrieve context for."},
                    "k": {"type": "integer", "description": "Number of chunks to retrieve.", "default": 4}
                },
                "required": ["query"],
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
    "get_augmented_news": lambda **kw: get_augmented_news(
        symbol=kw.get("symbol", ""),
        limit=int(kw.get("limit", 10)),
        include_full_text=bool(kw.get("include_full_text", True)),
        include_rag=bool(kw.get("include_rag", True)),
        rag_k=int(kw.get("rag_k", 3)),
        max_chars=int(kw.get("max_chars", 6000)),
        timeout=int(kw.get("timeout", 8)),
    ),
    "get_risk_assessment": lambda **kw: get_risk_assessment(
        symbol=kw.get("symbol", ""),
        period=kw.get("period", "1y"),
        interval=kw.get("interval", "1d"),
        rf_rate=kw.get("rf_rate"),
        benchmark=kw.get("benchmark"),
    ),
    "rag_search": lambda **kw: rag_search(query=kw.get("query", ""), k=int(kw.get("k", 4))),
}
