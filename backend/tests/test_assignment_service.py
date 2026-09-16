"""Unit tests for AssignmentService (Hungarian EV-to-station assignment)."""
import pytest

from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import build_sample_road_network
from app.graph.weighted_graph import WeightedGraph
from app.services.assignment_service import AssignmentService, UNREACHABLE_PENALTY
from app.services.routing_service import RoutingService
from app.services.station_optimization_service import StationOptimizationService


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
def assignment_service(sample_network):
    """Provides an isolated AssignmentService with sample network."""
    graph, meta = sample_network
    rs = RoutingService()
    rs.set_network(graph, meta)
    sos = StationOptimizationService(routing_service=rs)
    return AssignmentService(
        routing_service=rs,
        station_optimization_service=sos,
    )


class TestAssignmentService:
    """Test suite for AssignmentService."""

    def test_assignment_with_mds_resolved_stations(self, assignment_service):
        """When station_ids is None, Hungarian assigns to MDS-selected stations."""
        evs = [
            {"ev_id": "EV-01", "latitude": 10.001, "longitude": 76.302},
            {"ev_id": "EV-02", "latitude": 10.005, "longitude": 76.308},
        ]
        # Use coverage_radius_km=0.5 so MDS selects multiple stations across sample network
        result = assignment_service.assign_evs_to_stations(
            evs=evs,
            coverage_radius_km=0.5,
        )

        assert result["algorithm"] == "hungarian"
        assert result["ev_count"] == 2
        assert result["assigned_count"] == 2
        assert result["unassigned_count"] == 0
        assert len(result["assignments"]) == 2
        assert result["total_cost_km"] > 0
        assert result["cost_metric"] in ["network_distance_km", "geographic_distance_km"]

        # Check assignment structure
        for a in result["assignments"]:
            assert a["ev_id"] in ["EV-01", "EV-02"]
            assert a["station_id"].startswith("CAND-")
            assert a["cost_km"] >= 0
            assert len(a["path_coordinates"]) >= 2

    def test_equal_number_of_evs_and_stations(self, assignment_service):
        """2 EVs assigned to 2 specific stations."""
        # Query feasible candidates
        rs = assignment_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 2
        station_ids = [candidates[0].candidate_id, candidates[1].candidate_id]

        evs = [
            {"ev_id": "EV-01", "latitude": candidates[0].latitude, "longitude": candidates[0].longitude},
            {"ev_id": "EV-02", "latitude": candidates[1].latitude, "longitude": candidates[1].longitude},
        ]
        result = assignment_service.assign_evs_to_stations(evs=evs, station_ids=station_ids)

        assert result["assigned_count"] == 2
        assert result["unassigned_count"] == 0
        assert len(result["unassigned_ev_ids"]) == 0
        assert len(result["unassigned_station_ids"]) == 0

    def test_more_evs_than_stations_rectangular(self, assignment_service):
        """3 EVs competing for 1 station: 1 assigned, 2 unassigned."""
        rs = assignment_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        station_ids = [candidates[0].candidate_id]

        evs = [
            {"ev_id": "EV-01", "latitude": 10.001, "longitude": 76.301},
            {"ev_id": "EV-02", "latitude": 10.005, "longitude": 76.305},
            {"ev_id": "EV-03", "latitude": 10.008, "longitude": 76.310},
        ]
        result = assignment_service.assign_evs_to_stations(evs=evs, station_ids=station_ids)

        assert result["ev_count"] == 3
        assert result["station_count"] == 1
        assert result["assigned_count"] == 1
        assert result["unassigned_count"] == 2
        assert len(result["unassigned_ev_ids"]) == 2
        assert len(result["assignments"]) == 1

    def test_more_stations_than_evs_rectangular(self, assignment_service):
        """1 EV with 3 stations available: 1 assigned, 0 unassigned EVs, 2 unassigned stations."""
        rs = assignment_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 3
        station_ids = [c.candidate_id for c in candidates[:3]]

        evs = [
            {"ev_id": "EV-01", "latitude": 10.002, "longitude": 76.303},
        ]
        result = assignment_service.assign_evs_to_stations(evs=evs, station_ids=station_ids)

        assert result["ev_count"] == 1
        assert result["station_count"] == 3
        assert result["assigned_count"] == 1
        assert result["unassigned_count"] == 0
        assert len(result["unassigned_ev_ids"]) == 0
        assert len(result["unassigned_station_ids"]) == 2

    def test_single_ev_and_single_station(self, assignment_service):
        """1 EV and 1 station: straightforward 1:1 match."""
        rs = assignment_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        station_ids = [candidates[0].candidate_id]

        evs = [{"ev_id": "EV-SOLO", "latitude": 10.001, "longitude": 76.302}]
        result = assignment_service.assign_evs_to_stations(evs=evs, station_ids=station_ids)

        assert result["assigned_count"] == 1
        assert result["assignments"][0]["ev_id"] == "EV-SOLO"
        assert result["assignments"][0]["station_id"] == station_ids[0]

    def test_empty_ev_list(self, assignment_service):
        """Empty EV input handled safely without errors."""
        result = assignment_service.assign_evs_to_stations(evs=[])

        assert result["ev_count"] == 0
        assert result["assigned_count"] == 0
        assert result["unassigned_count"] == 0
        assert result["assignments"] == []
        assert result["total_cost_km"] == 0.0

    def test_empty_station_list(self, assignment_service):
        """Empty station list marks all EVs as unassigned."""
        evs = [{"ev_id": "EV-01", "latitude": 10.001, "longitude": 76.302}]
        result = assignment_service.assign_evs_to_stations(evs=evs, station_ids=[])

        assert result["ev_count"] == 1
        assert result["station_count"] == 0
        assert result["assigned_count"] == 0
        assert result["unassigned_count"] == 1
        assert result["unassigned_ev_ids"] == ["EV-01"]
        assert result["total_cost_km"] == 0.0

    def test_invalid_coordinates_raises_error(self, assignment_service):
        """Out of bounds or non-numeric coordinates raise ValueError/TypeError."""
        with pytest.raises(ValueError):
            assignment_service.assign_evs_to_stations(evs=[
                {"ev_id": "EV-BAD", "latitude": 999.0, "longitude": 76.302}
            ])

        with pytest.raises(ValueError):
            assignment_service.assign_evs_to_stations(evs=[
                {"ev_id": "EV-NAN", "latitude": float("nan"), "longitude": 76.302}
            ])

    def test_invalid_station_id_raises_error(self, assignment_service):
        """Non-existent station ID raises ValueError."""
        evs = [{"ev_id": "EV-01", "latitude": 10.001, "longitude": 76.302}]
        with pytest.raises(ValueError, match="not found"):
            assignment_service.assign_evs_to_stations(evs=evs, station_ids=["NON-EXISTENT-STATION"])

    def test_duplicate_ev_id_raises_error(self, assignment_service):
        """Duplicate EV IDs raise ValueError."""
        evs = [
            {"ev_id": "EV-SAME", "latitude": 10.001, "longitude": 76.302},
            {"ev_id": "EV-SAME", "latitude": 10.002, "longitude": 76.303},
        ]
        with pytest.raises(ValueError, match="Duplicate ev_id"):
            assignment_service.assign_evs_to_stations(evs=evs)

    def test_unreachable_ev_station_not_forced(self):
        """
        In a disconnected graph where an EV cannot reach a station,
        the assignment is NOT forced and the EV remains unassigned.
        """
        g = WeightedGraph(directed=False)
        # Component 1: Node A with station
        g.add_node("A", lat=10.0, lon=76.0)
        # Component 2: Node B with EV (no edge between A and B)
        g.add_node("B", lat=10.1, lon=76.1)

        candidate = CandidateLocation(
            candidate_id="CAND-DISCONNECTED",
            latitude=10.0,
            longitude=76.0,
            nearest_road_node="A",
            road_distance_m=0.0,
            feasible=True,
            feasibility_score=0.9,
        )
        service = AssignmentService()

        evs = [{"ev_id": "EV-ISOLATED", "latitude": 10.1, "longitude": 76.1}]
        result = service.assign_evs_to_stations(
            evs=evs,
            station_ids=["CAND-DISCONNECTED"],
            graph=g,
            candidates=[candidate],
            cost_metric="network_distance_km",
        )

        assert result["assigned_count"] == 0
        assert result["unassigned_count"] == 1
        assert result["unassigned_ev_ids"] == ["EV-ISOLATED"]
        assert result["total_cost_km"] == 0.0

    def test_service_does_not_modify_underlying_graph(self, sample_network, assignment_service):
        """Underlying road graph remains immutable during assignment execution."""
        graph, _ = sample_network
        init_nodes = graph.num_nodes()
        init_edges = graph.num_edges()

        evs = [
            {"ev_id": "EV-01", "latitude": 10.001, "longitude": 76.302},
            {"ev_id": "EV-02", "latitude": 10.005, "longitude": 76.308},
        ]
        assignment_service.assign_evs_to_stations(evs=evs)

        assert graph.num_nodes() == init_nodes
        assert graph.num_edges() == init_edges
