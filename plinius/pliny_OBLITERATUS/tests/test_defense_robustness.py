"""Tests for defense robustness evaluation framework."""

from __future__ import annotations

from unittest.mock import MagicMock

import torch

from obliteratus.analysis.defense_robustness import (
    DefenseProfile,
    DefenseRobustnessEvaluator,
    EntanglementMap,
    SelfRepairResult,
)


def _make_mock_pipeline(n_layers=6, hidden_dim=16, n_prompts=5):
    """Create a mock pipeline with refusal directions and activations."""
    pipeline = MagicMock()
    pipeline.model_name = "test-model"

    # Generate refusal directions (some strong, some weak)
    torch.manual_seed(42)
    directions = {}
    for i in range(n_layers):
        d = torch.randn(hidden_dim)
        directions[i] = d / d.norm()
    pipeline.refusal_directions = directions

    # Generate activations with a planted refusal signal in middle layers
    harmful_means = {}
    harmless_means = {}
    harmful_acts = {}
    harmless_acts = {}

    for i in range(n_layers):
        base = torch.randn(hidden_dim)
        harmless_means[i] = base.unsqueeze(0)

        # Middle layers have stronger refusal signal
        signal_strength = 3.0 if 2 <= i <= 4 else 0.5
        harmful_means[i] = (base + signal_strength * directions[i]).unsqueeze(0)

        harmful_acts[i] = [base + signal_strength * directions[i] + torch.randn(hidden_dim) * 0.1 for _ in range(n_prompts)]
        harmless_acts[i] = [base + torch.randn(hidden_dim) * 0.1 for _ in range(n_prompts)]

    pipeline._harmful_means = harmful_means
    pipeline._harmless_means = harmless_means
    pipeline._harmful_acts = harmful_acts
    pipeline._harmless_acts = harmless_acts

    return pipeline


class TestDefenseProfile:
    def test_profile_generates(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        profile = evaluator.profile_defense()

        assert isinstance(profile, DefenseProfile)
        assert profile.model_name == "test-model"
        assert profile.refusal_layer_spread > 0
        assert profile.mean_refusal_strength > 0
        assert profile.max_refusal_strength >= profile.mean_refusal_strength
        assert profile.estimated_robustness in ("low", "medium", "high", "very_high")

    def test_alignment_type_estimate(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        profile = evaluator.profile_defense()
        assert profile.alignment_type_estimate != "unknown"

    def test_empty_pipeline(self):
        pipeline = MagicMock()
        pipeline.model_name = "empty"
        pipeline.refusal_directions = {}
        evaluator = DefenseRobustnessEvaluator(pipeline)
        profile = evaluator.profile_defense()
        assert profile.estimated_robustness == "unknown"

    def test_concentration_bounded(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        profile = evaluator.profile_defense()
        # Gini coefficient should be between 0 and 1
        assert 0 <= profile.refusal_concentration <= 1.0

    def test_self_repair_bounded(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        profile = evaluator.profile_defense()
        assert 0 <= profile.self_repair_estimate <= 1.0

    def test_format_report(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        profile = evaluator.profile_defense()
        report = DefenseRobustnessEvaluator.format_defense_profile(profile)
        assert "Defense Robustness" in report
        assert "test-model" in report


class TestSelfRepair:
    def test_self_repair_measurement(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        result = evaluator.measure_self_repair(layer_idx=3)

        assert isinstance(result, SelfRepairResult)
        assert result.layer_idx == 3
        assert result.original_refusal_strength >= 0
        assert 0 <= result.repair_ratio <= 1.0
        assert len(result.compensating_layers) > 0
        assert 3 not in result.compensating_layers  # shouldn't list itself

    def test_repair_ratio_high_for_distributed(self):
        """Distributed refusal should have high repair ratio."""
        pipeline = _make_mock_pipeline(n_layers=10)
        evaluator = DefenseRobustnessEvaluator(pipeline)
        result = evaluator.measure_self_repair(layer_idx=3)
        # With distributed signal, removing one layer leaves much compensation
        assert result.repair_ratio > 0.5

    def test_format_self_repair(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        result = evaluator.measure_self_repair(layer_idx=2)
        report = DefenseRobustnessEvaluator.format_self_repair(result)
        assert "Self-Repair" in report
        assert "Layer 2" in report


class TestEntanglement:
    def test_entanglement_map(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        emap = evaluator.map_entanglement()

        assert isinstance(emap, EntanglementMap)
        assert len(emap.layer_entanglement) > 0
        assert 0 <= emap.overall_entanglement <= 1.0
        assert len(emap.most_entangled_layers) > 0
        assert len(emap.least_entangled_layers) > 0

    def test_capability_sensitivity_keys(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        emap = evaluator.map_entanglement()

        expected_keys = {"factual_knowledge", "reasoning", "language_fluency",
                         "instruction_following", "math"}
        assert set(emap.capability_sensitivity.keys()) == expected_keys

    def test_math_most_sensitive(self):
        """Math should be estimated as the most sensitive capability."""
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        emap = evaluator.map_entanglement()
        if emap.overall_entanglement > 0:
            assert emap.capability_sensitivity["math"] >= emap.capability_sensitivity["language_fluency"]

    def test_format_entanglement(self):
        pipeline = _make_mock_pipeline()
        evaluator = DefenseRobustnessEvaluator(pipeline)
        emap = evaluator.map_entanglement()
        report = DefenseRobustnessEvaluator.format_entanglement(emap)
        assert "Entanglement" in report
        assert "math" in report
