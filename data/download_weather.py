"""
Download historical weather data from Open-Meteo for Delhi.

Open-Meteo provides free access to ERA5 reanalysis data without an API key.
We fetch daily wind, temperature, and humidity data needed for the model.

Usage:
    python data/download_weather.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import requests

# Add project root to path so we can import src.config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import (
    DELHI_LAT,
    DELHI_LON,
    OPEN_METEO_DAILY_VARS,
    RAW_DIR,
    WEATHER_END_DATE,
    WEATHER_START_DATE,
)


def download_weather() -> pd.DataFrame:
    """
    Fetch historical daily weather for Delhi from Open-Meteo.

    Returns:
        DataFrame with columns: date, temp_max, temp_min, humidity_mean,
        wind_speed_max, wind_dir_dominant.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": DELHI_LAT,
        "longitude": DELHI_LON,
        "start_date": WEATHER_START_DATE,
        "end_date": WEATHER_END_DATE,
        "daily": ",".join(OPEN_METEO_DAILY_VARS),
        "timezone": "Asia/Kolkata",
    }

    print(f"Fetching weather data from Open-Meteo ({WEATHER_START_DATE} to {WEATHER_END_DATE})...")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = data["daily"]
    df = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "temp_max": daily["temperature_2m_max"],
        "temp_min": daily["temperature_2m_min"],
        "humidity_mean": daily["relative_humidity_2m_mean"],
        "wind_speed_max": daily["wind_speed_10m_max"],
        "wind_dir_dominant": daily["wind_direction_10m_dominant"],
    })

    # Save to CSV
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / "weather_delhi.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} days of weather data to {out_path}")

    return df


if __name__ == "__main__":
    df = download_weather()
    print(f"\nSample:\n{df.head()}")
    print(f"\nDate range: {df['date'].min()} to {df['date'].max()}")
    print(f"Missing values:\n{df.isnull().sum()}")
