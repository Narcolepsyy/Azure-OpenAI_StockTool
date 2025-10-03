"""
Test the enhanced RAG service to verify web search integration is working correctly.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.enhanced_rag_service import EnhancedRAGService


async def test_enhanced_rag():
    """Test the enhanced RAG service with web search."""
    
    print("🔍 Testing Enhanced RAG Service with Web Search Integration")
    print("=" * 60)
    
    # Initialize the service
    enhanced_rag = EnhancedRAGService()
    
    # Test queries
    test_queries = [
        "What is Apple's current stock price?",
        "Latest Tesla earnings report",
        "Microsoft financial performance 2024"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing query: '{query}'")
        print("-" * 40)
        
        try:
            # Use augmented search which combines KB + web search
            results = await enhanced_rag.augmented_search(query, kb_k=3, web_results=5, max_total_chunks=8)
            
            print(f"✅ Query successful!")
            print(f"📊 Total results: {len(results.get('combined_chunks', []))}")
            
            # Show breakdown by source
            kb_count = len([r for r in results.get('combined_chunks', []) if r.get('source') == 'knowledge_base'])
            web_count = len([r for r in results.get('combined_chunks', []) if r.get('source') == 'web_search'])
            
            print(f"   📚 Knowledge base results: {kb_count}")
            print(f"   🌐 Web search results: {web_count}")
            
            # Show first few results
            for j, chunk in enumerate(results.get('combined_chunks', [])[:2]):
                source_icon = "📚" if chunk.get('source') == 'knowledge_base' else "🌐"
                print(f"   {source_icon} {j+1}. {chunk.get('title', 'No title')}")
                if chunk.get('url'):
                    print(f"      🔗 {chunk['url']}")
                if chunk.get('search_source'):
                    print(f"      📡 Source: {chunk['search_source']}")
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Enhanced RAG test completed!")


if __name__ == "__main__":
    asyncio.run(test_enhanced_rag())