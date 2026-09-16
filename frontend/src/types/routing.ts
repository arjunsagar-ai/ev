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

