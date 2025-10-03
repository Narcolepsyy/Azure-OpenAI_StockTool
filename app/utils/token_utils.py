"""Token calculation utilities with caching for performance optimization."""
import json
import logging
from typing import Dict, Any, List
from cachetools import LRUCache

logger = logging.getLogger(__name__)

# Global token cache to avoid recalculating tokens for the same content
_token_cache = LRUCache(maxsize=1000)  # Cache up to 1000 token calculations

def estimate_tokens(text: str) -> int:
    """Estimate token count for text (simple heuristic: ~4 chars per token)."""
    if not text:
        return 0
    # Simple estimation: average ~4 characters per token for English
    # This is a rough approximation, could be replaced with tiktoken for accuracy
    return max(1, len(text) // 4)

def get_cached_token_count(message: Dict[str, Any]) -> int:
    """Get token count for a message with caching to avoid recalculation."""
    # Check if message already has cached token count
    if isinstance(message, dict) and '_cached_tokens' in message:
        return message['_cached_tokens']
    
    # Create a stable key for caching (exclude mutable fields)
    cache_key_data = {
        'role': message.get('role', ''),
        'content': message.get('content', ''),
        'name': message.get('name', ''),
        'tool_calls': message.get('tool_calls', []),
        'tool_call_id': message.get('tool_call_id', '')
    }
    
    # Create hash-friendly key
    try:
        cache_key = json.dumps(cache_key_data, sort_keys=True)
    except (TypeError, ValueError):
        # Fallback for non-serializable content
        cache_key = str(cache_key_data)
    
    # Check cache first
    if cache_key in _token_cache:
        token_count = _token_cache[cache_key]
        # Store in message for immediate reuse
        if isinstance(message, dict):
            message['_cached_tokens'] = token_count
        return token_count
    
    # Calculate token count
    try:
        message_json = json.dumps(message, ensure_ascii=False)
        token_count = estimate_tokens(message_json)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize message for token counting: {e}")
        # Fallback to content-only token counting
        content = message.get('content', '') if isinstance(message, dict) else str(message)
        token_count = estimate_tokens(content)
    
    # Cache the result
    _token_cache[cache_key] = token_count
    
    # Store in message for immediate reuse
    if isinstance(message, dict):
        message['_cached_tokens'] = token_count
    
    return token_count

def calculate_total_tokens(messages: List[Dict[str, Any]]) -> int:
    """Calculate total tokens for a list of messages with caching."""
    return sum(get_cached_token_count(msg) for msg in messages)

def optimize_messages_for_token_budget(
    messages: List[Dict[str, Any]], 
    max_tokens: int,
    preserve_system: bool = True,
    preserve_recent_user: int = 1
) -> List[Dict[str, Any]]:
    """Optimize message list to fit within token budget while preserving important messages."""
    if not messages:
        return messages
    
    # Pre-calculate all token counts (cached)
    for msg in messages:
        get_cached_token_count(msg)
    
    current_tokens = calculate_total_tokens(messages)
    if current_tokens <= max_tokens:
        return messages
    
    logger.info(f"Optimizing messages: {current_tokens} tokens > {max_tokens} budget")
    
    # First, identify tool call/tool response pairs to keep them together
    tool_call_groups = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg.get('role', '')
        
        if role == 'assistant' and msg.get('tool_calls'):
            # Found assistant message with tool calls, collect all following tool messages
            group = [i]  # Start with assistant message
            j = i + 1
            
            # Collect all consecutive tool messages that respond to this tool call
            while j < len(messages) and messages[j].get('role') == 'tool':
                group.append(j)
                j += 1
            
            tool_call_groups.append(group)
            i = j  # Continue after the tool group
        else:
            i += 1
    
    # Identify messages to preserve
    preserved_messages = []
    other_messages = []
    tool_group_indices = set()
    
    # Mark all indices that are part of tool call groups
    for group in tool_call_groups:
        tool_group_indices.update(group)
    
    for i, msg in enumerate(messages):
        role = msg.get('role', '')
        
        # Always preserve system messages
        if preserve_system and role == 'system':
            preserved_messages.append((i, msg))
        # Preserve recent user messages
        elif role == 'user' and i >= len(messages) - preserve_recent_user:
            preserved_messages.append((i, msg))
        else:
            other_messages.append((i, msg))
    
    # Calculate tokens for preserved messages
    preserved_tokens = sum(get_cached_token_count(msg) for _, msg in preserved_messages)
    
    if preserved_tokens >= max_tokens:
        logger.warning(f"Preserved messages ({preserved_tokens} tokens) exceed budget")
        # Keep only the most essential (last user message + system)
        essential = []
        if preserve_system:
            system_msgs = [msg for _, msg in preserved_messages if msg.get('role') == 'system']
            if system_msgs:
                essential.append(system_msgs[-1])  # Keep last system message
        
        # Keep last user message
        user_msgs = [msg for _, msg in preserved_messages if msg.get('role') == 'user']
        if user_msgs:
            essential.append(user_msgs[-1])
        
        return essential
    
    # Add other messages until we hit the budget, but keep tool call groups together
    remaining_budget = max_tokens - preserved_tokens
    selected_other = []
    selected_indices = set()
    
    # First, try to add complete tool call groups from newest to oldest
    for group in reversed(tool_call_groups):
        group_msgs = [messages[idx] for idx in group]
        group_tokens = sum(get_cached_token_count(msg) for msg in group_msgs)
        
        # Only add if we can fit the entire group
        if group_tokens <= remaining_budget and not any(idx in selected_indices for idx in group):
            selected_other.extend(group_msgs)
            selected_indices.update(group)
            remaining_budget -= group_tokens
    
    # Then add non-tool-group messages by recency
    non_tool_other = [(i, msg) for i, msg in other_messages if i not in tool_group_indices and i not in selected_indices]
    non_tool_other.sort(key=lambda x: x[0], reverse=True)  # Sort by recency
    
    for i, msg in non_tool_other:
        msg_tokens = get_cached_token_count(msg)
        if msg_tokens <= remaining_budget:
            selected_other.append(msg)
            selected_indices.add(i)
            remaining_budget -= msg_tokens
    
    # If we have leftover budget and couldn't fit any messages, try truncating the most recent tool group
    if remaining_budget > 100 and not selected_other and tool_call_groups:
        # Try to fit the most recent tool group with truncated tool responses
        latest_group = tool_call_groups[-1]
        group_msgs = [messages[idx] for idx in latest_group]
        
        # Always keep the assistant message with tool_calls
        assistant_msg = group_msgs[0] if group_msgs and group_msgs[0].get('role') == 'assistant' else None
        if assistant_msg:
            assistant_tokens = get_cached_token_count(assistant_msg)
            if assistant_tokens <= remaining_budget:
                selected_other.append(assistant_msg)
                remaining_budget -= assistant_tokens
                
                # Try to add truncated tool responses
                for msg in group_msgs[1:]:
                    if msg.get('role') == 'tool':
                        msg_tokens = get_cached_token_count(msg)
                        if msg_tokens <= remaining_budget:
                            selected_other.append(msg)
                            remaining_budget -= msg_tokens
                        elif remaining_budget > 50:  # Only truncate if we have meaningful space
                            truncated_content = str(msg.get('content', ''))[:remaining_budget * 4]
                            truncated_msg = {**msg, 'content': truncated_content + '...[truncated]'}
                            selected_other.append(truncated_msg)
                            break
    
    # Combine preserved and selected messages
    result_messages = [msg for _, msg in preserved_messages] + selected_other
    
    # Sort by original message index to maintain conversation flow
    message_indices = {id(msg): i for i, msg in enumerate(messages)}
    result_messages.sort(key=lambda x: message_indices.get(id(x), float('inf')))
    
    # Validate that tool call/response pairs are complete
    validated_messages = []
    i = 0
    while i < len(result_messages):
        msg = result_messages[i]
        role = msg.get('role', '')
        
        if role == 'assistant' and msg.get('tool_calls'):
            # Assistant message with tool calls - check if all tool responses are present
            tool_calls = msg.get('tool_calls', [])
            expected_tool_call_ids = {tc.get('id') if hasattr(tc, 'get') else tc['id'] for tc in tool_calls}
            
            # Look ahead for corresponding tool messages
            j = i + 1
            found_tool_call_ids = set()
            tool_responses = []
            
            while j < len(result_messages) and result_messages[j].get('role') == 'tool':
                tool_msg = result_messages[j]
                tool_call_id = tool_msg.get('tool_call_id')
                if tool_call_id in expected_tool_call_ids:
                    found_tool_call_ids.add(tool_call_id)
                    tool_responses.append(tool_msg)
                j += 1
            
            # Only include if all tool calls have responses
            if found_tool_call_ids == expected_tool_call_ids:
                validated_messages.append(msg)
                validated_messages.extend(tool_responses)
            else:
                missing_ids = expected_tool_call_ids - found_tool_call_ids
                logger.warning(f"Removing incomplete tool call group: missing responses for {missing_ids}")
            
            i = j  # Skip past the tool messages we've processed
        elif role == 'tool':
            # Check if there's a preceding assistant message with tool_calls that we kept
            if (i > 0 and 
                validated_messages and 
                validated_messages[-1].get('role') == 'assistant' and 
                validated_messages[-1].get('tool_calls')):
                # This tool message should have been processed in the assistant block above
                # If we reach here, it means it's an extra tool message
                logger.warning(f"Skipping extra tool message at position {i}")
            else:
                # Orphaned tool message
                logger.warning(f"Removing orphaned tool message at position {i}")
            i += 1
        else:
            validated_messages.append(msg)
            i += 1
    
    final_tokens = calculate_total_tokens(validated_messages)
    removed_count = len(result_messages) - len(validated_messages)
    logger.info(f"Optimized to {len(validated_messages)} messages, {final_tokens} tokens (removed {removed_count} incomplete/orphaned messages)")
    
    return validated_messages

def clear_token_cache():
    """Clear the token cache (useful for testing or memory management)."""
    global _token_cache
    _token_cache.clear()
    logger.debug("Token cache cleared")

def get_token_cache_stats() -> Dict[str, Any]:
    """Get token cache statistics."""
    return {
        'size': len(_token_cache),
        'maxsize': _token_cache.maxsize,
        'hits': getattr(_token_cache, 'hits', 0),
        'misses': getattr(_token_cache, 'misses', 0)
    }