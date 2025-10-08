#!/usr/bin/env python3
"""Monitor tool usage data collection for ML training."""
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.tool_usage_logger import get_log_stats


def main():
    """Display current statistics of tool usage logs."""
    print("=" * 60)
    print("Tool Usage Data Collection Monitor")
    print("=" * 60)
    print()
    
    stats = get_log_stats()
    
    if "error" in stats:
        print(f"❌ Error: {stats['error']}")
        print()
        print("No data collected yet. Data will be collected automatically")
        print("as users interact with the chat endpoint.")
        return
    
    print(f"📊 Total logs: {stats['total_logs']}")
    print(f"✅ Successes: {stats['successes']}")
    print(f"❌ Failures: {stats['failures']}")
    print(f"📈 Success rate: {stats['success_rate']}%")
    print(f"⏱️  Average execution time: {stats['avg_execution_time']}s")
    print(f"💾 Log file size: {stats['file_size_mb']} MB")
    print(f"📁 Log file: {stats['log_file']}")
    print()
    
    tools = stats.get('tools_called_count', {})
    if tools:
        print("🔧 Tools Called (frequency):")
        for tool, count in sorted(tools.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool:30s}: {count:4d} calls")
    else:
        print("🔧 No tools called yet")
    
    print()
    print("=" * 60)
    
    # Training readiness check
    total = stats['total_logs']
    if total == 0:
        print("⏳ Status: Waiting for data collection to begin")
        print("   Start using the chat endpoint to collect training data")
    elif total < 100:
        print(f"⏳ Status: Collecting data ({total}/100 minimum)")
        print("   Need more data for initial training")
    elif total < 500:
        print(f"🟡 Status: Early training possible ({total}/500 recommended)")
        print("   Can start training but more data will improve accuracy")
    elif total < 1000:
        print(f"🟢 Status: Good for training ({total}/1000 optimal)")
        print("   Ready to train with good accuracy expected")
    else:
        print(f"✅ Status: Excellent dataset ({total} logs)")
        print("   Ready for high-quality ML training")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
