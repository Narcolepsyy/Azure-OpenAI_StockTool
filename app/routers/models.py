"""Model selector endpoint for easy frontend integration."""
from fastapi import APIRouter
from typing import Dict, Any
from app.services.openai_client import get_available_models
from app.core.config import DEFAULT_MODEL, AVAILABLE_MODELS

router = APIRouter(prefix="/api/models", tags=["models"])

@router.get("/")
def get_models():
    """Get available models with full configuration details."""
    available = get_available_models()
    
    return {
        "status": "success",
        "data": {
            "default_model": DEFAULT_MODEL,
            "models": available
        }
    }

@router.get("/status")
def get_model_status():
    """Get model availability status for debugging."""
    from app.services.openai_client import get_azure_client, get_openai_client
    
    azure_available = bool(get_azure_client())
    openai_available = bool(get_openai_client())
    
    configured_models = {}
    for model_key, config in AVAILABLE_MODELS.items():
        provider = config.get("provider")
        deployment = config.get("deployment")
        model_name = config.get("model")
        
        configured_models[model_key] = {
            "provider": provider,
            "deployment": deployment,
            "model": model_name,
            "configured": bool(deployment if provider == "azure" else model_name),
            "provider_available": azure_available if provider == "azure" else openai_available
        }
    
    return {
        "status": "success",
        "data": {
            "azure_client_available": azure_available,
            "openai_client_available": openai_available,
            "configured_models": configured_models
        }
    }
