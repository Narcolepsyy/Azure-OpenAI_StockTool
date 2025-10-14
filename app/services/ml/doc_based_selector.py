"""
Document-based tool selector using embedding similarity to tool_usage.md

This provides a fallback when ML classifier isn't trained or has low confidence.
"""
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from cachetools import TTLCache
import json
import re

logger = logging.getLogger(__name__)


class DocBasedToolSelector:
    """
    Tool selector based on embedding similarity to tool documentation.
    
    Uses tool descriptions from tool_usage.md to find relevant tools
    through semantic similarity matching.
    """
    
    def __init__(
        self,
        embedder,  # QueryEmbedder instance
        doc_path: str = "knowledge/tool_usage.md",
        cache_size: int = 100,
        cache_ttl: int = 3600,
        similarity_threshold: float = 0.5
    ):
        """
        Initialize doc-based tool selector.
        
        Args:
            embedder: QueryEmbedder instance for generating embeddings
            doc_path: Path to tool_usage.md documentation
            cache_size: Number of tool embeddings to cache
            cache_ttl: Time-to-live for cache in seconds
            similarity_threshold: Minimum cosine similarity to include tool
        """
        self.embedder = embedder
        self.doc_path = Path(doc_path)
        self.similarity_threshold = similarity_threshold
        
        # Cache for tool description embeddings
        self.tool_embeddings: Dict[str, np.ndarray] = {}
        self.tool_descriptions: Dict[str, str] = {}
        
        # Cache for query results
        self.query_cache: TTLCache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        
        self.initialized = False
        
        logger.info(f"DocBasedToolSelector initialized with threshold={similarity_threshold}")
    
    def _parse_tool_documentation(self) -> Dict[str, str]:
        """
        Parse tool_usage.md to extract tool descriptions.
        
        Returns:
            Dict mapping tool_name -> description text
        """
        if not self.doc_path.exists():
            logger.error(f"Tool documentation not found: {self.doc_path}")
            return {}
        
        try:
            content = self.doc_path.read_text(encoding='utf-8')
            tools = {}
            
            # Split by tool sections (looking for "Tool: tool_name")
            tool_pattern = r'Tool:\s+(\w+)(.*?)(?=Tool:|$)'
            matches = re.finditer(tool_pattern, content, re.DOTALL)
            
            for match in matches:
                tool_name = match.group(1).strip()
                tool_section = match.group(2).strip()
                
                # Extract purpose, input, and tips for better context
                description_parts = []
                
                # Extract purpose line
                purpose_match = re.search(r'-\s*Purpose:\s*(.+?)(?:\n-|$)', tool_section, re.DOTALL)
                if purpose_match:
                    description_parts.append(f"Purpose: {purpose_match.group(1).strip()}")
                
                # Extract parameter descriptions
                input_match = re.search(r'-\s*Input\s*\n(.*?)(?:\n-\s*Returns|$)', tool_section, re.DOTALL)
                if input_match:
                    params = input_match.group(1).strip()
                    description_parts.append(f"Parameters: {params[:200]}")  # Limit length
                
                # Extract tips
                tips_match = re.search(r'-\s*Tips:?\s*(.+?)(?:\n---|$)', tool_section, re.DOTALL)
                if tips_match:
                    description_parts.append(f"Usage tips: {tips_match.group(1).strip()[:200]}")
                
                if description_parts:
                    tools[tool_name] = f"{tool_name}. " + " ".join(description_parts)
                    logger.debug(f"Parsed documentation for tool: {tool_name}")
            
            logger.info(f"Parsed {len(tools)} tool descriptions from documentation")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to parse tool documentation: {e}", exc_info=True)
            return {}
    
    def _initialize(self):
        """Initialize by parsing docs and pre-computing embeddings."""
        if self.initialized:
            return
        
        logger.info("Initializing doc-based tool selector...")
        
        # Parse documentation
        self.tool_descriptions = self._parse_tool_documentation()
        
        if not self.tool_descriptions:
            logger.warning("No tool descriptions found, doc-based selection unavailable")
            return
        
        # Pre-compute embeddings for all tools
        tool_names = list(self.tool_descriptions.keys())
        tool_texts = list(self.tool_descriptions.values())
        
        try:
            # Batch embed all tool descriptions
            logger.info(f"Computing embeddings for {len(tool_texts)} tool descriptions...")
            embeddings = self.embedder.embed_batch(tool_texts)
            
            # Store in dict
            for tool_name, embedding in zip(tool_names, embeddings):
                self.tool_embeddings[tool_name] = embedding
            
            self.initialized = True
            logger.info(f"✅ Doc-based selector initialized with {len(self.tool_embeddings)} tools")
            
        except Exception as e:
            logger.error(f"Failed to compute tool embeddings: {e}", exc_info=True)
    
    def predict_tools(
        self,
        query: str,
        max_tools: int = 5,
        available_tools: Optional[List[str]] = None
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Predict relevant tools based on semantic similarity to documentation.
        
        Args:
            query: User query text
            max_tools: Maximum number of tools to return
            available_tools: Optional list of available tools to filter by
        
        Returns:
            Tuple of (selected_tools, similarity_scores)
        """
        # Lazy initialization
        if not self.initialized:
            self._initialize()
        
        if not self.initialized or not self.tool_embeddings:
            logger.warning("Doc-based selector not initialized, returning empty list")
            return [], {}
        
        # Check cache
        cache_key = f"{query}:{max_tools}:{sorted(available_tools or [])}"
        if cache_key in self.query_cache:
            logger.debug("Query cache hit for doc-based selection")
            return self.query_cache[cache_key]
        
        try:
            # Embed query
            query_embedding = self.embedder.embed(query)
            
            # Compute cosine similarity with all tools
            similarities = {}
            for tool_name, tool_embedding in self.tool_embeddings.items():
                # Filter by available tools if specified
                if available_tools and tool_name not in available_tools:
                    continue
                
                # Cosine similarity
                similarity = np.dot(query_embedding, tool_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(tool_embedding)
                )
                
                # Only include if above threshold
                if similarity >= self.similarity_threshold:
                    similarities[tool_name] = float(similarity)
            
            # Sort by similarity and limit to max_tools
            sorted_tools = sorted(
                similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:max_tools]
            
            selected_tools = [tool for tool, _ in sorted_tools]
            scores = dict(sorted_tools)
            
            # Cache result
            self.query_cache[cache_key] = (selected_tools, scores)
            
            logger.info(
                f"Doc-based selected {len(selected_tools)} tools "
                f"(avg similarity: {np.mean(list(scores.values())):.2f}): {selected_tools}"
            )
            
            return selected_tools, scores
            
        except Exception as e:
            logger.error(f"Doc-based tool prediction failed: {e}", exc_info=True)
            return [], {}
    
    def get_tool_description(self, tool_name: str) -> Optional[str]:
        """Get the documentation description for a tool."""
        if not self.initialized:
            self._initialize()
        return self.tool_descriptions.get(tool_name)
    
    def explain_selection(
        self,
        query: str,
        selected_tools: List[str],
        scores: Dict[str, float]
    ) -> str:
        """
        Generate human-readable explanation of tool selection.
        
        Args:
            query: Original query
            selected_tools: List of selected tool names
            scores: Similarity scores for each tool
        
        Returns:
            Explanation text
        """
        if not selected_tools:
            return "No tools selected (no matches above similarity threshold)"
        
        explanation = f"For query '{query[:50]}...', selected {len(selected_tools)} tools:\n\n"
        
        for tool in selected_tools:
            score = scores.get(tool, 0.0)
            desc = self.tool_descriptions.get(tool, "No description available")
            
            # Extract just the purpose line for brevity
            purpose_match = re.search(r'Purpose:\s*(.+?)(?:\.|Parameters)', desc)
            purpose = purpose_match.group(1) if purpose_match else desc[:100]
            
            explanation += f"- {tool} (similarity: {score:.2f}): {purpose}\n"
        
        return explanation
    
    def refresh_cache(self):
        """Clear query cache (useful after updating documentation)."""
        size = len(self.query_cache)
        self.query_cache.clear()
        logger.info(f"Cleared {size} cached queries")
        
        # Also re-parse documentation
        self.initialized = False
        self._initialize()


def get_doc_based_selector(embedder) -> DocBasedToolSelector:
    """
    Factory function to get doc-based selector.
    
    Args:
        embedder: QueryEmbedder instance
    
    Returns:
        DocBasedToolSelector instance
    """
    return DocBasedToolSelector(embedder)
