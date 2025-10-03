#!/usr/bin/env python3
"""
Test script to demonstrate Perplexity-style citations in web search results.
"""

import asyncio
from app.services.perplexity_web_search import perplexity_web_search

def test_citation_system():
    """Test the enhanced citation system that works like Perplexity."""
    print("🔍 Testing Perplexity-Style Citation System")
    print("=" * 60)
    
    test_queries = [
        {
            "query": "Tesla Q3 2025 earnings results and financial performance",
            "description": "Financial earnings query - should have detailed citations"
        },
        {
            "query": "Latest developments in artificial intelligence technology September 2025",
            "description": "Current tech news - should cite multiple recent sources"
        },
        {
            "query": "日本の経済成長率 2025年第三四半期",
            "description": "Japanese economic data - should handle multilingual citations"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: {test['description']}")
        print(f"   Query: {test['query']}")
        print("-" * 50)
        
        try:
            result = perplexity_web_search(
                query=test['query'],
                max_results=6,
                synthesize_answer=True,
                include_recent=True
            )
            
            # Display performance metrics
            print(f"   📊 Sources found: {len(result.get('sources', []))}")
            print(f"   ⏱️  Search time: {result.get('search_time', 0):.2f}s")
            print(f"   🧠 Synthesis time: {result.get('synthesis_time', 0):.2f}s")
            print(f"   📈 Confidence: {result.get('confidence_score', 0):.2f}")
            
            # Show the formatted answer with citations
            answer = result.get('answer', '')
            if answer:
                print(f"\n   💡 **ANSWER WITH CITATIONS:**")
                print("   " + "─" * 40)
                
                # Show first 300 characters of the answer
                answer_preview = answer[:500] + "..." if len(answer) > 500 else answer
                print(f"   {answer_preview}")
                
                # Count citations in the answer
                import re
                citation_matches = re.findall(r'\[\d+\]', answer)
                print(f"\n   📝 Citations found in text: {len(citation_matches)} ({', '.join(set(citation_matches))})")
                
                # Show if sources section is included
                if "**Sources:**" in answer:
                    print(f"   ✅ Sources section included at end")
                    sources_section = answer.split("**Sources:**")[1]
                    source_lines = [line.strip() for line in sources_section.split('\n') if line.strip() and line.strip().startswith('[')]
                    print(f"   🔗 Source links: {len(source_lines)}")
                else:
                    print(f"   ⚠️  No sources section found")
            
            # Show citation structure
            citations = result.get('citations', {})
            if citations:
                print(f"\n   📚 **CITATION DETAILS:**")
                for citation_id, citation_info in list(citations.items())[:3]:  # Show first 3
                    if isinstance(citation_info, dict):
                        print(f"   [{citation_id}] {citation_info.get('title', 'No title')[:60]}...")
                        print(f"       Domain: {citation_info.get('domain', 'Unknown')}")
                        print(f"       URL: {citation_info.get('url', 'No URL')[:60]}...")
                    else:
                        print(f"   [{citation_id}] {str(citation_info)[:60]}...")
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Citation System Test Complete")
    print("\n📋 **PERPLEXITY-STYLE FEATURES DEMONSTRATED:**")
    print("   • In-text citations [1,2,3] throughout the answer")
    print("   • Comprehensive source list at the end")
    print("   • Clickable links in markdown format")
    print("   • Domain attribution for credibility")
    print("   • Clean, professional formatting")

def show_citation_comparison():
    """Show the difference between old and new citation systems."""
    print("\n🔄 **CITATION SYSTEM COMPARISON**")
    print("=" * 60)
    
    print("**OLD SYSTEM (Basic):**")
    print("Tesla reported strong earnings. The stock price increased.")
    print("Citations: [1] Tesla Q3 Report - tesla.com")
    
    print("\n**NEW SYSTEM (Perplexity-style):**")
    print("Tesla reported record Q3 earnings of $25.2B [1], representing a 15% increase")
    print("year-over-year [2]. Following the announcement, Tesla stock (TSLA) surged 8.5%")  
    print("in after-hours trading [3], reaching a new 52-week high [1][4].")
    print("")
    print("**Sources:**")
    print("[1] [Tesla Reports Record Q3 2025 Earnings - tesla.com](https://tesla.com/earnings)")
    print("[2] [Tesla Q3 Results Beat Expectations - reuters.com](https://reuters.com/tesla)")
    print("[3] [TSLA Stock Surges on Strong Earnings - marketwatch.com](https://marketwatch.com/tsla)")
    print("[4] [Tesla Hits New 52-Week High - yahoo.com](https://finance.yahoo.com/tsla)")
    
    print("\n✨ **KEY IMPROVEMENTS:**")
    print("   • Every fact is immediately cited [1,2,3]")
    print("   • Multiple sources can support the same claim [1][4]") 
    print("   • Sources list provides clickable references")
    print("   • Professional, academic-style formatting")
    print("   • Easy to verify specific claims")

if __name__ == "__main__":
    print("🚀 Enhanced Citation System - Perplexity Style")
    print("=" * 60)
    
    # Show the comparison first
    show_citation_comparison()
    
    # Run the actual tests
    test_citation_system()