"""Geodesic distance calculation utilities."""
import math
from typing import Literal

from app.core.config import settings


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    unit: Literal["km", "m"] = "km"
) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula.

    Parameters:
        lat1 (float): Latitude of the first point in decimal degrees.
        lon1 (float): Longitude of the first point in decimal degrees.
        lat2 (float): Latitude of the second point in decimal degrees.
        lon2 (float): Longitude of the second point in decimal degrees.
        unit (str): Unit of distance to return: 'km' for kilometers (default)
                    or 'm' for meters.

    Returns:
        float: Great-circle distance between the two points in the requested unit.

    Raises:
        ValueError: If latitudes are outside [-90, 90] or longitudes outside [-180, 180],
                    or if an invalid unit is specified.
    """
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        raise ValueError(f"Latitude must be between -90 and 90 degrees. Got {lat1}, {lat2}.")
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        raise ValueError(f"Longitude must be between -180 and 180 degrees. Got {lon1}, {lon2}.")

    # Identical coordinates check
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clamp to avoid floating point precision issues outside [0, 1]
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    if unit == "km":
        return settings.EARTH_RADIUS_KM * c
    elif unit == "m":
        return settings.EARTH_RADIUS_METERS * c
    else:
        raise ValueError(f"Invalid unit '{unit}'. Supported units are 'km' and 'm'.")
