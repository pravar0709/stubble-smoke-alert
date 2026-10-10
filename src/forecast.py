"""
Forecast orchestrator for Stubble Smoke Alert.

Brings together the latest data, model prediction, and policy layer
to produce a complete forecast.json for the frontend and API.

Usage:
    python -m src.forecast
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    DELHI_LAT,
    DELHI_LON,
    MODEL_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    aqi_to_band,
)
from src.features import MODEL_FEATURES
from src.policy import build_reason, get_school_action
from src.predict import load_model, predict_band


def generate_forecast(
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    model_dir: Path = MODEL_DIR,
    output_path: Path = None,
) -> dict:
    """
    Generate the latest forecast.

    Steps:
    1. Load the most recent day's features from processed data
    2. Run model prediction for tomorrow's AQI band
    3. Apply policy layer
    4. Build reason string
    5. Gather recent fire data for map
    6. Write forecast.json

    Returns:
        Complete forecast dictionary.
    """
    # Load processed features (use the last row as "today")
    features_path = processed_dir / "features.csv"
    if not features_path.exists():
        raise FileNotFoundError("No processed features. Run the feature pipeline first.")

    df = pd.read_csv(features_path, parse_dates=["date"])
    df = df.sort_values("date")
    latest = df.iloc[-1]

    today_date = pd.Timestamp(latest["date"])
    forecast_date = today_date + timedelta(days=1)

    # Build feature dict for prediction
    features = {f: float(latest[f]) for f in MODEL_FEATURES}

    # Load model and predict
    model, le = load_model(model_dir)
    predicted_band = predict_band(features, model, le)

    # Get policy action
    policy = get_school_action(predicted_band)

    # Build reason
    reason = build_reason(
        band=predicted_band,
        wind_dir=features.get("wind_dir_dominant"),
        wind_speed=features.get("wind_speed_max"),
        fire_count=features.get("fires_total_upwind"),
        aqi_today=int(features.get("aqi_today", 0)),
    )

    # Load recent fire data for map (last 3 days)
    fires = _load_recent_fires(raw_dir, today_date, days=3)

    # Determine model type
    has_fire_data = features.get("fires_total_upwind", 0) > 0
    model_type = "gradient_boosting_with_fires" if has_fire_data else "gradient_boosting_weather_only"

    # Load evaluation metadata
    eval_path = model_dir / "evaluation_results.json"
    eval_data = {}
    if eval_path.exists():
        with open(eval_path) as f:
            eval_data = json.load(f)

    # AQI range for the predicted band
    band_ranges = {
        "Good": "0-50",
        "Moderate": "51-100",
        "Poor": "101-200",
        "Very Poor": "201-300",
        "Severe": "301-500",
    }

    forecast = {
        "forecast_date": str(forecast_date.date()),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "today_date": str(today_date.date()),
        "today_aqi": int(features.get("aqi_today", 0)),
        "today_band": aqi_to_band(features.get("aqi_today", 0)),
        "predicted_aqi_band": predicted_band,
        "predicted_aqi_range": band_ranges.get(predicted_band, "Unknown"),
        "action": policy["action"],
        "severity": policy["severity"],
        "color": policy["color"],
        "details": policy["details"],
        "reason": reason,
        "model_type": model_type,
        "model_accuracy": eval_data.get("model_accuracy", "N/A"),
        "baseline_accuracy": eval_data.get("baseline_accuracy", "N/A"),
        "features_used": {
            "wind_speed": features.get("wind_speed_max", 0),
            "wind_dir": features.get("wind_dir_dominant", 0),
            "fires_upwind": features.get("fires_total_upwind", 0),
            "aqi_today": int(features.get("aqi_today", 0)),
            "temperature": features.get("temp_max", 0),
            "humidity": features.get("humidity_mean", 0),
        },
        "fires": fires,
        "delhi": {"lat": DELHI_LAT, "lon": DELHI_LON},
        "disclaimer": (
            "This is an experimental forecast for educational purposes. "
            "Always verify with official CPCB bulletins before making "
            "school-level decisions."
        ),
        "data_source": "synthetic" if not has_fire_data else "mixed",
    }

    # Save forecast.json
    if output_path is None:
        output_path = processed_dir / "forecast.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(forecast, f, indent=2)
    print(f"Forecast generated -> {output_path}")
    print(f"  Date: {forecast_date.date()}")
    print(f"  Predicted band: {predicted_band}")
    print(f"  Action: {policy['action'][:60]}...")
    print(f"  Reason: {reason[:80]}...")

    return forecast


def _load_recent_fires(raw_dir: Path, today: pd.Timestamp, days: int = 3) -> list:
    """
    Load recent fire detections for the map display.

    If no real fire data exists, generates a representative set of
    synthetic fire markers for demo purposes.
    """
    fires_path = raw_dir / "fires_viirs.csv"

    if fires_path.exists():
        fires_df = pd.read_csv(fires_path, parse_dates=["acq_date"])
        cutoff = today - timedelta(days=days)
        recent = fires_df[fires_df["acq_date"] >= cutoff]
        return [
            {
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "frp": float(row.get("frp", 0)),
                "date": str(row["acq_date"].date()),
            }
            for _, row in recent.head(200).iterrows()  # Cap at 200 for map performance
        ]

    # No real fire data: generate representative markers for demo
    # These represent typical stubble burning locations in Punjab/Haryana
    rng = np.random.RandomState(42)
    demo_fires = []
    # Stubble burning hotspots: Patiala, Sangrur, Bathinda, Karnal
    hotspots = [
        (30.34, 76.39, "Patiala"),
        (30.23, 75.84, "Sangrur"),
        (30.21, 74.95, "Bathinda"),
        (29.69, 76.98, "Karnal"),
        (31.32, 75.57, "Jalandhar"),
        (30.90, 75.86, "Ludhiana"),
        (29.95, 76.82, "Panipat"),
        (30.38, 76.78, "Ambala"),
    ]
    for lat, lon, _ in hotspots:
        n = rng.randint(3, 12)
        for _ in range(n):
            demo_fires.append({
                "lat": round(lat + rng.normal(0, 0.15), 4),
                "lon": round(lon + rng.normal(0, 0.15), 4),
                "frp": round(rng.uniform(5, 50), 1),
                "date": str((today - timedelta(days=rng.randint(0, days))).date()),
            })

    return demo_fires


if __name__ == "__main__":
    forecast = generate_forecast()
    print(f"\nFull forecast:\n{json.dumps(forecast, indent=2)}")
