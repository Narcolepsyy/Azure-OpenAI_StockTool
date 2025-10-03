#!/usr/bin/env python3
"""
Test LLM-powered query synthesis for search optimization.
"""

import asyncio
import sys
sys.path.append('/home/khaitran/PycharmProjects/Azure-OpenAI_StockTool')

from app.services.perplexity_web_search import PerplexityWebSearchService

async def test_llm_query_synthesis():
    """Test the new LLM-powered query synthesis."""
    
    test_queries = [
        {
            "query": "八十二銀行と長野銀行の統合関連ニュースを検索してください。",
            "description": "Japanese banking merger query (complex sentence)"
        },
        {
            "query": "アップルの最新の決算について教えてください",
            "description": "Japanese Apple earnings query"
        },
        {
            "query": "Please tell me about the latest developments in artificial intelligence",
            "description": "English AI development query"
        },
        {
            "query": "Could you search for information about Tesla's stock performance this year?",
            "description": "English Tesla stock query"
        },
        {
            "query": "I would like to know about the merger between Microsoft and Activision",
            "description": "English Microsoft Activision merger query"
        }
    ]
    
    print("🤖 Testing LLM-Powered Query Synthesis")
    print("=" * 70)
    
    service = PerplexityWebSearchService()
    
    for i, test_case in enumerate(test_queries, 1):
        original_query = test_case["query"]
        description = test_case["description"]
        
        print(f"\n🔍 Test {i}: {description}")
        print(f"Original Query: {original_query}")
        print("-" * 50)
        
        try:
            # Test LLM synthesis directly
            llm_synthesized = await service._llm_synthesize_query(original_query, include_recent=True)
            
            # Test fallback rule-based
            rule_enhanced = service._fallback_enhance_query(original_query, include_recent=True)
            
            # Test full enhancement (LLM with fallback)
            full_enhanced = await service._enhance_search_query(original_query, include_recent=True)
            
            print(f"📊 Results:")
            print(f"  LLM Synthesized:  {llm_synthesized}")
            print(f"  Rule-based:       {rule_enhanced}")
            print(f"  Final Enhanced:   {full_enhanced}")
            
            # Analysis
            original_len = len(original_query)
            llm_len = len(llm_synthesized) if llm_synthesized else 0
            
            print(f"📈 Analysis:")
            print(f"  Length reduction: {original_len} → {llm_len} chars")
            print(f"  LLM success:      {'✅' if llm_synthesized else '❌'}")
            print(f"  Keyword focused:  {'✅' if llm_len < original_len else '❌'}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎉 Query Synthesis Testing Complete!")
    print(f"💡 Benefits of LLM synthesis:")
    print(f"   - Intelligent extraction of search intent")
    print(f"   - Language-aware optimization")
    print(f"   - Context-sensitive keyword selection")
    print(f"   - Automatic removal of conversational elements")

if __name__ == "__main__":
    asyncio.run(test_llm_query_synthesis())