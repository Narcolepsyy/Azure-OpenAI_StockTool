"""Enhanced memory service combining long-term RAG and short-term session memory with GPT-4o mini summarization."""
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from cachetools import TTLCache
from app.core.config import (
    RAG_ENABLED, CHUNK_MAX_TOKENS, MAX_TOKENS_PER_TURN,
    CONV_SUMMARY_THRESHOLD, SUMMARY_MODEL
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

class MemoryService:
    """Enhanced memory service with multi-layered memory architecture."""

    def __init__(self):
        self.gpt4o_mini_key = "gpt-4o-mini"  # Use GPT-4o mini for summarization

    async def store_conversation_memory(self, conv_id: str, messages: List[Dict[str, Any]],
                                      user_id: Optional[str] = None) -> None:
        """Store conversation in appropriate memory layers."""
        try:
            # Store in short-term memory
            SHORT_TERM_CACHE[conv_id] = {
                "messages": messages,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "turn_count": len([m for m in messages if m.get("role") == "user"])
            }

            # Extract and store entities for entity memory
            await self._extract_and_store_entities(messages, conv_id, user_id)

            # If conversation is getting long, create medium-term summary
            if len(messages) > CONV_SUMMARY_THRESHOLD:
                await self._create_medium_term_summary(conv_id, messages, user_id)

            # If conversation is very long, store in long-term memory
            if len(messages) > CONV_SUMMARY_THRESHOLD * 2:
                await self._store_long_term_memory(conv_id, messages, user_id)

        except Exception as e:
            logger.error(f"Error storing conversation memory: {e}")

    async def retrieve_contextual_memory(self, query: str, conv_id: str,
                                       user_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve relevant memory from all layers based on query."""
        memory_context = {
            "short_term": "",
            "medium_term": "",
            "long_term": "",
            "entities": [],
            "rag_context": "",
            "total_tokens": 0
        }

        try:
            # Get short-term memory (current session)
            short_term = self._get_short_term_memory(conv_id)
            if short_term:
                memory_context["short_term"] = short_term
                memory_context["total_tokens"] += estimate_tokens(short_term)

            # Get medium-term memory (recent summaries)
            medium_term = self._get_medium_term_memory(conv_id, user_id)
            if medium_term:
                memory_context["medium_term"] = medium_term
                memory_context["total_tokens"] += estimate_tokens(medium_term)

            # Get relevant entities
            entities = self._get_relevant_entities(query, user_id)
            if entities:
                memory_context["entities"] = entities
                entities_text = " ".join([f"{e['name']}: {e['context']}" for e in entities])
                memory_context["total_tokens"] += estimate_tokens(entities_text)

            # Get RAG context (long-term knowledge)
            if RAG_ENABLED:
                rag_context = await self._get_enhanced_rag_context(query, memory_context)
                if rag_context:
                    memory_context["rag_context"] = rag_context
                    memory_context["total_tokens"] += estimate_tokens(rag_context)

            # Get long-term conversation summaries
            long_term = self._get_long_term_memory(user_id, query)
            if long_term:
                memory_context["long_term"] = long_term
                memory_context["total_tokens"] += estimate_tokens(long_term)

        except Exception as e:
            logger.error(f"Error retrieving contextual memory: {e}")

        return memory_context

    async def _extract_and_store_entities(self, messages: List[Dict[str, Any]],
                                        conv_id: str, user_id: Optional[str]) -> None:
        """Extract and store important entities from conversation using GPT-4o mini."""
        try:
            # Get recent user messages for entity extraction
            recent_messages = [m for m in messages[-6:] if m.get("role") in ["user", "assistant"]]
            if not recent_messages:
                return

            conversation_text = "\n".join([f"{m.get('role', '')}: {m.get('content', '')}"
                                         for m in recent_messages])

            # Clean and truncate conversation text
            conversation_text = truncate_by_tokens(conversation_text, 800)

            entity_prompt = f"""Extract key financial entities from this conversation. Return ONLY a valid JSON array.

Focus on:
- Company names and stock symbols (e.g., "Apple", "AAPL")
- Financial metrics and numbers (e.g., "P/E ratio", "market cap")
- Investment strategies (e.g., "value investing", "day trading")
- Important dates or periods (e.g., "Q3 2024", "earnings season")
- Key financial concepts (e.g., "dividend yield", "volatility")

Format: [{{"name": "entity_name", "type": "company|metric|strategy|date|concept", "context": "brief_context"}}]

Conversation:
{conversation_text}

JSON Array:"""

            try:
                client, model_name = get_client_for_model(self.gpt4o_mini_key)

                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": entity_prompt}],
                    max_tokens=400,
                    temperature=0.0,  # Use 0 temperature for more consistent JSON output
                    response_format={"type": "json_object"} if "gpt-4" in model_name else None
                )

                entities_text = response.choices[0].message.content or ""

            except Exception as api_error:
                logger.warning(f"Entity extraction API call failed: {api_error}")
                return

            # Parse entities with multiple fallback strategies
            entities = self._parse_entities_with_fallback(entities_text, conversation_text, user_id, conv_id)

            # Store successfully parsed entities
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
                    logger.debug(f"Stored entity: {entity['name']} ({entity.get('type', 'unknown')})")
                except Exception as store_error:
                    logger.warning(f"Failed to store entity {entity}: {store_error}")

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")

    def _parse_entities_with_fallback(self, entities_text: str, conversation_text: str,
                                    user_id: Optional[str], conv_id: str) -> List[Dict[str, Any]]:
        """Parse entities with multiple fallback strategies."""
        entities = []

        # Strategy 1: Try direct JSON parsing
        try:
            # Clean the response text
            cleaned_text = entities_text.strip()

            # Try to extract JSON from markdown code blocks
            if "```json" in cleaned_text:
                json_start = cleaned_text.find("```json") + 7
                json_end = cleaned_text.find("```", json_start)
                if json_end > json_start:
                    cleaned_text = cleaned_text[json_start:json_end].strip()
            elif "```" in cleaned_text:
                json_start = cleaned_text.find("```") + 3
                json_end = cleaned_text.rfind("```")
                if json_end > json_start:
                    cleaned_text = cleaned_text[json_start:json_end].strip()

            # Try to find JSON array in the text
            if not cleaned_text.startswith('['):
                bracket_start = cleaned_text.find('[')
                if bracket_start >= 0:
                    cleaned_text = cleaned_text[bracket_start:]

            if not cleaned_text.endswith(']'):
                bracket_end = cleaned_text.rfind(']')
                if bracket_end >= 0:
                    cleaned_text = cleaned_text[:bracket_end + 1]

            parsed_entities = json.loads(cleaned_text)
            if isinstance(parsed_entities, list):
                for entity in parsed_entities:
                    if isinstance(entity, dict) and "name" in entity:
                        entities.append(entity)

            if entities:
                logger.debug(f"Successfully parsed {len(entities)} entities from JSON")
                return entities

        except json.JSONDecodeError as json_error:
            logger.debug(f"JSON parsing failed: {json_error}")
        except Exception as parse_error:
            logger.debug(f"Entity parsing failed: {parse_error}")

        # Strategy 2: Regex-based extraction as fallback
        try:
            entities = self._extract_entities_with_regex(conversation_text)
            if entities:
                logger.debug(f"Fallback regex extraction found {len(entities)} entities")
                return entities
        except Exception as regex_error:
            logger.warning(f"Regex fallback failed: {regex_error}")

        # Strategy 3: Simple keyword extraction as last resort
        try:
            entities = self._extract_entities_simple(conversation_text)
            if entities:
                logger.debug(f"Simple extraction found {len(entities)} entities")
                return entities
        except Exception as simple_error:
            logger.warning(f"Simple extraction failed: {simple_error}")

        return []

    def _extract_entities_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using regex patterns as fallback."""
        import re
        entities = []

        # Common stock symbols pattern (2-5 capital letters)
        stock_pattern = r'\b([A-Z]{2,5})\b'
        for match in re.finditer(stock_pattern, text):
            symbol = match.group(1)
            # Filter out common words that might match
            if symbol not in ['THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'HAD', 'HIS', 'HOW', 'ITS', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'HAS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE']:
                entities.append({
                    "name": symbol,
                    "type": "company",
                    "context": f"Stock symbol mentioned in conversation"
                })

        # Dollar amounts pattern
        dollar_pattern = r'\$[\d,]+(?:\.\d{2})?'
        for match in re.finditer(dollar_pattern, text):
            amount = match.group(0)
            entities.append({
                "name": amount,
                "type": "metric",
                "context": "Financial amount mentioned"
            })

        # Percentage pattern
        percent_pattern = r'\b\d+(?:\.\d+)?%'
        for match in re.finditer(percent_pattern, text):
            percent = match.group(0)
            entities.append({
                "name": percent,
                "type": "metric",
                "context": "Percentage value mentioned"
            })

        return entities[:10]  # Limit to 10 entities

    def _extract_entities_simple(self, text: str) -> List[Dict[str, Any]]:
        """Simple keyword-based entity extraction as last resort."""
        entities = []

        # Common financial keywords
        financial_keywords = {
            'companies': ['Apple', 'Microsoft', 'Google', 'Amazon', 'Tesla', 'Meta', 'Netflix', 'Nvidia'],
            'concepts': ['dividend', 'earnings', 'revenue', 'profit', 'growth', 'volatility', 'market cap', 'P/E ratio'],
            'strategies': ['buy and hold', 'day trading', 'value investing', 'growth investing', 'dividend investing']
        }

        text_lower = text.lower()

        for category, keywords in financial_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    entity_type = "company" if category == "companies" else "concept" if category == "concepts" else "strategy"
                    entities.append({
                        "name": keyword,
                        "type": entity_type,
                        "context": f"Financial {entity_type} mentioned in conversation"
                    })

        return entities[:5]  # Limit to 5 entities

    async def _create_medium_term_summary(self, conv_id: str, messages: List[Dict[str, Any]],
                                        user_id: Optional[str]) -> None:
        """Create intelligent medium-term summary using GPT-4o mini."""
        try:
            # Filter to conversation messages
            conv_messages = [m for m in messages if m.get("role") in ["user", "assistant"]]
            if len(conv_messages) < 4:
                return

            # Take older messages for summarization (keep recent ones raw)
            messages_to_summarize = conv_messages[:-8]  # Keep last 8 messages raw

            if not messages_to_summarize:
                return

            conversation_text = "\n".join([
                f"{m.get('role', '')}: {truncate_by_tokens(m.get('content', ''), 200)}"
                for m in messages_to_summarize
            ])

            summary_prompt = f"""Create an intelligent summary of this financial conversation focusing on:

1. Key investment topics and stocks discussed
2. Important financial data, metrics, or analysis mentioned
3. User preferences, goals, or investment strategies revealed
4. Decisions made or recommendations given
5. Context that would be valuable for future conversations

Format as structured summary with clear sections. Be concise but preserve important details.

Conversation:
{conversation_text}

Summary:"""

            client, model_name = get_client_for_model(self.gpt4o_mini_key)

            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=400,
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
                logger.debug(f"Created medium-term summary for conversation {conv_id[:8]}")

        except Exception as e:
            logger.error(f"Error creating medium-term summary: {e}")

    async def _store_long_term_memory(self, conv_id: str, messages: List[Dict[str, Any]],
                                    user_id: Optional[str]) -> None:
        """Store conversation summary in long-term RAG memory."""
        try:
            if not RAG_ENABLED:
                return

            # Create comprehensive summary for long-term storage
            conv_messages = [m for m in messages if m.get("role") in ["user", "assistant"]]

            conversation_text = "\n".join([
                f"{m.get('role', '')}: {truncate_by_tokens(m.get('content', ''), 300)}"
                for m in conv_messages
            ])

            long_term_prompt = f"""Create a comprehensive summary of this financial conversation for long-term memory storage. Include:

1. All companies, stocks, and financial instruments discussed
2. Key financial metrics, ratios, or data points mentioned
3. Investment strategies, analysis, or recommendations
4. User goals, preferences, or investment profile insights
5. Important decisions or conclusions reached
6. Market conditions or economic factors discussed

Make this summary detailed enough to provide valuable context in future conversations months later.

Conversation:
{truncate_by_tokens(conversation_text, 2000)}

Long-term Summary:"""

            client, model_name = get_client_for_model(self.gpt4o_mini_key)

            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": long_term_prompt}],
                max_tokens=600,
                temperature=0.1
            )

            long_term_summary = response.choices[0].message.content or ""

            if long_term_summary:
                # Store in long-term cache
                summary_key = f"longterm:{user_id or 'anon'}:{conv_id}"
                LONG_TERM_SUMMARIES[summary_key] = {
                    "summary": long_term_summary,
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "conv_id": conv_id
                }

                # Also store in RAG system if available
                await self._store_in_rag_system(long_term_summary, conv_id, user_id)

        except Exception as e:
            logger.error(f"Error storing long-term memory: {e}")

    async def _store_in_rag_system(self, summary: str, conv_id: str, user_id: Optional[str]) -> None:
        """Store summary in RAG vector database."""
        try:
            if not RAG_ENABLED:
                return

            from importlib import import_module
            Document = import_module("langchain_core.documents").Document

            vs = _get_vectorstore()
            if not vs:
                return

            # Create document with metadata
            doc = Document(
                page_content=summary,
                metadata={
                    "type": "conversation_summary",
                    "conv_id": conv_id,
                    "user_id": user_id or "anonymous",
                    "timestamp": datetime.now().isoformat(),
                    "source": "conversation"
                }
            )

            # Add to vector store
            vs.add_documents([doc])

        except Exception as e:
            logger.error(f"Error storing in RAG system: {e}")

    def _get_short_term_memory(self, conv_id: str) -> str:
        """Get short-term memory for current session."""
        try:
            memory_data = SHORT_TERM_CACHE.get(conv_id)
            if not memory_data:
                return ""

            messages = memory_data.get("messages", [])
            if not messages:
                return ""

            # Return recent conversation context
            recent_messages = [m for m in messages[-6:] if m.get("role") in ["user", "assistant"]]

            context_parts = []
            for msg in recent_messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if content:
                    truncated = truncate_by_tokens(content, 150)
                    context_parts.append(f"{role}: {truncated}")

            return "\n".join(context_parts) if context_parts else ""

        except Exception as e:
            logger.error(f"Error getting short-term memory: {e}")
            return ""

    def _get_medium_term_memory(self, conv_id: str, user_id: Optional[str]) -> str:
        """Get medium-term summary memory."""
        try:
            summary_data = MEDIUM_TERM_CACHE.get(f"{conv_id}:summary")
            if summary_data:
                return summary_data.get("summary", "")
            return ""
        except Exception as e:
            logger.error(f"Error getting medium-term memory: {e}")
            return ""

    def _get_long_term_memory(self, user_id: Optional[str], query: str) -> str:
        """Get relevant long-term memory summaries."""
        try:
            relevant_summaries = []
            query_lower = query.lower()

            # Search through long-term summaries for relevant content
            for key, summary_data in LONG_TERM_SUMMARIES.items():
                if summary_data.get("user_id") == user_id:
                    summary_text = summary_data.get("summary", "")
                    # Simple relevance check - could be enhanced with embeddings
                    if any(word in summary_text.lower() for word in query_lower.split()):
                        relevant_summaries.append(summary_text)

            return "\n\n".join(relevant_summaries[:2])  # Return top 2 relevant summaries

        except Exception as e:
            logger.error(f"Error getting long-term memory: {e}")
            return ""

    def _get_relevant_entities(self, query: str, user_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get relevant entities based on query."""
        try:
            relevant_entities = []
            query_lower = query.lower()

            for key, entity_data in ENTITY_MEMORY.items():
                if entity_data.get("user_id") == user_id:
                    entity_name = entity_data.get("name", "").lower()
                    entity_context = entity_data.get("context", "").lower()

                    # Check if entity is relevant to query
                    if (entity_name in query_lower or
                        any(word in entity_context for word in query_lower.split())):
                        relevant_entities.append({
                            "name": entity_data.get("name"),
                            "type": entity_data.get("type"),
                            "context": entity_data.get("context")
                        })

            return relevant_entities[:5]  # Return top 5 relevant entities

        except Exception as e:
            logger.error(f"Error getting relevant entities: {e}")
            return []

    async def _get_enhanced_rag_context(self, query: str, memory_context: Dict[str, Any]) -> str:
        """Get enhanced RAG context using query + memory context."""
        try:
            if not RAG_ENABLED:
                return ""

            # Enhance query with memory context for better retrieval
            enhanced_query = query

            # Add entity context to query
            if memory_context.get("entities"):
                entity_names = [e["name"] for e in memory_context["entities"]]
                enhanced_query += f" Related to: {', '.join(entity_names)}"

            # Add short-term context
            if memory_context.get("short_term"):
                recent_context = truncate_by_tokens(memory_context["short_term"], 100)
                enhanced_query += f" Context: {recent_context}"

            # Search RAG system
            rag_results = rag_search(enhanced_query, k=4)

            if not rag_results.get("results"):
                return ""

            # Build context from results
            context_parts = []
            total_tokens = 0
            max_rag_tokens = CHUNK_MAX_TOKENS * 2  # Allow more tokens for RAG context

            for result in rag_results["results"]:
                chunk_text = result.get("text", "")
                chunk_tokens = estimate_tokens(chunk_text)

                if total_tokens + chunk_tokens > max_rag_tokens:
                    break

                context_parts.append(chunk_text)
                total_tokens += chunk_tokens

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error getting enhanced RAG context: {e}")
            return ""

# Global memory service instance
memory_service = MemoryService()

# Export the class and instance for easy importing
__all__ = ['MemoryService', 'memory_service']
