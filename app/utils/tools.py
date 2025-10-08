"""Tool registry and specifications for OpenAI function calling."""
import asyncio
import copy
import logging
import re
from typing import Dict, Any, Callable, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

# ML tool selection imports (lazy loaded)
try:
    from app.services.ml.tool_selector import get_ml_tool_selector
    ML_SELECTOR_AVAILABLE = True
except ImportError:
    ML_SELECTOR_AVAILABLE = False
    logger.warning("ML tool selector not available - using rule-based selection only")

from app.services.stock_service import (
    get_stock_quote, get_company_profile, get_historical_prices,
    get_augmented_news, get_risk_assessment,
    get_financials, get_earnings_data, get_analyst_recommendations,
    get_institutional_holders, get_dividends_splits, get_market_indices,
    get_technical_indicators, get_market_summary, get_nikkei_news_with_sentiment,
    get_market_cap_details, check_golden_cross, calculate_correlation
)
from app.services.rag_service import rag_search
from app.services.enhanced_rag_service import augmented_rag_search
from app.services.perplexity_web_search import perplexity_web_search
from app.services.stock_prediction_service import (
    predict_stock_price, train_model, get_model_info, list_available_models
)

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
                        "description": "Time period (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max)",
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
            "name": "get_augmented_news",
            "description": "Get recent news articles with optional full article text and RAG context. Can be used for simple headlines (include_full_text=false, include_rag=false) or enriched analysis.",
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
    {
        "type": "function",
        "function": {
            "name": "get_financials",
            "description": "Get comprehensive financial statements including income statement, balance sheet, and cash flow data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."},
                    "freq": {"type": "string", "description": "Frequency: 'quarterly' or 'annual'", "default": "quarterly"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings_data",
            "description": "Get earnings history, quarterly earnings, and earnings calendar with estimates.",
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
            "name": "get_analyst_recommendations",
            "description": "Get analyst recommendations, price targets, upgrades/downgrades, and consensus ratings.",
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
            "name": "get_institutional_holders",
            "description": "Get institutional holders, mutual fund holders, and major shareholders data.",
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
            "name": "get_dividends_splits",
            "description": "Get dividend history and stock split information for a company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."},
                    "period": {"type": "string", "description": "Time period (1mo,3mo,6mo,1y,2y,5y,max)", "default": "1y"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_indices",
            "description": "Get current prices and performance of major market indices (S&P500, Nasdaq, Nikkei, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "Region: 'global', 'us', 'japan', 'europe', 'asia'", "default": "global"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_technical_indicators",
            "description": "Calculate technical analysis indicators (SMA, EMA, RSI, MACD, Bollinger Bands) for a stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol."},
                    "period": {"type": "string", "description": "Time period for analysis (1mo,3mo,6mo,1y)", "default": "3mo"},
                    "indicators": {"type": "array", "items": {"type": "string"}, "description": "List of indicators: sma_20, sma_50, ema_12, ema_26, rsi_14, macd, bb_20"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_summary",
            "description": "Get comprehensive market summary including global indices performance and market sentiment.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nikkei_news_with_sentiment",
            "description": "Get recent Nikkei 225 news headlines with sentiment analysis (Japanese market focused).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of news items to return.", "default": 5}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_cap_details",
            "description": "Get comprehensive market capitalization and valuation metrics including shares outstanding, enterprise value, debt, and valuation ratios.",
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
            "name": "check_golden_cross",
            "description": "Check for golden cross and death cross patterns between moving averages. Automatically extends period if needed for accurate analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, 8359.T)."},
                    "short_period": {"type": "integer", "description": "Short moving average period (default: 5 days)", "default": 5},
                    "long_period": {"type": "integer", "description": "Long moving average period (default: 25 days)", "default": 25},
                    "period": {"type": "string", "description": "Data period (will auto-extend if too short)", "default": "3mo"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_correlation",
            "description": "Calculate correlation coefficient between two stocks or indices based on their daily returns over a specified period. Perfect for analyzing relationships between securities, sectors, or market indices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol1": {"type": "string", "description": "First stock/index ticker symbol (e.g., 8359.T, AAPL)."},
                    "symbol2": {"type": "string", "description": "Second stock/index ticker symbol (e.g., ^KRX, ^N225, SPY)."},
                    "period": {"type": "string", "description": "Time period for correlation analysis (1mo,3mo,6mo,1y,2y)", "default": "6mo"},
                    "interval": {"type": "string", "description": "Data interval (1d for daily, 1wk for weekly)", "default": "1d"}
                },
                "required": ["symbol1", "symbol2"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "perplexity_search",
            "description": "PRIORITY TOOL: Enhanced web search with AI-powered answer synthesis - USE THIS WHENEVER YOU'RE UNCERTAIN OR LACK CURRENT INFORMATION. This is the primary web search tool for all general searches, real-time information, current events, recent news, and any research questions where you need up-to-date or comprehensive information. Always use this when you don't have complete knowledge or need to verify facts. Supports Japanese queries and provides comprehensive results with proper source attribution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in any language (supports Japanese, English, etc.)"},
                    "max_results": {"type": "integer", "description": "Maximum number of search results to process", "default": 8},
                    "synthesize_answer": {"type": "boolean", "description": "Whether to generate AI-synthesized answer", "default": True},
                    "include_recent": {"type": "boolean", "description": "Whether to prioritize recent content", "default": True}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "augmented_rag_search",
            "description": "COMPREHENSIVE SEARCH: Advanced search that combines knowledge base and web search for complete context. Use for complex queries requiring both internal knowledge and current information. Always includes web search by default to ensure you have the most current and complete information available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for augmented RAG"},
                    "kb_k": {"type": "integer", "description": "Number of knowledge base chunks to retrieve", "default": 3},
                    "web_results": {"type": "integer", "description": "Number of web search results", "default": 5},
                    "include_web": {"type": "boolean", "description": "Whether to include web search (strongly recommended)", "default": True},
                    "web_content": {"type": "boolean", "description": "Whether to fetch full content from web pages", "default": True}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_stock_price",
            "description": "AI-powered stock price prediction using LSTM neural network. Predicts future prices for 1-30 days. Optimized for lightweight GPU (GTX 1650 Ti). Returns predicted prices with trend analysis. Requires trained model (auto-trains if needed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, 8359.T)."},
                    "days": {"type": "integer", "description": "Number of days to predict (1-30)", "default": 7},
                    "auto_train": {"type": "boolean", "description": "Auto-train model if not found", "default": True}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "train_model",
            "description": "Train LSTM prediction model for a stock symbol. Uses 2 years of historical data by default. Model is saved for future predictions. Returns training metrics (loss, MAE). Use this when prediction model doesn't exist or needs retraining.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol to train model for."},
                    "period": {"type": "string", "description": "Historical data period for training (1y, 2y, 5y)", "default": "2y"},
                    "save_model": {"type": "boolean", "description": "Whether to save trained model", "default": True}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_info",
            "description": "Get information about trained prediction model for a stock symbol. Shows training date, performance metrics, and model configuration.",
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
            "name": "list_available_models",
            "description": "List all available trained prediction models with their training dates and performance metrics.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# Map tool name to specification for quick lookup and dynamic selection
