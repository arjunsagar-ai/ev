"""Integration and API tests for Phase 5B: Hungarian EV Assignment Endpoint."""
import logging
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.routing_service import get_routing_service

client = TestClient(app)


class TestAssignmentAPI:
    """Test suite for POST /api/optimize/assignment."""

    def test_post_assignment_success_with_mds_resolved_stations(self):
        """Standard request assigning 2 EVs to MDS-resolved charging stations."""
        payload = {
            "evs": [
                {"ev_id": "EV-ALPHA", "latitude": 10.002, "longitude": 76.303},
                {"ev_id": "EV-BETA", "latitude": 10.006, "longitude": 76.309},
            ],
            "coverage_radius_km": 0.5,
            "cost_metric": "network_distance_km",
        }
        response = client.post("/api/optimize/assignment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "hungarian"
        assert data["ev_count"] == 2
        assert data["assigned_count"] == 2
        assert data["unassigned_count"] == 0
        assert len(data["assignments"]) == 2
        assert data["total_cost_km"] > 0
        assert data["cost_metric"] in ["network_distance_km", "geographic_distance_km"]

        assigned_ev_ids = [a["ev_id"] for a in data["assignments"]]
        assert "EV-ALPHA" in assigned_ev_ids
        assert "EV-BETA" in assigned_ev_ids

    def test_post_assignment_with_explicit_station_ids(self):
        """Request specifying exact station IDs."""
        rs = get_routing_service()
        candidates = rs.get_feasible_candidates()
        assert len(candidates) >= 2
        s1 = candidates[0].candidate_id
        s2 = candidates[1].candidate_id

        payload = {
            "evs": [
                {"ev_id": "EV-01", "latitude": candidates[0].latitude, "longitude": candidates[0].longitude},
                {"ev_id": "EV-02", "latitude": candidates[1].latitude, "longitude": candidates[1].longitude},
            ],
            "station_ids": [s1, s2],
        }
        response = client.post("/api/optimize/assignment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_count"] == 2
        assert len(data["unassigned_ev_ids"]) == 0

    def test_post_assignment_rectangular_more_evs_than_stations(self):
        """More EVs than stations results in unassigned EVs in the API response."""
        rs = get_routing_service()
        candidates = rs.get_feasible_candidates()
        s1 = candidates[0].candidate_id

        payload = {
            "evs": [
                {"ev_id": "EV-1", "latitude": 10.001, "longitude": 76.301},
                {"ev_id": "EV-2", "latitude": 10.003, "longitude": 76.303},
                {"ev_id": "EV-3", "latitude": 10.005, "longitude": 76.305},
            ],
            "station_ids": [s1],
        }
        response = client.post("/api/optimize/assignment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ev_count"] == 3
        assert data["station_count"] == 1
        assert data["assigned_count"] == 1
        assert data["unassigned_count"] == 2
        assert len(data["unassigned_ev_ids"]) == 2

    def test_post_assignment_explicit_geographic_metric(self):
        """Explicit geographic_distance_km metric requested."""
        payload = {
            "evs": [
                {"ev_id": "EV-GEO", "latitude": 10.002, "longitude": 76.303},
            ],
            "cost_metric": "geographic_distance_km",
        }
        response = client.post("/api/optimize/assignment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["cost_metric"] == "geographic_distance_km"
        assert data["assigned_count"] == 1

    def test_post_assignment_invalid_coordinates_rejected(self):
        """Invalid coordinates (out of range) are rejected with 422."""
        payload = {
            "evs": [
                {"ev_id": "EV-BAD", "latitude": 100.0, "longitude": 76.303},
            ]
        }
        response = client.post("/api/optimize/assignment", json=payload)
        assert response.status_code == 422

    def test_post_assignment_invalid_station_id_returns_400(self):
        """Non-existent station ID returns HTTP 400 Bad Request."""
        payload = {
            "evs": [
                {"ev_id": "EV-01", "latitude": 10.002, "longitude": 76.303},
            ],
            "station_ids": ["NON-EXISTENT-STATION"],
        }
        response = client.post("/api/optimize/assignment", json=payload)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_post_assignment_empty_ev_list(self):
        """Empty EV list returns HTTP 200 with 0 assignments."""
        payload = {"evs": []}
        response = client.post("/api/optimize/assignment", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["ev_count"] == 0
        assert data["assigned_count"] == 0
        assert data["assignments"] == []

    def test_openapi_schema_registers_assignment_endpoint(self):
        """OpenAPI spec documents /api/optimize/assignment endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        assert "/api/optimize/assignment" in paths
        assert "post" in paths["/api/optimize/assignment"]

    def test_privacy_no_gps_logged_in_assignment(self, caplog):
        """Server logs do not print raw coordinates during Hungarian assignment."""
        with caplog.at_level(logging.INFO):
            payload = {
                "evs": [
                    {"ev_id": "PRIVACY-EV", "latitude": 10.002, "longitude": 76.303},
                ],
            }
            response = client.post("/api/optimize/assignment", json=payload)
            assert response.status_code == 200

        for record in caplog.records:
            # Check that raw GPS pair is not in log records
            assert "10.002" not in record.message
            assert "76.303" not in record.message
