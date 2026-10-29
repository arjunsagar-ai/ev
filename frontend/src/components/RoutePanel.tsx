import {
  Navigation,
  Clock,
  MapPin,
  ShieldCheck,
  Zap,
  Milestone,
  Sparkles,
  Layers,
  Loader2,
  X,
  ArrowRightLeft,
  Network,
  Database,
} from 'lucide-react';
import {
  AssignmentResponse,
  CapacityResponse,
  DominatingSetResponse,
  ExistingStation,
  InfrastructureResponse,
  LiveRouteResponse,
  LocationSource,
  UserCoordinates,
  UserLocationSelection,
} from '../types/routing';
import { formatDistance, formatEta } from '../utils/coordinates';
import { LoadingState } from './LoadingState';
import { ErrorMessage } from './ErrorMessage';
import { LocationCard } from './LocationCard';

interface RoutePanelProps {
  locationSelection: UserLocationSelection | null;
  isLoadingLiveGps: boolean;
  liveGpsError: string | null;
  onUseLiveLocation: () => void;
  onConfirmLocation: (coords: UserCoordinates, source: LocationSource, label: string) => void;
  onChangeLocation: () => void;
  isSelectingOnMap: boolean;
  onStartMapSelection: () => void;
  onCancelMapSelection: () => void;
  pendingCoordinates: UserCoordinates | null;
  pendingLabel: string | null;
  onClearPending: () => void;
  onSelectPendingCoords: (coords: UserCoordinates, label: string) => void;

  // Phase 7.1: Ernakulam District Scope & Real EV Stations props
  districtBoundary?: any;
  existingStations?: ExistingStation[] | null;
  nearbyStations?: ExistingStation[] | null;
  nearbyStationsLoading?: boolean;
  nearbyStationsMessage?: string | null;
  networkSource?: string | null;
  projectArea?: string | null;

  routeResponse: LiveRouteResponse | null;
  isLoading: boolean;
  loadingStep: 'gps' | 'routing' | null;
  error: string | null;
  onClearError?: () => void;

  // Phase 5A: MDS Optimization props
  mdsResponse: DominatingSetResponse | null;
  mdsLoading: boolean;
  mdsError: string | null;
  onOptimizeMds: () => void;
  onClearMds?: () => void;

  // Phase 5B: Hungarian Assignment props
  hungarianResponse: AssignmentResponse | null;
  hungarianLoading: boolean;
  hungarianError: string | null;
  onAssignHungarian: () => void;
  onClearHungarian?: () => void;

  // Phase 5C: Prim MST Infrastructure props
  infraResponse: InfrastructureResponse | null;
  infraLoading: boolean;
  infraError: string | null;
  onOptimizeInfrastructure: () => void;
  onClearInfrastructure?: () => void;

  // Phase 6: Ford-Fulkerson Capacity & Bottleneck Analysis props
  capacityResponse: CapacityResponse | null;
  capacityLoading: boolean;
  capacityError: string | null;
  onAnalyzeCapacity: () => void;
  onClearCapacity?: () => void;
}

