#!/usr/bin/env python3
"""
Train and evaluate ML tool classifier.

This script:
1. Loads prepared training data
2. Splits into train/test sets
3. Trains the classifier
4. Evaluates performance
5. Saves the trained model
6. Provides deployment recommendations
"""
import sys
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ml.classifier import ToolClassifier

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_training_data(data_dir: str = "data") -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
    """Load prepared training data."""
    data_path = Path(data_dir)
    
    logger.info("Loading training data...")
    
    X = np.load(data_path / "X_train.npy")
    y = np.load(data_path / "y_train.npy")
    
    with open(data_path / "queries.json", "r") as f:
        queries = json.load(f)
    
    with open(data_path / "tool_names.json", "r") as f:
        tool_names = json.load(f)
    
    logger.info(f"✅ Loaded {X.shape[0]} samples with {X.shape[1]} features")
    logger.info(f"✅ {len(tool_names)} tools: {', '.join(tool_names[:5])}...")
    
    return X, y, queries, tool_names


def split_data(X: np.ndarray, y: np.ndarray, queries: List[str], test_size: float = 0.2) -> Tuple:
    """Split data into train/test sets."""
    from sklearn.model_selection import train_test_split
    
    logger.info(f"\nSplitting data (test_size={test_size})...")
    
    X_train, X_test, y_train, y_test, queries_train, queries_test = train_test_split(
        X, y, queries, test_size=test_size, random_state=42
    )
    
    logger.info(f"  Train set: {X_train.shape[0]} samples")
    logger.info(f"  Test set:  {X_test.shape[0]} samples")
    
    return X_train, X_test, y_train, y_test, queries_train, queries_test


def train_classifier(X_train: np.ndarray, y_train: np.ndarray, tool_names: List[str]) -> ToolClassifier:
    """Train the classifier."""
    logger.info("\n" + "=" * 70)
    logger.info("TRAINING CLASSIFIER")
    logger.info("=" * 70)
    
    classifier = ToolClassifier(tool_names)
    classifier.train(X_train, y_train)
    
    return classifier


