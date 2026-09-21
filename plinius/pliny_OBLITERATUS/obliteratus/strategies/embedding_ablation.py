"""Ablation strategy: zero-out specific embedding dimensions."""

from __future__ import annotations

import torch

from obliteratus.models.loader import ModelHandle
from obliteratus.strategies.base import AblationSpec, AblationStrategy
from obliteratus.strategies.registry import register_strategy
from obliteratus.strategies.utils import get_embedding_module


@register_strategy
class EmbeddingAblationStrategy(AblationStrategy):
    """Zero-out a contiguous range of embedding dimensions.

    By default, ablates one chunk at a time (chunk_size controls the width).
    Useful for understanding which embedding dimensions carry the most information.
    """

    name = "embedding_ablation"

    def enumerate(self, handle: ModelHandle, **kwargs) -> list[AblationSpec]:
        chunk_size = kwargs.get("chunk_size", max(1, handle.hidden_size // 16))
        specs = []
        for start in range(0, handle.hidden_size, chunk_size):
            end = min(start + chunk_size, handle.hidden_size)
            specs.append(
                AblationSpec(
                    strategy_name=self.name,
                    component=f"embed_dims_{start}_{end}",
                    description=f"Zero-out embedding dimensions [{start}:{end})",
                    metadata={"dim_start": start, "dim_end": end},
                )
            )
        return specs

    def apply(self, handle: ModelHandle, spec: AblationSpec) -> None:
        dim_start = spec.metadata["dim_start"]
        dim_end = spec.metadata["dim_end"]
        embed = get_embedding_module(handle)
        with torch.no_grad():
            embed.weight.data[:, dim_start:dim_end] = 0.0
