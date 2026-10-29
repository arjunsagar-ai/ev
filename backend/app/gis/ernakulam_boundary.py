"""
Ernakulam District Administrative Boundary & Point-in-Polygon Validator.

Loads the authoritative OpenStreetMap/Census administrative boundary for
Ernakulam District, Kerala, India and provides deterministic ray-casting
spatial containment validation.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Rejection message required across the project
ERNAKULAM_COVERAGE_MESSAGE = "This project currently supports Ernakulam district, Kerala only."

_DEFAULT_BOUNDARY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ernakulam_boundary.geojson",
)

# In-memory cached boundary representation
_CACHED_GEOJSON: Optional[Dict[str, Any]] = None
_CACHED_POLYGONS: Optional[List[List[Tuple[float, float]]]] = None
_CACHED_BBOX: Optional[Tuple[float, float, float, float]] = None  # (min_lat, max_lat, min_lon, max_lon)


def _load_boundary_data(file_path: Optional[str] = None) -> Tuple[Dict[str, Any], List[List[Tuple[float, float]]], Tuple[float, float, float, float]]:
    """Load and parse the GeoJSON boundary into list of polygon rings."""
    global _CACHED_GEOJSON, _CACHED_POLYGONS, _CACHED_BBOX

    if _CACHED_GEOJSON is not None and _CACHED_POLYGONS is not None and _CACHED_BBOX is not None and file_path is None:
        return _CACHED_GEOJSON, _CACHED_POLYGONS, _CACHED_BBOX

    path = file_path or _DEFAULT_BOUNDARY_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Ernakulam boundary file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract geometry (supports Feature or Geometry directly)
    geom = data.get("geometry", data)
    geom_type = geom.get("type")
    coords = geom.get("coordinates", [])

    polygon_rings: List[List[Tuple[float, float]]] = []

    if geom_type == "Polygon":
        # coords is list of linear rings: [ [ [lon, lat], ... ], ... ]
        if coords and len(coords) > 0:
            # We take the exterior ring (index 0)
            polygon_rings.append([(float(pt[0]), float(pt[1])) for pt in coords[0]])
    elif geom_type == "MultiPolygon":
        # coords is list of polygons: [ [ [ [lon, lat], ... ] ], ... ]
        for poly in coords:
            if poly and len(poly) > 0:
                polygon_rings.append([(float(pt[0]), float(pt[1])) for pt in poly[0]])
    else:
        raise ValueError(f"Unsupported geometry type for boundary: {geom_type}")

    # Compute bounding box across all rings
    all_lons = [pt[0] for ring in polygon_rings for pt in ring]
    all_lats = [pt[1] for ring in polygon_rings for pt in ring]
    bbox = (min(all_lats), max(all_lats), min(all_lons), max(all_lons))

    if file_path is None:
        _CACHED_GEOJSON = data
        _CACHED_POLYGONS = polygon_rings
        _CACHED_BBOX = bbox

    return data, polygon_rings, bbox


def _point_in_ring(lon: float, lat: float, ring: List[Tuple[float, float]]) -> bool:
    """Standard ray-casting algorithm for a point (lon, lat) in a 2D polygon ring."""
    n = len(ring)
    if n < 3:
        return False

    inside = False
    p1x, p1y = ring[0]
    for i in range(1, n + 1):
        p2x, p2y = ring[i % n]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    else:
                        xinters = p1x
                    if p1x == p2x or lon <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def is_point_in_ernakulam(latitude: float, longitude: float, boundary_path: Optional[str] = None) -> bool:
    """
    Check if the given (latitude, longitude) coordinate lies inside
    the geographic boundary of Ernakulam District, Kerala.

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees (e.g. ~9.98).
    longitude : float
        Longitude in decimal degrees (e.g. ~76.30).
    boundary_path : str, optional
        Custom path to boundary GeoJSON (used for testing).

    Returns
    -------
    bool
        True if the point is within Ernakulam District; False otherwise.
    """
    _, rings, (min_lat, max_lat, min_lon, max_lon) = _load_boundary_data(boundary_path)

    # Fast bounding-box check
    if not (min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon):
        return False

    # Ray-casting check against all exterior rings
    for ring in rings:
        if _point_in_ring(longitude, latitude, ring):
            return True

    return False


def validate_in_ernakulam(latitude: float, longitude: float, boundary_path: Optional[str] = None) -> None:
    """
    Validate that (latitude, longitude) is inside Ernakulam District.

    Raises
    ------
    ValueError
        If the coordinates are outside Ernakulam District.
    """
    if not is_point_in_ernakulam(latitude, longitude, boundary_path):
        raise ValueError(ERNAKULAM_COVERAGE_MESSAGE)


def get_ernakulam_boundary_geojson(boundary_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve the raw GeoJSON feature dict representing Ernakulam District boundary."""
    data, _, _ = _load_boundary_data(boundary_path)
    return data
