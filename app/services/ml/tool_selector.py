"""
ML-based tool selector for intelligent tool selection.

This module provides the high-level interface for using ML to select tools
based on user queries. It handles:
- Loading the trained model
- Embedding queries
- Predicting relevant tools
- Confidence filtering
- Fallback to rule-based selection
- Performance tracking and statistics
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import threading

from app.core.config import (
    ML_MODEL_PATH,
    ML_CONFIDENCE_THRESHOLD,
    ML_MAX_TOOLS,
    ML_TOOL_SELECTION_ENABLED
)
from app.services.ml.embedder import QueryEmbedder
from app.services.ml.classifier import ToolClassifier
from app.services.ml.doc_based_selector import DocBasedToolSelector

logger = logging.getLogger(__name__)


class MLToolSelector:
    """
    High-level ML tool selector with caching, fallback, and monitoring.
    
    Features:
    - Lazy model loading (only loads when first needed)
    - Query embedding with caching
    - Confidence-based filtering
    - Fallback to rule-based when confidence is low
    - Statistics tracking for monitoring
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for efficient resource usage."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the ML tool selector (lazy loading)."""
        if self._initialized:
            return
            
        self.embedder: Optional[QueryEmbedder] = None
        self.classifier: Optional[ToolClassifier] = None
        self.doc_selector: Optional[DocBasedToolSelector] = None
        self.model_loaded = False
        self.model_path = ML_MODEL_PATH
        self.confidence_threshold = ML_CONFIDENCE_THRESHOLD
        self.max_tools = ML_MAX_TOOLS
        
        # Statistics tracking
        self.stats = {
            'total_predictions': 0,
            'fallback_count': 0,
            'doc_based_count': 0,  # Track doc-based usage
            'ml_count': 0,  # Track ML usage
            'avg_confidence': 0.0,
            'avg_prediction_time_ms': 0.0,
            'tools_predicted': defaultdict(int),
            'confidence_distribution': defaultdict(int),  # bins: 0-0.3, 0.3-0.5, 0.5-0.7, 0.7-1.0
        }
        self.stats_lock = threading.Lock()
        
        self._initialized = True
        logger.info("MLToolSelector initialized (lazy loading enabled)")
    
    def _load_model(self) -> bool:
        """
        Load the trained model and embedder (lazy loading).
        
        Returns:
            True if successful, False otherwise
        """
        if self.model_loaded:
            return True
            
        try:
            logger.info(f"Loading ML model from {self.model_path}...")
            
            # Check if model file exists
            model_file = Path(self.model_path)
            if not model_file.exists():
                logger.error(f"Model file not found: {self.model_path}")
                return False
            
            # Initialize embedder
            self.embedder = QueryEmbedder()
            logger.info("Query embedder initialized")
            
            # Load classifier
            self.classifier = ToolClassifier.load(self.model_path)
            logger.info(f"Classifier loaded with {len(self.classifier.tool_names)} tools")
            
            # Initialize doc-based selector (shares embedder)
            self.doc_selector = DocBasedToolSelector(self.embedder)
            logger.info("Doc-based selector initialized")
            
            self.model_loaded = True
            logger.info("✅ ML model loaded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}", exc_info=True)
            self.model_loaded = False
            return False
    
    def predict_tools(
        self,
        query: str,
        available_tools: Optional[List[str]] = None,
        return_probabilities: bool = False,
        use_hybrid: bool = True
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Predict relevant tools for a query using ML with doc-based fallback.
        
        HYBRID STRATEGY:
        1. Try ML classifier first (fastest, best for trained patterns)
        2. If ML confidence is low, use doc-based similarity (better cold start)
        3. Merge results if both provide partial matches
        
        Args:
            query: User query text
            available_tools: Optional list of available tools to filter by
            return_probabilities: Whether to return tool probabilities
            use_hybrid: Whether to use hybrid ML + doc-based approach
            
        Returns:
            Tuple of (selected_tools, probabilities_dict)
            - selected_tools: List of tool names above confidence threshold
            - probabilities_dict: Dict of tool -> probability (empty if not requested)
        """
        start_time = time.time()
        
        # Lazy load model if needed
        if not self.model_loaded:
            if not self._load_model():
                logger.warning("ML model not loaded, falling back to doc-based")
                return self._predict_doc_based(query, available_tools, return_probabilities)
        
        try:
            # Step 1: Try ML classifier first
            logger.debug(f"Embedding query: {query[:100]}...")
            query_embedding = self.embedder.embed(query)
            
            logger.debug("Predicting tool probabilities with ML...")
            tool_probs = self.classifier.predict_proba(query_embedding)
            
            # Filter by available tools if specified
            if available_tools:
                tool_probs = {
                    tool: prob 
                    for tool, prob in tool_probs.items() 
                    if tool in available_tools
                }
            
            # Filter by confidence threshold
            filtered_tools = {
                tool: prob 
                for tool, prob in tool_probs.items() 
                if prob >= self.confidence_threshold
            }
            
            # Sort by probability and limit to max_tools
            sorted_tools = sorted(
                filtered_tools.items(),
                key=lambda x: x[1],
                reverse=True
            )[:self.max_tools]
            
            selected_tools = [tool for tool, _ in sorted_tools]
            probabilities = dict(sorted_tools)
            
            # Calculate average confidence
            avg_confidence = sum(probabilities.values()) / len(probabilities) if probabilities else 0.0
            
            # Step 2: Check if we should augment with doc-based (hybrid mode)
            if use_hybrid and self.doc_selector:
                # Use doc-based if:
                # - ML returned nothing
                # - ML confidence is low (< 0.40) regardless of tool count
                # This is more aggressive to ensure doc-based gets used
                should_augment = (
                    not selected_tools or
                    avg_confidence < 0.40
                )
                
                if should_augment:
                    logger.info(
                        f"ML confidence low ({avg_confidence:.2f}) or few tools ({len(selected_tools)}), "
                        "augmenting with doc-based selector"
                    )
                    
                    # Get doc-based predictions
                    doc_tools, doc_scores = self.doc_selector.predict_tools(
                        query,
                        max_tools=self.max_tools,
                        available_tools=available_tools
                    )
                    
                    # Merge results (prioritize ML, add doc-based if needed)
                    merged_tools = list(selected_tools)  # Start with ML tools
                    merged_probs = dict(probabilities)
                    
                    for doc_tool in doc_tools:
                        if doc_tool not in merged_tools and len(merged_tools) < self.max_tools:
                            merged_tools.append(doc_tool)
                            # Convert similarity (0-1) to probability-like score
                            merged_probs[doc_tool] = doc_scores.get(doc_tool, 0.0) * 0.7  # Scale down
                    
                    # Update if we got better results
                    if len(merged_tools) > len(selected_tools):
                        logger.info(
                            f"Hybrid approach added {len(merged_tools) - len(selected_tools)} "
                            f"doc-based tools: {[t for t in merged_tools if t not in selected_tools]}"
                        )
                        selected_tools = merged_tools
                        probabilities = merged_probs
                        avg_confidence = sum(probabilities.values()) / len(probabilities)
                        
                        # Track doc-based usage
                        with self.stats_lock:
                            self.stats['doc_based_count'] += 1
            
            # Update statistics
            prediction_time_ms = (time.time() - start_time) * 1000
            self._update_stats(
                selected_tools, 
                probabilities, 
                prediction_time_ms, 
                avg_confidence,
                method='ml' if not use_hybrid or avg_confidence >= 0.5 else 'hybrid'
            )
            
            probabilities_out = probabilities if return_probabilities else {}
            
            logger.info(
                f"{'Hybrid' if use_hybrid and avg_confidence < 0.5 else 'ML'} predicted "
                f"{len(selected_tools)} tools in {prediction_time_ms:.1f}ms "
                f"(avg confidence: {avg_confidence:.2f}): {selected_tools}"
            )
            
            return selected_tools, probabilities_out
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}", exc_info=True)
            
            # Final fallback: try doc-based
            if use_hybrid and self.doc_selector:
                logger.info("ML failed, trying doc-based fallback")
                return self._predict_doc_based(query, available_tools, return_probabilities)
            
            return [], {}
    
    def _predict_doc_based(
        self,
        query: str,
        available_tools: Optional[List[str]],
        return_probabilities: bool
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Predict using doc-based selector only.
        
        This is used when ML is unavailable or as a fallback.
        """
        if not self.doc_selector:
            # Initialize doc selector if not already done
            if self.embedder:
                self.doc_selector = DocBasedToolSelector(self.embedder)
            else:
                self.embedder = QueryEmbedder()
                self.doc_selector = DocBasedToolSelector(self.embedder)
        
        try:
            tools, scores = self.doc_selector.predict_tools(
                query,
                max_tools=self.max_tools,
                available_tools=available_tools
            )
            
            # Track usage
            with self.stats_lock:
                self.stats['doc_based_count'] += 1
                self.stats['total_predictions'] += 1
            
            logger.info(f"Doc-based selected {len(tools)} tools: {tools}")
            
            return tools, scores if return_probabilities else {}
            
        except Exception as e:
            logger.error(f"Doc-based prediction failed: {e}", exc_info=True)
            return [], {}
    
    def should_use_ml(self) -> bool:
        """
        Check if ML tool selection should be used.
        
        Returns:
            True if ML is enabled and model is loaded/loadable
        """
        if not ML_TOOL_SELECTION_ENABLED:
            return False
        
        if not self.model_loaded:
            return self._load_model()
        
        return True
    
    def _update_stats(
        self,
        selected_tools: List[str],
        probabilities: Dict[str, float],
        prediction_time_ms: float,
        avg_confidence: float,
        method: str = 'ml'
    ):
        """Update statistics tracking."""
        with self.stats_lock:
            n = self.stats['total_predictions']
            
            # Update running averages
            self.stats['avg_confidence'] = (
                (self.stats['avg_confidence'] * n + avg_confidence) / (n + 1)
            )
            self.stats['avg_prediction_time_ms'] = (
                (self.stats['avg_prediction_time_ms'] * n + prediction_time_ms) / (n + 1)
            )
            self.stats['total_predictions'] += 1
            
            # Track method usage
            if method == 'ml':
                self.stats['ml_count'] += 1
            
            # Track tool usage
            for tool in selected_tools:
                self.stats['tools_predicted'][tool] += 1
            
            # Track confidence distribution
            if avg_confidence < 0.3:
                self.stats['confidence_distribution']['0.0-0.3'] += 1
            elif avg_confidence < 0.5:
                self.stats['confidence_distribution']['0.3-0.5'] += 1
            elif avg_confidence < 0.7:
                self.stats['confidence_distribution']['0.7-0.9'] += 1
            else:
                self.stats['confidence_distribution']['0.7-1.0'] += 1
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        with self.stats_lock:
            total = self.stats['total_predictions']
            return {
                'total_predictions': total,
                'ml_count': self.stats['ml_count'],
                'doc_based_count': self.stats['doc_based_count'],
                'fallback_count': self.stats['fallback_count'],
                'ml_rate': self.stats['ml_count'] / total if total > 0 else 0.0,
                'doc_based_rate': self.stats['doc_based_count'] / total if total > 0 else 0.0,
                'fallback_rate': self.stats['fallback_count'] / total if total > 0 else 0.0,
                'avg_confidence': round(self.stats['avg_confidence'], 3),
                'avg_prediction_time_ms': round(self.stats['avg_prediction_time_ms'], 2),
                'tools_predicted': dict(self.stats['tools_predicted']),
                'confidence_distribution': dict(self.stats['confidence_distribution']),
                'model_loaded': self.model_loaded,
                'ml_enabled': ML_TOOL_SELECTION_ENABLED,
                'doc_selector_available': self.doc_selector is not None,
            }
    
    def record_fallback(self):
        """Record that fallback to rule-based was used."""
        with self.stats_lock:
            self.stats['fallback_count'] += 1
    
    def reset_stats(self):
        """Reset statistics (useful for testing/monitoring)."""
        with self.stats_lock:
            self.stats = {
                'total_predictions': 0,
                'fallback_count': 0,
                'doc_based_count': 0,
                'ml_count': 0,
                'avg_confidence': 0.0,
                'avg_prediction_time_ms': 0.0,
                'tools_predicted': defaultdict(int),
                'confidence_distribution': defaultdict(int),
            }
        logger.info("Statistics reset")
    
    def get_doc_selector(self) -> Optional[DocBasedToolSelector]:
        """Get the doc-based selector for direct use."""
        if not self.doc_selector and self.embedder:
            self.doc_selector = DocBasedToolSelector(self.embedder)
        return self.doc_selector


# Global singleton instance
_ml_selector = MLToolSelector()


def get_ml_tool_selector() -> MLToolSelector:
    """
    Get the global ML tool selector instance.
    
    Returns:
        MLToolSelector singleton instance
    """
    return _ml_selector


def predict_tools_ml(
    query: str,
    available_tools: Optional[List[str]] = None,
    return_probabilities: bool = False
) -> Tuple[List[str], Dict[str, float]]:
    """
    Convenience function for ML tool prediction.
    
    Args:
        query: User query text
        available_tools: Optional list of available tools to filter by
        return_probabilities: Whether to return tool probabilities
        
    Returns:
        Tuple of (selected_tools, probabilities_dict)
    """
    selector = get_ml_tool_selector()
    return selector.predict_tools(query, available_tools, return_probabilities)


def get_ml_stats() -> Dict:
    """
    Get ML tool selector statistics.
    
    Returns:
        Dictionary with statistics
    """
    selector = get_ml_tool_selector()
    return selector.get_stats()
