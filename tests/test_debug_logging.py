#!/usr/bin/env python3
"""
Test with detailed logging to see what's happening with Brave Search.
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

async def test_with_logging():
    """Test with detailed logging enabled."""
    print("=== Testing with Debug Logging ===")
    
    async with PerplexityWebSearchService() as search_service:
        response = await search_service.perplexity_search(
            query="Tesla stock news",
            max_results=2,
            synthesize_answer=False,  # Skip synthesis for faster testing
            include_recent=True
        )
        
        print(f"\n=== Results Summary ===")
        print(f"Total sources: {len(response.sources)}")
        
        for i, source in enumerate(response.sources):
            print(f"\nSource {i+1}:")
            print(f"  Title: {source.title}")
            print(f"  URL: {source.url}")
            print(f"  Source: {source.source}")
            print(f"  Search Engine: {getattr(source, 'search_engine', 'N/A')}")
            print(f"  Relevance Score: {source.relevance_score}")
            
if __name__ == "__main__":
    asyncio.run(test_with_logging())