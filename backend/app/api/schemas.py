"""Pydantic request and response schemas for REST API endpoints."""
import math
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.gis.spatial_index import validate_coordinates


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="ok", description="Service health status")
    version: str = Field(default="0.3.0", description="API version")


class NetworkInfoResponse(BaseModel):
    """Road network summary schema."""
    node_count: int = Field(..., description="Total number of nodes in the road network")
    edge_count: int = Field(..., description="Total number of edges in the road network")
    data_source: str = Field(..., description="Origin of network data: 'osm', 'cache', or 'sample'")


class LiveRouteRequest(BaseModel):
    """
    Live GPS route calculation request schema.
    
    Accepts the user's real-time latitude and longitude, with an optional
    search radius restriction.
    """
    latitude: float = Field(..., description="User GPS latitude in decimal degrees (-90.0 to 90.0)")
    longitude: float = Field(..., description="User GPS longitude in decimal degrees (-180.0 to 180.0)")
    max_station_distance_km: Optional[float] = Field(
        default=None,
        description="Optional maximum road distance in km to consider when selecting a charging station",
    )

    @model_validator(mode="after")
    def validate_gps_coordinates(self) -> "LiveRouteRequest":
        """Validate latitude and longitude using Phase 2 spatial validator."""
        validate_coordinates(self.latitude, self.longitude)
        if self.max_station_distance_km is not None:
            if not isinstance(self.max_station_distance_km, (int, float)):
                raise TypeError("max_station_distance_km must be numeric.")
            if math.isnan(self.max_station_distance_km) or math.isinf(self.max_station_distance_km):
                raise ValueError("max_station_distance_km must not be NaN or infinite.")
            if self.max_station_distance_km <= 0:
                raise ValueError("max_station_distance_km must be strictly positive.")
        return self


class UserLocation(BaseModel):
    """User input GPS coordinates representation."""
    latitude: float
    longitude: float


class StationInfo(BaseModel):
    """Selected EV charging station information."""
    candidate_id: str = Field(..., description="Unique candidate station ID")
    latitude: float = Field(..., description="Station latitude")
    longitude: float = Field(..., description="Station longitude")
    nearest_road_node: Optional[Any] = Field(None, description="Nearest road node ID connected to this station")
    road_distance_m: Optional[float] = Field(None, description="Distance from candidate to nearest road node in meters")
    feasibility_score: Optional[float] = Field(None, description="Station feasibility score (0.0 to 1.0)")
    data_source: Optional[str] = Field(None, description="Data provenance: 'osm', 'cache', or 'sample'")


class RouteInfo(BaseModel):
    """Route navigation details calculated via Dijkstra's algorithm."""
    node_ids: List[Any] = Field(..., description="Ordered list of road network node IDs along the route")
    coordinates: List[List[float]] = Field(..., description="Ordered list of [latitude, longitude] route points")
    distance_km: float = Field(..., description="Total route distance in kilometers")
    estimated_eta_minutes: Optional[float] = Field(
        default=None,
        description="Estimated travel time in minutes based on average speed (not real-time traffic)",
    )


class LiveRouteResponse(BaseModel):
    """Complete live navigation response schema."""
    user_location: UserLocation = Field(..., description="User's original GPS coordinates")
    snapped_node: Any = Field(..., description="Road network node ID to which the user GPS was snapped")
    distance_to_snapped_node_m: float = Field(..., description="Distance in meters from user GPS to snapped road node")
    station: StationInfo = Field(..., description="Selected feasible charging station")
    route: RouteInfo = Field(..., description="Optimal Dijkstra route from snapped node to station")

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ── Phase 5A: Minimum Dominating Set (MDS) schemas ──────────────────

