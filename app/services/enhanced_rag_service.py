"""Enhanced RAG service with web search integration for augmented context retrieval."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from functools import lru_cache
from app.services.rag_service import rag_search as kb_search, get_rag_status
from app.services.perplexity_web_search import perplexity_web_search
from app.core.config import RAG_ENABLED

logger = logging.getLogger(__name__)

class EnhancedRAGService:
    """Enhanced RAG service that combines knowledge base and web search results."""
    
    def __init__(self):
        self.kb_weight = 0.7  # Weight for knowledge base results
        self.web_weight = 0.3  # Weight for web search results
        
    async def augmented_search(
        self,
        query: str,
        kb_k: int = 3,
        web_results: int = 5,
        include_web: bool = True,
        web_content: bool = True,
        max_total_chunks: int = 8
    ) -> Dict[str, Any]:
        """
        Perform augmented RAG search combining knowledge base and web results.
        
        Args:
            query: Search query
            kb_k: Number of knowledge base chunks to retrieve
            web_results: Number of web search results
            include_web: Whether to include web search
            web_content: Whether to fetch full content from web pages
            max_total_chunks: Maximum total chunks to return
            
        Returns:
            Combined search results with sources
        """
        start_time = datetime.now()
        results = {
            'query': query,
            'timestamp': start_time.isoformat(),
            'sources': {
                'knowledge_base': {'enabled': RAG_ENABLED, 'count': 0, 'results': []},
                'web_search': {'enabled': include_web, 'count': 0, 'results': []}
            },
            'combined_chunks': [],
            'total_chunks': 0,
            'strategy': 'augmented_rag'
        }
        
        # 1. Search knowledge base
        if RAG_ENABLED:
            try:
                kb_results = kb_search(query, k=kb_k)
                if kb_results.get('enabled') and kb_results.get('results'):
                    results['sources']['knowledge_base'] = kb_results
                    
                    # Convert KB results to standardized format
                    for idx, kb_item in enumerate(kb_results['results']):
                        chunk = {
                            'source': 'knowledge_base',
                            'title': kb_item.get('metadata', {}).get('path', f"KB Document {idx+1}"),
                            'content': kb_item['text'],
                            'relevance_score': kb_item.get('score', 1.0) * self.kb_weight,
                            'metadata': kb_item.get('metadata', {}),
                            'type': 'knowledge_base'
                        }
                        results['combined_chunks'].append(chunk)
                        
            except Exception as e:
                logger.error(f"Knowledge base search error: {e}")
                results['sources']['knowledge_base']['error'] = str(e)
        
        # 2. Search web if enabled (use optimized search)
        if include_web:
            try:
                # Use Perplexity search for better performance  
                web_results_data = perplexity_web_search(
                    query=query,
                    max_results=web_results, 
                    synthesize_answer=False,
                    include_recent=True
                )
                
                if web_results_data.get('sources'):
                    results['sources']['web_search'] = {
                        'enabled': True,
                        'count': len(web_results_data['sources']),
                        'results': web_results_data['sources'],
                        'method': web_results_data.get('method', 'perplexity'),
                        'duration': web_results_data.get('total_time', 0)
                    }
                    
                    # Convert Perplexity results to standardized format
                    for web_item in web_results_data['sources']:
                        # Use snippet as content (alternative search provides good snippets)
                        content = web_item.get('snippet', '') or web_item.get('content', '')
                        
                        # Include results even with minimal content (they provide valuable links)
                        if web_item.get('title'):  
                            chunk = {
                                'source': 'web_search',
                                'title': web_item.get('title', 'Web Result'),
                                'url': web_item.get('url'),
                                'content': content or f"Search result: {web_item.get('title')}",
                                'snippet': web_item.get('snippet', ''),
                                'relevance_score': web_item.get('relevance_score', 1.0) * self.web_weight,
                                'timestamp': web_item.get('timestamp'),
                                'type': 'web_search',
                                'search_source': web_item.get('source', 'unknown')
                            }
                            results['combined_chunks'].append(chunk)
                            
            except Exception as e:
                logger.error(f"Web search error: {e}")
                results['sources']['web_search']['error'] = str(e)
        
        # 3. Rank and limit results
        results['combined_chunks'] = self._rank_and_limit_chunks(
            results['combined_chunks'], 
            max_total_chunks
        )
        
        results['total_chunks'] = len(results['combined_chunks'])
        results['sources']['knowledge_base']['count'] = len([c for c in results['combined_chunks'] if c['source'] == 'knowledge_base'])
        results['sources']['web_search']['count'] = len([c for c in results['combined_chunks'] if c['source'] == 'web_search'])
        
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = duration
        
        logger.info(f"Augmented RAG search for '{query[:50]}...': KB={results['sources']['knowledge_base']['count']}, Web={results['sources']['web_search']['count']}")
        
        return results
    
    def _rank_and_limit_chunks(self, chunks: List[Dict[str, Any]], max_chunks: int) -> List[Dict[str, Any]]:
        """Rank chunks by relevance score and limit to max_chunks."""
        # Sort by relevance score (descending)
        chunks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Ensure we have a good mix of sources if both are available
        kb_chunks = [c for c in chunks if c['source'] == 'knowledge_base']
        web_chunks = [c for c in chunks if c['source'] == 'web_search']
        
        if kb_chunks and web_chunks and max_chunks >= 4:
            # Ensure at least 1 from each source, then fill with highest scores
            selected = []
            
            # Add top KB chunk
            if kb_chunks:
                selected.append(kb_chunks[0])
                kb_chunks = kb_chunks[1:]
            
            # Add top web chunk
            if web_chunks:
                selected.append(web_chunks[0])
                web_chunks = web_chunks[1:]
            
            # Fill remaining slots with highest scores
            remaining = kb_chunks + web_chunks
            remaining.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            selected.extend(remaining[:max_chunks - len(selected)])
            
            return selected
        else:
            # Simple case: just take top max_chunks
            return chunks[:max_chunks]
    
    async def search_financial_context(
        self,
        query: str,
        symbol: Optional[str] = None,
        include_news: bool = True,
        kb_k: int = 3,
        web_results: int = 4
    ) -> Dict[str, Any]:
        """
        Specialized search for financial context, combining knowledge base, web search, and news.
        
        Args:
            query: Financial query
            symbol: Stock symbol (if applicable)
            include_news: Whether to include recent news
            kb_k: Knowledge base results
            web_results: Web search results
            
        Returns:
            Enhanced financial context
        """
        # Enhance query with financial terms
        enhanced_query = query
        if symbol:
            enhanced_query = f"{symbol} {query}"
        
        # Add financial context terms if not present
        financial_terms = ['financial', 'stock', 'market', 'investment', 'trading', 'analysis']
        if not any(term in query.lower() for term in financial_terms):
            enhanced_query += " financial market analysis"
        
        # Perform augmented search
        results = await self.augmented_search(
            query=enhanced_query,
            kb_k=kb_k,
            web_results=web_results,
            include_web=True,
            web_content=True,
            max_total_chunks=8
        )
        
        # Add news search if requested and symbol provided
        if include_news and symbol:
            try:
                news_query = f"{symbol} stock news earnings"
                news_results = perplexity_web_search(
                    query=f"{news_query} latest news",
                    max_results=3,
                    synthesize_answer=False,
                    include_recent=True
                )
                
                if news_results.get('sources'):
                    # Add news as separate source
                    results['sources']['recent_news'] = {
                        'enabled': True,
                        'count': len(news_results['sources']),
                        'results': news_results['sources']
                    }
                    
                    # Add top news items to combined chunks
                    for news_item in news_results['sources'][:2]:  # Limit to top 2 news items
                        if news_item.get('content'):
                            chunk = {
                                'source': 'recent_news',
                                'title': news_item.get('title', 'Recent News'),
                                'url': news_item.get('url'),
                                'content': news_item['content'][:2000],  # Truncate for context
                                'relevance_score': 0.8,  # High relevance for recent news
                                'timestamp': news_item.get('timestamp'),
                                'type': 'recent_news',
                                'symbol': symbol
                            }
                            results['combined_chunks'].append(chunk)
                    
                    # Re-rank with news included
                    results['combined_chunks'] = self._rank_and_limit_chunks(
                        results['combined_chunks'], 
                        10  # Allow more for financial context
                    )
                    results['total_chunks'] = len(results['combined_chunks'])
                    
            except Exception as e:
                logger.warning(f"News search failed for {symbol}: {e}")
        
        results['strategy'] = 'financial_augmented_rag'
        results['symbol'] = symbol
        
        return results
    
    def format_context_for_llm(self, search_results: Dict[str, Any], max_context_length: int = 4000) -> str:
        """
        Format augmented search results into context string for LLM.
        
        Args:
            search_results: Results from augmented_search or search_financial_context
            max_context_length: Maximum length of context string
            
        Returns:
            Formatted context string
        """
        if not search_results.get('combined_chunks'):
            return ""
        
        context_parts = []
        context_parts.append("=== RETRIEVED CONTEXT ===\n")
        
        current_length = len(context_parts[0])
        
        for chunk in search_results['combined_chunks']:
            source = chunk['source']
            title = chunk.get('title', 'Unknown')
            content = chunk.get('content', '')
            
            # Format based on source type
            if source == 'knowledge_base':
                chunk_text = f"\n[KNOWLEDGE BASE] {title}\n{content}\n"
            elif source == 'web_search':
                url = chunk.get('url', '')
                chunk_text = f"\n[WEB SEARCH] {title}\nURL: {url}\n{content}\n"
            elif source == 'recent_news':
                url = chunk.get('url', '')
                timestamp = chunk.get('timestamp', '')
                chunk_text = f"\n[RECENT NEWS] {title}\nURL: {url}\nTime: {timestamp}\n{content}\n"
            else:
                chunk_text = f"\n[{source.upper()}] {title}\n{content}\n"
            
            # Check if adding this chunk would exceed limit
            if current_length + len(chunk_text) > max_context_length:
                if current_length < max_context_length * 0.8:  # Only truncate if we haven't used most space
                    # Truncate this chunk to fit
                    remaining_space = max_context_length - current_length - 50  # Leave some buffer
                    if remaining_space > 100:  # Only include if meaningful space left
                        truncated_content = content[:remaining_space] + "..."
                        chunk_text = chunk_text.replace(content, truncated_content)
                        context_parts.append(chunk_text)
                break
            
            context_parts.append(chunk_text)
            current_length += len(chunk_text)
        
        context_parts.append("\n=== END CONTEXT ===")
        
        return ''.join(context_parts)

# Global enhanced RAG service instance
_enhanced_rag_service = None

def get_enhanced_rag_service() -> EnhancedRAGService:
    """Get or create the global enhanced RAG service instance."""
    global _enhanced_rag_service
    if _enhanced_rag_service is None:
        _enhanced_rag_service = EnhancedRAGService()
    return _enhanced_rag_service

# Convenience functions
def augmented_rag_search(query: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for augmented RAG search."""
    import asyncio
    service = get_enhanced_rag_service()
    
    # Run the async method properly
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in an event loop, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, service.augmented_search(query, **kwargs))
                return future.result()
        else:
            return loop.run_until_complete(service.augmented_search(query, **kwargs))
    except RuntimeError:
        # No event loop exists
        return asyncio.run(service.augmented_search(query, **kwargs))

def financial_context_search(query: str, symbol: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function for financial context search."""
    import asyncio
    service = get_enhanced_rag_service()
    
    # Run the async method properly
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in an event loop, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, service.search_financial_context(query, symbol, **kwargs))
                return future.result()
        else:
            return loop.run_until_complete(service.search_financial_context(query, symbol, **kwargs))
    except RuntimeError:
        # No event loop exists
        return asyncio.run(service.search_financial_context(query, symbol, **kwargs))