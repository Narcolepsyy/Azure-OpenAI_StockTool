"""
AI Stocks Assistant API - Main Application Entry Point

A modular FastAPI application for AI-powered stock analysis with:
- Authentication and user management
- Conversational AI with tool calling
- Stock data retrieval and analysis
- RAG (Retrieval-Augmented Generation) knowledge base
- Admin functionality
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.routers import auth, chat, admin
from app.routers.rag import router as rag_router
from app.routers.models import router as models_router
from app.routers.enhanced_search import router as enhanced_search_router
from app.routers.dashboard import router as dashboard_router
from app.routers.prediction import router as prediction_router
from app.core.config import FRONTEND_ORIGINS
from app.services.openai_client import get_provider
from app.core.config import RAG_ENABLED, KNOWLEDGE_DIR

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting AI Stocks Assistant API...")
    yield
    # Shutdown
    logger.info("Shutting down AI Stocks Assistant API...")
    try:
        from app.routers.chat import cleanup_chat_resources
        await cleanup_chat_resources()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Create FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="AI Stocks Assistant API",
    version="0.4.0",
    description="Modular FastAPI + OpenAI/Azure OpenAI with stock analysis tools and RAG knowledge base.",
)

# Configure CORS
def setup_cors():
    """Configure CORS settings based on environment."""
    _frontend_origins = FRONTEND_ORIGINS
    allow_origins_list = [o.strip() for o in _frontend_origins.split(",") if o.strip()]
    use_regex = False
    origin_regex = None

    if not allow_origins_list or allow_origins_list == ["*"]:
        # With credentials, wildcard is invalid. Allow localhost/127.0.0.1 any port in dev by regex.
        use_regex = True
        origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        allow_origins_list = []

    cors_kwargs = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }

    if use_regex and origin_regex:
        cors_kwargs["allow_origin_regex"] = origin_regex
    else:
        cors_kwargs["allow_origins"] = allow_origins_list

    app.add_middleware(CORSMiddleware, **cors_kwargs)

setup_cors()

# Include API routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(rag_router)
app.include_router(models_router)
app.include_router(enhanced_search_router)
app.include_router(dashboard_router)
app.include_router(prediction_router)

# Serve static files
app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")
app.mount("/app", StaticFiles(directory="frontend/dist", html=True, check_dir=False), name="app")

# Health check endpoints
@app.get("/healthz", tags=["ops"])
async def healthz():
    """Liveness probe."""
    return {"status": "ok"}

@app.get("/readyz", tags=["ops"])
async def readyz():
    """Readiness probe with system status."""
    # Check provider configuration without forcing client init
    azure_ok = bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"))
    openai_ok = bool(os.getenv("OPENAI_API_KEY"))
    kb_ok = bool(os.path.isdir(KNOWLEDGE_DIR))

    return {
        "status": "ready",
        "provider": ("openai" if openai_ok else ("azure" if azure_ok else None)),
        "openai_configured": openai_ok,
        "azure_configured": azure_ok,
        "rag_enabled": RAG_ENABLED,
        "knowledge_dir_exists": kb_ok,
    }

# Root endpoint
@app.get("/", tags=["info"])
async def root():
    """API information."""
    return {
        "name": "AI Stocks Assistant API",
        "version": "0.4.0",
        "description": "Modular FastAPI application with AI chat, stock tools, and RAG knowledge base",
        "features": [
            "User authentication with JWT",
            "Conversational AI with tool calling",
            "Stock data retrieval and analysis",
            "RAG knowledge base integration",
            "Admin functionality and logs",
            "CORS support for web frontends"
        ],
        "endpoints": {
            "auth": "/auth/*",
            "chat": "/chat/*",
            "admin": "/admin/*",
            "rag": "/api/rag/*",
            "health": "/healthz, /readyz"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}
    )
