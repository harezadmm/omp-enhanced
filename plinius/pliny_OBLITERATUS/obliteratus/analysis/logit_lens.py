"""Logit lens analysis of refusal directions.

The logit lens (nostalgebraist, 2020) decodes intermediate representations
through the model's unembedding matrix to see what tokens they predict.
Applied to refusal directions, this reveals:

  1. Which tokens the refusal direction *promotes* when present
     (expected: "I", "sorry", "cannot", "apologize", "As")
  2. Which tokens the refusal direction *suppresses*
     (expected: harmful content tokens, or compliance tokens)
  3. How the refusal direction's token-level effect changes across layers
     (early layers may promote different tokens than late layers)

This provides a mechanistic explanation of *how* the refusal direction
produces refusal behavior: by directly boosting refusal-associated tokens
in the output logit space.

Mathematical formulation:
    Given refusal direction r (hidden_dim,) and unembedding matrix W_U (vocab, hidden):
    logit_effect = W_U @ r  (gives per-token logit boost from the direction)
    The tokens with highest logit_effect are "promoted" by the direction.

Contribution: We extend this to compute the "refusal token spectrum" --
the distribution of logit effects across semantically meaningful token groups
(refusal phrases, compliance phrases, neutral phrases), providing a
quantitative measure of how specifically the direction targets refusal tokens
vs. having broad effects.

References:
    - nostalgebraist (2020): Logit Lens blog post
    - Belrose et al. (2023): Tuned Lens (learned affine correction)
    - LogitLens4LLMs (2025): Extended analysis framework
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# Semantically meaningful token groups for refusal analysis
REFUSAL_TOKENS = [
    "sorry", "Sorry", "SORRY",
    "cannot", "Cannot", "CANNOT",
    "can't", "Can't",
    "won't", "Won't",
    "shouldn't", "Shouldn't",
    "apologize", "Apologize",
    "unable", "Unable",
    "inappropriate", "Inappropriate",
    "unethical", "Unethical",
    "illegal", "Illegal",
    "harmful", "Harmful",
    "dangerous", "Dangerous",
    "refuse", "Refuse",
    "decline", "Decline",
    "assist", " assist",  # as in "I can't assist"
    "I", " I",
    "As", " As",
]

COMPLIANCE_TOKENS = [
    "Sure", "sure", "SURE",
    "Here", "here",
    "Okay", "okay", "OK",
    "Absolutely", "absolutely",
    "Certainly", "certainly",
    "Of", " Of",  # "Of course"
    "course",
    "Yes", "yes",
    "Happy", "happy",
    "glad", "Glad",
    "help", "Help",
    "First", "first",
    "Step", "step",
    "To", " To",
    "The", " The",
    "Let", " Let",
]


@dataclass
class LogitLensResult:
    """Result of logit lens analysis for a refusal direction."""

    layer_idx: int
    top_promoted: list[tuple[str, float]]   # (token, logit_boost) highest promoted
    top_suppressed: list[tuple[str, float]]  # (token, logit_boost) most suppressed
    refusal_token_mean_boost: float          # mean logit boost for refusal tokens
    compliance_token_mean_boost: float       # mean logit boost for compliance tokens
    refusal_specificity: float               # how specifically direction targets refusal
    logit_effect_entropy: float              # entropy of effect distribution
    refusal_compliance_gap: float            # refusal_boost - compliance_boost


@dataclass
class MultiLayerLogitLensResult:
    """Aggregated logit lens results across layers."""

    per_layer: dict[int, LogitLensResult]
    strongest_refusal_layer: int
    peak_specificity_layer: int
    mean_refusal_compliance_gap: float


class RefusalLogitLens:
    """Decode refusal directions through the unembedding matrix.

    Reveals which output tokens a refusal direction promotes or suppresses,
    providing mechanistic insight into how refusal behavior is implemented
    at the token prediction level.
    """

    def __init__(self, top_k: int = 25):
        """
        Args:
            top_k: Number of top/bottom tokens to report.
        """
        self.top_k = top_k

    def analyze_direction(
        self,
        direction: torch.Tensor,
        model: torch.nn.Module,
        tokenizer,
        layer_idx: int = 0,
    ) -> LogitLensResult:
        """Analyze a single refusal direction through the logit lens.

        Args:
            direction: (hidden_dim,) refusal direction vector.
            model: The language model (needs access to unembedding weights).
            tokenizer: Tokenizer for decoding token IDs to strings.
            layer_idx: Index of the layer this direction came from.

        Returns:
            LogitLensResult with token-level analysis.
        """
        d = direction.float()
        if d.dim() > 1:
            d = d.squeeze()
        d = d / d.norm().clamp(min=1e-8)

        # Get unembedding matrix
        unembed = self._get_unembedding_matrix(model).float()  # (vocab, hidden)

        # Apply LayerNorm if the model uses it before the LM head
        ln_weight, ln_bias = self._get_final_layernorm(model)
        if ln_weight is not None:
            # LayerNorm applied to direction (approximation: treat direction
            # as if it were an activation to be normalized)
            d_normed = d * ln_weight.float()
            if ln_bias is not None:
                d_normed = d_normed + ln_bias.float()
        else:
            d_normed = d

        # Compute logit effect: how much each output token's logit changes
        # when the refusal direction is present in the residual stream
        logit_effect = unembed @ d_normed  # (vocab_size,)

        # Top promoted and suppressed tokens
        top_vals, top_ids = logit_effect.topk(self.top_k)
        bot_vals, bot_ids = logit_effect.topk(self.top_k, largest=False)

        top_promoted = []
        for val, tid in zip(top_vals.tolist(), top_ids.tolist()):
            token_str = tokenizer.decode([tid])
            top_promoted.append((token_str, val))

        top_suppressed = []
        for val, tid in zip(bot_vals.tolist(), bot_ids.tolist()):
            token_str = tokenizer.decode([tid])
            top_suppressed.append((token_str, val))

        # Compute mean boost for refusal and compliance token groups
        refusal_boosts = self._get_token_group_boosts(
            logit_effect, tokenizer, REFUSAL_TOKENS
        )
        compliance_boosts = self._get_token_group_boosts(
            logit_effect, tokenizer, COMPLIANCE_TOKENS
        )

        refusal_mean = sum(refusal_boosts) / max(len(refusal_boosts), 1)
        compliance_mean = sum(compliance_boosts) / max(len(compliance_boosts), 1)

        # Refusal specificity: how much more the direction promotes refusal
        # tokens vs. the average token
        global_mean = logit_effect.mean().item()
        global_std = logit_effect.std().item()
        specificity = (refusal_mean - global_mean) / max(global_std, 1e-8)

        # Entropy of logit effect distribution (measures how focused vs. diffuse)
        probs = F.softmax(logit_effect, dim=-1)
        entropy = -(probs * probs.log().clamp(min=-100)).sum().item()

        gap = refusal_mean - compliance_mean

        return LogitLensResult(
            layer_idx=layer_idx,
            top_promoted=top_promoted,
            top_suppressed=top_suppressed,
            refusal_token_mean_boost=refusal_mean,
            compliance_token_mean_boost=compliance_mean,
            refusal_specificity=specificity,
            logit_effect_entropy=entropy,
            refusal_compliance_gap=gap,
        )

    def analyze_all_layers(
        self,
        refusal_directions: dict[int, torch.Tensor],
        model: torch.nn.Module,
        tokenizer,
        strong_layers: list[int] | None = None,
    ) -> MultiLayerLogitLensResult:
        """Analyze refusal directions across all (or strong) layers.

        Args:
            refusal_directions: {layer_idx: direction} for each layer.
            model: The language model.
            tokenizer: Tokenizer for decoding.
            strong_layers: If provided, only analyze these layers.

        Returns:
            MultiLayerLogitLensResult with per-layer and aggregate analysis.
        """
        layers_to_analyze = strong_layers or sorted(refusal_directions.keys())

        per_layer = {}
        for idx in layers_to_analyze:
            if idx not in refusal_directions:
                continue
            per_layer[idx] = self.analyze_direction(
                refusal_directions[idx], model, tokenizer, layer_idx=idx
            )

        if not per_layer:
            return MultiLayerLogitLensResult(
                per_layer={},
                strongest_refusal_layer=0,
                peak_specificity_layer=0,
                mean_refusal_compliance_gap=0.0,
            )

        # Find layer with strongest refusal token promotion
        strongest = max(per_layer.items(), key=lambda x: x[1].refusal_compliance_gap)
        peak_spec = max(per_layer.items(), key=lambda x: x[1].refusal_specificity)

        mean_gap = sum(r.refusal_compliance_gap for r in per_layer.values()) / len(per_layer)

        return MultiLayerLogitLensResult(
            per_layer=per_layer,
            strongest_refusal_layer=strongest[0],
            peak_specificity_layer=peak_spec[0],
            mean_refusal_compliance_gap=mean_gap,
        )

    def _get_unembedding_matrix(self, model: torch.nn.Module) -> torch.Tensor:
        """Extract the unembedding (LM head) weight matrix."""
        # Try common paths
        for attr_path in ["lm_head.weight", "embed_out.weight", "output.weight"]:
            try:
                obj = model
                for attr in attr_path.split("."):
                    obj = getattr(obj, attr)
                return obj.data
            except AttributeError:
                continue

        # Check for tied embeddings (weight sharing with input embeddings)
        for attr_path in [
            "transformer.wte.weight",
            "model.embed_tokens.weight",
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

    def _get_final_layernorm(
        self, model: torch.nn.Module
    ) -> tuple[torch.Tensor | None, torch.Tensor | None]:
        """Extract the final LayerNorm weight and bias (applied before LM head)."""
        for attr_path in [
            "transformer.ln_f",
            "model.norm",
            "gpt_neox.final_layer_norm",
            "model.final_layernorm",
            "transformer.norm_f",
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

    def _get_token_group_boosts(
        self,
        logit_effect: torch.Tensor,
        tokenizer,
        token_strings: list[str],
    ) -> list[float]:
        """Get logit boosts for a group of token strings."""
        boosts = []
        for tok_str in token_strings:
            try:
                ids = tokenizer.encode(tok_str, add_special_tokens=False)
                if ids:
                    # Use the first token in the encoding
                    tid = ids[0]
                    if 0 <= tid < logit_effect.shape[0]:
                        boosts.append(logit_effect[tid].item())
            except Exception:
                logger.debug("Failed to encode token %r for logit boost lookup", tok_str, exc_info=True)
                continue
        return boosts

    @staticmethod
    def format_report(result: MultiLayerLogitLensResult) -> str:
        """Format multi-layer logit lens analysis as a report."""
        lines = []
        lines.append("Refusal Direction Logit Lens Analysis")
        lines.append("=" * 40)
        lines.append("")

        if not result.per_layer:
            lines.append("No layers analyzed.")
            return "\n".join(lines)

        lines.append(f"Strongest refusal layer: {result.strongest_refusal_layer}")
        lines.append(f"Peak specificity layer: {result.peak_specificity_layer}")
        lines.append(f"Mean refusal-compliance gap: {result.mean_refusal_compliance_gap:.4f}")
        lines.append("")

        for idx in sorted(result.per_layer.keys()):
            r = result.per_layer[idx]
            lines.append(f"Layer {idx}:")
            lines.append(f"  Refusal specificity: {r.refusal_specificity:.3f}")
            lines.append(f"  Refusal-compliance gap: {r.refusal_compliance_gap:.4f}")
            lines.append(f"  Logit effect entropy: {r.logit_effect_entropy:.2f}")
            lines.append("  Top promoted tokens:")
            for tok, val in r.top_promoted[:10]:
                lines.append(f"    {repr(tok):20s} +{val:.4f}")
            lines.append("  Top suppressed tokens:")
            for tok, val in r.top_suppressed[:10]:
                lines.append(f"    {repr(tok):20s} {val:.4f}")
            lines.append("")

        return "\n".join(lines)
