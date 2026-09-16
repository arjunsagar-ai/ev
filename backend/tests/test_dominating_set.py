"""Unit tests for Minimum Dominating Set (MDS) Greedy Approximation."""
import pytest
from app.graph.weighted_graph import WeightedGraph
from app.algorithms.dominating_set import minimum_dominating_set


class TestMinimumDominatingSet:
    """Ground-truth tests for MDS greedy approximation."""

    def test_star_graph_single_central_station_covers_all(self):
        """
        Star graph with central hub 'C' and leaves 'L1', 'L2', 'L3', 'L4'.
        Each edge has weight 1.0.
        With coverage_radius = 1.0, central node 'C' covers all 5 nodes.
        Greedy algorithm must pick exactly ['C'] and achieve 100% coverage.
        """
        g = WeightedGraph(directed=False)
        for leaf in ["L1", "L2", "L3", "L4"]:
            g.add_edge("C", leaf, weight=1.0)

        res = minimum_dominating_set(g, coverage_radius=1.0)

        assert res["selected_nodes"] == ["C"]
        assert set(res["covered_nodes"]) == {"C", "L1", "L2", "L3", "L4"}
        assert res["uncovered_nodes"] == []
        assert res["coverage_percentage"] == 100.0
        assert set(res["coverage_map"]["C"]) == {"C", "L1", "L2", "L3", "L4"}

    def test_linear_graph_optimal_placement(self):
        """
        Path graph: 1 - 2 - 3 - 4 - 5 with edge weights 1.0.
        With radius 1.0:
            Node 2 covers {1, 2, 3}
            Node 4 covers {3, 4, 5}
        Greedy algorithm should select 2 nodes (e.g. 2 and 4, or 3 and 1/5) covering all 5 nodes.
        """
        g = WeightedGraph(directed=False)
        g.add_edge(1, 2, weight=1.0)
        g.add_edge(2, 3, weight=1.0)
        g.add_edge(3, 4, weight=1.0)
        g.add_edge(4, 5, weight=1.0)

        res = minimum_dominating_set(g, coverage_radius=1.0)

        assert len(res["selected_nodes"]) == 2
        assert set(res["covered_nodes"]) == {1, 2, 3, 4, 5}
        assert res["coverage_percentage"] == 100.0

    def test_candidate_nodes_restricted(self):
        """When candidate stations are restricted to a subset, only eligible candidates are picked."""
        g = WeightedGraph(directed=False)
        g.add_edge("SubstationA", "Road1", weight=1.0)
        g.add_edge("Road1", "Road2", weight=1.0)
        g.add_edge("SubstationB", "Road2", weight=1.0)

        # Only Substations are eligible to host stations
        candidates = ["SubstationA", "SubstationB"]
        demands = ["Road1", "Road2"]

        res = minimum_dominating_set(
            g,
            coverage_radius=1.5,
            candidate_nodes=candidates,
            demand_nodes=demands,
        )

        for sel in res["selected_nodes"]:
            assert sel in candidates
        assert set(res["covered_nodes"]) == {"Road1", "Road2"}
        assert res["coverage_percentage"] == 100.0

    def test_disconnected_graph_partial_coverage(self):
        """If a node is isolated and not eligible or unreachable, coverage is partial."""
        g = WeightedGraph(directed=False)
        g.add_edge("A", "B", weight=1.0)
        g.add_node("Isolated")

        # Only 'A' is candidate
        res = minimum_dominating_set(
            g,
            coverage_radius=1.0,
            candidate_nodes=["A"],
            demand_nodes=["A", "B", "Isolated"],
        )

        assert res["selected_nodes"] == ["A"]
        assert "Isolated" in res["uncovered_nodes"]
        assert res["coverage_percentage"] == round(2.0 / 3.0 * 100.0, 2)

    def test_empty_graph(self):
        g = WeightedGraph()
        res = minimum_dominating_set(g, coverage_radius=5.0)
        assert res["selected_nodes"] == []
        assert res["covered_nodes"] == []
        assert res["coverage_percentage"] == 100.0
