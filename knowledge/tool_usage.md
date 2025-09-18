# Curated Tool Usage Guide

This page documents all available tools with tight JSON schemas, allowed values, defaults, and examples. Follow these patterns to avoid trial-and-error calls, reduce latency, and keep token usage low.

General rules
- Always use the parameter names exactly as listed (e.g., symbol, not ticker). Booleans are true/false, not strings.
- Prefer small limits and concise periods/intervals to minimize tokens.
- If you only need a price or a short fact, do not fetch large histories or augmented news.
- Tools may return {"error": "..."}; handle gracefully and try a smaller/simpler call if needed.

Note: For OSS-style pseudo tool markup, the router will remap ticker->symbol, but you should still prefer symbol.

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

Quick recipes
- Latest price then short rationale
  1) get_stock_quote(symbol)
  2) Generate a 1–2 sentence answer; avoid extra tool calls.
- Trend snapshot
  1) get_historical_prices(symbol, period:"5d", interval:"1d", limit:5)
  2) Summarize movement and volatility briefly.
- Headline-driven summary with KB grounding
  1) get_augmented_news(symbol, limit:5, include_full_text:false, include_rag:true, rag_k:2)
  2) Synthesize 3 bullets; cite 1–2 sources by publisher/date.
- Risk profile
  1) get_risk_assessment(symbol, period:"1y", interval:"1d", benchmark:"SPY")
  2) Explain volatility, Sharpe, max drawdown, beta succinctly.

Performance tips
- Prefer smaller periods/intervals/limits.
- Avoid requesting full article text unless needed.
- When using rag_search, keep k ≤ 4 and avoid pasting large chunks back into the conversation.

Reindex the KB after edits
- Use the RAG API: POST /api/rag/reindex with body {"clear": true} to rebuild the index after changing knowledge files.

