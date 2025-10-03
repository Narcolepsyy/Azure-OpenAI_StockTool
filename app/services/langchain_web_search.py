"""
LangChain-based web search service with advanced capabilities.
Provides structured search with retry logic, caching, and result ranking.
"""
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib
import re
from collections import Counter
import math

logger = logging.getLogger(__name__)

# LangChain imports
try:
    from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
    from langchain_community.tools import DuckDuckGoSearchResults
    from langchain.agents import AgentType, initialize_agent, Tool
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not installed. Install with: pip install langchain langchain-community langchain-openai")
    LANGCHAIN_AVAILABLE = False

# Brave Search (premium alternative)
try:
    from langchain_community.utilities import BraveSearchWrapper
    BRAVE_AVAILABLE = True
except ImportError:
    BRAVE_AVAILABLE = False
    logger.debug("Brave Search not available - install langchain-community for full support")

# Caching
from cachetools import TTLCache

# Cache configuration
SEARCH_CACHE = TTLCache(maxsize=500, ttl=1800)  # 30 min cache
SYNTHESIS_CACHE = TTLCache(maxsize=200, ttl=3600)  # 1 hour cache

# Environment configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
LANGCHAIN_VERBOSE = os.getenv("LANGCHAIN_VERBOSE", "false").lower() == "true"


@dataclass
class LangChainSearchResult:
    """Structured search result from LangChain."""
    title: str
    url: str
    snippet: str
    source: str = "langchain"
    relevance_score: float = 0.0
    timestamp: Optional[str] = None
    citation_id: int = 0


@dataclass
class LangChainSearchResponse:
    """Complete search response with synthesis."""
    query: str
    answer: str
    results: List[LangChainSearchResult]
    citations: List[Dict[str, Any]]
    search_time: float
    synthesis_time: float
    total_time: float
    result_count: int
    source_engine: str


