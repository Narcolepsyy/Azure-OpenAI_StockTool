#!/usr/bin/env python3
"""
Comprehensive Response Speed Test Suite
Tests real-world performance of the AI Stocks Assistant API
"""
import asyncio
import sys
import time
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime
import statistics

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class PerformanceTest:
    """Performance test suite for AI service response times."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.base_url = "http://127.0.0.1:8000"
        
    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
        print(f"{BOLD}{BLUE}{text.center(80)}{RESET}")
        print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")
    
    def print_test(self, name: str):
        """Print test name."""
        print(f"{BOLD}Testing:{RESET} {name}...", end=" ", flush=True)
    
    def print_result(self, duration: float, target: float, details: str = ""):
        """Print test result with color coding."""
        status = "✅ PASS" if duration <= target else "⚠️  SLOW" if duration <= target * 1.5 else "❌ FAIL"
        
        if duration <= target:
            color = GREEN
        elif duration <= target * 1.5:
            color = YELLOW
        else:
            color = RED
        
        print(f"{color}{status}{RESET} - {duration:.2f}s (target: {target:.0f}s) {details}")
    
    async def test_stock_quote_speed(self) -> Dict[str, Any]:
        """Test simple stock quote retrieval speed."""
        self.print_test("Simple Stock Quote (AAPL)")
        
        try:
            from app.services.stock_service import get_stock_quote
            
            start = time.perf_counter()
            result = get_stock_quote("AAPL")
            duration = time.perf_counter() - start
            
            target = 2.0  # 2 seconds for stock quote
            self.print_result(duration, target, f"(${result.get('price', 'N/A')})")
            
            return {
                "test": "stock_quote",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "result_size": len(str(result))
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "stock_quote", "duration": 0, "target": 2.0, "passed": False, "error": str(e)}
    
    async def test_stock_news_speed(self) -> Dict[str, Any]:
        """Test stock news retrieval speed."""
        self.print_test("Stock News (AAPL, 5 articles)")
        
        try:
            from app.services.stock_service import get_stock_news
            
            start = time.perf_counter()
            result = get_stock_news("AAPL", limit=5)
            duration = time.perf_counter() - start
            
            target = 5.0  # 5 seconds for news
            self.print_result(duration, target, f"({result.get('count', 0)} articles)")
            
            return {
                "test": "stock_news",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "articles_count": result.get('count', 0)
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "stock_news", "duration": 0, "target": 5.0, "passed": False, "error": str(e)}
    
    async def test_web_search_speed(self) -> Dict[str, Any]:
        """Test web search speed."""
        self.print_test("Web Search (Financial news)")
        
        try:
            from app.services.perplexity_web_search import perplexity_search
            
            start = time.perf_counter()
            result = await perplexity_search(
                query="Latest Tesla stock market news",
                max_results=5,
                synthesize_answer=True
            )
            duration = time.perf_counter() - start
            
            target = 15.0  # 15 seconds for web search with synthesis
            sources = len(result.get('sources', []))
            self.print_result(duration, target, f"({sources} sources)")
            
            return {
                "test": "web_search",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "sources_count": sources
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "web_search", "duration": 0, "target": 15.0, "passed": False, "error": str(e)}
    
    async def test_simple_chat_speed(self) -> Dict[str, Any]:
        """Test simple chat response speed (no tools)."""
        self.print_test("Simple Chat ('Hello')")
        
        try:
            from app.utils.conversation import prepare_conversation_messages
            from app.services.openai_client import get_client_for_model
            
            messages, conv_id = prepare_conversation_messages(
                prompt="Hello",
                system_prompt="You are a helpful assistant. Keep responses brief.",
                conv_id="test-simple",
                reset=True
            )
            
            start = time.perf_counter()
            client, model, config = get_client_for_model("gpt-4o-mini")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=100,
                timeout=config.get("timeout", 25)
            )
            duration = time.perf_counter() - start
            
            target = 3.0  # 3 seconds for simple chat
            tokens = response.usage.total_tokens if response.usage else 0
            self.print_result(duration, target, f"({tokens} tokens)")
            
            return {
                "test": "simple_chat",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "tokens": tokens
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "simple_chat", "duration": 0, "target": 3.0, "passed": False, "error": str(e)}
    
    async def test_tool_call_speed(self) -> Dict[str, Any]:
        """Test chat with tool calling speed."""
        self.print_test("Chat with Tool Call (get stock quote)")
        
        try:
            from app.utils.conversation import prepare_conversation_messages
            from app.services.openai_client import get_client_for_model
            from app.utils.tools import build_tools_for_request
            
            prompt = "What is Apple's current stock price?"
            tools_spec = build_tools_for_request(prompt)
            
            messages, conv_id = prepare_conversation_messages(
                prompt=prompt,
                system_prompt="You are a financial assistant.",
                conv_id="test-tool",
                reset=True
            )
            
            start = time.perf_counter()
            client, model, config = get_client_for_model("gpt-4o-mini")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools_spec if tools_spec else None,
                max_tokens=config.get("max_completion_tokens", 600),
                timeout=config.get("timeout", 25)
            )
            duration = time.perf_counter() - start
            
            target = 5.0  # 5 seconds for chat + tool call
            has_tool_calls = bool(response.choices[0].message.tool_calls)
            self.print_result(duration, target, f"(tool_calls: {has_tool_calls})")
            
            return {
                "test": "tool_call_chat",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "has_tool_calls": has_tool_calls
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "tool_call_chat", "duration": 0, "target": 5.0, "passed": False, "error": str(e)}
    
    async def test_cache_hit_speed(self) -> Dict[str, Any]:
        """Test cached response speed."""
        self.print_test("Cached Response")
        
        try:
            from app.services.stock_service import get_stock_quote
            
            # First call to populate cache
            get_stock_quote("MSFT")
            
            # Second call (should be cached)
            start = time.perf_counter()
            result = get_stock_quote("MSFT")
            duration = time.perf_counter() - start
            
            target = 0.01  # 10ms for cached response
            self.print_result(duration, target, f"(${result.get('price', 'N/A')})")
            
            return {
                "test": "cache_hit",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "speedup": "instant" if duration < 0.1 else f"{2.0/duration:.1f}x"
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "cache_hit", "duration": 0, "target": 0.01, "passed": False, "error": str(e)}
    
    async def test_parallel_tools_speed(self) -> Dict[str, Any]:
        """Test parallel tool execution speed."""
        self.print_test("Parallel Tool Calls (3 stocks)")
        
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from app.services.stock_service import get_stock_quote
            
            symbols = ["AAPL", "GOOGL", "TSLA"]
            
            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(get_stock_quote, sym) for sym in symbols]
                results = [f.result() for f in as_completed(futures)]
            duration = time.perf_counter() - start
            
            target = 3.0  # Should be similar to single call due to parallelization
            self.print_result(duration, target, f"({len(results)} stocks)")
            
            return {
                "test": "parallel_tools",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "stocks_count": len(results)
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "parallel_tools", "duration": 0, "target": 3.0, "passed": False, "error": str(e)}
    
    async def test_rag_search_speed(self) -> Dict[str, Any]:
        """Test RAG knowledge base search speed."""
        self.print_test("RAG Knowledge Search")
        
        try:
            from app.services.rag_service import rag_search
            from app.core.config import RAG_ENABLED
            
            if not RAG_ENABLED:
                print(f"{YELLOW}SKIP{RESET} - RAG disabled")
                return {"test": "rag_search", "skipped": True, "reason": "RAG disabled"}
            
            start = time.perf_counter()
            result = rag_search("financial risk assessment", k=3)
            duration = time.perf_counter() - start
            
            target = 2.0  # 2 seconds for RAG search
            results_count = result.get('count', 0)
            self.print_result(duration, target, f"({results_count} results)")
            
            return {
                "test": "rag_search",
                "duration": duration,
                "target": target,
                "passed": duration <= target,
                "results_count": results_count
            }
        except Exception as e:
            print(f"{RED}ERROR:{RESET} {e}")
            return {"test": "rag_search", "duration": 0, "target": 2.0, "passed": False, "error": str(e)}
    
    def print_summary(self):
        """Print test summary with statistics."""
        self.print_header("TEST SUMMARY")
        
        # Filter out skipped tests
        completed = [r for r in self.results if "skipped" not in r]
        
        if not completed:
            print(f"{RED}No tests completed{RESET}")
            return
        
        passed = sum(1 for r in completed if r.get('passed', False))
        failed = len(completed) - passed
        
        print(f"Total Tests: {len(completed)}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}\n")
        
        # Performance statistics
        durations = [r['duration'] for r in completed if r['duration'] > 0]
        if durations:
            print(f"Performance Statistics:")
            print(f"  Average: {statistics.mean(durations):.2f}s")
            print(f"  Median:  {statistics.median(durations):.2f}s")
            print(f"  Min:     {min(durations):.4f}s")
            print(f"  Max:     {max(durations):.2f}s\n")
        
        # Individual test results
        print(f"{BOLD}Individual Test Results:{RESET}")
        for result in completed:
            name = result['test'].replace('_', ' ').title()
            duration = result['duration']
            target = result.get('target', 0)
            
            status = f"{GREEN}✅{RESET}" if result.get('passed') else f"{RED}❌{RESET}"
            print(f"  {status} {name:30s} {duration:6.2f}s / {target:.0f}s")
        
        # Performance rating
        print(f"\n{BOLD}Overall Performance Rating:{RESET}")
        if failed == 0:
            print(f"  {GREEN}🌟 EXCELLENT - All tests passed!{RESET}")
        elif passed / len(completed) >= 0.8:
            print(f"  {YELLOW}👍 GOOD - Most tests passed{RESET}")
        elif passed / len(completed) >= 0.5:
            print(f"  {YELLOW}⚠️  ACCEPTABLE - Some optimization needed{RESET}")
        else:
            print(f"  {RED}❌ NEEDS IMPROVEMENT - Major optimization required{RESET}")
        
        # Recommendations
        print(f"\n{BOLD}Recommendations:{RESET}")
        
        slow_tests = [r for r in completed if not r.get('passed') and r['duration'] > 0]
        if slow_tests:
            print(f"  {YELLOW}Slow tests detected:{RESET}")
            for test in slow_tests:
                name = test['test'].replace('_', ' ').title()
                duration = test['duration']
                target = test.get('target', 0)
                slowdown = duration / target if target > 0 else 0
                print(f"    - {name}: {duration:.2f}s (target: {target:.0f}s, {slowdown:.1f}x slower)")
        else:
            print(f"  {GREEN}✅ All tests meeting performance targets!{RESET}")
        
        # Cache effectiveness
        cache_test = next((r for r in completed if r['test'] == 'cache_hit'), None)
        if cache_test and cache_test.get('duration', 1) < 0.1:
            print(f"  {GREEN}✅ Caching is working effectively{RESET}")
        
        # Parallel execution
        parallel_test = next((r for r in completed if r['test'] == 'parallel_tools'), None)
        if parallel_test and parallel_test.get('passed'):
            print(f"  {GREEN}✅ Parallel tool execution is optimized{RESET}")


async def main():
    """Run all performance tests."""
    tester = PerformanceTest()
    
    tester.print_header("AI STOCKS ASSISTANT - RESPONSE SPEED TEST")
    print(f"Testing response times against performance targets...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run all tests
    tests = [
        tester.test_cache_hit_speed(),
        tester.test_stock_quote_speed(),
        tester.test_stock_news_speed(),
        tester.test_simple_chat_speed(),
        tester.test_tool_call_speed(),
        tester.test_parallel_tools_speed(),
        tester.test_rag_search_speed(),
        tester.test_web_search_speed(),
    ]
    
    for test in tests:
        result = await test
        tester.results.append(result)
        await asyncio.sleep(0.5)  # Small delay between tests
    
    # Print summary
    tester.print_summary()
    
    # Exit code based on results
    completed = [r for r in tester.results if "skipped" not in r]
    failed = sum(1 for r in completed if not r.get('passed', False))
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Test suite error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
