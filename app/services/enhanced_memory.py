"""Enhanced memory service with performance optimizations - minimal API calls for fast responses."""
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from cachetools import TTLCache
from app.core.config import (
    RAG_ENABLED, CHUNK_MAX_TOKENS, MAX_TOKENS_PER_TURN,
    CONV_SUMMARY_THRESHOLD
)
from app.services.openai_client import get_client_for_model
from app.services.rag_service import rag_search, _get_vectorstore
from app.utils.conversation import estimate_tokens, truncate_by_tokens

logger = logging.getLogger(__name__)

# Memory caches with different TTLs for different memory types
SHORT_TERM_CACHE = TTLCache(maxsize=1000, ttl=60 * 60 * 2)  # 2 hours
MEDIUM_TERM_CACHE = TTLCache(maxsize=500, ttl=60 * 60 * 24)  # 24 hours
LONG_TERM_SUMMARIES = TTLCache(maxsize=200, ttl=60 * 60 * 24 * 7)  # 1 week
ENTITY_MEMORY = TTLCache(maxsize=1000, ttl=60 * 60 * 24 * 30)  # 30 days

# Performance optimization: Track last processing times
LAST_ENTITY_EXTRACTION = {}
LAST_SUMMARY_CREATION = {}

class MemoryService:
    """Enhanced memory service with performance optimizations."""

    def __init__(self):
        self.gpt4o_mini_key = "gpt-4o-mini"
        self._background_tasks = set()  # Track background tasks

    async def store_conversation_memory(self, conv_id: str, messages: List[Dict[str, Any]],
                                      user_id: Optional[str] = None) -> None:
        """Store conversation in appropriate memory layers with performance optimizations."""
        try:
            # Always store in short-term memory (fast operation)
            SHORT_TERM_CACHE[conv_id] = {
                "messages": messages,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "turn_count": len([m for m in messages if m.get("role") == "user"])
            }

            # Performance optimization: Only do expensive operations periodically
            message_count = len(messages)

            # Extract entities only every 3rd message or on significant content
            if self._should_extract_entities(conv_id, message_count):
                # Run entity extraction in background to not block response
                task = asyncio.create_task(self._extract_and_store_entities_async(messages, conv_id, user_id))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

            # Create summaries only when really needed and in background
            if self._should_create_summary(conv_id, message_count):
                task = asyncio.create_task(self._create_summaries_async(conv_id, messages, user_id))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        except Exception as e:
            logger.error(f"Error storing conversation memory: {e}")

    def _should_extract_entities(self, conv_id: str, message_count: int) -> bool:
        """Determine if entity extraction should run (performance optimization)."""
        last_extraction = LAST_ENTITY_EXTRACTION.get(conv_id, 0)
        current_time = datetime.now().timestamp()

        # Extract entities only:
        # - Every 3 messages OR
        # - Every 5 minutes OR
        # - If never extracted for this conversation
        return (
            message_count % 3 == 0 or
            current_time - last_extraction > 300 or  # 5 minutes
            last_extraction == 0
        )

    def _should_create_summary(self, conv_id: str, message_count: int) -> bool:
        """Determine if summary creation should run (performance optimization)."""
        if message_count < CONV_SUMMARY_THRESHOLD:
            return False

        last_summary = LAST_SUMMARY_CREATION.get(conv_id, 0)
        current_time = datetime.now().timestamp()

        # Create summaries only:
        # - Every 10 messages after threshold OR
        # - Every 10 minutes after threshold
        return (
            message_count % 10 == 0 or
            current_time - last_summary > 600  # 10 minutes
        )

    async def retrieve_contextual_memory(self, query: str, conv_id: str,
                                       user_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve relevant memory from all layers with fast retrieval."""
        memory_context = {
            "short_term": "",
            "medium_term": "",
            "long_term": "",
            "entities": [],
            "rag_context": "",
            "total_tokens": 0
        }

        try:
            # Fast operations first (cached data)
            short_term = self._get_short_term_memory(conv_id)
            if short_term:
                memory_context["short_term"] = short_term
                memory_context["total_tokens"] += estimate_tokens(short_term)

            medium_term = self._get_medium_term_memory(conv_id, user_id)
            if medium_term:
                memory_context["medium_term"] = medium_term
                memory_context["total_tokens"] += estimate_tokens(medium_term)

            entities = self._get_relevant_entities(query, user_id)
            if entities:
                memory_context["entities"] = entities
                entities_text = " ".join([f"{e['name']}: {e['context']}" for e in entities])
                memory_context["total_tokens"] += estimate_tokens(entities_text)

            # Only get RAG context if we haven't exceeded token limits (performance check)
            if memory_context["total_tokens"] < MAX_TOKENS_PER_TURN // 2 and RAG_ENABLED:
                rag_context = await self._get_rag_context_fast(query)
                if rag_context:
                    memory_context["rag_context"] = rag_context
                    memory_context["total_tokens"] += estimate_tokens(rag_context)

            long_term = self._get_long_term_memory(user_id, query)
            if long_term:
                memory_context["long_term"] = long_term
                memory_context["total_tokens"] += estimate_tokens(long_term)

        except Exception as e:
            logger.error(f"Error retrieving contextual memory: {e}")

        return memory_context

    async def _extract_and_store_entities_async(self, messages: List[Dict[str, Any]],
                                              conv_id: str, user_id: Optional[str]) -> None:
        """Extract entities asynchronously in background."""
        try:
            LAST_ENTITY_EXTRACTION[conv_id] = datetime.now().timestamp()

            # Get only the most recent messages for efficiency
            recent_messages = [m for m in messages[-4:] if m.get("role") in ["user", "assistant"]]
            if not recent_messages:
                return

            # Use simple extraction first, fall back to AI only if needed
            entities = self._extract_entities_simple_fast(recent_messages)

            # Only call AI model if simple extraction found very few entities
            if len(entities) < 2:
                entities = await self._extract_entities_with_ai(recent_messages)

            # Store entities
            for entity in entities:
                try:
                    entity_key = f"{user_id or 'anonymous'}:{entity['name'].lower()}"
                    ENTITY_MEMORY[entity_key] = {
                        "name": entity.get("name"),
                        "type": entity.get("type", "unknown"),
                        "context": entity.get("context", ""),
                        "conv_id": conv_id,
                        "timestamp": datetime.now().isoformat(),
                        "user_id": user_id
                    }
                except Exception as store_error:
                    logger.warning(f"Failed to store entity {entity}: {store_error}")

        except Exception as e:
            logger.error(f"Error in async entity extraction: {e}")

    def _extract_entities_simple_fast(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fast rule-based entity extraction without AI calls."""
        import re
        entities = []

        # Combine all message content
        text = " ".join([m.get("content", "") for m in messages])

        # Stock symbols (2-5 caps, common patterns)
        stock_pattern = r'\b([A-Z]{2,5})\b'
        exclude_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HOW', 'ITS', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'END', 'FEW', 'LET', 'MAN', 'PUT', 'SAY', 'SHE', 'TOO', 'USE', 'WAY', 'WIN', 'YES'}

        for match in re.finditer(stock_pattern, text):
            symbol = match.group(1)
            if symbol not in exclude_words and len(symbol) <= 5:
                entities.append({
                    "name": symbol,
                    "type": "company",
                    "context": "Stock symbol"
                })

        # Dollar amounts
        for match in re.finditer(r'\$[\d,]+(?:\.\d{2})?', text):
            entities.append({
                "name": match.group(0),
                "type": "metric",
                "context": "Financial amount"
            })

        # Percentages
        for match in re.finditer(r'\b\d+(?:\.\d+)?%', text):
            entities.append({
                "name": match.group(0),
                "type": "metric",
                "context": "Percentage"
            })

        # Common company names
        companies = ['Apple', 'Microsoft', 'Google', 'Amazon', 'Tesla', 'Meta', 'Netflix', 'Nvidia', 'AMD', 'Intel']
        text_lower = text.lower()
        for company in companies:
            if company.lower() in text_lower:
                entities.append({
                    "name": company,
                    "type": "company",
                    "context": "Company name"
                })

        return entities[:8]  # Limit for performance

    async def _extract_entities_with_ai(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract entities with AI as fallback (reduced prompt for speed)."""
        try:
            conversation_text = "\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in messages])
            conversation_text = truncate_by_tokens(conversation_text, 400)  # Reduced for speed

            # Simplified prompt for faster processing
            entity_prompt = f"""Extract financial entities from this conversation as JSON array:
[{{"name": "entity", "type": "company|metric", "context": "brief"}}]

Text: {conversation_text}

JSON:"""

            client, model_name, _ = get_client_for_model(self.gpt4o_mini_key)

            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": entity_prompt}],
                max_tokens=200,  # Reduced for speed
                temperature=0.0
            )

            entities_text = response.choices[0].message.content or ""

            # Simple JSON parsing
            try:
                entities = json.loads(entities_text.strip())
                if isinstance(entities, list):
                    return entities[:5]
            except:
                pass

            return []

        except Exception as e:
            logger.error(f"AI entity extraction failed: {e}")
            return []

    async def _create_summaries_async(self, conv_id: str, messages: List[Dict[str, Any]],
                                    user_id: Optional[str]) -> None:
        """Create summaries asynchronously in background."""
        try:
            LAST_SUMMARY_CREATION[conv_id] = datetime.now().timestamp()

            # Only create medium-term summary for performance
            await self._create_medium_term_summary_fast(conv_id, messages, user_id)

            # Only create long-term summary for very long conversations
            if len(messages) > CONV_SUMMARY_THRESHOLD * 3:
                await self._store_long_term_memory_fast(conv_id, messages, user_id)

        except Exception as e:
            logger.error(f"Error in async summary creation: {e}")

    async def _create_medium_term_summary_fast(self, conv_id: str, messages: List[Dict[str, Any]],
                                             user_id: Optional[str]) -> None:
        """Create fast medium-term summary."""
        try:
            conv_messages = [m for m in messages if m.get("role") in ["user", "assistant"]]
            if len(conv_messages) < 6:
                return
                
            # Take only older messages, keep recent ones raw
            messages_to_summarize = conv_messages[:-6]
            if not messages_to_summarize:
                return
                
            conversation_text = "\n".join([
                f"{m.get('role', '')}: {truncate_by_tokens(m.get('content', ''), 100)}"
                for m in messages_to_summarize
            ])
            
            # Simplified prompt for speed
            summary_prompt = f"""Summarize key points from this financial conversation:

{conversation_text}

Summary:"""

            client, model_name = get_client_for_model(self.gpt4o_mini_key)
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=200,  # Reduced for speed
                temperature=0.2
            )
            
            summary = response.choices[0].message.content or ""
            
            if summary:
                MEDIUM_TERM_CACHE[f"{conv_id}:summary"] = {
                    "summary": summary,
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "message_count": len(messages_to_summarize)
                }

        except Exception as e:
            logger.error(f"Error creating fast medium-term summary: {e}")

    async def _store_long_term_memory_fast(self, conv_id: str, messages: List[Dict[str, Any]],
                                         user_id: Optional[str]) -> None:
        """Store long-term memory with minimal processing."""
        try:
            if not RAG_ENABLED:
                return
                
            # Simple extraction of key information without AI summarization
            conv_messages = [m for m in messages if m.get("role") in ["user", "assistant"]]
            
            # Create simple summary from recent important messages
            important_messages = [m for m in conv_messages if
                                len(m.get("content", "")) > 50 and
                any(word in m.get("content", "").lower() for word in
                    ['stock', 'invest', 'buy', 'sell', 'price', 'market', 'analysis'])]

            if important_messages:
                simple_summary = "\n".join([
                    truncate_by_tokens(m.get("content", ""), 150)
                    for m in important_messages[-5:]  # Last 5 important messages
                ])

                summary_key = f"longterm:{user_id or 'anon'}:{conv_id}"
                LONG_TERM_SUMMARIES[summary_key] = {
                    "summary": simple_summary,
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "conv_id": conv_id
                }
                
        except Exception as e:
            logger.error(f"Error storing fast long-term memory: {e}")

    async def _get_rag_context_fast(self, query: str) -> str:
        """Get RAG context with performance optimizations."""
        try:
            if not RAG_ENABLED:
                return ""

            # Simplified RAG search with fewer results for speed
            rag_results = rag_search(query, k=2)  # Reduced from 4 to 2

            if not rag_results.get("results"):
                return ""

            # Build context with token limits
            context_parts = []
            total_tokens = 0
            max_rag_tokens = CHUNK_MAX_TOKENS  # Reduced limit

            for result in rag_results["results"]:
                chunk_text = result.get("text", "")
                chunk_tokens = estimate_tokens(chunk_text)

                if total_tokens + chunk_tokens > max_rag_tokens:
                    break

                context_parts.append(truncate_by_tokens(chunk_text, 300))  # Truncate chunks
                total_tokens += chunk_tokens

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error getting fast RAG context: {e}")
            return ""

    def _get_short_term_memory(self, conv_id: str) -> str:
        """Get short-term memory for current session (optimized)."""
        try:
            memory_data = SHORT_TERM_CACHE.get(conv_id)
            if not memory_data:
                return ""

            messages = memory_data.get("messages", [])
            if not messages:
                return ""

            # Return recent conversation context (reduced for performance)
            recent_messages = [m for m in messages[-4:] if m.get("role") in ["user", "assistant"]]

            context_parts = []
            for msg in recent_messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if content:
                    truncated = truncate_by_tokens(content, 100)  # Reduced from 150
                    context_parts.append(f"{role}: {truncated}")

            return "\n".join(context_parts) if context_parts else ""

        except Exception as e:
            logger.error(f"Error getting short-term memory: {e}")
            return ""

    def _get_medium_term_memory(self, conv_id: str, user_id: Optional[str]) -> str:
        """Get medium-term summary memory (cached lookup)."""
        try:
            summary_data = MEDIUM_TERM_CACHE.get(f"{conv_id}:summary")
            if summary_data:
                return summary_data.get("summary", "")
            return ""
        except Exception as e:
            logger.error(f"Error getting medium-term memory: {e}")
            return ""

    def _get_long_term_memory(self, user_id: Optional[str], query: str) -> str:
        """Get relevant long-term memory summaries (optimized search)."""
        try:
            relevant_summaries = []
            query_words = set(query.lower().split())

            # Quick search through long-term summaries
            for key, summary_data in LONG_TERM_SUMMARIES.items():
                if summary_data.get("user_id") == user_id:
                    summary_text = summary_data.get("summary", "").lower()
                    # Fast word-based relevance check
                    summary_words = set(summary_text.split())
                    if query_words.intersection(summary_words):
                        relevant_summaries.append(summary_data.get("summary", ""))
                        if len(relevant_summaries) >= 2:  # Limit for performance
                            break

            return "\n\n".join(relevant_summaries)

        except Exception as e:
            logger.error(f"Error getting long-term memory: {e}")
            return ""

    def _get_relevant_entities(self, query: str, user_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get relevant entities based on query (optimized search)."""
        try:
            relevant_entities = []
            query_words = set(query.lower().split())

            for key, entity_data in ENTITY_MEMORY.items():
                if entity_data.get("user_id") == user_id:
                    entity_name = entity_data.get("name", "").lower()

                    # Fast relevance check
                    if (entity_name in query.lower() or
                        any(word in entity_name for word in query_words)):
                        relevant_entities.append({
                            "name": entity_data.get("name"),
                            "type": entity_data.get("type"),
                            "context": entity_data.get("context")
                        })

                        if len(relevant_entities) >= 5:  # Limit for performance
                            break

            return relevant_entities

        except Exception as e:
            logger.error(f"Error getting relevant entities: {e}")
            return []

    async def _store_in_rag_system(self, summary: str, conv_id: str, user_id: Optional[str]) -> None:
        """Store summary in RAG vector database (simplified for performance)."""
        try:
            if not RAG_ENABLED:
                return

            # Only store if summary is substantial
            if len(summary) < 100:
                return

            from importlib import import_module
            Document = import_module("langchain_core.documents").Document

            vs = _get_vectorstore()
            if not vs:
                return

            # Create document with minimal metadata for speed
            doc = Document(
                page_content=summary,
                metadata={
                    "type": "conversation_summary",
                    "conv_id": conv_id[:8],  # Shorter ID
                    "timestamp": datetime.now().strftime("%Y-%m-%d"),  # Date only
                    "source": "conversation"
                }
            )

            # Add to vector store
            vs.add_documents([doc])

        except Exception as e:
            logger.error(f"Error storing in RAG system: {e}")

    # Cleanup methods for performance
    def cleanup_old_memories(self) -> None:
        """Clean up old memory data to maintain performance."""
        try:
            current_time = datetime.now().timestamp()

            # Clean up tracking dictionaries
            expired_keys = []
            for key, timestamp in LAST_ENTITY_EXTRACTION.items():
                if current_time - timestamp > 3600:  # 1 hour
                    expired_keys.append(key)

            for key in expired_keys:
                del LAST_ENTITY_EXTRACTION[key]

            expired_keys = []
            for key, timestamp in LAST_SUMMARY_CREATION.items():
                if current_time - timestamp > 3600:  # 1 hour
                    expired_keys.append(key)

            for key in expired_keys:
                del LAST_SUMMARY_CREATION[key]

        except Exception as e:
            logger.error(f"Error cleaning up memories: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory service statistics for monitoring."""
        return {
            "short_term_count": len(SHORT_TERM_CACHE),
            "medium_term_count": len(MEDIUM_TERM_CACHE),
            "long_term_count": len(LONG_TERM_SUMMARIES),
            "entity_count": len(ENTITY_MEMORY),
            "background_tasks": len(self._background_tasks),
            "active_extractions": len(LAST_ENTITY_EXTRACTION),
            "active_summaries": len(LAST_SUMMARY_CREATION)
        }

# Global memory service instance
_memory_service = None

def get_memory_service():
    """Get the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service

async def get_user_memory(user_id: str, query: str) -> str:
    """Get relevant memory context for a user query (simplified interface for conversation.py)."""
    try:
        service = get_memory_service()
        # Use empty conv_id as we're getting general user memory
        memory_context = await service.retrieve_contextual_memory(query, "", user_id)

        # Combine different memory types into a single context string
        context_parts = []

        if memory_context.get("short_term"):
            context_parts.append(f"Recent: {memory_context['short_term']}")

        if memory_context.get("entities"):
            entities_text = ", ".join([f"{e['name']}" for e in memory_context['entities'][:3]])
            if entities_text:
                context_parts.append(f"Related: {entities_text}")

        if memory_context.get("medium_term"):
            context_parts.append(f"Previous: {memory_context['medium_term']}")

        combined_context = " | ".join(context_parts)

        # Limit context size for performance
        if len(combined_context) > 500:
            combined_context = combined_context[:500] + "..."

        return combined_context

    except Exception as e:
        logger.warning(f"Failed to get user memory: {e}")
        return ""

async def update_user_memory(user_id: str, user_message: str, assistant_message: str):
    """Update user memory with a new interaction (simplified interface for conversation.py)."""
    try:
        service = get_memory_service()

        # Create message format for memory storage
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ]

        # Generate a simple conversation ID for this interaction
        conv_id = f"user_{user_id}_{hash(user_message) % 10000}"

        # Store in memory asynchronously (won't block)
        await service.store_conversation_memory(conv_id, messages, user_id)

    except Exception as e:
        logger.warning(f"Failed to update user memory: {e}")