_TOOL_SPEC_BY_NAME: Dict[str, Dict[str, Any]] = {
    spec["function"]["name"]: spec for spec in tools_spec
}

_DEFAULT_TICKER_TOOLS: Set[str] = {
    "get_stock_quote",
    "get_company_profile",
    "get_historical_prices",
}

_DEFAULT_WEB_SEARCH_TOOLS: Set[str] = {"perplexity_search"}

_KNOWLEDGE_KEYWORDS = {
    "explain",
    "what is",
    "strategy",
    "how does",
    "education",
    "define",
    "analysis",
    "overview",
    "why",
}

_NEWS_KEYWORDS = {"news", "headline", "headlines", "article", "articles", "速報", "ニュース"}
_RISK_KEYWORDS = {"risk", "volatility", "var", "value at risk", "beta", "sharpe"}
_TECHNICAL_KEYWORDS = {"technical", "indicator", "sma", "ema", "rsi", "macd", "bollinger"}
_CORRELATION_KEYWORDS = {"correlation", "relationship", "covariance"}
_GOLDEN_CROSS_KEYWORDS = {"golden cross", "death cross"}
_MARKET_SUMMARY_KEYWORDS = {"market summary", "market overview", "indices", "index"}
_PREDICTION_KEYWORDS = {"predict", "forecast", "future", "prediction", "forecasting", "予測", "予想", "見通し"}

