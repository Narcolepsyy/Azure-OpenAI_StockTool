#!/usr/bin/env python3
"""
Test the enhanced Japanese query simplification.
"""

import sys
sys.path.append('/home/khaitran/PycharmProjects/Azure-OpenAI_StockTool')

from app.services.perplexity_web_search import PerplexityWebSearchService

def test_japanese_query_simplification():
    """Test the new Japanese query simplification feature."""
    
    service = PerplexityWebSearchService()
    
    test_queries = [
        "八十二銀行と長野銀行の統合関連ニュースを検索してください。",
        "アップルの株価について教えてください",
        "トヨタの決算情報をお願いします",
        "日本の経済状況を調べてください"
    ]
    
    print("🔧 Testing Japanese Query Simplification")
    print("=" * 60)
    
    for i, original_query in enumerate(test_queries, 1):
        enhanced_query = service._enhance_search_query(original_query, include_recent=True)
        
        print(f"\nTest {i}:")
        print(f"  Original:  {original_query}")
        print(f"  Enhanced:  {enhanced_query}")
        print(f"  Length:    {len(original_query)} → {len(enhanced_query)} chars")
        print(f"  Simplified: {'✅' if len(enhanced_query) < len(original_query) else '❌'}")

if __name__ == "__main__":
    test_japanese_query_simplification()