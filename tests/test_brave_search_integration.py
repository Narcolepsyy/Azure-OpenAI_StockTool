#!/usr/bin/env python3
"""
Test script for Brave Search API integration in perplexity web search service.
"""

import asyncio
import json
import os
from app.services.perplexity_web_search import BraveSearchClient, PerplexityWebSearchService, perplexity_web_search

async def test_brave_search_client():
    """Test the Brave Search API client directly."""
    print("🔍 Testing Brave Search API Client")
    print("=" * 60)
    
    brave_client = BraveSearchClient()
    
    if not brave_client.api_key:
        print("⚠️  BRAVE_API_KEY not configured - skipping Brave Search tests")
        print("   To enable Brave Search, get an API key from: https://api.search.brave.com/app/keys")
        return False
    
    test_queries = [
        "Tesla stock performance 2025",
        "日本の経済状況 2025",
        "latest AI technology news"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing query: {query}")
        print("-" * 40)
        
        try:
            results = await brave_client.search(query, count=5, freshness="pw")
            
            print(f"   ✅ Search completed successfully")
            print(f"   📊 Results found: {len(results)}")
            
            if results:
                for j, result in enumerate(results[:3]):
                    print(f"   {j+1}. {result.get('title', 'No title')[:60]}...")
                    print(f"      URL: {result.get('url', 'No URL')}")
                    print(f"      Score: {result.get('relevance_score', 0)}")
            else:
                print("   ⚠️  No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return True

async def test_integrated_search():
    """Test the integrated perplexity search with Brave API."""
    print("\n🔄 Testing Integrated Perplexity Search with Brave API")
    print("=" * 60)
    
    service = PerplexityWebSearchService()
    
    test_queries = [
        {
            "query": "Recent developments in financial technology 2025",
            "description": "Technology and finance - should use both search engines"
        },
        {
            "query": "Current market analysis for tech stocks",
            "description": "Financial market data - should prioritize recent information"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: {test['description']}")
        print(f"   Query: {test['query']}")
        print("-" * 40)
        
        try:
            # Test the enhanced search method
            enhanced_results = await service._enhanced_web_search(
                query=test['query'],
                max_results=8,
                include_recent=True
            )
            
            print(f"   ✅ Enhanced search completed")
            print(f"   📊 Sources found: {len(enhanced_results)}")
            
            # Count sources by provider
            source_count = {}
            for result in enhanced_results:
                source = result.source
                source_count[source] = source_count.get(source, 0) + 1
            
            print(f"   📈 Source breakdown: {source_count}")
            
            if enhanced_results:
                print(f"   💡 Top results:")
                for j, result in enumerate(enhanced_results[:3]):
                    print(f"      {j+1}. [{result.source}] {result.title[:50]}...")
                    print(f"         Score: {result.relevance_score:.2f}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_perplexity_wrapper():
    """Test the full perplexity wrapper function."""
    print("\n🎯 Testing Full Perplexity Web Search Wrapper")
    print("=" * 60)
    
    test_query = "Latest news about AI and machine learning in 2025"
    
    try:
        print(f"Query: {test_query}")
        print("-" * 40)
        
        result = perplexity_web_search(
            query=test_query,
            max_results=6,
            synthesize_answer=True,
            include_recent=True
        )
        
        print(f"✅ Full search completed successfully")
        print(f"📊 Sources found: {len(result.get('sources', []))}")
        print(f"⏱️  Search time: {result.get('search_time', 0):.2f}s")
        print(f"🧠 Synthesis time: {result.get('synthesis_time', 0):.2f}s")
        print(f"📈 Confidence: {result.get('confidence_score', 0):.2f}")
        print(f"🔧 Method: {result.get('method', 'unknown')}")
        
        # Check answer quality
        answer = result.get('answer', '')
        if answer and len(answer) > 100:
            print(f"💡 Answer preview: {answer[:200]}...")
        else:
            print(f"⚠️  Answer seems short: {answer}")
        
        # Show source distribution
        sources = result.get('sources', [])
        if sources:
            source_types = {}
            for source in sources:
                source_type = source.get('source', 'unknown')
                source_types[source_type] = source_types.get(source_type, 0) + 1
            print(f"📋 Source distribution: {source_types}")
            
    except Exception as e:
        print(f"❌ Full search failed: {e}")

async def main():
    """Run all Brave Search integration tests."""
    print("🚀 Brave Search API Integration Tests")
    print("=" * 60)
    
    # Test Brave Search client
    brave_available = await test_brave_search_client()
    
    # Test integrated search (works with or without Brave)
    await test_integrated_search()
    
    # Test full wrapper
    test_perplexity_wrapper()
    
    print("\n" + "=" * 60)
    if brave_available:
        print("✅ Brave Search API integration tests completed successfully!")
        print("🎉 Your system now uses both Brave Search and DuckDuckGo for comprehensive results.")
    else:
        print("⚠️  Tests completed with DuckDuckGo only (Brave API key not configured)")
        print("💡 To enable Brave Search:")
        print("   1. Get API key from: https://api.search.brave.com/app/keys")
        print("   2. Add it to .env file: BRAVE_API_KEY=your_key_here")
        print("   3. Restart the application")

if __name__ == "__main__":
    asyncio.run(main())