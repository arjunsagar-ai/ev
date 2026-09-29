"""
Unit tests for CapacityService (Phase 6 — Ford-Fulkerson max-flow).

All tests use deterministic, injected CapacityService instances.
No singletons are touched.
"""
import pytest

from app.services.capacity_service import CapacityService, DEFAULT_STATION_CAPACITY


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def service() -> CapacityService:
    return CapacityService()


def _evs(*specs):
    """Build EV list from (ev_id, demand) tuples. demand defaults to 1."""
    result = []
    for spec in specs:
        if isinstance(spec, str):
            result.append({"ev_id": spec, "demand_units": 1})
        else:
            ev_id, demand = spec
            result.append({"ev_id": ev_id, "demand_units": demand})
    return result


def _stations(*specs):
    """Build station list from (station_id, capacity) tuples. capacity defaults to DEFAULT."""
    result = []
    for spec in specs:
        if isinstance(spec, str):
            result.append({"station_id": spec, "capacity_units": DEFAULT_STATION_CAPACITY})
        else:
            st_id, cap = spec
            result.append({"station_id": st_id, "capacity_units": cap})
    return result


# ---------------------------------------------------------------------------
# 1. Basic max-flow: single EV, single station, demand <= capacity
# ---------------------------------------------------------------------------


def test_single_ev_single_station_fully_satisfied(service):
    """Single EV fully absorbed by single station with ample capacity."""
    evs = _evs(("ev1", 2))
    stations = _stations(("st1", 5))
    result = service.analyze_capacity(evs=evs, stations=stations)

    assert result["max_flow"] == 2.0
    assert result["total_demand"] == 2.0
    assert result["network_status"] == "capacity_available"
    assert result["bottleneck_station_ids"] == []


# ---------------------------------------------------------------------------
# 2. Demand equals capacity → fully_satisfied
# ---------------------------------------------------------------------------


def test_demand_equals_capacity_fully_satisfied(service):
    evs = _evs(("ev1", 3))
    stations = _stations(("st1", 3))
    result = service.analyze_capacity(evs=evs, stations=stations)

    assert result["max_flow"] == 3.0
    assert result["network_status"] == "fully_satisfied"
    assert result["bottleneck_station_ids"] == ["st1"]


# ---------------------------------------------------------------------------
# 3. Demand exceeds capacity → capacity_limited
# ---------------------------------------------------------------------------


def test_demand_exceeds_capacity_limited(service):
    evs = _evs(("ev1", 5), ("ev2", 5))
    stations = _stations(("st1", 4))
    result = service.analyze_capacity(evs=evs, stations=stations)

    assert result["network_status"] == "capacity_limited"
    assert result["max_flow"] < result["total_demand"]
    assert result["max_flow"] == 4.0


# ---------------------------------------------------------------------------
# 4. Multiple EVs, multiple stations, demand satisfied with spare capacity
# ---------------------------------------------------------------------------


def test_multiple_evs_multiple_stations_capacity_available(service):
    evs = _evs(("ev1", 1), ("ev2", 1))
    stations = _stations(("st1", 5), ("st2", 5))
    result = service.analyze_capacity(evs=evs, stations=stations)

    assert result["network_status"] == "capacity_available"
    assert result["max_flow"] == 2.0
    assert result["total_demand"] == 2.0


# ---------------------------------------------------------------------------
# 5. Bottleneck detection: station saturated
# ---------------------------------------------------------------------------


def test_bottleneck_detection_saturated_station(service):
    evs = _evs(("ev1", 3))
    stations = _stations(("st1", 3))
    result = service.analyze_capacity(evs=evs, stations=stations)

    util = {s["station_id"]: s for s in result["station_utilization"]}
    assert util["st1"]["is_saturated"] is True
    assert "st1" in result["bottleneck_station_ids"]


# ---------------------------------------------------------------------------
# 6. Non-bottleneck station not in bottleneck list
# ---------------------------------------------------------------------------


def test_non_saturated_station_not_bottleneck(service):
    evs = _evs(("ev1", 1))
    stations = _stations(("st1", 10))
    result = service.analyze_capacity(evs=evs, stations=stations)

    util = {s["station_id"]: s for s in result["station_utilization"]}
    assert util["st1"]["is_saturated"] is False
    assert result["bottleneck_station_ids"] == []


# ---------------------------------------------------------------------------
# 7. Assignments restrict flow (ev1→st1, ev2→st2 only)
# ---------------------------------------------------------------------------


def test_assignments_restrict_ev_station_edges(service):
    evs = _evs(("ev1", 2), ("ev2", 2))
    stations = _stations(("st1", 5), ("st2", 5))
    assignments = [{"ev_id": "ev1", "station_id": "st1"}, {"ev_id": "ev2", "station_id": "st2"}]
    result = service.analyze_capacity(evs=evs, stations=stations, assignments=assignments)

    # All demand should be satisfied
    assert result["max_flow"] == 4.0
    # Only ev1→st1 and ev2→st2 edges should appear in flow edges
    for edge in result["flow_edges"]:
        if edge["from_ev_id"] == "ev1":
            assert edge["to_station_id"] == "st1"
        if edge["from_ev_id"] == "ev2":
            assert edge["to_station_id"] == "st2"


