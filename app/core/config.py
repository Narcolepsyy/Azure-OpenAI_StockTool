"""Application configuration and environment variables."""
import os
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment from .env if present
load_dotenv()

# ---------- OpenAI/Azure config ----------
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Standard OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Enhanced deployment configurations
AZURE_OPENAI_DEPLOYMENT_4_1 = os.getenv("AZURE_OPENAI_DEPLOYMENT_4_1")
AZURE_OPENAI_DEPLOYMENT_4_1_MINI = os.getenv("AZURE_OPENAI_DEPLOYMENT_4_1_MINI")
AZURE_OPENAI_DEPLOYMENT_O3 = os.getenv("AZURE_OPENAI_DEPLOYMENT_O3")
AZURE_OPENAI_DEPLOYMENT_GPT5 = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT5")
AZURE_OPENAI_DEPLOYMENT_OSS_120B = os.getenv("AZURE_OPENAI_DEPLOYMENT_OSS_120B")

# Model Selection Configuration
AVAILABLE_MODELS = {
    # Azure deployed models (your deployment)
    "gpt-oss-120b": {
        "provider": "azure",
        "deployment": AZURE_OPENAI_DEPLOYMENT_OSS_120B,
        "display_name": "GPT OSS 120B (Azure)",
        "description": "Large open-source model deployed on Azure",
        "default": True,  # Set as default since you deployed it
        "timeout": 120,  # Longer timeout for large models
        "max_completion_tokens": 1000,  # Reasonable limit for faster responses
        "temperature": 0.3  # Lower temperature for more focused responses
    },

    # OpenAI models
    "gpt-5": {
        "provider": "openai",
        "model": "gpt-5",
        "display_name": "GPT-5",
        "description": "Latest GPT-5 model from OpenAI",
        "timeout": 60
    },
    "o3": {
        "provider": "openai",
        "model": "o3",
        "display_name": "O3",
        "description": "OpenAI O3 reasoning model",
        "timeout": 90  # Reasoning models may need more time
    },
    "gpt-4.1": {
        "provider": "openai",
        "model": "gpt-4.1",
        "display_name": "GPT-4.1",
        "description": "Enhanced GPT-4.1 model",
        "timeout": 60
    },
    "gpt-4o": {
        "provider": "openai",
        "model": "gpt-4o",
        "display_name": "GPT-4o",
        "description": "GPT-4 Omni multimodal model",
        "timeout": 60
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "description": "Faster, cost-effective GPT-4o variant",
        "timeout": 30
    }
}

# Get default model
DEFAULT_MODEL = next((k for k, v in AVAILABLE_MODELS.items() if v.get("default")), "gpt-oss-120b")

# RAG Configuration
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() in {"1", "true", "yes"}
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge")
CHROMA_DIR = os.getenv("CHROMA_DIR", ".chroma")
OPENAI_EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small")
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))

# Cache Configuration
QUOTE_CACHE_SIZE = int(os.getenv("QUOTE_CACHE_SIZE", "1024"))
QUOTE_TTL_SECONDS = int(os.getenv("QUOTE_TTL_SECONDS", "60"))
CONV_CACHE_SIZE = int(os.getenv("CONV_CACHE_SIZE", "1000"))
CONV_TTL_SECONDS = int(os.getenv("CONV_TTL_SECONDS", str(60 * 60 * 4)))  # 4 hours
NEWS_CACHE_SIZE = int(os.getenv("NEWS_CACHE_SIZE", "1024"))
NEWS_TTL_SECONDS = int(os.getenv("NEWS_TTL_SECONDS", "300"))  # 5 minutes

# Conversation Management
MAX_CONV_MESSAGES = int(os.getenv("MAX_CONV_MESSAGES", "50"))
CONV_SUMMARY_THRESHOLD = int(os.getenv("CONV_SUMMARY_THRESHOLD", "20"))
MAX_TOKENS_PER_TURN = int(os.getenv("MAX_TOKENS_PER_TURN", "8000"))
RAG_MAX_CHUNKS = int(os.getenv("RAG_MAX_CHUNKS", "3"))
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "512"))
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")

