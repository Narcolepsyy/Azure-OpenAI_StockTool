#!/usr/bin/env python3
"""
Test the simplified Brave Search implementation with country parameter
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

async def test_simple_brave_search():
    """Test simplified Brave Search with different countries"""
    
    test_cases = [
        {
            "query": "Tesla stock price",
            "country": None,  # Global search
            "description": "Global search for Tesla stock"
        },
        {
            "query": "Tesla stock price", 
            "country": "US",
            "description": "US-specific search for Tesla stock"
        },
        {
            "query": "Microsoft earnings",
            "country": "GB", 
            "description": "UK-specific search for Microsoft earnings"
        },
        {
            "query": "Apple financial results",
            "country": "JP",
            "description": "Japan-specific search for Apple"
        }
    ]
    
    print("🚀 Testing Simplified Brave Search with Country Parameter")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        country = test_case["country"]
        description = test_case["description"]
        
        print(f"\n{i}. {description}")
        print(f"   Query: '{query}'")
        print(f"   Country: {country or 'Global'}")
        print("-" * 40)
        
        try:
            results = await simple_brave_search(
                query=query,
                count=5,
                country=country
            )
            
            if results:
                print(f"✅ Success! Retrieved {len(results)} results")
                for j, result in enumerate(results[:3], 1):  # Show first 3
                    print(f"   {j}. {result['title']}")
                    print(f"      URL: {result['url']}")
                    if result.get('description'):
                        desc = result['description'][:100] + "..." if len(result['description']) > 100 else result['description']
                        print(f"      Desc: {desc}")
                    print()
            else:
                print("❌ No results returned")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Test failed for {description}: {e}")

if __name__ == "__main__":
    print("Testing Simplified Brave Search Implementation")
    asyncio.run(test_simple_brave_search())