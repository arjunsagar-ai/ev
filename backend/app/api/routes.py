"""API routes for network information and live GPS routing."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.api.schemas import (
    HealthResponse,
    LiveRouteRequest,
    LiveRouteResponse,
    NetworkInfoResponse,
)
from app.services.routing_service import RoutingService, get_routing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["EV Routing & Optimization"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns service availability and active version.",
)
def get_health() -> HealthResponse:
    """Check API operational health status."""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
    )


@router.get(
    "/gis/network",
    response_model=NetworkInfoResponse,
    summary="Get loaded road network metadata",
    description="Returns node count, edge count, and data source of currently loaded road network.",
)
def get_network_info(
    service: RoutingService = Depends(get_routing_service),
) -> NetworkInfoResponse:
    """Retrieve road network summary information."""
    try:
        summary = service.get_network_summary()
        return NetworkInfoResponse(
            node_count=summary["node_count"],
            edge_count=summary["edge_count"],
            data_source=summary["data_source"],
        )
    except Exception as exc:
        logger.error("Failed to retrieve network summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Road network is currently unavailable.",
        )


@router.post(
    "/route/live",
    response_model=LiveRouteResponse,
    summary="Calculate live GPS route to optimal EV charging station",
    description=(
        "Accepts live user GPS latitude and longitude, snaps the coordinates to the "
        "nearest road network vertex, selects the closest feasible charging station, "
        "and computes the shortest path route via Dijkstra's algorithm."
    ),
    responses={
        400: {"description": "Invalid GPS coordinates or snapping distance exceeded."},
        404: {"description": "No feasible charging station found or reachable."},
        503: {"description": "Road network is not initialized."},
    },
)
def post_live_route(
    request: LiveRouteRequest,
    service: RoutingService = Depends(get_routing_service),
) -> LiveRouteResponse:
    """Calculate shortest path route from live GPS position to nearest charging station."""
    try:
        route_result = service.calculate_live_route(
            latitude=request.latitude,
            longitude=request.longitude,
            max_station_distance_km=request.max_station_distance_km,
        )
        return LiveRouteResponse(**route_result)
    except (ValueError, TypeError) as exc:
        logger.warning("Live route validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except LookupError as exc:
        logger.warning("Live route station lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except RuntimeError as exc:
        logger.error("Live route runtime failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Road network is not initialized or unavailable.",
        )
    except Exception as exc:
        logger.error("Unexpected error during live route calculation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while calculating the route.",
        )
