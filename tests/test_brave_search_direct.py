#!/usr/bin/env python3
"""
Direct test of Brave Search API to diagnose why it's not returning results.
"""

import asyncio
import aiohttp
import json
import os
import sys
from urllib.parse import urlencode
import time

# Load .env file to get environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Successfully loaded .env file")
except ImportError:
    print("❌ python-dotenv not available, .env file will not be loaded")

# Brave Search configuration
BRAVE_API_BASE_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

async def test_brave_search_direct():
    """Test Brave Search API directly with minimal parameters."""
    print("=== Testing Brave Search API Directly ===")
    print(f"API Key available: {'Yes' if BRAVE_API_KEY else 'No'}")
    print(f"API Key length: {len(BRAVE_API_KEY) if BRAVE_API_KEY else 0}")
    print(f"API Base URL: {BRAVE_API_BASE_URL}")
    
    if not BRAVE_API_KEY:
        print("❌ BRAVE_API_KEY not found in environment variables")
        return
    
    # Test queries
    test_queries = [
        "Tesla stock news",
        "Bitcoin price",
        "Microsoft earnings",
        "八十二銀行と長野銀行の統合"  # Japanese banking query
    ]
    
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': BRAVE_API_KEY,
        'User-Agent': 'Mozilla/5.0 (compatible; BraveSearchClient/1.0)'
    }
    
    timeout = aiohttp.ClientTimeout(total=15, connect=5)
    
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test {i}: '{query}' ---")
            
            # Build minimal parameters
            params = {
                'q': query,
                'count': 5,
                'safesearch': 'moderate',
                'textDecorations': 'false'
            }
            
            print(f"Request URL: {BRAVE_API_BASE_URL}")
            print(f"Parameters: {params}")
            print(f"Headers: {dict(headers)}")
            
            try:
                start_time = time.time()
                
                async with session.get(BRAVE_API_BASE_URL, params=params) as response:
                    elapsed = time.time() - start_time
                    print(f"Response status: {response.status}")
                    print(f"Response time: {elapsed:.2f}s")
                    print(f"Response headers: {dict(response.headers)}")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print("✅ Successfully got JSON response")
                            
                            # Analyze response structure
                            print(f"Response keys: {list(data.keys())}")
                            
                            if 'web' in data:
                                web_data = data['web']
                                print(f"Web data keys: {list(web_data.keys())}")
                                
                                if 'results' in web_data:
                                    results = web_data['results']
                                    print(f"Number of results: {len(results)}")
                                    
                                    if results:
                                        print("Sample result:")
                                        sample = results[0]
                                        for key, value in sample.items():
                                            if isinstance(value, str) and len(value) > 100:
                                                print(f"  {key}: {value[:100]}...")
                                            else:
                                                print(f"  {key}: {value}")
                                    else:
                                        print("⚠️  Results array is empty")
                                else:
                                    print("❌ No 'results' key in web data")
                            else:
                                print("❌ No 'web' key in response")
                                print(f"Full response: {json.dumps(data, indent=2)[:500]}...")
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON decode error: {e}")
                            text = await response.text()
                            print(f"Raw response: {text[:300]}...")
                            
                    elif response.status == 401:
                        print("❌ Unauthorized - API key may be invalid")
                        text = await response.text()
                        print(f"Error response: {text}")
                        
                    elif response.status == 422:
                        print("❌ Parameter validation error")
                        text = await response.text()
                        print(f"Error response: {text}")
                        
                    elif response.status == 429:
                        print("❌ Rate limit exceeded")
                        text = await response.text()
                        print(f"Error response: {text}")
                        
                    else:
                        print(f"❌ Unexpected status code: {response.status}")
                        text = await response.text()
                        print(f"Error response: {text[:300]}...")
                
            except asyncio.TimeoutError:
                print("❌ Request timed out")
            except Exception as e:
                print(f"❌ Request failed: {type(e).__name__}: {e}")
            
            # Rate limiting - wait 1 second between requests
            if i < len(test_queries):
                print("⏳ Waiting 1s for rate limiting...")
                await asyncio.sleep(1)

async def test_brave_minimal():
    """Test with absolute minimal parameters."""
    print("\n=== Testing with Minimal Parameters ===")
    
    if not BRAVE_API_KEY:
        print("❌ BRAVE_API_KEY not found")
        return
    
    headers = {
        'X-Subscription-Token': BRAVE_API_KEY
    }
    
    params = {
        'q': 'test query'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BRAVE_API_BASE_URL, params=params, headers=headers) as response:
                print(f"Minimal test status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    results_count = len(data.get('web', {}).get('results', []))
                    print(f"✅ Minimal test successful: {results_count} results")
                else:
                    text = await response.text()
                    print(f"❌ Minimal test failed: {text[:200]}...")
                    
        except Exception as e:
            print(f"❌ Minimal test error: {e}")

async def main():
    """Run all Brave Search tests."""
    await test_brave_search_direct()
    await test_brave_minimal()
    
    print("\n=== Summary ===")
    print("If you see empty results arrays, possible causes:")
    print("1. API key may be invalid or expired")
    print("2. Account may have exceeded quota")
    print("3. Brave API may be having issues")
    print("4. Query parameters may be incorrect")
    print("5. Network/firewall issues")

if __name__ == "__main__":
    asyncio.run(main())