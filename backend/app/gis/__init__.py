"""GIS subsystem for OpenStreetMap ingestion, spatial indexing, and candidate generation."""
from app.gis.models import CandidateLocation, RoadNetworkMetadata
from app.gis.osm_loader import (
    build_sample_road_network,
    get_road_network,
    load_osm_network,
)
from app.gis.spatial_index import (
    find_nearest_road_node,
    snap_coordinates_to_road,
    validate_coordinates,
)
from app.gis.candidate_generator import (
    compute_feasibility_score,
    filter_feasible_candidates,
    generate_candidates_from_graph,
    generate_candidates_from_points,
)

__all__ = [
    "CandidateLocation",
    "RoadNetworkMetadata",
    "build_sample_road_network",
    "get_road_network",
    "load_osm_network",
    "find_nearest_road_node",
    "snap_coordinates_to_road",
    "validate_coordinates",
    "compute_feasibility_score",
    "filter_feasible_candidates",
    "generate_candidates_from_graph",
    "generate_candidates_from_points",
]
