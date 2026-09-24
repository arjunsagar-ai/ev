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
} from 'lucide-react';
import {
  AssignmentResponse,
  DominatingSetResponse,
  InfrastructureResponse,
  LiveRouteResponse,
} from '../types/routing';
import { formatDistance, formatEta } from '../utils/coordinates';
import { LocationButton } from './LocationButton';
import { LoadingState } from './LoadingState';
import { ErrorMessage } from './ErrorMessage';

interface RoutePanelProps {
  routeResponse: LiveRouteResponse | null;
  isLoading: boolean;
  loadingStep: 'gps' | 'routing' | null;
  error: string | null;
  onLocate: () => void;
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
}

export const RoutePanel: React.FC<RoutePanelProps> = ({
  routeResponse,
  isLoading,
  loadingStep,
  error,
  onLocate,
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
}) => {
  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-lg p-5 flex flex-col space-y-4">
      {/* Action Button */}
      <div className="space-y-2">
        <LocationButton
          onClick={onLocate}
          isLoading={isLoading}
          isError={!!error}
          loadingStep={loadingStep}
        />

        {/* Network Optimization Action Button */}
        <button
          type="button"
          onClick={onOptimizeMds}
          disabled={mdsLoading || isLoading}
          className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-purple-200 
            text-sm font-semibold rounded-xl shadow-xs transition-all duration-200 focus:outline-none 
            focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 bg-purple-50 hover:bg-purple-100 
            text-purple-700 disabled:opacity-60 disabled:cursor-not-allowed active:scale-[0.98]"
        >
          {mdsLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2 text-purple-600" />
              <span>Optimizing station placement...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 mr-2 text-purple-600" />
              <span>Optimize Charging Stations</span>
            </>
          )}
        </button>

        {/* Phase 5B: Hungarian Bipartite Assignment Action Button */}
        <button
          type="button"
          onClick={onAssignHungarian}
          disabled={hungarianLoading || isLoading}
          className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-amber-200 
            text-sm font-semibold rounded-xl shadow-xs transition-all duration-200 focus:outline-none 
            focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 bg-amber-50 hover:bg-amber-100 
            text-amber-800 disabled:opacity-60 disabled:cursor-not-allowed active:scale-[0.98]"
        >
          {hungarianLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2 text-amber-600" />
              <span>Calculating Hungarian matching...</span>
            </>
          ) : (
            <>
              <ArrowRightLeft className="w-4 h-4 mr-2 text-amber-600" />
              <span>Assign EVs to Stations</span>
            </>
          )}
        </button>

        {/* Phase 5C: Prim MST Infrastructure Optimization Action Button */}
        <button
          type="button"
          onClick={onOptimizeInfrastructure}
          disabled={infraLoading || isLoading}
          className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-teal-200 
            text-sm font-semibold rounded-xl shadow-xs transition-all duration-200 focus:outline-none 
            focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 bg-teal-50 hover:bg-teal-100 
            text-teal-800 disabled:opacity-60 disabled:cursor-not-allowed active:scale-[0.98]"
        >
          {infraLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2 text-teal-600" />
              <span>Optimizing infrastructure MST...</span>
            </>
          ) : (
            <>
              <Network className="w-4 h-4 mr-2 text-teal-600" />
              <span>Optimize Infrastructure</span>
            </>
          )}
        </button>
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
          onRetry={onLocate}
        />
      )}

      {/* Active Route Summary Card */}
      {routeResponse && !isLoading && !error && (
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50/40 border border-emerald-200/70 rounded-xl p-4 space-y-3.5">
          {/* Status Badge & Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-sm">
                <Zap className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Destination Station
                </h3>
                <p className="text-sm font-bold text-gray-900">
                  {routeResponse.station.candidate_id}
                </p>
              </div>
            </div>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              ● Route found
            </span>
          </div>

          <p className="text-xs text-emerald-800 font-medium">
            Nearest feasible charging station
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
