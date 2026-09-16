"""Tests for spatial indexing, coordinate validation, and GPS snapping."""
import math
import pytest

from app.gis.osm_loader import build_sample_road_network
from app.gis.spatial_index import (
    find_nearest_road_node,
    snap_coordinates_to_road,
    validate_coordinates,
)
from app.graph.weighted_graph import WeightedGraph


# ────────────────── fixtures ─────────────────────────────────────────────

@pytest.fixture
def sample_graph() -> WeightedGraph:
    g, _ = build_sample_road_network()
    return g


# ────────────────── validate_coordinates ─────────────────────────────────

class TestValidateCoordinates:
    def test_valid_coordinates(self):
        validate_coordinates(10.0, 76.3)   # no exception
        validate_coordinates(-90.0, -180.0)
        validate_coordinates(90.0, 180.0)
        validate_coordinates(0.0, 0.0)

    def test_latitude_out_of_range(self):
        with pytest.raises(ValueError, match="latitude must be between"):
            validate_coordinates(91.0, 76.0)

    def test_latitude_negative_out_of_range(self):
        with pytest.raises(ValueError, match="latitude must be between"):
            validate_coordinates(-91.0, 76.0)

    def test_longitude_out_of_range(self):
        with pytest.raises(ValueError, match="longitude must be between"):
            validate_coordinates(10.0, 181.0)

    def test_longitude_negative_out_of_range(self):
        with pytest.raises(ValueError, match="longitude must be between"):
            validate_coordinates(10.0, -181.0)

    def test_nan_latitude(self):
        with pytest.raises(ValueError, match="must not be NaN"):
            validate_coordinates(float("nan"), 76.0)

    def test_nan_longitude(self):
        with pytest.raises(ValueError, match="must not be NaN"):
            validate_coordinates(10.0, float("nan"))

    def test_infinity_latitude(self):
        with pytest.raises(ValueError, match="must not be infinite"):
            validate_coordinates(float("inf"), 76.0)

    def test_infinity_longitude(self):
        with pytest.raises(ValueError, match="must not be infinite"):
            validate_coordinates(10.0, float("-inf"))

    def test_non_numeric_latitude(self):
        with pytest.raises(TypeError, match="latitude must be numeric"):
            validate_coordinates("ten", 76.0)  # type: ignore

    def test_non_numeric_longitude(self):
        with pytest.raises(TypeError, match="longitude must be numeric"):
            validate_coordinates(10.0, None)  # type: ignore


# ────────────────── find_nearest_road_node ───────────────────────────────

class TestFindNearestRoadNode:
    def test_exact_node_coordinate(self, sample_graph):
        """Query point exactly at node N01 (10.000, 76.300)."""
        result = find_nearest_road_node(sample_graph, 10.000, 76.300)
        assert result["node_id"] == "N01"
        assert result["distance_m"] == 0.0

    def test_coordinate_between_nodes(self, sample_graph):
        """A point between N01 (10.000,76.300) and N02 (10.000,76.305)
        should snap to the closer one."""
        result = find_nearest_road_node(sample_graph, 10.000, 76.301)
        assert result["node_id"] in ("N01", "N02")
        assert result["distance_m"] > 0.0

    def test_far_away_coordinate(self, sample_graph):
        """A point far from the network still returns the closest node."""
        result = find_nearest_road_node(sample_graph, 10.050, 76.350)
        assert result["node_id"] is not None
        assert result["distance_m"] > 1000  # well over 1 km away

    def test_empty_graph_raises(self):
        g = WeightedGraph()
        with pytest.raises(ValueError, match="no nodes with coordinates"):
            find_nearest_road_node(g, 10.0, 76.0)

    def test_graph_with_no_coords_raises(self):
        g = WeightedGraph()
        g.add_node("X")
        g.add_node("Y")
        with pytest.raises(ValueError, match="no nodes with coordinates"):
            find_nearest_road_node(g, 10.0, 76.0)


# ────────────────── snap_coordinates_to_road ─────────────────────────────

class TestSnapCoordinates:
    def test_snap_close_point(self, sample_graph):
        result = snap_coordinates_to_road(sample_graph, 10.0001, 76.3001)
        assert result["nearest_node"]["id"] is not None
        assert result["distance_to_road_m"] < 100  # close by
        assert result["input"]["latitude"] == 10.0001

    def test_snap_returns_correct_structure(self, sample_graph):
        result = snap_coordinates_to_road(sample_graph, 10.003, 76.310)
        assert "input" in result
        assert "nearest_node" in result
        assert "distance_to_road_m" in result
        assert "id" in result["nearest_node"]
        assert "latitude" in result["nearest_node"]
        assert "longitude" in result["nearest_node"]

    def test_snap_rejects_too_far(self, sample_graph):
        """Point 50 km away should exceed max snap distance."""
        with pytest.raises(ValueError, match="exceeding the maximum snap distance"):
            snap_coordinates_to_road(
                sample_graph, 10.500, 76.800, max_distance_m=1000.0,
            )

    def test_snap_rejects_invalid_coords(self, sample_graph):
        with pytest.raises(ValueError, match="latitude must be between"):
            snap_coordinates_to_road(sample_graph, 95.0, 76.0)

    def test_snap_rejects_nan(self, sample_graph):
        with pytest.raises(ValueError, match="must not be NaN"):
            snap_coordinates_to_road(sample_graph, float("nan"), 76.0)
