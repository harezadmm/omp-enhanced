"""Tests for visualization module (non-interactive, save-to-file)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import torch

from obliteratus.analysis.cross_layer import CrossLayerAlignmentAnalyzer
from obliteratus.analysis.activation_probing import ActivationProbe
from obliteratus.analysis.visualization import (
    _sanitize_label,
    plot_refusal_topology,
    plot_cross_layer_heatmap,
    plot_angular_drift,
    plot_probe_dashboard,
    plot_defense_radar,
)
from obliteratus.analysis.defense_robustness import DefenseProfile


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _make_refusal_data(n_layers=6, hidden_dim=16):
    """Create test refusal directions and means."""
    torch.manual_seed(42)
    directions = {}
    harmful_means = {}
    harmless_means = {}

    for i in range(n_layers):
        d = torch.randn(hidden_dim)
        directions[i] = d / d.norm()
        base = torch.randn(hidden_dim)
        harmless_means[i] = base.unsqueeze(0)
        harmful_means[i] = (base + (2.0 if i in [2, 3, 4] else 0.3) * directions[i]).unsqueeze(0)

    strong_layers = [2, 3, 4]
    return directions, harmful_means, harmless_means, strong_layers


class TestRefusalTopology:
    def test_plot_saves_file(self, tmp_dir):
        directions, h_means, b_means, strong = _make_refusal_data()
        path = tmp_dir / "topology.png"
        plot_refusal_topology(
            directions, h_means, b_means, strong, output_path=path
        )
        assert path.exists()
        assert path.stat().st_size > 0

    def test_plot_returns_figure(self, tmp_dir):
        directions, h_means, b_means, strong = _make_refusal_data()
        fig = plot_refusal_topology(
            directions, h_means, b_means, strong, output_path=tmp_dir / "test.png"
        )
        assert fig is not None


class TestCrossLayerHeatmap:
    def test_plot_saves_file(self, tmp_dir):
        torch.manual_seed(42)
        directions = {i: torch.randn(16) for i in range(6)}
        analyzer = CrossLayerAlignmentAnalyzer()
        result = analyzer.analyze(directions)

        path = tmp_dir / "heatmap.png"
        plot_cross_layer_heatmap(result, output_path=path)
        assert path.exists()


class TestAngularDrift:
    def test_plot_saves_file(self, tmp_dir):
        torch.manual_seed(42)
        directions = {i: torch.randn(16) for i in range(8)}
        analyzer = CrossLayerAlignmentAnalyzer()
        result = analyzer.analyze(directions)

        path = tmp_dir / "drift.png"
        plot_angular_drift(result, output_path=path)
        assert path.exists()


class TestProbeDashboard:
    def test_plot_saves_file(self, tmp_dir):
        torch.manual_seed(42)
        harmful = {i: [torch.randn(8) for _ in range(3)] for i in range(4)}
        harmless = {i: [torch.randn(8) for _ in range(3)] for i in range(4)}
        dirs = {i: torch.randn(8) for i in range(4)}

        probe = ActivationProbe()
        result = probe.probe_all_layers(harmful, harmless, dirs)

        path = tmp_dir / "probe.png"
        plot_probe_dashboard(result, output_path=path)
        assert path.exists()


class TestDefenseRadar:
    def test_plot_saves_file(self, tmp_dir):
        profile = DefenseProfile(
            model_name="test-model",
            alignment_type_estimate="RLHF-like",
            refusal_concentration=0.4,
            refusal_layer_spread=5,
            mean_refusal_strength=2.0,
            max_refusal_strength=4.0,
            self_repair_estimate=0.6,
            entanglement_score=0.3,
            estimated_robustness="medium",
        )
        path = tmp_dir / "radar.png"
        plot_defense_radar(profile, output_path=path)
        assert path.exists()

    def test_model_name_sanitized_in_title(self, tmp_dir):
        """Ensure sensitive paths in model_name don't leak into saved charts."""
        profile = DefenseProfile(
            model_name="/home/user/.cache/huggingface/hub/models--secret-org/private-model",
            alignment_type_estimate="RLHF-like",
            refusal_concentration=0.4,
            refusal_layer_spread=5,
            mean_refusal_strength=2.0,
            max_refusal_strength=4.0,
            self_repair_estimate=0.6,
            entanglement_score=0.3,
            estimated_robustness="medium",
        )
        path = tmp_dir / "radar_sanitized.png"
        fig = plot_defense_radar(profile, output_path=path)
        # Title should not contain the full filesystem path
        title_text = fig.axes[0].get_title()
        assert "/home/user" not in title_text
        assert ".cache" not in title_text


class TestSanitizeLabel:
    def test_strips_absolute_paths(self):
        result = _sanitize_label("/home/user/.cache/huggingface/models--org/model")
        assert "/home/user" not in result
        assert "model" in result

    def test_redacts_hf_tokens(self):
        result = _sanitize_label("model with hf_abcdefghij token")
        assert "hf_abcdefghij" not in result
        assert "<TOKEN>" in result

    def test_redacts_long_hex_strings(self):
        hex_str = "a" * 40
        result = _sanitize_label(f"commit {hex_str}")
        assert hex_str not in result
        assert "<REDACTED>" in result

    def test_truncates_long_strings(self):
        long = "x" * 200
        result = _sanitize_label(long)
        assert len(result) <= 80
        assert result.endswith("...")

    def test_passes_normal_strings_through(self):
        assert _sanitize_label("Refusal Topology Map") == "Refusal Topology Map"
