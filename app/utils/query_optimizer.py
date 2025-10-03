"""Fast-path query detection for performance optimization."""
import re
from typing import Tuple

# Patterns for simple queries that can use fast model and skip heavy processing
SIMPLE_GREETING_PATTERNS = [
    r'(?i)^(hi|hello|hey|howdy|sup)(\s+(there|everyone|all))?\s*[\s.,!?]*$',
    r'(?i)^(good\s+(morning|afternoon|evening|day))[\s.,!?]*$',
    r'(?i)^(おはよう|こんにちは|こんばんは|やあ|どうも)[\s.,!?]*$',
]

SIMPLE_THANKS_PATTERNS = [
    r'(?i)^(thanks?|thank\s+you|thx|ty|appreciate\s+it?)[\s.,!?]*$',
    r'(?i)^(ありがとう|ありがとうございます|どうも)[\s.,!?]*$',
]

SIMPLE_GOODBYE_PATTERNS = [
    r'(?i)^(bye|goodbye|see\s+you|see\s+ya|later|farewell)[\s.,!?]*$',
    r'(?i)^(さようなら|バイバイ|じゃあね|またね)[\s.,!?]*$',
]

# Queries that need only basic tool access, no RAG/web search
BASIC_TOOL_PATTERNS = [
    r'(?i)^(what|show|get|fetch|give\s+me).*\b(stock\s+price|quote|current\s+price)\b.*for\s+\w+[\s.,!?]*$',
    r'(?i)^\w{1,5}\s+(stock|price|quote)[\s.,!?]*$',  # e.g., "AAPL stock", "TSLA price"
    r'(?i)^price\s+of\s+\w+[\s.,!?]*$',  # e.g., "price of AAPL"
]

# Compile patterns for performance
_SIMPLE_GREETING_RE = [re.compile(p) for p in SIMPLE_GREETING_PATTERNS]
_SIMPLE_THANKS_RE = [re.compile(p) for p in SIMPLE_THANKS_PATTERNS]
_SIMPLE_GOODBYE_RE = [re.compile(p) for p in SIMPLE_GOODBYE_PATTERNS]
_BASIC_TOOL_RE = [re.compile(p) for p in BASIC_TOOL_PATTERNS]


def is_simple_query(prompt: str) -> Tuple[bool, str]:
    """
    Detect if a query is simple and can use fast-path optimization.
    
    Args:
        prompt: User's input prompt
    
    Returns:
        Tuple of (is_simple, query_type) where query_type is one of:
        - 'greeting': Simple greeting
        - 'thanks': Thank you message
        - 'goodbye': Farewell message
        - 'basic_tool': Basic tool query (stock price, etc.)
        - 'complex': Complex query needing full processing
    """
    if not prompt or len(prompt.strip()) == 0:
        return False, 'complex'
    
    prompt_clean = prompt.strip()
    
    # Check for simple greetings
    for pattern in _SIMPLE_GREETING_RE:
        if pattern.match(prompt_clean):
            return True, 'greeting'
    
    # Check for thanks
    for pattern in _SIMPLE_THANKS_RE:
        if pattern.match(prompt_clean):
            return True, 'thanks'
    
    # Check for goodbye
    for pattern in _SIMPLE_GOODBYE_RE:
        if pattern.match(prompt_clean):
            return True, 'goodbye'
    
    # Check for basic tool queries
    for pattern in _BASIC_TOOL_RE:
        if pattern.match(prompt_clean):
            return True, 'basic_tool'
    
    # Check length - very short queries are likely simple
    if len(prompt_clean) < 15 and not any(word in prompt_clean.lower() for word in ['why', 'how', 'explain', 'compare', 'analyze']):
        # Could be a simple query like "AAPL" or "Tesla stock"
        words = prompt_clean.split()
        if len(words) <= 3:
            return True, 'basic_tool'
    
    return False, 'complex'


def should_skip_rag_and_web_search(prompt: str) -> bool:
    """
    Determine if RAG and web search can be skipped for performance.
    
    Args:
        prompt: User's input prompt
    
    Returns:
        True if RAG/web search can be skipped, False otherwise
    """
    is_simple, query_type = is_simple_query(prompt)
    
    # Skip for greetings, thanks, and goodbye
    if query_type in ('greeting', 'thanks', 'goodbye'):
        return True
    
    # Skip for basic tool queries (stock price lookups)
    if query_type == 'basic_tool':
        return True
    
    # Don't skip for complex queries
    return False


def get_fast_model_recommendation(prompt: str) -> str:
    """
    Recommend a fast model for simple queries.
    
    Args:
        prompt: User's input prompt
    
    Returns:
        Recommended model key, or empty string if no recommendation
    """
    is_simple, query_type = is_simple_query(prompt)
    
    if query_type in ('greeting', 'thanks', 'goodbye'):
        # Use fastest model for conversational responses
        return 'gpt-4o-mini'
    
    if query_type == 'basic_tool':
        # Use fast model for basic tool queries
        return 'gpt-4o-mini'
    
    # No recommendation for complex queries
    return ''
