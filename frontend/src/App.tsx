import React, { useState, useEffect } from 'react';
import {
  Zap,
  Activity,
  Compass,
  Database,
} from 'lucide-react';
import { MapView } from './components/MapView';
import { RoutePanel } from './components/RoutePanel';
import { useGeolocation } from './hooks/useGeolocation';
import {
  fetchLiveRoute,
  fetchHealth,
  fetchNetworkInfo,
  fetchDominatingSetOptimization,
  fetchHungarianAssignment,
  fetchInfrastructureOptimization,
  fetchCapacityOptimization,
} from './api/routingApi';
import {
  LiveRouteResponse,
  UserCoordinates,
  DominatingSetResponse,
  AssignmentResponse,
  InfrastructureResponse,
  CapacityResponse,
} from './types/routing';

export const App: React.FC = () => {
  const {
    coordinates: geoCoords,
    loading: geoLoading,
    error: geoError,
    getLocation,
    clearError: clearGeoError,
  } = useGeolocation();

  // Active user location displayed on map
  const [activeCoords, setActiveCoords] = useState<UserCoordinates | null>(null);

  // Routing state
  const [routeResponse, setRouteResponse] = useState<LiveRouteResponse | null>(null);
  const [routeLoading, setRouteLoading] = useState<boolean>(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  // Phase 5A: Minimum Dominating Set (MDS) Station Optimization state
  const [mdsResponse, setMdsResponse] = useState<DominatingSetResponse | null>(null);
  const [mdsLoading, setMdsLoading] = useState<boolean>(false);
  const [mdsError, setMdsError] = useState<string | null>(null);

  // Phase 5B: Hungarian Bipartite Assignment state
  const [hungarianResponse, setHungarianResponse] = useState<AssignmentResponse | null>(null);
  const [hungarianLoading, setHungarianLoading] = useState<boolean>(false);
  const [hungarianError, setHungarianError] = useState<string | null>(null);

  // Phase 5C: Prim's Minimum Spanning Tree (MST) Infrastructure state
  const [infraResponse, setInfraResponse] = useState<InfrastructureResponse | null>(null);
  const [infraLoading, setInfraLoading] = useState<boolean>(false);
  const [infraError, setInfraError] = useState<string | null>(null);

  // Phase 6: Ford-Fulkerson Capacity & Bottleneck Analysis state
  const [capacityResponse, setCapacityResponse] = useState<CapacityResponse | null>(null);
  const [capacityLoading, setCapacityLoading] = useState<boolean>(false);
  const [capacityError, setCapacityError] = useState<string | null>(null);

  // Health / Backend status
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'offline'>('checking');
  const [backendVersion, setBackendVersion] = useState<string>('0.9.0');
  const [networkSource, setNetworkSource] = useState<string | null>(null);

  // Check backend health and road network info on initial mount
  useEffect(() => {
    let isMounted = true;
    fetchHealth()
      .then((res) => {
        if (isMounted) {
          setBackendStatus(res.status === 'ok' ? 'connected' : 'offline');
          if (res.version) setBackendVersion(res.version);
        }
      })
      .catch(() => {
        if (isMounted) {
          setBackendStatus('offline');
        }
      });

    fetchNetworkInfo()
      .then((info) => {
        if (isMounted && info?.data_source) {
          setNetworkSource(info.data_source);
        }
      })
      .catch(() => {
        // network info optional on mount
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Synchronize geolocation hook state with active coordinates
  useEffect(() => {
    if (geoCoords) {
      setActiveCoords(geoCoords);
    }
  }, [geoCoords]);

  // Combined loading state and step indicator
  const isLoading = geoLoading || routeLoading;
  const loadingStep: 'gps' | 'routing' | null = geoLoading
    ? 'gps'
    : routeLoading
    ? 'routing'
    : null;

  // Combined error state
  const currentError = geoError || routeError;

  const handleClearError = () => {
    clearGeoError();
    setRouteError(null);
  };

  /**
   * Main flow: request user GPS, snap to road network, and calculate Dijkstra route.
   */
  const handleUseMyLocation = async () => {
    handleClearError();
    try {
      // Step 1: Request GPS location from browser
      const coords = await getLocation();
      setActiveCoords(coords);

      // Step 2: Send GPS coordinates to backend for Dijkstra routing
      setRouteLoading(true);
      const result = await fetchLiveRoute({
        latitude: coords.latitude,
        longitude: coords.longitude,
      });

      // Explicitly clear any previous error and set active route
      handleClearError();
      setRouteResponse(result);
    } catch (err: unknown) {
      // On failure, clear any previous route so stale route is not displayed
      setRouteResponse(null);
      if (err instanceof Error) {
        setRouteError(err.message);
      } else {
        setRouteError('An unexpected routing error occurred.');
      }
    } finally {
      setRouteLoading(false);
    }
  };

  /**
   * Optional helper to test coordinates near the sample network
   * if physical browser GPS is unavailable or blocked.
   */
  const handleTestSampleLocation = async () => {
    handleClearError();
    const sampleCoords: UserCoordinates = {
      latitude: 10.001,
      longitude: 76.302,
      accuracy: 10,
    };
    setActiveCoords(sampleCoords);

    try {
      setRouteLoading(true);
      const result = await fetchLiveRoute({
        latitude: sampleCoords.latitude,
        longitude: sampleCoords.longitude,
      });
      // Explicitly clear any previous error and set active route
      handleClearError();
      setRouteResponse(result);
    } catch (err: unknown) {
      setRouteResponse(null);
      if (err instanceof Error) {
        setRouteError(err.message);
      } else {
        setRouteError('An error occurred calculating the route.');
      }
    } finally {
      setRouteLoading(false);
    }
  };

  /**
   * Phase 5A: Calculate network-wide Minimum Dominating Set (MDS)
   * for optimal charging station placement.
   */
  const handleOptimizeMds = async () => {
    setMdsError(null);
    setMdsLoading(true);
    try {
      const result = await fetchDominatingSetOptimization();
      setMdsResponse(result);
    } catch (err: unknown) {
      setMdsResponse(null);
      if (err instanceof Error) {
        setMdsError(err.message);
      } else {
        setMdsError('An error occurred calculating dominating set station placement.');
      }
    } finally {
      setMdsLoading(false);
    }
  };

  const handleClearMds = () => {
    setMdsResponse(null);
    setMdsError(null);
    setInfraResponse(null);
    setInfraError(null);
  };

  /**
   * Phase 5B: Assign EVs to selected charging stations using Hungarian algorithm.
   */
  const handleAssignHungarian = async () => {
    setHungarianError(null);
    setHungarianLoading(true);

    // Build deterministic EV list: use activeCoords if available + fleet vehicles
    const evList = activeCoords
      ? [
          { ev_id: 'User-EV', latitude: activeCoords.latitude, longitude: activeCoords.longitude },
          { ev_id: 'Fleet-EV2', latitude: 10.003, longitude: 76.305 },
          { ev_id: 'Fleet-EV3', latitude: 10.007, longitude: 76.312 },
        ]
      : [
          { ev_id: 'Fleet-EV1', latitude: 10.001, longitude: 76.302 },
          { ev_id: 'Fleet-EV2', latitude: 10.003, longitude: 76.305 },
          { ev_id: 'Fleet-EV3', latitude: 10.007, longitude: 76.312 },
        ];

    const stationIds = mdsResponse?.selected_stations?.map((s) => s.candidate_id);

    try {
      const result = await fetchHungarianAssignment({
        evs: evList,
        station_ids: stationIds && stationIds.length > 0 ? stationIds : undefined,
        coverage_radius_km: 0.5,
        cost_metric: 'network_distance_km',
      });
      setHungarianResponse(result);
    } catch (err: unknown) {
      setHungarianResponse(null);
      if (err instanceof Error) {
        setHungarianError(err.message);
      } else {
        setHungarianError('An error occurred calculating Hungarian EV assignments.');
      }
    } finally {
      setHungarianLoading(false);
    }
  };

  const handleClearHungarian = () => {
    setHungarianResponse(null);
    setHungarianError(null);
  };

  /**
   * Phase 5C: Minimum Spanning Tree (MST) Infrastructure Optimization using Prim's algorithm.
   */
  const handleOptimizeInfrastructure = async () => {
    setInfraError(null);

    // Ensure MDS stations have been selected first
    if (!mdsResponse?.selected_stations || mdsResponse.selected_stations.length === 0) {
      setInfraError('Run station optimization first.');
      return;
    }

    setInfraLoading(true);
    const stationIds = mdsResponse.selected_stations.map((s) => s.candidate_id);

    try {
      const result = await fetchInfrastructureOptimization({
        station_ids: stationIds,
        cost_metric: 'network_distance_km',
      });
      setInfraResponse(result);
    } catch (err: unknown) {
      setInfraResponse(null);
      if (err instanceof Error) {
        setInfraError(err.message);
      } else {
        setInfraError('An error occurred calculating infrastructure optimization.');
      }
    } finally {
      setInfraLoading(false);
    }
  };

  const handleClearInfrastructure = () => {
    setInfraResponse(null);
    setInfraError(null);
  };

  /**
   * Phase 6: Ford-Fulkerson Max-Flow — Analyze EV charging capacity and bottlenecks.
   * Requires Hungarian assignments to be available first (builds the EV→Station graph).
   * All capacity values are simulated — not real electrical grid data.
   */
  const handleAnalyzeCapacity = async () => {
    setCapacityError(null);

    // Require Hungarian assignments first
    if (!hungarianResponse?.assignments || hungarianResponse.assignments.length === 0) {
      setCapacityError('Run EV assignment (Hungarian) first to build the capacity flow graph.');
      return;
    }

    setCapacityLoading(true);

    // Build EV list from assignments (unique EVs)
    const evMap = new Map<string, number>();
    for (const a of hungarianResponse.assignments) {
      evMap.set(a.ev_id, 1); // demand_units = 1 per EV (simulated)
    }
    const evs = Array.from(evMap.entries()).map(([ev_id, demand_units]) => ({
      ev_id,
      demand_units,
    }));

    // Build station list from MDS or Hungarian station IDs
    const stationIds = mdsResponse?.selected_stations?.map((s) => s.candidate_id)
      ?? [...new Set(hungarianResponse.assignments.map((a) => a.station_id))];
    const stations = stationIds.map((station_id) => ({
      station_id,
      capacity_units: 3, // simulated capacity per station
    }));

    // Build assignments list from Hungarian result
    const assignments = hungarianResponse.assignments.map((a) => ({
      ev_id: a.ev_id,
      station_id: a.station_id,
    }));

    try {
      const result = await fetchCapacityOptimization({ evs, stations, assignments });
      setCapacityResponse(result);
    } catch (err: unknown) {
      setCapacityResponse(null);
      if (err instanceof Error) {
        setCapacityError(err.message);
      } else {
        setCapacityError('An error occurred during capacity analysis.');
      }
    } finally {
      setCapacityLoading(false);
    }
  };

  const handleClearCapacity = () => {
    setCapacityResponse(null);
    setCapacityError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* ── Global Header ────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200/80 shadow-xs sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 tracking-tight leading-none">
                EV Charging Network Optimization
              </h1>
              <p className="text-xs font-medium text-gray-500 mt-0.5">
                Graph-Based Smart Charging Navigation
              </p>
            </div>
          </div>

          {/* Backend Status Indicator */}
          <div className="flex items-center space-x-2">
            {networkSource && (
              <div className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600 border border-gray-200/60">
                <Database className="w-3.5 h-3.5 text-gray-400" />
                <span>Network: <strong className="capitalize">{networkSource === 'sample' ? 'Sample (Fallback)' : networkSource}</strong></span>
              </div>
            )}

            <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600 border border-gray-200/60">
              <Activity className="w-3.5 h-3.5 text-gray-400" />
              <span>Backend v{backendVersion}</span>
            </div>

            <div
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                backendStatus === 'connected'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : backendStatus === 'offline'
                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full mr-1.5 ${
                  backendStatus === 'connected'
                    ? 'bg-emerald-500'
                    : backendStatus === 'offline'
                    ? 'bg-rose-500'
                    : 'bg-amber-500 animate-ping'
                }`}
              ></span>
              <span className="capitalize">{backendStatus}</span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Content Layout ──────────────────────────────────── */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col">
        {/* Desktop Layout: 2-column (Map primary, Sidebar secondary) */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Map View Column (8 cols on large screens) */}
          <div className="lg:col-span-8 h-[520px] lg:h-[680px] w-full flex flex-col">
            <MapView
              userCoordinates={activeCoords}
              routeResponse={routeResponse}
              mdsStations={mdsResponse?.selected_stations}
              hungarianResponse={hungarianResponse}
              infraResponse={infraResponse}
              capacityResponse={capacityResponse}
            />
          </div>

          {/* Route Panel & Controls Column (4 cols on large screens) */}
          <div className="lg:col-span-4 flex flex-col space-y-4">
            <RoutePanel
              routeResponse={routeResponse}
              isLoading={isLoading}
              loadingStep={loadingStep}
              error={currentError}
              onLocate={handleUseMyLocation}
              onClearError={handleClearError}
              mdsResponse={mdsResponse}
              mdsLoading={mdsLoading}
              mdsError={mdsError}
              onOptimizeMds={handleOptimizeMds}
              onClearMds={handleClearMds}
              hungarianResponse={hungarianResponse}
              hungarianLoading={hungarianLoading}
              hungarianError={hungarianError}
              onAssignHungarian={handleAssignHungarian}
              onClearHungarian={handleClearHungarian}
              infraResponse={infraResponse}
              infraLoading={infraLoading}
              infraError={infraError}
              onOptimizeInfrastructure={handleOptimizeInfrastructure}
              onClearInfrastructure={handleClearInfrastructure}
              capacityResponse={capacityResponse}
              capacityLoading={capacityLoading}
              capacityError={capacityError}
              onAnalyzeCapacity={handleAnalyzeCapacity}
              onClearCapacity={handleClearCapacity}
            />

            {/* Quick Testing Card for Offline / Desktop environments */}
            <div className="bg-white rounded-xl border border-gray-200/70 p-3.5 text-xs text-gray-500 shadow-xs flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Compass className="w-4 h-4 text-gray-400" />
                <span>Testing without physical GPS?</span>
              </div>
              <button
                type="button"
                onClick={handleTestSampleLocation}
                disabled={isLoading}
                className="font-semibold text-emerald-600 hover:text-emerald-700 hover:underline disabled:opacity-50"
              >
                Simulate Location
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* ── Minimal Footer ───────────────────────────────────────── */}
      <footer className="bg-white border-t border-gray-200/60 py-3 text-center text-xs text-gray-400">
        <p>
          EV Charging Network Optimization &bull; Dijkstra Shortest Path Navigation
        </p>
      </footer>
    </div>
  );
};

export default App;
