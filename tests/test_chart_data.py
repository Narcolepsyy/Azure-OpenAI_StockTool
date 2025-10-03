"""
Test chart data generation for stock detail page
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services import yfinance_service
import json

def test_chart_data():
    """Test chart data with various stocks"""
    
    test_symbols = [
        "7203.T",  # Toyota
        "6758.T",  # Sony
        "AAPL",    # Apple (US stock)
    ]
    
    print("=" * 80)
    print("Testing Chart Data Generation")
    print("=" * 80)
    print()
    
    for symbol in test_symbols:
        print(f"\n{'='*60}")
        print(f"📊 Testing: {symbol}")
        print('='*60)
        
        # Test without chart
        print("\n1️⃣  Without chart data:")
        data_no_chart = yfinance_service.get_stock_info(symbol, with_chart=False)
        if "error" in data_no_chart:
            print(f"   ❌ Error: {data_no_chart['error']}")
            continue
        
        print(f"   ✅ Symbol: {data_no_chart.get('symbol')}")
        print(f"   ✅ Name: {data_no_chart.get('name')}")
        print(f"   ✅ Price: {data_no_chart.get('current_price')}")
        print(f"   ✅ Chart included: {'chart' in data_no_chart}")
        
        # Test with chart
        print("\n2️⃣  With chart data:")
        data_with_chart = yfinance_service.get_stock_info(symbol, with_chart=True)
        if "error" in data_with_chart:
            print(f"   ❌ Error: {data_with_chart['error']}")
            continue
        
        print(f"   ✅ Symbol: {data_with_chart.get('symbol')}")
        print(f"   ✅ Name: {data_with_chart.get('name')}")
        print(f"   ✅ Price: {data_with_chart.get('current_price')}")
        print(f"   ✅ Chart included: {'chart' in data_with_chart}")
        
        if 'chart' in data_with_chart:
            chart = data_with_chart['chart']
            print(f"\n   📈 Chart Details:")
            print(f"      • Timezone: {chart.get('timezone')}")
            print(f"      • Default range: {chart.get('default_range')}")
            print(f"      • Number of ranges: {len(chart.get('ranges', []))}")
            
            for range_data in chart.get('ranges', []):
                key = range_data.get('key')
                label = range_data.get('label')
                points_count = len(range_data.get('points', []))
                print(f"      • {label} ({key}): {points_count} data points")
                
                # Show first point as sample
                if range_data.get('points'):
                    first_point = range_data['points'][0]
                    print(f"        Sample: time={first_point.get('time')}, close={first_point.get('close')}")
        
        # Check company profile
        if 'company_profile' in data_with_chart:
            profile = data_with_chart['company_profile']
            print(f"\n   🏢 Company Profile:")
            print(f"      • Sector: {profile.get('sector')}")
            print(f"      • Industry: {profile.get('industry')}")
            print(f"      • Website: {profile.get('website')}")
            print(f"      • Description length: {len(profile.get('description', '')) if profile.get('description') else 0} chars")
        
        # Test JSON serialization
        print("\n3️⃣  JSON Serialization Test:")
        try:
            json_str = json.dumps(data_with_chart, indent=2, default=str)
            print(f"   ✅ Successfully serialized ({len(json_str)} bytes)")
        except Exception as e:
            print(f"   ❌ Serialization failed: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_chart_data()
