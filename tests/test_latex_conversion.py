#!/usr/bin/env python3
"""Test script to verify LaTeX format conversion."""

import re


def _convert_latex_format(text: str) -> str:
    """Normalize LaTeX math delimiters to `\(`, `\)`, `\[`, and `\]`."""
    if not text:
        return text
    try:
        def _replace_block(match: re.Match[str]) -> str:
            inner = match.group(1).strip()
            return f'\\[{inner}\\]'

        converted = re.sub(r'\$\$(.+?)\$\$', _replace_block, text, flags=re.DOTALL)

        def _replace_inline(match: re.Match[str]) -> str:
            inner = match.group(1).strip()
            return f'\\({inner}\\)'

        converted = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', _replace_inline, converted, flags=re.DOTALL)

        def _replace_bracket(match: re.Match[str]) -> str:
            content = match.group(0)
            inner = content[1:-1].strip()
            return f'\\({inner}\\)'

        converted = re.sub(r'\[\s*\\[a-zA-Z]+.*?\]', _replace_bracket, converted, flags=re.DOTALL)

        return converted
    except Exception as e:
        print(f"Failed to convert LaTeX format: {e}")
        return text

def test_latex_conversion():
    """Test LaTeX format conversion."""
    
    test_cases = [
        "日本の銀行セクターは過去1日間で [ \\frac{1,498.0 - 1,484.5}{1,484.5} \\times 100 \\approx 0.91% ] 上昇しました。",
        "The calculation is [ \\frac{a + b}{c} ] where a=1, b=2, c=3.",
        "No math here, just regular text.",
        "Multiple math: [ \\sin(x) ] and [ \\cos(y) ] are trigonometric functions.",
        "Complex math: [ \\frac{\\partial f}{\\partial x} = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h} ]"
    ]
    
    print("Testing LaTeX format conversion:")
    print("=" * 60)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Input:  {test_text}")
        converted = _convert_latex_format(test_text)
        print(f"Output: {converted}")
        
        # Check if conversion happened
        if test_text != converted:
            print("✅ Conversion applied")
        else:
            print("ℹ️  No conversion needed")

if __name__ == "__main__":
    test_latex_conversion()