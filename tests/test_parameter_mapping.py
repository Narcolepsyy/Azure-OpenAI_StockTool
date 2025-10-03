#!/usr/bin/env python3
"""Test script to verify the updated pseudo tool call parsing with various parameter formats."""

import re
import json
from typing import List, Dict, Any

# Copy the updated regex and function from the chat router
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
            
            # Map various result count parameters to max_results for web search compatibility
            if "max_results" not in args_dict:
                if "top_k" in args_dict:
                    args_dict["max_results"] = args_dict.pop("top_k")
                elif "top_n" in args_dict:
                    args_dict["max_results"] = args_dict.pop("top_n")
                elif "num_results" in args_dict:
                    args_dict["max_results"] = args_dict.pop("num_results")
                elif "limit" in args_dict:
                    args_dict["max_results"] = args_dict.pop("limit")
            
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

def test_various_parameter_formats():
    """Test various parameter formats used by different OSS models."""
    
    test_cases = [
        # Original case with top_k and recency_days
        '<|start|>assistant<|channel|>commentary to=functions.web_search <|constrain|>json<|message|>{"query": "2025年9月22日 銀行 セクター パフォーマンス 日本 株式", "top_k": 10, "recency_days": 1}<|call|>',
        
        # New case with top_n 
        '<|start|>assistant<|channel|>commentary to=functions.web_search <|constrain|>json<|message|>{"query": "2025年9月22日 銀行 セクター 日本株 パフォーマンス", "top_n": 10, "include_recent": true}<|call|>',
        
        # Case with num_results
        '<|start|>assistant<|channel|>commentary to=web_search <|message|>{"query": "test query", "num_results": 5, "synthesize_answer": false}<|call|>',
        
        # Case with limit
        '<|start|>assistant<|channel|>commentary to=web_search <|message|>{"query": "another test", "limit": 15}<|call|>',
        
        # Case with max_results (should not be changed)
        '<|start|>assistant<|channel|>commentary to=web_search <|message|>{"query": "standard format", "max_results": 8}<|call|>'
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}:")
        print(f"Input: {test_text[:80]}...")
        
        # Test regex matching
        matches = list(_PSEUDO_TOOL_RE.finditer(test_text))
        if matches:
            match = matches[0]
            print(f"Tool name: {match.group(1)}")
            print(f"JSON payload: {match.group(2)}")
        
        # Test full extraction
        tool_calls = _extract_pseudo_tool_calls(test_text)
        
        if tool_calls:
            call = tool_calls[0]
            print(f"Function name: {call['function']['name']}")
            args = json.loads(call['function']['arguments'])
            print(f"Mapped arguments: {args}")
            
            # Check if parameter mapping worked correctly
            if "max_results" in args:
                print(f"✅ max_results: {args['max_results']}")
            if "include_recent" in args:
                print(f"✅ include_recent: {args['include_recent']}")
        else:
            print("❌ No tool calls extracted")

if __name__ == "__main__":
    test_various_parameter_formats()