_CAPABILITY_TOOL_MAP: Dict[str, Set[str]] = {
    "quote": {"get_stock_quote"},
    "profile": {"get_company_profile"},
    "historical": {"get_historical_prices"},
    "news": {"get_augmented_news"},
    "risk": {"get_risk_assessment"},
    "financials": {"get_financials"},
    "earnings": {"get_earnings_data"},
    "analyst": {"get_analyst_recommendations"},
    "holders": {"get_institutional_holders"},
    "dividends": {"get_dividends_splits"},
    "technical": {"get_technical_indicators", "check_golden_cross"},
    "market_summary": {"get_market_summary"},
    "nikkei_news": {"get_nikkei_news_with_sentiment"},
    "market_cap": {"get_market_cap_details"},
    "correlation": {"calculate_correlation"},
    "golden_cross": {"check_golden_cross"},
    "prediction": {"predict_stock_price", "get_model_info", "train_model"},
    "forecast": {"predict_stock_price"},
    "rag": {"rag_search", "augmented_rag_search"},
    "augmented_rag": {"augmented_rag_search"},
    "web_search": {"perplexity_search", "augmented_rag_search"},
    "perplexity": {"perplexity_search"},
}

_TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b")
_TICKER_STOPWORDS = {
    "NEWS",
    "MARKET",
    "INDEX",
    "INDEXES",
    "INDEXS",
    "INDEXES",
    "STOCK",
    "SHARE",
    "PRICE",
    "VALUE",
}

def _detect_ticker(prompt: str) -> bool:
    for match in _TICKER_PATTERN.finditer(prompt or ""):
        token = match.group(1)
        if token and token.upper() not in _TICKER_STOPWORDS and not token.isdigit():
            return True
    return False


def _apply_capabilities(capabilities: Optional[Iterable[str]]) -> Set[str]:
    selected: Set[str] = set()
    if not capabilities:
        return selected

    for cap in capabilities:
        if not cap:
            continue
        norm = cap.lower().strip()
        if not norm:
            continue
        # Allow direct tool names
        if norm in _TOOL_SPEC_BY_NAME:
            selected.add(norm)
            continue
        mapped = _CAPABILITY_TOOL_MAP.get(norm)
        if mapped:
            selected.update(mapped)
    return selected


def _apply_keyword_heuristics(prompt: str) -> Set[str]:
    prompt_lower = (prompt or "").lower()
    names: Set[str] = set()

    if any(keyword in prompt_lower for keyword in _NEWS_KEYWORDS):
        names.add("get_augmented_news")

    if any(keyword in prompt_lower for keyword in _RISK_KEYWORDS):
        names.add("get_risk_assessment")

    if any(keyword in prompt_lower for keyword in _TECHNICAL_KEYWORDS):
        names.update({"get_technical_indicators", "check_golden_cross"})

    if any(keyword in prompt_lower for keyword in _CORRELATION_KEYWORDS):
        names.add("calculate_correlation")

    if any(keyword in prompt_lower for keyword in _GOLDEN_CROSS_KEYWORDS):
        names.add("check_golden_cross")

    if any(keyword in prompt_lower for keyword in _MARKET_SUMMARY_KEYWORDS):
        names.add("get_market_summary")

    if any(keyword in prompt_lower for keyword in _PREDICTION_KEYWORDS):
        names.update({"predict_stock_price", "get_model_info"})

    if any(keyword in prompt_lower for keyword in _KNOWLEDGE_KEYWORDS):
        names.update({"rag_search"})

    return names


def select_tool_names_for_prompt(prompt: str, capabilities: Optional[Iterable[str]] = None) -> Set[str]:
    """Infer a minimal set of tool names for a prompt using heuristics and capabilities."""
    names: Set[str] = set()

    ticker_detected = _detect_ticker(prompt)
    if ticker_detected:
        names.update(_DEFAULT_TICKER_TOOLS)

    # Always allow web search unless explicitly disabled via capabilities mapping in the future
    names.update(_DEFAULT_WEB_SEARCH_TOOLS)

    names.update(_apply_capabilities(capabilities))
    names.update(_apply_keyword_heuristics(prompt))

    # If no ticker detected and no capability, favor knowledge tools when the query looks explanatory
    if not names.intersection(_DEFAULT_TICKER_TOOLS):
        prompt_lower = (prompt or "").lower()
        if any(keyword in prompt_lower for keyword in _KNOWLEDGE_KEYWORDS):
            names.add("rag_search")

    # Guard: ensure returned names are valid tool specs
    return {name for name in names if name in _TOOL_SPEC_BY_NAME}


