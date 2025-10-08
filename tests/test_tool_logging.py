#!/usr/bin/env python3
"""Test tool usage logging functionality."""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.tool_usage_logger import log_tool_usage, get_log_stats


def test_logging():
    """Test the logging functionality."""
    print("Testing tool usage logging...")
    print()
    
    # Test case 1: Stock quote query
    print("1. Testing stock quote query...")
    log_tool_usage(
        query="What is Apple's stock price?",
        tools_available={"get_stock_quote", "get_company_profile", "perplexity_search"},
        tools_called=["get_stock_quote"],
        success=True,
        execution_time=0.5,
        model="gpt-4o",
        conversation_id="test-conv-1",
        user_id="test-user",
        tool_results=[
            {"name": "get_stock_quote", "result": {"symbol": "AAPL", "price": 175.50}}
        ]
    )
    print("✅ Logged stock quote query")
    
    # Test case 2: News search query
    print("2. Testing news search query...")
    log_tool_usage(
        query="Latest AI news",
        tools_available={"perplexity_search", "rag_search"},
        tools_called=["perplexity_search"],
        success=True,
        execution_time=6.5,
        model="gpt-4o",
        conversation_id="test-conv-2",
        user_id="test-user",
        tool_results=[
            {"name": "perplexity_search", "result": {"answer": "AI news..."}}
        ]
    )
    print("✅ Logged news search query")
    
    # Test case 3: Failed query
    print("3. Testing failed query...")
    log_tool_usage(
        query="Invalid ticker XYZ123",
        tools_available={"get_stock_quote"},
        tools_called=["get_stock_quote"],
        success=False,
        execution_time=0.3,
        model="gpt-4o",
        conversation_id="test-conv-3",
        user_id="test-user",
        error="Ticker not found",
        tool_results=[
            {"name": "get_stock_quote", "error": "Ticker not found"}
        ]
    )
    print("✅ Logged failed query")
    
    # Test case 4: Japanese query
    print("4. Testing Japanese query...")
    log_tool_usage(
        query="トヨタの株価を教えて",
        tools_available={"get_stock_quote", "perplexity_search"},
        tools_called=["get_stock_quote"],
        success=True,
        execution_time=0.6,
        model="gpt-4o",
        conversation_id="test-conv-4",
        user_id="test-user",
        tool_results=[
            {"name": "get_stock_quote", "result": {"symbol": "TM", "price": 180.25}}
        ]
    )
    print("✅ Logged Japanese query")
    
    # Test case 5: Multiple tools
    print("5. Testing multiple tool calls...")
    log_tool_usage(
        query="Analyze Tesla stock",
        tools_available={"get_stock_quote", "get_company_profile", "get_technical_indicators"},
        tools_called=["get_stock_quote", "get_technical_indicators"],
        success=True,
        execution_time=1.8,
        model="gpt-4o",
        conversation_id="test-conv-5",
        user_id="test-user",
        tool_results=[
            {"name": "get_stock_quote", "result": {"symbol": "TSLA", "price": 250.00}},
            {"name": "get_technical_indicators", "result": {"rsi": 65, "macd": 1.5}}
        ]
    )
    print("✅ Logged multiple tool query")
    
    print()
    print("=" * 60)
    print("All test logs written successfully!")
    print("=" * 60)
    print()
    
    # Show stats
    print("Current statistics:")
    print()
    stats = get_log_stats()
    
    print(f"📊 Total logs: {stats['total_logs']}")
    print(f"✅ Successes: {stats['successes']}")
    print(f"❌ Failures: {stats['failures']}")
    print(f"📈 Success rate: {stats['success_rate']}%")
    print(f"⏱️  Average execution time: {stats['avg_execution_time']}s")
    print()
    
    tools = stats.get('tools_called_count', {})
    if tools:
        print("🔧 Tools Called:")
        for tool, count in sorted(tools.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool:30s}: {count} calls")
    
    print()
    print("✅ Test complete! Check data/tool_usage_logs.jsonl for logged data")


def view_logs():
    """View the actual log file."""
    log_file = Path("data/tool_usage_logs.jsonl")
    
    if not log_file.exists():
        print("No log file found yet.")
        return
    
    print()
    print("=" * 60)
    print("Recent log entries:")
    print("=" * 60)
    print()
    
    with open(log_file, "r") as f:
        lines = f.readlines()
        
    # Show last 5 entries
    for line in lines[-5:]:
        try:
            entry = json.loads(line)
            print(f"Query: {entry['query'][:60]}...")
            print(f"  Tools available: {entry['tools_available']}")
            print(f"  Tools called: {entry['tools_called']}")
            print(f"  Success: {entry['success']}")
            print(f"  Time: {entry['execution_time']}s")
            print()
        except:
            pass


if __name__ == "__main__":
    try:
        test_logging()
        view_logs()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
