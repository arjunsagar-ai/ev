/**
 * TypeScript types matching backend schemas from app/api/schemas.py.
 */

export interface UserLocation {
  latitude: number;
  longitude: number;
}

export interface StationInfo {
  candidate_id: string;
  latitude: number;
  longitude: number;
  nearest_road_node?: string | number | null;
  road_distance_m?: number | null;
  feasibility_score?: number | null;
  data_source?: string | null;
}

export interface RouteInfo {
  node_ids: (string | number)[];
  coordinates: [number, number][]; // [lat, lon] tuples
  distance_km: number;
  estimated_eta_minutes?: number | null;
}

export interface LiveRouteResponse {
  user_location: UserLocation;
  snapped_node: string | number;
  distance_to_snapped_node_m: number;
  station: StationInfo;
  route: RouteInfo;
}

export interface LiveRouteRequest {
  latitude: number;
  longitude: number;
  max_station_distance_km?: number;
}

export interface NetworkInfoResponse {
  node_count: number;
  edge_count: number;
  data_source: string;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface UserCoordinates {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

// ── Phase 5A: Minimum Dominating Set (MDS) types ──────────────────

export interface DominatingSetStation {
  candidate_id: string;
  node_id: string | number;
  latitude: number;
  longitude: number;
  feasible: boolean;
  feasibility_score?: number | null;
  covered_demand_count?: number | null;
}

export interface DominatingSetRequest {
  coverage_radius_km?: number;
  min_feasibility_score?: number;
  max_stations?: number;
}

export interface DominatingSetResponse {
  selected_stations: DominatingSetStation[];
  selected_count: number;
  candidate_count: number;
  total_demand_nodes: number;
  covered_demand_nodes: number;
  coverage_percentage: number;
  coverage_radius_km: number;
  algorithm: string;
}

// ── Phase 5B: Hungarian EV Assignment types ───────────────────────

export interface EVLocationInput {
  ev_id: string;
  latitude: number;
  longitude: number;
}

export interface AssignmentRequest {
  evs: EVLocationInput[];
  station_ids?: string[];
  coverage_radius_km?: number;
  min_feasibility_score?: number;
  max_stations?: number;
  cost_metric?: string;
}

export interface EVAssignment {
  ev_id: string;
  station_id: string;
  cost_km: number;
  ev_latitude: number;
  ev_longitude: number;
  station_latitude: number;
  station_longitude: number;
  path_coordinates?: [number, number][];
}

export interface AssignmentResponse {
  algorithm: string;
  cost_metric: string;
  ev_count: number;
  station_count: number;
  assigned_count: number;
  unassigned_count: number;
  assignments: EVAssignment[];
  unassigned_ev_ids: string[];
  unassigned_station_ids: string[];
  total_cost_km: number;
}

// ── Phase 5C: Prim MST Infrastructure Optimization types ──────────

export interface InfrastructureStation {
  station_id: string;
  candidate_id: string;
  latitude: number;
  longitude: number;
  nearest_road_node?: string | number | null;
  connected: boolean;
}

export interface InfrastructureEdge {
  from_station_id: string;
  to_station_id: string;
  cost_km: number;
  path_coordinates: [number, number][];
}

export interface InfrastructureRequest {
  station_ids?: string[];
  coverage_radius_km?: number;
  min_feasibility_score?: number;
  max_stations?: number;
  cost_metric?: string;
}

export interface InfrastructureResponse {
  algorithm: string;
  cost_metric: string;
  station_count: number;
  connected_station_count: number;
  mst_edge_count: number;
  total_cost_km: number;
  stations: InfrastructureStation[];
  edges: InfrastructureEdge[];
  connected_station_ids: string[];
  unconnected_station_ids: string[];
}


// ============================================================================
// Phase 6 — Ford-Fulkerson Capacity & Bottleneck Analysis
// ============================================================================

export interface CapacityEVInput {
  ev_id: string;
  demand_units: number;
}

export interface CapacityStationInput {
  station_id: string;
  capacity_units: number;
}

export interface CapacityAssignment {
  ev_id: string;
  station_id: string;
}

export interface StationUtilization {
  station_id: string;
  available_capacity: number;
  utilized_capacity: number;
  unused_capacity: number;
  utilization_pct: number;
  is_saturated: boolean;
  simulated_capacity: boolean;
}

export interface CapacityFlowEdge {
  from_ev_id: string;
  to_station_id: string;
  flow_units: number;
}

export interface CapacityRequest {
  evs: CapacityEVInput[];
  stations: CapacityStationInput[];
  assignments?: CapacityAssignment[] | null;
}

export interface CapacityResponse {
  algorithm: string;
  network_status: 'fully_satisfied' | 'capacity_limited' | 'capacity_available';
  max_flow: number;
  total_demand: number;
  station_utilization: StationUtilization[];
  bottleneck_station_ids: string[];
  flow_edges: CapacityFlowEdge[];
  note: string;
}
