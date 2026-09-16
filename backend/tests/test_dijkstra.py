"""Unit tests for Dijkstra's shortest path algorithm."""
import pytest
from app.graph.weighted_graph import WeightedGraph
from app.algorithms.dijkstra import dijkstra_shortest_path


class TestDijkstraShortestPath:
    """Ground-truth mathematical tests for Dijkstra's shortest path."""

    @pytest.fixture
    def known_graph(self) -> WeightedGraph:
        """
        Creates a deterministic directed graph with a known shortest path:
            S -> A: 1
            S -> B: 4
            A -> B: 2
            A -> C: 5
            B -> C: 1
            B -> T: 6
            C -> T: 3
        Shortest Path from S to T:
            S -> A (cost 1) -> B (cost 1+2=3) -> C (cost 3+1=4) -> T (cost 4+3=7)
            Path: ['S', 'A', 'B', 'C', 'T']
            Total distance: 7.0
        """
        g = WeightedGraph(directed=True)
        g.add_edge("S", "A", weight=1.0)
        g.add_edge("S", "B", weight=4.0)
        g.add_edge("A", "B", weight=2.0)
        g.add_edge("A", "C", weight=5.0)
        g.add_edge("B", "C", weight=1.0)
        g.add_edge("B", "T", weight=6.0)
        g.add_edge("C", "T", weight=3.0)
        return g

    def test_known_shortest_path_and_distance(self, known_graph):
        res = dijkstra_shortest_path(known_graph, "S", "T")

        assert res["path"] == ["S", "A", "B", "C", "T"]
        assert res["total_distance"] == 7.0
        assert "S" in res["visited_nodes"]
        assert "T" in res["visited_nodes"]
        assert res["execution_time"] >= 0.0

    def test_direct_edge_suboptimal_compared_to_multihop(self):
        """Verify that algorithm picks the lower cost multi-hop over expensive direct link."""
        g = WeightedGraph(directed=True)
        g.add_edge("Home", "Work", weight=50.0)  # Expensive direct route
        g.add_edge("Home", "Way1", weight=10.0)
        g.add_edge("Way1", "Way2", weight=10.0)
        g.add_edge("Way2", "Work", weight=10.0)  # Total 30.0

        res = dijkstra_shortest_path(g, "Home", "Work")
        assert res["path"] == ["Home", "Way1", "Way2", "Work"]
        assert res["total_distance"] == 30.0

    def test_source_equals_target(self, known_graph):
        res = dijkstra_shortest_path(known_graph, "S", "S")
        assert res["path"] == ["S"]
        assert res["total_distance"] == 0.0
        assert res["visited_nodes"] == ["S"]

    def test_unreachable_target_returns_empty_path_and_inf(self, known_graph):
        known_graph.add_node("Isolated")
        res = dijkstra_shortest_path(known_graph, "S", "Isolated")

        assert res["path"] == []
        assert res["total_distance"] == float("inf")

    def test_invalid_source_raises_value_error(self, known_graph):
        with pytest.raises(ValueError, match="Source node 'NonExistent' does not exist"):
            dijkstra_shortest_path(known_graph, "NonExistent", "T")

    def test_invalid_target_raises_value_error(self, known_graph):
        with pytest.raises(ValueError, match="Target node 'NonExistent' does not exist"):
            dijkstra_shortest_path(known_graph, "S", "NonExistent")
