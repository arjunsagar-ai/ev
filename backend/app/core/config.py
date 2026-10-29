"""Application settings and constants."""
import os
from typing import Dict, Any


class Settings:
    PROJECT_NAME: str = "Graph-Based EV Charging Station Optimization"
    VERSION: str = "0.9.0"
    API_V1_STR: str = "/api"

    # Allowed CORS origins for frontend integration
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ]

    # Default average vehicle travel speed in km/h for estimated ETA
    DEFAULT_AVERAGE_SPEED_KMH: float = 40.0

    # Default coverage radius for Minimum Dominating Set (in kilometers)
    DEFAULT_COVERAGE_RADIUS_KM: float = 5.0

    # Earth radius in kilometers for Haversine calculations
    EARTH_RADIUS_KM: float = 6371.0088
    # Earth radius in meters
    EARTH_RADIUS_METERS: float = 6371008.8

    # ── GIS / OpenStreetMap settings (Phase 2) ──────────────────────────

    # Overpass API endpoint — configurable via OVERPASS_URL env var
    OVERPASS_API_URL: str = os.environ.get(
        "OVERPASS_URL",
        "https://overpass-api.de/api/interpreter",
    )

    # Local cache directory for downloaded OSM data (relative to backend/)
    OSM_CACHE_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "osm",
    )

    # Sample data directory
    SAMPLE_DATA_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "sample",
    )

    # Road types to include when building the road network from OSM
    OSM_HIGHWAY_TYPES: list = [
        "motorway", "trunk", "primary", "secondary", "tertiary",
        "residential", "unclassified", "motorway_link", "trunk_link",
        "primary_link", "secondary_link", "tertiary_link",
    ]

    # Maximum snap distance (meters): reject GPS if farther than this
    # from the nearest road node
    MAX_SNAP_DISTANCE_M: float = 5000.0

    # ── Ernakulam District Geographic Scope (Phase 7.1) ─────────────────
    # Official bounding box enclosing all parts of Ernakulam District
    ERNAKULAM_BBOX: Dict[str, float] = {
        "north": 10.31,
        "south": 9.78,
        "east": 76.85,
        "west": 76.16,
    }

    # Ernakulam District boundary GeoJSON path
    ERNAKULAM_BOUNDARY_FILE: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "ernakulam_boundary.geojson",
    )

    # National EV charging stations CSV dataset path
    EV_STATIONS_CSV_FILE: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "ev-charging-stations-india.csv",
    )

    # Configurable search radius in km for discovering nearby real EV stations
    EV_STATION_SEARCH_RADIUS_KM: float = 25.0

    # ── Feasibility scoring weights ─────────────────────────────────────
    # Controls how candidate EV station locations are scored.
    # All weights should be non-negative. Higher weight = more important.
    FEASIBILITY_WEIGHTS: Dict[str, float] = {
        "accessibility": 0.30,   # Road accessibility (0-1)
        "land":          0.25,   # Land availability / suitability (0-1)
        "grid":          0.25,   # Proximity to electrical grid (0-1)
        "cost":          0.20,   # Installation cost penalty (0-1, inverted)
    }

    # Minimum feasibility score (0.0–1.0) for a candidate to be viable
    FEASIBILITY_THRESHOLD: float = 0.40

    # Maximum distance from road (meters) for a candidate to be accessible
    CANDIDATE_MAX_ROAD_DISTANCE_M: float = 500.0


settings = Settings()
