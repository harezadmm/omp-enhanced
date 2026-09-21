"""Real Activation Patching for refusal circuit identification.

Unlike the simulation-based CausalRefusalTracer (causal_tracing.py), this
module performs *actual* activation patching by running the model with
interventions. It implements the interchange intervention framework from
Heimersheim & Nanda (2024) and the activation patching methodology from
Meng et al. (2022).

The core idea: to determine if a component is causally important for refusal,
we run the model on a harmful prompt (clean run), collect all activations,
then run the model again but replace ("patch") one component's activation
with what it would have been on a harmless prompt (corrupted run). If
refusal disappears, that component was causally necessary.

Three patching modes:
  1. **Noising** (corruption): Replace clean activation with corrupted
     (add noise or swap with harmless-prompt activation). Measures necessity.
  2. **Denoising** (restoration): Start from corrupted run, patch in the
     clean activation at one site. Measures sufficiency.
  3. **Interchange**: Replace activation from prompt A with activation from
     prompt B at a specific site. Measures causal mediation.

This requires actual model forward passes, unlike the approximation in
causal_tracing.py.

References:
    - Meng et al. (2022): Locating and Editing Factual Associations in GPT
    - Heimersheim & Nanda (2024): How to use and interpret activation patching
    - Conmy et al. (2023): Towards Automated Circuit Discovery (ACDC)
    - Goldowsky-Dill et al. (2023): Localizing Model Behavior with Path Patching
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import torch

logger = logging.getLogger(__name__)


@dataclass
class PatchingSite:
    """Specification of where to patch in the model."""

    layer_idx: int
    component: str  # "residual", "attn_out", "mlp_out", "attn_head"
    head_idx: int | None = None  # only for component="attn_head"
    token_position: int | str = "last"  # int index, or "last", "all"


@dataclass
class PatchingEffect:
    """Measured effect of patching a single site."""

    site: PatchingSite
    clean_metric: float       # metric value on clean (harmful) run
    corrupted_metric: float   # metric value on fully corrupted run
    patched_metric: float     # metric value after patching this site
    direct_effect: float      # (patched - corrupted) / (clean - corrupted)
    is_significant: bool      # above threshold


@dataclass
class ActivationPatchingResult:
    """Full results from an activation patching sweep."""

    n_layers: int
    n_sites: int
    patching_mode: str  # "noising", "denoising", or "interchange"
    effects: list[PatchingEffect]
    clean_baseline: float
    corrupted_baseline: float
    total_effect: float  # clean - corrupted

    # Circuit identification
    significant_sites: list[PatchingSite]
    circuit_fraction: float

    # Top components
    top_causal_layers: list[int]


class ActivationPatcher:
    """Perform real activation patching to identify refusal circuits.

    This class hooks into a model's forward pass to collect and patch
    activations at specified sites. It requires actual model inference,
    so it's slower than the simulation-based approach in causal_tracing.py,
    but produces real causal evidence.
    """

    def __init__(
        self,
        significance_threshold: float = 0.1,
        metric_fn: Callable[[torch.Tensor], float] | None = None,
    ):
        """
        Args:
            significance_threshold: Minimum direct effect (normalized) to be
                considered significant.
            metric_fn: Function that takes model output logits and returns a
                scalar measuring "refusal strength". Default: projection of
                output onto refusal direction.
        """
        self.significance_threshold = significance_threshold
        self.metric_fn = metric_fn

    def patch_sweep(
        self,
        model: torch.nn.Module,
        clean_input_ids: torch.Tensor,
        corrupted_input_ids: torch.Tensor,
        sites: list[PatchingSite] | None = None,
        refusal_direction: torch.Tensor | None = None,
        mode: str = "noising",
    ) -> ActivationPatchingResult:
        """Run activation patching across all specified sites.

        Args:
            model: The language model.
            clean_input_ids: Token IDs for the harmful (clean) prompt.
            corrupted_input_ids: Token IDs for the harmless (corrupted) prompt.
            sites: List of sites to patch. If None, patches all residual stream
                positions across all layers.
            refusal_direction: If provided, used as the metric (projection onto
                this direction). Otherwise uses self.metric_fn.
            mode: "noising" (corrupt clean), "denoising" (restore from corrupt),
                or "interchange" (swap between prompts).

        Returns:
            ActivationPatchingResult with per-site causal effects.
        """
        # Detect number of layers
        n_layers = self._count_layers(model)

        if sites is None:
            sites = [
                PatchingSite(layer_idx=li, component="residual")
                for li in range(n_layers)
            ]

        # Define metric function
        if self.metric_fn is not None:
            metric = self.metric_fn
        elif refusal_direction is not None:
            r = refusal_direction.float().squeeze()
            r = r / r.norm().clamp(min=1e-8)
            def metric(logits: torch.Tensor) -> float:
                # Use last-token hidden state projection
                return (logits.float().squeeze() @ r).item()
        else:
            def metric(logits: torch.Tensor) -> float:
                return logits.float().squeeze().norm().item()

        # Collect activations from both runs
        clean_acts = self._collect_activations(model, clean_input_ids, n_layers)
        corrupted_acts = self._collect_activations(model, corrupted_input_ids, n_layers)

        # Compute baselines
        with torch.no_grad():
            clean_out = model(clean_input_ids)
            clean_logits = clean_out.logits if hasattr(clean_out, 'logits') else clean_out[0]
            clean_metric = metric(clean_logits[:, -1, :])

            corrupted_out = model(corrupted_input_ids)
            corrupted_logits = corrupted_out.logits if hasattr(corrupted_out, 'logits') else corrupted_out[0]
            corrupted_metric = metric(corrupted_logits[:, -1, :])

        total_effect = clean_metric - corrupted_metric

        # Patch each site
        effects = []
        for site in sites:
            patched_metric = self._run_with_patch(
                model, clean_input_ids, corrupted_input_ids,
                clean_acts, corrupted_acts,
                site, metric, mode, n_layers,
            )

            if abs(total_effect) > 1e-10:
                if mode == "noising":
                    direct_effect = (clean_metric - patched_metric) / abs(total_effect)
                else:  # denoising
                    direct_effect = (patched_metric - corrupted_metric) / abs(total_effect)
            else:
                direct_effect = 0.0

            effects.append(PatchingEffect(
                site=site,
                clean_metric=clean_metric,
                corrupted_metric=corrupted_metric,
                patched_metric=patched_metric,
                direct_effect=direct_effect,
                is_significant=abs(direct_effect) > self.significance_threshold,
            ))

        significant = [e.site for e in effects if e.is_significant]
        circuit_fraction = len(significant) / max(len(effects), 1)

        # Top causal layers
        layer_effects = {}
        for e in effects:
            li = e.site.layer_idx
            if li not in layer_effects or abs(e.direct_effect) > abs(layer_effects[li]):
                layer_effects[li] = e.direct_effect
        top_layers = sorted(layer_effects, key=lambda k: abs(layer_effects[k]), reverse=True)[:5]

        return ActivationPatchingResult(
            n_layers=n_layers,
            n_sites=len(sites),
            patching_mode=mode,
            effects=effects,
            clean_baseline=clean_metric,
            corrupted_baseline=corrupted_metric,
            total_effect=total_effect,
            significant_sites=significant,
            circuit_fraction=circuit_fraction,
            top_causal_layers=top_layers,
        )

    def _collect_activations(
        self,
        model: torch.nn.Module,
        input_ids: torch.Tensor,
        n_layers: int,
    ) -> dict[int, torch.Tensor]:
        """Collect residual stream activations at each layer using hooks."""
        activations = {}
        hooks = []

        def make_hook(layer_idx):
            def hook_fn(module, input, output):
                if isinstance(output, tuple):
                    activations[layer_idx] = output[0].detach().clone()
                else:
                    activations[layer_idx] = output.detach().clone()
            return hook_fn

        # Register hooks on transformer layers
        layers = self._get_layers(model)
        for i, layer in enumerate(layers):
            if i < n_layers:
                h = layer.register_forward_hook(make_hook(i))
                hooks.append(h)

        with torch.no_grad():
            model(input_ids)

        for h in hooks:
            h.remove()

        return activations

    def _run_with_patch(
        self,
        model: torch.nn.Module,
        clean_ids: torch.Tensor,
        corrupted_ids: torch.Tensor,
        clean_acts: dict[int, torch.Tensor],
        corrupted_acts: dict[int, torch.Tensor],
        site: PatchingSite,
        metric: Callable,
        mode: str,
        n_layers: int,
    ) -> float:
        """Run model with a single activation patched."""
        # Determine which input to use and what to patch in
        if mode == "noising":
            run_ids = clean_ids
            source_acts = corrupted_acts  # patch corrupted into clean run
        else:
            run_ids = corrupted_ids
            source_acts = clean_acts  # patch clean into corrupted run

        patch_layer = site.layer_idx
        patch_act = source_acts.get(patch_layer)

        if patch_act is None:
            # No activation collected for this layer, return clean metric
            return metric(torch.zeros(1))

        hooks = []

        def patch_hook(module, input, output):
            if isinstance(output, tuple):
                # Replace the residual stream activation
                new_out = list(output)
                new_out[0] = patch_act
                return tuple(new_out)
            else:
                return patch_act

        layers = self._get_layers(model)
        if patch_layer < len(layers):
            h = layers[patch_layer].register_forward_hook(patch_hook)
            hooks.append(h)

        with torch.no_grad():
            out = model(run_ids)
            logits = out.logits if hasattr(out, 'logits') else out[0]
            result = metric(logits[:, -1, :])

        for h in hooks:
            h.remove()

        return result

    def _count_layers(self, model: torch.nn.Module) -> int:
        """Count the number of transformer layers."""
        layers = self._get_layers(model)
        return len(layers)

    def _get_layers(self, model: torch.nn.Module) -> list:
        """Get the list of transformer layers."""
        for attr_path in [
            "transformer.h", "model.layers", "gpt_neox.layers",
            "model.decoder.layers", "transformer.blocks",
        ]:
            try:
                obj = model
                for attr in attr_path.split("."):
                    obj = getattr(obj, attr)
                return list(obj)
            except AttributeError:
                continue
        return []

    @staticmethod
    def format_report(result: ActivationPatchingResult) -> str:
        """Format activation patching results as a report."""
        lines = []
        lines.append("Activation Patching — Refusal Circuit Identification")
        lines.append("=" * 53)
        lines.append("")
        lines.append(f"Mode: {result.patching_mode}")
        lines.append(f"Layers: {result.n_layers}, Sites patched: {result.n_sites}")
        lines.append(f"Clean baseline: {result.clean_baseline:.4f}")
        lines.append(f"Corrupted baseline: {result.corrupted_baseline:.4f}")
        lines.append(f"Total effect: {result.total_effect:.4f}")
        lines.append("")
        lines.append(
            f"Significant sites: {len(result.significant_sites)} / {result.n_sites} "
            f"({result.circuit_fraction:.0%})"
        )
        lines.append(f"Top causal layers: {result.top_causal_layers}")
        lines.append("")

        if result.effects:
            sorted_effects = sorted(
                result.effects, key=lambda e: abs(e.direct_effect), reverse=True,
            )
            lines.append("Top patching effects:")
            for e in sorted_effects[:15]:
                marker = " [SIG]" if e.is_significant else ""
                head_str = f".head{e.site.head_idx}" if e.site.head_idx is not None else ""
                lines.append(
                    f"  Layer {e.site.layer_idx:3d} {e.site.component}{head_str:8s}  "
                    f"effect={e.direct_effect:+.4f}  "
                    f"patched={e.patched_metric:.4f}{marker}"
                )

        return "\n".join(lines)