class DominatingSetStation(BaseModel):
    """Charging station selected by the greedy MDS algorithm."""
    candidate_id: str = Field(..., description="Candidate station unique identifier")
    node_id: Any = Field(..., description="Associated road network node ID")
    latitude: float = Field(..., description="Station latitude")
    longitude: float = Field(..., description="Station longitude")
    feasible: bool = Field(default=True, description="Feasibility status of candidate")
    feasibility_score: Optional[float] = Field(None, description="Estimated feasibility score (0.0 to 1.0)")
    covered_demand_count: Optional[int] = Field(None, description="Number of demand nodes covered by this station")


class DominatingSetRequest(BaseModel):
    """Request payload for greedy MDS station placement."""
    coverage_radius_km: Optional[float] = Field(
        default=None,
        description="Graph distance coverage radius in km around each station",
        gt=0,
    )
    min_feasibility_score: Optional[float] = Field(
        default=None,
        description="Optional minimum candidate feasibility score threshold (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    max_stations: Optional[int] = Field(
        default=None,
        description="Optional maximum number of stations to select",
        gt=0,
    )


class DominatingSetResponse(BaseModel):
    """Response payload for greedy MDS station placement."""
    selected_stations: List[DominatingSetStation] = Field(
        ...,
        description="List of charging stations chosen by greedy MDS coverage approximation",
    )
    selected_count: int = Field(..., description="Total number of selected charging stations")
    candidate_count: int = Field(..., description="Total number of eligible feasible candidates evaluated")
    total_demand_nodes: int = Field(..., description="Total demand nodes in the road network")
    covered_demand_nodes: int = Field(..., description="Total demand nodes covered by the selected stations")
    coverage_percentage: float = Field(..., description="Percentage of network demand nodes covered (0.0 to 100.0)")
    coverage_radius_km: float = Field(..., description="Coverage radius applied during optimization in km")
    algorithm: str = Field(
        default="greedy_mds_approximation",
        description="Algorithm designation (greedy set-cover approximation)",
    )


# ── Phase 5B: Hungarian Algorithm Assignment schemas ───────────────

class EVLocationInput(BaseModel):
    """Input representation of an EV location for assignment."""
    ev_id: str = Field(..., description="Unique identifier for the electric vehicle (e.g. EV-001)")
    latitude: float = Field(..., description="Latitude coordinate in decimal degrees", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="Longitude coordinate in decimal degrees", ge=-180.0, le=180.0)


class AssignmentRequest(BaseModel):
    """Request payload for assigning EVs to charging stations using Hungarian algorithm."""
    evs: List[EVLocationInput] = Field(
        ...,
        description="List of EV positions requiring charging assignment",
    )
    station_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of candidate/station IDs to assign to. If omitted, MDS-selected stations will be used.",
    )
    coverage_radius_km: Optional[float] = Field(
        default=None,
        description="Coverage radius in km for dynamic MDS station selection if station_ids omitted",
        gt=0,
    )
    min_feasibility_score: Optional[float] = Field(
        default=None,
        description="Minimum feasibility score threshold for dynamic candidate filtering",
        ge=0.0,
        le=1.0,
    )
    max_stations: Optional[int] = Field(
        default=None,
        description="Optional maximum stations limit",
        gt=0,
    )
    cost_metric: Optional[str] = Field(
        default="network_distance_km",
        description="Preferred cost metric: 'network_distance_km' (default) or 'geographic_distance_km'",
    )


class EVAssignment(BaseModel):
    """Single EV-to-station assignment result."""
    ev_id: str = Field(..., description="EV identifier")
    station_id: str = Field(..., description="Assigned charging station ID")
    cost_km: float = Field(..., description="Assignment cost in kilometers")
    ev_latitude: float = Field(..., description="EV latitude coordinate")
    ev_longitude: float = Field(..., description="EV longitude coordinate")
    station_latitude: float = Field(..., description="Station latitude coordinate")
    station_longitude: float = Field(..., description="Station longitude coordinate")
    path_coordinates: Optional[List[List[float]]] = Field(
        default=None,
        description="Polyline coordinates [[lat, lon], ...] connecting EV and station",
    )


