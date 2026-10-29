"""Dijkstra's Shortest Path Algorithm from scratch."""
import heapq
import time
from typing import Any, Dict, List, Optional

from app.graph.weighted_graph import WeightedGraph


def dijkstra_shortest_path(
    graph: WeightedGraph,
    source: Any,
    target: Any
) -> Dict[str, Any]:
    """
    Compute the shortest path between source and target nodes in a weighted graph
    using Dijkstra's algorithm with a min-priority queue (heap).

    Parameters:
        graph (WeightedGraph): The weighted road/network graph.
        source (Any): The source node identifier.
        target (Any): The destination/target node identifier.

    Returns:
        Dict[str, Any]: Structured result containing:
            - 'path': List of node IDs from source to target (empty if unreachable).
            - 'total_distance': Total shortest path distance (float('inf') if unreachable).
            - 'visited_nodes': List of settled nodes in order of exploration.
            - 'execution_time': Execution runtime in seconds.

    Raises:
        ValueError: If source or target do not exist in the graph.
    """
    start_time = time.perf_counter()

    if not graph.has_node(source):
        raise ValueError(f"Source node '{source}' does not exist in the graph.")
    if not graph.has_node(target):
        raise ValueError(f"Target node '{target}' does not exist in the graph.")

    # Edge case: source is target
    if source == target:
        elapsed = time.perf_counter() - start_time
        return {
            "path": [source],
            "total_distance": 0.0,
            "visited_nodes": [source],
            "execution_time": elapsed,
        }

    # Fast-check for disconnected components if precomputed on graph
    comp_map = getattr(graph, "_component_map", None)
    if comp_map is not None:
        source_comp = comp_map.get(source)
        target_comp = comp_map.get(target)
        if source_comp is not None and target_comp is not None and source_comp != target_comp:
            elapsed = time.perf_counter() - start_time
            return {
                "path": [],
                "total_distance": float("inf"),
                "visited_nodes": [],
                "execution_time": elapsed,
            }

    # Distance table: distance from source to discovered nodes (on-demand to avoid allocating large tables)
    distances: Dict[Any, float] = {source: 0.0}

    # Predecessor mapping for path reconstruction
    predecessors: Dict[Any, Optional[Any]] = {source: None}

    # Check for target node coordinates for A* heuristic
    t_coords = graph.get_coordinates(target) if hasattr(graph, "get_coordinates") else None
    has_heuristic = t_coords is not None
    t_lat, t_lon = t_coords if has_heuristic else (0.0, 0.0)

    # Min-priority queue storing tuples: (priority, distance, node)
    pq: List[tuple[float, float, Any]] = [(0.0, 0.0, source)]
    settled: set[Any] = set()
    visited_nodes: List[Any] = []

    while pq:
        _, curr_dist, u = heapq.heappop(pq)

        if u in settled:
            continue
        settled.add(u)
        visited_nodes.append(u)

        # Early exit: reached target with optimal distance
        if u == target:
            break

        # If current distance is worse than recorded best, skip
        if curr_dist > distances.get(u, float("inf")):
            continue

        # Relax incident edges
        for neighbor, weight in graph.get_neighbors(u).items():
            new_dist = curr_dist + weight
            if neighbor not in distances or new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                predecessors[neighbor] = u
                h = 0.0
                if has_heuristic:
                    nc = graph.get_coordinates(neighbor)
                    if nc:
                        import math
                        dlat = abs(t_lat - nc[0]) * 110.0
                        dlon = abs(t_lon - nc[1]) * 108.0
                        h = math.hypot(dlat, dlon)
                heapq.heappush(pq, (new_dist + h, new_dist, neighbor))

    # Path reconstruction
    if target not in distances:
        path: List[Any] = []
        total_dist = float("inf")
    else:
        path = []
        curr = target
        while curr is not None:
            path.append(curr)
            curr = predecessors.get(curr)
        path.reverse()
        total_dist = distances[target]

    elapsed = time.perf_counter() - start_time
    return {
        "path": path,
        "total_distance": total_dist,
        "visited_nodes": visited_nodes,
        "execution_time": elapsed,
    }
