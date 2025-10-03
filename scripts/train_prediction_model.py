#!/usr/bin/env python3
"""
Standalone script to train stock prediction models.

Usage:
    python scripts/train_prediction_model.py AAPL
    python scripts/train_prediction_model.py AAPL --period 5y
    python scripts/train_prediction_model.py --all  # Train for all major stocks
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.stock_prediction_service import train_model, list_available_models


# Popular stocks to train on
POPULAR_STOCKS = [
    # US Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    # US Finance
    "JPM", "BAC", "GS", "MS",
    # Japanese
    "^N225", "7203.T", "6758.T", "9984.T",  # Nikkei, Toyota, Sony, SoftBank
    # Indices
    "^GSPC", "^IXIC", "^DJI",
]


def main():
    parser = argparse.ArgumentParser(description="Train stock prediction models")
    parser.add_argument(
        "symbol",
        nargs="?",
        help="Stock ticker symbol to train (e.g., AAPL, ^N225)"
    )
    parser.add_argument(
        "--period",
        default="2y",
        help="Historical data period (1y, 2y, 5y). Default: 2y"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Train models for all popular stocks"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all trained models"
    )
    
    args = parser.parse_args()
    
    # List existing models
    if args.list:
        print("📊 Trained Models:")
        print("=" * 60)
        models = list_available_models()
        
        if models["count"] == 0:
            print("No trained models found.")
        else:
            for model in models["models"]:
                print(f"  {model['symbol']:10s} - Trained: {model['trained_date'][:10]} - MAE: {model['val_mae']:.4f}")
        
        print("=" * 60)
        return
    
    # Train all popular stocks
    if args.all:
        print(f"🚀 Training models for {len(POPULAR_STOCKS)} popular stocks...")
        print(f"   Period: {args.period}")
        print("=" * 60)
        
        success_count = 0
        failed = []
        
        for symbol in POPULAR_STOCKS:
            try:
                print(f"\n📈 Training {symbol}...")
                result = train_model(symbol, period=args.period, save_model=True)
                
                metrics = result["metrics"]
                print(f"   ✓ Success! Val Loss: {metrics['val_loss']:.6f}, Val MAE: {metrics['val_mae']:.6f}")
                success_count += 1
                
            except Exception as e:
                print(f"   ✗ Failed: {e}")
                failed.append(symbol)
        
        print("\n" + "=" * 60)
        print(f"✅ Successfully trained: {success_count}/{len(POPULAR_STOCKS)}")
        
        if failed:
            print(f"❌ Failed: {', '.join(failed)}")
        
        return
    
    # Train single stock
    if not args.symbol:
        parser.print_help()
        return
    
    symbol = args.symbol.upper()
    print(f"🚀 Training model for {symbol}")
    print(f"   Period: {args.period}")
    print("=" * 60)
    
    try:
        result = train_model(symbol, period=args.period, save_model=True)
        
        print(f"\n✅ Training completed successfully!")
        print(f"\n📊 Model Metrics:")
        print(f"   Train Loss: {result['metrics']['train_loss']:.6f}")
        print(f"   Val Loss:   {result['metrics']['val_loss']:.6f}")
        print(f"   Train MAE:  {result['metrics']['train_mae']:.6f}")
        print(f"   Val MAE:    {result['metrics']['val_mae']:.6f}")
        
        print(f"\n💾 Model saved to: {result['model_path']}")
        print(f"   Scaler saved to: {result['scaler_path']}")
        
        print(f"\n📈 Data Info:")
        print(f"   Train samples: {result['data_info']['train_samples']}")
        print(f"   Test samples:  {result['data_info']['test_samples']}")
        print(f"   Features: {', '.join(result['data_info']['features'])}")
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
