"""Contracts for strategy navigation and head/embedding fallback behavior."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from obliteratus.models.loader import ModelHandle
from obliteratus.strategies.base import AblationSpec
from obliteratus.strategies.head_pruning import HeadPruningStrategy
from obliteratus.strategies.utils import (
    get_attention_module,
    get_embedding_module,
    get_ffn_module,
    get_layer_modules,
)


class _DummyTokenizer:
    pad_token = "<pad>"
    eos_token = "<eos>"


class _LlamaLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.self_attn = nn.Module()
        self.self_attn.q_proj = nn.Linear(8, 8, bias=True)
        self.self_attn.k_proj = nn.Linear(8, 8, bias=True)
        self.self_attn.v_proj = nn.Linear(8, 8, bias=True)
        self.self_attn.o_proj = nn.Linear(8, 8, bias=True)
        self.mlp = nn.Module()
        self.mlp.down_proj = nn.Linear(8, 8, bias=True)


class _Qwen35MoeLayer(nn.Module):
    def __init__(self, *, with_primary_attn: bool):
        super().__init__()
        if with_primary_attn:
            self.self_attn = nn.Module()
        else:
            self.linear_attn = nn.Module()
        self.mlp = nn.Module()


class _Qwen35MoeModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Module()
        self.model.layers = nn.ModuleList(
            [_Qwen35MoeLayer(with_primary_attn=True), _Qwen35MoeLayer(with_primary_attn=False)]
        )
        self.model.embed_tokens = nn.Embedding(32, 8)


class _NoEmbeddingModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Module()
        self.model.layers = nn.ModuleList([nn.Module()])


class _NemotronHModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = nn.Module()
        layer = nn.Module()
        layer.mixer = nn.Module()
        self.backbone.layers = nn.ModuleList([layer])


def _handle(model: nn.Module, *, architecture: str, hidden_size: int = 8, num_layers: int = 1, num_heads: int = 2):
    return ModelHandle(
        model=model,
        tokenizer=_DummyTokenizer(),
        config=SimpleNamespace(
            model_type=architecture,
            hidden_size=hidden_size,
            num_hidden_layers=num_layers,
            num_attention_heads=num_heads,
            intermediate_size=hidden_size * 4,
        ),
        model_name="test-model",
        task="causal_lm",
    )


def test_strategy_navigation_resolves_fallback_layers_and_missing_attention():
    handle = _handle(_Qwen35MoeModel(), architecture="qwen3_5_moe", num_layers=2)

    layers = get_layer_modules(handle)
    assert len(layers) == 2
    assert get_attention_module(layers[0], handle.architecture) is layers[0].self_attn
    assert get_attention_module(layers[1], handle.architecture) is layers[1].linear_attn
    assert get_ffn_module(layers[0], handle.architecture) is layers[0].mlp

    broken = nn.Module()
    with pytest.raises(AttributeError):
        get_attention_module(broken, "qwen3_5_moe")


def test_nemotron_h_navigation_uses_backbone_layers_and_mixer():
    handle = _handle(_NemotronHModel(), architecture="nemotron_h")

    layers = get_layer_modules(handle)
    assert layers is handle.model.backbone.layers
    assert get_attention_module(layers[0], handle.architecture) is layers[0].mixer
    assert get_ffn_module(layers[0], handle.architecture) is layers[0].mixer


def test_head_pruning_zeros_qkv_and_output_slices_for_standard_attention():
    model = nn.Module()
    model.model = nn.Module()
    model.model.layers = nn.ModuleList([_LlamaLayer()])
    handle = _handle(model, architecture="llama")

    spec = AblationSpec(
        strategy_name="head_pruning",
        component="layer_0_head_1",
        description="test",
        metadata={"layer_idx": 0, "head_idx": 1},
    )
    HeadPruningStrategy().apply(handle, spec)

    attn = get_attention_module(get_layer_modules(handle)[0], handle.architecture)
    head_dim = handle.hidden_size // handle.num_heads
    start = head_dim
    end = start + head_dim
    for proj_name in ("q_proj", "k_proj", "v_proj"):
        proj = getattr(attn, proj_name)
        assert torch.all(proj.weight[start:end, :] == 0)
        assert torch.all(proj.bias[start:end] == 0)
    assert torch.all(attn.o_proj.weight[:, start:end] == 0)


def test_embedding_navigation_uses_first_embedding_and_fails_without_one():
    handle = _handle(_Qwen35MoeModel(), architecture="qwen3_5_moe")
    assert get_embedding_module(handle) is handle.model.model.embed_tokens

    with pytest.raises(RuntimeError, match="Cannot locate embedding module"):
        get_embedding_module(_handle(_NoEmbeddingModel(), architecture="qwen3_5_moe"))