# Performance optimizations
ENABLE_RESPONSE_CACHE = os.getenv("ENABLE_RESPONSE_CACHE", "true").lower() in {"1", "true", "yes"}
RESPONSE_CACHE_TTL = int(os.getenv("RESPONSE_CACHE_TTL", "300"))  # 5 minutes
SIMPLE_QUERY_CACHE_TTL = int(os.getenv("SIMPLE_QUERY_CACHE_TTL", "60"))  # 1 minute for simple queries

# Simple query patterns that don't need RAG/tools
SIMPLE_QUERY_PATTERNS = [
    r'(?i)^(hi|hello|hey|good morning|good afternoon).*',
    r'(?i)^(what|how|who|when|where|why)\s+(is|are|do|does|can|will|would).*',
    r'(?i)^(tell me|explain|describe).*',
    r'(?i).*(stock price|current price|quote).*',
    r'(?i)^(thanks|thank you|bye|goodbye).*'
]

# Streaming optimizations
STREAM_CHUNK_SIZE = int(os.getenv("STREAM_CHUNK_SIZE", "64"))  # Smaller chunks for faster streaming
MAX_STREAM_CHUNKS = int(os.getenv("MAX_STREAM_CHUNKS", "500"))  # Prevent runaway streams

# Tool execution optimizations
ENABLE_PARALLEL_TOOLS = os.getenv("ENABLE_PARALLEL_TOOLS", "true").lower() in {"1", "true", "yes"}
TOOL_TIMEOUT = int(os.getenv("TOOL_TIMEOUT", "10"))  # 10 seconds max per tool

# Model-specific optimizations
FAST_MODEL_FOR_SIMPLE = os.getenv("FAST_MODEL_FOR_SIMPLE", "gpt-4o-mini")

# Model-specific system prompts for performance optimization
MODEL_SYSTEM_PROMPTS = {
    "gpt-oss-120b": """You are a helpful AI assistant specializing in financial and stock market analysis. 
Be concise and direct in your responses. Focus on accuracy and speed. 
For simple queries like stock prices or company info, provide direct answers without extensive elaboration unless specifically requested.""",
    "default": """You are a helpful AI assistant with expertise in financial markets and investment analysis. 
You have access to real-time stock data, news, and analytical tools to provide comprehensive market insights."""
}

def get_system_prompt_for_model(model_key: str) -> str:
    """Get optimized system prompt for specific model."""
    return MODEL_SYSTEM_PROMPTS.get(model_key, MODEL_SYSTEM_PROMPTS["default"])

# Risk Assessment
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.015"))

# News Configuration
NEWS_USER_AGENT = os.getenv("NEWS_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Auth Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")

# Admin Configuration
ADMIN_USERNAMES = {u.strip().lower() for u in os.getenv("ADMIN_USERNAMES", "admin").split(",") if u.strip()}

# CORS Configuration  
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*")

# Validation patterns
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,9}$")

def _clean_env(v: Optional[str]) -> str:
    """Clean environment variable values."""
    s = (v or "").strip().strip('"').strip("'")
    # treat template placeholders like <your> as empty
    if s.startswith("<") and s.endswith(">"):
        return ""
    if "</" in s or s.startswith("<"):
        return ""
    return s

def _normalize_azure_endpoint(ep: Optional[str]) -> str:
    """Helper to normalize Azure endpoint if a full path was provided."""
    s = _clean_env(ep)
    if not s:
        return s
    # Strip trailing slashes
    while s.endswith('/'):
        s = s[:-1]
    # If the env contains '/openai/deployments/', cut back to base '/'
    m = re.search(r"/openai/.*$", s)
    if m:
        s = s[: m.start()]  # keep just the resource base URL
    return s

