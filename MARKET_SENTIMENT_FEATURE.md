# Market Sentiment Indicator Feature

## Overview
Real-time market sentiment indicator displayed in the top-right corner of the navigation bar, similar to Perplexity's market status display. Uses Alpha Vantage NEWS_SENTIMENT API to aggregate sentiment from recent financial news.

## Features

### 1. **Visual Indicator**
- **Bullish** 🟢 - Green color when market sentiment is positive (score > 0.15)
- **Bearish** 🔴 - Red color when market sentiment is negative (score < -0.15)
- **Neutral** ⚪ - Gray color when market sentiment is balanced

### 2. **Confidence Level**
- **3 bars** - High confidence (30+ articles, 60%+ agreement)
- **2 bars** - Medium confidence (15+ articles, 50%+ agreement)
- **1 bar** - Low confidence (fewer articles or mixed sentiment)

### 3. **Interactive Tooltip**
Hover over the indicator to see detailed breakdown:
- Sentiment label and score
- Number of articles analyzed
- Confidence level
- Breakdown of bullish/neutral/bearish articles
- Last updated timestamp

### 4. **Auto-Refresh**
- Automatically refreshes every 5 minutes
- Configurable refresh interval
- Can be disabled if needed

## API Endpoint

### `GET /dashboard/market/sentiment`

**Authentication:** Required (JWT Bearer token)

**Response:**
```json
{
  "sentiment": "bullish",
  "sentiment_score": 0.234,
  "confidence": "high",
  "article_count": 45,
  "bullish_count": 28,
  "bearish_count": 8,
  "neutral_count": 9,
  "last_updated": "2025-10-03T12:34:56.789Z"
}
```

**Fields:**
- `sentiment`: Overall market sentiment ("bullish", "bearish", "neutral")
- `sentiment_score`: Weighted average sentiment (-1 to +1 scale)
- `confidence`: Confidence level ("high", "medium", "low")
- `article_count`: Total number of articles analyzed
- `bullish_count`: Number of bullish articles
- `bearish_count`: Number of bearish articles
- `neutral_count`: Number of neutral articles
- `last_updated`: ISO timestamp of last calculation

## Sentiment Calculation Algorithm

### 1. **Data Collection**
```python
# Fetch 50 recent articles about economy and financial markets
sentiment_data = alphavantage_service.get_news_sentiment(
    topics="economy_macro,financial_markets",
    limit=50
)
```

### 2. **Weighted Aggregation**
Each article's sentiment is weighted by its relevance score:

```python
weighted_score = Σ(sentiment_score × relevance_score) / Σ(relevance_score)
```

### 3. **Sentiment Classification**
- **Bullish**: `weighted_score > 0.15`
- **Bearish**: `weighted_score < -0.15`
- **Neutral**: `-0.15 ≤ weighted_score ≤ 0.15`

### 4. **Confidence Calculation**
```python
agreement_ratio = dominant_count / total_count

if article_count >= 30 and agreement_ratio > 0.6:
    confidence = "high"
elif article_count >= 15 and agreement_ratio > 0.5:
    confidence = "medium"
else:
    confidence = "low"
```

## Frontend Component

### Location
- **File:** `frontend/src/components/market/MarketSentiment.tsx`
- **Placement:** Top-right corner of navigation bar in `App.tsx`

### Props
```typescript
interface MarketSentimentProps {
  className?: string        // Additional CSS classes
  autoRefresh?: boolean     // Enable auto-refresh (default: true)
  refreshInterval?: number  // Refresh interval in ms (default: 300000 = 5min)
}
```

### Usage Example
```tsx
import { MarketSentiment } from './components/market'

// Basic usage (auto-refresh every 5 minutes)
<MarketSentiment />

// Custom refresh interval (2 minutes)
<MarketSentiment refreshInterval={120000} />

// Disable auto-refresh
<MarketSentiment autoRefresh={false} />

// With custom styling
<MarketSentiment className="ml-4" />
```

## Design Details

### Visual Style (Perplexity-inspired)
```css
/* Container */
backdrop-blur-sm           /* Glassmorphism effect */
rounded-full               /* Pill shape */
px-3 py-1.5               /* Compact padding */
border                     /* Subtle border */

/* Color Schemes */
Bullish:  bg-green-500/10 border-green-500/30 text-green-400
Bearish:  bg-red-500/10 border-red-500/30 text-red-400
Neutral:  bg-gray-500/10 border-gray-500/30 text-gray-400

/* Interactions */
hover:scale-105           /* Subtle scale on hover */
transition-all duration-200
```

