#!/usr/bin/env python3
"""
Prepare training data WITHOUT requiring OpenAI API (for testing).

Uses simulated embeddings based on TF-IDF for offline training.
"""
import sys
import json
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# All possible tools
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
                if entry.get("success", False):
                    logs.append(entry)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed log line: {e}")
                continue
    
    return logs


def create_simulated_embeddings(queries: List[str]) -> np.ndarray:
    """
    Create simulated embeddings using TF-IDF (for offline training).
    
    This allows training without OpenAI API key.
    In production, replace with real embeddings from text-embedding-3-small.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    
    logger.info("Creating simulated embeddings using TF-IDF + SVD...")
    
    # Create TF-IDF features
    vectorizer = TfidfVectorizer(
        max_features=500,
        ngram_range=(1, 2),
        min_df=1
    )
    
    tfidf_matrix = vectorizer.fit_transform(queries)
    
    # Reduce to ~1500 dimensions (similar to text-embedding-3-small)
    n_components = min(300, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1])
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    embeddings = svd.fit_transform(tfidf_matrix)
    
    logger.info(f"Created embeddings with shape {embeddings.shape}")
    logger.info(f"⚠️  NOTE: Using simulated embeddings for testing")
    logger.info(f"⚠️  For production, use real OpenAI embeddings")
    
    return embeddings.astype(np.float32)


def create_training_data(log_file: str = "data/tool_usage_logs.jsonl") -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Convert logs to training data using simulated embeddings."""
    log_path = Path(log_file)
    
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_file}")
    
    logger.info(f"Loading logs from {log_file}...")
    logs = load_logs(log_path)
    
    if not logs:
        raise ValueError("No successful logs found for training")
    
    logger.info(f"Loaded {len(logs)} successful interactions")
    
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
    
    # Generate simulated embeddings
    X = create_simulated_embeddings(queries)
    
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
    
    logger.info(f"\nSaving training data to {output_dir}...")
    
    np.save(output_path / "X_train.npy", X)
    np.save(output_path / "y_train.npy", y)
    
    with open(output_path / "queries.json", "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)
    
    with open(output_path / "tool_names.json", "w", encoding="utf-8") as f:
        json.dump(ALL_TOOLS, f, indent=2)
    
    logger.info("✅ Training data saved successfully!")
    logger.info(f"  X_train.npy: {X.shape}")
    logger.info(f"  y_train.npy: {y.shape}")


def main():
    """Main preparation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare training data (simulated embeddings)")
    parser.add_argument(
        "--input",
        type=str,
        default="data/tool_usage_logs.jsonl",
        help="Input log file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data",
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    try:
        X, y, queries = create_training_data(args.input)
        save_training_data(X, y, queries, args.output)
        
        print()
        print("=" * 70)
        print("Training data preparation complete!")
        print("=" * 70)
        print()
        print("⚠️  NOTE: Using simulated embeddings (TF-IDF + SVD)")
        print("   For production, use real OpenAI embeddings")
        print()
        print("Next step: Train the model")
        print("  python scripts/train_tool_classifier.py")
        print()
        
    except Exception as e:
        logger.error(f"Failed to prepare training data: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
