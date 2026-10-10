"""
Download active fire detections from NASA FIRMS (VIIRS).

Requires a free MAP_KEY from https://firms.modaps.eosdis.nasa.gov/api/
Set FIRMS_MAP_KEY in your .env file.

If no key is available, this script exits gracefully and the pipeline
falls back to a weather-only model.

Usage:
    python data/download_fires.py
"""

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import FIRE_BBOX, FIRMS_MAP_KEY, RAW_DIR


# FIRMS API endpoint for area queries
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# We query in chunks (FIRMS allows max 10 days per request for area queries)
CHUNK_DAYS = 10


def download_fires(
    start_date: str = "2022-10-01",
    end_date: str = "2024-12-31",
) -> pd.DataFrame | None:
    """
    Download VIIRS fire detections for the Punjab-Haryana-UP region.

    Args:
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        DataFrame of fire detections, or None if no MAP_KEY.
    """
    if not FIRMS_MAP_KEY:
        print("[WARNING] No FIRMS_MAP_KEY set. Skipping fire data download.")
        print("   Set FIRMS_MAP_KEY in .env to enable fire-based features.")
        print("   Get a free key at: https://firms.modaps.eosdis.nasa.gov/api/")
        return None

    bbox = f"{FIRE_BBOX['west']},{FIRE_BBOX['south']},{FIRE_BBOX['east']},{FIRE_BBOX['north']}"
    all_fires = []

    date_range = pd.date_range(start_date, end_date, freq="D")
    chunks = [date_range[i:i + CHUNK_DAYS] for i in range(0, len(date_range), CHUNK_DAYS)]

    print(f"Downloading VIIRS fire data ({start_date} to {end_date})...")
    print(f"Bounding box: {bbox}")
    print(f"Total chunks: {len(chunks)}")

    for idx, chunk in enumerate(chunks):
        chunk_start = chunk[0].strftime("%Y-%m-%d")
        n_days = len(chunk)

        url = f"{FIRMS_BASE_URL}/{FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/{bbox}/{n_days}/{chunk_start}"

        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and resp.text.strip():
                chunk_df = pd.read_csv(StringIO(resp.text))
                if not chunk_df.empty:
                    all_fires.append(chunk_df)
                    if (idx + 1) % 10 == 0:
                        print(f"  Chunk {idx + 1}/{len(chunks)}: {len(chunk_df)} detections")
            elif resp.status_code == 400:
                # Likely no data for this period (e.g., future dates)
                pass
            else:
                print(f"  [WARN] Chunk {idx + 1}: HTTP {resp.status_code}")
        except requests.RequestException as e:
            print(f"  [WARN] Chunk {idx + 1} failed: {e}")
            continue

    if not all_fires:
        print("No fire data retrieved. Will use weather-only model.")
        return None

    df = pd.concat(all_fires, ignore_index=True)

    # Standardize columns
    if "acq_date" in df.columns:
        df["acq_date"] = pd.to_datetime(df["acq_date"])

    # Keep relevant columns only
    keep_cols = ["latitude", "longitude", "acq_date", "bright_ti4", "confidence", "frp"]
    available_cols = [c for c in keep_cols if c in df.columns]
    df = df[available_cols]

    # Save
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / "fires_viirs.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {len(df)} fire detections to {out_path}")

    return df


if __name__ == "__main__":
    df = download_fires()
    if df is not None:
        print(f"\nSample:\n{df.head()}")
        print(f"\nDate range: {df['acq_date'].min()} to {df['acq_date'].max()}")
