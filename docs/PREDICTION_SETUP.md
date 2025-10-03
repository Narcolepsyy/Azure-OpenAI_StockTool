# Stock Price Prediction - Quick Setup Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Install ML Dependencies

```bash
pip install tensorflow>=2.15.0,<2.16.0 scikit-learn>=1.3.0
```

**For GTX 1650 Ti (4GB VRAM):** This TensorFlow version is optimized for your GPU.

### Step 2: Verify GPU Detection (Optional)

```python
import tensorflow as tf
print("GPUs Available:", tf.config.list_physical_devices('GPU'))
```

If no GPU detected, models will run on CPU (slower but still works).

### Step 3: Train Your First Model

```bash
# Train Apple stock prediction model
python scripts/train_prediction_model.py AAPL

# Expected output:
# 🚀 Training model for AAPL
#    Period: 2y
# ============================================================
# 
# ✅ Training completed successfully!
# 
# 📊 Model Metrics:
#    Train Loss: 0.000234
#    Val Loss:   0.000456
#    Train MAE:  0.012
#    Val MAE:    0.018
# 
# 💾 Model saved to: models/stock_predictions/AAPL_model.h5
```

### Step 4: Test the Integration

```bash
# Run test suite (uses CPU, no GPU required)
python test_stock_prediction.py

# Expected: All 4 tests should pass
```

### Step 5: Use in Chat Interface

Start the server:
```bash
uvicorn main:app --reload
```

Register/login to get a token, then chat:

**You:** "Predict AAPL price for next week"

**AI:** *[Automatically calls prediction tool and shows results]*

## 📊 Usage Examples

### Via Python Script

```python
from app.services.stock_prediction_service import predict_stock_price

# Predict with auto-training
result = predict_stock_price(
    symbol="AAPL",
    days=7,
    auto_train=True  # Trains model if not found
)

print(f"Current: ${result['current_price']}")
print(f"7-day prediction: ${result['summary']['final_predicted_price']}")
print(f"Trend: {result['summary']['trend_en']}")
```

### Via REST API

```bash
# Get auth token first
TOKEN=$(curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password" | jq -r .access_token)

# Make prediction
curl -X POST "http://localhost:8000/predict/forecast" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "days": 7, "auto_train": true}'
```

### Supported Chat Commands

The AI assistant will automatically detect these intents:

- **English:**
  - "Predict AAPL for next 7 days"
  - "Forecast Tesla stock price"
  - "What will Microsoft stock be in 2 weeks?"

- **Japanese:**
  - "株価予測してください: トヨタ (7203.T)"
  - "アップルの株価を1週間予測して"
  - "ソフトバンクの株価見通しは？"

## 🎯 Train Popular Stocks

```bash
# Train multiple stocks at once
python scripts/train_prediction_model.py --all

# This trains models for:
# - US Tech: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA
# - US Finance: JPM, BAC, GS, MS
# - Japanese: ^N225, 7203.T, 6758.T, 9984.T
# - Indices: ^GSPC, ^IXIC, ^DJI
```

## 🔧 Troubleshooting

### GPU Not Detected

**Problem:** TensorFlow doesn't see your GPU

**Solution:**
```bash
# Install CUDA-enabled TensorFlow
pip install tensorflow[and-cuda]>=2.15.0

# Verify GPU
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### Out of Memory (OOM)

**Problem:** Training fails with OOM error on 4GB GPU

**Solution 1:** Memory growth is already enabled, but you can force CPU:
```bash
CUDA_VISIBLE_DEVICES="" python scripts/train_prediction_model.py AAPL
```

**Solution 2:** Reduce batch size in `app/services/stock_prediction_service.py`:
```python
MODEL_CONFIG = {
    "batch_size": 16,  # Reduce from 32
    # ... rest of config
}
```

### Model Not Found

**Problem:** Prediction fails with "No trained model found"

**Solution:** Enable auto-training:
```python
predict_stock_price("AAPL", days=7, auto_train=True)
```

Or train manually first:
```bash
python scripts/train_prediction_model.py AAPL
```

### Slow Predictions

**Problem:** Predictions take > 5 seconds

**Solution:**
1. **Check if GPU is being used:**
   ```python
   import tensorflow as tf
   print("Num GPUs:", len(tf.config.list_physical_devices('GPU')))
   ```

2. **GPU should be 10-50x faster than CPU**
   - CPU inference: 2-5 seconds
   - GPU inference: < 1 second

## 📈 Model Performance

### Expected Metrics

Good model performance for daily stock predictions:
- **Val MAE:** < 0.05 (excellent), 0.05-0.10 (good), > 0.10 (retrain)
- **Val Loss:** < 0.001 (excellent), 0.001-0.005 (good)

### Improving Accuracy

1. **Use more training data:**
   ```bash
   python scripts/train_prediction_model.py AAPL --period 5y
   ```

2. **Retrain periodically:**
   ```bash
   # Retrain with latest data
   python scripts/train_prediction_model.py AAPL --period 2y
   ```

3. **Check data quality:**
   - Avoid stocks with gaps in historical data
   - Avoid highly volatile stocks (crypto, penny stocks)
   - Indices (^GSPC, ^N225) often have better predictions

## 🔐 API Authentication

All prediction endpoints require authentication:

```bash
# Register new user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "trader", "email": "trader@example.com", "password": "secure_password"}'

# Login to get token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader&password=secure_password"

# Returns: {"access_token": "eyJ...", "token_type": "bearer"}
```

## 📝 Next Steps

1. **Train models for your favorite stocks:**
   ```bash
   python scripts/train_prediction_model.py YOUR_SYMBOL
   ```

2. **Integrate with chat interface:**
   - Just ask the AI to predict any stock
   - It will auto-train if needed

3. **Monitor model performance:**
   ```bash
   python scripts/train_prediction_model.py --list
   ```

4. **Schedule retraining:**
   - Add to cron job to retrain weekly/monthly
   - Or use `auto_train=True` for automatic retraining

## 📚 Documentation

- Full docs: `docs/STOCK_PREDICTION.md`
- API endpoints: `http://localhost:8000/docs` (FastAPI Swagger UI)
- Code: `app/services/stock_prediction_service.py`

---

**Ready to predict! 🚀📈**
