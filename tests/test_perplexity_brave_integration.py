#!/usr/bin/env python3
"""
Test the actual perplexity search service to verify Brave Search integration is working.
"""

import asyncio
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.perplexity_web_search import PerplexityWebSearchService

async def test_perplexity_search():
    """Test the actual perplexity search service with Brave integration."""
    print("=== Testing Perplexity Search Service with Brave Integration ===")
    
    # Test queries
    test_queries = [
        "Tesla stock news 2025",
        "八十二銀行と長野銀行の統合関連ニュースを検索してください。",
        "Microsoft earnings report"
    ]
    
    async with PerplexityWebSearchService() as search_service:
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test {i}: '{query}' ---")
            
            try:
                # Test with a small number of results to avoid hitting limits
                response = await search_service.perplexity_search(
                    query=query,
                    max_results=3,
                    synthesize_answer=True,
                    include_recent=True
                )
                
                print(f"✅ Search completed successfully")
                print(f"Search time: {response.search_time:.2f}s")
                print(f"Synthesis time: {response.synthesis_time:.2f}s")
                print(f"Total time: {response.total_time:.2f}s")
                print(f"Confidence: {response.confidence_score:.2f}")
                print(f"Number of sources: {len(response.sources)}")
                
                # Show source breakdown
                brave_sources = [s for s in response.sources if s.source == 'brave_search']
                ddgs_sources = [s for s in response.sources if s.source == 'ddgs']
                
                print(f"  - Brave Search sources: {len(brave_sources)}")
                print(f"  - DDGS sources: {len(ddgs_sources)}")
                
                if brave_sources:
                    print("  ✅ Brave Search is working!")
                    for source in brave_sources[:2]:  # Show first 2 Brave sources
                        print(f"    - {source.title[:80]}... (score: {source.relevance_score:.2f})")
                else:
                    print("  ⚠️  No Brave Search results found")
                
                # Show short answer
                if response.answer:
                    print(f"Answer preview: {response.answer[:200]}...")
                    
            except Exception as e:
                print(f"❌ Search failed: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()

async def main():
    """Run all tests."""
    await test_perplexity_search()
    
    print("\n=== Summary ===")
    print("If you see 'Brave Search is working!' then the integration is successful.")
    print("If you see only DDGS sources, check:")
    print("1. BRAVE_API_KEY is properly loaded in config")
    print("2. Rate limits haven't been exceeded")
    print("3. Network connectivity to Brave API")

if __name__ == "__main__":
    asyncio.run(main())