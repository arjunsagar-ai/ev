import { GeocodeResult } from '../types/routing';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Fallback landmarks in Ernakulam in case of complete backend disconnection
const FALLBACK_ERNAKULAM_PLACES: GeocodeResult[] = [
  { placeId: 'fallback-kochi', name: 'Kochi City Center', displayName: 'Kochi City Center, Ernakulam District', latitude: 9.9816, longitude: 76.2999, type: 'city' },
  { placeId: 'fallback-aluva', name: 'Aluva', displayName: 'Aluva Town & Metro Terminal, Ernakulam', latitude: 10.1076, longitude: 76.3516, type: 'town' },
  { placeId: 'fallback-kakkanad', name: 'Kakkanad (Infopark)', displayName: 'Kakkanad & Infopark IT Corridor, Kochi', latitude: 10.0159, longitude: 76.3419, type: 'suburb' },
  { placeId: 'fallback-edappally', name: 'Edappally', displayName: 'Edappally Junction & Lulu Mall Area, Kochi', latitude: 10.0261, longitude: 76.3086, type: 'junction' },
  { placeId: 'fallback-vyttila', name: 'Vyttila Mobility Hub', displayName: 'Vyttila Mobility Hub & Central Transit, Kochi', latitude: 9.9684, longitude: 76.3197, type: 'transit' },
  { placeId: 'fallback-palarivattom', name: 'Palarivattom', displayName: 'Palarivattom Bypass Junction, Kochi', latitude: 10.0055, longitude: 76.3075, type: 'suburb' },
  { placeId: 'fallback-kalamassery', name: 'Kalamassery', displayName: 'Kalamassery Industrial & CUSAT Area, Kochi', latitude: 10.0537, longitude: 76.3219, type: 'town' },
  { placeId: 'fallback-tripunithura', name: 'Tripunithura', displayName: 'Tripunithura Royal Heritage City, Ernakulam', latitude: 9.9472, longitude: 76.3458, type: 'town' },
  { placeId: 'fallback-angamaly', name: 'Angamaly', displayName: 'Angamaly Town, Ernakulam District', latitude: 10.1960, longitude: 76.3860, type: 'town' },
];

/**
 * Searches for places/addresses in Ernakulam District via backend search API.
 * Never blocked by CORS or Nominatim 403.
 */
export async function searchLocation(query: string): Promise<GeocodeResult[]> {
  const trimmed = query.trim();
  if (!trimmed) {
    throw new Error('Please enter a location to search.');
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/gis/search?q=${encodeURIComponent(trimmed)}`,
      {
        headers: { Accept: 'application/json' },
      }
    );

    if (response.ok) {
      const data = await response.json();
      if (Array.isArray(data?.results) && data.results.length > 0) {
        return data.results.map((item: any) => ({
          placeId: String(item.place_id || `${item.latitude},${item.longitude}`),
          name: item.name,
          displayName: item.display_name || item.name,
          latitude: Number(item.latitude),
          longitude: Number(item.longitude),
          type: item.type || 'locality',
        }));
      }
    }
  } catch {
    // If backend network error, proceed to fallback filter below
  }

  // Fallback matching against prominent Ernakulam places
  const lower = trimmed.toLowerCase();
  const matched = FALLBACK_ERNAKULAM_PLACES.filter(
    (p) => p.name.toLowerCase().includes(lower) || p.displayName.toLowerCase().includes(lower)
  );

  if (matched.length > 0) {
    return matched;
  }

  return [];
}
