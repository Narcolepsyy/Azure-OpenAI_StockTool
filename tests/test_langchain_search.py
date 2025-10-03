"""
Test script for LangChain web search service.
Demonstrates various search capabilities and compares with existing search.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.langchain_web_search import (
    LangChainWebSearchService,
    langchain_web_search,
    LANGCHAIN_AVAILABLE
)


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def print_result(result: dict):
    """Print search result in formatted way."""
    print(f"📊 Query: {result.get('query', 'N/A')}")
    print(f"⏱️  Total Time: {result.get('total_time', 0):.2f}s")
    print(f"   - Search: {result.get('search_time', 0):.2f}s")
    print(f"   - Synthesis: {result.get('synthesis_time', 0):.2f}s")
    print(f"🔍 Source: {result.get('source_engine', 'unknown').upper()}")
    print(f"📄 Results: {result.get('result_count', 0)}")
    
    # Print answer
    if result.get('answer'):
        print(f"\n💡 Answer:")
        print("-" * 80)
        print(result['answer'])
        print("-" * 80)
    
    # Print top 3 sources
    results = result.get('results', [])
    if results:
        print(f"\n📚 Top Sources:")
        for idx, res in enumerate(results[:3], 1):
            print(f"\n  [{idx}] {res.get('title', 'No title')}")
            print(f"      URL: {res.get('url', 'No URL')}")
            print(f"      {res.get('snippet', 'No snippet')[:150]}...")
    
    # Print citations
    citations = result.get('citations', [])
    if citations:
        print(f"\n🔗 Citations: {len(citations)} sources")


async def test_basic_search():
    """Test basic search functionality."""
    print_header("Test 1: Basic Search")
    
    try:
        result = await langchain_web_search(
            query="What is the current stock price of Apple (AAPL)?",
            max_results=5,
            synthesize_answer=True
        )
        print_result(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_news_search():
    """Test news search."""
    print_header("Test 2: Recent News Search")
    
    try:
        result = await langchain_web_search(
            query="Latest developments in artificial intelligence October 2025",
            max_results=8,
            synthesize_answer=True,
            include_recent=True
        )
        print_result(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_japanese_query():
    """Test Japanese language query."""
    print_header("Test 3: Japanese Query")
    
    try:
        result = await langchain_web_search(
            query="トヨタ自動車の最新ニュース",
            max_results=5,
            synthesize_answer=True
        )
        print_result(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_without_synthesis():
    """Test search without AI synthesis."""
    print_header("Test 4: Search Without Synthesis")
    
    try:
        result = await langchain_web_search(
            query="Microsoft earnings report 2025",
            max_results=10,
            synthesize_answer=False
        )
        print_result(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_brave_preference():
    """Test Brave Search preference."""
    print_header("Test 5: Brave Search Priority")
    
    try:
        result = await langchain_web_search(
            query="Tesla stock analysis",
            max_results=5,
            synthesize_answer=True,
            prefer_brave=True
        )
        print_result(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_service_class():
    """Test using service class directly."""
    print_header("Test 6: Service Class Usage")
    
    try:
        service = LangChainWebSearchService(
            model="gpt-4o-mini",
            temperature=0.2,
            max_results=5,
            verbose=False
        )
        
        result = await service.search(
            query="What are the benefits of diversification in stock portfolio?",
            synthesize_answer=True
        )
        
        print_result(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def run_all_tests():
    """Run all test cases."""
    print_header("LangChain Web Search Test Suite")
    
    if not LANGCHAIN_AVAILABLE:
        print("❌ LangChain not available!")
        print("Install with: pip install langchain langchain-community langchain-openai")
        return
    
    print("✅ LangChain is available")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Basic Search", test_basic_search),
        ("News Search", test_news_search),
        ("Japanese Query", test_japanese_query),
        ("No Synthesis", test_without_synthesis),
        ("Brave Preference", test_brave_preference),
        ("Service Class", test_service_class),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*80}\n")


async def demo_comparison():
    """Demo comparing LangChain search with existing search."""
    print_header("Comparison: LangChain vs Existing Search")
    
    query = "What factors affect stock market volatility?"
    
    print(f"Query: {query}\n")
    
    # LangChain search
    print("🔷 LangChain Search:")
    print("-" * 80)
    try:
        lc_result = await langchain_web_search(
            query=query,
            max_results=5,
            synthesize_answer=True
        )
        print(f"Time: {lc_result['total_time']:.2f}s")
        print(f"Results: {lc_result['result_count']}")
        print(f"Engine: {lc_result['source_engine']}")
        if lc_result.get('answer'):
            print(f"\nAnswer preview:\n{lc_result['answer'][:300]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*80 + "\n")
    
    # Existing perplexity search (if available)
    print("🔶 Existing Perplexity Search:")
    print("-" * 80)
    try:
        from app.services.perplexity_web_search import perplexity_web_search
        
        existing_result = perplexity_web_search(
            query=query,
            max_results=5,
            synthesize_answer=False  # Fast mode
        )
        print(f"Time: N/A")
        print(f"Results: {len(existing_result.get('results', []))}")
        print(f"Engine: Brave/DDGS")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LangChain web search")
    parser.add_argument(
        "--mode",
        choices=["all", "basic", "demo", "comparison"],
        default="all",
        help="Test mode to run"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Custom query to test"
    )
    
    args = parser.parse_args()
    
    if args.query:
        # Custom query test
        async def custom_test():
            print_header(f"Custom Query Test")
            result = await langchain_web_search(
                query=args.query,
                max_results=5,
                synthesize_answer=True
            )
            print_result(result)
        
        asyncio.run(custom_test())
    
    elif args.mode == "basic":
        asyncio.run(test_basic_search())
    elif args.mode == "demo":
        asyncio.run(test_basic_search())
    elif args.mode == "comparison":
        asyncio.run(demo_comparison())
    else:
        asyncio.run(run_all_tests())
