# AI Stocks Assistant - Copilot Instructions

## Architecture Overview

This is a **modular FastAPI + React** application for AI-powered stock analysis with web search augmentation. The system combines:
- **OpenAI/Azure OpenAI** for conversational AI with function calling
- **yfinance** for stock data and financial analysis  
- **Perplexity-style web search** (DuckDuckGo/Brave) with LLM synthesis
- **RAG system** (ChromaDB + LangChain) for knowledge base search
- **JWT authentication** with user/admin roles

### Key Directories
```
app/
├── auth/          # JWT tokens, password hashing, user auth
├── core/          # Environment config, model aliases, settings
├── models/        # SQLAlchemy DB models + Pydantic schemas
├── routers/       # API endpoints (chat, auth, admin, rag, enhanced_search)
├── services/      # Business logic (openai_client, stock_service, perplexity_web_search)
└── utils/         # Tool registry, conversation management, connection pooling
frontend/          # React + Vite + TypeScript + TailwindCSS
knowledge/         # RAG knowledge base files (indexed to ChromaDB)
```

## Critical Development Patterns

### 1. Tool Function Calling Architecture
- **Tool registry**: `app/utils/tools.py` defines all AI tools via `TOOL_REGISTRY` dict
- **Tool specs**: `tools_spec` array contains OpenAI function calling definitions
- Each tool maps to a service function (e.g., `get_stock_quote` → `app/services/stock_service.py`)
- Tools are **auto-injected** into chat requests based on query content

**Adding a new tool:**
1. Define function in appropriate service (e.g., `stock_service.py`)
2. Add spec to `tools_spec` in `utils/tools.py` with JSON schema
3. Register in `TOOL_REGISTRY` dict mapping name → function
4. Tool becomes available to AI automatically

### 2. Multi-Provider Model System
- **Model resolution**: `app/core/config.py` has `AVAILABLE_MODELS` dict with provider routing
- Supports both **Azure OpenAI** (deployment names) and **standard OpenAI** (model names)
- Default model: `gpt-oss-120b` (configurable via `DEFAULT_MODEL`)
- Client selection: `get_client_for_model()` in `openai_client.py` returns (client, model_name, config)

**Environment variables:**
- Azure: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_*`
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`

### 3. Performance Optimization Strategy
- **TTL caching**: `cachetools.TTLCache` used extensively (see `app/services/memory_service.py`)
- **Connection pooling**: Custom pool in `app/utils/connection_pool.py` for HTTP clients
- **Parallel execution**: Tool calls use `ThreadPoolExecutor` (8 workers), embeddings use `asyncio.gather()`
- **Smart truncation**: Web search results preserve citations while truncating content (see `_smart_truncate_answer` in `chat.py`)
- **Circuit breakers**: Yahoo Finance API has circuit breaker pattern to prevent cascade failures
- **Aggressive timeouts**: Models have 25-45s timeouts (not 60-120s) - see `AVAILABLE_MODELS` in `config.py`
- **Token limits**: Reduced to 500-800 tokens for faster generation (not 1000-4000)
- **Streaming support**: Use `/chat/stream` for immediate user feedback during long operations

### 4. Citation-Preserving Truncation
**Critical pattern** in `app/routers/chat.py`:
- Web search tools (`perplexity_search`, `web_search`, etc.) return results with **citation metadata**
- `_sanitize_perplexity_result()` truncates answers to 1500 chars while preserving citation arrays
- Frontend extracts citations from tool results to display Perplexity-style source cards
- **Never** generically truncate web search results—use the sanitizer functions

### 5. Conversation Management
- **Session-based**: `conversation_id` tracks multi-turn conversations
- **Token optimization**: `app/utils/conversation.py` manages message history with token limits
- **Memory layers**: Short-term (2h), medium-term (24h), long-term (7d) caches in `memory_service.py`
- Conversations auto-expire based on TTL; manual clear via `/chat/clear`

### 6. Japanese Language Support
- System auto-detects Japanese queries and appends `\n\n日本語で回答してください。` directive
- BM25 scoring supports Japanese tokenization with `mecab-python3` (optional)
- Nikkei news sentiment analysis available via `get_nikkei_news_with_sentiment()`

## Development Workflows

### Running the Application
```bash
# Backend (from project root)
uvicorn main:app --reload
# Runs on http://127.0.0.1:8000

# Frontend (from frontend/)
npm install
npm run dev
# Runs on http://localhost:5173
```

### Testing Patterns
Tests are **standalone scripts** (not pytest-based):
```bash
# Run individual test
python test_enhanced_search.py
python test_brave_search_integration.py

# Tests use asyncio.run() and direct service imports
# Check test_*.py files for examples of testing each service
```

