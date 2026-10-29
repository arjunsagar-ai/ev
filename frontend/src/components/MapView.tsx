import React, { useEffect, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  GeoJSON,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L, { LatLngBoundsExpression } from 'leaflet';
import { X } from 'lucide-react';
import { StationMarker } from './StationMarker';
import {
  AssignmentResponse,
  CapacityResponse,
  DominatingSetStation,
  ExistingStation,
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
  isSelectingOnMap?: boolean;
  onMapClick?: (coords: [number, number]) => void;
  pendingCoordinates?: UserCoordinates | null;
  pendingLabel?: string | null;
  onCancelMapSelection?: () => void;
  existingStations?: ExistingStation[] | null;
  districtBoundary?: any;
}

// Neutral default center for Ernakulam District
const DEFAULT_CENTER: [number, number] = [10.020, 76.330];
const DEFAULT_ZOOM = 12;

// Custom Green Pin for Verified Existing EV Stations from dataset
const existingStationIcon = L.divIcon({
  className: 'custom-real-station-marker',
  html: `
    <div style="
      width: 26px;
      height: 26px;
      background: #059669;
      border: 2px solid #ffffff;
      border-radius: 50%;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-size: 13px;
      font-weight: bold;
    ">
      ⚡
    </div>
  `,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
  popupAnchor: [0, -13],
});

// Custom Amber Pulsing Pending Location Marker for Search / Map Picking preview
const pendingMarkerIcon = L.divIcon({
  className: 'custom-pending-location-marker',
  html: `
    <div style="
      position: relative;
      width: 26px;
      height: 26px;
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        position: absolute;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: rgba(245, 158, 11, 0.4);
        box-shadow: 0 0 10px rgba(245, 158, 11, 0.8);
      "></div>
      <div style="
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #f59e0b;
        border: 2.5px solid #ffffff;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.35);
      "></div>
    </div>
  `,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
  popupAnchor: [0, -14],
});

// Map click event interceptor
const MapClickHandler: React.FC<{
  active: boolean;
  onMapClick?: (coords: [number, number]) => void;
}> = ({ active, onMapClick }) => {
  useMapEvents({
    click(e) {
      if (active && onMapClick) {
        onMapClick([e.latlng.lat, e.latlng.lng]);
      }
    },
  });
  return null;
};

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
  pendingCoordinates?: UserCoordinates | null;
  routeCoordinates?: [number, number][];
  mdsStations?: DominatingSetStation[] | null;
  hungarianResponse?: AssignmentResponse | null;
  infraResponse?: InfrastructureResponse | null;
}> = ({ userCoordinates, pendingCoordinates, routeCoordinates, mdsStations, hungarianResponse, infraResponse }) => {
  const map = useMap();
  const prevRouteRef = useRef<string | null>(null);
  const prevPendingRef = useRef<string | null>(null);
  const prevUserRef = useRef<string | null>(null);
  const prevMdsRef = useRef<string | null>(null);
  const prevHungarianRef = useRef<string | null>(null);
  const prevInfraRef = useRef<string | null>(null);

  useEffect(() => {
    // 0. If pending preview coordinates exist and changed, center view on preview
    if (pendingCoordinates) {
      const pKey = `${pendingCoordinates.latitude},${pendingCoordinates.longitude}`;
      if (pKey !== prevPendingRef.current) {
        prevPendingRef.current = pKey;
        map.setView([pendingCoordinates.latitude, pendingCoordinates.longitude], 15);
        return;
      }
    }

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
  isSelectingOnMap,
  onMapClick,
  pendingCoordinates,
  pendingLabel,
  onCancelMapSelection,
  existingStations,
  districtBoundary,
}) => {
  const routePolyline = routeResponse?.route?.coordinates;

  return (
    <div className={`relative w-full h-full min-h-[400px] rounded-2xl overflow-hidden border border-gray-200/80 shadow-md ${
      isSelectingOnMap ? 'ring-2 ring-blue-500' : ''
    }`}>
      {/* Floating Map Picking Instruction Banner */}
      {isSelectingOnMap && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-blue-600/95 backdrop-blur-xs text-white px-4 py-2 rounded-xl shadow-lg flex items-center space-x-2 text-xs font-semibold animate-pulse">
          <span>🗺️ Click anywhere on the map to set your location</span>
          {onCancelMapSelection && (
            <button
              type="button"
              onClick={onCancelMapSelection}
              className="ml-2 bg-blue-700 hover:bg-blue-800 text-white p-1 rounded-md transition-colors"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      <MapContainer
        center={
          pendingCoordinates
            ? [pendingCoordinates.latitude, pendingCoordinates.longitude]
            : userCoordinates
            ? [userCoordinates.latitude, userCoordinates.longitude]
            : DEFAULT_CENTER
        }
        zoom={DEFAULT_ZOOM}
        scrollWheelZoom={true}
        className={`w-full h-full ${isSelectingOnMap ? 'cursor-crosshair' : ''}`}
      >
        {/* Map Click Handler for "Choose on Map" mode */}
        <MapClickHandler active={!!isSelectingOnMap} onMapClick={onMapClick} />

        {/* OpenStreetMap Standard Vector Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* Auto Bounds and View Handler */}
        <MapAutoBounds
          userCoordinates={userCoordinates}
          pendingCoordinates={pendingCoordinates}
          routeCoordinates={routePolyline}
          mdsStations={mdsStations}
          hungarianResponse={hungarianResponse}
          infraResponse={infraResponse}
        />

        {/* Ernakulam District Administrative Boundary Outline */}
        {districtBoundary && (
          <GeoJSON
            key="ernakulam-district-boundary-layer"
            data={districtBoundary}
            pathOptions={{
              color: '#059669',
              weight: 2,
              dashArray: '6, 6',
              fillColor: '#10b981',
              fillOpacity: 0.03,
            }}
          />
        )}

        {/* Existing Real-World EV Charging Stations (from CSV dataset) */}
        {existingStations &&
          existingStations.map((stn) => (
            <Marker
              key={`existing-${stn.station_id}`}
              position={[stn.latitude, stn.longitude]}
              icon={existingStationIcon}
            >
              <Popup>
                <div className="p-1 text-xs max-w-[220px]">
                  <div className="flex items-center justify-between pb-1 mb-1 border-b border-gray-100">
                    <span className="font-bold text-gray-900 text-xs truncate mr-1.5">{stn.name}</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 whitespace-nowrap">
                      Existing EV Station
                    </span>
                  </div>
                  <p className="text-gray-600 text-[11px] leading-tight mb-1">{stn.address}</p>
                  <p className="text-gray-500 text-[10px]">
                    Locality: <strong>{stn.city}</strong> &bull; Type: <strong>{stn.station_type}</strong>
                  </p>
                  {stn.distance_km !== undefined && stn.distance_km !== null && (
                    <p className="text-emerald-700 font-bold mt-1 text-[11px]">
                      Distance: {stn.distance_km} km
                    </p>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}

        {/* Pending Location Preview Marker */}
        {pendingCoordinates && (
          <Marker
            position={[pendingCoordinates.latitude, pendingCoordinates.longitude]}
            icon={pendingMarkerIcon}
          >
            <Popup>
              <div className="p-1.5 text-xs">
                <div className="flex items-center space-x-1.5 font-bold text-amber-900 pb-1 border-b border-amber-100">
                  <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping"></span>
                  <span>📍 Preview Location</span>
                </div>
                <p className="text-gray-700 mt-1 font-medium">
                  {pendingLabel || 'Click "Confirm Location" in the panel to activate.'}
                </p>
              </div>
            </Popup>
          </Marker>
        )}

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
