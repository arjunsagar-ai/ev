"""
End-to-end pipeline integration tests (Phase 7).

Verifies the complete workflow:
    EV/User location → snap → Dijkstra → candidates → MDS →
    Hungarian → Prim MST → Ford-Fulkerson capacity

Tests use the deterministic sample road network and focus on
integration boundaries between stages.  They do NOT duplicate
the exhaustive unit tests in each algorithm module.
"""
import pytest

from app.algorithms.dijkstra import dijkstra_shortest_path
from app.algorithms.dominating_set import minimum_dominating_set
from app.algorithms.ford_fulkerson import ford_fulkerson_max_flow
from app.algorithms.hungarian import hungarian_algorithm
from app.algorithms.prim import prim_mst
from app.gis.candidate_generator import (
    filter_feasible_candidates,
    generate_candidates_from_graph,
)
from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import build_sample_road_network
from app.gis.spatial_index import snap_coordinates_to_road
from app.graph.weighted_graph import WeightedGraph
from app.services.assignment_service import AssignmentService
from app.services.capacity_service import CapacityService
from app.services.infrastructure_service import InfrastructureService
from app.services.routing_service import RoutingService
from app.services.station_optimization_service import StationOptimizationService


# ────────────────────── fixtures ──────────────────────────────────────────

@pytest.fixture
def sample_graph():
    """Build the deterministic sample road network."""
    graph, source = build_sample_road_network()
    assert source == "sample"
    return graph


@pytest.fixture
def sample_service(sample_graph):
    """RoutingService loaded with the sample network."""
    meta = RoadNetworkMetadata(
        data_source="sample",
        num_nodes=sample_graph.num_nodes(),
        num_edges=sample_graph.num_edges(),
    )
    svc = RoutingService()
    svc.set_network(sample_graph, meta)
    return svc


# ────────────── stage 1: snap + Dijkstra (routing) ────────────────────────

class TestStage1_SnapAndRoute:
    """GPS → snap → Dijkstra route to nearest station."""

    def test_snap_and_route(self, sample_service):
        """Full routing pipeline on sample network returns a valid route."""
        result = sample_service.calculate_live_route(
            latitude=10.003, longitude=76.310,
        )
        assert result["snapped_node"] is not None
        assert result["route"]["distance_km"] >= 0
        assert len(result["route"]["coordinates"]) >= 1
        assert result["station"]["candidate_id"] is not None
        # Phase 7: data_source should be surfaced
        assert result["data_source"] == "sample"

    def test_route_eta_is_estimate(self, sample_service):
        """ETA must be present and non-negative (average-speed estimate)."""
        result = sample_service.calculate_live_route(
            latitude=10.003, longitude=76.310,
        )
        eta = result["route"]["estimated_eta_minutes"]
        assert eta is not None
        assert eta >= 0


# ────────────── stage 2: MDS station placement ────────────────────────────

class TestStage2_MDS:
    """Candidates → MDS greedy approximation → selected stations."""

    def test_mds_selects_stations(self, sample_graph):
        """MDS should select at least one station from sample network."""
        candidates = generate_candidates_from_graph(
            sample_graph, data_source="sample", node_selection="all",
        )
        assert len(candidates) > 0

        # Run greedy MDS directly
        result = minimum_dominating_set(
            sample_graph,
            coverage_radius=2.0,
            candidate_nodes=[c.nearest_road_node for c in candidates],
            demand_nodes=list(sample_graph.nodes()),
        )
        assert len(result["selected_nodes"]) > 0
        assert result["coverage_percentage"] > 0

    def test_mds_output_feeds_hungarian(self, sample_service):
        """MDS-selected stations can be used as Hungarian assignment targets."""
        opt_svc = StationOptimizationService(routing_service=sample_service)
        mds_result = opt_svc.optimize_station_placement()
        assert len(mds_result["selected_stations"]) > 0

        # These station IDs should be usable by Hungarian
        station_ids = [s["candidate_id"] for s in mds_result["selected_stations"]]
        assert all(isinstance(sid, str) for sid in station_ids)


# ────────────── stage 3: Hungarian assignment ─────────────────────────────

