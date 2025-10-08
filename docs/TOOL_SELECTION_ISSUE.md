# Tool Selection Analysis

**Date:** October 8, 2025  
**Issue:** Tool selection may be inaccurate - choosing slow web search instead of fast stock tools

## Problem Observed

From streaming tests, we saw:
```
Query: "What is Apple's stock price?"
Tool called: perplexity_search (20s)
Expected: get_stock_quote (0.5s)
```

The system chose a **40x slower tool** for a simple stock price query!

## Root Cause Analysis

### Current Tool Selection Logic

**File:** `app/utils/tools.py`  
**Function:** `select_tool_names_for_prompt()`

```python
def select_tool_names_for_prompt(prompt: str, capabilities: Optional[Iterable[str]] = None) -> Set[str]:
    names: Set[str] = set()

    # 1. If ticker detected, add ticker tools
    ticker_detected = _detect_ticker(prompt)
    if ticker_detected:
        names.update(_DEFAULT_TICKER_TOOLS)  # get_stock_quote, get_company_profile, get_historical_prices

    # 2. ALWAYS add web search tools (PROBLEM!)
    names.update(_DEFAULT_WEB_SEARCH_TOOLS)  # perplexity_search

    # 3. Add capability-based tools
    names.update(_apply_capabilities(capabilities))
    
    # 4. Add keyword-based tools
    names.update(_apply_keyword_heuristics(prompt))
```

### The Problem

**Line 549:** `names.update(_DEFAULT_WEB_SEARCH_TOOLS)`

This line **ALWAYS** adds `perplexity_search` to the available tools, even when:
- A ticker is detected
- Fast stock tools are available
- The query is simple and direct

### Why This Causes Issues

When the AI model sees **multiple tools** for the same goal:
- `get_stock_quote` - Fast (0.5s), specific
- `perplexity_search` - Slow (20s), general

The model sometimes chooses the **general-purpose tool** because:
1. It seems more "comprehensive"
2. The tool description might be more appealing
3. No priority/ranking system exists

## Impact Analysis

### Performance Impact

| Query Type | Right Tool | Wrong Tool | Time Difference |
|------------|-----------|------------|-----------------|
| Stock price | `get_stock_quote` (0.5s) | `perplexity_search` (20s) | **40x slower** |
| Company info | `get_company_profile` (1s) | `perplexity_search` (20s) | **20x slower** |
| Stock news | `get_augmented_news` (6s) | `perplexity_search` (20s) | **3x slower** |

### Test Results

From `test_streaming.py`:

**First run:**
```
Query: "What is Apple's stock price?"
Tool called: perplexity_search
Duration: 25.30s ❌ (FAIL)
```

**Second run:**
```
Query: "What is Apple's stock price?"
Tool called: rag_search
Duration: 8.73s ⚠️ (Better, but still not optimal)
```

**Third run:**
```
Query: "What is Apple's stock price?"
Tool called: rag_search
Duration: 6.51s ✅ (PASS, but should be 0.5s with get_stock_quote)
```

## Why RAG Search Instead of Stock Quote?

Even when NOT using `perplexity_search`, the system sometimes uses:
- `rag_search` - Knowledge base search (3-8s)
- Instead of `get_stock_quote` - Direct API call (0.5s)

This happens because:
1. Ticker detection might fail for some patterns
2. Multiple tools match the query
3. Model makes suboptimal choice

## Proposed Solutions

### Option 1: Remove Automatic Web Search ⚡ (Recommended)

**Change:** Only add web search when query patterns match

```python
def select_tool_names_for_prompt(prompt: str, capabilities: Optional[Iterable[str]] = None) -> Set[str]:
    names: Set[str] = set()

    ticker_detected = _detect_ticker(prompt)
    if ticker_detected:
        names.update(_DEFAULT_TICKER_TOOLS)

    # ONLY add web search if query needs general web info
    needs_web_search = _needs_web_search(prompt, ticker_detected)
    if needs_web_search:
        names.update(_DEFAULT_WEB_SEARCH_TOOLS)

    names.update(_apply_capabilities(capabilities))
    names.update(_apply_keyword_heuristics(prompt))
    
    return {name for name in names if name in _TOOL_SPEC_BY_NAME}


def _needs_web_search(prompt: str, ticker_detected: bool) -> bool:
    """Determine if query needs web search."""
    prompt_lower = prompt.lower()
    
    # Don't use web search for simple ticker queries
    if ticker_detected:
        simple_patterns = [
            'price', 'quote', 'current', 'trading at',
            'how much', 'value', 'worth'
        ]
        if any(pattern in prompt_lower for pattern in simple_patterns):
            return False  # Use stock tools instead
    
    # Use web search for general questions
    web_indicators = [
        'what is', 'who is', 'how does', 'why',
        'explain', 'latest news', 'recent developments',
        'analysis', 'trends', 'market sentiment'
    ]
    
    return any(indicator in prompt_lower for indicator in web_indicators)
```

