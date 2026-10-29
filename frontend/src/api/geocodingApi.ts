import { GeocodeResult } from '../types/routing';

const NOMINATIM_BASE_URL =
  import.meta.env.VITE_NOMINATIM_URL || 'https://nominatim.openstreetmap.org/search';

/**
 * Searches for places/addresses using OpenStreetMap Nominatim geocoding.
 * 
 * Free public geocoding service; respects usage policy with:
 * - Limited results (5)
 * - Structured address details
 * - 8-second request timeout via AbortController
 * - Clean user-facing error messages
 */
export async function searchLocation(query: string): Promise<GeocodeResult[]> {
  const trimmed = query.trim();
  if (!trimmed) {
    throw new Error('Please enter a location to search.');
  }

  // Prioritize Ernakulam District and Kerala viewbox without hard-bounding (bounded=0)
  const url = `${NOMINATIM_BASE_URL}?q=${encodeURIComponent(
    trimmed
  )}&format=json&limit=5&addressdetails=1&countrycodes=in&viewbox=76.16,10.31,76.85,9.78&bounded=0`;

  let response: Response;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000);

  try {
    response = await fetch(url, {
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
      },
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Location search request timed out. Please try again.');
    }
    throw new Error(
      'Location search is temporarily unavailable. Please check your network connection.'
    );
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw new Error('Location search service is temporarily unavailable.');
  }

  let data: any[];
  try {
    data = await response.json();
  } catch {
    throw new Error('Invalid response received from location search.');
  }

  if (!Array.isArray(data) || data.length === 0) {
    return [];
  }

  return data.map((item) => {
    const lat = parseFloat(item.lat);
    const lon = parseFloat(item.lon);
    const parts = (item.display_name || '').split(',');
    const mainName = item.name || parts[0]?.trim() || 'Selected Place';
    const context = parts.slice(1, 4).join(',').trim();

    return {
      placeId: item.place_id || `${lat},${lon}`,
      name: mainName,
      displayName: context ? `${mainName}, ${context}` : item.display_name || mainName,
      latitude: lat,
      longitude: lon,
      type: item.type,
    };
  });
}
