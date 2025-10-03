#!/usr/bin/env python3
"""
Test script to verify web search speed optimizations.
Expected: <3s response time vs original 15-30s
"""

import asyncio
import time
import sys
from app.services.perplexity_web_search import get_perplexity_service, cleanup_perplexity_service

async def test_fast_search():
    """Test fast search performance."""
    print("=" * 80)
    print("Web Search Speed Test - Target: <3s")
    print("=" * 80)
    
    service = get_perplexity_service()
    
    test_queries = [
        "What are analysts saying about Tesla stock?",
        "Latest news on Apple earnings",
        "Microsoft AI developments 2025",
        "住信SBIネット銀行の最新情報",  # Japanese query test
    ]
    
    total_time = 0
    results_summary = []
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n[Test {idx}/{len(test_queries)}] Query: {query[:60]}{'...' if len(query) > 60 else ''}")
        print("-" * 80)
        
        start_time = time.perf_counter()
        
        try:
            response = await service.perplexity_search(
                query=query,
                max_results=8,
                synthesize_answer=False,  # No synthesis for pure search speed test
                include_recent=False
            )
            
            end_time = time.perf_counter()
            elapsed = end_time - start_time
            total_time += elapsed
            
            # Extract results
            result_count = len(response.sources) if response.sources else 0
            citations_count = len(response.citations) if response.citations else 0
            
            # Performance assessment
            if elapsed < 3.0:
                status = "✅ EXCELLENT"
                status_icon = "🚀"
            elif elapsed < 5.0:
                status = "✅ GOOD"
                status_icon = "⚡"
            elif elapsed < 10.0:
                status = "⚠️  ACCEPTABLE"
                status_icon = "⏱️"
            else:
                status = "❌ SLOW"
                status_icon = "🐢"
            
            print(f"{status_icon} Status: {status}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"📄 Results: {result_count} sources, {citations_count} citations")
            
            # Show timing breakdown
            print(f"\nTiming Breakdown:")
            print(f"  Search: {response.search_time:.2f}s")
            print(f"  Synthesis: {response.synthesis_time:.2f}s")
            print(f"  Total: {response.total_time:.2f}s")
            
            # Show top 3 sources
            if response.sources:
                print(f"\nTop Sources:")
                for i, source in enumerate(response.sources[:3], 1):
                    print(f"  [{i}] {source.title[:70]}{'...' if len(source.title) > 70 else ''}")
                    print(f"      URL: {source.url[:80]}")
                    print(f"      Source: {source.source}, Score: {source.combined_score:.3f}")
            
            results_summary.append({
                'query': query[:50],
                'time': elapsed,
                'results': result_count,
                'status': status
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results_summary.append({
                'query': query[:50],
                'time': 0,
                'results': 0,
                'status': "❌ ERROR"
            })
        
        # Small delay between tests
        if idx < len(test_queries):
            await asyncio.sleep(0.5)
    
    # Print summary
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    
    avg_time = total_time / len(test_queries) if test_queries else 0
    
    for result in results_summary:
        print(f"{result['status']:20} | {result['time']:6.2f}s | {result['results']:2} results | {result['query']}")
    
    print("-" * 80)
    print(f"Average Time: {avg_time:.2f}s")
    print(f"Total Time: {total_time:.2f}s")
    
    # Final verdict
    print("\n" + "=" * 80)
    if avg_time < 3.0:
        print("🎉 SUCCESS! Web search is ChatGPT/Perplexity speed!")
        print(f"   Average: {avg_time:.2f}s < 3.0s target")
    elif avg_time < 5.0:
        print("✅ GOOD! Close to target speed.")
        print(f"   Average: {avg_time:.2f}s (target: 3.0s)")
    else:
        print("⚠️  NEEDS IMPROVEMENT - Still slower than target")
        print(f"   Average: {avg_time:.2f}s (target: 3.0s)")
    print("=" * 80)
    
    # Cleanup
    await cleanup_perplexity_service()

if __name__ == "__main__":
    try:
        asyncio.run(test_fast_search())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
