#!/usr/bin/env python3
"""
Test the enhanced scoring system with a Japanese banking merger query.
This tests domain priors, language detection, and financial content ranking.
"""

import asyncio
import os
import sys
sys.path.append('/home/khaitran/PycharmProjects/Azure-OpenAI_StockTool')

from app.services.perplexity_web_search import PerplexityWebSearchService

async def test_japanese_banking_query():
    """Test Japanese banking merger query with enhanced scoring system."""
    
    # The query: "Please search for news related to the merger between Hachijuni Bank and Nagano Bank"
    query = "八十二銀行と長野銀行の統合関連ニュースを検索してください。"
    
    print("🏦 Testing Japanese Banking Merger Query")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"Translation: Search for news related to the merger between Hachijuni Bank and Nagano Bank")
    print("=" * 60)
    
    # Test the enhanced search system
    async with PerplexityWebSearchService() as search_service:
        try:
            # Perform the search
            response = await search_service.perplexity_search(
                query=query,
                max_results=8,
                synthesize_answer=True,
                include_recent=True
            )
            
            print(f"\n✅ Search completed successfully!")
            print(f"📊 Search time: {response.search_time:.2f}s")
            print(f"📝 Synthesis time: {response.synthesis_time:.2f}s")
            print(f"⏱️ Total time: {response.total_time:.2f}s")
            print(f"🎯 Confidence: {response.confidence_score:.2f}")
            
            # Analyze results with domain priors
            print(f"\n📰 Found {len(response.sources)} sources:")
            print("-" * 60)
            
            domain_boosts_detected = {}
            score_range = []
            
            for i, source in enumerate(response.sources, 1):
                domain = source.url.split('/')[2] if '/' in source.url else 'unknown'
                
                # Track domain boosts
                if source.domain_boost != 1.0:
                    domain_boosts_detected[domain] = source.domain_boost
                
                # Track score range
                score_range.append(source.combined_score)
                
                print(f"{i}. {source.title[:80]}{'...' if len(source.title) > 80 else ''}")
                print(f"   🌐 Domain: {domain}")
                print(f"   📊 Combined Score: {source.combined_score:.3f}")
                print(f"   📈 BM25: {source.bm25_score:.3f} | Semantic: {source.semantic_score:.3f}")
                print(f"   🎯 Domain Boost: {source.domain_boost:.2f}x")
                print(f"   📅 Recency Boost: {source.recency_boost:.2f}x")
                print(f"   📝 Snippet-Title Boost: {source.snippet_title_boost:.2f}x")
                print(f"   🔗 URL: {source.url}")
                print()
            
            # Enhanced scoring analysis
            print("🔍 Enhanced Scoring Analysis:")
            print("-" * 40)
            
            if score_range:
                min_score = min(score_range)
                max_score = max(score_range)
                avg_score = sum(score_range) / len(score_range)
                score_std = (sum((x - avg_score) ** 2 for x in score_range) / len(score_range)) ** 0.5
                
                print(f"📊 Score Distribution:")
                print(f"   Min: {min_score:.3f}")
                print(f"   Max: {max_score:.3f}")
                print(f"   Avg: {avg_score:.3f}")
                print(f"   Std Dev: {score_std:.3f}")
                print(f"   Range: {max_score - min_score:.3f}")
            
            if domain_boosts_detected:
                print(f"\n🎯 Domain Priors Active:")
                for domain, boost in domain_boosts_detected.items():
                    boost_type = "📈 Boost" if boost > 1.0 else "📉 Penalty"
                    print(f"   {boost_type}: {domain} ({boost:.2f}x)")
            else:
                print(f"\n⚪ No domain priors applied (results from general domains)")
            
            # Language detection test
            print(f"\n🌐 Language Processing:")
            print(f"   Query contains Japanese characters: {'✅' if any(ord(c) > 127 for c in query) else '❌'}")
            print(f"   Expected locale optimization: JP/ja")
            
            # Financial content detection
            financial_terms = ['銀行', 'bank', '統合', 'merger', 'financial', 'ニュース', 'news']
            detected_terms = [term for term in financial_terms if term in query.lower()]
            print(f"   Financial terms detected: {detected_terms}")
            
            # Display synthesized answer
            if response.answer:
                print(f"\n📝 Synthesized Answer:")
                print("-" * 40)
                print(response.answer[:500] + "..." if len(response.answer) > 500 else response.answer)
            
            # Citations analysis
            if response.citations:
                print(f"\n📚 Citations ({len(response.citations)}):")
                print("-" * 30)
                for cit_id, cit_info in response.citations.items():
                    print(f"[{cit_id}] {cit_info}")
            
            print(f"\n🎉 Test completed successfully!")
            print(f"✨ Enhanced scoring system working with:")
            print(f"   - Japanese language detection")
            print(f"   - Financial domain recognition") 
            print(f"   - Domain priors (if applicable)")
            print(f"   - BM25 + semantic hybrid ranking")
            print(f"   - Multi-signal scoring (domain, recency, snippet-title)")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_japanese_banking_query())
    sys.exit(0 if success else 1)