**Impact:**
- ✅ Simple stock queries use fast tools (0.5s)
- ✅ Complex queries still get web search
- ✅ 40x faster for common queries

### Option 2: Add Tool Priority System 🎯

**Change:** Add priority hints to tool specs

```python
tools_spec = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "priority": 10,  # High priority for stock prices
            "description": "Get REAL-TIME stock quote with current price. USE THIS FIRST for price queries.",
            # ...
        }
    },
    {
        "type": "function",
        "function": {
            "name": "perplexity_search",
            "priority": 1,  # Low priority - fallback only
            "description": "General web search. Use ONLY when specific tools don't match the query.",
            # ...
        }
    }
]
```

**Note:** OpenAI doesn't support priority in function calling, so this would need:
1. Sort tools by priority before sending to model
2. Update descriptions to emphasize priority
3. Filter out low-priority tools when high-priority match

### Option 3: Improve Tool Descriptions 📝

**Change:** Make tool descriptions clearer about when to use

**Current:**
```python
"description": "Search the web for information..."  # Too general
```

**Improved:**
```python
"description": "Search the web for information NOT available in stock tools. DO NOT use for stock prices, quotes, or company info - use specific stock tools instead."
```

### Option 4: Add Tool Selection Prompt 🤖

**Change:** Add system message to guide tool selection

```python
system_prompt = """
When selecting tools:
1. For stock prices/quotes: ALWAYS use get_stock_quote (fastest)
2. For company info: Use get_company_profile
3. For news: Use get_augmented_news
4. For web search: ONLY use perplexity_search when above tools don't apply

Prefer specific tools over general web search.
"""
```

## Recommended Solution

**Combination approach:**

1. ✅ **Remove automatic web search** (Option 1)
2. ✅ **Improve tool descriptions** (Option 3)
3. ⚠️ **Add selection guidance** in system prompt (Option 4)

This provides:
- **Fast defaults** (no web search unless needed)
- **Clear guidance** (better descriptions)
- **Model hints** (system prompt)

## Implementation

### Quick Fix (5 minutes)

Just remove the automatic web search line:

```python
# Line 549 in app/utils/tools.py
# REMOVE THIS LINE:
names.update(_DEFAULT_WEB_SEARCH_TOOLS)

# ADD THIS INSTEAD:
if _needs_web_search(prompt, ticker_detected):
    names.update(_DEFAULT_WEB_SEARCH_TOOLS)
```

### Full Fix (30 minutes)

1. Add `_needs_web_search()` function
2. Update tool descriptions
3. Add tool selection guidance to system prompt
4. Test with various queries

## Testing

After fix, test these queries:

```python
# Should use get_stock_quote (0.5s)
"What is Apple's stock price?"
"AAPL current price"
"How much is Tesla trading at?"

# Should use get_company_profile (1s)
"Tell me about Apple company"
"What does Microsoft do?"

# Should use perplexity_search (20s)
"What is the latest AI news?"
"Explain quantum computing"
"Market sentiment for tech stocks"
```

**Expected results:**
- Stock queries: < 2s ✅
- Company queries: < 3s ✅
- General queries: < 15s ✅

## Risks

### Removing automatic web search might:
1. ❌ Miss some queries that need web context
2. ❌ Reduce answer comprehensiveness
3. ❌ Require fallback logic

**Mitigation:**
- Keep web search as fallback if stock tools fail
- Model can still call web search explicitly if needed
- Add logging to track tool selection patterns

## Monitoring

After deployment, track:

1. **Tool usage frequency**
   ```python
   logger.info(f"Tool called: {tool_name}, query: {query[:50]}")
   ```

2. **Response times by tool**
   ```python
   {
     "get_stock_quote": 0.5s avg,
     "perplexity_search": 8s avg (down from 20s)
   }
   ```

3. **Tool selection accuracy**
   ```python
   {
     "correct_tool": 85%,
     "suboptimal_tool": 10%,
     "wrong_tool": 5%
   }
   ```

## Conclusion

### Current State
- ❌ Web search always included
- ❌ Model chooses slow tools
- ❌ 40x slower than optimal

### After Fix
- ✅ Web search only when needed
- ✅ Model guided to fast tools
- ✅ Optimal performance

**Recommendation:** Implement quick fix immediately for 40x speedup on stock queries.

---

**Status:** 🔴 CRITICAL - Tool selection needs immediate fix  
**Priority:** HIGH  
**Effort:** 5 minutes (quick fix) to 30 minutes (full fix)  
**Impact:** 40x faster stock queries
