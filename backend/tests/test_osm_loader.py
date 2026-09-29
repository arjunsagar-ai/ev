"""Tests for OSM road-network loader, caching, and sample fallback."""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.gis.osm_loader import (
    _bbox_cache_key,
    _build_graph_from_osm,
    _build_overpass_query,
    build_sample_road_network,
    load_cached_network,
    load_osm_network,
    save_cached_network,
)
from app.graph.weighted_graph import WeightedGraph


# ────────────────── fixtures ─────────────────────────────────────────────

@pytest.fixture
def minimal_osm_data() -> dict:
    """
    Minimal Overpass-style JSON with 3 nodes and 1 way so we can test
    the graph-building pipeline without network access.
    """
    return {
        "elements": [
            {"type": "node", "id": 100, "lat": 10.0, "lon": 76.3},
            {"type": "node", "id": 200, "lat": 10.001, "lon": 76.301},
            {"type": "node", "id": 300, "lat": 10.002, "lon": 76.302},
            {
                "type": "way",
                "id": 9000,
                "nodes": [100, 200, 300],
                "tags": {"highway": "residential", "name": "Test Road"},
            },
        ]
    }


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Provide a temporary cache directory."""
    d = tmp_path / "osm_cache"
    d.mkdir()
    return str(d)


# ────────────────── cache key ────────────────────────────────────────────

class TestCacheKey:
    def test_deterministic(self):
        k1 = _bbox_cache_key(10.0, 9.0, 77.0, 76.0)
        k2 = _bbox_cache_key(10.0, 9.0, 77.0, 76.0)
        assert k1 == k2

    def test_different_bbox_different_key(self):
        k1 = _bbox_cache_key(10.0, 9.0, 77.0, 76.0)
        k2 = _bbox_cache_key(11.0, 9.0, 77.0, 76.0)
        assert k1 != k2


# ────────────────── save / load cache ────────────────────────────────────

class TestCacheIO:
    def test_save_and_load(self, tmp_cache_dir, minimal_osm_data):
        path = os.path.join(tmp_cache_dir, "test.json")
        save_cached_network(path, minimal_osm_data)
        loaded = load_cached_network(path)
        assert loaded is not None
        assert loaded["elements"][0]["id"] == 100

    def test_load_missing_file_returns_none(self, tmp_cache_dir):
        path = os.path.join(tmp_cache_dir, "missing.json")
        assert load_cached_network(path) is None


# ────────────────── graph construction from OSM ──────────────────────────

class TestBuildGraphFromOSM:
    def test_basic_graph(self, minimal_osm_data):
        g = _build_graph_from_osm(minimal_osm_data)
        assert isinstance(g, WeightedGraph)
        assert g.num_nodes() == 3
        assert g.num_edges() == 2  # undirected: 100-200, 200-300
        assert g.has_edge(100, 200)
        assert g.has_edge(200, 300)

    def test_coordinates_preserved(self, minimal_osm_data):
        g = _build_graph_from_osm(minimal_osm_data)
        coords = g.get_coordinates(100)
        assert coords == (10.0, 76.3)

    def test_empty_osm_data(self):
        g = _build_graph_from_osm({"elements": []})
        assert g.num_nodes() == 0
        assert g.num_edges() == 0


# ────────────────── sample network ───────────────────────────────────────

class TestSampleNetwork:
    def test_sample_has_correct_shape(self):
        g, source = build_sample_road_network()
        assert source == "sample"
        assert g.num_nodes() == 15
        assert g.num_edges() == 20

    def test_sample_nodes_have_coordinates(self):
        g, _ = build_sample_road_network()
        for nid in g.nodes():
            assert g.get_coordinates(nid) is not None

    def test_sample_has_alternative_routes(self):
        """N01 → N07 is reachable via N01-N02-N07 and N01-N06-N07."""
        g, _ = build_sample_road_network()
        assert g.has_edge("N01", "N02")
        assert g.has_edge("N02", "N07")
        assert g.has_edge("N01", "N06")
        assert g.has_edge("N06", "N07")


# ────────────────── load_osm_network ─────────────────────────────────────

class TestLoadOSMNetwork:
    def test_invalid_bbox_raises(self):
        with pytest.raises(ValueError, match="south .* must be less than north"):
            load_osm_network(north=9.0, south=10.0, east=77.0, west=76.0)

    def test_invalid_bbox_east_west(self):
        with pytest.raises(ValueError, match="west .* must be less than east"):
            load_osm_network(north=10.0, south=9.0, east=76.0, west=77.0)

    def test_loads_from_cache(self, tmp_cache_dir, minimal_osm_data):
        """If cache file exists, it should be used (data_source='cache')."""
        # Pre-populate cache
        key = _bbox_cache_key(10.003, 9.999, 76.303, 76.299)
        path = os.path.join(tmp_cache_dir, key)
        save_cached_network(path, minimal_osm_data)

        graph, meta = load_osm_network(
            north=10.003, south=9.999, east=76.303, west=76.299,
            cache_dir=tmp_cache_dir,
        )
        assert meta.data_source == "cache"
        assert graph.num_nodes() == 3

    def test_fallback_to_sample_without_internet(self, tmp_cache_dir):
        """With no cache and no internet, the sample network should be returned."""
        import requests
        with patch("requests.post", side_effect=requests.ConnectionError("offline")):
            graph, meta = load_osm_network(
                north=10.003, south=9.999, east=76.303, west=76.299,
                cache_dir=tmp_cache_dir,
            )
            assert meta.data_source == "sample"
            assert graph.num_nodes() == 15  # sample network


# ────────────────── Overpass query builder ────────────────────────────────

class TestOverpassQuery:
    def test_query_contains_bbox(self):
        q = _build_overpass_query(10.0, 9.0, 77.0, 76.0)
        assert "9.0,76.0,10.0,77.0" in q.replace(" ", "").replace("\n", "")

    def test_query_contains_highway_filter(self):
        q = _build_overpass_query(10.0, 9.0, 77.0, 76.0, highway_types=["primary"])
        assert "primary" in q


# ────────────────── HTTP headers and retry (Phase 7) ─────────────────────

class TestOverpassReliability:
    """Verify HTTP headers, retry logic, and error handling in _download_osm_data."""

    def test_download_sends_proper_headers(self, tmp_cache_dir, minimal_osm_data):
        """Overpass request should include User-Agent and Accept headers."""
        import requests
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = minimal_osm_data
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_resp) as mock_post:
            from app.gis.osm_loader import _download_osm_data
            _download_osm_data(10.003, 9.999, 76.303, 76.299)

            call_kwargs = mock_post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
            assert "User-Agent" in headers
            assert "EVChargingOptimizer" in headers["User-Agent"]
            assert headers.get("Accept") == "application/json"

    def test_download_retries_on_429(self, minimal_osm_data):
        """HTTP 429 should trigger retry, not immediate failure."""
        import requests

        mock_429 = MagicMock()
        mock_429.status_code = 429

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = minimal_osm_data
        mock_200.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_429, mock_200]):
            with patch("app.gis.osm_loader.time.sleep"):  # skip real delays
                from app.gis.osm_loader import _download_osm_data
                result = _download_osm_data(10.003, 9.999, 76.303, 76.299)
                assert "elements" in result

    def test_download_retries_on_500(self, minimal_osm_data):
        """HTTP 5xx should trigger retry."""
        import requests

        mock_500 = MagicMock()
        mock_500.status_code = 500

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = minimal_osm_data
        mock_200.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_500, mock_200]):
            with patch("app.gis.osm_loader.time.sleep"):
                from app.gis.osm_loader import _download_osm_data
                result = _download_osm_data(10.003, 9.999, 76.303, 76.299)
                assert "elements" in result

    def test_download_raises_on_406(self, minimal_osm_data):
        """HTTP 406 should raise immediately (not retried)."""
        import requests

        mock_406 = MagicMock()
        mock_406.status_code = 406
        mock_406.raise_for_status.side_effect = requests.HTTPError("406 Client Error")

        with patch("requests.post", return_value=mock_406):
            from app.gis.osm_loader import _download_osm_data
            with pytest.raises(requests.HTTPError):
                _download_osm_data(10.003, 9.999, 76.303, 76.299)

    def test_download_retries_on_connection_error(self, minimal_osm_data):
        """ConnectionError should trigger retry."""
        import requests

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = minimal_osm_data
        mock_200.raise_for_status = MagicMock()

        with patch("requests.post",
                    side_effect=[requests.ConnectionError("refused"), mock_200]):
            with patch("app.gis.osm_loader.time.sleep"):
                from app.gis.osm_loader import _download_osm_data
                result = _download_osm_data(10.003, 9.999, 76.303, 76.299)
                assert "elements" in result

    def test_configurable_overpass_url(self, minimal_osm_data):
        """OVERPASS_URL env var should control the endpoint used."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = minimal_osm_data
        mock_resp.raise_for_status = MagicMock()

        custom_url = "https://overpass.kumi.systems/api/interpreter"
        with patch("app.gis.osm_loader.settings") as mock_settings:
            mock_settings.OVERPASS_API_URL = custom_url
            mock_settings.OSM_HIGHWAY_TYPES = ["primary", "secondary"]

            with patch("requests.post", return_value=mock_resp) as mock_post:
                from app.gis.osm_loader import _download_osm_data
                _download_osm_data(10.003, 9.999, 76.303, 76.299)
                call_args = mock_post.call_args
                assert call_args[0][0] == custom_url or call_args.kwargs.get("url") == custom_url
