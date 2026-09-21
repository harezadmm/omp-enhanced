"""Bayesian-Optimized Kernel Projection for refusal direction extraction.

Heretic (p-e-w, 2025) demonstrated that Bayesian optimization over
abliteration hyperparameters (layer ranges, projection weights, direction
indices) dramatically reduces KL divergence compared to fixed presets.

This module implements a similar approach: instead of using fixed
hyperparameters for direction extraction and projection, it uses
Tree-structured Parzen Estimator (TPE) style optimization to search
over a combinatorial space of:

  1. Layer range: which layers to include in direction extraction
  2. Per-layer projection weights: how much to project at each layer
  3. Direction selection: which SVD components to use per layer
  4. Regularization strength: per-layer regularization

The objective function balances refusal removal effectiveness against
capability preservation (measured by KL divergence or reconstruction
error on harmless prompts).

Unlike Heretic, which requires model inference in the optimization loop,
this implementation works on pre-collected activations, making each
trial fast enough for hundreds of evaluations.

References:
    - p-e-w (2025): Heretic — Automated abliteration via dual-objective
      optimization (GitHub: p-e-w/heretic)
    - Bergstra et al. (2011): Algorithms for Hyper-Parameter Optimization
      (TPE algorithm)
    - Optuna (2019): A Next-generation Hyperparameter Optimization Framework
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

import torch

logger = logging.getLogger(__name__)


@dataclass
class ProjectionConfig:
    """A single trial configuration for kernel projection."""

    layer_range: tuple[int, int]            # (start, end) inclusive
    per_layer_weights: dict[int, float]     # projection weight per layer [0, 1]
    n_directions: int                       # SVD directions to use
    regularization: float                   # L2 regularization strength
    norm_preserve: bool                     # whether to preserve norms


@dataclass
class TrialResult:
    """Result of evaluating a single projection configuration."""

    config: ProjectionConfig
    refusal_reduction: float       # fraction of refusal signal removed
    harmless_distortion: float     # distortion on harmless inputs (lower=better)
    combined_score: float          # weighted objective value
    trial_idx: int


@dataclass
class BayesianOptimizationResult:
    """Full result of Bayesian optimization over projection configs."""

    best_config: ProjectionConfig
    best_score: float
    best_refusal_reduction: float
    best_harmless_distortion: float

    n_trials: int
    all_trials: list[TrialResult]

    # Analysis
    pareto_configs: list[TrialResult]  # Pareto-optimal configs
    layer_importance: dict[int, float]  # inferred per-layer importance


class BayesianKernelProjection:
    """Bayesian optimization over abliteration projection hyperparameters.

    Uses a TPE-inspired search to find the projection configuration that
    best balances refusal removal against capability preservation.
    """

    def __init__(
        self,
        n_trials: int = 100,
        refusal_weight: float = 0.6,
        distortion_weight: float = 0.4,
        seed: int = 42,
    ):
        """
        Args:
            n_trials: Number of optimization trials.
            refusal_weight: Weight for refusal reduction in the objective (w_1).
            distortion_weight: Weight for distortion penalty (w_2).
            seed: Random seed for reproducibility.
        """
        self.n_trials = n_trials
        self.refusal_weight = refusal_weight
        self.distortion_weight = distortion_weight
        self.seed = seed

    def optimize(
        self,
        harmful_acts: dict[int, list[torch.Tensor]],
        harmless_acts: dict[int, list[torch.Tensor]],
        refusal_directions: dict[int, torch.Tensor],
        max_directions: int = 8,
    ) -> BayesianOptimizationResult:
        """Run Bayesian optimization over projection configurations.

        Args:
            harmful_acts: {layer_idx: [activations]} from harmful prompts.
            harmless_acts: {layer_idx: [activations]} from harmless prompts.
            refusal_directions: {layer_idx: direction} per-layer refusal directions.
            max_directions: Maximum number of SVD directions to consider.

        Returns:
            BayesianOptimizationResult with the optimal configuration.
        """
        random.seed(self.seed)
        torch.manual_seed(self.seed)

        layers = sorted(set(harmful_acts.keys()) & set(harmless_acts.keys()) & set(refusal_directions.keys()))
        n_layers = len(layers)

        if n_layers == 0:
            return BayesianOptimizationResult(
                best_config=ProjectionConfig(
                    layer_range=(0, 0), per_layer_weights={}, n_directions=1,
                    regularization=0.0, norm_preserve=True,
                ),
                best_score=0.0,
                best_refusal_reduction=0.0,
                best_harmless_distortion=0.0,
                n_trials=0,
                all_trials=[],
                pareto_configs=[],
                layer_importance={},
            )

        # Pre-compute per-layer statistics for fast trial evaluation
        layer_stats = self._precompute_stats(harmful_acts, harmless_acts, refusal_directions, layers)

        # Phase 1: Random exploration (first 30% of trials)
        n_explore = max(int(self.n_trials * 0.3), 10)
        trials = []

        for i in range(n_explore):
            config = self._random_config(layers, max_directions)
            result = self._evaluate_trial(config, layer_stats, layers, i)
            trials.append(result)

        # Phase 2: TPE-inspired exploitation (remaining trials)
        for i in range(n_explore, self.n_trials):
            config = self._tpe_sample(trials, layers, max_directions)
            result = self._evaluate_trial(config, layer_stats, layers, i)
            trials.append(result)

        # Find best
        best = min(trials, key=lambda t: t.combined_score)

        # Pareto front
        pareto = self._pareto_front(trials)

        # Layer importance: how often each layer appears in top-10 configs
        top_10 = sorted(trials, key=lambda t: t.combined_score)[:max(10, len(trials) // 10)]
        layer_importance = {}
        for ly in layers:
            count = sum(
                1 for t in top_10
                if t.config.per_layer_weights.get(ly, 0) > 0.3
            )
            layer_importance[ly] = count / len(top_10)

        return BayesianOptimizationResult(
            best_config=best.config,
            best_score=best.combined_score,
            best_refusal_reduction=best.refusal_reduction,
            best_harmless_distortion=best.harmless_distortion,
            n_trials=len(trials),
            all_trials=trials,
            pareto_configs=pareto,
            layer_importance=layer_importance,
        )

    def _precompute_stats(
        self,
        harmful_acts: dict[int, list[torch.Tensor]],
        harmless_acts: dict[int, list[torch.Tensor]],
        refusal_directions: dict[int, torch.Tensor],
        layers: list[int],
    ) -> dict:
        """Pre-compute per-layer statistics for fast trial evaluation."""
        stats = {}
        for ly in layers:
            H = torch.stack([a.squeeze() for a in harmful_acts[ly]]).float()
            B = torch.stack([a.squeeze() for a in harmless_acts[ly]]).float()
            r = refusal_directions[ly].float().squeeze()
            r = r / r.norm().clamp(min=1e-10)

            # Refusal projections
            harm_projs = H @ r  # (n_harm,)
            safe_projs = B @ r  # (n_safe,)

            # Refusal signal strength
            refusal_signal = (harm_projs.mean() - safe_projs.mean()).abs().item()

            # Harmless variance along this direction
            safe_var = safe_projs.var().item()

            # Harmless activation norms
            safe_norms = B.norm(dim=1)
            mean_safe_norm = safe_norms.mean().item()

            stats[ly] = {
                "refusal_signal": refusal_signal,
                "safe_variance": safe_var,
                "mean_safe_norm": mean_safe_norm,
                "direction": r,
            }

        return stats

    def _evaluate_trial(
        self,
        config: ProjectionConfig,
        layer_stats: dict,
        layers: list[int],
        trial_idx: int,
    ) -> TrialResult:
        """Evaluate a single projection configuration."""
        total_refusal_removed = 0.0
        total_refusal_available = 0.0
        total_distortion = 0.0

        start, end = config.layer_range
        active_layers = [ly for ly in layers if start <= ly <= end]

        for ly in active_layers:
            if ly not in layer_stats:
                continue

            w = config.per_layer_weights.get(ly, 0.0)
            if w < 1e-6:
                continue

            st = layer_stats[ly]
            refusal = st["refusal_signal"]
            safe_var = st["safe_variance"]
            safe_norm = st["mean_safe_norm"]

            # Refusal removed at this layer (proportional to weight)
            removed = refusal * w
            total_refusal_removed += removed
            total_refusal_available += refusal

            # Distortion: projecting out causes distortion proportional to
            # the variance along the direction in harmless activations
            # Regularization reduces distortion at cost of less refusal removal
            reg = config.regularization
            distortion = w * safe_var / max(safe_norm ** 2, 1e-10) * (1.0 - reg)
            total_distortion += distortion

        # Normalize
        if total_refusal_available > 0:
            refusal_reduction = total_refusal_removed / total_refusal_available
        else:
            refusal_reduction = 0.0

        # Combined objective: minimize (1 - refusal_reduction) * w1 + distortion * w2
        score = (
            self.refusal_weight * (1.0 - refusal_reduction)
            + self.distortion_weight * total_distortion
        )

        return TrialResult(
            config=config,
            refusal_reduction=refusal_reduction,
            harmless_distortion=total_distortion,
            combined_score=score,
            trial_idx=trial_idx,
        )

    def _random_config(
        self, layers: list[int], max_directions: int,
    ) -> ProjectionConfig:
        """Generate a random projection configuration."""
        n_layers = len(layers)

        # Random layer range
        start_idx = random.randint(0, n_layers - 1)
        end_idx = random.randint(start_idx, n_layers - 1)
        start = layers[start_idx]
        end = layers[end_idx]

        # Random per-layer weights
        weights = {}
        for ly in layers:
            if start <= ly <= end:
                weights[ly] = random.uniform(0.0, 1.0)
            else:
                weights[ly] = 0.0

        n_dirs = random.randint(1, max_directions)
        reg = random.uniform(0.0, 0.5)
        norm_preserve = random.choice([True, False])

        return ProjectionConfig(
            layer_range=(start, end),
            per_layer_weights=weights,
            n_directions=n_dirs,
            regularization=reg,
            norm_preserve=norm_preserve,
        )

    def _tpe_sample(
        self,
        trials: list[TrialResult],
        layers: list[int],
        max_directions: int,
    ) -> ProjectionConfig:
        """TPE-inspired sampling: bias towards configurations similar to good trials."""
        n_layers = len(layers)

        # Split trials into good (bottom 25%) and bad (top 75%)
        sorted_trials = sorted(trials, key=lambda t: t.combined_score)
        n_good = max(1, len(sorted_trials) // 4)
        good_trials = sorted_trials[:n_good]

        # Sample layer range from good trials (with some noise)
        ref = random.choice(good_trials).config
        try:
            ref_start_idx = layers.index(ref.layer_range[0])
        except ValueError:
            ref_start_idx = 0
        try:
            ref_end_idx = layers.index(ref.layer_range[1])
        except ValueError:
            ref_end_idx = n_layers - 1
        start_idx = max(0, min(n_layers - 1, ref_start_idx + random.randint(-1, 1)))
        end_idx = max(0, min(n_layers - 1, ref_end_idx + random.randint(-1, 1)))
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        start = layers[start_idx]
        end = layers[end_idx]

        # Sample per-layer weights from good trial weights + noise
        weights = {}
        for ly in layers:
            if start <= ly <= end:
                base = ref.per_layer_weights.get(ly, 0.5)
                w = max(0.0, min(1.0, base + random.gauss(0, 0.15)))
                weights[ly] = w
            else:
                weights[ly] = 0.0

        n_dirs = max(1, min(max_directions, ref.n_directions + random.randint(-1, 1)))
        reg = max(0.0, min(0.5, ref.regularization + random.gauss(0, 0.05)))
        norm_preserve = ref.norm_preserve if random.random() > 0.2 else (not ref.norm_preserve)

        return ProjectionConfig(
            layer_range=(start, end),
            per_layer_weights=weights,
            n_directions=n_dirs,
            regularization=reg,
            norm_preserve=norm_preserve,
        )

    def _pareto_front(self, trials: list[TrialResult]) -> list[TrialResult]:
        """Extract Pareto-optimal trials (refusal reduction vs distortion)."""
        pareto = []
        sorted_by_refusal = sorted(trials, key=lambda t: -t.refusal_reduction)

        best_distortion = float('inf')
        for t in sorted_by_refusal:
            if t.harmless_distortion < best_distortion:
                pareto.append(t)
                best_distortion = t.harmless_distortion

        return pareto

    @staticmethod
    def format_report(result: BayesianOptimizationResult) -> str:
        """Format Bayesian optimization results."""
        lines = []
        lines.append("Bayesian-Optimized Kernel Projection")
        lines.append("=" * 38)
        lines.append("")
        lines.append(f"Trials run: {result.n_trials}")
        lines.append(f"Best score: {result.best_score:.6f}")
        lines.append(f"Best refusal reduction: {result.best_refusal_reduction:.1%}")
        lines.append(f"Best harmless distortion: {result.best_harmless_distortion:.6f}")
        lines.append("")

        bc = result.best_config
        lines.append("Best configuration:")
        lines.append(f"  Layer range: {bc.layer_range[0]} - {bc.layer_range[1]}")
        lines.append(f"  Directions: {bc.n_directions}")
        lines.append(f"  Regularization: {bc.regularization:.4f}")
        lines.append(f"  Norm preserve: {bc.norm_preserve}")
        lines.append("  Per-layer weights:")
        for ly in sorted(bc.per_layer_weights.keys()):
            w = bc.per_layer_weights[ly]
            if w > 0.01:
                lines.append(f"    Layer {ly:3d}: {w:.3f}")
        lines.append("")

        lines.append(f"Pareto-optimal configs: {len(result.pareto_configs)}")
        if result.pareto_configs:
            lines.append("  Refusal ↑     Distortion ↓")
            for p in result.pareto_configs[:5]:
                lines.append(
                    f"  {p.refusal_reduction:6.1%}        {p.harmless_distortion:.6f}"
                )
        lines.append("")

        if result.layer_importance:
            lines.append("Layer importance (fraction of top configs using each layer):")
            for ly in sorted(result.layer_importance.keys()):
                imp = result.layer_importance[ly]
                bar = "#" * int(imp * 20)
                lines.append(f"  Layer {ly:3d}: {imp:.2f} {bar}")

        return "\n".join(lines)
