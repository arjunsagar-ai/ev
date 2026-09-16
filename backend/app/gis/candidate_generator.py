"""
Candidate EV Charging-Station Location Generator.

Uses GIS/OSM data and configurable heuristics to:
  1. Identify candidate locations from POI tags, road intersections,
     and geographic features.
  2. Score each candidate on a weighted feasibility model.
  3. Filter candidates into feasible / rejected buckets with reasons.

Scoring model
─────────────
  feasibility_score =
      W_accessibility × accessibility_score
    + W_land          × land_available
    + W_grid          × grid_capacity
    − W_cost          × installation_cost

where each factor is in [0, 1] and weights come from ``settings.FEASIBILITY_WEIGHTS``.

IMPORTANT:
  OSM data provides geographic context only.  Values such as ``grid_capacity``
  are marked **estimated** or **synthetic** when real electrical-substation
  data is not available.
"""
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.gis.models import CandidateLocation
from app.gis.spatial_index import find_nearest_road_node, validate_coordinates
from app.graph.weighted_graph import WeightedGraph
from app.utils.distance import haversine_distance

logger = logging.getLogger(__name__)

# OSM amenity / land-use tags that hint at good EV-station sites
_CANDIDATE_POI_TAGS: Dict[str, float] = {
    # tag value  →  base land-availability score
    "parking":          0.85,
    "fuel":             0.90,
    "charging_station": 0.95,
    "bus_station":      0.60,
    "car_wash":         0.70,
    "mall":             0.65,
    "supermarket":      0.60,
    "rest_area":        0.80,
}


# ───────────────── scoring ───────────────────────────────────────────────

def compute_feasibility_score(candidate: CandidateLocation) -> float:
    """
    Calculate a composite feasibility score ∈ [0, 1].

    Formula
    -------
    score = W_a × accessibility + W_l × land + W_g × grid − W_c × cost

    The result is clamped to [0, 1].

    Parameters
    ----------
    candidate : CandidateLocation
        Must have accessibility_score, land_available, grid_capacity,
        and installation_cost already populated.

    Returns
    -------
    float  (0.0 – 1.0)
    """
    w = settings.FEASIBILITY_WEIGHTS
    score = (
        w["accessibility"] * candidate.accessibility_score
        + w["land"]        * candidate.land_available
        + w["grid"]        * candidate.grid_capacity
        - w["cost"]        * candidate.installation_cost
    )
    return max(0.0, min(1.0, score))


# ───────────────── accessibility heuristic ───────────────────────────────

def _road_accessibility(road_distance_m: float) -> float:
    """
    Heuristic: accessibility decreases linearly as the candidate gets
    further from the nearest road node.

    Returns a value in [0, 1].
    """
    max_d = settings.CANDIDATE_MAX_ROAD_DISTANCE_M
    if road_distance_m <= 0:
        return 1.0
    if road_distance_m >= max_d:
        return 0.0
    return 1.0 - (road_distance_m / max_d)


# ───────────────── grid-capacity estimate ────────────────────────────────

def _estimate_grid_capacity(
    candidate: CandidateLocation,
    graph: WeightedGraph,
) -> Tuple[float, str]:
    """
    Estimate electrical grid capacity for a location.

    Without real substation data, we use a distance-to-center heuristic:
    locations nearer the geographic centroid of the road network receive
    a higher synthetic score (urban areas tend to have denser grids).

    Returns (score, source) where *source* is always ``'estimated'``
    when real data is unavailable.
    """
    nodes = graph.nodes()
    if not nodes:
        return 0.5, "estimated"

    # Compute centroid of the network
    lats, lons = [], []
    for nid in nodes:
        coords = graph.get_coordinates(nid)
        if coords:
            lats.append(coords[0])
            lons.append(coords[1])
    if not lats:
        return 0.5, "estimated"

    clat = sum(lats) / len(lats)
    clon = sum(lons) / len(lons)

    dist_to_center_m = haversine_distance(
        candidate.latitude, candidate.longitude, clat, clon, unit="m",
    )

    # Max radius of the network (crude bounding)
    max_radius_m = max(
        haversine_distance(min(lats), min(lons), max(lats), max(lons), unit="m"),
        1.0,
    )

    score = max(0.0, 1.0 - (dist_to_center_m / max_radius_m))
    return round(score, 4), "estimated"


# ──────────────── candidate generation from graph nodes ──────────────────

