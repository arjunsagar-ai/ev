"""Custom Weighted Graph data structure using an Adjacency List."""
from typing import Any, Dict, List, Optional, Set, Tuple

from app.utils.distance import haversine_distance


class WeightedGraph:
    """
    A reusable weighted graph data structure G = (V, E, W).
    
    Represents road networks, electrical transmission grids, and general network topologies.
    Internally maintained via an adjacency-list representation mapping:
        u -> {v: weight}
    
    Nodes can store geographical coordinates (lat, lon) and arbitrary metadata.
    Edges support distance-based weights, custom costs/capacities, and directed/undirected configurations.
    """

    def __init__(self, directed: bool = False):
        """
        Initialize an empty weighted graph.
        
        Parameters:
            directed (bool): Whether edges added to this graph default to directed (True)
                            or undirected/bidirectional (False).
        """
        self.default_directed: bool = directed
        # Node attributes: node_id -> {"lat": float, "lon": float, ...}
        self._nodes: Dict[Any, Dict[str, Any]] = {}
        # Adjacency list: u -> {v: weight}
        self._adj: Dict[Any, Dict[Any, float]] = {}
        # Edge metadata: (u, v) -> dict of attributes
        self._edge_data: Dict[Tuple[Any, Any], Dict[str, Any]] = {}

    def add_node(
        self,
        node_id: Any,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        **attrs: Any
    ) -> None:
        """
        Add a node to the graph with optional latitude and longitude coordinates.

        Parameters:
            node_id: Unique identifier for the node (int, str, etc.).
            lat (float, optional): Latitude coordinate in decimal degrees.
            lon (float, optional): Longitude coordinate in decimal degrees.
            **attrs: Additional arbitrary node attributes (e.g., node type, demand).
        """
        if node_id not in self._nodes:
            self._nodes[node_id] = {}
            self._adj[node_id] = {}

        if lat is not None:
            self._nodes[node_id]["lat"] = float(lat)
        if lon is not None:
            self._nodes[node_id]["lon"] = float(lon)

        self._nodes[node_id].update(attrs)

    def has_node(self, node_id: Any) -> bool:
        """Check whether a node exists in the graph."""
        return node_id in self._nodes

    def get_coordinates(self, node_id: Any) -> Optional[Tuple[float, float]]:
        """
        Get the (latitude, longitude) of a node if set.

        Returns:
            Tuple[float, float] if coordinates exist, None otherwise.
        """
        if not self.has_node(node_id):
            raise KeyError(f"Node '{node_id}' does not exist in graph.")

        data = self._nodes[node_id]
        if "lat" in data and "lon" in data:
            return (data["lat"], data["lon"])
        return None

    def get_node_data(self, node_id: Any) -> Dict[str, Any]:
        """Retrieve all attributes stored on a node."""
        if not self.has_node(node_id):
            raise KeyError(f"Node '{node_id}' does not exist in graph.")
        return dict(self._nodes[node_id])

    def add_edge(
        self,
        u: Any,
        v: Any,
        weight: Optional[float] = None,
        directed: Optional[bool] = None,
        **attrs: Any
    ) -> None:
        """
        Add a weighted edge between node u and node v.
        If nodes u or v do not exist, they are automatically added.
        
        If weight is not provided and both nodes possess (lat, lon) coordinates,
        the weight defaults to the Haversine distance in kilometers.

        Parameters:
            u: Source node identifier.
            v: Destination/target node identifier.
            weight (float, optional): Edge weight (e.g. distance, travel time, cost).
            directed (bool, optional): If True, adds edge u -> v only.
                                       If False, adds bidirectional edges u <-> v.
                                       Defaults to self.default_directed if None.
            **attrs: Additional edge metadata (e.g., capacity, max_speed).
        """
        # Ensure both endpoints exist
        if not self.has_node(u):
            self.add_node(u)
        if not self.has_node(v):
            self.add_node(v)

        is_directed = self.default_directed if directed is None else directed

        # Calculate geographic distance if weight not explicitly supplied
        if weight is None:
            coord_u = self.get_coordinates(u)
            coord_v = self.get_coordinates(v)
            if coord_u is not None and coord_v is not None:
                weight = haversine_distance(coord_u[0], coord_u[1], coord_v[0], coord_v[1], unit="km")
            else:
                raise ValueError(
                    f"Edge ({u}, {v}) weight not specified and node coordinates are missing."
                )

        if weight < 0:
            raise ValueError(f"Edge weight cannot be negative: got {weight} for edge ({u}, {v}).")

        self._adj[u][v] = float(weight)
        self._edge_data[(u, v)] = dict(attrs)

        if not is_directed:
            self._adj[v][u] = float(weight)
            self._edge_data[(v, u)] = dict(attrs)

    def has_edge(self, u: Any, v: Any) -> bool:
        """Check whether a directed edge from u to v exists."""
        return u in self._adj and v in self._adj[u]

    def get_weight(self, u: Any, v: Any) -> float:
        """
        Retrieve the weight of directed edge (u, v).
        
        Raises:
            KeyError: If edge (u, v) does not exist.
        """
        if not self.has_edge(u, v):
            raise KeyError(f"Edge ({u}, {v}) does not exist in graph.")
        return self._adj[u][v]

    def get_edge_data(self, u: Any, v: Any) -> Dict[str, Any]:
        """Retrieve metadata attributes for edge (u, v)."""
        if not self.has_edge(u, v):
            raise KeyError(f"Edge ({u}, {v}) does not exist in graph.")
        return dict(self._edge_data.get((u, v), {}))

    def get_neighbors(self, node_id: Any) -> Dict[Any, float]:
        """
        Retrieve all outgoing neighbors of node_id along with their edge weights.

        Returns:
            Dict[neighbor_id, weight]
        """
        if not self.has_node(node_id):
            raise KeyError(f"Node '{node_id}' does not exist in graph.")
        return dict(self._adj[node_id])

    def nodes(self) -> List[Any]:
        """Return a list of all node identifiers in the graph."""
        return list(self._nodes.keys())

    def edges(self, data: bool = False) -> List[Tuple]:
        """
        Return a list of all edges in the graph.
        
        Parameters:
            data (bool): If True, returns (u, v, weight).
                         If False, returns (u, v).
        """
        edge_list: List[Tuple] = []
        visited_undirected: Set[Tuple[Any, Any]] = set()

        for u, neighbors in self._adj.items():
            for v, weight in neighbors.items():
                if not self.default_directed:
                    # Avoid duplicates in undirected representation
                    edge_pair = tuple(sorted([str(u), str(v)]))
                    if edge_pair in visited_undirected:
                        continue
                    visited_undirected.add(edge_pair)

                if data:
                    edge_list.append((u, v, weight))
                else:
                    edge_list.append((u, v))

        return edge_list

    def num_nodes(self) -> int:
        """Return total number of nodes in the graph."""
        return len(self._nodes)

    def num_edges(self) -> int:
        """Return total number of edges in the graph."""
        return len(self.edges(data=False))

    def remove_edge(self, u: Any, v: Any, directed: Optional[bool] = None) -> None:
        """Remove edge between u and v."""
        is_directed = self.default_directed if directed is None else directed
        if self.has_edge(u, v):
            del self._adj[u][v]
            self._edge_data.pop((u, v), None)

        if not is_directed and self.has_edge(v, u):
            del self._adj[v][u]
            self._edge_data.pop((v, u), None)

    def remove_node(self, node_id: Any) -> None:
        """Remove a node and all incident edges."""
        if not self.has_node(node_id):
            return

        # Remove incident incoming edges
        for u in list(self._adj.keys()):
            if node_id in self._adj[u]:
                del self._adj[u][node_id]
                self._edge_data.pop((u, node_id), None)

        # Remove outgoing edges and node entry
        for v in list(self._adj[node_id].keys()):
            self._edge_data.pop((node_id, v), None)

        del self._adj[node_id]
        del self._nodes[node_id]

    def clear(self) -> None:
        """Clear all nodes and edges from the graph."""
        self._nodes.clear()
        self._adj.clear()
        self._edge_data.clear()

    def __len__(self) -> int:
        return self.num_nodes()

    def __repr__(self) -> str:
        directed_str = "Directed" if self.default_directed else "Undirected"
        return f"<WeightedGraph ({directed_str}): {self.num_nodes()} nodes, {self.num_edges()} edges>"
