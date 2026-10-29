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

def _get_spatial_arrays(graph: WeightedGraph):
    """Retrieve or build cached numpy arrays for fast vectorized nearest-neighbor lookup."""
    cached = getattr(graph, "_spatial_index_cache", None)
    if cached is not None:
        return cached

    import numpy as np

    nodes = []
    coords_list = []
    for nid in graph.nodes():
        c = graph.get_coordinates(nid)
        if c is not None:
            nodes.append(nid)
            coords_list.append(c)

    if not coords_list:
        res = (np.empty((0, 2), dtype=np.float64), [], None)
        setattr(graph, "_spatial_index_cache", res)
        return res

    coords_arr = np.array(coords_list, dtype=np.float64)
    comp_map = getattr(graph, "_component_map", None)
    comp_arr = None
    if comp_map is not None:
        comp_arr = np.array([comp_map.get(n, -1) for n in nodes], dtype=np.int32)

    res = (coords_arr, nodes, comp_arr)
    setattr(graph, "_spatial_index_cache", res)
    return res


def find_nearest_road_node(
    graph: WeightedGraph,
    latitude: float,
    longitude: float,
    require_main_component: bool = False,
    prefer_connected: bool = True,
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
    require_main_component : bool
        If True, restricts search to nodes belonging to the main connected component.

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

    # Fast path: Vectorized lookup if numpy is available and graph has multiple nodes
    try:
        import numpy as np

        coords_arr, nodes, comp_arr = _get_spatial_arrays(graph)
        if len(nodes) > 100:
            mask = None
            if require_main_component and comp_arr is not None:
                mask = (comp_arr == 0)
                if not np.any(mask):
                    mask = None

            active_coords = coords_arr[mask] if mask is not None else coords_arr
            active_nodes = [nodes[i] for i in np.where(mask)[0]] if mask is not None else nodes

            if len(active_nodes) > 0:
                cos_lat = math.cos(math.radians(latitude))
                dlat = (active_coords[:, 0] - latitude) * 111000.0
                dlon = (active_coords[:, 1] - longitude) * (111000.0 * cos_lat)
                dist_sq = dlat**2 + dlon**2

                top_k = min(20, len(active_nodes))
                closest_indices = np.argpartition(dist_sq, top_k)[:top_k]

                best_node = None
                best_dist = float("inf")
                best_lat = 0.0
                best_lon = 0.0

                # Candidates in main component (comp 0)
                main_node = None
                main_dist = float("inf")
                main_lat = 0.0
                main_lon = 0.0

                for idx in closest_indices:
                    nlat, nlon = active_coords[idx]
                    d_m = haversine_distance(latitude, longitude, nlat, nlon, unit="m")
                    if d_m < best_dist:
                        best_dist = d_m
                        best_node = active_nodes[idx]
                        best_lat = nlat
                        best_lon = nlon

                    if comp_arr is not None and comp_arr[idx] == 0:
                        if d_m < main_dist:
                            main_dist = d_m
                            main_node = active_nodes[idx]
                            main_lat = nlat
                            main_lon = nlon

                # If prefer_connected and a main component node is reasonably close, prefer it
                if prefer_connected and main_node is not None and not require_main_component:
                    if main_dist <= min(best_dist + 500.0, settings.MAX_SNAP_DISTANCE_M):
                        best_node = main_node
                        best_dist = main_dist
                        best_lat = main_lat
                        best_lon = main_lon

                if best_node is not None:
                    return {
                        "node_id": best_node,
                        "latitude": best_lat,
                        "longitude": best_lon,
                        "distance_m": round(best_dist, 2),
                    }
    except Exception:
        pass

    # Fallback linear scan
    best_node: Optional[Any] = None
    best_dist: float = float("inf")
    best_lat: float = 0.0
    best_lon: float = 0.0

    comp_map = getattr(graph, "_component_map", None)

    for nid in graph.nodes():
        if require_main_component and comp_map is not None:
            if comp_map.get(nid, -1) != 0:
                continue
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

    # If the nearest node is in an isolated component, prefer the main road network component
    comp_map = getattr(graph, "_component_map", None)
    if comp_map is not None and graph.num_nodes() > 500:
        node_comp = comp_map.get(nearest["node_id"], -1)
        if node_comp != 0:
            try:
                main_nearest = find_nearest_road_node(
                    graph, latitude, longitude, require_main_component=True
                )
                if main_nearest["distance_m"] <= limit:
                    nearest = main_nearest
            except Exception:
                pass

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
