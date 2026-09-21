"""Behavioral contracts for non-destructive BESTIARY preset augmentation."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from obliteratus import bestiary_sync, models_client, presets


@dataclass
class Preset:
    name: str
    hf_id: str
    description: str
    tier: str
    params: str
    recommended_dtype: str
    recommended_quantization: str | None
    gated: bool


@pytest.mark.parametrize(
    "model_id",
    [
        "Qwen/Qwen3.8-27B",
        "Qwen/Qwen3.8-2.4T-A95B",
        "deepseek-ai/DeepSeek-V4-Flash-0731",
        "deepseek-ai/DeepSeek-V4-Pro-0813",
        "ibm-granite/granite-4.1-3b",
        "ibm-granite/granite-4.1-8b",
        "ibm-granite/granite-4.1-30b",
        "LiquidAI/LFM2.5-230M",
        "LiquidAI/LFM2.5-350M",
        "LiquidAI/LFM2.5-1.2B-Instruct",
        "LiquidAI/LFM2.5-2.6B",
        "LiquidAI/LFM2.5-8B-A1B",
        "openai/gpt-oss-120b",
        "zai-org/GLM-5.2",
    ],
)
def test_current_verified_models_are_curated(model_id: str) -> None:
    assert model_id in presets.MODEL_PRESETS


def test_qwen38_27b_preset_matches_the_published_model_contract() -> None:
    preset = presets.MODEL_PRESETS["Qwen/Qwen3.8-27B"]

    assert preset.name == "Qwen3.8-27B"
    assert preset.params == "27B"
    assert preset.tier == "large"
    assert preset.recommended_dtype == "bfloat16"
    assert preset.recommended_quantization == "4bit"
    assert preset.gated is False


@pytest.mark.parametrize(
    "size, expected",
    [
        ("1.99B", ("tiny", "1.99B")),
        ("2B", ("small", "2B")),
        ("7.99B", ("small", "7.99B")),
        ("8B", ("medium", "8B")),
        ("15.99B", ("medium", "15.99B")),
        ("16B", ("large", "16B")),
        ("69.9B", ("large", "69.9B")),
        ("70B", ("frontier", "70B")),
    ],
)
def test_tier_boundaries_are_explicit(size: str, expected: tuple[str, str]) -> None:
    assert bestiary_sync._infer_tier_params(f"org/model-{size}", {}) == expected


def test_tier_inference_prefers_total_moe_size_and_fails_heavy_when_unknown() -> None:
    assert bestiary_sync._infer_tier_params("org/MoE-A3B-235B", {}) == (
        "frontier",
        "235B",
    )
    assert bestiary_sync._infer_tier_params("org/model", {"name": "unsized"}) == (
        "large",
        "unknown",
    )


def test_curated_presets_win_and_catalog_duplicates_are_suppressed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = [
        {"hf_id": "curated/model", "name": "curated", "capabilities": []},
        {
            "hf_id": "Meta-Llama/Fresh-70B",
            "name": "Fresh",
            "released": "2026-08-16",
            "capabilities": ["tools", "vision"],
        },
        {"hf_id": "Meta-Llama/Fresh-70B", "name": "duplicate", "capabilities": []},
        {"hf_id": "org/tiny-1B", "capabilities": []},
    ]
    monkeypatch.setattr(models_client, "models", lambda **_kwargs: records)

    presets = bestiary_sync.extra_presets(Preset, {"curated/model"})

    assert [preset.hf_id for preset in presets] == [
        "Meta-Llama/Fresh-70B",
        "org/tiny-1B",
    ]
    assert presets[0].tier == "frontier"
    assert presets[0].recommended_quantization == "4bit"
    assert presets[0].gated is True
    assert presets[0].description == "[BESTIARY · 2026-08-16] tools, vision."
    assert presets[1].name == "tiny-1B"
    assert presets[1].tier == "tiny"
    assert presets[1].recommended_quantization is None
    assert presets[1].description == "[BESTIARY · ?] open-weight."


def test_catalog_or_transformation_failure_is_an_empty_safe_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(**_kwargs):
        raise OSError("offline")

    monkeypatch.setattr(models_client, "models", unavailable)
    assert bestiary_sync.extra_presets(Preset, set()) == []

    for malformed in (
        [None],
        [{"hf_id": 7, "capabilities": []}],
        [{"hf_id": "org/model", "capabilities": "tools"}],
        [{"hf_id": "org/model", "capabilities": [7]}],
        [{"hf_id": "org/model", "name": 7, "capabilities": []}],
        [{"hf_id": "org/model", "released": 7, "capabilities": []}],
    ):
        monkeypatch.setattr(models_client, "models", lambda **_kwargs: malformed)
        assert bestiary_sync.extra_presets(Preset, set()) == []


def test_preset_constructor_failure_does_not_return_partial_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = [
        {"hf_id": "org/valid-7B", "capabilities": []},
        {"hf_id": "org/explode-8B", "capabilities": []},
    ]
    monkeypatch.setattr(models_client, "models", lambda **_kwargs: records)

    class RejectSecond(Preset):
        def __init__(self, **kwargs):
            if kwargs["hf_id"] == "org/explode-8B":
                raise ValueError("rejected")
            super().__init__(**kwargs)

    assert bestiary_sync.extra_presets(RejectSecond, set()) == []


def test_presets_refresh_merges_bestiary_records_without_replacing_curated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    curated_id = next(iter(presets.MODEL_PRESETS))
    curated = presets.MODEL_PRESETS[curated_id]
    discovered = presets.ModelPreset(
        name="Fresh 3B",
        hf_id="example/Fresh-3B",
        description="[BESTIARY · 2026-08-23] text.",
        tier="small",
        params="3B",
        recommended_dtype="bfloat16",
    )
    replacement = presets.ModelPreset(
        name="replacement",
        hf_id=curated_id,
        description="must not win",
        tier="tiny",
        params="1B",
        recommended_dtype="float32",
    )
    seen_existing: set[str] = set()

    def extras(_preset_type, existing: set[str]):
        seen_existing.update(existing)
        return [discovered] if curated_id in existing else [replacement, discovered]

    monkeypatch.setattr(bestiary_sync, "extra_presets", extras)
    try:
        assert presets.refresh_presets_from_bestiary() == 1
        assert curated_id in seen_existing
        assert presets.MODEL_PRESETS[curated_id] is curated
        assert presets.MODEL_PRESETS[discovered.hf_id] is discovered
    finally:
        presets.MODEL_PRESETS.pop(discovered.hf_id, None)
