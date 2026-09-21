"""Tests for analysis techniques: concept cones, alignment imprints,
multi-token position, and sparse direction surgery."""

from __future__ import annotations


import torch

from obliteratus.analysis.concept_geometry import (
    ConceptConeAnalyzer,
    ConeConeResult,
    MultiLayerConeResult,
    CategoryDirection,
    DEFAULT_HARM_CATEGORIES,
)
from obliteratus.analysis.alignment_imprint import (
    AlignmentImprintDetector,
    AlignmentImprint,
    BaseInstructDelta,
)
from obliteratus.analysis.multi_token_position import (
    MultiTokenPositionAnalyzer,
    PositionAnalysisResult,
    MultiTokenSummary,
)
from obliteratus.analysis.sparse_surgery import (
    SparseDirectionSurgeon,
    SparseProjectionResult,
    SparseSurgeryPlan,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _make_category_activations(
    hidden_dim=32, n_prompts=30, n_categories=5, category_spread=0.3,
):
    """Create synthetic activations with planted per-category refusal directions.

    Each category gets its own refusal direction, with some shared component
    to simulate a polyhedral cone structure.
    """
    torch.manual_seed(42)

    # Shared refusal component
    shared = torch.randn(hidden_dim)
    shared = shared / shared.norm()

    # Per-category unique components
    cat_dirs = {}
    categories = [f"cat_{i}" for i in range(n_categories)]
    for cat in categories:
        unique = torch.randn(hidden_dim)
        unique = unique / unique.norm()
        combined = shared + category_spread * unique
        cat_dirs[cat] = combined / combined.norm()

    # Assign prompts to categories
    prompts_per_cat = n_prompts // n_categories
    category_map = {}
    for i, cat in enumerate(categories):
        for j in range(prompts_per_cat):
            category_map[i * prompts_per_cat + j] = cat

    actual_n = prompts_per_cat * n_categories

    # Generate activations
    harmful_acts = []
    harmless_acts = []
    for idx in range(actual_n):
        cat = category_map[idx]
        base = torch.randn(hidden_dim) * 0.1
        harmful_acts.append(base + 2.0 * cat_dirs[cat])
        harmless_acts.append(base)

    return harmful_acts, harmless_acts, category_map, cat_dirs


def _make_refusal_directions(n_layers=8, hidden_dim=32, concentration="distributed"):
    """Create synthetic refusal directions with specified concentration pattern."""
    torch.manual_seed(123)
    directions = {}
    strengths = {}

    for i in range(n_layers):
        d = torch.randn(hidden_dim)
        directions[i] = d / d.norm()

        if concentration == "concentrated":
            # Strong in last few layers only (SFT-like)
            strengths[i] = 3.0 if i >= n_layers - 2 else 0.1
        elif concentration == "distributed":
            # Even across layers (RLHF-like)
            strengths[i] = 1.0 + 0.2 * torch.randn(1).item()
        elif concentration == "orthogonal":
            # Each layer direction is more orthogonal (CAI-like)
            if i > 0:
                # Make each direction more orthogonal to previous
                prev = directions[i - 1]
                d = d - (d @ prev) * prev
                d = d / d.norm().clamp(min=1e-8)
                directions[i] = d
            strengths[i] = 1.5
        else:
            strengths[i] = 2.0 if 2 <= i <= 4 else 0.5

    return directions, strengths


# ===========================================================================
#  Tests: Concept Cone Geometry
# ===========================================================================

class TestConceptConeAnalyzer:
    def test_basic_analysis(self):
        harmful, harmless, cat_map, _ = _make_category_activations()
        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_layer(harmful, harmless, layer_idx=5)

        assert isinstance(result, ConeConeResult)
        assert result.layer_idx == 5
        assert result.category_count >= 2
        assert result.cone_dimensionality > 0
        assert result.cone_solid_angle >= 0
        assert 0 <= result.mean_pairwise_cosine <= 1.0

    def test_polyhedral_detection(self):
        """With spread-out categories, should detect polyhedral geometry."""
        harmful, harmless, cat_map, _ = _make_category_activations(
            category_spread=2.0,  # Large spread -> distinct directions
        )
        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_layer(harmful, harmless)
        # With high spread, directions should be more distinct
        assert result.cone_dimensionality > 1.0

    def test_linear_detection(self):
        """With no spread, should detect linear (single direction) geometry."""
        harmful, harmless, cat_map, _ = _make_category_activations(
            category_spread=0.0,  # No spread -> all directions aligned
        )
        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_layer(harmful, harmless)
        assert result.mean_pairwise_cosine > 0.8

    def test_category_directions_populated(self):
        harmful, harmless, cat_map, _ = _make_category_activations()
        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_layer(harmful, harmless)

        for cd in result.category_directions:
            assert isinstance(cd, CategoryDirection)
            assert cd.strength > 0
            assert cd.n_prompts >= 2
            assert 0 <= cd.specificity <= 1.0

    def test_pairwise_cosines(self):
        harmful, harmless, cat_map, _ = _make_category_activations()
        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_layer(harmful, harmless)

        for (a, b), cos in result.pairwise_cosines.items():
            assert 0 <= cos <= 1.0
            assert a < b  # Sorted pair

    def test_general_direction_unit(self):
        harmful, harmless, cat_map, _ = _make_category_activations()
        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_layer(harmful, harmless)
        assert abs(result.general_direction.norm().item() - 1.0) < 0.01

    def test_multi_layer_analysis(self):
        harmful, harmless, cat_map, _ = _make_category_activations()
        harmful_by_layer = {i: harmful for i in range(4)}
        harmless_by_layer = {i: harmless for i in range(4)}

        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_all_layers(harmful_by_layer, harmless_by_layer)

        assert isinstance(result, MultiLayerConeResult)
        assert len(result.per_layer) == 4
        assert result.mean_cone_dimensionality > 0

    def test_format_report(self):
        harmful, harmless, cat_map, _ = _make_category_activations()
        analyzer = ConceptConeAnalyzer(category_map=cat_map)
        result = analyzer.analyze_layer(harmful, harmless, layer_idx=3)
        report = ConceptConeAnalyzer.format_report(result)

        assert "Concept Cone" in report
        assert "Layer 3" in report
        assert "dimensionality" in report

    def test_default_category_map(self):
        assert len(DEFAULT_HARM_CATEGORIES) == 30
        cats = set(DEFAULT_HARM_CATEGORIES.values())
        assert "weapons" in cats
        assert "cyber" in cats

    def test_empty_activations(self):
        analyzer = ConceptConeAnalyzer()
        result = analyzer.analyze_layer([], [], layer_idx=0)
        assert result.category_count == 0

    def test_min_category_size(self):
        """Categories with too few prompts should be excluded."""
        harmful, harmless, cat_map, _ = _make_category_activations(
            n_prompts=10, n_categories=5,
        )
        analyzer = ConceptConeAnalyzer(category_map=cat_map, min_category_size=3)
        result = analyzer.analyze_layer(harmful, harmless)
        # Each category has only 2 prompts, so with min_size=3 all are excluded
        assert result.category_count == 0


# ===========================================================================
#  Tests: Alignment Imprint Detector
# ===========================================================================

class TestAlignmentImprintDetector:
    def test_basic_detection(self):
        directions, strengths = _make_refusal_directions()
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)

        assert isinstance(imprint, AlignmentImprint)
        assert imprint.predicted_method in ("dpo", "rlhf", "cai", "sft")
        assert 0 <= imprint.confidence <= 1.0

    def test_probabilities_sum_to_one(self):
        directions, strengths = _make_refusal_directions()
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)

        total = (imprint.dpo_probability + imprint.rlhf_probability +
                 imprint.cai_probability + imprint.sft_probability)
        assert abs(total - 1.0) < 0.01

    def test_concentrated_detects_sft_or_dpo(self):
        """Concentrated refusal (tail-biased) should predict SFT or DPO."""
        directions, strengths = _make_refusal_directions(concentration="concentrated")
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)
        # SFT and DPO both have concentrated signatures
        assert imprint.predicted_method in ("sft", "dpo")

    def test_distributed_detects_not_sft(self):
        """Distributed refusal should not be predicted as SFT."""
        directions, strengths = _make_refusal_directions(
            n_layers=16, concentration="distributed",
        )
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)
        # With distributed refusal, Gini is low -> SFT is unlikely to be top prediction
        assert imprint.predicted_method != "sft"

    def test_orthogonal_detects_cai(self):
        """Orthogonal layer directions should lean toward CAI."""
        directions, strengths = _make_refusal_directions(
            n_layers=12, concentration="orthogonal",
        )
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)
        # CAI should rank highly due to orthogonality
        assert imprint.cai_probability > 0.15

    def test_feature_extraction(self):
        directions, strengths = _make_refusal_directions()
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)

        assert 0 <= imprint.gini_coefficient <= 1.0
        assert imprint.effective_rank > 0
        assert 0 <= imprint.cross_layer_smoothness <= 1.0
        assert 0 <= imprint.tail_layer_bias <= 1.0
        assert 0 <= imprint.mean_pairwise_orthogonality <= 1.0
        assert imprint.spectral_decay_rate >= 0

    def test_empty_directions(self):
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint({})
        assert imprint.predicted_method == "unknown"
        assert imprint.confidence == 0.0

    def test_compare_base_instruct(self):
        torch.manual_seed(42)
        hidden_dim = 32
        directions, _ = _make_refusal_directions(hidden_dim=hidden_dim)

        base_acts = {i: torch.randn(hidden_dim) for i in range(8)}
        instruct_acts = {
            i: base_acts[i] + 1.5 * directions[i] for i in range(8)
        }

        detector = AlignmentImprintDetector()
        deltas = detector.compare_base_instruct(base_acts, instruct_acts, directions)

        assert len(deltas) == 8
        for d in deltas:
            assert isinstance(d, BaseInstructDelta)
            assert d.delta_magnitude > 0
            # Since delta IS the refusal direction, cosine should be high
            assert abs(d.cosine_with_refusal) > 0.5

    def test_format_imprint(self):
        directions, strengths = _make_refusal_directions()
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)
        report = AlignmentImprintDetector.format_imprint(imprint)

        assert "Alignment Imprint" in report
        assert "DPO" in report
        assert "RLHF" in report
        assert "Gini" in report

    def test_per_layer_strength_populated(self):
        directions, strengths = _make_refusal_directions()
        detector = AlignmentImprintDetector()
        imprint = detector.detect_imprint(directions, strengths)
        assert len(imprint.per_layer_strength) == len(directions)


