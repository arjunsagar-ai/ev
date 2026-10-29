"""Integration and end-to-end REST API tests for Phase 3 endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.routing_service import get_routing_service
from app.gis.osm_loader import build_sample_road_network
from app.gis.models import RoadNetworkMetadata


@pytest.fixture(autouse=True)
def setup_sample_routing_service():
    """Ensure routing service uses deterministic sample network for all API tests."""
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


class TestPhase3APIEndpoints:
    """Tests for Phase 3 REST API endpoints."""

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "EV Charging Network Optimization" in data["message"]

    def test_api_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.9.0"

    def test_api_gis_network_endpoint(self, client):
        resp = client.get("/api/gis/network")
        assert resp.status_code == 200
        data = resp.json()
        assert data["node_count"] == 15
        assert data["edge_count"] == 20
        assert data["data_source"] == "sample"

    def test_post_live_route_success(self, client):
        payload = {
            "latitude": 10.001,
            "longitude": 76.302,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Validate top-level response structure
        assert "user_location" in data
        assert "snapped_node" in data
        assert "distance_to_snapped_node_m" in data
        assert "station" in data
        assert "route" in data

        # Validate user location
        assert data["user_location"]["latitude"] == 10.001
        assert data["user_location"]["longitude"] == 76.302

        # Validate snapped node
        assert data["snapped_node"] is not None
        assert data["distance_to_snapped_node_m"] > 0

        # Validate station details
        station = data["station"]
        assert station["candidate_id"].startswith("CAND-")
        assert station["latitude"] is not None
        assert station["longitude"] is not None
        assert station["nearest_road_node"] is not None

        # Validate route details (Dijkstra)
        route = data["route"]
        assert isinstance(route["node_ids"], list)
        assert len(route["node_ids"]) >= 1
        assert isinstance(route["coordinates"], list)
        assert len(route["coordinates"]) == len(route["node_ids"])
        for pt in route["coordinates"]:
            assert len(pt) == 2
            assert isinstance(pt[0], float)
            assert isinstance(pt[1], float)
        assert route["distance_km"] >= 0.0
        assert route["estimated_eta_minutes"] is not None
        assert route["estimated_eta_minutes"] >= 0.0

    def test_post_live_route_with_max_station_distance(self, client):
        # 10.0 km radius is sufficient to reach stations in the sample network
        payload = {
            "latitude": 10.001,
            "longitude": 76.302,
            "max_station_distance_km": 10.0,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["route"]["distance_km"] <= 10.0

    def test_post_live_route_distance_too_small_returns_404(self, client):
        payload = {
            "latitude": 10.000,
            "longitude": 76.300,
            "max_station_distance_km": 0.1,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "No reachable charging station found" in data["detail"]

    def test_post_live_route_invalid_latitude_rejected(self, client):
        payload = {
            "latitude": 95.0,  # Invalid
            "longitude": 76.302,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code in (400, 422)

    def test_post_live_route_invalid_longitude_rejected(self, client):
        payload = {
            "latitude": 10.001,
            "longitude": 195.0,  # Invalid
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code in (400, 422)

    def test_post_live_route_nan_rejected(self, client):
        # Sending null or invalid float
        payload = {
            "latitude": "NaN",
            "longitude": 76.302,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code in (400, 422)

    def test_post_live_route_non_numeric_rejected(self, client):
        payload = {
            "latitude": "ten_point_one",
            "longitude": 76.302,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code == 422

    def test_post_live_route_far_away_snapping_error(self, client):
        payload = {
            "latitude": 10.150,  # Inside Ernakulam, but far from sample network nodes (~10.0, 76.3)
            "longitude": 76.250,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code == 400
        data = resp.json()
        assert "outside the coverage area" in data["detail"]

    def test_post_live_route_outside_ernakulam_rejected(self, client):
        payload = {
            "latitude": 8.8932,  # Kollam (outside Ernakulam)
            "longitude": 76.6141,
        }
        resp = client.post("/api/route/live", json=payload)
        assert resp.status_code == 400
        data = resp.json()
        assert "This project currently supports Ernakulam district, Kerala only." in data["detail"]

    def test_swagger_and_openapi_docs_accessible(self, client):
        resp_docs = client.get("/docs")
        assert resp_docs.status_code == 200

        resp_openapi = client.get("/openapi.json")
        assert resp_openapi.status_code == 200
        schema = resp_openapi.json()
        assert "/api/health" in schema["paths"]
        assert "/api/gis/network" in schema["paths"]
        assert "/api/route/live" in schema["paths"]
