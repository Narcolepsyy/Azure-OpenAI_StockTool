#!/usr/bin/env python3
"""
Quick Response Speed Test
Simple test to check if responses are fast enough
"""
import time
import sys


def test_basic_operations():
    """Test basic operations that should be instant."""
    print("🔍 Testing Basic Operations...")
    
    # Test 1: Cache operations
    print("  Testing cache...", end=" ")
    from app.utils.cache_manager import get_cache_manager, CacheType
    
    cache_mgr = get_cache_manager()
    start = time.perf_counter()
    cache_mgr.set(CacheType.STOCK_QUOTES, "TEST", {"price": 100})
    result = cache_mgr.get(CacheType.STOCK_QUOTES, "TEST")
    duration = time.perf_counter() - start
    
    if duration < 0.001 and result:
        print(f"✅ {duration*1000:.2f}ms")
    else:
        print(f"❌ Too slow: {duration*1000:.2f}ms")
        return False
    
    # Test 2: Token estimation
    print("  Testing token estimation...", end=" ")
    from app.utils.conversation import estimate_tokens
    
    start = time.perf_counter()
    tokens = estimate_tokens("This is a test message" * 10)
    duration = time.perf_counter() - start
    
    if duration < 0.001 and tokens > 0:
        print(f"✅ {duration*1000:.2f}ms ({tokens} tokens)")
    else:
        print(f"❌ Too slow: {duration*1000:.2f}ms")
        return False
    
    # Test 3: Config loading
    print("  Testing config...", end=" ")
    from app.core.config import DEFAULT_MODEL, AVAILABLE_MODELS
    
    start = time.perf_counter()
    model = AVAILABLE_MODELS.get(DEFAULT_MODEL)
    duration = time.perf_counter() - start
    
    if duration < 0.001 and model:
        print(f"✅ {duration*1000:.2f}ms (model: {DEFAULT_MODEL})")
    else:
        print(f"❌ Too slow: {duration*1000:.2f}ms")
        return False
    
    return True


def test_stock_data():
    """Test stock data retrieval speed."""
    print("\n📊 Testing Stock Data Retrieval...")
    
    # Test 1: Stock quote (should be < 2s on first call, < 1ms on cache hit)
    print("  Getting AAPL quote (first call)...", end=" ", flush=True)
    from app.services.stock_service import get_stock_quote
    
    try:
        start = time.perf_counter()
        result = get_stock_quote("AAPL")
        duration = time.perf_counter() - start
        
        if duration < 3.0 and result.get("price"):
            print(f"✅ {duration:.2f}s (${result['price']})")
        else:
            print(f"⚠️  Slow: {duration:.2f}s")
            return False
        
        # Test cache hit
        print("  Getting AAPL quote (cached)...", end=" ", flush=True)
        start = time.perf_counter()
        result = get_stock_quote("AAPL")
        duration = time.perf_counter() - start
        
        if duration < 0.1:
            print(f"✅ {duration*1000:.2f}ms (cache hit)")
        else:
            print(f"⚠️  Cache slow: {duration*1000:.2f}ms")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_chat_performance():
    """Test chat response speed."""
    print("\n💬 Testing Chat Performance...")
    
    print("  Simple chat response...", end=" ", flush=True)
    
    try:
        from app.services.openai_client import get_client_for_model
        
        start = time.perf_counter()
        client, model, config = get_client_for_model("gpt-4o-mini")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Be brief."},
                {"role": "user", "content": "Say 'OK'"}
            ],
            max_tokens=10,
            timeout=config.get("timeout", 25)
        )
        duration = time.perf_counter() - start
        
        if duration < 5.0 and response.choices:
            tokens = response.usage.total_tokens if response.usage else 0
            print(f"✅ {duration:.2f}s ({tokens} tokens)")
            return True
        else:
            print(f"⚠️  Slow: {duration:.2f}s")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def print_summary(results):
    """Print test summary."""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Response times are FAST ENOUGH!")
        print("\nPerformance Grade: A+ 🌟")
    elif passed >= total * 0.8:
        print("\n👍 Most tests passed! Response times are GOOD!")
        print("\nPerformance Grade: B")
    elif passed >= total * 0.6:
        print("\n⚠️  Some tests slow. Response times are ACCEPTABLE.")
        print("\nPerformance Grade: C")
    else:
        print("\n❌ Multiple tests failed. OPTIMIZATION NEEDED!")
        print("\nPerformance Grade: D")
    
    print("\nCurrent optimizations active:")
    from app.core.config import AVAILABLE_MODELS, DEFAULT_MODEL
    model = AVAILABLE_MODELS.get(DEFAULT_MODEL, {})
    print(f"  - Timeout: {model.get('timeout', 'N/A')}s")
    print(f"  - Max tokens: {model.get('max_completion_tokens', 'N/A')}")
    print(f"  - Parallel tools: ThreadPoolExecutor(8 workers)")
    print(f"  - Caching: Multi-layer TTLCache")
    print(f"  - Connection pooling: Enabled")
    
    return passed == total


def main():
    """Run quick performance tests."""
    print("="*60)
    print("QUICK RESPONSE SPEED TEST")
    print("="*60)
    print("\nTesting if current implementation is fast enough...\n")
    
    results = {}
    
    # Run tests
    results["Basic Operations"] = test_basic_operations()
    results["Stock Data"] = test_stock_data()
    results["Chat Performance"] = test_chat_performance()
    
    # Print summary
    all_passed = print_summary(results)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
