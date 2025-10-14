# Comprehensive Stock Analysis Tool Guide

This page documents all available tools for comprehensive financial analysis and market research. The system uses **hybrid ML + document-based tool selection** to intelligently choose the most relevant tools for each query.

## Tool Selection System

The system uses a two-stage intelligent tool selection process:

**Stage 1: ML/Hybrid Selector** (Your assistant's brain)
- Analyzes your query using machine learning
- Narrows down from 24+ tools to 2-5 most relevant tools
- Uses hybrid approach: ML classifier + document-based similarity
- Confidence threshold: 0.40 (triggers doc-based fallback when lower)

**Stage 2: OpenAI Function Calling** (GPT decides)
- Receives the filtered tool list from Stage 1
- Decides which specific tool(s) to actually call based on query context
- May call 0, 1, or multiple tools depending on what's needed

**Example Flow:**
```
Query: "詳細な事業内容や最新ニュース" (business info and news)
Stage 1: ML selects ['perplexity_search', 'get_stock_quote'] 
Stage 2: GPT calls only 'perplexity_search' (more relevant for news)
```

## General Rules

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

---

Tool: perplexity_search
- Purpose: **PRIORITY TOOL** - Enhanced web search with AI-powered answer synthesis
- Input
  - query: string (required) - Search query in any language (supports Japanese, English, etc.)
  - max_results: integer (default: 8) - Maximum number of search results to process
  - synthesize_answer: boolean (default: true) - Whether to generate AI-synthesized answer
  - include_recent: boolean (default: true) - Whether to prioritize recent content
- Returns
  - { query, answer, citations: {}, sources: [], css_styles, method, duration }
- Example call
  - {"type":"function","function":{"name":"perplexity_search","arguments":"{\"query\":\"Tesla earnings Q4 2024\",\"max_results\":5}"}}
- Tips
  - **Use whenever you're uncertain or lack current information**
  - Primary tool for real-time information, current events, recent news
  - Supports Japanese queries with bilingual results
  - Returns properly cited answers with source attribution
  - Performance: ~500ms average response time

---

Tool: augmented_rag_search
- Purpose: **COMPREHENSIVE SEARCH** - Combines knowledge base and web search
- Input
  - query: string (required) - Search query for augmented RAG
  - kb_k: integer (default: 3) - Number of knowledge base chunks to retrieve
  - web_results: integer (default: 5) - Number of web search results
  - include_web: boolean (default: true) - Whether to include web search
  - web_content: boolean (default: true) - Whether to fetch full content from web pages
- Returns
  - { query, combined_chunks: [{source, title, content, url, relevance_score, type}], sources }
- Example call
  - {"type":"function","function":{"name":"augmented_rag_search","arguments":"{\"query\":\"stock analysis methodology\",\"kb_k\":3,\"web_results\":5}"}}
- Tips
  - Use for complex queries requiring both internal knowledge and current information
  - Always includes web search by default for most current data
  - Best for comprehensive research and analysis

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

## STOCK PREDICTION TOOLS (AI/ML)

Tool: predict_stock_price
- Purpose: AI-powered stock price prediction using LSTM neural network
- Input
  - symbol: string (required) - Stock ticker symbol (e.g., AAPL, 8359.T)
  - days: integer (default: 7) - Number of days to predict (1-30)
  - auto_train: boolean (default: true) - Auto-train model if not found
- Returns
  - { symbol, predictions: [{date, predicted_price}], trend, confidence, model_info }
- Example call
  - {"type":"function","function":{"name":"predict_stock_price","arguments":"{\"symbol\":\"AAPL\",\"days\":7}"}}
- Tips
  - Optimized for lightweight GPU (GTX 1650 Ti)
  - Returns predicted prices with trend analysis
  - Requires trained model (auto-trains if needed)
  - Best for 7-14 day predictions

---

Tool: train_model
- Purpose: Train LSTM prediction model for a stock symbol
- Input
  - symbol: string (required) - Stock ticker symbol to train model for
  - period: string (default: "2y") - Historical data period for training (1y, 2y, 5y)
  - save_model: boolean (default: true) - Whether to save trained model
- Returns
  - { symbol, training_metrics: {loss, mae}, model_saved, training_time }
- Example call
  - {"type":"function","function":{"name":"train_model","arguments":"{\"symbol\":\"TSLA\",\"period\":\"2y\"}"}}
- Tips
  - Use when prediction model doesn't exist or needs retraining
  - Uses 2 years of historical data by default
  - Model is saved for future predictions
  - Returns training metrics (loss, MAE)

---

Tool: get_model_info
- Purpose: Get information about trained prediction model
- Input
  - symbol: string (required) - Stock ticker symbol
- Returns
  - { symbol, model_exists, training_date, performance_metrics, model_config }
- Example call
  - {"type":"function","function":{"name":"get_model_info","arguments":"{\"symbol\":\"AAPL\"}"}}
- Tips
  - Shows training date, performance metrics, and model configuration
  - Use to check if model exists before prediction

---

Tool: list_available_models
- Purpose: List all available trained prediction models
- Input
  - (no parameters required)
- Returns
  - { count, models: [{symbol, training_date, performance_metrics}] }
- Example call
  - {"type":"function","function":{"name":"list_available_models","arguments":"{}"}}
- Tips
  - Shows all trained models with their training dates and performance metrics
  - Useful for checking which stocks have prediction models available

---

## COMPREHENSIVE ANALYSIS RECIPES

**Quick Price Check**
1) get_stock_quote(symbol)
2) Generate a 1–2 sentence answer; avoid extra tool calls.

