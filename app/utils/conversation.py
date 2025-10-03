"""Conversation management utilities for cost optimization and token management."""
import json
import secrets
import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
from cachetools import TTLCache
from app.core.config import (
    CONV_CACHE_SIZE, CONV_TTL_SECONDS, MAX_CONV_MESSAGES,
    CONV_SUMMARY_THRESHOLD, MAX_TOKENS_PER_TURN, CHUNK_MAX_TOKENS,
    SUMMARY_MODEL, RAG_ENABLED, RAG_MAX_CHUNKS
)
from app.services.openai_client import get_client, resolve_model

logger = logging.getLogger(__name__)

# Conversation memory (in-memory, TTL-based)
CONV_CACHE = TTLCache(maxsize=CONV_CACHE_SIZE, ttl=CONV_TTL_SECONDS)
SUMMARY_CACHE = TTLCache(maxsize=500, ttl=60 * 60 * 24)  # 24 hours

# Token estimation cache - uses LRU cache for frequently computed strings
@lru_cache(maxsize=2048)
def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token for English text. Cached for performance."""
    return max(1, len(text) // 4)

def truncate_by_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximate token limit."""
    if estimate_tokens(text) <= max_tokens:
        return text
    # Rough truncation: keep first part within token limit
    target_chars = max_tokens * 4
    if len(text) <= target_chars:
        return text
    return text[:target_chars] + "..."

def _new_conversation_id() -> str:
    """Generate a new conversation ID."""
    return secrets.token_hex(12)

