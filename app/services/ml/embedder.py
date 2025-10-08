"""Query embedding service for semantic understanding."""
import logging
import numpy as np
from typing import Optional, Dict
from openai import OpenAI
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class QueryEmbedder:
    """
    Converts queries to semantic embeddings for ML-based tool selection.
    
    Uses OpenAI's text-embedding-3-small model for fast, high-quality embeddings.
    Includes caching to avoid redundant API calls.
    """
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        cache_size: int = 1000,
        cache_ttl: int = 3600
    ):
        """
        Initialize query embedder.
        
        Args:
            model: OpenAI embedding model to use
            cache_size: Maximum number of cached embeddings
            cache_ttl: Time-to-live for cached embeddings in seconds
        """
        self.client = OpenAI()  # Uses OPENAI_API_KEY env var
        self.model = model
        self.cache: TTLCache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        self.embedding_dim = 1536  # text-embedding-3-small dimension
        
        logger.info(
            f"Initialized QueryEmbedder with model={model}, "
            f"cache_size={cache_size}, ttl={cache_ttl}s"
        )
    
    def embed(self, query: str) -> np.ndarray:
        """
        Convert query to semantic vector.
        
        Args:
            query: User query text
        
        Returns:
            NumPy array of shape (embedding_dim,)
        
        Raises:
            Exception: If embedding fails
        """
        # Check cache first
        if query in self.cache:
            logger.debug(f"Embedding cache hit for query: {query[:50]}")
            return self.cache[query]
        
        try:
            # Call OpenAI API
            response = self.client.embeddings.create(
                input=query,
                model=self.model
            )
            
            # Extract embedding
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Cache for future use
            self.cache[query] = embedding
            
            logger.debug(
                f"Generated embedding for query: {query[:50]} "
                f"(dim={len(embedding)})"
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for query '{query[:50]}': {e}")
            raise
    
    def embed_batch(self, queries: list[str]) -> np.ndarray:
        """
        Convert multiple queries to embeddings (more efficient).
        
        Args:
            queries: List of query texts
        
        Returns:
            NumPy array of shape (num_queries, embedding_dim)
        """
        if not queries:
            return np.array([]).reshape(0, self.embedding_dim)
        
        # Check which queries need embedding
        embeddings = []
        queries_to_embed = []
        indices_to_embed = []
        
        for i, query in enumerate(queries):
            if query in self.cache:
                embeddings.append(self.cache[query])
            else:
                queries_to_embed.append(query)
                indices_to_embed.append(i)
                embeddings.append(None)  # Placeholder
        
        # Batch embed queries not in cache
        if queries_to_embed:
            try:
                response = self.client.embeddings.create(
                    input=queries_to_embed,
                    model=self.model
                )
                
                # Fill in the embeddings
                for i, data in enumerate(response.data):
                    embedding = np.array(data.embedding, dtype=np.float32)
                    query = queries_to_embed[i]
                    original_index = indices_to_embed[i]
                    
                    # Cache it
                    self.cache[query] = embedding
                    
                    # Add to result
                    embeddings[original_index] = embedding
                
                logger.debug(
                    f"Generated {len(queries_to_embed)} embeddings, "
                    f"{len(queries) - len(queries_to_embed)} from cache"
                )
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                raise
        
        return np.array(embeddings, dtype=np.float32)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.cache.maxsize,
            "ttl": self.cache.ttl
        }
    
    def clear_cache(self) -> int:
        """Clear embedding cache."""
        size = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {size} cached embeddings")
        return size
