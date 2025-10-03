#!/usr/bin/env python3
"""Test script for web search functionality."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.perplexity_web_search import perplexity_web_search
from app.services.enhanced_rag_service import augmented_rag_search, financial_context_search

def test_web_search():
    """Test basic web search functionality."""
    print("Testing perplexity web search...")
    
    try:
        results = perplexity_web_search("Apple stock price 2024", max_results=3, synthesize_answer=False)
        print(f"✓ Perplexity web search returned {len(results['sources'])} results")
        if results['sources']:
            print(f"  First result: {results['sources'][0]['title']}")
            print(f"  URL: {results['sources'][0]['url']}")
            print(f"  Source: {results['sources'][0].get('source', 'unknown')}")
        
    except Exception as e:
        print(f"✗ Web search failed: {e}")
        return False
    
    return True

def test_news_search():
    """Test news search functionality."""
    print("\nTesting news search with perplexity...")
    
    try:
        results = perplexity_web_search("AAPL earnings news", max_results=3, include_recent=True, synthesize_answer=False)
        print(f"✓ News search returned {len(results['sources'])} results")
        if results['sources']:
            print(f"  First result: {results['sources'][0]['title']}")
    except Exception as e:
        print(f"✗ News search failed: {e}")
        return False
    
    return True

def test_augmented_rag():
    """Test augmented RAG functionality."""
    print("\nTesting augmented RAG search...")
    
    try:
        results = augmented_rag_search(
            "what is technical analysis", 
            kb_k=2, 
            web_results=2, 
            include_web=True
        )
        print(f"✓ Augmented RAG returned {results['total_chunks']} total chunks")
        print(f"  KB results: {results['sources']['knowledge_base']['count']}")
        print(f"  Web results: {results['sources']['web_search']['count']}")
    except Exception as e:
        print(f"✗ Augmented RAG failed: {e}")
        return False
    
    return True

def test_financial_context():
    """Test financial context search."""
    print("\nTesting financial context search...")
    
    try:
        results = financial_context_search(
            "Apple earnings analysis", 
            symbol="AAPL",
            include_news=True
        )
        print(f"✓ Financial context search returned {results['total_chunks']} chunks")
        if 'recent_news' in results['sources']:
            print(f"  Recent news: {results['sources']['recent_news']['count']} items")
    except Exception as e:
        print(f"✗ Financial context search failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing Web Search Integration\n" + "="*40)
    
    tests = [
        test_web_search,
        test_news_search,
        test_augmented_rag,
        test_financial_context
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test_func.__name__} crashed: {e}")
    
    print(f"\n{'='*40}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Web search integration is working.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1)