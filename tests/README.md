# Tests

This directory contains all test files for the Azure-OpenAI Stock Analysis Tool project.

## Test Categories

### AWS Integration Tests
- `test_aws_integration.py` - Complete AWS service integration tests (S3, DynamoDB, SQS, CloudWatch)

### Web Search Tests
- `test_enhanced_search.py` - Enhanced search functionality tests
- `test_enhanced_search_integration.py` - Enhanced search integration tests
- `test_web_search.py` - Basic web search tests
- `test_web_search_integration.py` - Web search integration tests
- `test_web_search_detailed.py` - Detailed web search tests
- `test_web_search_priority.py` - Web search priority tests
- `test_web_results.py` - Web results parsing tests
- `test_fast_search.py` - Fast search implementation tests

### Brave Search Tests
- `test_brave_search_integration.py` - Brave search integration tests
- `test_brave_search_direct.py` - Direct Brave API tests
- `test_brave_quality_enhancement.py` - Brave quality enhancement tests
- `test_simple_brave.py` - Simple Brave search tests

### DuckDuckGo Search Tests
- `test_ddgs_direct.py` - Direct DuckDuckGo API tests
- `test_ddg_raw.py` - Raw DDG response tests
- `test_ddg_structured.py` - Structured DDG response tests
- `test_ddgs_regions.py` - DDG region-specific tests

### Perplexity/Enhanced Search Tests
- `test_enhanced_perplexity.py` - Enhanced Perplexity-style search tests
- `test_perplexity_brave_integration.py` - Perplexity + Brave integration tests
- `test_perplexity_cache.py` - Perplexity caching tests
- `test_perplexity_citations.py` - Citation extraction tests
- `test_perplexity_truncation_sanitization.py` - Result truncation tests

### LangChain Tests
- `test_langchain_search.py` - LangChain search tests
- `test_langchain_streaming.py` - LangChain streaming tests

### RAG Tests
- `test_enhanced_rag.py` - Enhanced RAG system tests

### Citation System Tests
- `test_citation_system.py` - Citation system tests
- `test_citation_preservation.py` - Citation preservation tests
- `test_citation_url_normalization.py` - URL normalization tests

### Scoring & Relevance Tests
- `test_relevance_scoring.py` - Relevance scoring tests
- `test_enhanced_relevance.py` - Enhanced relevance tests
- `test_scoring_comparison.py` - Scoring comparison tests
- `test_enhanced_scoring_final.py` - Final scoring implementation tests
- `test_nli_verification.py` - Natural Language Inference verification tests

### LLM Integration Tests
- `test_llm_query_synthesis.py` - LLM query synthesis tests
- `test_llm_synthesis_debug.py` - LLM synthesis debugging tests
- `test_single_llm.py` - Single LLM tests

### Chat & Merger Tests
- `test_chat_merger_flow.py` - Chat merger flow tests
- `test_merger_search_fix.py` - Merger search fix tests
- `test_mixed_tools.py` - Mixed tool usage tests
- `test_pseudo_tool_fix.py` - Pseudo tool fix tests

### Japanese Language Tests
- `test_japanese_bank_search.py` - Japanese bank search tests
- `test_japanese_banking_query.py` - Japanese banking query tests
- `test_jp_dashboard.py` - Japanese dashboard tests
- `test_jp_endpoints.sh` - Japanese endpoint tests (shell script)

### Query Processing Tests
- `test_query_simplification.py` - Query simplification tests
- `test_domain_priors_demo.py` - Domain priors demo tests

### Parameter & Configuration Tests
- `test_parameter_mapping.py` - Parameter mapping tests
- `test_corrected_params.py` - Corrected parameters tests
- `test_source_parameter.py` - Source parameter tests
- `test_new_format.py` - New format tests

### Transport & Connection Tests
- `test_transport_cleanup.py` - HTTP transport cleanup tests
- `test_asyncio_fix.py` - Asyncio fix tests
- `test_websocket_connection.py` - WebSocket connection tests

### Dashboard Tests
- `test_dashboard_setup.py` - Dashboard setup tests
- `test_chart_data.py` - Chart data tests

### Other Service Tests
- `test_alphavantage_search.py` - Alpha Vantage integration tests
- `test_get_augmented_news.py` - Augmented news tests

### Optimization Tests
- `test_streaming_optimizations.py` - Streaming optimization tests
- `test_fallback_mode.py` - Fallback mode tests

### Misc Tests
- `test_latex_conversion.py` - LaTeX conversion tests
- `test_debug_logging.py` - Debug logging tests
- `test_minimal_english.py` - Minimal English tests

## Running Tests

### Run All Tests
```bash
# From project root
python -m pytest tests/

# Or run all tests manually
for test in tests/test_*.py; do python "$test"; done
```

### Run Individual Test
```bash
# From project root
python tests/test_aws_integration.py

# Or with pytest
python -m pytest tests/test_aws_integration.py -v
```

### Run Test Category
```bash
# Run all AWS tests
python tests/test_aws_integration.py

# Run all web search tests
python tests/test_web_search*.py
```

## Test Requirements

Most tests require:
- Running backend server (`python main.py`)
- LocalStack for AWS tests (`docker-compose up -d`)
- Valid API keys in `.env` file

## Test Structure

Each test file typically includes:
- Setup/teardown functions
- Multiple test cases with assertions
- Colored output for readability (✅/❌)
- Summary statistics

## Contributing

When adding new tests:
1. Use the `test_*.py` naming convention
2. Include docstrings explaining what's being tested
3. Add proper error handling and assertions
4. Update this README with the new test file
5. Ensure tests are isolated and can run independently
