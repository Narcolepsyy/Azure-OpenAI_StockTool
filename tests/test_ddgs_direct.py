#!/usr/bin/env python3
"""
Test DDGS directly to diagnose the issue.
"""

import sys
sys.path.append('/home/khaitran/PycharmProjects/Azure-OpenAI_StockTool')

from ddgs import DDGS

def test_ddgs_direct():
    """Test DDGS directly with the Japanese query."""
    
    test_queries = [
        "八十二銀行 長野銀行 統合",  # Simplified version that worked
        "Hachijuni Bank Nagano Bank merger",
        "regional bank merger Japan"
    ]
    
    print("🔍 Testing DDGS Direct API")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: {query}")
        print("-" * 30)
        
        try:
            with DDGS() as ddgs:
                search_params = {
                    'query': query,
                    'region': 'jp-jp' if any(ord(c) > 127 for c in query) else 'us-en',
                    'safesearch': 'moderate',
                    'max_results': 5
                }
                
                print(f"Search params: {search_params}")
                
                results = list(ddgs.text(**search_params))
                print(f"Results found: {len(results)}")
                
                for j, result in enumerate(results[:3], 1):
                    print(f"  {j}. {result.get('title', 'No title')[:60]}...")
                    print(f"     URL: {result.get('href', 'No URL')}")
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_ddgs_direct()