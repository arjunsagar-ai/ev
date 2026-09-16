"""
Spatial indexing and GPS coordinate snapping.

Provides:
  • GPS coordinate validation
  • Nearest-road-node lookup (using Haversine distance)
  • GPS → road-network snapping service

The spatial-index logic is deliberately isolated so the underlying search
strategy can be replaced (e.g. with a KD-Tree) without touching routing
or graph code.
"""
import logging
import math
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.graph.weighted_graph import WeightedGraph
from app.utils.distance import haversine_distance

logger = logging.getLogger(__name__)


# ───────────────────── coordinate validation ─────────────────────────────

def validate_coordinates(latitude: Any, longitude: Any) -> None:
    """
    Validate that *latitude* and *longitude* are finite numeric values
    within the legal WGS-84 range.

    Raises
    ------
    TypeError
        If either value is not numeric (int / float).
    ValueError
        If either value is NaN, infinite, or out of range.
    """
    for name, val in [("latitude", latitude), ("longitude", longitude)]:
        if not isinstance(val, (int, float)):
            raise TypeError(f"{name} must be numeric, got {type(val).__name__}.")
        if math.isnan(val):
            raise ValueError(f"{name} must not be NaN.")
        if math.isinf(val):
            raise ValueError(f"{name} must not be infinite.")

    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(
            f"latitude must be between -90 and 90 degrees, got {latitude}."
        )
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(
            f"longitude must be between -180 and 180 degrees, got {longitude}."
        )


# ───────────────────── nearest-node lookup ───────────────────────────────

def find_nearest_road_node(
    graph: WeightedGraph,
    latitude: float,
    longitude: float,
) -> Dict[str, Any]:
    """
    Find the node in *graph* whose coordinates are closest (by Haversine
    great-circle distance) to the given GPS point.

    Parameters
    ----------
    graph : WeightedGraph
        Road-network graph with lat/lon on every node.
    latitude, longitude : float
        Query point in decimal degrees.

    Returns
    -------
    dict with keys:
        node_id     – identifier of the nearest node
        latitude    – latitude of the nearest node
        longitude   – longitude of the nearest node
        distance_m  – Haversine distance in **meters**

    Raises
    ------
    ValueError
        If the graph contains no nodes with coordinates.
    """
    validate_coordinates(latitude, longitude)

    best_node: Optional[Any] = None
    best_dist: float = float("inf")
    best_lat: float = 0.0
    best_lon: float = 0.0

    for nid in graph.nodes():
        coords = graph.get_coordinates(nid)
        if coords is None:
            continue
        nlat, nlon = coords
        dist_m = haversine_distance(latitude, longitude, nlat, nlon, unit="m")
        if dist_m < best_dist:
            best_dist = dist_m
            best_node = nid
            best_lat = nlat
            best_lon = nlon

    if best_node is None:
        raise ValueError("Graph contains no nodes with coordinates.")

    return {
        "node_id": best_node,
        "latitude": best_lat,
        "longitude": best_lon,
        "distance_m": round(best_dist, 2),
    }


# ─────────────────── snapping service ────────────────────────────────────

def snap_coordinates_to_road(
    graph: WeightedGraph,
    latitude: float,
    longitude: float,
    max_distance_m: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Snap a raw GPS point to the nearest node in the road network.

    Parameters
    ----------
    graph : WeightedGraph
        Road-network graph with lat/lon on every node.
    latitude, longitude : float
        Raw GPS coordinates from the user's device.
    max_distance_m : float, optional
        Maximum acceptable snap distance in meters.
        Defaults to ``settings.MAX_SNAP_DISTANCE_M``.

    Returns
    -------
    dict:
        input           – {latitude, longitude}
        nearest_node    – {id, latitude, longitude}
        distance_to_road_m – Haversine distance in meters

    Raises
    ------
    TypeError / ValueError
        If coordinates are invalid (see ``validate_coordinates``).
    ValueError
        If the nearest road node exceeds *max_distance_m*.
    """
    # Validate first
    validate_coordinates(latitude, longitude)

    nearest = find_nearest_road_node(graph, latitude, longitude)

    limit = max_distance_m if max_distance_m is not None else settings.MAX_SNAP_DISTANCE_M
    if nearest["distance_m"] > limit:
        raise ValueError(
            f"Nearest road node is {nearest['distance_m']:.0f} m away, "
            f"exceeding the maximum snap distance of {limit:.0f} m."
        )

    logger.info(
        "Snapped GPS to road node %s (%.1f m away)",
        nearest["node_id"], nearest["distance_m"],
    )

    return {
        "input": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "nearest_node": {
            "id": nearest["node_id"],
            "latitude": nearest["latitude"],
            "longitude": nearest["longitude"],
        },
        "distance_to_road_m": nearest["distance_m"],
    }
