"""API routes for network information and live GPS routing."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.api.schemas import (
    AssignmentRequest,
    AssignmentResponse,
    CapacityRequest,
    CapacityResponse,
    DominatingSetRequest,
    DominatingSetResponse,
    ExistingStationInfo,
    ExistingStationsResponse,
    HealthResponse,
    LiveRouteRequest,
    LiveRouteResponse,
    NearbyStationsRequest,
    NearbyStationsResponse,
    NetworkInfoResponse,
    InfrastructureRequest,
    InfrastructureResponse,
)
from app.gis.ernakulam_boundary import get_ernakulam_boundary_geojson
from app.gis.ev_station_loader import load_ernakulam_ev_stations
from app.services.routing_service import RoutingService, get_routing_service
from app.services.station_optimization_service import (
    StationOptimizationService,
    get_station_optimization_service,
)
from app.services.assignment_service import (
    AssignmentService,
    get_assignment_service,
)
from app.services.infrastructure_service import (
    InfrastructureService,
    get_infrastructure_service,
)
from app.services.capacity_service import (
    CapacityService,
    get_capacity_service,
)

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
    description="Returns node count, edge count, data source, and project area of currently loaded road network.",
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
            project_area=summary.get("project_area", "Ernakulam District"),
        )
    except Exception as exc:
        logger.error("Failed to retrieve network summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Road network is currently unavailable.",
        )


@router.get(
    "/gis/boundary",
    summary="Get Ernakulam District boundary GeoJSON",
    description="Returns the official administrative boundary polygon for Ernakulam District, Kerala.",
)
def get_district_boundary() -> dict:
    """Retrieve Ernakulam District geographic boundary GeoJSON."""
    try:
        return get_ernakulam_boundary_geojson()
    except Exception as exc:
        logger.error("Failed to retrieve district boundary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="District boundary data is currently unavailable.",
        )


@router.get(
    "/stations/existing",
    response_model=ExistingStationsResponse,
    summary="Get existing EV charging stations in Ernakulam District",
    description="Returns all verified real-world charging stations loaded from the provided dataset within Ernakulam District.",
)
def get_existing_stations() -> ExistingStationsResponse:
    """Retrieve list of existing EV charging stations in Ernakulam District."""
    try:
        stations = load_ernakulam_ev_stations()
        station_items = [
            ExistingStationInfo(
                station_id=s.station_id,
                name=s.name,
                state=s.state,
                city=s.city,
                address=s.address,
                latitude=s.latitude,
                longitude=s.longitude,
                station_type=s.station_type,
                is_existing=True,
            )
            for s in stations
        ]
        return ExistingStationsResponse(
            total_stations=len(station_items),
            project_area="Ernakulam District, Kerala",
            stations=station_items,
        )
    except Exception as exc:
        logger.error("Failed to load existing stations: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Existing station dataset is currently unavailable.",
        )


@router.post(
    "/stations/nearby",
    response_model=NearbyStationsResponse,
    summary="Find nearby existing EV charging stations",
    description="Finds real charging stations within the configured search radius from user coordinates.",
    responses={
        400: {"description": "Location outside Ernakulam District or invalid coordinates."},
    },
)
def post_nearby_stations(
    request: NearbyStationsRequest,
    service: RoutingService = Depends(get_routing_service),
) -> NearbyStationsResponse:
    """Query reachable real EV stations near the user location."""
    try:
        res = service.find_nearby_existing_stations(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km,
        )
        return NearbyStationsResponse(**res)
    except (ValueError, TypeError) as exc:
        logger.warning("Nearby station validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error in nearby stations query: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query nearby stations.",
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


@router.post(
    "/optimize/dominating-set",
    response_model=DominatingSetResponse,
    summary="Compute greedy Minimum Dominating Set station placement",
    description=(
        "Executes a greedy set-cover approximation of the Minimum Dominating Set (MDS) "
        "to select a subset of feasible EV charging station candidates providing maximal "
        "coverage across road network demand nodes within the specified radius."
    ),
    responses={
        400: {"description": "Invalid optimization parameters."},
        503: {"description": "Road network or candidate generator unavailable."},
    },
)
def post_dominating_set_optimization(
    request: DominatingSetRequest = DominatingSetRequest(),
    service: StationOptimizationService = Depends(get_station_optimization_service),
) -> DominatingSetResponse:
    """Execute greedy MDS charging station placement optimization."""
    try:
        result = service.optimize_station_placement(
            coverage_radius_km=request.coverage_radius_km,
            min_feasibility_score=request.min_feasibility_score,
            max_stations=request.max_stations,
        )
        return DominatingSetResponse(**result)
    except (ValueError, TypeError) as exc:
        logger.warning("MDS optimization validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error during MDS optimization: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while calculating the dominating set.",
        )


@router.post(
    "/optimize/assignment",
    response_model=AssignmentResponse,
    summary="Assign EVs to charging stations using Hungarian algorithm",
    description=(
        "Executes Kuhn-Munkres (Hungarian) minimum weight bipartite matching to "
        "optimally assign electric vehicles to charging stations based on road network "
        "travel distance or geographic distance cost matrix."
    ),
    responses={
        400: {"description": "Invalid assignment input or coordinates."},
        500: {"description": "Internal error during Hungarian matching."},
    },
)
def post_hungarian_assignment(
    request: AssignmentRequest,
    service: AssignmentService = Depends(get_assignment_service),
) -> AssignmentResponse:
    """Execute Hungarian optimal bipartite matching for EV-to-station assignment."""
    try:
        evs_data = [ev.model_dump() for ev in request.evs]
        result = service.assign_evs_to_stations(
            evs=evs_data,
            station_ids=request.station_ids,
            coverage_radius_km=request.coverage_radius_km,
            min_feasibility_score=request.min_feasibility_score,
            max_stations=request.max_stations,
            cost_metric=request.cost_metric or "network_distance_km",
        )
        return AssignmentResponse(**result)
    except (ValueError, TypeError) as exc:
        logger.warning("Hungarian assignment validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error during Hungarian assignment: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while calculating EV-to-station assignments.",
        )


@router.post(
    "/optimize/infrastructure",
    response_model=InfrastructureResponse,
    summary="Compute minimum spanning infrastructure connection network using Prim's MST",
    description=(
        "Executes Prim's algorithm on selected EV charging stations to determine "
        "the minimum spanning infrastructure connection network based on road network "
        "shortest-path distance or geographic distance."
    ),
    responses={
        400: {"description": "Invalid station IDs or optimization parameters."},
        500: {"description": "Internal error during infrastructure optimization."},
    },
)
def post_infrastructure_optimization(
    request: InfrastructureRequest = InfrastructureRequest(),
    service: InfrastructureService = Depends(get_infrastructure_service),
) -> InfrastructureResponse:
    """Execute Prim's MST to connect selected EV charging stations with minimum infrastructure distance."""
    try:
        result = service.optimize_infrastructure(
            station_ids=request.station_ids,
            coverage_radius_km=request.coverage_radius_km,
            min_feasibility_score=request.min_feasibility_score,
            max_stations=request.max_stations,
            cost_metric=request.cost_metric or "network_distance_km",
        )
        return InfrastructureResponse(**result)
    except (ValueError, TypeError) as exc:
        logger.warning("Infrastructure optimization validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error during infrastructure optimization: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while calculating infrastructure optimization.",
        )


