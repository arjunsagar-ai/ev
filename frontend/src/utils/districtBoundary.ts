/**
 * Ernakulam District Geographic Boundary & Point-in-Polygon Containment.
 *
 * Implements the standard ray-casting algorithm to test whether a given
 * (latitude, longitude) coordinate lies strictly inside Ernakulam District.
 */

export const ERNAKULAM_COVERAGE_MESSAGE =
  'This project currently supports Ernakulam district, Kerala only.';

export function isPointInPolygonRing(
  lon: number,
  lat: number,
  ring: [number, number][],
): boolean {
  const n = ring.length;
  if (n < 3) return false;

  let inside = false;
  let p1x = ring[0][0];
  let p1y = ring[0][1];

  for (let i = 1; i <= n; i++) {
    const p2x = ring[i % n][0];
    const p2y = ring[i % n][1];

    if (lat > Math.min(p1y, p2y)) {
      if (lat <= Math.max(p1y, p2y)) {
        if (lon <= Math.max(p1x, p2x)) {
          let xinters: number;
          if (p1y !== p2y) {
            xinters = ((lat - p1y) * (p2x - p1x)) / (p2y - p1y) + p1x;
          } else {
            xinters = p1x;
          }
          if (p1x === p2x || lon <= xinters) {
            inside = !inside;
          }
        }
      }
    }
    p1x = p2x;
    p1y = p2y;
  }

  return inside;
}

/**
 * Checks if coordinates lie within Ernakulam District using the provided GeoJSON boundary.
 */
export function isPointInErnakulam(
  latitude: number,
  longitude: number,
  boundaryGeoJson: any,
): boolean {
  if (!boundaryGeoJson) {
    // Fallback bounding box pre-filter for Ernakulam District if boundaryGeoJson is not yet loaded
    return latitude >= 9.78 && latitude <= 10.31 && longitude >= 76.16 && longitude <= 76.85;
  }

  const geom = boundaryGeoJson.geometry || boundaryGeoJson;
  const geomType = geom.type;
  const coords = geom.coordinates;

  if (geomType === 'Polygon' && Array.isArray(coords) && coords.length > 0) {
    // Exterior ring
    return isPointInPolygonRing(longitude, latitude, coords[0]);
  }

  if (geomType === 'MultiPolygon' && Array.isArray(coords)) {
    for (const poly of coords) {
      if (Array.isArray(poly) && poly.length > 0) {
        if (isPointInPolygonRing(longitude, latitude, poly[0])) {
          return true;
        }
      }
    }
    return false;
  }

  return false;
}
