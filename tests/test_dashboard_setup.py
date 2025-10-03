#!/usr/bin/env python3
"""
Quick test script to verify Dashboard setup
"""
import sys
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import finnhub
        print("✅ finnhub-python installed")
    except ImportError:
        print("❌ finnhub-python NOT installed")
        print("   Run: pip install finnhub-python")
        return False
    
    try:
        import websocket
        print("✅ websocket-client installed")
    except ImportError:
        print("❌ websocket-client NOT installed")
        print("   Run: pip install websocket-client")
        return False
    
    try:
        from app.services.finnhub_service import get_finnhub_service
        print("✅ finnhub_service module loads correctly")
    except Exception as e:
        print(f"❌ Error loading finnhub_service: {e}")
        return False
    
    try:
        from app.routers.dashboard import router
        print("✅ dashboard router loads correctly")
    except Exception as e:
        print(f"❌ Error loading dashboard router: {e}")
        return False
    
    return True

def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    
    from app.core.config import FINNHUB_API_KEY
    
    if not FINNHUB_API_KEY:
        print("⚠️  FINNHUB_API_KEY not set in environment")
        print("   Add to .env: FINNHUB_API_KEY=your_key_here")
        print("   Get free key at: https://finnhub.io/")
        return False
    elif FINNHUB_API_KEY.startswith("your_") or FINNHUB_API_KEY == "your_key_here":
        print("⚠️  FINNHUB_API_KEY is placeholder value")
        print("   Update .env with your actual API key")
        return False
    else:
        print(f"✅ FINNHUB_API_KEY configured ({FINNHUB_API_KEY[:10]}...)")
        return True

def test_finnhub_connection():
    """Test connection to Finnhub API."""
    print("\nTesting Finnhub API connection...")
    
    from app.core.config import FINNHUB_API_KEY
    
    if not FINNHUB_API_KEY or FINNHUB_API_KEY.startswith("your_"):
        print("⚠️  Skipping API test (no valid API key)")
        return False
    
    try:
        from app.services.finnhub_service import get_finnhub_quote
        
        print("   Fetching AAPL quote...")
        quote = get_finnhub_quote("AAPL", FINNHUB_API_KEY)
        
        if "error" in quote:
            print(f"❌ API Error: {quote['error']}")
            return False
        
        print(f"✅ Successfully fetched quote:")
        print(f"   Symbol: {quote.get('symbol')}")
        print(f"   Price: ${quote.get('current_price', 0):.2f}")
        print(f"   Change: {quote.get('change', 0):+.2f} ({quote.get('percent_change', 0):+.2f}%)")
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Dashboard Setup Verification")
    print("=" * 60)
    print()
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test config
    results.append(("Configuration", test_config()))
    
    # Test API connection (only if config is valid)
    if results[-1][1]:  # If config test passed
        results.append(("API Connection", test_finnhub_connection()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Dashboard is ready to use.")
        print("\nNext steps:")
        print("1. Start backend: uvicorn main:app --reload")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Access dashboard at http://localhost:5173")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
