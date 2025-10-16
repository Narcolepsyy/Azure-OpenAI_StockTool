#!/usr/bin/env python3
"""
Prepare training data from generated samples JSON file.

This script converts the generated training samples to embeddings and labels.
"""
import sys
import json
import numpy as np
from pathlib import Path
from typing import Tuple, List
import logging
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ml.embedder import QueryEmbedder

logging.basicConfig(level=logging.INFO, format='%(message)s')
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
    "calculate_correlation",
]

# Create tool index mapping
TOOL_INDEX = {tool: idx for idx, tool in enumerate(ALL_TOOLS)}


def load_samples(samples_file: str) -> List[dict]:
    """Load training samples from JSON file."""
    with open(samples_file, "r", encoding="utf-8") as f:
        samples = json.load(f)
    return samples


def prepare_training_data(
    samples: List[dict],
    output_dir: str = "data"
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Convert samples to training data (embeddings + labels).
    
    Args:
        samples: List of dicts with 'query' and 'tools' keys
        output_dir: Directory to save prepared data
        
    Returns:
        X: Query embeddings (n_samples, embedding_dim)
        y: Tool labels (n_samples, n_tools) - binary matrix
        queries: Original queries for reference
    """
    logger.info(f"Processing {len(samples)} samples...")
    
    # Initialize embedder
    logger.info("Initializing query embedder...")
    embedder = QueryEmbedder()
    
    # Extract queries and tools
    queries = []
    tools_per_query = []
    
    for sample in samples:
        query = sample.get("query", "")
        tools = sample.get("tools", [])
        
        if not query or not tools:
            continue
        
        queries.append(query)
        tools_per_query.append(tools)
    
    logger.info(f"Valid samples: {len(queries)}")
    
    # Batch embed all queries
    logger.info("Generating embeddings (this may take a while)...")
    embeddings = embedder.embed_batch(queries)
    X = np.array(embeddings)
    
    logger.info(f"Embeddings shape: {X.shape}")
    
    # Create label matrix
    logger.info("Creating label matrix...")
    n_samples = len(queries)
    n_tools = len(ALL_TOOLS)
    y = np.zeros((n_samples, n_tools), dtype=np.int32)
    
    for i, tools in enumerate(tools_per_query):
        for tool in tools:
            if tool in TOOL_INDEX:
                j = TOOL_INDEX[tool]
                y[i, j] = 1
            else:
                logger.warning(f"Unknown tool '{tool}' in query: {queries[i][:50]}...")
    
    logger.info(f"Label matrix shape: {y.shape}")
    
    # Save to disk
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\nSaving to {output_dir}/...")
    
    np.save(output_path / "X_train.npy", X)
    logger.info(f"  ✅ X_train.npy ({X.shape})")
    
    np.save(output_path / "y_train.npy", y)
    logger.info(f"  ✅ y_train.npy ({y.shape})")
    
    with open(output_path / "queries.json", "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)
    logger.info(f"  ✅ queries.json ({len(queries)} queries)")
    
    with open(output_path / "tool_names.json", "w", encoding="utf-8") as f:
        json.dump(ALL_TOOLS, f, indent=2)
    logger.info(f"  ✅ tool_names.json ({len(ALL_TOOLS)} tools)")
    
    # Print label distribution
    logger.info("\nLabel distribution:")
    for tool_idx, tool_name in enumerate(ALL_TOOLS):
        count = y[:, tool_idx].sum()
        percentage = (count / n_samples) * 100
        logger.info(f"  {tool_name:30s}: {count:4d} samples ({percentage:5.1f}%)")
    
    # Print multi-label statistics
    labels_per_sample = y.sum(axis=1)
    logger.info(f"\nLabels per sample:")
    logger.info(f"  Min:  {labels_per_sample.min()}")
    logger.info(f"  Max:  {labels_per_sample.max()}")
    logger.info(f"  Mean: {labels_per_sample.mean():.2f}")
    logger.info(f"  Median: {np.median(labels_per_sample):.0f}")
    
    return X, y, queries


def main():
    """Main preparation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare training data from samples")
    parser.add_argument(
        "--samples-file",
        type=str,
        default="data/expanded_training_samples.json",
        help="Path to samples JSON file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Directory to save prepared data"
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("="*70)
        logger.info("PREPARING TRAINING DATA FROM SAMPLES")
        logger.info("="*70)
        
        # Load samples
        logger.info(f"\nLoading samples from {args.samples_file}...")
        samples = load_samples(args.samples_file)
        logger.info(f"✅ Loaded {len(samples)} samples")
        
        # Prepare training data
        X, y, queries = prepare_training_data(samples, args.output_dir)
        
        logger.info("\n" + "="*70)
        logger.info("✅ PREPARATION COMPLETE!")
        logger.info("="*70)
        logger.info(f"\nTraining data ready in {args.output_dir}/")
        logger.info(f"  - X_train.npy: {X.shape}")
        logger.info(f"  - y_train.npy: {y.shape}")
        logger.info(f"  - queries.json: {len(queries)} queries")
        logger.info(f"  - tool_names.json: {len(ALL_TOOLS)} tools")
        
        logger.info("\nNext step:")
        logger.info("  python scripts/train_tool_classifier.py")
        logger.info("="*70)
        
    except FileNotFoundError as e:
        logger.error(f"\n❌ Error: {e}")
        logger.error("\nPlease run first:")
        logger.error("  python scripts/generate_expanded_training_data.py")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Preparation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
