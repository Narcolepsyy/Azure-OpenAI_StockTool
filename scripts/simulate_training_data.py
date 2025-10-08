#!/usr/bin/env python3
"""
Simulate realistic user interactions to generate training data for ML tool selection.

This script generates synthetic but realistic queries that mimic actual user behavior,
allowing you to train the ML model without needing a deployed application.
"""
import sys
import random
import time
from pathlib import Path
from typing import List, Tuple, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.tool_usage_logger import log_tool_usage


# Realistic query templates with expected tools
QUERY_TEMPLATES = [
    # Stock price queries (should use get_stock_quote)
    {
        "queries": [
            "What is {ticker}'s stock price?",
            "How much is {ticker} trading at?",
            "Current price of {ticker}",
            "Tell me {ticker}'s stock price",
            "What's the value of {ticker} stock?",
            "{ticker} stock price today",
            "Price for {ticker}",
            "How's {ticker} doing?",
            "What is {ticker} worth?",
            "{ticker} current quote",
        ],
        "tools_available": {"get_stock_quote", "get_company_profile", "perplexity_search"},
        "tools_called": ["get_stock_quote"],
        "success": True,
        "execution_time": (0.4, 0.8),
    },
    
    # Company profile queries (should use get_company_profile)
    {
        "queries": [
            "Tell me about {ticker}",
            "What does {ticker} do?",
            "{ticker} company information",
            "Give me details on {ticker}",
            "Who is the CEO of {ticker}?",
            "{ticker} company profile",
            "What industry is {ticker} in?",
            "Background on {ticker}",
            "Information about {ticker}",
            "{ticker} company overview",
        ],
        "tools_available": {"get_company_profile", "get_stock_quote", "perplexity_search"},
        "tools_called": ["get_company_profile"],
        "success": True,
        "execution_time": (0.5, 1.0),
    },
    
    # Technical analysis queries (should use get_technical_indicators)
    {
        "queries": [
            "{ticker} technical indicators",
            "Show me {ticker}'s RSI and MACD",
            "Technical analysis for {ticker}",
            "{ticker} momentum indicators",
            "Is {ticker} overbought or oversold?",
            "{ticker} moving averages",
            "Technical signals for {ticker}",
            "{ticker} chart analysis",
        ],
        "tools_available": {"get_technical_indicators", "get_stock_quote", "get_historical_prices"},
        "tools_called": ["get_technical_indicators"],
        "success": True,
        "execution_time": (0.8, 1.5),
    },
    
    # Historical data queries (should use get_historical_prices)
    {
        "queries": [
            "{ticker} price history",
            "Show me {ticker}'s historical prices",
            "{ticker} stock performance over time",
            "Past 30 days for {ticker}",
            "{ticker} price chart",
            "Historical data for {ticker}",
            "{ticker} stock history",
        ],
        "tools_available": {"get_historical_prices", "get_stock_quote", "get_technical_indicators"},
        "tools_called": ["get_historical_prices"],
        "success": True,
        "execution_time": (0.7, 1.3),
    },
    
    # News queries (should use perplexity_search)
    {
        "queries": [
            "Latest news about {topic}",
            "What's happening with {topic}?",
            "Recent developments in {topic}",
            "{topic} news",
            "Latest {topic} updates",
            "Tell me about recent {topic} events",
            "What's new with {topic}?",
            "Current {topic} situation",
        ],
        "tools_available": {"perplexity_search", "rag_search"},
        "tools_called": ["perplexity_search"],
        "success": True,
        "execution_time": (5.0, 8.0),
    },
    
    # General knowledge queries (should use perplexity_search or rag_search)
    {
        "queries": [
            "What is {concept}?",
            "Explain {concept}",
            "How does {concept} work?",
            "Tell me about {concept}",
            "Define {concept}",
            "What does {concept} mean?",
        ],
        "tools_available": {"perplexity_search", "rag_search"},
        "tools_called": ["perplexity_search"],
        "success": True,
        "execution_time": (4.0, 7.0),
    },
    
    # Multi-tool queries (should use multiple tools)
    {
        "queries": [
            "Analyze {ticker} stock",
            "Complete analysis of {ticker}",
            "{ticker} stock analysis with indicators",
            "Comprehensive {ticker} report",
            "Full breakdown of {ticker}",
        ],
        "tools_available": {"get_stock_quote", "get_company_profile", "get_technical_indicators"},
        "tools_called": ["get_stock_quote", "get_technical_indicators"],
        "success": True,
        "execution_time": (1.5, 2.5),
    },
    
    # Japanese queries (should use get_stock_quote)
    {
        "queries": [
            "{ticker}の株価を教えて",
            "{ticker}の現在価格は？",
            "{ticker}の株価はいくらですか？",
            "{ticker}の値段を知りたい",
        ],
        "tools_available": {"get_stock_quote", "get_company_profile", "perplexity_search"},
        "tools_called": ["get_stock_quote"],
        "success": True,
        "execution_time": (0.5, 0.9),
    },
]

