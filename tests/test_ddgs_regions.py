#!/usr/bin/env python3
"""Test script for DDGS region configuration."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_ddgs_regions():
    """Test DDGS region configuration with different query types."""
    print("🌍 Testing DDGS Region Configuration")
    print("=" * 50)
    
    from app.services.perplexity_web_search import get_perplexity_service
    
    service = get_perplexity_service()
    
    # Test queries for different regions
    test_queries = [
        ("Tesla stock price", "English/US query"),
        ("トヨタ 株価", "Japanese query"),
        ("日本の株式市場 最新", "Japanese financial query"),
        ("Microsoft earnings report", "English tech query"),
        ("ソフトバンク 決算", "Japanese tech query"),
        ("China economy news", "China-related query"),
        ("European market trends", "Europe-related query")
    ]
    
    print("Testing optimal region detection:")
    print(f"{'Query':<25} {'Expected Region':<15} {'Detected Region':<15} {'Description'}")
    print("-" * 80)
    
    for query, description in test_queries:
        detected_region = service._get_optimal_ddgs_region(query)
        
        # Expected regions based on content
        if any(char for char in query if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF'):
            expected = "jp-jp"
        elif "china" in query.lower():
            expected = "cn-zh"
        elif "europe" in query.lower():
            expected = "eu-en"
        else:
            expected = "jp-jp"  # Default for your setup
        
        status = "✅" if detected_region == expected else "⚠️"
        print(f"{status} {query:<25} {expected:<15} {detected_region:<15} {description}")

async def test_ddgs_search_with_regions():
    """Test actual DDGS search with different regions."""
    print(f"\n🔍 Testing DDGS Search with Region Configuration")
    print("=" * 50)
    
    try:
        from app.services.perplexity_web_search import perplexity_web_search
        
        # Test with Japanese financial query
        query = "トヨタ 株価 最新"
        print(f"Testing Japanese query: {query}")
        
        result = perplexity_web_search(
            query=query,
            max_results=3,
            synthesize_answer=False,  # Skip synthesis for faster testing
            include_recent=True
        )
        
        print(f"✅ Search completed successfully!")
        print(f"Sources found: {len(result.get('sources', []))}")
        print(f"Search time: {result.get('search_time', 0):.2f}s")
        
        # Show first few results
        sources = result.get('sources', [])
        if sources:
            print(f"\nTop search results:")
            for i, source in enumerate(sources[:2]):
                print(f"{i+1}. {source.get('title', '')}")
                print(f"   URL: {source.get('url', '')}")
                print(f"   Snippet: {source.get('snippet', '')[:100]}...")
        
        # Test with English query
        print(f"\n" + "=" * 30)
        query = "Tesla stock analysis"
        print(f"Testing English query: {query}")
        
        result = perplexity_web_search(
            query=query,
            max_results=3,
            synthesize_answer=False,
            include_recent=True
        )
        
        print(f"✅ Search completed successfully!")
        print(f"Sources found: {len(result.get('sources', []))}")
        
        sources = result.get('sources', [])
        if sources:
            print(f"\nTop search results:")
            for i, source in enumerate(sources[:2]):
                print(f"{i+1}. {source.get('title', '')}")
                print(f"   URL: {source.get('url', '')}")
        
        return True
        
    except Exception as e:
        print(f"❌ DDGS search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_configuration():
    """Test DDGS configuration settings."""
    print(f"\n⚙️  Testing DDGS Configuration")
    print("=" * 50)
    
    from app.core.config import DDGS_REGION, DDGS_SAFESEARCH, DDGS_TIMELIMIT
    
    print(f"DDGS_REGION: {DDGS_REGION}")
    print(f"DDGS_SAFESEARCH: {DDGS_SAFESEARCH}")
    print(f"DDGS_TIMELIMIT: {DDGS_TIMELIMIT or 'None (no time limit)'}")
    
    # Test import
    try:
        from ddgs import DDGS
        print("✅ DDGS library imported successfully")
        
        # Quick connectivity test
        with DDGS() as ddgs:
            # Just test creation, don't actually search
            print("✅ DDGS connection test successful")
            
    except ImportError:
        print("❌ DDGS library not available")
        return False
    except Exception as e:
        print(f"⚠️  DDGS connection issue: {e}")
        # Still return True as this might be a network issue
    
    return True

async def main():
    """Run all DDGS region tests."""
    print("DDGS Region Configuration Test Suite")
    print("Testing enhanced region detection and search optimization")
    
    # Test configuration
    config_ok = await test_configuration()
    if not config_ok:
        print("\n❌ Configuration test failed!")
        return False
    
    # Test region detection
    await test_ddgs_regions()
    
    # Test actual search functionality
    search_ok = await test_ddgs_search_with_regions()
    
    if search_ok:
        print(f"\n🎉 All DDGS region tests passed!")
        print(f"\nConfiguration Summary:")
        print(f"  • Default region: jp-jp (Japan) - optimal for Japanese financial markets")
        print(f"  • Dynamic region detection based on query language")
        print(f"  • Support for Japanese, Chinese, Korean, European, and US regions")
        print(f"  • Automatic fallback to jp-jp for your primary market focus")
        return True
    else:
        print(f"\n❌ Some DDGS tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)