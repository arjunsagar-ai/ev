"""
Station Optimization Service using Greedy Minimum Dominating Set (MDS).

Provides coverage-oriented EV charging station placement using the existing
greedy MDS approximation on the road network graph.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.algorithms.dominating_set import minimum_dominating_set
from app.gis.models import CandidateLocation
from app.graph.weighted_graph import WeightedGraph
from app.services.routing_service import RoutingService, get_routing_service

logger = logging.getLogger(__name__)


class StationOptimizationService:
    """
    Orchestrates candidate filtering, graph node mapping, and greedy MDS
    execution for network-wide charging station placement.
    """

    def __init__(self, routing_service: Optional[RoutingService] = None) -> None:
        self._routing_service = routing_service

    def _get_routing_service(self) -> RoutingService:
        if self._routing_service is None:
            self._routing_service = get_routing_service()
        return self._routing_service

    def optimize_station_placement(
        self,
        coverage_radius_km: Optional[float] = None,
        min_feasibility_score: Optional[float] = None,
        max_stations: Optional[int] = None,
        graph: Optional[WeightedGraph] = None,
        candidates: Optional[List[CandidateLocation]] = None,
    ) -> Dict[str, Any]:
        """
        Determine optimal charging station placement using greedy MDS approximation.

        Parameters:
            coverage_radius_km: Service radius in km around each station (default from config).
            min_feasibility_score: Optional filter to restrict candidate pool to higher scores.
            max_stations: Optional maximum cap on number of stations to deploy.
            graph: Optional injected road network graph (defaults to cached active graph).
            candidates: Optional injected candidates (defaults to active feasible candidates).

        Returns:
            Dict containing selected stations, counts, demand coverage percentage, and metadata.
        """
        # Step 1: Obtain graph and candidates
        rs = self._get_routing_service()
        active_graph = graph if graph is not None else rs.get_network()[0]
        all_candidates = candidates if candidates is not None else rs.get_feasible_candidates()

        radius = coverage_radius_km if coverage_radius_km is not None else settings.DEFAULT_COVERAGE_RADIUS_KM
        if radius <= 0:
            raise ValueError(f"coverage_radius_km must be strictly positive, got {radius}")

        if min_feasibility_score is not None:
            if not (0.0 <= min_feasibility_score <= 1.0):
                raise ValueError(f"min_feasibility_score must be between 0.0 and 1.0, got {min_feasibility_score}")

        if max_stations is not None and max_stations <= 0:
            raise ValueError(f"max_stations must be a positive integer, got {max_stations}")

        # Step 2: Filter for feasible candidates meeting score threshold
        filtered_candidates: List[CandidateLocation] = [
            c for c in all_candidates if c.feasible
        ]
        if min_feasibility_score is not None:
            filtered_candidates = [
                c for c in filtered_candidates
                if c.feasibility_score >= min_feasibility_score
            ]

        # Step 3: Map candidate locations to road network nodes
        # If multiple candidates attach to the same road node, select the one with highest feasibility score
        node_to_candidate: Dict[Any, CandidateLocation] = {}
        for cand in filtered_candidates:
            node = cand.nearest_road_node
            if node is None or not active_graph.has_node(node):
                continue
            if node not in node_to_candidate or cand.feasibility_score > node_to_candidate[node].feasibility_score:
                node_to_candidate[node] = cand

        candidate_node_ids = list(node_to_candidate.keys())
        total_demand_nodes = active_graph.num_nodes()

        # Step 4: Handle empty candidates or empty graph safely
        if not candidate_node_ids or total_demand_nodes == 0:
            logger.info("MDS optimization: no eligible candidate nodes available.")
            return {
                "selected_stations": [],
                "selected_count": 0,
                "candidate_count": len(filtered_candidates),
                "total_demand_nodes": total_demand_nodes,
                "covered_demand_nodes": 0,
                "coverage_percentage": 0.0,
                "coverage_radius_km": radius,
                "algorithm": "greedy_mds_approximation",
            }

        # Step 5: Execute greedy Minimum Dominating Set approximation
        mds_result = minimum_dominating_set(
            graph=active_graph,
            coverage_radius=radius,
            candidate_nodes=candidate_node_ids,
            demand_nodes=active_graph.nodes(),
        )

        selected_node_ids = mds_result["selected_nodes"]
        coverage_map = mds_result["coverage_map"]

        # Step 6: Apply optional max_stations limit if requested
        if max_stations is not None and len(selected_node_ids) > max_stations:
            selected_node_ids = selected_node_ids[:max_stations]
            # Recalculate covered demand for truncated set
            covered_set = set()
            for nid in selected_node_ids:
                covered_set.update(coverage_map.get(nid, []))
            covered_count = len(covered_set)
            coverage_pct = round((covered_count / total_demand_nodes) * 100.0, 2) if total_demand_nodes > 0 else 0.0
        else:
            covered_count = len(mds_result["covered_nodes"])
            coverage_pct = mds_result["coverage_percentage"]

        # Step 7: Map selected nodes back to station candidate details
        selected_stations: List[Dict[str, Any]] = []
        for nid in selected_node_ids:
            cand = node_to_candidate[nid]
            selected_stations.append({
                "candidate_id": cand.candidate_id,
                "node_id": nid,
                "latitude": cand.latitude,
                "longitude": cand.longitude,
                "feasible": cand.feasible,
                "feasibility_score": round(cand.feasibility_score, 4),
                "covered_demand_count": len(coverage_map.get(nid, [])),
            })

        logger.info(
            "MDS station placement: selected %d stations from %d candidates (coverage: %.1f%%, radius: %.1f km)",
            len(selected_stations),
            len(filtered_candidates),
            coverage_pct,
            radius,
        )

        return {
            "selected_stations": selected_stations,
            "selected_count": len(selected_stations),
            "candidate_count": len(filtered_candidates),
            "total_demand_nodes": total_demand_nodes,
            "covered_demand_nodes": covered_count,
            "coverage_percentage": coverage_pct,
            "coverage_radius_km": radius,
            "algorithm": "greedy_mds_approximation",
        }


# Singleton service instance
_station_optimization_service_instance: Optional[StationOptimizationService] = None


def get_station_optimization_service() -> StationOptimizationService:
    """Dependency provider for StationOptimizationService singleton."""
    global _station_optimization_service_instance
    if _station_optimization_service_instance is None:
        _station_optimization_service_instance = StationOptimizationService()
    return _station_optimization_service_instance
