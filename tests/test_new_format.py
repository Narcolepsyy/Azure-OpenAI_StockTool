#!/usr/bin/env python3
"""Test the new format variation with <|channel|>commentary json."""

import re
import json

# Updated regex pattern
_PSEUDO_TOOL_RE = re.compile(
    r"<\|start\|>assistant<\|channel\|>commentary\s+to=(?:functions\.)?(\w+)(?:<\|channel\|>commentary\s+json|(?:\s+<\|constrain\|>json)?)\s*<\|message\|>(\{.*?\})<\|call\|>",
    re.DOTALL | re.IGNORECASE,
)

def test_new_format():
    # Test the new format variation
    test_text = '<|start|>assistant<|channel|>commentary to=functions.web_search<|channel|>commentary json<|message|>{"query": "日本 地域銀行 セクター指数 ティッカー", "top_n": 10, "synthesize_answer": true}<|call|>'
    
    print("Testing new format variation:")
    print("=" * 60)
    print(f"Input: {test_text}")
    print()
    
    matches = list(_PSEUDO_TOOL_RE.finditer(test_text))
    print(f"Found {len(matches)} matches")
    
    if matches:
        match = matches[0]
        print(f"Tool name (group 1): '{match.group(1)}'")
        print(f"JSON payload (group 2): '{match.group(2)}'")
        
        # Test JSON parsing
        try:
            payload = json.loads(match.group(2))
            print(f"Parsed JSON: {payload}")
            
            # Check parameter mapping
            if "top_n" in payload:
                print(f"✅ top_n parameter found: {payload['top_n']}")
            if "synthesize_answer" in payload:
                print(f"✅ synthesize_answer parameter found: {payload['synthesize_answer']}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
    else:
        print("❌ No matches found")
    
    # Also test the original formats still work
    print("\n" + "=" * 60)
    print("Testing backward compatibility:")
    
    old_formats = [
        '<|start|>assistant<|channel|>commentary to=functions.web_search <|constrain|>json<|message|>{"query": "test", "top_k": 5}<|call|>',
        '<|start|>assistant<|channel|>commentary to=web_search<|message|>{"query": "test2", "limit": 10}<|call|>'
    ]
    
    for i, old_text in enumerate(old_formats, 1):
        print(f"\nOld format {i}: {old_text[:50]}...")
        matches = list(_PSEUDO_TOOL_RE.finditer(old_text))
        print(f"Matches: {len(matches)}")
        if matches:
            match = matches[0]
            print(f"  Tool: '{match.group(1)}'")
            print(f"  JSON: '{match.group(2)}'")
            print("  ✅ Still works")
        else:
            print("  ❌ Broken")

if __name__ == "__main__":
    test_new_format()