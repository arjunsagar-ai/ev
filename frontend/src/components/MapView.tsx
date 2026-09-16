import React, { useEffect, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from 'react-leaflet';
import L, { LatLngBoundsExpression } from 'leaflet';
import { StationMarker } from './StationMarker';
import {
  DominatingSetStation,
  LiveRouteResponse,
  UserCoordinates,
} from '../types/routing';
import { formatCoordinates } from '../utils/coordinates';

interface MapViewProps {
  userCoordinates: UserCoordinates | null;
  routeResponse: LiveRouteResponse | null;
  mdsStations?: DominatingSetStation[] | null;
}

// Neutral default center (near sample network area)
const DEFAULT_CENTER: [number, number] = [10.003, 76.310];
const DEFAULT_ZOOM = 14;

// Custom Blue Pulsing User Location Marker
const userMarkerIcon = L.divIcon({
  className: 'custom-user-location-marker',
  html: `
    <div style="
      position: relative;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        position: absolute;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: rgba(37, 99, 235, 0.35);
      "></div>
      <div style="
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #2563eb;
        border: 2.5px solid #ffffff;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.35);
      "></div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  popupAnchor: [0, -14],
});

/**
 * Helper component that auto-centers or fits bounds on location/route updates.
 * Avoids recentering on every manual pan/zoom.
 */
const MapAutoBounds: React.FC<{
  userCoordinates: UserCoordinates | null;
  routeCoordinates?: [number, number][];
  mdsStations?: DominatingSetStation[] | null;
}> = ({ userCoordinates, routeCoordinates, mdsStations }) => {
  const map = useMap();
  const prevRouteRef = useRef<string | null>(null);
  const prevUserRef = useRef<string | null>(null);
  const prevMdsRef = useRef<string | null>(null);

  useEffect(() => {
    // 1. If route coordinates exist and changed, fit the view to encompass the entire route
    if (routeCoordinates && routeCoordinates.length > 0) {
      const routeKey = JSON.stringify(routeCoordinates);
      if (routeKey !== prevRouteRef.current) {
        prevRouteRef.current = routeKey;
        const bounds: LatLngBoundsExpression = routeCoordinates.map((c) => [c[0], c[1]]);
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
        return;
      }
    }

    // 2. If MDS stations exist and changed (and no active route), fit view to stations
    if (mdsStations && mdsStations.length > 0 && (!routeCoordinates || routeCoordinates.length === 0)) {
      const mdsKey = mdsStations.map((s) => s.candidate_id).join(',');
      if (mdsKey !== prevMdsRef.current) {
        prevMdsRef.current = mdsKey;
        const bounds: LatLngBoundsExpression = mdsStations.map((s) => [s.latitude, s.longitude]);
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 15 });
        return;
      }
    }

    // 3. Otherwise, if user location just became available, pan to user
    if (userCoordinates) {
      const userKey = `${userCoordinates.latitude},${userCoordinates.longitude}`;
      if (userKey !== prevUserRef.current) {
        prevUserRef.current = userKey;
        map.setView([userCoordinates.latitude, userCoordinates.longitude], 15);
      }
    }
  }, [map, userCoordinates, routeCoordinates, mdsStations]);

  return null;
};

export const MapView: React.FC<MapViewProps> = ({
  userCoordinates,
  routeResponse,
  mdsStations,
}) => {
  const routePolyline = routeResponse?.route?.coordinates;

  return (
    <div className="relative w-full h-full min-h-[400px] rounded-2xl overflow-hidden border border-gray-200/80 shadow-md">
      <MapContainer
        center={
          userCoordinates
            ? [userCoordinates.latitude, userCoordinates.longitude]
            : DEFAULT_CENTER
        }
        zoom={DEFAULT_ZOOM}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        {/* OpenStreetMap Standard Vector Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* Auto Bounds and View Handler */}
        <MapAutoBounds
          userCoordinates={userCoordinates}
          routeCoordinates={routePolyline}
        />

        {/* User GPS Location Marker */}
        {userCoordinates && (
          <Marker
            position={[userCoordinates.latitude, userCoordinates.longitude]}
            icon={userMarkerIcon}
          >
            <Popup>
              <div className="p-1 text-xs">
                <div className="flex items-center space-x-1.5 font-bold text-gray-900 pb-1 border-b border-gray-100">
                  <span className="h-2 w-2 rounded-full bg-blue-600"></span>
                  <span>You are here</span>
                </div>
                <p className="text-gray-500 mt-1.5">
                  {formatCoordinates(
                    userCoordinates.latitude,
                    userCoordinates.longitude
                  )}
                </p>
                {userCoordinates.accuracy !== undefined && (
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    Accuracy: ±{Math.round(userCoordinates.accuracy)}m
                  </p>
                )}
              </div>
            </Popup>
          </Marker>
        )}

        {/* MDS Optimized Station Markers */}
        {mdsStations &&
          mdsStations.map((station) => (
            <StationMarker
              key={`mds-${station.candidate_id}`}
              station={station}
              variant="mds_selected"
              coveredDemandCount={station.covered_demand_count}
            />
          ))}

        {/* Destination Station Marker */}
        {routeResponse?.station && (
          <StationMarker
            station={routeResponse.station}
            distanceKm={routeResponse.route?.distance_km}
            etaMinutes={routeResponse.route?.estimated_eta_minutes}
            variant="route_destination"
          />
        )}

        {/* Dijkstra Route Polyline */}
        {routePolyline && routePolyline.length > 0 && (
          <>
            {/* Route Shadow/Border for contrast */}
            <Polyline
              positions={routePolyline}
              pathOptions={{
                color: '#1e40af',
                weight: 7,
                opacity: 0.35,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
            {/* Main Vibrant Route Polyline */}
            <Polyline
              positions={routePolyline}
              pathOptions={{
                color: '#2563eb',
                weight: 4.5,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
          </>
        )}
      </MapContainer>
    </div>
  );
};
