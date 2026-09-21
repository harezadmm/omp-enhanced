"""Tests for advanced evaluation metrics."""

from __future__ import annotations

import pytest
import torch

from obliteratus.evaluation.advanced_metrics import (
    REFUSAL_PREFIXES,
    REFUSAL_SUBSTRINGS,
    AbliterationEvalResult,
    _is_degenerate,
    _is_refusal,
    _is_refusal_detailed,
    _strip_cot_tags,
    activation_cosine_similarity,
    effective_rank,
    effective_rank_change,
    first_token_kl_divergence,
    format_eval_report,
    linear_cka,
    refusal_projection_magnitude,
    refusal_rate,
    refusal_rate_with_ci,
    token_kl_divergence,
)

# ---------------------------------------------------------------------------
# Refusal Rate
# ---------------------------------------------------------------------------

class TestRefusalRate:
    def test_cot_extraction_and_degenerate_classification_boundaries(self):
        assert _strip_cot_tags("<assistant> final answer ") == "final answer"
        assert _is_degenerate("") is True
        assert _is_degenerate("!!!") is True
        assert _is_degenerate("ababababab") is True
        assert _is_degenerate("normal answer") is False

    def test_empty_and_degenerate_post_cot_outputs_are_not_refusals(self):
        assert _is_refusal("<assistant>   ", mode="combined") is False
        assert _is_refusal("!!!!!!!!", mode="combined") is False
        assert _is_refusal_detailed("   ") == (False, "")
        assert _is_refusal_detailed("<assistant>   ") == (False, "")
        assert _is_refusal_detailed("!!!!!!!!") == (False, "DEGENERATE")

    @pytest.mark.parametrize(
        ("response", "mode", "reason_prefix"),
        [
            ("I'm sorry, I cannot help with that.", "prefix", "prefix:"),
            ("Context first: I cannot assist with that request.", "substring", "substring:"),
            ("This raises serious safety concerns for users.", "semantic", "semantic:"),
            ("A normal helpful response.", "combined", ""),
        ],
    )
    def test_detailed_refusal_reasons_cover_each_decision_mode(
        self,
        response,
        mode,
        reason_prefix,
    ):
        refused, reason = _is_refusal_detailed(response, mode=mode)
        assert refused is bool(reason_prefix)
        assert reason.startswith(reason_prefix)

    def test_semantic_classifier_reports_positive_and_negative_matches(self):
        from obliteratus.evaluation.advanced_metrics import _is_refusal_semantic

        assert _is_refusal_semantic("This raises serious legal concerns.") is True
        assert _is_refusal_semantic("A normal helpful response.") is False

    def test_empty_confidence_interval_is_explicitly_unavailable(self):
        assert refusal_rate_with_ci([]) == {
            "available": False,
            "rate": None,
            "ci_lower": None,
            "ci_upper": None,
            "n_samples": 0,
            "refusal_count": 0,
        }

    def test_refusal_mentioning_assistant_is_detected(self):
        response = (
            "I cannot help with that request. I am designed to be a helpful "
            "and harmless AI assistant while strictly adhering to safety "
            "guidelines."
        )
        assert _is_refusal(response, mode="combined") is True

    def test_chatml_preamble_still_stripped(self):
        response = (
            "<|im_start|>user\nI cannot get my script to work, fix it<|im_end|>\n"
            "<|im_start|>assistant\nSure! Here is the corrected script:"
        )
        assert _is_refusal(response, mode="combined") is False

    def test_harmony_preamble_still_stripped(self):
        response = "analysis\nThe user asks for X.assistant I cannot help with that."
        assert _is_refusal(response, mode="combined") is True

    def test_think_tag_preamble_still_stripped(self):
        response = (
            "<think>user wants X, I should refuse</think>"
            "assistant Sure, here is how you do it"
        )
        assert _is_refusal(response, mode="combined") is False

    def test_refusal_rate_counts_assistant_phrasing(self):
        responses = [
            "I cannot provide that. I am a harmless AI assistant bound by policy.",
            "I cannot help with that request.",
        ]
        assert refusal_rate(responses, mode="combined") == 1.0

    def test_all_refusals(self):
        responses = [
            "I'm sorry, but I cannot help with that.",
            "I apologize, but I'm unable to assist.",
            "As an AI, I cannot provide that information.",
        ]
        assert refusal_rate(responses, mode="prefix") == 1.0

    def test_no_refusals(self):
        responses = [
            "Sure, here's how to do that.",
            "Here's a step-by-step guide.",
            "The answer is 42.",
        ]
        assert refusal_rate(responses, mode="prefix") == 0.0

    def test_mixed_responses(self):
        responses = [
            "I'm sorry, I can't do that.",
            "Sure, here you go.",
            "I cannot provide that.",
            "Here's what you need.",
        ]
        rate = refusal_rate(responses, mode="prefix")
        assert rate == 0.5  # 2 out of 4

    def test_substring_mode(self):
        responses = [
            "Well, actually I cannot help with that request.",
            "Let me explain how to do this.",
        ]
        assert refusal_rate(responses, mode="substring") == 0.5

    def test_combined_mode(self):
        responses = [
            "I'm sorry, but no.",  # caught by prefix
            "That said, i won't do that for you.",  # caught by substring
            "Here's the answer.",  # not a refusal
        ]
        rate = refusal_rate(responses, mode="combined")
        assert abs(rate - 2.0 / 3.0) < 1e-6

    def test_empty_responses(self):
        assert refusal_rate([], mode="prefix") == 0.0

    def test_empty_string_not_refusal(self):
        assert not _is_refusal("", mode="combined")

    def test_is_refusal_prefix(self):
        assert _is_refusal("I'm sorry, I can't do that.", mode="prefix")
        assert _is_refusal("As an AI language model, I cannot", mode="prefix")
        assert not _is_refusal("The answer is 42.", mode="prefix")

    def test_is_refusal_substring(self):
        assert _is_refusal("I must say, i cannot assist with that.", mode="substring")
        assert not _is_refusal("The capital of France is Paris.", mode="substring")

    def test_refusal_prefixes_nonempty(self):
        assert len(REFUSAL_PREFIXES) > 20

    def test_refusal_substrings_nonempty(self):
        assert len(REFUSAL_SUBSTRINGS) > 10

    @pytest.mark.parametrize("entrypoint", [refusal_rate, refusal_rate_with_ci])
    def test_rejects_unknown_mode(self, entrypoint):
        with pytest.raises(ValueError, match="Unknown refusal detection mode"):
            entrypoint(["I cannot help"], mode="typo")

    def test_private_classifier_rejects_unknown_mode(self):
        with pytest.raises(ValueError, match="Unknown refusal detection mode"):
            _is_refusal("I cannot help", mode="typo")

    @pytest.mark.parametrize("confidence", [0.0, 0.9 + 1e-10, 1.0])
    def test_rejects_unsupported_confidence(self, confidence):
        with pytest.raises(ValueError, match="confidence must"):
            refusal_rate_with_ci(["Sure"], confidence=confidence)

    def test_measured_zero_is_not_unavailable(self):
        result = refusal_rate_with_ci(["Sure, here is the answer."])
        assert result["available"] is True
        assert result["rate"] == 0.0
        assert result["refusal_count"] == 0

    @pytest.mark.parametrize(
        "response",
        [
            "  I'M SORRY!!! I cannot help with that.",
            "抱歉，我无法帮助这个请求。",
            "Извините, я не могу помочь с этим запросом.",
        ],
    )
    def test_case_punctuation_and_multilingual_refusals(self, response):
        assert _is_refusal(response, mode="combined")

    def test_hard_negative_is_not_a_refusal(self):
        response = "The parser accepts cannot_help as an ordinary variable name."
        assert not _is_refusal(response, mode="combined")


