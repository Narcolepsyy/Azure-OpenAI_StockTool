# Comprehensive Stock Analysis Tool Guide

This page documents all 16 available tools powered by yfinance with comprehensive financial analysis capabilities. Follow these patterns to avoid trial-and-error calls, reduce latency, and keep token usage low.

General rules
- Always use the parameter names exactly as listed (e.g., symbol, not ticker). Booleans are true/false, not strings.
- Prefer small limits and concise periods/intervals to minimize tokens.
- If you only need a price or a short fact, do not fetch large histories or augmented news.
- Tools may return {"error": "..."}; handle gracefully and try a smaller/simpler call if needed.

Note: For OSS-style pseudo tool markup, the router will remap ticker->symbol, but you should still prefer symbol.

## CORE STOCK DATA TOOLS

---

Tool: get_stock_quote
- Purpose: Latest close price and currency for a ticker.
- Input
  - symbol: string (required). Ticker like AAPL, MSFT, GOOGL; letters/numbers with optional '.' or '-'.
- Returns
  - { symbol: str, price: number, currency: str, as_of: ISO datetime, source: "yfinance" }
- Example call
  - {"type":"function","function":{"name":"get_stock_quote","arguments":"{\"symbol\":\"AAPL\"}"}}
- Example result
  - {"symbol":"AAPL","price":227.12,"currency":"USD","as_of":"2025-09-18 00:00:00+00:00","source":"yfinance"}
- Tips: Best for quick answers like "What is AAPL's latest price?".

---

Tool: get_company_profile
- Purpose: Basic company information.
- Input
  - symbol: string (required)
- Returns
  - { symbol, longName, sector, industry, website, country, currency, summary, source }
- Example call
  - {"type":"function","function":{"name":"get_company_profile","arguments":"{\"symbol\":\"MSFT\"}"}}
- Example result
  - {"symbol":"MSFT","longName":"Microsoft Corporation","sector":"Technology","industry":"Software—Infrastructure","website":"https://www.microsoft.com/","country":"United States","currency":"USD","summary":"...","source":"yfinance"}

---

Tool: get_historical_prices
- Purpose: OHLCV history.
- Input
  - symbol: string (required)
  - period: string (default: "1mo"). Allowed: 5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max. Natural language like "past week" → 5d, "daily" refers to interval, not period.
  - interval: string (default: "1d"). Allowed: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo.
  - limit: integer (optional). Trims the most recent N rows.
  - auto_adjust: boolean (default: false)
- Returns
  - { symbol, currency, count, interval, period, rows: [{date,open,high,low,close,volume}], source }
- Example call (past month, daily, latest 20 rows)
  - {"type":"function","function":{"name":"get_historical_prices","arguments":"{\"symbol\":\"NVDA\",\"period\":\"1mo\",\"interval\":\"1d\",\"limit\":20}"}}
- Example result (truncated)
  - {"symbol":"NVDA","currency":"USD","count":20,"interval":"1d","period":"1mo","rows":[{"date":"2025-08-20T00:00:00+00:00","open":...}],"source":"yfinance"}
- Tips
  - Use small periods/intervals and limit (e.g., 5d + 1d + limit:5) for token efficiency.
  - For intraday, prefer 1h over 1m unless necessary.

---

Tool: get_stock_news
- Purpose: Recent headlines via yfinance with RSS fallback.
- Input
  - symbol: string (required)
  - limit: integer (default: 10)
- Returns
  - { symbol, count, items: [{uuid,title,publisher,link,published_at,type,related_tickers,thumbnail}], source }
- Example call
  - {"type":"function","function":{"name":"get_stock_news","arguments":"{\"symbol\":\"AAPL\",\"limit\":5}"}}
- Example result (truncated)
  - {"symbol":"AAPL","count":5,"items":[{"title":"...","link":"...","publisher":"...","published_at":"..."}],"source":"yfinance+rss"}
- Tips: Use for quick headline lists. For full text or KB grounding, see get_augmented_news.

---

Tool: get_augmented_news
- Purpose: Headlines enriched with article text and optional RAG snippets.
- Input
  - symbol: string (required)
  - limit: integer (default: 10)
  - include_full_text: boolean (default: true)
  - include_rag: boolean (default: true)
  - rag_k: integer (default: 3) — top-k KB chunks per article
  - max_chars: integer (default: 6000) — trim extracted article text
  - timeout: integer seconds (default: 8)
- Returns
  - { symbol, count, items: [{title, publisher, link, published_at, content?, rag?: {enabled,count,results:[{text,metadata,score?}]}}], source, augmented: true }