class AssignmentResponse(BaseModel):
    """Response payload for Hungarian bipartite EV-to-station assignment."""
    algorithm: str = Field(
        default="hungarian",
        description="Algorithm designation (Kuhn-Munkres minimum weight bipartite matching)",
    )
    cost_metric: str = Field(
        ...,
        description="Distance metric used: 'network_distance_km' or 'geographic_distance_km'",
    )
    ev_count: int = Field(..., description="Total number of EVs in request")
    station_count: int = Field(..., description="Total number of candidate stations evaluated")
    assigned_count: int = Field(..., description="Number of successful assignments")
    unassigned_count: int = Field(..., description="Number of unassigned EVs")
    assignments: List[EVAssignment] = Field(..., description="List of EV-to-station assignments")
    unassigned_ev_ids: List[str] = Field(default_factory=list, description="List of EV IDs that could not be assigned")
    unassigned_station_ids: List[str] = Field(default_factory=list, description="List of station IDs not assigned to any EV")
    total_cost_km: float = Field(..., description="Total assignment cost across all matched pairs in km")


# ── Phase 5C: Prim's Minimum Spanning Tree (MST) schemas ───────────

class InfrastructureStation(BaseModel):
    """Charging station node within the infrastructure connection network."""
    station_id: str = Field(..., description="Unique station candidate identifier")
    candidate_id: str = Field(..., description="Candidate identifier (alias for station_id)")
    latitude: float = Field(..., description="Station latitude")
    longitude: float = Field(..., description="Station longitude")
    nearest_road_node: Optional[Any] = Field(None, description="Road network node ID associated with station")
    connected: bool = Field(default=True, description="Whether station is connected in the MST component")


class InfrastructureEdge(BaseModel):
    """Minimum spanning tree connection edge between two charging stations."""
    from_station_id: str = Field(..., description="Source station candidate ID")
    to_station_id: str = Field(..., description="Destination station candidate ID")
    cost_km: float = Field(..., description="Infrastructure connection distance/cost in kilometers")
    path_coordinates: List[List[float]] = Field(
        default_factory=list,
        description="Polyline coordinates [[lat, lon], ...] along the road network connecting the stations",
    )


class InfrastructureRequest(BaseModel):
    """Request payload for Prim MST infrastructure connection optimization."""
    station_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of candidate station IDs to connect. If omitted, MDS-selected stations will be used.",
    )
    coverage_radius_km: Optional[float] = Field(
        default=None,
        description="Coverage radius in km for dynamic MDS station selection if station_ids omitted",
        gt=0,
    )
    min_feasibility_score: Optional[float] = Field(
        default=None,
        description="Minimum feasibility score threshold for dynamic candidate filtering",
        ge=0.0,
        le=1.0,
    )
    max_stations: Optional[int] = Field(
        default=None,
        description="Optional maximum stations limit",
        gt=0,
    )
    cost_metric: Optional[str] = Field(
        default="network_distance_km",
        description="Preferred cost metric: 'network_distance_km' (default) or 'geographic_distance_km'",
    )


class InfrastructureResponse(BaseModel):
    """Response payload for Prim MST infrastructure network optimization."""
    algorithm: str = Field(
        default="prim_mst",
        description="Algorithm designation (Prim Minimum Spanning Tree)",
    )
    cost_metric: str = Field(
        ...,
        description="Distance metric used: 'network_distance_km' or 'geographic_distance_km'",
    )
    station_count: int = Field(..., description="Total number of candidate stations evaluated")
    connected_station_count: int = Field(..., description="Number of stations connected in the MST component")
    mst_edge_count: int = Field(..., description="Total number of connection edges in the MST")
    total_cost_km: float = Field(..., description="Total infrastructure connection distance across all MST edges in km")
    stations: List[InfrastructureStation] = Field(..., description="List of evaluated stations with connection status")
    edges: List[InfrastructureEdge] = Field(..., description="List of MST infrastructure connection edges")
    connected_station_ids: List[str] = Field(default_factory=list, description="IDs of stations connected in the MST")
    unconnected_station_ids: List[str] = Field(default_factory=list, description="IDs of stations unreachable in network")


