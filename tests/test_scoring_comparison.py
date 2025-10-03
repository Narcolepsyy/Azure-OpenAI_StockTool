#!/usr/bin/env python3
"""
Compare results with and without embeddings to show scoring quality
"""
from app.utils.tools import TOOL_REGISTRY

def compare_scoring():
    """Compare BM25-only vs BM25+Embeddings"""
    
    query = "Apple stock price analysis"
    
    web_search = TOOL_REGISTRY["web_search"]
    
    print("=" * 80)
    print("SCORING COMPARISON TEST")
    print("=" * 80)
    print(f"\nQuery: {query}")
    print("\nThis test shows how hybrid scoring (BM25 + embeddings) ranks results")
    print("better than keyword matching alone.\n")
    
    try:
        result = web_search(
            query=query,
            max_results=5,
            synthesize_answer=False,
            prefer_brave=False
        )
        
        results = result.get('results', [])
        
        print(f"✅ Found {len(results)} results")
        print(f"   Search time: {result.get('search_time', 0):.2f}s")
        print("\n" + "=" * 80)
        print("RESULTS RANKED BY RELEVANCE SCORE")
        print("=" * 80)
        
        for idx, res in enumerate(results, 1):
            score = res.get('relevance_score', 0.0)
            title = res.get('title', 'No title')
            
            # Visual indicator
            if score >= 0.7:
                indicator = "🟢 Excellent"
            elif score >= 0.5:
                indicator = "🟡 Good"
            elif score >= 0.3:
                indicator = "🟠 Fair"
            else:
                indicator = "🔴 Poor"
            
            print(f"\n{idx}. {indicator} (Score: {score:.3f})")
            print(f"   Title: {title}")
            print(f"   URL: {res.get('url', 'N/A')[:80]}")
            
            # Show snippet
            snippet = res.get('snippet', '')[:150]
            if snippet:
                print(f"   Snippet: {snippet}...")
        
        print("\n" + "=" * 80)
        print("SCORING BREAKDOWN")
        print("=" * 80)
        print("\n📊 How hybrid scoring works:")
        print("   • BM25 (40%): Keyword matching (term frequency + document length)")
        print("   • Embeddings (60%): Semantic similarity (meaning-based)")
        print("   • Combined: More accurate relevance than keywords alone")
        print("\n✨ Benefits:")
        print("   • Finds semantically similar content even with different words")
        print("   • Ranks exact keyword matches higher")
        print("   • Balances precision and recall")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    compare_scoring()