# Sample tickers for stock queries
TICKERS = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA", "AMD", "NFLX", "DIS"]

# Sample topics for news queries
TOPICS = ["AI", "cryptocurrency", "electric vehicles", "climate change", "tech stocks", 
          "Federal Reserve", "inflation", "robotics", "5G technology", "quantum computing"]

# Sample concepts for knowledge queries
CONCEPTS = ["machine learning", "blockchain", "quantum computing", "neural networks",
            "stock options", "ETFs", "market cap", "P/E ratio", "dividend yield", "beta"]


def generate_query(template: dict) -> Tuple[str, Set[str], List[str], bool, float]:
    """Generate a realistic query from template."""
    query_template = random.choice(template["queries"])
    
    # Fill in placeholders
    if "{ticker}" in query_template:
        query = query_template.format(ticker=random.choice(TICKERS))
    elif "{topic}" in query_template:
        query = query_template.format(topic=random.choice(TOPICS))
    elif "{concept}" in query_template:
        query = query_template.format(concept=random.choice(CONCEPTS))
    else:
        query = query_template
    
    # Get expected behavior
    tools_available = template["tools_available"]
    tools_called = template["tools_called"].copy()  # Copy to avoid mutation
    success = template["success"]
    
    # Random execution time within range
    exec_time = random.uniform(*template["execution_time"])
    
    # 10% chance of failure
    if random.random() < 0.1:
        success = False
        exec_time = min(exec_time, 1.0)  # Failures are faster
    
    return query, tools_available, tools_called, success, exec_time


def simulate_data_collection(num_samples: int = 200, show_progress: bool = True):
    """
    Simulate realistic user interactions to generate training data.
    
    Args:
        num_samples: Number of samples to generate
        show_progress: Whether to show progress
    """
    print(f"🤖 Simulating {num_samples} user interactions...")
    print()
    
    models = ["gpt-4o", "gpt-4o-mini", "gpt-oss-120b"]
    
    for i in range(num_samples):
        # Select random template
        template = random.choice(QUERY_TEMPLATES)
        
        # Generate query and metadata
        query, tools_available, tools_called, success, exec_time = generate_query(template)
        
        # Random model selection
        model = random.choice(models)
        
        # Log the interaction
        log_tool_usage(
            query=query,
            tools_available=tools_available,
            tools_called=tools_called,
            success=success,
            execution_time=exec_time,
            model=model,
            conversation_id=f"sim-{i+1}",
            user_id="simulator",
            error=None if success else "Simulated failure"
        )
        
        # Show progress
        if show_progress and (i + 1) % 20 == 0:
            print(f"  Generated {i+1}/{num_samples} samples...")
    
    print()
    print(f"✅ Successfully generated {num_samples} training samples!")


def main():
    """Main simulation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulate user interactions for ML training")
    parser.add_argument(
        "--samples", "-n",
        type=int,
        default=200,
        help="Number of samples to generate (default: 200)"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode: generate 100 samples"
    )
    parser.add_argument(
        "--large", "-l",
        action="store_true",
        help="Large dataset: generate 500 samples"
    )
    
    args = parser.parse_args()
    
    # Determine number of samples
    if args.quick:
        num_samples = 100
    elif args.large:
        num_samples = 500
    else:
        num_samples = args.samples
    
    print()
    print("=" * 70)
    print("ML Training Data Simulator")
    print("=" * 70)
    print()
    print(f"This will generate {num_samples} realistic user interactions")
    print("for training the ML-based tool selection system.")
    print()
    print("Sample queries will include:")
    print("  • Stock price lookups")
    print("  • Company information requests")
    print("  • Technical analysis queries")
    print("  • News searches")
    print("  • Japanese language queries")
    print("  • Multi-tool requests")
    print()
    
    # Confirm
    response = input(f"Generate {num_samples} samples? [Y/n]: ").strip().lower()
    if response and response not in ['y', 'yes']:
        print("Cancelled.")
        return
    
    print()
    
    # Run simulation
    start_time = time.time()
    simulate_data_collection(num_samples)
    elapsed = time.time() - start_time
    
    print()
    print("=" * 70)
    print("Simulation Complete!")
    print("=" * 70)
    print()
    print(f"⏱️  Time: {elapsed:.2f} seconds")
    print(f"📊 Samples generated: {num_samples}")
    print(f"📁 Saved to: data/tool_usage_logs.jsonl")
    print()
    
    # Show stats
    print("Next steps:")
    print("  1. Check stats: python scripts/monitor_tool_usage.py")
    print("  2. View logs: cat data/tool_usage_logs.jsonl | jq .")
    print("  3. Train model: python scripts/train_tool_classifier.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSimulation cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