# ===========================================================================
#  Tests: Multi-Token Position Analysis
# ===========================================================================

class TestMultiTokenPositionAnalyzer:
    def _make_activations_with_trigger(
        self, seq_len=20, hidden_dim=32, trigger_pos=5,
    ):
        """Create activations with a planted trigger at a specific position."""
        torch.manual_seed(42)
        refusal_dir = torch.randn(hidden_dim)
        refusal_dir = refusal_dir / refusal_dir.norm()

        # Background activations
        acts = torch.randn(seq_len, hidden_dim) * 0.1

        # Strong refusal at trigger position
        acts[trigger_pos] += 3.0 * refusal_dir

        # Weaker refusal at last position
        acts[-1] += 1.0 * refusal_dir

        # Moderate at a few positions after trigger (decay)
        for i in range(trigger_pos + 1, min(trigger_pos + 4, seq_len)):
            decay = 0.5 ** (i - trigger_pos)
            acts[i] += 3.0 * decay * refusal_dir

        return acts, refusal_dir

    def test_basic_analysis(self):
        acts, ref_dir = self._make_activations_with_trigger()
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir, layer_idx=3)

        assert isinstance(result, PositionAnalysisResult)
        assert result.layer_idx == 3
        assert result.n_tokens == 20
        assert result.peak_strength > 0

    def test_trigger_detection(self):
        acts, ref_dir = self._make_activations_with_trigger(trigger_pos=5)
        analyzer = MultiTokenPositionAnalyzer(trigger_threshold=0.5)
        result = analyzer.analyze_prompt(acts, ref_dir)

        # The planted trigger should be detected
        assert 5 in result.trigger_positions
        assert result.peak_position == 5

    def test_peak_vs_last(self):
        """Peak should be at trigger, not last token."""
        acts, ref_dir = self._make_activations_with_trigger(trigger_pos=5)
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir)

        assert result.peak_strength > result.last_token_strength
        assert result.peak_position != result.n_tokens - 1

    def test_decay_rate_positive(self):
        acts, ref_dir = self._make_activations_with_trigger(trigger_pos=5)
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir)
        # With exponential decay planted, decay rate should be positive
        assert result.decay_rate > 0

    def test_position_gini_bounded(self):
        acts, ref_dir = self._make_activations_with_trigger()
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir)
        assert 0 <= result.position_gini <= 1.0

    def test_token_profiles_length(self):
        acts, ref_dir = self._make_activations_with_trigger(seq_len=15)
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir)
        assert len(result.token_profiles) == 15

    def test_custom_token_texts(self):
        acts, ref_dir = self._make_activations_with_trigger(seq_len=10, trigger_pos=3)
        tokens = ["How", "to", "make", "a", "bomb", "from", "scratch", "please", "help", "me"]
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir, token_texts=tokens)
        for tp in result.token_profiles:
            assert tp.token_text in tokens or tp.token_text.startswith("pos_")

    def test_batch_analysis(self):
        batch = []
        for i in range(5):
            acts, ref_dir = self._make_activations_with_trigger(
                trigger_pos=3 + i % 3,
            )
            batch.append(acts)

        analyzer = MultiTokenPositionAnalyzer()
        summary = analyzer.analyze_batch(batch, ref_dir)

        assert isinstance(summary, MultiTokenSummary)
        assert len(summary.per_prompt) == 5
        assert summary.mean_peak_vs_last_ratio > 0
        assert summary.mean_trigger_count > 0
        assert 0 <= summary.peak_is_last_fraction <= 1.0
        assert 0 <= summary.last_token_dominance <= 1.0

    def test_last_token_dominant_case(self):
        """When signal is only at last token, peak should equal last."""
        torch.manual_seed(42)
        hidden_dim = 32
        seq_len = 10
        ref_dir = torch.randn(hidden_dim)
        ref_dir = ref_dir / ref_dir.norm()

        acts = torch.randn(seq_len, hidden_dim) * 0.01
        acts[-1] += 5.0 * ref_dir

        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir)
        assert result.peak_position == seq_len - 1

    def test_format_position_report(self):
        acts, ref_dir = self._make_activations_with_trigger()
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir, prompt_text="How to hack?")
        report = MultiTokenPositionAnalyzer.format_position_report(result)

        assert "Multi-Token" in report
        assert "Peak position" in report

    def test_format_summary(self):
        batch = []
        for _ in range(3):
            acts, ref_dir = self._make_activations_with_trigger()
            batch.append(acts)

        analyzer = MultiTokenPositionAnalyzer()
        summary = analyzer.analyze_batch(batch, ref_dir)
        report = MultiTokenPositionAnalyzer.format_summary(summary)

        assert "Summary" in report
        assert "Prompts analyzed" in report

    def test_3d_activations_handled(self):
        """Should handle (1, seq_len, hidden_dim) inputs."""
        acts, ref_dir = self._make_activations_with_trigger()
        acts = acts.unsqueeze(0)  # Add batch dim
        analyzer = MultiTokenPositionAnalyzer()
        result = analyzer.analyze_prompt(acts, ref_dir)
        assert result.n_tokens == 20

    def test_empty_batch(self):
        ref_dir = torch.randn(32)
        analyzer = MultiTokenPositionAnalyzer()
        summary = analyzer.analyze_batch([], ref_dir)
        assert len(summary.per_prompt) == 0
        assert summary.peak_is_last_fraction == 1.0