# Build model aliases
def build_model_aliases() -> Dict[str, str]:
    """Build model alias mapping for deployment resolution."""
    MODEL_ALIASES: Dict[str, str] = {}
    
    # Clean deployment names
    deployment_4_1 = _clean_env(AZURE_OPENAI_DEPLOYMENT_4_1)
    deployment_4_1_mini = _clean_env(AZURE_OPENAI_DEPLOYMENT_4_1_MINI)
    deployment_o3 = _clean_env(AZURE_OPENAI_DEPLOYMENT_O3)
    deployment_gpt5 = _clean_env(AZURE_OPENAI_DEPLOYMENT_GPT5)
    deployment_oss_120b = _clean_env(AZURE_OPENAI_DEPLOYMENT_OSS_120B)
    
    if deployment_4_1:
        for a in ("gpt-4.1", "gpt-4-1"):
            MODEL_ALIASES[a.lower()] = deployment_4_1
    if deployment_4_1_mini:
        for a in ("gpt-4.1-mini", "gpt-4-1-mini"):
            MODEL_ALIASES[a.lower()] = deployment_4_1_mini
    if deployment_o3:
        for a in ("o3", "gpt-o3", "gpt o3"):
            MODEL_ALIASES[a.lower()] = deployment_o3
    if deployment_gpt5:
        for a in ("gpt-5", "gpt 5", "gpt5"):
            MODEL_ALIASES[a.lower()] = deployment_gpt5
    if deployment_oss_120b:
        for a in ("gpt-oss-120b", "oss-120b", "gpt oss 120b"):
            MODEL_ALIASES[a.lower()] = deployment_oss_120b
    
    # Fallback generic aliases
    MODEL_ALIASES.setdefault("gpt-4.1", "gpt-4-1")
    MODEL_ALIASES.setdefault("gpt-4-1", "gpt-4-1")
    MODEL_ALIASES.setdefault("gpt-4.1-mini", "gpt-4-1-mini")
    MODEL_ALIASES.setdefault("gpt-4-1-mini", "gpt-4-1-mini")
    MODEL_ALIASES.setdefault("o3", "o3")
    MODEL_ALIASES.setdefault("gpt-o3", "o3")
    MODEL_ALIASES.setdefault("gpt o3", "o3")
    MODEL_ALIASES.setdefault("gpt-5", "gpt-5")
    MODEL_ALIASES.setdefault("gpt 5", "gpt-5")
    MODEL_ALIASES.setdefault("gpt5", "gpt-5")
    MODEL_ALIASES.setdefault("gpt-oss-120b", "gpt-oss-120b")
    MODEL_ALIASES.setdefault("oss-120b", "gpt-oss-120b")
    MODEL_ALIASES.setdefault("gpt oss 120b", "gpt-oss-120b")
    
    return MODEL_ALIASES

# Get model aliases
MODEL_ALIASES = build_model_aliases()

# Compute default Azure deployment
DEFAULT_AZURE_DEPLOYMENT = (
    _clean_env(AZURE_OPENAI_DEPLOYMENT)
    or _clean_env(AZURE_OPENAI_DEPLOYMENT_OSS_120B)
    or MODEL_ALIASES.get("gpt-oss-120b")
    or _clean_env(AZURE_OPENAI_DEPLOYMENT_4_1)
    or _clean_env(AZURE_OPENAI_DEPLOYMENT_4_1_MINI)
    or _clean_env(AZURE_OPENAI_DEPLOYMENT_O3)
    or _clean_env(AZURE_OPENAI_DEPLOYMENT_GPT5)
    or MODEL_ALIASES.get("gpt-4.1")
)

def check_model_availability() -> Dict[str, bool]:
    """Check which models are actually available."""
    availability = {}

    # Check Azure models
    azure_available = bool(AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT)

    for model_key, config in AVAILABLE_MODELS.items():
        if config["provider"] == "azure":
            deployment = config.get("deployment")
            availability[model_key] = azure_available and bool(deployment)
        elif config["provider"] == "openai":
            availability[model_key] = bool(OPENAI_API_KEY)
        else:
            availability[model_key] = False

    return availability

def get_available_models() -> Dict[str, Dict[str, Any]]:
    """Get models with availability status."""
    availability = check_model_availability()

    models = {}
    for model_key, config in AVAILABLE_MODELS.items():
        models[model_key] = {
            **config,
            "available": availability.get(model_key, False)
        }

    return models

# Update model configurations with availability
for model_key in AVAILABLE_MODELS:
    if model_key not in AVAILABLE_MODELS[model_key]:
        AVAILABLE_MODELS[model_key]["available"] = False