### Database Migrations
- Uses SQLAlchemy with `app.db` (SQLite by default)
- Models in `app/models/database.py`
- No Alembic—schema changes require manual DB drops or ALTER statements

### Environment Setup
- Copy environment variables from README.md (no `.env.example` exists)
- Required: Either `AZURE_OPENAI_*` or `OPENAI_API_KEY`
- Optional: `RAG_ENABLED=true` + `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` for RAG

## Service Integration Points

### Stock Data Flow
1. User query → Chat router → OpenAI function calling
2. AI calls tool (e.g., `get_stock_quote`) → `stock_service.py` 
3. Service queries yfinance API → Applies circuit breaker → Returns data
4. Data cached in `QUOTE_CACHE` (TTL: configurable, default 5min)

### Web Search Flow  
1. Tool call to `perplexity_search` → `perplexity_web_search.py`
2. **Search phase**: DuckDuckGo/Brave query → Extract content concurrently
3. **Ranking phase**: BM25 + embeddings similarity scoring (parallel)
4. **Synthesis phase**: Azure GPT generates answer with citations
5. Result includes: `answer`, `citations` dict, `sources` array, `css_styles`

### RAG Flow
1. Admin triggers `/admin/rag/reindex` → Indexes `knowledge/` files
2. Query calls `rag_search` → ChromaDB similarity search
3. Returns top-k chunks with scores
4. Augmented search (`augmented_rag_search`) merges KB + web results

## Common Gotchas

### 1. Authentication Headers
- All protected endpoints require `Authorization: Bearer <token>` header
- Admin endpoints additionally check `user.is_admin` flag
- Test with `/auth/register` → `/auth/login` → use returned access token

### 2. Model Timeout Errors
- Large models (gpt-oss-120b) have **45s timeout** - optimized for fast failure
- Synthesis operations have **30s timeout** - fast web search synthesis
- Never increase timeouts above 60s - prefer faster failure + retry
- Adjust per-model in `AVAILABLE_MODELS[model_key]["timeout"]` in `config.py`
- **Web search now targets <3s** - see `WEB_SEARCH_SPEED_OPTIMIZATIONS.md`

### 3. Web Search Performance
- **CRITICAL**: Web search optimized for speed (target <3s vs original 15-30s)
- LLM query enhancement **skipped** (saves 8-20s per search)
- Content extraction **skipped** - uses snippets only (saves 8-15s)
- Semantic scoring **limited to top 5** results with 2s timeout (saves 17-27s)
- Parallel BM25 + semantic ranking with 3s total timeout
- Aggressive search timeouts: Brave 1.5s, DDGS 2s
- Minimal rate limiting: 300ms vs 1s delays
- See `WEB_SEARCH_SPEED_OPTIMIZATIONS.md` for complete optimization guide

### 3. Citation Data Loss
- **Always** use `_sanitize_perplexity_result()` when truncating web search tool results
- Generic string truncation breaks frontend citation extraction
- Web search tools must preserve `citations`, `sources`, and `css_styles` keys

### 4. Async/Sync Mixing
- Tool functions are **synchronous** (run in ThreadPoolExecutor)
- Web search uses **async** internally but exposed as sync via `asyncio.run()`
- Never call async functions directly from tool registry—wrap with `asyncio.run()`

### 5. Japanese Text Processing
- MeCab is optional dependency (may not be installed)
- Wrap Japanese-specific code in try/except with ASCII fallback
- See `app/services/perplexity_web_search.py` BM25 tokenization for example

## Key Configuration Files

- `app/core/config.py` - All env vars, model aliases, feature flags
- `app/utils/tools.py` - Tool registry and OpenAI function specs  
- `requirements.txt` - Python dependencies (no lock file)
- `frontend/package.json` - React dependencies

## Documentation References

- `ARCHITECTURE.md` - Detailed modular architecture explanation
- `PERFORMANCE_OPTIMIZATIONS.md` - Optimization strategies and benchmarks
- `RESPONSE_TIME_OPTIMIZATIONS.md` - Timeout and token limit improvements (3min → 45s)
- `DOUBLE_SYNTHESIS_FIX.md` - **CRITICAL**: Eliminated redundant synthesis (saves 30s per query)
- `WEB_SEARCH_SPEED_OPTIMIZATIONS.md` - **CRITICAL**: Web search speed optimizations (<3s vs 15-30s)
- `CITATION_SYSTEM_COMPLETE.md` - Citation system implementation details
- `WEB_SEARCH_INTEGRATION.md` - Web search capabilities overview
- `TASKS.md` - Feature backlog and technical debt items
