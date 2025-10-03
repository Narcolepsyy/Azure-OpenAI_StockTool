"""Test enhanced relevance filtering in web search."""
import asyncio
import sys
sys.path.append('.')
from app.services.perplexity_web_search import PerplexityWebSearchService

async def test_relevance_search():
    """Test the enhanced search with relevance filtering."""
    service = PerplexityWebSearchService()
    
    # Test with a specific query
    query = "latest AI developments 2025"
    print(f"Testing query: '{query}'")
    print("=" * 50)
    
    result = await service.perplexity_search(query)
    
    print(f"Answer length: {len(result.answer)} characters")
    print(f"Sources found: {len(result.sources)}")
    print(f"Citations: {list(result.citations.keys())}")
    
    print("\n--- SOURCE DETAILS ---")
    for i, source in enumerate(result.sources[:5], 1):  # Show first 5 sources
        print(f"{i}. {source.title}")
        print(f"   URL: {source.url}")
        print(f"   Score: {source.relevance_score:.2f}")
        print(f"   Source: {source.source}")
        print(f"   Snippet: {source.snippet[:100]}...")
        print()
    
    print("--- CHECKING INLINE CITATIONS ---")
    import re
    citations = re.findall(r'\[\d+\]', result.answer)
    print(f"Found citations in answer: {citations}")
    
    if citations:
        print("✅ Inline citations found!")
    else:
        print("❌ No inline citations found")

if __name__ == "__main__":
    asyncio.run(test_relevance_search())