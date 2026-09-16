import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { formatDistance, formatEta } from '../utils/coordinates';
import { StationInfo } from '../types/routing';

interface StationMarkerProps {
  station: StationInfo;
  distanceKm?: number;
  etaMinutes?: number | null;
}

// Custom Green EV Charging Station Pin
const stationIcon = L.divIcon({
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

export const StationMarker: React.FC<StationMarkerProps> = ({
  station,
  distanceKm,
  etaMinutes,
}) => {
  return (
    <Marker
      position={[station.latitude, station.longitude]}
      icon={stationIcon}
    >
      <Popup>
        <div className="p-1 min-w-[200px]">
          <div className="flex items-center space-x-2 border-b border-gray-100 pb-2 mb-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">
              ⚡
            </span>
            <div>
              <h3 className="font-bold text-gray-900 text-sm">
                EV Charging Station
              </h3>
              <p className="text-[11px] font-medium text-emerald-600">
                Nearest feasible charging station
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
          </div>
        </div>
      </Popup>
    </Marker>
  );
};
