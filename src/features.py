"""
Feature engineering for Stubble Smoke Alert.

Merges AQI, weather, and (optional) fire data into a daily feature matrix
ready for model training. Each row is one day, with the target being
tomorrow's AQI band.

Key features:
- Upwind fire counts in distance rings (0-200km, 200-400km)
- Fire radiative power (FRP) from upwind fires
- Wind speed, direction, and NW-quadrant indicator
- Temperature range (inversion proxy), humidity
- Autoregressive: today's AQI, 3-day rolling average
- Seasonality: day-of-year, stubble-season indicator
"""

import numpy as np
import pandas as pd

from src.config import (
    AQI_BANDS,
    DELHI_LAT,
    DELHI_LON,
    DISTANCE_RINGS_KM,
    STUBBLE_SEASON_END_DAY,
    STUBBLE_SEASON_END_MONTH,
    STUBBLE_SEASON_START_DAY,
    STUBBLE_SEASON_START_MONTH,
    aqi_to_band,
)
from src.geo import (
    angular_difference,
    bearing_vectorized,
    haversine_vectorized,
)


def load_aqi(raw_dir) -> pd.DataFrame:
    """
    Load AQI data, preferring real data over synthetic.

    Looks for:
    1. data/raw/delhi_aqi.csv (real data, user-provided)
    2. data/raw/delhi_aqi_synthetic.csv (generated fallback)

    Returns:
        DataFrame with 'date' (datetime) and 'aqi' (int) columns.
    """
    real_path = raw_dir / "delhi_aqi.csv"
    synth_path = raw_dir / "delhi_aqi_synthetic.csv"

    if real_path.exists():
        print("Loading REAL AQI data from delhi_aqi.csv")
        df = pd.read_csv(real_path, parse_dates=["date"])
        # Ensure we have the aqi column
        if "aqi" not in df.columns:
            # Try common alternatives
            for col in ["AQI", "aqi_value", "AQI_Value"]:
                if col in df.columns:
                    df = df.rename(columns={col: "aqi"})
                    break
        return df[["date", "aqi"]].dropna()
    elif synth_path.exists():
        print("Loading SYNTHETIC AQI data (clearly labeled)")
        df = pd.read_csv(synth_path, parse_dates=["date"])
        return df[["date", "aqi"]].dropna()
    else:
        raise FileNotFoundError(
            "No AQI data found. Run generate_synthetic_aqi.py first."
        )


def load_weather(raw_dir) -> pd.DataFrame:
    """Load weather data from CSV."""
    path = raw_dir / "weather_delhi.csv"
    if not path.exists():
        raise FileNotFoundError(
            "No weather data. Run download_weather.py first."
        )
    return pd.read_csv(path, parse_dates=["date"])


def load_fires(raw_dir) -> pd.DataFrame | None:
    """Load fire data if available."""
    path = raw_dir / "fires_viirs.csv"
    if not path.exists():
        print("No fire data available. Building weather-only features.")
        return None
    df = pd.read_csv(path, parse_dates=["acq_date"])
    print(f"Loaded {len(df)} fire detections")
    return df


def compute_fire_features(
    fires_df: pd.DataFrame,
    date: pd.Timestamp,
    wind_dir: float,
) -> dict:
    """
    Compute fire-based features for a single day.

    For each distance ring, count fires that are "upwind" of Delhi
    (bearing from Delhi to fire is within UPWIND_HALF_ANGLE of wind direction).

    Args:
        fires_df: Full fire detection DataFrame.
        date: The date to compute features for.
        wind_dir: Dominant wind direction (degrees, wind blows FROM).

    Returns:
        Dict of fire feature values.
    """
    from src.config import UPWIND_HALF_ANGLE

    # Filter fires for this date
    day_fires = fires_df[fires_df["acq_date"].dt.date == date.date()]

    if day_fires.empty:
        return {
            "fires_0_200km_upwind": 0,
            "fires_200_400km_upwind": 0,
            "fires_total_upwind": 0.0,
            "fire_frp_sum_upwind": 0.0,
        }

    lats = day_fires["latitude"].values
    lons = day_fires["longitude"].values

    # Compute distances and bearings from Delhi to each fire
    dists = haversine_vectorized(DELHI_LAT, DELHI_LON, lats, lons)
    bearings = bearing_vectorized(DELHI_LAT, DELHI_LON, lats, lons)

    # Compute angular difference between wind direction and fire bearing
    ang_diffs = np.array([angular_difference(wind_dir, b) for b in bearings])

    # Upwind mask: fire is "upwind" if bearing is close to wind-from direction
    upwind_mask = ang_diffs <= UPWIND_HALF_ANGLE

    # Cosine-weighted upwind score
    upwind_weights = np.where(
        upwind_mask,
        np.cos(np.radians(ang_diffs) * (90.0 / UPWIND_HALF_ANGLE)),
        0.0,
    )

    # Distance ring binning
    ring_0_200 = (dists <= 200) & upwind_mask
    ring_200_400 = (dists > 200) & (dists <= 400) & upwind_mask

    # FRP sum from upwind fires
    frp_col = day_fires.get("frp", pd.Series(np.ones(len(day_fires))))
    frp_vals = frp_col.fillna(0).values

    return {
        "fires_0_200km_upwind": float(upwind_weights[ring_0_200].sum()),
        "fires_200_400km_upwind": float(upwind_weights[ring_200_400].sum()),
        "fires_total_upwind": float(upwind_weights.sum()),
        "fire_frp_sum_upwind": float((frp_vals * upwind_weights).sum()),
    }


