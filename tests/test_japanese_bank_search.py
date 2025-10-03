#!/usr/bin/env python3
"""
Test Japanese bank integration news search using simplified Brave Search
"""
import asyncio
import logging
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from app.services.simple_brave_search import simple_brave_search

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_japanese_bank_search():
    """Test search for Japanese bank integration news"""
    
    query = "八十二銀行と長野銀行の統合関連ニュース"
    
    print("🏦 Testing Japanese Bank Integration News Search")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"Translation: Hachijuni Bank and Nagano Bank integration news")
    print("-" * 60)
    
    try:
        # Test with Japan country parameter
        print("\n1. Japan-specific search (JP):")
        jp_results = await simple_brave_search(
            query=query,
            count=8,
            country="JP"
        )
        
        if jp_results:
            print(f"✅ Success! Retrieved {len(jp_results)} Japan-specific results")
            for i, result in enumerate(jp_results, 1):
                print(f"\n   {i}. {result['title']}")
                print(f"      URL: {result['url']}")
                if result.get('description'):
                    desc = result['description'][:150] + "..." if len(result['description']) > 150 else result['description']
                    print(f"      Description: {desc}")
        else:
            print("❌ No Japan-specific results returned")
        
        # Wait between requests for rate limiting
        print("\n⏳ Waiting 2 seconds for rate limiting...")
        await asyncio.sleep(2)
        
        # Test with global search
        print("\n2. Global search:")
        global_results = await simple_brave_search(
            query=query,
            count=8,
            country=None
        )
        
        if global_results:
            print(f"✅ Success! Retrieved {len(global_results)} global results")
            for i, result in enumerate(global_results, 1):
                print(f"\n   {i}. {result['title']}")
                print(f"      URL: {result['url']}")
                if result.get('description'):
                    desc = result['description'][:150] + "..." if len(result['description']) > 150 else result['description']
                    print(f"      Description: {desc}")
        else:
            print("❌ No global results returned")
        
        # Analysis
        print("\n" + "=" * 60)
        print("📊 Analysis:")
        
        if jp_results and global_results:
            jp_domains = set(result['url'].split('/')[2] for result in jp_results)
            global_domains = set(result['url'].split('/')[2] for result in global_results)
            
            print(f"   Japan-specific domains: {jp_domains}")
            print(f"   Global search domains: {global_domains}")
            print(f"   Unique to JP search: {jp_domains - global_domains}")
            print(f"   Common domains: {jp_domains & global_domains}")
        
        elif jp_results:
            print(f"   Only Japan search worked: {len(jp_results)} results")
        elif global_results:
            print(f"   Only global search worked: {len(global_results)} results")
        else:
            print("   Both searches failed - possibly rate limited or API issue")

    except Exception as e:
        print(f"❌ Error during search: {e}")
        logger.error(f"Japanese bank search failed: {e}")

if __name__ == "__main__":
    print("Testing Japanese Bank Integration News Search")
    asyncio.run(test_japanese_bank_search())