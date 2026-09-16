"""Unit tests for WeightedGraph and Haversine distance utilities."""
import pytest
import math
from app.graph.weighted_graph import WeightedGraph
from app.utils.distance import haversine_distance


class TestHaversineDistance:
    """Mathematical ground-truth tests for Haversine distance calculation."""

    def test_identical_coordinates_returns_zero(self):
        dist = haversine_distance(12.9716, 77.5946, 12.9716, 77.5946, unit="km")
        assert dist == 0.0

    def test_known_city_distance_london_to_paris(self):
        """
        London: (51.5074 N, 0.1278 W)
        Paris:  (48.8566 N, 2.3522 E)
        Expected great-circle distance is ~343.5 km (+/- 2 km).
        """
        dist_km = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522, unit="km")
        assert math.isclose(dist_km, 343.5, abs_tol=2.0)

    def test_known_distance_in_meters(self):
        dist_km = haversine_distance(12.9716, 77.5946, 13.0827, 80.2707, unit="km")
        dist_m = haversine_distance(12.9716, 77.5946, 13.0827, 80.2707, unit="m")
        assert math.isclose(dist_m, dist_km * 1000.0, rel_tol=1e-5)

    def test_invalid_latitude_raises_value_error(self):
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            haversine_distance(95.0, 0.0, 10.0, 10.0)

    def test_invalid_longitude_raises_value_error(self):
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            haversine_distance(10.0, -190.0, 10.0, 10.0)

    def test_invalid_unit_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid unit"):
            haversine_distance(10.0, 20.0, 10.0, 21.0, unit="miles")  # type: ignore


class TestWeightedGraph:
    """Ground-truth tests for custom WeightedGraph data structure."""

    def test_add_nodes_and_retrieve_coordinates(self):
        g = WeightedGraph(directed=False)
        g.add_node("A", lat=12.9716, lon=77.5946, type="substation")
        g.add_node("B", lat=12.9800, lon=77.6000, type="station")

        assert g.has_node("A")
        assert g.has_node("B")
        assert not g.has_node("C")
        assert g.num_nodes() == 2
        assert len(g) == 2

        coords_a = g.get_coordinates("A")
        assert coords_a == (12.9716, 77.5946)
        assert g.get_node_data("A")["type"] == "substation"

    def test_add_edge_explicit_weight_undirected(self):
        g = WeightedGraph(directed=False)
        g.add_edge("A", "B", weight=4.5)

        assert g.has_edge("A", "B")
        assert g.has_edge("B", "A")
        assert g.get_weight("A", "B") == 4.5
        assert g.get_weight("B", "A") == 4.5
        assert g.get_neighbors("A") == {"B": 4.5}
        assert g.get_neighbors("B") == {"A": 4.5}

    def test_add_edge_directed(self):
        g = WeightedGraph(directed=True)
        g.add_edge("A", "B", weight=2.0)

        assert g.has_edge("A", "B")
        assert not g.has_edge("B", "A")
        assert g.get_weight("A", "B") == 2.0
        assert "B" not in g.get_neighbors("B")

    def test_add_edge_haversine_auto_weight(self):
        g = WeightedGraph(directed=False)
        # London and Paris
        g.add_node("London", lat=51.5074, lon=-0.1278)
        g.add_node("Paris", lat=48.8566, lon=2.3522)
        # Without explicit weight, should compute Haversine distance in km
        g.add_edge("London", "Paris")

        weight = g.get_weight("London", "Paris")
        assert math.isclose(weight, 343.5, abs_tol=2.0)

    def test_negative_weight_raises_error(self):
        g = WeightedGraph()
        with pytest.raises(ValueError, match="Edge weight cannot be negative"):
            g.add_edge("A", "B", weight=-1.0)

    def test_missing_coordinates_and_no_weight_raises_error(self):
        g = WeightedGraph()
        g.add_node("A")
        g.add_node("B")
        with pytest.raises(ValueError, match="Edge .* weight not specified and node coordinates are missing"):
            g.add_edge("A", "B")

    def test_remove_edge_and_node(self):
        g = WeightedGraph(directed=False)
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=2.0)

        assert g.num_edges() == 2
        g.remove_edge("A", "B")
        assert not g.has_edge("A", "B")
        assert not g.has_edge("B", "A")
        assert g.num_edges() == 1

        g.remove_node("B")
        assert not g.has_node("B")
        assert not g.has_edge("B", "C")
        assert g.num_nodes() == 2

    def test_clear_graph(self):
        g = WeightedGraph()
        g.add_edge("A", "B", weight=3.0)
        g.clear()
        assert g.num_nodes() == 0
        assert g.num_edges() == 0