# ===========================================================================
#  Tests: Sparse Direction Surgery
# ===========================================================================

class TestSparseDirectionSurgeon:
    def _make_weight_with_sparse_refusal(
        self, out_dim=64, in_dim=32, n_refusal_rows=5,
    ):
        """Create a weight matrix where refusal is concentrated in a few rows."""
        torch.manual_seed(42)
        refusal_dir = torch.randn(in_dim)
        refusal_dir = refusal_dir / refusal_dir.norm()

        W = torch.randn(out_dim, in_dim) * 0.1

        # Plant strong refusal signal in specific rows
        refusal_rows = list(range(n_refusal_rows))
        for i in refusal_rows:
            W[i] += 5.0 * refusal_dir

        return W, refusal_dir, refusal_rows

    def test_basic_analysis(self):
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()
        surgeon = SparseDirectionSurgeon(sparsity=0.1)
        result = surgeon.analyze_weight_matrix(W, ref_dir, layer_idx=3)

        assert isinstance(result, SparseProjectionResult)
        assert result.layer_idx == 3
        assert result.n_rows_total == 64
        assert result.n_rows_modified > 0
        assert result.mean_projection > 0
        assert result.max_projection > result.mean_projection

    def test_refusal_sparsity_index(self):
        """With sparse refusal, RSI should be high."""
        W, ref_dir, _ = self._make_weight_with_sparse_refusal(
            out_dim=100, n_refusal_rows=5,
        )
        surgeon = SparseDirectionSurgeon()
        result = surgeon.analyze_weight_matrix(W, ref_dir)
        assert result.refusal_sparsity_index > 0.3  # Concentrated signal

    def test_energy_removed(self):
        """Top rows should capture most of the refusal energy."""
        W, ref_dir, _ = self._make_weight_with_sparse_refusal(
            out_dim=64, n_refusal_rows=5,
        )
        surgeon = SparseDirectionSurgeon(sparsity=0.15)  # ~10 rows out of 64
        result = surgeon.analyze_weight_matrix(W, ref_dir)
        # With 5 refusal rows and 10 modified, should capture most energy
        assert result.energy_removed > 0.5

    def test_frobenius_change_bounded(self):
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()
        surgeon = SparseDirectionSurgeon(sparsity=0.1)
        result = surgeon.analyze_weight_matrix(W, ref_dir)
        assert result.frobenius_change > 0
        assert result.frobenius_change < 1.0  # Shouldn't change more than 100%

    def test_apply_sparse_projection(self):
        """Sparse projection should reduce refusal signal."""
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()
        surgeon = SparseDirectionSurgeon(sparsity=0.1)

        W_modified = surgeon.apply_sparse_projection(W, ref_dir)

        # Check that modified rows have reduced projection
        original_proj = (W @ ref_dir).abs().sum().item()
        modified_proj = (W_modified @ ref_dir).abs().sum().item()
        assert modified_proj < original_proj

    def test_sparse_preserves_unmodified_rows(self):
        """Rows below the threshold should be unchanged."""
        W, ref_dir, refusal_rows = self._make_weight_with_sparse_refusal(
            out_dim=64, n_refusal_rows=5,
        )
        surgeon = SparseDirectionSurgeon(sparsity=0.1)  # ~6 rows
        W_modified = surgeon.apply_sparse_projection(W, ref_dir)

        # Count rows that actually changed
        diffs = (W - W_modified).abs().sum(dim=1)
        n_changed = (diffs > 1e-6).sum().item()
        n_unchanged = (diffs < 1e-6).sum().item()

        assert n_changed <= int(0.1 * 64) + 1  # Sparsity bound
        assert n_unchanged >= 57  # Most rows unchanged

    def test_dense_vs_sparse_comparison(self):
        """Dense projection should modify all rows; sparse should modify fewer."""
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()

        # Dense projection
        r = ref_dir / ref_dir.norm()
        W_dense = W - (W @ r).unsqueeze(1) * r.unsqueeze(0)

        # Sparse projection
        surgeon = SparseDirectionSurgeon(sparsity=0.1)
        W_sparse = surgeon.apply_sparse_projection(W, ref_dir)

        dense_changes = (W - W_dense).abs().sum(dim=1)
        sparse_changes = (W - W_sparse).abs().sum(dim=1)

        n_dense_changed = (dense_changes > 1e-6).sum().item()
        n_sparse_changed = (sparse_changes > 1e-6).sum().item()

        assert n_sparse_changed < n_dense_changed

    def test_plan_surgery(self):
        weights = {}
        directions = {}
        for i in range(6):
            W, ref_dir, _ = self._make_weight_with_sparse_refusal()
            weights[i] = W
            directions[i] = ref_dir

        surgeon = SparseDirectionSurgeon(sparsity=0.1)
        plan = surgeon.plan_surgery(weights, directions)

        assert isinstance(plan, SparseSurgeryPlan)
        assert len(plan.per_layer) == 6
        assert 0 < plan.recommended_sparsity < 1.0
        assert plan.mean_refusal_sparsity_index > 0
        assert plan.mean_energy_removed > 0

    def test_auto_sparsity(self):
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()
        surgeon = SparseDirectionSurgeon(auto_sparsity=True)
        result = surgeon.analyze_weight_matrix(W, ref_dir)
        # Auto sparsity should find a reasonable value
        assert 0.01 <= result.sparsity <= 0.5

    def test_auto_sparsity_apply(self):
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()
        surgeon = SparseDirectionSurgeon(auto_sparsity=True)
        W_modified = surgeon.apply_sparse_projection(W, ref_dir)
        # Should reduce projection
        assert (W_modified @ ref_dir).abs().sum() < (W @ ref_dir).abs().sum()

    def test_format_analysis(self):
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()
        surgeon = SparseDirectionSurgeon(sparsity=0.1)
        result = surgeon.analyze_weight_matrix(W, ref_dir, layer_idx=4)
        report = SparseDirectionSurgeon.format_analysis(result)

        assert "Sparse Direction Surgery" in report
        assert "Layer 4" in report
        assert "Refusal Sparsity Index" in report

    def test_format_plan(self):
        weights = {i: torch.randn(32, 16) for i in range(4)}
        directions = {i: torch.randn(16) for i in range(4)}

        surgeon = SparseDirectionSurgeon(sparsity=0.1)
        plan = surgeon.plan_surgery(weights, directions)
        report = SparseDirectionSurgeon.format_plan(plan)

        assert "Sparse Direction Surgery Plan" in report
        assert "Recommended sparsity" in report

    def test_empty_inputs(self):
        surgeon = SparseDirectionSurgeon()
        plan = surgeon.plan_surgery({}, {})
        assert len(plan.per_layer) == 0

    def test_output_dtype_preserved(self):
        """Output should match input dtype."""
        W, ref_dir, _ = self._make_weight_with_sparse_refusal()
        W_half = W.half()
        surgeon = SparseDirectionSurgeon(sparsity=0.1)
        W_out = surgeon.apply_sparse_projection(W_half, ref_dir)
        assert W_out.dtype == torch.float16


# ===========================================================================
#  Tests: Integration / Imports
# ===========================================================================

class TestAnalysisImports:
    def test_all_new_modules_importable(self):
        from obliteratus.analysis import (
            ConceptConeAnalyzer,
            AlignmentImprintDetector,
            MultiTokenPositionAnalyzer,
            SparseDirectionSurgeon,
        )
        assert ConceptConeAnalyzer is not None
        assert AlignmentImprintDetector is not None
        assert MultiTokenPositionAnalyzer is not None
        assert SparseDirectionSurgeon is not None
