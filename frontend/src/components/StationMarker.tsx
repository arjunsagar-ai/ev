import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { formatDistance, formatEta } from '../utils/coordinates';
import { StationInfo, StationUtilization } from '../types/routing';

interface StationMarkerProps {
  station: StationInfo;
  distanceKm?: number;
  etaMinutes?: number | null;
  variant?: 'route_destination' | 'mds_selected';
  coveredDemandCount?: number | null;
  capacityUtilization?: StationUtilization | null;
}

// Custom Green Pin for Live Route Destination Station
const routeStationIcon = L.divIcon({
  className: 'custom-station-icon',
  html: `
    <div style="
      background-color: #10b981;
      width: 38px;
      height: 38px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      border: 3px solid #ffffff;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25);
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        transform: rotate(45deg);
        color: #ffffff;
        font-size: 16px;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        ⚡
      </div>
    </div>
  `,
  iconSize: [38, 38],
  iconAnchor: [19, 38],
  popupAnchor: [0, -36],
});

// Custom Purple/Indigo Pin for MDS-Selected Stations
const mdsStationIcon = L.divIcon({
  className: 'custom-mds-station-icon',
  html: `
    <div style="
      background-color: #7c3aed;
      width: 34px;
      height: 34px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      border: 3px solid #ffffff;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25);
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        transform: rotate(45deg);
        color: #ffffff;
        font-size: 14px;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        ★
      </div>
    </div>
  `,
  iconSize: [34, 34],
  iconAnchor: [17, 34],
  popupAnchor: [0, -32],
});

export const StationMarker: React.FC<StationMarkerProps> = ({
  station,
  distanceKm,
  etaMinutes,
  variant = 'route_destination',
  coveredDemandCount,
  capacityUtilization,
}) => {
  const isMds = variant === 'mds_selected';
  const icon = isMds ? mdsStationIcon : routeStationIcon;

  return (
    <Marker
      position={[station.latitude, station.longitude]}
      icon={icon}
    >
      <Popup>
        <div className="p-1 min-w-[210px]">
          <div className="flex items-center space-x-2 border-b border-gray-100 pb-2 mb-2">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                isMds
                  ? 'bg-purple-100 text-purple-700'
                  : 'bg-emerald-100 text-emerald-700'
              }`}
            >
              {isMds ? '★' : '⚡'}
            </span>
            <div>
              <h3 className="font-bold text-gray-900 text-sm">
                EV Charging Station
              </h3>
              <p
                className={`text-[11px] font-medium ${
                  isMds ? 'text-purple-600' : 'text-emerald-600'
                }`}
              >
                {isMds
                  ? 'MDS Selected (Coverage Approx.)'
                  : 'Nearest feasible charging station'}
              </p>
            </div>
          </div>

          <div className="space-y-1.5 text-xs text-gray-600">
            <div className="flex justify-between">
              <span className="text-gray-500">Station ID:</span>
              <span className="font-semibold text-gray-800">{station.candidate_id}</span>
            </div>

            {distanceKm !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">Distance:</span>
                <span className="font-semibold text-emerald-700">
                  {formatDistance(distanceKm)}
                </span>
              </div>
            )}

            {etaMinutes !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">Estimated Travel Time:</span>
                <span className="font-semibold text-gray-800">
                  {formatEta(etaMinutes)}
                </span>
              </div>
            )}

            {station.nearest_road_node && (
              <div className="flex justify-between">
                <span className="text-gray-500">Connected Road Node:</span>
                <span className="font-mono text-gray-700">{String(station.nearest_road_node)}</span>
              </div>
            )}

            {station.feasibility_score !== undefined && station.feasibility_score !== null && (
              <div className="flex justify-between">
                <span className="text-gray-500">Feasibility Score:</span>
                <span className="font-semibold text-gray-800">
                  {(station.feasibility_score * 100).toFixed(0)}%
                </span>
              </div>
            )}

            {coveredDemandCount !== undefined && coveredDemandCount !== null && (
              <div className="flex justify-between">
                <span className="text-gray-500">Demand Nodes Covered:</span>
                <span className="font-semibold text-purple-700">
                  {coveredDemandCount}
                </span>
              </div>
            )}

            {/* Phase 6: Simulated Capacity Utilization (if available) */}
            {capacityUtilization && (
              <>
                <div className="border-t border-violet-100 pt-1.5 mt-1.5">
                  <span className="text-[10px] font-bold text-violet-700 uppercase tracking-wide">
                    Simulated Capacity
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Flow / Capacity:</span>
                  <span className={`font-semibold ${capacityUtilization.is_saturated ? 'text-rose-700' : 'text-violet-700'}`}>
                    {capacityUtilization.utilized_capacity}/{capacityUtilization.available_capacity}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Utilization:</span>
                  <span className={`font-semibold ${capacityUtilization.is_saturated ? 'text-rose-700' : 'text-violet-700'}`}>
                    {capacityUtilization.utilization_pct}%
                    {capacityUtilization.is_saturated && ' ⚠ Saturated'}
                  </span>
                </div>
                <p className="text-[10px] text-gray-400 leading-tight">
                  Estimated planning values — not real grid data.
                </p>
              </>
            )}
          </div>
        </div>
      </Popup>
    </Marker>
  );
};
