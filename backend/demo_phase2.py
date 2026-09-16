"""
Phase 2 Demonstration — GIS / OSM Ingestion + Spatial Snapping.

Demonstrates:
  1. Load sample / cached OSM road network
  2. Display graph statistics
  3. Generate candidate EV charging-station locations
  4. Filter candidates by feasibility
  5. Test a sample GPS coordinate → nearest road node
  6. Display candidate statistics

NOTE: This demo does NOT run Dijkstra or any Phase 1 routing algorithms.
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stdout,
)

from app.gis.osm_loader import build_sample_road_network, load_osm_network
from app.gis.spatial_index import find_nearest_road_node, snap_coordinates_to_road
from app.gis.candidate_generator import (
    generate_candidates_from_graph,
    generate_candidates_from_points,
    filter_feasible_candidates,
)


def main() -> None:
    print("=" * 62)
    print("  PHASE 2: GIS / OSM INGESTION & SPATIAL SNAPPING DEMO")
    print("=" * 62)

    # ── 1. Load road network ────────────────────────────────────────
    print("\n[1] LOADING ROAD NETWORK")
    graph, meta = load_osm_network(
        north=10.007, south=9.999, east=76.321, west=76.299,
    )
    print(f"    Data source  : {meta.data_source}")
    print(f"    Road nodes   : {meta.num_nodes}")
    print(f"    Road edges   : {meta.num_edges}")
    print(f"    Load time    : {meta.load_time_seconds:.4f} s")
    if meta.bbox:
        bb = meta.bbox
        print(f"    Bounding box : [{bb['south']:.4f}, {bb['west']:.4f}] "
              f"→ [{bb['north']:.4f}, {bb['east']:.4f}]")

    # ── 2. Graph topology summary ───────────────────────────────────
    print("\n[2] GRAPH TOPOLOGY")
    degrees = {}
    for nid in graph.nodes():
        d = len(graph.get_neighbors(nid))
        degrees[d] = degrees.get(d, 0) + 1
    for deg in sorted(degrees):
        print(f"    Degree {deg}: {degrees[deg]} node(s)")

    # ── 3. Generate candidate locations ─────────────────────────────
    print("\n[3] CANDIDATE GENERATION")
    cands_intersections = generate_candidates_from_graph(
        graph, data_source=meta.data_source, node_selection="intersections",
    )
    cands_all = generate_candidates_from_graph(
        graph, data_source=meta.data_source, node_selection="all",
    )
    print(f"    Intersection candidates (degree ≥ 3) : {len(cands_intersections)}")
    print(f"    All-node candidates                  : {len(cands_all)}")

    # Also try a couple of external points
    external_pts = [
        {"latitude": 10.002, "longitude": 76.308, "candidate_id": "EXT-Park-01"},
        {"latitude": 10.005, "longitude": 76.318, "candidate_id": "EXT-Mall-01"},
        {"latitude": 10.050, "longitude": 76.350, "candidate_id": "EXT-Far-01"},
    ]
    ext_cands = generate_candidates_from_points(
        external_pts, graph, data_source=meta.data_source,
    )
    print(f"    External-point candidates             : {len(ext_cands)}")

    # ── 4. Feasibility filtering ────────────────────────────────────
    print("\n[4] FEASIBILITY FILTERING")
    all_candidates = cands_intersections + ext_cands
    result = filter_feasible_candidates(all_candidates)
    feasible = result["feasible"]
    rejected = result["rejected"]

    print(f"    Total candidates evaluated: {len(all_candidates)}")
    print(f"    Feasible  : {len(feasible)}")
    print(f"    Rejected  : {len(rejected)}")

    if feasible:
        print("\n    ── Top feasible candidates ──")
        for c in sorted(feasible, key=lambda x: x.feasibility_score, reverse=True)[:5]:
            print(
                f"      {c.candidate_id}  "
                f"score={c.feasibility_score:.3f}  "
                f"access={c.accessibility_score:.2f}  "
                f"land={c.land_available:.2f}  "
                f"grid={c.grid_capacity:.2f} ({c.grid_capacity_source})  "
                f"cost={c.installation_cost:.2f}"
            )

    if rejected:
        print("\n    ── Rejected candidates ──")
        for c in rejected[:5]:
            print(f"      {c.candidate_id}  reason: {c.rejection_reason}")

    # ── 5. GPS → nearest road node ──────────────────────────────────
    print("\n[5] GPS COORDINATE SNAPPING")
    test_points = [
        (10.001, 76.302, "Near node N02"),
        (10.004, 76.311, "Between rows 2 & 3"),
        (10.000, 76.320, "At N05 corner"),
    ]
    for lat, lon, label in test_points:
        snap = snap_coordinates_to_road(graph, lat, lon)
        nn = snap["nearest_node"]
        print(
            f"    GPS ({lat:.3f}, {lon:.3f}) [{label}]\n"
            f"      → Node {nn['id']}  ({nn['latitude']:.4f}, {nn['longitude']:.4f})  "
            f"dist={snap['distance_to_road_m']:.1f} m"
        )

    # ── 6. Summary statistics ───────────────────────────────────────
    print("\n[6] SUMMARY")
    print(f"    Data source                 : {meta.data_source}")
    print(f"    Road network nodes          : {meta.num_nodes}")
    print(f"    Road network edges          : {meta.num_edges}")
    print(f"    Intersection candidates     : {len(cands_intersections)}")
    print(f"    External candidates tested  : {len(ext_cands)}")
    print(f"    Total feasible locations    : {len(feasible)}")
    print(f"    Total rejected locations    : {len(rejected)}")

    print("\n" + "=" * 62)
    print("  PHASE 2 DEMO COMPLETE")
    print("=" * 62)


if __name__ == "__main__":
    main()
