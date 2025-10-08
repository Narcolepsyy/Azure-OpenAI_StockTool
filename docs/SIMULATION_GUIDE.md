# Training ML Tool Selection Without Deployment

**Problem:** You want to train the ML model but haven't deployed the app yet.  
**Solution:** Use the data simulation script to generate realistic training data instantly!

---

## 🎯 Why Simulation?

Instead of waiting 1-2 weeks for real user data, you can:
- ✅ Generate 200+ realistic samples in **5 seconds**
- ✅ Train the model **immediately**  
- ✅ Test ML tool selection **before deployment**
- ✅ Skip the waiting period entirely

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Generate Training Data (5 seconds)
```bash
python scripts/simulate_training_data.py --samples 200
```

**What it does:**
- Generates 200 realistic user queries
- Includes stock lookups, news searches, technical analysis, Japanese queries
- Simulates correct tool selection behavior
- Adds realistic execution times and 10% failure rate

**Output:**
```
✅ Successfully generated 200 training samples!
📊 Samples generated: 200
📁 Saved to: data/tool_usage_logs.jsonl
```

### Step 2: Verify Data (2 seconds)
```bash
python scripts/monitor_tool_usage.py
```

**Expected output:**
```
📊 Total logs: 205
✅ Successes: 187
❌ Failures: 18
📈 Success rate: 91.2%

🔧 Tools Called (frequency):
  get_stock_quote               : 75 calls
  get_technical_indicators      : 59 calls
  perplexity_search             : 52 calls
  get_historical_prices         : 26 calls
  get_company_profile           : 20 calls

🟡 Status: Early training possible (205/500 recommended)
```

### Step 3: Ready to Train! ✅
You now have enough data to train the ML model in Phase 2.

---

## 📋 Simulation Options

### Default (Recommended)
```bash
python scripts/simulate_training_data.py --samples 200
```
- **200 samples** - Good balance
- **Training ready** - Sufficient for initial model
- **Time:** 5 seconds

### Quick Mode
```bash
python scripts/simulate_training_data.py --quick
```
- **100 samples** - Minimum for training
- **Faster** - For testing
- **Time:** 3 seconds

### Large Dataset
```bash
python scripts/simulate_training_data.py --large
```
- **500 samples** - Recommended size
- **Better accuracy** - More data = better model
- **Time:** 10 seconds

### Custom Size
```bash
python scripts/simulate_training_data.py --samples 1000
```
- **Any number** - Your choice
- **Optimal:** 500-1000 samples

---

## 🧪 What Gets Simulated

### Query Types (Realistic Distribution)

**1. Stock Price Queries (~37%)**
```
"What is AAPL's stock price?"
"How much is TSLA trading at?"
"NVDA current quote"
```
→ Should use: `get_stock_quote` (0.4-0.8s)

**2. Company Information (~10%)**
```
"Tell me about GOOGL"
"What does MSFT do?"
"Who is the CEO of META?"
```
→ Should use: `get_company_profile` (0.5-1.0s)

**3. Technical Analysis (~29%)**
```
"AAPL technical indicators"
"Show me TSLA's RSI and MACD"
"Is NVDA overbought?"
```
→ Should use: `get_technical_indicators` (0.8-1.5s)

**4. Historical Data (~13%)**
```
"MSFT price history"
"Past 30 days for AMZN"
"NFLX historical prices"
```
→ Should use: `get_historical_prices` (0.7-1.3s)

**5. News & Knowledge (~25%)**
```
"Latest AI news"
"What's happening with electric vehicles?"
"Explain blockchain"
```
→ Should use: `perplexity_search` (5.0-8.0s)

**6. Multi-Tool Queries (~10%)**
```
"Analyze TSLA stock"
"Complete analysis of AAPL"
"Comprehensive NVDA report"
```
→ Should use: Multiple tools (1.5-2.5s)

**7. Japanese Queries (~5%)**
```
"AAPLの株価を教えて"
"TSLAの現在価格は？"
```
→ Should use: `get_stock_quote` (0.5-0.9s)

### Realistic Features

✅ **Random Tickers:** AAPL, GOOGL, MSFT, TSLA, AMZN, META, NVDA, AMD, NFLX, DIS  
✅ **Random Topics:** AI, crypto, EVs, tech stocks, inflation, etc.  
✅ **Random Execution Times:** Based on actual tool performance  
✅ **10% Failure Rate:** Simulates real-world errors  
✅ **Multiple Models:** gpt-4o, gpt-4o-mini, gpt-oss-120b

---

## 🔍 Verify Generated Data

### View Recent Samples
```bash
# Show last 5 entries
tail -n 5 data/tool_usage_logs.jsonl | jq .
```

**Example output:**
```json
{
  "timestamp": "2025-10-08T...",
  "query": "What is AAPL's stock price?",
  "tools_available": ["get_stock_quote", "get_company_profile", "perplexity_search"],
  "tools_called": ["get_stock_quote"],
  "success": true,
  "execution_time": 0.58,
  "model": "gpt-4o"
}
```

### Statistics
```bash
python scripts/monitor_tool_usage.py
```

