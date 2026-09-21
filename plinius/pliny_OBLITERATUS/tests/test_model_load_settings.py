"""Contracts for explicit and automatic web-UI model loading settings."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from obliteratus.model_load_settings import resolve_model_load_settings


def _resolve(quantization="Auto (default)", dtype="Auto (default)", auto="4bit"):
    calls = []

    def automatic(resolved_dtype):
        calls.append(resolved_dtype)
        return auto

    return resolve_model_load_settings(
        quantization, dtype, auto_quantization=automatic,
    ), calls


def test_defaults_preserve_float16_and_automatic_quantization():
    settings, calls = _resolve()
    assert settings.dtype == "float16"
    assert settings.quantization == "4bit"
    assert calls == ["float16"]


def test_explicit_bfloat16_without_quantization_bypasses_auto_policy():
    settings, calls = _resolve("None", "BF16")
    assert settings.dtype == "bfloat16"
    assert settings.quantization is None
    assert calls == []
    assert settings.summary == "quantization=none, compute dtype=bfloat16"


def test_explicit_four_bit_and_dtype_are_preserved():
    settings, calls = _resolve("4-bit", "FP16", auto=None)
    assert settings.quantization == "4bit"
    assert settings.dtype == "float16"
    assert calls == []


@pytest.mark.parametrize(
    ("quantization", "dtype", "match"),
    [
        ("3-bit", "FP16", "Unsupported quantization choice"),
        ("None", "TF32", "Unsupported compute dtype"),
    ],
)
def test_invalid_choices_fail_early_with_actionable_errors(quantization, dtype, match):
    with pytest.raises(ValueError, match=match):
        _resolve(quantization, dtype)


def test_every_auto_quantization_ui_entry_point_uses_resolved_settings():
    """Guard every path that historically called app._should_quantize()."""
    tree = ast.parse(Path("app.py").read_text())
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for name in ("benchmark", "benchmark_multi_model", "obliterate", "strength_sweep"):
        calls = {
            node.func.id
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "_resolve_ui_load_settings" in calls, name

    reload_calls = {
        node.func.id
        for node in ast.walk(functions["load_bench_into_chat"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "_settings_from_metadata" in reload_calls

    direct_auto_callers = []
    for name, function in functions.items():
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_should_quantize"
            for node in ast.walk(function)
        ):
            direct_auto_callers.append(name)
    assert direct_auto_callers == ["_resolve_ui_load_settings"]
