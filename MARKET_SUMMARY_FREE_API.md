# Market Summary Feature - Free API Version

## Overview
The Market Summary feature provides a comprehensive overview of current market news across different categories (stocks, crypto, commodities) using **completely free data sources** - no paid API keys required!

## Features

### 📰 **Multi-Source News Aggregation**
- **Yahoo Finance RSS** - Stock market headlines
- **CNBC RSS** - Business and earnings news  
- **CoinTelegraph RSS** - Cryptocurrency news
- **CoinDesk RSS** - Bitcoin and blockchain updates
- **Investing.com RSS** - Commodities (gold, oil, etc.)
- **Optional: NewsAPI.org** - Enhanced coverage (100 free requests/day)

### 🎯 **Smart Categorization**
- **Stock Market News** - Indices, market trends, economic data
- **Notable Corporate Moves** - Earnings, acquisitions, major announcements
- **Cryptocurrency** - Bitcoin, Ethereum, blockchain developments
- **Commodities** - Gold, oil, silver, energy markets

### 💡 **Key Features**
- ✅ **100% Free** - No API keys required for basic functionality
- ✅ **Real-time Updates** - Latest news from RSS feeds
- ✅ **Click to View** - Modal overlay with expandable sections
- ✅ **Persistent State** - Remains on dashboard when opened
- ✅ **Source Attribution** - Links to original articles
- ✅ **Dark Theme** - Matches application design

## Architecture

### Backend

#### Free News Service (`app/services/free_news_service.py`)

**Primary Function:**
```python
get_market_news(categories: List[str], limit_per_category: int) -> Dict[str, List[Dict]]
```

**Data Sources:**
1. **RSS Feeds** (Always free, no limits):
   - Yahoo Finance, CNBC, CoinTelegraph, CoinDesk, Investing.com
   - Parsed using `feedparser` library
   - No authentication required

2. **NewsAPI.org** (Optional, 100 requests/day):
   - Set `NEWSAPI_API_KEY` environment variable
   - Falls back to RSS if not configured
   - Get free key: https://newsapi.org/

**Article Structure:**
```python
{
    "title": str,        # Article headline
    "content": str,      # Summary/description
    "source": str,       # Publisher name
    "url": str,          # Link to full article
    "published": str,    # Publication timestamp
    "image": str | None  # Optional thumbnail
}
```

#### Dashboard Endpoint

**Route:** `GET /dashboard/market/summary`

**Authentication:** Required (JWT Bearer token)

**Response Format:**
```json
{
  "sections": [
    {
      "section_title": "Stock Market News",
      "items": [
        {
          "title": "S&P 500 Hits Record High...",
          "content": "The S&P 500 and Nasdaq reached...",
          "source": "Yahoo Finance",
          "url": "https://..."
        }
      ],
      "source_count": 5
    }
  ],
  "last_updated": "2025-10-03T12:34:56.789Z",
  "total_articles": 45,
  "sources": "Yahoo Finance RSS, CNBC RSS, CoinTelegraph, and more"
}
```

### Frontend

#### MarketSummary Component (`frontend/src/components/dashboard/MarketSummary.tsx`)

**Props:**
```typescript
interface MarketSummaryProps {
  isOpen: boolean      // Controls visibility
  onClose: () => void  // Callback to close modal
}
```

**Features:**
- 🔄 **Auto-refresh** - Manual refresh button with loading state
- 📂 **Collapsible Sections** - Click to expand/collapse categories
- 🔗 **External Links** - Opens articles in new tab
- ⏱️ **Relative Time** - "Updated 5 minutes ago"
- 🎨 **Smooth Animations** - Fade in/out, expand/collapse

**State Management:**
```typescript
const [data, setData] = useState<MarketSummaryData | null>(null)
const [loading, setLoading] = useState(false)
const [error, setError] = useState<string | null>(null)
const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
```

#### Dashboard Integration

**Button Location:** Search bar area (top of dashboard)

**State:**
```typescript
const [showMarketSummary, setShowMarketSummary] = useState(false)
```

