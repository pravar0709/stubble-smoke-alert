"""
Tests for the rule-based policy layer.

The policy layer is independent of the ML model and must be
thoroughly tested since it drives school-level decisions.
"""

import pytest

from src.policy import (
    POLICY_TABLE,
    _degrees_to_compass,
    build_reason,
    get_all_policies,
    get_school_action,
)
from src.config import BAND_LABELS


class TestGetSchoolAction:
    """Test the policy mapping function."""

    def test_all_bands_have_policies(self):
        """Every CPCB band must have a defined policy."""
        for band in BAND_LABELS:
            result = get_school_action(band)
            assert result is not None
            assert result["band"] == band

    def test_all_bands_have_required_keys(self):
        """Each policy must include all required keys."""
        required_keys = {"band", "action", "severity", "details", "color"}
        for band in BAND_LABELS:
            result = get_school_action(band)
            assert set(result.keys()) == required_keys

    def test_severity_increases_with_band(self):
        """Severity must increase monotonically from Good to Severe."""
        severities = [get_school_action(b)["severity"] for b in BAND_LABELS]
        assert severities == sorted(severities)
        assert severities[0] == 1
        assert severities[-1] == 5

    def test_invalid_band_raises_error(self):
        """Unknown band names must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown AQI band"):
            get_school_action("Excellent")

    def test_good_allows_outdoor(self):
        """Good AQI should allow normal outdoor activity."""
        result = get_school_action("Good")
        assert "outdoor" in result["action"].lower()
        assert "normal" in result["action"].lower()

    def test_severe_cancels_outdoor(self):
        """Severe AQI must cancel outdoor activities."""
        result = get_school_action("Severe")
        assert "cancel" in result["action"].lower()
        assert "parent" in result["action"].lower()

    def test_poor_mentions_masks(self):
        """Poor AQI should mention masks for sensitive students."""
        result = get_school_action("Poor")
        assert "mask" in result["action"].lower()

    def test_very_poor_moves_indoors(self):
        """Very Poor AQI should move activities indoors."""
        result = get_school_action("Very Poor")
        assert "indoor" in result["action"].lower()
        assert "window" in result["action"].lower()

    def test_colors_are_hex(self):
        """All colors must be valid hex color codes."""
        for band in BAND_LABELS:
            color = get_school_action(band)["color"]
            assert color.startswith("#")
            assert len(color) == 7


class TestBuildReason:
    """Test the reason builder."""

    def test_with_all_context(self):
        """Reason should include wind, fires, and AQI context."""
        reason = build_reason(
            "Very Poor",
            wind_dir=315,
            wind_speed=18,
            fire_count=142,
            aqi_today=250,
        )
        assert "wind" in reason.lower()
        assert "fire" in reason.lower()
        assert "250" in reason

    def test_no_fires_mentions_no_activity(self):
        """Zero fire count should mention no fire activity."""
        reason = build_reason("Good", fire_count=0)
        assert "no significant" in reason.lower()

    def test_with_wind_only(self):
        """Should work with just wind context."""
        reason = build_reason("Moderate", wind_dir=270, wind_speed=12)
        assert "wind" in reason.lower()
        assert "12" in reason

    def test_empty_context(self):
        """With no context, should still return a valid string."""
        reason = build_reason("Poor")
        assert len(reason) > 0
        assert "Poor" in reason

    def test_starts_with_capital(self):
        """Reason should start with a capital letter."""
        reason = build_reason("Severe", wind_dir=315, fire_count=50)
        assert reason[0].isupper()


class TestDegreesToCompass:
    """Test wind direction conversion."""

    def test_north(self):
        assert "north" in _degrees_to_compass(0).lower()

    def test_east(self):
        assert "east" in _degrees_to_compass(90).lower()

    def test_south(self):
        assert "south" in _degrees_to_compass(180).lower()

    def test_west(self):
        assert "west" in _degrees_to_compass(270).lower()

    def test_northwest(self):
        assert "northwest" in _degrees_to_compass(315).lower()


class TestGetAllPolicies:
    """Test the policy table retrieval."""

    def test_returns_all_bands(self):
        policies = get_all_policies()
        assert set(policies.keys()) == set(BAND_LABELS)

    def test_all_have_actions(self):
        policies = get_all_policies()
        for band, policy in policies.items():
            assert len(policy["action"]) > 10
