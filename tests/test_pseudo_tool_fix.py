#!/usr/bin/env python3
"""Test script to verify the pseudo tool call parsing fix."""

import re
import json
from typing import List, Dict, Any

# Copy the regex and function from the chat router
_PSEUDO_TOOL_RE = re.compile(
    r"<\|start\|>assistant<\|channel\|>commentary\s+to=(?:functions\.)?(\w+)(?:\s+<\|constrain\|>json)?\s*<\|message\|>(\{.*?\})<\|call\|>",
    re.DOTALL | re.IGNORECASE,
)

def _extract_pseudo_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Parse pseudo tool calls embedded in assistant text into standard tool_call format."""
    calls: List[Dict[str, Any]] = []
    if not text:
        return calls
    try:
        matches = list(_PSEUDO_TOOL_RE.finditer(text))
        counter = 0
        for m in matches:
            # Extract tool name from group 1 and JSON payload from group 2
            tool_name = m.group(1)
            raw_json = m.group(2)
            
            try:
                payload = json.loads(raw_json)
            except Exception:
                continue
            
            # Use tool name from regex match or fallback to payload
            name = tool_name or payload.get("tool") or payload.get("name")
            if not name:
                continue
            
            # Handle tool name mapping for OSS models
            tool_name_mapping = {
                "functions.web_search": "web_search",
                "web_search": "web_search",
                "perplexity_search": "perplexity_search"
            }
            mapped_name = tool_name_mapping.get(name, name)
            
            # Build args, remapping common parameter variations
            args_dict = {k: v for k, v in payload.items() if k not in ("tool", "name")}
            
            # Parameter mapping for different models
            if "ticker" in args_dict and "symbol" not in args_dict:
                args_dict["symbol"] = args_dict.pop("ticker")
            
            # Map top_k to max_results for web search compatibility
            if "top_k" in args_dict and "max_results" not in args_dict:
                args_dict["max_results"] = args_dict.pop("top_k")
            
            # Map recency_days to include_recent for web search compatibility
            if "recency_days" in args_dict and "include_recent" not in args_dict:
                recency_days = args_dict.pop("recency_days")
                # Set include_recent=True if recency_days <= 7
                args_dict["include_recent"] = int(recency_days) <= 7 if isinstance(recency_days, (int, str)) else True
            
            try:
                args_json = json.dumps(args_dict)
            except Exception:
                args_json = "{}"
            counter += 1
            calls.append({
                "id": f"pseudo-{counter}",
                "type": "function",
                "function": {"name": mapped_name, "arguments": args_json}
            })
    except Exception as e:
        print(f"Error parsing pseudo tool calls: {e}")
        return []
    return calls

def test_pseudo_tool_call_parsing():
    """Test the pseudo tool call parsing with your example."""
    test_text = '<|start|>assistant<|channel|>commentary to=functions.web_search <|constrain|>json<|message|>{"query": "2025年9月22日 銀行 セクター パフォーマンス 日本 株式", "top_k": 10, "recency_days": 1}<|call|> there a problem with gpt oss 120b it call correct tool and using correct tool but return weird respond'
    
    print("Testing pseudo tool call parsing...")
    print(f"Input text: {test_text[:100]}...")
    
    # Test regex matching
    matches = list(_PSEUDO_TOOL_RE.finditer(test_text))
    print(f"Found {len(matches)} matches")
    
    if matches:
        for i, match in enumerate(matches):
            print(f"Match {i + 1}:")
            print(f"  Tool name (group 1): {match.group(1)}")
            print(f"  JSON payload (group 2): {match.group(2)}")
    
    # Test full extraction
    tool_calls = _extract_pseudo_tool_calls(test_text)
    print(f"\nExtracted {len(tool_calls)} tool calls:")
    
    for i, call in enumerate(tool_calls):
        print(f"Tool call {i + 1}:")
        print(f"  ID: {call['id']}")
        print(f"  Function name: {call['function']['name']}")
        print(f"  Arguments: {call['function']['arguments']}")
        
        # Parse arguments to check mapping
        try:
            args = json.loads(call['function']['arguments'])
            print(f"  Parsed args: {args}")
        except Exception as e:
            print(f"  Error parsing args: {e}")

if __name__ == "__main__":
    test_pseudo_tool_call_parsing()