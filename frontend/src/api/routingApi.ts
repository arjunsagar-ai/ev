import {
  AssignmentRequest,
  AssignmentResponse,
  DominatingSetRequest,
  DominatingSetResponse,
  HealthResponse,
  LiveRouteRequest,
  LiveRouteResponse,
  NetworkInfoResponse,
} from '../types/routing';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function fetchLiveRoute(
  request: LiveRouteRequest
): Promise<LiveRouteResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/route/live`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error('Unable to connect to the routing server. Please check your network connection.');
  }

  if (!response.ok) {
    let errorDetail = 'Routing service encountered an error.';
    try {
      const errorJson = await response.json();
      if (errorJson?.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Fall back to status text
      errorDetail = `Server responded with status ${response.status}: ${response.statusText}`;
    }

    if (response.status === 404) {
      throw new Error(errorDetail || 'No feasible charging station could be found.');
    }
    if (response.status === 400) {
      throw new Error(errorDetail || 'Unable to find a nearby road from your coordinates.');
    }
    if (response.status >= 500) {
      throw new Error('Routing service is currently unavailable. Please try again shortly.');
    }

    throw new Error(errorDetail);
  }

  return response.json();
}

export async function fetchDominatingSetOptimization(
  request: DominatingSetRequest = {}
): Promise<DominatingSetResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/optimize/dominating-set`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error('Unable to connect to the optimization server. Please check your network connection.');
  }

  if (!response.ok) {
    let errorDetail = 'Station optimization service encountered an error.';
    try {
      const errorJson = await response.json();
      if (errorJson?.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = `Server responded with status ${response.status}: ${response.statusText}`;
    }

    if (response.status >= 500) {
      throw new Error('Station optimization service is currently unavailable.');
    }

    throw new Error(errorDetail);
  }

  return response.json();
}

export async function fetchHungarianAssignment(
  request: AssignmentRequest
): Promise<AssignmentResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/optimize/assignment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error('Unable to connect to the assignment optimization server. Please check your network connection.');
  }

  if (!response.ok) {
    let errorDetail = 'Hungarian assignment service encountered an error.';
    try {
      const errorJson = await response.json();
      if (errorJson?.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = `Server responded with status ${response.status}: ${response.statusText}`;
    }

    if (response.status >= 500) {
      throw new Error('Assignment optimization service is currently unavailable.');
    }

    throw new Error(errorDetail);
  }

  return response.json();
}

export async function fetchNetworkInfo(): Promise<NetworkInfoResponse> {
  const response = await fetch(`${API_BASE_URL}/api/gis/network`);
  if (!response.ok) {
    throw new Error('Failed to retrieve road network metadata.');
  }
  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error('Health check failed.');
  }
  return response.json();
}

