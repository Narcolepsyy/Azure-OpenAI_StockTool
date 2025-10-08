#!/usr/bin/env python3
"""
View ML tool selection statistics and recent activity.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ.setdefault("ML_TOOL_SELECTION_ENABLED", "true")

from app.services.ml.tool_selector import get_ml_stats


def main():
    """Display ML tool selection statistics."""
    print("\n" + "="*70)
    print("ML TOOL SELECTION - LIVE STATISTICS")
    print("="*70)
    
    try:
        stats = get_ml_stats()
        
        print(f"\n📊 Overall Statistics:")
        print(f"   ML Enabled:        {stats.get('ml_enabled')}")
        print(f"   Model Loaded:      {stats.get('model_loaded')}")
        print(f"   Total Predictions: {stats.get('total_predictions')}")
        print(f"   Fallback Count:    {stats.get('fallback_count')}")
        print(f"   Fallback Rate:     {stats.get('fallback_rate'):.1%}")
        
        print(f"\n⚡ Performance:")
        print(f"   Avg Confidence:    {stats.get('avg_confidence'):.3f}")
        print(f"   Avg Pred Time:     {stats.get('avg_prediction_time_ms'):.2f}ms")
        
        print(f"\n🔧 Tools Predicted:")
        tools_predicted = stats.get('tools_predicted', {})
        if tools_predicted:
            for tool, count in sorted(tools_predicted.items(), key=lambda x: x[1], reverse=True):
                print(f"   {tool:30s} {count:3d} times")
        else:
            print("   No predictions yet")
        
        print(f"\n📈 Confidence Distribution:")
        conf_dist = stats.get('confidence_distribution', {})
        if conf_dist:
            for bin_range, count in sorted(conf_dist.items()):
                print(f"   {bin_range:10s} {count:3d} predictions")
        else:
            print("   No data yet")
        
        print("\n" + "="*70)
        
        if stats.get('total_predictions', 0) > 0:
            print("✅ ML tool selection is active and working!")
        else:
            print("⚠️  No predictions yet. Make some API requests to see ML in action.")
        
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error retrieving statistics: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