# ===========================================================================
# Phase 6 — Ford-Fulkerson Capacity & Bottleneck Analysis
# ===========================================================================


class CapacityEVInput(BaseModel):
    """Single EV entry for capacity analysis."""

    ev_id: str = Field(..., description="Unique EV identifier")
    demand_units: int = Field(
        default=1,
        ge=1,
        description="Simulated demand load this EV places on the charging network (planning units, not real kW)",
    )


class CapacityStationInput(BaseModel):
    """Single station entry for capacity analysis."""

    station_id: str = Field(..., description="Unique station identifier (matches MDS / Hungarian IDs)")
    capacity_units: int = Field(
        default=5,
        ge=1,
        description="Simulated serving capacity of this station (planning units, not real kW or real utility data)",
    )


class CapacityAssignment(BaseModel):
    """EV-to-station assignment pair (mirrors Hungarian output)."""

    ev_id: str = Field(..., description="EV identifier")
    station_id: str = Field(..., description="Station identifier the EV is assigned to")


class StationUtilization(BaseModel):
    """Per-station simulated flow utilization result."""

    station_id: str = Field(..., description="Station identifier")
    available_capacity: float = Field(..., description="Simulated station capacity (planning units)")
    utilized_capacity: float = Field(..., description="Simulated flow allocated to this station")
    unused_capacity: float = Field(..., description="Remaining unused simulated capacity")
    utilization_pct: float = Field(..., description="Utilization percentage (0-100)")
    is_saturated: bool = Field(..., description="True when the station is at or above simulated capacity")
    simulated_capacity: bool = Field(
        default=True,
        description="Always true — values are simulated for planning, not real electrical data",
    )


class CapacityFlowEdge(BaseModel):
    """A single EV->Station flow edge in the max-flow result."""

    from_ev_id: str = Field(..., description="Source EV identifier")
    to_station_id: str = Field(..., description="Destination station identifier")
    flow_units: float = Field(..., description="Flow units allocated on this edge")


class CapacityRequest(BaseModel):
    """Request payload for Ford-Fulkerson EV charging capacity analysis."""

    evs: List[CapacityEVInput] = Field(
        ...,
        min_length=1,
        description="List of EVs with simulated demand",
    )
    stations: List[CapacityStationInput] = Field(
        ...,
        min_length=1,
        description="List of stations with simulated capacity",
    )
    assignments: Optional[List[CapacityAssignment]] = Field(
        default=None,
        description=(
            "Optional EV-to-station assignments from Hungarian algorithm. "
            "If provided, only assigned pairs form EV->Station edges. "
            "If omitted, every EV is connected to every station."
        ),
    )


class CapacityResponse(BaseModel):
    """Response payload for Ford-Fulkerson EV charging capacity analysis."""

    algorithm: str = Field(
        default="ford_fulkerson_edmonds_karp",
        description="Algorithm used: Ford-Fulkerson with Edmonds-Karp BFS",
    )
    network_status: str = Field(
        ...,
        description=(
            "One of: 'fully_satisfied' (max_flow == total_demand), "
            "'capacity_limited' (max_flow < total_demand), "
            "'capacity_available' (demand met with spare capacity remaining)"
        ),
    )
    max_flow: float = Field(..., description="Maximum simulated flow routed through the network")
    total_demand: float = Field(..., description="Total simulated EV demand across all EVs")
    station_utilization: List[StationUtilization] = Field(
        ..., description="Per-station simulated utilization breakdown"
    )
    bottleneck_station_ids: List[str] = Field(
        default_factory=list,
        description="Station IDs where simulated utilization equals or exceeds simulated capacity",
    )
    flow_edges: List[CapacityFlowEdge] = Field(
        default_factory=list,
        description="EV->Station flow edges carrying positive simulated flow",
    )
    note: str = Field(
        ...,
        description="Disclaimer: all values are simulated/estimated for planning — not real utility data",
    )
