"""
Tests for the feature engineering pipeline.
"""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

from src.config import aqi_to_band, BAND_LABELS
from src.features import build_features, compute_fire_features, MODEL_FEATURES


@pytest.fixture
def temp_data_dirs(tmp_path):
    """Create temp dirs with minimal test data."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()

    # Create minimal weather CSV
    dates = pd.date_range("2024-10-01", periods=30, freq="D")
    weather = pd.DataFrame({
        "date": dates,
        "temp_max": np.random.uniform(25, 35, 30),
        "temp_min": np.random.uniform(15, 25, 30),
        "humidity_mean": np.random.uniform(40, 80, 30),
        "wind_speed_max": np.random.uniform(5, 25, 30),
        "wind_dir_dominant": np.random.uniform(270, 350, 30),
    })
    weather.to_csv(raw_dir / "weather_delhi.csv", index=False)

    # Create minimal AQI CSV (synthetic)
    aqi = pd.DataFrame({
        "date": dates,
        "aqi": np.random.randint(50, 350, 30),
        "source": "synthetic",
    })
    aqi.to_csv(raw_dir / "delhi_aqi_synthetic.csv", index=False)

    return raw_dir, processed_dir


class TestBuildFeatures:
    """Test the feature building pipeline."""

    def test_output_shape(self, temp_data_dirs):
        """Feature matrix should have expected columns and correct row count."""
        raw_dir, processed_dir = temp_data_dirs
        df = build_features(raw_dir, processed_dir)

        # Should have 29 rows (30 days minus 1 for shift)
        assert len(df) == 29

        # All model features should be present
        for feat in MODEL_FEATURES:
            assert feat in df.columns, f"Missing feature: {feat}"

        # Target should be present
        assert "aqi_band_tomorrow" in df.columns

    def test_no_nan_in_features(self, temp_data_dirs):
        """No NaN values in model features after building."""
        raw_dir, processed_dir = temp_data_dirs
        df = build_features(raw_dir, processed_dir)

        for feat in MODEL_FEATURES:
            nan_count = df[feat].isna().sum()
            assert nan_count == 0, f"Feature {feat} has {nan_count} NaN values"

    def test_target_values_are_valid_bands(self, temp_data_dirs):
        """All target values must be valid CPCB band labels."""
        raw_dir, processed_dir = temp_data_dirs
        df = build_features(raw_dir, processed_dir)

        valid_bands = set(BAND_LABELS)
        for band in df["aqi_band_tomorrow"].unique():
            assert band in valid_bands, f"Invalid band: {band}"

    def test_stubble_season_flag(self, temp_data_dirs):
        """October dates should be flagged as stubble season."""
        raw_dir, processed_dir = temp_data_dirs
        df = build_features(raw_dir, processed_dir)

        # Our test data is all in October, so is_stubble_season should be 1
        assert (df["is_stubble_season"] == 1).all()

    def test_saves_csv(self, temp_data_dirs):
        """Should save processed features to CSV."""
        raw_dir, processed_dir = temp_data_dirs
        build_features(raw_dir, processed_dir)

        assert (processed_dir / "features.csv").exists()

    def test_fire_columns_zero_without_fire_data(self, temp_data_dirs):
        """Without fire data, fire columns should be all zeros."""
        raw_dir, processed_dir = temp_data_dirs
        df = build_features(raw_dir, processed_dir)

        assert (df["fires_0_200km_upwind"] == 0).all()
        assert (df["fires_200_400km_upwind"] == 0).all()
        assert (df["fires_total_upwind"] == 0).all()


class TestComputeFireFeatures:
    """Test fire feature computation."""

    def test_empty_fires_returns_zeros(self):
        """No fires on a given date should return all zeros."""
        fires_df = pd.DataFrame({
            "latitude": [30.0],
            "longitude": [76.0],
            "acq_date": [pd.Timestamp("2024-09-01")],
            "frp": [10.0],
        })
        result = compute_fire_features(
            fires_df, pd.Timestamp("2024-10-01"), 315.0
        )
        assert result["fires_total_upwind"] == 0.0
        assert result["fire_frp_sum_upwind"] == 0.0

    def test_upwind_fire_detected(self):
        """A fire upwind of Delhi should produce non-zero weight."""
        # Fire NW of Delhi, wind from NW
        fires_df = pd.DataFrame({
            "latitude": [30.5],
            "longitude": [76.0],
            "acq_date": [pd.Timestamp("2024-10-15")],
            "frp": [25.0],
        })
        result = compute_fire_features(
            fires_df, pd.Timestamp("2024-10-15"), 315.0
        )
        assert result["fires_total_upwind"] > 0


class TestAqiBand:
    """Test AQI to band conversion."""

    def test_good(self):
        assert aqi_to_band(30) == "Good"

    def test_moderate(self):
        assert aqi_to_band(75) == "Moderate"

    def test_poor(self):
        assert aqi_to_band(150) == "Poor"

    def test_very_poor(self):
        assert aqi_to_band(250) == "Very Poor"

    def test_severe(self):
        assert aqi_to_band(350) == "Severe"

    def test_above_500(self):
        assert aqi_to_band(600) == "Severe"

    def test_boundary_50(self):
        assert aqi_to_band(50) == "Good"

    def test_boundary_51(self):
        assert aqi_to_band(51) == "Moderate"