**Web-Enhanced Stock Research**
1) get_stock_quote(symbol) — current price
2) get_company_profile(symbol) — basic info
3) perplexity_search(f"{symbol} recent news and analyst opinions") — current market sentiment
4) get_technical_indicators(symbol, indicators:["rsi_14", "sma_20"]) — technical analysis
5) Synthesize comprehensive view with recent context

**Stock Price Prediction Analysis**
1) predict_stock_price(symbol, days:7) — AI prediction for next week
2) get_historical_prices(symbol, period:"3mo") — recent price history
3) get_technical_indicators(symbol, period:"3mo") — technical signals
4) get_risk_assessment(symbol, period:"1y") — risk metrics
5) Generate prediction analysis with risk assessment

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
- Use perplexity_search instead of multiple news tools for current info

**Tool Selection Strategy (Handled Automatically by ML)**
- System uses **hybrid ML + document-based selection** (0.40 confidence threshold)
- ML classifier provides fast tool selection for trained patterns
- Doc-based fallback uses embedding similarity to this guide when ML confidence is low
- You don't need to manually select tools - the system does it intelligently

**When ML Selector Triggers Doc-Based Fallback:**
- Query confidence < 0.40 (e.g., vague or unusual queries)
- Meta-queries about tool capabilities (e.g., "Which tool gets institutional data?")
- New or uncommon use cases not in training data
- Doc-based finds specific tools by matching query to tool descriptions in this guide

**Example of Hybrid Selection in Action:**
```
Query: "Which tool retrieves institutional ownership data?"
ML-only: get_technical_indicators, perplexity_search (0.375 confidence)
Hybrid: Added get_institutional_holders (doc-based found the right tool!)
```

**Error Handling**
- Tools may return {"error": "..."}; handle gracefully
- Try smaller periods if "insufficient data" errors occur
- Fallback to simpler tools if complex ones fail

**Multi-Language Support**
- System supports Japanese queries natively
- get_nikkei_news_with_sentiment() provides bilingual sentiment
- perplexity_search handles multilingual queries
- Market analysis adapts to user's language preference automatically

## TOOL SELECTION PERFORMANCE

