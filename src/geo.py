"""
Geospatial utilities for Stubble Smoke Alert.

Implements haversine distance, bearing calculation, and upwind weighting
using only numpy — no heavy GIS dependencies.
"""

import numpy as np

from src.config import EARTH_RADIUS_KM, UPWIND_HALF_ANGLE


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points (in km).

    Uses the haversine formula. Inputs in decimal degrees.

    Args:
        lat1, lon1: Coordinates of point 1.
        lat2, lon2: Coordinates of point 2.

    Returns:
        Distance in kilometres.
    """
    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lat2_r, lon2_r = np.radians(lat2), np.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return float(EARTH_RADIUS_KM * c)


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial bearing from point 1 to point 2.

    Returns bearing in degrees [0, 360) where 0=North, 90=East, etc.

    Args:
        lat1, lon1: Coordinates of origin point.
        lat2, lon2: Coordinates of destination point.

    Returns:
        Bearing in degrees.
    """
    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lat2_r, lon2_r = np.radians(lat2), np.radians(lon2)

    dlon = lon2_r - lon1_r

    x = np.sin(dlon) * np.cos(lat2_r)
    y = np.cos(lat1_r) * np.sin(lat2_r) - np.sin(lat1_r) * np.cos(lat2_r) * np.cos(dlon)

    initial_bearing = np.degrees(np.arctan2(x, y))
    return float(initial_bearing % 360)


def angular_difference(angle1: float, angle2: float) -> float:
    """
    Compute the smallest angular difference between two bearings.

    Args:
        angle1, angle2: Bearings in degrees [0, 360).

    Returns:
        Absolute angular difference in degrees [0, 180].
    """
    diff = abs(angle1 - angle2) % 360
    return min(diff, 360 - diff)


def upwind_weight(
    fire_lat: float,
    fire_lon: float,
    target_lat: float,
    target_lon: float,
    wind_dir_deg: float,
    half_angle: float = UPWIND_HALF_ANGLE,
) -> float:
    """
    Calculate how 'upwind' a fire is relative to a target location.

    The wind_dir_deg is the meteorological wind direction: the direction
    the wind is blowing FROM. A fire is upwind if the bearing from the
    target to the fire is close to the wind direction.

    Returns a weight in [0, 1]:
      - 1.0 if the fire is directly upwind.
      - 0.0 if the fire is outside the upwind sector.
      - Cosine-scaled for fires within the sector (smooth falloff).

    Args:
        fire_lat, fire_lon: Fire detection coordinates.
        target_lat, target_lon: Target city coordinates (Delhi).
        wind_dir_deg: Wind direction in degrees (direction wind blows FROM).
        half_angle: Half-width of the upwind sector in degrees.

    Returns:
        Weight in [0, 1].
    """
    # Bearing from target (Delhi) to fire
    fire_bearing = bearing(target_lat, target_lon, fire_lat, fire_lon)

    # Angular difference between wind-from direction and fire bearing
    diff = angular_difference(wind_dir_deg, fire_bearing)

    if diff > half_angle:
        return 0.0

    # Cosine-scaled weight: 1.0 when aligned, decays to 0 at half_angle
    return float(np.cos(np.radians(diff) * (90.0 / half_angle)))


def haversine_vectorized(
    lat1: float, lon1: float,
    lats: np.ndarray, lons: np.ndarray,
) -> np.ndarray:
    """
    Vectorized haversine: distance from one point to many points.

    Args:
        lat1, lon1: Reference point coordinates.
        lats, lons: Arrays of target coordinates.

    Returns:
        Array of distances in km.
    """
    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lats_r, lons_r = np.radians(lats), np.radians(lons)

    dlat = lats_r - lat1_r
    dlon = lons_r - lon1_r

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lats_r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def bearing_vectorized(
    lat1: float, lon1: float,
    lats: np.ndarray, lons: np.ndarray,
) -> np.ndarray:
    """
    Vectorized bearing: bearing from one point to many points.

    Returns bearings in degrees [0, 360).
    """
    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lats_r, lons_r = np.radians(lats), np.radians(lons)

    dlon = lons_r - lon1_r

    x = np.sin(dlon) * np.cos(lats_r)
    y = np.cos(lat1_r) * np.sin(lats_r) - np.sin(lat1_r) * np.cos(lats_r) * np.cos(dlon)

    bearings = np.degrees(np.arctan2(x, y))
    return bearings % 360