# ---------------------------------------------------------------------------
# 8. Assignments that block flow → capacity_limited
# ---------------------------------------------------------------------------


def test_assignments_can_cause_capacity_limited(service):
    """If assignments only connect to a low-capacity station, demand is limited."""
    evs = _evs(("ev1", 5))
    stations = _stations(("st1", 2), ("st2", 10))
    # ev1 can only go to st1 (capacity 2), not st2 (capacity 10)
    assignments = [{"ev_id": "ev1", "station_id": "st1"}]
    result = service.analyze_capacity(evs=evs, stations=stations, assignments=assignments)

    assert result["network_status"] == "capacity_limited"
    assert result["max_flow"] == 2.0


# ---------------------------------------------------------------------------
# 9. No assignments — full bipartite, max flow is min(total_demand, total_capacity)
# ---------------------------------------------------------------------------


def test_no_assignments_full_bipartite(service):
    evs = _evs(("ev1", 3), ("ev2", 3))
    stations = _stations(("st1", 10))
    result = service.analyze_capacity(evs=evs, stations=stations, assignments=None)

    # Total demand 6, station cap 10 → all demand can flow
    assert result["max_flow"] == 6.0
    assert result["network_status"] == "capacity_available"


# ---------------------------------------------------------------------------
# 10. flow_edges strips virtual SOURCE/SINK edges
# ---------------------------------------------------------------------------


def test_flow_edges_only_ev_to_station(service):
    evs = _evs(("ev1", 1))
    stations = _stations(("st1", 5))
    result = service.analyze_capacity(evs=evs, stations=stations)

    for edge in result["flow_edges"]:
        assert "__SOURCE__" not in edge["from_ev_id"]
        assert "__SINK__" not in edge["to_station_id"]
        assert edge["from_ev_id"] == "ev1"
        assert edge["to_station_id"] == "st1"


# ---------------------------------------------------------------------------
# 11. station_utilization has correct fields and simulated_capacity flag
# ---------------------------------------------------------------------------


def test_station_utilization_fields(service):
    evs = _evs(("ev1", 2))
    stations = _stations(("st1", 5))
    result = service.analyze_capacity(evs=evs, stations=stations)

    util = result["station_utilization"][0]
    assert util["station_id"] == "st1"
    assert util["available_capacity"] == 5.0
    assert util["utilized_capacity"] == 2.0
    assert util["unused_capacity"] == 3.0
    assert util["utilization_pct"] == pytest.approx(40.0)
    assert util["simulated_capacity"] is True


# ---------------------------------------------------------------------------
# 12. Result always contains a 'note' disclaimer
# ---------------------------------------------------------------------------


def test_result_contains_note_disclaimer(service):
    evs = _evs("ev1")
    stations = _stations("st1")
    result = service.analyze_capacity(evs=evs, stations=stations)

    assert "note" in result
    note = result["note"].lower()
    assert "simulated" in note or "estimated" in note


# ---------------------------------------------------------------------------
# 13. Empty EV list raises ValueError
# ---------------------------------------------------------------------------


def test_empty_evs_raises_value_error(service):
    with pytest.raises(ValueError, match="At least one EV"):
        service.analyze_capacity(evs=[], stations=_stations("st1"))


# ---------------------------------------------------------------------------
# 14. Empty station list raises ValueError
# ---------------------------------------------------------------------------


def test_empty_stations_raises_value_error(service):
    with pytest.raises(ValueError, match="At least one station"):
        service.analyze_capacity(evs=_evs("ev1"), stations=[])


# ---------------------------------------------------------------------------
# 15. Duplicate ev_id raises ValueError
# ---------------------------------------------------------------------------


def test_duplicate_ev_id_raises_value_error(service):
    evs = [{"ev_id": "ev1", "demand_units": 1}, {"ev_id": "ev1", "demand_units": 2}]
    with pytest.raises(ValueError, match="Duplicate ev_id"):
        service.analyze_capacity(evs=evs, stations=_stations("st1"))


# ---------------------------------------------------------------------------
# 16. Duplicate station_id raises ValueError
# ---------------------------------------------------------------------------


def test_duplicate_station_id_raises_value_error(service):
    stations = [
        {"station_id": "st1", "capacity_units": 3},
        {"station_id": "st1", "capacity_units": 5},
    ]
    with pytest.raises(ValueError, match="Duplicate station_id"):
        service.analyze_capacity(evs=_evs("ev1"), stations=stations)


# ---------------------------------------------------------------------------
# 17. algorithm field is correct
# ---------------------------------------------------------------------------


def test_algorithm_field_value(service):
    evs = _evs("ev1")
    stations = _stations("st1")
    result = service.analyze_capacity(evs=evs, stations=stations)

    assert result["algorithm"] == "ford_fulkerson_edmonds_karp"