def evaluate_classifier(
    classifier: ToolClassifier,
    X_test: np.ndarray,
    y_test: np.ndarray,
    queries_test: List[str],
    tool_names: List[str]
) -> Dict:
    """Comprehensive evaluation of the classifier."""
    from sklearn.metrics import (
        precision_recall_fscore_support,
        hamming_loss,
        jaccard_score,
        accuracy_score
    )
    
    logger.info("\n" + "=" * 70)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 70)
    
    # Predict on test set
    y_pred = np.zeros_like(y_test)
    
    for i in range(X_test.shape[0]):
        probs = classifier.predict_proba(X_test[i])
        for j, tool in enumerate(tool_names):
            y_pred[i, j] = 1 if probs.get(tool, 0) >= 0.3 else 0
    
    # Overall metrics
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='micro', zero_division=0
    )
    
    hamming = hamming_loss(y_test, y_pred)
    jaccard = jaccard_score(y_test, y_pred, average='samples', zero_division=0)
    
    # Exact match accuracy
    exact_match = accuracy_score(y_test, y_pred)
    
    logger.info("\n📊 Overall Performance:")
    logger.info(f"  Precision:    {precision:.3f} {'✅' if precision >= 0.8 else '⚠️' if precision >= 0.7 else '❌'}")
    logger.info(f"  Recall:       {recall:.3f} {'✅' if recall >= 0.8 else '⚠️' if recall >= 0.7 else '❌'}")
    logger.info(f"  F1 Score:     {f1:.3f} {'✅' if f1 >= 0.8 else '⚠️' if f1 >= 0.7 else '❌'}")
    logger.info(f"  Hamming Loss: {hamming:.3f} {'✅' if hamming <= 0.1 else '⚠️' if hamming <= 0.2 else '❌'}")
    logger.info(f"  Jaccard:      {jaccard:.3f} {'✅' if jaccard >= 0.7 else '⚠️' if jaccard >= 0.6 else '❌'}")
    logger.info(f"  Exact Match:  {exact_match:.3f} {'✅' if exact_match >= 0.7 else '⚠️' if exact_match >= 0.5 else '❌'}")
    
    # Per-tool metrics
    logger.info("\n📊 Per-Tool Performance:")
    
    tool_metrics = []
    
    for i, tool in enumerate(tool_names):
        if y_test[:, i].sum() == 0:
            continue  # Skip tools not in test set
        
        y_true_tool = y_test[:, i]
        y_pred_tool = y_pred[:, i]
        
        precision_tool = precision_recall_fscore_support(
            y_true_tool, y_pred_tool, average='binary', zero_division=0
        )[0]
        recall_tool = precision_recall_fscore_support(
            y_true_tool, y_pred_tool, average='binary', zero_division=0
        )[1]
        f1_tool = precision_recall_fscore_support(
            y_true_tool, y_pred_tool, average='binary', zero_division=0
        )[2]
        
        support = int(y_true_tool.sum())
        
        tool_metrics.append({
            'tool': tool,
            'precision': precision_tool,
            'recall': recall_tool,
            'f1': f1_tool,
            'support': support
        })
        
        status = '✅' if f1_tool >= 0.8 else '⚠️' if f1_tool >= 0.7 else '❌'
        logger.info(f"  {tool:30s}: P={precision_tool:.2f} R={recall_tool:.2f} F1={f1_tool:.2f} (n={support:3d}) {status}")
    
    # Example predictions
    logger.info("\n📊 Sample Predictions:")
    
    sample_indices = np.random.choice(len(X_test), min(5, len(X_test)), replace=False)
    
    for idx in sample_indices:
        query = queries_test[idx]
        true_tools = {tool_names[i] for i in range(len(tool_names)) if y_test[idx, i] == 1}
        pred_probs = classifier.predict_proba(X_test[idx])
        pred_tools = {tool for tool, prob in pred_probs.items() if prob >= 0.3}
        
        correct = true_tools == pred_tools
        status = '✅' if correct else '❌'
        
        logger.info(f"\n  Query: \"{query[:60]}...\"")
        logger.info(f"  True:  {sorted(true_tools)}")
        logger.info(f"  Pred:  {sorted(pred_tools)}")
        logger.info(f"  Status: {status}")
        
        if not correct:
            missing = true_tools - pred_tools
            extra = pred_tools - true_tools
            if missing:
                logger.info(f"    Missing: {sorted(missing)}")
            if extra:
                logger.info(f"    Extra:   {sorted(extra)}")
    
    # Compile results
    results = {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'hamming_loss': hamming,
        'jaccard': jaccard,
        'exact_match': exact_match,
        'tool_metrics': tool_metrics
    }
    
    return results


def deployment_recommendation(results: Dict) -> Tuple[bool, str, List[str]]:
    """
    Determine if model is ready for deployment.
    
    Returns:
        (ready: bool, grade: str, issues: List[str])
    """
    f1 = results['f1']
    precision = results['precision']
    recall = results['recall']
    exact_match = results['exact_match']
    
    issues = []
    
    # Check F1 score
    if f1 < 0.7:
        issues.append(f"F1 score too low ({f1:.3f} < 0.7)")
    
    # Check precision
    if precision < 0.7:
        issues.append(f"Precision too low ({precision:.3f} < 0.7)")
    
    # Check recall
    if recall < 0.7:
        issues.append(f"Recall too low ({recall:.3f} < 0.7)")
    
    # Check per-tool performance
    poor_tools = [
        m['tool'] for m in results['tool_metrics']
        if m['f1'] < 0.6 and m['support'] >= 5
    ]
    
    if poor_tools:
        issues.append(f"Poor performance on tools: {', '.join(poor_tools)}")
    
    # Determine grade and readiness
    if f1 >= 0.9 and precision >= 0.85 and recall >= 0.85:
        grade = "A+ ⭐"
        ready = True
    elif f1 >= 0.85 and precision >= 0.8 and recall >= 0.8:
        grade = "A"
        ready = True
    elif f1 >= 0.8 and precision >= 0.75 and recall >= 0.75:
        grade = "B+"
        ready = True
    elif f1 >= 0.75 and precision >= 0.7 and recall >= 0.7:
        grade = "B"
        ready = True
    elif f1 >= 0.7:
        grade = "C+"
        ready = False
    else:
        grade = "C"
        ready = False
    
    return ready, grade, issues


