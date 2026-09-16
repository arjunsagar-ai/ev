"""Minimum Dominating Set (MDS) Greedy Approximation for EV Station Placement."""
import heapq
from typing import Any, Dict, List, Optional, Set

from app.graph.weighted_graph import WeightedGraph


def _get_nodes_within_radius(
    graph: WeightedGraph,
    source: Any,
    radius: float
) -> Set[Any]:
    """
    Find all nodes in the graph reachable from source within a given graph distance radius
    using Dijkstra exploration bounded by radius.
    """
    covered: Set[Any] = {source}
    if radius <= 0:
        return covered

    # Min-heap of (dist, node)
    pq: List[tuple[float, Any]] = [(0.0, source)]
    distances: Dict[Any, float] = {source: 0.0}

    while pq:
        curr_dist, u = heapq.heappop(pq)
        if curr_dist > distances[u]:
            continue

        for neighbor, weight in graph.get_neighbors(u).items():
            new_dist = curr_dist + weight
            if new_dist <= radius:
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    covered.add(neighbor)
                    heapq.heappush(pq, (new_dist, neighbor))

    return covered


def minimum_dominating_set(
    graph: WeightedGraph,
    coverage_radius: float,
    candidate_nodes: Optional[List[Any]] = None,
    demand_nodes: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Compute a greedy approximation of the Minimum Dominating Set (MDS) on a weighted graph.

    DISCLAIMER:
        The Minimum Dominating Set problem is NP-hard. This function implements a
        greedy set-cover approximation algorithm. It does NOT guarantee the mathematically
        exact minimal set for arbitrary graphs, but provides a robust, polynomial-time
        placement strategy with an O(ln |V|) approximation ratio for EV charging infrastructure.

    Parameters:
        graph (WeightedGraph): The weighted road/network graph.
        coverage_radius (float): Maximum graph distance (in graph weight units, e.g. km)
                                 within which a charging station can serve adjacent demand nodes.
        candidate_nodes (List[Any], optional): Subset of nodes eligible to host charging stations.
                                               Defaults to all nodes in the graph.
        demand_nodes (List[Any], optional): Subset of nodes requiring EV charging coverage.
                                            Defaults to all nodes in the graph.

    Returns:
        Dict[str, Any]: Structured result containing:
            - 'selected_nodes': List of candidate nodes chosen as charging station locations.
            - 'covered_nodes': List of demand nodes covered by at least one selected station.
            - 'uncovered_nodes': List of demand nodes that could not be covered.
            - 'coverage_percentage': Percentage of demand nodes successfully covered (0.0 - 100.0).
            - 'coverage_map': Dict mapping each selected station -> list of covered demand nodes.
    """
    all_nodes = graph.nodes()
    candidates = list(candidate_nodes) if candidate_nodes is not None else list(all_nodes)
    demands = list(demand_nodes) if demand_nodes is not None else list(all_nodes)

    if not demands:
        return {
            "selected_nodes": [],
            "covered_nodes": [],
            "uncovered_nodes": [],
            "coverage_percentage": 100.0,
            "coverage_map": {},
        }

    uncovered_demand: Set[Any] = set(demands)
    candidate_coverage: Dict[Any, Set[Any]] = {}

    # Precompute coverage for each candidate node bounded by coverage_radius
    for cand in candidates:
        if graph.has_node(cand):
            reachable = _get_nodes_within_radius(graph, cand, coverage_radius)
            candidate_coverage[cand] = reachable & uncovered_demand
        else:
            candidate_coverage[cand] = set()

    selected_nodes: List[Any] = []
    coverage_map: Dict[Any, List[Any]] = {}
    available_candidates: Set[Any] = set(candidates)

    # Iteratively pick candidate that covers the maximum number of remaining uncovered demand nodes
    while uncovered_demand and available_candidates:
        best_candidate: Optional[Any] = None
        best_coverage: Set[Any] = set()

        for cand in available_candidates:
            useful_coverage = candidate_coverage[cand] & uncovered_demand
            if len(useful_coverage) > len(best_coverage):
                best_coverage = useful_coverage
                best_candidate = cand

        # If no candidate can cover any remaining uncovered demand, terminate
        if best_candidate is None or len(best_coverage) == 0:
            break

        selected_nodes.append(best_candidate)
        coverage_map[best_candidate] = sorted(list(best_coverage))
        uncovered_demand -= best_coverage
        available_candidates.remove(best_candidate)

    covered_demand: Set[Any] = set(demands) - uncovered_demand
    coverage_pct = (len(covered_demand) / len(demands)) * 100.0

    return {
        "selected_nodes": selected_nodes,
        "covered_nodes": sorted(list(covered_demand)),
        "uncovered_nodes": sorted(list(uncovered_demand)),
        "coverage_percentage": round(coverage_pct, 2),
        "coverage_map": coverage_map,
    }
