#!/usr/bin/env python3
"""
Japanese Web Search Test
Tests web search functionality with Japanese queries
"""
import asyncio
import sys
import time
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


def print_result(result: Dict[str, Any]):
    """Print search result details."""
    print(f"\n{BOLD}Search Results:{RESET}")
    
    # Answer
    answer = result.get('answer', '')
    if answer:
        print(f"\n{BOLD}Answer:{RESET}")
        print(f"{answer[:500]}..." if len(answer) > 500 else answer)
    
    # Sources
    sources = result.get('sources', [])
    print(f"\n{BOLD}Sources: {len(sources)}{RESET}")
    for i, source in enumerate(sources[:5], 1):
        title = source.get('title', 'N/A')
        url = source.get('url', 'N/A')
        print(f"  [{i}] {title[:60]}")
        print(f"      {url[:70]}")
    
    # Citations
    citations = result.get('citations', {})
    if citations:
        print(f"\n{BOLD}Citations: {len(citations)}{RESET}")
        for cid, citation in list(citations.items())[:3]:
            if isinstance(citation, dict):
                print(f"  [{cid}] {citation.get('title', 'N/A')[:60]}")
            else:
                print(f"  [{cid}] {str(citation)[:60]}")
    
    # Search time
    search_time = result.get('search_time', 0)
    print(f"\n{BOLD}Search time: {search_time:.2f}s{RESET}")


async def test_japanese_search():
    """Test Japanese web search functionality."""
    print_header("JAPANESE WEB SEARCH TEST")
    
    from app.services.perplexity_web_search import perplexity_web_search
    
    test_queries = [
        {
            "query": "トヨタの株価",
            "description": "Toyota stock price (simple)",
            "target_time": 15
        },
        {
            "query": "日本の最新技術ニュース",
            "description": "Latest Japan tech news",
            "target_time": 20
        },
        {
            "query": "円相場の動向について教えてください",
            "description": "Yen exchange rate trends (polite form)",
            "target_time": 20
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        description = test_case["description"]
        target_time = test_case["target_time"]
        
        print(f"\n{BOLD}Test {i}: {description}{RESET}")
        print(f"Query: {query}")
        print(f"Target time: < {target_time}s")
        print("-" * 70)
        
        try:
            start_time = time.perf_counter()
            
            # Run web search
            result = perplexity_web_search(
                query=query,
                max_results=5,
                synthesize_answer=True,
                include_recent=True
            )
            
            duration = time.perf_counter() - start_time
            
            # Print results
            print_result(result)
            
            # Validation
            checks = {
                "Has answer": bool(result.get('answer')),
                "Has sources": len(result.get('sources', [])) > 0,
                "Has citations": len(result.get('citations', {})) > 0,
                f"Fast enough (< {target_time}s)": duration < target_time,
                "Answer has content": len(result.get('answer', '')) > 50
            }
            
            passed = sum(checks.values())
            total = len(checks)
            
            print(f"\n{BOLD}Validation: {passed}/{total}{RESET}")
            for check, status in checks.items():
                icon = f"{GREEN}✅{RESET}" if status else f"{RED}❌{RESET}"
                print(f"  {icon} {check}")
            
            # Check for Japanese characters in answer
            answer = result.get('answer', '')
            has_japanese = any('\u3040' <= char <= '\u30ff' or '\u4e00' <= char <= '\u9faf' for char in answer)
            
            if has_japanese:
                print(f"\n  {GREEN}✅ Answer contains Japanese characters{RESET}")
            else:
                print(f"\n  {YELLOW}⚠️  Answer is in English/mixed language{RESET}")
            
            results.append({
                "query": query,
                "description": description,
                "duration": duration,
                "passed": all(checks.values()),
                "has_japanese": has_japanese,
                "answer_length": len(answer),
                "sources_count": len(result.get('sources', []))
            })
            
            print(f"\n{GREEN if all(checks.values()) else YELLOW}Status: {'PASS' if all(checks.values()) else 'PARTIAL'}{RESET}")
            
        except Exception as e:
            print(f"\n{RED}❌ Error: {e}{RESET}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": query,
                "description": description,
                "duration": 0,
                "passed": False,
                "error": str(e)
            })
        
        if i < len(test_queries):
            print(f"\n{BLUE}{'='*70}{RESET}")
            await asyncio.sleep(2)  # Brief pause between tests
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    
    print(f"{BOLD}Results:{RESET}")
    for result in results:
        status = f"{GREEN}✅ PASS{RESET}" if result.get("passed") else f"{YELLOW}⚠️  PARTIAL{RESET}"
        desc = result["description"]
        duration = result.get("duration", 0)
        
        details = []
        if duration > 0:
            details.append(f"{duration:.2f}s")
        if result.get("has_japanese"):
            details.append("日本語")
        if result.get("sources_count"):
            details.append(f"{result['sources_count']} sources")
        
        detail_str = f" ({', '.join(details)})" if details else ""
        print(f"  {status} {desc}{detail_str}")
    
    print(f"\n{BOLD}Passed: {passed}/{total}{RESET}")
    
    # Japanese language support assessment
    japanese_answers = sum(1 for r in results if r.get("has_japanese"))
    
    print(f"\n{BOLD}Japanese Language Support:{RESET}")
    if japanese_answers == total:
        print(f"  {GREEN}✅ Excellent - All answers in Japanese{RESET}")
        grade = "A+"
    elif japanese_answers >= total * 0.7:
        print(f"  {GREEN}✅ Good - Most answers in Japanese ({japanese_answers}/{total}){RESET}")
        grade = "A"
    elif japanese_answers > 0:
        print(f"  {YELLOW}⚠️  Partial - Some answers in Japanese ({japanese_answers}/{total}){RESET}")
        grade = "B"
    else:
        print(f"  {YELLOW}⚠️  Limited - Answers in English{RESET}")
        print(f"  {BLUE}ℹ️  Note: English answers may still be accurate{RESET}")
        grade = "B-"
    
    print(f"\n{BOLD}Overall Grade: {grade}{RESET}")
    
    # Performance metrics
    durations = [r["duration"] for r in results if r.get("duration", 0) > 0]
    if durations:
        print(f"\n{BOLD}Performance Metrics:{RESET}")
        print(f"  Average time: {sum(durations)/len(durations):.2f}s")
        print(f"  Fastest: {min(durations):.2f}s")
        print(f"  Slowest: {max(durations):.2f}s")
    
    return passed == total


async def main():
    """Run all Japanese search tests."""
    print(f"Testing Japanese web search functionality...")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    success = await test_japanese_search()
    
    return 0 if success else 1


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