class TestStage3_Hungarian:
    """MDS stations + EVs → Hungarian optimal assignment."""

    def test_hungarian_assigns_evs_to_mds_stations(self, sample_service):
        """EVs can be assigned to MDS-selected stations via Hungarian."""
        opt_svc = StationOptimizationService(routing_service=sample_service)
        asgn_svc = AssignmentService(
            routing_service=sample_service,
            station_optimization_service=opt_svc,
        )

        # Simulate 2 EVs at known network locations
        ev_inputs = [
            {"ev_id": "EV_A", "latitude": 10.000, "longitude": 76.300},
            {"ev_id": "EV_B", "latitude": 10.006, "longitude": 76.320},
        ]

        result = asgn_svc.assign_evs_to_stations(evs=ev_inputs)
        assert result["algorithm"] == "hungarian"
        assert len(result["assignments"]) > 0
        assert result["total_cost_km"] >= 0

        # Every assignment should have valid fields
        for a in result["assignments"]:
            assert "ev_id" in a
            assert "station_id" in a
            assert "cost_km" in a
            assert a["cost_km"] >= 0


# ────────────── stage 4: Prim MST infrastructure ──────────────────────────

class TestStage4_PrimMST:
    """MDS stations → Prim MST spanning connection network."""

    def test_prim_on_mds_stations(self, sample_service):
        """Prim MST should connect MDS-selected stations via road network."""
        opt_svc = StationOptimizationService(routing_service=sample_service)
        infra_svc = InfrastructureService(
            routing_service=sample_service,
            station_optimization_service=opt_svc,
        )

        result = infra_svc.optimize_infrastructure()
        assert result["algorithm"] == "prim_mst"
        assert result["station_count"] > 0
        assert result["total_cost_km"] >= 0
        assert result["cost_metric"] == "network_distance_km"


# ──────────── stage 5: Ford-Fulkerson capacity ────────────────────────────

class TestStage5_FordFulkerson:
    """Hungarian assignments + station capacity → Ford-Fulkerson max-flow."""

    def test_capacity_analysis_on_assignments(self, sample_service):
        """Ford-Fulkerson capacity model receives data from Hungarian output."""
        # Step 1: get assignment
        opt_svc = StationOptimizationService(routing_service=sample_service)
        asgn_svc = AssignmentService(
            routing_service=sample_service,
            station_optimization_service=opt_svc,
        )

        ev_inputs = [
            {"ev_id": "EV_1", "latitude": 10.000, "longitude": 76.300},
            {"ev_id": "EV_2", "latitude": 10.006, "longitude": 76.310},
        ]
        asgn_result = asgn_svc.assign_evs_to_stations(evs=ev_inputs)

        # Step 2: build capacity inputs from assignment output
        cap_svc = CapacityService()
        ev_list = []
        station_set = set()
        assignments = []
        for a in asgn_result["assignments"]:
            ev_list.append({"ev_id": a["ev_id"], "demand_units": 1})
            station_set.add(a["station_id"])
            assignments.append({
                "ev_id": a["ev_id"],
                "station_id": a["station_id"],
            })

        station_list = [
            {"station_id": sid, "capacity_units": 3}
            for sid in station_set
        ]

        cap_result = cap_svc.analyze_capacity(
            evs=ev_list,
            stations=station_list,
            assignments=assignments,
        )

        assert cap_result["algorithm"] == "ford_fulkerson_edmonds_karp"
        assert cap_result["max_flow"] >= 0
        assert cap_result["total_demand"] == len(ev_list)
        assert cap_result["network_status"] in (
            "fully_satisfied", "capacity_limited", "capacity_available",
        )
        assert isinstance(cap_result["station_utilization"], list)
        assert isinstance(cap_result["bottleneck_station_ids"], list)


# ──────── stage 6: complete end-to-end pipeline ───────────────────────────

