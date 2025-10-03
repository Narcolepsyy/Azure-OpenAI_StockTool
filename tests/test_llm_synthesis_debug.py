#!/usr/bin/env python3
"""
Test LLM query synthesis specifically to see what's causing validation failures.
"""

import asyncio
import sys
import os
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.perplexity_web_search import PerplexityWebSearchService

async def test_llm_synthesis():
    """Test LLM query synthesis with various queries to identify issues."""
    print("=== Testing LLM Query Synthesis ===")
    
    test_queries = [
        "Tesla stock news",
        "八十二銀行と長野銀行の統合関連ニュースを検索してください。",
        "Microsoft earnings report",
        "Simple test query"
    ]
    
    async with PerplexityWebSearchService() as search_service:
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test {i}: '{query}' ---")
            
            try:
                # Call the LLM synthesis method directly
                enhanced_query = await search_service._llm_synthesize_query(query, include_recent=True)
                
                if enhanced_query:
                    print(f"✅ Success: '{query}' → '{enhanced_query}'")
                else:
                    print(f"❌ Failed: LLM synthesis returned empty string")
                    
            except Exception as e:
                print(f"❌ Exception: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_synthesis())