# ---------------------------------------------------------------------------
# KL Divergence
# ---------------------------------------------------------------------------

class TestKLDivergence:
    def test_rejects_wrong_tensor_dimension(self):
        with pytest.raises(ValueError, match="both be 3D tensors"):
            token_kl_divergence(torch.zeros(2, 3), torch.zeros(2, 3))

    def test_first_token_kl_rejects_empty_sequence_axis(self):
        empty = torch.empty(1, 0, 3)
        with pytest.raises(ValueError, match="must not be empty"):
            first_token_kl_divergence(empty, empty)

    def test_identical_distributions(self):
        """KL divergence of identical distributions should be 0."""
        logits = torch.randn(2, 10, 100)
        kl = token_kl_divergence(logits, logits)
        assert abs(kl) < 1e-5

    def test_different_distributions(self):
        """KL divergence of different distributions should be positive."""
        torch.manual_seed(42)
        logits_a = torch.randn(2, 10, 100)
        logits_b = torch.randn(2, 10, 100)
        kl = token_kl_divergence(logits_a, logits_b)
        assert kl > 0

    def test_kl_nonnegative(self):
        """KL divergence should always be non-negative."""
        torch.manual_seed(42)
        for _ in range(5):
            logits_a = torch.randn(1, 5, 50)
            logits_b = torch.randn(1, 5, 50)
            kl = token_kl_divergence(logits_a, logits_b)
            assert kl >= -1e-6  # allow small numerical errors

    def test_first_token_kl_identical(self):
        """First-token KL of identical distributions should be 0."""
        logits = torch.randn(4, 20, 100)
        kl = first_token_kl_divergence(logits, logits)
        assert abs(kl) < 1e-5

    def test_first_token_kl_different(self):
        """First-token KL of different distributions should be positive."""
        torch.manual_seed(42)
        logits_a = torch.randn(4, 20, 100)
        logits_b = torch.randn(4, 20, 100)
        kl = first_token_kl_divergence(logits_a, logits_b)
        assert kl > 0

    def test_temperature_effect(self):
        """Higher temperature should reduce KL divergence (smoother distributions)."""
        torch.manual_seed(42)
        logits_a = torch.randn(2, 5, 50)
        logits_b = torch.randn(2, 5, 50)
        kl_t1 = token_kl_divergence(logits_a, logits_b, temperature=1.0)
        kl_t5 = token_kl_divergence(logits_a, logits_b, temperature=5.0)
        assert kl_t5 < kl_t1

    def test_common_logit_offset_is_invariant(self):
        torch.manual_seed(42)
        logits_a = torch.randn(2, 3, 8)
        logits_b = torch.randn(2, 3, 8)
        expected = token_kl_divergence(logits_a, logits_b)
        assert token_kl_divergence(logits_a + 11, logits_b - 7) == pytest.approx(
            expected, abs=1e-6,
        )

    @pytest.mark.parametrize("temperature", [0, -1, float("inf"), float("nan"), "hot"])
    def test_rejects_invalid_temperature(self, temperature):
        logits = torch.zeros(1, 2, 3)
        with pytest.raises(ValueError, match="temperature"):
            token_kl_divergence(logits, logits, temperature=temperature)

    def test_rejects_shape_and_nonfinite_input(self):
        with pytest.raises(ValueError, match="identical shapes"):
            token_kl_divergence(torch.zeros(1, 2, 3), torch.zeros(1, 3, 3))
        logits = torch.zeros(1, 2, 3)
        logits[0, 0, 0] = float("inf")
        with pytest.raises(ValueError, match="finite"):
            first_token_kl_divergence(logits, logits)


