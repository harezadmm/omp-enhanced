"""Hyperparameter sweep runner for ablation studies.

Systematically varies abliteration hyperparameters to answer:
  - Does n_directions=4 actually outperform n_directions=1?
  - Does regularization help or hurt?
  - How many refinement passes are needed before diminishing returns?
  - Is whitened SVD actually better than standard SVD?

Usage:
    from obliteratus.sweep import run_sweep, SweepConfig

    config = SweepConfig(
        model_name="meta-llama/Llama-3.1-8B-Instruct",
        sweep_params={
            "n_directions": [1, 2, 4, 8],
            "regularization": [0.0, 0.1, 0.3],
        },
        # Fixed params for all runs:
        fixed_params={"norm_preserve": True, "method": "advanced"},
    )
    results = run_sweep(config)
    results.to_csv("sweep_results.csv")
"""

from __future__ import annotations

import itertools
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SweepConfig:
    """Configuration for a hyperparameter sweep."""
    model_name: str
    sweep_params: dict[str, list[Any]]
    fixed_params: dict[str, Any] = field(default_factory=dict)
    output_dir: str = "sweep_results"
    seed: int = 42
    n_seeds: int = 1  # run each config with multiple seeds for variance


@dataclass
class SweepResult:
    """Results from a single sweep configuration."""
    params: dict[str, Any]
    seed: int
    quality_metrics: dict[str, Any]
    stage_durations: dict[str, float]
    strong_layers: list[int]
    error: str | None = None


def _param_grid(sweep_params: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Generate all combinations of sweep parameters."""
    keys = sorted(sweep_params.keys())
    values = [sweep_params[k] for k in keys]
    configs = []
    for combo in itertools.product(*values):
        configs.append(dict(zip(keys, combo)))
    return configs


def run_sweep(config: SweepConfig) -> list[SweepResult]:
    """Run a hyperparameter sweep over abliteration configurations.

    For each combination of sweep_params (crossed with n_seeds random seeds),
    runs the full abliteration pipeline and records quality metrics.

    Args:
        config: SweepConfig specifying the sweep grid.

    Returns:
        List of SweepResult, one per (param_config, seed) pair.
    """
    from obliteratus.abliterate import AbliterationPipeline

    grid = _param_grid(config.sweep_params)
    total_runs = len(grid) * config.n_seeds
    logger.info("Sweep: %d configs x %d seeds = %d total runs", len(grid), config.n_seeds, total_runs)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[SweepResult] = []
    for run_idx, (params, seed_offset) in enumerate(
        itertools.product(grid, range(config.n_seeds))
    ):
        seed = config.seed + seed_offset
        run_params = {**config.fixed_params, **params}
        logger.info(
            "[%d/%d] params=%s seed=%d",
            run_idx + 1, total_runs, params, seed,
        )

        try:
            pipeline = AbliterationPipeline(
                model_name=config.model_name,
                output_dir=str(output_dir / f"run_{run_idx:03d}"),
                seed=seed,
                **run_params,
            )
            pipeline.run()

            result = SweepResult(
                params=params,
                seed=seed,
                quality_metrics=dict(pipeline._quality_metrics),
                stage_durations=dict(pipeline._stage_durations),
                strong_layers=list(pipeline._strong_layers),
            )
        except Exception as e:
            logger.error("Run %d failed: %s", run_idx, e)
            result = SweepResult(
                params=params,
                seed=seed,
                quality_metrics={},
                stage_durations={},
                strong_layers=[],
                error=str(e),
            )

        results.append(result)

        # Save incremental results
        _save_results(results, output_dir / "sweep_results.json")

    return results


def _save_results(results: list[SweepResult], path: Path) -> None:
    """Save sweep results to JSON."""
    data = []
    for r in results:
        data.append({
            "params": r.params,
            "seed": r.seed,
            "quality_metrics": r.quality_metrics,
            "stage_durations": r.stage_durations,
            "strong_layers": r.strong_layers,
            "error": r.error,
        })
    path.write_text(json.dumps(data, indent=2, default=str))
