#!/usr/bin/env python3
"""
Test the new web_search tool integration in tools.py
"""
import sys
import json
from app.utils.tools import TOOL_REGISTRY, tools_spec

def test_tool_registry():
    """Test that web_search is registered correctly"""
    print("=" * 80)
    print("Testing Tool Registry")
    print("=" * 80)
    
    # Check if web_search is in registry
    if "web_search" in TOOL_REGISTRY:
        print("✅ web_search found in TOOL_REGISTRY")
    else:
        print("❌ web_search NOT found in TOOL_REGISTRY")
        print(f"Available tools: {list(TOOL_REGISTRY.keys())}")
        return False
    
    # Check if perplexity_search is removed
    if "perplexity_search" not in TOOL_REGISTRY:
        print("✅ perplexity_search removed from TOOL_REGISTRY")
    else:
        print("❌ perplexity_search still in TOOL_REGISTRY")
        return False
    
    return True

def test_tool_spec():
    """Test that web_search is in the OpenAI function spec"""
    print("\n" + "=" * 80)
    print("Testing Tool Spec")
    print("=" * 80)
    
    tool_names = [tool["function"]["name"] for tool in tools_spec]
    
    # Check if web_search is in spec
    if "web_search" in tool_names:
        print("✅ web_search found in tools_spec")
        
        # Get the web_search spec
        web_search_spec = next(t for t in tools_spec if t["function"]["name"] == "web_search")
        print(f"\nTool name: {web_search_spec['function']['name']}")
        print(f"Description: {web_search_spec['function']['description'][:100]}...")
        print(f"Parameters: {list(web_search_spec['function']['parameters']['properties'].keys())}")
    else:
        print("❌ web_search NOT found in tools_spec")
        print(f"Available tools: {tool_names}")
        return False
    
    # Check if perplexity_search is removed
    if "perplexity_search" not in tool_names:
        print("✅ perplexity_search removed from tools_spec")
    else:
        print("❌ perplexity_search still in tools_spec")
        return False
    
    return True

def test_tool_execution():
    """Test that web_search can be called"""
    print("\n" + "=" * 80)
    print("Testing Tool Execution")
    print("=" * 80)
    
    try:
        # Get the web_search function
        web_search_func = TOOL_REGISTRY["web_search"]
        print("✅ web_search function retrieved")
        
        # Try to call it with a simple query
        print("\nCalling web_search with query='Apple stock price'...")
        result = web_search_func(
            query="Apple stock price",
            max_results=3,
            synthesize_answer=False,
            prefer_brave=False
        )
        
        print(f"✅ web_search executed successfully")
        print(f"\nResult keys: {list(result.keys())}")
        
        # Check result structure
        if "results" in result:
            print(f"Number of results: {len(result['results'])}")
            if result['results']:
                first_result = result['results'][0]
                print(f"\nFirst result keys: {list(first_result.keys())}")
                print(f"Title: {first_result.get('title', 'N/A')[:80]}")
                print(f"URL: {first_result.get('url', 'N/A')[:80]}")
        
        if "answer" in result:
            answer = result.get('answer', '')
            if answer:
                print(f"\nAnswer: {answer[:200]}...")
            else:
                print("\nNo answer (synthesis disabled)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error executing web_search: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("WEB SEARCH INTEGRATION TEST")
    print("=" * 80)
    
    results = []
    
    # Test 1: Tool Registry
    results.append(("Tool Registry", test_tool_registry()))
    
    # Test 2: Tool Spec
    results.append(("Tool Spec", test_tool_spec()))
    
    # Test 3: Tool Execution
    results.append(("Tool Execution", test_tool_execution()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed! web_search integration successful!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
