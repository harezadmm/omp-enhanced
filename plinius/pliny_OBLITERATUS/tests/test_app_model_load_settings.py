"""Web-application contracts for configurable model loading."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.operator_ui
def test_ui_resolves_auto_explicit_bfloat16_and_invalid_hardware():
    """Exercise app helpers in isolation from Gradio's import-time sockets."""
    script = r'''
from unittest.mock import Mock
import torch
import app

app.dev.get_device = lambda _requested="auto": "cuda:0"
app.dev.supports_bfloat16 = lambda _device=None: True
app.dev.supports_bitsandbytes = lambda _device=None: True

automatic = Mock(return_value="4bit")
app._should_quantize = automatic
settings = app._resolve_ui_load_settings(
    "Qwen/Qwen3.8-27B", True, "Auto (default)", "Auto (default)",
)
assert settings.quantization == "4bit"
assert settings.dtype == "float16"
automatic.assert_called_once_with(
    "Qwen/Qwen3.8-27B", is_preset=True, dtype="float16",
)

automatic = Mock(side_effect=AssertionError("automatic policy must not run"))
app._should_quantize = automatic
settings = app._resolve_ui_load_settings(
    "Qwen/Qwen3.8-27B", True, "None", "BF16",
)
assert settings.quantization is None
assert settings.dtype == "bfloat16"
assert app._checkpoint_load_kwargs(settings) == {"torch_dtype": torch.bfloat16}
automatic.assert_not_called()

app.dev.supports_bfloat16 = lambda _device=None: False
try:
    app._resolve_ui_load_settings("org/model", False, "None", "BF16")
except ValueError as exc:
    assert "BF16 is not supported" in str(exc)
    assert "FP16 or FP32" in str(exc)
else:
    raise AssertionError("unsupported BF16 must fail before pipeline construction")
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.operator_ui
def test_result_card_uses_configured_sequence_token_kl_budget():
    """The UI must not apply independent hard-coded KL thresholds."""
    script = r'''
from types import SimpleNamespace

import app

pipeline = SimpleNamespace(
    _quality_metrics={
        "kl_divergence": 0.24,
        "kl_budget": 0.50,
        "kl_metric": "sequence_token_forward_kl_nats",
    },
    _strong_layers=[1, 2],
    kl_budget=0.50,
)
card = app._format_obliteration_metrics(pipeline, "advanced", "1s")
assert "Token KL / Budget" in card
assert "0.2400 / 0.5000" in card
assert "🟢" in card

pipeline._quality_metrics["kl_divergence"] = 0.51
card = app._format_obliteration_metrics(pipeline, "advanced", "1s")
assert "0.5100 / 0.5000" in card
assert "🔴" in card
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.operator_ui
def test_result_card_exposes_spectral_inconclusive_reason():
    script = r'''
from types import SimpleNamespace

import app

pipeline = SimpleNamespace(
    _quality_metrics={
        "spectral_certification": "INCONCLUSIVE",
        "spectral_diagnostic_reason": "insufficient_samples",
    },
    _strong_layers=[1],
)
card = app._format_obliteration_metrics(pipeline, "advanced", "1s")
assert "Spectral Diagnostic" in card
assert "INCONCLUSIVE (insufficient_samples)" in card
assert "⚪" in card
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
