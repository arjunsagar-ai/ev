"""Tests for candidate-location generation, feasibility scoring, and filtering."""
import pytest

from app.gis.candidate_generator import (
    compute_feasibility_score,
    filter_feasible_candidates,
    generate_candidates_from_graph,
    generate_candidates_from_points,
    _road_accessibility,
)
from app.gis.models import CandidateLocation
from app.gis.osm_loader import build_sample_road_network
from app.graph.weighted_graph import WeightedGraph


# ────────────────── fixtures ─────────────────────────────────────────────

@pytest.fixture
def sample_graph() -> WeightedGraph:
    g, _ = build_sample_road_network()
    return g


# ────────────────── road accessibility heuristic ─────────────────────────

class TestRoadAccessibility:
    def test_on_road(self):
        assert _road_accessibility(0.0) == 1.0

    def test_at_max_distance(self):
        from app.core.config import settings
        assert _road_accessibility(settings.CANDIDATE_MAX_ROAD_DISTANCE_M) == 0.0

    def test_halfway(self):
        from app.core.config import settings
        mid = settings.CANDIDATE_MAX_ROAD_DISTANCE_M / 2
        assert abs(_road_accessibility(mid) - 0.5) < 0.01

    def test_beyond_max(self):
        assert _road_accessibility(99999.0) == 0.0


# ────────────────── feasibility scoring ──────────────────────────────────

class TestFeasibilityScore:
    def test_perfect_candidate(self):
        cand = CandidateLocation(
            candidate_id="BEST",
            latitude=10.0, longitude=76.3,
            accessibility_score=1.0,
            land_available=1.0,
            grid_capacity=1.0,
            installation_cost=0.0,
        )
        score = compute_feasibility_score(cand)
        # 0.30*1 + 0.25*1 + 0.25*1 - 0.20*0 = 0.80
        assert abs(score - 0.80) < 0.01

    def test_worst_candidate(self):
        cand = CandidateLocation(
            candidate_id="WORST",
            latitude=10.0, longitude=76.3,
            accessibility_score=0.0,
            land_available=0.0,
            grid_capacity=0.0,
            installation_cost=1.0,
        )
        score = compute_feasibility_score(cand)
        # 0 + 0 + 0 - 0.20 = -0.20 → clamped to 0.0
        assert score == 0.0

    def test_score_is_clamped_to_unit_interval(self):
        cand = CandidateLocation(
            candidate_id="OVER",
            latitude=10.0, longitude=76.3,
            accessibility_score=5.0,
            land_available=5.0,
            grid_capacity=5.0,
            installation_cost=0.0,
        )
        score = compute_feasibility_score(cand)
        assert 0.0 <= score <= 1.0


# ────────────────── generate from graph ──────────────────────────────────

class TestGenerateFromGraph:
    def test_returns_non_empty_list(self, sample_graph):
        candidates = generate_candidates_from_graph(sample_graph)
        assert len(candidates) > 0

    def test_each_candidate_has_required_fields(self, sample_graph):
        candidates = generate_candidates_from_graph(sample_graph)
        for c in candidates:
            assert c.candidate_id is not None
            assert c.latitude is not None
            assert c.longitude is not None
            assert c.nearest_road_node is not None
            assert c.data_source == "sample"
            assert c.grid_capacity_source in ("estimated", "unknown", "measured", "synthetic")
            assert 0.0 <= c.feasibility_score <= 1.0

    def test_intersection_filter(self, sample_graph):
        all_cands = generate_candidates_from_graph(sample_graph, node_selection="all")
        int_cands = generate_candidates_from_graph(sample_graph, node_selection="intersections")
        assert len(int_cands) <= len(all_cands)


# ────────────────── generate from external points ────────────────────────

class TestGenerateFromPoints:
    def test_valid_points(self, sample_graph):
        pts = [
            {"latitude": 10.001, "longitude": 76.302},
            {"latitude": 10.004, "longitude": 76.312},
        ]
        cands = generate_candidates_from_points(pts, sample_graph)
        assert len(cands) == 2
        for c in cands:
            assert c.nearest_road_node is not None

    def test_invalid_point_skipped(self, sample_graph):
        pts = [
            {"latitude": 10.001, "longitude": 76.302},
            {"latitude": 999.0, "longitude": 76.302},  # invalid
            {"latitude": 10.002},                       # missing lon
        ]
        cands = generate_candidates_from_points(pts, sample_graph)
        assert len(cands) == 1


# ────────────────── filtering ────────────────────────────────────────────