export const RoutePanel: React.FC<RoutePanelProps> = ({
  locationSelection,
  isLoadingLiveGps,
  liveGpsError,
  onUseLiveLocation,
  onConfirmLocation,
  onChangeLocation,
  isSelectingOnMap,
  onStartMapSelection,
  onCancelMapSelection,
  pendingCoordinates,
  pendingLabel,
  onClearPending,
  onSelectPendingCoords,
  districtBoundary,
  existingStations: _existingStations,
  nearbyStations,
  nearbyStationsLoading = false,
  nearbyStationsMessage,
  networkSource,
  projectArea,
  routeResponse,
  isLoading,
  loadingStep,
  error,
  onClearError,
  mdsResponse,
  mdsLoading,
  mdsError,
  onOptimizeMds,
  onClearMds,
  hungarianResponse,
  hungarianLoading,
  hungarianError,
  onAssignHungarian,
  onClearHungarian,
  infraResponse,
  infraLoading,
  infraError,
  onOptimizeInfrastructure,
  onClearInfrastructure,
  capacityResponse,
  capacityLoading,
  capacityError,
  onAnalyzeCapacity,
  onClearCapacity,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-lg p-5 flex flex-col space-y-4">
      {/* ── Geographic Scope & Road Network Indicator ── */}
      <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-xl p-3 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-xs text-xs font-bold">
            📍
          </span>
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">
              Project Area
            </div>
            <div className="font-semibold text-emerald-950">
              {projectArea || 'Ernakulam District, Kerala'}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            Road Network
          </div>
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold capitalize ${
            networkSource === 'osm'
              ? 'bg-blue-100 text-blue-800'
              : networkSource === 'cache'
              ? 'bg-green-100 text-green-800'
              : 'bg-amber-100 text-amber-800'
          }`}>
            {networkSource === 'sample' ? 'Offline Sample' : networkSource ? networkSource.toUpperCase() : 'Ready'}
          </span>
        </div>
      </div>

      {/* 📍 Step 1: Your Location Card */}
      <LocationCard
        locationSelection={locationSelection}
        isLoadingLiveGps={isLoadingLiveGps}
        liveGpsError={liveGpsError}
        onUseLiveLocation={onUseLiveLocation}
        onConfirmLocation={onConfirmLocation}
        onChangeLocation={onChangeLocation}
        isSelectingOnMap={isSelectingOnMap}
        onStartMapSelection={onStartMapSelection}
        onCancelMapSelection={onCancelMapSelection}
        pendingCoordinates={pendingCoordinates}
        pendingLabel={pendingLabel}
        onClearPending={onClearPending}
        onSelectPendingCoords={onSelectPendingCoords}
        districtBoundary={districtBoundary}
      />

      {/* ── Nearby Real EV Charging Stations Card (from dataset) ── */}
      {locationSelection && (
        <div className="bg-gradient-to-br from-slate-50 to-emerald-50/30 border border-emerald-200/80 rounded-xl p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-700 text-white text-xs font-bold">
                ⚡
              </span>
              <div>
                <h4 className="text-xs font-bold text-gray-900">
                  Verified Real EV Stations
                </h4>
                <p className="text-[10px] text-gray-500">
                  Ernakulam District Dataset &bull; Max 25 km radius
                </p>
              </div>
            </div>
            {nearbyStations && (
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                {nearbyStations.length} nearby
              </span>
            )}
          </div>

          {nearbyStationsLoading && (
            <div className="flex items-center justify-center space-x-2 py-3 text-xs text-gray-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
              <span>Scanning verified charging stations in Ernakulam...</span>
            </div>
          )}

          {!nearbyStationsLoading && nearbyStationsMessage && nearbyStations?.length === 0 && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 p-2.5 rounded-lg text-xs">
              {nearbyStationsMessage}
            </div>
          )}

          {!nearbyStationsLoading && nearbyStations && nearbyStations.length > 0 && (
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {nearbyStations.map((st) => (
                <div
                  key={`nearby-${st.station_id}`}
                  className="bg-white/90 border border-emerald-100 rounded-lg p-2 text-xs flex items-center justify-between shadow-xs hover:border-emerald-300 transition-colors"
                >
                  <div className="flex-1 min-w-0 pr-2">
                    <div className="font-semibold text-gray-900 truncate">
                      {st.name}
                    </div>
                    <div className="text-[11px] text-gray-500 truncate">
                      {st.address || st.city}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {st.distance_km != null ? formatDistance(st.distance_km) : 'In range'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="text-[10px] text-gray-400 border-t border-gray-100 pt-1.5 flex items-center justify-between">
            <span>Real Stations: Verified dataset</span>
            <span>MDS Candidates: Optimization nodes</span>
          </div>
        </div>
      )}

      {/* ── Workflow Stepper Indicator ── */}
      <div className="bg-gray-50 border border-gray-200/70 rounded-xl p-2.5">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
          Optimization Workflow:
        </p>
        <div className="flex items-center justify-between text-[11px] font-semibold text-gray-500">
          <div className={`flex items-center space-x-1 ${locationSelection ? 'text-emerald-700 font-bold' : 'text-gray-900 font-bold'}`}>
            <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
              locationSelection ? 'bg-emerald-600 text-white' : 'bg-gray-300 text-gray-700'
            }`}>
              1
            </span>
            <span>Location</span>
          </div>
          <span className="text-gray-300">→</span>
          <div className={`flex items-center space-x-1 ${mdsResponse ? 'text-purple-700 font-bold' : locationSelection ? 'text-gray-800' : 'text-gray-400'}`}>
            <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
              mdsResponse ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-600'
            }`}>
              2
            </span>
            <span>Stations</span>
          </div>
          <span className="text-gray-300">→</span>
          <div className={`flex items-center space-x-1 ${hungarianResponse ? 'text-amber-700 font-bold' : mdsResponse ? 'text-gray-800' : 'text-gray-400'}`}>
            <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
              hungarianResponse ? 'bg-amber-600 text-white' : 'bg-gray-200 text-gray-600'
            }`}>
              3
            </span>
            <span>EVs</span>
          </div>
          <span className="text-gray-300">→</span>
          <div className={`flex items-center space-x-1 ${infraResponse ? 'text-teal-700 font-bold' : mdsResponse ? 'text-gray-800' : 'text-gray-400'}`}>
            <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
              infraResponse ? 'bg-teal-600 text-white' : 'bg-gray-200 text-gray-600'
            }`}>
              4
            </span>
            <span>MST</span>
          </div>
          <span className="text-gray-300">→</span>
          <div className={`flex items-center space-x-1 ${capacityResponse ? 'text-violet-700 font-bold' : hungarianResponse ? 'text-gray-800' : 'text-gray-400'}`}>
            <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
              capacityResponse ? 'bg-violet-600 text-white' : 'bg-gray-200 text-gray-600'
            }`}>
              5
            </span>
            <span>Capacity</span>
          </div>
        </div>
      </div>

      {/* ── Optimization Actions ── */}
      <div className="space-y-3">
        {!locationSelection && (
          <div className="p-2.5 bg-amber-50/80 border border-amber-200 rounded-xl text-center text-xs text-amber-800 font-medium">
            📍 Set your location first to enable charging station optimization.
          </div>
        )}

        {/* Step 2: Network Optimization Action Button (Greedy MDS) */}
        <div>
          <button
            type="button"
            onClick={onOptimizeMds}
            disabled={!locationSelection || mdsLoading || isLoading}
            className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-purple-200
              text-xs font-bold rounded-xl shadow-xs transition-all duration-200 focus:outline-none
              focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 bg-purple-50 hover:bg-purple-100
              text-purple-700 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
          >
            {mdsLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-2 text-purple-600" />
                <span>Optimizing station placement...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 mr-2 text-purple-600" />
                <span>✨ Optimize Stations (Greedy MDS)</span>
              </>
            )}
          </button>
          <p className="text-[11px] text-gray-500 mt-1 px-1 leading-tight">
            Selects feasible charging-station locations using greedy network coverage optimization.
          </p>
        </div>

        {/* Step 3: Phase 5B: Hungarian Bipartite Assignment Action Button */}
        <div>
          <button
            type="button"
            onClick={onAssignHungarian}
            disabled={!locationSelection || hungarianLoading || isLoading}
            className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-amber-200
              text-xs font-bold rounded-xl shadow-xs transition-all duration-200 focus:outline-none
              focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 bg-amber-50 hover:bg-amber-100
              text-amber-800 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
          >
            {hungarianLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-2 text-amber-600" />
                <span>Calculating Hungarian matching...</span>
              </>
            ) : (
              <>
                <ArrowRightLeft className="w-3.5 h-3.5 mr-2 text-amber-600" />
                <span>⇄ Assign EVs to Stations</span>
              </>
            )}
          </button>
          <p className="text-[11px] text-gray-500 mt-1 px-1 leading-tight">
            Assigns EV requests to selected charging stations.
          </p>
        </div>

        {/* Step 4: Phase 5C: Prim MST Infrastructure Optimization Action Button */}
        <div>
          <button
            type="button"
            onClick={onOptimizeInfrastructure}
            disabled={!locationSelection || infraLoading || isLoading}
            className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-teal-200
              text-xs font-bold rounded-xl shadow-xs transition-all duration-200 focus:outline-none
              focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 bg-teal-50 hover:bg-teal-100
              text-teal-800 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
          >
            {infraLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-2 text-teal-600" />
                <span>Optimizing infrastructure MST...</span>
              </>
            ) : (
              <>
                <Network className="w-3.5 h-3.5 mr-2 text-teal-600" />
                <span>♧ Optimize Infrastructure</span>
              </>
            )}
          </button>
          <p className="text-[11px] text-gray-500 mt-1 px-1 leading-tight">
            Finds a minimum connection network between selected stations.
          </p>
        </div>

        {/* Step 5: Phase 6: Ford-Fulkerson Capacity Analysis Action Button */}
        <div>
          <button
            type="button"
            onClick={onAnalyzeCapacity}
            disabled={!locationSelection || capacityLoading || isLoading}
            className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-violet-200
              text-xs font-bold rounded-xl shadow-xs transition-all duration-200 focus:outline-none
              focus:ring-2 focus:ring-offset-2 focus:ring-violet-500 bg-violet-50 hover:bg-violet-100
              text-violet-800 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
          >
            {capacityLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-2 text-violet-600" />
                <span>Analyzing capacity flow...</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5 mr-2 text-violet-600" />
                <span>⚡ Analyze Charging Capacity</span>
              </>
            )}
          </button>
          <p className="text-[11px] text-gray-500 mt-1 px-1 leading-tight">
            Calculates modeled charging capacity and identifies bottlenecks using Ford-Fulkerson.
          </p>
        </div>
      </div>

      {/* Infrastructure Error Message Display */}
      {infraError && !infraLoading && (
        <ErrorMessage
          message={infraError}
          onRetry={onOptimizeInfrastructure}
        />
      )}

      {/* Hungarian Error Message Display */}
      {hungarianError && !hungarianLoading && (
        <ErrorMessage
          message={hungarianError}
          onRetry={onAssignHungarian}
        />
      )}

      {/* MDS Error Message Display */}
      {mdsError && !mdsLoading && (
        <ErrorMessage
          message={mdsError}
          onRetry={onOptimizeMds}
        />
      )}

      {/* Phase 6: Capacity Error Message Display */}
      {capacityError && !capacityLoading && (
        <ErrorMessage
          message={capacityError}
          onRetry={onAnalyzeCapacity}
        />
      )}

      {/* Phase 6: Ford-Fulkerson Capacity & Bottleneck Analysis Summary Card */}
      {capacityResponse && !capacityLoading && !capacityError && (
        <div className="bg-gradient-to-br from-violet-50 to-purple-50/40 border border-violet-200/80 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-600 text-white shadow-xs">
                <Zap className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Capacity Analysis
                </h3>
                <p className="text-sm font-bold text-gray-900">
                  Ford-Fulkerson Max-Flow
                </p>
              </div>
            </div>
            {onClearCapacity && (
              <button
                type="button"
                onClick={onClearCapacity}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
                title="Hide capacity analysis"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Network Status Badge */}
          <div className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-bold border ${
            capacityResponse.network_status === 'fully_satisfied'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : capacityResponse.network_status === 'capacity_available'
              ? 'bg-sky-50 text-sky-800 border-sky-200'
              : 'bg-rose-50 text-rose-800 border-rose-200'
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full mr-1.5 ${
              capacityResponse.network_status === 'fully_satisfied'
                ? 'bg-emerald-500'
                : capacityResponse.network_status === 'capacity_available'
                ? 'bg-sky-500'
                : 'bg-rose-500'
            }`} />
            {capacityResponse.network_status === 'fully_satisfied'
              ? 'Fully Satisfied'
              : capacityResponse.network_status === 'capacity_available'
              ? 'Capacity Available'
              : 'Capacity Limited'}
          </div>

          {/* Flow Summary */}
          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <div className="bg-white/80 rounded-lg p-2 border border-violet-100">
              <span className="text-gray-500 block">Max Flow / Demand</span>
              <span className="text-sm font-bold text-gray-900">
                {capacityResponse.max_flow} / {capacityResponse.total_demand}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-violet-100">
              <span className="text-gray-500 block">Bottleneck Stations</span>
              <span className={`text-sm font-bold ${
                capacityResponse.bottleneck_station_ids.length > 0 ? 'text-rose-700' : 'text-emerald-700'
              }`}>
                {capacityResponse.bottleneck_station_ids.length}
              </span>
            </div>
          </div>

          {/* Per-Station Utilization */}
          {capacityResponse.station_utilization.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <span className="text-[11px] font-semibold text-gray-500 uppercase">
                Station Utilization (Simulated)
              </span>
              <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                {capacityResponse.station_utilization.map((s) => (
                  <div
                    key={`cap-util-${s.station_id}`}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-md border text-xs ${
                      s.is_saturated
                        ? 'bg-rose-50 border-rose-200 text-rose-900'
                        : 'bg-white/70 border-violet-100 text-gray-800'
                    }`}
                  >
                    <span className="font-medium">
                      <span className="text-purple-700 font-bold">{s.station_id}</span>
                      {s.is_saturated && <span className="ml-1 text-rose-600 font-bold">⚠ Saturated</span>}
                    </span>
                    <span className="font-mono text-[11px] text-gray-600">
                      {s.utilized_capacity}/{s.available_capacity} ({s.utilization_pct}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-[10px] text-gray-500 leading-tight border-t border-violet-100 pt-2">
            ⚡ Simulated capacity values only — not real electrical grid data. Max-flow via Edmonds-Karp BFS.
          </p>
        </div>
      )}

      {/* Phase 5C: Prim MST Infrastructure Summary Card */}
      {infraResponse && !infraLoading && !infraError && (
        <div className="bg-gradient-to-br from-teal-50 to-emerald-50/40 border border-teal-200/80 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-600 text-white shadow-xs">
                <Network className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Infrastructure Optimization
                </h3>
                <p className="text-sm font-bold text-gray-900">
                  Prim Minimum Spanning Tree
                </p>
              </div>
            </div>
            {onClearInfrastructure && (
              <button
                type="button"
                onClick={onClearInfrastructure}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
                title="Hide Infrastructure MST"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100">
              <span className="text-gray-500 block">Stations</span>
              <span className="text-sm font-bold text-gray-900">
                {infraResponse.connected_station_count} / {infraResponse.station_count}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100">
              <span className="text-gray-500 block">MST Connections</span>
              <span className="text-sm font-bold text-teal-800">
                {infraResponse.mst_edge_count}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100 col-span-2">
              <span className="text-gray-500 block">Total Infrastructure Distance</span>
              <span className="text-base font-extrabold text-teal-900">
                {infraResponse.total_cost_km} km
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100 col-span-2">
              <span className="text-gray-500 block">Cost Metric</span>
              <span className="text-sm font-semibold text-gray-800 capitalize">
                {infraResponse.cost_metric === 'network_distance_km'
                  ? 'Network Distance'
                  : 'Geographic Distance'}
              </span>
            </div>
          </div>

          {/* Disconnected Network Warning if applicable */}
          {infraResponse.unconnected_station_ids && infraResponse.unconnected_station_ids.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 p-2.5 rounded-lg text-xs space-y-1">
              <div className="font-bold flex items-center space-x-1">
                <span>⚠️ Disconnected Station Network</span>
              </div>
              <p className="text-[11px] leading-tight">
                {infraResponse.unconnected_station_ids.length} station(s) cannot be reached using the available road network:
              </p>
              <div className="font-mono text-[11px] text-amber-900">
                {infraResponse.unconnected_station_ids.join(', ')}
              </div>
            </div>
          )}

          {/* List of MST Infrastructure Connections */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[11px] font-semibold text-gray-500 uppercase">
              Spanning Connections
            </span>
            <div className="space-y-1 max-h-32 overflow-y-auto pr-1 text-xs">
              {infraResponse.edges.map((edge, idx) => (
                <div
                  key={`mst-list-${edge.from_station_id}-${edge.to_station_id}-${idx}`}
                  className="flex items-center justify-between bg-white/70 px-2.5 py-1.5 rounded-md border border-teal-100"
                >
                  <span className="font-medium text-gray-800">
                    <span className="text-purple-700 font-bold">{edge.from_station_id}</span> &harr; <span className="text-purple-700 font-bold">{edge.to_station_id}</span>
                  </span>
                  <span className="text-gray-500 font-mono text-[11px]">
                    {edge.cost_km} km
                  </span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-[10px] text-gray-500 leading-tight border-t border-teal-100 pt-2">
            Minimum spanning infrastructure connection distance calculated via Prim's algorithm on shortest road paths.
          </p>
        </div>
      )}

      {/* Hungarian EV Assignment Summary Card */}
      {hungarianResponse && !hungarianLoading && !hungarianError && (
        <div className="bg-gradient-to-br from-amber-50 to-orange-50/40 border border-amber-200/80 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-600 text-white shadow-xs">
                <ArrowRightLeft className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Hungarian Matching
                </h3>
                <p className="text-sm font-bold text-gray-900">
                  EV Slot Assignment
                </p>
              </div>
            </div>
            {onClearHungarian && (
              <button
                type="button"
                onClick={onClearHungarian}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
                title="Hide Hungarian matching"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <div className="bg-white/80 rounded-lg p-2 border border-amber-100">
              <span className="text-gray-500 block">EVs / Stations</span>
              <span className="text-sm font-bold text-gray-900">
                {hungarianResponse.ev_count} / {hungarianResponse.station_count}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-amber-100">
              <span className="text-gray-500 block">Assigned / Unassigned</span>
              <span className="text-sm font-bold text-amber-800">
                {hungarianResponse.assigned_count} / {hungarianResponse.unassigned_count}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-amber-100">
              <span className="text-gray-500 block">Total Cost</span>
              <span className="text-sm font-bold text-gray-900">
                {hungarianResponse.total_cost_km} km
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-amber-100">
              <span className="text-gray-500 block">Cost Metric</span>
              <span className="text-sm font-bold text-gray-900 capitalize">
                {hungarianResponse.cost_metric === 'network_distance_km'
                  ? 'Network Distance'
                  : 'Geographic Distance'}
              </span>
            </div>
          </div>

          {/* List of Matched Pairs */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[11px] font-semibold text-gray-500 uppercase">
              Matched Pairs
            </span>
            <div className="space-y-1 max-h-32 overflow-y-auto pr-1 text-xs">
              {hungarianResponse.assignments.map((asgn) => (
                <div
                  key={`asgn-list-${asgn.ev_id}-${asgn.station_id}`}
                  className="flex items-center justify-between bg-white/70 px-2.5 py-1.5 rounded-md border border-amber-100"
                >
                  <span className="font-medium text-gray-800">
                    {asgn.ev_id} &rarr; <span className="text-purple-700 font-bold">{asgn.station_id}</span>
                  </span>
                  <span className="text-gray-500 font-mono text-[11px]">
                    {asgn.cost_km} km
                  </span>
                </div>
              ))}
              {hungarianResponse.unassigned_ev_ids && hungarianResponse.unassigned_ev_ids.length > 0 && (
                <div className="bg-rose-50 border border-rose-200 text-rose-700 px-2.5 py-1.5 rounded-md text-[11px]">
                  Unassigned: {hungarianResponse.unassigned_ev_ids.join(', ')}
                </div>
              )}
            </div>
          </div>

          <p className="text-[10px] text-gray-500 leading-tight border-t border-amber-100 pt-2">
            Kuhn-Munkres minimum-cost bipartite matching over the distance cost matrix.
          </p>
        </div>
      )}

      {/* MDS Station Placement Summary Card */}
      {mdsResponse && !mdsLoading && !mdsError && (
        <div className="bg-gradient-to-br from-purple-50 to-indigo-50/40 border border-purple-200/80 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-600 text-white shadow-xs">
                <Layers className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Station Placement
                </h3>
                <p className="text-sm font-bold text-gray-900">
                  Greedy Minimum Dominating Set
                </p>
              </div>
            </div>
            {onClearMds && (
              <button
                type="button"
                onClick={onClearMds}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
                title="Hide MDS overlay"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2.5 text-xs pt-1">
            <div className="bg-white/80 rounded-lg p-2.5 border border-purple-100">
              <span className="text-gray-500 block">Candidate Pool</span>
              <span className="text-base font-bold text-gray-900">
                {mdsResponse.candidate_count}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2.5 border border-purple-100">
              <span className="text-gray-500 block">Selected Stations</span>
              <span className="text-base font-bold text-purple-700">
                {mdsResponse.selected_count}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2.5 border border-purple-100">
              <span className="text-gray-500 block">Demand Coverage</span>
              <span className="text-base font-bold text-gray-900">
                {mdsResponse.coverage_percentage}%
              </span>
              <span className="text-[10px] text-gray-400 block">
                {mdsResponse.covered_demand_nodes}/{mdsResponse.total_demand_nodes} nodes
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2.5 border border-purple-100">
              <span className="text-gray-500 block">Service Radius</span>
              <span className="text-base font-bold text-gray-900">
                {mdsResponse.coverage_radius_km} km
              </span>
            </div>
          </div>

          <p className="text-[11px] text-purple-900/80 leading-relaxed pt-1 border-t border-purple-100/70">
            ★ Greedy set-cover approximation for network coverage. Not guaranteed globally optimal.
          </p>
        </div>
      )}

      {/* Loading State Feedback */}
      {isLoading && loadingStep && (
        <LoadingState step={loadingStep} />
      )}

      {/* Error Message Display */}
      {error && !isLoading && (
        <ErrorMessage
          message={error}
          onDismiss={onClearError}
          onRetry={
            locationSelection
              ? () => onConfirmLocation(locationSelection.coordinates, locationSelection.source, locationSelection.label || 'Confirmed Location')
              : onUseLiveLocation
          }
        />
      )}

      {/* Active Route Summary Card */}
      {routeResponse && !isLoading && !error && (
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50/40 border border-emerald-200/70 rounded-xl p-4 space-y-3.5">
          {/* Status Badge & Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className={`flex h-7 w-7 items-center justify-center rounded-lg text-white shadow-sm ${
                routeResponse.station.is_existing ? 'bg-emerald-600' : 'bg-purple-600'
              }`}>
                <Zap className="w-4 h-4" />
              </span>
              <div>
                <div className="flex items-center space-x-1.5">
                  <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                    Destination Station
                  </h3>
                  {routeResponse.station.is_existing ? (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                      Real EV Station
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-300">
                      Planning Candidate
                    </span>
                  )}
                </div>
                <p className="text-sm font-bold text-gray-900">
                  {routeResponse.station.name || routeResponse.station.candidate_id}
                </p>
                {routeResponse.station.address && (
                  <p className="text-[11px] text-gray-600 truncate max-w-[200px] sm:max-w-xs">
                    {routeResponse.station.address}
                  </p>
                )}
              </div>
            </div>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              ● Route found
            </span>
          </div>

          <p className="text-xs text-emerald-800 font-medium">
            {routeResponse.station.is_existing
              ? 'Nearest verified EV charging station via road network Dijkstra'
              : 'Nearest feasible candidate charging station'}
          </p>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            {/* Distance Card */}
            <div className="bg-white/80 backdrop-blur-sm rounded-lg p-3 border border-emerald-100/80 shadow-xs">
              <div className="flex items-center space-x-1.5 text-gray-500 mb-1">
                <Milestone className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-medium">Distance</span>
              </div>
              <p className="text-lg font-extrabold text-gray-900 tracking-tight">
                {formatDistance(routeResponse.route.distance_km)}
              </p>
            </div>

            {/* Travel Time Card */}
            <div className="bg-white/80 backdrop-blur-sm rounded-lg p-3 border border-emerald-100/80 shadow-xs">
              <div className="flex items-center space-x-1.5 text-gray-500 mb-1">
                <Clock className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-medium">Est. Travel Time</span>
              </div>
              <p className="text-lg font-extrabold text-gray-900 tracking-tight">
                {formatEta(routeResponse.route.estimated_eta_minutes)}
              </p>
            </div>
          </div>

          {/* Technical Route Details */}
          <div className="text-xs text-gray-600 border-t border-emerald-200/60 pt-3 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="flex items-center text-gray-500">
                <MapPin className="w-3.5 h-3.5 mr-1 text-gray-400" />
                Snapped Road Node:
              </span>
              <span className="font-mono text-gray-800 font-semibold">
                {String(routeResponse.snapped_node)} ({Math.round(routeResponse.distance_to_snapped_node_m)}m away)
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="flex items-center text-gray-500">
                <Navigation className="w-3.5 h-3.5 mr-1 text-gray-400" />
                Route Segments:
              </span>
              <span className="font-mono text-gray-800">
                {routeResponse.route.node_ids.length} road nodes
              </span>
            </div>

            {routeResponse.data_source && (
              <div className="flex items-center justify-between">
                <span className="flex items-center text-gray-500">
                  <Database className="w-3.5 h-3.5 mr-1 text-gray-400" />
                  Road Network Source:
                </span>
                <span className={`font-semibold capitalize px-2 py-0.5 rounded text-[10px] ${
                  routeResponse.data_source === 'osm'
                    ? 'bg-blue-100 text-blue-800'
                    : routeResponse.data_source === 'cache'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-amber-100 text-amber-800'
                }`}>
                  {routeResponse.data_source === 'sample' ? 'Sample (Offline Fallback)' : routeResponse.data_source}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Initial Guidance Card when no route has been fetched */}
      {!routeResponse && !isLoading && !error && (
        <div className="bg-gray-50/80 border border-dashed border-gray-300 rounded-xl p-4 text-center">
          <div className="inline-flex p-3 rounded-full bg-emerald-50 text-emerald-600 mb-2">
            <Navigation className="w-5 h-5" />
          </div>
          <h4 className="text-sm font-semibold text-gray-800">
            Ready to Navigate
          </h4>
          <p className="text-xs text-gray-500 mt-1 leading-relaxed">
            Click <strong>Use My Location</strong> to find the nearest feasible charging station and calculate the Dijkstra route.
          </p>
        </div>
      )}

      {/* Privacy Notice Footer */}
      <div className="flex items-center justify-center space-x-1.5 text-[11px] text-gray-400 pt-1">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
        <span>Location is processed ephemerally and never stored</span>
      </div>
    </div>
  );
};
