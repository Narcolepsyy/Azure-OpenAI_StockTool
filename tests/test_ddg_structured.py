#!/usr/bin/env python3
"""
Test DuckDuckGoSearchResults (the correct tool)
"""
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchResults

def test_ddg_results():
    """Test DuckDuckGoSearchResults"""
    print("=" * 80)
    print("DUCKDUCKGO SEARCHRESULTS TEST")
    print("=" * 80)
    
    # Create wrapper and tool
    ddg_search = DuckDuckGoSearchAPIWrapper(max_results=5)
    ddg_tool = DuckDuckGoSearchResults(api_wrapper=ddg_search)
    
    query = "Tesla stock price"
    print(f"\nQuery: {query}")
    print("Max results: 5")
    print("\nExecuting search...\n")
    
    try:
        result = ddg_tool.run(query)
        
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, (str, list)) else 'N/A'}")
        print("\n" + "=" * 80)
        print("RAW RESULT:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        
        # Try to parse as JSON
        if isinstance(result, str):
            import json
            try:
                parsed = json.loads(result)
                print(f"\n✅ Successfully parsed as JSON")
                print(f"Type: {type(parsed)}")
                if isinstance(parsed, list):
                    print(f"Number of results: {len(parsed)}")
                    if parsed:
                        print(f"\nFirst result keys: {list(parsed[0].keys())}")
                        print(f"\nFirst result:")
                        print(json.dumps(parsed[0], indent=2))
            except json.JSONDecodeError as e:
                print(f"\n❌ Not valid JSON: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ddg_results()
