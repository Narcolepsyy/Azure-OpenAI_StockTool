#!/usr/bin/env python3
"""Test that web search still works with the updated parameter mapping logic."""

import re
import json
from typing import List, Dict, Any

# Updated regex pattern
_PSEUDO_TOOL_RE = re.compile(
    r"<\|start\|>assistant<\|channel\|>commentary\s+to=(?:functions\.)?(\w+)(?:<\|channel\|>commentary\s+json|(?:\s+<\|constrain\|>json)?)\s*<\|message\|>(\{.*?\})<\|call\|>",
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
                "perplexity_search": "perplexity_search",
                "functions.get_augmented_news": "get_augmented_news",
                "functions.get_company_profile": "get_company_profile",
                "functions.get_stock_quote": "get_stock_quote",
                "functions.get_historical_prices": "get_historical_prices",
                "functions.get_risk_assessment": "get_risk_assessment",
                "functions.rag_search": "rag_search"
            }
            mapped_name = tool_name_mapping.get(name, name)
            
            # Build args, remapping common parameter variations
            args_dict = {k: v for k, v in payload.items() if k not in ("tool", "name")}
            
            # Parameter mapping for different models
            if "ticker" in args_dict and "symbol" not in args_dict:
                args_dict["symbol"] = args_dict.pop("ticker")
            
            # Map various result count parameters to max_results for web search compatibility ONLY
            if mapped_name in ["web_search", "perplexity_search"] and "max_results" not in args_dict:
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

def test_mixed_tools():
    """Test both web search and non-web search tools."""
    
    test_cases = [
        # Web search - should map limit to max_results
        ('<|start|>assistant<|channel|>commentary to=functions.web_search <|message|>{"query": "test", "limit": 15}<|call|>', "web_search", True),
        
        # Get augmented news - should keep limit as limit
        ('<|start|>assistant<|channel|>commentary to=functions.get_augmented_news <|message|>{"symbol": "AAPL", "limit": 10}<|call|>', "get_augmented_news", False),
        
        # Web search with top_n - should map to max_results  
        ('<|start|>assistant<|channel|>commentary to=web_search <|message|>{"query": "test2", "top_n": 8}<|call|>', "web_search", True),
    ]
    
    for i, (test_text, expected_tool, should_have_max_results) in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {expected_tool}")
        print(f"Should have max_results: {should_have_max_results}")
        
        tool_calls = _extract_pseudo_tool_calls(test_text)
        
        if tool_calls:
            call = tool_calls[0]
            args = json.loads(call['function']['arguments'])
            
            print(f"Function name: {call['function']['name']}")
            print(f"Arguments: {args}")
            
            # Check tool name
            if call['function']['name'] == expected_tool:
                print(f"✅ Tool name correct: {expected_tool}")
            else:
                print(f"❌ Tool name wrong: expected {expected_tool}, got {call['function']['name']}")
            
            # Check parameter mapping
            has_max_results = "max_results" in args
            has_limit = "limit" in args
            
            if should_have_max_results:
                if has_max_results and not has_limit:
                    print(f"✅ Correctly mapped to max_results: {args['max_results']}")
                else:
                    print(f"❌ Should have max_results but has limit: {has_limit}, max_results: {has_max_results}")
            else:
                if has_limit and not has_max_results:
                    print(f"✅ Correctly preserved limit: {args['limit']}")
                else:
                    print(f"❌ Should have limit but has max_results: {has_max_results}, limit: {has_limit}")
        else:
            print("❌ No tool calls extracted")

if __name__ == "__main__":
    test_mixed_tools()