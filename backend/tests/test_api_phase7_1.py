"""
Integration tests for Phase 7.1 endpoints:
  - GET /api/gis/boundary
  - GET /api/stations/existing
  - POST /api/stations/nearby
  - POST /api/route/live with Ernakulam boundary validation
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestPhase71API:
    """Test Ernakulam district boundary and real EV station endpoints."""

    def test_get_district_boundary(self, client):
        resp = client.get("/api/gis/boundary")
        assert resp.status_code == 200
        data = resp.json()
        assert "geometry" in data or "type" in data
        geom = data.get("geometry", data)
        assert geom.get("type") in ("Polygon", "MultiPolygon")

    def test_get_existing_stations(self, client):
        resp = client.get("/api/stations/existing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_stations"] == 25
        assert "Ernakulam" in data["project_area"]
        assert len(data["stations"]) == 25
        for stn in data["stations"]:
            assert stn["is_existing"] is True
            assert stn["station_id"].startswith("REAL-EV-")

    def test_post_nearby_stations_kochi(self, client):
        payload = {
            "latitude": 9.9816,
            "longitude": 76.2999,
            "radius_km": 15.0,
        }
        resp = client.post("/api/stations/nearby", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] > 0
        assert len(data["stations"]) == data["total_found"]
        # Distance must be ascending
        distances = [s["distance_km"] for s in data["stations"]]
        assert distances == sorted(distances)

    def test_post_nearby_stations_outside_ernakulam_rejected(self, client):
        payload = {
            "latitude": 8.8932,  # Kollam
            "longitude": 76.6141,
        }
        resp = client.post("/api/stations/nearby", json=payload)
        assert resp.status_code == 400
        data = resp.json()
        assert "This project currently supports Ernakulam district, Kerala only." in data["detail"]

    def test_network_info_surfaces_project_area(self, client):
        resp = client.get("/api/gis/network")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("project_area") == "Ernakulam District"

    def test_gis_search_kochi(self, client):
        resp = client.get("/api/gis/search?q=kochi")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] > 0
        assert any("kochi" in r["name"].lower() for r in data["results"])

    def test_gis_search_aluva(self, client):
        resp = client.get("/api/gis/search?q=aluva")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] > 0
        assert any("aluva" in r["name"].lower() for r in data["results"])

    def test_gis_search_empty_query_returns_prominent_places(self, client):
        resp = client.get("/api/gis/search?q=")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] > 0
