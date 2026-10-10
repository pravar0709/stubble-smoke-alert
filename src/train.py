"""
Model training for Stubble Smoke Alert.

Trains a GradientBoostingClassifier to predict tomorrow's AQI band
from weather, fire, and autoregressive features.

Key design decisions:
- Chronological train/test split (no shuffling) to avoid data leakage
- class_weight simulation via sample_weight (GB doesn't support class_weight)
- Saves model to model/model.joblib
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder

from src.config import BAND_LABELS, MODEL_DIR, PROCESSED_DIR, RANDOM_STATE, TRAIN_TEST_SPLIT_RATIO
from src.features import MODEL_FEATURES


def load_training_data(processed_dir: Path = PROCESSED_DIR):
    """
    Load feature matrix and split chronologically.

    Returns:
        (X_train, X_test, y_train, y_test, label_encoder, split_date)
    """
    df = pd.read_csv(processed_dir / "features.csv", parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Chronological split
    split_idx = int(len(df) * TRAIN_TEST_SPLIT_RATIO)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    split_date = train_df["date"].iloc[-1]
    print(f"Chronological split: train={len(train_df)} rows (up to {split_date.date()}), "
          f"test={len(test_df)} rows")

    X_train = train_df[MODEL_FEATURES].values
    X_test = test_df[MODEL_FEATURES].values

    # Encode target labels
    le = LabelEncoder()
    le.fit(BAND_LABELS)  # Ensure consistent label ordering

    y_train = le.transform(train_df["aqi_band_tomorrow"].values)
    y_test = le.transform(test_df["aqi_band_tomorrow"].values)

    return X_train, X_test, y_train, y_test, le, split_date, train_df, test_df


def compute_sample_weights(y_train: np.ndarray) -> np.ndarray:
    """
    Compute sample weights to handle class imbalance.

    GradientBoosting doesn't support class_weight directly,
    so we use sample_weight inversely proportional to class frequency.
    """
    classes, counts = np.unique(y_train, return_counts=True)
    total = len(y_train)
    n_classes = len(classes)

    weights = np.zeros(len(y_train))
    for cls, count in zip(classes, counts):
        w = total / (n_classes * count)
        weights[y_train == cls] = w

    return weights


def train_model(processed_dir: Path = PROCESSED_DIR, model_dir: Path = MODEL_DIR):
    """
    Train the AQI band prediction model.

    Returns:
        (model, label_encoder, metadata_dict)
    """
    X_train, X_test, y_train, y_test, le, split_date, train_df, test_df = \
        load_training_data(processed_dir)

    sample_weights = compute_sample_weights(y_train)

    print("\nTraining GradientBoostingClassifier...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        min_samples_split=10,
        min_samples_leaf=5,
        subsample=0.8,
        random_state=RANDOM_STATE,
    )
    model.fit(X_train, y_train, sample_weight=sample_weights)
    print("Training complete.")

    # Save model
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "model.joblib"
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

    # Save label encoder
    le_path = model_dir / "label_encoder.joblib"
    joblib.dump(le, le_path)

    # Save feature names for validation
    meta = {
        "features": MODEL_FEATURES,
        "labels": list(le.classes_),
        "split_date": str(split_date.date()),
        "train_size": len(train_df),
        "test_size": len(test_df),
        "model_type": "GradientBoostingClassifier",
        "has_fire_data": any(
            train_df[c].sum() > 0
            for c in ["fires_0_200km_upwind", "fires_total_upwind"]
        ),
    }
    with open(model_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    return model, le, meta


if __name__ == "__main__":
    model, le, meta = train_model()
    print(f"\nModel metadata: {json.dumps(meta, indent=2)}")
