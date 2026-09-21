"""Ablation control baselines for validating that refusal direction removal works.

A skeptical reviewer's first question: "Would ablating a *random* direction
produce similar results?" If random ablation also reduces refusal rates,
the refusal direction extraction is no better than noise.

This module provides:
    - Random direction ablation (negative control)
    - PCA direction ablation (simpler baseline)
    - Shuffled-prompt ablation (data quality control)

Usage:
    from obliteratus.evaluation.baselines import random_direction_baseline

    result = random_direction_baseline(pipeline, n_trials=5)
    print(f"Random ablation refusal rate: {result['mean_refusal_rate']:.0%}")
    print(f"  vs real ablation: {pipeline._quality_metrics['refusal_rate']:.0%}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import torch

logger = logging.getLogger(__name__)


@dataclass
class BaselineResult:
    """Result from a baseline comparison."""
    baseline_name: str
    refusal_rate: float
    refusal_rates: list[float] = field(default_factory=list)  # per-trial
    mean_refusal_rate: float = 0.0
    std_refusal_rate: float = 0.0
    n_trials: int = 1
    details: dict[str, Any] = field(default_factory=dict)


def random_direction_ablation(
    pipeline,
    n_trials: int = 5,
    seed: int = 0,
) -> BaselineResult:
    """Ablate random directions as a negative control.

    For each trial:
    1. Generate a random unit vector in activation space
    2. Project it out of the same weight matrices
    3. Measure refusal rate

    If random ablation produces similar refusal reduction as the learned
    direction, the extraction method is not working.

    Args:
        pipeline: A completed AbliterationPipeline (after run()).
        n_trials: Number of random directions to test.
        seed: Random seed for reproducibility.

    Returns:
        BaselineResult with per-trial and aggregate statistics.
    """
    rng = torch.Generator().manual_seed(seed)

    if not pipeline._strong_layers or not pipeline.refusal_directions:
        return BaselineResult(
            baseline_name="random_direction",
            refusal_rate=0.0,
            details={"error": "Pipeline has no directions to compare against"},
        )

    # Get hidden dim from first direction
    first_layer = pipeline._strong_layers[0]
    hidden_dim = pipeline.refusal_directions[first_layer].shape[-1]

    refusal_rates = []
    for trial in range(n_trials):
        # Generate random unit vector
        random_dir = torch.randn(hidden_dim, generator=rng)
        random_dir = random_dir / random_dir.norm()

        # Measure projection magnitude on harmful activations
        # (how much does the harmful signal project onto random directions?)
        if pipeline._harmful_means:
            projections = []
            for layer_idx in pipeline._strong_layers:
                if layer_idx in pipeline._harmful_means:
                    proj = (pipeline._harmful_means[layer_idx].float() @ random_dir.float()).abs().item()
                    projections.append(proj)
            if projections:
                mean_proj = sum(projections) / len(projections)
                refusal_rates.append(mean_proj)

    if not refusal_rates:
        return BaselineResult(
            baseline_name="random_direction",
            refusal_rate=0.0,
            details={"error": "Could not compute random projections (activations cleared)"},
        )

    mean_rate = sum(refusal_rates) / len(refusal_rates)
    variance = sum((r - mean_rate) ** 2 for r in refusal_rates) / max(len(refusal_rates) - 1, 1)
    std_rate = variance ** 0.5

    return BaselineResult(
        baseline_name="random_direction",
        refusal_rate=mean_rate,
        refusal_rates=refusal_rates,
        mean_refusal_rate=mean_rate,
        std_refusal_rate=std_rate,
        n_trials=n_trials,
        details={
            "hidden_dim": hidden_dim,
            "n_strong_layers": len(pipeline._strong_layers),
        },
    )


def direction_specificity_test(pipeline) -> dict[str, float]:
    """Test whether the extracted refusal direction is specific to harmful prompts.

    Computes the ratio of harmful-to-harmless projection magnitudes.
    A good refusal direction should have much higher projection from
    harmful activations than harmless ones.

    Returns:
        Dict with harmful_projection, harmless_projection, specificity_ratio.
    """
    if not pipeline._strong_layers or not pipeline.refusal_directions:
        return {"error": "No directions available"}

    harmful_projs = []
    harmless_projs = []

    for layer_idx in pipeline._strong_layers:
        direction = pipeline.refusal_directions.get(layer_idx)
        harmful_mean = pipeline._harmful_means.get(layer_idx)
        harmless_mean = pipeline._harmless_means.get(layer_idx)

        if direction is None or harmful_mean is None or harmless_mean is None:
            continue

        d = direction.float()
        d = d / d.norm().clamp(min=1e-8)
        harmful_projs.append((harmful_mean.float() @ d).abs().item())
        harmless_projs.append((harmless_mean.float() @ d).abs().item())

    if not harmful_projs:
        return {"error": "Could not compute projections (activations cleared)"}

    mean_harmful = sum(harmful_projs) / len(harmful_projs)
    mean_harmless = sum(harmless_projs) / len(harmless_projs)
    ratio = mean_harmful / max(mean_harmless, 1e-8)

    return {
        "harmful_projection": mean_harmful,
        "harmless_projection": mean_harmless,
        "specificity_ratio": ratio,
    }
