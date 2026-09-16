"""Unit tests for Kuhn-Munkres (Hungarian) Algorithm."""
import numpy as np
import pytest
from app.algorithms.hungarian import hungarian_algorithm


class TestHungarianAlgorithm:
    """Ground-truth tests for Kuhn-Munkres optimal bipartite matching."""

    def test_known_3x3_cost_matrix(self):
        """
        Matrix:
            [4, 1, 3]
            [2, 0, 5]
            [3, 2, 2]
        Optimal matching:
            (0, 1) -> 1
            (1, 0) -> 2
            (2, 2) -> 2
        Total minimum cost: 1 + 2 + 2 = 5.0
        """
        cost_matrix = [
            [4, 1, 3],
            [2, 0, 5],
            [3, 2, 2]
        ]
        res = hungarian_algorithm(cost_matrix)

        assert res["total_cost"] == 5.0
        assert res["assignments"] == [(0, 1), (1, 0), (2, 2)]

    def test_known_4x4_cost_matrix(self):
        """
        Matrix:
            [9, 2, 7, 8]
            [6, 4, 3, 7]
            [5, 8, 1, 8]
            [7, 6, 9, 4]
        Optimal matching:
            (0, 1) -> 2
            (1, 0) -> 6
            (2, 2) -> 1
            (3, 3) -> 4
        Total minimum cost: 2 + 6 + 1 + 4 = 13.0
        """
        cost_matrix = np.array([
            [9, 2, 7, 8],
            [6, 4, 3, 7],
            [5, 8, 1, 8],
            [7, 6, 9, 4]
        ])
        res = hungarian_algorithm(cost_matrix)

        assert res["total_cost"] == 13.0
        assert res["assignments"] == [(0, 1), (1, 0), (2, 2), (3, 3)]

    def test_rectangular_matrix_more_columns_than_rows(self):
        """
        2 EVs requesting 3 charging stations:
            [10,  5, 20]
            [ 8, 12, 15]
        Optimal:
            EV 0 -> Station 1 (cost 5)
            EV 1 -> Station 0 (cost 8)
        Total cost: 13.0
        """
        cost_matrix = [
            [10, 5, 20],
            [8, 12, 15]
        ]
        res = hungarian_algorithm(cost_matrix)

        assert res["total_cost"] == 13.0
        assert res["assignments"] == [(0, 1), (1, 0)]

    def test_rectangular_matrix_more_rows_than_columns(self):
        """
        3 EVs competing for 2 charging stations:
            [10,  5]
            [ 8, 12]
            [15, 15]
        Optimal assignment to the 2 stations:
            EV 0 -> Station 1 (5)
            EV 1 -> Station 0 (8)
        Total cost: 13.0
        """
        cost_matrix = [
            [10, 5],
            [8, 12],
            [15, 15]
        ]
        res = hungarian_algorithm(cost_matrix)

        assert res["total_cost"] == 13.0
        assert len(res["assignments"]) == 2
        assert res["assignments"] == [(0, 1), (1, 0)]

    def test_matrix_with_negative_values(self):
        """
        Matrix with negative values:
            [-1, -2]
            [-3, -4]
        Min sum:
            (0, 0) -> -1, (1, 1) -> -4 => -5.0
            or (0, 1) -> -2, (1, 0) -> -3 => -5.0
        """
        cost_matrix = np.array([
            [-1, -2],
            [-3, -4]
        ])
        res = hungarian_algorithm(cost_matrix)
        assert res["total_cost"] == -5.0
        assert len(res["assignments"]) == 2

    def test_single_element_matrix(self):
        res = hungarian_algorithm([[42.0]])
        assert res["assignments"] == [(0, 0)]
        assert res["total_cost"] == 42.0

    def test_empty_matrix(self):
        res = hungarian_algorithm([])
        assert res["assignments"] == []
        assert res["total_cost"] == 0.0

    def test_invalid_dimensions_raises_error(self):
        with pytest.raises(ValueError, match="must be 2-dimensional"):
            hungarian_algorithm([1, 2, 3])

    def test_nan_or_inf_raises_error(self):
        with pytest.raises(ValueError, match="cannot contain NaN or Inf"):
            hungarian_algorithm([[1.0, float("nan")], [2.0, 3.0]])
