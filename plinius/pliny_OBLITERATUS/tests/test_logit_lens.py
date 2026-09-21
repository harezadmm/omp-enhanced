"""Tests for logit lens refusal direction analysis."""

from __future__ import annotations

from unittest.mock import MagicMock

import torch

from obliteratus.analysis.logit_lens import (
    RefusalLogitLens,
    LogitLensResult,
    MultiLayerLogitLensResult,
    REFUSAL_TOKENS,
    COMPLIANCE_TOKENS,
)


def _make_mock_model(hidden_dim=32, vocab_size=100):
    """Create a mock model with LM head and layer norm."""
    model = MagicMock()

    # LM head weight (vocab_size, hidden_dim)
    lm_head = MagicMock()
    lm_head.weight = MagicMock()
    lm_head.weight.data = torch.randn(vocab_size, hidden_dim)
    model.lm_head = lm_head

    # Final LayerNorm
    ln_f = MagicMock()
    ln_f.weight = MagicMock()
    ln_f.weight.data = torch.ones(hidden_dim)
    ln_f.bias = MagicMock()
    ln_f.bias.data = torch.zeros(hidden_dim)
    model.transformer = MagicMock()
    model.transformer.ln_f = ln_f

    return model


def _make_mock_tokenizer(vocab_size=100):
    """Create a mock tokenizer."""
    tokenizer = MagicMock()

    def mock_decode(ids):
        if isinstance(ids, list) and len(ids) == 1:
            return f"tok_{ids[0]}"
        return f"tok_{ids}"

    def mock_encode(text, add_special_tokens=False):
        # Return a deterministic token ID based on the text
        return [hash(text) % vocab_size]

    tokenizer.decode = mock_decode
    tokenizer.encode = mock_encode
    return tokenizer


class TestRefusalLogitLens:
    def test_basic_analysis(self):
        """Should produce a LogitLensResult with expected fields."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        direction = torch.randn(32)

        lens = RefusalLogitLens(top_k=10)
        result = lens.analyze_direction(direction, model, tokenizer, layer_idx=5)

        assert isinstance(result, LogitLensResult)
        assert result.layer_idx == 5
        assert len(result.top_promoted) == 10
        assert len(result.top_suppressed) == 10
        assert isinstance(result.refusal_specificity, float)
        assert isinstance(result.logit_effect_entropy, float)
        assert isinstance(result.refusal_compliance_gap, float)

    def test_promoted_suppressed_ordering(self):
        """Top promoted should have higher logit boost than top suppressed."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        direction = torch.randn(32)

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_direction(direction, model, tokenizer)

        # Promoted tokens should have positive-ish values
        # Suppressed tokens should have negative-ish values
        max_promoted = max(v for _, v in result.top_promoted)
        min_suppressed = min(v for _, v in result.top_suppressed)
        assert max_promoted > min_suppressed

    def test_multi_layer_analysis(self):
        """Should analyze multiple layers."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        directions = {0: torch.randn(32), 1: torch.randn(32), 2: torch.randn(32)}

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_all_layers(directions, model, tokenizer)

        assert isinstance(result, MultiLayerLogitLensResult)
        assert len(result.per_layer) == 3
        assert result.strongest_refusal_layer in [0, 1, 2]
        assert result.peak_specificity_layer in [0, 1, 2]

    def test_strong_layers_filter(self):
        """Should only analyze specified strong layers."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        directions = {i: torch.randn(32) for i in range(10)}

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_all_layers(
            directions, model, tokenizer, strong_layers=[2, 5]
        )
        assert set(result.per_layer.keys()) == {2, 5}

    def test_handles_unnormalized_direction(self):
        """Should handle non-unit directions."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        direction = torch.randn(32) * 100.0  # large magnitude

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_direction(direction, model, tokenizer)
        # Should still produce valid results
        assert len(result.top_promoted) == 5

    def test_format_report(self):
        """Format report should produce readable output."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        directions = {0: torch.randn(32), 1: torch.randn(32)}

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_all_layers(directions, model, tokenizer)
        report = RefusalLogitLens.format_report(result)
        assert "Logit Lens" in report
        assert "Layer 0:" in report

    def test_empty_directions(self):
        """Should handle empty input gracefully."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_all_layers({}, model, tokenizer)
        assert len(result.per_layer) == 0

    def test_token_lists_nonempty(self):
        """Refusal and compliance token lists should have entries."""
        assert len(REFUSAL_TOKENS) > 10
        assert len(COMPLIANCE_TOKENS) > 10

    def test_entropy_nonnegative(self):
        """Logit effect entropy should be non-negative."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        direction = torch.randn(32)

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_direction(direction, model, tokenizer)
        assert result.logit_effect_entropy >= 0

    def test_2d_direction_input(self):
        """Should handle 2D direction input (unsqueezed)."""
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        direction = torch.randn(1, 32)

        lens = RefusalLogitLens(top_k=5)
        result = lens.analyze_direction(direction, model, tokenizer)
        assert len(result.top_promoted) == 5
