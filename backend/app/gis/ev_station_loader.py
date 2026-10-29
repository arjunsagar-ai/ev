"""
EV Charging Station Dataset Loader & Ernakulam Geographic Filter.

Ingests the provided national dataset (ev-charging-stations-india.csv),
normalizes coordinate fields (mapping the CSV's 'lattitude' typo to 'latitude'),
filters strictly to Ernakulam District via point-in-polygon containment,
identifies and handles missing coordinates and duplicate records,
and returns clean existing EV charging station records.
"""
import csv
import logging
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from app.gis.ernakulam_boundary import is_point_in_ernakulam

logger = logging.getLogger(__name__)

_DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ev-charging-stations-india.csv",
)


@dataclass
class RealEVStation:
    """Represents an existing real-world EV charging station from the dataset."""

    station_id: str
    name: str
    state: str
    city: str
    address: str
    latitude: float
    longitude: float
    station_type: str
    is_existing: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Cached stations list
_CACHED_STATIONS: Optional[List[RealEVStation]] = None
_CACHED_SUMMARY: Optional[Dict[str, Any]] = None


def load_ernakulam_ev_stations(
    csv_path: Optional[str] = None,
    deduplicate: bool = True,
    force_reload: bool = False,
) -> List[RealEVStation]:
    """
    Load, validate, filter, and deduplicate EV charging stations inside Ernakulam District.

    Parameters
    ----------
    csv_path : str, optional
        Path to the CSV dataset file.
    deduplicate : bool
        Whether to deduplicate co-located records with matching coordinates/names.
    force_reload : bool
        Whether to bypass the in-memory cache.

    Returns
    -------
    list of RealEVStation
    """
    global _CACHED_STATIONS
    if _CACHED_STATIONS is not None and not force_reload and csv_path is None:
        return _CACHED_STATIONS

    summary = get_ev_stations_summary(csv_path=csv_path, deduplicate=deduplicate)
    stations = summary["stations"]

    if csv_path is None:
        _CACHED_STATIONS = stations

    return stations


def get_ev_stations_summary(
    csv_path: Optional[str] = None,
    deduplicate: bool = True,
) -> Dict[str, Any]:
    """
    Parse the CSV and produce complete inspection statistics required by Phase 7.1:
      - total source records
      - Kerala rows
      - Ernakulam rows (point-in-boundary)
      - rows with missing/invalid coordinates
      - duplicate candidates
      - final usable station count
    """
    path = csv_path or _DEFAULT_CSV_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(f"EV charging station dataset not found at {path}")

    total_records = 0
    kerala_records = 0
    missing_coords_count = 0
    invalid_coords_count = 0
    raw_ernakulam_stations: List[Dict[str, Any]] = []

    with open(path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=1):
            total_records += 1

            name = (row.get("name") or "").strip()
            state = (row.get("state") or "").strip()
            city = (row.get("city") or "").strip()
            address = (row.get("address") or "").strip()
            # Map CSV's 'lattitude' column name to latitude
            lat_raw = (row.get("lattitude") or "").strip().rstrip(",")
            lon_raw = (row.get("longitude") or "").strip().rstrip(",")
            stn_type = (row.get("type") or "").strip()

            # Track records tagged or referring to Kerala
            if state.lower() == "kerala" or "kerala" in address.lower() or "kerala" in city.lower():
                kerala_records += 1

            # Missing coordinate validation
            if not lat_raw or not lon_raw:
                missing_coords_count += 1
                continue

            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
            except ValueError:
                invalid_coords_count += 1
                continue

            # Check point-in-boundary for Ernakulam District
            if is_point_in_ernakulam(lat, lon):
                raw_ernakulam_stations.append({
                    "row_index": row_idx,
                    "name": name,
                    "state": state,
                    "city": city,
                    "address": address,
                    "latitude": lat,
                    "longitude": lon,
                    "type": stn_type,
                })

    # Duplicate detection: group by rounded coordinate proximity (~10m) and clean name
    usable_stations: List[RealEVStation] = []
    seen_coords: Dict[Tuple[float, float], str] = {}
    duplicates: List[Dict[str, Any]] = []

    station_counter = 1
    for stn in raw_ernakulam_stations:
        coord_key = (round(stn["latitude"], 4), round(stn["longitude"], 4))
        name_clean = re.sub(r"[^a-zA-Z0-9]", "", stn["name"].lower())

        if deduplicate and coord_key in seen_coords:
            duplicates.append({
                "duplicate_record": stn["name"],
                "existing_record": seen_coords[coord_key],
                "coordinates": (stn["latitude"], stn["longitude"]),
            })
            continue

        seen_coords[coord_key] = stn["name"]
        station_id = f"REAL-EV-{station_counter:03d}"
        usable_stations.append(
            RealEVStation(
                station_id=station_id,
                name=stn["name"],
                state=stn["state"] or "Kerala",
                city=stn["city"] or "Ernakulam",
                address=stn["address"],
                latitude=stn["latitude"],
                longitude=stn["longitude"],
                station_type=stn["type"] or "Standard EV Charger",
                is_existing=True,
            )
        )
        station_counter += 1

    return {
        "total_source_records": total_records,
        "kerala_records": kerala_records,
        "ernakulam_records_raw": len(raw_ernakulam_stations),
        "missing_coordinates_count": missing_coords_count,
        "invalid_coordinates_count": invalid_coords_count,
        "duplicate_candidates_count": len(duplicates),
        "duplicates": duplicates,
        "final_usable_count": len(usable_stations),
        "stations": usable_stations,
    }
