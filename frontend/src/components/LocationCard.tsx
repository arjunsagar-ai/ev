import React, { useState } from 'react';
import {
  MapPin,
  Search,
  LocateFixed,
  Map as MapIcon,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  X,
} from 'lucide-react';
import {
  LocationSource,
  UserCoordinates,
  UserLocationSelection,
  GeocodeResult,
} from '../types/routing';
import { searchLocation } from '../api/geocodingApi';
import { isPointInErnakulam, ERNAKULAM_COVERAGE_MESSAGE } from '../utils/districtBoundary';

interface LocationCardProps {
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
  districtBoundary?: any;
}

export const LocationCard: React.FC<LocationCardProps> = ({
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
}) => {
  // Search state
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<GeocodeResult[]>([]);
  const [isSearchLoading, setIsSearchLoading] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleStartSearch = () => {
    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);
    onCancelMapSelection();
    onClearPending();
  };

  const handleCancelSearch = () => {
    setIsSearching(false);
    setSearchQuery('');
    setSearchResults([]);
    setSearchError(null);
    onClearPending();
  };

  const handleExecuteSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      setSearchError('Please enter a location to search.');
      return;
    }

    setIsSearchLoading(true);
    setSearchError(null);
    try {
      const results = await searchLocation(query);
      if (results.length === 0) {
        setSearchError('No locations found. Try a different place name or city.');
      } else {
        setSearchResults(results);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setSearchError(err.message);
      } else {
        setSearchError('Location search is temporarily unavailable.');
      }
    } finally {
      setIsSearchLoading(false);
    }
  };

  const handlePickSearchResult = (result: GeocodeResult) => {
    // Phase 7.1: Verify point is inside Ernakulam District
    const inErnakulam = isPointInErnakulam(result.latitude, result.longitude, districtBoundary);
    if (!inErnakulam) {
      const placeName = result.name || result.displayName.split(',')[0] || 'Selected location';
      setSearchError(
        `${placeName} is outside the current Ernakulam district project coverage. ${ERNAKULAM_COVERAGE_MESSAGE}`
      );
      onClearPending();
      return;
    }

    setSearchError(null);
    onSelectPendingCoords(
      {
        latitude: result.latitude,
        longitude: result.longitude,
      },
      result.displayName
    );
  };

  const handleConfirmPending = () => {
    if (!pendingCoordinates) return;

    // Phase 7.1: Strict check before confirming any pending coordinate
    const inErnakulam = isPointInErnakulam(
      pendingCoordinates.latitude,
      pendingCoordinates.longitude,
      districtBoundary
    );
    if (!inErnakulam) {
      const label = pendingLabel || 'Selected location';
      setSearchError(
        `${label} is outside the current Ernakulam district project coverage. ${ERNAKULAM_COVERAGE_MESSAGE}`
      );
      onClearPending();
      return;
    }

    const source: LocationSource = isSelectingOnMap ? 'map' : 'search';
    const label = pendingLabel || (source === 'map' ? 'Selected on Map' : 'Search Result');
    onConfirmLocation(pendingCoordinates, source, label);
    setIsSearching(false);
    setSearchQuery('');
    setSearchResults([]);
    onCancelMapSelection();
  };

  // Helper for source badge text
  const getSourceDisplay = (source: LocationSource) => {
    switch (source) {
      case 'live':
        return 'Live GPS';
      case 'search':
        return 'Search';
      case 'map':
        return 'Map Selection';
    }
  };

  const handleSelectPreset = (preset: { label: string; latitude: number; longitude: number }) => {
    setSearchError(null);
    onConfirmLocation(
      { latitude: preset.latitude, longitude: preset.longitude },
      'search',
      preset.label
    );
  };

  const QUICK_PRESETS = [
    { label: 'Kochi (Center)', latitude: 9.9816, longitude: 76.2999 },
    { label: 'Aluva', latitude: 10.1076, longitude: 76.3516 },
    { label: 'Kakkanad', latitude: 10.0159, longitude: 76.3419 },
    { label: 'Edappally', latitude: 10.0261, longitude: 76.3086 },
  ];

  return (
    <div className="bg-white rounded-2xl border border-gray-200/90 shadow-md p-4 transition-all">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-gray-900 leading-tight">Your Location</h2>
            <p className="text-[11px] text-gray-500">Origin for EV route and charging optimization</p>
          </div>
        </div>

        {locationSelection && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
            Selected
          </span>
        )}
      </div>

      {/* Global Notice if Error Exists */}
      {searchError && (
        <div className="mt-3 bg-rose-50 border border-rose-200 rounded-xl p-2.5 text-rose-800 text-xs flex items-start justify-between space-x-2">
          <div className="flex items-start space-x-2">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
            <span>{searchError}</span>
          </div>
          <button
            type="button"
            onClick={() => setSearchError(null)}
            className="text-rose-500 hover:text-rose-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ── Mode 1: Confirmed Location Active ── */}
      {locationSelection && !isSearching && !isSelectingOnMap && !pendingCoordinates && (
        <div className="pt-3 space-y-3">
          <div className="bg-emerald-50/70 border border-emerald-100 rounded-xl p-3">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700">
                  ✓ Location Confirmed
                </span>
                <p className="text-sm font-bold text-gray-900 leading-snug">
                  {locationSelection.label || 'Current Location'}
                </p>
                <div className="flex items-center space-x-2 pt-1">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-white text-gray-700 border border-gray-200 shadow-2xs">
                    Source: {getSourceDisplay(locationSelection.source)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onChangeLocation}
            className="w-full inline-flex items-center justify-center px-3 py-2 text-xs font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl transition-colors"
          >
            Change Location
          </button>
        </div>
      )}

      {/* ── Mode 2: Pending Confirmation (from Search Result or Map Click) ── */}
      {pendingCoordinates && (
        <div className="pt-3 space-y-3">
          <div className="bg-amber-50/80 border border-amber-200 rounded-xl p-3">
            <div className="flex items-start space-x-2">
              <MapPin className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">
                  {isSelectingOnMap ? '📍 Selected on Map' : '📍 Selected from Search'}
                </span>
                <p className="text-sm font-bold text-gray-900 mt-0.5 leading-snug">
                  {pendingLabel || (isSelectingOnMap ? 'Pin placed on map' : 'Selected place')}
                </p>
                <p className="text-[11px] text-amber-800/80 mt-1">
                  Preview marker placed on map. Confirm to use this origin.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={handleConfirmPending}
              className="inline-flex items-center justify-center px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all active:scale-[0.98]"
            >
              <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
              Confirm Location
            </button>
            <button
              type="button"
              onClick={() => {
                onClearPending();
                if (isSelectingOnMap) {
                  onStartMapSelection();
                }
              }}
              className="inline-flex items-center justify-center px-3 py-2.5 bg-white hover:bg-gray-50 text-gray-700 text-xs font-semibold border border-gray-200 rounded-xl transition-colors"
            >
              {isSelectingOnMap ? 'Choose Again' : 'Search Again'}
            </button>
          </div>
        </div>
      )}

      {/* ── Mode 3: Map Selecting Active Banner ── */}
      {isSelectingOnMap && !pendingCoordinates && (
        <div className="pt-3 space-y-3">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
            <div className="flex items-center space-x-2">
              <MapIcon className="w-4 h-4 text-blue-600 shrink-0" />
              <div>
                <p className="text-xs font-bold text-blue-900">Click on the map</p>
                <p className="text-[11px] text-blue-700">
                  Click anywhere on the map to place your origin pin.
                </p>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onCancelMapSelection}
            className="w-full inline-flex items-center justify-center px-3 py-2 text-xs font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl transition-colors"
          >
            Cancel Map Selection
          </button>
        </div>
      )}

      {/* ── Mode 4: Search Location Box ── */}
      {isSearching && !pendingCoordinates && !isSelectingOnMap && (
        <div className="pt-3 space-y-3">
          <form onSubmit={handleExecuteSearch} className="space-y-2">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search city, suburb, or landmark..."
                className="w-full pl-9 pr-16 py-2.5 text-xs text-gray-900 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent placeholder-gray-400"
                autoFocus
              />
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-12 top-2.5 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                type="submit"
                disabled={isSearchLoading || !searchQuery.trim()}
                className="absolute right-1.5 top-1.5 px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition-colors"
              >
                {isSearchLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Go'}
              </button>
            </div>

            {/* Quick Suggestions Chips */}
            <div className="flex flex-wrap gap-1 pt-1">
              {['Kochi', 'Aluva', 'Kakkanad', 'Edappally', 'Vyttila'].map((place) => (
                <button
                  key={`chip-${place}`}
                  type="button"
                  onClick={async () => {
                    setSearchQuery(place);
                    setIsSearchLoading(true);
                    setSearchError(null);
                    try {
                      const results = await searchLocation(place);
                      setSearchResults(results);
                    } catch (err: any) {
                      setSearchError(err?.message || 'Search failed');
                    } finally {
                      setIsSearchLoading(false);
                    }
                  }}
                  className="px-2 py-0.5 bg-gray-100 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 border border-gray-200 rounded-full text-[10px] text-gray-600 transition-colors"
                >
                  {place}
                </button>
              ))}
            </div>
          </form>

          {/* Search Error Feedback */}
          {searchError && (
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-2.5 text-rose-800 text-xs flex items-start space-x-2">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
              <span>{searchError}</span>
            </div>
          )}

          {/* Results List */}
          {searchResults.length > 0 && (
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                Select a Location:
              </p>
              {searchResults.map((res) => (
                <button
                  key={res.placeId}
                  type="button"
                  onClick={() => handlePickSearchResult(res)}
                  className="w-full text-left p-2.5 rounded-xl border border-gray-100 hover:border-emerald-200 hover:bg-emerald-50/50 transition-all flex items-start space-x-2.5 group"
                >
                  <MapPin className="w-4 h-4 text-gray-400 group-hover:text-emerald-600 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-gray-900 truncate">{res.name}</p>
                    <p className="text-[11px] text-gray-500 truncate">{res.displayName}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          <button
            type="button"
            onClick={handleCancelSearch}
            className="w-full inline-flex items-center justify-center px-3 py-1.5 text-xs font-semibold text-gray-600 hover:text-gray-900 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* ── Mode 5: Initial Options (No location selected, or changing location) ── */}
      {!locationSelection && !isSearching && !isSelectingOnMap && !pendingCoordinates && (
        <div className="pt-3 space-y-2.5">
          {/* Live GPS Failure Alert */}
          {liveGpsError && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-amber-900 text-xs space-y-1">
              <div className="flex items-center space-x-1.5 font-bold text-amber-900">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                <span>Couldn&apos;t access your live location</span>
              </div>
              <p className="text-[11px] text-amber-800 leading-relaxed">
                {liveGpsError.includes('denied')
                  ? 'Location permission was denied. Try searching for your city or area below.'
                  : 'GPS signal is currently unavailable. Use Search Location or Choose on Map.'}
              </p>
            </div>
          )}

          {/* Prompt description when clean */}
          {!liveGpsError && (
            <p className="text-xs text-gray-500 pb-1">
              Select your starting location using one of the methods below:
            </p>
          )}

          {/* Primary Action A: Use Live Location */}
          <button
            type="button"
            onClick={onUseLiveLocation}
            disabled={isLoadingLiveGps}
            className="w-full inline-flex items-center justify-center px-4 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-75 text-white text-xs font-bold rounded-xl shadow-xs transition-all active:scale-[0.98]"
          >
            {isLoadingLiveGps ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                <span>Detecting location...</span>
              </>
            ) : liveGpsError ? (
              <>
                <RotateCw className="w-4 h-4 mr-2" />
                <span>Try Live GPS Again</span>
              </>
            ) : (
              <>
                <LocateFixed className="w-4 h-4 mr-2" />
                <span>Use Live Location</span>
              </>
            )}
          </button>

          {/* Quick Demo Location Option when GPS fails */}
          {liveGpsError && (
            <button
              type="button"
              onClick={() => handleSelectPreset(QUICK_PRESETS[0])}
              className="w-full inline-flex items-center justify-center px-4 py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-bold rounded-xl transition-all shadow-xs"
            >
              <CheckCircle2 className="w-4 h-4 mr-2 text-emerald-600" />
              <span>Use Kochi (Demo Location)</span>
            </button>
          )}

          {/* Secondary Action B: Search Location */}
          <button
            type="button"
            onClick={handleStartSearch}
            className="w-full inline-flex items-center justify-center px-4 py-2.5 bg-gray-50 hover:bg-gray-100 text-gray-800 text-xs font-bold rounded-xl border border-gray-200 transition-colors"
          >
            <Search className="w-3.5 h-3.5 mr-2 text-gray-500" />
            <span>Search Location</span>
          </button>

          {/* Optional Action C: Choose on Map */}
          <button
            type="button"
            onClick={onStartMapSelection}
            className="w-full inline-flex items-center justify-center px-4 py-2 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-xl transition-colors"
          >
            <MapIcon className="w-3.5 h-3.5 mr-1.5 text-gray-400" />
            <span>Choose on Map</span>
          </button>

          {/* Quick Preset Destinations in Ernakulam */}
          <div className="pt-2 border-t border-gray-100">
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
              Quick Locations in Ernakulam:
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {QUICK_PRESETS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => handleSelectPreset(p)}
                  className="px-2.5 py-1.5 text-[11px] font-semibold text-gray-700 bg-gray-50 hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-200 border border-gray-200 rounded-lg text-left truncate transition-colors"
                >
                  📍 {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
