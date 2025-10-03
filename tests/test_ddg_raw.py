#!/usr/bin/env python3
"""
Debug what DuckDuckGo search returns directly
"""
import asyncio
from langchain_community.tools import DuckDuckGoSearchRun

async def test_ddg_direct():
    """Test DuckDuckGo search directly"""
    print("=" * 80)
    print("DUCKDUCKGO DIRECT TEST")
    print("=" * 80)
    
    search = DuckDuckGoSearchRun()
    query = "Apple stock price"
    
    print(f"\nQuery: {query}")
    print("\nExecuting search...\n")
    
    try:
        # Run search
        result = search.run(query)
        
        print("Result type:", type(result))
        print("Result length:", len(result) if isinstance(result, (str, list)) else "N/A")
        print("\n" + "=" * 80)
        print("RAW RESULT:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        
        # Try to parse it
        if isinstance(result, str):
            # Split by common separators
            parts = result.split(", snippet:")
            print(f"\n\nFound {len(parts)} potential results when splitting by ', snippet:'")
            
            for i, part in enumerate(parts[:3], 1):
                print(f"\n--- Part {i} ---")
                print(part[:200] + "..." if len(part) > 200 else part)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ddg_direct())
