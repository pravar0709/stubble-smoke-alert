"""
Prediction module for Stubble Smoke Alert.

Loads the trained model and makes predictions on new feature vectors.
Separated from orchestration (forecast.py) for clean modularity.
"""

from pathlib import Path

import joblib
import numpy as np

from src.config import MODEL_DIR
from src.features import MODEL_FEATURES


def load_model(model_dir: Path = MODEL_DIR):
    """
    Load the trained model and label encoder.

    Returns:
        (model, label_encoder)
    """
    model = joblib.load(model_dir / "model.joblib")
    le = joblib.load(model_dir / "label_encoder.joblib")
    return model, le


def predict_band(features: dict, model=None, le=None, model_dir: Path = MODEL_DIR) -> str:
    """
    Predict tomorrow's AQI band from a feature dictionary.

    Args:
        features: Dict with keys matching MODEL_FEATURES.
        model: Pre-loaded model (optional, loaded if None).
        le: Pre-loaded label encoder (optional, loaded if None).

    Returns:
        Predicted AQI band label (e.g., "Very Poor").
    """
    if model is None or le is None:
        model, le = load_model(model_dir)

    # Build feature vector in correct order
    X = np.array([[features.get(f, 0) for f in MODEL_FEATURES]])
    y_pred = model.predict(X)
    return le.inverse_transform(y_pred)[0]