def build_features(raw_dir, processed_dir) -> pd.DataFrame:
    """
    Build the complete daily feature matrix.

    Merges AQI + weather + fires, engineers features, and creates
    the target variable (tomorrow's AQI band).

    Args:
        raw_dir: Path to raw data directory.
        processed_dir: Path to save processed features.

    Returns:
        DataFrame with features and target, one row per day.
    """
    # Load data
    aqi_df = load_aqi(raw_dir)
    weather_df = load_weather(raw_dir)
    fires_df = load_fires(raw_dir)

    has_fires = fires_df is not None

    # Merge AQI and weather on date
    df = pd.merge(aqi_df, weather_df, on="date", how="inner")
    df = df.sort_values("date").reset_index(drop=True)
    print(f"Merged dataset: {len(df)} days ({df['date'].min().date()} to {df['date'].max().date()})")

    # ── Weather features ───────────────────────────────────────────────
    df["temp_range"] = df["temp_max"] - df["temp_min"]
    df["wind_from_nw"] = ((df["wind_dir_dominant"] >= 270) |
                          (df["wind_dir_dominant"] <= 45)).astype(int)

    # ── Seasonality features ───────────────────────────────────────────
    df["day_of_year"] = df["date"].dt.dayofyear
    df["month"] = df["date"].dt.month
    df["is_stubble_season"] = (
        ((df["date"].dt.month == STUBBLE_SEASON_START_MONTH) &
         (df["date"].dt.day >= STUBBLE_SEASON_START_DAY)) |
        ((df["date"].dt.month == STUBBLE_SEASON_END_MONTH) &
         (df["date"].dt.day <= STUBBLE_SEASON_END_DAY))
    ).astype(int)

    # ── AQI band ───────────────────────────────────────────────────────
    df["aqi_band"] = df["aqi"].apply(aqi_to_band)

    # ── Autoregressive features ────────────────────────────────────────
    df["aqi_today"] = df["aqi"]
    df["aqi_3day_avg"] = df["aqi"].rolling(window=3, min_periods=1).mean()
    df["aqi_7day_avg"] = df["aqi"].rolling(window=7, min_periods=1).mean()

    # ── Fire features (if available) ───────────────────────────────────
    if has_fires:
        print("Computing fire features (this may take a moment)...")
        fire_features = []
        for _, row in df.iterrows():
            ff = compute_fire_features(fires_df, row["date"], row["wind_dir_dominant"])
            fire_features.append(ff)
        fire_df = pd.DataFrame(fire_features)
        df = pd.concat([df, fire_df], axis=1)
    else:
        # No fire data: add zero-filled columns so model code works unchanged
        df["fires_0_200km_upwind"] = 0
        df["fires_200_400km_upwind"] = 0
        df["fires_total_upwind"] = 0.0
        df["fire_frp_sum_upwind"] = 0.0

    # ── Target: tomorrow's AQI band ───────────────────────────────────
    df["aqi_tomorrow"] = df["aqi"].shift(-1)
    df["aqi_band_tomorrow"] = df["aqi_tomorrow"].apply(
        lambda x: aqi_to_band(x) if pd.notna(x) else None
    )

    # Drop last row (no "tomorrow" available)
    df = df.dropna(subset=["aqi_band_tomorrow"]).reset_index(drop=True)

    # ── Save ───────────────────────────────────────────────────────────
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "features.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} feature rows to {out_path}")

    # Summary
    print(f"\nTarget distribution:")
    print(df["aqi_band_tomorrow"].value_counts().sort_index().to_string())
    print(f"\nFeature columns: {list(df.columns)}")
    print(f"Has fire data: {has_fires}")

    return df


# Feature columns used by the model (excludes date, raw aqi, target, etc.)
MODEL_FEATURES = [
    "temp_max",
    "temp_min",
    "humidity_mean",
    "wind_speed_max",
    "wind_dir_dominant",
    "temp_range",
    "wind_from_nw",
    "day_of_year",
    "month",
    "is_stubble_season",
    "aqi_today",
    "aqi_3day_avg",
    "aqi_7day_avg",
    "fires_0_200km_upwind",
    "fires_200_400km_upwind",
    "fires_total_upwind",
    "fire_frp_sum_upwind",
]


if __name__ == "__main__":
    from src.config import PROCESSED_DIR, RAW_DIR
    df = build_features(RAW_DIR, PROCESSED_DIR)
    print(f"\nSample (first 5 rows):\n{df[MODEL_FEATURES + ['aqi_band_tomorrow']].head()}")
