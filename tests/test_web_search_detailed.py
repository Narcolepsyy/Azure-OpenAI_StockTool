#!/usr/bin/env python3
"""
Detailed test of web_search to see the full result structure
"""
import json
from app.utils.tools import TOOL_REGISTRY

def test_detailed_web_search():
    """Test web_search and display full result structure"""
    
    web_search = TOOL_REGISTRY["web_search"]
    
    print("=" * 80)
    print("DETAILED WEB SEARCH TEST")
    print("=" * 80)
    print("\nQuery: 'Tesla stock price'")
    print("Max results: 5")
    print("Prefer Brave: False (using DuckDuckGo)")
    print()
    
    try:
        result = web_search(
            query="Tesla stock price",
            max_results=5,
            synthesize_answer=False,
            prefer_brave=False
        )
        
        print("=" * 80)
        print("FULL RESULT STRUCTURE")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_detailed_web_search()
