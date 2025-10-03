#!/usr/bin/env python3
"""
Test BM25 + embedding relevance scoring
"""
import json
from app.utils.tools import TOOL_REGISTRY

def test_relevance_scoring():
    """Test web_search with relevance scoring"""
    
    test_cases = [
        {
            "name": "Specific stock query",
            "query": "Apple AAPL stock price today",
            "max_results": 5
        },
        {
            "name": "Technical query",
            "query": "NVIDIA GPU AI chips market share 2024",
            "max_results": 5
        },
        {
            "name": "Financial news",
            "query": "Tesla Q3 2024 earnings report",
            "max_results": 5
        }
    ]
    
    web_search = TOOL_REGISTRY["web_search"]
    
    for i, test in enumerate(test_cases, 1):
        print("=" * 80)
        print(f"Test {i}: {test['name']}")
        print(f"Query: {test['query']}")
        print("=" * 80)
        
        try:
            result = web_search(
                query=test["query"],
                max_results=test["max_results"],
                synthesize_answer=False,
                prefer_brave=False
            )
            
            # Display summary
            print(f"\n✅ Search completed")
            print(f"   Result count: {result.get('result_count', 0)}")
            print(f"   Search time: {result.get('search_time', 0):.2f}s")
            print(f"   Source engine: {result.get('source_engine', 'N/A')}")
            
            # Display results with scores
            results = result.get('results', [])
            if results:
                print(f"\n📊 Results sorted by relevance:")
                for idx, res in enumerate(results, 1):
                    score = res.get('relevance_score', 0.0)
                    title = res.get('title', 'No title')[:70]
                    print(f"\n   [{idx}] Score: {score:.3f} ⭐")
                    print(f"       Title: {title}")
                    print(f"       URL: {res.get('url', 'N/A')[:80]}")
                    snippet = res.get('snippet', '')[:120]
                    if snippet:
                        print(f"       Snippet: {snippet}...")
                
                # Show score distribution
                scores = [r.get('relevance_score', 0.0) for r in results]
                print(f"\n   📈 Score statistics:")
                print(f"      Highest: {max(scores):.3f}")
                print(f"      Lowest: {min(scores):.3f}")
                print(f"      Average: {sum(scores)/len(scores):.3f}")
                print(f"      Range: {max(scores) - min(scores):.3f}")
            else:
                print("\n⚠️ No results returned!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("RELEVANCE SCORING TEST (BM25 + Embeddings)")
    print("=" * 80)
    print("\nTesting hybrid relevance scoring with BM25 and semantic embeddings...\n")
    
    test_relevance_scoring()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n💡 Results should be sorted by relevance score (highest first)")
    print("   - BM25 captures keyword matching")
    print("   - Embeddings capture semantic meaning")
    print("   - Hybrid score combines both (60% semantic, 40% BM25)")
