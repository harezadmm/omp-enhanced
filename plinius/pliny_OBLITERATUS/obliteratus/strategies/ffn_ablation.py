"""Ablation strategy: zero-out the feed-forward network in a transformer layer."""

from __future__ import annotations

import torch

from obliteratus.models.loader import ModelHandle
from obliteratus.strategies.base import AblationSpec, AblationStrategy
from obliteratus.strategies.registry import register_strategy
from obliteratus.strategies.utils import get_layer_modules, get_ffn_module


@register_strategy
class FFNAblationStrategy(AblationStrategy):
    """Zero-out the MLP / feed-forward block of a specific transformer layer."""

    name = "ffn_ablation"

    def enumerate(self, handle: ModelHandle, **kwargs) -> list[AblationSpec]:
        specs = []
        for idx in range(handle.num_layers):
            specs.append(
                AblationSpec(
                    strategy_name=self.name,
                    component=f"ffn_layer_{idx}",
                    description=f"Zero-out FFN/MLP in layer {idx}",
                    metadata={"layer_idx": idx},
                )
            )
        return specs

    def apply(self, handle: ModelHandle, spec: AblationSpec) -> None:
        layer_idx = spec.metadata["layer_idx"]
        layers = get_layer_modules(handle)
        ffn = get_ffn_module(layers[layer_idx], handle.architecture)
        with torch.no_grad():
            for param in ffn.parameters():
                param.zero_()
