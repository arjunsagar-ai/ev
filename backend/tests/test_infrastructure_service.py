"""Unit tests for InfrastructureService (Prim's MST for EV station connections)."""
import pytest

from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import build_sample_road_network
from app.graph.weighted_graph import WeightedGraph
from app.services.infrastructure_service import InfrastructureService
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
def infrastructure_service(sample_network):
    """Provides an isolated InfrastructureService with sample network."""
    graph, meta = sample_network
    rs = RoutingService()
    rs.set_network(graph, meta)
    sos = StationOptimizationService(routing_service=rs)
    return InfrastructureService(
        routing_service=rs,
        station_optimization_service=sos,
    )


class TestInfrastructureService:
    """Test suite for InfrastructureService."""

    def test_one_station_zero_mst_cost(self, infrastructure_service):
        """Item 1: One station -> zero MST cost, 0 edges, 1 connected station."""
        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 1
        s1 = candidates[0].candidate_id

        result = infrastructure_service.optimize_infrastructure(station_ids=[s1])

        assert result["algorithm"] == "prim_mst"
        assert result["station_count"] == 1
        assert result["connected_station_count"] == 1
        assert result["mst_edge_count"] == 0
        assert result["total_cost_km"] == 0.0
        assert len(result["edges"]) == 0
        assert result["connected_station_ids"] == [s1]
        assert result["unconnected_station_ids"] == []
        assert result["stations"][0]["connected"] is True

    def test_two_connected_stations(self, infrastructure_service):
        """Item 2: Two connected stations -> exactly 1 MST edge and correct total cost."""
        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 2
        s1 = candidates[0].candidate_id
        s2 = candidates[1].candidate_id

        result = infrastructure_service.optimize_infrastructure(station_ids=[s1, s2])

        assert result["station_count"] == 2
        assert result["connected_station_count"] == 2
        assert result["mst_edge_count"] == 1
        assert result["total_cost_km"] > 0
        assert len(result["edges"]) == 1
        edge = result["edges"][0]
        assert {edge["from_station_id"], edge["to_station_id"]} == {s1, s2}
        assert edge["cost_km"] == result["total_cost_km"]
        assert len(edge["path_coordinates"]) >= 2
        assert set(result["connected_station_ids"]) == {s1, s2}
        assert result["unconnected_station_ids"] == []

    def test_multiple_connected_stations(self, infrastructure_service):
        """Item 3: Multiple connected stations -> connected tree spanning all stations."""
        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 3
        station_ids = [c.candidate_id for c in candidates[:3]]

        result = infrastructure_service.optimize_infrastructure(station_ids=station_ids)

        assert result["station_count"] == 3
        assert result["connected_station_count"] == 3
        assert result["mst_edge_count"] == 2
        assert result["total_cost_km"] > 0
        assert len(result["edges"]) == 2
        assert set(result["connected_station_ids"]) == set(station_ids)
        assert result["unconnected_station_ids"] == []

    def test_correct_mst_edge_count(self, infrastructure_service):
        """Item 4: Correct MST edge count (|V| - 1 for connected graph)."""
        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 4
        station_ids = [c.candidate_id for c in candidates[:4]]

        result = infrastructure_service.optimize_infrastructure(station_ids=station_ids)

        # For 4 connected stations, tree must contain 3 edges
        assert result["mst_edge_count"] == 3
        assert len(result["edges"]) == 3

    def test_correct_total_mst_cost(self, infrastructure_service):
        """Item 5: Correct total MST cost equals sum of individual edge costs."""
        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 3
        station_ids = [c.candidate_id for c in candidates[:3]]

        result = infrastructure_service.optimize_infrastructure(station_ids=station_ids)

        edge_sum = sum(edge["cost_km"] for edge in result["edges"])
        assert round(edge_sum, 3) == pytest.approx(result["total_cost_km"], abs=1e-3)

    def test_selected_station_id_mapping(self, infrastructure_service):
        """Item 6: Selected station ID mapping resolves coordinates and nearest road nodes."""
        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        c0 = candidates[0]
        c1 = candidates[1]

        result = infrastructure_service.optimize_infrastructure(
            station_ids=[c0.candidate_id, c1.candidate_id]
        )

        station_map = {s["station_id"]: s for s in result["stations"]}
        assert station_map[c0.candidate_id]["latitude"] == c0.latitude
        assert station_map[c0.candidate_id]["longitude"] == c0.longitude
        assert station_map[c0.candidate_id]["nearest_road_node"] == c0.nearest_road_node

        assert station_map[c1.candidate_id]["latitude"] == c1.latitude
        assert station_map[c1.candidate_id]["longitude"] == c1.longitude
        assert station_map[c1.candidate_id]["nearest_road_node"] == c1.nearest_road_node

    def test_invalid_station_id_raises_value_error(self, infrastructure_service):
        """Item 7: Non-existent station ID raises ValueError."""
        with pytest.raises(ValueError, match="not found among feasible candidates"):
            infrastructure_service.optimize_infrastructure(
                station_ids=["NON-EXISTENT-CANDIDATE-ID"]
            )

    def test_duplicate_station_ids(self, infrastructure_service):
        """Item 8: Duplicate station IDs are deduplicated cleanly without self-loops."""
        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        s1 = candidates[0].candidate_id
        s2 = candidates[1].candidate_id

        # Pass duplicates of s1 and s2
        result = infrastructure_service.optimize_infrastructure(
            station_ids=[s1, s1, s2, s2, s1]
        )

        assert result["station_count"] == 2
        assert result["connected_station_count"] == 2
        assert result["mst_edge_count"] == 1
        assert len(result["stations"]) == 2

    def test_empty_station_list(self, infrastructure_service):
        """Item 9: Empty station list returns valid empty result."""
        result = infrastructure_service.optimize_infrastructure(station_ids=[])

        assert result["station_count"] == 0
        assert result["connected_station_count"] == 0
        assert result["mst_edge_count"] == 0
        assert result["total_cost_km"] == 0.0
        assert result["stations"] == []
        assert result["edges"] == []
        assert result["connected_station_ids"] == []
        assert result["unconnected_station_ids"] == []

    def test_disconnected_graph(self):
        """
        Item 10: Disconnected graph does not fabricate impossible edges and
        reports unreachable stations in unconnected_station_ids.
        """
        # Graph with two disconnected components
        g = WeightedGraph(directed=False)
        # Component 1
        g.add_node("Road-A1", lat=10.000, lon=76.300)
        g.add_node("Road-A2", lat=10.005, lon=76.305)
        g.add_edge("Road-A1", "Road-A2", weight=1.5)

        # Component 2 (isolated)
        g.add_node("Road-B1", lat=10.050, lon=76.350)

        candidates = [
            CandidateLocation(
                candidate_id="CAND-A1",
                latitude=10.000,
                longitude=76.300,
                nearest_road_node="Road-A1",
                feasible=True,
                feasibility_score=0.9,
            ),
            CandidateLocation(
                candidate_id="CAND-A2",
                latitude=10.005,
                longitude=76.305,
                nearest_road_node="Road-A2",
                feasible=True,
                feasibility_score=0.85,
            ),
            CandidateLocation(
                candidate_id="CAND-B1",
                latitude=10.050,
                longitude=76.350,
                nearest_road_node="Road-B1",
                feasible=True,
                feasibility_score=0.8,
            ),
        ]

        service = InfrastructureService()
        result = service.optimize_infrastructure(
            station_ids=["CAND-A1", "CAND-A2", "CAND-B1"],
            graph=g,
            candidates=candidates,
        )

        assert result["station_count"] == 3
        # CAND-A1 and CAND-A2 are connected; CAND-B1 is isolated
        assert result["connected_station_count"] == 2
        assert result["mst_edge_count"] == 1
        assert "CAND-B1" in result["unconnected_station_ids"]
        assert set(result["connected_station_ids"]) == {"CAND-A1", "CAND-A2"}

        station_map = {s["station_id"]: s for s in result["stations"]}
        assert station_map["CAND-A1"]["connected"] is True
        assert station_map["CAND-A2"]["connected"] is True
        assert station_map["CAND-B1"]["connected"] is False

    def test_graph_immutability(self, sample_network, infrastructure_service):
        """Item 11: Underlying road graph remains immutable after MST computation."""
        graph, _ = sample_network
        init_nodes = graph.num_nodes()
        init_edges = graph.num_edges()

        rs = infrastructure_service._get_routing_service()
        candidates = rs.get_feasible_candidates()
        station_ids = [c.candidate_id for c in candidates[:3]]

        infrastructure_service.optimize_infrastructure(station_ids=station_ids)

        assert graph.num_nodes() == init_nodes
        assert graph.num_edges() == init_edges

    def test_dynamic_mds_resolution_when_station_ids_omitted(self, infrastructure_service):
        """When station_ids is None, dynamically resolves MDS stations and runs Prim MST."""
        result = infrastructure_service.optimize_infrastructure(
            station_ids=None,
            coverage_radius_km=0.5,
        )

        assert result["algorithm"] == "prim_mst"
        assert result["station_count"] > 0
        assert result["connected_station_count"] > 0
        assert result["mst_edge_count"] >= 0
