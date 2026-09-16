import { useState, useCallback } from 'react';
import { UserCoordinates } from '../types/routing';

interface UseGeolocationReturn {
  coordinates: UserCoordinates | null;
  loading: boolean;
  error: string | null;
  getLocation: () => Promise<UserCoordinates>;
  clearError: () => void;
}

export function useGeolocation(): UseGeolocationReturn {
  const [coordinates, setCoordinates] = useState<UserCoordinates | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const getLocation = useCallback((): Promise<UserCoordinates> => {
    return new Promise((resolve, reject) => {
      if (!('geolocation' in navigator)) {
        const msg = 'Geolocation is not supported by your browser.';
        setError(msg);
        setLoading(false);
        reject(new Error(msg));
        return;
      }

      setLoading(true);
      setError(null);

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords: UserCoordinates = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          };
          setCoordinates(coords);
          setLoading(false);
          setError(null);
          resolve(coords);
        },
        (geoError) => {
          setLoading(false);
          let userMessage: string;

          switch (geoError.code) {
            case geoError.PERMISSION_DENIED:
              userMessage =
                'Location permission was denied. Please enable location access in your browser and try again.';
              break;
            case geoError.POSITION_UNAVAILABLE:
              userMessage =
                'GPS location is currently unavailable. Please check your device location services.';
              break;
            case geoError.TIMEOUT:
              userMessage =
                'Location request timed out. Please check your GPS signal and try again.';
              break;
            default:
              userMessage =
                'Unable to retrieve your location. Please try again.';
              break;
          }

          setError(userMessage);
          reject(new Error(userMessage));
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 0,
        }
      );
    });
  }, []);

  return {
    coordinates,
    loading,
    error,
    getLocation,
    clearError,
  };
}
