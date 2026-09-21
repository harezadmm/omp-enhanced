"""Tuned Lens analysis of refusal directions.

The Tuned Lens (Belrose et al., 2023) improves on the Logit Lens by learning
a per-layer affine transformation before projecting through the unembedding
matrix. This corrects for the fact that intermediate residual stream
representations are not in the same "format" as the final layer output --
earlier layers require more correction than later ones.

For refusal analysis, the Tuned Lens provides more accurate per-layer
decoding of what tokens the refusal direction promotes/suppresses at each
layer, especially in early layers where the raw Logit Lens is unreliable.

The learned affine probes are trained to minimize cross-entropy between the
tuned-lens prediction at layer l and the model's actual next-token prediction.
Once trained, they can be applied to refusal directions to get calibrated
per-layer token effect estimates.

Mathematical formulation:
    Standard Logit Lens:  logits_l = W_U @ h_l
    Tuned Lens:           logits_l = W_U @ (A_l @ h_l + b_l)

    where A_l is a learned square matrix (hidden_dim x hidden_dim) and
    b_l is a learned bias vector, trained to minimize:
        L = CE(softmax(logits_l), softmax(logits_final))

For refusal direction analysis:
    logit_effect_l = W_U @ (A_l @ r_l)
    (bias cancels in direction analysis since we care about the
    differential effect, not absolute logits)

References:
    - Belrose et al. (2023): Eliciting Latent Predictions from Transformers
      with the Tuned Lens (arXiv:2303.08112)
    - nostalgebraist (2020): Logit Lens blog post (the precursor)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class TunedLensProbe:
    """A single per-layer affine probe for the Tuned Lens."""

    layer_idx: int
    weight: torch.Tensor   # (hidden_dim, hidden_dim)
    bias: torch.Tensor     # (hidden_dim,)
    train_loss: float       # final training loss


@dataclass
class TunedLensResult:
    """Result of Tuned Lens analysis for a refusal direction at one layer."""

    layer_idx: int
    top_promoted: list[tuple[str, float]]    # (token, logit_boost)
    top_suppressed: list[tuple[str, float]]  # (token, logit_boost)
    refusal_token_mean_boost: float
    compliance_token_mean_boost: float
    refusal_compliance_gap: float
    correction_magnitude: float    # how much the affine probe changes the direction


@dataclass
class MultiLayerTunedLensResult:
    """Aggregated Tuned Lens results across layers."""

    per_layer: dict[int, TunedLensResult]
    probes: dict[int, TunedLensProbe]
    strongest_refusal_layer: int
    peak_gap_layer: int
    mean_refusal_compliance_gap: float
    logit_lens_agreement: float    # correlation with raw logit lens results


# Reuse token groups from logit_lens module
REFUSAL_TOKENS = [
    "sorry", "Sorry", "cannot", "Cannot", "can't", "Can't",
    "won't", "Won't", "apologize", "unable", "Unable",
    "inappropriate", "refuse", "Refuse", "decline",
    "I", " I", "As", " As",
]

COMPLIANCE_TOKENS = [
    "Sure", "sure", "Here", "here", "Okay", "okay",
    "Absolutely", "Certainly", "certainly",
    "Yes", "yes", "Happy", "happy", "help", "Help",
    "First", "first", "Step", "step", "Let", " Let",
]


class TunedLensTrainer:
    """Train per-layer affine probes for the Tuned Lens.

    Each probe learns to map intermediate residual stream activations
    to the final-layer representation space, so that projecting through
    the unembedding matrix gives accurate next-token predictions.
    """

    def __init__(
        self,
        hidden_dim: int,
        n_epochs: int = 100,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
    ):
        self.hidden_dim = hidden_dim
        self.n_epochs = n_epochs
        self.lr = lr
        self.weight_decay = weight_decay

    def train_probe(
        self,
        layer_activations: torch.Tensor,
        final_activations: torch.Tensor,
        layer_idx: int,
    ) -> TunedLensProbe:
        """Train a single affine probe for one layer.

        Args:
            layer_activations: (n_samples, hidden_dim) activations at layer l.
            final_activations: (n_samples, hidden_dim) activations at the final layer.
            layer_idx: Index of the source layer.

        Returns:
            TunedLensProbe with learned affine parameters.
        """
        d = layer_activations.shape[1]

        X = layer_activations.float()
        Y = final_activations.float()

        # Initialize weight as identity + small noise (probe starts near identity)
        weight = nn.Parameter(torch.eye(d) + torch.randn(d, d) * 0.01)
        bias = nn.Parameter(torch.zeros(d))

        optimizer = torch.optim.Adam([weight, bias], lr=self.lr, weight_decay=self.weight_decay)

        final_loss = 0.0
        for epoch in range(self.n_epochs):
            # Affine transform: Y_hat = X @ W^T + b
            Y_hat = X @ weight.T + bias.unsqueeze(0)

            # MSE loss in representation space (proxy for matching final logits)
            loss = F.mse_loss(Y_hat, Y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            final_loss = loss.item()

        return TunedLensProbe(
            layer_idx=layer_idx,
            weight=weight.data.detach(),
            bias=bias.data.detach(),
            train_loss=final_loss,
        )

    def train_all_layers(
        self,
        layer_activations: dict[int, torch.Tensor],
        final_activations: torch.Tensor,
    ) -> dict[int, TunedLensProbe]:
        """Train probes for all layers.

        Args:
            layer_activations: {layer_idx: (n_samples, hidden_dim)} per-layer activations.
            final_activations: (n_samples, hidden_dim) final-layer activations.

        Returns:
            {layer_idx: TunedLensProbe} for each layer.
        """
        probes = {}
        for idx in sorted(layer_activations.keys()):
            probes[idx] = self.train_probe(
                layer_activations[idx], final_activations, idx,
            )
        return probes


class RefusalTunedLens:
    """Decode refusal directions through learned per-layer affine probes.

    Provides more accurate per-layer analysis than the raw Logit Lens,
    especially for early and middle layers where the representation
    format differs most from the final layer.
    """

    def __init__(self, top_k: int = 25):
        self.top_k = top_k

    def analyze_direction(
        self,
        direction: torch.Tensor,
        probe: TunedLensProbe,
        model: nn.Module,
        tokenizer,
    ) -> TunedLensResult:
        """Analyze a refusal direction through a trained Tuned Lens probe.

        Args:
            direction: (hidden_dim,) refusal direction vector.
            probe: Trained TunedLensProbe for this layer.
            model: The language model (for unembedding matrix).
            tokenizer: Tokenizer for decoding token IDs.

        Returns:
            TunedLensResult with calibrated token-level analysis.
        """
        d = direction.float()
        if d.dim() > 1:
            d = d.squeeze()
        d = d / d.norm().clamp(min=1e-8)

        # Apply the learned affine correction
        # For direction analysis, only the linear part matters (bias cancels)
        d_tuned = probe.weight @ d  # (hidden_dim,)

        # Measure how much the probe changed the direction
        correction_mag = (d_tuned / d_tuned.norm().clamp(min=1e-8) - d).norm().item()

        # Get unembedding matrix
        unembed = self._get_unembedding_matrix(model).float()

        # Apply final LayerNorm
        ln_w, ln_b = self._get_final_layernorm(model)
        if ln_w is not None:
            d_normed = d_tuned * ln_w.float()
            if ln_b is not None:
                d_normed = d_normed + ln_b.float()
        else:
            d_normed = d_tuned

        # Compute logit effect
        logit_effect = unembed @ d_normed

        # Top promoted/suppressed
        top_vals, top_ids = logit_effect.topk(self.top_k)
        bot_vals, bot_ids = logit_effect.topk(self.top_k, largest=False)

        top_promoted = [
            (tokenizer.decode([tid]), val)
            for val, tid in zip(top_vals.tolist(), top_ids.tolist())
        ]
        top_suppressed = [
            (tokenizer.decode([tid]), val)
            for val, tid in zip(bot_vals.tolist(), bot_ids.tolist())
        ]

        # Token group analysis
        refusal_boosts = self._get_token_group_boosts(logit_effect, tokenizer, REFUSAL_TOKENS)
        compliance_boosts = self._get_token_group_boosts(logit_effect, tokenizer, COMPLIANCE_TOKENS)

        refusal_mean = sum(refusal_boosts) / max(len(refusal_boosts), 1)
        compliance_mean = sum(compliance_boosts) / max(len(compliance_boosts), 1)

        return TunedLensResult(
            layer_idx=probe.layer_idx,
            top_promoted=top_promoted,
            top_suppressed=top_suppressed,
            refusal_token_mean_boost=refusal_mean,
            compliance_token_mean_boost=compliance_mean,
            refusal_compliance_gap=refusal_mean - compliance_mean,
            correction_magnitude=correction_mag,
        )

    def analyze_all_layers(
        self,
        refusal_directions: dict[int, torch.Tensor],
        probes: dict[int, TunedLensProbe],
        model: nn.Module,
        tokenizer,
    ) -> MultiLayerTunedLensResult:
        """Analyze refusal directions across all layers with trained probes.

        Args:
            refusal_directions: {layer_idx: direction} for each layer.
            probes: {layer_idx: TunedLensProbe} trained probes.
            model: The language model.
            tokenizer: Tokenizer for decoding.

        Returns:
            MultiLayerTunedLensResult with per-layer and aggregate analysis.
        """
        per_layer = {}
        for idx in sorted(refusal_directions.keys()):
            if idx not in probes:
                continue
            per_layer[idx] = self.analyze_direction(
                refusal_directions[idx], probes[idx], model, tokenizer,
            )

        if not per_layer:
            return MultiLayerTunedLensResult(
                per_layer={},
                probes=probes,
                strongest_refusal_layer=0,
                peak_gap_layer=0,
                mean_refusal_compliance_gap=0.0,
                logit_lens_agreement=0.0,
            )

        strongest = max(per_layer.items(), key=lambda x: x[1].refusal_compliance_gap)
        peak_gap = max(per_layer.items(), key=lambda x: abs(x[1].refusal_compliance_gap))

        mean_gap = sum(r.refusal_compliance_gap for r in per_layer.values()) / len(per_layer)

        return MultiLayerTunedLensResult(
            per_layer=per_layer,
            probes=probes,
            strongest_refusal_layer=strongest[0],
            peak_gap_layer=peak_gap[0],
            mean_refusal_compliance_gap=mean_gap,
            logit_lens_agreement=0.0,  # filled in by compare_with_logit_lens
        )

    @staticmethod
    def compare_with_logit_lens(
        tuned_result: MultiLayerTunedLensResult,
        logit_lens_gaps: dict[int, float],
    ) -> float:
        """Compute rank correlation between Tuned Lens and Logit Lens gap rankings.

        Args:
            tuned_result: MultiLayerTunedLensResult from analyze_all_layers.
            logit_lens_gaps: {layer_idx: refusal_compliance_gap} from raw Logit Lens.

        Returns:
            Spearman rank correlation between the two methods' gap rankings.
        """
        common_layers = sorted(
            set(tuned_result.per_layer.keys()) & set(logit_lens_gaps.keys())
        )
        if len(common_layers) < 2:
            return 1.0

        tuned_gaps = [tuned_result.per_layer[ly].refusal_compliance_gap for ly in common_layers]
        logit_gaps = [logit_lens_gaps[ly] for ly in common_layers]

        # Rank both lists
        def _rank(values):
            indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=True)
            ranks = [0] * len(values)
            for rank, (idx, _) in enumerate(indexed):
                ranks[idx] = rank
            return ranks

        t_ranks = _rank(tuned_gaps)
        l_ranks = _rank(logit_gaps)

        n = len(common_layers)
        d_sq = sum((t - lr) ** 2 for t, lr in zip(t_ranks, l_ranks))
        denom = n * (n * n - 1)
        if denom == 0:
            return 1.0
        rho = 1.0 - (6.0 * d_sq) / denom
        return max(-1.0, min(1.0, rho))

    def _get_unembedding_matrix(self, model: nn.Module) -> torch.Tensor:
        for attr_path in ["lm_head.weight", "embed_out.weight", "output.weight"]:
            try:
                obj = model
                for attr in attr_path.split("."):
                    obj = getattr(obj, attr)
                return obj.data
            except AttributeError:
                continue
        for attr_path in [
            "transformer.wte.weight", "model.embed_tokens.weight",
            "gpt_neox.embed_in.weight",
        ]:
            try:
                obj = model
                for attr in attr_path.split("."):
                    obj = getattr(obj, attr)
                return obj.data
            except AttributeError:
                continue
        raise RuntimeError("Cannot locate unembedding matrix in model.")

    def _get_final_layernorm(self, model: nn.Module):
        for attr_path in [
            "transformer.ln_f", "model.norm", "gpt_neox.final_layer_norm",
            "model.final_layernorm", "transformer.norm_f",
        ]:
            try:
                obj = model
                for attr in attr_path.split("."):
                    obj = getattr(obj, attr)
                weight = getattr(obj, "weight", None)
                bias = getattr(obj, "bias", None)
                if weight is not None:
                    return weight.data, bias.data if bias is not None else None
            except AttributeError:
                continue
        return None, None

    def _get_token_group_boosts(self, logit_effect, tokenizer, token_strings):
        boosts = []
        for tok_str in token_strings:
            try:
                ids = tokenizer.encode(tok_str, add_special_tokens=False)
                if ids:
                    tid = ids[0]
                    if 0 <= tid < logit_effect.shape[0]:
                        boosts.append(logit_effect[tid].item())
            except Exception:
                continue
        return boosts

    @staticmethod
    def format_report(result: MultiLayerTunedLensResult) -> str:
        """Format Tuned Lens analysis as a report."""
        lines = []
        lines.append("Tuned Lens — Refusal Direction Analysis")
        lines.append("=" * 42)
        lines.append("")

        if not result.per_layer:
            lines.append("No layers analyzed.")
            return "\n".join(lines)

        lines.append(f"Strongest refusal layer: {result.strongest_refusal_layer}")
        lines.append(f"Peak gap layer: {result.peak_gap_layer}")
        lines.append(f"Mean refusal-compliance gap: {result.mean_refusal_compliance_gap:.4f}")
        lines.append(f"Logit Lens agreement (Spearman): {result.logit_lens_agreement:.3f}")
        lines.append("")

        for idx in sorted(result.per_layer.keys()):
            r = result.per_layer[idx]
            lines.append(f"Layer {idx}:")
            lines.append(f"  Refusal-compliance gap: {r.refusal_compliance_gap:.4f}")
            lines.append(f"  Correction magnitude: {r.correction_magnitude:.4f}")
            lines.append("  Top promoted:")
            for tok, val in r.top_promoted[:5]:
                lines.append(f"    {repr(tok):20s} +{val:.4f}")
            lines.append("  Top suppressed:")
            for tok, val in r.top_suppressed[:5]:
                lines.append(f"    {repr(tok):20s} {val:.4f}")
            lines.append("")

        return "\n".join(lines)
