"""Prim's Minimum Spanning Tree (MST) Algorithm from scratch."""
import heapq
from typing import Any, Dict, List, Optional, Set, Tuple

from app.graph.weighted_graph import WeightedGraph


def prim_mst(
    graph: WeightedGraph,
    start_node: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Compute the Minimum Spanning Tree (MST) of a weighted graph using Prim's algorithm
    with a priority queue.

    Parameters:
        graph (WeightedGraph): The graph representing physical road connections or
                               candidate electrical cable links between stations.
        start_node (Any, optional): The initial root node for building the tree.
                                    Defaults to the first node in the graph.

    Returns:
        Dict[str, Any]: Structured result containing:
            - 'mst_edges': List of tuples (u, v, weight) representing the edges in the MST.
            - 'total_cost': Total sum of weights of the MST edges.
            - 'connected_nodes': List of nodes successfully included in the tree.
            - 'unconnected_nodes': List of nodes unreachable from the root (in disconnected graphs).

    Raises:
        TypeError: If graph is not an instance of WeightedGraph.
        ValueError: If start_node is specified but not in the graph.
    """
    if not isinstance(graph, WeightedGraph):
        raise TypeError(f"Expected WeightedGraph instance, got {type(graph).__name__}.")

    nodes = graph.nodes()

    # Empty graph
    if not nodes:
        return {
            "mst_edges": [],
            "total_cost": 0.0,
            "connected_nodes": [],
            "unconnected_nodes": [],
        }

    # Single-node graph
    if len(nodes) == 1:
        return {
            "mst_edges": [],
            "total_cost": 0.0,
            "connected_nodes": [nodes[0]],
            "unconnected_nodes": [],
        }

    # Validate start_node
    if start_node is None:
        start_node = nodes[0]
    elif not graph.has_node(start_node):
        raise ValueError(f"Start node '{start_node}' does not exist in graph.")

    in_mst: Set[Any] = {start_node}
    mst_edges: List[Tuple[Any, Any, float]] = []
    total_cost: float = 0.0

    # Min-priority queue storing tuples: (weight, u, v)
    pq: List[Tuple[float, Any, Any]] = []

    # Push all initial edges from start_node into the priority queue
    for neighbor, weight in graph.get_neighbors(start_node).items():
        heapq.heappush(pq, (weight, start_node, neighbor))

    # Prim's greedy frontier expansion
    while pq and len(in_mst) < len(nodes):
        weight, u, v = heapq.heappop(pq)

        # If destination node is already part of the MST, skip cycle
        if v in in_mst:
            continue

        # Add node v and edge (u, v) to the MST
        in_mst.add(v)
        mst_edges.append((u, v, weight))
        total_cost += weight

        # Push newly exposed edges from v to unvisited neighbors
        for neighbor, edge_weight in graph.get_neighbors(v).items():
            if neighbor not in in_mst:
                heapq.heappush(pq, (edge_weight, v, neighbor))

    all_nodes_set = set(nodes)
    unconnected = all_nodes_set - in_mst

    return {
        "mst_edges": mst_edges,
        "total_cost": round(total_cost, 6),
        "connected_nodes": sorted(list(in_mst), key=str),
        "unconnected_nodes": sorted(list(unconnected), key=str),
    }
