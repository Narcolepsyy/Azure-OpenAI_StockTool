"""Enhanced web search API routes with Perplexity-style functionality."""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from app.services.perplexity_web_search import perplexity_web_search, get_perplexity_service

router = APIRouter(prefix="/api/search", tags=["enhanced_search"])
logger = logging.getLogger(__name__)

class PerplexitySearchRequest(BaseModel):
    """Request model for Perplexity-style search."""
    query: str
    max_results: Optional[int] = 8
    synthesize_answer: Optional[bool] = True
    include_recent: Optional[bool] = True

class WebSearchRequest(BaseModel):
    """Request model for enhanced web search."""
    query: str
    max_results: Optional[int] = 8
    include_content: Optional[bool] = True

@router.post("/perplexity")
async def perplexity_search_endpoint(request: PerplexitySearchRequest):
    """
    Perplexity-style web search with AI-powered answer synthesis and source citations.
    
    This endpoint provides comprehensive research capabilities by:
    - Searching multiple web sources for relevant information
    - Extracting and processing content from web pages
    - Synthesizing coherent answers using AI
    - Providing proper source citations and references
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if request.max_results < 1 or request.max_results > 20:
            raise HTTPException(status_code=400, detail="max_results must be between 1 and 20")
        
        result = perplexity_web_search(
            query=request.query.strip(),
            max_results=request.max_results,
            synthesize_answer=request.synthesize_answer,
            include_recent=request.include_recent
        )
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Perplexity search error for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/perplexity")
async def perplexity_search_get(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(8, ge=1, le=20, description="Maximum results"),
    synthesize: bool = Query(True, description="Generate synthesized answer"),
    recent: bool = Query(True, description="Include recent content")
):
    """
    Perplexity-style web search via GET request.
    
    Query parameters:
    - q: Search query (required)
    - max_results: Maximum number of results (1-20, default 8)
    - synthesize: Whether to generate AI synthesized answer (default true)
    - recent: Whether to prioritize recent content (default true)
    """
    try:
        result = perplexity_web_search(
            query=q.strip(),
            max_results=max_results,
            synthesize_answer=synthesize,
            include_recent=recent
        )
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Perplexity search error for query '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/enhanced")
async def enhanced_web_search(request: WebSearchRequest):
    """
    Enhanced web search with improved content extraction.
    
    This endpoint provides:
    - Multi-source web search capabilities
    - Enhanced content extraction from web pages
    - Improved result ranking and relevance
    - Source tracking and metadata
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if request.max_results < 1 or request.max_results > 20:
            raise HTTPException(status_code=400, detail="max_results must be between 1 and 20")
        
        # Use perplexity search without answer synthesis for enhanced search
        result = perplexity_web_search(
            query=request.query.strip(),
            max_results=request.max_results,
            synthesize_answer=False,  # No synthesis for basic enhanced search
            include_recent=True
        )
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Enhanced web search error for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/enhanced")
async def enhanced_web_search_get(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(8, ge=1, le=20, description="Maximum results"),
    content: bool = Query(True, description="Include full content extraction")
):
    """
    Enhanced web search via GET request.
    
    Query parameters:
    - q: Search query (required)
    - max_results: Maximum number of results (1-20, default 8)
    - content: Whether to extract full content (default true)
    """
    try:
        result = perplexity_web_search(
            query=q.strip(),
            max_results=max_results,
            synthesize_answer=False,
            include_recent=True
        )
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Enhanced web search error for query '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/status")
async def search_service_status():
    """Get status of the enhanced search service."""
    try:
        service = get_perplexity_service()
        
        return {
            "status": "success",
            "data": {
                "service_available": True,
                "max_content_length": service.max_content_length,
                "max_synthesis_sources": service.max_synthesis_sources,
                "features": {
                    "content_extraction": True,
                    "answer_synthesis": True,
                    "source_citations": True,
                    "relevance_ranking": True
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Search service status check failed: {e}")
        return {
            "status": "error", 
            "data": {
                "service_available": False,
                "error": str(e)
            }
        }