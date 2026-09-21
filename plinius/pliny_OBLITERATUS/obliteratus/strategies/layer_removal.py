"""Ablation strategy: remove entire transformer layers one at a time."""

from __future__ import annotations

import torch

from obliteratus.models.loader import ModelHandle
from obliteratus.strategies.base import AblationSpec, AblationStrategy
from obliteratus.strategies.registry import register_strategy
from obliteratus.strategies.utils import get_layer_modules


@register_strategy
class LayerRemovalStrategy(AblationStrategy):
    """Zero-out all parameters of a transformer layer, effectively removing it.

    This is a 'soft' removal — the layer stays in the graph but becomes an
    identity-like pass-through (all weights set to zero, biases set to zero).
    For a harder removal that physically deletes the layer from the module list,
    see `LayerDeletionStrategy` (not yet implemented).
    """

    name = "layer_removal"

    def enumerate(self, handle: ModelHandle, **kwargs) -> list[AblationSpec]:
        specs = []
        for idx in range(handle.num_layers):
            specs.append(
                AblationSpec(
                    strategy_name=self.name,
                    component=f"layer_{idx}",
                    description=f"Zero-out all parameters of transformer layer {idx}",
                    metadata={"layer_idx": idx},
                )
            )
        return specs

    def apply(self, handle: ModelHandle, spec: AblationSpec) -> None:
        layer_idx = spec.metadata["layer_idx"]
        layers = get_layer_modules(handle)
        layer = layers[layer_idx]
        with torch.no_grad():
            for param in layer.parameters():
                param.zero_()
