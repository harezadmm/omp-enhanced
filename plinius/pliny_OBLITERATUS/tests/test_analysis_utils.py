"""Tests for shared analysis utilities (gini_coefficient, etc.)."""

from __future__ import annotations

import pytest

from obliteratus.analysis.utils import gini_coefficient


class TestGiniCoefficient:
    """Tests for the Gini coefficient computation."""

    def test_empty_list(self):
        assert gini_coefficient([]) == 0.0

    def test_single_value(self):
        assert gini_coefficient([42.0]) == 0.0

    def test_uniform_distribution(self):
        """All-equal values → Gini = 0."""
        assert gini_coefficient([1.0, 1.0, 1.0, 1.0]) == pytest.approx(0.0, abs=1e-10)

    def test_maximally_concentrated(self):
        """One value, rest zero → Gini ≈ 1."""
        result = gini_coefficient([100.0, 0.0, 0.0, 0.0])
        assert result > 0.7  # For n=4, max Gini = (n-1)/n = 0.75

    def test_all_zeros(self):
        assert gini_coefficient([0.0, 0.0, 0.0]) == 0.0

    def test_two_equal_values(self):
        assert gini_coefficient([5.0, 5.0]) == pytest.approx(0.0, abs=1e-10)

    def test_two_unequal_values(self):
        """[0, 10] → Gini = 0.5 for n=2."""
        result = gini_coefficient([0.0, 10.0])
        assert result == pytest.approx(0.5, abs=0.01)

    def test_moderate_inequality(self):
        """Moderate spread → Gini between 0 and 1."""
        result = gini_coefficient([1.0, 2.0, 3.0, 4.0, 5.0])
        assert 0.1 < result < 0.5

    def test_result_in_valid_range(self):
        """Gini is always in [0, 1]."""
        for vals in [[1, 2, 3], [0, 0, 100], [5, 5, 5], [1], [0.1, 0.9]]:
            result = gini_coefficient(vals)
            assert 0.0 <= result <= 1.0, f"Gini({vals}) = {result} out of range"

    def test_large_uniform(self):
        """Large uniform distribution → Gini ≈ 0."""
        vals = [1.0] * 1000
        assert gini_coefficient(vals) == pytest.approx(0.0, abs=1e-10)

    def test_large_concentrated(self):
        """Large distribution with one outlier → high Gini."""
        vals = [0.0] * 999 + [1000.0]
        result = gini_coefficient(vals)
        assert result > 0.99

    def test_order_invariant(self):
        """Gini should not depend on input order."""
        a = gini_coefficient([1.0, 3.0, 5.0, 7.0])
        b = gini_coefficient([7.0, 1.0, 5.0, 3.0])
        assert a == pytest.approx(b)
