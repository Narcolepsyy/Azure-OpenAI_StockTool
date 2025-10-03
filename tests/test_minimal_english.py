#!/usr/bin/env python3
"""
Test with a minimal English query to isolate parameter issues.
"""

import asyncio
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.perplexity_web_search import BraveSearchClient

async def test_minimal_english():
    """Test with minimal English query."""
    print("=== Testing Minimal English Query ===")
    
    async with BraveSearchClient() as brave_client:
        if not brave_client.is_available:
            print("❌ Brave Search API not available")
            return
        
        # Simple English query
        query = "Tesla news"
        print(f"Testing query: '{query}'")
        
        try:
            results = await brave_client.search(
                query=query,
                count=2
            )
            
            if results:
                print(f"✅ Success! Retrieved {len(results)} results")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. {result['title'][:80]}...")
            else:
                print("⚠️  No results returned")
                
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_minimal_english())