def _validate_message_sequence(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate message sequence and remove incomplete tool call/response pairs."""
    if not messages:
        return messages
    
    validated = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg.get('role', '')
        
        if role == 'assistant' and msg.get('tool_calls'):
            # Assistant message with tool calls - check if all tool responses are present
            tool_calls = msg.get('tool_calls', [])
            expected_tool_call_ids = {tc.get('id') if hasattr(tc, 'get') else tc['id'] for tc in tool_calls}
            
            # Look ahead for corresponding tool messages
            j = i + 1
            found_tool_call_ids = set()
            tool_responses = []
            
            while j < len(messages) and messages[j].get('role') == 'tool':
                tool_msg = messages[j]
                tool_call_id = tool_msg.get('tool_call_id')
                if tool_call_id in expected_tool_call_ids:
                    found_tool_call_ids.add(tool_call_id)
                    tool_responses.append(tool_msg)
                j += 1
            
            # Only include if all tool calls have responses
            if found_tool_call_ids == expected_tool_call_ids:
                validated.append(msg)
                validated.extend(tool_responses)
            else:
                missing_ids = expected_tool_call_ids - found_tool_call_ids
                logger.warning(f"Removing incomplete tool call group from conversation: missing responses for {missing_ids}")
            
            i = j  # Skip past the tool messages we've processed
        elif role == 'tool':
            # Check if there's a preceding assistant message with tool_calls that we kept
            if (validated and 
                validated[-1].get('role') == 'assistant' and 
                validated[-1].get('tool_calls')):
                # This tool message should have been processed in the assistant block above
                logger.warning(f"Skipping extra tool message from conversation: {msg.get('tool_call_id', 'no_id')}")
            else:
                # Orphaned tool message
                logger.warning(f"Removing orphaned tool message from conversation: {msg.get('tool_call_id', 'no_id')}")
            i += 1
        else:
            validated.append(msg)
            i += 1
    
    return validated

def conv_get(conv_id: str) -> List[Dict[str, Any]]:
    """Get conversation messages from cache with validation."""
    try:
        msgs = CONV_CACHE.get(conv_id) or []
        if not isinstance(msgs, list):
            msgs = []
        # Validate and clean up any orphaned tool messages
        return _validate_message_sequence(msgs)
    except Exception:
        return []

def conv_set(conv_id: str, msgs: List[Dict[str, Any]]):
    """Set conversation messages in cache with size limits and validation."""
    try:
        # Validate message sequence first
        validated_msgs = _validate_message_sequence(msgs)
        
        # Trim to last N user+assistant messages to bound size
        if len(validated_msgs) > MAX_CONV_MESSAGES:
            validated_msgs = validated_msgs[-MAX_CONV_MESSAGES:]
        
        CONV_CACHE[conv_id] = validated_msgs
    except Exception:
        pass

def conv_clear(conv_id: str) -> bool:
    """Clear a conversation from cache."""
    existed = conv_id in CONV_CACHE
    try:
        if existed:
            del CONV_CACHE[conv_id]
        # Also clear summary cache
        if conv_id in SUMMARY_CACHE:
            del SUMMARY_CACHE[conv_id]
    except Exception:
        pass
    return existed

def _summarize_conversation(messages: List[Dict[str, Any]], conv_id: str) -> str:
    """Create a compact summary of older conversation turns to reduce token usage."""
    if conv_id in SUMMARY_CACHE:
        return SUMMARY_CACHE[conv_id]

    # Filter to user/assistant messages only
    conv_msgs = [m for m in messages if m.get("role") in {"user", "assistant"}]
    if len(conv_msgs) < 4:  # Need meaningful conversation to summarize
        return ""

    # Build summary prompt with token-conscious content
    summary_content = []
    for msg in conv_msgs[:-4]:  # Keep last 4 messages unsummarized
        role = msg.get("role", "")
        content = msg.get("content", "")
        if content:
            # Truncate very long messages for summary
            truncated = truncate_by_tokens(content, CHUNK_MAX_TOKENS)
            summary_content.append(f"{role}: {truncated}")

    if not summary_content:
        return ""

    summary_prompt = f"""Summarize this conversation history in 2-3 concise bullet points, focusing on:
- Key topics discussed (stocks, companies, financial concepts)
- Important data points or decisions mentioned
- Context needed for future questions

Conversation:
{chr(10).join(summary_content)}

Summary:"""

    try:
        client = get_client()
        summary_model = resolve_model(SUMMARY_MODEL)

        response = client.chat.completions.create(
            model=summary_model,
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=200,
            temperature=0.3
        )

        summary = response.choices[0].message.content or ""
        if summary:
            SUMMARY_CACHE[conv_id] = summary
            logger.debug(f"Generated summary for conversation {conv_id[:8]}...")
            return summary
    except Exception as e:
        logger.warning(f"Failed to generate summary: {e}")

    return ""

def optimize_conversation_context(messages: List[Dict[str, Any]], conv_id: str) -> List[Dict[str, Any]]:
    """Optimize conversation context for cost and performance using summarization."""
    if len(messages) <= CONV_SUMMARY_THRESHOLD:
        return messages

    # Calculate current token usage
    total_tokens = sum(estimate_tokens(json.dumps(m)) for m in messages)

    if total_tokens <= MAX_TOKENS_PER_TURN:
        return messages

    # Find system message and recent messages to preserve
    system_msgs = [m for m in messages if m.get("role") == "system"]
    recent_msgs = messages[-10:]  # Keep last 10 messages
    older_msgs = messages[len(system_msgs):-10] if len(messages) > 10 else []

    optimized = system_msgs[:]

    # Add summary of older conversation if it exists
    if older_msgs:
        summary = _summarize_conversation(older_msgs, conv_id)
        if summary:
            optimized.append({
                "role": "system",
                "content": f"Previous conversation summary: {summary}"
            })

    # Add recent messages
    optimized.extend(recent_msgs)

    # Final token check - truncate if still too large
    final_tokens = sum(estimate_tokens(json.dumps(m)) for m in optimized)
    if final_tokens > MAX_TOKENS_PER_TURN:
        # Aggressively truncate content in non-system messages
        for msg in optimized:
            if msg.get("role") != "system" and msg.get("content"):
                msg["content"] = truncate_by_tokens(msg["content"], CHUNK_MAX_TOKENS // 2)

    logger.debug(f"Optimized conversation {conv_id[:8]}: {len(messages)} -> {len(optimized)} messages")
    return optimized

def get_relevant_rag_context(query: str, conversation_context: str = "") -> str:
    """Get RAG context optimized for cost with semantic filtering."""
    from app.services.rag_service import rag_search

    if not RAG_ENABLED:
        return ""

    # Combine query with recent conversation context for better retrieval
    search_query = f"{query}"
    if conversation_context:
        # Add context but limit tokens
        context_snippet = truncate_by_tokens(conversation_context, 200)
        search_query = f"{query} Context: {context_snippet}"

    try:
        # Use limited retrieval to control costs
        rag_results = rag_search(search_query, k=RAG_MAX_CHUNKS)

        if not rag_results.get("results"):
            return ""

        # Build context with token limits
        context_parts = []
        total_tokens = 0

        for result in rag_results["results"]:
            chunk_text = result.get("text", "")
            chunk_tokens = estimate_tokens(chunk_text)

            # Skip if adding this chunk would exceed budget
            if total_tokens + chunk_tokens > CHUNK_MAX_TOKENS * RAG_MAX_CHUNKS:
                break

            # Truncate chunk if too long
            if chunk_tokens > CHUNK_MAX_TOKENS:
                chunk_text = truncate_by_tokens(chunk_text, CHUNK_MAX_TOKENS)

            context_parts.append(chunk_text)
            total_tokens += chunk_tokens

        return "\n\n".join(context_parts)

    except Exception as e:
        logger.warning(f"RAG search failed: {e}")
        return ""

# Enhanced conversation preparation with memory and performance optimizations
async def prepare_conversation_messages_with_memory(
    prompt: str,
    system_prompt: Optional[str],
    conversation_id: str,
    reset: bool,
    user_id: str,
    model_key: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """Enhanced conversation preparation with memory optimization and caching."""
    from app.services.enhanced_memory import get_user_memory, update_user_memory
    from app.services.response_cache import is_simple_query, is_stock_price_query
    from app.core.config import get_system_prompt_for_model, RAG_ENABLED

    if reset:
        conv_id = conversation_id or _new_conversation_id()
        conv_clear(conv_id)
        return await prepare_conversation_messages_with_memory(
            prompt, system_prompt, conv_id, False, user_id, model_key
        )

    conv_id = conversation_id or _new_conversation_id()

    # Get existing conversation
    messages = conv_get(conv_id)

    # Optimize system prompt based on model and query type
    if not system_prompt:
        if model_key:
            system_prompt = get_system_prompt_for_model(model_key)
        else:
            # Use shorter prompt for simple queries
            if is_simple_query(prompt) or is_stock_price_query(prompt):
                system_prompt = """You are a helpful AI assistant. Be concise and direct."""
            else:
                system_prompt = get_system_prompt_for_model("default")

    # Add system message if not present
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": system_prompt})

    # Enhanced memory integration with performance optimization
    try:
        # Skip memory for simple queries to improve speed
        if not (is_simple_query(prompt) or is_stock_price_query(prompt)):
            memory_context = await get_user_memory(user_id, prompt)
            if memory_context and len(memory_context) > 10:  # Only add if meaningful
                # Add memory as system context
                messages.append({
                    "role": "system",
                    "content": f"Relevant context from previous conversations: {memory_context}"
                })
    except Exception as e:
        logger.warning(f"Memory retrieval failed: {e}")

    # Add RAG context for knowledge-seeking queries
    try:
        if RAG_ENABLED:
            # Check if query is asking for knowledge/context/analysis
            knowledge_keywords = ['news', 'context', 'analysis', 'explain', 'about', 'information',
                                'market', 'financial', 'investment', 'strategy', 'risk', 'valuation',
                                'technical', 'fundamental', 'ratio', 'metrics', 'beta', 'sharpe']

            should_use_rag = False

            # Always use RAG for knowledge-seeking queries
            query_lower = prompt.lower()
            if any(keyword in query_lower for keyword in knowledge_keywords):
                should_use_rag = True
                logger.info(f"Using RAG for knowledge query: {prompt[:50]}...")

            # Also use RAG for complex queries (existing logic)
            elif not (is_simple_query(prompt) or is_stock_price_query(prompt)):
                should_use_rag = True
                logger.info(f"Using RAG for complex query: {prompt[:50]}...")

            if should_use_rag:
                from app.services.rag_service import rag_search
                from app.core.config import RAG_MAX_CHUNKS

                # Quick RAG search with limited results
                rag_results = rag_search(prompt, k=min(RAG_MAX_CHUNKS, 3))  # Increased to 3 for better results
                logger.info(f"RAG search returned {rag_results.get('count', 0)} results")

                if rag_results.get("count", 0) > 0:
                    chunks = []
                    for item in rag_results["results"][:3]:  # Allow up to 3 chunks
                        chunk_text = item.get("text", "")[:500]  # Increased chunk size for better context
                        if chunk_text.strip():
                            chunks.append(chunk_text.strip())

                    if chunks:
                        rag_context = "\n\n---\n\n".join(chunks)
                        messages.append({
                            "role": "system",
                            "content": f"Knowledge Base Context:\n{rag_context}\n\nUse this information to provide accurate, detailed responses."
                        })
                        logger.info(f"Added RAG context with {len(chunks)} chunks")
                else:
                    logger.info("No RAG results found for query")
            else:
                logger.info(f"Skipping RAG for simple query: {prompt[:50]}...")
    except Exception as e:
        logger.warning(f"RAG search failed: {e}")

    # Add the current user message
    messages.append({"role": "user", "content": prompt})

    # Optimize conversation length for performance
    messages = optimize_conversation_context(messages, conv_id)

    return messages, conv_id

async def store_conversation_messages_with_memory(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    user_id: str
):
    """Store conversation with enhanced memory updates."""
    from app.services.enhanced_memory import update_user_memory

    # Store in conversation cache
    conv_set(conversation_id, messages)

    # Update user memory asynchronously for performance
    try:
        # Extract meaningful interactions for memory
        recent_messages = messages[-4:]  # Last 2 exchanges
        user_messages = [m for m in recent_messages if m.get("role") == "user"]
        assistant_messages = [m for m in recent_messages if m.get("role") == "assistant"]

        if user_messages and assistant_messages:
            # Create memory context from recent interaction
            last_user = user_messages[-1].get("content", "")
            last_assistant = assistant_messages[-1].get("content", "")

            if len(last_user) > 10 and len(last_assistant) > 10:
                await update_user_memory(user_id, last_user, last_assistant)
    except Exception as e:
        logger.warning(f"Memory update failed: {e}")

def prepare_conversation_messages(
    prompt: str, 
    system_prompt: Optional[str], 
    conv_id: str, 
    reset: bool
) -> Tuple[List[Dict[str, Any]], str]:
    """Legacy function for backward compatibility - enhanced with basic memory."""
    # Handle conversation ID
    if reset or not conv_id:
        conv_id = _new_conversation_id()
        messages = []
    else:
        messages = conv_get(conv_id)

    # Get basic RAG context
    rag_context = get_relevant_rag_context(prompt)

    # Build system prompt with RAG context
    base_system = system_prompt or """You are a helpful AI assistant specializing in financial analysis and investment guidance. 
You have access to real-time stock data, financial tools, and comprehensive market knowledge. 
Provide accurate, well-researched responses and use available tools when needed."""

    enhanced_system = base_system
    if rag_context:
        enhanced_system += f"\n\n## Knowledge Base Context:\n{rag_context}"

    # Limit system prompt tokens
    if estimate_tokens(enhanced_system) > MAX_TOKENS_PER_TURN // 3:
        enhanced_system = truncate_by_tokens(enhanced_system, MAX_TOKENS_PER_TURN // 3)

    # Prepare messages
    if not messages or not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": enhanced_system})
    else:
        # Update existing system message
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                messages[i]["content"] = enhanced_system
                break

    # Add user prompt
    messages.append({"role": "user", "content": prompt})

    # Optimize conversation for token limits
    messages = optimize_conversation_context(messages, conv_id)

    return messages, conv_id

def store_conversation_messages(conv_id: str, messages: List[Dict[str, Any]]):
    """Legacy function for backward compatibility."""
    conv_set(conv_id, messages)
