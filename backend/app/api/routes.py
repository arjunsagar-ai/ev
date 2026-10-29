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
    GeocodeResultItem,
    GeocodeSearchResponse,
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


ERNAKULAM_LANDMARKS = [
    {"place_id": "lm-kochi", "name": "Kochi", "display_name": "Kochi City Center, Ernakulam District, Kerala", "latitude": 9.9816, "longitude": 76.2999, "type": "city"},
    {"place_id": "lm-ernakulam-south", "name": "Ernakulam South (Junction)", "display_name": "Ernakulam South Railway Station, Jos Junction, Kochi", "latitude": 9.9687, "longitude": 76.2925, "type": "station"},
    {"place_id": "lm-ernakulam-north", "name": "Ernakulam North (Town)", "display_name": "Ernakulam North Railway Station, Kaloor, Kochi", "latitude": 9.9922, "longitude": 76.2848, "type": "station"},
    {"place_id": "lm-marine-drive", "name": "Marine Drive", "display_name": "Marine Drive Promenade & Backwaters, Ernakulam, Kochi", "latitude": 9.9798, "longitude": 76.2757, "type": "landmark"},
    {"place_id": "lm-mg-road", "name": "MG Road", "display_name": "Mahatma Gandhi Road, Ernakulam Central, Kochi", "latitude": 9.9715, "longitude": 76.2829, "type": "road"},
    {"place_id": "lm-aluva", "name": "Aluva", "display_name": "Aluva Town & Metro Terminal, Ernakulam District", "latitude": 10.1076, "longitude": 76.3516, "type": "town"},
    {"place_id": "lm-kakkanad", "name": "Kakkanad (Infopark)", "display_name": "Kakkanad & Infopark IT Corridor, Kochi", "latitude": 10.0159, "longitude": 76.3419, "type": "suburb"},
    {"place_id": "lm-edappally", "name": "Edappally", "display_name": "Edappally Junction & Lulu Mall Area, Kochi", "latitude": 10.0261, "longitude": 76.3086, "type": "junction"},
    {"place_id": "lm-palarivattom", "name": "Palarivattom", "display_name": "Palarivattom Junction & Bypass, Kochi", "latitude": 10.0055, "longitude": 76.3075, "type": "suburb"},
    {"place_id": "lm-vyttila", "name": "Vyttila Mobility Hub", "display_name": "Vyttila Mobility Hub & Multi-Modal Terminal, Kochi", "latitude": 9.9684, "longitude": 76.3197, "type": "transit"},
    {"place_id": "lm-kalamassery", "name": "Kalamassery", "display_name": "Kalamassery Industrial & CUSAT University, Kochi", "latitude": 10.0537, "longitude": 76.3219, "type": "town"},
    {"place_id": "lm-tripunithura", "name": "Tripunithura", "display_name": "Tripunithura Royal Heritage Town, Ernakulam", "latitude": 9.9472, "longitude": 76.3458, "type": "town"},
    {"place_id": "lm-angamaly", "name": "Angamaly", "display_name": "Angamaly Gateway Town, Ernakulam District", "latitude": 10.1960, "longitude": 76.3860, "type": "town"},
    {"place_id": "lm-perumbavoor", "name": "Perumbavoor", "display_name": "Perumbavoor Town, Ernakulam District", "latitude": 10.1118, "longitude": 76.4756, "type": "town"},
    {"place_id": "lm-muvattupuzha", "name": "Muvattupuzha", "display_name": "Muvattupuzha Municipal Town, Ernakulam District", "latitude": 9.9894, "longitude": 76.5790, "type": "town"},
    {"place_id": "lm-kothamangalam", "name": "Kothamangalam", "display_name": "Kothamangalam Gateway, Ernakulam District", "latitude": 10.0614, "longitude": 76.6239, "type": "town"},
    {"place_id": "lm-paravur", "name": "North Paravur", "display_name": "North Paravur Heritage Town, Ernakulam District", "latitude": 10.1472, "longitude": 76.2292, "type": "town"},
    {"place_id": "lm-piravom", "name": "Piravom", "display_name": "Piravom Town, Ernakulam District", "latitude": 9.8732, "longitude": 76.4925, "type": "town"},
    {"place_id": "lm-kaloor", "name": "Kaloor", "display_name": "Kaloor Stadium Hub, Kochi", "latitude": 9.9984, "longitude": 76.2999, "type": "suburb"},
    {"place_id": "lm-panampilly", "name": "Panampilly Nagar", "display_name": "Panampilly Nagar, Kochi", "latitude": 9.9610, "longitude": 76.2952, "type": "suburb"},
    {"place_id": "lm-thrikkakara", "name": "Thrikkakara", "display_name": "Thrikkakara Municipal Area, Kochi", "latitude": 10.0382, "longitude": 76.3312, "type": "suburb"},
    {"place_id": "lm-cial", "name": "Cochin International Airport (CIAL)", "display_name": "CIAL Airport, Nedumbassery, Ernakulam District", "latitude": 10.1518, "longitude": 76.3930, "type": "airport"},
]


@router.get(
    "/gis/search",
    response_model=GeocodeSearchResponse,
    summary="Search locations within Ernakulam District",
    description="Geocodes addresses or localities in Ernakulam with local landmark database and online fallback.",
)
def search_gis_locations(q: str = "") -> GeocodeSearchResponse:
    """Search for places, suburbs, and landmarks inside Ernakulam District."""
    from app.gis.ernakulam_boundary import is_point_in_ernakulam
    import urllib.request
    import json

    query = q.strip().lower()
    results: list[GeocodeResultItem] = []
    seen_keys: set[str] = set()

    def add_item(place_id: str, name: str, display_name: str, lat: float, lon: float, item_type: str = "locality"):
        key = f"{round(lat, 4)},{round(lon, 4)}"
        if key not in seen_keys:
            seen_keys.add(key)
            results.append(GeocodeResultItem(
                place_id=place_id,
                name=name,
                display_name=display_name,
                latitude=lat,
                longitude=lon,
                type=item_type,
            ))

    # 1. Match local landmarks
    for lm in ERNAKULAM_LANDMARKS:
        if not query or query in lm["name"].lower() or query in lm["display_name"].lower():
            add_item(lm["place_id"], lm["name"], lm["display_name"], lm["latitude"], lm["longitude"], lm["type"])

    # 2. Match verified real charging stations from dataset
    try:
        real_stations = load_ernakulam_ev_stations()
        for st in real_stations:
            if query and (query in st.name.lower() or query in st.address.lower() or query in st.city.lower()):
                add_item(
                    f"stn-{st.station_id}",
                    st.name,
                    f"{st.name}, {st.address or st.city}",
                    st.latitude,
                    st.longitude,
                    "ev_station",
                )
    except Exception as exc:
        logger.debug("Failed searching real stations: %s", exc)

    # 3. If online search requested and local matches are few, query Nominatim with proper User-Agent
    if query and len(results) < 5:
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=5&addressdetails=1&countrycodes=in&viewbox=76.16,10.31,76.85,9.78&bounded=0"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "EV-Charging-Optimizer/1.0 (ev-navigation-project; contact: arjunajusagar@gmail.com)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    for item in data:
                        try:
                            lat = float(item["lat"])
                            lon = float(item["lon"])
                            # Verify inside Ernakulam District
                            if is_point_in_ernakulam(lat, lon):
                                parts = (item.get("display_name") or "").split(",")
                                name = item.get("name") or parts[0].strip() or "Selected Place"
                                add_item(
                                    str(item.get("place_id", f"{lat},{lon}")),
                                    name,
                                    item.get("display_name", name),
                                    lat,
                                    lon,
                                    item.get("type", "location"),
                                )
                        except (ValueError, KeyError):
                            continue
        except Exception as exc:
            logger.debug("Nominatim online search skipped/timed out: %s", exc)

    return GeocodeSearchResponse(
        query=q,
        total_found=len(results),
        results=results[:10],
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
