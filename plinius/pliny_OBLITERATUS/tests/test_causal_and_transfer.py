"""Tests for causal tracing, residual stream decomposition,
probing classifiers, and cross-model transfer analysis."""

from __future__ import annotations

import math

import torch

from obliteratus.analysis.causal_tracing import (
    CausalRefusalTracer,
    CausalTracingResult,
    ComponentCausalEffect,
)
from obliteratus.analysis.residual_stream import (
    ResidualStreamDecomposer,
    ResidualStreamResult,
    LayerDecomposition,
)
from obliteratus.analysis.probing_classifiers import (
    LinearRefusalProbe,
    ProbeResult,
    ProbingSuiteResult,
)
from obliteratus.analysis.cross_model_transfer import (
    TransferAnalyzer,
    CrossModelResult,
    CrossCategoryResult,
    CrossLayerResult,
    UniversalityReport,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _make_layer_activations(
    n_layers=8, hidden_dim=32, refusal_strength=2.0,
):
    """Create synthetic per-layer activations with planted refusal signal."""
    torch.manual_seed(42)
    directions = {}
    activations = {}

    base = torch.randn(hidden_dim) * 0.1

    for i in range(n_layers):
        d = torch.randn(hidden_dim)
        d = d / d.norm()
        directions[i] = d

        # Stronger refusal in middle layers
        strength = refusal_strength if 2 <= i <= 5 else 0.3
        activations[i] = base + strength * d + torch.randn(hidden_dim) * 0.05

    return activations, directions


def _make_separable_activations(
    n_per_class=20, hidden_dim=16, separation=3.0, seed=42,
):
    """Create harmful/harmless activations that are linearly separable."""
    torch.manual_seed(seed)
    direction = torch.randn(hidden_dim)
    direction = direction / direction.norm()

    harmful = [
        torch.randn(hidden_dim) * 0.5 + separation * direction
        for _ in range(n_per_class)
    ]
    harmless = [
        torch.randn(hidden_dim) * 0.5 - separation * direction
        for _ in range(n_per_class)
    ]
    return harmful, harmless, direction


# ===========================================================================
#  Tests: Causal Tracing
# ===========================================================================

class TestCausalTracing:
    def test_basic_tracing(self):
        activations, directions = _make_layer_activations()
        tracer = CausalRefusalTracer(noise_level=3.0)
        result = tracer.trace_from_activations(activations, directions)

        assert isinstance(result, CausalTracingResult)
        assert result.n_layers == 8
        assert result.clean_refusal_strength > 0
        assert len(result.component_effects) == 8

    def test_causal_components_identified(self):
        activations, directions = _make_layer_activations()
        tracer = CausalRefusalTracer(noise_level=3.0, causal_threshold=0.05)
        result = tracer.trace_from_activations(activations, directions)

        assert result.circuit_size > 0
        assert result.circuit_fraction > 0
        assert len(result.causal_components) > 0

    def test_corruption_reduces_strength(self):
        activations, directions = _make_layer_activations(refusal_strength=5.0)
        tracer = CausalRefusalTracer(noise_level=10.0)
        result = tracer.trace_from_activations(activations, directions)

        # With high noise, corrupted should differ from clean
        assert result.total_corruption_effect != 0

    def test_single_direction_input(self):
        activations, directions = _make_layer_activations()
        single_dir = directions[3]  # Use one direction for all layers
        tracer = CausalRefusalTracer()
        result = tracer.trace_from_activations(activations, single_dir)

        assert result.n_layers == 8
        assert len(result.component_effects) == 8

    def test_component_effects_structure(self):
        activations, directions = _make_layer_activations()
        tracer = CausalRefusalTracer()
        result = tracer.trace_from_activations(activations, directions)

        for e in result.component_effects:
            assert isinstance(e, ComponentCausalEffect)
            assert e.component_type == "full_layer"
            assert e.causal_effect >= 0

    def test_correlation_causal_agreement_bounded(self):
        activations, directions = _make_layer_activations()
        tracer = CausalRefusalTracer()
        result = tracer.trace_from_activations(activations, directions)
        assert -1.0 <= result.correlation_causal_agreement <= 1.0

    def test_silent_contributors(self):
        activations, directions = _make_layer_activations()
        tracer = CausalRefusalTracer()
        result = tracer.trace_from_activations(activations, directions)
        sc = tracer.identify_silent_contributors(result, top_k=3)

        assert "silent_contributors" in sc
        assert "loud_non_contributors" in sc
        assert len(sc["silent_contributors"]) <= 3

    def test_custom_component_types(self):
        activations, directions = _make_layer_activations()
        tracer = CausalRefusalTracer()
        result = tracer.trace_from_activations(
            activations, directions,
            component_types=["attention", "mlp"],
        )
        # 8 layers * 2 types = 16 effects
        assert len(result.component_effects) == 16

    def test_format_report(self):
        activations, directions = _make_layer_activations()
        tracer = CausalRefusalTracer()
        result = tracer.trace_from_activations(activations, directions)
        report = CausalRefusalTracer.format_tracing_report(result)

        assert "Causal Tracing" in report
        assert "Circuit size" in report


# ===========================================================================
#  Tests: Residual Stream Decomposition
# ===========================================================================

class TestResidualStreamDecomposition:
    def test_basic_decomposition(self):
        activations, directions = _make_layer_activations()
        decomposer = ResidualStreamDecomposer()
        result = decomposer.decompose(activations, directions)

        assert isinstance(result, ResidualStreamResult)
        assert result.n_layers == 8
        assert len(result.per_layer) == 8
        assert result.total_attention_contribution > 0
        assert result.total_mlp_contribution > 0

    def test_attention_fraction_bounded(self):
        activations, directions = _make_layer_activations()
        decomposer = ResidualStreamDecomposer()
        result = decomposer.decompose(activations, directions)
        assert 0 <= result.attention_fraction <= 1.0

    def test_with_head_count(self):
        activations, directions = _make_layer_activations()
        decomposer = ResidualStreamDecomposer(n_heads_per_layer=4)
        result = decomposer.decompose(activations, directions)

        assert result.n_refusal_heads >= 0
        assert len(result.refusal_heads) > 0

    def test_layer_decomposition_structure(self):
        activations, directions = _make_layer_activations()
        decomposer = ResidualStreamDecomposer()
        result = decomposer.decompose(activations, directions)

        for _layer_idx, d in result.per_layer.items():
            assert isinstance(d, LayerDecomposition)
            assert 0 <= d.attn_mlp_ratio <= 1.0
            assert d.cumulative_refusal >= 0

    def test_accumulation_profile(self):
        activations, directions = _make_layer_activations()
        decomposer = ResidualStreamDecomposer()
        result = decomposer.decompose(activations, directions)

        assert len(result.accumulation_profile) == 8
        # Accumulation should be monotonically non-decreasing
        for i in range(1, len(result.accumulation_profile)):
            assert result.accumulation_profile[i] >= result.accumulation_profile[i - 1]

    def test_with_explicit_attn_mlp(self):
        """Test with provided attention and MLP outputs."""
        torch.manual_seed(42)
        hidden_dim = 16
        n_layers = 4
        ref_dir = torch.randn(hidden_dim)
        ref_dir = ref_dir / ref_dir.norm()

        acts = {}
        attn_outs = {}
        mlp_outs = {}
        for i in range(n_layers):
            attn = torch.randn(hidden_dim) * 0.5
            mlp = torch.randn(hidden_dim) * 0.5
            attn_outs[i] = attn
            mlp_outs[i] = mlp
            acts[i] = attn + mlp + (torch.randn(hidden_dim) * 0.1 if i == 0 else acts[i-1])

        decomposer = ResidualStreamDecomposer()
        result = decomposer.decompose(
            acts, ref_dir,
            attn_outputs=attn_outs, mlp_outputs=mlp_outs,
        )
        assert len(result.per_layer) == n_layers

    def test_single_direction(self):
        activations, _ = _make_layer_activations()
        single_dir = torch.randn(32)
        decomposer = ResidualStreamDecomposer()
        result = decomposer.decompose(activations, single_dir)
        assert result.n_layers == 8

    def test_head_concentration_bounded(self):
        activations, directions = _make_layer_activations()
        decomposer = ResidualStreamDecomposer(n_heads_per_layer=8)
        result = decomposer.decompose(activations, directions)
        assert 0 <= result.head_concentration <= 1.0

    def test_format_decomposition(self):
        activations, directions = _make_layer_activations()
        decomposer = ResidualStreamDecomposer(n_heads_per_layer=4)
        result = decomposer.decompose(activations, directions)
        report = ResidualStreamDecomposer.format_decomposition(result)

        assert "Residual Stream" in report
        assert "Attention" in report
        assert "MLP" in report


# ===========================================================================
#  Tests: Probing Classifiers
# ===========================================================================

class TestProbingClassifiers:
    def test_separable_data_high_accuracy(self):
        """With well-separated data, probe should achieve high accuracy."""
        harmful, harmless, direction = _make_separable_activations(
            n_per_class=30, separation=5.0,
        )
        probe = LinearRefusalProbe(n_epochs=200)
        result = probe.probe_layer(harmful, harmless, direction, layer_idx=5)

        assert isinstance(result, ProbeResult)
        assert result.layer_idx == 5
        assert result.accuracy > 0.7  # Should be separable

    def test_inseparable_data_low_accuracy(self):
        """With overlapping data, probe should have lower accuracy."""
        harmful, harmless, direction = _make_separable_activations(
            n_per_class=30, separation=0.01,
        )
        probe = LinearRefusalProbe(n_epochs=50)
        result = probe.probe_layer(harmful, harmless, direction)
        # Accuracy should be near chance (0.5)
        assert result.accuracy < 0.9

    def test_learned_direction_unit(self):
        harmful, harmless, direction = _make_separable_activations()
        probe = LinearRefusalProbe(n_epochs=100)
        result = probe.probe_layer(harmful, harmless, direction)
        assert abs(result.learned_direction.norm().item() - 1.0) < 0.01

    def test_cosine_with_analytical(self):
        """Learned direction should align with analytical direction."""
        harmful, harmless, direction = _make_separable_activations(
            n_per_class=50, separation=5.0,
        )
        probe = LinearRefusalProbe(n_epochs=300)
        result = probe.probe_layer(harmful, harmless, direction)
        # With clear separation, learned direction should agree
        assert result.cosine_with_analytical > 0.3

    def test_without_analytical_direction(self):
        harmful, harmless, _ = _make_separable_activations()
        probe = LinearRefusalProbe(n_epochs=50)
        result = probe.probe_layer(harmful, harmless)
        assert result.cosine_with_analytical == 0.0

    def test_auroc_bounded(self):
        harmful, harmless, direction = _make_separable_activations()
        probe = LinearRefusalProbe(n_epochs=100)
        result = probe.probe_layer(harmful, harmless, direction)
        assert 0 <= result.auroc <= 1.0

    def test_mutual_information_nonnegative(self):
        harmful, harmless, direction = _make_separable_activations()
        probe = LinearRefusalProbe(n_epochs=100)
        result = probe.probe_layer(harmful, harmless, direction)
        assert result.mutual_information >= 0

    def test_probe_all_layers(self):
        harmful_acts = {}
        harmless_acts = {}
        anal_dirs = {}
        for li in range(6):
            harmful, harmless, direction = _make_separable_activations(
                n_per_class=15, separation=3.0, seed=li * 10,
            )
            harmful_acts[li] = harmful
            harmless_acts[li] = harmless
            anal_dirs[li] = direction

        probe = LinearRefusalProbe(n_epochs=100)
        result = probe.probe_all_layers(harmful_acts, harmless_acts, anal_dirs)

        assert isinstance(result, ProbingSuiteResult)
        assert len(result.per_layer) == 6
        assert result.best_accuracy > 0
        assert result.total_mutual_information >= 0

    def test_format_report(self):
        harmful_acts = {}
        harmless_acts = {}
        for li in range(4):
            harmful, harmless, _ = _make_separable_activations(
                n_per_class=15, seed=li,
            )
            harmful_acts[li] = harmful
            harmless_acts[li] = harmless

        probe = LinearRefusalProbe(n_epochs=50)
        result = probe.probe_all_layers(harmful_acts, harmless_acts)
        report = LinearRefusalProbe.format_probing_report(result)

        assert "Linear Probing" in report
        assert "accuracy" in report.lower()

    def test_cross_entropy_finite(self):
        harmful, harmless, direction = _make_separable_activations()
        probe = LinearRefusalProbe(n_epochs=100)
        result = probe.probe_layer(harmful, harmless, direction)
        assert math.isfinite(result.cross_entropy)


# ===========================================================================
#  Tests: Cross-Model Transfer Analysis
# ===========================================================================

class TestTransferAnalysis:
    def test_cross_model_identical(self):
        """Identical directions should give perfect transfer."""
        torch.manual_seed(42)
        dirs = {i: torch.randn(32) for i in range(8)}
        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_model(dirs, dirs, "model_a", "model_a")

        assert isinstance(result, CrossModelResult)
        assert result.mean_transfer_score > 0.99

    def test_cross_model_random(self):
        """Random directions should give low transfer."""
        torch.manual_seed(42)
        dirs_a = {i: torch.randn(32) for i in range(8)}
        torch.manual_seed(99)
        dirs_b = {i: torch.randn(32) for i in range(8)}

        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_model(dirs_a, dirs_b, "a", "b")
        # Random 32-dim vectors have low expected cosine
        assert result.mean_transfer_score < 0.7

    def test_cross_model_structure(self):
        torch.manual_seed(42)
        dirs_a = {i: torch.randn(32) for i in range(8)}
        dirs_b = {i: torch.randn(32) for i in range(8)}
        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_model(dirs_a, dirs_b)

        assert 0 <= result.transfer_above_threshold <= 1.0
        assert len(result.per_layer_transfer) == 8

    def test_cross_category_similar(self):
        """Similar categories should cluster together."""
        torch.manual_seed(42)
        shared = torch.randn(32)
        shared = shared / shared.norm()

        cat_dirs = {}
        for cat in ["weapons", "bombs", "explosives"]:
            d = shared + 0.2 * torch.randn(32)
            cat_dirs[cat] = d / d.norm()

        # Add one very different category
        cat_dirs["fraud"] = torch.randn(32)

        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_category(cat_dirs)

        assert isinstance(result, CrossCategoryResult)
        assert result.mean_cross_category_transfer > 0
        assert len(result.categories) == 4

    def test_cross_category_specificity(self):
        torch.manual_seed(42)
        cat_dirs = {f"cat_{i}": torch.randn(16) for i in range(5)}
        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_category(cat_dirs)

        assert result.most_universal_category != ""
        assert result.most_specific_category != ""
        assert len(result.category_clusters) > 0

    def test_cross_layer(self):
        _, directions = _make_layer_activations()
        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_layer(directions)

        assert isinstance(result, CrossLayerResult)
        assert result.mean_adjacent_transfer >= 0
        assert result.transfer_decay_rate >= 0

    def test_cross_layer_adjacent_vs_distant(self):
        """Adjacent layers typically have higher transfer than distant ones."""
        torch.manual_seed(42)
        # Create directions with gradual drift
        d = torch.randn(32)
        d = d / d.norm()
        directions = {}
        for i in range(10):
            noise = torch.randn(32) * 0.1 * i
            di = d + noise
            directions[i] = di / di.norm()

        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_layer(directions)
        # Adjacent should have higher transfer than distant
        assert result.mean_adjacent_transfer >= result.mean_distant_transfer - 0.1

    def test_universality_index(self):
        torch.manual_seed(42)
        dirs = {i: torch.randn(32) for i in range(6)}

        analyzer = TransferAnalyzer()
        cross_model = analyzer.analyze_cross_model(dirs, dirs)
        cross_layer = analyzer.analyze_cross_layer(dirs)
        cat_dirs = {f"cat_{i}": torch.randn(32) for i in range(4)}
        cross_cat = analyzer.analyze_cross_category(cat_dirs)

        report = analyzer.compute_universality_index(
            cross_model=cross_model,
            cross_category=cross_cat,
            cross_layer=cross_layer,
        )

        assert isinstance(report, UniversalityReport)
        assert 0 <= report.universality_index <= 1.0

    def test_universality_empty(self):
        analyzer = TransferAnalyzer()
        report = analyzer.compute_universality_index()
        assert report.universality_index == 0.0

    def test_format_cross_model(self):
        torch.manual_seed(42)
        dirs = {i: torch.randn(32) for i in range(4)}
        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_model(dirs, dirs, "llama", "mistral")
        report = TransferAnalyzer.format_cross_model(result)
        assert "Cross-Model" in report
        assert "llama" in report

    def test_format_cross_category(self):
        torch.manual_seed(42)
        cat_dirs = {f"cat_{i}": torch.randn(16) for i in range(3)}
        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_category(cat_dirs)
        report = TransferAnalyzer.format_cross_category(result)
        assert "Cross-Category" in report

    def test_format_universality(self):
        analyzer = TransferAnalyzer()
        report_obj = analyzer.compute_universality_index()
        report = TransferAnalyzer.format_universality(report_obj)
        assert "Universality" in report

    def test_dimension_mismatch_handled(self):
        """Cross-model with different hidden dims should truncate."""
        dirs_a = {0: torch.randn(32), 1: torch.randn(32)}
        dirs_b = {0: torch.randn(64), 1: torch.randn(64)}
        analyzer = TransferAnalyzer()
        result = analyzer.analyze_cross_model(dirs_a, dirs_b)
        assert len(result.per_layer_transfer) == 2


# ===========================================================================
#  Tests: Integration
# ===========================================================================

class TestNewImports:
    def test_all_new_modules_importable(self):
        from obliteratus.analysis import (
            CausalRefusalTracer,
            ResidualStreamDecomposer,
            LinearRefusalProbe,
            TransferAnalyzer,
        )
        assert CausalRefusalTracer is not None
        assert ResidualStreamDecomposer is not None
        assert LinearRefusalProbe is not None
        assert TransferAnalyzer is not None