def build_tools_for_request(prompt: str, capabilities: Optional[Iterable[str]] = None, skip_heavy_tools: bool = False) -> List[Dict[str, Any]]:
    """
    Build tool specifications dynamically for a request.
    
    Args:
        prompt: User's input prompt
        capabilities: Optional set of capability filters
        skip_heavy_tools: If True, skip RAG and web search for performance
    
    Returns:
        List of tool specifications
    """
    names = select_tool_names_for_prompt(prompt, capabilities)

    # Performance optimization: skip heavy tools for simple queries
    if skip_heavy_tools:
        # Filter out RAG and web search tools
        heavy_tools = {
            'rag_search', 'augmented_rag_search', 'perplexity_search',
            'web_search', 'web_search_news', 'financial_context_search',
            'augmented_rag_web'
        }
        names = {name for name in names if name not in heavy_tools}
        logger.info(f"Skipping heavy tools for simple query: {heavy_tools & set(select_tool_names_for_prompt(prompt, capabilities))}")
    
    # Always provide at least basic stock tools if no tools selected
    if not names:
        # For simple queries, provide only basic stock tools
        if skip_heavy_tools:
            names = {'get_stock_quote', 'get_company_profile'}
        else:
            names = set(_DEFAULT_WEB_SEARCH_TOOLS)

    # Preserve deterministic ordering for reproducibility
    ordered_names = sorted(names)
    return [copy.deepcopy(_TOOL_SPEC_BY_NAME[name]) for name in ordered_names]


