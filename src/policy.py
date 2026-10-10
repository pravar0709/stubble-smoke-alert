"""
Rule-based policy layer for Stubble Smoke Alert.

Maps predicted AQI bands to bounded school actions.
This module is INDEPENDENT of the ML model and can be audited separately.

Each output includes:
- band: The predicted AQI band
- action: Specific, bounded instruction for school administrators
- severity: Numeric severity (1-5) for UI color coding
- details: Additional context for the action
"""


# Policy definitions: band -> (action, severity, details)
# severity: 1=Good, 2=Moderate, 3=Poor, 4=Very Poor, 5=Severe
POLICY_TABLE = {
    "Good": {
        "action": "Normal outdoor activity. All sports and assemblies proceed as scheduled.",
        "severity": 1,
        "details": "Air quality is satisfactory. No restrictions needed.",
        "color": "#4caf50",  # Green
    },
    "Moderate": {
        "action": "Normal outdoor activity. Monitor sensitive students.",
        "severity": 2,
        "details": "Air quality is acceptable. Unusually sensitive students may experience mild symptoms.",
        "color": "#ffeb3b",  # Yellow
    },
    "Poor": {
        "action": "Shorten outdoor activity to 30 minutes. Sensitive students should wear masks.",
        "severity": 3,
        "details": "Members of sensitive groups (asthma, respiratory conditions) may experience health effects. Limit prolonged outdoor exertion.",
        "color": "#ff9800",  # Orange
    },
    "Very Poor": {
        "action": "Move PE and assembly indoors. Keep windows and doors closed. Run air purifiers if available.",
        "severity": 4,
        "details": "Health effects likely for all students with prolonged exposure. Avoid all outdoor physical activity.",
        "color": "#f44336",  # Red
    },
    "Severe": {
        "action": "Cancel all outdoor activities. Send advisory to parents. Consider early dismissal if air purifiers are not available.",
        "severity": 5,
        "details": "Health emergency conditions. All students affected. Outdoor exposure is hazardous.",
        "color": "#9c27b0",  # Purple
    },
}


def get_school_action(band: str) -> dict:
    """
    Get the recommended school action for a predicted AQI band.

    Args:
        band: Predicted AQI band (Good, Moderate, Poor, Very Poor, Severe).

    Returns:
        Dict with keys: band, action, severity, details, color.

    Raises:
        ValueError: If band is not a recognized CPCB category.
    """
    if band not in POLICY_TABLE:
        raise ValueError(
            f"Unknown AQI band: '{band}'. "
            f"Valid bands: {list(POLICY_TABLE.keys())}"
        )

    policy = POLICY_TABLE[band]
    return {
        "band": band,
        "action": policy["action"],
        "severity": policy["severity"],
        "details": policy["details"],
        "color": policy["color"],
    }


def build_reason(
    band: str,
    wind_dir: float = None,
    wind_speed: float = None,
    fire_count: float = None,
    aqi_today: int = None,
) -> str:
    """
    Build a plain-language reason for the forecast.

    This explains WHY the predicted band was reached, making the
    forecast actionable and understandable for non-technical users.

    Args:
        band: Predicted AQI band.
        wind_dir: Dominant wind direction in degrees.
        wind_speed: Wind speed in km/h.
        fire_count: Number of upwind fire detections.
        aqi_today: Today's AQI value.

    Returns:
        Human-readable reason string.
    """
    parts = []

    # Wind direction description
    if wind_dir is not None:
        direction = _degrees_to_compass(wind_dir)
        if wind_speed is not None:
            parts.append(f"{direction} winds at {wind_speed:.0f} km/h")
        else:
            parts.append(f"{direction} winds")

    # Fire context
    if fire_count is not None and fire_count > 0:
        parts.append(f"{int(fire_count)} upwind fire detections carrying smoke toward Delhi")
    elif fire_count is not None and fire_count == 0:
        parts.append("no significant upwind fire activity detected")

    # Today's AQI context
    if aqi_today is not None:
        if band in ("Very Poor", "Severe") and aqi_today > 200:
            parts.append(f"already elevated AQI of {aqi_today} today")
        elif band in ("Good", "Moderate") and aqi_today < 100:
            parts.append(f"current AQI of {aqi_today} is favorable")

    if not parts:
        return f"Predicted AQI band: {band}."

    reason = "; ".join(parts) + "."
    return reason[0].upper() + reason[1:]


def _degrees_to_compass(degrees: float) -> str:
    """Convert wind direction in degrees to compass label."""
    directions = [
        "northerly", "north-northeasterly", "northeasterly", "east-northeasterly",
        "easterly", "east-southeasterly", "southeasterly", "south-southeasterly",
        "southerly", "south-southwesterly", "southwesterly", "west-southwesterly",
        "westerly", "west-northwesterly", "northwesterly", "north-northwesterly",
    ]
    idx = int((degrees + 11.25) / 22.5) % 16
    return directions[idx]


def get_all_policies() -> dict:
    """Return the complete policy table (for documentation/testing)."""
    return {
        band: get_school_action(band)
        for band in POLICY_TABLE
    }
