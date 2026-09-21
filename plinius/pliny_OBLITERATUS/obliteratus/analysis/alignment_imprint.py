"""DPO/RLHF Alignment Imprint Detector.

Different alignment training methods leave distinct geometric "fingerprints"
in model activations. This module detects and characterizes these imprints
by comparing the structure of the refusal subspace against known signatures:

**DPO (Direct Preference Optimization)**:
  - Refusal tends to be *sparse* and *concentrated* in a few layers
  - The refusal direction has high cosine similarity with the preference
    gradient direction (since DPO directly optimizes logprob ratios)
  - Imprint signature: High Gini coefficient of per-layer refusal strength,
    low effective rank of the refusal subspace

**RLHF (PPO-based)**:
  - Refusal is more *distributed* across layers due to policy gradient updates
  - The reward model introduces smoothing that spreads the signal
  - Imprint signature: Lower Gini coefficient, higher effective rank,
    smoother cross-layer alignment profile

**Constitutional AI (CAI)**:
  - Multi-round self-critique creates *layered* refusal with recursive structure
  - Refusal directions at different layers tend to be more mutually orthogonal
  - Imprint signature: Low mean pairwise cosine between layer directions,
    high cone dimensionality

**SFT-only (Supervised Fine-Tuning)**:
  - Simplest imprint — refusal lives mostly in the final few layers
  - Often highly concentrated with low dimensionality
  - Imprint signature: Strong tail-layer bias, low spread

Contributions:
  - Systematic taxonomy of alignment training fingerprints in
    the refusal subspace geometry
  - Quantitative Alignment Imprint Score (AIS) that maps geometric
    features to a probability distribution over training methods
  - Cross-layer spectral analysis to detect recursive CAI structures

References:
    - Rafailov et al. (2023): DPO — Direct Preference Optimization
    - Ouyang et al. (2022): InstructGPT / RLHF
    - Bai et al. (2022): Constitutional AI
    - Lee et al. (2025): Geometric signatures of RLHF
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import torch


@dataclass
class AlignmentImprint:
    """Detected alignment training imprint."""

    # Probability estimates for each method
    dpo_probability: float
    rlhf_probability: float
    cai_probability: float
    sft_probability: float

    # The most likely alignment method
    predicted_method: str

    # Geometric features used for classification
    gini_coefficient: float          # Concentration of refusal strength across layers
    effective_rank: float            # Dimensionality of refusal subspace
    cross_layer_smoothness: float    # How smoothly refusal varies across layers
    tail_layer_bias: float           # Fraction of refusal in final 25% of layers
    mean_pairwise_orthogonality: float  # Mean (1 - |cos|) between layer directions
    spectral_decay_rate: float       # How fast singular values decay

    # Per-layer feature vector
    per_layer_strength: dict[int, float] = field(default_factory=dict)

    # Confidence in the prediction
    confidence: float = 0.0


@dataclass
class BaseInstructDelta:
    """Comparison between base model and instruct model activations.

    This captures what alignment training actually changed — the "delta"
    between the base model's representations and the aligned model's.
    """

    layer_idx: int
    cosine_with_refusal: float       # How aligned is the delta with the refusal direction
    delta_magnitude: float           # How much the layer changed
    delta_direction: torch.Tensor    # Unit vector of the change
    refusal_component: float         # Magnitude of delta along refusal direction
    orthogonal_component: float      # Magnitude of delta orthogonal to refusal


class AlignmentImprintDetector:
    """Detect alignment training method from refusal geometry.

    Analyzes the geometric structure of refusal directions across layers
    to infer which alignment training procedure was used. Different methods
    leave distinct geometric signatures ("imprints") that can be detected
    from the refusal subspace alone.
    """

    # Feature weights for method classification (derived from literature)
    # Format: {method: {feature: (ideal_value, weight)}}
    METHOD_SIGNATURES = {
        "dpo": {
            "gini_coefficient": (0.7, 2.0),      # DPO: concentrated
            "effective_rank": (1.5, 1.5),          # DPO: low-rank
            "cross_layer_smoothness": (0.3, 1.0),  # DPO: not smooth
            "tail_layer_bias": (0.5, 1.0),         # DPO: moderate tail bias
            "mean_pairwise_orthogonality": (0.2, 1.0),  # DPO: aligned
            "spectral_decay_rate": (2.0, 1.5),     # DPO: fast decay
        },
        "rlhf": {
            "gini_coefficient": (0.3, 2.0),        # RLHF: distributed
            "effective_rank": (3.0, 1.5),           # RLHF: higher rank
            "cross_layer_smoothness": (0.7, 1.0),   # RLHF: smooth
            "tail_layer_bias": (0.3, 1.0),          # RLHF: not tail-biased
            "mean_pairwise_orthogonality": (0.4, 1.0),  # RLHF: moderate
            "spectral_decay_rate": (0.8, 1.5),      # RLHF: slow decay
        },
        "cai": {
            "gini_coefficient": (0.4, 1.5),        # CAI: moderate
            "effective_rank": (4.0, 2.0),           # CAI: high rank (recursive)
            "cross_layer_smoothness": (0.5, 1.0),   # CAI: moderate
            "tail_layer_bias": (0.35, 0.5),         # CAI: not strongly biased
            "mean_pairwise_orthogonality": (0.6, 2.0),  # CAI: orthogonal layers
            "spectral_decay_rate": (0.5, 1.5),      # CAI: very slow decay
        },
        "sft": {
            "gini_coefficient": (0.8, 2.0),        # SFT: very concentrated
            "effective_rank": (1.2, 1.5),           # SFT: nearly rank-1
            "cross_layer_smoothness": (0.2, 1.0),   # SFT: not smooth
            "tail_layer_bias": (0.7, 2.0),          # SFT: strong tail bias
            "mean_pairwise_orthogonality": (0.15, 1.0),  # SFT: very aligned
            "spectral_decay_rate": (3.0, 1.5),      # SFT: very fast decay
        },
    }

    def detect_imprint(
        self,
        refusal_directions: dict[int, torch.Tensor],
        refusal_strengths: dict[int, float] | None = None,
    ) -> AlignmentImprint:
        """Detect alignment method from refusal direction geometry.

        Args:
            refusal_directions: {layer_idx: direction_vector} per layer.
            refusal_strengths: {layer_idx: strength} if available.
                If None, uses direction norms.

        Returns:
            AlignmentImprint with method prediction and feature analysis.
        """
        if not refusal_directions:
            return AlignmentImprint(
                dpo_probability=0.25, rlhf_probability=0.25,
                cai_probability=0.25, sft_probability=0.25,
                predicted_method="unknown",
                gini_coefficient=0.0, effective_rank=0.0,
                cross_layer_smoothness=0.0, tail_layer_bias=0.0,
                mean_pairwise_orthogonality=0.0, spectral_decay_rate=0.0,
                confidence=0.0,
            )

        # Compute per-layer strengths
        if refusal_strengths is None:
            strengths = {k: v.norm().item() for k, v in refusal_directions.items()}
        else:
            strengths = dict(refusal_strengths)

        # Extract geometric features
        features = self._extract_features(refusal_directions, strengths)

        # Classify using feature matching
        scores = self._classify(features)

        # Normalize to probabilities via softmax
        max_score = max(scores.values())
        exp_scores = {k: math.exp(v - max_score) for k, v in scores.items()}
        total = sum(exp_scores.values())
        probs = {k: v / total for k, v in exp_scores.items()}

        predicted = max(probs, key=probs.get)
        confidence = probs[predicted]

        return AlignmentImprint(
            dpo_probability=probs["dpo"],
            rlhf_probability=probs["rlhf"],
            cai_probability=probs["cai"],
            sft_probability=probs["sft"],
            predicted_method=predicted,
            gini_coefficient=features["gini_coefficient"],
            effective_rank=features["effective_rank"],
            cross_layer_smoothness=features["cross_layer_smoothness"],
            tail_layer_bias=features["tail_layer_bias"],
            mean_pairwise_orthogonality=features["mean_pairwise_orthogonality"],
            spectral_decay_rate=features["spectral_decay_rate"],
            per_layer_strength=strengths,
            confidence=confidence,
        )

    def compare_base_instruct(
        self,
        base_activations: dict[int, torch.Tensor],
        instruct_activations: dict[int, torch.Tensor],
        refusal_directions: dict[int, torch.Tensor],
    ) -> list[BaseInstructDelta]:
        """Compare base vs. instruct activations to measure alignment delta.

        Args:
            base_activations: {layer_idx: mean_activation} from base model.
            instruct_activations: {layer_idx: mean_activation} from instruct model.
            refusal_directions: {layer_idx: refusal_direction} for decomposition.

        Returns:
            List of per-layer BaseInstructDelta results.
        """
        results = []
        common_layers = set(base_activations.keys()) & set(instruct_activations.keys())

        for layer_idx in sorted(common_layers):
            base_act = base_activations[layer_idx].float().squeeze()
            inst_act = instruct_activations[layer_idx].float().squeeze()
            delta = inst_act - base_act

            delta_mag = delta.norm().item()
            if delta_mag < 1e-10:
                results.append(BaseInstructDelta(
                    layer_idx=layer_idx,
                    cosine_with_refusal=0.0,
                    delta_magnitude=0.0,
                    delta_direction=torch.zeros_like(delta),
                    refusal_component=0.0,
                    orthogonal_component=0.0,
                ))
                continue

            delta_dir = delta / delta.norm()

            # Decompose delta into refusal and orthogonal components
            if layer_idx in refusal_directions:
                ref_dir = refusal_directions[layer_idx].float().squeeze()
                ref_dir = ref_dir / ref_dir.norm().clamp(min=1e-10)
                cos = (delta_dir @ ref_dir).item()
                refusal_comp = abs(cos) * delta_mag
                orth_comp = math.sqrt(max(0, delta_mag**2 - refusal_comp**2))
            else:
                cos = 0.0
                refusal_comp = 0.0
                orth_comp = delta_mag

            results.append(BaseInstructDelta(
                layer_idx=layer_idx,
                cosine_with_refusal=cos,
                delta_magnitude=delta_mag,
                delta_direction=delta_dir,
                refusal_component=refusal_comp,
                orthogonal_component=orth_comp,
            ))

        return results

    def _extract_features(
        self,
        directions: dict[int, torch.Tensor],
        strengths: dict[int, float],
    ) -> dict[str, float]:
        """Extract geometric features from refusal directions."""
        layers = sorted(directions.keys())
        n_layers = len(layers)

        # 1. Gini coefficient of layer strengths
        vals = sorted(strengths.values())
        n = len(vals)
        if n > 0 and sum(vals) > 0:
            cumulative = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(vals))
            gini = cumulative / (n * sum(vals))
        else:
            gini = 0.0
        gini = max(0.0, min(1.0, gini))

        # 2. Effective rank of direction matrix
        if n_layers >= 2:
            D = torch.stack([directions[li].float().squeeze() for li in layers])
            s = torch.linalg.svdvals(D)
            s = s[s > 1e-10]
            if len(s) > 0:
                p = s / s.sum()
                entropy = -(p * p.log()).sum()
                eff_rank = torch.exp(entropy).item()
                # Spectral decay rate
                if len(s) >= 2:
                    decay = (s[0] / s[-1]).item()
                    spectral_decay = math.log(max(1.0, decay))
                else:
                    spectral_decay = 0.0
            else:
                eff_rank = 0.0
                spectral_decay = 0.0
        else:
            eff_rank = 1.0
            spectral_decay = 0.0

        # 3. Cross-layer smoothness (mean cosine between adjacent layers)
        adj_cosines = []
        for i in range(len(layers) - 1):
            d_a = directions[layers[i]].float().squeeze()
            d_b = directions[layers[i + 1]].float().squeeze()
            cos = (d_a @ d_b).abs().item() / max(
                d_a.norm().item() * d_b.norm().item(), 1e-10
            )
            adj_cosines.append(cos)
        smoothness = sum(adj_cosines) / len(adj_cosines) if adj_cosines else 0.0

        # 4. Tail layer bias
        if n_layers >= 4:
            tail_start = layers[int(0.75 * n_layers)]
            total_strength = sum(strengths.values())
            tail_strength = sum(
                v for k, v in strengths.items() if k >= tail_start
            )
            tail_bias = tail_strength / max(total_strength, 1e-10)
        else:
            tail_bias = 0.5

        # 5. Mean pairwise orthogonality
        pair_orths = []
        for i in range(len(layers)):
            for j in range(i + 1, len(layers)):
                d_a = directions[layers[i]].float().squeeze()
                d_b = directions[layers[j]].float().squeeze()
                cos = (d_a @ d_b).abs().item() / max(
                    d_a.norm().item() * d_b.norm().item(), 1e-10
                )
                pair_orths.append(1.0 - cos)
        mean_orth = sum(pair_orths) / len(pair_orths) if pair_orths else 0.0

        return {
            "gini_coefficient": gini,
            "effective_rank": eff_rank,
            "cross_layer_smoothness": smoothness,
            "tail_layer_bias": tail_bias,
            "mean_pairwise_orthogonality": mean_orth,
            "spectral_decay_rate": spectral_decay,
        }

    def _classify(self, features: dict[str, float]) -> dict[str, float]:
        """Compute method scores using Gaussian-kernel feature matching."""
        scores = {}
        for method, signature in self.METHOD_SIGNATURES.items():
            score = 0.0
            for feat_name, (ideal, weight) in signature.items():
                actual = features.get(feat_name, 0.0)
                # Gaussian kernel: exp(-0.5 * ((actual - ideal) / sigma)^2)
                sigma = max(0.3 * abs(ideal), 0.1)
                dist = (actual - ideal) / sigma
                feat_score = math.exp(-0.5 * dist * dist)
                score += weight * feat_score
            scores[method] = score
        return scores

    @staticmethod
    def format_imprint(imprint: AlignmentImprint) -> str:
        """Format alignment imprint as a report."""
        lines = []
        lines.append("Alignment Imprint Detection")
        lines.append("=" * 40)
        lines.append("")
        lines.append(f"Predicted method: {imprint.predicted_method.upper()}")
        lines.append(f"Confidence: {imprint.confidence:.1%}")
        lines.append("")
        lines.append("Method probabilities:")
        lines.append(f"  DPO:  {imprint.dpo_probability:.1%}")
        lines.append(f"  RLHF: {imprint.rlhf_probability:.1%}")
        lines.append(f"  CAI:  {imprint.cai_probability:.1%}")
        lines.append(f"  SFT:  {imprint.sft_probability:.1%}")
        lines.append("")
        lines.append("Geometric features:")
        lines.append(f"  Gini coefficient:    {imprint.gini_coefficient:.3f}")
        lines.append(f"  Effective rank:      {imprint.effective_rank:.2f}")
        lines.append(f"  Cross-layer smooth:  {imprint.cross_layer_smoothness:.3f}")
        lines.append(f"  Tail layer bias:     {imprint.tail_layer_bias:.3f}")
        lines.append(f"  Pairwise orthogon:   {imprint.mean_pairwise_orthogonality:.3f}")
        lines.append(f"  Spectral decay:      {imprint.spectral_decay_rate:.2f}")
        return "\n".join(lines)
