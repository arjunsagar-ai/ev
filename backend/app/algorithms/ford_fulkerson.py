"""Ford-Fulkerson Maximum Flow and Minimum Cut Algorithm using Edmonds-Karp BFS."""
from collections import deque
from typing import Any, Dict, List, Set, Tuple

from app.graph.weighted_graph import WeightedGraph


def ford_fulkerson_max_flow(
    graph: WeightedGraph,
    source: Any,
    sink: Any
) -> Dict[str, Any]:
    """
    Compute the Maximum Flow and Minimum Cut between source and sink in a flow network
    using the Edmonds-Karp algorithm (BFS-based implementation of the Ford-Fulkerson method).

    In the context of EV charging infrastructure:
        - Vertices represent power substations, distribution nodes, and charging stations.
        - Edge weights represent power transmission capacities (kW or MW) or vehicle throughput (EVs/hr).
        - Maximum flow determines peak concurrent power capacity deliverable to charging stations.
        - Minimum cut identifies critical transmission lines and road corridors forming bottlenecks.

    Parameters:
        graph (WeightedGraph): The flow network with edge weights representing capacities.
        source (Any): The source node (e.g. regional power grid generator/substation).
        sink (Any): The sink node (e.g. charging station demand cluster).

    Returns:
        Dict[str, Any]: Structured result containing:
            - 'maximum_flow': Total maximum flow value from source to sink.
            - 'edge_flows': Dict of (u, v) -> net positive flow.
            - 'residual_graph': Dict representing residual capacities between adjacent nodes.
            - 'min_cut': Dict containing 'source_partition', 'sink_partition', and 'cut_capacity'.
            - 'bottleneck_edges': List of saturated edges (u, v, capacity) bridging the min-cut.

    Raises:
        ValueError: If source or sink does not exist, or if edge capacities are negative.
    """
    if not graph.has_node(source):
        raise ValueError(f"Source node '{source}' does not exist in graph.")
    if not graph.has_node(sink):
        raise ValueError(f"Sink node '{sink}' does not exist in graph.")

    all_nodes = graph.nodes()

    # Edge case: source is sink
    if source == sink:
        return {
            "maximum_flow": 0.0,
            "edge_flows": {},
            "residual_graph": {n: {} for n in all_nodes},
            "min_cut": {
                "source_partition": [source],
                "sink_partition": [n for n in all_nodes if n != source],
                "cut_capacity": 0.0,
            },
            "bottleneck_edges": [],
        }

    # Build adjacency and capacity mapping for the residual network
    # residual_capacity[u][v] = remaining capacity along edge u -> v
    residual: Dict[Any, Dict[Any, float]] = {u: {} for u in all_nodes}
    original_capacities: Dict[Tuple[Any, Any], float] = {}

    for u in all_nodes:
        for v, weight in graph.get_neighbors(u).items():
            cap = float(graph.get_edge_data(u, v).get("capacity", weight))
            if cap < 0:
                raise ValueError(f"Negative capacity {cap} found on edge ({u}, {v}).")

            original_capacities[(u, v)] = cap
            residual[u][v] = residual[u].get(v, 0.0) + cap
            # Ensure reverse edge exists in residual graph
            if u not in residual[v]:
                residual[v][u] = 0.0

    max_flow: float = 0.0

    # Edmonds-Karp BFS to find shortest augmenting path (fewest edges)
    while True:
        parent: Dict[Any, Any] = {}
        queue: deque = deque([source])
        visited: Set[Any] = {source}

        while queue:
            curr = queue.popleft()
            if curr == sink:
                break

            for nxt, res_cap in residual[curr].items():
                if nxt not in visited and res_cap > 1e-9:
                    visited.add(nxt)
                    parent[nxt] = curr
                    queue.append(nxt)

        # If sink was not reached, no more augmenting paths exist
        if sink not in parent:
            break

        # Find bottleneck capacity along the augmenting path
        path_flow = float("inf")
        s = sink
        while s != source:
            p = parent[s]
            path_flow = min(path_flow, residual[p][s])
            s = p

        # Augment flow and update residual capacities
        v = sink
        while v != source:
            u = parent[v]
            residual[u][v] -= path_flow
            residual[v][u] += path_flow
            v = u

        max_flow += path_flow

    # Compute net positive edge flows on original graph edges
    edge_flows: Dict[Tuple[Any, Any], float] = {}
    for (u, v), cap in original_capacities.items():
        # Net flow = original capacity - remaining residual capacity
        flow = cap - residual[u].get(v, 0.0)
        if flow > 1e-9:
            edge_flows[(u, v)] = round(flow, 6)

    # Find Min-Cut: reachable nodes from source in final residual graph
    cut_visited: Set[Any] = {source}
    cut_queue: deque = deque([source])
    while cut_queue:
        curr = cut_queue.popleft()
        for nxt, res_cap in residual[curr].items():
            if nxt not in cut_visited and res_cap > 1e-9:
                cut_visited.add(nxt)
                cut_queue.append(nxt)

    source_partition = sorted(list(cut_visited), key=str)
    sink_partition = sorted(list(set(all_nodes) - cut_visited), key=str)

    # Bottleneck edges: original edges crossing from source partition to sink partition
    bottleneck_edges: List[Tuple[Any, Any, float]] = []
    cut_capacity: float = 0.0

    for (u, v), cap in original_capacities.items():
        if u in cut_visited and v not in cut_visited:
            cut_capacity += cap
            # Saturated edge if remaining residual capacity is 0 (or within float precision)
            if residual[u].get(v, 0.0) <= 1e-9 and cap > 0:
                bottleneck_edges.append((u, v, cap))

    # Format residual graph for clean JSON serializability
    clean_residual = {
        u: {v: round(c, 6) for v, c in neighbors.items() if c > 1e-9}
        for u, neighbors in residual.items()
    }

    return {
        "maximum_flow": round(max_flow, 6),
        "edge_flows": {f"{u}->{v}": fl for (u, v), fl in edge_flows.items()},
        "residual_graph": clean_residual,
        "min_cut": {
            "source_partition": source_partition,
            "sink_partition": sink_partition,
            "cut_capacity": round(cut_capacity, 6),
        },
        "bottleneck_edges": bottleneck_edges,
    }
