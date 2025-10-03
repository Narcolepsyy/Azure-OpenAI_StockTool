#!/usr/bin/env python3
"""
Test a single LLM query synthesis to see detailed response.
"""

import asyncio
import sys
import os
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.perplexity_web_search import PerplexityWebSearchService

async def test_single_query():
    """Test a single query with detailed logging."""
    print("=== Testing Single LLM Query Synthesis ===")
    
    async with PerplexityWebSearchService() as search_service:
        query = "Microsoft earnings report"
        print(f"Testing query: '{query}'")
        
        try:
            enhanced_query = await search_service._llm_synthesize_query(query, include_recent=True)
            
            if enhanced_query:
                print(f"✅ Success: '{enhanced_query}'")
            else:
                print(f"❌ Failed: Empty result")
                
        except Exception as e:
            print(f"❌ Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_query())