def main():
    """Main training and evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train and evaluate ML tool classifier")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing training data"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="models/tool_classifier.pkl",
        help="Path to save trained model"
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data to use for testing"
    )
    
    args = parser.parse_args()
    
    try:
        # Load data
        X, y, queries, tool_names = load_training_data(args.data_dir)
        
        # Split data
        X_train, X_test, y_train, y_test, queries_train, queries_test = split_data(
            X, y, queries, args.test_size
        )
        
        # Train
        classifier = train_classifier(X_train, y_train, tool_names)
        
        # Evaluate
        results = evaluate_classifier(classifier, X_test, y_test, queries_test, tool_names)
        
        # Deployment recommendation
        ready, grade, issues = deployment_recommendation(results)
        
        logger.info("\n" + "=" * 70)
        logger.info("DEPLOYMENT ASSESSMENT")
        logger.info("=" * 70)
        logger.info(f"\n🎯 Overall Grade: {grade}")
        logger.info(f"📊 F1 Score: {results['f1']:.3f}")
        logger.info(f"🎯 Precision: {results['precision']:.3f}")
        logger.info(f"🎯 Recall: {results['recall']:.3f}")
        logger.info(f"🎯 Exact Match: {results['exact_match']:.3f}")
        
        if ready:
            logger.info(f"\n✅ MODEL IS READY FOR DEPLOYMENT!")
            logger.info("\nRecommendations:")
            logger.info("  1. Save the model")
            logger.info("  2. Enable ML_TOOL_SELECTION_ENABLED=true")
            logger.info("  3. Start with A/B testing (50% ML, 50% rule-based)")
            logger.info("  4. Monitor performance in production")
            logger.info("  5. Retrain weekly with real data")
        else:
            logger.info(f"\n⚠️  MODEL NEEDS IMPROVEMENT")
            logger.info("\nIssues found:")
            for issue in issues:
                logger.info(f"  ❌ {issue}")
            logger.info("\nRecommendations:")
            logger.info("  1. Collect more training data (500+ samples)")
            logger.info("  2. Balance dataset (ensure all tools represented)")
            logger.info("  3. Check query quality and labels")
            logger.info("  4. Try different model parameters")
        
        # Save model
        logger.info(f"\n💾 Saving model to {args.model_path}...")
        classifier.save(args.model_path)
        logger.info("✅ Model saved successfully!")
        
        # Save evaluation results
        results_path = Path(args.model_path).parent / "evaluation_results.json"
        with open(results_path, "w") as f:
            # Convert numpy types to Python types for JSON
            json_results = {
                'precision': float(results['precision']),
                'recall': float(results['recall']),
                'f1': float(results['f1']),
                'hamming_loss': float(results['hamming_loss']),
                'jaccard': float(results['jaccard']),
                'exact_match': float(results['exact_match']),
                'grade': grade,
                'ready_for_deployment': ready,
                'issues': issues,
                'tool_metrics': [
                    {
                        'tool': m['tool'],
                        'precision': float(m['precision']),
                        'recall': float(m['recall']),
                        'f1': float(m['f1']),
                        'support': int(m['support'])
                    }
                    for m in results['tool_metrics']
                ]
            }
            json.dump(json_results, f, indent=2)
        
        logger.info(f"📊 Evaluation results saved to {results_path}")
        
        logger.info("\n" + "=" * 70)
        logger.info("TRAINING COMPLETE!")
        logger.info("=" * 70)
        
        sys.exit(0 if ready else 1)
        
    except Exception as e:
        logger.error(f"\n❌ Training failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
