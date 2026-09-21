"""Sparse Direction Surgery for targeted weight modification.

Standard abliteration projects out the refusal direction from the *entire*
weight matrix, modifying every row equally. But not all rows contribute
equally to the refusal signal. Sparse Direction Surgery identifies and
modifies only the rows with the highest projection onto the refusal
direction, leaving the rest of the weight matrix untouched.

Why this matters:
  - **Reduced collateral damage**: By modifying fewer rows, we preserve
    more of the model's capabilities (factual knowledge, reasoning, etc.)
  - **Better capability retention**: Rows with low refusal projection
    likely encode useful capabilities — leaving them alone avoids damage
  - **Controllable sparsity**: The sparsity parameter lets you dial in
    the tradeoff between refusal removal and capability preservation
  - **Diagnostic value**: The distribution of projections across rows
    reveals whether refusal is "dense" (spread across many neurons) or
    "sparse" (concentrated in a few key neurons)

The approach:
  1. For each weight matrix W, compute per-row projections onto the
     refusal direction r: proj_i = |W[i] · r| / ||r||
  2. Sort rows by projection magnitude
  3. Only modify the top-k% of rows (by projection magnitude)
  4. For modified rows, apply the standard projection: W'[i] = W[i] - (W[i]·r)r

This is inspired by pruning literature (Magnitude pruning, SparseGPT) and
by the observation that safety features, like other learned features, tend
to be encoded in specific neurons rather than distributed uniformly.

Contributions:
  - Application of sparsity-aware direction projection to abliteration
  - Refusal Sparsity Index (RSI): Quantifies how concentrated vs. distributed
    the refusal signal is across weight matrix rows
  - Optimal sparsity estimation based on the "knee" of the projection curve
  - Per-layer sparsity profiles for understanding refusal architecture

References:
    - Frantar & Alistarh (2023): SparseGPT — pruning at scale
    - Arditi et al. (2024): Standard (dense) direction projection
    - Sun et al. (2024): Wanda — pruning without data
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch


@dataclass
class SparseProjectionResult:
    """Result of sparse direction surgery on a single weight matrix."""

    layer_idx: int
    n_rows_total: int
    n_rows_modified: int
    sparsity: float              # fraction of rows modified
    mean_projection: float       # mean |projection| across all rows
    max_projection: float        # max |projection|
    median_projection: float     # median |projection|
    refusal_sparsity_index: float  # RSI: how concentrated the refusal signal is
    projection_gini: float       # Gini coefficient of row projections
    energy_removed: float        # fraction of total refusal energy removed
    frobenius_change: float      # relative change in Frobenius norm


@dataclass
class SparseSurgeryPlan:
    """Plan for sparse surgery across multiple layers."""

    per_layer: dict[int, SparseProjectionResult]
    recommended_sparsity: float       # global recommendation
    mean_refusal_sparsity_index: float
    mean_energy_removed: float
    mean_frobenius_change: float
    most_sparse_layer: int            # layer where refusal is most concentrated
    most_dense_layer: int             # layer where refusal is most distributed


class SparseDirectionSurgeon:
    """Perform sparse direction surgery on weight matrices.

    Instead of modifying all rows of a weight matrix, only modifies
    the rows with the highest projection onto the refusal direction.
    """

    def __init__(
        self,
        sparsity: float = 0.1,
        auto_sparsity: bool = False,
    ):
        """
        Args:
            sparsity: Fraction of rows to modify (0 to 1). Default 0.1 = top 10%.
            auto_sparsity: If True, automatically determine optimal sparsity
                per layer using knee detection.
        """
        self.sparsity = sparsity
        self.auto_sparsity = auto_sparsity

    def analyze_weight_matrix(
        self,
        weight: torch.Tensor,
        refusal_direction: torch.Tensor,
        layer_idx: int = 0,
    ) -> SparseProjectionResult:
        """Analyze the projection distribution of a weight matrix.

        Args:
            weight: (out_dim, in_dim) weight matrix.
            refusal_direction: (in_dim,) refusal direction.
            layer_idx: Layer index for metadata.

        Returns:
            SparseProjectionResult with projection distribution analysis.
        """
        W = weight.float()
        r = refusal_direction.float().squeeze()
        r = r / r.norm().clamp(min=1e-10)

        # Per-row projection magnitudes
        projections = (W @ r).abs()  # (out_dim,)
        n_rows = projections.shape[0]

        sorted_proj, _ = projections.sort(descending=True)

        # Basic statistics
        mean_proj = projections.mean().item()
        max_proj = projections.max().item()
        median_proj = projections.median().item()

        # Determine sparsity
        if self.auto_sparsity:
            sparsity = self._find_knee(sorted_proj)
        else:
            sparsity = self.sparsity

        n_modify = max(1, int(sparsity * n_rows))

        # Energy analysis: what fraction of total projection energy is
        # captured by the top-k rows
        total_energy = (projections ** 2).sum().item()
        top_k_energy = (sorted_proj[:n_modify] ** 2).sum().item()
        energy_removed = top_k_energy / max(total_energy, 1e-10)

        # Compute what the Frobenius norm change would be
        top_indices = projections.argsort(descending=True)[:n_modify]
        delta_norm_sq = 0.0
        for idx in top_indices:
            proj_val = (W[idx] @ r).item()
            delta_norm_sq += proj_val ** 2
        original_norm = W.norm().item()
        fro_change = math.sqrt(delta_norm_sq) / max(original_norm, 1e-10)

        # Refusal Sparsity Index (RSI)
        # Gini of projection magnitudes — high Gini means concentrated
        rsi = self._gini(projections.tolist())

        # Gini coefficient
        proj_gini = rsi

        return SparseProjectionResult(
            layer_idx=layer_idx,
            n_rows_total=n_rows,
            n_rows_modified=n_modify,
            sparsity=sparsity,
            mean_projection=mean_proj,
            max_projection=max_proj,
            median_projection=median_proj,
            refusal_sparsity_index=rsi,
            projection_gini=proj_gini,
            energy_removed=energy_removed,
            frobenius_change=fro_change,
        )

    def plan_surgery(
        self,
        weights: dict[int, torch.Tensor],
        refusal_directions: dict[int, torch.Tensor],
    ) -> SparseSurgeryPlan:
        """Plan sparse surgery across multiple layers.

        Args:
            weights: {layer_idx: weight_matrix} per layer.
            refusal_directions: {layer_idx: refusal_direction} per layer.

        Returns:
            SparseSurgeryPlan with per-layer analysis and recommendations.
        """
        per_layer = {}
        common_layers = set(weights.keys()) & set(refusal_directions.keys())

        for layer_idx in sorted(common_layers):
            per_layer[layer_idx] = self.analyze_weight_matrix(
                weights[layer_idx],
                refusal_directions[layer_idx],
                layer_idx=layer_idx,
            )

        if not per_layer:
            return SparseSurgeryPlan(
                per_layer={},
                recommended_sparsity=self.sparsity,
                mean_refusal_sparsity_index=0.0,
                mean_energy_removed=0.0,
                mean_frobenius_change=0.0,
                most_sparse_layer=0,
                most_dense_layer=0,
            )

        rsis = {k: v.refusal_sparsity_index for k, v in per_layer.items()}
        energies = {k: v.energy_removed for k, v in per_layer.items()}
        fro_changes = {k: v.frobenius_change for k, v in per_layer.items()}

        # Recommend sparsity based on mean RSI
        mean_rsi = sum(rsis.values()) / len(rsis)
        # Higher RSI (more concentrated) -> lower sparsity needed
        recommended = max(0.01, min(0.5, 1.0 - mean_rsi))

        return SparseSurgeryPlan(
            per_layer=per_layer,
            recommended_sparsity=recommended,
            mean_refusal_sparsity_index=mean_rsi,
            mean_energy_removed=sum(energies.values()) / len(energies),
            mean_frobenius_change=sum(fro_changes.values()) / len(fro_changes),
            most_sparse_layer=max(rsis, key=rsis.get),
            most_dense_layer=min(rsis, key=rsis.get),
        )

    def apply_sparse_projection(
        self,
        weight: torch.Tensor,
        refusal_direction: torch.Tensor,
        sparsity: float | None = None,
    ) -> torch.Tensor:
        """Apply sparse direction projection to a weight matrix.

        Only modifies the top-k% of rows by projection magnitude.

        Args:
            weight: (out_dim, in_dim) weight matrix.
            refusal_direction: (in_dim,) refusal direction.
            sparsity: Override sparsity for this call.

        Returns:
            Modified weight matrix with sparse projection applied.
        """
        W = weight.float()
        r = refusal_direction.float().squeeze()
        r = r / r.norm().clamp(min=1e-10)

        projections = (W @ r).abs()
        n_rows = projections.shape[0]

        sp = sparsity if sparsity is not None else self.sparsity
        if self.auto_sparsity and sparsity is None:
            sorted_proj, _ = projections.sort(descending=True)
            sp = self._find_knee(sorted_proj)

        n_modify = max(1, int(sp * n_rows))
        top_indices = projections.argsort(descending=True)[:n_modify]

        # Apply projection only to selected rows
        W_modified = W.clone()
        for idx in top_indices:
            proj_val = (W_modified[idx] @ r)
            W_modified[idx] = W_modified[idx] - proj_val * r

        return W_modified.to(weight.dtype)

    def _find_knee(self, sorted_projections: torch.Tensor) -> float:
        """Find the "knee" in the sorted projection curve.

        Uses the maximum curvature method to find where the sorted
        projection magnitudes transition from "high" to "low".

        Returns:
            Recommended sparsity (fraction of rows above knee).
        """
        n = len(sorted_projections)
        if n < 3:
            return self.sparsity

        vals = sorted_projections.tolist()

        # Normalize to [0, 1] range
        max_val = vals[0]
        if max_val < 1e-10:
            return self.sparsity

        normalized = [v / max_val for v in vals]

        # Find knee using the perpendicular distance to the line
        # from first point to last point
        x0, y0 = 0.0, normalized[0]
        x1, y1 = 1.0, normalized[-1]

        dx = x1 - x0
        dy = y1 - y0
        line_len = math.sqrt(dx * dx + dy * dy)

        if line_len < 1e-10:
            return self.sparsity

        max_dist = 0.0
        knee_idx = 0
        for i in range(1, n - 1):
            x = i / (n - 1)
            y = normalized[i]
            # Perpendicular distance from point to line
            dist = abs(dy * x - dx * y + x1 * y0 - y1 * x0) / line_len
            if dist > max_dist:
                max_dist = dist
                knee_idx = i

        return max(0.01, min(0.5, (knee_idx + 1) / n))

    @staticmethod
    def _gini(values: list[float]) -> float:
        """Compute Gini coefficient."""
        from obliteratus.analysis.utils import gini_coefficient
        return gini_coefficient(values)

    @staticmethod
    def format_analysis(result: SparseProjectionResult) -> str:
        """Format single-layer analysis."""
        lines = []
        lines.append(f"Sparse Direction Surgery — Layer {result.layer_idx}")
        lines.append("=" * 45)
        lines.append("")
        lines.append(f"Total rows: {result.n_rows_total}")
        lines.append(f"Rows to modify: {result.n_rows_modified} ({result.sparsity:.1%})")
        lines.append(f"Refusal Sparsity Index: {result.refusal_sparsity_index:.3f}")
        lines.append(f"Projection Gini: {result.projection_gini:.3f}")
        lines.append("")
        lines.append("Projection stats:")
        lines.append(f"  Max:    {result.max_projection:.4f}")
        lines.append(f"  Mean:   {result.mean_projection:.4f}")
        lines.append(f"  Median: {result.median_projection:.4f}")
        lines.append(f"  Max/Mean ratio: {result.max_projection / max(result.mean_projection, 1e-10):.1f}x")
        lines.append("")
        lines.append(f"Energy removed: {result.energy_removed:.1%} of total refusal energy")
        lines.append(f"Frobenius change: {result.frobenius_change:.4f} (relative)")
        return "\n".join(lines)

    @staticmethod
    def format_plan(plan: SparseSurgeryPlan) -> str:
        """Format surgery plan."""
        lines = []
        lines.append("Sparse Direction Surgery Plan")
        lines.append("=" * 40)
        lines.append("")
        lines.append(f"Layers analyzed: {len(plan.per_layer)}")
        lines.append(f"Recommended sparsity: {plan.recommended_sparsity:.1%}")
        lines.append(f"Mean RSI: {plan.mean_refusal_sparsity_index:.3f}")
        lines.append(f"Mean energy captured: {plan.mean_energy_removed:.1%}")
        lines.append(f"Mean Frobenius change: {plan.mean_frobenius_change:.4f}")
        lines.append(f"Most sparse layer: {plan.most_sparse_layer}")
        lines.append(f"Most dense layer: {plan.most_dense_layer}")
        lines.append("")

        if plan.mean_refusal_sparsity_index > 0.6:
            lines.append(
                "FINDING: Refusal signal is SPARSE — concentrated in few neurons. "
                "Sparse surgery should be highly effective with minimal collateral damage."
            )
        elif plan.mean_refusal_sparsity_index < 0.3:
            lines.append(
                "FINDING: Refusal signal is DENSE — distributed across many neurons. "
                "Sparse surgery may miss significant refusal energy. Consider higher "
                "sparsity or standard dense projection."
            )
        else:
            lines.append(
                "FINDING: Refusal signal has moderate sparsity. Sparse surgery "
                "offers a good tradeoff between precision and effectiveness."
            )

        return "\n".join(lines)