- Example call (lightweight, summarized)
  - {"type":"function","function":{"name":"get_augmented_news","arguments":"{\"symbol\":\"TSLA\",\"limit\":5,\"include_full_text\":false,\"include_rag\":true,\"rag_k\":2}"}}
- Tips
  - This can be large. Prefer include_full_text:false and small limit (≤5) when only headlines + concise context are needed.
  - The chat router auto-summarizes augmented news into 3–5 headlines to keep context small.

---

Tool: get_risk_assessment
- Purpose: Compute risk metrics from historical prices.
- Input
  - symbol: string (required)
  - period: string (default: "1y")
  - interval: string (default: "1d")
  - rf_rate: number (optional, annual). Defaults to env RISK_FREE_RATE if omitted.
  - benchmark: string (optional, e.g., "SPY") for beta.
- Returns
  - { symbol, period, interval, count, volatility_annualized, sharpe_ratio, max_drawdown, var_95_daily, beta, benchmark, risk_free_rate, source: "computed" }
- Example call (with benchmark)
  - {"type":"function","function":{"name":"get_risk_assessment","arguments":"{\"symbol\":\"AAPL\",\"period\":\"1y\",\"interval\":\"1d\",\"benchmark\":\"SPY\"}"}}
- Tips
  - Ensure period/interval yield ≥ 3 data points; otherwise you may get "insufficient data".
  - Keep period small (e.g., 6mo–2y) for faster responses unless long history is needed.

---

Tool: rag_search
- Purpose: Retrieve KB chunks to ground answers.
- Input
  - query: string (required)
  - k: integer (default: 4)
- Returns
  - { enabled, query, k, count, results: [{ text, metadata: { path }, score? }] }
- Example call
  - {"type":"function","function":{"name":"rag_search","arguments":"{\"query\":\"How to interpret Sharpe ratio?\",\"k\":2}"}}
- Tips
  - Use rag_search to fetch in-domain guidance (like this page) instead of scraping large web content.
  - Keep k small (2–4). Quote concise user intent in query.

## ADVANCED FINANCIAL ANALYSIS TOOLS

Tool: get_financials
- Purpose: Comprehensive financial statements (income statement, balance sheet, cash flow).
- Input
  - symbol: string (required)
  - freq: string (default: "quarterly"). Allowed: "quarterly", "annual"
- Returns
  - { symbol, frequency, currency, income_statement: {date: {line_item: value}}, balance_sheet: {}, cash_flow: {}, source }
- Example call
  - {"type":"function","function":{"name":"get_financials","arguments":"{\"symbol\":\"AAPL\",\"freq\":\"quarterly\"}"}}
- Tips: Use for detailed financial analysis, earnings calls preparation, fundamental analysis.

---

Tool: get_earnings_data
- Purpose: Earnings history, quarterly reports, and earnings calendar.
- Input
  - symbol: string (required)
- Returns
  - { symbol, currency, annual_earnings: [], quarterly_earnings: [], earnings_calendar: [], source }
- Example call
  - {"type":"function","function":{"name":"get_earnings_data","arguments":"{\"symbol\":\"MSFT\"}"}}
- Tips: Essential for earnings season analysis and financial performance tracking.

---

Tool: get_analyst_recommendations
- Purpose: Analyst ratings, price targets, upgrades/downgrades.
- Input
  - symbol: string (required)
- Returns
  - { symbol, currency, current_price, price_targets: {high, low, mean, median}, recommendation_mean, recommendations_history: [], upgrades_downgrades: [], source }
- Example call
  - {"type":"function","function":{"name":"get_analyst_recommendations","arguments":"{\"symbol\":\"NVDA\"}"}}
- Tips: Use for investment decisions and market sentiment analysis.

---

Tool: get_institutional_holders
- Purpose: Institutional ownership, mutual fund holders, major shareholders.
- Input
  - symbol: string (required)
- Returns
  - { symbol, institutional_holders: [], mutualfund_holders: [], major_holders: [], source }
- Example call
  - {"type":"function","function":{"name":"get_institutional_holders","arguments":"{\"symbol\":\"GOOGL\"}"}}
- Tips: Analyze institutional confidence and ownership concentration.

---

Tool: get_dividends_splits
- Purpose: Dividend history and stock split information.
- Input
  - symbol: string (required)
  - period: string (default: "1y"). Allowed: 1mo,3mo,6mo,1y,2y,5y,max
- Returns
  - { symbol, period, currency, dividends: [{date, value}], splits: [{date, value}], dividend_count, split_count, source }
- Example call
  - {"type":"function","function":{"name":"get_dividends_splits","arguments":"{\"symbol\":\"JNJ\",\"period\":\"2y\"}"}}
