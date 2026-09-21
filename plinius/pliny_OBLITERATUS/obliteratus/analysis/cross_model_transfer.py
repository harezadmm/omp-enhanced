"""Cross-Model Transfer Analysis for refusal direction generalization.

A critical question for abliteration research: Do refusal directions
transfer across models? This has major implications:

  - If directions transfer, alignment has a *universal* geometric structure
    that doesn't depend on the specific model
  - If they don't, each model needs its own abliteration pass, and the
    geometry is model-specific

This module tests transfer at two levels:

  1. **Cross-model transfer**: Does a refusal direction extracted from
     Model A work when applied to Model B?

  2. **Cross-category transfer**: Does a direction extracted from one
     harm category (e.g., weapons) transfer to another (e.g., cyber)?

  3. **Cross-layer transfer**: Does a direction from layer L work at
     layer L' in the same model?

Metrics:
  - **Transfer Score**: Cosine similarity between directions from
    different sources
  - **Transfer Effectiveness**: How much refusal is removed when using
    a transferred direction (vs. native direction)
  - **Universality Index**: Aggregate measure of how universal the
    refusal geometry is

Contributions:
  - Systematic cross-model refusal direction transfer analysis
  - Cross-category transfer matrix revealing which harm types share
    refusal mechanisms
  - Universality Index quantifying the model-independence of refusal

References:
    - Arditi et al. (2024): Implicit claim of universality (single direction)
    - Wollschlager et al. (2025): Category-specific directions (arXiv:2502.17420)
    - Zou et al. (2023): Universal adversarial suffixes (related concept)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch


@dataclass
class TransferPair:
    """Transfer analysis between two direction sources."""

    source: str                    # identifier of source direction
    target: str                    # identifier of target direction
    cosine_similarity: float       # cos(source_dir, target_dir)
    transfer_effectiveness: float  # how much refusal is removed using source on target
    angular_distance: float        # arccos(|cos|) in degrees


@dataclass
class CrossModelResult:
    """Cross-model transfer analysis."""

    model_a: str
    model_b: str
    per_layer_transfer: dict[int, TransferPair]
    mean_transfer_score: float
    best_transfer_layer: int
    worst_transfer_layer: int
    transfer_above_threshold: float  # fraction of layers with cos > 0.5


@dataclass
class CrossCategoryResult:
    """Cross-category transfer matrix."""

    categories: list[str]
    transfer_matrix: dict[tuple[str, str], float]  # (cat_a, cat_b) -> cosine
    mean_cross_category_transfer: float
    most_universal_category: str      # highest mean transfer to others
    most_specific_category: str       # lowest mean transfer to others
    category_clusters: list[list[str]]  # groups of categories with high mutual transfer


@dataclass
class CrossLayerResult:
    """Cross-layer transfer analysis."""

    layer_pairs: dict[tuple[int, int], float]  # (layer_a, layer_b) -> cosine
    mean_adjacent_transfer: float       # mean cos between adjacent layers
    mean_distant_transfer: float        # mean cos between non-adjacent layers
    transfer_decay_rate: float          # how fast transfer drops with layer distance
    persistent_layers: list[int]        # layers whose direction transfers well everywhere


@dataclass
class UniversalityReport:
    """Comprehensive universality analysis."""

    cross_model: CrossModelResult | None
    cross_category: CrossCategoryResult | None
    cross_layer: CrossLayerResult | None
    universality_index: float    # 0 = completely model-specific, 1 = fully universal


class TransferAnalyzer:
    """Analyze how well refusal directions transfer across contexts.

    Tests whether the geometric structure of refusal is universal
    (model-independent) or specific to each model/category/layer.
    """

    def __init__(
        self,
        transfer_threshold: float = 0.5,
        cluster_threshold: float = 0.7,
    ):
        """
        Args:
            transfer_threshold: Minimum cosine for "successful" transfer.
            cluster_threshold: Minimum cosine for same-cluster classification.
        """
        self.transfer_threshold = transfer_threshold
        self.cluster_threshold = cluster_threshold

    def analyze_cross_model(
        self,
        directions_a: dict[int, torch.Tensor],
        directions_b: dict[int, torch.Tensor],
        model_a_name: str = "model_a",
        model_b_name: str = "model_b",
    ) -> CrossModelResult:
        """Analyze transfer between two models.

        Args:
            directions_a: {layer_idx: refusal_direction} from model A.
            directions_b: {layer_idx: refusal_direction} from model B.
            model_a_name: Name of model A.
            model_b_name: Name of model B.

        Returns:
            CrossModelResult with per-layer transfer scores.
        """
        common = set(directions_a.keys()) & set(directions_b.keys())
        per_layer = {}

        for ly in sorted(common):
            d_a = directions_a[ly].float().reshape(-1)
            d_b = directions_b[ly].float().reshape(-1)

            # Handle dimension mismatch
            min_dim = min(d_a.shape[-1], d_b.shape[-1])
            d_a = d_a[:min_dim]
            d_b = d_b[:min_dim]

            d_a = d_a / d_a.norm().clamp(min=1e-10)
            d_b = d_b / d_b.norm().clamp(min=1e-10)

            cos = (d_a @ d_b).abs().item()
            angle = math.degrees(math.acos(min(1.0, cos)))

            per_layer[ly] = TransferPair(
                source=model_a_name,
                target=model_b_name,
                cosine_similarity=cos,
                transfer_effectiveness=cos,  # approximation
                angular_distance=angle,
            )

        if not per_layer:
            return CrossModelResult(
                model_a=model_a_name, model_b=model_b_name,
                per_layer_transfer={}, mean_transfer_score=0.0,
                best_transfer_layer=0, worst_transfer_layer=0,
                transfer_above_threshold=0.0,
            )

        scores = {ly: p.cosine_similarity for ly, p in per_layer.items()}
        mean_score = sum(scores.values()) / len(scores)
        best = max(scores, key=scores.get)
        worst = min(scores, key=scores.get)
        above = sum(1 for v in scores.values() if v > self.transfer_threshold) / len(scores)

        return CrossModelResult(
            model_a=model_a_name,
            model_b=model_b_name,
            per_layer_transfer=per_layer,
            mean_transfer_score=mean_score,
            best_transfer_layer=best,
            worst_transfer_layer=worst,
            transfer_above_threshold=above,
        )

    def analyze_cross_category(
        self,
        category_directions: dict[str, torch.Tensor],
    ) -> CrossCategoryResult:
        """Analyze transfer between harm categories.

        Args:
            category_directions: {category_name: refusal_direction}.

        Returns:
            CrossCategoryResult with transfer matrix.
        """
        cats = sorted(category_directions.keys())
        matrix = {}

        for i, cat_a in enumerate(cats):
            for j, cat_b in enumerate(cats):
                if i < j:
                    d_a = category_directions[cat_a].float().reshape(-1)
                    d_b = category_directions[cat_b].float().reshape(-1)
                    d_a = d_a / d_a.norm().clamp(min=1e-10)
                    d_b = d_b / d_b.norm().clamp(min=1e-10)
                    cos = (d_a @ d_b).abs().item()
                    matrix[(cat_a, cat_b)] = cos
                    matrix[(cat_b, cat_a)] = cos  # symmetric

        if not matrix:
            return CrossCategoryResult(
                categories=cats, transfer_matrix={},
                mean_cross_category_transfer=0.0,
                most_universal_category=cats[0] if cats else "",
                most_specific_category=cats[0] if cats else "",
                category_clusters=[cats],
            )

        # Mean cross-category transfer
        unique_pairs = {(a, b): v for (a, b), v in matrix.items() if a < b}
        mean_transfer = sum(unique_pairs.values()) / len(unique_pairs) if unique_pairs else 0.0

        # Per-category mean transfer
        cat_means = {}
        for cat in cats:
            others = [matrix.get((cat, other), 0.0) for other in cats if other != cat]
            cat_means[cat] = sum(others) / len(others) if others else 0.0

        most_universal = max(cat_means, key=cat_means.get) if cat_means else ""
        most_specific = min(cat_means, key=cat_means.get) if cat_means else ""

        # Cluster detection via simple agglomerative approach
        clusters = self._cluster_categories(cats, matrix)

        return CrossCategoryResult(
            categories=cats,
            transfer_matrix=matrix,
            mean_cross_category_transfer=mean_transfer,
            most_universal_category=most_universal,
            most_specific_category=most_specific,
            category_clusters=clusters,
        )

    def analyze_cross_layer(
        self,
        refusal_directions: dict[int, torch.Tensor],
    ) -> CrossLayerResult:
        """Analyze how well directions transfer between layers.

        Args:
            refusal_directions: {layer_idx: refusal_direction}.

        Returns:
            CrossLayerResult with layer-pair transfer scores.
        """
        layers = sorted(refusal_directions.keys())
        pairs = {}

        for i, l_a in enumerate(layers):
            for j, l_b in enumerate(layers):
                if i < j:
                    d_a = refusal_directions[l_a].float().reshape(-1)
                    d_b = refusal_directions[l_b].float().reshape(-1)
                    d_a = d_a / d_a.norm().clamp(min=1e-10)
                    d_b = d_b / d_b.norm().clamp(min=1e-10)
                    cos = (d_a @ d_b).abs().item()
                    pairs[(l_a, l_b)] = cos

        if not pairs:
            return CrossLayerResult(
                layer_pairs={}, mean_adjacent_transfer=0.0,
                mean_distant_transfer=0.0, transfer_decay_rate=0.0,
                persistent_layers=[],
            )

        # Adjacent vs distant
        adjacent = []
        distant = []
        for (a, b), cos in pairs.items():
            if abs(a - b) == 1 or (layers.index(b) - layers.index(a) == 1):
                adjacent.append(cos)
            else:
                distant.append(cos)

        mean_adj = sum(adjacent) / len(adjacent) if adjacent else 0.0
        mean_dist = sum(distant) / len(distant) if distant else 0.0

        # Decay rate: fit cos ~ exp(-rate * |layer_a - layer_b|)
        decay_rate = self._estimate_decay_rate(pairs)

        # Persistent layers: directions that transfer well everywhere
        persistent = []
        for ly in layers:
            others = [pairs.get((min(ly, l2), max(ly, l2)), 0.0)
                       for l2 in layers if l2 != ly]
            mean = sum(others) / len(others) if others else 0.0
            if mean > self.transfer_threshold:
                persistent.append(ly)

        return CrossLayerResult(
            layer_pairs=pairs,
            mean_adjacent_transfer=mean_adj,
            mean_distant_transfer=mean_dist,
            transfer_decay_rate=decay_rate,
            persistent_layers=persistent,
        )

    def compute_universality_index(
        self,
        cross_model: CrossModelResult | None = None,
        cross_category: CrossCategoryResult | None = None,
        cross_layer: CrossLayerResult | None = None,
    ) -> UniversalityReport:
        """Compute aggregate Universality Index.

        Combines all transfer analyses into a single 0-1 score.
        Higher = more universal refusal geometry.

        Returns:
            UniversalityReport with aggregate score.
        """
        scores = []
        weights = []

        if cross_model is not None:
            scores.append(cross_model.mean_transfer_score)
            weights.append(3.0)  # Most important for universality

        if cross_category is not None:
            scores.append(cross_category.mean_cross_category_transfer)
            weights.append(2.0)

        if cross_layer is not None:
            scores.append(cross_layer.mean_adjacent_transfer)
            weights.append(1.0)

        if scores:
            universality = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        else:
            universality = 0.0

        return UniversalityReport(
            cross_model=cross_model,
            cross_category=cross_category,
            cross_layer=cross_layer,
            universality_index=universality,
        )

    def _cluster_categories(
        self,
        categories: list[str],
        matrix: dict[tuple[str, str], float],
    ) -> list[list[str]]:
        """Simple single-link clustering of categories."""
        # Union-find for clustering
        parent = {cat: cat for cat in categories}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for (a, b), cos in matrix.items():
            if a < b and cos > self.cluster_threshold:
                union(a, b)

        clusters_dict = {}
        for cat in categories:
            root = find(cat)
            if root not in clusters_dict:
                clusters_dict[root] = []
            clusters_dict[root].append(cat)

        return list(clusters_dict.values())

    def _estimate_decay_rate(
        self, pairs: dict[tuple[int, int], float],
    ) -> float:
        """Estimate exponential decay of transfer with layer distance."""
        if not pairs:
            return 0.0

        distances = []
        log_cosines = []
        for (a, b), cos in pairs.items():
            d = abs(b - a)
            if cos > 1e-10 and d > 0:
                distances.append(d)
                log_cosines.append(math.log(cos))

        if len(distances) < 2:
            return 0.0

        # Linear regression: log(cos) = -rate * distance
        mean_d = sum(distances) / len(distances)
        mean_lc = sum(log_cosines) / len(log_cosines)
        num = sum((d - mean_d) * (lc - mean_lc) for d, lc in zip(distances, log_cosines))
        den = sum((d - mean_d) ** 2 for d in distances)

        if abs(den) < 1e-10:
            return 0.0

        return max(0.0, -(num / den))

    @staticmethod
    def format_cross_model(result: CrossModelResult) -> str:
        """Format cross-model transfer report."""
        lines = []
        lines.append(f"Cross-Model Transfer: {result.model_a} → {result.model_b}")
        lines.append("=" * 55)
        lines.append("")
        lines.append(f"Mean transfer score: {result.mean_transfer_score:.3f}")
        lines.append(f"Best transfer layer: {result.best_transfer_layer}")
        lines.append(f"Worst transfer layer: {result.worst_transfer_layer}")
        lines.append(f"Layers above threshold: {result.transfer_above_threshold:.0%}")
        lines.append("")
        lines.append("Per-layer transfer:")
        for ly in sorted(result.per_layer_transfer.keys()):
            p = result.per_layer_transfer[ly]
            bar = "█" * int(p.cosine_similarity * 15)
            lines.append(f"  Layer {ly:3d}: cos={p.cosine_similarity:.3f} {bar}")
        return "\n".join(lines)

    @staticmethod
    def format_cross_category(result: CrossCategoryResult) -> str:
        """Format cross-category transfer report."""
        lines = []
        lines.append("Cross-Category Transfer Matrix")
        lines.append("=" * 45)
        lines.append("")
        lines.append(f"Mean transfer: {result.mean_cross_category_transfer:.3f}")
        lines.append(f"Most universal: {result.most_universal_category}")
        lines.append(f"Most specific: {result.most_specific_category}")
        lines.append(f"Clusters: {len(result.category_clusters)}")
        lines.append("")
        for (a, b), cos in sorted(result.transfer_matrix.items()):
            if a < b:
                lines.append(f"  {a:15s} ↔ {b:15s}: {cos:.3f}")
        return "\n".join(lines)

    @staticmethod
    def format_universality(report: UniversalityReport) -> str:
        """Format universality report."""
        lines = []
        lines.append("Universality Index Report")
        lines.append("=" * 35)
        lines.append("")
        lines.append(f"Universality Index: {report.universality_index:.3f}")
        lines.append("")
        if report.universality_index > 0.7:
            lines.append("FINDING: Refusal geometry is largely UNIVERSAL.")
            lines.append("Directions from one model likely transfer to others.")
        elif report.universality_index < 0.3:
            lines.append("FINDING: Refusal geometry is MODEL-SPECIFIC.")
            lines.append("Each model requires its own abliteration pass.")
        else:
            lines.append("FINDING: Refusal geometry has moderate universality.")
            lines.append("Some transfer is possible but model-specific tuning helps.")
        return "\n".join(lines)
