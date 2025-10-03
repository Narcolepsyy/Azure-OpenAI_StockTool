#!/usr/bin/env python3
"""Test script for enhanced Perplexity web search with BM25, embeddings, and GPT OSS 120B."""

import asyncio
import sys
import json
from typing import Dict, Any
from app.services.perplexity_web_search import get_perplexity_service, PerplexityWebSearchService
from app.core.config import (
    AZURE_OPENAI_DEPLOYMENT_OSS_120B,
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
    AZURE_OPENAI_API_KEY
)

async def test_enhanced_search(query: str, test_name: str = "Test") -> Dict[str, Any]:
    """Test enhanced search with detailed scoring breakdown."""
    print(f"\n{'='*60}")
    print(f"{test_name}: {query}")
    print(f"{'='*60}")
    
    try:
        service = get_perplexity_service()
        response = await service.perplexity_search(
            query=query,
            max_results=5,
            synthesize_answer=True,
            include_recent=True
        )
        
        print(f"\nQuery: {response.query}")
        print(f"Confidence Score: {response.confidence_score:.3f}")
        print(f"Search Time: {response.search_time:.2f}s")
        print(f"Synthesis Time: {response.synthesis_time:.2f}s")
        print(f"Total Time: {response.total_time:.2f}s")
        
        print(f"\nSynthesized Answer:")
        print(f"{response.answer}")
        
        print(f"\nSearch Results Ranking:")
        print(f"{'#':<3} {'Title':<40} {'BM25':<6} {'Semantic':<8} {'Combined':<8} {'Citations'}")
        print("-" * 80)
        
        for i, source in enumerate(response.sources):
            citations = [f"[{cit_id}]" for cit_id, cit_text in response.citations.items() if source.title in cit_text]
            citation_str = "".join(citations) if citations else ""
            
            print(f"{i+1:<3} {source.title[:40]:<40} {source.bm25_score:.3f}  {source.semantic_score:.3f}   {source.combined_score:.3f}   {citation_str}")
        
        print(f"\nCitations:")
        for cit_id, cit_text in response.citations.items():
            print(f"[{cit_id}] {cit_text}")
        
        return {
            "success": True,
            "query": query,
            "num_sources": len(response.sources),
            "has_answer": bool(response.answer),
            "confidence": response.confidence_score,
            "total_time": response.total_time,
            "avg_combined_score": sum(s.combined_score for s in response.sources) / len(response.sources) if response.sources else 0
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

async def test_configuration():
    """Test Azure configuration and dependencies."""
    print("🔧 Testing Configuration...")
    
    # Check Azure GPT OSS 120B
    if AZURE_OPENAI_DEPLOYMENT_OSS_120B and AZURE_OPENAI_API_KEY:
        print(f"✅ Azure GPT OSS 120B: {AZURE_OPENAI_DEPLOYMENT_OSS_120B}")
    else:
        print("❌ Azure GPT OSS 120B not configured")
    
    # Check Azure Embeddings
    if AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT and AZURE_OPENAI_API_KEY:
        print(f"✅ Azure Embeddings: {AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT}")
    else:
        print("❌ Azure Embeddings not configured")
    
    # Test dependencies
    try:
        from rank_bm25 import BM25Okapi
        print("✅ rank-bm25 imported successfully")
    except ImportError as e:
        print(f"❌ rank-bm25 import failed: {e}")
    
    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        print("✅ scikit-learn and numpy imported successfully")
    except ImportError as e:
        print(f"❌ scikit-learn/numpy import failed: {e}")

async def run_comprehensive_tests():
    """Run comprehensive test suite."""
    print("🚀 Enhanced Perplexity Search Test Suite")
    print("Testing BM25 + Semantic Embeddings + GPT OSS 120B")
    
    await test_configuration()
    
    # Test queries covering different scenarios
    test_queries = [
        ("Tesla stock price today", "Financial Query - Simple"),
        ("Microsoft Azure AI services latest features", "Technology Query - Complex"),
        ("日本の金融市場の最新動向", "Japanese Financial Query"),
        ("Climate change impact on renewable energy stocks", "Analytical Query"),
        ("What is artificial intelligence", "General Knowledge Query")
    ]
    
    results = []
    
    for query, test_name in test_queries:
        result = await test_enhanced_search(query, test_name)
        results.append(result)
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    successful_tests = [r for r in results if r.get("success")]
    failed_tests = [r for r in results if not r.get("success")]
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if successful_tests:
        avg_time = sum(r.get("total_time", 0) for r in successful_tests) / len(successful_tests)
        avg_confidence = sum(r.get("confidence", 0) for r in successful_tests) / len(successful_tests)
        avg_sources = sum(r.get("num_sources", 0) for r in successful_tests) / len(successful_tests)
        
        print(f"\nPerformance Metrics:")
        print(f"  Average Response Time: {avg_time:.2f}s")
        print(f"  Average Confidence: {avg_confidence:.3f}")
        print(f"  Average Sources: {avg_sources:.1f}")
    
    if failed_tests:
        print(f"\nFailed Tests:")
        for test in failed_tests:
            print(f"  - {test['query']}: {test.get('error', 'Unknown error')}")
    
    return len(successful_tests) == len(results)

async def test_ranking_comparison():
    """Test to show ranking improvement with BM25 + semantic scoring."""
    print(f"\n{'='*60}")
    print("RANKING COMPARISON TEST")
    print(f"{'='*60}")
    
    query = "OpenAI GPT-4 artificial intelligence capabilities"
    
    try:
        service = get_perplexity_service()
        
        # Get search results
        response = await service.perplexity_search(
            query=query,
            max_results=6,
            synthesize_answer=False,  # Skip synthesis for ranking focus
            include_recent=True
        )
        
        print(f"Query: {query}")
        print(f"Results: {len(response.sources)}")
        
        print(f"\nDetailed Ranking Breakdown:")
        print(f"{'Rank':<4} {'Original':<8} {'BM25':<8} {'Semantic':<8} {'Combined':<8} {'Title'}")
        print("-" * 85)
        
        for i, source in enumerate(response.sources):
            print(f"{i+1:<4} {source.relevance_score:.3f}    {source.bm25_score:.3f}   {source.semantic_score:.3f}   {source.combined_score:.3f}   {source.title[:40]}")
        
        # Show score distribution
        bm25_scores = [s.bm25_score for s in response.sources]
        semantic_scores = [s.semantic_score for s in response.sources]
        combined_scores = [s.combined_score for s in response.sources]
        
        print(f"\nScore Statistics:")
        print(f"  BM25 Range: {min(bm25_scores):.3f} - {max(bm25_scores):.3f}")
        print(f"  Semantic Range: {min(semantic_scores):.3f} - {max(semantic_scores):.3f}")
        print(f"  Combined Range: {min(combined_scores):.3f} - {max(combined_scores):.3f}")
        
    except Exception as e:
        print(f"❌ Ranking comparison failed: {e}")

if __name__ == "__main__":
    async def main():
        print("Enhanced Perplexity Search - BM25 + Embeddings + GPT OSS 120B")
        
        # Run comprehensive tests
        success = await run_comprehensive_tests()
        
        # Run ranking comparison
        await test_ranking_comparison()
        
        if success:
            print("\n🎉 All tests passed! Enhanced search is working correctly.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Check configuration and logs.")
            sys.exit(1)
    
    asyncio.run(main())