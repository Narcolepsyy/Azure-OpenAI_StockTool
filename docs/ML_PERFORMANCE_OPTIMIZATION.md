# ML Tool Selection - Performance Optimization Guide

## Problem: Slow First-Time Response (~7-10 seconds)

The bottleneck is **OpenAI embedding API calls** taking **~6 seconds**.

```
First request breakdown:
- Model loading: 1.3s (18.5%)
- OpenAI embedding: 5.9s (81.0%) ← BOTTLENECK
- ML prediction: 0.03s (0.4%)
- Total: 7.3s
```

**Good news**: 
- Cached queries are **225x faster** (32ms vs 7286ms) ✅
- Actual ML prediction is only 33ms (very fast!) ✅

---

## Solution Options

### Option 1: Accept Current Performance ✅ (Recommended for Now)

**Keep using OpenAI embeddings** since caching makes repeat queries instant.

**Pros**:
- ✅ Best accuracy (A+ grade, 93% F1)
- ✅ Already working
- ✅ Cached queries are instant (32ms)
- ✅ No additional dependencies

**Cons**:
- ❌ First-time queries are slow (~6-7s)
- ❌ Costs money (OpenAI API calls)

**When to use**: If most queries are similar (benefit from cache)

---

### Option 2: Switch to Fast Local Embeddings ⚡

**Use sentence-transformers** instead of OpenAI API.

**Performance**:
```
OpenAI API:          1500-6000ms per query
sentence-transformers:  50-150ms per query (30-60x faster!)
```

**Pros**:
- ✅ **30-60x faster** (50-150ms vs 6000ms)
- ✅ Free (no API calls)
- ✅ Works offline
- ✅ Still has caching

**Cons**:
- ⚠️ Slightly lower accuracy (~2-5% F1 drop, still good)
- ⚠️ Need to retrain model with new embeddings
- ⚠️ Requires installing sentence-transformers (~500MB)

**How to implement**:

```bash
# 1. Install package
pip install sentence-transformers

# 2. Update embedder in tool_selector.py
from app.services.ml.fast_embedder import FastLocalEmbedder

# Use FastLocalEmbedder instead of QueryEmbedder
self.embedder = FastLocalEmbedder()

# 3. Retrain model with new embeddings
python scripts/prepare_training_data_local.py  # Use local embeddings
python scripts/train_tool_classifier.py

# 4. Restart server
```

**Expected performance after switch**:
```
First request: ~1.5s (vs 7.3s now) - 5x faster!
Cached request: ~50ms (vs 32ms now) - similar
```

---

### Option 3: Hybrid Approach (Best of Both Worlds) 🎯

Use **fast local embeddings for tool selection**, but keep OpenAI for other features.

**Implementation**:
```python
# In tool_selector.py
class MLToolSelector:
    def __init__(self):
        # Use fast local embedder for tool selection
        from app.services.ml.fast_embedder import get_fast_embedder
        self.embedder = get_fast_embedder()
```

**Pros**:
- ✅ Fast tool selection (~150ms)
- ✅ Free for tool selection
- ✅ Can still use OpenAI embeddings for RAG/search
- ✅ Best balance

**Cons**:
- ⚠️ Need to retrain with local embeddings
- ⚠️ Slightly different embedding space

---

## Recommendation

### For Production: **Option 2 or 3** (Fast Local Embeddings)

Why?
1. **6 seconds is too slow** for tool selection
2. Fast local embeddings still give good accuracy (~88-90% F1)
3. No API costs for tool selection
4. Works offline

### Quick Win: **Option 1** (Keep Current, Monitor Cache Hit Rate)

Why?
1. Already working with A+ accuracy
2. Cached queries are instant
3. No code changes needed
4. Can switch later if needed

---

## Implementation Steps for Option 2 (Fast Local)

### Step 1: Install Dependencies
```bash
pip install sentence-transformers
```

### Step 2: Update Tool Selector
```python
# In app/services/ml/tool_selector.py
from app.services.ml.fast_embedder import get_fast_embedder

class MLToolSelector:
    def _load_model(self):
        # Use fast local embedder
        self.embedder = get_fast_embedder()  # Fast local model
        # ... rest of code
```

### Step 3: Retrain Model (Optional but Recommended)
```bash
# Create script to prepare data with local embeddings
python scripts/prepare_training_data_local.py
python scripts/train_tool_classifier.py
```

### Step 4: Test Performance
```bash
python analyze_ml_performance.py
```

Expected results:
- First prediction: ~1.5s (was 7.3s)
- Cached: ~50ms (was 32ms)
- Accuracy: ~88-90% F1 (was 93%)

---

## Performance Comparison

| Metric | OpenAI Embeddings | Local Embeddings | Improvement |
|--------|-------------------|------------------|-------------|
| **First query** | 7.3s | 1.5s | 5x faster ✅ |
| **Cached query** | 32ms | 50ms | Similar ✅ |
| **F1 Score** | 93% | ~88-90% | -3-5% ⚠️ |
| **Cost per query** | $0.00002 | $0 | Free ✅ |
| **Offline support** | ❌ No | ✅ Yes | Better ✅ |

---

## Current Status

✅ **ML tool selection is working**
⚠️ **Embedding is slow** (6s per unique query)
✅ **Caching works great** (225x speedup for repeat queries)

## What to Do Next?

1. **Monitor cache hit rate** - If >70%, current performance is fine
2. **If most queries are unique**, switch to local embeddings
3. **For production**, recommend local embeddings for better UX

---

## Quick Test: Check Cache Hit Rate

Add this to your monitoring:

```python
from app.services.ml.tool_selector import get_ml_tool_selector

selector = get_ml_tool_selector()
stats = selector.get_stats()

cache_hit_rate = 1.0 - (stats['fallback_count'] / stats['total_predictions'])
print(f"Cache hit rate: {cache_hit_rate:.1%}")
```

If cache hit rate >70%, current performance is acceptable.
If <50%, switch to local embeddings for better UX.
