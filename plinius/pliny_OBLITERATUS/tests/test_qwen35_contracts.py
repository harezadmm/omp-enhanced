"""Contracts for the explicitly supported Qwen3.8-27B residual writers."""

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from obliteratus.abliterate import AbliterationPipeline
from obliteratus.models.qwen35_contracts import (
    Qwen35LayerTargets,
    Qwen35ContractError,
    validate_qwen38_27b_projection_contract,
)


class _LinearAttentionLayer(nn.Module):
    def __init__(self):
        super().__init__()
        with torch.device("meta"):
            self.linear_attn = nn.Module()
            self.linear_attn.out_proj = nn.Linear(6144, 5120, bias=False)
            self.linear_attn.in_proj_qkv = nn.Linear(5120, 10240, bias=False)
            self.linear_attn.in_proj_z = nn.Linear(5120, 6144, bias=False)
            self.mlp = nn.Module()
            self.mlp.down_proj = nn.Linear(17408, 5120, bias=False)
            self.mlp.gate_proj = nn.Linear(5120, 17408, bias=False)
            self.mlp.up_proj = nn.Linear(5120, 17408, bias=False)


class _FullAttentionLayer(nn.Module):
    def __init__(self):
        super().__init__()
        with torch.device("meta"):
            self.self_attn = nn.Module()
            self.self_attn.o_proj = nn.Linear(6144, 5120, bias=False)
            self.self_attn.q_proj = nn.Linear(5120, 12288, bias=False)
            self.self_attn.k_proj = nn.Linear(5120, 1024, bias=False)
            self.self_attn.v_proj = nn.Linear(5120, 1024, bias=False)
            self.mlp = nn.Module()
            self.mlp.down_proj = nn.Linear(17408, 5120, bias=False)
            self.mlp.gate_proj = nn.Linear(5120, 17408, bias=False)
            self.mlp.up_proj = nn.Linear(5120, 17408, bias=False)


def _handle():
    layer_types = [
        layer_type
        for _ in range(16)
        for layer_type in (
            "linear_attention",
            "linear_attention",
            "linear_attention",
            "full_attention",
        )
    ]
    layers = nn.ModuleList(
        _LinearAttentionLayer() if kind == "linear_attention" else _FullAttentionLayer()
        for kind in layer_types
    )
    text_config = SimpleNamespace(
        layer_types=layer_types,
        hidden_size=5120,
        intermediate_size=17408,
        num_hidden_layers=64,
    )
    return SimpleNamespace(
        architecture="qwen3_5",
        model_name="Qwen/Qwen3.8-27B",
        config=SimpleNamespace(text_config=text_config),
        model=SimpleNamespace(model=SimpleNamespace(layers=layers)),
        num_layers=64,
    )


def test_qwen38_manifest_contains_only_residual_writers():
    targets = validate_qwen38_27b_projection_contract(_handle())

    assert len(targets) == 64
    assert sum(target.mixer_attribute == "linear_attn" for target in targets) == 48
    assert sum(target.mixer_attribute == "self_attn" for target in targets) == 16
    assert targets[0].parameter_names == frozenset(
        {"linear_attn.out_proj.weight", "mlp.down_proj.weight"}
    )
    assert targets[3].parameter_names == frozenset(
        {"self_attn.o_proj.weight", "mlp.down_proj.weight"}
    )
    forbidden = {
        "in_proj_qkv",
        "in_proj_z",
        "q_proj",
        "k_proj",
        "v_proj",
        "gate_proj",
        "up_proj",
        "lm_head",
    }
    assert all(
        not any(name in parameter for name in forbidden)
        for target in targets
        for parameter in target.parameter_names
    )


def test_qwen38_manifest_fails_closed_on_topology_change():
    handle = _handle()
    handle.config.text_config.layer_types[0] = "full_attention"

    with pytest.raises(Qwen35ContractError, match="48 DeltaNet"):
        validate_qwen38_27b_projection_contract(handle)


def test_qwen38_manifest_fails_closed_on_writer_shape_change():
    handle = _handle()
    with torch.device("meta"):
        handle.model.model.layers[0].linear_attn.out_proj = nn.Linear(5120, 5120, bias=False)

    with pytest.raises(Qwen35ContractError, match="unexpected type or shape"):
        validate_qwen38_27b_projection_contract(handle)