**Usage:**
```tsx
{/* Market Summary Button */}
<button
  onClick={() => setShowMarketSummary(true)}
  className="px-4 py-3 bg-blue-600 hover:bg-blue-700..."
>
  <svg>...</svg>
  Market Summary
</button>

{/* Market Summary Modal */}
<MarketSummary 
  isOpen={showMarketSummary} 
  onClose={() => setShowMarketSummary(false)} 
/>
```

## Setup Instructions

### 1. Backend Setup

**Required Dependencies:**
```bash
# Already in requirements.txt
pip install feedparser>=6.0.11
pip install requests>=2.31.0
```

**Optional Environment Variable:**
```bash
# Get free API key from https://newsapi.org/
export NEWSAPI_API_KEY="your_key_here"
```

**Note:** If `NEWSAPI_API_KEY` is not set, the system falls back to RSS feeds only (still fully functional).

### 2. Frontend Setup

**No additional dependencies needed** - uses existing React components and icons.

### 3. Testing

**Start Backend:**
```bash
cd /path/to/project
source .venv/bin/activate  # or activate venv
uvicorn main:app --reload
```

**Start Frontend:**
```bash
cd frontend
npm run dev
```

**Test the Feature:**
1. Login to the application
2. Navigate to Dashboard view
3. Click "Market Summary" button (top-right of search bar)
4. View categorized news in modal
5. Click sections to expand/collapse
6. Click external link icons to read full articles

## Data Flow

```
┌─────────────────┐
│   Dashboard     │
│   Component     │
└────────┬────────┘
         │
         │ onClick (Market Summary button)
         ▼
┌─────────────────┐
│  MarketSummary  │◄──── isOpen={true}
│   Component     │
└────────┬────────┘
         │
         │ fetchMarketSummary()
         ▼
┌─────────────────┐
│  GET /dashboard │
│ /market/summary │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  free_news_service.py           │
│  ┌─────────────────────────┐   │
│  │ get_market_news()       │   │
│  │  ├─ RSS: Yahoo Finance  │   │
│  │  ├─ RSS: CNBC           │   │
│  │  ├─ RSS: CoinTelegraph  │   │
│  │  └─ NewsAPI (optional)  │   │
│  └─────────────────────────┘   │
└─────────────────────────────────┘
         │
         │ Categorize & Format
         ▼
┌─────────────────┐
│  Return JSON    │
│  - sections[]   │
│  - articles     │
│  - sources      │
└─────────────────┘
```

## RSS Feed Sources

### Financial News
- **Yahoo Finance**: `https://feeds.finance.yahoo.com/rss/2.0/headline`
  - General market news and stock updates
  - Updated frequently (every 15-30 minutes)

- **CNBC Top News**: `https://www.cnbc.com/id/100003114/device/rss/rss.html`
  - Breaking business news
  - Market analysis and expert opinions

- **CNBC Earnings**: `https://www.cnbc.com/id/10000664/device/rss/rss.html`
  - Earnings reports and guidance
  - Corporate financial results

### Cryptocurrency
- **CoinTelegraph**: `https://cointelegraph.com/rss`
  - Bitcoin, Ethereum, altcoin news
  - Blockchain technology updates

- **CoinDesk**: `https://www.coindesk.com/arc/outboundfeeds/rss/`
  - Crypto market analysis
  - Regulatory developments

### Commodities
- **Investing.com**: `https://www.investing.com/rss/commodities.rss`
  - Gold, silver, oil prices
  - Energy market news

## Optional NewsAPI Integration

**Benefits:**
- More diverse news sources (80+ publishers)
- Better search capabilities
- Structured sentiment data

**Limitations:**
- 100 requests/day (free tier)
- 24-hour article history only
- Requires API key

**Setup:**
1. Get free key: https://newsapi.org/register
2. Set environment variable:
   ```bash
   export NEWSAPI_API_KEY="your_api_key"
   ```
3. Restart backend - NewsAPI will automatically be used

**Cost:**
- Free tier: 100 requests/day
- Sufficient for personal use
- RSS feeds used as fallback

## Customization

### Add More RSS Feeds

Edit `app/services/free_news_service.py`:

```python
FREE_RSS_FEEDS = {
    "financial": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        # Add your feed here:
        "https://example.com/rss/feed.xml"
    ],
    "your_category": [
        "https://example.com/category/rss"
    ]
}
```

