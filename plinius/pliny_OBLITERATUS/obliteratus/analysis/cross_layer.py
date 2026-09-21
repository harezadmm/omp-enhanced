"""Cross-layer refusal direction alignment analysis.

A key open question in abliteration research is whether refusal is mediated
by the *same* direction propagated through the residual stream, or by
*different* directions at each layer. This module answers that question
quantitatively by computing pairwise cosine similarities between refusal
directions across all layers.

If refusal uses a single persistent direction, we expect high cosine
similarities across adjacent layers (the residual stream preserves the
direction). If different layers encode refusal independently, similarities
will be low even between adjacent layers.

This analysis also reveals "refusal direction clusters" -- groups of layers
that share similar refusal geometry, which may correspond to distinct
functional stages of refusal processing:
  - Early layers: instruction comprehension
  - Middle layers: harm assessment / refusal decision
  - Late layers: refusal token generation

Contribution: We also compute the "refusal direction flow" --
the cumulative angular drift of the refusal direction through the network,
measured as the total geodesic distance on the unit hypersphere.

References:
    - Arditi et al. (2024): Found refusal concentrated in middle-late layers
    - Joad et al. (2026): Identified 11 geometrically distinct refusal directions
    - Anthropic Biology (2025): Default refusal circuits span specific layer ranges
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class CrossLayerResult:
    """Result of cross-layer alignment analysis."""

    cosine_matrix: torch.Tensor             # (n_layers, n_layers) pairwise cosines
    layer_indices: list[int]                # which layers have refusal directions
    clusters: list[list[int]]               # groups of aligned layers
    angular_drift: list[float]              # cumulative angular drift per layer
    total_geodesic_distance: float          # total direction drift through network
    mean_adjacent_cosine: float             # avg cosine between consecutive layers
    direction_persistence_score: float      # 0=independent per layer, 1=single direction
    cluster_count: int                      # number of distinct direction clusters


class CrossLayerAlignmentAnalyzer:
    """Analyze how refusal directions relate across transformer layers.

    Computes a full pairwise cosine similarity matrix and identifies
    clusters of layers that share similar refusal geometry.
    """

    def __init__(self, cluster_threshold: float = 0.85):
        """
        Args:
            cluster_threshold: Minimum cosine similarity for two layers
                to be considered in the same refusal direction cluster.
        """
        self.cluster_threshold = cluster_threshold

    def analyze(
        self,
        refusal_directions: dict[int, torch.Tensor],
        strong_layers: list[int] | None = None,
    ) -> CrossLayerResult:
        """Compute cross-layer alignment analysis.

        Args:
            refusal_directions: {layer_idx: direction_tensor} for each layer.
                Directions should be (hidden_dim,) unit vectors.
            strong_layers: Optional subset of layers to analyze. If None,
                all layers with directions are included.

        Returns:
            CrossLayerResult with full alignment analysis.
        """
        if strong_layers is not None:
            indices = sorted(strong_layers)
        else:
            indices = sorted(refusal_directions.keys())

        if not indices:
            return CrossLayerResult(
                cosine_matrix=torch.zeros(0, 0),
                layer_indices=[],
                clusters=[],
                angular_drift=[],
                total_geodesic_distance=0.0,
                mean_adjacent_cosine=0.0,
                direction_persistence_score=0.0,
                cluster_count=0,
            )

        # Stack all directions into a matrix
        directions = []
        for idx in indices:
            d = refusal_directions[idx].float()
            if d.dim() > 1:
                d = d.squeeze()
            d = d / d.norm().clamp(min=1e-8)
            directions.append(d)

        D = torch.stack(directions)  # (n_layers, hidden_dim)
        n = len(indices)

        # Pairwise cosine similarity matrix (using absolute value since
        # direction sign is arbitrary in SVD)
        cosine_matrix = (D @ D.T).abs()  # (n, n)

        # Adjacent layer cosines (for layers in sorted order)
        adjacent_cosines = []
        for i in range(n - 1):
            adjacent_cosines.append(cosine_matrix[i, i + 1].item())

        mean_adjacent = sum(adjacent_cosines) / max(len(adjacent_cosines), 1)

        # Angular drift: cumulative angle change from layer to layer
        angular_drift = [0.0]
        total_geodesic = 0.0
        for i in range(n - 1):
            cos_val = cosine_matrix[i, i + 1].clamp(max=1.0).item()
            angle = torch.acos(torch.tensor(cos_val)).item()
            total_geodesic += angle
            angular_drift.append(total_geodesic)

        # Direction persistence score:
        # 1.0 = all layers use identical direction (perfect persistence)
        # 0.0 = all layers use orthogonal directions (no persistence)
        # Computed as mean off-diagonal cosine similarity
        if n > 1:
            mask = ~torch.eye(n, dtype=torch.bool)
            persistence = cosine_matrix[mask].mean().item()
        else:
            persistence = 1.0

        # Cluster detection via greedy agglomerative approach
        clusters = self._find_clusters(cosine_matrix, indices)

        return CrossLayerResult(
            cosine_matrix=cosine_matrix,
            layer_indices=indices,
            clusters=clusters,
            angular_drift=angular_drift,
            total_geodesic_distance=total_geodesic,
            mean_adjacent_cosine=mean_adjacent,
            direction_persistence_score=persistence,
            cluster_count=len(clusters),
        )

    def _find_clusters(
        self, cosine_matrix: torch.Tensor, indices: list[int]
    ) -> list[list[int]]:
        """Find clusters of layers with similar refusal directions.

        Uses single-linkage clustering: two layers are in the same cluster
        if their cosine similarity exceeds the threshold. Connected
        components form the clusters.
        """
        n = len(indices)
        if n == 0:
            return []

        # Build adjacency from threshold
        adj = cosine_matrix >= self.cluster_threshold

        # Find connected components via BFS
        visited = set()
        clusters = []

        for i in range(n):
            if i in visited:
                continue
            # BFS from i
            cluster = []
            queue = [i]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                cluster.append(indices[node])
                for j in range(n):
                    if j not in visited and adj[node, j]:
                        queue.append(j)
            clusters.append(sorted(cluster))

        return sorted(clusters, key=lambda c: c[0])

    @staticmethod
    def format_report(result: CrossLayerResult) -> str:
        """Format cross-layer analysis as a human-readable report."""
        lines = []
        lines.append("Cross-Layer Refusal Direction Alignment Analysis")
        lines.append("=" * 52)
        lines.append("")

        if not result.layer_indices:
            lines.append("No layers to analyze.")
            return "\n".join(lines)

        lines.append(f"Layers analyzed: {result.layer_indices}")
        lines.append(f"Direction persistence score: {result.direction_persistence_score:.3f}")
        lines.append("  (1.0 = single direction, 0.0 = all orthogonal)")
        lines.append(f"Mean adjacent-layer cosine: {result.mean_adjacent_cosine:.3f}")
        lines.append(f"Total geodesic distance: {result.total_geodesic_distance:.3f} rad")
        lines.append(f"Number of direction clusters: {result.cluster_count}")
        lines.append("")

        # Cluster summary
        lines.append("Direction Clusters:")
        for i, cluster in enumerate(result.clusters):
            lines.append(f"  Cluster {i + 1}: layers {cluster}")
        lines.append("")

        # Angular drift
        lines.append("Cumulative Angular Drift:")
        for i, (idx, drift) in enumerate(
            zip(result.layer_indices, result.angular_drift)
        ):
            bar_len = int(drift / max(result.total_geodesic_distance, 0.01) * 20)
            lines.append(f"  layer {idx:3d}: {drift:.3f} rad {'▓' * bar_len}")
        lines.append("")

        # Cosine matrix (abbreviated for large models)
        n = len(result.layer_indices)
        if n <= 20:
            lines.append("Pairwise Cosine Similarity Matrix:")
            header = "       " + "".join(f"{idx:6d}" for idx in result.layer_indices)
            lines.append(header)
            for i, idx_i in enumerate(result.layer_indices):
                row = f"  {idx_i:3d}  "
                for j in range(n):
                    val = result.cosine_matrix[i, j].item()
                    row += f" {val:.3f}"
                lines.append(row)
        else:
            lines.append(f"(Cosine matrix too large to display: {n}x{n})")

        return "\n".join(lines)
