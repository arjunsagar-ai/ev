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
  AssignmentResponse,
  CapacityResponse,
  DominatingSetStation,
  InfrastructureResponse,
  LiveRouteResponse,
  UserCoordinates,
} from '../types/routing';
import { formatCoordinates } from '../utils/coordinates';

interface MapViewProps {
  userCoordinates: UserCoordinates | null;
  routeResponse: LiveRouteResponse | null;
  mdsStations?: DominatingSetStation[] | null;
  hungarianResponse?: AssignmentResponse | null;
  infraResponse?: InfrastructureResponse | null;
  capacityResponse?: CapacityResponse | null;
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

// Custom Amber EV Location Marker for Hungarian Matching
const evMarkerIcon = (label: string) =>
  L.divIcon({
    className: 'custom-ev-marker',
    html: `
      <div style="
        position: relative;
        display: inline-flex;
        align-items: center;
        gap: 3px;
        background: #f59e0b;
        color: white;
        border: 2px solid white;
        border-radius: 12px;
        padding: 2px 7px;
        font-size: 11px;
        font-weight: 700;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.35);
        white-space: nowrap;
      ">
        <span style="font-size: 11px;">⚡</span>
        <span>${label}</span>
      </div>
    `,
    iconSize: [60, 24],
    iconAnchor: [30, 12],
    popupAnchor: [0, -14],
  });

/**
 * Helper component that auto-centers or fits bounds on location/route/assignment updates.
 * Avoids recentering on every manual pan/zoom.
 */
const MapAutoBounds: React.FC<{
  userCoordinates: UserCoordinates | null;
  routeCoordinates?: [number, number][];
  mdsStations?: DominatingSetStation[] | null;
  hungarianResponse?: AssignmentResponse | null;
  infraResponse?: InfrastructureResponse | null;
}> = ({ userCoordinates, routeCoordinates, mdsStations, hungarianResponse, infraResponse }) => {
  const map = useMap();
  const prevRouteRef = useRef<string | null>(null);
  const prevUserRef = useRef<string | null>(null);
  const prevMdsRef = useRef<string | null>(null);
  const prevHungarianRef = useRef<string | null>(null);
  const prevInfraRef = useRef<string | null>(null);

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

    // 2. If infrastructure MST edges exist and changed (and no active route), fit view to infrastructure edges
    if (
      infraResponse?.edges &&
      infraResponse.edges.length > 0 &&
      (!routeCoordinates || routeCoordinates.length === 0)
    ) {
      const infraKey = infraResponse.edges.map((e) => `${e.from_station_id}->${e.to_station_id}`).join(',');
      if (infraKey !== prevInfraRef.current) {
        prevInfraRef.current = infraKey;
        const allPoints: [number, number][] = [];
        infraResponse.edges.forEach((e) => {
          e.path_coordinates.forEach((pt) => {
            allPoints.push([pt[0], pt[1]]);
          });
        });
        if (allPoints.length > 0) {
          map.fitBounds(allPoints, { padding: [60, 60], maxZoom: 15 });
          return;
        }
      }
    }

    // 3. If Hungarian assignments exist and changed (and no active route), fit view to assignments
    if (
      hungarianResponse?.assignments &&
      hungarianResponse.assignments.length > 0 &&
      (!routeCoordinates || routeCoordinates.length === 0)
    ) {
      const hKey = hungarianResponse.assignments.map((a) => `${a.ev_id}->${a.station_id}`).join(',');
      if (hKey !== prevHungarianRef.current) {
        prevHungarianRef.current = hKey;
        const allPoints: [number, number][] = [];
        hungarianResponse.assignments.forEach((a) => {
          allPoints.push([a.ev_latitude, a.ev_longitude]);
          allPoints.push([a.station_latitude, a.station_longitude]);
        });
        if (allPoints.length > 0) {
          map.fitBounds(allPoints, { padding: [60, 60], maxZoom: 15 });
          return;
        }
      }
    }

    // 4. If MDS stations exist and changed (and no active route), fit view to stations
    if (mdsStations && mdsStations.length > 0 && (!routeCoordinates || routeCoordinates.length === 0)) {
      const mdsKey = mdsStations.map((s) => s.candidate_id).join(',');
      if (mdsKey !== prevMdsRef.current) {
        prevMdsRef.current = mdsKey;
        const bounds: LatLngBoundsExpression = mdsStations.map((s) => [s.latitude, s.longitude]);
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 15 });
        return;
      }
    }

    // 5. Otherwise, if user location just became available, pan to user
    if (userCoordinates) {
      const userKey = `${userCoordinates.latitude},${userCoordinates.longitude}`;
      if (userKey !== prevUserRef.current) {
        prevUserRef.current = userKey;
        map.setView([userCoordinates.latitude, userCoordinates.longitude], 15);
      }
    }
  }, [map, userCoordinates, routeCoordinates, mdsStations, hungarianResponse, infraResponse]);

  return null;
};

