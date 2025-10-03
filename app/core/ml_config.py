"""GPU and ML configuration for stock prediction.

This module handles GPU detection, memory configuration, and ML model settings
optimized for GTX 1650 Ti Mobile (4GB VRAM).
"""

import os
import logging

logger = logging.getLogger(__name__)

# GPU Configuration
GPU_MEMORY_LIMIT_MB = int(os.getenv("GPU_MEMORY_LIMIT_MB", "3584"))  # 3.5GB max for 4GB GPU
ENABLE_GPU_MEMORY_GROWTH = os.getenv("ENABLE_GPU_MEMORY_GROWTH", "true").lower() in {"1", "true", "yes"}
FORCE_CPU = os.getenv("FORCE_CPU", "false").lower() in {"1", "true", "yes"}

# Model Training Configuration
PREDICTION_MODEL_CONFIG = {
    # LSTM Architecture (optimized for 4GB VRAM)
    "lstm_units": [64, 32, 16],  # Layers: 64 -> 32 -> 16 units
    "dropout": 0.2,
    "lookback_days": 60,
    "prediction_days": 7,
    
    # Training Parameters
    "batch_size": int(os.getenv("PREDICTION_BATCH_SIZE", "32")),
    "epochs": int(os.getenv("PREDICTION_EPOCHS", "50")),
    "learning_rate": float(os.getenv("PREDICTION_LEARNING_RATE", "0.001")),
    
    # Early Stopping
    "early_stopping_patience": int(os.getenv("PREDICTION_EARLY_STOPPING_PATIENCE", "10")),
    "reduce_lr_patience": int(os.getenv("PREDICTION_REDUCE_LR_PATIENCE", "5")),
    
    # Features
    "features": ["close", "volume", "high", "low", "sma_5", "sma_20", "rsi_14"],
    
    # Data
    "train_test_split": float(os.getenv("PREDICTION_TRAIN_SPLIT", "0.8")),
    "validation_split": float(os.getenv("PREDICTION_VAL_SPLIT", "0.2")),
}


def configure_gpu():
    """Configure GPU settings for optimal performance on GTX 1650 Ti.
    
    Returns:
        bool: True if GPU is available and configured, False otherwise
    """
    if FORCE_CPU:
        logger.info("GPU disabled by FORCE_CPU environment variable")
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        return False
    
    try:
        import tensorflow as tf
        
        gpus = tf.config.list_physical_devices('GPU')
        
        if not gpus:
            logger.info("No GPU detected, using CPU")
            return False
        
        logger.info(f"Detected {len(gpus)} GPU(s): {[gpu.name for gpu in gpus]}")
        
        for gpu in gpus:
            try:
                # Enable memory growth to avoid OOM on 4GB GPU
                if ENABLE_GPU_MEMORY_GROWTH:
                    tf.config.experimental.set_memory_growth(gpu, True)
                    logger.info(f"Enabled memory growth for {gpu.name}")
                
                # Set memory limit if specified
                if GPU_MEMORY_LIMIT_MB > 0:
                    tf.config.set_logical_device_configuration(
                        gpu,
                        [tf.config.LogicalDeviceConfiguration(
                            memory_limit=GPU_MEMORY_LIMIT_MB
                        )]
                    )
                    logger.info(f"Set memory limit to {GPU_MEMORY_LIMIT_MB}MB for {gpu.name}")
                
            except RuntimeError as e:
                # Memory growth must be set before GPUs are initialized
                logger.warning(f"Could not configure {gpu.name}: {e}")
        
        # Verify GPU is available for TensorFlow
        if tf.test.is_built_with_cuda():
            logger.info("TensorFlow is built with CUDA support")
        else:
            logger.warning("TensorFlow is NOT built with CUDA support (CPU only)")
        
        return len(gpus) > 0
        
    except ImportError:
        logger.warning("TensorFlow not installed, GPU configuration skipped")
        return False
    except Exception as e:
        logger.error(f"GPU configuration failed: {e}")
        return False


def get_device_info():
    """Get information about available compute devices.
    
    Returns:
        dict: Device information including GPU/CPU details
    """
    info = {
        "gpu_available": False,
        "gpu_count": 0,
        "gpu_names": [],
        "cpu_only": True,
        "tensorflow_version": None,
        "cuda_available": False,
    }
    
    try:
        import tensorflow as tf
        
        info["tensorflow_version"] = tf.__version__
        info["cuda_available"] = tf.test.is_built_with_cuda()
        
        gpus = tf.config.list_physical_devices('GPU')
        
        if gpus:
            info["gpu_available"] = True
            info["gpu_count"] = len(gpus)
            info["gpu_names"] = [gpu.name for gpu in gpus]
            info["cpu_only"] = False
        
    except ImportError:
        info["error"] = "TensorFlow not installed"
    except Exception as e:
        info["error"] = str(e)
    
    return info


# Auto-configure GPU on module import
_GPU_CONFIGURED = False

def ensure_gpu_configured():
    """Ensure GPU is configured (idempotent)."""
    global _GPU_CONFIGURED
    if not _GPU_CONFIGURED:
        configure_gpu()
        _GPU_CONFIGURED = True
