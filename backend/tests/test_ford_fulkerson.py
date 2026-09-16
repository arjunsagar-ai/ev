"""Unit tests for Ford-Fulkerson (Edmonds-Karp) Maximum Flow and Minimum Cut."""
import pytest
from app.graph.weighted_graph import WeightedGraph
from app.algorithms.ford_fulkerson import ford_fulkerson_max_flow


class TestFordFulkersonMaxFlow:
    """Ground-truth mathematical tests for Ford-Fulkerson (Edmonds-Karp)."""

    def test_standard_4_node_flow_network(self):
        """
        Flow network:
            s -> u (capacity 10)
            s -> v (capacity 6)
            u -> v (capacity 2)
            u -> t (capacity 4)
            v -> t (capacity 8)

        Max Flow calculation:
            - Augment s -> u -> t: flow 4 (u -> t saturated)
            - Augment s -> v -> t: flow 6 (s -> v saturated)
            - Augment s -> u -> v -> t: flow 2 (u -> v and v -> t saturated)
            Total Max Flow = 4 + 6 + 2 = 12.0.

        Min Cut:
            S = {s, u, v}, T = {t}
            Bottleneck saturated edges: (u, t, 4.0), (v, t, 8.0)
            Cut capacity = 12.0.
        """
        g = WeightedGraph(directed=True)
        g.add_edge("s", "u", weight=10.0)
        g.add_edge("s", "v", weight=6.0)
        g.add_edge("u", "v", weight=2.0)
        g.add_edge("u", "t", weight=4.0)
        g.add_edge("v", "t", weight=8.0)

        res = ford_fulkerson_max_flow(g, source="s", sink="t")

        assert res["maximum_flow"] == 12.0
        assert set(res["min_cut"]["source_partition"]) == {"s", "u"}
        assert set(res["min_cut"]["sink_partition"]) == {"v", "t"}
        assert res["min_cut"]["cut_capacity"] == 12.0

        # Verify bottleneck edges crossing the min-cut (s->v, u->v, u->t)
        bottleneck_pairs = [(u, v) for u, v, _ in res["bottleneck_edges"]]
        assert ("s", "v") in bottleneck_pairs
        assert ("u", "v") in bottleneck_pairs
        assert ("u", "t") in bottleneck_pairs

        # Verify edge flows
        assert res["edge_flows"]["s->u"] == 6.0
        assert res["edge_flows"]["s->v"] == 6.0
        assert res["edge_flows"]["u->t"] == 4.0
        assert res["edge_flows"]["v->t"] == 8.0
        assert res["edge_flows"]["u->v"] == 2.0

    def test_classic_clrs_6_node_flow_network(self):
        """
        Standard Cormen-Leiserson-Rivest-Stein 6-node network:
        Source 's', Sink 't'.
        Known maximum flow is exactly 23.0.
        """
        g = WeightedGraph(directed=True)
        g.add_edge("s", "v1", weight=16.0)
        g.add_edge("s", "v2", weight=13.0)
        g.add_edge("v1", "v3", weight=12.0)
        g.add_edge("v2", "v1", weight=4.0)
        g.add_edge("v1", "v2", weight=10.0)
        g.add_edge("v2", "v4", weight=14.0)
        g.add_edge("v3", "v2", weight=9.0)
        g.add_edge("v3", "t", weight=20.0)
        g.add_edge("v4", "v3", weight=7.0)
        g.add_edge("v4", "t", weight=4.0)

        res = ford_fulkerson_max_flow(g, source="s", sink="t")
        assert res["maximum_flow"] == 23.0
        assert res["min_cut"]["cut_capacity"] == 23.0

    def test_source_equals_sink(self):
        g = WeightedGraph(directed=True)
        g.add_edge("s", "s", weight=10.0)
        res = ford_fulkerson_max_flow(g, source="s", sink="s")
        assert res["maximum_flow"] == 0.0

    def test_disconnected_source_and_sink(self):
        g = WeightedGraph(directed=True)
        g.add_edge("s", "u", weight=5.0)
        g.add_edge("v", "t", weight=5.0)
        # No path between u and v
        res = ford_fulkerson_max_flow(g, source="s", sink="t")
        assert res["maximum_flow"] == 0.0
        assert "t" in res["min_cut"]["sink_partition"]

    def test_zero_capacity_network(self):
        g = WeightedGraph(directed=True)
        g.add_edge("s", "t", weight=0.0)
        res = ford_fulkerson_max_flow(g, source="s", sink="t")
        assert res["maximum_flow"] == 0.0

    def test_negative_capacity_raises_error(self):
        g = WeightedGraph(directed=True)
        # Inject negative capacity via edge data
        g.add_node("s")
        g.add_node("t")
        g._adj["s"]["t"] = -5.0
        with pytest.raises(ValueError, match="Negative capacity"):
            ford_fulkerson_max_flow(g, "s", "t")

    def test_invalid_source_or_sink_raises_error(self):
        g = WeightedGraph(directed=True)
        g.add_node("s")
        with pytest.raises(ValueError, match="Sink node 'Ghost' does not exist"):
            ford_fulkerson_max_flow(g, "s", "Ghost")
