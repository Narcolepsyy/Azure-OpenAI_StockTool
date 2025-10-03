"""Prediction API endpoints for stock price forecasting."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.auth.dependencies import get_current_user
from app.models.database import User
from app.services.stock_prediction_service import (
    predict_stock_price,
    train_model,
    get_model_info,
    list_available_models
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["prediction"])


class PredictionRequest(BaseModel):
    """Request model for stock price prediction."""
    symbol: str = Field(..., description="Stock ticker symbol (e.g., AAPL, ^N225)")
    days: int = Field(7, ge=1, le=30, description="Number of days to predict (1-30)")
    auto_train: bool = Field(True, description="Auto-train model if not found")


class TrainRequest(BaseModel):
    """Request model for model training."""
    symbol: str = Field(..., description="Stock ticker symbol to train")
    period: str = Field("2y", description="Historical data period (1y, 2y, 5y)")
    save_model: bool = Field(True, description="Whether to save trained model")


@router.post("/forecast")
async def forecast_price(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Predict future stock prices using AI/ML model.
    
    - **symbol**: Stock ticker symbol (e.g., AAPL, MSFT, ^N225)
    - **days**: Number of days to predict (1-30, default: 7)
    - **auto_train**: Auto-train model if not found (default: true)
    
    Returns predicted prices with trend analysis.
    """
    try:
        result = predict_stock_price(
            symbol=request.symbol,
            days=request.days,
            auto_train=request.auto_train
        )
        return result
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Prediction failed for {request.symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/train")
async def train_prediction_model(
    request: TrainRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Train a new prediction model for a stock symbol.
    
    - **symbol**: Stock ticker symbol
    - **period**: Historical data period (1y, 2y, 5y)
    - **save_model**: Whether to save the trained model
    
    Returns training metrics and model information.
    """
    try:
        result = train_model(
            symbol=request.symbol,
            period=request.period,
            save_model=request.save_model
        )
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Training failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Training failed for {request.symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Training failed: {str(e)}"
        )


@router.get("/model/{symbol}")
async def get_model_details(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get information about a trained model for a stock symbol.
    
    Returns model configuration, training date, and performance metrics.
    """
    try:
        result = get_model_info(symbol=symbol)
        return result
    
    except Exception as e:
        logger.error(f"Failed to get model info for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve model info: {str(e)}"
        )


@router.get("/models")
async def list_models(
    current_user: User = Depends(get_current_user)
):
    """
    List all available trained prediction models.
    
    Returns list of models with training dates and performance metrics.
    """
    try:
        result = list_available_models()
        return result
    
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )
