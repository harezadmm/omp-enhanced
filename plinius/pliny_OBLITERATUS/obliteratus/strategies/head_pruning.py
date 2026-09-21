"""Ablation strategy: zero-out individual attention heads."""

from __future__ import annotations

import torch

from obliteratus.models.loader import ModelHandle
from obliteratus.strategies.base import AblationSpec, AblationStrategy
from obliteratus.strategies.registry import register_strategy
from obliteratus.strategies.utils import get_layer_modules, get_attention_module


@register_strategy
class HeadPruningStrategy(AblationStrategy):
    """Zero-out the Q/K/V projection weights for a specific attention head.

    Works with models that store multi-head attention as a single fused linear
    (GPT-2, LLaMA, Mistral, Falcon, etc.).
    """

    name = "head_pruning"

    def enumerate(self, handle: ModelHandle, **kwargs) -> list[AblationSpec]:
        specs = []
        layer_indices = kwargs.get("layers", range(handle.num_layers))
        for layer_idx in layer_indices:
            for head_idx in range(handle.num_heads):
                specs.append(
                    AblationSpec(
                        strategy_name=self.name,
                        component=f"layer_{layer_idx}_head_{head_idx}",
                        description=(
                            f"Zero-out attention head {head_idx} in layer {layer_idx}"
                        ),
                        metadata={"layer_idx": layer_idx, "head_idx": head_idx},
                    )
                )
        return specs

    def apply(self, handle: ModelHandle, spec: AblationSpec) -> None:
        layer_idx = spec.metadata["layer_idx"]
        head_idx = spec.metadata["head_idx"]
        head_dim = handle.hidden_size // handle.num_heads

        layers = get_layer_modules(handle)
        attn = get_attention_module(layers[layer_idx], handle.architecture)

        start = head_idx * head_dim
        end = start + head_dim

        with torch.no_grad():
            # GPT-2 uses Conv1D (c_attn fuses Q/K/V, shape [in, 3*out])
            c_attn = getattr(attn, "c_attn", None)
            if c_attn is not None and hasattr(c_attn, "weight"):
                # Conv1D weight shape: (in_features, out_features)
                # Q/K/V are stacked: [0:H], [H:2H], [2H:3H] in the out dim
                H = handle.hidden_size
                for offset in (0, H, 2 * H):
                    c_attn.weight.data[:, offset + start : offset + end] = 0.0
                    if c_attn.bias is not None:
                        c_attn.bias.data[offset + start : offset + end] = 0.0

                # Zero out the corresponding output projection slice
                c_proj = getattr(attn, "c_proj", None)
                if c_proj is not None and hasattr(c_proj, "weight"):
                    c_proj.weight.data[start:end, :] = 0.0
                    if c_proj.bias is not None:
                        c_proj.bias.data[:] += 0  # bias is full-size, don't slice
                return

            # Standard architectures: separate Q/K/V projections (LLaMA, Mistral, etc.)
            for proj_name in ("q_proj", "k_proj", "v_proj", "query", "key", "value"):
                proj = getattr(attn, proj_name, None)
                if proj is not None and hasattr(proj, "weight"):
                    proj.weight.data[start:end, :] = 0.0
                    if proj.bias is not None:
                        proj.bias.data[start:end] = 0.0

            # Also zero-out the corresponding output projection slice
            for proj_name in ("o_proj", "out_proj", "dense"):
                proj = getattr(attn, proj_name, None)
                if proj is not None and hasattr(proj, "weight"):
                    proj.weight.data[:, start:end] = 0.0
