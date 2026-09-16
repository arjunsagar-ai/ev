"""GIS data models for candidate charging station locations."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CandidateLocation:
    """
    Represents a candidate site for an EV charging station.

    Attributes:
        candidate_id: Unique identifier for this candidate.
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        nearest_road_node: ID of the nearest node in the road WeightedGraph.
        road_distance_m: Distance in meters from this candidate to its nearest road node.
        accessibility_score: Road accessibility rating (0.0–1.0). Higher is better.
        land_available: Land suitability / availability rating (0.0–1.0).
        grid_capacity: Electrical grid capacity rating (0.0–1.0).
            Marked as 'estimated' or 'unknown' via grid_capacity_source when
            real substation data is unavailable.
        grid_capacity_source: Provenance of grid_capacity value:
            'measured', 'estimated', 'synthetic', or 'unknown'.
        installation_cost: Normalised installation cost (0.0–1.0, higher = costlier).
        feasibility_score: Composite weighted feasibility score (0.0–1.0).
        feasible: Whether the candidate passes the feasibility threshold.
        rejection_reason: Explanation when feasible is False; None otherwise.
        data_source: Origin of the candidate data — 'osm', 'cache', or 'sample'.
        osm_tags: Raw OSM tags if the candidate was derived from OSM amenity data.
    """

    candidate_id: str
    latitude: float
    longitude: float
    nearest_road_node: Optional[Any] = None
    road_distance_m: float = 0.0
    accessibility_score: float = 0.0
    land_available: float = 0.0
    grid_capacity: float = 0.0
    grid_capacity_source: str = "unknown"
    installation_cost: float = 0.5
    feasibility_score: float = 0.0
    feasible: bool = False
    rejection_reason: Optional[str] = None
    data_source: str = "sample"
    osm_tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "candidate_id": self.candidate_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "nearest_road_node": self.nearest_road_node,
            "road_distance_m": round(self.road_distance_m, 2),
            "accessibility_score": round(self.accessibility_score, 4),
            "land_available": round(self.land_available, 4),
            "grid_capacity": round(self.grid_capacity, 4),
            "grid_capacity_source": self.grid_capacity_source,
            "installation_cost": round(self.installation_cost, 4),
            "feasibility_score": round(self.feasibility_score, 4),
            "feasible": self.feasible,
            "rejection_reason": self.rejection_reason,
            "data_source": self.data_source,
        }


@dataclass
class RoadNetworkMetadata:
    """Metadata about a loaded road network."""

    data_source: str          # "osm", "cache", or "sample"
    num_nodes: int = 0
    num_edges: int = 0
    bbox: Optional[Dict[str, float]] = None   # {north, south, east, west}
    load_time_seconds: float = 0.0
