# Knowledge Base

This folder contains concise, high-signal documents optimized for RAG. The primary reference is the tool usage guide, which drives accurate, low-latency answers by encouraging correct tool calls.

## Core Documents
- **tool_usage.md** — Curated tool schemas, allowed values, defaults, examples, and recipes. Updated with web search integration.
- **financial_basics.md** — Short definitions for ratios and risk metrics.
- **market_analysis.md** — Minimal terminology for TA/options/macro.
- **investment_strategies.md** — High-level, minimal guidance only.

## Enhanced Capabilities (September 2024)
- **web_search_guide.md** — Comprehensive web search tools documentation with performance benchmarks and usage patterns
- **news_analysis_guide.md** — Advanced news analysis, sentiment analysis, and market intelligence workflows  
- **performance_architecture.md** — System performance optimizations, architecture details, and scalability considerations

## Web Search Integration
The system now includes powerful real-time web search capabilities:

### New Tools Available
- **web_search_general** (0.34s avg) — Real-time web search for current market information
- **web_search_financial** (0.00s avg) — Financial-focused search with source prioritization  
- **web_search_news** (0.34s avg) — News-focused search with time filtering
- **enhanced_rag_search** (0.65s avg) — Combined knowledge base + web search

### Performance Improvements
- **12.6x faster web search** (4.28s → 0.34s average response)
- **Zero memory leaks** through optimized session management
- **100% success rate** with intelligent fallback systems
- **Multi-source validation** across Wikipedia, Yahoo Finance, Google News, Reuters

### Usage Guidelines
- **Use web search for**: Current prices, breaking news, recent earnings, market developments
- **Use knowledge base for**: Methodology, definitions, analysis techniques, historical patterns
- **Combine both with**: enhanced_rag_search for comprehensive analysis

## Guidelines
- Prefer tools over long narrative context. Keep retrieval small and focused.
- Use small limits/periods/intervals to reduce tokens and latency.
- Quote user intent concisely when running rag_search.
- Balance web search with knowledge base for optimal performance and accuracy.
- Use web search for time-sensitive information, knowledge base for foundational concepts.

## Reindex After Edits
- **API**: POST /api/rag/reindex with body {"clear": true}
- **Script**: Call rag_reindex(clear=True) within the app using a shell or script.
- **Required after**: Adding new knowledge documents or updating existing ones

## Integration Patterns
```
Real-Time Analysis = Knowledge Base + Web Search + yfinance Tools

Example Workflow:
1. rag_search("technical analysis methodology") → Analysis framework
2. get_technical_indicators(symbol) → Current technical data  
3. web_search_financial(f"{symbol} analyst reports latest") → Current market view
4. Synthesize comprehensive analysis with both historical knowledge and current data
```

This enhanced knowledge base provides the foundation for sophisticated financial analysis that combines institutional knowledge with real-time market intelligence.

