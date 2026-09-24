"""
Infrastructure Service using Prim's Minimum Spanning Tree (MST).

Calculates the minimum spanning infrastructure connection network between
selected EV charging stations using the road network graph.
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.algorithms.dijkstra import dijkstra_shortest_path
from app.algorithms.prim import prim_mst
from app.gis.models import CandidateLocation
from app.graph.weighted_graph import WeightedGraph
from app.services.routing_service import RoutingService, get_routing_service
from app.services.station_optimization_service import (
    StationOptimizationService,
    get_station_optimization_service,
)
from app.utils.distance import haversine_distance

logger = logging.getLogger(__name__)


class InfrastructureService:
    """
    Orchestrates infrastructure connection network optimization between
    selected EV charging stations using Prim's MST algorithm.
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

    def optimize_infrastructure(
        self,
        station_ids: Optional[List[str]] = None,
        coverage_radius_km: Optional[float] = None,
        min_feasibility_score: Optional[float] = None,
        max_stations: Optional[int] = None,
        cost_metric: str = "network_distance_km",
        graph: Optional[WeightedGraph] = None,
        candidates: Optional[List[CandidateLocation]] = None,
    ) -> Dict[str, Any]:
        """
        Compute the minimum spanning infrastructure connection network for selected stations.

        Parameters:
            station_ids: Optional explicit list of candidate station IDs.
                         If None, MDS-selected stations will be used.
            coverage_radius_km: Service radius for dynamic MDS calculation if station_ids is None.
            min_feasibility_score: Min feasibility threshold if station_ids is None.
            max_stations: Maximum stations cap if station_ids is None.
            cost_metric: 'network_distance_km' (preferred) or 'geographic_distance_km'.
            graph: Optional injected WeightedGraph (defaults to active routing graph).
            candidates: Optional injected candidate locations.

        Returns:
            Dict containing stations, MST edges, total distance/cost, and connection status.
        """
        rs = self._get_routing_service()
        active_graph = graph if graph is not None else rs.get_network()[0]
        all_candidates = candidates if candidates is not None else rs.get_feasible_candidates()

        resolved_stations: List[Dict[str, Any]] = []

        if station_ids is not None:
            # Handle duplicate station IDs while preserving order
            seen_ids: Set[str] = set()
            deduped_ids: List[str] = []
            for sid in station_ids:
                clean_id = str(sid).strip()
                if not clean_id:
                    continue
                if clean_id not in seen_ids:
                    seen_ids.add(clean_id)
                    deduped_ids.append(clean_id)

            cand_map = {c.candidate_id: c for c in all_candidates}
            for sid in deduped_ids:
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
        else:
            # Station IDs not supplied: resolve dynamically via MDS
            sos = self._get_station_optimization_service()
            mds_res = sos.optimize_station_placement(
                coverage_radius_km=coverage_radius_km,
                min_feasibility_score=min_feasibility_score,
                max_stations=max_stations,
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

        station_count = len(resolved_stations)

        # Step 1: Handle 0 stations
        if station_count == 0:
            return {
                "algorithm": "prim_mst",
                "cost_metric": cost_metric,
                "station_count": 0,
                "connected_station_count": 0,
                "mst_edge_count": 0,
                "total_cost_km": 0.0,
                "stations": [],
                "edges": [],
                "connected_station_ids": [],
                "unconnected_station_ids": [],
            }

        # Step 2: Handle 1 station (MST cost is 0.0)
        if station_count == 1:
            st = resolved_stations[0]
            sid = st["station_id"]
            return {
                "algorithm": "prim_mst",
                "cost_metric": cost_metric,
                "station_count": 1,
                "connected_station_count": 1,
                "mst_edge_count": 0,
                "total_cost_km": 0.0,
                "stations": [{
                    "station_id": sid,
                    "candidate_id": sid,
                    "latitude": st["latitude"],
                    "longitude": st["longitude"],
                    "nearest_road_node": st.get("nearest_road_node"),
                    "connected": True,
                }],
                "edges": [],
                "connected_station_ids": [sid],
                "unconnected_station_ids": [],
            }

        # Step 3: Build the station infrastructure graph (undirected)
        # Note: Do NOT modify the underlying road network graph.
        station_graph = WeightedGraph(directed=False)
        for st in resolved_stations:
            station_graph.add_node(
                st["station_id"],
                lat=st["latitude"],
                lon=st["longitude"],
                nearest_road_node=st.get("nearest_road_node"),
            )

        paths_map: Dict[Tuple[str, str], List[List[float]]] = {}
        actual_metric = cost_metric

        if cost_metric == "network_distance_km" and active_graph.num_nodes() > 0:
            # Pairwise shortest paths across the road network using Dijkstra
            for i in range(station_count):
                st_i = resolved_stations[i]
                u_node = st_i.get("nearest_road_node")

                for j in range(i + 1, station_count):
                    st_j = resolved_stations[j]
                    v_node = st_j.get("nearest_road_node")

                    if u_node is None or not active_graph.has_node(u_node):
                        continue
                    if v_node is None or not active_graph.has_node(v_node):
                        continue

                    edge_key = tuple(sorted([st_i["station_id"], st_j["station_id"]]))

                    if u_node == v_node:
                        # Both stations snap to the same road node
                        station_graph.add_edge(st_i["station_id"], st_j["station_id"], weight=0.0)
                        paths_map[edge_key] = [
                            [st_i["latitude"], st_i["longitude"]],
                            [st_j["latitude"], st_j["longitude"]],
                        ]
                    else:
                        dijkstra_res = dijkstra_shortest_path(active_graph, source=u_node, target=v_node)
                        dist = dijkstra_res["total_distance"]
                        if dist != float("inf"):
                            path_coords = [[st_i["latitude"], st_i["longitude"]]]
                            for nid in dijkstra_res["path"]:
                                c = active_graph.get_coordinates(nid)
                                if c:
                                    pt = [c[0], c[1]]
                                    if pt != path_coords[-1]:
                                        path_coords.append(pt)
                            end_pt = [st_j["latitude"], st_j["longitude"]]
                            if end_pt != path_coords[-1]:
                                path_coords.append(end_pt)

                            station_graph.add_edge(
                                st_i["station_id"],
                                st_j["station_id"],
                                weight=round(dist, 6),
                            )
                            paths_map[edge_key] = path_coords

            actual_metric = "network_distance_km"
        else:
            # Fallback or requested geographic Haversine distance
            for i in range(station_count):
                st_i = resolved_stations[i]
                for j in range(i + 1, station_count):
                    st_j = resolved_stations[j]
                    dist = haversine_distance(
                        st_i["latitude"], st_i["longitude"],
                        st_j["latitude"], st_j["longitude"],
                        unit="km",
                    )
                    edge_key = tuple(sorted([st_i["station_id"], st_j["station_id"]]))
                    station_graph.add_edge(
                        st_i["station_id"],
                        st_j["station_id"],
                        weight=round(dist, 6),
                    )
                    paths_map[edge_key] = [
                        [st_i["latitude"], st_i["longitude"]],
                        [st_j["latitude"], st_j["longitude"]],
                    ]
            actual_metric = "geographic_distance_km"

        # Step 4: Execute existing Prim MST
        # Pick start node: prefer first node that has at least one edge in station_graph
        start_node = resolved_stations[0]["station_id"]
        for st in resolved_stations:
            if len(station_graph.get_neighbors(st["station_id"])) > 0:
                start_node = st["station_id"]
                break

        prim_result = prim_mst(station_graph, start_node=start_node)

        raw_mst_edges = prim_result["mst_edges"]
        total_cost = prim_result["total_cost"]
        connected_set = set(prim_result["connected_nodes"])
        unconnected_set = set(prim_result["unconnected_nodes"])

        # Step 5: Format edges
        formatted_edges: List[Dict[str, Any]] = []
        for u, v, weight in raw_mst_edges:
            edge_key = tuple(sorted([u, v]))
            path_coords = paths_map.get(edge_key, [])
            formatted_edges.append({
                "from_station_id": u,
                "to_station_id": v,
                "cost_km": round(weight, 3),
                "path_coordinates": path_coords,
            })

        # Step 6: Format station output
        formatted_stations: List[Dict[str, Any]] = []
        for st in resolved_stations:
            sid = st["station_id"]
            formatted_stations.append({
                "station_id": sid,
                "candidate_id": sid,
                "latitude": st["latitude"],
                "longitude": st["longitude"],
                "nearest_road_node": st.get("nearest_road_node"),
                "connected": sid in connected_set,
            })

        logger.info(
            "Prim MST infrastructure optimization complete: %d stations (%d connected, %d edges, total: %.3f km, metric: %s)",
            station_count,
            len(connected_set),
            len(formatted_edges),
            total_cost,
            actual_metric,
        )

        return {
            "algorithm": "prim_mst",
            "cost_metric": actual_metric,
            "station_count": station_count,
            "connected_station_count": len(connected_set),
            "mst_edge_count": len(formatted_edges),
            "total_cost_km": round(total_cost, 3),
            "stations": formatted_stations,
            "edges": formatted_edges,
            "connected_station_ids": sorted(list(connected_set)),
            "unconnected_station_ids": sorted(list(unconnected_set)),
        }


# Singleton service instance
_infrastructure_service_instance: Optional[InfrastructureService] = None


def get_infrastructure_service() -> InfrastructureService:
    """Dependency provider for InfrastructureService singleton."""
    global _infrastructure_service_instance
    if _infrastructure_service_instance is None:
        _infrastructure_service_instance = InfrastructureService()
    return _infrastructure_service_instance
