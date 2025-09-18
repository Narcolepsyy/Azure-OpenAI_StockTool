# Knowledge Base

This folder contains concise, high-signal documents optimized for RAG. The primary reference is the tool usage guide, which drives accurate, low-latency answers by encouraging correct tool calls.

Contents
- tool_usage.md — Curated tool schemas, allowed values, defaults, examples, and recipes.
- financial_basics.md — Short definitions for ratios and risk metrics.
- market_analysis.md — Minimal terminology for TA/options/macro.
- investment_strategies.md — High-level, minimal guidance only.

Guidelines
- Prefer tools over long narrative context. Keep retrieval small and focused.
- Use small limits/periods/intervals to reduce tokens and latency.
- Quote user intent concisely when running rag_search.

Reindex after edits
- API: POST /api/rag/reindex with body {"clear": true}
- Or call rag_reindex(clear=True) within the app using a shell or script.

