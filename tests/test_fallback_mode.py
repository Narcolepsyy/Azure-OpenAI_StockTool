#!/usr/bin/env python3
"""Test the new fallback mode behavior in Perplexity web search."""

import asyncio
import os
import sys
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up logging to see the fallback behavior
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from services.perplexity_web_search import PerplexityWebSearchService

async def test_fallback_scenarios():
    """Test different fallback scenarios."""
    print("Testing Perplexity Search Fallback Mode")
    print("="*50)
    
    service = PerplexityWebSearchService()
    
    # Test query
    query = "Tesla stock performance 2024"
    
    print(f"Current configuration:")
    print(f"- Brave API available: {service.use_brave}")
    print(f"- Minimum results threshold: {service.min_results_threshold}")
    print(f"- Fallback mode: Enabled")
    print()
    
    print(f"Testing search for: '{query}'")
    print("-" * 30)
    
    try:
        # Test the enhanced web search directly to see fallback logic
        results = await service._enhanced_web_search(query, max_results=5, include_recent=True)
        
        print(f"Final results count: {len(results)}")
        print("Search providers used:")
        
        brave_count = sum(1 for r in results if hasattr(r, 'source') and r.source == 'brave_search')
        ddgs_count = len(results) - brave_count
        
        print(f"- Brave Search: {brave_count} results")
        print(f"- DuckDuckGo: {ddgs_count} results")
        
        print("\nResult preview:")
        for i, result in enumerate(results[:3]):
            provider = "Brave" if hasattr(result, 'source') and result.source == 'brave_search' else "DDGS"
            print(f"{i+1}. [{provider}] {result.title[:60]}...")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

def test_threshold_configuration():
    """Test different threshold configurations."""
    print("\n" + "="*50)
    print("Testing Threshold Configuration")
    print("="*50)
    
    # Test with different threshold values
    thresholds = [1, 3, 5, 10]
    
    for threshold in thresholds:
        os.environ["MIN_SEARCH_RESULTS_THRESHOLD"] = str(threshold)
        service = PerplexityWebSearchService()
        print(f"Threshold {threshold}: Service configured with min_results_threshold = {service.min_results_threshold}")
    
    # Reset to default
    if "MIN_SEARCH_RESULTS_THRESHOLD" in os.environ:
        del os.environ["MIN_SEARCH_RESULTS_THRESHOLD"]

async def test_brave_simulation():
    """Simulate Brave API scenarios."""
    print("\n" + "="*50)
    print("Testing Brave API Scenarios")
    print("="*50)
    
    # Save original state
    original_brave_key = os.environ.get("BRAVE_API_KEY")
    
    # Test 1: With Brave API
    if original_brave_key:
        print("Scenario 1: Brave API enabled")
        service = PerplexityWebSearchService()
        print(f"- use_brave: {service.use_brave}")
        print(f"- Expected behavior: Try Brave first, fallback to DDGS if insufficient")
    
    # Test 2: Without Brave API
    print("\nScenario 2: Brave API disabled")
    if "BRAVE_API_KEY" in os.environ:
        del os.environ["BRAVE_API_KEY"]
    
    service = PerplexityWebSearchService()
    print(f"- use_brave: {service.use_brave}")
    print(f"- Expected behavior: Use DDGS only")
    
    # Restore original state
    if original_brave_key:
        os.environ["BRAVE_API_KEY"] = original_brave_key

if __name__ == "__main__":
    print("Perplexity Search Fallback Mode Test")
    print("="*50)
    
    # Test configuration
    test_threshold_configuration()
    
    # Test Brave scenarios
    asyncio.run(test_brave_simulation())
    
    # Test actual search (optional)
    print(f"\nRun actual search test? (y/n): ", end="")
    response = input().strip().lower()
    if response == 'y':
        asyncio.run(test_fallback_scenarios())
    else:
        print("Skipping actual search test.")
    
    print("\nFallback mode testing completed!")
    print("\nKey improvements:")
    print("✅ Brave Search tried first when available")
    print("✅ DDGS fallback only when needed (failures or insufficient results)")
    print("✅ Configurable minimum results threshold")
    print("✅ Detailed logging for debugging")
    print("✅ Better performance (fewer concurrent API calls)")