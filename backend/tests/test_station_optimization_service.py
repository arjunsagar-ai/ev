"""Unit tests for StationOptimizationService (MDS EV station placement)."""
import pytest

from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import build_sample_road_network
from app.graph.weighted_graph import WeightedGraph
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
def optimization_service(sample_network):
    """Provides an isolated StationOptimizationService with sample network."""
    graph, meta = sample_network
    rs = RoutingService()
    rs.set_network(graph, meta)
    return StationOptimizationService(routing_service=rs)


class TestStationOptimizationService:
    """Test suite for StationOptimizationService."""

    def test_mds_service_executes_successfully(self, optimization_service):
        result = optimization_service.optimize_station_placement()

        assert "selected_stations" in result
        assert "selected_count" in result
        assert "coverage_percentage" in result
        assert "algorithm" in result
        assert result["algorithm"] == "greedy_mds_approximation"
        assert result["selected_count"] > 0
        assert result["coverage_percentage"] > 0.0

    def test_only_feasible_candidates_selected(self, optimization_service):
        result = optimization_service.optimize_station_placement()

        for st in result["selected_stations"]:
            assert st["feasible"] is True
            assert st["candidate_id"].startswith("CAND-")
            assert st["latitude"] is not None
            assert st["longitude"] is not None

    def test_selected_candidate_ids_map_correctly_to_graph_nodes(self, sample_network):
        graph, meta = sample_network
        rs = RoutingService()
        rs.set_network(graph, meta)
        service = StationOptimizationService(routing_service=rs)

        result = service.optimize_station_placement()

        for st in result["selected_stations"]:
            assert graph.has_node(st["node_id"])

    def test_max_stations_parameter_limits_output(self, optimization_service):
        result = optimization_service.optimize_station_placement(max_stations=2)

        assert len(result["selected_stations"]) <= 2
        assert result["selected_count"] <= 2

    def test_min_feasibility_score_filtering(self, optimization_service):
        # Using an impossibly high score should filter out all candidates
        result = optimization_service.optimize_station_placement(min_feasibility_score=0.999)

        assert result["selected_count"] == 0
        assert len(result["selected_stations"]) == 0
        assert result["coverage_percentage"] == 0.0

    def test_empty_candidate_set_handled_safely(self, sample_network):
        graph, meta = sample_network
        rs = RoutingService()
        rs.set_network(graph, meta, candidates=[])
        service = StationOptimizationService(routing_service=rs)

        result = service.optimize_station_placement(candidates=[])

        assert result["selected_count"] == 0
        assert result["selected_stations"] == []
        assert result["coverage_percentage"] == 0.0

    def test_service_does_not_modify_underlying_graph(self, sample_network):
        graph, meta = sample_network
        rs = RoutingService()
        rs.set_network(graph, meta)
        service = StationOptimizationService(routing_service=rs)

        nodes_before = graph.num_nodes()
        edges_before = graph.num_edges()

        service.optimize_station_placement()

        assert graph.num_nodes() == nodes_before
        assert graph.num_edges() == edges_before

    def test_invalid_parameters_raise_value_error(self, optimization_service):
        with pytest.raises(ValueError, match="coverage_radius_km must be strictly positive"):
            optimization_service.optimize_station_placement(coverage_radius_km=-1.0)

        with pytest.raises(ValueError, match="coverage_radius_km must be strictly positive"):
            optimization_service.optimize_station_placement(coverage_radius_km=0.0)

        with pytest.raises(ValueError, match="min_feasibility_score must be between"):
            optimization_service.optimize_station_placement(min_feasibility_score=-0.1)

        with pytest.raises(ValueError, match="min_feasibility_score must be between"):
            optimization_service.optimize_station_placement(min_feasibility_score=1.5)

        with pytest.raises(ValueError, match="max_stations must be a positive integer"):
            optimization_service.optimize_station_placement(max_stations=0)

        with pytest.raises(ValueError, match="max_stations must be a positive integer"):
            optimization_service.optimize_station_placement(max_stations=-3)
