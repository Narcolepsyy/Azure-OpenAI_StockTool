#!/usr/bin/env python3
"""
Augment existing training data from tool_usage_logs.jsonl

This script:
1. Loads real usage data from JSONL logs
2. Creates variations of successful queries with:
   - Synonym substitutions
   - Rephrasings
   - Different company tickers
   - Multi-language variations
3. Balances the dataset across tools
4. Outputs augmented training data
"""
import sys
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple, Set
from collections import Counter
import re

# Synonym/variation mappings for augmentation
QUERY_VARIATIONS = {
    # Price queries
    r'\b(price|quote|value|cost)\b': ['price', 'quote', 'value', 'cost', 'trading at', 'worth'],
    r'\b(current|today|now|latest)\b': ['current', 'today', 'now', 'latest', 'right now', 'at present'],
    r'\b(stock|share)\b': ['stock', 'share', 'equity'],
    r'\b(show me|get me|tell me|what is|give me)\b': ['show me', 'get me', 'tell me', 'what is', 'what\'s', 'give me', 'fetch'],
    
    # Company profile queries
    r'\b(company information|company profile|details|background|information|info)\b': ['company information', 'company profile', 'details', 'background', 'information', 'info', 'overview', 'about'],
    r'\b(tell me about|give me details on|show me|what is)\b': ['tell me about', 'give me details on', 'show me', 'what is', 'info on', 'background on'],
    
    # Historical queries
    r'\b(history|historical|chart|performance|trend)\b': ['history', 'historical data', 'chart', 'performance', 'trend', 'past prices', 'historical prices'],
    r'\b(over time|over the|for the last|in the past)\b': ['over time', 'over the', 'for the last', 'in the past', 'historically'],
    
    # Technical indicators
    r'\b(technical indicators|technicals|indicators|signals|analysis)\b': ['technical indicators', 'technicals', 'indicators', 'signals', 'technical analysis', 'momentum'],
    r'\b(RSI|MACD|moving average)\b': ['RSI', 'MACD', 'moving average', 'technical signals', 'momentum indicators'],
    
    # Analysis queries
    r'\b(analysis|analyze|comprehensive|full|complete|detailed)\b': ['analysis', 'analyze', 'comprehensive', 'full', 'complete', 'detailed', 'in-depth', 'thorough'],
    r'\b(report|breakdown|overview)\b': ['report', 'breakdown', 'overview', 'summary', 'analysis'],
}

# Companies to substitute for augmentation
COMPANIES = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD", "INTC", "NFLX",
    "DIS", "PYPL", "ADBE", "CRM", "ORCL", "IBM", "CSCO", "V", "MA", "JPM"
]

def load_logs(log_file: str) -> List[Dict]:
    """Load successful tool usage logs."""
    logs = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                # Only use successful queries
                if entry.get("success", False):
                    logs.append(entry)
            except json.JSONDecodeError:
                continue
    return logs


def extract_company_ticker(query: str) -> Set[str]:
    """Extract company tickers from query."""
    tickers = set()
    for company in COMPANIES:
        if re.search(r'\b' + company + r'\b', query, re.IGNORECASE):
            tickers.add(company)
    return tickers


def substitute_company(query: str, old_company: str, new_company: str) -> str:
    """Replace company ticker in query."""
    # Case-insensitive replacement
    pattern = r'\b' + re.escape(old_company) + r'\b'
    return re.sub(pattern, new_company, query, flags=re.IGNORECASE)


def create_variation(query: str) -> str:
    """Create a variation of the query using synonym substitution."""
    # Randomly select 1-2 patterns to vary
    patterns = list(QUERY_VARIATIONS.keys())
    random.shuffle(patterns)
    
    varied_query = query
    variations_made = 0
    
    for pattern in patterns:
        if variations_made >= 2:  # Limit to 2 variations per query
            break
            
        match = re.search(pattern, varied_query, re.IGNORECASE)
        if match:
            options = QUERY_VARIATIONS[pattern]
            original = match.group(0)
            # Don't replace with the same word
            options = [opt for opt in options if opt.lower() != original.lower()]
            if options:
                replacement = random.choice(options)
                varied_query = re.sub(pattern, replacement, varied_query, count=1, flags=re.IGNORECASE)
                variations_made += 1
    
    return varied_query if varied_query != query else query


def augment_entry(entry: Dict, augmentation_factor: int = 3) -> List[Tuple[str, List[str]]]:
    """
    Create augmented versions of a log entry.
    
    Args:
        entry: Original log entry
        augmentation_factor: How many variations to create
        
    Returns:
        List of (query, tools) tuples
    """
    original_query = entry["query"]
    tools = entry["tools_called"]
    
    augmented = [(original_query, tools)]  # Always include original
    
    # Extract company tickers from query
    tickers = extract_company_ticker(original_query)
    
    for i in range(augmentation_factor - 1):
        # Strategy 1: Rephrase using synonyms (50% chance)
        if random.random() < 0.5:
            varied_query = create_variation(original_query)
            if varied_query != original_query:
                augmented.append((varied_query, tools))
        
        # Strategy 2: Substitute company ticker (40% chance, if ticker exists)
        elif tickers and random.random() < 0.4:
            old_ticker = random.choice(list(tickers))
            new_ticker = random.choice([c for c in COMPANIES if c != old_ticker])
            new_query = substitute_company(original_query, old_ticker, new_ticker)
            if new_query != original_query:
                augmented.append((new_query, tools))
        
        # Strategy 3: Combine variation + company substitution (10% chance)
        elif tickers and random.random() < 0.1:
            varied = create_variation(original_query)
            old_ticker = random.choice(list(tickers))
            new_ticker = random.choice([c for c in COMPANIES if c != old_ticker])
            new_query = substitute_company(varied, old_ticker, new_ticker)
            if new_query != original_query:
                augmented.append((new_query, tools))
    
    # Remove exact duplicates
    seen = set()
    unique_augmented = []
    for query, tools in augmented:
        if query.lower() not in seen:
            seen.add(query.lower())
            unique_augmented.append((query, tools))
    
    return unique_augmented


