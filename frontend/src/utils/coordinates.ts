/**
 * Utility functions for coordinate formatting and distance presentation.
 */

export function formatDistance(distanceKm: number): string {
  if (distanceKm < 1.0) {
    const meters = Math.round(distanceKm * 1000);
    return `${meters} m`;
  }
  return `${distanceKm.toFixed(2)} km`;
}

export function formatEta(minutes?: number | null): string {
  if (minutes === undefined || minutes === null) {
    return 'N/A';
  }
  if (minutes < 1.0) {
    return '< 1 min';
  }
  return `${minutes.toFixed(1)} min`;
}

export function formatCoordinates(lat: number, lon: number): string {
  const latDir = lat >= 0 ? 'N' : 'S';
  const lonDir = lon >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
}
