"""
Routing and station selection service.

Orchestrates:
  1. Coordinate validation (via spatial_index)
  2. Snapping GPS to nearest road node (via spatial_index)
  3. Feasible charging station selection (nearest graph distance)
  4. Shortest path computation (via dijkstra_shortest_path)
  5. Assembling route coordinates and estimated ETA
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.algorithms.dijkstra import dijkstra_shortest_path
from app.gis.candidate_generator import (
    filter_feasible_candidates,
    generate_candidates_from_graph,
)
from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import get_road_network
from app.gis.spatial_index import (
    snap_coordinates_to_road,
    validate_coordinates,
)
from app.graph.weighted_graph import WeightedGraph

logger = logging.getLogger(__name__)


class RoutingService:
    """
    Singleton service managing network caching and live GPS routing orchestration.
    """

    def __init__(self) -> None:
        self._graph: Optional[WeightedGraph] = None
        self._metadata: Optional[RoadNetworkMetadata] = None
        self._feasible_candidates: List[CandidateLocation] = []
        self._candidates_loaded: bool = False

    def get_network(self) -> Tuple[WeightedGraph, RoadNetworkMetadata]:
        """Retrieve the cached road network, or load on demand if absent."""
        if self._graph is None or self._metadata is None:
            self.load_network()
        assert self._graph is not None
        assert self._metadata is not None
        return self._graph, self._metadata

    def get_feasible_candidates(self) -> List[CandidateLocation]:
        """Retrieve the cached list of feasible charging station candidates."""
        if not self._candidates_loaded:
            if self._graph is None:
                self.load_network()
            else:
                self._generate_and_cache_candidates()
        return self._feasible_candidates

    def load_network(
        self,
        force_reload: bool = False,
        **kwargs: Any,
    ) -> Tuple[WeightedGraph, RoadNetworkMetadata]:
        """
        Load or reload the road network from cache/OSM/sample data.
        """
        if self._graph is None or force_reload:
            logger.info("Initializing road network for routing service...")
            graph, meta = get_road_network(**kwargs)
            self._graph = graph
            self._metadata = meta
            self._generate_and_cache_candidates()
            logger.info(
                "Routing network ready: %d nodes, %d edges [%s]",
                graph.num_nodes(),
                graph.num_edges(),
                meta.data_source,
            )

        assert self._graph is not None
        assert self._metadata is not None
        return self._graph, self._metadata

    def set_network(
        self,
        graph: WeightedGraph,
        metadata: RoadNetworkMetadata,
        candidates: Optional[List[CandidateLocation]] = None,
    ) -> None:
        """
        Explicitly inject a network and candidate list (primarily for tests).
        """
        self._graph = graph
        self._metadata = metadata
        if candidates is not None:
            self._feasible_candidates = candidates
            self._candidates_loaded = True
        else:
            self._generate_and_cache_candidates()

    def _generate_and_cache_candidates(self) -> None:
        """Generate and filter feasible station candidates from the active graph."""
        if self._graph is None:
            return

        source = self._metadata.data_source if self._metadata else "sample"
        # Generate candidates from road intersections (degree >= 3)
        raw_candidates = generate_candidates_from_graph(
            self._graph,
            data_source=source,
            node_selection="intersections",
        )
        # Fallback to all nodes if no intersections found (e.g. tiny graph)
        if not raw_candidates:
            raw_candidates = generate_candidates_from_graph(
                self._graph,
                data_source=source,
                node_selection="all",
            )

        filtered = filter_feasible_candidates(raw_candidates)
        feasible = filtered["feasible"]

        # If strict filtering rejected everything, fall back to top candidates
        if not feasible and raw_candidates:
            logger.warning("All candidates failed strict threshold; falling back to top candidates.")
            feasible = sorted(raw_candidates, key=lambda c: c.feasibility_score, reverse=True)[:3]
            for c in feasible:
                c.feasible = True

        self._feasible_candidates = feasible
        self._candidates_loaded = True
        logger.info("Cached %d feasible charging stations for live routing.", len(self._feasible_candidates))

    def get_network_summary(self) -> Dict[str, Any]:
        """Return basic metadata about the currently loaded road network."""
        graph, meta = self.get_network()
        return {
            "node_count": graph.num_nodes(),
            "edge_count": graph.num_edges(),
            "data_source": meta.data_source,
        }

    def calculate_live_route(
        self,
        latitude: float,
        longitude: float,
        max_station_distance_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the shortest path route from live GPS coordinates to the nearest
        feasible EV charging station.

        Workflow:
          1. Validate coordinates
          2. Snap GPS coordinates to nearest road network node
          3. Query feasible station candidates
          4. Select candidate with shortest graph distance via Dijkstra
          5. Return route node IDs, [lat, lon] polyline, distance, and estimated ETA
        """
        # Step 1: Validate input coordinates
        validate_coordinates(latitude, longitude)

        # Step 2: Ensure road network is loaded
        graph, _ = self.get_network()
        if graph.num_nodes() == 0:
            raise RuntimeError("Road network is not initialized or contains no nodes.")

        # Step 3: Snap GPS coordinates to nearest road node
        # Raises ValueError if nearest road node is further than MAX_SNAP_DISTANCE_M
        snap_result = snap_coordinates_to_road(
            graph,
            latitude,
            longitude,
            max_distance_m=settings.MAX_SNAP_DISTANCE_M,
        )
        snapped_node_id = snap_result["nearest_node"]["id"]
        distance_to_road_m = snap_result["distance_to_road_m"]

        # Step 4: Retrieve feasible candidates
        candidates = self.get_feasible_candidates()
        if not candidates:
            raise LookupError("No feasible EV charging stations available in the network.")

        # Step 5: Select best station based on shortest graph distance
        best_candidate: Optional[CandidateLocation] = None
        best_dijkstra: Optional[Dict[str, Any]] = None
        min_graph_distance: float = float("inf")

        for cand in candidates:
            target_node = cand.nearest_road_node
            if target_node is None or not graph.has_node(target_node):
                continue

            # Run Dijkstra to determine exact road network distance
            res = dijkstra_shortest_path(graph, source=snapped_node_id, target=target_node)
            dist = res["total_distance"]

            if dist == float("inf"):
                # Candidate is unreachable in a disconnected component
                continue

            # Check optional search radius restriction
            if max_station_distance_km is not None and dist > max_station_distance_km:
                continue

            if dist < min_graph_distance:
                min_graph_distance = dist
                best_candidate = cand
                best_dijkstra = res

        if best_candidate is None or best_dijkstra is None:
            if max_station_distance_km is not None:
                raise LookupError(
                    f"No reachable charging station found within {max_station_distance_km} km."
                )
            raise LookupError("No reachable charging station found from user position.")

        # Step 6: Assemble route coordinates polyline
        path_nodes = best_dijkstra["path"]
        coordinates: List[List[float]] = []
        for nid in path_nodes:
            coords = graph.get_coordinates(nid)
            if coords:
                coordinates.append([coords[0], coords[1]])

        # Step 7: Calculate estimated ETA in minutes (based on average speed)
        speed = settings.DEFAULT_AVERAGE_SPEED_KMH
        estimated_eta = round((min_graph_distance / speed) * 60.0, 1) if speed > 0 else None

        # Sanitize logging: do NOT log raw user GPS coordinates for privacy
        logger.info(
            "Live route computed: snapped to node %s (dist %.1f m) -> station %s (dist %.2f km)",
            snapped_node_id,
            distance_to_road_m,
            best_candidate.candidate_id,
            min_graph_distance,
        )

        return {
            "user_location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "snapped_node": snapped_node_id,
            "distance_to_snapped_node_m": distance_to_road_m,
            "station": {
                "candidate_id": best_candidate.candidate_id,
                "latitude": best_candidate.latitude,
                "longitude": best_candidate.longitude,
                "nearest_road_node": best_candidate.nearest_road_node,
                "road_distance_m": best_candidate.road_distance_m,
                "feasibility_score": best_candidate.feasibility_score,
                "data_source": best_candidate.data_source,
            },
            "route": {
                "node_ids": path_nodes,
                "coordinates": coordinates,
                "distance_km": round(min_graph_distance, 3),
                "estimated_eta_minutes": estimated_eta,
            },
        }


# Singleton instance for application lifecycle
_routing_service_instance: Optional[RoutingService] = None


def get_routing_service() -> RoutingService:
    """Dependency provider for RoutingService singleton."""
    global _routing_service_instance
    if _routing_service_instance is None:
        _routing_service_instance = RoutingService()
    return _routing_service_instance
