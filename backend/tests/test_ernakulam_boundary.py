"""
Unit tests for Ernakulam District boundary containment and validation.
"""
import pytest
from app.gis.ernakulam_boundary import (
    ERNAKULAM_COVERAGE_MESSAGE,
    get_ernakulam_boundary_geojson,
    is_point_in_ernakulam,
    validate_in_ernakulam,
)


class TestErnakulamBoundary:
    """Validate spatial containment of points against Ernakulam District boundary."""

    @pytest.mark.parametrize(
        "location_name,latitude,longitude",
        [
            ("Kochi", 9.9816, 76.2999),
            ("Aluva", 10.1076, 76.3516),
            ("Angamaly", 10.1960, 76.3860),
            ("Perumbavoor", 10.1118, 76.4756),
            ("Muvattupuzha", 9.9894, 76.5790),
            ("Kothamangalam", 10.0614, 76.6239),
            ("North Paravur", 10.1472, 76.2292),
            ("Kakkanad", 10.0159, 76.3419),
            ("Vyttila", 9.9678, 76.3183),
            ("Piravom", 9.8732, 76.4925),
        ],
    )
    def test_locations_inside_ernakulam_accepted(self, location_name, latitude, longitude):
        assert is_point_in_ernakulam(latitude, longitude) is True
        # validate_in_ernakulam should not raise
        validate_in_ernakulam(latitude, longitude)

    @pytest.mark.parametrize(
        "location_name,latitude,longitude",
        [
            ("Kollam", 8.8932, 76.6141),
            ("Thrissur", 10.5276, 76.2144),
            ("Kottayam", 9.5916, 76.5222),
            ("Thiruvananthapuram", 8.5241, 76.9366),
            ("Kozhikode", 11.2588, 75.7804),
            ("Palakkad", 10.7867, 76.6548),
            ("Hyderabad", 17.3850, 78.4867),
            ("Bengaluru", 12.9716, 77.5946),
            ("Mumbai", 19.0760, 72.8777),
        ],
    )
    def test_locations_outside_ernakulam_rejected(self, location_name, latitude, longitude):
        assert is_point_in_ernakulam(latitude, longitude) is False
        with pytest.raises(ValueError) as exc_info:
            validate_in_ernakulam(latitude, longitude)
        assert ERNAKULAM_COVERAGE_MESSAGE in str(exc_info.value)

    def test_boundary_geojson_retrieval(self):
        geojson = get_ernakulam_boundary_geojson()
        assert isinstance(geojson, dict)
        assert "geometry" in geojson or "type" in geojson
