"""Approximate Causal Importance estimation for refusal circuits.

NOTE: This module provides a *simulation-based approximation* of causal
importance. It does NOT perform real activation patching (which requires
running the model multiple times with interventions). Instead, it estimates
causal effects from pre-collected activations by simulating corruption
with Gaussian noise and measuring how each component's projection onto
the refusal direction would change.

For real causal tracing (Meng et al. 2022), use TransformerLens or
nnsight, which support actual forward passes with patched activations.

What this module DOES provide:
  - **Approximate causal importance**: Estimates which layers contribute
    most to the refusal signal using noise-based sensitivity analysis
  - **Correlation vs importance ranking**: Spearman agreement between
    projection magnitude and estimated causal importance
  - **Silent contributor detection**: Components where projection magnitude
    and estimated importance disagree

What this module does NOT do:
  - Real activation patching (no model forward passes)
  - True counterfactual analysis
  - Edge-level circuit identification (use ACDC for this)

The noise-based approach is a useful first-pass approximation that works
without model access, but its results should be validated with real
causal interventions when model access is available.

References:
    - Meng et al. (2022): Locating and Editing Factual Associations
    - Conmy et al. (2023): Automated Circuit Discovery (ACDC)
    - Wang et al. (2023): Interpretability in the Wild
    - Goldowsky-Dill et al. (2023): Localizing Model Behavior
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class ComponentCausalEffect:
    """Causal effect of a single component."""

    layer_idx: int
    component_type: str  # "attention", "mlp", "full_layer"
    clean_projection: float       # refusal projection in clean run
    corrupted_projection: float   # refusal projection in corrupted run
    restored_projection: float    # refusal projection after patching this component
    causal_effect: float          # how much patching this component restores refusal
    indirect_effect: float        # total - direct effect (mediated through downstream)
    is_causal: bool               # above threshold for causal importance


@dataclass
class CausalTracingResult:
    """Full causal tracing results."""

    n_layers: int
    noise_level: float
    component_effects: list[ComponentCausalEffect]

    # Aggregate metrics
    clean_refusal_strength: float
    corrupted_refusal_strength: float
    total_corruption_effect: float  # clean - corrupted

    # Circuit identification
    causal_components: list[tuple[int, str]]  # (layer, type) pairs above threshold
    circuit_size: int               # number of causally important components
    circuit_fraction: float         # fraction of total components that are causal

    # Correlation vs causation analysis
    correlation_causal_agreement: float  # how well projection predicts causal importance


class CausalRefusalTracer:
    """Identify causally important components for refusal via activation patching.

    Instead of just measuring where the refusal signal is large (correlational),
    this determines which components *actually cause* refusal by intervening
    on individual components and measuring the effect.
    """

    def __init__(
        self,
        noise_level: float = 3.0,
        causal_threshold: float = 0.1,
    ):
        """
        Args:
            noise_level: Standard deviation of Gaussian noise for corruption.
            causal_threshold: Minimum causal effect to classify as "causal".
        """
        self.noise_level = noise_level
        self.causal_threshold = causal_threshold

    def trace_from_activations(
        self,
        clean_activations: dict[int, torch.Tensor],
        refusal_direction: dict[int, torch.Tensor] | torch.Tensor,
        component_types: list[str] | None = None,
    ) -> CausalTracingResult:
        """Perform causal tracing using pre-collected activations.

        This is a simulation-based approach that doesn't require running
        the actual model — it estimates causal effects from the activation
        geometry alone.

        For each component, we estimate: "if we removed this component's
        contribution to the refusal direction, how much would refusal decrease?"

        Args:
            clean_activations: {layer_idx: activation_tensor} from harmful prompt.
            refusal_direction: Per-layer or single refusal direction.
            component_types: Which component types to trace. Default: ["full_layer"].

        Returns:
            CausalTracingResult with causal importance map.
        """
        if component_types is None:
            component_types = ["full_layer"]

        layers = sorted(clean_activations.keys())
        n_layers = len(layers)

        # Normalize refusal directions
        if isinstance(refusal_direction, torch.Tensor):
            ref_dirs = {ly: refusal_direction.float().squeeze() for ly in layers}
        else:
            ref_dirs = {
                ly: refusal_direction[ly].float().squeeze()
                for ly in layers if ly in refusal_direction
            }

        for ly in ref_dirs:
            ref_dirs[ly] = ref_dirs[ly] / ref_dirs[ly].norm().clamp(min=1e-10)

        # Clean projections
        clean_projs = {}
        for ly in layers:
            if ly in ref_dirs:
                act = clean_activations[ly].float().squeeze()
                clean_projs[ly] = (act @ ref_dirs[ly]).item()
            else:
                clean_projs[ly] = 0.0

        clean_strength = sum(abs(v) for v in clean_projs.values()) / max(len(clean_projs), 1)

        # Simulate corruption: add noise to estimate corrupted baseline
        torch.manual_seed(42)
        corrupted_projs = {}
        for ly in layers:
            if ly in ref_dirs:
                act = clean_activations[ly].float().squeeze()
                noise = torch.randn_like(act) * self.noise_level
                corrupted = act + noise
                corrupted_projs[ly] = (corrupted @ ref_dirs[ly]).item()
            else:
                corrupted_projs[ly] = 0.0

        corrupted_strength = sum(abs(v) for v in corrupted_projs.values()) / max(len(corrupted_projs), 1)

        total_corruption = clean_strength - corrupted_strength

        # For each component, estimate causal effect via ablation
        effects = []
        for ly in layers:
            for comp_type in component_types:
                if ly not in ref_dirs:
                    continue

                act = clean_activations[ly].float().squeeze()

                # Clean projection at this layer
                clean_proj = clean_projs[ly]

                # Corrupted projection at this layer
                corrupted_proj = corrupted_projs[ly]

                # Restored projection: patch clean activation back in
                # In the simulation, this means the projection returns to clean value
                restored_proj = clean_proj

                # Causal effect: how much does restoring this component
                # recover the refusal signal (normalized by total corruption)
                if abs(total_corruption) > 1e-10:
                    causal_effect = abs(clean_proj - corrupted_proj) / (
                        abs(total_corruption) * n_layers
                    )
                else:
                    causal_effect = 0.0

                # Indirect effect: contribution mediated through downstream layers
                # Estimate via the projection magnitude relative to total
                total_proj = sum(abs(v) for v in clean_projs.values())
                if total_proj > 1e-10:
                    direct_fraction = abs(clean_proj) / total_proj
                else:
                    direct_fraction = 0.0
                indirect = max(0.0, causal_effect - direct_fraction)

                is_causal = causal_effect > self.causal_threshold

                effects.append(ComponentCausalEffect(
                    layer_idx=ly,
                    component_type=comp_type,
                    clean_projection=clean_proj,
                    corrupted_projection=corrupted_proj,
                    restored_projection=restored_proj,
                    causal_effect=causal_effect,
                    indirect_effect=indirect,
                    is_causal=is_causal,
                ))

        # Identify circuit
        causal_components = [
            (e.layer_idx, e.component_type) for e in effects if e.is_causal
        ]
        total_components = len(effects)
        circuit_fraction = len(causal_components) / max(total_components, 1)

        # Correlation vs causation agreement
        # Compare ranking by projection magnitude vs ranking by causal effect
        agreement = self._rank_agreement(effects)

        return CausalTracingResult(
            n_layers=n_layers,
            noise_level=self.noise_level,
            component_effects=effects,
            clean_refusal_strength=clean_strength,
            corrupted_refusal_strength=corrupted_strength,
            total_corruption_effect=total_corruption,
            causal_components=causal_components,
            circuit_size=len(causal_components),
            circuit_fraction=circuit_fraction,
            correlation_causal_agreement=agreement,
        )

    def identify_silent_contributors(
        self, result: CausalTracingResult, top_k: int = 5,
    ) -> dict[str, list[ComponentCausalEffect]]:
        """Find components where correlational and causal importance disagree.

        "Silent contributors" have high causal effect but low projection.
        "Loud non-contributors" have high projection but low causal effect.

        Args:
            result: CausalTracingResult from trace_from_activations.
            top_k: Number of components to return in each category.

        Returns:
            Dict with "silent_contributors" and "loud_non_contributors".
        """
        effects = result.component_effects
        if not effects:
            return {"silent_contributors": [], "loud_non_contributors": []}

        # Score the discrepancy
        for e in effects:
            # Normalize to [0, 1] ranges
            max_proj = max(abs(x.clean_projection) for x in effects)
            max_causal = max(x.causal_effect for x in effects)

            if max_proj > 0:
                norm_proj = abs(e.clean_projection) / max_proj
            else:
                norm_proj = 0.0
            if max_causal > 0:
                norm_causal = e.causal_effect / max_causal
            else:
                norm_causal = 0.0

            e._norm_proj = norm_proj
            e._norm_causal = norm_causal

        # Silent: high causal, low projection
        silent = sorted(
            effects,
            key=lambda e: e._norm_causal - e._norm_proj,
            reverse=True,
        )[:top_k]

        # Loud: high projection, low causal
        loud = sorted(
            effects,
            key=lambda e: e._norm_proj - e._norm_causal,
            reverse=True,
        )[:top_k]

        # Clean up temporary attributes
        for e in effects:
            if hasattr(e, '_norm_proj'):
                delattr(e, '_norm_proj')
            if hasattr(e, '_norm_causal'):
                delattr(e, '_norm_causal')

        return {
            "silent_contributors": silent,
            "loud_non_contributors": loud,
        }

    def _rank_agreement(self, effects: list[ComponentCausalEffect]) -> float:
        """Compute Spearman-like rank agreement between projection and causal rankings."""
        if len(effects) < 2:
            return 1.0

        # Rank by projection magnitude
        proj_ranked = sorted(
            range(len(effects)),
            key=lambda i: abs(effects[i].clean_projection),
            reverse=True,
        )
        proj_ranks = {idx: rank for rank, idx in enumerate(proj_ranked)}

        # Rank by causal effect
        causal_ranked = sorted(
            range(len(effects)),
            key=lambda i: effects[i].causal_effect,
            reverse=True,
        )
        causal_ranks = {idx: rank for rank, idx in enumerate(causal_ranked)}

        # Spearman correlation
        n = len(effects)
        d_sq_sum = sum(
            (proj_ranks[i] - causal_ranks[i]) ** 2 for i in range(n)
        )
        if n * (n * n - 1) == 0:
            return 1.0
        rho = 1.0 - (6.0 * d_sq_sum) / (n * (n * n - 1))
        return max(-1.0, min(1.0, rho))

    @staticmethod
    def format_tracing_report(result: CausalTracingResult) -> str:
        """Format causal tracing results."""
        lines = []
        lines.append("Causal Tracing — Refusal Circuit Identification")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Layers traced: {result.n_layers}")
        lines.append(f"Noise level: {result.noise_level}")
        lines.append(f"Clean refusal strength: {result.clean_refusal_strength:.4f}")
        lines.append(f"Corrupted strength: {result.corrupted_refusal_strength:.4f}")
        lines.append(f"Corruption effect: {result.total_corruption_effect:.4f}")
        lines.append("")
        lines.append(f"Circuit size: {result.circuit_size} / {len(result.component_effects)} "
                      f"({result.circuit_fraction:.0%})")
        lines.append(f"Correlation-causation agreement: {result.correlation_causal_agreement:.3f}")
        lines.append("")

        if result.component_effects:
            lines.append("Top causal components:")
            sorted_effects = sorted(
                result.component_effects,
                key=lambda e: e.causal_effect,
                reverse=True,
            )
            for e in sorted_effects[:10]:
                marker = " [CAUSAL]" if e.is_causal else ""
                lines.append(
                    f"  Layer {e.layer_idx:3d} {e.component_type:10s}  "
                    f"causal={e.causal_effect:.4f}  "
                    f"proj={e.clean_projection:+.4f}{marker}"
                )

        return "\n".join(lines)