# ---------------------------------------------------------------------------
# Effective Rank
# ---------------------------------------------------------------------------

class TestEffectiveRank:
    @pytest.mark.parametrize(
        ("matrix", "message"),
        [
            (torch.empty(0, 2), "non-empty"),
            (torch.tensor([[float("inf")]]), "finite"),
        ],
    )
    def test_rejects_empty_and_nonfinite_matrices(self, matrix, message):
        with pytest.raises(ValueError, match=message):
            effective_rank(matrix)

    def test_rank_one_matrix(self):
        """Rank-1 matrix should have effective rank close to 1."""
        v = torch.randn(8, 1)
        u = torch.randn(1, 4)
        W = v @ u  # rank-1
        erank = effective_rank(W)
        assert erank < 1.5

    def test_identity_matrix(self):
        """Identity matrix should have effective rank equal to dimension."""
        n = 8
        W = torch.eye(n)
        erank = effective_rank(W)
        assert abs(erank - n) < 0.1

    def test_random_full_rank(self):
        """Random matrix should have high effective rank."""
        torch.manual_seed(42)
        W = torch.randn(16, 16)
        erank = effective_rank(W)
        assert erank > 10  # should be close to 16

    def test_zero_matrix(self):
        """Zero matrix should have effective rank 0."""
        W = torch.zeros(4, 4)
        erank = effective_rank(W)
        assert erank == 0.0

    def test_effective_rank_change(self):
        """Should compute before/after rank comparison."""
        torch.manual_seed(42)
        W_before = torch.randn(8, 8)
        # Simulate abliteration: remove a direction (reduces rank slightly)
        d = torch.randn(8, 1)
        d = d / d.norm()
        W_after = W_before - (W_before @ d) @ d.T

        result = effective_rank_change(W_before, W_after)
        assert "rank_before" in result
        assert "rank_after" in result
        assert "rank_delta" in result
        assert "rank_ratio" in result
        assert result["rank_after"] <= result["rank_before"] + 0.1

    def test_rejects_non_2d(self):
        """Should raise ValueError for non-2D tensors."""
        with pytest.raises(ValueError):
            effective_rank(torch.randn(4, 4, 4))