### Responsive Behavior
- **Desktop:** Full display with label and confidence bars
- **Mobile:** Could be simplified to icon-only (future enhancement)

## Alpha Vantage Integration

### API Limits
- **Free Tier:** 25 requests per day
- **Rate Limit:** 5 requests per minute

### Cost Optimization
1. **Cache sentiment data** for 5+ minutes to reduce API calls
2. **Fallback to cached data** if API limit is reached
3. **Graceful degradation** when API is unavailable

### API Key Configuration
Set in `.env`:
```bash
ALPHA_VANTAGE_API_KEY=your_api_key_here
```

Get free API key: https://www.alphavantage.co/support/#api-key

## Error Handling

### Backend Errors
```python
# Returns fallback data with error message
{
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "confidence": "low",
    "market_status": "open",
    "last_updated": datetime.now().isoformat(),
    "error": "API rate limit reached"
}
```

### Frontend Error States
1. **Loading:** Shows spinner with "Market" label
2. **Error (no data):** Shows gray indicator with alert icon
3. **Error (with data):** Shows last known data + warning in tooltip

## Performance Considerations

### Backend
- **Caching:** Consider implementing Redis cache for sentiment data
- **Rate Limiting:** Track API usage to prevent quota exhaustion
- **Async Processing:** Sentiment calculation happens asynchronously

### Frontend
- **Lazy Loading:** Component only loads when user is authenticated
- **Memoization:** Uses `useCallback` to prevent unnecessary re-renders
- **Debouncing:** Auto-refresh prevents rapid successive API calls

## Future Enhancements

### 1. **Historical Trend**
Show sentiment trend over the past 24 hours:
```tsx
<div className="sentiment-trend">
  📊 +12% vs 24h ago
</div>
```

### 2. **Clickable Navigation**
Navigate to detailed sentiment analysis page:
```tsx
onClick={() => navigate('/market/sentiment')}
```

### 3. **Multiple Markets**
Support different markets (US, EU, Asia):
```tsx
<MarketSentiment market="US" />
<MarketSentiment market="JP" />
```

### 4. **Real-time Updates**
WebSocket integration for live sentiment updates:
```tsx
useWebSocket('/market/sentiment/stream')
```

### 5. **Customizable Topics**
Allow users to customize sentiment topics:
```tsx
<MarketSentiment topics={['tech', 'finance', 'crypto']} />
```

## Testing

### Manual Testing
1. **Start backend:**
   ```bash
   uvicorn main:app --reload
   ```

2. **Start frontend:**
   ```bash
   cd frontend && npm run dev
   ```

3. **Verify display:**
   - Log in to app
   - Check top-right corner for sentiment indicator
   - Hover to see tooltip with detailed breakdown
   - Wait 5 minutes to verify auto-refresh

### API Testing
```bash
# Test sentiment endpoint
curl -X GET "http://127.0.0.1:8000/dashboard/market/sentiment" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Expected Behavior
- ✅ Indicator appears in top-right corner
- ✅ Color changes based on sentiment
- ✅ Tooltip shows on hover
- ✅ Auto-refreshes every 5 minutes
- ✅ Handles API errors gracefully
- ✅ Shows loading state initially

## Troubleshooting

### Issue: Indicator not appearing
**Solution:** Check browser console for authentication errors

### Issue: "API rate limit reached"
**Solution:** 
1. Check Alpha Vantage dashboard for usage
2. Wait until next day (resets at midnight ET)
3. Upgrade to paid plan if needed

### Issue: Always showing "neutral"
**Solution:** 
1. Verify Alpha Vantage API key is configured
2. Check backend logs for API errors
3. Ensure news sentiment API is returning data

### Issue: Tooltip not showing
**Solution:** Check z-index and positioning in CSS

## Files Modified/Created

### Backend
- ✅ `app/routers/dashboard.py` - Added `/market/sentiment` endpoint
- ✅ `app/services/alphavantage_service.py` - Already existed

### Frontend
- ✅ `frontend/src/components/market/MarketSentiment.tsx` - New component
- ✅ `frontend/src/components/market/index.ts` - Export file
- ✅ `frontend/src/App.tsx` - Integrated component

### Documentation
- ✅ `MARKET_SENTIMENT_FEATURE.md` - This file

## Related Documentation
- Alpha Vantage NEWS_SENTIMENT API: https://www.alphavantage.co/documentation/#news-sentiment
- React Best Practices: Component composition and hooks
- Tailwind CSS: Utility-first CSS framework

## License
Same as project license (check repository root)