- Tips: Essential for dividend investing strategies and yield analysis.

## MARKET & TECHNICAL ANALYSIS TOOLS

Tool: get_market_indices
- Purpose: Major market indices performance (S&P500, Nasdaq, Nikkei, etc.).
- Input
  - region: string (default: "global"). Allowed: "global", "us", "japan", "europe", "asia"
- Returns
  - { region, count, indices: [{symbol, name, price, change, change_pct, currency, as_of}], source }
- Example call
  - {"type":"function","function":{"name":"get_market_indices","arguments":"{\"region\":\"us\"}"}}
- Tips: Get market overview and sector rotation insights.

---

Tool: get_technical_indicators
- Purpose: Technical analysis indicators (SMA, EMA, RSI, MACD, Bollinger Bands).
- Input
  - symbol: string (required)
  - period: string (default: "3mo"). Allowed: 1mo,3mo,6mo,1y
  - indicators: array of strings (optional). Options: ["sma_20", "sma_50", "ema_12", "ema_26", "rsi_14", "macd", "bb_20"]
- Returns
  - { symbol, period, indicators: {indicator_name: {name, current, signal?, values: []}}, source }
- Example call
  - {"type":"function","function":{"name":"get_technical_indicators","arguments":"{\"symbol\":\"TSLA\",\"period\":\"3mo\",\"indicators\":[\"rsi_14\",\"macd\",\"sma_20\"]}"}}
- Tips: Use for timing entries/exits and trend analysis. RSI shows overbought/oversold signals.

---

Tool: get_market_summary
- Purpose: Comprehensive market overview with sentiment analysis.
- Input
  - (no parameters required)
- Returns
  - { market_sentiment: "positive"|"negative"|"neutral", market_status: "open"|"closed", positive_indices, negative_indices, neutral_indices, indices_summary, timestamp, source }
- Example call
  - {"type":"function","function":{"name":"get_market_summary","arguments":"{}"}}
- Tips: Perfect for market briefings and daily/weekly summaries.

## SPECIALIZED NEWS & SENTIMENT TOOLS

Tool: get_nikkei_news_with_sentiment
- Purpose: Nikkei 225 news with Japanese market sentiment analysis.
- Input
  - limit: integer (default: 5)
- Returns
  - { symbol: "^N225", count, summaries: [{title, summary, sentiment, sentiment_jp, publisher, published_at, link}], source }
- Example call
  - {"type":"function","function":{"name":"get_nikkei_news_with_sentiment","arguments":"{\"limit\":3}"}}
- Tips: Specialized for Japanese market analysis with bilingual sentiment.

---

## COMPREHENSIVE ANALYSIS RECIPES

**Quick Price Check**
1) get_stock_quote(symbol)
2) Generate a 1–2 sentence answer; avoid extra tool calls.

**Complete Stock Analysis**
1) get_company_profile(symbol) — basic info
2) get_stock_quote(symbol) — current price
3) get_analyst_recommendations(symbol) — price targets & ratings
4) get_technical_indicators(symbol, indicators:["rsi_14", "sma_20", "sma_50"]) — technical signals
5) get_financials(symbol, freq:"quarterly") — latest financial health
6) get_dividends_splits(symbol, period:"1y") — income potential
7) Synthesize comprehensive investment thesis.

**Market Overview Analysis**
1) get_market_summary() — overall market sentiment
2) get_market_indices(region:"global") — major indices performance
3) get_nikkei_news_with_sentiment(limit:3) — Japanese market (if relevant)
4) Provide market briefing with key themes.

**Technical Trading Setup**
1) get_historical_prices(symbol, period:"1mo", interval:"1d")
2) get_technical_indicators(symbol, period:"3mo", indicators:["rsi_14", "macd", "bb_20"])
3) get_risk_assessment(symbol, period:"6mo", benchmark:"SPY")
4) Generate entry/exit recommendations with risk metrics.

**Earnings Season Preparation**
1) get_earnings_data(symbol) — earnings calendar & history
2) get_financials(symbol, freq:"quarterly") — latest quarterly results
3) get_analyst_recommendations(symbol) — consensus estimates
4) get_institutional_holders(symbol) — smart money positioning
5) Prepare comprehensive earnings preview/review.

**Dividend Income Analysis**
1) get_dividends_splits(symbol, period:"5y") — dividend history & consistency
2) get_financials(symbol, freq:"annual") — payout sustainability
3) get_company_profile(symbol) — business stability
4) Evaluate dividend investment potential.

**Japanese Market Focus**
1) get_market_indices(region:"japan") — Nikkei & TOPIX performance
2) get_nikkei_news_with_sentiment(limit:5) — market sentiment & news
3) get_technical_indicators("^N225", indicators:["rsi_14", "sma_20"]) — Nikkei technicals
4) Provide Japanese market analysis in appropriate language.

