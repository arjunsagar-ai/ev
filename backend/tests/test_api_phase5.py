"""Integration and API tests for Phase 5A Minimum Dominating Set endpoint."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.gis.models import RoadNetworkMetadata
from app.gis.osm_loader import build_sample_road_network
from app.services.routing_service import get_routing_service


@pytest.fixture(autouse=True)
def setup_sample_routing_service():
    """Ensure routing service uses deterministic sample network for API tests."""
    graph, source = build_sample_road_network()
    meta = RoadNetworkMetadata(
        data_source=source,
        num_nodes=graph.num_nodes(),
        num_edges=graph.num_edges(),
        load_time_seconds=0.01,
    )
    service = get_routing_service()
    service.set_network(graph, meta)
    yield service


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestPhase5MDSAPI:
    """Tests for POST /api/optimize/dominating-set endpoint."""

    def test_post_dominating_set_default_params(self, client):
        resp = client.post("/api/optimize/dominating-set", json={})
        assert resp.status_code == 200
        data = resp.json()

        # Validate response schema
        assert "selected_stations" in data
        assert "selected_count" in data
        assert "candidate_count" in data
        assert "total_demand_nodes" in data
        assert "covered_demand_nodes" in data
        assert "coverage_percentage" in data
        assert "coverage_radius_km" in data
        assert data["algorithm"] == "greedy_mds_approximation"

        assert data["selected_count"] > 0
        assert len(data["selected_stations"]) == data["selected_count"]

        # Validate station item structure
        for station in data["selected_stations"]:
            assert "candidate_id" in station
            assert "node_id" in station
            assert "latitude" in station
            assert "longitude" in station
            assert station["feasible"] is True

    def test_post_dominating_set_custom_radius(self, client):
        resp = client.post(
            "/api/optimize/dominating-set",
            json={"coverage_radius_km": 1.5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["coverage_radius_km"] == 1.5
        assert data["selected_count"] > 0

    def test_post_dominating_set_max_stations(self, client):
        resp = client.post(
            "/api/optimize/dominating-set",
            json={"max_stations": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected_count"] == 1
        assert len(data["selected_stations"]) == 1

    def test_post_dominating_set_min_feasibility_score(self, client):
        resp = client.post(
            "/api/optimize/dominating-set",
            json={"min_feasibility_score": 0.40},
        )
        assert resp.status_code == 200
        data = resp.json()
        for station in data["selected_stations"]:
            assert station["feasibility_score"] >= 0.40

    def test_post_dominating_set_invalid_radius_rejected(self, client):
        resp = client.post(
            "/api/optimize/dominating-set",
            json={"coverage_radius_km": -2.0},
        )
        assert resp.status_code in (400, 422)

    def test_post_dominating_set_invalid_score_rejected(self, client):
        resp = client.post(
            "/api/optimize/dominating-set",
            json={"min_feasibility_score": 1.8},
        )
        assert resp.status_code in (400, 422)

    def test_openapi_spec_includes_mds_endpoint(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/api/optimize/dominating-set" in schema["paths"]
        assert "post" in schema["paths"]["/api/optimize/dominating-set"]
