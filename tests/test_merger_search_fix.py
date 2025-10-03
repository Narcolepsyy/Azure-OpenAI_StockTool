#!/usr/bin/env python3
"""
Test script to simulate the Hachijuni Bank merger query issue and validate the fix.
This tests the enhanced web search functionality for merger-related queries.
"""
import asyncio
import json
from typing import Dict, Any

def test_hachijuni_bank_merger_search():
    """Test the enhanced web search for Hachijuni Bank merger information."""
    print("🔍 Testing Hachijuni Bank merger search functionality...")
    
    try:
        # Import the tool registry
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from app.utils.tools import TOOL_REGISTRY
        
        # Test the specific query that was problematic
        query = "Hachijuni Bank merger with Nagano Bank"
        print(f"Query: {query}")
        
        # Get the web search tool
        web_search_tool = TOOL_REGISTRY.get('web_search')
        if not web_search_tool:
            print("❌ Web search tool not found")
            return False
        
        # Execute the search
        result = web_search_tool(query=query, max_results=8)
        
        # Validate results
        print(f"\n📊 Search Results Analysis:")
        print(f"  - Query processed: {result.get('query')}")
        print(f"  - Method used: {result.get('method')}")  
        print(f"  - Results count: {result.get('count')}")
        print(f"  - Duration: {result.get('duration_seconds', 0):.2f}s")
        print(f"  - Merger info detected: {result.get('merger_info_detected', False)}")
        
        # Check for merger-specific information
        merger_info = result.get('merger_info_detected', False)
        merger_summary = result.get('merger_summary', '')
        primary_url = result.get('primary_source_url', '')
        
        print(f"\n🔍 Merger Information Analysis:")
        print(f"  - Merger detection: {'✅' if merger_info else '❌'}")
        print(f"  - Summary available: {'✅' if merger_summary else '❌'}")
        print(f"  - Primary source URL: {'✅' if primary_url else '❌'}")
        
        if merger_summary:
            print(f"  - Summary: {merger_summary}")
            
        if primary_url:
            print(f"  - Primary URL: {primary_url}")
        
        # Analyze search results quality
        results = result.get('results', [])
        relevant_results = 0
        financial_sources = 0
        
        print(f"\n📄 Results Quality Analysis:")
        for i, res in enumerate(results, 1):
            title = res.get('title', '')
            url = res.get('url', '')
            snippet = res.get('snippet', '')
            relevance = res.get('relevance_score', 0)
            
            # Check relevance
            merger_keywords = ['merger', 'acquisition', 'integrate', 'share exchange', 'business integration']
            if any(keyword.lower() in title.lower() or keyword.lower() in snippet.lower() for keyword in merger_keywords):
                relevant_results += 1
            
            # Check for financial sources
            financial_domains = ['tipranks.com', 'marketscreener.com', 'bloomberg.com', 'reuters.com', 'nikkei.com']
            if any(domain in url.lower() for domain in financial_domains):
                financial_sources += 1
                
            print(f"  {i}. {title}")
            print(f"     Relevance: {relevance:.2f}")
            print(f"     URL: {url}")
            print(f"     Snippet: {snippet[:80]}...")
            
        print(f"\n✅ Quality Metrics:")
        print(f"  - Relevant results: {relevant_results}/{len(results)}")
        print(f"  - Financial sources: {financial_sources}/{len(results)}")
        print(f"  - Average relevance: {sum(r.get('relevance_score', 0) for r in results) / len(results):.2f}")
        
        # Success criteria
        success = (
            len(results) >= 3 and 
            merger_info and 
            relevant_results >= 2 and
            merger_summary
        )
        
        print(f"\n🎯 Overall Assessment: {'✅ SUCCESS' if success else '❌ NEEDS IMPROVEMENT'}")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_merger_summary_extraction():
    """Test the merger summary extraction functionality."""
    print("\n🔍 Testing merger summary extraction...")
    
    try:
        from app.utils.tools import _extract_merger_summary
        
        # Mock search results that contain merger information
        mock_results = [
            {
                'title': 'Hachijuni Bank Announces Merger with Nagano Bank',
                'snippet': 'The merger is scheduled for January 1, 2026, with Hachijuni Bank issuing 2.54 shares for every one share of Naganobank. Transaction value: ¥10.8 billion.',
                'content': 'The Hachijuni Bank, Ltd. completed the acquisition of the remaining 98.33% stake in The Naganobank, Ltd.',
                'url': 'https://www.tipranks.com/news/hachijuni-merger',
                'relevance_score': 1.0
            },
            {
                'title': 'Business Integration Details',
                'snippet': 'The banks will integrate business in June 2023 and promote discussions towards early merger after the business integration.',
                'content': 'Expected to close on June 1, 2023 with necessary regulatory approvals.',
                'url': 'https://www.naganobank.co.jp/integration',
                'relevance_score': 0.9
            }
        ]
        
        summary = _extract_merger_summary(mock_results)
        print(f"📄 Extracted summary: {summary}")
        
        # Validate summary contains key information
        has_date = 'date' in summary.lower()
        has_ratio = 'ratio' in summary.lower() or 'shares' in summary.lower()
        has_value = 'billion' in summary.lower() or 'value' in summary.lower()
        has_url = 'http' in summary
        
        print(f"Summary analysis:")
        print(f"  - Contains date info: {'✅' if has_date else '❌'}")
        print(f"  - Contains share ratio: {'✅' if has_ratio else '❌'}")
        print(f"  - Contains transaction value: {'✅' if has_value else '❌'}")
        print(f"  - Contains source URL: {'✅' if has_url else '❌'}")
        
        return summary and (has_date or has_ratio or has_value)
        
    except Exception as e:
        print(f"❌ Summary extraction test failed: {e}")
        return False

def main():
    """Run all merger search functionality tests."""
    print("🚀 Enhanced Web Search - Merger Detection Tests")
    print("=" * 55)
    
    tests = [
        ("Hachijuni Bank Merger Search", test_hachijuni_bank_merger_search),
        ("Merger Summary Extraction", test_merger_summary_extraction)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📋 Test Summary:")
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! Hachijuni Bank merger search issue is RESOLVED.")
        print("\n✅ Improvements made:")
        print("  - Enhanced relevance scoring for merger content")
        print("  - Automatic detection of financial/merger keywords")  
        print("  - Improved prioritization of financial news sources")
        print("  - Added merger summary extraction")
        print("  - Enhanced primary source URL identification")
    else:
        print(f"\n⚠️ Some tests failed. Need further improvements.")
    
    return passed == total

if __name__ == "__main__":
    main()