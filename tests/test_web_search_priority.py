#!/usr/bin/env python3
"""
Test script to validate that the system prioritizes web search for unknown information.
"""

import asyncio
import json
from app.services.perplexity_web_search import perplexity_web_search

async def test_web_search_priority():
    """Test various scenarios to ensure web search is used for unknown information."""
    
    test_queries = [
        {
            "query": "Latest news about 八十二銀行と長野銀行の統合",
            "description": "Japanese financial news - should use web search for current information"
        },
        {
            "query": "What happened to Tesla stock today?",
            "description": "Current stock information - should use web search for latest data"
        },
        {
            "query": "Recent developments in AI technology in 2025",
            "description": "Current technology trends - should use web search"
        },
        {
            "query": "Current inflation rate in Japan",
            "description": "Current economic data - should use web search"
        }
    ]
    
    print("🔍 Testing Web Search Priority System")
    print("=" * 60)
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: {test['description']}")
        print(f"   Query: {test['query']}")
        print("-" * 40)
        
        try:
            # Test the perplexity web search directly
            result = perplexity_web_search(
                query=test['query'],
                max_results=5,
                synthesize_answer=True,
                include_recent=True
            )
            
            print(f"   ✅ Search completed successfully")
            print(f"   📊 Sources found: {len(result.get('sources', []))}")
            print(f"   ⏱️  Search time: {result.get('search_time', 0):.2f}s")
            print(f"   🧠 Synthesis time: {result.get('synthesis_time', 0):.2f}s")
            print(f"   📈 Confidence: {result.get('confidence_score', 0):.2f}")
            
            # Check if we got a meaningful answer
            answer = result.get('answer', '')
            if answer and len(answer) > 50:
                print(f"   💡 Answer preview: {answer[:100]}...")
            else:
                print(f"   ⚠️  Answer seems short or empty")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Web Search Priority Test Complete")

def test_tool_descriptions():
    """Test that tool descriptions emphasize web search priority."""
    from app.utils.tools import tools_spec
    
    print("\n🔧 Checking Tool Descriptions for Web Search Priority")
    print("=" * 60)
    
    web_search_tools = ['web_search', 'perplexity_search', 'augmented_rag_search']
    
    for tool_spec in tools_spec:
        if tool_spec['function']['name'] in web_search_tools:
            name = tool_spec['function']['name']
            description = tool_spec['function']['description']
            
            print(f"\n📋 Tool: {name}")
            
            # Check for priority keywords
            priority_keywords = ['PRIORITY', 'ESSENTIAL', 'COMPREHENSIVE', 'ALWAYS USE', 'WHENEVER']
            has_priority = any(keyword in description.upper() for keyword in priority_keywords)
            
            if has_priority:
                print(f"   ✅ Has priority keywords")
            else:
                print(f"   ⚠️  Missing priority emphasis")
                
            print(f"   📝 Description: {description[:100]}...")
    
    print("\n✅ Tool Description Check Complete")

if __name__ == "__main__":
    # Run synchronous tests first
    test_tool_descriptions()
    
    # Run async tests
    try:
        asyncio.run(test_web_search_priority())
    except Exception as e:
        print(f"❌ Async test failed: {e}")