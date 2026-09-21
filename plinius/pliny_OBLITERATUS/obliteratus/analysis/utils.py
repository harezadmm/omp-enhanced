"""Shared utilities for analysis modules."""

from __future__ import annotations


def gini_coefficient(values: list[float]) -> float:
    """Compute Gini coefficient of a distribution.

    Returns a value in [0, 1] where 0 = perfectly uniform and 1 = maximally concentrated.
    """
    if not values or sum(values) == 0:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    cumulative = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(sorted_vals))
    return max(0.0, min(1.0, cumulative / (n * sum(sorted_vals))))