class TestFilterCandidates:
    def test_feasible_candidate_passes(self):
        cand = CandidateLocation(
            candidate_id="GOOD", latitude=10.0, longitude=76.3,
            accessibility_score=0.9, land_available=0.8,
            grid_capacity=0.7, installation_cost=0.3,
            feasibility_score=0.7, road_distance_m=50.0,
        )
        result = filter_feasible_candidates([cand])
        assert len(result["feasible"]) == 1
        assert len(result["rejected"]) == 0

    def test_low_score_rejected(self):
        cand = CandidateLocation(
            candidate_id="LOW", latitude=10.0, longitude=76.3,
            accessibility_score=0.2, land_available=0.1,
            grid_capacity=0.1, installation_cost=0.9,
            feasibility_score=0.05, road_distance_m=100.0,
        )
        result = filter_feasible_candidates([cand])
        assert len(result["rejected"]) == 1
        assert "below threshold" in result["rejected"][0].rejection_reason

    def test_excessive_road_distance_rejected(self):
        cand = CandidateLocation(
            candidate_id="FAR", latitude=10.0, longitude=76.3,
            accessibility_score=0.9, land_available=0.8,
            grid_capacity=0.7, installation_cost=0.3,
            feasibility_score=0.7, road_distance_m=9999.0,
        )
        result = filter_feasible_candidates([cand], max_road_distance_m=500.0)
        assert len(result["rejected"]) == 1
        assert "excessive road distance" in result["rejected"][0].rejection_reason

    def test_insufficient_accessibility_rejected(self):
        cand = CandidateLocation(
            candidate_id="NOACC", latitude=10.0, longitude=76.3,
            accessibility_score=0.05, land_available=0.8,
            grid_capacity=0.7, installation_cost=0.3,
            feasibility_score=0.5, road_distance_m=10.0,
        )
        result = filter_feasible_candidates([cand])
        assert len(result["rejected"]) == 1
        assert "insufficient accessibility" in result["rejected"][0].rejection_reason

    def test_insufficient_land_rejected(self):
        cand = CandidateLocation(
            candidate_id="NOLAND", latitude=10.0, longitude=76.3,
            accessibility_score=0.5, land_available=0.05,
            grid_capacity=0.7, installation_cost=0.3,
            feasibility_score=0.5, road_distance_m=10.0,
        )
        result = filter_feasible_candidates([cand])
        assert len(result["rejected"]) == 1
        assert "insufficient land" in result["rejected"][0].rejection_reason

    def test_insufficient_grid_rejected(self):
        cand = CandidateLocation(
            candidate_id="NOGRID", latitude=10.0, longitude=76.3,
            accessibility_score=0.5, land_available=0.8,
            grid_capacity=0.05, installation_cost=0.3,
            feasibility_score=0.5, road_distance_m=10.0,
        )
        result = filter_feasible_candidates([cand])
        assert len(result["rejected"]) == 1
        assert "insufficient grid" in result["rejected"][0].rejection_reason

    def test_mixed_batch(self, sample_graph):
        candidates = generate_candidates_from_graph(sample_graph)
        result = filter_feasible_candidates(candidates)
        total = len(result["feasible"]) + len(result["rejected"])
        assert total == len(candidates)


# ────────────────── integration: OSM → candidates → filter ───────────────

class TestIntegrationPipeline:
    def test_full_pipeline(self, sample_graph):
        """Load sample → generate candidates → snap → filter."""
        candidates = generate_candidates_from_graph(sample_graph, data_source="sample")
        assert len(candidates) > 0

        result = filter_feasible_candidates(candidates)
        assert len(result["feasible"]) >= 0
        assert len(result["rejected"]) >= 0

        for c in result["feasible"]:
            assert c.feasible is True
            assert c.rejection_reason is None

        for c in result["rejected"]:
            assert c.feasible is False
            assert c.rejection_reason is not None

    def test_gps_snap_then_candidate(self, sample_graph):
        """GPS coord → nearest node → candidate generation."""
        from app.gis.spatial_index import snap_coordinates_to_road

        snap = snap_coordinates_to_road(sample_graph, 10.001, 76.306)
        assert snap["nearest_node"]["id"] is not None

        # Use the snapped node's coords to generate a point candidate
        pts = [{"latitude": snap["nearest_node"]["latitude"],
                "longitude": snap["nearest_node"]["longitude"]}]
        cands = generate_candidates_from_points(pts, sample_graph)
        assert len(cands) == 1
        assert cands[0].road_distance_m < 1.0  # very close to its own node
