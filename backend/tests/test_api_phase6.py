"""
API integration tests for Phase 6 — POST /api/optimize/capacity endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ENDPOINT = "/api/optimize/capacity"

# ---------------------------------------------------------------------------
# Minimal valid payload helpers
# ---------------------------------------------------------------------------


def _payload(evs=None, stations=None, assignments=None):
    body = {
        "evs": evs or [{"ev_id": "ev1", "demand_units": 1}],
        "stations": stations or [{"station_id": "st1", "capacity_units": 5}],
    }
    if assignments is not None:
        body["assignments"] = assignments
    return body


# ---------------------------------------------------------------------------
# Test 1: Basic 200 success response
# ---------------------------------------------------------------------------


def test_capacity_endpoint_returns_200():
    response = client.post(ENDPOINT, json=_payload())
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test 2: Response schema has required top-level fields
# ---------------------------------------------------------------------------


def test_response_schema_has_required_fields():
    response = client.post(ENDPOINT, json=_payload())
    data = response.json()
    required = {
        "algorithm", "network_status", "max_flow", "total_demand",
        "station_utilization", "bottleneck_station_ids", "flow_edges", "note",
    }
    assert required.issubset(data.keys())


# ---------------------------------------------------------------------------
# Test 3: Algorithm field is ford_fulkerson
# ---------------------------------------------------------------------------


def test_algorithm_field_is_ford_fulkerson():
    response = client.post(ENDPOINT, json=_payload())
    assert response.json()["algorithm"] == "ford_fulkerson_edmonds_karp"


# ---------------------------------------------------------------------------
# Test 4: network_status is valid string
# ---------------------------------------------------------------------------


def test_network_status_is_valid():
    response = client.post(ENDPOINT, json=_payload())
    valid = {"fully_satisfied", "capacity_limited", "capacity_available"}
    assert response.json()["network_status"] in valid


# ---------------------------------------------------------------------------
# Test 5: max_flow <= total_demand
# ---------------------------------------------------------------------------


def test_max_flow_lte_total_demand():
    payload = _payload(
        evs=[{"ev_id": "ev1", "demand_units": 3}, {"ev_id": "ev2", "demand_units": 4}],
        stations=[{"station_id": "st1", "capacity_units": 2}],
    )
    data = client.post(ENDPOINT, json=payload).json()
    assert data["max_flow"] <= data["total_demand"]


# ---------------------------------------------------------------------------
# Test 6: capacity_limited when demand exceeds station capacity
# ---------------------------------------------------------------------------


def test_capacity_limited_when_demand_exceeds_station():
    payload = _payload(
        evs=[{"ev_id": "ev1", "demand_units": 10}],
        stations=[{"station_id": "st1", "capacity_units": 3}],
    )
    data = client.post(ENDPOINT, json=payload).json()
    assert data["network_status"] == "capacity_limited"
    assert data["max_flow"] == 3.0


# ---------------------------------------------------------------------------
# Test 7: capacity_available when surplus capacity exists
# ---------------------------------------------------------------------------


def test_capacity_available_when_surplus_capacity():
    payload = _payload(
        evs=[{"ev_id": "ev1", "demand_units": 1}],
        stations=[{"station_id": "st1", "capacity_units": 10}],
    )
    data = client.post(ENDPOINT, json=payload).json()
    assert data["network_status"] == "capacity_available"


# ---------------------------------------------------------------------------
# Test 8: fully_satisfied when demand equals capacity
# ---------------------------------------------------------------------------


def test_fully_satisfied_when_demand_equals_capacity():
    payload = _payload(
        evs=[{"ev_id": "ev1", "demand_units": 5}],
        stations=[{"station_id": "st1", "capacity_units": 5}],
    )
    data = client.post(ENDPOINT, json=payload).json()
    assert data["network_status"] == "fully_satisfied"


# ---------------------------------------------------------------------------
# Test 9: Bottleneck station in response when saturated
# ---------------------------------------------------------------------------


def test_bottleneck_station_ids_populated_when_saturated():
    payload = _payload(
        evs=[{"ev_id": "ev1", "demand_units": 5}],
        stations=[{"station_id": "st1", "capacity_units": 5}],
    )
    data = client.post(ENDPOINT, json=payload).json()
    assert "st1" in data["bottleneck_station_ids"]


# ---------------------------------------------------------------------------
# Test 10: station_utilization contains simulated_capacity flag
# ---------------------------------------------------------------------------


def test_station_utilization_has_simulated_flag():
    response = client.post(ENDPOINT, json=_payload())
    for util in response.json()["station_utilization"]:
        assert util["simulated_capacity"] is True


# ---------------------------------------------------------------------------
# Test 11: Response note contains disclaimer text
# ---------------------------------------------------------------------------


def test_response_note_contains_disclaimer():
    response = client.post(ENDPOINT, json=_payload())
    note = response.json()["note"].lower()
    assert "simulated" in note or "estimated" in note


# ---------------------------------------------------------------------------
# Test 12: With assignments — only assigned edges used
# ---------------------------------------------------------------------------


def test_assignments_restrict_flow_edges():
    payload = _payload(
        evs=[{"ev_id": "ev1", "demand_units": 2}, {"ev_id": "ev2", "demand_units": 2}],
        stations=[{"station_id": "st1", "capacity_units": 5}, {"station_id": "st2", "capacity_units": 5}],
        assignments=[{"ev_id": "ev1", "station_id": "st1"}, {"ev_id": "ev2", "station_id": "st2"}],
    )
    data = client.post(ENDPOINT, json=payload).json()
    assert data["max_flow"] == 4.0
    for edge in data["flow_edges"]:
        if edge["from_ev_id"] == "ev1":
            assert edge["to_station_id"] == "st1"
        if edge["from_ev_id"] == "ev2":
            assert edge["to_station_id"] == "st2"


# ---------------------------------------------------------------------------
# Test 13: Empty EVs list returns 422
# ---------------------------------------------------------------------------


def test_empty_evs_returns_422():
    payload = {"evs": [], "stations": [{"station_id": "st1", "capacity_units": 5}]}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 14: Empty stations list returns 422
# ---------------------------------------------------------------------------


def test_empty_stations_returns_422():
    payload = {"evs": [{"ev_id": "ev1", "demand_units": 1}], "stations": []}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 15: Missing evs key returns 422
# ---------------------------------------------------------------------------


def test_missing_evs_returns_422():
    payload = {"stations": [{"station_id": "st1", "capacity_units": 5}]}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 16: Missing stations key returns 422
# ---------------------------------------------------------------------------


def test_missing_stations_returns_422():
    payload = {"evs": [{"ev_id": "ev1", "demand_units": 1}]}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 17: Duplicate station_id in request returns 400
# ---------------------------------------------------------------------------


def test_duplicate_station_id_returns_400():
    payload = {
        "evs": [{"ev_id": "ev1", "demand_units": 1}],
        "stations": [
            {"station_id": "st1", "capacity_units": 3},
            {"station_id": "st1", "capacity_units": 5},
        ],
    }
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 400
    assert "Duplicate station_id" in response.json()["detail"]
