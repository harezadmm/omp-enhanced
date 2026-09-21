"""Multi-Token Position analysis for refusal signal localization.

Most abliteration work assumes the refusal signal lives at the *last token
position* of the prompt. But recent work (Park et al. 2025, Templeton et al.
2024) shows that refusal is computed across multiple token positions, with
different positions carrying different aspects of the decision:

  - **Last token**: The final "vote" for refusal (where it's most visible)
  - **Trigger tokens**: Specific harmful content tokens that first activate
    refusal circuits (e.g., "bomb", "hack", "kill")
  - **Instruction tokens**: System prompt / instruction tokens that set
    the refusal threshold
  - **Context integration positions**: Mid-sequence positions where the
    model integrates context to decide if the request is harmful

This module provides:

  1. **Position-wise Refusal Profiling**: Measure refusal signal strength
     at every token position, not just the last one.

  2. **Trigger Token Detection**: Identify which specific tokens in a
     prompt activate the refusal circuit most strongly.

  3. **Positional Decay Analysis**: Measure how the refusal signal
     propagates and decays from trigger tokens to the final position.

  4. **Multi-Position Excision Mapping**: For each position, measure how
     much abliteration at that position alone would reduce refusal.

Contributions:
  - Comprehensive position-wise refusal profiling beyond last-token
  - Trigger token detection using per-position projection onto refusal direction
  - Decay rate estimation showing how refusal propagates through positions
  - Position-importance ranking for targeted excision

References:
    - Park et al. (2025): Position-dependent safety representations
    - Templeton et al. (2024): Scaling monosemanticity (position structure)
    - Arditi et al. (2024): Last-token assumption baseline
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch


@dataclass
class TokenRefusalProfile:
    """Refusal signal at a single token position."""

    position: int
    token_text: str
    refusal_projection: float    # projection onto refusal direction
    relative_strength: float     # strength relative to max position
    is_trigger: bool             # whether this position is a trigger token


@dataclass
class PositionAnalysisResult:
    """Full multi-position refusal analysis for a single prompt."""

    prompt_text: str
    layer_idx: int
    token_profiles: list[TokenRefusalProfile]
    peak_position: int           # position with strongest refusal signal
    peak_strength: float         # refusal projection at peak
    last_token_strength: float   # refusal projection at last token
    trigger_positions: list[int]  # positions classified as triggers
    decay_rate: float            # exponential decay rate from peak to end
    position_gini: float         # Gini coefficient of positional distribution
    n_tokens: int


@dataclass
class MultiTokenSummary:
    """Aggregate multi-token analysis across multiple prompts."""

    per_prompt: list[PositionAnalysisResult]
    mean_peak_vs_last_ratio: float    # avg ratio of peak to last-token strength
    mean_trigger_count: float         # avg number of trigger tokens per prompt
    mean_decay_rate: float            # avg positional decay rate
    mean_position_gini: float         # avg Gini of positional distribution
    peak_is_last_fraction: float      # fraction of prompts where peak == last token
    last_token_dominance: float       # how much of total signal is at last token


class MultiTokenPositionAnalyzer:
    """Analyze refusal signal across token positions.

    Goes beyond the standard last-token assumption to profile where
    refusal actually lives in the sequence.
    """

    def __init__(
        self,
        trigger_threshold: float = 0.5,
        min_strength: float = 0.01,
    ):
        """
        Args:
            trigger_threshold: Fraction of peak strength above which a
                position is classified as a "trigger token".
            min_strength: Minimum absolute projection to consider non-noise.
        """
        self.trigger_threshold = trigger_threshold
        self.min_strength = min_strength

    def analyze_prompt(
        self,
        activations: torch.Tensor,
        refusal_direction: torch.Tensor,
        token_texts: list[str] | None = None,
        layer_idx: int = 0,
        prompt_text: str = "",
    ) -> PositionAnalysisResult:
        """Analyze refusal signal at each token position.

        Args:
            activations: (seq_len, hidden_dim) activations for one prompt.
            refusal_direction: (hidden_dim,) refusal direction vector.
            token_texts: Optional list of token strings for annotation.
            layer_idx: Layer index for metadata.
            prompt_text: Original prompt text for metadata.

        Returns:
            PositionAnalysisResult with per-position refusal profiling.
        """
        acts = activations.float()
        if acts.ndim == 3:
            acts = acts.squeeze(0)  # Remove batch dim
        seq_len, hidden_dim = acts.shape

        ref_dir = refusal_direction.float().squeeze()
        ref_dir = ref_dir / ref_dir.norm().clamp(min=1e-10)

        # Compute projection at each position
        projections = (acts @ ref_dir).tolist()  # (seq_len,)

        # Find peak
        abs_projections = [abs(p) for p in projections]
        peak_strength = max(abs_projections) if abs_projections else 0.0
        peak_position = abs_projections.index(peak_strength) if abs_projections else 0

        if token_texts is None:
            token_texts = [f"pos_{i}" for i in range(seq_len)]

        # Build per-token profiles
        profiles = []
        trigger_positions = []
        for i in range(seq_len):
            abs_proj = abs_projections[i]
            rel = abs_proj / max(peak_strength, 1e-10)
            is_trigger = (
                abs_proj > self.min_strength
                and rel >= self.trigger_threshold
            )
            if is_trigger:
                trigger_positions.append(i)

            profiles.append(TokenRefusalProfile(
                position=i,
                token_text=token_texts[i] if i < len(token_texts) else f"pos_{i}",
                refusal_projection=projections[i],
                relative_strength=rel,
                is_trigger=is_trigger,
            ))

        # Last token strength
        last_strength = abs_projections[-1] if abs_projections else 0.0

        # Decay rate from peak to end
        decay_rate = self._compute_decay_rate(abs_projections, peak_position)

        # Position Gini coefficient
        position_gini = self._gini(abs_projections)

        return PositionAnalysisResult(
            prompt_text=prompt_text,
            layer_idx=layer_idx,
            token_profiles=profiles,
            peak_position=peak_position,
            peak_strength=peak_strength,
            last_token_strength=last_strength,
            trigger_positions=trigger_positions,
            decay_rate=decay_rate,
            position_gini=position_gini,
            n_tokens=seq_len,
        )

    def analyze_batch(
        self,
        activations_list: list[torch.Tensor],
        refusal_direction: torch.Tensor,
        token_texts_list: list[list[str]] | None = None,
        layer_idx: int = 0,
        prompt_texts: list[str] | None = None,
    ) -> MultiTokenSummary:
        """Analyze multiple prompts and aggregate.

        Args:
            activations_list: List of (seq_len, hidden_dim) tensors.
            refusal_direction: (hidden_dim,) refusal direction.
            token_texts_list: Optional list of token text lists.
            layer_idx: Layer index.
            prompt_texts: Optional prompt strings.

        Returns:
            MultiTokenSummary with per-prompt and aggregate results.
        """
        results = []
        for i, acts in enumerate(activations_list):
            tokens = token_texts_list[i] if token_texts_list else None
            prompt = prompt_texts[i] if prompt_texts else f"prompt_{i}"
            result = self.analyze_prompt(
                acts, refusal_direction,
                token_texts=tokens, layer_idx=layer_idx, prompt_text=prompt,
            )
            results.append(result)

        if not results:
            return MultiTokenSummary(
                per_prompt=[], mean_peak_vs_last_ratio=1.0,
                mean_trigger_count=0.0, mean_decay_rate=0.0,
                mean_position_gini=0.0, peak_is_last_fraction=1.0,
                last_token_dominance=1.0,
            )

        # Aggregate statistics
        ratios = []
        trigger_counts = []
        decay_rates = []
        ginis = []
        peak_is_last = 0
        last_dom_values = []

        for r in results:
            if r.last_token_strength > 1e-10:
                ratios.append(r.peak_strength / r.last_token_strength)
            else:
                ratios.append(1.0)

            trigger_counts.append(len(r.trigger_positions))
            decay_rates.append(r.decay_rate)
            ginis.append(r.position_gini)

            if r.peak_position == r.n_tokens - 1:
                peak_is_last += 1

            total = sum(abs(tp.refusal_projection) for tp in r.token_profiles)
            if total > 0:
                last_dom_values.append(r.last_token_strength / total)
            else:
                last_dom_values.append(1.0)

        n = len(results)
        return MultiTokenSummary(
            per_prompt=results,
            mean_peak_vs_last_ratio=sum(ratios) / n,
            mean_trigger_count=sum(trigger_counts) / n,
            mean_decay_rate=sum(decay_rates) / n,
            mean_position_gini=sum(ginis) / n,
            peak_is_last_fraction=peak_is_last / n,
            last_token_dominance=sum(last_dom_values) / n,
        )

    def _compute_decay_rate(
        self, abs_projections: list[float], peak_pos: int
    ) -> float:
        """Estimate exponential decay rate from peak to end of sequence.

        Models: strength(pos) ~ peak * exp(-decay * (pos - peak_pos))

        Returns:
            Estimated decay rate (higher = faster decay).
        """
        if peak_pos >= len(abs_projections) - 1:
            return 0.0

        peak_val = abs_projections[peak_pos]
        if peak_val < 1e-10:
            return 0.0

        # Use least-squares fit of log(strength/peak) vs distance
        distances = []
        log_ratios = []
        for i in range(peak_pos + 1, len(abs_projections)):
            ratio = abs_projections[i] / peak_val
            if ratio > 1e-10:
                distances.append(i - peak_pos)
                log_ratios.append(math.log(ratio))

        if len(distances) < 2:
            return 0.0

        # Simple linear regression: log_ratio = -decay * distance
        mean_d = sum(distances) / len(distances)
        mean_lr = sum(log_ratios) / len(log_ratios)
        num = sum((d - mean_d) * (lr - mean_lr) for d, lr in zip(distances, log_ratios))
        den = sum((d - mean_d) ** 2 for d in distances)

        if abs(den) < 1e-10:
            return 0.0

        slope = num / den
        return max(0.0, -slope)  # Decay rate should be positive

    @staticmethod
    def _gini(values: list[float]) -> float:
        """Compute Gini coefficient of a list of non-negative values."""
        from obliteratus.analysis.utils import gini_coefficient
        return gini_coefficient(values)

    @staticmethod
    def format_position_report(result: PositionAnalysisResult) -> str:
        """Format single-prompt position analysis."""
        lines = []
        lines.append(f"Multi-Token Position Analysis — Layer {result.layer_idx}")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Prompt: {result.prompt_text[:80]}...")
        lines.append(f"Tokens: {result.n_tokens}")
        lines.append(f"Peak position: {result.peak_position} (strength={result.peak_strength:.4f})")
        lines.append(f"Last token strength: {result.last_token_strength:.4f}")
        lines.append(f"Peak/Last ratio: {result.peak_strength / max(result.last_token_strength, 1e-10):.2f}x")
        lines.append(f"Trigger tokens: {len(result.trigger_positions)}")
        lines.append(f"Decay rate: {result.decay_rate:.3f}")
        lines.append(f"Position Gini: {result.position_gini:.3f}")
        lines.append("")

        # Show top positions
        sorted_profiles = sorted(
            result.token_profiles, key=lambda x: abs(x.refusal_projection), reverse=True
        )
        lines.append("Top refusal positions:")
        for tp in sorted_profiles[:10]:
            marker = " [TRIGGER]" if tp.is_trigger else ""
            lines.append(
                f"  pos {tp.position:4d} '{tp.token_text:15s}' "
                f"proj={tp.refusal_projection:+.4f} "
                f"rel={tp.relative_strength:.2f}{marker}"
            )

        return "\n".join(lines)

    @staticmethod
    def format_summary(summary: MultiTokenSummary) -> str:
        """Format multi-prompt summary."""
        lines = []
        lines.append("Multi-Token Position Summary")
        lines.append("=" * 40)
        lines.append("")
        lines.append(f"Prompts analyzed: {len(summary.per_prompt)}")
        lines.append(f"Mean peak/last ratio: {summary.mean_peak_vs_last_ratio:.2f}x")
        lines.append(f"Mean trigger tokens: {summary.mean_trigger_count:.1f}")
        lines.append(f"Mean decay rate: {summary.mean_decay_rate:.3f}")
        lines.append(f"Peak is last token: {summary.peak_is_last_fraction:.0%}")
        lines.append(f"Last-token dominance: {summary.last_token_dominance:.1%}")
        lines.append(f"Position Gini: {summary.mean_position_gini:.3f}")
        lines.append("")

        if summary.mean_peak_vs_last_ratio > 1.5:
            lines.append(
                "FINDING: Refusal signal is significantly stronger at "
                "non-final positions. Last-token-only abliteration may be "
                "leaving substantial refusal signal intact."
            )
        elif summary.peak_is_last_fraction > 0.8:
            lines.append(
                "FINDING: Refusal signal is concentrated at the last token "
                "for most prompts. Standard last-token abliteration is "
                "appropriate for this model."
            )
        else:
            lines.append(
                "FINDING: Refusal signal shows a mixed positional pattern. "
                "Multi-position abliteration may improve effectiveness."
            )

        return "\n".join(lines)
