"""Fail-closed projection contract for the Qwen3.8-27B text backbone."""

from __future__ import annotations

from dataclasses import dataclass

import torch.nn as nn

from obliteratus.models.loader import ModelHandle
from obliteratus.strategies.utils import get_layer_modules


class Qwen35ContractError(RuntimeError):
    """The loaded Qwen hybrid does not match the validated surgery layout."""


@dataclass(frozen=True)
class Qwen35LayerTargets:
    """Semantic residual-writer targets for one decoder layer."""

    mixer_attribute: str
    mixer_output: str
    ffn_attribute: str = "mlp"
    ffn_output: str = "down_proj"

    @property
    def parameter_names(self) -> frozenset[str]:
        return frozenset(
            {
                f"{self.mixer_attribute}.{self.mixer_output}.weight",
                f"{self.ffn_attribute}.{self.ffn_output}.weight",
            }
        )


_QWEN38_27B_LAYER_TYPES = tuple(
    layer_type
    for _ in range(16)
    for layer_type in ("linear_attention", "linear_attention", "linear_attention", "full_attention")
)


def validate_qwen38_27b_projection_contract(
    handle: ModelHandle,
) -> tuple[Qwen35LayerTargets, ...]:
    """Validate and return the complete Qwen3.8-27B output-writer manifest.

    This intentionally supports only the researched dense 27B topology.  Other
    Qwen3.5/Qwen3.8 sizes, MoE variants, or changed module shapes remain blocked.
    """
    if str(handle.architecture).lower() != "qwen3_5":
        raise Qwen35ContractError(
            f"unsupported Qwen hybrid architecture {handle.architecture!r}"
        )
    model_id = str(getattr(handle, "model_name", "")).rstrip("/").lower()
    if model_id != "qwen/qwen3.8-27b":
        raise Qwen35ContractError(
            "validated Qwen hybrid surgery currently supports only Qwen/Qwen3.8-27B"
        )

    text_config = getattr(handle.config, "text_config", None)
    if text_config is None:
        raise Qwen35ContractError("Qwen3.8-27B is missing its nested text_config")
    layer_types = tuple(getattr(text_config, "layer_types", ()) or ())
    if layer_types != _QWEN38_27B_LAYER_TYPES:
        raise Qwen35ContractError(
            "Qwen3.8-27B layer_types do not match the validated 48 DeltaNet / "
            "16 full-attention topology"
        )
    if (
        getattr(text_config, "hidden_size", None) != 5120
        or getattr(text_config, "intermediate_size", None) != 17408
        or getattr(text_config, "num_hidden_layers", None) != 64
    ):
        raise Qwen35ContractError("Qwen3.8-27B text dimensions do not match the validated contract")

    layers = get_layer_modules(handle)
    if len(layers) != len(layer_types):
        raise Qwen35ContractError(
            f"Qwen3.8-27B exposes {len(layers)} layers; expected {len(layer_types)}"
        )

    targets: list[Qwen35LayerTargets] = []
    for index, (layer, layer_type) in enumerate(zip(layers, layer_types, strict=True)):
        if layer_type == "linear_attention":
            target = Qwen35LayerTargets("linear_attn", "out_proj")
            expected_mixer_shape = (5120, 6144)
        else:
            target = Qwen35LayerTargets("self_attn", "o_proj")
            expected_mixer_shape = (5120, 6144)
        try:
            mixer_output = getattr(getattr(layer, target.mixer_attribute), target.mixer_output)
            ffn_output = getattr(getattr(layer, target.ffn_attribute), target.ffn_output)
        except AttributeError as error:
            raise Qwen35ContractError(
                f"Qwen3.8-27B layer {index} is missing a required residual writer"
            ) from error
        if not isinstance(mixer_output, nn.Linear) or tuple(mixer_output.weight.shape) != expected_mixer_shape:
            raise Qwen35ContractError(
                f"Qwen3.8-27B layer {index} mixer output has unexpected type or shape"
            )
        if not isinstance(ffn_output, nn.Linear) or tuple(ffn_output.weight.shape) != (5120, 17408):
            raise Qwen35ContractError(
                f"Qwen3.8-27B layer {index} MLP output has unexpected type or shape"
            )
        targets.append(target)
    return tuple(targets)
