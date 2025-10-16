#!/usr/bin/env python3
"""
Generate expanded training data for tool classifier with higher quality and diversity.

This script creates a comprehensive training dataset with:
- More diverse query patterns
- Multiple phrasings for each intent
- Real-world query variations
- Edge cases and ambiguous queries
- Japanese queries for i18n support
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# All available tools
ALL_TOOLS = [
    "get_stock_quote",
    "get_company_profile",
    "get_historical_prices",
    "get_technical_indicators",
    "get_risk_assessment",
    "perplexity_search",
    "web_search",
    "rag_search",
    "search_knowledge_base",
    "calculate_correlation",
]


def generate_training_samples() -> List[Tuple[str, List[str]]]:
    """
    Generate comprehensive training samples.
    Returns list of (query, tools) tuples.
    """
    samples = []
    
    # Companies to use for variations
    companies = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "NFLX", "DIS", "ORCL", "IBM", "CSCO", "CRM", "ADBE", "PYPL", "V", "MA", "JPM"]
    
    # === GET_STOCK_QUOTE queries (high confidence needed) ===
    stock_quote_patterns = [
        "What is {}'s current stock price?",
        "Show me {} stock price",
        "Current price for {}",
        "How much is {} stock?",
        "Get {} price",
        "{} current quote",
        "Price of {} stock",
        "What's {} trading at?",
        "Tell me {}'s share price",
        "Current value of {} stock",
        "Show me the price of {}",
        "Latest {} quote",
        "{} stock price now",
        "{} price today",
        "{} current stock value",
        "What's {} stock at?",
        "{} share price",
        "How much for {} stock?",
        "{} quote",
        "Get me {} price",
    ]
    
    # Generate for multiple companies
    for pattern in stock_quote_patterns:
        for company in companies[:15]:  # Use 15 companies
            samples.append((pattern.format(company), ["get_stock_quote"]))
    
    # Add Japanese variations
    samples.extend([
        ("トヨタの株価を教えてください", ["get_stock_quote"]),
        ("ソニーの株価は？", ["get_stock_quote"]),
        ("任天堂の現在の株価", ["get_stock_quote"]),
        ("日経平均の値段", ["get_stock_quote"]),
        ("トヨタの株価", ["get_stock_quote"]),
        ("ホンダの株の値段", ["get_stock_quote"]),
    ])
    
    # === GET_COMPANY_PROFILE queries ===
    company_profile_queries = [
        ("Tell me about Apple as a company", ["get_company_profile"]),
        ("Get Microsoft's company profile", ["get_company_profile"]),
        ("What does Tesla do?", ["get_company_profile"]),
        ("Google company information", ["get_company_profile"]),
        ("NVIDIA company overview", ["get_company_profile"]),
        ("Amazon business description", ["get_company_profile"]),
        ("META company details", ["get_company_profile"]),
        ("What industry is TSLA in?", ["get_company_profile"]),
        ("Apple's business model", ["get_company_profile"]),
        ("Microsoft company fundamentals", ["get_company_profile"]),
        ("Tell me about AAPL's business", ["get_company_profile"]),
        ("What is the market cap of Apple?", ["get_company_profile"]),
        ("Netflix company info", ["get_company_profile"]),
        ("Who is the CEO of Tesla?", ["get_company_profile"]),
        ("AMD company description", ["get_company_profile"]),
        # Japanese
        ("トヨタの会社概要", ["get_company_profile"]),
        ("ソニーの事業内容", ["get_company_profile"]),
    ]
    samples.extend(company_profile_queries)
    
    # === GET_HISTORICAL_PRICES queries ===
    historical_queries = [
        ("Show me Apple's price history", ["get_historical_prices"]),
        ("TSLA historical data", ["get_historical_prices"]),
        ("Microsoft stock chart", ["get_historical_prices"]),
        ("Google price over the last year", ["get_historical_prices"]),
        ("NVIDIA historical prices", ["get_historical_prices"]),
        ("Amazon's stock performance last 6 months", ["get_historical_prices"]),
        ("META price chart", ["get_historical_prices"]),
        ("Tesla's price trend", ["get_historical_prices"]),
        ("Show me AAPL's historical data", ["get_historical_prices"]),
        ("MSFT price history for 2024", ["get_historical_prices"]),
        ("Netflix stock performance", ["get_historical_prices"]),
        ("AMD price chart last month", ["get_historical_prices"]),
        ("Historical data for GOOGL", ["get_historical_prices"]),
        ("Show Facebook's stock history", ["get_historical_prices"]),
        ("INTC historical prices", ["get_historical_prices"]),
        # Japanese
        ("トヨタの株価推移", ["get_historical_prices"]),
        ("ソニーの過去の株価", ["get_historical_prices"]),
    ]
    samples.extend(historical_queries)
    
    # === GET_TECHNICAL_INDICATORS queries ===
    technical_queries = [
        ("Show me AAPL's RSI", ["get_technical_indicators"]),
        ("Tesla MACD indicator", ["get_technical_indicators"]),
        ("Microsoft's moving averages", ["get_technical_indicators"]),
        ("Get technical indicators for GOOGL", ["get_technical_indicators"]),
        ("NVIDIA RSI and MACD", ["get_technical_indicators"]),
        ("Amazon technical analysis", ["get_technical_indicators"]),
        ("Show me META's RSI", ["get_technical_indicators"]),
        ("TSLA technical indicators", ["get_technical_indicators"]),
        ("Apple's moving average crossover", ["get_technical_indicators"]),
        ("Microsoft RSI value", ["get_technical_indicators"]),
        ("Calculate MACD for AAPL", ["get_technical_indicators"]),
        ("Netflix technical signals", ["get_technical_indicators"]),
        ("AMD momentum indicators", ["get_technical_indicators"]),
        ("Show technical analysis for FB", ["get_technical_indicators"]),
        ("INTC RSI indicator", ["get_technical_indicators"]),
        # Japanese
        ("トヨタのRSI指標", ["get_technical_indicators"]),
        ("ソニーのテクニカル分析", ["get_technical_indicators"]),
    ]
    samples.extend(technical_queries)
    
    # === GET_RISK_ASSESSMENT queries ===
    risk_queries = [
        ("How risky is Apple stock?", ["get_risk_assessment"]),
        ("Tesla risk assessment", ["get_risk_assessment"]),
        ("Microsoft stock volatility", ["get_risk_assessment"]),
        ("Is Google stock risky?", ["get_risk_assessment"]),
        ("NVIDIA risk analysis", ["get_risk_assessment"]),
        ("Amazon investment risk", ["get_risk_assessment"]),
        ("META risk profile", ["get_risk_assessment"]),
        ("How volatile is TSLA?", ["get_risk_assessment"]),
        ("Apple's beta coefficient", ["get_risk_assessment"]),
        ("Risk level of Microsoft stock", ["get_risk_assessment"]),
        ("AAPL volatility analysis", ["get_risk_assessment"]),
        ("Is Netflix a risky investment?", ["get_risk_assessment"]),
        ("AMD risk metrics", ["get_risk_assessment"]),
        ("Facebook stock risk", ["get_risk_assessment"]),
        ("INTC investment risk", ["get_risk_assessment"]),
    ]
    samples.extend(risk_queries)
    
    # === PERPLEXITY_SEARCH queries (news and current events) ===
    perplexity_queries = [
        ("What's the latest news about Apple?", ["perplexity_search"]),
        ("Tesla recent news", ["perplexity_search"]),
        ("Microsoft earnings announcement", ["perplexity_search"]),
        ("Google AI developments", ["perplexity_search"]),
        ("NVIDIA chip shortage", ["perplexity_search"]),
        ("Amazon stock split news", ["perplexity_search"]),
        ("META layoffs", ["perplexity_search"]),
        ("Latest Tesla news", ["perplexity_search"]),
        ("Apple iPhone sales", ["perplexity_search"]),
        ("Microsoft Azure growth", ["perplexity_search"]),
        ("What happened to AAPL stock today?", ["perplexity_search"]),
        ("Why is Tesla stock down?", ["perplexity_search"]),
        ("Netflix subscriber numbers", ["perplexity_search"]),
        ("AMD new products", ["perplexity_search"]),
        ("Facebook metaverse news", ["perplexity_search"]),
        ("Intel manufacturing expansion", ["perplexity_search"]),
        ("Stock market news today", ["perplexity_search"]),
        ("Tech sector news", ["perplexity_search"]),
        ("What's happening with AI stocks?", ["perplexity_search"]),
        ("Semiconductor industry news", ["perplexity_search"]),
        # Japanese
        ("日経平均の最新ニュース", ["perplexity_search"]),
        ("トヨタの最近のニュース", ["perplexity_search"]),
        ("ソニーの決算発表", ["perplexity_search"]),
    ]
    samples.extend(perplexity_queries)
    
    # === WEB_SEARCH queries (general info) ===
    web_search_queries = [
        ("Tell me about the stock market", ["web_search"]),
        ("What is a good P/E ratio?", ["web_search"]),
        ("How to invest in stocks?", ["web_search"]),
        ("What is dividend yield?", ["web_search"]),
        ("Explain market capitalization", ["web_search"]),
        ("What is a bear market?", ["web_search"]),
        ("How to read stock charts?", ["web_search"]),
        ("What is technical analysis?", ["web_search"]),
        ("Fundamental analysis explained", ["web_search"]),
        ("What is day trading?", ["web_search"]),
    ]
    samples.extend(web_search_queries)
    
    # === RAG_SEARCH queries (knowledge base) ===
    rag_queries = [
        ("What tools are available?", ["search_knowledge_base"]),
        ("How do I use this system?", ["search_knowledge_base"]),
        ("What is quantum computing?", ["search_knowledge_base"]),
        ("Explain blockchain technology", ["search_knowledge_base"]),
        ("What is machine learning?", ["search_knowledge_base"]),
        ("Define artificial intelligence", ["search_knowledge_base"]),
        ("What is a neural network?", ["search_knowledge_base"]),
        ("How does the stock market work?", ["search_knowledge_base"]),
        ("What are derivatives?", ["search_knowledge_base"]),
        ("Explain options trading", ["search_knowledge_base"]),
    ]
    samples.extend(rag_queries)
    
    # === CALCULATE_CORRELATION queries ===
    correlation_queries = [
        ("Calculate correlation between AAPL and MSFT", ["calculate_correlation"]),
        ("How correlated are Tesla and Ford?", ["calculate_correlation"]),
        ("Compare GOOGL and META correlation", ["calculate_correlation"]),
        ("Correlation between NVDA and AMD", ["calculate_correlation"]),
        ("Are Apple and Microsoft correlated?", ["calculate_correlation"]),
        ("Tesla and Amazon correlation", ["calculate_correlation"]),
        ("Compare price movements of AAPL and GOOGL", ["calculate_correlation"]),
        ("How similar are MSFT and AMZN trends?", ["calculate_correlation"]),
        ("Correlation analysis for NFLX and DIS", ["calculate_correlation"]),
        ("Compare stock correlation INTC and AMD", ["calculate_correlation"]),
    ]
    samples.extend(correlation_queries)
    
    # === MULTI-TOOL queries (combinations) ===
    multi_tool_queries = [
        ("Analyze Apple stock", ["get_stock_quote", "get_company_profile", "get_technical_indicators"]),
        ("Give me a complete analysis of TSLA", ["get_stock_quote", "get_company_profile", "get_risk_assessment"]),
        ("Microsoft stock report", ["get_stock_quote", "get_company_profile", "get_historical_prices"]),
        ("Detailed Google analysis", ["get_stock_quote", "get_company_profile", "get_technical_indicators"]),
        ("Full Tesla overview", ["get_company_profile", "get_historical_prices", "get_technical_indicators"]),
        ("Analyze NVIDIA with news", ["get_stock_quote", "perplexity_search"]),
        ("Apple stock with recent news", ["get_stock_quote", "perplexity_search"]),
        ("Microsoft fundamentals and technicals", ["get_company_profile", "get_technical_indicators"]),
        ("Tesla price and risk", ["get_stock_quote", "get_risk_assessment"]),
        ("Google stock with history", ["get_stock_quote", "get_historical_prices"]),
        ("AAPL comprehensive report", ["get_stock_quote", "get_company_profile", "get_historical_prices", "get_technical_indicators"]),
        ("Analyze AMZN business and performance", ["get_company_profile", "perplexity_search"]),
        ("MSFT technicals and news", ["get_technical_indicators", "perplexity_search"]),
        ("Tesla stock analysis and latest developments", ["get_stock_quote", "get_technical_indicators", "perplexity_search"]),
        ("Apple investment analysis", ["get_stock_quote", "get_risk_assessment", "get_company_profile"]),
        # Japanese multi-tool
        ("トヨタの詳細な分析", ["get_stock_quote", "get_company_profile", "get_technical_indicators"]),
        ("ソニーの株価と最新ニュース", ["get_stock_quote", "perplexity_search"]),
    ]
    samples.extend(multi_tool_queries)
    
    # === EDGE CASES and VARIATIONS ===
    edge_cases = [
        # Ambiguous queries that need search
        ("Tell me about investing", ["web_search"]),
        ("What should I invest in?", ["perplexity_search"]),
        ("Market trends", ["perplexity_search"]),
        ("Best tech stocks", ["perplexity_search"]),
        ("Investment advice", ["web_search"]),
        
        # Very specific technical queries
        ("AAPL 50-day moving average", ["get_technical_indicators"]),
        ("Tesla beta coefficient", ["get_risk_assessment"]),
        ("Microsoft P/E ratio", ["get_company_profile"]),
        
        # Casual/conversational queries
        ("How's Apple doing?", ["get_stock_quote", "perplexity_search"]),
        ("What's up with Tesla?", ["get_stock_quote", "perplexity_search"]),
        ("Is Microsoft stock good?", ["get_stock_quote", "get_risk_assessment"]),
        ("Should I buy Google?", ["get_stock_quote", "get_risk_assessment"]),
        
        # Price-focused queries
        ("AAPL price", ["get_stock_quote"]),
        ("Tesla stock value", ["get_stock_quote"]),
        ("MSFT quote", ["get_stock_quote"]),
        ("GOOGL current", ["get_stock_quote"]),
        
        # News-focused queries
        ("Apple news", ["perplexity_search"]),
        ("Tesla updates", ["perplexity_search"]),
        ("Microsoft announcements", ["perplexity_search"]),
        ("Google developments", ["perplexity_search"]),
    ]
    samples.extend(edge_cases)
    
    return samples


def save_training_samples(samples: List[Tuple[str, List[str]]], output_file: str = "data/expanded_training_samples.json"):
    """Save generated samples to JSON file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to structured format
    structured_data = [
        {
            "query": query,
            "tools": tools,
            "success": True
        }
        for query, tools in samples
    ]
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(structured_data)} training samples to {output_file}")


def print_statistics(samples: List[Tuple[str, List[str]]]):
    """Print dataset statistics."""
    from collections import Counter
    
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
    """Generate and save expanded training data."""
    print("="*70)
    print("GENERATING EXPANDED TRAINING DATA")
    print("="*70)
    
    # Generate samples
    print("\n📝 Generating training samples...")
    samples = generate_training_samples()
    
    # Print statistics
    print_statistics(samples)
    
    # Save to file
    print("\n💾 Saving samples...")
    save_training_samples(samples)
    
    print("\n" + "="*70)
    print("✅ GENERATION COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Review the generated samples in data/expanded_training_samples.json")
    print("  2. Run: python scripts/prepare_training_data_from_samples.py")
    print("  3. Run: python scripts/train_tool_classifier.py")
    print("="*70)


if __name__ == "__main__":
    main()