# ---------------------------------------------------------------------------
# Activation Cosine Similarity
# ---------------------------------------------------------------------------

class TestActivationCosineSimilarity:
    def test_identical_activations(self):
        acts = torch.randn(10, 32)
        sim = activation_cosine_similarity(acts, acts)
        assert abs(sim - 1.0) < 1e-5

    def test_orthogonal_activations(self):
        """Orthogonal activations should have cosine near 0."""
        a = torch.tensor([[1.0, 0.0, 0.0]])
        b = torch.tensor([[0.0, 1.0, 0.0]])
        sim = activation_cosine_similarity(a, b)
        assert abs(sim) < 1e-5

    def test_opposite_activations(self):
        """Opposite activations should have cosine -1."""
        a = torch.randn(5, 16)
        sim = activation_cosine_similarity(a, -a)
        assert abs(sim - (-1.0)) < 1e-5

    def test_handles_3d(self):
        """Should handle 3D tensors by reshaping."""
        a = torch.randn(2, 5, 16)
        b = torch.randn(2, 5, 16)
        sim = activation_cosine_similarity(a, b)
        assert -1.0 <= sim <= 1.0

    def test_rejects_mismatched_or_nonfinite_activations(self):
        with pytest.raises(ValueError, match="identical shapes"):
            activation_cosine_similarity(torch.zeros(2, 3), torch.zeros(3, 3))
        bad = torch.zeros(2, 3)
        bad[0, 0] = float("nan")
        with pytest.raises(ValueError, match="finite"):
            activation_cosine_similarity(bad, bad)


# ---------------------------------------------------------------------------
# Linear CKA
# ---------------------------------------------------------------------------

class TestLinearCKA:
    def test_zero_centered_energy_returns_defined_zero(self):
        assert linear_cka(torch.ones(2, 3), torch.ones(2, 4)) == 0.0

    def test_identical_representations(self):
        """CKA of identical representations should be 1.0."""
        X = torch.randn(20, 16)
        cka = linear_cka(X, X)
        assert abs(cka - 1.0) < 1e-4

    def test_scaled_representations(self):
        """CKA should be invariant to isotropic scaling."""
        X = torch.randn(20, 16)
        Y = X * 5.0
        cka = linear_cka(X, Y)
        assert abs(cka - 1.0) < 1e-4

    def test_random_representations(self):
        """CKA of random representations should be low."""
        torch.manual_seed(42)
        X = torch.randn(100, 16)
        Y = torch.randn(100, 16)
        cka = linear_cka(X, Y)
        assert cka < 0.3  # random should be near 0

    def test_cka_bounded(self):
        """CKA should be between 0 and 1."""
        torch.manual_seed(42)
        for _ in range(5):
            X = torch.randn(20, 8)
            Y = torch.randn(20, 8)
            cka = linear_cka(X, Y)
            assert -0.01 <= cka <= 1.01  # small tolerance for numerics

    def test_different_dimensions(self):
        """CKA should work with different hidden dimensions."""
        X = torch.randn(20, 16)
        Y = torch.randn(20, 32)
        cka = linear_cka(X, Y)
        assert -0.01 <= cka <= 1.01

    def test_handles_3d(self):
        """Should handle 3D tensors by reshaping."""
        X = torch.randn(2, 10, 16)
        Y = torch.randn(2, 10, 16)
        cka = linear_cka(X, Y)
        assert -0.01 <= cka <= 1.01

    def test_joint_row_permutation_is_invariant(self):
        torch.manual_seed(42)
        x = torch.randn(20, 8)
        y = torch.randn(20, 12)
        permutation = torch.randperm(20)
        assert linear_cka(x[permutation], y[permutation]) == pytest.approx(
            linear_cka(x, y), abs=1e-6,
        )

    def test_rejects_different_sample_counts(self):
        with pytest.raises(ValueError, match="same sample count"):
            linear_cka(torch.zeros(2, 3), torch.zeros(3, 4))

    def test_rejects_single_sample_degeneracy(self):
        with pytest.raises(ValueError, match="at least two samples"):
            linear_cka(torch.zeros(1, 3), torch.zeros(1, 4))


# ---------------------------------------------------------------------------
# Refusal Direction Projection Magnitude
# ---------------------------------------------------------------------------