def balance_dataset(samples: List[Tuple[str, List[str]]], target_min: int = 80) -> List[Tuple[str, List[str]]]:
    """
    Balance dataset by ensuring each tool has minimum representation.
    
    Oversamples underrepresented tools by duplicating queries with variations.
    """
    # Count tool usage
    tool_counts = Counter()
    tool_samples = {}  # tool -> list of samples
    
    for query, tools in samples:
        for tool in tools:
            tool_counts[tool] += 1
            if tool not in tool_samples:
                tool_samples[tool] = []
            tool_samples[tool].append((query, tools))
    
    print("\n📊 Original tool distribution:")
    for tool, count in sorted(tool_counts.items(), key=lambda x: x[1]):
        print(f"  {tool:30s}: {count:4d} samples")
    
    # Oversample underrepresented tools
    balanced_samples = list(samples)  # Start with originals
    
    for tool, count in tool_counts.items():
        if count < target_min:
            needed = target_min - count
            print(f"\n🔄 Oversampling {tool}: need {needed} more samples")
            
            # Duplicate and vary samples for this tool
            tool_sample_list = tool_samples[tool]
            for _ in range(needed):
                # Pick random sample with this tool
                query, tools = random.choice(tool_sample_list)
                # Create variation
                varied_query = create_variation(query)
                # Try company substitution if it failed to vary
                if varied_query == query:
                    tickers = extract_company_ticker(query)
                    if tickers:
                        old_ticker = random.choice(list(tickers))
                        new_ticker = random.choice([c for c in COMPANIES if c != old_ticker])
                        varied_query = substitute_company(query, old_ticker, new_ticker)
                
                balanced_samples.append((varied_query, tools))
    
    # Shuffle to mix original and augmented
    random.shuffle(balanced_samples)
    
    return balanced_samples


def print_statistics(samples: List[Tuple[str, List[str]]]):
    """Print dataset statistics."""
    print("\n" + "="*70)
    print("DATASET STATISTICS")
    print("="*70)
    
    print(f"\nTotal samples: {len(samples)}")
    
    # Tool distribution
    all_tools_used = []
    for _, tools in samples:
        all_tools_used.extend(tools)
    
    tool_counts = Counter(all_tools_used)
    
    print(f"\nTool usage distribution:")
    for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(samples)) * 100
        bar = "█" * int(percentage / 2)
        print(f"  {tool:30s}: {count:4d} ({percentage:5.1f}%) {bar}")
    
    # Multi-tool queries
    multi_tool_count = sum(1 for _, tools in samples if len(tools) > 1)
    single_tool_count = len(samples) - multi_tool_count
    
    print(f"\nQuery complexity:")
    print(f"  Single-tool queries: {single_tool_count} ({single_tool_count/len(samples)*100:.1f}%)")
    print(f"  Multi-tool queries:  {multi_tool_count} ({multi_tool_count/len(samples)*100:.1f}%)")
    
    # Average tools per query
    avg_tools = sum(len(tools) for _, tools in samples) / len(samples)
    print(f"  Average tools/query: {avg_tools:.2f}")
    
    print("\n" + "="*70)


def main():
    """Main augmentation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Augment training data from logs")
    parser.add_argument(
        "--log-file",
        type=str,
        default="data/tool_usage_logs.jsonl",
        help="Path to tool usage logs"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="data/augmented_training_samples.json",
        help="Path to save augmented samples"
    )
    parser.add_argument(
        "--augmentation-factor",
        type=int,
        default=3,
        help="How many variations to create per sample"
    )
    parser.add_argument(
        "--balance-min",
        type=int,
        default=80,
        help="Minimum samples per tool after balancing"
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("AUGMENTING TRAINING DATA FROM LOGS")
    print("="*70)
    
    # Load logs
    print(f"\n📂 Loading logs from {args.log_file}...")
    logs = load_logs(args.log_file)
    print(f"✅ Loaded {len(logs)} successful interactions")
    
    # Augment each entry
    print(f"\n🔄 Creating {args.augmentation_factor}x augmentations per sample...")
    all_samples = []
    for entry in logs:
        augmented = augment_entry(entry, args.augmentation_factor)
        all_samples.extend(augmented)
    
    print(f"✅ Generated {len(all_samples)} samples ({len(all_samples) / len(logs):.1f}x original)")
    
    # Balance dataset
    print(f"\n⚖️  Balancing dataset (min {args.balance_min} samples per tool)...")
    balanced_samples = balance_dataset(all_samples, target_min=args.balance_min)
    print(f"✅ Balanced to {len(balanced_samples)} samples")
    
    # Show statistics
    print_statistics(balanced_samples)
    
    # Save to file
    print(f"\n💾 Saving to {args.output_file}...")
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to structured format
    structured_data = [
        {
            "query": query,
            "tools": tools,
            "success": True
        }
        for query, tools in balanced_samples
    ]
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(structured_data)} augmented samples")
    
    print("\n" + "="*70)
    print("✅ AUGMENTATION COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print(f"  1. Review samples in {args.output_file}")
    print("  2. Run: python scripts/prepare_training_data_from_samples.py --samples-file", args.output_file)
    print("  3. Run: python scripts/train_tool_classifier.py")
    print("="*70)


if __name__ == "__main__":
    main()
