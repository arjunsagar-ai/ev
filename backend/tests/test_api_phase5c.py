"""Integration and API tests for Phase 5C: Prim MST Infrastructure Optimization Endpoint."""
import logging
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.routing_service import get_routing_service

client = TestClient(app)


class TestInfrastructureAPI:
    """Test suite for POST /api/optimize/infrastructure."""

    def test_post_infrastructure_success_with_station_ids(self):
        """Item 12: Successful infrastructure optimization with explicit MDS station IDs."""
        rs = get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 3
        s_ids = [c.candidate_id for c in candidates[:3]]

        payload = {
            "station_ids": s_ids,
            "cost_metric": "network_distance_km",
        }
        response = client.post("/api/optimize/infrastructure", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "prim_mst"
        assert data["cost_metric"] == "network_distance_km"
        assert data["station_count"] == 3
        assert data["connected_station_count"] == 3
        assert data["mst_edge_count"] == 2
        assert data["total_cost_km"] > 0
        assert len(data["stations"]) == 3
        assert len(data["edges"]) == 2
        assert data["unconnected_station_ids"] == []

        for edge in data["edges"]:
            assert "from_station_id" in edge
            assert "to_station_id" in edge
            assert edge["cost_km"] > 0
            assert isinstance(edge["path_coordinates"], list)

    def test_post_infrastructure_single_station(self):
        """Single station returns zero cost and zero edges."""
        rs = get_routing_service()
        candidates = rs.get_feasible_candidates()
        s1 = candidates[0].candidate_id

        payload = {"station_ids": [s1]}
        response = client.post("/api/optimize/infrastructure", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["station_count"] == 1
        assert data["connected_station_count"] == 1
        assert data["mst_edge_count"] == 0
        assert data["total_cost_km"] == 0.0
        assert data["edges"] == []
        assert data["connected_station_ids"] == [s1]

    def test_post_infrastructure_dynamic_mds_resolution(self):
        """When station_ids is omitted, dynamically runs MDS and returns MST."""
        payload = {
            "coverage_radius_km": 0.5,
            "cost_metric": "network_distance_km",
        }
        response = client.post("/api/optimize/infrastructure", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "prim_mst"
        assert data["station_count"] > 0
        assert data["connected_station_count"] > 0

    def test_post_infrastructure_empty_station_list(self):
        """Empty station list returns HTTP 200 with 0 stations and 0 edges."""
        payload = {"station_ids": []}
        response = client.post("/api/optimize/infrastructure", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["station_count"] == 0
        assert data["connected_station_count"] == 0
        assert data["mst_edge_count"] == 0
        assert data["total_cost_km"] == 0.0
        assert data["stations"] == []
        assert data["edges"] == []

    def test_post_infrastructure_invalid_station_id_returns_400(self):
        """Item 13: Non-existent station ID returns HTTP 400 Bad Request."""
        payload = {
            "station_ids": ["NON-EXISTENT-CANDIDATE-ID"],
        }
        response = client.post("/api/optimize/infrastructure", json=payload)

        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_post_infrastructure_validation_negative_radius_rejected(self):
        """Item 13: Invalid parameters (e.g. negative radius) return 422 Unprocessable Entity."""
        payload = {
            "coverage_radius_km": -5.0,
        }
        response = client.post("/api/optimize/infrastructure", json=payload)
        assert response.status_code == 422

    def test_post_infrastructure_geographic_metric(self):
        """Geographic distance cost metric is supported."""
        rs = get_routing_service()
        candidates = rs.get_feasible_candidates()
        s_ids = [c.candidate_id for c in candidates[:2]]

        payload = {
            "station_ids": s_ids,
            "cost_metric": "geographic_distance_km",
        }
        response = client.post("/api/optimize/infrastructure", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["cost_metric"] == "geographic_distance_km"
        assert data["mst_edge_count"] == 1

    def test_openapi_schema_registers_infrastructure_endpoint(self):
        """OpenAPI spec documents /api/optimize/infrastructure endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        assert "/api/optimize/infrastructure" in paths
        assert "post" in paths["/api/optimize/infrastructure"]

    def test_privacy_no_gps_logged_in_infrastructure(self, caplog):
        """Item 14: Server logs do not persist or leak raw GPS coordinates during MST calculation."""
        with caplog.at_level(logging.INFO):
            payload = {
                "coverage_radius_km": 0.5,
            }
            response = client.post("/api/optimize/infrastructure", json=payload)
            assert response.status_code == 200

        for record in caplog.records:
            assert "gps_history" not in record.message.lower()
