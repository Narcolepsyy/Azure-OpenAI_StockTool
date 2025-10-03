#!/usr/bin/env python3
"""
Test if web_search returns actual web results
"""
import json
from app.utils.tools import TOOL_REGISTRY

def test_web_search_results():
    """Test web_search with different queries"""
    
    test_queries = [
        {
            "query": "Apple stock price today",
            "max_results": 5,
            "synthesize_answer": False,
            "prefer_brave": False
        },
        {
            "query": "Tesla earnings 2024",
            "max_results": 3,
            "synthesize_answer": False,
            "prefer_brave": False
        },
        {
            "query": "NVIDIA AI chips market share",
            "max_results": 5,
            "synthesize_answer": False,
            "prefer_brave": False
        }
    ]
    
    web_search = TOOL_REGISTRY["web_search"]
    
    for i, test in enumerate(test_queries, 1):
        print("=" * 80)
        print(f"Test {i}: {test['query']}")
        print("=" * 80)
        
        try:
            result = web_search(**test)
            
            # Display summary
            print(f"\n✅ Search completed")
            print(f"   Query: {result.get('query', 'N/A')}")
            print(f"   Result count: {result.get('result_count', 0)}")
            print(f"   Search time: {result.get('search_time', 0):.2f}s")
            print(f"   Total time: {result.get('total_time', 0):.2f}s")
            print(f"   Source engine: {result.get('source_engine', 'N/A')}")
            
            # Display results
            results = result.get('results', [])
            if results:
                print(f"\n📄 Found {len(results)} results:")
                for idx, res in enumerate(results, 1):
                    print(f"\n   [{idx}] {res.get('title', 'No title')}")
                    print(f"       URL: {res.get('url', 'N/A')}")
                    snippet = res.get('snippet', '')
                    if snippet:
                        # Truncate long snippets
                        snippet_display = snippet[:150] + "..." if len(snippet) > 150 else snippet
                        print(f"       Snippet: {snippet_display}")
                    print(f"       Source: {res.get('source', 'N/A')}")
                    print(f"       Relevance: {res.get('relevance_score', 0):.2f}")
            else:
                print("\n⚠️ No results returned!")
            
            # Display answer if available
            answer = result.get('answer', '')
            if answer:
                print(f"\n💬 Answer (synthesis):")
                answer_display = answer[:300] + "..." if len(answer) > 300 else answer
                print(f"   {answer_display}")
            
            # Display citations
            citations = result.get('citations', {})
            if citations:
                print(f"\n📚 Citations: {len(citations)} sources")
                for cit_id, cit_info in list(citations.items())[:3]:
                    print(f"   [{cit_id}] {cit_info.get('title', 'N/A')[:60]}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("WEB SEARCH RESULTS TEST")
    print("=" * 80)
    print("\nTesting if web_search returns actual web results...\n")
    
    test_web_search_results()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
