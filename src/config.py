"""
Configuration constants for Stubble Smoke Alert.

All geographic, AQI classification, and pipeline parameters live here
so they can be adjusted without touching model or policy code.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present (never in Lambda — uses env vars directly)
load_dotenv()

# ── Project paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_DIR = PROJECT_ROOT / "model"

# ── Delhi reference point ─────────────────────────────────────────────────
DELHI_LAT = 28.6139
DELHI_LON = 77.2090

# ── Geographic parameters ─────────────────────────────────────────────────
# Distance rings (km) for fire detection binning
DISTANCE_RINGS_KM = [0, 200, 400]

# Bounding box for fire data download (Punjab + Haryana + W UP)
# Format: south_lat, west_lon, north_lat, east_lon
FIRE_BBOX = {
    "south": 26.0,
    "north": 33.0,
    "west": 73.0,
    "east": 80.0,
}

# Wind direction tolerance (degrees): fires within ±this angle of the
# upwind direction are considered "upwind" of Delhi.
UPWIND_HALF_ANGLE = 60  # ±60° → 120° sector

# Earth radius for haversine (km)
EARTH_RADIUS_KM = 6371.0

# ── CPCB AQI band definitions ─────────────────────────────────────────────
# (upper_bound_inclusive, label)  — order matters for classification
AQI_BANDS = [
    (50, "Good"),
    (100, "Moderate"),
    (200, "Poor"),
    (300, "Very Poor"),
    (500, "Severe"),       # We merge 301-400 + 401-500 into "Severe"
]

BAND_LABELS = [b[1] for b in AQI_BANDS]  # ordered list for model output


def aqi_to_band(aqi_value: float) -> str:
    """Convert a numeric AQI value to its CPCB band label."""
    for upper, label in AQI_BANDS:
        if aqi_value <= upper:
            return label
    return "Severe"  # anything above 500


# ── Weather data parameters ───────────────────────────────────────────────
# Date range for historical data download
WEATHER_START_DATE = "2022-10-01"
WEATHER_END_DATE = "2024-12-31"

# Open-Meteo variables to fetch
OPEN_METEO_DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
    "wind_direction_10m_dominant",
]

# ── FIRMS / fire data ─────────────────────────────────────────────────────
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

# ── AWS ────────────────────────────────────────────────────────────────────
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "stubble-smoke-alert-bucket")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
API_BASE_URL = os.getenv("API_BASE_URL", "")

# ── Model parameters ──────────────────────────────────────────────────────
TRAIN_TEST_SPLIT_RATIO = 0.8  # chronological, no shuffling
RANDOM_STATE = 42

# ── Stubble burning season (for seasonality feature) ──────────────────────
STUBBLE_SEASON_START_MONTH = 10  # October
STUBBLE_SEASON_START_DAY = 1
STUBBLE_SEASON_END_MONTH = 11    # November
STUBBLE_SEASON_END_DAY = 30