export const MapView: React.FC<MapViewProps> = ({
  userCoordinates,
  routeResponse,
  mdsStations,
  hungarianResponse,
  infraResponse,
  capacityResponse,
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
          mdsStations={mdsStations}
          hungarianResponse={hungarianResponse}
          infraResponse={infraResponse}
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
          mdsStations.map((station) => {
            // Build per-station capacity utilization if Phase 6 data is available
            const capUtil = capacityResponse?.station_utilization?.find(
              (u) => u.station_id === station.candidate_id,
            );
            return (
              <StationMarker
                key={`mds-${station.candidate_id}`}
                station={station}
                variant="mds_selected"
                coveredDemandCount={station.covered_demand_count}
                capacityUtilization={capUtil}
              />
            );
          })}

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

        {/* Phase 5B: Hungarian EV Markers and Assignment Polylines */}
        {hungarianResponse?.assignments &&
          hungarianResponse.assignments.map((asgn) => {
            const isUserLocation =
              userCoordinates &&
              Math.abs(userCoordinates.latitude - asgn.ev_latitude) < 0.0001 &&
              Math.abs(userCoordinates.longitude - asgn.ev_longitude) < 0.0001;

            const pathPositions: [number, number][] =
              asgn.path_coordinates && asgn.path_coordinates.length > 0
                ? (asgn.path_coordinates as [number, number][])
                : [
                    [asgn.ev_latitude, asgn.ev_longitude],
                    [asgn.station_latitude, asgn.station_longitude],
                  ];

            return (
              <React.Fragment key={`hungarian-${asgn.ev_id}-${asgn.station_id}`}>
                {/* Render distinct EV marker if not at user's exact current pin */}
                {!isUserLocation && (
                  <Marker
                    position={[asgn.ev_latitude, asgn.ev_longitude]}
                    icon={evMarkerIcon(asgn.ev_id)}
                  >
                    <Popup>
                      <div className="p-1 text-xs">
                        <div className="flex items-center space-x-1.5 font-bold text-gray-900 pb-1 border-b border-gray-100">
                          <span className="h-2 w-2 rounded-full bg-amber-500"></span>
                          <span>Vehicle {asgn.ev_id}</span>
                        </div>
                        <p className="text-gray-600 mt-1">
                          Matched to Station: <strong>{asgn.station_id}</strong>
                        </p>
                        <p className="text-gray-500 mt-0.5">
                          Cost: <strong>{asgn.cost_km} km</strong>
                        </p>
                      </div>
                    </Popup>
                  </Marker>
                )}

                {/* Orange Dashed Hungarian Assignment Polyline */}
                <Polyline
                  positions={pathPositions}
                  pathOptions={{
                    color: '#ea580c',
                    weight: 3.5,
                    dashArray: '6, 8',
                    opacity: 0.9,
                    lineCap: 'round',
                  }}
                >
                  <Popup>
                    <div className="p-1 text-xs">
                      <p className="font-bold text-orange-700">Hungarian Matching</p>
                      <p className="text-gray-700 mt-0.5">
                        <strong>{asgn.ev_id}</strong> &rarr; <strong>{asgn.station_id}</strong>
                      </p>
                      <p className="text-gray-500 mt-0.5">
                        Distance: <strong>{asgn.cost_km} km</strong>
                      </p>
                    </div>
                  </Popup>
                </Polyline>
              </React.Fragment>
            );
          })}

        {/* Phase 5C: Prim MST Infrastructure Connection Edges */}
        {infraResponse?.edges &&
          infraResponse.edges.map((edge, idx) => {
            const pathPositions: [number, number][] =
              edge.path_coordinates && edge.path_coordinates.length > 0
                ? (edge.path_coordinates as [number, number][])
                : [];

            if (pathPositions.length === 0) return null;

            return (
              <React.Fragment key={`mst-edge-${edge.from_station_id}-${edge.to_station_id}-${idx}`}>
                {/* Background Shadow/Glow for Infrastructure Polyline */}
                <Polyline
                  positions={pathPositions}
                  pathOptions={{
                    color: '#0f766e',
                    weight: 6,
                    opacity: 0.25,
                    lineCap: 'round',
                  }}
                />
                {/* Teal Dashed Infrastructure Edge */}
                <Polyline
                  positions={pathPositions}
                  pathOptions={{
                    color: '#0d9488',
                    weight: 4,
                    dashArray: '10, 6',
                    opacity: 0.95,
                    lineCap: 'round',
                  }}
                >
                  <Popup>
                    <div className="p-1 text-xs">
                      <div className="flex items-center space-x-1.5 font-bold text-teal-800 pb-1 border-b border-teal-100">
                        <span className="h-2 w-2 rounded-full bg-teal-600"></span>
                        <span>MST Infrastructure Connection</span>
                      </div>
                      <p className="text-gray-700 mt-1">
                        <strong>{edge.from_station_id}</strong> &harr; <strong>{edge.to_station_id}</strong>
                      </p>
                      <p className="text-gray-500 mt-0.5">
                        Connection Distance: <strong>{edge.cost_km} km</strong>
                      </p>
                    </div>
                  </Popup>
                </Polyline>
              </React.Fragment>
            );
          })}
      </MapContainer>
    </div>
  );
};
