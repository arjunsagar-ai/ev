"""
Unit tests for EV charging stations dataset loader and Ernakulam filter.
"""
import pytest
from app.gis.ernakulam_boundary import is_point_in_ernakulam
from app.gis.ev_station_loader import (
    RealEVStation,
    get_ev_stations_summary,
    load_ernakulam_ev_stations,
)


class TestEVStationLoader:
    """Validate loading, filtering, and deduplication of real EV charging station dataset."""

    def test_summary_metrics(self):
        summary = get_ev_stations_summary()
        assert summary["total_source_records"] == 1547
        assert summary["kerala_records"] > 0
        assert summary["missing_coordinates_count"] == 6
        assert summary["duplicate_candidates_count"] == 7
        assert summary["ernakulam_records_raw"] == 32
        assert summary["final_usable_count"] == 25

    def test_loaded_stations_all_in_ernakulam(self):
        stations = load_ernakulam_ev_stations(force_reload=True)
        assert len(stations) == 25

        for stn in stations:
            assert isinstance(stn, RealEVStation)
            assert stn.station_id.startswith("REAL-EV-")
            assert stn.latitude is not None and stn.longitude is not None
            assert stn.name != ""
            assert stn.is_existing is True
            # Assert every single station is strictly inside Ernakulam District
            assert is_point_in_ernakulam(stn.latitude, stn.longitude) is True

    def test_stations_from_other_districts_excluded(self):
        """Confirm that known stations in other districts are excluded."""
        stations = load_ernakulam_ev_stations()
        station_names = [s.name.lower() for s in stations]

        # Stations in Kollam, Thrissur, Trivandrum, Kozhikode must not be included
        assert not any("kollam" in name for name in station_names)
        assert not any("viyyur" in name for name in station_names)
        assert not any("nemom" in name for name in station_names)
        assert not any("calicut" in name for name in station_names)
        assert not any("hilite mall" in name for name in station_names)

    def test_deduplication_toggle(self):
        raw_stations = load_ernakulam_ev_stations(deduplicate=False, force_reload=True)
        assert len(raw_stations) == 32

        deduped = load_ernakulam_ev_stations(deduplicate=True, force_reload=True)
        assert len(deduped) == 25
