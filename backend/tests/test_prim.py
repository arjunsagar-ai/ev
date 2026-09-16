"""Unit tests for Prim's Minimum Spanning Tree (MST) algorithm."""
import pytest
from app.graph.weighted_graph import WeightedGraph
from app.algorithms.prim import prim_mst


class TestPrimMST:
    """Ground-truth mathematical tests for Prim's MST."""

    @pytest.fixture
    def known_mst_graph(self) -> WeightedGraph:
        """
        Deterministic undirected graph:
            A - B: 1
            B - C: 2
            A - C: 4
            C - D: 3
            B - D: 5
            C - E: 6
            D - E: 7

        Expected MST edges:
            (A, B, 1)
            (B, C, 2)
            (C, D, 3)
            (C, E, 6)
        Total MST Cost: 1 + 2 + 3 + 6 = 12.0
        """
        g = WeightedGraph(directed=False)
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=2.0)
        g.add_edge("A", "C", weight=4.0)
        g.add_edge("C", "D", weight=3.0)
        g.add_edge("B", "D", weight=5.0)
        g.add_edge("C", "E", weight=6.0)
        g.add_edge("D", "E", weight=7.0)
        return g

    def test_known_mst_total_cost_and_edges(self, known_mst_graph):
        res = prim_mst(known_mst_graph, start_node="A")

        assert res["total_cost"] == 12.0
        assert len(res["mst_edges"]) == 4  # |V| - 1 = 5 - 1 = 4
        assert set(res["connected_nodes"]) == {"A", "B", "C", "D", "E"}
        assert res["unconnected_nodes"] == []

        # Verify all MST edges sum to total cost
        edge_weight_sum = sum(edge[2] for edge in res["mst_edges"])
        assert edge_weight_sum == 12.0

    def test_single_node_graph(self):
        g = WeightedGraph(directed=False)
        g.add_node("SingleHub")
        res = prim_mst(g)

        assert res["total_cost"] == 0.0
        assert res["mst_edges"] == []
        assert res["connected_nodes"] == ["SingleHub"]
        assert res["unconnected_nodes"] == []

    def test_empty_graph(self):
        g = WeightedGraph(directed=False)
        res = prim_mst(g)

        assert res["total_cost"] == 0.0
        assert res["mst_edges"] == []
        assert res["connected_nodes"] == []
        assert res["unconnected_nodes"] == []

    def test_disconnected_graph_reports_unconnected_nodes(self):
        g = WeightedGraph(directed=False)
        # Component 1
        g.add_edge("A", "B", weight=3.0)
        # Component 2 (isolated)
        g.add_edge("X", "Y", weight=5.0)

        res = prim_mst(g, start_node="A")

        assert res["total_cost"] == 3.0
        assert len(res["mst_edges"]) == 1
        assert set(res["connected_nodes"]) == {"A", "B"}
        assert set(res["unconnected_nodes"]) == {"X", "Y"}

    def test_invalid_graph_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected WeightedGraph instance"):
            prim_mst("not_a_graph")  # type: ignore

    def test_invalid_start_node_raises_value_error(self, known_mst_graph):
        with pytest.raises(ValueError, match="Start node 'Ghost' does not exist"):
            prim_mst(known_mst_graph, start_node="Ghost")