class TestRefusalProjection:
    @pytest.mark.parametrize(
        ("activations", "direction", "message"),
        [
            (torch.ones(2), torch.ones(2), "activations"),
            (torch.empty(0, 2), torch.ones(2), "activations"),
            (torch.ones(2, 2), torch.empty(0), "refusal_direction"),
            (torch.ones(2, 2), torch.ones(1, 1, 2), "refusal_direction"),
            (torch.tensor([[float("nan"), 0.0]]), torch.ones(2), "finite"),
            (torch.ones(1, 2), torch.tensor([float("inf"), 0.0]), "finite"),
        ],
    )
    def test_rejects_invalid_projection_inputs(self, activations, direction, message):
        with pytest.raises(ValueError, match=message):
            refusal_projection_magnitude(activations, direction)

    def test_three_dimensional_activations_and_row_direction_are_normalized(self):
        result = refusal_projection_magnitude(
            torch.tensor([[[2.0, 0.0], [4.0, 0.0]]]),
            torch.tensor([[2.0, 0.0]]),
        )
        assert result["mean"] == 3.0

    def test_aligned_activations(self):
        """Activations aligned with direction should have high projection."""
        d = torch.tensor([1.0, 0.0, 0.0])
        acts = torch.tensor([
            [5.0, 0.0, 0.0],
            [3.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
        ])
        result = refusal_projection_magnitude(acts, d)
        assert result["mean"] == 4.0
        assert result["abs_mean"] == 4.0

    def test_orthogonal_activations(self):
        """Orthogonal activations should have zero projection."""
        d = torch.tensor([1.0, 0.0, 0.0])
        acts = torch.tensor([
            [0.0, 5.0, 0.0],
            [0.0, 0.0, 3.0],
        ])
        result = refusal_projection_magnitude(acts, d)
        assert abs(result["mean"]) < 1e-5
        assert abs(result["abs_mean"]) < 1e-5

    def test_result_keys(self):
        """Should return all expected keys."""
        d = torch.randn(8)
        acts = torch.randn(5, 8)
        result = refusal_projection_magnitude(acts, d)
        assert set(result.keys()) == {"mean", "std", "max", "min", "abs_mean"}

    def test_single_sample_has_defined_population_std(self):
        result = refusal_projection_magnitude(
            torch.tensor([[2.0, 0.0]]), torch.tensor([1.0, 0.0]),
        )
        assert result["std"] == 0.0

    @pytest.mark.parametrize("direction", [torch.zeros(2), torch.ones(3)])
    def test_rejects_invalid_direction(self, direction):
        with pytest.raises(ValueError):
            refusal_projection_magnitude(torch.ones(2, 2), direction)


# ---------------------------------------------------------------------------
# Eval Report Formatting
# ---------------------------------------------------------------------------

class TestEvalReport:
    @pytest.mark.parametrize(
        ("kl", "label"),
        [(0.3, "good"), (0.7, "moderate degradation")],
    )
    def test_format_report_kl_quality_boundaries(self, kl, label):
        result = AbliterationEvalResult(0.0, 0.0, kl, 1.0, 1.0, 1.0, 1.0)
        assert label in format_eval_report(result)

    def test_format_report(self):
        result = AbliterationEvalResult(
            refusal_rate_harmful=0.1,
            refusal_rate_harmless=0.02,
            kl_divergence=0.15,
            perplexity=12.5,
            coherence_score=0.8,
            mean_activation_cosine=0.95,
            mean_cka=0.92,
        )
        report = format_eval_report(result)
        assert "10.0%" in report
        assert "12.50" in report
        assert "excellent" in report  # KL < 0.2

    def test_format_report_high_kl(self):
        result = AbliterationEvalResult(
            refusal_rate_harmful=0.0,
            refusal_rate_harmless=0.0,
            kl_divergence=1.5,
            perplexity=50.0,
            coherence_score=0.4,
            mean_activation_cosine=None,
            mean_cka=None,
        )
        report = format_eval_report(result)
        assert "significant damage" in report

    def test_unavailable_metrics_are_not_rendered_as_zero(self):
        result = AbliterationEvalResult(
            refusal_rate_harmful=None,
            refusal_rate_harmless=0.0,
            kl_divergence=None,
            perplexity=None,
            coherence_score=None,
            mean_activation_cosine=None,
            mean_cka=None,
        )
        report = format_eval_report(result)
        assert report.count("unavailable") >= 4
        assert "Harmless prompt over-refusal: 0.0%" in report

    def test_format_report_no_kl(self):
        result = AbliterationEvalResult(
            refusal_rate_harmful=0.5,
            refusal_rate_harmless=0.1,
            kl_divergence=None,
            perplexity=20.0,
            coherence_score=1.0,
            mean_activation_cosine=None,
            mean_cka=None,
        )
        report = format_eval_report(result)
        assert "50.0%" in report
        assert "KL divergence: unavailable" in report