### Check Specific Tool Frequency
```bash
cat data/tool_usage_logs.jsonl | jq -r '.tools_called[]' | sort | uniq -c | sort -rn
```

---

## 📊 Data Quality

### Distribution Check
After generating 200 samples:

| Tool | Expected % | Actual Calls | ✓ |
|------|-----------|--------------|---|
| get_stock_quote | ~37% | 75 | ✅ |
| get_technical_indicators | ~29% | 59 | ✅ |
| perplexity_search | ~25% | 52 | ✅ |
| get_historical_prices | ~13% | 26 | ✅ |
| get_company_profile | ~10% | 20 | ✅ |

### Quality Metrics
- ✅ **Success Rate:** ~90% (realistic with 10% failures)
- ✅ **Execution Times:** Match real tool performance
- ✅ **Query Diversity:** 10+ templates per tool type
- ✅ **Language Support:** Includes Japanese queries
- ✅ **Tool Combinations:** Includes multi-tool queries

---

## 🔄 Compare: Simulation vs Real Data

### Simulation (Instant)
```bash
python scripts/simulate_training_data.py --samples 200
# ✅ 200 samples in 5 seconds
# ✅ Perfect tool selection labels
# ✅ Controlled distribution
```

**Pros:**
- ⚡ Instant (5 seconds)
- 🎯 Perfect labels (100% correct)
- 📊 Balanced distribution
- 🧪 Reproducible
- 🚀 Start training immediately

**Cons:**
- 🤖 Synthetic (not real users)
- 📉 May miss edge cases
- 🔄 Needs validation with real data later

### Real Data (1-2 Weeks)
```bash
# Deploy app, wait for users...
# ⏳ 100-500 samples in 1-2 weeks
# ⚠️ Some mislabeled (if AI chose wrong tool)
# 📊 Natural distribution
```

**Pros:**
- 👥 Real user queries
- 🌍 Real-world diversity
- 📈 Captures edge cases
- ✅ Production-ready labels

**Cons:**
- ⏳ Slow (1-2 weeks wait)
- ⚠️ May have mislabeled data
- 📉 Unbalanced distribution
- 🚫 Requires deployment

### Best Approach: Hybrid

1. **Now:** Train on simulated data (5 minutes)
2. **Deploy:** Enable ML selection
3. **Collect:** Gather real user data
4. **Retrain:** Weekly with real data
5. **Improve:** Model gets better over time

---

## ⚠️ Important Notes

### Simulation Limitations

**Good For:**
- ✅ Initial training
- ✅ Testing ML pipeline
- ✅ Proof of concept
- ✅ Development/testing

**Not Perfect For:**
- ⚠️ Production deployment (validate first!)
- ⚠️ Edge case handling
- ⚠️ Novel query types
- ⚠️ Real user behavior patterns

### Recommendations

1. **Train on simulated data** (now)
2. **Test thoroughly** with diverse queries
3. **Deploy with feature flag** (ML_TOOL_SELECTION_ENABLED=false initially)
4. **Collect real data** (with rule-based as fallback)
5. **Retrain weekly** with real data
6. **Enable ML gradually** (A/B testing)

---

## 🎯 Next Steps

### After Generating Data

1. ✅ **Verify:** `python scripts/monitor_tool_usage.py`
2. 🧠 **Train:** Proceed to Phase 2 - Model Training
3. 🧪 **Test:** Evaluate on held-out simulated data
4. 🚀 **Deploy:** Enable with real data collection
5. 🔄 **Iterate:** Retrain with real user data

### Regenerate Anytime
```bash
# Clear old logs (optional)
rm data/tool_usage_logs.jsonl

# Generate fresh dataset
python scripts/simulate_training_data.py --samples 500

# Verify
python scripts/monitor_tool_usage.py
```

---

## 💡 Pro Tips

### Generate More Data
```bash
# Run multiple times to accumulate more samples
python scripts/simulate_training_data.py --samples 100
python scripts/simulate_training_data.py --samples 100
python scripts/simulate_training_data.py --samples 100
# Now you have 300+ samples
```

### Clean Dataset
```bash
# Start fresh
rm data/tool_usage_logs.jsonl
python scripts/simulate_training_data.py --samples 500
```

### Balanced Dataset
```bash
# Large dataset for better balance
python scripts/simulate_training_data.py --large
# 500 samples with ~90 per tool type
```

### Custom Queries
Edit `scripts/simulate_training_data.py` to add your own query templates:
```python
QUERY_TEMPLATES.append({
    "queries": ["Your custom query template"],
    "tools_available": {...},
    "tools_called": [...],
    ...
})
```

---

## ✅ Summary

**Problem:** Can't collect real data without deployment  
**Solution:** Simulate 200+ realistic samples in 5 seconds!

**Benefits:**
- ⚡ Start training **immediately**
- 🎯 Perfect labels (100% correct tool selection)
- 📊 Balanced dataset
- 🚀 Skip the 1-2 week waiting period

**Trade-offs:**
- Synthetic data (validate with real data later)
- May miss edge cases
- Needs retraining with real data eventually

**Verdict:** Perfect for getting started! Train now, validate later. 🚀

---

**Next:** Proceed to Phase 2 - Train the ML model with your simulated data!