### Adjust Article Limits

In `dashboard.py`:
```python
news_by_category = free_news_service.get_market_news(
    categories=["financial", "crypto", "commodities"],
    limit_per_category=20  # Change from 15 to 20
)
```

### Auto-Refresh Interval

In `MarketSummary.tsx`:
```typescript
// Add auto-refresh every 10 minutes
useEffect(() => {
  const interval = setInterval(() => {
    if (isOpen) {
      fetchMarketSummary()
    }
  }, 10 * 60 * 1000) // 10 minutes
  
  return () => clearInterval(interval)
}, [isOpen])
```

## Troubleshooting

### Issue: "No articles available"
**Causes:**
- RSS feeds temporarily down
- Network connectivity issues
- Content blocked by firewall

**Solutions:**
1. Check internet connection
2. Verify RSS feed URLs are accessible
3. Try with NewsAPI key for fallback
4. Check backend logs for specific errors

### Issue: Slow loading
**Causes:**
- Multiple RSS feeds fetched sequentially
- Large feed parsing

**Solutions:**
1. Reduce `limit_per_category` parameter
2. Remove slow/unreliable feeds
3. Implement caching (Redis)
4. Use async/await for parallel fetching

### Issue: Duplicate articles
**Causes:**
- Same story from multiple sources
- RSS feed republishing

**Solutions:**
- Algorithm already deduplicates by title
- Adjust similarity threshold in code
- Implement fuzzy matching

### Issue: NewsAPI rate limit
**Causes:**
- Exceeded 100 requests/day

**Solutions:**
- System automatically falls back to RSS
- Implement caching to reduce API calls
- Upgrade to NewsAPI paid plan (if needed)

## Performance Optimization

### Backend Caching
```python
from cachetools import TTLCache

# Cache news for 15 minutes
news_cache = TTLCache(maxsize=100, ttl=900)

@router.get("/market/summary")
async def get_market_summary(current_user: User = Depends(get_current_user)):
    cache_key = "market_summary"
    
    if cache_key in news_cache:
        return news_cache[cache_key]
    
    # Fetch news...
    result = {...}
    
    news_cache[cache_key] = result
    return result
```

### Parallel Feed Fetching
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def fetch_all_feeds_parallel():
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, fetch_rss_feeds, category)
            for category in ["financial", "crypto", "commodities"]
        ]
        results = await asyncio.gather(*tasks)
    return results
```

## Future Enhancements

1. **Sentiment Analysis** - Add bullish/bearish indicators
2. **Trending Topics** - Show most mentioned stocks/cryptos
3. **Personalization** - User-selected news categories
4. **Export Feature** - Download summary as PDF
5. **Email Digest** - Daily summary via email
6. **Translation** - Multi-language support
7. **Voice Reading** - TTS for accessibility

## Files Modified/Created

### Backend
- ✅ `app/services/free_news_service.py` - **NEW** free news aggregation service
- ✅ `app/routers/dashboard.py` - Added `/market/summary` endpoint

### Frontend
- ✅ `frontend/src/components/dashboard/MarketSummary.tsx` - **NEW** modal component
- ✅ `frontend/src/components/Dashboard.tsx` - Added button and state

### Documentation
- ✅ `MARKET_SUMMARY_FREE_API.md` - This file

## Comparison: Free vs Paid APIs

| Feature | Free (RSS) | Alpha Vantage | NewsAPI Paid |
|---------|-----------|---------------|--------------|
| **Cost** | $0 | $0-$500/mo | $449/mo |
| **Request Limit** | Unlimited | 25/day | 1M/mo |
| **News Sources** | 5-10 feeds | Limited | 80,000+ |
| **Historical Data** | Last 24h | Yes | 30 days |
| **Sentiment** | No | Yes | No |
| **Setup** | None | API key | API key |
| **Reliability** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation:** Start with free RSS feeds. Add NewsAPI.org free tier for enhanced coverage. Only upgrade to paid if you need 100+ requests/day.

## License
Same as project license.

## Support
For issues or questions, check project documentation or create a GitHub issue.
