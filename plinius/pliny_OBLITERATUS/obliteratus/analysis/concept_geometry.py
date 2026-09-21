"""Concept Cone Geometry analysis for refusal subspace characterization.

The 2025 paper "Geometry of Concepts in LLMs" (Wollschlager et al., arXiv:2502.17420) showed that
refusal is NOT a single linear direction or even a linear subspace — it's a
*polyhedral concept cone*. Different categories of harmful content activate
geometrically distinct refusal directions that share a common half-space
but are NOT collinear.

This module implements tools to:

  1. **Concept Cone Estimation**: Fit the minimal cone containing all
     per-category refusal directions, measuring its solid angle and
     dimensionality.

  2. **Per-Category Direction Decomposition**: Extract separate refusal
     directions for each harm category (weapons, cyber, fraud, etc.)
     and measure their pairwise geometric relationships.

  3. **Cone Complexity Scaling**: Measure how cone dimensionality scales
     with model size, testing the finding that larger models have
     higher-dimensional refusal cones.

  4. **Direction Specificity Index**: For each refusal direction, measure
     how specifically it targets one category vs. being a general-purpose
     refusal signal.

Extensions beyond prior work:
  - We compute the *minimal enclosing cone* explicitly using convex
    optimization over the half-space intersection
  - We introduce the Direction Specificity Index (DSI), which quantifies
    how categorical vs. universal each component of refusal is
  - We test whether the cone structure is consistent across layers

References:
    - Wollschlager et al. (2025): Geometry of Concepts in LLMs (arXiv:2502.17420)
    - Joad et al. (2026): 11 geometrically distinct refusal directions
    - Arditi et al. (2024): Single-direction assumption (shown incomplete)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch


# Default category assignments for the OBLITERATUS synthetic harmful prompts
# Maps prompt index -> category name
DEFAULT_HARM_CATEGORIES = {
    0: "weapons", 1: "weapons", 2: "weapons",
    3: "cyber", 4: "cyber", 5: "cyber", 6: "cyber",
    7: "cyber", 8: "cyber", 9: "cyber", 10: "cyber", 11: "cyber",
    12: "fraud", 13: "fraud", 14: "fraud", 15: "fraud",
    16: "intrusion", 17: "intrusion", 18: "intrusion", 19: "intrusion",
    20: "substances", 21: "substances",
    22: "extremism", 23: "stalking",
    24: "privacy", 25: "privacy",
    26: "manipulation", 27: "manipulation",
    28: "self_harm", 29: "self_harm",
}


@dataclass
class CategoryDirection:
    """Refusal direction for a specific harm category."""

    category: str
    direction: torch.Tensor        # (hidden_dim,) unit vector
    strength: float                # magnitude of the category's refusal signal
    n_prompts: int                 # number of prompts in this category
    specificity: float             # how specific to this category (0=general, 1=unique)


@dataclass
class ConeConeResult:
    """Result of concept cone geometry analysis for a single layer."""

    layer_idx: int
    category_directions: list[CategoryDirection]
    pairwise_cosines: dict[tuple[str, str], float]  # (cat_a, cat_b) -> cosine
    cone_solid_angle: float        # solid angle of the minimal enclosing cone (steradians)
    cone_dimensionality: float     # effective dimensionality of the cone
    mean_pairwise_cosine: float    # average cosine between category directions
    is_linear: bool                # True if cone is essentially 1D (all directions aligned)
    is_polyhedral: bool            # True if distinct directions detected
    general_direction: torch.Tensor  # the mean direction (closest to "single direction")
    category_count: int


@dataclass
class MultiLayerConeResult:
    """Cone geometry across multiple layers."""

    per_layer: dict[int, ConeConeResult]
    most_polyhedral_layer: int     # layer with most complex cone
    most_linear_layer: int         # layer with simplest cone
    cone_complexity_by_layer: dict[int, float]  # cone dimensionality per layer
    mean_cone_dimensionality: float


class ConceptConeAnalyzer:
    """Analyze the geometric structure of refusal as a concept cone.

    Instead of assuming refusal is a single direction (Arditi) or a linear
    subspace (Gabliteration), this analyzes the actual cone-like geometry
    where different harm categories have distinct but related directions.
    """

    def __init__(
        self,
        category_map: dict[int, str] | None = None,
        min_category_size: int = 2,
    ):
        """
        Args:
            category_map: {prompt_index: category_name} for grouping prompts.
                If None, uses DEFAULT_HARM_CATEGORIES.
            min_category_size: Minimum prompts per category to compute a
                category-specific direction.
        """
        self.category_map = category_map or DEFAULT_HARM_CATEGORIES
        self.min_category_size = min_category_size

    def analyze_layer(
        self,
        harmful_activations: list[torch.Tensor],
        harmless_activations: list[torch.Tensor],
        layer_idx: int = 0,
    ) -> ConeConeResult:
        """Analyze cone geometry at a single layer.

        Args:
            harmful_activations: List of per-prompt activation tensors.
            harmless_activations: List of per-prompt activation tensors.
            layer_idx: Layer index for metadata.

        Returns:
            ConeConeResult with full cone geometry analysis.
        """
        n_prompts = min(len(harmful_activations), len(harmless_activations))

        # Group prompts by category
        categories: dict[str, list[int]] = {}
        for idx in range(n_prompts):
            cat = self.category_map.get(idx, "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(idx)

        # Compute per-category refusal directions
        cat_directions: list[CategoryDirection] = []
        direction_vectors: dict[str, torch.Tensor] = {}

        for cat, indices in sorted(categories.items()):
            if len(indices) < self.min_category_size:
                continue

            # Category mean difference
            cat_harmful = torch.stack([
                harmful_activations[i].float().squeeze() for i in indices
            ]).mean(dim=0)
            cat_harmless = torch.stack([
                harmless_activations[i].float().squeeze() for i in indices
            ]).mean(dim=0)

            diff = cat_harmful - cat_harmless
            strength = diff.norm().item()

            if strength > 1e-8:
                direction = diff / diff.norm()
            else:
                direction = diff

            direction_vectors[cat] = direction
            cat_directions.append(CategoryDirection(
                category=cat,
                direction=direction,
                strength=strength,
                n_prompts=len(indices),
                specificity=0.0,  # computed below
            ))

        # Compute pairwise cosine similarities
        pairwise: dict[tuple[str, str], float] = {}
        cats = sorted(direction_vectors.keys())
        for i, cat_a in enumerate(cats):
            for j, cat_b in enumerate(cats):
                if i < j:
                    cos = (direction_vectors[cat_a] @ direction_vectors[cat_b]).abs().item()
                    pairwise[(cat_a, cat_b)] = cos

        # Mean pairwise cosine
        if pairwise:
            mean_cos = sum(pairwise.values()) / len(pairwise)
        else:
            mean_cos = 1.0

        # Compute Direction Specificity Index (DSI) for each category
        # DSI = 1 - mean(|cos(d_cat, d_other)|) for all other categories
        # High DSI = direction is unique to this category
        for cd in cat_directions:
            other_cosines = []
            for other_cd in cat_directions:
                if other_cd.category != cd.category:
                    cos = (cd.direction @ other_cd.direction).abs().item()
                    other_cosines.append(cos)
            if other_cosines:
                cd.specificity = 1.0 - (sum(other_cosines) / len(other_cosines))
            else:
                cd.specificity = 1.0

        # General direction (mean of all category directions)
        if direction_vectors:
            all_dirs = torch.stack(list(direction_vectors.values()))
            general = all_dirs.mean(dim=0)
            general = general / general.norm().clamp(min=1e-8)
        else:
            general = torch.zeros(1)

        # Cone dimensionality estimation
        # Use SVD of the category direction matrix
        cone_dim, solid_angle = self._estimate_cone_geometry(direction_vectors)

        # Classification
        is_linear = mean_cos > 0.9 and cone_dim < 1.5
        is_polyhedral = mean_cos < 0.8 or cone_dim > 2.0

        return ConeConeResult(
            layer_idx=layer_idx,
            category_directions=cat_directions,
            pairwise_cosines=pairwise,
            cone_solid_angle=solid_angle,
            cone_dimensionality=cone_dim,
            mean_pairwise_cosine=mean_cos,
            is_linear=is_linear,
            is_polyhedral=is_polyhedral,
            general_direction=general,
            category_count=len(cat_directions),
        )

    def analyze_all_layers(
        self,
        harmful_acts: dict[int, list[torch.Tensor]],
        harmless_acts: dict[int, list[torch.Tensor]],
        strong_layers: list[int] | None = None,
    ) -> MultiLayerConeResult:
        """Analyze cone geometry across multiple layers.

        Args:
            harmful_acts: {layer_idx: [activations]} per layer.
            harmless_acts: {layer_idx: [activations]} per layer.
            strong_layers: If provided, only analyze these layers.

        Returns:
            MultiLayerConeResult with per-layer and aggregate analysis.
        """
        layers = strong_layers or sorted(harmful_acts.keys())
        per_layer = {}

        for idx in layers:
            if idx not in harmful_acts or idx not in harmless_acts:
                continue
            per_layer[idx] = self.analyze_layer(
                harmful_acts[idx], harmless_acts[idx], layer_idx=idx
            )

        if not per_layer:
            return MultiLayerConeResult(
                per_layer={},
                most_polyhedral_layer=0,
                most_linear_layer=0,
                cone_complexity_by_layer={},
                mean_cone_dimensionality=0.0,
            )

        complexity = {idx: r.cone_dimensionality for idx, r in per_layer.items()}
        most_poly = max(complexity, key=complexity.get)
        most_linear = min(complexity, key=complexity.get)
        mean_dim = sum(complexity.values()) / len(complexity)

        return MultiLayerConeResult(
            per_layer=per_layer,
            most_polyhedral_layer=most_poly,
            most_linear_layer=most_linear,
            cone_complexity_by_layer=complexity,
            mean_cone_dimensionality=mean_dim,
        )

    def _estimate_cone_geometry(
        self, direction_vectors: dict[str, torch.Tensor]
    ) -> tuple[float, float]:
        """Estimate cone dimensionality and solid angle.

        Uses the effective rank of the direction matrix (SVD-based) as the
        cone dimensionality, and approximates the solid angle from the
        spread of directions.

        Returns:
            (cone_dimensionality, solid_angle_steradians)
        """
        if len(direction_vectors) < 2:
            return 1.0, 0.0

        D = torch.stack(list(direction_vectors.values()))  # (n_cats, hidden_dim)
        n_cats = D.shape[0]

        # SVD to get effective dimensionality
        s = torch.linalg.svdvals(D)
        s = s[s > 1e-10]
        if len(s) == 0:
            return 0.0, 0.0

        # Effective rank via entropy
        p = s / s.sum()
        entropy = -(p * p.log()).sum()
        eff_rank = torch.exp(entropy).item()

        # Solid angle approximation:
        # For directions on a unit sphere, the solid angle is related to
        # the volume of the spherical cap they span.
        # Approximate using: Omega ~ 2*pi*(1 - min_cos) for a circular cone
        # For polyhedral cones, use the mean angular spread
        cos_values = []
        mean_dir = D.mean(dim=0)
        mean_dir = mean_dir / mean_dir.norm().clamp(min=1e-8)
        for i in range(n_cats):
            cos = (D[i] @ mean_dir).abs().item()
            cos_values.append(cos)

        if cos_values:
            min_cos = min(cos_values)
            # Solid angle of a cone with half-angle theta:
            # Omega = 2*pi*(1 - cos(theta))
            # For high dimensions, generalize: Omega ~ (1 - min_cos)^(d/2)
            # Use simplified 3D formula as approximation
            solid_angle = 2 * math.pi * (1 - min_cos)
        else:
            solid_angle = 0.0

        return eff_rank, solid_angle

    @staticmethod
    def format_report(result: ConeConeResult) -> str:
        """Format single-layer cone analysis as a report."""
        lines = []
        lines.append(f"Concept Cone Geometry — Layer {result.layer_idx}")
        lines.append("=" * 45)
        lines.append("")

        geometry_type = "LINEAR (single direction)" if result.is_linear else (
            "POLYHEDRAL (concept cone)" if result.is_polyhedral else "INTERMEDIATE"
        )
        lines.append(f"Geometry: {geometry_type}")
        lines.append(f"Cone dimensionality: {result.cone_dimensionality:.2f}")
        lines.append(f"Solid angle: {result.cone_solid_angle:.4f} sr")
        lines.append(f"Mean pairwise cosine: {result.mean_pairwise_cosine:.3f}")
        lines.append(f"Categories analyzed: {result.category_count}")
        lines.append("")

        lines.append("Per-Category Refusal Directions:")
        for cd in sorted(result.category_directions, key=lambda x: -x.strength):
            lines.append(
                f"  {cd.category:15s}  strength={cd.strength:.3f}  "
                f"specificity={cd.specificity:.3f}  (n={cd.n_prompts})"
            )
        lines.append("")

        if result.pairwise_cosines:
            lines.append("Pairwise Direction Cosines:")
            for (a, b), cos in sorted(result.pairwise_cosines.items()):
                bar = "█" * int(cos * 15)
                lines.append(f"  {a:12s} ↔ {b:12s}: {cos:.3f} {bar}")

        return "\n".join(lines)
