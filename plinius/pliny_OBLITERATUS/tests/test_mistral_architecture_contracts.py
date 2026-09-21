"""Offline Mistral 3/4 architecture and loader contracts."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
import torch.nn as nn

from obliteratus.architecture_profiles import ArchitectureClass, detect_architecture
from obliteratus.models import loader
from obliteratus.models.loader import ModelHandle
from obliteratus.strategies.utils import (
    get_attention_module,
    get_embedding_module,
    get_ffn_module,
    get_layer_modules,
)


class _MistralLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.self_attn = nn.Module()
        self.mlp = nn.Module()


class _Mistral3ConditionalModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Module()
        self.model.language_model = nn.Module()
        self.model.language_model.layers = nn.ModuleList(
            [_MistralLayer(), _MistralLayer()]
        )
        self.model.language_model.embed_tokens = nn.Embedding(32, 16)


class _BareMistral3Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.language_model = nn.Module()
        self.language_model.layers = nn.ModuleList(
            [_MistralLayer(), _MistralLayer()]
        )
        self.language_model.embed_tokens = nn.Embedding(32, 16)


class _Mistral4CausalModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Module()
        self.model.layers = nn.ModuleList([_MistralLayer(), _MistralLayer()])
        self.model.embed_tokens = nn.Embedding(32, 16)


def _mistral4_text_config():
    return SimpleNamespace(
        model_type="mistral4",
        num_hidden_layers=36,
        num_attention_heads=32,
        hidden_size=4096,
        intermediate_size=12288,
        moe_intermediate_size=2048,
        vocab_size=131072,
        n_routed_experts=128,
        n_shared_experts=1,
        num_experts_per_tok=4,
    )


def _mistral3_config(text_config=None):
    return SimpleNamespace(
        model_type="mistral3",
        architectures=["Mistral3ForConditionalGeneration"],
        text_config=text_config or SimpleNamespace(
            model_type="mistral",
            num_hidden_layers=2,
            num_attention_heads=4,
            hidden_size=16,
            intermediate_size=64,
            vocab_size=32,
        ),
    )


def _handle(model: nn.Module, config, tokenizer=None) -> ModelHandle:
    return ModelHandle(
        model=model,
        tokenizer=tokenizer or SimpleNamespace(pad_token="<pad>", eos_token="<eos>"),
        config=config,
        model_name="mistralai/synthetic-mistral",
        task="causal_lm",
    )


def test_mistral_loader_uses_only_verified_image_text_mappings(monkeypatch):
    causal = object()
    classification = object()
    image_text = object()
    monkeypatch.setitem(loader.TASK_MODEL_MAP, "causal_lm", causal)
    monkeypatch.setitem(loader.TASK_MODEL_MAP, "classification", classification)
    monkeypatch.setattr(loader, "AutoModelForImageTextToText", image_text)

    assert loader._select_model_class("causal_lm", _mistral3_config()) is image_text
    assert loader._select_model_class(
        "causal_lm",
        SimpleNamespace(model_type="mistral4", architectures=["Mistral4ForCausalLM"]),
    ) is image_text
    assert loader._select_model_class("classification", _mistral3_config()) is classification
    assert loader._select_model_class(
        "causal_lm",
        SimpleNamespace(model_type="unknown", architectures=["OtherForConditionalGeneration"]),
    ) is causal


def test_mistral_loader_fails_when_required_transformers_mapping_is_missing(monkeypatch):
    monkeypatch.setattr(loader, "AutoModelForImageTextToText", None)

    with pytest.raises(
        RuntimeError,
        match=r"AutoModelForImageTextToText.*mistral3.*Upgrade transformers",
    ):
        loader._select_model_class("causal_lm", _mistral3_config())


def test_composite_profile_uses_text_backbone_without_misclassifying_mistral3():
    dense = detect_architecture(
        "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        config=_mistral3_config(),
    )
    moe = detect_architecture(
        "mistralai/Mistral-Small-4-119B-2603",
        config=_mistral3_config(_mistral4_text_config()),
    )

    assert dense.model_type == "mistral"
    assert dense.arch_class is ArchitectureClass.DENSE
    assert not dense.is_moe
    assert moe.model_type == "mistral4"
    assert moe.arch_class is ArchitectureClass.LARGE_MOE
    assert moe.is_moe
    assert (moe.num_experts, moe.num_active_experts) == (128, 4)
    assert moe.total_params_b >= 100


def test_composite_memory_estimate_counts_routed_and_shared_experts():
    config = _mistral3_config(_mistral4_text_config())

    estimate_gb = loader._estimate_model_memory_gb(config, torch.bfloat16)

    assert 200 < estimate_gb < 300


def test_mistral_small_4_name_fallback_is_large_moe():
    profile = detect_architecture("mistralai/Mistral-Small-4-119B-2603")

    assert profile.arch_class is ArchitectureClass.LARGE_MOE
    assert profile.is_moe


@pytest.mark.parametrize(
    "model",
    [_Mistral3ConditionalModel(), _BareMistral3Model()],
)
def test_mistral3_navigation_preserves_outer_config_and_tokenizer(model):
    config = _mistral3_config(_mistral4_text_config())
    tokenizer = SimpleNamespace(pad_token="<pad>", eos_token="<eos>")
    handle = _handle(model, config, tokenizer)
    layers = get_layer_modules(handle)

    assert handle.config is config
    assert handle.tokenizer is tokenizer
    assert handle.architecture == "mistral3"
    assert (handle.num_layers, handle.num_heads, handle.hidden_size) == (36, 32, 4096)
    assert len(layers) == 2
    assert get_attention_module(layers[0], handle.architecture) is layers[0].self_attn
    assert get_ffn_module(layers[0], handle.architecture) is layers[0].mlp
    assert get_embedding_module(handle).embedding_dim == 16


def test_direct_mistral4_navigation_uses_causal_wrapper_layout():
    config = _mistral4_text_config()
    handle = _handle(_Mistral4CausalModel(), config)
    layers = get_layer_modules(handle)

    assert handle.architecture == "mistral4"
    assert len(layers) == 2
    assert get_attention_module(layers[0], handle.architecture) is layers[0].self_attn
    assert get_ffn_module(layers[0], handle.architecture) is layers[0].mlp
    assert get_embedding_module(handle).num_embeddings == 32


def test_known_mistral3_layout_mismatch_fails_with_attempted_paths():
    with pytest.raises(
        RuntimeError,
        match=r"known architecture 'mistral3'.*model.language_model.layers.*language_model.layers",
    ):
        get_layer_modules(_handle(nn.Module(), _mistral3_config()))
