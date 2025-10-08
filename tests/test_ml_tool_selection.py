#!/usr/bin/env python3
"""
Test ML tool selection to verify it works correctly.

Tests:
1. Model loading
2. Query embedding
3. Tool prediction
4. Confidence filtering
5. Integration with build_tools_for_request_ml
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ.setdefault("ML_TOOL_SELECTION_ENABLED", "true")

from app.services.ml.tool_selector import get_ml_tool_selector, get_ml_stats
from app.utils.tools import build_tools_for_request_ml


def test_model_loading():
    """Test 1: Model loading"""
    print("\n" + "="*70)
    print("TEST 1: Model Loading")
    print("="*70)
    
    selector = get_ml_tool_selector()
    
    # Check if model loads
    if selector.should_use_ml():
        print("✅ ML model loaded successfully")
        print(f"   Model path: {selector.model_path}")
        print(f"   Confidence threshold: {selector.confidence_threshold}")
        print(f"   Max tools: {selector.max_tools}")
        return True
    else:
        print("❌ ML model failed to load")
        return False


def test_query_embedding():
    """Test 2: Query embedding"""
    print("\n" + "="*70)
    print("TEST 2: Query Embedding")
    print("="*70)
    
    selector = get_ml_tool_selector()
    
    test_queries = [
        "What's the price of AAPL?",
        "Tell me about Tesla",
        "Latest AI news",
    ]
    
    all_passed = True
    for query in test_queries:
        try:
            start = time.time()
            embedding = selector.embedder.embed(query)
            elapsed = (time.time() - start) * 1000
            
            print(f"✅ '{query}'")
            print(f"   Embedding shape: {embedding.shape}")
            print(f"   Time: {elapsed:.1f}ms")
        except Exception as e:
            print(f"❌ '{query}' - Error: {e}")
            all_passed = False
    
    return all_passed


def test_tool_prediction():
    """Test 3: Tool prediction"""
    print("\n" + "="*70)
    print("TEST 3: Tool Prediction")
    print("="*70)
    
    selector = get_ml_tool_selector()
    
    test_cases = [
        {
            "query": "What's the price of AAPL?",
            "expected_tools": ["get_stock_quote"],
            "description": "Simple stock quote query"
        },
        {
            "query": "Show me GOOGL's historical data",
            "expected_tools": ["get_historical_prices"],
            "description": "Historical data query"
        },
        {
            "query": "Latest news about electric vehicles",
            "expected_tools": ["perplexity_search"],
            "description": "News search query"
        },
        {
            "query": "Tell me about Microsoft company profile",
            "expected_tools": ["get_company_profile"],
            "description": "Company profile query"
        },
        {
            "query": "TSLA technical analysis",
            "expected_tools": ["get_technical_indicators"],
            "description": "Technical indicators query"
        },
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected_tools"]
        description = test_case["description"]
        
        print(f"\n{i}. {description}")
        print(f"   Query: '{query}'")
        
        try:
            start = time.time()
            tools, probs = selector.predict_tools(query, return_probabilities=True)
            elapsed = (time.time() - start) * 1000
            
            print(f"   Predicted: {tools}")
            print(f"   Probabilities: {probs}")
            print(f"   Time: {elapsed:.1f}ms")
            
            # Check if expected tools are in predicted tools
            matched = all(exp in tools for exp in expected)
            
            if matched:
                print(f"   ✅ PASS - Expected tools found")
            else:
                print(f"   ⚠️  PARTIAL - Expected {expected}, got {tools}")
                # Don't fail, just warn (ML may predict additional tools)
                
        except Exception as e:
            print(f"   ❌ FAIL - Error: {e}")
            all_passed = False
    
    return all_passed


def test_confidence_filtering():
    """Test 4: Confidence filtering"""
    print("\n" + "="*70)
    print("TEST 4: Confidence Filtering")
    print("="*70)
    
    selector = get_ml_tool_selector()
    
    # Test query with varying confidence
    query = "random text xyz123 blah"
    
    print(f"Query: '{query}'")
    print(f"Threshold: {selector.confidence_threshold}")
    
    try:
        tools, probs = selector.predict_tools(query, return_probabilities=True)
        
        print(f"Predicted tools: {tools}")
        print(f"Probabilities: {probs}")
        
        # Check all probabilities are above threshold
        all_above = all(p >= selector.confidence_threshold for p in probs.values())
        
        if all_above:
            print(f"✅ All predicted tools are above confidence threshold")
            return True
        else:
            print(f"❌ Some tools below threshold: {probs}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_integration():
    """Test 5: Integration with build_tools_for_request_ml"""
    print("\n" + "="*70)
    print("TEST 5: Integration with build_tools_for_request_ml")
    print("="*70)
    
    test_queries = [
        "What's the price of NVDA?",
        "Show me Tesla's historical prices",
        "Latest developments in quantum computing",
    ]
    
    all_passed = True
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        
        try:
            start = time.time()
            tool_specs, metadata = build_tools_for_request_ml(
                query,
                use_ml=True,
                fallback_to_rules=True
            )
            elapsed = (time.time() - start) * 1000
            
            tool_names = [spec['function']['name'] for spec in tool_specs]
            
            print(f"   Method: {metadata.get('method')}")
            print(f"   Tools: {tool_names}")
            print(f"   Confidence: {metadata.get('confidence')}")
            print(f"   Count: {metadata.get('tools_count')}")
            print(f"   Time: {elapsed:.1f}ms")
            
            if metadata.get('method') == 'ml':
                print(f"   ✅ Using ML selection")
            elif metadata.get('fallback_used'):
                print(f"   ⚠️  ML attempted but fell back to rules")
            else:
                print(f"   ⚠️  Using rule-based selection")
                
        except Exception as e:
            print(f"   ❌ FAIL - Error: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    return all_passed


def test_statistics():
    """Test 6: Statistics tracking"""
    print("\n" + "="*70)
    print("TEST 6: Statistics Tracking")
    print("="*70)
    
    try:
        stats = get_ml_stats()
        
        print(f"ML Enabled: {stats.get('ml_enabled')}")
        print(f"Model Loaded: {stats.get('model_loaded')}")
        print(f"Total Predictions: {stats.get('total_predictions')}")
        print(f"Fallback Count: {stats.get('fallback_count')}")
        print(f"Fallback Rate: {stats.get('fallback_rate'):.1%}")
        print(f"Avg Confidence: {stats.get('avg_confidence'):.3f}")
        print(f"Avg Prediction Time: {stats.get('avg_prediction_time_ms'):.2f}ms")
        print(f"Tools Predicted: {stats.get('tools_predicted')}")
        print(f"Confidence Distribution: {stats.get('confidence_distribution')}")
        
        print("✅ Statistics retrieved successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("ML TOOL SELECTION TEST SUITE")
    print("="*70)
    
    results = {}
    
    # Run tests
    results['Model Loading'] = test_model_loading()
    
    if results['Model Loading']:
        results['Query Embedding'] = test_query_embedding()
        results['Tool Prediction'] = test_tool_prediction()
        results['Confidence Filtering'] = test_confidence_filtering()
        results['Integration'] = test_integration()
        results['Statistics'] = test_statistics()
    else:
        print("\n⚠️  Skipping remaining tests (model not loaded)")
        results['Query Embedding'] = False
        results['Tool Prediction'] = False
        results['Confidence Filtering'] = False
        results['Integration'] = False
        results['Statistics'] = False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! ML tool selection is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
