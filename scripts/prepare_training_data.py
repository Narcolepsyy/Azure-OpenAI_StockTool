#!/usr/bin/env python3
"""
Prepare training data from tool usage logs.

Converts JSONL logs to embeddings + labels for ML training.
"""
import sys
import json
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict, Set
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ml.embedder import QueryEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# All possible tools (must match TOOL_REGISTRY in app/utils/tools.py)
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
    "get_augmented_news",
]

# Create tool index mapping
TOOL_INDEX = {tool: idx for idx, tool in enumerate(ALL_TOOLS)}


def load_logs(log_file: Path) -> List[Dict]:
    """Load tool usage logs from JSONL file."""
    logs = []
    
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                entry = json.loads(line)
                # Only use successful queries for training
                if entry.get("success", False):
                    logs.append(entry)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed log line: {e}")
                continue
    
    return logs


def create_training_data(log_file: str = "data/tool_usage_logs.jsonl") -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Convert logs to training data (embeddings + labels).
    
    Returns:
        X: Query embeddings (n_samples, embedding_dim)
        y: Tool labels (n_samples, n_tools) - binary matrix
        queries: Original queries for reference
    """
    log_path = Path(log_file)
    
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_file}")
    
    logger.info(f"Loading logs from {log_file}...")
    logs = load_logs(log_path)
    
    if not logs:
        raise ValueError("No successful logs found for training")
    
    logger.info(f"Loaded {len(logs)} successful interactions")
    
    # Initialize embedder
    logger.info("Initializing query embedder...")
    embedder = QueryEmbedder()
    
    # Extract queries and tools
    queries = []
    tools_called_list = []
    
    for entry in logs:
        query = entry.get("query", "")
        tools_called = entry.get("tools_called", [])
        
        if not query or not tools_called:
            continue
        
        queries.append(query)
        tools_called_list.append(tools_called)
    
    logger.info(f"Processing {len(queries)} queries...")
    
    # Generate embeddings (batch for efficiency)
    logger.info("Generating embeddings...")
    X = embedder.embed_batch(queries)
    
    logger.info(f"Generated embeddings with shape {X.shape}")
    
    # Create multi-hot encoded labels
    logger.info("Creating label matrix...")
    y = np.zeros((len(queries), len(ALL_TOOLS)), dtype=np.int32)
    
    for i, tools_called in enumerate(tools_called_list):
        for tool in tools_called:
            if tool in TOOL_INDEX:
                y[i, TOOL_INDEX[tool]] = 1
            else:
                logger.warning(f"Unknown tool '{tool}' in logs (skipping)")
    
    logger.info(f"Created label matrix with shape {y.shape}")
    
    # Statistics
    tools_per_query = y.sum(axis=1)
    logger.info(f"Average tools per query: {tools_per_query.mean():.2f}")
    logger.info(f"Max tools per query: {tools_per_query.max()}")
    logger.info(f"Min tools per query: {tools_per_query.min()}")
    
    tool_frequencies = y.sum(axis=0)
    logger.info("\nTool frequencies:")
    for tool, freq in zip(ALL_TOOLS, tool_frequencies):
        if freq > 0:
            logger.info(f"  {tool:30s}: {int(freq):4d} samples")
    
    return X, y, queries


def save_training_data(X: np.ndarray, y: np.ndarray, queries: List[str], output_dir: str = "data"):
    """Save prepared training data."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    logger.info(f"Saving training data to {output_dir}...")
    
    np.save(output_path / "X_train.npy", X)
    np.save(output_path / "y_train.npy", y)
    
    # Save queries for reference
    with open(output_path / "queries.json", "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)
    
    # Save tool names
    with open(output_path / "tool_names.json", "w", encoding="utf-8") as f:
        json.dump(ALL_TOOLS, f, indent=2)
    
    logger.info("✅ Training data saved successfully!")
    logger.info(f"  X_train.npy: {X.shape}")
    logger.info(f"  y_train.npy: {y.shape}")
    logger.info(f"  queries.json: {len(queries)} queries")
    logger.info(f"  tool_names.json: {len(ALL_TOOLS)} tools")


def main():
    """Main preparation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare training data from tool usage logs")
    parser.add_argument(
        "--input",
        type=str,
        default="data/tool_usage_logs.jsonl",
        help="Input log file (JSONL format)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data",
        help="Output directory for training data"
    )
    
    args = parser.parse_args()
    
    try:
        # Load and convert logs
        X, y, queries = create_training_data(args.input)
        
        # Save prepared data
        save_training_data(X, y, queries, args.output)
        
        print()
        print("=" * 70)
        print("Training data preparation complete!")
        print("=" * 70)
        print()
        print("Next step: Train the model")
        print("  python scripts/train_tool_classifier.py")
        print()
        
    except Exception as e:
        logger.error(f"Failed to prepare training data: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
