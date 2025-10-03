# Stock Prediction Models Directory

This directory stores trained LSTM models for stock price prediction.

## Structure

For each trained symbol, the following files are created:

```
{SYMBOL}_model.h5      - Trained Keras/TensorFlow model
{SYMBOL}_scaler.pkl    - MinMaxScaler for feature normalization
{SYMBOL}_config.json   - Model configuration and metadata
```

## Example

```
AAPL_model.h5
AAPL_scaler.pkl
AAPL_config.json
```

## Size Guidelines

- Model files (.h5): ~10-20 MB each
- Scaler files (.pkl): < 1 MB each
- Config files (.json): < 10 KB each

## Training Models

Use the training script to create models:

```bash
# Train single symbol
python scripts/train_prediction_model.py AAPL

# Train multiple symbols
python scripts/train_prediction_model.py --all

# List trained models
python scripts/train_prediction_model.py --list
```

## Git Ignore

Model files are excluded from git (see `.gitignore`). This is because:
1. Models can be large (10-20 MB each)
2. Models are specific to training data and time
3. Models should be retrained periodically with fresh data

To share models, use model versioning tools or cloud storage.
