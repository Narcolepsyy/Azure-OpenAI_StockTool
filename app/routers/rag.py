"""RAG (Retrieval-Augmented Generation) API routes."""
import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import RAGReindexRequest, RAGSearchRequest, RAGQueryRequest
from app.services.rag_service import rag_reindex, rag_search, get_rag_status
from app.services.openai_client import get_client, resolve_model
from app.core.config import RAG_ENABLED

router = APIRouter(prefix="/api/rag", tags=["rag"])
logger = logging.getLogger(__name__)

@router.post("/reindex")
async def api_rag_reindex(req: RAGReindexRequest):
    """Reindex the knowledge base for RAG functionality."""
    try:
        result = rag_reindex(clear=req.clear)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"RAG reindex error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def api_rag_search(req: RAGSearchRequest):
    """Search the knowledge base using RAG functionality."""
    try:
        result = rag_search(req.query, k=req.k)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def api_rag_query(req: RAGQueryRequest):
    """Query with RAG-enhanced responses using Azure OpenAI."""
    try:
        if not RAG_ENABLED:
            raise HTTPException(status_code=400, detail="RAG is not enabled")

        # Search for relevant context
        search_result = rag_search(req.query, k=req.k)

        if search_result.get("error"):
            raise HTTPException(status_code=500, detail=search_result["error"])

        # Build context from search results
        context_parts = []
        if search_result.get("results"):
            for result in search_result["results"]:
                source = result.get("metadata", {}).get("path", "knowledge base")
                context_parts.append(f"From {source}:\n{result['text']}")

        context = "\n\n".join(context_parts) if context_parts else "No relevant context found."

        # Create enhanced prompt with context
        enhanced_prompt = f"""Based on the following context from the knowledge base, please answer the user's question.

Context:
{context}

User Question: {req.query}

Please provide a comprehensive answer based on the context provided. If the context doesn't contain relevant information, please say so and provide what general knowledge you can."""

        # Use the chat completion with RAG-enhanced context
        client = get_client()
        model_name = resolve_model(req.model) or resolve_model(None)

        if not model_name:
            raise HTTPException(status_code=500, detail="No model configured")

        messages = [{"role": "user", "content": enhanced_prompt}]

        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            choice = completion.choices[0] if completion.choices else None
            if not choice or not choice.message:
                raise HTTPException(status_code=500, detail="No response generated")

            response_content = choice.message.content or ""

            return {
                "status": "success",
                "data": {
                    "query": req.query,
                    "response": response_content,
                    "context_used": len(context_parts),
                    "sources": [
                        result.get("metadata", {}).get("path", "unknown")
                        for result in search_result.get("results", [])
                    ]
                }
            }

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def api_rag_status():
    """Get RAG system status and configuration."""
    try:
        result = get_rag_status()
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"RAG status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
