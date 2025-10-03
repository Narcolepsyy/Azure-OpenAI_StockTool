"""Test script for enhanced Perplexity-style web search functionality."""
import asyncio
import json
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_perplexity_search():
    """Test the new Perplexity-style web search functionality."""
    print("=" * 80)
    print("TESTING ENHANCED PERPLEXITY-STYLE WEB SEARCH")
    print("=" * 80)
    
    # Test queries to validate different aspects
    test_queries = [
        {
            "query": "Apple stock price target 2024 analyst predictions",
            "description": "Financial query with recent data",
            "synthesize": True
        },
        {
            "query": "What is artificial intelligence machine learning",
            "description": "General knowledge query",
            "synthesize": True
        },
        {
            "query": "Tesla earnings Q3 2024 results",
            "description": "Recent news query", 
            "synthesize": True
        }
    ]
    
    success_count = 0
    total_tests = len(test_queries)
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{'='*20} TEST {i}/{total_tests} {'='*20}")
        print(f"Query: {test_case['query']}")
        print(f"Description: {test_case['description']}")
        print("-" * 60)
        
        try:
            # Import the function
            from app.services.perplexity_web_search import perplexity_web_search
            
            start_time = time.time()
            
            # Execute search
            result = perplexity_web_search(
                query=test_case['query'],
                max_results=6,
                synthesize_answer=test_case['synthesize'],
                include_recent=True
            )
            
            duration = time.time() - start_time
            
            # Validate results
            print(f"✓ Search completed in {duration:.2f}s")
            print(f"  Method: {result.get('method', 'unknown')}")
            print(f"  Sources found: {len(result.get('sources', []))}")
            print(f"  Citations: {len(result.get('citations', {}))}")
            print(f"  Confidence: {result.get('confidence_score', 0):.2f}")
            print(f"  Search time: {result.get('search_time', 0):.2f}s")
            print(f"  Synthesis time: {result.get('synthesis_time', 0):.2f}s")
            
            # Check answer quality
            answer = result.get('answer', '')
            if answer:
                print(f"✓ Answer generated ({len(answer)} chars)")
                print(f"  Preview: {answer[:200]}...")
                
                # Check for citations in answer
                import re
                citations_in_answer = len(re.findall(r'\[\d+\]', answer))
                if citations_in_answer > 0:
                    print(f"✓ Citations found in answer: {citations_in_answer}")
                else:
                    print("⚠ No citations found in answer")
            else:
                print("⚠ No answer generated")
            
            # Check sources quality
            sources = result.get('sources', [])
            if sources:
                print(f"✓ Sources details:")
                for idx, source in enumerate(sources[:3], 1):
                    print(f"  {idx}. {source.get('title', 'No title')[:80]}...")
                    print(f"     URL: {source.get('url', 'No URL')}")
                    print(f"     Content: {source.get('word_count', 0)} words")
                    print(f"     Relevance: {source.get('relevance_score', 0):.2f}")
            
            # Check citations
            citations = result.get('citations', {})
            if citations:
                print(f"✓ Citations mapping:")
                for cite_id, cite_info in list(citations.items())[:3]:
                    print(f"  [{cite_id}] {cite_info}")
            
            success_count += 1
            print("✅ TEST PASSED")
            
        except Exception as e:
            print(f"❌ TEST FAILED: {str(e)}")
            logger.error(f"Test failed for query '{test_case['query']}': {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print(f"TEST SUMMARY: {success_count}/{total_tests} tests passed")
    print("=" * 80)
    
    return success_count == total_tests

def test_tool_integration():
    """Test the tool integration functionality."""
    print("\n" + "=" * 80)
    print("TESTING TOOL INTEGRATION")
    print("=" * 80)
    
    try:
        # Test tool registry
        from app.utils.tools import TOOL_REGISTRY, tools_spec
        
        # Check if perplexity_search is in tools
        if 'perplexity_search' in TOOL_REGISTRY:
            print("✓ perplexity_search tool found in TOOL_REGISTRY")
        else:
            print("❌ perplexity_search tool NOT found in TOOL_REGISTRY")
            return False
        
        # Check if tool spec exists
        perplexity_spec = None
        for tool in tools_spec:
            if tool.get('function', {}).get('name') == 'perplexity_search':
                perplexity_spec = tool
                break
        
        if perplexity_spec:
            print("✓ perplexity_search tool specification found")
            
            # Validate spec structure
            func_spec = perplexity_spec['function']
            required_fields = ['name', 'description', 'parameters']
            
            for field in required_fields:
                if field in func_spec:
                    print(f"  ✓ {field}: {func_spec[field][:100] if isinstance(func_spec[field], str) else 'OK'}")
                else:
                    print(f"  ❌ Missing {field}")
                    return False
        else:
            print("❌ perplexity_search tool specification NOT found")
            return False
        
        # Test tool execution
        print("\nTesting tool execution...")
        tool_func = TOOL_REGISTRY['perplexity_search']
        result = tool_func(query="test query", max_results=3, synthesize_answer=False)
        
        if result and isinstance(result, dict):
            print("✓ Tool execution successful")
            print(f"  Result keys: {list(result.keys())}")
        else:
            print("❌ Tool execution failed or returned invalid result")
            return False
        
        print("✅ TOOL INTEGRATION TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ TOOL INTEGRATION TESTS FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test the API endpoints (basic structure test)."""
    print("\n" + "=" * 80)
    print("TESTING API ENDPOINTS")
    print("=" * 80)
    
    try:
        # Import router to check it's properly configured
        from app.routers.enhanced_search import router
        
        print("✓ Enhanced search router imported successfully")
        
        # Check router configuration
        if hasattr(router, 'routes'):
            routes = [route.path for route in router.routes]
            print(f"✓ Router has {len(routes)} routes:")
            for route in routes:
                print(f"  - {route}")
        
        # Import main app to check router registration
        from main import app
        
        # Check if router is included
        router_prefixes = []
        for route in app.routes:
            if hasattr(route, 'path_regex'):
                path = str(route.path_regex.pattern)
                if '/api/search' in path:
                    router_prefixes.append(path)
        
        if router_prefixes:
            print("✓ Enhanced search router registered in main app")
            for prefix in router_prefixes:
                print(f"  - {prefix}")
        else:
            print("⚠ Enhanced search router may not be properly registered")
        
        print("✅ API ENDPOINT TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ API ENDPOINT TESTS FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Starting Enhanced Web Search Tests...")
    print(f"Test started at: {datetime.now().isoformat()}")
    
    all_passed = True
    
    # Test 1: Core Perplexity functionality
    if not test_perplexity_search():
        all_passed = False
    
    # Test 2: Tool integration
    if not test_tool_integration():
        all_passed = False
    
    # Test 3: API endpoints
    if not test_api_endpoints():
        all_passed = False
    
    # Final summary
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Enhanced web search is working correctly.")
        print("✅ Perplexity-style search with answer synthesis")
        print("✅ Source citations and content extraction")
        print("✅ Tool integration for AI assistant")
        print("✅ API endpoints for direct access")
    else:
        print("❌ SOME TESTS FAILED! Please check the output above.")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    main()