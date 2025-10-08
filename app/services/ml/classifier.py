"""Tool classifier for ML-based tool selection."""
import logging
import numpy as np
from typing import Dict, List, Set, Optional
from pathlib import Path
import joblib

logger = logging.getLogger(__name__)


class ToolClassifier:
    """
    Multi-label classifier for tool selection.
    
    Uses Gradient Boosting to predict which tools are relevant for a given query.
    Supports probability scores for ranking and confidence thresholds.
    """
    
    def __init__(self, tool_names: List[str]):
        """
        Initialize tool classifier.
        
        Args:
            tool_names: List of all possible tool names
        """
        self.tool_names = tool_names
        self.n_tools = len(tool_names)
        self.classifier = None
        self.feature_importance = None
        
        logger.info(f"Initialized ToolClassifier with {self.n_tools} tools")
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """
        Train classifier on query embeddings and tool labels.
        
        Args:
            X: Query embeddings (n_samples, embedding_dim)
            y: Tool labels (n_samples, n_tools) - binary matrix
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.multioutput import MultiOutputClassifier
        
        logger.info(f"Training on {X.shape[0]} samples with {X.shape[1]} features")
        
        # Use RandomForest instead of GradientBoosting (handles sparse labels better)
        base_clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=2,
            random_state=42,
            n_jobs=1  # Individual jobs, MultiOutputClassifier handles parallelism
        )
        
        self.classifier = MultiOutputClassifier(base_clf, n_jobs=-1)
        
        # Train
        self.classifier.fit(X, y)
        
        logger.info("Training complete!")
        
        # Compute feature importance (average across all estimators)
        self.feature_importance = self._compute_importance()
    
    def predict_proba(self, query_embedding: np.ndarray) -> Dict[str, float]:
        """
        Predict probability for each tool.
        
        Args:
            query_embedding: Query embedding vector (embedding_dim,)
        
        Returns:
            Dictionary mapping tool names to probabilities
        """
        if self.classifier is None:
            raise ValueError("Classifier not trained yet")
        
        # Reshape for prediction
        X = query_embedding.reshape(1, -1)
        
        # Get predictions from each estimator
        tool_probs = {}
        
        for i, tool_name in enumerate(self.tool_names):
            estimator = self.classifier.estimators_[i]
            
            # Check if tool was trained (has more than one class)
            if hasattr(estimator, 'classes_') and len(estimator.classes_) < 2:
                # Tool never appeared in training data - set to 0
                tool_probs[tool_name] = 0.0
                continue
            
            try:
                # Get probability for positive class (tool is relevant)
                proba = estimator.predict_proba(X)[0]
                
                # proba is [prob_negative, prob_positive]
                tool_probs[tool_name] = float(proba[1]) if len(proba) > 1 else 0.0
            except:
                # If prediction fails, assume tool is not relevant
                tool_probs[tool_name] = 0.0
        
        return tool_probs
    
    def predict(self, query_embedding: np.ndarray, threshold: float = 0.5) -> Set[str]:
        """
        Predict relevant tools above threshold.
        
        Args:
            query_embedding: Query embedding vector
            threshold: Minimum probability threshold
        
        Returns:
            Set of relevant tool names
        """
        probs = self.predict_proba(query_embedding)
        return {tool for tool, prob in probs.items() if prob >= threshold}
    
    def predict_batch(self, X: np.ndarray, threshold: float = 0.5) -> List[Set[str]]:
        """
        Predict tools for multiple queries.
        
        Args:
            X: Query embeddings (n_samples, embedding_dim)
            threshold: Minimum probability threshold
        
        Returns:
            List of sets of predicted tool names
        """
        predictions = []
        
        for i in range(X.shape[0]):
            tools = self.predict(X[i], threshold)
            predictions.append(tools)
        
        return predictions
    
    def _compute_importance(self) -> Optional[np.ndarray]:
        """Compute average feature importance across all estimators."""
        try:
            importances = []
            for estimator in self.classifier.estimators_:
                importances.append(estimator.feature_importances_)
            
            return np.mean(importances, axis=0)
        except Exception as e:
            logger.warning(f"Could not compute feature importance: {e}")
            return None
    
    def save(self, path: str):
        """Save trained model."""
        model_path = Path(path)
        model_path.parent.mkdir(exist_ok=True, parents=True)
        
        joblib.dump({
            'classifier': self.classifier,
            'tool_names': self.tool_names,
            'feature_importance': self.feature_importance,
            'n_tools': self.n_tools
        }, path)
        
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> 'ToolClassifier':
        """Load trained model."""
        data = joblib.load(path)
        
        model = cls(data['tool_names'])
        model.classifier = data['classifier']
        model.feature_importance = data.get('feature_importance')
        model.n_tools = data.get('n_tools', len(data['tool_names']))
        
        logger.info(f"Model loaded from {path}")
        
        return model
