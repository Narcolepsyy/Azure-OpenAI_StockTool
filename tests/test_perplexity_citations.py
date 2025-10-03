#!/usr/bin/env python3
"""Test the enhanced Perplexity-style citations."""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.perplexity_web_search import (
    perplexity_web_search, 
    CitationInfo, 
    get_citation_css_styles
)

def test_citation_info():
    """Test the CitationInfo class functionality."""
    print("Testing CitationInfo class...")
    
    citation = CitationInfo(
        citation_id=1,
        title="Tesla Stock Analysis: Q3 2024 Earnings Report",
        url="https://finance.yahoo.com/news/tesla-earnings-q3-2024",
        domain="finance.yahoo.com",
        snippet="Tesla reported strong Q3 earnings with revenue growth of 8% year-over-year...",
        publish_date="October 15, 2024",
        word_count=450
    )
    
    print(f"Display Format: {citation.to_display_format()}")
    print(f"Markdown Link: {citation.to_markdown_link()}")
    print("\nCitation Card HTML:")
    print(citation.to_citation_card_html())
    print("\nJSON Serializable:")
    import json
    print(json.dumps(citation.to_json_serializable(), indent=2))

def test_css_styles():
    """Test CSS styles generation."""
    print("\n" + "="*50)
    print("Testing CSS Styles...")
    print("="*50)
    styles = get_citation_css_styles()
    print(styles[:200] + "..." if len(styles) > 200 else styles)

def test_perplexity_search():
    """Test the enhanced perplexity search with citations."""
    print("\n" + "="*50)
    print("Testing Perplexity Search with Citations...")
    print("="*50)
    
    # Test query
    query = "Tesla stock performance 2024"
    
    print(f"Searching for: {query}")
    
    try:
        result = perplexity_web_search(
            query=query,
            max_results=3,
            synthesize_answer=True,
            include_recent=True
        )
        
        print(f"\nQuery: {result['query']}")
        print(f"Confidence: {result['confidence_score']:.2f}")
        print(f"Search Time: {result['search_time']:.2f}s")
        print(f"Total Sources: {len(result['sources'])}")
        print(f"Citations: {len(result['citations'])}")
        
        print("\nAnswer Preview:")
        print(result['answer'][:300] + "..." if len(result['answer']) > 300 else result['answer'])
        
        print("\nCitations:")
        for citation_id, citation_info in result['citations'].items():
            print(f"[{citation_id}] {citation_info['title']} - {citation_info['domain']}")
            if citation_info['snippet']:
                print(f"    > {citation_info['snippet'][:100]}...")
        
        print(f"\nCSS Styles Available: {'citation_styles' in result}")
        
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing Enhanced Perplexity Citations")
    print("="*50)
    
    # Test individual components
    test_citation_info()
    test_css_styles()
    
    # Test full search (if desired - this makes actual web requests)
    print(f"\nRun full search test? (y/n): ", end="")
    response = input().strip().lower()
    if response == 'y':
        test_perplexity_search()
    else:
        print("Skipping full search test.")
    
    print("\nAll tests completed!")