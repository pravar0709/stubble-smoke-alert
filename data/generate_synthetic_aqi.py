"""
Generate synthetic Delhi AQI data for development and demo purposes.

This produces a realistic seasonal pattern matching known Delhi AQI behaviour:
- Summer (Apr-Sep): generally Good-Moderate (40-120)
- Monsoon (Jul-Sep): cleanest air, Good (30-80)
- Post-monsoon / Stubble season (Oct-Nov): sharp spike, Poor-Severe (150-450)
- Winter (Dec-Feb): elevated, Moderate-Very Poor (100-300)

⚠️  This is SYNTHETIC data. It is clearly labeled as such everywhere.
    If you have a real AQI CSV, place it at data/raw/delhi_aqi.csv and
    the pipeline will use it instead.

Usage:
    python data/generate_synthetic_aqi.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RAW_DIR


def generate_synthetic_aqi(
    start_date: str = "2022-10-01",
    end_date: str = "2024-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a synthetic daily AQI time series for Delhi.

    The pattern is calibrated against published Delhi AQI statistics:
    - Annual mean AQI ~160 (CPCB 2023 report)
    - Oct-Nov peak days routinely exceed 300
    - Diwali spike (late Oct / early Nov) is the worst period
    - Monsoon months see the cleanest air

    Args:
        start_date: Start of the series.
        end_date: End of the series.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with date and aqi columns.
    """
    rng = np.random.RandomState(seed)
    dates = pd.date_range(start_date, end_date, freq="D")
    n = len(dates)

    # Base seasonal signal: day-of-year dependent
    day_of_year = dates.dayofyear.values.astype(float)

    # Seasonal component using known Delhi pollution calendar
    seasonal = np.zeros(n)
    for i, d in enumerate(dates):
        month, day = d.month, d.day
        if month in (7, 8, 9):
            # Monsoon: cleanest
            seasonal[i] = 50 + rng.normal(0, 15)
        elif month == 10 and day < 15:
            # Early October: transition
            seasonal[i] = 100 + rng.normal(0, 25)
        elif month == 10 and day >= 15:
            # Late October: stubble burning starts
            seasonal[i] = 200 + rng.normal(0, 50)
        elif month == 11 and day <= 15:
            # Early November: peak stubble + Diwali
            seasonal[i] = 320 + rng.normal(0, 60)
        elif month == 11 and day > 15:
            # Late November: declining but still bad
            seasonal[i] = 250 + rng.normal(0, 45)
        elif month == 12:
            # December: winter inversion
            seasonal[i] = 220 + rng.normal(0, 40)
        elif month in (1, 2):
            # Jan-Feb: cold weather trapping
            seasonal[i] = 200 + rng.normal(0, 40)
        elif month == 3:
            # March: improving
            seasonal[i] = 140 + rng.normal(0, 30)
        elif month in (4, 5, 6):
            # Pre-monsoon summer: moderate
            seasonal[i] = 100 + rng.normal(0, 25)

    # Add autocorrelation (AQI today is correlated with yesterday)
    aqi = np.zeros(n)
    aqi[0] = seasonal[0]
    for i in range(1, n):
        aqi[i] = 0.5 * seasonal[i] + 0.5 * aqi[i - 1] + rng.normal(0, 10)

    # Clamp to valid AQI range
    aqi = np.clip(aqi, 10, 500).astype(int)

    df = pd.DataFrame({
        "date": dates,
        "aqi": aqi,
        "source": "synthetic",  # Clearly labeled
    })

    # Save
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / "delhi_aqi_synthetic.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} days of synthetic AQI data -> {out_path}")
    print(f"  Mean AQI: {aqi.mean():.0f}")
    print(f"  Range: {aqi.min()} - {aqi.max()}")

    # Distribution by band
    from src.config import aqi_to_band
    bands = df["aqi"].apply(aqi_to_band)
    print(f"\n  Band distribution:\n{bands.value_counts().sort_index().to_string()}")

    return df


if __name__ == "__main__":
    df = generate_synthetic_aqi()
    print(f"\nSample:\n{df.head(10)}")
