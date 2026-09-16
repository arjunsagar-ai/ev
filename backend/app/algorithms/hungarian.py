"""Kuhn-Munkres (Hungarian) Algorithm from scratch for optimal bipartite matching."""
from typing import Any, Dict, List, Sequence, Tuple, Union
import numpy as np


def hungarian_algorithm(
    cost_matrix: Union[Sequence[Sequence[float]], np.ndarray]
) -> Dict[str, Any]:
    """
    Solve the linear sum assignment (minimum weight bipartite matching) problem
    using the Kuhn-Munkres (Hungarian) algorithm from scratch.

    Supports:
        - NumPy arrays or nested Python lists
        - Square matrices (N x N)
        - Rectangular matrices (N x M, where N != M)
        - Matrices with positive, zero, or negative weights

    Parameters:
        cost_matrix: 2D array-like of shape (N, M) representing assignment costs
                     (e.g., EV requests as rows, charging station slots as columns).

    Returns:
        Dict[str, Any]: Structured result containing:
            - 'assignments': List of tuples (row_idx, col_idx) representing optimal pairs.
            - 'total_cost': The minimum total sum of assignment costs.

    Raises:
        ValueError: If cost_matrix is not 2-dimensional or contains NaN / Inf values.
    """
    # Handle empty matrix or empty sequence
    if not hasattr(cost_matrix, "__len__") or len(cost_matrix) == 0:
        return {"assignments": [], "total_cost": 0.0}

    # Convert input to float NumPy array
    try:
        matrix = np.array(cost_matrix, dtype=float)
    except Exception as e:
        raise ValueError(f"Could not convert input to numeric matrix: {e}")

    if matrix.size == 0 or matrix.ndim == 0:
        return {"assignments": [], "total_cost": 0.0}

    if matrix.ndim != 2:
        raise ValueError(f"Cost matrix must be 2-dimensional, got {matrix.ndim}D.")

    num_rows, num_cols = matrix.shape

    # Handle empty matrix
    if num_rows == 0 or num_cols == 0:
        return {"assignments": [], "total_cost": 0.0}

    if np.isnan(matrix).any() or np.isinf(matrix).any():
        raise ValueError("Cost matrix cannot contain NaN or Inf values.")

    original_matrix = matrix.copy()

    # Step 0: Ensure all values are non-negative for standard Munkres
    min_val = np.min(matrix)
    if min_val < 0:
        matrix = matrix - min_val

    # Handle rectangular matrices by padding with zeros to make it K x K
    k = max(num_rows, num_cols)
    square_matrix = np.zeros((k, k), dtype=float)
    square_matrix[:num_rows, :num_cols] = matrix

    # Run Munkres on the K x K non-negative square matrix
    starred_zeros = _munkres_solve(square_matrix)

    # Filter out dummy rows and dummy columns
    assignments: List[Tuple[int, int]] = []
    total_cost: float = 0.0

    for r, c in starred_zeros:
        if r < num_rows and c < num_cols:
            assignments.append((r, c))
            total_cost += float(original_matrix[r, c])

    # Sort assignments by row index for deterministic results
    assignments.sort(key=lambda x: x[0])

    return {
        "assignments": assignments,
        "total_cost": round(total_cost, 6),
    }


def _munkres_solve(cost: np.ndarray) -> List[Tuple[int, int]]:
    """
    Core Munkres state machine algorithm for a K x K non-negative matrix.
    """
    n = cost.shape[0]
    c = cost.copy()

    # Step 1: Subtract row minimum from each row
    for r in range(n):
        c[r, :] -= np.min(c[r, :])

    # Step 2: Subtract column minimum from each column
    for col in range(n):
        c[:, col] -= np.min(c[:, col])

    # Masks: 0 = normal, 1 = starred (*), 2 = primed (')
    marked = np.zeros((n, n), dtype=int)
    row_covered = np.zeros(n, dtype=bool)
    col_covered = np.zeros(n, dtype=bool)

    # Step 3: Initial greedy starring of zeros
    for r in range(n):
        for col in range(n):
            if c[r, col] == 0 and not row_covered[r] and not col_covered[col]:
                marked[r, col] = 1
                row_covered[r] = True
                col_covered[col] = True

    row_covered[:] = False
    col_covered[:] = False

    def cover_starred_columns() -> int:
        col_covered[:] = False
        for col in range(n):
            if np.any(marked[:, col] == 1):
                col_covered[col] = True
        return int(np.sum(col_covered))

    def find_uncovered_zero() -> Tuple[int, int]:
        for r in range(n):
            if not row_covered[r]:
                for col in range(n):
                    if not col_covered[col] and c[r, col] == 0:
                        return (r, col)
        return (-1, -1)

    while True:
        # Step 4: Cover columns containing starred zeros
        covered_count = cover_starred_columns()
        if covered_count >= n:
            break

        # Step 5: Prime uncovered zeros
        while True:
            r, col = find_uncovered_zero()
            if r == -1:
                # No uncovered zeros left: find smallest uncovered element
                uncovered_vals = [
                    c[i, j]
                    for i in range(n) if not row_covered[i]
                    for j in range(n) if not col_covered[j]
                ]
                if not uncovered_vals:
                    break
                h = min(uncovered_vals)

                # Add h to covered rows, subtract h from uncovered cols
                for i in range(n):
                    if row_covered[i]:
                        c[i, :] += h
                for j in range(n):
                    if not col_covered[j]:
                        c[:, j] -= h
                continue

            marked[r, col] = 2  # Prime the zero

            # Check if there is a starred zero in row r
            starred_in_row = np.where(marked[r, :] == 1)[0]
            if len(starred_in_row) > 0:
                star_col = starred_in_row[0]
                row_covered[r] = True
                col_covered[star_col] = False
            else:
                # Step 6: Alternating path starting from uncovered primed zero (r, col)
                path = [(r, col)]
                while True:
                    cur_r, cur_c = path[-1]
                    # Find starred zero in the same column
                    star_row = np.where(marked[:, cur_c] == 1)[0]
                    if len(star_row) == 0:
                        break
                    path.append((star_row[0], cur_c))

                    # Find primed zero in the same row
                    prime_col = np.where(marked[star_row[0], :] == 2)[0][0]
                    path.append((star_row[0], prime_col))

                # Unstar each starred zero in path, star each primed zero
                for pr_r, pr_c in path:
                    if marked[pr_r, pr_c] == 1:
                        marked[pr_r, pr_c] = 0
                    elif marked[pr_r, pr_c] == 2:
                        marked[pr_r, pr_c] = 1

                # Clear all primes and covers
                marked[marked == 2] = 0
                row_covered[:] = False
                col_covered[:] = False
                break

    # Extract all starred zeros
    starred_positions = []
    for r in range(n):
        for col in range(n):
            if marked[r, col] == 1:
                starred_positions.append((r, col))

    return starred_positions
