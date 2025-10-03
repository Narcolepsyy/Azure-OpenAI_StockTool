"""
Simplified Brave Search implementation with country parameter support
"""
import logging
import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional
from app.core.config import BRAVE_API_KEY

logger = logging.getLogger(__name__)

class SimpleBraveSearchClient:
    """Simplified Brave Search client with country parameter"""
    
    def __init__(self):
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        self._rate_lock = asyncio.Lock()
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 1 second between requests
    
    async def search(
        self, 
        query: str, 
        count: int = 10, 
        country: Optional[str] = None,
        safesearch: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """
        Simple Brave Search with basic parameters
        
        Args:
            query: Search query
            count: Number of results (1-20)
            country: Country code (e.g., 'US', 'JP', 'GB') or None for global
            safesearch: Safe search level ('strict', 'moderate', 'off')
        
        Returns:
            List of search results
        """
        if not BRAVE_API_KEY:
            logger.error("BRAVE_API_KEY not configured")
            return []
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                # Rate limiting
                async with self._rate_lock:
                    current_time = time.time()
                    time_since_last = current_time - self._last_request_time
                    
                    if time_since_last < self._min_request_interval:
                        sleep_time = self._min_request_interval - time_since_last
                        await asyncio.sleep(sleep_time)
                    
                    self._last_request_time = time.time()
                
                # Build parameters
                params = {
                    'q': query.strip(),
                    'count': min(max(count, 1), 20),
                    'safesearch': safesearch,
                    'text_decorations': 'false'  # Use string instead of boolean
                }
                
                # Add country if specified
                if country and country.upper() != "ALL":
                    params['country'] = country.upper()
                
                logger.info(f"Brave Search: '{query}' (country: {country})")
                logger.debug(f"Parameters: {params}")
                
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = self._parse_results(data)
                        logger.info(f"Brave Search returned {len(results)} results")
                        return results
                    
                    elif response.status == 422:
                        logger.warning("Parameter validation error, retrying with minimal params")
                        # Retry with just query and count
                        minimal_params = {'q': query.strip(), 'count': min(count, 10)}
                        
                        async with session.get(self.base_url, params=minimal_params) as retry_response:
                            if retry_response.status == 200:
                                data = await retry_response.json()
                                results = self._parse_results(data)
                                logger.info(f"Brave Search retry: {len(results)} results")
                                return results
                    
                    else:
                        logger.error(f"Brave Search API error: {response.status}")
                        if response.status == 429:
                            logger.warning("Rate limit exceeded")
                        elif response.status == 401:
                            logger.error("Invalid API key")
                        return []
            
            except Exception as e:
                logger.error(f"Brave Search error: {e}")
                return []
    
    def _parse_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Brave API response"""
        results = []
        web_results = data.get('web', {}).get('results', [])
        
        for result in web_results:
            parsed_result = {
                'title': result.get('title', '').strip(),
                'url': result.get('url', ''),
                'description': result.get('description', '').strip(),
                'published': result.get('published')
            }
            
            # Only add if we have minimum required fields
            if parsed_result['title'] and parsed_result['url']:
                results.append(parsed_result)
        
        return results

# Convenience function for simple usage
async def simple_brave_search(
    query: str, 
    count: int = 10, 
    country: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Simple function to perform Brave search
    
    Args:
        query: Search query
        count: Number of results
        country: Country code (e.g., 'US', 'JP', 'GB')
    
    Returns:
        List of search results
    """
    client = SimpleBraveSearchClient()
    return await client.search(query, count, country)