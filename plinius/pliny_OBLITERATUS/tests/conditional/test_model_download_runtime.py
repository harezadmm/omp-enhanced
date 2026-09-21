"""Pinned, networked tiny-model load plus cache-only replay."""

from __future__ import annotations

import os
import uuid

import pytest
import torch

from obliteratus.architecture_profiles import ArchitectureClass, detect_architecture
from obliteratus.models.loader import _select_model_class, load_model
from transformers import AutoConfig, AutoModelForImageTextToText


pytestmark = [pytest.mark.network, pytest.mark.download]
MODEL = "hf-internal-testing/tiny-random-gpt2"
REVISION = "71034c5d8bde858ff824298bdedc65515b97d2b9"
MISTRAL4_MODEL = "mistralai/Mistral-Small-4-119B-2603"
MISTRAL4_REVISION = "a11f36bebf709121056b1dbcc943d1c6afbe494d"
QWEN38_MODEL = "Qwen/Qwen3.8-27B"


def test_pinned_tiny_model_download_inference_and_offline_cache(monkeypatch):
    handle = load_model(
        MODEL,
        revision=REVISION,
        device="cpu",
        dtype="float32",
        trust_remote_code=False,
        skip_snapshot=True,
    )
    encoded = handle.tokenizer("conditional gate", return_tensors="pt")
    with torch.no_grad():
        output = handle.model(**encoded)
    assert output.logits.shape[:2] == encoded["input_ids"].shape
    assert next(handle.model.parameters()).device.type == "cpu"
    handle.cleanup()

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    cached = load_model(
        MODEL,
        revision=REVISION,
        device="cpu",
        local_files_only=True,
        trust_remote_code=False,
        skip_snapshot=True,
    )
    assert cached.model_name == MODEL
    cached.cleanup()

    missing = f"obliteratus/offline-missing-{uuid.uuid4().hex}"
    with pytest.raises(OSError):
        load_model(missing, revision=REVISION, device="cpu", local_files_only=True)


def test_pinned_mistral4_config_resolves_composite_contract_without_remote_code():
    config = AutoConfig.from_pretrained(
        MISTRAL4_MODEL,
        revision=MISTRAL4_REVISION,
        trust_remote_code=False,
    )

    assert config.model_type == "mistral3"
    assert config.architectures == ["Mistral3ForConditionalGeneration"]
    assert config.text_config.model_type == "mistral4"
    assert config.text_config.n_routed_experts == 128
    assert config.text_config.num_experts_per_tok == 4
    assert _select_model_class("causal_lm", config) is AutoModelForImageTextToText

    profile = detect_architecture(MISTRAL4_MODEL, config=config)
    assert profile.model_type == "mistral4"
    assert profile.arch_class is ArchitectureClass.LARGE_MOE
    assert (profile.num_experts, profile.num_active_experts) == (128, 4)


@pytest.mark.gpu
def test_qwen38_bf16_pristine_baseline_validates_projection_contract(tmp_path):
    """Operator-gated 27B regression: healthy stock model and exact manifest."""
    if os.environ.get("OBLITERATUS_QWEN38_E2E") != "1":
        pytest.skip("set OBLITERATUS_QWEN38_E2E=1 on a >=80 GiB GPU runner")

    from obliteratus.abliterate import AbliterationPipeline

    pipeline = AbliterationPipeline(
        QWEN38_MODEL,
        output_dir=str(tmp_path / "qwen38-output"),
        dtype="bfloat16",
        quantization=None,
    )
    pipeline._summon()
    pipeline._capture_stock_baseline()
    assert pipeline._stock_baseline["perplexity"] > 0
    assert pipeline._stock_baseline["coherence"] > 0
    pipeline._validate_architecture_surgery_support()
    assert len(pipeline._qwen35_projection_manifest) == 64
    assert sum(
        target.mixer_attribute == "linear_attn"
        for target in pipeline._qwen35_projection_manifest
    ) == 48
    assert pipeline._excise_modified_count is None