def test_qwen_output_only_projection_preserves_forbidden_tensors_bit_exactly():
    torch.manual_seed(7)
    layer = nn.Module()
    layer.linear_attn = nn.Module()
    layer.linear_attn.out_proj = nn.Linear(4, 4, bias=False)
    layer.linear_attn.in_proj_qkv = nn.Linear(4, 8, bias=False)
    layer.linear_attn.in_proj_z = nn.Linear(4, 4, bias=False)
    layer.mlp = nn.Module()
    layer.mlp.down_proj = nn.Linear(8, 4, bias=False)
    layer.mlp.gate_proj = nn.Linear(4, 8, bias=False)
    layer.mlp.up_proj = nn.Linear(4, 8, bias=False)
    target = Qwen35LayerTargets("linear_attn", "out_proj")
    forbidden_before = {
        name: parameter.detach().clone()
        for name, parameter in layer.named_parameters()
        if name not in target.parameter_names
    }
    allowed_before = {
        name: parameter.detach().clone()
        for name, parameter in layer.named_parameters()
        if name in target.parameter_names
    }
    direction = torch.tensor([[1.0], [0.0], [0.0], [0.0]])

    saved_norms = AbliterationPipeline._capture_layer_weight_norms(
        layer, parameter_names=target.parameter_names
    )
    AbliterationPipeline._project_out_advanced(
        layer.linear_attn,
        direction,
        [target.mixer_output],
        norm_preserve=False,
    )
    AbliterationPipeline._project_out_advanced(
        layer.mlp,
        direction,
        [target.ffn_output],
        norm_preserve=False,
    )
    AbliterationPipeline._restore_layer_weight_norms(layer, saved_norms)

    current = dict(layer.named_parameters())
    assert all(torch.equal(current[name], value) for name, value in forbidden_before.items())
    assert all(not torch.equal(current[name], value) for name, value in allowed_before.items())


def test_qwen_excise_route_does_not_touch_inputs_gates_or_lm_head():
    torch.manual_seed(11)
    layer = nn.Module()
    layer.linear_attn = nn.Module()
    layer.linear_attn.out_proj = nn.Linear(4, 4, bias=False)
    layer.linear_attn.in_proj_qkv = nn.Linear(4, 8, bias=False)
    layer.linear_attn.in_proj_z = nn.Linear(4, 4, bias=False)
    layer.mlp = nn.Module()
    layer.mlp.down_proj = nn.Linear(8, 4, bias=False)
    layer.mlp.gate_proj = nn.Linear(4, 8, bias=False)
    layer.mlp.up_proj = nn.Linear(4, 8, bias=False)
    model = nn.Module()
    model.model = nn.Module()
    model.model.layers = nn.ModuleList([layer])
    model.lm_head = nn.Linear(4, 16, bias=False)
    handle = SimpleNamespace(
        architecture="qwen3_5",
        config=SimpleNamespace(num_attention_heads=1),
        model=model,
        num_layers=1,
    )
    pipeline = AbliterationPipeline(
        model_name="Qwen/Qwen3.8-27B",
        method="advanced",
        projection_target="all",
    )
    pipeline.handle = handle
    pipeline._qwen35_projection_manifest = (
        Qwen35LayerTargets("linear_attn", "out_proj"),
    )
    pipeline._strong_layers = [0]
    pipeline.refusal_subspaces = {
        0: torch.tensor([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
    }
    pipeline.refusal_directions = {0: pipeline.refusal_subspaces[0][0]}
    pipeline._layer_excise_weights = {}
    pipeline._on_log = lambda _message: None
    before = {name: value.detach().clone() for name, value in model.named_parameters()}

    pipeline._excise()

    after = dict(model.named_parameters())
    allowed = {
        "model.layers.0.linear_attn.out_proj.weight",
        "model.layers.0.mlp.down_proj.weight",
    }
    assert all(not torch.equal(after[name], before[name]) for name in allowed)
    assert all(
        torch.equal(after[name], before[name])
        for name in before.keys() - allowed
    )
    assert pipeline._effective_refinement_passes == 1
    method_config = pipeline._build_metadata()["method_config"]
    assert method_config["refinement_passes"] == 1
    assert method_config["requested_refinement_passes"] == 2


@pytest.mark.parametrize("architecture", ["qwen3_5_text", "qwen3_5_moe"])
def test_other_qwen35_variants_remain_blocked(architecture):
    handle = _handle()
    handle.architecture = architecture

    with pytest.raises(Qwen35ContractError, match="unsupported Qwen hybrid architecture"):
        validate_qwen38_27b_projection_contract(handle)
