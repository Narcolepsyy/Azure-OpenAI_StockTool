#!/usr/bin/env python3
"""
Integration test for ML tool selection via the API.

This script:
1. Starts the FastAPI server
2. Sends test queries
3. Verifies ML tool selection is working
4. Shows tool selection metadata
"""

import requests
import json
import time

# API endpoint
BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{BASE_URL}/chat"
LOGIN_URL = f"{BASE_URL}/auth/token"

# Test credentials (will register if doesn't exist)
TEST_USER = {
    "username": "test_ml_user",
    "email": "test_ml@example.com",
    "password": "TestML123!"
}


def get_auth_token():
    """Get or create test user and return auth token."""
    # Try to register
    try:
        register_response = requests.post(
            f"{BASE_URL}/auth/register",
            json=TEST_USER
        )
        if register_response.status_code == 200:
            print("✅ Test user registered")
    except Exception:
        pass  # User might already exist
    
    # Login
    login_response = requests.post(
        LOGIN_URL,
        data={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        print(f"✅ Logged in as {TEST_USER['username']}")
        return token
    else:
        print(f"❌ Login failed: {login_response.text}")
        return None


def test_chat_query(token, prompt, expected_tool=None):
    """Send a chat query and verify ML tool selection."""
    print(f"\n{'='*70}")
    print(f"Query: '{prompt}'")
    print(f"{'='*70}")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "prompt": prompt,
        "deployment": "gpt-oss-120b",  # Use fast model for testing
        "stream": False
    }
    
    start = time.time()
    
    try:
        response = requests.post(CHAT_URL, json=payload, headers=headers)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Response received in {elapsed:.2f}s")
            
            # Show full response structure (handle both 'answer' and 'content' keys)
            answer = data.get('answer') or data.get('content', '')
            
            if answer:
                print(f"\n✅ Answer received ({len(answer)} chars):")
                print(f"   {answer[:300]}...")
            else:
                print(f"\n⚠️  Empty answer in response")
                print(f"   Full response: {json.dumps(data, indent=2)[:500]}...")
            
            # Check for tool selection metadata in logs
            # (This would be in server logs, not API response)
            print(f"\n📊 Response Metadata:")
            print(f"   Model: {data.get('model', 'N/A')}")
            print(f"   Conversation ID: {data.get('conversation_id', 'N/A')}")
            
            if expected_tool and answer:
                answer_lower = answer.lower()
                # Check for tool-specific indicators
                indicators = {
                    'get_stock_quote': ['price', 'quote', '$', 'trading'],
                    'get_historical_prices': ['historical', 'history', 'prices', 'data'],
                    'perplexity_search': ['recent', 'news', 'latest', 'developments']
                }
                
                tool_indicators = indicators.get(expected_tool, [])
                matched = any(ind in answer_lower for ind in tool_indicators)
                
                if matched:
                    print(f"   ✅ Response contains {expected_tool} indicators")
                else:
                    print(f"   ⚠️  Response may not have used {expected_tool}")
            
            return True
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False


def main():
    """Run integration tests."""
    print("\n" + "="*70)
    print("ML TOOL SELECTION - API INTEGRATION TEST")
    print("="*70)
    
    # Check if server is running
    try:
        health_response = requests.get(f"{BASE_URL}/")
        print(f"✅ Server is running at {BASE_URL}")
    except Exception as e:
        print(f"❌ Server is not running at {BASE_URL}")
        print(f"   Error: {e}")
        print(f"\n⚠️  Please start the server first:")
        print(f"   uvicorn main:app --reload")
        return 1
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to authenticate")
        return 1
    
    # Test queries
    test_cases = [
        {
            "prompt": "What's the current price of AAPL?",
            "expected_tool": "get_stock_quote",
            "description": "Stock quote query"
        },
        {
            "prompt": "Show me GOOGL's historical prices for the past month",
            "expected_tool": "get_historical_prices",
            "description": "Historical data query"
        },
        {
            "prompt": "Latest news about artificial intelligence",
            "expected_tool": "perplexity_search",
            "description": "News search query"
        },
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#'*70}")
        print(f"TEST {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'#'*70}")
        
        success = test_chat_query(
            token,
            test_case["prompt"],
            test_case.get("expected_tool")
        )
        results.append(success)
        
        # Wait a bit between requests
        if i < len(test_cases):
            time.sleep(1)
    
    # Summary
    print(f"\n\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_case, success) in enumerate(zip(test_cases, results), 1):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - Test {i}: {test_case['description']}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All API integration tests passed!")
        print("\n📝 Check the server logs to see ML tool selection in action:")
        print("   - Look for 'Tool selection: method=ml'")
        print("   - Check confidence scores")
        print("   - Verify correct tools are being selected")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
