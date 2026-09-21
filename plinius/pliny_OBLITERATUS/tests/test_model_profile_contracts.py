"""Contracts for model-profile estimation and defaults."""

from __future__ import annotations

import json

import pytest

from obliteratus.model_profile import (
    ModelProfile,
    default_self_improve_params,
    estimate_active_params_b,
    estimate_total_params,
    profile_model,
)


def test_estimate_total_params_prefers_explicit_counts():
    for key in ("num_parameters", "n_params", "total_params"):
        cfg = {key: 12345}
        assert estimate_total_params(cfg) == 12345


@pytest.mark.parametrize(
    "cfg",
    [
        {"hidden_size": 0, "num_hidden_layers": 2},
        {"hidden_size": 128, "num_hidden_layers": 0},
        {"hidden_size": -1, "num_hidden_layers": 2},
    ],
)
def test_estimate_total_params_rejects_invalid_or_zero_dimensions(cfg):
    assert estimate_total_params(cfg) is None


def test_estimate_total_params_and_active_params_cover_moe_shapes():
    cfg = {
        "hidden_size": 4096,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "num_key_value_heads": 8,
        "head_dim": 128,
        "intermediate_size": 14336,
        "num_local_experts": 8,
        "num_experts_per_tok": 2,
        "moe_intermediate_size": 28672,
        "vocab_size": 32000,
    }

    total = estimate_total_params(cfg)
    assert total is not None
    assert total > 0

    active = estimate_active_params_b(cfg, total / 1e9)
    assert active > 0
    assert active < total / 1e9


def test_profile_model_uses_local_config_when_safetensors_absent(tmp_path):
    model_dir = tmp_path / "toy"
    model_dir.mkdir()
    (model_dir / "config.json").write_text(
        json.dumps(
            {
                "model_type": "toy",
                "hidden_size": 64,
                "num_hidden_layers": 2,
                "num_attention_heads": 4,
                "intermediate_size": 128,
                "vocab_size": 320,
            }
        )
    )

    profile = profile_model(str(model_dir), dtype="float16")
    assert profile.source == "local_config"
    assert profile.total_params is not None
    assert profile.total_params > 0
    assert profile.dtype == "float16"


def test_mid_size_defaults_and_modelprofile_round_trip():
    profile = ModelProfile(
        model="mid",
        source="test",
        total_params=int(10e9),
        total_params_b=10.0,
        active_params_b=6.0,
        num_layers=24,
        hidden_size=4096,
        intermediate_size=14336,
        vocab_size=32000,
        model_type="qwen",
        dtype="bfloat16",
    )

    defaults = default_self_improve_params(profile)
    assert defaults["n_directions"] == 3
    assert defaults["refinement_passes"] == 1
    assert defaults["verify_sample_size"] == 40
    assert defaults["residue_weight"] == 5

    assert profile.to_json()["total_params"] == int(10e9)
