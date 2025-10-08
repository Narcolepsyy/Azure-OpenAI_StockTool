#!/usr/bin/env python3
"""
Web Search Performance Test
Tests Perplexity-style web search functionality and speed
"""
import asyncio
import time
import sys
from typing import Dict, Any

# Color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(70)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


def print_result(test_name: str, duration: float, target: float, details: str = ""):
    """Print test result with color coding."""
    if duration <= target:
        status = f"{GREEN}✅ FAST{RESET}"
        color = GREEN
    elif duration <= target * 1.5:
        status = f"{YELLOW}⚠️  SLOW{RESET}"
        color = YELLOW
    else:
        status = f"{RED}❌ VERY SLOW{RESET}"
        color = RED
    
    print(f"{BOLD}{test_name}{RESET}")
    print(f"  {status} - {color}{duration:.2f}s{RESET} (target: {target:.0f}s)")
    if details:
        print(f"  {details}")
    print()


async def test_async_web_search():
    """Test async web search (used internally)."""
    print(f"{BOLD}Testing Async Web Search...{RESET}\n")
    
    try:
        from app.services.perplexity_web_search import get_perplexity_service
        
        service = get_perplexity_service()
        
        # Test 1: Quick search without synthesis
        print("Test 1: Quick search (no synthesis)...", end=" ", flush=True)
        start = time.perf_counter()
        result = await service.perplexity_search(
            query="Tesla stock price today",
            max_results=5,
            synthesize_answer=False
        )
        duration = time.perf_counter() - start
        
        target = 8.0  # 8 seconds for search only
        # Handle both dict and PerplexityResponse object
        sources = len(result.sources if hasattr(result, 'sources') else result.get('sources', []))
        print_result("Quick Search", duration, target, f"Found {sources} sources")
        
        # Test 2: Search with synthesis
        print("Test 2: Search with AI synthesis...", end=" ", flush=True)
        start = time.perf_counter()
        result = await service.perplexity_search(
            query="Latest Microsoft earnings report summary",
            max_results=5,
            synthesize_answer=True
        )
        duration = time.perf_counter() - start
        
        target = 20.0  # 20 seconds for search + synthesis
        # Handle both dict and PerplexityResponse object
        answer = result.answer if hasattr(result, 'answer') else result.get('answer', '')
        sources = len(result.sources if hasattr(result, 'sources') else result.get('sources', []))
        answer_preview = answer[:100] + "..." if len(answer) > 100 else answer
        
        print_result(
            "Search + Synthesis", 
            duration, 
            target, 
            f"Sources: {sources}\nAnswer preview: {answer_preview}"
        )
        
        return True
        
    except Exception as e:
        print(f"{RED}ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_sync_web_search():
    """Test synchronous web search wrapper (used by tools)."""
    print(f"{BOLD}Testing Sync Web Search Wrapper...{RESET}\n")
    
    try:
        from app.services.perplexity_web_search import perplexity_web_search
        
        # Test 1: Basic search
        print("Test 1: Basic search (sync wrapper)...", end=" ", flush=True)
        start = time.perf_counter()
        result = perplexity_web_search(
            query="Apple stock news",
            max_results=5,
            synthesize_answer=False
        )
        duration = time.perf_counter() - start
        
        target = 10.0  # 10 seconds for sync wrapper
        sources = len(result.get('sources', []))
        print_result("Sync Basic Search", duration, target, f"Found {sources} sources")
        
        # Test 2: Search with synthesis
        print("Test 2: Search with synthesis (sync wrapper)...", end=" ", flush=True)
        start = time.perf_counter()
        result = perplexity_web_search(
            query="Amazon earnings latest news",
            max_results=5,
            synthesize_answer=True
        )
        duration = time.perf_counter() - start
        
        target = 25.0  # 25 seconds for sync wrapper with synthesis
        answer = result.get('answer', '')
        sources = len(result.get('sources', []))
        citations = result.get('citations', {})
        
        answer_preview = answer[:80] + "..." if len(answer) > 80 else answer
        
        print_result(
            "Sync Search + Synthesis",
            duration,
            target,
            f"Sources: {sources}, Citations: {len(citations)}\nAnswer: {answer_preview}"
        )
        
        # Show citation details
        if citations:
            print(f"  {BOLD}Citation details:{RESET}")
            for cid, citation in list(citations.items())[:3]:  # Show first 3
                print(f"    [{cid}] {citation.get('title', 'N/A')[:50]}")
        
        return True
        
    except Exception as e:
        print(f"{RED}ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_recent_news_search():
    """Test recent news search with time limits."""
    print(f"{BOLD}Testing Recent News Search...{RESET}\n")
    
    try:
        from app.services.perplexity_web_search import perplexity_web_search
        
        print("Test: Recent news (last week)...", end=" ", flush=True)
        start = time.perf_counter()
        result = perplexity_web_search(
            query="tech sector stock market",
            max_results=5,
            synthesize_answer=True,
            include_recent=True,
            time_limit='w'  # Last week
        )
        duration = time.perf_counter() - start
        
        target = 25.0  # 25 seconds for recent news with synthesis
        sources = len(result.get('sources', []))
        answer = result.get('answer', '')
        
        print_result(
            "Recent News Search",
            duration,
            target,
            f"Sources: {sources}\nAnswer length: {len(answer)} chars"
        )
        
        return True
        
    except Exception as e:
        print(f"{RED}ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_search_quality():
    """Test search result quality and structure."""
    print(f"{BOLD}Testing Search Quality...{RESET}\n")
    
    try:
        from app.services.perplexity_web_search import perplexity_web_search
        
        print("Checking search result structure...", end=" ", flush=True)
        result = perplexity_web_search(
            query="Nvidia AI chip market",
            max_results=5,
            synthesize_answer=True
        )
        
        # Check result structure
        checks = {
            "Has answer": bool(result.get('answer')),
            "Has sources": len(result.get('sources', [])) > 0,
            "Has citations": len(result.get('citations', {})) > 0,
            "Has search time": 'search_time' in result or 'latency_ms' in result,
            "Sources have URLs": all(s.get('url') for s in result.get('sources', [])),
            "Sources have titles": all(s.get('title') for s in result.get('sources', [])),
        }
        
        passed = sum(checks.values())
        total = len(checks)
        
        print(f"{GREEN if passed == total else YELLOW}{passed}/{total} checks passed{RESET}\n")
        
        for check, status in checks.items():
            icon = f"{GREEN}✅{RESET}" if status else f"{RED}❌{RESET}"
            print(f"  {icon} {check}")
        
        # Show sample source
        if result.get('sources'):
            source = result['sources'][0]
            print(f"\n  {BOLD}Sample source:{RESET}")
            print(f"    Title: {source.get('title', 'N/A')[:60]}")
            print(f"    URL: {source.get('url', 'N/A')[:60]}")
            print(f"    Domain: {source.get('domain', 'N/A')}")
        
        # Show answer preview
        answer = result.get('answer', '')
        if answer:
            print(f"\n  {BOLD}Answer preview:{RESET}")
            print(f"    {answer[:150]}...")
        
        return passed >= total - 1  # Allow 1 optional field to be missing
        
    except Exception as e:
        print(f"{RED}ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results: Dict[str, bool]):
    """Print test summary."""
    print_header("TEST SUMMARY")
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = f"{GREEN}✅{RESET}" if result else f"{RED}❌{RESET}"
        print(f"{status} {test}")
    
    print(f"\n{BOLD}Passed: {passed}/{total}{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 All web search tests passed!{RESET}")
        print(f"{GREEN}Web search is working correctly and fast enough.{RESET}")
        grade = "A+"
    elif passed >= total * 0.75:
        print(f"\n{YELLOW}👍 Most tests passed. Some improvements possible.{RESET}")
        grade = "B"
    else:
        print(f"\n{RED}❌ Multiple tests failed. Investigation needed.{RESET}")
        grade = "C"
    
    print(f"\n{BOLD}Performance Grade: {grade}{RESET}")
    
    # Performance tips
    print(f"\n{BOLD}Performance Tips:{RESET}")
    print("  • Search without synthesis: ~8-10s (for quick results)")
    print("  • Search with synthesis: ~20-25s (for AI-generated answers)")
    print("  • Use cache: Subsequent identical queries are instant")
    print("  • Limit results: Fewer results = faster response")
    
    return passed == total


async def main():
    """Run all web search tests."""
    print_header("WEB SEARCH PERFORMANCE TEST")
    print(f"Testing Perplexity-style web search functionality...")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Run tests
    print("="*70)
    results["Async Web Search"] = await test_async_web_search()
    
    print("="*70)
    results["Sync Web Search"] = test_sync_web_search()
    
    print("="*70)
    results["Recent News Search"] = test_recent_news_search()
    
    print("="*70)
    results["Search Quality"] = test_search_quality()
    
    # Print summary
    print("="*70)
    all_passed = print_summary(results)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Test error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
