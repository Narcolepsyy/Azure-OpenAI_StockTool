#!/usr/bin/env python3
"""
Test script to verify HTTP transport cleanup fixes in perplexity_web_search
"""
import asyncio
import sys
sys.path.append('.')

async def test_multiple_searches():
    """Test multiple searches to verify proper cleanup."""
    from app.services.perplexity_web_search import PerplexityWebSearchService, cleanup_perplexity_service
    
    print("🔧 Testing HTTP Transport Cleanup Fixes")
    print("="*50)
    
    # Test 1: Multiple searches with same service
    print("Test 1: Multiple searches with same service...")
    service = PerplexityWebSearchService()
    
    try:
        queries = [
            "Tesla stock performance",
            "Apple latest earnings",
            "Microsoft Azure news"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"  Search {i}: {query}")
            result = await service.perplexity_search(query, max_results=2)
            print(f"    ✅ Success - {len(result.sources)} sources, {len(result.answer)} chars")
            
            # Small delay between searches
            await asyncio.sleep(0.5)
        
        print("  ✅ Multiple searches completed successfully")
        
    except Exception as e:
        print(f"  ❌ Error during multiple searches: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Explicit cleanup
        await service._close_session()
        print("  🧹 Service session cleaned up")
    
    # Test 2: Service singleton pattern
    print("\nTest 2: Service singleton pattern...")
    try:
        from app.services.perplexity_web_search import get_perplexity_service
        
        service1 = get_perplexity_service()
        service2 = get_perplexity_service()
        
        print(f"  Same instance: {service1 is service2}")
        
        result = await service1.perplexity_search("Bitcoin price analysis", max_results=2)
        print(f"  ✅ Singleton search successful - {len(result.sources)} sources")
        
        # Global cleanup
        await cleanup_perplexity_service()
        print("  🧹 Global service cleaned up")
        
    except Exception as e:
        print(f"  ❌ Error in singleton test: {e}")
    
    # Test 3: Concurrent searches
    print("\nTest 3: Concurrent searches...")
    try:
        service = PerplexityWebSearchService()
        
        concurrent_queries = [
            "Google stock analysis",
            "Amazon earnings report",
            "NVIDIA AI chips news"
        ]
        
        # Run searches concurrently
        tasks = [
            service.perplexity_search(query, max_results=2)
            for query in concurrent_queries
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        print(f"  ✅ Concurrent searches: {len(successful_results)}/{len(concurrent_queries)} successful")
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"    ❌ Query {i+1} failed: {result}")
            else:
                print(f"    ✅ Query {i+1}: {len(result.sources)} sources")
        
        await service._close_session()
        print("  🧹 Concurrent service cleaned up")
        
    except Exception as e:
        print(f"  ❌ Error in concurrent test: {e}")
    
    print("\n🎯 Transport cleanup test completed!")

if __name__ == "__main__":
    asyncio.run(test_multiple_searches())