def generate_candidates_from_graph(
    graph: WeightedGraph,
    data_source: str = "sample",
    node_selection: str = "intersections",
) -> List[CandidateLocation]:
    """
    Generate candidate charging-station locations from the road-network graph.

    Strategy
    --------
    Select high-connectivity intersection nodes (degree ≥ 3) as candidate
    sites.  This heuristic favours locations with good road accessibility.

    Parameters
    ----------
    graph : WeightedGraph
        Loaded road network.
    data_source : str
        'osm', 'cache', or 'sample' — propagated to each candidate.
    node_selection : str
        Strategy: 'intersections' (degree ≥ 3) or 'all'.

    Returns
    -------
    list[CandidateLocation]
    """
    candidates: List[CandidateLocation] = []
    idx = 0

    for nid in graph.nodes():
        coords = graph.get_coordinates(nid)
        if coords is None:
            continue

        neighbors = graph.get_neighbors(nid)
        degree = len(neighbors)

        if node_selection == "intersections" and degree < 3:
            continue

        lat, lon = coords

        # Build a raw candidate
        cand = CandidateLocation(
            candidate_id=f"CAND-{idx:04d}",
            latitude=lat,
            longitude=lon,
            nearest_road_node=nid,
            road_distance_m=0.0,  # node IS on the road
            data_source=data_source,
        )

        # Accessibility: on-road → 1.0
        cand.accessibility_score = 1.0

        # Land: heuristic from node tags if available
        node_data = graph.get_node_data(nid)
        osm_amenity = node_data.get("amenity", "")
        cand.land_available = _CANDIDATE_POI_TAGS.get(osm_amenity, 0.55)

        # Grid capacity estimate
        grid_score, grid_src = _estimate_grid_capacity(cand, graph)
        cand.grid_capacity = grid_score
        cand.grid_capacity_source = grid_src

        # Installation cost heuristic (lower degree → harder logistics → costlier)
        cand.installation_cost = max(0.0, min(1.0, 1.0 - (degree / 10.0)))

        # Score
        cand.feasibility_score = compute_feasibility_score(cand)

        candidates.append(cand)
        idx += 1

    logger.info(
        "Generated %d candidate locations from graph [%s]",
        len(candidates), data_source,
    )
    return candidates


def generate_candidates_from_points(
    points: List[Dict[str, Any]],
    graph: WeightedGraph,
    data_source: str = "sample",
) -> List[CandidateLocation]:
    """
    Score a list of externally-supplied (lat, lon) points against the
    road network.

    Each dict in *points* must contain ``latitude`` and ``longitude``;
    optionally ``candidate_id``, ``land_available``, etc.
    """
    candidates: List[CandidateLocation] = []

    for idx, pt in enumerate(points):
        lat = pt.get("latitude")
        lon = pt.get("longitude")
        if lat is None or lon is None:
            continue
        try:
            validate_coordinates(lat, lon)
        except (TypeError, ValueError):
            continue

        nearest = find_nearest_road_node(graph, lat, lon)

        cand = CandidateLocation(
            candidate_id=pt.get("candidate_id", f"EXT-{idx:04d}"),
            latitude=lat,
            longitude=lon,
            nearest_road_node=nearest["node_id"],
            road_distance_m=nearest["distance_m"],
            data_source=data_source,
        )

        cand.accessibility_score = _road_accessibility(cand.road_distance_m)
        cand.land_available = pt.get("land_available", 0.55)

        grid_score, grid_src = _estimate_grid_capacity(cand, graph)
        cand.grid_capacity = grid_score
        cand.grid_capacity_source = grid_src

        cand.installation_cost = pt.get("installation_cost", 0.50)
        cand.feasibility_score = compute_feasibility_score(cand)

        candidates.append(cand)

    logger.info(
        "Generated %d candidate locations from external points [%s]",
        len(candidates), data_source,
    )
    return candidates


# ───────────────── filtering ─────────────────────────────────────────────

def filter_feasible_candidates(
    candidates: List[CandidateLocation],
    threshold: Optional[float] = None,
    max_road_distance_m: Optional[float] = None,
) -> Dict[str, List[CandidateLocation]]:
    """
    Partition candidates into *feasible* and *rejected* lists.

    Rejection reasons
    -----------------
    • ``"feasibility_score below threshold"``
    • ``"excessive road distance"``
    • ``"insufficient accessibility"``
    • ``"insufficient land availability"``
    • ``"insufficient grid capacity"``

    Returns
    -------
    dict with keys ``'feasible'`` and ``'rejected'``.
    """
    thr = threshold if threshold is not None else settings.FEASIBILITY_THRESHOLD
    max_rd = (
        max_road_distance_m
        if max_road_distance_m is not None
        else settings.CANDIDATE_MAX_ROAD_DISTANCE_M
    )

    feasible: List[CandidateLocation] = []
    rejected: List[CandidateLocation] = []

    for cand in candidates:
        reason: Optional[str] = None

        if cand.road_distance_m > max_rd:
            reason = f"excessive road distance ({cand.road_distance_m:.0f} m > {max_rd:.0f} m)"
        elif cand.accessibility_score < 0.1:
            reason = "insufficient accessibility"
        elif cand.land_available < 0.1:
            reason = "insufficient land availability"
        elif cand.grid_capacity < 0.1:
            reason = "insufficient grid capacity"
        elif cand.feasibility_score < thr:
            reason = (
                f"feasibility_score below threshold "
                f"({cand.feasibility_score:.3f} < {thr:.2f})"
            )

        if reason is not None:
            cand.feasible = False
            cand.rejection_reason = reason
            rejected.append(cand)
        else:
            cand.feasible = True
            cand.rejection_reason = None
            feasible.append(cand)

    logger.info(
        "Candidate filtering: %d feasible, %d rejected (threshold=%.2f)",
        len(feasible), len(rejected), thr,
    )
    return {"feasible": feasible, "rejected": rejected}