@router.post(
    "/optimize/capacity",
    response_model=CapacityResponse,
    summary="Analyze EV charging capacity and bottlenecks (Ford-Fulkerson)",
    description=(
        "Builds a directed flow network (SOURCE->EVs->Stations->SINK) and computes maximum flow "
        "using the Ford-Fulkerson Edmonds-Karp algorithm. Returns per-station simulated "
        "utilization, bottleneck station IDs, and network status. "
        "All capacity values are simulated/estimated for planning purposes — "
        "not real electrical grid capacity, actual substation limits, or utility data."
    ),
)
def analyze_capacity(
    request: CapacityRequest,
    service: CapacityService = Depends(get_capacity_service),
) -> CapacityResponse:
    """Run Ford-Fulkerson max-flow to analyse simulated EV charging capacity and bottlenecks."""
    try:
        evs = [ev.model_dump() for ev in request.evs]
        stations = [st.model_dump() for st in request.stations]
        assignments = (
            [a.model_dump() for a in request.assignments]
            if request.assignments is not None
            else None
        )
        result = service.analyze_capacity(
            evs=evs,
            stations=stations,
            assignments=assignments,
        )
        return CapacityResponse(**result)
    except (ValueError, TypeError) as exc:
        logger.warning("Capacity analysis validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error during capacity analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while performing capacity analysis.",
        )
