"""
Tests for geospatial utilities (haversine, bearing, upwind weight).

Uses known reference values to validate correctness.
"""

import numpy as np
import pytest

from src.geo import (
    angular_difference,
    bearing,
    bearing_vectorized,
    haversine,
    haversine_vectorized,
    upwind_weight,
)


# ── Haversine tests ───────────────────────────────────────────────────────

class TestHaversine:
    """Test haversine distance calculations against known values."""

    def test_same_point_returns_zero(self):
        assert haversine(28.6, 77.2, 28.6, 77.2) == pytest.approx(0.0, abs=0.01)

    def test_delhi_to_chandigarh(self):
        """Delhi (28.61, 77.21) → Chandigarh (30.73, 76.77) ≈ 240 km."""
        d = haversine(28.6139, 77.2090, 30.7333, 76.7794)
        assert 230 < d < 250, f"Expected ~240 km, got {d}"

    def test_delhi_to_amritsar(self):
        """Delhi → Amritsar ≈ 400 km."""
        d = haversine(28.6139, 77.2090, 31.6340, 74.8723)
        assert 380 < d < 430, f"Expected ~400 km, got {d}"

    def test_symmetry(self):
        """haversine(A, B) == haversine(B, A)."""
        d1 = haversine(28.6, 77.2, 30.7, 76.8)
        d2 = haversine(30.7, 76.8, 28.6, 77.2)
        assert d1 == pytest.approx(d2, rel=1e-9)

    def test_equator_one_degree_longitude(self):
        """One degree of longitude at the equator ≈ 111.3 km."""
        d = haversine(0.0, 0.0, 0.0, 1.0)
        assert 110 < d < 113, f"Expected ~111 km, got {d}"


# ── Bearing tests ──────────────────────────────────────────────────────────

class TestBearing:
    """Test bearing calculations."""

    def test_due_north(self):
        """Going north should be ~0°."""
        b = bearing(28.0, 77.0, 29.0, 77.0)
        assert b == pytest.approx(0.0, abs=1.0)

    def test_due_east(self):
        """Going east on equator should be ~90°."""
        b = bearing(0.0, 0.0, 0.0, 1.0)
        assert b == pytest.approx(90.0, abs=1.0)

    def test_due_south(self):
        """Going south should be ~180°."""
        b = bearing(29.0, 77.0, 28.0, 77.0)
        assert b == pytest.approx(180.0, abs=1.0)

    def test_due_west(self):
        """Going west on equator should be ~270°."""
        b = bearing(0.0, 1.0, 0.0, 0.0)
        assert b == pytest.approx(270.0, abs=1.0)

    def test_delhi_to_chandigarh_is_northwest(self):
        """Chandigarh is NW of Delhi → bearing should be 300-360°."""
        b = bearing(28.6139, 77.2090, 30.7333, 76.7794)
        assert 330 < b < 360 or 0 <= b < 10, f"Expected NW bearing, got {b}"


# ── Angular difference tests ──────────────────────────────────────────────

class TestAngularDifference:
    """Test angular difference wrapping."""

    def test_same_angle(self):
        assert angular_difference(90, 90) == pytest.approx(0.0)

    def test_opposite(self):
        assert angular_difference(0, 180) == pytest.approx(180.0)

    def test_wrap_around(self):
        """350° and 10° should be 20° apart, not 340°."""
        assert angular_difference(350, 10) == pytest.approx(20.0)

    def test_symmetry(self):
        assert angular_difference(30, 100) == pytest.approx(angular_difference(100, 30))


# ── Upwind weight tests ───────────────────────────────────────────────────

class TestUpwindWeight:
    """Test upwind weighting logic."""

    def test_directly_upwind_returns_one(self):
        """Fire exactly in the wind-from direction → weight = 1.0."""
        # Wind from 315° (NW), fire is to the NW of Delhi
        # Bearing from Delhi to fire should be ~315°
        # Using a point NW of Delhi
        w = upwind_weight(
            fire_lat=30.0, fire_lon=76.0,
            target_lat=28.6139, target_lon=77.2090,
            wind_dir_deg=315.0,
        )
        # The bearing from Delhi to (30, 76) is roughly NW
        assert w > 0.7, f"Expected high weight for upwind fire, got {w}"

    def test_downwind_returns_zero(self):
        """Fire in the opposite direction of wind → weight = 0."""
        # Wind from 315° (NW), fire is to the SE of Delhi
        w = upwind_weight(
            fire_lat=27.0, fire_lon=78.5,
            target_lat=28.6139, target_lon=77.2090,
            wind_dir_deg=315.0,
        )
        assert w == pytest.approx(0.0), f"Expected zero for downwind fire, got {w}"

    def test_weight_between_zero_and_one(self):
        """All upwind weights must be in [0, 1]."""
        for wind in range(0, 360, 30):
            for lat in np.linspace(26, 34, 5):
                for lon in np.linspace(73, 80, 5):
                    w = upwind_weight(lat, lon, 28.6, 77.2, float(wind))
                    assert 0.0 <= w <= 1.0, f"Weight {w} out of range"


# ── Vectorized tests ──────────────────────────────────────────────────────

class TestVectorized:
    """Test vectorized versions match scalar versions."""

    def test_haversine_vectorized_matches_scalar(self):
        lats = np.array([30.7333, 31.6340, 28.6139])
        lons = np.array([76.7794, 74.8723, 77.2090])
        dists = haversine_vectorized(28.6139, 77.2090, lats, lons)

        for i in range(len(lats)):
            scalar = haversine(28.6139, 77.2090, lats[i], lons[i])
            assert dists[i] == pytest.approx(scalar, rel=1e-9)

    def test_bearing_vectorized_matches_scalar(self):
        lats = np.array([30.7333, 31.6340, 0.0])
        lons = np.array([76.7794, 74.8723, 1.0])
        bearings = bearing_vectorized(28.6139, 77.2090, lats, lons)

        for i in range(len(lats)):
            scalar = bearing(28.6139, 77.2090, lats[i], lons[i])
            assert bearings[i] == pytest.approx(scalar, rel=1e-6)
