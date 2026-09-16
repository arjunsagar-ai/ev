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
} from 'lucide-react';
import { DominatingSetResponse, LiveRouteResponse } from '../types/routing';
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
      </div>

      {/* MDS Error Message Display */}
      {mdsError && !mdsLoading && (
        <ErrorMessage
          message={mdsError}
          onRetry={onOptimizeMds}
        />
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
