"""
Model evaluation for Stubble Smoke Alert.

Computes accuracy, macro F1, per-class metrics, and compares
against a "tomorrow equals today" baseline.

Reports honestly, including if the lift over baseline is small.
"""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from src.config import BAND_LABELS, MODEL_DIR, PROCESSED_DIR
from src.train import load_training_data

import joblib


def evaluate_model(
    processed_dir: Path = PROCESSED_DIR,
    model_dir: Path = MODEL_DIR,
) -> dict:
    """
    Evaluate the trained model against test set and baseline.

    The baseline predicts "tomorrow's AQI band = today's AQI band".
    This is a strong baseline for AQI because air quality has high
    day-to-day autocorrelation.

    Returns:
        Dictionary of evaluation results.
    """
    # Load model and data
    model = joblib.load(model_dir / "model.joblib")
    le = joblib.load(model_dir / "label_encoder.joblib")
    X_train, X_test, y_test_encoded, _, _, split_date, train_df, test_df = \
        load_training_data(processed_dir)

    # --- Model predictions ---
    y_pred_encoded = model.predict(X_test)
    y_pred_labels = le.inverse_transform(y_pred_encoded)
    y_true_labels = test_df["aqi_band_tomorrow"].values

    model_accuracy = accuracy_score(y_true_labels, y_pred_labels)
    model_f1 = f1_score(y_true_labels, y_pred_labels, average="macro", zero_division=0)

    # --- Baseline: tomorrow = today ---
    baseline_pred = test_df["aqi_band"].values  # today's band
    baseline_accuracy = accuracy_score(y_true_labels, baseline_pred)
    baseline_f1 = f1_score(y_true_labels, baseline_pred, average="macro", zero_division=0)

    # --- Lift over baseline ---
    accuracy_lift = model_accuracy - baseline_accuracy
    f1_lift = model_f1 - baseline_f1

    # --- Classification report ---
    report = classification_report(
        y_true_labels, y_pred_labels,
        labels=BAND_LABELS,
        zero_division=0,
        output_dict=True,
    )
    report_str = classification_report(
        y_true_labels, y_pred_labels,
        labels=BAND_LABELS,
        zero_division=0,
    )

    # --- Confusion matrix ---
    cm = confusion_matrix(y_true_labels, y_pred_labels, labels=BAND_LABELS)

    # --- Feature importances ---
    from src.features import MODEL_FEATURES
    importances = model.feature_importances_
    feat_imp = sorted(
        zip(MODEL_FEATURES, importances),
        key=lambda x: x[1],
        reverse=True,
    )

    results = {
        "model_accuracy": round(model_accuracy, 4),
        "model_macro_f1": round(model_f1, 4),
        "baseline_accuracy": round(baseline_accuracy, 4),
        "baseline_macro_f1": round(baseline_f1, 4),
        "accuracy_lift": round(accuracy_lift, 4),
        "f1_lift": round(f1_lift, 4),
        "test_size": len(test_df),
        "split_date": str(split_date.date()),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "feature_importances": [(f, round(float(i), 4)) for f, i in feat_imp[:10]],
    }

    # --- Print results ---
    print("=" * 60)
    print("MODEL EVALUATION RESULTS")
    print("=" * 60)
    print(f"\nTest set: {len(test_df)} days (after {split_date.date()})")
    print(f"\n--- Model Performance ---")
    print(f"  Accuracy:  {model_accuracy:.4f}")
    print(f"  Macro F1:  {model_f1:.4f}")
    print(f"\n--- Baseline (tomorrow = today) ---")
    print(f"  Accuracy:  {baseline_accuracy:.4f}")
    print(f"  Macro F1:  {baseline_f1:.4f}")
    print(f"\n--- Lift over baseline ---")
    print(f"  Accuracy:  {accuracy_lift:+.4f}")
    print(f"  Macro F1:  {f1_lift:+.4f}")

    if accuracy_lift <= 0:
        print("\n  NOTE: The model does not beat the naive baseline on accuracy.")
        print("  This is common for AQI prediction due to high autocorrelation.")
        print("  The model may still add value through better coverage of")
        print("  rare severe events and the policy layer's bounded actions.")

    print(f"\n--- Classification Report ---\n{report_str}")

    print(f"\n--- Top Feature Importances ---")
    for feat, imp in feat_imp[:10]:
        print(f"  {feat:30s}  {imp:.4f}")

    print(f"\n--- Confusion Matrix ---")
    print(f"  Labels: {BAND_LABELS}")
    for i, row in enumerate(cm):
        print(f"  {BAND_LABELS[i]:10s}  {row}")

    # Save results
    results_path = model_dir / "evaluation_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {results_path}")

    return results


if __name__ == "__main__":
    evaluate_model()