**ML Selector Statistics** (Your assistant's performance)
- Average prediction time: 500-700ms (includes embedding + classification)
- ML confidence threshold: 0.40 (triggers doc-based when lower)
- Typical tool count: 2-3 tools per query
- Doc-based fallback rate: ~10-20% (triggered for unusual queries)

**Two-Stage Tool Selection Flow:**
```
User Query
    ↓
ML/Hybrid Selector (Stage 1)
    ├─ ML Classifier (fast, trained on usage patterns)
    │  └─ Confidence ≥ 0.40? → Return tools
    └─ Doc-Based Fallback (embedding similarity to this guide)
       └─ Confidence < 0.40? → Augment with doc-based tools
    ↓
Filtered Tool List (2-5 tools)
    ↓
OpenAI Function Calling (Stage 2)
    └─ GPT decides which tool(s) to actually call
    ↓
Tool Execution (0-N tools)
```

**Why You May See Different Tool Counts:**
- **Selected**: Tools suggested by ML/hybrid selector (Stage 1)
- **Executed**: Tools actually called by GPT (Stage 2)
- Example: Selected 2 tools, but GPT only executed 1 (most relevant)

## WEB SEARCH INTEGRATION

**Primary Web Search Tool: perplexity_search**
- **Purpose**: Enhanced web search with AI-powered answer synthesis
- **Performance**: ~500ms average response time
- **Use whenever**: You need current information, real-time data, or recent news
- **Supports**: Multilingual queries (Japanese, English, etc.)
- **Returns**: Properly cited answers with source attribution

**Comprehensive Search: augmented_rag_search**
- **Purpose**: Combines knowledge base + web search
- **Performance**: ~1-2s (includes both KB and web search)
- **Use for**: Complex queries needing both historical knowledge and current info
- **Best for**: Investment methodology + current market analysis

### Web Search Integration Patterns

**Current Market Analysis**
```
1. get_market_summary() → Market context
2. perplexity_search("market sentiment today") → Current sentiment with AI synthesis
3. get_stock_quote(symbols) → Price movements
4. Synthesize comprehensive view
```

**Breaking News Response**
```
1. perplexity_search("breaking financial news today") → AI-synthesized headlines
2. get_stock_quote(affected_symbols) → Price impacts
3. Provide timely market update with citations
```

**Enhanced Stock Research**
```
1. get_company_profile(symbol) → Basic info
2. get_stock_quote(symbol) → Current price
3. perplexity_search(f"{symbol} recent analyst reports and earnings") → Latest context
4. get_technical_indicators(symbol) → Technical analysis
5. augmented_rag_search("investment analysis best practices") → Methodology guidance
6. Generate comprehensive investment thesis
```

**AI-Powered Stock Prediction**
```
1. predict_stock_price(symbol, days=7) → AI prediction
2. get_historical_prices(symbol, period="3mo") → Recent history
3. perplexity_search(f"{symbol} upcoming catalysts") → Market-moving events
4. get_risk_assessment(symbol) → Risk metrics
5. Generate prediction analysis with risk assessment
```

### Performance Optimizations
- **Hybrid tool selection**: ML + doc-based (500-700ms)
- **Fast web search**: perplexity_search (~500ms average)
- **Intelligent caching**: 5-minute TTL for repeated queries
- **Concurrent processing**: Parallel tool execution when possible
- **Smart truncation**: Citation-preserving content reduction

## KNOWLEDGE BASE MAINTENANCE

**Reindexing**
- Use RAG API: POST /api/rag/reindex with body {"clear": true} to rebuild the index after changing knowledge files
- Update this guide when new tools are added
- Test new tools with various market conditions
- Reindex after updating this documentation

**Best Practices for This Guide**
- Document new tool patterns as they're developed
- Maintain example calls that work reliably  
- Keep performance tips updated based on real usage
- Update tool descriptions when APIs change
- **Important**: Doc-based tool selector parses this guide to find relevant tools
- Use clear, descriptive tool purposes and tips for better ML/doc-based matching

**How Doc-Based Selector Uses This Guide:**
1. Parses each "Tool: tool_name" section
2. Extracts Purpose, Parameters, and Tips for each tool
3. Creates embeddings of tool descriptions
4. When ML confidence is low (<0.40), matches query to tool descriptions
5. Returns tools with highest semantic similarity to user query

**Example of Effective Tool Description:**
```
Tool: get_institutional_holders
- Purpose: Institutional ownership, mutual fund holders, major shareholders
- Tips: Analyze institutional confidence and ownership concentration
```
Query: "Which tool retrieves institutional ownership data?"
→ Doc-based matches "institutional ownership" → Selects get_institutional_holders ✓

**Knowledge Base Files in System**
- `tool_usage.md` - This comprehensive guide (you are here!)
- Used by doc-based selector for intelligent tool discovery
- Updated: October 2025 with hybrid ML + doc-based tool selection

**System Architecture:**
- **24+ total tools** available across stock analysis, news, predictions, and web search
- **ML classifier** trained on usage patterns (10 tools in training set)
- **Doc-based fallback** uses embeddings of this guide (20+ tools documented)
- **Hybrid approach** provides best coverage: speed (ML) + completeness (doc-based)




