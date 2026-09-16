"""
OpenStreetMap Road-Network Loader.

Downloads road-network data via the Overpass API, converts it into our
WeightedGraph representation, and manages a local file cache so repeated
starts do not re-download the same area.

Data source flow
────────────────
1. Check local cache  →  hit  →  deserialise cached JSON  →  build graph
2. Cache miss          →  query Overpass API  →  save response to cache  →  build graph
3. Network failure     →  load cache if stale copy exists  →  else use sample network
"""
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.gis.models import RoadNetworkMetadata
from app.graph.weighted_graph import WeightedGraph
from app.utils.distance import haversine_distance

logger = logging.getLogger(__name__)


# ───────────────────────── cache helpers ──────────────────────────────────

def _bbox_cache_key(north: float, south: float, east: float, west: float) -> str:
    """Return a deterministic filename-safe cache key for a bounding box."""
    raw = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"osm_{digest}.json"


def save_cached_network(
    cache_path: str,
    osm_data: Dict[str, Any],
) -> None:
    """Persist raw Overpass JSON to a local file."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as fh:
        json.dump(osm_data, fh)
    logger.info("Saved OSM cache → %s", cache_path)


def load_cached_network(cache_path: str) -> Optional[Dict[str, Any]]:
    """Load previously cached Overpass JSON.  Returns None if absent."""
    if not os.path.isfile(cache_path):
        return None
    with open(cache_path) as fh:
        data = json.load(fh)
    logger.info("Loaded OSM data from cache → %s", cache_path)
    return data


# ───────────────────────── Overpass query ─────────────────────────────────

def _build_overpass_query(
    north: float, south: float, east: float, west: float,
    highway_types: Optional[List[str]] = None,
) -> str:
    """Build an Overpass QL query for road ways inside a bounding box."""
    types = highway_types or settings.OSM_HIGHWAY_TYPES
    type_filter = "|".join(types)
    bbox = f"{south},{west},{north},{east}"
    return (
        f"[out:json][timeout:60];\n"
        f"(\n"
        f'  way["highway"~"^({type_filter})$"]({bbox});\n'
        f");\n"
        f"out body;\n"
        f">;\n"
        f"out skel qt;\n"
    )


def _download_osm_data(
    north: float, south: float, east: float, west: float,
    highway_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Query the Overpass API and return the raw JSON response."""
    import requests  # deferred import — only used for live downloads

    query = _build_overpass_query(north, south, east, west, highway_types)
    logger.info("Querying Overpass API for bbox [%.4f,%.4f,%.4f,%.4f] …",
                south, west, north, east)
    resp = requests.post(
        settings.OVERPASS_API_URL,
        data={"data": query},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()


# ───────────────────────── graph builder ──────────────────────────────────

def _build_graph_from_osm(osm_data: Dict[str, Any]) -> WeightedGraph:
    """
    Convert raw Overpass JSON into our WeightedGraph.

    Elements are either *nodes* (with lat/lon) or *ways* (with an ordered
    list of node refs).  We create a graph node for every referenced OSM
    node and an undirected edge for every consecutive node pair in every way.
    """
    graph = WeightedGraph(directed=False)
    elements = osm_data.get("elements", [])

    # First pass: collect node coordinates
    node_coords: Dict[int, Tuple[float, float]] = {}
    for el in elements:
        if el.get("type") == "node":
            nid = el["id"]
            node_coords[nid] = (el["lat"], el["lon"])

    # Second pass: process ways → edges
    for el in elements:
        if el.get("type") != "way":
            continue
        refs: List[int] = el.get("nodes", [])
        tags = el.get("tags", {})
        road_type = tags.get("highway", "unknown")
        road_name = tags.get("name", "")

        for i in range(len(refs) - 1):
            u, v = refs[i], refs[i + 1]
            if u not in node_coords or v not in node_coords:
                continue

            lat_u, lon_u = node_coords[u]
            lat_v, lon_v = node_coords[v]

            # Ensure both nodes exist with coords
            if not graph.has_node(u):
                graph.add_node(u, lat=lat_u, lon=lon_u, road_type=road_type)
            if not graph.has_node(v):
                graph.add_node(v, lat=lat_v, lon=lon_v, road_type=road_type)

            # Edge weight = Haversine distance in km
            dist_km = haversine_distance(lat_u, lon_u, lat_v, lon_v, unit="km")
            if not graph.has_edge(u, v):
                graph.add_edge(
                    u, v,
                    weight=dist_km,
                    road_type=road_type,
                    road_name=road_name,
                )

    return graph


# ───────────────────── sample / fallback network ─────────────────────────

def build_sample_road_network() -> Tuple[WeightedGraph, str]:
    """
    Build a deterministic sample road network for offline testing.

    The sample models a small 15-node grid-like town layout with realistic
    coordinates near latitude 10.0°N, longitude 76.3°E (a generic location;
    NOT hardcoded to any specific city).  It includes:
      • 15 intersection nodes with fixed lat/lon
      • 20 road edges with geographic Haversine distances
      • Multiple alternative routes between any two points
    """
    graph = WeightedGraph(directed=False)

    # ── nodes: 5 × 3 grid-like layout ──
    nodes = {
        "N01": (10.000, 76.300),
        "N02": (10.000, 76.305),
        "N03": (10.000, 76.310),
        "N04": (10.000, 76.315),
        "N05": (10.000, 76.320),
        "N06": (10.003, 76.300),
        "N07": (10.003, 76.305),
        "N08": (10.003, 76.310),
        "N09": (10.003, 76.315),
        "N10": (10.003, 76.320),
        "N11": (10.006, 76.300),
        "N12": (10.006, 76.305),
        "N13": (10.006, 76.310),
        "N14": (10.006, 76.315),
        "N15": (10.006, 76.320),
    }

    for nid, (lat, lon) in nodes.items():
        graph.add_node(nid, lat=lat, lon=lon, road_type="residential")

    # ── edges: horizontal, vertical, and a couple of diagonals ──
    edges = [
        # Row 1 horizontal
        ("N01", "N02"), ("N02", "N03"), ("N03", "N04"), ("N04", "N05"),
        # Row 2 horizontal
        ("N06", "N07"), ("N07", "N08"), ("N08", "N09"), ("N09", "N10"),
        # Row 3 horizontal
        ("N11", "N12"), ("N12", "N13"), ("N13", "N14"), ("N14", "N15"),
        # Verticals
        ("N01", "N06"), ("N03", "N08"), ("N05", "N10"),
        ("N06", "N11"), ("N08", "N13"), ("N10", "N15"),
        # Diagonals (alternative routes)
        ("N02", "N07"), ("N09", "N14"),
    ]

    for u, v in edges:
        graph.add_edge(u, v)  # weight auto-computed from Haversine

    return graph, "sample"


# ──────────────────────── public API ─────────────────────────────────────

def load_osm_network(
    north: float,
    south: float,
    east: float,
    west: float,
    *,
    cache_dir: Optional[str] = None,
    highway_types: Optional[List[str]] = None,
    force_download: bool = False,
) -> Tuple[WeightedGraph, RoadNetworkMetadata]:
    """
    Load a road network for the given bounding box.

    Resolution order:
      1. Local cache (unless *force_download* is True).
      2. Live Overpass API download → save to cache.
      3. Fallback to a built-in sample network (no internet required).

    Parameters
    ----------
    north, south, east, west : float
        Geographic bounding box in decimal degrees.
    cache_dir : str, optional
        Override for the cache directory.  Defaults to ``settings.OSM_CACHE_DIR``.
    highway_types : list[str], optional
        Road types to include (overrides ``settings.OSM_HIGHWAY_TYPES``).
    force_download : bool
        When True, skip cache and re-download from Overpass.

    Returns
    -------
    (WeightedGraph, RoadNetworkMetadata)
    """
    if south >= north:
        raise ValueError(f"south ({south}) must be less than north ({north}).")
    if west >= east:
        raise ValueError(f"west ({west}) must be less than east ({east}).")

    cdir = cache_dir or settings.OSM_CACHE_DIR
    cache_key = _bbox_cache_key(north, south, east, west)
    cache_path = os.path.join(cdir, cache_key)
    start = time.perf_counter()
    data_source = "osm"

    osm_data: Optional[Dict[str, Any]] = None

    # 1. Try local cache
    if not force_download:
        osm_data = load_cached_network(cache_path)
        if osm_data is not None:
            data_source = "cache"

    # 2. Try live download
    if osm_data is None:
        try:
            osm_data = _download_osm_data(north, south, east, west, highway_types)
            save_cached_network(cache_path, osm_data)
            data_source = "osm"
        except Exception as exc:
            logger.warning("Overpass download failed: %s", exc)
            # Try stale cache
            osm_data = load_cached_network(cache_path)
            if osm_data is not None:
                data_source = "cache"

    # 3. Fallback to sample network
    if osm_data is None:
        logger.warning("Using built-in sample road network (offline fallback).")
        graph, data_source = build_sample_road_network()
        elapsed = time.perf_counter() - start
        meta = RoadNetworkMetadata(
            data_source=data_source,
            num_nodes=graph.num_nodes(),
            num_edges=graph.num_edges(),
            bbox={"north": north, "south": south, "east": east, "west": west},
            load_time_seconds=round(elapsed, 4),
        )
        logger.info(
            "Road network ready: %d nodes, %d edges [%s] in %.3f s",
            meta.num_nodes, meta.num_edges, data_source, elapsed,
        )
        return graph, meta

    # Build graph from the obtained OSM data
    graph = _build_graph_from_osm(osm_data)
    elapsed = time.perf_counter() - start
    meta = RoadNetworkMetadata(
        data_source=data_source,
        num_nodes=graph.num_nodes(),
        num_edges=graph.num_edges(),
        bbox={"north": north, "south": south, "east": east, "west": west},
        load_time_seconds=round(elapsed, 4),
    )
    logger.info(
        "Road network ready: %d nodes, %d edges [%s] in %.3f s",
        meta.num_nodes, meta.num_edges, data_source, elapsed,
    )
    return graph, meta


def get_road_network(
    north: float = 10.007,
    south: float = 9.999,
    east: float = 76.321,
    west: float = 76.299,
    **kwargs: Any,
) -> Tuple[WeightedGraph, RoadNetworkMetadata]:
    """
    Convenience wrapper with sensible defaults.

    The default bbox is a small generic area matching the sample network
    coordinates—**not** hardcoded to any named city.
    """
    return load_osm_network(north, south, east, west, **kwargs)
