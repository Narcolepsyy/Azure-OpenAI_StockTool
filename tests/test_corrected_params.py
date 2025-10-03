#!/usr/bin/env python3
"""
Test Brave Search with the corrected text_decorations parameter.
"""

import asyncio
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.perplexity_web_search import BraveSearchClient

async def test_corrected_parameters():
    """Test Brave Search with corrected parameters."""
    print("=== Testing Brave Search with Corrected Parameters ===")
    
    async with BraveSearchClient() as brave_client:
        if not brave_client.is_available:
            print("❌ Brave Search API not available")
            return
        
        # Test with Japanese query that was causing 422 errors
        query = "八十二銀行と長野銀行の統合"
        print(f"Testing query: '{query}'")
        
        try:
            results = await brave_client.search(
                query=query,
                count=3,
                country="JP"
            )
            
            if results:
                print(f"✅ Success! Retrieved {len(results)} results")
                for i, result in enumerate(results[:2], 1):
                    print(f"  {i}. {result['title'][:80]}...")
            else:
                print("⚠️  No results returned (but no 422 error)")
                
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_corrected_parameters())