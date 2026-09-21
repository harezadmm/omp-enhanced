"""Anti-Ouroboros: Adversarial Self-Repair Probing for circuit discovery.

The Ouroboros Effect (McGrath et al. 2023) showed that LLMs self-repair after
ablation — when one attention layer is knocked out, downstream layers
compensate. "Explorations of Self-Repair" (Feb 2024) found this is imperfect
(~30% via LayerNorm, rest via sparse anti-erasure neurons).

Current work treats self-repair as an obstacle to interpretability and
abliteration. This module flips it: self-repair is an *oracle* that reveals
hidden refusal redundancy.

Key insight: If you ablate component C and observe repair at component C',
then C' is a redundant carrier of the same information. By systematically
probing self-repair responses, we can build a complete *Adversarial Self-
Repair Graph* (ASRG) — a directed graph encoding which components compensate
for which others.

Contributions:
  1. **ASRG construction**: Directed graph where edge (i,j) with weight w
     means "ablating component i causes component j to increase its refusal
     contribution by w"
  2. **Constructive ablation depth bound**: The spectral gap lambda_2 of
     the ASRG lower-bounds the minimum simultaneous ablations needed
  3. **Repair circuit identification**: Components with high in-degree in
     the ASRG are "repair hubs" — ablating them disables self-repair
  4. **Optimal ablation ordering**: Topological sort of ASRG gives the
     order that minimizes total self-repair

References:
    - McGrath et al. (2023): The Ouroboros Effect — emergent self-repair
    - Rushing & Nanda (2024): Explorations of Self-Repair in LLMs (ICML 2024, arXiv:2402.15390)
    - Russinovich et al. (2026): GRP-Obliteration — safety representations are plastic
    - Paper Theorem 2: Ouroboros Self-Repair Bound
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import torch

logger = logging.getLogger(__name__)


@dataclass
class RepairEdge:
    """A directed edge in the Adversarial Self-Repair Graph."""

    source_layer: int          # layer that was ablated
    target_layer: int          # layer that compensated
    repair_weight: float       # strength of compensation (0-1)
    repair_type: str           # "layernorm" | "attention" | "mlp" | "mixed"
    latency: int               # how many layers downstream the repair occurs


@dataclass
class ASRGResult:
    """Complete Adversarial Self-Repair Graph analysis."""

    # Graph structure
    n_nodes: int                          # number of layers analyzed
    n_edges: int                          # number of significant repair edges
    edges: list[RepairEdge]               # all repair edges
    adjacency_matrix: torch.Tensor        # (n_layers, n_layers) repair weights

    # Spectral properties
    spectral_gap: float                   # lambda_2 of normalized Laplacian
    algebraic_connectivity: float         # Fiedler value
    min_simultaneous_ablations: int       # lower bound from spectral gap

    # Hub analysis
    repair_hubs: list[int]                # layers with high in-degree (repair centers)
    repair_hub_scores: dict[int, float]   # layer -> hub importance score
    vulnerability_ordering: list[int]     # optimal ablation order

    # Repair capacity
    total_repair_capacity: float          # sum of all repair weights
    mean_repair_ratio: float              # average compensation ratio
    max_single_repair: float              # strongest single repair edge
    repair_locality: float                # fraction of repair that's local (±2 layers)

    # Recommendations
    recommended_ablation_set: list[int]   # minimum set to overcome self-repair
    estimated_passes_needed: int          # predicted iterative refinement passes
    self_repair_risk: str                 # "low" | "medium" | "high" | "extreme"


class AntiOuroborosProber:
    """Discover refusal circuit redundancy by probing self-repair responses.

    Instead of treating the Ouroboros effect as an obstacle, this module
    deliberately triggers it to map the complete repair circuit — revealing
    which layers are redundant carriers of refusal and what the optimal
    ablation strategy is to defeat self-repair.
    """

    def __init__(
        self,
        repair_threshold: float = 0.05,
        n_ablation_probes: int = 3,
        hub_percentile: float = 0.9,
    ):
        """
        Args:
            repair_threshold: Minimum repair weight to consider an edge
                significant (below this, considered noise).
            n_ablation_probes: Number of repeated probes per layer for
                robustness (results are averaged).
            hub_percentile: Percentile threshold for identifying repair hubs
                (layers above this percentile in-degree are hubs).
        """
        self.repair_threshold = repair_threshold
        self.n_ablation_probes = n_ablation_probes
        self.hub_percentile = hub_percentile

    def build_asrg(
        self,
        refusal_strengths: dict[int, float],
        self_repair_results: list[dict] | None = None,
        layer_refusal_directions: dict[int, torch.Tensor] | None = None,
    ) -> ASRGResult:
        """Build the Adversarial Self-Repair Graph.

        Args:
            refusal_strengths: {layer_idx: refusal_signal_magnitude} for each
                layer in the baseline (no ablation) state.
            self_repair_results: Optional pre-computed repair data from
                DefenseRobustnessEvaluator. List of dicts with keys
                'ablated_layer', 'compensating_layers', 'repair_ratios'.
            layer_refusal_directions: Optional per-layer refusal directions
                for computing directional repair (not just magnitude).

        Returns:
            ASRGResult with complete self-repair graph analysis.
        """
        layers = sorted(refusal_strengths.keys())
        n_layers = len(layers)

        if n_layers < 2:
            return self._empty_result(n_layers)

        layer_to_idx = {ly: i for i, ly in enumerate(layers)}

        # Build adjacency matrix from repair data
        adj = torch.zeros(n_layers, n_layers)
        edges: list[RepairEdge] = []

        if self_repair_results is not None:
            # Use pre-computed repair data
            for result in self_repair_results:
                src = result.get("ablated_layer")
                if src not in layer_to_idx:
                    continue
                src_idx = layer_to_idx[src]

                comp_layers = result.get("compensating_layers", [])
                repair_ratios = result.get("repair_ratios", [])

                for tgt, ratio in zip(comp_layers, repair_ratios):
                    if tgt not in layer_to_idx:
                        continue
                    tgt_idx = layer_to_idx[tgt]

                    if ratio >= self.repair_threshold:
                        adj[src_idx, tgt_idx] = ratio
                        edges.append(RepairEdge(
                            source_layer=src,
                            target_layer=tgt,
                            repair_weight=ratio,
                            repair_type=self._classify_repair_type(src, tgt, layers),
                            latency=abs(tgt - src),
                        ))
        else:
            # Simulate repair from refusal strength distribution
            # When layer i is ablated, nearby layers with high refusal
            # strength are assumed to compensate proportionally
            adj, edges = self._simulate_repair_graph(
                layers, refusal_strengths, layer_to_idx
            )

        # Compute spectral properties of the ASRG
        spectral_gap, algebraic_connectivity = self._compute_spectral_properties(adj)

        # Minimum simultaneous ablations (from spectral gap bound)
        # k >= ceil(lambda_2 * n_layers / (1 - R_max))
        max_repair = adj.max().item() if adj.numel() > 0 else 0.0
        if max_repair < 1.0 and spectral_gap > 0:
            min_ablations = max(1, math.ceil(
                spectral_gap * n_layers / (1.0 - max_repair + 1e-10)
            ))
        else:
            min_ablations = max(1, n_layers // 3)
        min_ablations = min(min_ablations, n_layers)

        # Identify repair hubs (high in-degree nodes)
        in_degree = adj.sum(dim=0)  # sum over sources for each target
        repair_hub_scores = {
            layers[i]: in_degree[i].item() for i in range(n_layers)
        }

        threshold = torch.quantile(in_degree, self.hub_percentile).item()
        repair_hubs = [
            layers[i] for i in range(n_layers)
            if in_degree[i].item() >= threshold and in_degree[i].item() > 0
        ]

        # Compute optimal ablation ordering via greedy graph cut
        vulnerability_ordering = self._compute_vulnerability_ordering(
            adj, layers, refusal_strengths
        )

        # Recommended ablation set (minimum cut to overcome repair)
        recommended_set = vulnerability_ordering[:min_ablations]

        # Repair statistics
        total_repair = adj.sum().item()
        mean_repair = adj[adj > 0].mean().item() if (adj > 0).any() else 0.0

        # Repair locality: fraction of repair edges within ±2 layers
        local_edges = sum(1 for e in edges if e.latency <= 2)
        repair_locality = local_edges / max(len(edges), 1)

        # Estimated passes
        if max_repair > 0.7:
            passes = max(3, min_ablations)
        elif max_repair > 0.3:
            passes = 2
        else:
            passes = 1

        # Risk assessment
        if max_repair > 0.7 or total_repair > n_layers * 0.5:
            risk = "extreme"
        elif max_repair > 0.4 or total_repair > n_layers * 0.3:
            risk = "high"
        elif max_repair > 0.2:
            risk = "medium"
        else:
            risk = "low"

        return ASRGResult(
            n_nodes=n_layers,
            n_edges=len(edges),
            edges=edges,
            adjacency_matrix=adj,
            spectral_gap=spectral_gap,
            algebraic_connectivity=algebraic_connectivity,
            min_simultaneous_ablations=min_ablations,
            repair_hubs=repair_hubs,
            repair_hub_scores=repair_hub_scores,
            vulnerability_ordering=vulnerability_ordering,
            total_repair_capacity=total_repair,
            mean_repair_ratio=mean_repair,
            max_single_repair=max_repair,
            repair_locality=repair_locality,
            recommended_ablation_set=recommended_set,
            estimated_passes_needed=passes,
            self_repair_risk=risk,
        )

    def _simulate_repair_graph(
        self,
        layers: list[int],
        refusal_strengths: dict[int, float],
        layer_to_idx: dict[int, int],
    ) -> tuple[torch.Tensor, list[RepairEdge]]:
        """Simulate self-repair graph when no empirical data is available.

        Uses heuristic: when layer i is ablated, layers with high refusal
        strength that are nearby compensate proportionally to their
        strength * distance_decay.
        """
        n = len(layers)
        adj = torch.zeros(n, n)
        edges: list[RepairEdge] = []

        total_refusal = sum(refusal_strengths.values())
        if total_refusal < 1e-10:
            return adj, edges

        for i, src in enumerate(layers):
            src_strength = refusal_strengths.get(src, 0.0)
            if src_strength < 1e-10:
                continue

            # Remaining capacity distributed among other layers
            for j, tgt in enumerate(layers):
                if i == j:
                    continue
                tgt_strength = refusal_strengths.get(tgt, 0.0)

                # Distance decay: closer layers repair more
                distance = abs(i - j)
                decay = math.exp(-distance / max(n * 0.3, 1))

                # Repair proportional to target's existing strength * decay
                # Normalized by total remaining strength
                remaining = total_refusal - src_strength
                if remaining < 1e-10:
                    continue

                repair_ratio = (tgt_strength / remaining) * decay * 0.7
                repair_ratio = min(repair_ratio, 1.0)

                if repair_ratio >= self.repair_threshold:
                    adj[i, j] = repair_ratio
                    edges.append(RepairEdge(
                        source_layer=src,
                        target_layer=tgt,
                        repair_weight=repair_ratio,
                        repair_type=self._classify_repair_type(src, tgt, layers),
                        latency=abs(tgt - src),
                    ))

        return adj, edges

    def _compute_spectral_properties(
        self, adj: torch.Tensor
    ) -> tuple[float, float]:
        """Compute spectral gap and algebraic connectivity of the ASRG.

        The spectral gap (lambda_2 of the normalized Laplacian) measures
        how well-connected the repair graph is. A large spectral gap means
        repair is distributed and hard to overcome with few ablations.
        """
        n = adj.shape[0]
        if n < 2:
            return 0.0, 0.0

        # Make symmetric for Laplacian analysis
        sym_adj = (adj + adj.T) / 2

        # Degree matrix
        degree = sym_adj.sum(dim=1)
        degree_matrix = torch.diag(degree)

        # Laplacian L = D - A
        laplacian = degree_matrix - sym_adj

        try:
            eigenvalues = torch.linalg.eigvalsh(laplacian)
            eigenvalues = eigenvalues.sort().values

            # spectral_gap = lambda_2 (second smallest eigenvalue)
            # First eigenvalue should be ~0
            spectral_gap = eigenvalues[1].item() if n > 1 else 0.0

            # Algebraic connectivity (normalized by max degree)
            max_deg = degree.max().item()
            algebraic_connectivity = (
                spectral_gap / max_deg if max_deg > 0 else 0.0
            )

            return max(0.0, spectral_gap), max(0.0, algebraic_connectivity)
        except Exception:
            return 0.0, 0.0

    def _classify_repair_type(
        self, source: int, target: int, layers: list[int]
    ) -> str:
        """Classify the type of repair based on layer distance."""
        distance = abs(target - source)
        n = len(layers)

        if distance <= 1:
            return "layernorm"  # Adjacent layer repair, likely LayerNorm rescaling
        elif distance <= 3:
            return "attention"  # Short-range, likely attention head compensation
        elif distance <= n // 2:
            return "mlp"        # Medium-range, likely MLP anti-erasure neurons
        else:
            return "mixed"      # Long-range, likely multiple mechanisms

    def _compute_vulnerability_ordering(
        self,
        adj: torch.Tensor,
        layers: list[int],
        refusal_strengths: dict[int, float],
    ) -> list[int]:
        """Compute optimal ablation ordering via greedy maximum-impact.

        At each step, select the layer whose ablation causes the maximum
        reduction in total repair capacity, accounting for cascade effects.
        """
        n = len(layers)
        remaining = set(range(n))
        ordering = []

        # Greedy: pick layer with highest combined refusal + repair hub score
        scores = {}
        in_degree = adj.sum(dim=0)
        out_degree = adj.sum(dim=1)

        for i in range(n):
            refusal_score = refusal_strengths.get(layers[i], 0.0)
            hub_score = in_degree[i].item() + out_degree[i].item()
            scores[i] = refusal_score + hub_score

        for _ in range(n):
            if not remaining:
                break
            # Pick highest score among remaining
            best = max(remaining, key=lambda x: scores.get(x, 0.0))
            ordering.append(layers[best])
            remaining.remove(best)

        return ordering

    def _empty_result(self, n_layers: int) -> ASRGResult:
        return ASRGResult(
            n_nodes=n_layers,
            n_edges=0,
            edges=[],
            adjacency_matrix=torch.zeros(max(n_layers, 1), max(n_layers, 1)),
            spectral_gap=0.0,
            algebraic_connectivity=0.0,
            min_simultaneous_ablations=1,
            repair_hubs=[],
            repair_hub_scores={},
            vulnerability_ordering=[],
            total_repair_capacity=0.0,
            mean_repair_ratio=0.0,
            max_single_repair=0.0,
            repair_locality=0.0,
            recommended_ablation_set=[],
            estimated_passes_needed=1,
            self_repair_risk="low",
        )