def build_tools_for_request_ml(
    prompt: str, 
    capabilities: Optional[Iterable[str]] = None, 
    skip_heavy_tools: bool = False,
    use_ml: bool = True,
    fallback_to_rules: bool = True
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Build tool specifications using ML-based selection with fallback to rule-based.
    
    Args:
        prompt: User's input prompt
        capabilities: Optional set of capability filters
        skip_heavy_tools: If True, skip RAG and web search for performance
        use_ml: If True, attempt ML-based selection
        fallback_to_rules: If True, fall back to rule-based if ML fails
    
    Returns:
        Tuple of (tool_specs, metadata):
        - tool_specs: List of tool specifications
        - metadata: Dict with selection method, confidence, etc.
    """
    metadata = {
        'method': 'unknown',
        'ml_attempted': False,
        'ml_succeeded': False,
        'tools_count': 0,
        'confidence': None,
        'fallback_used': False,
    }
    
    # Try ML selection if enabled
    if use_ml and ML_SELECTOR_AVAILABLE:
        try:
            metadata['ml_attempted'] = True
            selector = get_ml_tool_selector()
            
            # Check if ML should be used
            if selector.should_use_ml():
                logger.info(f"Using ML tool selection for query: {prompt[:100]}...")
                
                # Get all available tool names
                available_tools = list(_TOOL_SPEC_BY_NAME.keys())
                
                # Predict tools with ML
                selected_tools, probabilities = selector.predict_tools(
                    query=prompt,
                    available_tools=available_tools,
                    return_probabilities=True
                )
                
                if selected_tools:
                    # Filter heavy tools if requested
                    if skip_heavy_tools:
                        heavy_tools = {
                            'rag_search', 'augmented_rag_search', 'perplexity_search',
                            'web_search', 'web_search_news', 'financial_context_search',
                            'augmented_rag_web'
                        }
                        selected_tools = [t for t in selected_tools if t not in heavy_tools]
                    
                    # Build tool specs
                    if selected_tools:
                        ordered_names = sorted(selected_tools)
                        tool_specs = [copy.deepcopy(_TOOL_SPEC_BY_NAME[name]) for name in ordered_names]
                        
                        avg_confidence = sum(probabilities.values()) / len(probabilities) if probabilities else 0.0
                        
                        metadata.update({
                            'method': 'ml',
                            'ml_succeeded': True,
                            'tools_count': len(tool_specs),
                            'confidence': round(avg_confidence, 3),
                            'probabilities': probabilities,
                            'fallback_used': False,
                        })
                        
                        logger.info(
                            f"ML selected {len(tool_specs)} tools "
                            f"(confidence: {avg_confidence:.2f}): {ordered_names}"
                        )
                        
                        return tool_specs, metadata
            
            # ML didn't return tools or should_use_ml returned False
            logger.info("ML selection didn't return tools, falling back to rule-based")
            
        except Exception as e:
            logger.error(f"ML tool selection failed: {e}", exc_info=True)
    
    # Fallback to rule-based selection
    if fallback_to_rules:
        logger.info("Using rule-based tool selection")
        tool_specs = build_tools_for_request(prompt, capabilities, skip_heavy_tools)
        
        metadata.update({
            'method': 'rule-based',
            'tools_count': len(tool_specs),
            'fallback_used': metadata['ml_attempted'],  # True if ML was attempted but failed
        })
        
        # Record fallback in ML stats if applicable
        if metadata['ml_attempted'] and ML_SELECTOR_AVAILABLE:
            try:
                selector = get_ml_tool_selector()
                selector.record_fallback()
            except Exception:
                pass
        
        return tool_specs, metadata
    
    # No fallback allowed and ML failed - return empty
    logger.warning("ML failed and fallback disabled, returning empty tool list")
    return [], metadata


# Parameter mapping helper for web_search compatibility
def _web_search_with_parameter_mapping(**kw) -> Dict[str, Any]:
    """Map various parameter names to perplexity_web_search format."""
    # Map various result count parameters to max_results
    max_results = (
        kw.get("max_results") or 
        kw.get("top_k") or 
        kw.get("top_n") or 
        kw.get("num_results") or 
        kw.get("limit") or 
        8
    )
    
    # Map recency_days -> include_recent (if recency_days <= 7, use recent content)
    recency_days = kw.get("recency_days")
    include_recent = kw.get("include_recent", True)
    if recency_days is not None:
        include_recent = int(recency_days) <= 7  # Recent if within a week
    
    # Handle source parameter
    source = kw.get("source")
    synthesize_answer = kw.get("synthesize_answer", True)
    if source == "news":
        include_recent = True  # News should be recent
        synthesize_answer = True  # News should be synthesized for better readability
    elif source == "academic":
        include_recent = False  # Academic sources may be older but more authoritative
        synthesize_answer = True
    
    return perplexity_web_search(
        query=kw.get("query", ""),
        max_results=int(max_results),
        synthesize_answer=bool(synthesize_answer),
        include_recent=bool(include_recent)
    )

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
    "get_financials": lambda **kw: get_financials(
        symbol=kw.get("symbol", ""),
        freq=kw.get("freq", "quarterly")
    ),
    "get_earnings_data": lambda **kw: get_earnings_data(symbol=kw.get("symbol", "")),
    "get_analyst_recommendations": lambda **kw: get_analyst_recommendations(symbol=kw.get("symbol", "")),
    "get_institutional_holders": lambda **kw: get_institutional_holders(symbol=kw.get("symbol", "")),
    "get_dividends_splits": lambda **kw: get_dividends_splits(
        symbol=kw.get("symbol", ""),
        period=kw.get("period", "1y")
    ),
    "get_market_indices": lambda **kw: get_market_indices(region=kw.get("region", "global")),
    "get_technical_indicators": lambda **kw: get_technical_indicators(
        symbol=kw.get("symbol", ""),
        period=kw.get("period", "3mo"),
        indicators=kw.get("indicators")
    ),
    "get_market_summary": lambda **kw: get_market_summary(),
    "get_nikkei_news_with_sentiment": lambda **kw: get_nikkei_news_with_sentiment(
        limit=int(kw.get("limit", 5))
    ),
    "get_market_cap_details": lambda **kw: get_market_cap_details(symbol=kw.get("symbol", "")),
    "check_golden_cross": lambda **kw: check_golden_cross(
        symbol=kw.get("symbol", ""),
        short_period=int(kw.get("short_period", 5)),
        long_period=int(kw.get("long_period", 25)),
        period=kw.get("period", "3mo")
    ),
    "calculate_correlation": lambda **kw: calculate_correlation(
        symbol1=kw.get("symbol1", ""),
        symbol2=kw.get("symbol2", ""),
        period=kw.get("period", "6mo"),
        interval=kw.get("interval", "1d")
    ),

    "perplexity_search": lambda **kw: perplexity_web_search(
        query=kw.get("query", ""),
        max_results=int(kw.get("max_results", 8)),
        synthesize_answer=bool(kw.get("synthesize_answer", True)),
        include_recent=bool(kw.get("include_recent", True))
    ),
    "augmented_rag_search": lambda **kw: augmented_rag_search(
        query=kw.get("query", ""),
        kb_k=int(kw.get("kb_k", 3)),
        web_results=int(kw.get("web_results", 5)),
        include_web=bool(kw.get("include_web", True)),
        web_content=bool(kw.get("web_content", True))
    ),
    
    # Stock prediction tools
    "predict_stock_price": lambda **kw: predict_stock_price(
        symbol=kw.get("symbol", ""),
        days=int(kw.get("days", 7)),
        auto_train=bool(kw.get("auto_train", True))
    ),
    "train_model": lambda **kw: train_model(
        symbol=kw.get("symbol", ""),
        period=kw.get("period", "2y"),
        save_model=bool(kw.get("save_model", True))
    ),
    "get_model_info": lambda **kw: get_model_info(symbol=kw.get("symbol", "")),
    "list_available_models": lambda **kw: list_available_models(),
}
