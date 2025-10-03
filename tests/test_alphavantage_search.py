"""
Test AlphaVantage symbol search functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services import alphavantage_service

def test_search():
    """Test symbol search with various queries"""
    
    test_queries = [
        "Toyota",
        "AAPL",
        "Microsoft",
        "7203",
        "Sony"
    ]
    
    print("=" * 80)
    print("Testing AlphaVantage Symbol Search")
    print("=" * 80)
    print()
    
    for query in test_queries:
        print(f"\n🔍 Searching for: '{query}'")
        print("-" * 60)
        
        results = alphavantage_service.search_symbol(query)
        
        if not results:
            print("  ❌ No results found or API error")
            continue
        
        print(f"  ✅ Found {len(results)} results:")
        for i, result in enumerate(results[:5], 1):  # Show top 5
            symbol = result.get('symbol', 'N/A')
            name = result.get('description', 'N/A')
            type_ = result.get('type', 'N/A')
            region = result.get('region', 'N/A')
            match_score = result.get('matchScore', '0.0')
            
            print(f"    {i}. {symbol:10s} - {name[:40]:40s} ({type_}, {region})")
            print(f"       Match Score: {match_score}")
    
    print("\n" + "=" * 80)
    print("Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_search()