class LangChainWebSearchService:
    """
    Web search service using LangChain framework.
    
    Features:
    - Multiple search backends (DuckDuckGo, Brave)
    - Automatic retry and fallback
    - Result caching
    - AI-powered answer synthesis
    - Citation management
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        brave_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_results: int = 10,
        verbose: bool = False
    ):
        """
        Initialize LangChain web search service.
        
        Args:
            openai_api_key: OpenAI API key for synthesis
            brave_api_key: Brave Search API key (optional)
            model: OpenAI model for synthesis
            temperature: Model temperature
            max_results: Maximum search results
            verbose: Enable verbose logging
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required. Install: pip install langchain langchain-community langchain-openai")
        
        self.openai_api_key = openai_api_key or OPENAI_API_KEY
        self.brave_api_key = brave_api_key or BRAVE_API_KEY
        self.model = model
        self.temperature = temperature
        self.max_results = max_results
        self.verbose = verbose or LANGCHAIN_VERBOSE
        
        # Initialize LLM for synthesis
        if self.openai_api_key:
            self.llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                openai_api_key=self.openai_api_key,
                timeout=20.0
            )
            # Initialize embeddings for semantic scoring
            try:
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=self.openai_api_key,
                    model="text-embedding-3-small"
                )
                logger.debug("Embeddings initialized for semantic scoring")
            except Exception as e:
                logger.warning(f"Failed to initialize embeddings: {e}")
                self.embeddings = None
        else:
            logger.warning("No OpenAI API key - synthesis and embeddings will be disabled")
            self.llm = None
            self.embeddings = None
        
        # Initialize search tools
        self.search_tools = self._initialize_search_tools()
        
        logger.info(f"LangChain search initialized with {len(self.search_tools)} search backends")
    
    def _initialize_search_tools(self) -> List[Tool]:
        """Initialize available search tools."""
        tools = []
        
        # DuckDuckGo Search (always available)
        try:
            ddg_search = DuckDuckGoSearchAPIWrapper(max_results=self.max_results)
            ddg_tool = DuckDuckGoSearchResults(api_wrapper=ddg_search)
            tools.append(Tool(
                name="duckduckgo_search",
                func=ddg_tool.run,
                description="Search DuckDuckGo for recent information, news, and general queries"
            ))
            logger.debug("DuckDuckGo search tool initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize DuckDuckGo: {e}")
        
        # Brave Search (premium, if available)
        if BRAVE_AVAILABLE and self.brave_api_key:
            try:
                brave_search = BraveSearchWrapper(api_key=self.brave_api_key)
                tools.append(Tool(
                    name="brave_search",
                    func=brave_search.run,
                    description="Search Brave for high-quality, recent results with enhanced relevance"
                ))
                logger.debug("Brave search tool initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Brave Search: {e}")
        
        return tools
    
    def _get_cache_key(self, query: str, synthesize: bool) -> str:
        """Generate cache key for query."""
        key_str = f"{query}:{synthesize}:{self.max_results}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        synthesize_answer: bool = True,
        include_recent: bool = True,
        prefer_brave: bool = True
    ) -> Dict[str, Any]:
        """
        Perform web search with LangChain.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            synthesize_answer: Whether to generate AI summary
            include_recent: Prioritize recent content
            prefer_brave: Prefer Brave Search if available
            
        Returns:
            LangChainSearchResponse as dict
        """
        start_time = datetime.now()
        
        # Check cache
        cache_key = self._get_cache_key(query, synthesize_answer)
        if cache_key in SEARCH_CACHE:
            logger.debug(f"Cache HIT for query: {query[:60]}")
            return SEARCH_CACHE[cache_key]
        
        try:
            # Perform search
            search_start = datetime.now()
            results = await self._execute_search(
                query=query,
                max_results=max_results or self.max_results,
                prefer_brave=prefer_brave
            )
            
            # Calculate relevance scores (BM25 + semantic)
            if results:
                results = await self._calculate_relevance_scores(query, results)
            
            search_time = (datetime.now() - search_start).total_seconds()
            
            # Synthesize answer
            synthesis_start = datetime.now()
            answer = ""
            citations = []
            
            if synthesize_answer and self.llm and results:
                answer, citations = await self._synthesize_answer(query, results)
            
            synthesis_time = (datetime.now() - synthesis_start).total_seconds()
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Build response
            response = LangChainSearchResponse(
                query=query,
                answer=answer,
                results=results,
                citations=citations,
                search_time=search_time,
                synthesis_time=synthesis_time,
                total_time=total_time,
                result_count=len(results),
                source_engine=self._get_engine_used(results)
            )
            
            # Convert to dict
            response_dict = {
                "query": response.query,
                "answer": response.answer,
                "results": [asdict(r) for r in response.results],
                "citations": response.citations,
                "search_time": response.search_time,
                "synthesis_time": response.synthesis_time,
                "total_time": response.total_time,
                "result_count": response.result_count,
                "source_engine": response.source_engine
            }
            
            # Cache result
            SEARCH_CACHE[cache_key] = response_dict
            
            logger.info(
                f"LangChain search completed: {len(results)} results in {total_time:.2f}s "
                f"(search: {search_time:.2f}s, synthesis: {synthesis_time:.2f}s)"
            )
            
            return response_dict
            
        except Exception as e:
            logger.error(f"LangChain search error: {e}", exc_info=True)
            return {
                "query": query,
                "answer": f"Search error: {str(e)}",
                "results": [],
                "citations": [],
                "search_time": 0.0,
                "synthesis_time": 0.0,
                "total_time": (datetime.now() - start_time).total_seconds(),
                "result_count": 0,
                "source_engine": "error"
            }
    
    async def _execute_search(
        self,
        query: str,
        max_results: int,
        prefer_brave: bool
    ) -> List[LangChainSearchResult]:
        """Execute search with retry and fallback logic."""
        results = []
        
        # Determine search order
        search_order = []
        if prefer_brave and any(t.name == "brave_search" for t in self.search_tools):
            search_order = ["brave_search", "duckduckgo_search"]
        else:
            search_order = ["duckduckgo_search", "brave_search"]
        
        # Try each search backend
        for tool_name in search_order:
            tool = next((t for t in self.search_tools if t.name == tool_name), None)
            if not tool:
                continue
            
            try:
                logger.debug(f"Trying {tool_name} for query: {query[:60]}")
                
                # Execute search (synchronous tools need to be run in executor)
                raw_results = await asyncio.get_event_loop().run_in_executor(
                    None, tool.func, query
                )
                
                # Parse results
                parsed = self._parse_search_results(raw_results, tool_name)
                if parsed:
                    results.extend(parsed[:max_results])
                    logger.debug(f"{tool_name} returned {len(parsed)} results")
                    break  # Success - stop trying other backends
                    
            except Exception as e:
                logger.warning(f"{tool_name} failed: {e}")
                continue
        
        # Assign citation IDs
        for idx, result in enumerate(results, 1):
            result.citation_id = idx
        
        return results[:max_results]
    
    def _parse_search_results(
        self,
        raw_results: Any,
        source: str
    ) -> List[LangChainSearchResult]:
        """Parse raw search results into structured format."""
        parsed = []
        
        try:
            # Handle string results (common format)
            if isinstance(raw_results, str):
                # Try to parse as list of dicts
                import json
                try:
                    results_list = json.loads(raw_results)
                except (json.JSONDecodeError, TypeError):
                    # Parse as formatted text
                    results_list = self._parse_text_results(raw_results)
            elif isinstance(raw_results, list):
                results_list = raw_results
            else:
                logger.warning(f"Unexpected result type: {type(raw_results)}")
                return []
            
            # Convert to LangChainSearchResult
            for item in results_list:
                if isinstance(item, dict):
                    parsed.append(LangChainSearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", item.get("link", "")),
                        snippet=item.get("snippet", item.get("description", "")),
                        source=source,
                        relevance_score=0.0,  # Will be calculated later with BM25 + embeddings
                        timestamp=None
                    ))
                elif isinstance(item, str):
                    # Plain text result
                    parsed.append(LangChainSearchResult(
                        title="Search Result",
                        url="",
                        snippet=item[:500],
                        source=source,
                        relevance_score=0.0  # Will be calculated later
                    ))
            
        except Exception as e:
            logger.error(f"Failed to parse {source} results: {e}")
        
        return parsed
    
    def _parse_text_results(self, text: str) -> List[Dict[str, str]]:
        """
        Parse text-formatted search results from DuckDuckGo.
        Format: snippet: ... , title: ... , link: ... , snippet: ... , title: ... , link: ...
        """
        results = []
        
        # Split by the pattern ", snippet:" which marks the start of a new result
        parts = text.split(", snippet:")
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            # For the first part, it already has "snippet:" at the start
            # For subsequent parts, we need to add it back
            if i > 0:
                part = "snippet:" + part
            
            result = {}
            
            # Extract snippet (before ", title:")
            if ", title:" in part:
                snippet_part, rest = part.split(", title:", 1)
                result["snippet"] = snippet_part.replace("snippet:", "").strip()
                
                # Extract title (before ", link:")
                if ", link:" in rest:
                    title_part, link_part = rest.split(", link:", 1)
                    result["title"] = title_part.strip()
                    result["url"] = link_part.strip()
                else:
                    result["title"] = rest.strip()
            else:
                # Fallback: no structured format found
                result["snippet"] = part.replace("snippet:", "").strip()
                result["title"] = "Search Result"
                result["url"] = ""
            
            # Only add if we have meaningful content
            if result.get("snippet") or result.get("title"):
                results.append(result)
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25 scoring."""
        # Simple word tokenization (could be enhanced with proper NLP)
        text = text.lower()
        # Remove punctuation and split
        words = re.findall(r'\w+', text)
        return words
    
    def _calculate_bm25_score(
        self,
        query: str,
        document: str,
        k1: float = 1.5,
        b: float = 0.75,
        avgdl: float = 100.0
    ) -> float:
        """
        Calculate BM25 score for a document given a query.
        
        Args:
            query: Search query
            document: Document text (title + snippet)
            k1: BM25 k1 parameter (term frequency saturation)
            b: BM25 b parameter (length normalization)
            avgdl: Average document length
            
        Returns:
            BM25 score (higher is better)
        """
        query_terms = self._tokenize(query)
        doc_terms = self._tokenize(document)
        doc_length = len(doc_terms)
        
        # Count term frequencies
        doc_tf = Counter(doc_terms)
        
        score = 0.0
        for term in query_terms:
            if term in doc_tf:
                tf = doc_tf[term]
                # Simplified IDF (assume all terms are equally important)
                idf = 1.0
                
                # BM25 formula
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_length / avgdl))
                score += idf * (numerator / denominator)
        
        return score
    
    async def _calculate_semantic_score(
        self,
        query: str,
        document: str
    ) -> float:
        """
        Calculate semantic similarity using embeddings.
        
        Args:
            query: Search query
            document: Document text
            
        Returns:
            Cosine similarity score [0, 1]
        """
        if not self.embeddings:
            return 0.0
        
        try:
            # Get embeddings
            query_embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.embeddings.embed_query(query)
            )
            doc_embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.embeddings.embed_query(document)
            )
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(query_embedding, doc_embedding))
            norm_query = math.sqrt(sum(a * a for a in query_embedding))
            norm_doc = math.sqrt(sum(b * b for b in doc_embedding))
            
            if norm_query == 0 or norm_doc == 0:
                return 0.0
            
            similarity = dot_product / (norm_query * norm_doc)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.warning(f"Semantic scoring failed: {e}")
            return 0.0
    
    async def _calculate_relevance_scores(
        self,
        query: str,
        results: List[LangChainSearchResult],
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6
    ) -> List[LangChainSearchResult]:
        """
        Calculate hybrid relevance scores for search results.
        
        Args:
            query: Search query
            results: List of search results
            bm25_weight: Weight for BM25 score
            semantic_weight: Weight for semantic score
            
        Returns:
            Results with updated relevance scores (sorted by score)
        """
        if not results:
            return results
        
        # Calculate average document length for BM25
        avgdl = sum(len(self._tokenize(r.title + " " + r.snippet)) for r in results) / len(results)
        
        # Score each result
        scored_results = []
        for result in results:
            document = f"{result.title} {result.snippet}"
            
            # BM25 score
            bm25_score = self._calculate_bm25_score(query, document, avgdl=avgdl)
            
            # Semantic score (if embeddings available)
            semantic_score = 0.0
            if self.embeddings:
                semantic_score = await self._calculate_semantic_score(query, document)
            
            # Normalize BM25 score to [0, 1] range (using sigmoid-like function)
            bm25_normalized = 2 / (1 + math.exp(-bm25_score / 5)) - 1
            
            # Calculate hybrid score
            if self.embeddings:
                hybrid_score = (bm25_weight * bm25_normalized) + (semantic_weight * semantic_score)
            else:
                # If no embeddings, use only BM25
                hybrid_score = bm25_normalized
            
            result.relevance_score = round(hybrid_score, 3)
            scored_results.append(result)
        
        # Sort by relevance score (highest first)
        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.debug(f"Relevance scoring: BM25={bm25_weight}, Semantic={semantic_weight}")
        
        return scored_results
    
    async def _synthesize_answer(
        self,
        query: str,
        results: List[LangChainSearchResult]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Synthesize answer from search results using LLM."""
        if not results:
            return "No search results found.", []
        
        # Check synthesis cache
        synthesis_key = hashlib.md5(f"{query}:{len(results)}".encode()).hexdigest()
        if synthesis_key in SYNTHESIS_CACHE:
            logger.debug("Synthesis cache HIT")
            return SYNTHESIS_CACHE[synthesis_key]
        
        try:
            # Build context from results
            context = self._build_context(results)
            
            # Create synthesis prompt
            prompt_template = PromptTemplate(
                input_variables=["query", "context"],
                template="""You are a helpful research assistant. Answer the user's query based on the provided search results.

Query: {query}

Search Results:
{context}

Instructions:
- Provide a clear, comprehensive answer
- Cite sources using [number] format (e.g., [1], [2])
- Use Markdown formatting
- Keep response concise but complete
- If results are insufficient, acknowledge the limitation

Answer:"""
            )
            
            # Create and run chain
            chain = LLMChain(llm=self.llm, prompt=prompt_template, verbose=self.verbose)
            
            # Run synthesis
            answer = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: chain.run(query=query, context=context)
            )
            
            # Extract citations
            citations = self._extract_citations(answer, results)
            
            # Cache result
            SYNTHESIS_CACHE[synthesis_key] = (answer, citations)
            
            return answer, citations
            
        except Exception as e:
            logger.error(f"Synthesis error: {e}", exc_info=True)
            return f"Found {len(results)} results but synthesis failed: {str(e)}", []
    
    def _build_context(self, results: List[LangChainSearchResult]) -> str:
        """Build context string from search results."""
        context_parts = []
        
        for idx, result in enumerate(results, 1):
            part = f"[{idx}] {result.title}\n"
            if result.url:
                part += f"URL: {result.url}\n"
            part += f"Content: {result.snippet[:500]}\n"
            context_parts.append(part)
        
        return "\n".join(context_parts)
    
    def _extract_citations(
        self,
        answer: str,
        results: List[LangChainSearchResult]
    ) -> List[Dict[str, Any]]:
        """Extract citation metadata from results."""
        citations = []
        
        for result in results:
            if result.url:
                citations.append({
                    "id": result.citation_id,
                    "url": result.url,
                    "title": result.title,
                    "snippet": result.snippet[:200]
                })
        
        return citations
    
    def _get_engine_used(self, results: List[LangChainSearchResult]) -> str:
        """Determine which search engine was used."""
        if not results:
            return "none"
        
        sources = set(r.source for r in results)
        if "brave_search" in sources:
            return "brave"
        elif "duckduckgo_search" in sources:
            return "duckduckgo"
        else:
            return "unknown"


# Convenience function for direct usage
async def langchain_web_search(
    query: str,
    max_results: int = 10,
    synthesize_answer: bool = True,
    prefer_brave: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Perform web search using LangChain.
    
    Args:
        query: Search query
        max_results: Maximum results
        synthesize_answer: Whether to generate AI summary
        prefer_brave: Prefer Brave Search if available
        **kwargs: Additional arguments for LangChainWebSearchService
        
    Returns:
        Search response dict
    """
    service = LangChainWebSearchService(
        max_results=max_results,
        **kwargs
    )
    
    return await service.search(
        query=query,
        max_results=max_results,
        synthesize_answer=synthesize_answer,
        prefer_brave=prefer_brave
    )


# Synchronous wrapper for compatibility
def langchain_web_search_sync(
    query: str,
    max_results: int = 10,
    synthesize_answer: bool = True,
    prefer_brave: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Synchronous wrapper for langchain_web_search."""
    return asyncio.run(langchain_web_search(
        query=query,
        max_results=max_results,
        synthesize_answer=synthesize_answer,
        prefer_brave=prefer_brave,
        **kwargs
    ))
