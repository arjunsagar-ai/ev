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
from app.gis.ernakulam_boundary import validate_in_ernakulam, is_point_in_ernakulam
from app.gis.ev_station_loader import load_ernakulam_ev_stations, RealEVStation
from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import get_road_network
from app.gis.spatial_index import (
    find_nearest_road_node,
    snap_coordinates_to_road,
    validate_coordinates,
)
from app.graph.weighted_graph import WeightedGraph
from app.utils.distance import haversine_distance

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
        self._explicit_candidates: bool = False

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
            self._explicit_candidates = False
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
        self._explicit_candidates = candidates is not None
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
            "project_area": "Ernakulam District",
        }

    def find_nearby_existing_stations(
        self,
        latitude: float,
        longitude: float,
        radius_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Identify existing EV charging stations from the dataset within radius_km
        of the specified user coordinates.

        Uses network Dijkstra distance where road nodes are reachable, falling back
        to Haversine distance.
        """
        # Step 1: Validate point is inside Ernakulam District
        validate_in_ernakulam(latitude, longitude)
        validate_coordinates(latitude, longitude)

        search_radius = radius_km if radius_km is not None else settings.EV_STATION_SEARCH_RADIUS_KM
        real_stations = load_ernakulam_ev_stations()
        graph, _ = self.get_network()

        # Attempt to snap user to road network for Dijkstra distance
        snapped_node_id = None
        try:
            snap_res = snap_coordinates_to_road(
                graph, latitude, longitude, max_distance_m=settings.MAX_SNAP_DISTANCE_M
            )
            snapped_node_id = snap_res["nearest_node"]["id"]
        except Exception:
            snapped_node_id = None

        station_results = []
        for stn in real_stations:
            network_dist = float("inf")
            target_node = None
            if snapped_node_id is not None:
                try:
                    target_snap = find_nearest_road_node(graph, stn.latitude, stn.longitude)
                    target_node = target_snap["node_id"]
                    dijkstra_res = dijkstra_shortest_path(graph, source=snapped_node_id, target=target_node)
                    network_dist = dijkstra_res["total_distance"]
                except Exception:
                    pass

            if network_dist != float("inf"):
                dist_km = round(network_dist, 2)
            else:
                dist_km = round(
                    haversine_distance(latitude, longitude, stn.latitude, stn.longitude, unit="km"),
                    2,
                )

            if dist_km <= search_radius:
                station_results.append({
                    "station_id": stn.station_id,
                    "name": stn.name,
                    "state": stn.state,
                    "city": stn.city,
                    "address": stn.address,
                    "latitude": stn.latitude,
                    "longitude": stn.longitude,
                    "station_type": stn.station_type,
                    "is_existing": True,
                    "nearest_road_node": target_node,
                    "distance_km": dist_km,
                })

        station_results.sort(key=lambda s: s["distance_km"])
        msg = None
        if not station_results:
            msg = "No existing charging stations from the provided dataset were found within the configured search range."

        return {
            "user_location": {"latitude": latitude, "longitude": longitude},
            "search_radius_km": search_radius,
            "total_found": len(station_results),
            "stations": station_results,
            "message": msg,
        }

    def calculate_live_route(
        self,
        latitude: float,
        longitude: float,
        max_station_distance_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the shortest path route from live GPS coordinates to the nearest
        EV charging station.

        Workflow:
          1. Geographic boundary validation: verify point is in Ernakulam District
          2. Coordinate validation
          3. Snap GPS coordinates to nearest road network node
          4. Query real existing stations from dataset; if reachable via Dijkstra,
             route to the nearest real station.
          5. Fallback to candidate locations if no real station is connected/reachable.
          6. Return route node IDs, [lat, lon] polyline, distance, and estimated ETA
        """
        # Step 1: Validate input coordinates first, then district boundary
        validate_coordinates(latitude, longitude)
        validate_in_ernakulam(latitude, longitude)

        # Step 2: Ensure road network is loaded
        graph, meta = self.get_network()
        if graph.num_nodes() == 0:
            raise RuntimeError("Road network is not initialized or contains no nodes.")

        # Step 3: Snap GPS coordinates to nearest road node
        try:
            snap_result = snap_coordinates_to_road(
                graph,
                latitude,
                longitude,
                max_distance_m=settings.MAX_SNAP_DISTANCE_M,
            )
        except ValueError as snap_exc:
            snap_msg = str(snap_exc)
            if "exceeding the maximum snap distance" in snap_msg:
                raise ValueError(
                    "Your location appears to be outside the coverage area of the "
                    "available road network. The nearest road node is too far from "
                    "your coordinates. Try using a location within the network area, "
                    "or use the simulated test coordinates."
                ) from snap_exc
            raise
        snapped_node_id = snap_result["nearest_node"]["id"]
        distance_to_road_m = snap_result["distance_to_road_m"]

        # Step 4: First attempt to route to nearest real existing station if on OSM/cached network
        best_station_info: Optional[Dict[str, Any]] = None
        best_dijkstra: Optional[Dict[str, Any]] = None
        min_graph_distance: float = float("inf")

        use_real_stations = (meta.data_source in ("osm", "cache")) and not self._explicit_candidates
        if use_real_stations:
            real_stations = load_ernakulam_ev_stations()
            for rstn in real_stations:
                try:
                    stn_snap = find_nearest_road_node(graph, rstn.latitude, rstn.longitude)
                    target_node = stn_snap["node_id"]
                    res = dijkstra_shortest_path(graph, source=snapped_node_id, target=target_node)
                    dist = res["total_distance"]
                    if dist != float("inf"):
                        if max_station_distance_km is not None and dist > max_station_distance_km:
                            continue
                        if dist < min_graph_distance:
                            min_graph_distance = dist
                            best_station_info = {
                                "candidate_id": rstn.station_id,
                                "name": rstn.name,
                                "address": rstn.address,
                                "city": rstn.city,
                                "latitude": rstn.latitude,
                                "longitude": rstn.longitude,
                                "nearest_road_node": target_node,
                                "road_distance_m": stn_snap["distance_m"],
                                "feasibility_score": 1.0,
                                "data_source": meta.data_source,
                                "is_existing": True,
                            }
                            best_dijkstra = res
                except Exception:
                    continue

        # Step 5: Fallback to planning candidates (sample network or when real stations unreachable)
        if best_station_info is None or best_dijkstra is None:
            candidates = self.get_feasible_candidates()
            if not candidates:
                raise LookupError("No feasible EV charging stations available in the network.")

            for cand in candidates:
                target_node = cand.nearest_road_node
                if target_node is None or not graph.has_node(target_node):
                    continue

                res = dijkstra_shortest_path(graph, source=snapped_node_id, target=target_node)
                dist = res["total_distance"]

                if dist == float("inf"):
                    continue

                if max_station_distance_km is not None and dist > max_station_distance_km:
                    continue

                if dist < min_graph_distance:
                    min_graph_distance = dist
                    best_station_info = {
                        "candidate_id": cand.candidate_id,
                        "name": f"Planning Candidate {cand.candidate_id}",
                        "address": "Generated Planning Node",
                        "city": "Ernakulam District",
                        "latitude": cand.latitude,
                        "longitude": cand.longitude,
                        "nearest_road_node": cand.nearest_road_node,
                        "road_distance_m": cand.road_distance_m,
                        "feasibility_score": cand.feasibility_score,
                        "data_source": cand.data_source,
                        "is_existing": False,
                    }
                    best_dijkstra = res

        if best_station_info is None or best_dijkstra is None:
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
            "Live route computed: snapped to node %s (dist %.1f m) -> station %s (%s, dist %.2f km)",
            snapped_node_id,
            distance_to_road_m,
            best_station_info["candidate_id"],
            "existing" if best_station_info.get("is_existing") else "candidate",
            min_graph_distance,
        )

        return {
            "user_location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "snapped_node": snapped_node_id,
            "distance_to_snapped_node_m": distance_to_road_m,
            "station": best_station_info,
            "route": {
                "node_ids": path_nodes,
                "coordinates": coordinates,
                "distance_km": round(min_graph_distance, 3),
                "estimated_eta_minutes": estimated_eta,
            },
            "data_source": self._metadata.data_source if self._metadata else None,
        }


# Singleton instance for application lifecycle
_routing_service_instance: Optional[RoutingService] = None


def get_routing_service() -> RoutingService:
    """Dependency provider for RoutingService singleton."""
    global _routing_service_instance
    if _routing_service_instance is None:
        _routing_service_instance = RoutingService()
    return _routing_service_instance