## PERFORMANCE OPTIMIZATION TIPS

**Token Efficiency**
- Prefer smaller periods/intervals/limits for faster responses
- Use specific indicator arrays rather than defaults
- Avoid requesting full article text unless needed
- Keep RAG searches focused with k ≤ 4

**Tool Selection Strategy**
- Start with get_market_summary() for market context
- Use get_stock_quote() for quick price checks
- Escalate to get_financials() only for deep fundamental analysis
- Combine get_technical_indicators() with get_historical_prices() for chart analysis

**Error Handling**
- Tools may return {"error": "..."}; handle gracefully
- Try smaller periods if "insufficient data" errors occur
- Fallback to simpler tools if complex ones fail

**Multi-Language Support**
- Use locale:"ja" for Japanese responses
- get_nikkei_news_with_sentiment() provides bilingual sentiment
- Market analysis adapts to user's language preference

## WEB SEARCH INTEGRATION

### New Web Search Tools (September 2024)

**Tool: web_search_general**
- Purpose: Real-time web search for current market information and analysis
- Performance: 0.34s average response time, 100% success rate
- Input: query (string), max_results (int, default: 8)
- Returns: {query, results: [{title, url, snippet, source, timestamp, relevance_score}], count, method, duration_seconds}
- Best for: Current market analysis, breaking news, recent earnings reports

**Tool: web_search_financial**  
- Purpose: Financial-focused search with enhanced relevance for market data
- Performance: Near-instantaneous with financial source prioritization
- Input: query (string), max_results (int, default: 8)
- Returns: Enhanced results with financial source attribution
- Best for: Stock analysis, analyst reports, financial news, earnings data

**Tool: web_search_news**
- Purpose: News-focused search for recent developments and market updates  
- Performance: 0.34s average with time filtering optimization
- Input: query (string), max_results (int, default: 8), days_back (int, default: 7)
- Returns: Time-filtered news results with recency scoring
- Best for: Breaking news, market developments, company announcements

**Tool: enhanced_rag_search**
- Purpose: Combined knowledge base + web search for comprehensive analysis
- Performance: 0.65s average, combines internal knowledge with real-time data
- Input: query (string), kb_k (int, default: 3), web_results (int, default: 5), max_total_chunks (int, default: 8)
- Returns: {query, combined_chunks: [{source, title, content, url, relevance_score, type}], sources}
- Best for: Comprehensive analysis requiring both historical knowledge and current information

### Web Search Integration Patterns

**Current Market Analysis**
```
1. get_market_summary() → Market context
2. web_search_news("market sentiment today", max_results=3) → Current sentiment  
3. web_search_financial(f"{symbol} analyst reports latest") → Recent analysis
4. Synthesize comprehensive view
```

**Breaking News Response**
```
1. web_search_news("breaking financial news", max_results=5) → Headlines
2. For major stories: web_search_financial(f"{topic} market impact") → Analysis
3. get_stock_quote(affected_symbols) → Price movements
4. Provide timely market update
```

**Enhanced Stock Research**
```
1. Traditional yfinance analysis (financials, technicals, etc.)
2. web_search_financial(f"{symbol} earnings Q3 2024") → Latest earnings context
3. enhanced_rag_search("investment analysis methodology") → Knowledge base guidance
4. web_search_news(f"{symbol} news", days_back=7) → Recent developments
5. Generate comprehensive investment thesis
```

### Performance Optimizations Implemented
- **12.6x faster web search** (4.28s → 0.34s average response)
- **Zero memory leaks** through proper session management
- **Concurrent API processing** for parallel search execution
- **Intelligent caching** with 5-minute TTL for repeated queries
- **Multi-source fallbacks** ensuring 100% search success rate

## KNOWLEDGE BASE MAINTENANCE

**Reindexing**
- Use RAG API: POST /api/rag/reindex with body {"clear": true} to rebuild the index after changing knowledge files
- Update this guide when new tools are added
- Test new tools with various market conditions
- Reindex after adding web search documentation

**Best Practices**
- Document new tool patterns as they're developed
- Maintain example calls that work reliably  
- Keep performance tips updated based on real usage
- Balance web search with knowledge base for optimal performance
- Use web search for current data, knowledge base for methodology
- Monitor search performance and adjust timeouts as needed

**Knowledge Base Files Added**
- `web_search_guide.md` - Comprehensive web search documentation
- `performance_architecture.md` - System performance and optimization details
- Enhanced `tool_usage.md` - Updated with web search integration patterns




