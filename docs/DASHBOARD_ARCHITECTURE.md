# Dashboard Architecture Diagram

## Overview
The Dashboard module (`app/routers/dashboard.py`) provides real-time stock data streaming and REST endpoints for market data visualization.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Dashboard  │  │  WebSocket   │  │ Market       │          │
│  │   Component  │  │   Client     │  │ Summary      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │ HTTP REST        │ WebSocket        │ HTTP REST
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼──────────────────┐
│         ▼                  ▼                  ▼                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │       FastAPI Router: dashboard.py                   │        │
│  │              /dashboard/*                            │        │
│  └──────────────────┬───────────────────────────────────┘        │
│                     │                                             │
│         ┌───────────┼───────────┐                                │
│         │           │           │                                 │
│         ▼           ▼           ▼                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐                    │
│  │ REST API │ │ WebSocket│ │ Connection   │                    │
│  │ Endpoints│ │ Endpoint │ │ Manager      │                    │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘                    │
│       │            │               │                             │
│       │            │               │                             │
└───────┼────────────┼───────────────┼─────────────────────────────┘
        │            │               │
        │            │               │ Broadcast
        │            │               │ Updates
        ▼            ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Finnhub     │  │  yfinance    │  │ Alpha Vantage│          │
│  │  Service     │  │  Service     │  │  Service     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      External APIs                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Finnhub API │  │ Yahoo Finance│  │ Alpha Vantage│          │
│  │  (US Stocks) │  │ (JP Stocks)  │  │ (News/Sent.) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. REST API Endpoints

```
┌─────────────────────────────────────────────────────────────────┐
│                    REST API Endpoints                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ US Stock Endpoints (Finnhub)                             │  │
│  │                                                           │  │
│  │  GET /dashboard/quote/{symbol}                           │  │
│  │      └─> Get current quote (price, change, volume)       │  │
│  │                                                           │  │
│  │  GET /dashboard/profile/{symbol}                         │  │
│  │      └─> Get company profile (name, country, industry)   │  │
│  │                                                           │  │
│  │  GET /dashboard/search?q={query}                         │  │
│  │      └─> Search stock symbols                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Japanese Stock Endpoints (yfinance)                      │  │
│  │                                                           │  │
│  │  GET /dashboard/jp/quote/{symbol}?with_chart=true        │  │
│  │      └─> Get JP stock quote + chart data                 │  │
│  │                                                           │  │
│  │  GET /dashboard/jp/news/{symbol}?limit=5                 │  │
│  │      └─> Get news articles for JP stock                  │  │
│  │                                                           │  │
│  │  GET /dashboard/jp/trend/{symbol}?period=1mo             │  │
│  │      └─> Get price trend analysis                        │  │
│  │                                                           │  │
│  │  GET /dashboard/jp/market-movers?limit=5                 │  │
│  │      └─> Get top gainers/losers in JP market             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Market News & Sentiment (Alpha Vantage)                  │  │
│  │                                                           │  │
│  │  GET /dashboard/news/sentiment?tickers=AAPL&limit=10     │  │
│  │      └─> Get news with sentiment analysis                │  │
│  │                                                           │  │
│  │  GET /dashboard/market/top-movers                        │  │
│  │      └─> Get US market gainers/losers                    │  │
│  │                                                           │  │
│  │  GET /dashboard/market/status                            │  │
│  │      └─> Get global market open/close status             │  │
│  │                                                           │  │
│  │  GET /dashboard/market/sentiment                         │  │
│  │      └─> Get overall market sentiment (bullish/bearish)  │  │
│  │                                                           │  │
│  │  GET /dashboard/market/summary                           │  │
│  │      └─> Get market summary from free RSS feeds          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Health Check                                             │  │
│  │                                                           │  │
│  │  GET /dashboard/health                                    │  │
│  │      └─> Check service availability                       │  │
│  │                                                           │  │
│  │  GET /dashboard/test                                      │  │
│  │      └─> Test endpoint (no auth required)                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. WebSocket Real-Time Updates

```
┌─────────────────────────────────────────────────────────────────┐
│                  WebSocket Architecture                          │
│                                                                   │
│  Client                     Server                               │
│  ┌──────────┐            ┌──────────────────┐                  │
│  │ Frontend │            │ ConnectionManager│                   │
│  │ Dashboard│◄──────────►│                  │                   │
│  └──────────┘            │  - connections[] │                   │
│       │                  │  - subscriptions{}│                   │
│       │                  └────────┬──────────┘                   │
│       │                           │                               │
│       │ 1. Connect                │                               │
│       ├──────────────────────────►│                               │
│       │                           │                               │
│       │ 2. Subscribe              │                               │
│       │  {"action":"subscribe",   │                               │
│       │   "symbols":["AAPL"]}     │                               │
│       ├──────────────────────────►│                               │
│       │                           │                               │
│       │                           ├─► Store subscription          │
│       │                           │                               │
│       │ 3. Start Update Loop      │                               │
│       │                           ├─► Async Task Created          │
│       │                           │   ┌────────────────┐          │
│       │                           │   │ send_updates() │          │
│       │                           │   │                │          │
│       │                           │   │ while True:    │          │
│       │                           │   │   for symbol:  │          │
│       │                           │   │     fetch()    │          │
│       │                           │   │     send()     │          │
│       │                           │   │     sleep(1.5s)│          │
│       │                           │   └────────────────┘          │
│       │                           │                               │
│       │ 4. Quote Updates          │                               │
│       │  {"type":"quote_update",  │                               │
│       │   "data":{...}}           │                               │
│       │◄──────────────────────────┤                               │
│       │                           │                               │
│       │ 5. Unsubscribe            │                               │
│       │  {"action":"unsubscribe", │                               │
│       │   "symbols":["AAPL"]}     │                               │
│       ├──────────────────────────►│                               │
│       │                           │                               │
│       │ 6. Disconnect             │                               │
│       ├──────────────────────────►│                               │
│       │                           │                               │
│       │                           ├─► Cleanup subscriptions       │
│       │                           ├─► Cancel update task          │
│       │                           ├─► Remove connection           │
│                                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Rate Limiting Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│              Finnhub API Rate Limiting (Free Tier)               │
│                                                                   │
│  Limit: 60 API calls per minute (1 call/second)                 │
│                                                                   │
│  Strategy:                                                        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  1. Sequential Updates (Not Parallel)                     │ │
│  │     ┌──────┐      ┌──────┐      ┌──────┐                 │ │
│  │     │ AAPL │ 1.5s │ MSFT │ 1.5s │ TSLA │                 │ │
│  │     └──────┘ ───► └──────┘ ───► └──────┘                 │ │
│  │                                                            │ │
│  │  2. 1.5 Second Delay Between Calls                        │ │
│  │     (Safe margin: 60 calls/min = 1 call/1.5s = 40/min)   │ │
│  │                                                            │ │
│  │  3. Rate Limit Detection                                  │ │
│  │     If API returns rate limit error:                      │ │
│  │       - Send warning to client                            │ │
│  │       - Pause updates for 60 seconds                      │ │
│  │       - Resume after cooldown                             │ │
│  │                                                            │ │
│  │  4. Update Frequency Per Symbol                           │ │
│  │     Watchlist: [AAPL, MSFT, TSLA, GOOGL, AMZN]          │ │
│  │     Cycle time: 5 symbols × 1.5s = 7.5 seconds           │ │
│  │     Each symbol updated every ~8 seconds                  │ │
│  │                                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Connection Manager Class

```
┌─────────────────────────────────────────────────────────────────┐
│                    ConnectionManager                             │
│                                                                   │
│  Properties:                                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ active_connections: List[WebSocket]                       │ │
│  │   └─> All currently connected WebSocket clients           │ │
│  │                                                            │ │
│  │ subscriptions: dict[WebSocket, set[str]]                  │ │
│  │   └─> Maps each connection to its subscribed symbols      │ │
│  │       Example: {                                          │ │
│  │         <WebSocket1>: {"AAPL", "MSFT"},                   │ │
│  │         <WebSocket2>: {"TSLA", "GOOGL"}                   │ │
│  │       }                                                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Methods:                                                         │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ async connect(websocket: WebSocket)                       │ │
│  │   1. Accept WebSocket connection                          │ │
│  │   2. Add to active_connections list                       │ │
│  │   3. Initialize empty subscription set                    │ │
│  │   4. Log connection count                                 │ │
│  │                                                            │ │
│  │ disconnect(websocket: WebSocket)                          │ │
│  │   1. Remove from active_connections                       │ │
│  │   2. Delete subscriptions entry                           │ │
│  │   3. Log remaining connections                            │ │
│  │                                                            │ │
│  │ subscribe(websocket: WebSocket, symbol: str)              │ │
│  │   1. Add symbol to connection's subscription set          │ │
│  │   2. Convert symbol to uppercase                          │ │
│  │   3. Log subscription                                     │ │
│  │                                                            │ │
│  │ unsubscribe(websocket: WebSocket, symbol: str)            │ │
│  │   1. Remove symbol from subscription set                  │ │
│  │   2. Log unsubscription                                   │ │
│  │                                                            │ │
│  │ async broadcast_quote(symbol: str, data: dict)            │ │
│  │   1. Loop through all connections                         │ │
│  │   2. Check if connection subscribed to symbol             │ │
│  │   3. Send quote_update message                            │ │
│  │   4. Handle disconnected clients                          │ │
│  │   5. Cleanup failed connections                           │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Data Flow: Quote Request

```
┌─────────────────────────────────────────────────────────────────┐
│              GET /dashboard/quote/AAPL Flow                      │
│                                                                   │
│  1. Request                                                       │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ GET /dashboard/quote/AAPL                           │    │
│     │ Headers: Authorization: Bearer {JWT_TOKEN}          │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  2. Authentication     ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ get_current_user(JWT_TOKEN)                         │    │
│     │   └─> Verify token, extract user                    │    │
│     │   └─> Check if user is authenticated                │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  3. Validate API Key   ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ if not FINNHUB_API_KEY:                             │    │
│     │     return HTTPException(503)                       │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  4. Call Service       ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ get_finnhub_quote("AAPL", FINNHUB_API_KEY)         │    │
│     │   ├─> Build API URL                                 │    │
│     │   ├─> Send HTTP request to Finnhub                  │    │
│     │   ├─> Parse response JSON                           │    │
│     │   └─> Return quote data                             │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  5. Response           ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ {                                                    │    │
│     │   "symbol": "AAPL",                                 │    │
│     │   "current_price": 178.23,                          │    │
│     │   "change": 2.45,                                   │    │
│     │   "percent_change": 1.39,                           │    │
│     │   "high": 179.50,                                   │    │
│     │   "low": 176.80,                                    │    │
│     │   "open": 177.00,                                   │    │
│     │   "previous_close": 175.78                          │    │
│     │ }                                                    │    │
│     └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 6. Data Flow: Market Sentiment

```
┌─────────────────────────────────────────────────────────────────┐
│          GET /dashboard/market/sentiment Flow                    │
│                                                                   │
│  1. Request                                                       │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ GET /dashboard/market/sentiment                     │    │
│     │ Headers: Authorization: Bearer {JWT_TOKEN}          │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  2. Fetch News         ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ alphavantage_service.get_news_sentiment(            │    │
│     │     topics="economy_macro,financial_markets",       │    │
│     │     limit=50                                        │    │
│     │ )                                                    │    │
│     │   └─> Fetch 50 recent financial news articles       │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  3. Aggregate Scores   ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ For each article:                                    │    │
│     │   sentiment_score = article["overall_sentiment"]    │    │
│     │   relevance = article["relevance_score"]            │    │
│     │   total_score += sentiment_score × relevance        │    │
│     │   total_relevance += relevance                      │    │
│     │                                                      │    │
│     │   if "bullish": bullish_count++                     │    │
│     │   if "bearish": bearish_count++                     │    │
│     │   if "neutral": neutral_count++                     │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  4. Calculate Metrics  ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ avg_sentiment = total_score / total_relevance       │    │
│     │                                                      │    │
│     │ if avg_sentiment > 0.15:  sentiment = "bullish"     │    │
│     │ if avg_sentiment < -0.15: sentiment = "bearish"     │    │
│     │ else:                     sentiment = "neutral"     │    │
│     │                                                      │    │
│     │ agreement = max_count / total_articles              │    │
│     │                                                      │    │
│     │ if articles ≥ 30 and agreement > 0.6:               │    │
│     │     confidence = "high"                             │    │
│     │ elif articles ≥ 15 and agreement > 0.5:             │    │
│     │     confidence = "medium"                           │    │
│     │ else:                                                │    │
│     │     confidence = "low"                              │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  5. Response           ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ {                                                    │    │
│     │   "sentiment": "bullish",                           │    │
│     │   "sentiment_score": 0.234,                         │    │
│     │   "confidence": "high",                             │    │
│     │   "article_count": 45,                              │    │
│     │   "bullish_count": 28,                              │    │
│     │   "bearish_count": 8,                               │    │
│     │   "neutral_count": 9,                               │    │
│     │   "last_updated": "2025-10-03T12:34:56Z"           │    │
│     │ }                                                    │    │
│     └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 7. Data Flow: Market Summary (Free RSS)

```
┌─────────────────────────────────────────────────────────────────┐
│          GET /dashboard/market/summary Flow                      │
│                                                                   │
│  1. Request                                                       │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ GET /dashboard/market/summary                       │    │
│     │ Headers: Authorization: Bearer {JWT_TOKEN}          │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  2. Fetch Free News    ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ free_news_service.get_market_news(                  │    │
│     │     categories=["financial", "crypto", "commodities"]│   │
│     │     limit_per_category=15                           │    │
│     │ )                                                    │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  3. Fetch RSS Feeds    ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ For each category:                                   │    │
│     │                                                      │    │
│     │   Financial:                                         │    │
│     │     ├─> Yahoo Finance RSS                           │    │
│     │     ├─> CNBC Top News RSS                           │    │
│     │     └─> CNBC Earnings RSS                           │    │
│     │                                                      │    │
│     │   Crypto:                                            │    │
│     │     ├─> CoinTelegraph RSS                           │    │
│     │     └─> CoinDesk RSS                                │    │
│     │                                                      │    │
│     │   Commodities:                                       │    │
│     │     └─> Investing.com RSS                           │    │
│     │                                                      │    │
│     │   Parse with feedparser (5s timeout per feed)       │    │
│     │   Extract: title, content, source, url              │    │
│     │   Deduplicate by title                              │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  4. Categorize         ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ Analyze article titles/content for keywords:         │    │
│     │                                                      │    │
│     │   Stock Market:                                      │    │
│     │     - General: S&P 500, Nasdaq, Dow Jones           │    │
│     │     - Corporate: Tesla, Apple, Google, etc.         │    │
│     │                                                      │    │
│     │   Cryptocurrency:                                    │    │
│     │     - Bitcoin, Ethereum, crypto, blockchain         │    │
│     │                                                      │    │
│     │   Commodities:                                       │    │
│     │     - Gold, oil, silver, copper                     │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  5. Generate Summaries ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ For each category:                                   │    │
│     │   - Take top 5 articles                             │    │
│     │   - Truncate content to 300 chars                   │    │
│     │   - Count unique sources                            │    │
│     │   - Format as section                               │    │
│     └──────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│  6. Response           ▼                                         │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ {                                                    │    │
│     │   "sections": [                                     │    │
│     │     {                                                │    │
│     │       "section_title": "Stock Market News",         │    │
│     │       "items": [                                    │    │
│     │         {                                            │    │
│     │           "title": "S&P 500 Hits Record...",        │    │
│     │           "content": "The S&P 500 and...",          │    │
│     │           "source": "Yahoo Finance",                │    │
│     │           "url": "https://..."                      │    │
│     │         }                                            │    │
│     │       ],                                             │    │
│     │       "source_count": 3                             │    │
│     │     },                                               │    │
│     │     { ... crypto section ... },                     │    │
│     │     { ... commodities section ... }                 │    │
│     │   ],                                                 │    │
│     │   "last_updated": "2025-10-03T12:34:56Z",          │    │
│     │   "total_articles": 45,                             │    │
│     │   "sources": "Yahoo Finance RSS, CNBC RSS..."       │    │
│     │ }                                                    │    │
│     └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Service Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ finnhub_service.py                                       │  │
│  │                                                           │  │
│  │  Functions:                                              │  │
│  │  ├─ get_finnhub_quote(symbol, api_key)                  │  │
│  │  │    └─> GET /quote?symbol={symbol}                    │  │
│  │  │        Returns: price, change, volume, timestamps    │  │
│  │  │                                                       │  │
│  │  ├─ get_finnhub_company_profile(symbol, api_key)        │  │
│  │  │    └─> GET /stock/profile2?symbol={symbol}           │  │
│  │  │        Returns: name, country, industry, logo        │  │
│  │  │                                                       │  │
│  │  └─ search_finnhub_symbols(query, api_key)              │  │
│  │       └─> GET /search?q={query}                         │  │
│  │           Returns: matching symbols with descriptions   │  │
│  │                                                           │  │
│  │  Rate Limiting: 60 calls/minute (free tier)             │  │
│  │  Circuit Breaker: Detects rate limits, returns error    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ yfinance_service.py                                      │  │
│  │                                                           │  │
│  │  Functions:                                              │  │
│  │  ├─ get_stock_info(symbol, with_chart=False)            │  │
│  │  │    └─> Uses yfinance.Ticker(symbol)                  │  │
│  │  │        Returns: price, PE ratio, volume, market cap  │  │
│  │  │        Optional: chart data for multiple timeframes  │  │
│  │  │                                                       │  │
│  │  ├─ get_stock_news(symbol, limit=5)                     │  │
│  │  │    └─> ticker.news                                   │  │
│  │  │        Returns: articles with title, link, date      │  │
│  │  │                                                       │  │
│  │  ├─ get_price_history(symbol, period="1mo")             │  │
│  │  │    └─> ticker.history(period)                        │  │
│  │  │        Returns: OHLCV data + trend analysis          │  │
│  │  │                                                       │  │
│  │  └─ get_japanese_market_movers(limit=5)                 │  │
│  │       └─> Fetch TOPIX components                        │  │
│  │           Calculate gainers/losers                      │  │
│  │           Returns: top movers in JP market              │  │
│  │                                                           │  │
│  │  No Rate Limits: Free unlimited access                  │  │
│  │  Best for: Japanese stocks (.T suffix)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ alphavantage_service.py                                  │  │
│  │                                                           │  │
│  │  Functions:                                              │  │
│  │  ├─ get_news_sentiment(tickers, topics, limit)          │  │
│  │  │    └─> GET /query?function=NEWS_SENTIMENT            │  │
│  │  │        Returns: articles with sentiment scores       │  │
│  │  │                                                       │  │
│  │  ├─ get_top_gainers_losers()                            │  │
│  │  │    └─> GET /query?function=TOP_GAINERS_LOSERS        │  │
│  │  │        Returns: US market movers                     │  │
│  │  │                                                       │  │
│  │  └─ get_global_market_status()                          │  │
│  │       └─> GET /query?function=MARKET_STATUS             │  │
│  │           Returns: market open/close times worldwide    │  │
│  │                                                           │  │
│  │  Rate Limiting: 25 calls/day (free tier)                │  │
│  │  Error Handling: Returns cached/fallback on limit       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ free_news_service.py                                     │  │
│  │                                                           │  │
│  │  Functions:                                              │  │
│  │  ├─ fetch_rss_feeds(category, limit)                    │  │
│  │  │    └─> Parse RSS feeds with feedparser               │  │
│  │  │        5 second timeout per feed                     │  │
│  │  │        Returns: articles from free sources           │  │
│  │  │                                                       │  │
│  │  ├─ get_market_news(categories, limit_per_category)     │  │
│  │  │    └─> Fetch multiple RSS feeds                      │  │
│  │  │        Deduplicate by title                          │  │
│  │  │        Returns: categorized news                     │  │
│  │  │                                                       │  │
│  │  └─ generate_summary_from_news(articles, title)         │  │
│  │       └─> Format articles as summary section            │  │
│  │           Truncate content to 300 chars                 │  │
│  │           Count unique sources                          │  │
│  │                                                           │  │
│  │  No API Keys Required: 100% free RSS feeds              │  │
│  │  Sources: Yahoo, CNBC, CoinTelegraph, CoinDesk          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Authentication Layer                          │
│                                                                   │
│  All dashboard endpoints require authentication:                 │
│                                                                   │
│  Request                                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ GET /dashboard/*                                       │    │
│  │ Headers:                                               │    │
│  │   Authorization: Bearer eyJhbGc...                     │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │                                            │
│                     ▼                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Depends(get_current_user)                             │    │
│  │                                                        │    │
│  │  1. Extract JWT token from Authorization header       │    │
│  │  2. Decode and verify token                           │    │
│  │  3. Extract user_id from token payload                │    │
│  │  4. Query database for user                           │    │
│  │  5. Return User object                                │    │
│  │                                                        │    │
│  │  If invalid/expired:                                   │    │
│  │    └─> Raise HTTPException(401, "Not authenticated")  │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │                                            │
│                     ▼                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Endpoint Handler                                       │    │
│  │   - Has access to current_user: User                  │    │
│  │   - Can log user actions                              │    │
│  │   - Can apply user-specific logic                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Exception: /dashboard/test endpoint (no auth required)          │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Strategy                       │
│                                                                   │
│  1. API Key Missing                                              │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ if not FINNHUB_API_KEY:                             │   │
│     │     raise HTTPException(                            │   │
│     │         status_code=503,                            │   │
│     │         detail="Finnhub API key not configured"     │   │
│     │     )                                                │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                   │
│  2. Rate Limit Reached                                           │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ if quote.get("rate_limited"):                       │   │
│     │     await websocket.send_json({                     │   │
│     │         "type": "rate_limit_warning",               │   │
│     │         "message": "Rate limit reached..."          │   │
│     │     })                                               │   │
│     │     await asyncio.sleep(60)  # Wait 1 minute        │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                   │
│  3. Service Error                                                │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ try:                                                 │   │
│     │     data = service.fetch()                          │   │
│     │ except Exception as e:                              │   │
│     │     logger.error(f"Service error: {e}")             │   │
│     │     raise HTTPException(                            │   │
│     │         status_code=500,                            │   │
│     │         detail=str(e)                               │   │
│     │     )                                                │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                   │
│  4. WebSocket Disconnect                                         │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ try:                                                 │   │
│     │     await websocket.send_json(data)                 │   │
│     │ except Exception as e:                              │   │
│     │     logger.error(f"WebSocket error: {e}")           │   │
│     │     disconnected.append(connection)                 │   │
│     │     # Cleanup in finally block                      │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                   │
│  5. Fallback Data                                                │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ if "error" in sentiment_data:                       │   │
│     │     return {                                         │   │
│     │         "sentiment": "neutral",                     │   │
│     │         "sentiment_score": 0.0,                     │   │
│     │         "confidence": "low",                        │   │
│     │         "error": sentiment_data["error"]            │   │
│     │     }                                                │   │
│     └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Optimizations

```
┌─────────────────────────────────────────────────────────────────┐
│                   Performance Features                           │
│                                                                   │
│  1. Async/Await for WebSocket                                    │
│     - Non-blocking I/O operations                                │
│     - Multiple connections handled concurrently                  │
│     - Background tasks for updates                               │
│                                                                   │
│  2. Rate Limit Management                                        │
│     - Sequential API calls (not parallel)                        │
│     - Strategic delays between requests                          │
│     - Automatic cooldown on rate limit                           │
│                                                                   │
│  3. Connection Pooling                                           │
│     - Reuse HTTP connections to external APIs                    │
│     - Reduce handshake overhead                                  │
│                                                                   │
│  4. Error Recovery                                               │
│     - Graceful fallbacks for API failures                        │
│     - Cached data returned when available                        │
│     - Client notifications for service issues                    │
│                                                                   │
│  5. RSS Feed Timeouts                                            │
│     - 5 second timeout per feed                                  │
│     - Skip slow/unavailable feeds                                │
│     - Continue with available data                               │
│                                                                   │
│  6. Logging                                                       │
│     - Structured logging for debugging                           │
│     - Connection tracking                                        │
│     - Error context preservation                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **WebSocket for Real-Time Updates**: Provides low-latency stock updates without polling
2. **Sequential API Calls**: Respects Finnhub's rate limits while maintaining data freshness
3. **Multi-Provider Strategy**: Uses Finnhub (US), yfinance (JP), Alpha Vantage (news)
4. **Free RSS Feeds**: No-cost market summary using public RSS feeds
5. **Connection Manager**: Centralized WebSocket lifecycle management
6. **Rate Limit Detection**: Proactive handling of API quota exhaustion
7. **Graceful Degradation**: Returns cached/fallback data when services unavailable
8. **Type Safety**: Pydantic models for request/response validation
9. **Authentication**: JWT-based security on all endpoints (except test)
10. **Comprehensive Logging**: Debug and monitor all service interactions
