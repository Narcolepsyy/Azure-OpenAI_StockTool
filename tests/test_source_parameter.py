#!/usr/bin/env python3
"""Test the source parameter handling for web search."""

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
            
            # Handle source parameter for web search tools
            if mapped_name in ["web_search", "perplexity_search"] and "source" in args_dict:
                source = args_dict.pop("source")
                # If source is "news", prioritize recent content and enable synthesis
                if source == "news":
                    args_dict["include_recent"] = True
                    args_dict["synthesize_answer"] = True
            
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

def test_source_parameter():
    """Test the source parameter handling."""
    
    test_text = '<|start|>assistant<|channel|>commentary to=functions.web_search <|constrain|>json<|message|>{"query": "8359 2023年第2四半期 売上 高 2023", "top_n": 10, "source": "news"}<|call|>'
    
    print("Testing source parameter handling:")
    print("=" * 60)
    print(f"Input: {test_text}")
    print()
    
    # Test regex matching
    matches = list(_PSEUDO_TOOL_RE.finditer(test_text))
    print(f"Found {len(matches)} matches")
    
    if matches:
        match = matches[0]
        print(f"Tool name (group 1): '{match.group(1)}'")
        print(f"JSON payload (group 2): '{match.group(2)}'")
        
        # Parse original payload
        try:
            original_payload = json.loads(match.group(2))
            print(f"Original payload: {original_payload}")
        except:
            pass
    
    # Test full extraction
    tool_calls = _extract_pseudo_tool_calls(test_text)
    
    if tool_calls:
        call = tool_calls[0]
        args = json.loads(call['function']['arguments'])
        
        print(f"\nFunction name: {call['function']['name']}")
        print(f"Mapped arguments: {args}")
        
        # Check parameter mapping
        if "max_results" in args and args["max_results"] == 10:
            print(f"✅ top_n correctly mapped to max_results: {args['max_results']}")
        else:
            print(f"❌ top_n mapping failed")
        
        # Check source parameter was handled
        if "source" not in args:
            print(f"✅ source parameter removed correctly")
        else:
            print(f"❌ source parameter should have been removed")
        
        # Check that source="news" enabled the right settings
        if args.get("include_recent") is True:
            print(f"✅ include_recent set to True for news source")
        else:
            print(f"❌ include_recent should be True for news source")
        
        if args.get("synthesize_answer") is True:
            print(f"✅ synthesize_answer set to True for news source")
        else:
            print(f"❌ synthesize_answer should be True for news source")
            
    else:
        print("❌ No tool calls extracted")

if __name__ == "__main__":
    test_source_parameter()