class TestFullPipeline:
    """Complete pipeline: location → all 5 algorithms → capacity result."""

    def test_end_to_end(self, sample_service):
        """The complete pipeline runs without errors on the sample network."""
        # 1. Route
        route_result = sample_service.calculate_live_route(
            latitude=10.003, longitude=76.310,
        )
        assert route_result["route"]["distance_km"] >= 0

        # 2. MDS
        opt_svc = StationOptimizationService(routing_service=sample_service)
        mds_result = opt_svc.optimize_station_placement()
        selected_stations = mds_result["selected_stations"]
        assert len(selected_stations) > 0

        # 3. Hungarian
        asgn_svc = AssignmentService(
            routing_service=sample_service,
            station_optimization_service=opt_svc,
        )
        ev_inputs = [
            {"ev_id": "EV_1", "latitude": 10.000, "longitude": 76.300},
            {"ev_id": "EV_2", "latitude": 10.006, "longitude": 76.320},
        ]
        asgn_result = asgn_svc.assign_evs_to_stations(evs=ev_inputs)
        assert len(asgn_result["assignments"]) > 0

        # 4. Prim MST
        infra_svc = InfrastructureService(
            routing_service=sample_service,
            station_optimization_service=opt_svc,
        )
        infra_result = infra_svc.optimize_infrastructure()
        assert infra_result["total_cost_km"] >= 0

        # 5. Ford-Fulkerson
        cap_svc = CapacityService()
        ev_list = [
            {"ev_id": a["ev_id"], "demand_units": 1}
            for a in asgn_result["assignments"]
        ]
        station_ids = set(a["station_id"] for a in asgn_result["assignments"])
        station_list = [
            {"station_id": sid, "capacity_units": 3}
            for sid in station_ids
        ]
        assignments = [
            {"ev_id": a["ev_id"], "station_id": a["station_id"]}
            for a in asgn_result["assignments"]
        ]

        cap_result = cap_svc.analyze_capacity(
            evs=ev_list, stations=station_list, assignments=assignments,
        )
        assert cap_result["network_status"] in (
            "fully_satisfied", "capacity_limited", "capacity_available",
        )
        # With demand=2, capacity=3 per station → should be satisfiable
        assert cap_result["max_flow"] == cap_result["total_demand"]

    def test_data_source_propagation(self, sample_service):
        """data_source should be 'sample' throughout the sample network pipeline."""
        result = sample_service.calculate_live_route(
            latitude=10.003, longitude=76.310,
        )
        assert result["data_source"] == "sample"
        assert result["station"]["data_source"] == "sample"

        summary = sample_service.get_network_summary()
        assert summary["data_source"] == "sample"


# ──────── API-level integration ───────────────────────────────────────────

class TestAPIIntegration:
    """Verify all API endpoints return valid responses via TestClient."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_network_info_has_data_source(self, client):
        resp = client.get("/api/gis/network")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] in ("osm", "cache", "sample")

    def test_route_returns_data_source(self, client):
        resp = client.post("/api/route/live", json={
            "latitude": 10.003, "longitude": 76.310,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "data_source" in data
        assert data["data_source"] in ("osm", "cache", "sample")

    def test_dominating_set_endpoint(self, client):
        resp = client.post("/api/optimize/dominating-set", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["algorithm"] == "greedy_mds_approximation"
        assert len(data["selected_stations"]) > 0

    def test_assignment_endpoint(self, client):
        resp = client.post("/api/optimize/assignment", json={
            "evs": [
                {"ev_id": "EV1", "latitude": 10.000, "longitude": 76.300},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["algorithm"] == "hungarian"

    def test_infrastructure_endpoint(self, client):
        resp = client.post("/api/optimize/infrastructure", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["algorithm"] == "prim_mst"
        assert data["cost_metric"] == "network_distance_km"

    def test_capacity_endpoint(self, client):
        resp = client.post("/api/optimize/capacity", json={
            "evs": [{"ev_id": "EV1", "demand_units": 1}],
            "stations": [{"station_id": "ST1", "capacity_units": 5}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["algorithm"] == "ford_fulkerson_edmonds_karp"
        assert data["network_status"] in (
            "fully_satisfied", "capacity_limited", "capacity_available",
        )

    def test_openapi_spec(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        paths = spec.get("paths", {})
        assert "/api/route/live" in paths
        assert "/api/optimize/dominating-set" in paths
        assert "/api/optimize/assignment" in paths
        assert "/api/optimize/infrastructure" in paths
        assert "/api/optimize/capacity" in paths
