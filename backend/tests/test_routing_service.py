"""Unit tests for RoutingService and station selection logic."""
import math
import pytest

from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import build_sample_road_network
from app.graph.weighted_graph import WeightedGraph
from app.services.routing_service import RoutingService


@pytest.fixture
def sample_network():
    """Provides a deterministic sample road network."""
    graph, source = build_sample_road_network()
    meta = RoadNetworkMetadata(
        data_source=source,
        num_nodes=graph.num_nodes(),
        num_edges=graph.num_edges(),
        load_time_seconds=0.01,
    )
    return graph, meta


@pytest.fixture
def service_with_sample(sample_network):
    """Provides an isolated RoutingService pre-configured with the sample network."""
    graph, meta = sample_network
    srv = RoutingService()
    srv.set_network(graph, meta)
    return srv


class TestRoutingServiceCore:
    """Test core routing orchestration, snapping, and station selection."""

    def test_network_loading_and_summary(self, service_with_sample):
        summary = service_with_sample.get_network_summary()
        assert summary["node_count"] == 15
        assert summary["edge_count"] == 20
        assert summary["data_source"] == "sample"

    def test_candidates_generated_and_cached(self, service_with_sample):
        candidates = service_with_sample.get_feasible_candidates()
        assert len(candidates) > 0
        for cand in candidates:
            assert cand.feasible is True
            assert cand.nearest_road_node is not None

    def test_calculate_live_route_success(self, service_with_sample):
        """
        User is at (10.001, 76.302) near node N01 / N02.
        Service should snap, select a feasible station, and return Dijkstra route.
        """
        res = service_with_sample.calculate_live_route(latitude=10.001, longitude=76.302)

        # Check user location and snapping
        assert res["user_location"]["latitude"] == 10.001
        assert res["user_location"]["longitude"] == 76.302
        assert res["snapped_node"] in service_with_sample._graph.nodes()
        assert res["distance_to_snapped_node_m"] > 0.0

        # Check station selection
        assert res["station"]["candidate_id"] is not None
        assert res["station"]["latitude"] is not None
        assert res["station"]["nearest_road_node"] is not None

        # Check Dijkstra route
        route = res["route"]
        assert len(route["node_ids"]) >= 1
        assert route["node_ids"][0] == res["snapped_node"]
        assert route["node_ids"][-1] == res["station"]["nearest_road_node"]
        assert len(route["coordinates"]) == len(route["node_ids"])
        assert route["distance_km"] >= 0.0
        assert route["estimated_eta_minutes"] is not None
        assert route["estimated_eta_minutes"] >= 0.0

    def test_live_route_at_exact_station_node(self, service_with_sample):
        """
        When user GPS is exactly on the station node, distance should be 0.0 and path has 1 node.
        """
        cand = service_with_sample.get_feasible_candidates()[0]
        res = service_with_sample.calculate_live_route(
            latitude=cand.latitude,
            longitude=cand.longitude,
        )
        assert res["snapped_node"] == cand.nearest_road_node
        assert res["station"]["candidate_id"] == cand.candidate_id
        assert res["route"]["distance_km"] == 0.0
        assert res["route"]["node_ids"] == [cand.nearest_road_node]

    def test_max_station_distance_km_respected(self, service_with_sample):
        """
        Restricting max_station_distance_km to less than the distance to nearest station
        should raise LookupError. (From N01 at 10.000, 76.300, nearest station is ~0.33 km away).
        """
        with pytest.raises(LookupError, match="No reachable charging station found"):
            service_with_sample.calculate_live_route(
                latitude=10.000,
                longitude=76.300,
                max_station_distance_km=0.1,
            )

    def test_unreachable_station_handling(self, sample_network):
        """
        If a candidate station is in a completely disconnected component, it should be
        reported as unreachable or skipped in favor of reachable stations.
        """
        graph, meta = sample_network
        # Add an isolated node and station
        graph.add_node("IsolatedStationNode", lat=10.020, lon=76.350)
        isolated_cand = CandidateLocation(
            candidate_id="CAND-ISOLATED",
            latitude=10.020,
            longitude=76.350,
            nearest_road_node="IsolatedStationNode",
            feasible=True,
        )

        srv = RoutingService()
        # Set only the isolated candidate
        srv.set_network(graph, meta, candidates=[isolated_cand])

        # Routing from the main network (e.g. N01) to isolated candidate should raise LookupError
        with pytest.raises(LookupError, match="No reachable charging station found"):
            srv.calculate_live_route(latitude=10.000, longitude=76.300)

    def test_empty_candidate_list_raises_lookup_error(self, sample_network):
        graph, meta = sample_network
        srv = RoutingService()
        srv.set_network(graph, meta, candidates=[])

        with pytest.raises(LookupError, match="No feasible EV charging stations available"):
            srv.calculate_live_route(latitude=10.000, longitude=76.300)

    def test_far_away_gps_exceeds_max_snap_distance(self, service_with_sample):
        """Point 100 km away should exceed max snapping distance."""
        with pytest.raises(ValueError, match="outside the coverage area"):
            service_with_sample.calculate_live_route(latitude=11.500, longitude=77.500)

    def test_invalid_coordinates_rejected(self, service_with_sample):
        with pytest.raises(ValueError, match="latitude must be between"):
            service_with_sample.calculate_live_route(latitude=95.0, longitude=76.0)

        with pytest.raises(ValueError, match="longitude must be between"):
            service_with_sample.calculate_live_route(latitude=10.0, longitude=-190.0)

        with pytest.raises(ValueError, match="must not be NaN"):
            service_with_sample.calculate_live_route(latitude=float("nan"), longitude=76.0)

        with pytest.raises(ValueError, match="must not be infinite"):
            service_with_sample.calculate_live_route(latitude=10.0, longitude=float("inf"))

    def test_privacy_no_persistent_user_location(self, service_with_sample):
        """
        Verify that user GPS coordinates are request-time only and no history
        list/log is persisted on the service instance.
        """
        service_with_sample.calculate_live_route(latitude=10.001, longitude=76.302)
        # Service instance must not store history attributes
        assert not hasattr(service_with_sample, "user_history")
        assert not hasattr(service_with_sample, "location_history")
        assert not hasattr(service_with_sample, "last_user_location")
