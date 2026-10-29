"""
Assignment Service using Kuhn-Munkres (Hungarian) Algorithm.

Assigns electric vehicles (EVs) to charging stations (e.g. chosen by MDS)
by constructing a cost matrix (network travel distance or geographic distance)
and executing the Kuhn-Munkres bipartite matching algorithm.
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from app.algorithms.dijkstra import dijkstra_shortest_path
from app.algorithms.hungarian import hungarian_algorithm
from app.core.config import settings
from app.gis.models import CandidateLocation
from app.gis.spatial_index import snap_coordinates_to_road, find_nearest_road_node, validate_coordinates
from app.graph.weighted_graph import WeightedGraph
from app.services.routing_service import RoutingService, get_routing_service
from app.services.station_optimization_service import (
    StationOptimizationService,
    get_station_optimization_service,
)
from app.utils.distance import haversine_distance

logger = logging.getLogger(__name__)

# Sentinel penalty value for unreachable graph pairs (1 million km)
UNREACHABLE_PENALTY = 1_000_000.0


class AssignmentService:
    """
    Orchestrates EV-to-station bipartite matching using the Hungarian algorithm.
    """

    def __init__(
        self,
        routing_service: Optional[RoutingService] = None,
        station_optimization_service: Optional[StationOptimizationService] = None,
    ) -> None:
        self._routing_service = routing_service
        self._station_optimization_service = station_optimization_service

    def _get_routing_service(self) -> RoutingService:
        if self._routing_service is None:
            self._routing_service = get_routing_service()
        return self._routing_service

    def _get_station_optimization_service(self) -> StationOptimizationService:
        if self._station_optimization_service is None:
            self._station_optimization_service = get_station_optimization_service()
        return self._station_optimization_service

    def assign_evs_to_stations(
        self,
        evs: List[Dict[str, Any]],
        station_ids: Optional[List[str]] = None,
        coverage_radius_km: Optional[float] = None,
        min_feasibility_score: Optional[float] = None,
        max_stations: Optional[int] = None,
        cost_metric: str = "network_distance_km",
        graph: Optional[WeightedGraph] = None,
        candidates: Optional[List[CandidateLocation]] = None,
    ) -> Dict[str, Any]:
        """
        Assign electric vehicles to charging stations using Hungarian algorithm.

        Parameters:
            evs: List of dicts with 'ev_id', 'latitude', 'longitude'.
            station_ids: Optional list of candidate station IDs to assign to.
                         If None, MDS-selected stations will be used.
            coverage_radius_km: Service radius for dynamic MDS calculation if station_ids is None.
            min_feasibility_score: Min feasibility threshold if station_ids is None.
            max_stations: Maximum stations cap if station_ids is None.
            cost_metric: 'network_distance_km' (preferred) or 'geographic_distance_km'.
            graph: Optional injected WeightedGraph (defaults to active routing graph).
            candidates: Optional injected candidate locations.

        Returns:
            Dict containing assignments, unassigned EVs, total cost, and metadata.
        """
        # Step 1: Validate EV input
        validated_evs: List[Dict[str, Any]] = []
        seen_ev_ids: Set[str] = set()

        for ev in evs:
            ev_id = str(ev.get("ev_id", "")).strip()
            if not ev_id:
                raise ValueError("Each EV must provide a non-empty 'ev_id'.")
            if ev_id in seen_ev_ids:
                raise ValueError(f"Duplicate ev_id detected: '{ev_id}'.")
            seen_ev_ids.add(ev_id)

            lat = ev.get("latitude")
            lon = ev.get("longitude")
            validate_coordinates(lat, lon)
            validated_evs.append({
                "ev_id": ev_id,
                "latitude": float(lat),
                "longitude": float(lon),
            })

        # Step 2: Resolve target charging stations
        rs = self._get_routing_service()
        active_graph = graph if graph is not None else rs.get_network()[0]
        all_candidates = candidates if candidates is not None else rs.get_feasible_candidates()

        resolved_stations: List[Dict[str, Any]] = []

        if station_ids is not None:
            # Explicit station IDs supplied (e.g. from prior MDS or selection)
            cand_map = {c.candidate_id: c for c in all_candidates}
            for sid in station_ids:
                if sid not in cand_map:
                    raise ValueError(f"Candidate station ID '{sid}' not found among feasible candidates.")
                c = cand_map[sid]
                resolved_stations.append({
                    "station_id": c.candidate_id,
                    "latitude": c.latitude,
                    "longitude": c.longitude,
                    "nearest_road_node": c.nearest_road_node,
                    "feasibility_score": c.feasibility_score,
                })

            if max_stations is not None and len(resolved_stations) > max_stations:
                resolved_stations = resolved_stations[:max_stations]
            elif cost_metric == "network_distance_km" and len(resolved_stations) > 10:
                resolved_stations = resolved_stations[:10]
        else:
            # Station IDs not supplied: resolve dynamically via MDS
            sos = self._get_station_optimization_service()
            dyn_max_stations = max_stations if max_stations is not None else min(len(all_candidates), max(len(validated_evs) * 2, 5))
            mds_res = sos.optimize_station_placement(
                coverage_radius_km=coverage_radius_km,
                min_feasibility_score=min_feasibility_score,
                max_stations=dyn_max_stations,
                graph=active_graph,
                candidates=all_candidates,
            )
            for st in mds_res.get("selected_stations", []):
                resolved_stations.append({
                    "station_id": st["candidate_id"],
                    "latitude": st["latitude"],
                    "longitude": st["longitude"],
                    "nearest_road_node": st["node_id"],
                    "feasibility_score": st.get("feasibility_score"),
                })

        ev_count = len(validated_evs)
        station_count = len(resolved_stations)

        # Step 3: Handle empty inputs safely
        if ev_count == 0:
            return {
                "algorithm": "hungarian",
                "cost_metric": cost_metric,
                "ev_count": 0,
                "station_count": station_count,
                "assigned_count": 0,
                "unassigned_count": 0,
                "assignments": [],
                "unassigned_ev_ids": [],
                "unassigned_station_ids": [s["station_id"] for s in resolved_stations],
                "total_cost_km": 0.0,
            }

        if station_count == 0:
            return {
                "algorithm": "hungarian",
                "cost_metric": cost_metric,
                "ev_count": ev_count,
                "station_count": 0,
                "assigned_count": 0,
                "unassigned_count": ev_count,
                "assignments": [],
                "unassigned_ev_ids": [e["ev_id"] for e in validated_evs],
                "unassigned_station_ids": [],
                "total_cost_km": 0.0,
            }

        # Step 4: Build Cost Matrix (N rows = EVs, M cols = Stations)
        cost_matrix = np.zeros((ev_count, station_count), dtype=float)
        paths: Dict[Tuple[int, int], List[Any]] = {}
        actual_metric = cost_metric

        if cost_metric == "network_distance_km":
            # Attempt to snap each EV to the nearest road network node
            snapped_ev_nodes: List[Optional[Any]] = []
            can_use_network = active_graph.num_nodes() > 0

            for ev in validated_evs:
                try:
                    snap_res = snap_coordinates_to_road(
                        active_graph,
                        ev["latitude"],
                        ev["longitude"],
                        max_distance_m=settings.MAX_SNAP_DISTANCE_M,
                    )
                    snapped_ev_nodes.append(snap_res["nearest_node"]["id"])
                except Exception:
                    can_use_network = False
                    break

            if can_use_network:
                for i, ev in enumerate(validated_evs):
                    ev_node = snapped_ev_nodes[i]
                    for j, st in enumerate(resolved_stations):
                        st_node = st.get("nearest_road_node")
                        if st_node is None or not active_graph.has_node(st_node):
                            cost_matrix[i, j] = UNREACHABLE_PENALTY
                            continue

                        dijkstra_res = dijkstra_shortest_path(active_graph, source=ev_node, target=st_node)
                        dist = dijkstra_res["total_distance"]
                        if dist == float("inf"):
                            cost_matrix[i, j] = UNREACHABLE_PENALTY
                        else:
                            cost_matrix[i, j] = dist
                            paths[(i, j)] = dijkstra_res["path"]
                actual_metric = "network_distance_km"
            else:
                # Snapping or graph traversal not possible -> fallback to geographic distance
                logger.info("Falling back to geographic_distance_km for Hungarian cost matrix.")
                for i, ev in enumerate(validated_evs):
                    for j, st in enumerate(resolved_stations):
                        cost_matrix[i, j] = haversine_distance(
                            ev["latitude"], ev["longitude"],
                            st["latitude"], st["longitude"],
                            unit="km",
                        )
                actual_metric = "geographic_distance_km"
        else:
            # Explicit geographic distance metric requested
            for i, ev in enumerate(validated_evs):
                for j, st in enumerate(resolved_stations):
                    cost_matrix[i, j] = haversine_distance(
                        ev["latitude"], ev["longitude"],
                        st["latitude"], st["longitude"],
                        unit="km",
                    )
            actual_metric = "geographic_distance_km"

        # Step 5: Execute Hungarian Algorithm
        hungarian_res = hungarian_algorithm(cost_matrix)
        raw_assignments = hungarian_res["assignments"]

        # Step 6: Process assignments and exclude unreachable pairings
        assignments: List[Dict[str, Any]] = []
        assigned_ev_indices: Set[int] = set()
        assigned_st_indices: Set[int] = set()
        total_valid_cost: float = 0.0

        for r, c in raw_assignments:
            cost = cost_matrix[r, c]
            # Exclude unreachable sentinel pairings
            if cost >= (UNREACHABLE_PENALTY / 2.0):
                continue

            ev = validated_evs[r]
            st = resolved_stations[c]

            # Build polyline path coordinates
            path_coords: List[List[float]] = []
            if (r, c) in paths:
                node_ids = paths[(r, c)]
                for nid in node_ids:
                    coords = active_graph.get_coordinates(nid)
                    if coords:
                        path_coords.append([coords[0], coords[1]])
            else:
                # Straight line between EV and Station
                path_coords = [
                    [ev["latitude"], ev["longitude"]],
                    [st["latitude"], st["longitude"]],
                ]

            assignments.append({
                "ev_id": ev["ev_id"],
                "station_id": st["station_id"],
                "cost_km": round(float(cost), 3),
                "ev_latitude": ev["latitude"],
                "ev_longitude": ev["longitude"],
                "station_latitude": st["latitude"],
                "station_longitude": st["longitude"],
                "path_coordinates": path_coords,
            })
            assigned_ev_indices.add(r)
            assigned_st_indices.add(c)
            total_valid_cost += float(cost)

        unassigned_ev_ids = [
            validated_evs[i]["ev_id"]
            for i in range(ev_count)
            if i not in assigned_ev_indices
        ]
        unassigned_station_ids = [
            resolved_stations[j]["station_id"]
            for j in range(station_count)
            if j not in assigned_st_indices
        ]

        logger.info(
            "Hungarian matching complete: %d/%d EVs assigned to %d stations (total cost: %.3f km, metric: %s)",
            len(assignments),
            ev_count,
            station_count,
            total_valid_cost,
            actual_metric,
        )

        return {
            "algorithm": "hungarian",
            "cost_metric": actual_metric,
            "ev_count": ev_count,
            "station_count": station_count,
            "assigned_count": len(assignments),
            "unassigned_count": len(unassigned_ev_ids),
            "assignments": assignments,
            "unassigned_ev_ids": unassigned_ev_ids,
            "unassigned_station_ids": unassigned_station_ids,
            "total_cost_km": round(total_valid_cost, 3),
        }


# Singleton service instance
_assignment_service_instance: Optional[AssignmentService] = None


def get_assignment_service() -> AssignmentService:
    """Dependency provider for AssignmentService singleton."""
    global _assignment_service_instance
    if _assignment_service_instance is None:
        _assignment_service_instance = AssignmentService()
    return _assignment_service_instance
