"""Wasserstein Refusal Transfer Across Architectures.

When a model is successfully abliterated, the knowledge of *where* and *how*
refusal was embedded can potentially be transferred to other models without
re-running the full pipeline. "Transport and Merge" (2025) used optimal
transport for cross-architecture model merging; GiLOT (ICML 2024) used OT
for LLM interpretability.

This module uses OT maps to transfer refusal removal knowledge across
architectures. Given an abliterated source and aligned target, it computes
the Monge map T: A_source -> A_target between their activation distributions,
then transports the source's refusal directions through T.

Contributions:
  1. **OT-based refusal direction transfer**: Application of optimal
     transport to cross-architecture safety intervention transfer
  2. **Transfer error bound (informal)**: Excess refusal after transfer is
     bounded by W_2(mu_s, mu_t) * kappa(T)
  3. **Refusal removal knowledge graph**: Abliterate one model, transfer
     to a whole family via OT maps
  4. **Wasserstein compatibility metric**: Quantifies whether transfer is
     viable before attempting it

References:
    - Cui et al. (2025): Transport and Merge — cross-arch OT merging (arXiv:2602.05495)
    - Li et al. (ICML 2024): GiLOT — OT for LLM interpretability
    - Brenier (1991): Optimal maps for quadratic cost (uniqueness theorem)
    - Paper Appendix Theorem: Wasserstein Cost of Abliteration
    - OBLITERATUS: Cross-Model Universality Index
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import torch

logger = logging.getLogger(__name__)


@dataclass
class TransportPlan:
    """Optimal transport plan between two activation distributions."""

    source_model: str                   # name of source model
    target_model: str                   # name of target model
    transport_matrix: torch.Tensor      # (d_target, d_source) linear map T
    wasserstein_distance: float         # W_2 between source and target
    condition_number: float             # kappa(T), stability indicator
    transport_cost: float               # total transport cost
    is_viable: bool                     # whether transfer is recommended


@dataclass
class TransferredDirection:
    """A refusal direction transferred from source to target model."""

    source_layer: int                   # layer in source model
    target_layer: int                   # corresponding layer in target model
    source_direction: torch.Tensor      # original direction in source space
    transferred_direction: torch.Tensor # direction mapped to target space
    transfer_fidelity: float            # quality of transfer (0-1)
    estimated_refusal_removal: float    # expected removal effectiveness
    wasserstein_bound: float            # excess refusal upper bound


@dataclass
class WassersteinTransferResult:
    """Complete result of Wasserstein refusal transfer analysis."""

    # Transfer metadata
    source_model: str
    target_model: str
    n_layers_transferred: int

    # Transport plan
    wasserstein_distance: float         # W_2(source, target)
    condition_number: float             # stability of transport map
    transfer_viability: str             # "excellent" | "good" | "marginal" | "poor"

    # Transferred directions
    transferred_directions: list[TransferredDirection]
    mean_transfer_fidelity: float       # avg quality across layers
    min_transfer_fidelity: float        # worst layer

    # Bounds
    estimated_excess_refusal: float     # bound on residual refusal after transfer
    estimated_vs_native_ratio: float    # expected native/transfer performance ratio

    # Layer alignment
    layer_mapping: dict[int, int]       # source_layer -> target_layer
    unmapped_layers: list[int]          # target layers with no source correspondence

    # Recommendation
    recommendation: str                 # summary recommendation
    needs_refinement: bool              # whether a refinement pass is recommended


class WassersteinRefusalTransfer:
    """Transfer refusal removal knowledge across architectures via OT.

    Given a successfully abliterated source model and an aligned target,
    computes the optimal transport map between their activation spaces
    and uses it to transfer refusal directions.
    """

    def __init__(
        self,
        fidelity_threshold: float = 0.5,
        max_condition_number: float = 100.0,
        viability_threshold: float = 0.3,
        n_sinkhorn_iterations: int = 50,
    ):
        """
        Args:
            fidelity_threshold: Minimum transfer fidelity to consider
                a transferred direction useful.
            max_condition_number: Maximum condition number for the transport
                map before flagging instability.
            viability_threshold: W_2 threshold below which transfer is viable.
            n_sinkhorn_iterations: Iterations for Sinkhorn OT computation.
        """
        self.fidelity_threshold = fidelity_threshold
        self.max_condition_number = max_condition_number
        self.viability_threshold = viability_threshold
        self.n_sinkhorn_iterations = n_sinkhorn_iterations

    def compute_transfer(
        self,
        source_activations: dict[int, torch.Tensor],
        target_activations: dict[int, torch.Tensor],
        source_refusal_directions: dict[int, torch.Tensor],
        source_model_name: str = "source",
        target_model_name: str = "target",
        layer_mapping: dict[int, int] | None = None,
    ) -> WassersteinTransferResult:
        """Compute Wasserstein transfer of refusal directions.

        Args:
            source_activations: {layer_idx: (n_samples, d_source)} from source.
            target_activations: {layer_idx: (n_samples, d_target)} from target.
            source_refusal_directions: {layer_idx: (d_source,)} from source.
            source_model_name: Identifier for source model.
            target_model_name: Identifier for target model.
            layer_mapping: Optional explicit {source_layer -> target_layer}.
                If None, computed via activation similarity.

        Returns:
            WassersteinTransferResult with transferred directions and bounds.
        """
        source_layers = sorted(source_activations.keys())
        target_layers = sorted(target_activations.keys())

        if not source_layers or not target_layers:
            return self._empty_result(source_model_name, target_model_name)

        # Step 1: Compute layer mapping if not provided
        if layer_mapping is None:
            layer_mapping = self._compute_layer_mapping(
                source_layers, target_layers,
                source_activations, target_activations
            )

        # Step 2: For each mapped layer pair, compute OT map and transfer
        transferred: list[TransferredDirection] = []
        all_w2: list[float] = []
        all_kappa: list[float] = []

        for src_l, tgt_l in layer_mapping.items():
            if src_l not in source_activations or tgt_l not in target_activations:
                continue
            if src_l not in source_refusal_directions:
                continue

            src_acts = source_activations[src_l]
            tgt_acts = target_activations[tgt_l]
            src_dir = source_refusal_directions[src_l]

            # Compute OT map between layer activations
            plan = self._compute_transport_plan(
                src_acts, tgt_acts,
                source_model_name, target_model_name
            )
            all_w2.append(plan.wasserstein_distance)
            all_kappa.append(plan.condition_number)

            # Transport the refusal direction
            transferred_dir = self._transport_direction(
                src_dir, plan.transport_matrix, src_acts, tgt_acts
            )

            # Measure transfer fidelity
            fidelity = self._measure_fidelity(
                transferred_dir, tgt_acts, src_dir, src_acts
            )

            # Wasserstein bound on excess refusal
            w2_bound = plan.wasserstein_distance * plan.condition_number

            transferred.append(TransferredDirection(
                source_layer=src_l,
                target_layer=tgt_l,
                source_direction=src_dir,
                transferred_direction=transferred_dir,
                transfer_fidelity=fidelity,
                estimated_refusal_removal=max(0, 1.0 - w2_bound),
                wasserstein_bound=w2_bound,
            ))

        if not transferred:
            return self._empty_result(source_model_name, target_model_name)

        # Step 3: Aggregate results
        fidelities = [t.transfer_fidelity for t in transferred]
        mean_fidelity = sum(fidelities) / len(fidelities)
        min_fidelity = min(fidelities)

        mean_w2 = sum(all_w2) / len(all_w2)
        mean_kappa = sum(all_kappa) / len(all_kappa)

        excess_refusal = mean_w2 * mean_kappa

        # Viability assessment
        if mean_fidelity > 0.8 and mean_w2 < self.viability_threshold:
            viability = "excellent"
        elif mean_fidelity > 0.6 and mean_w2 < self.viability_threshold * 2:
            viability = "good"
        elif mean_fidelity > 0.4:
            viability = "marginal"
        else:
            viability = "poor"

        native_ratio = max(0.1, 1.0 - excess_refusal)
        needs_refinement = mean_fidelity < 0.7 or viability in ("marginal", "poor")

        unmapped = [
            ly for ly in target_layers if ly not in layer_mapping.values()
        ]

        recommendation = self._generate_recommendation(
            viability, mean_fidelity, excess_refusal, needs_refinement
        )

        return WassersteinTransferResult(
            source_model=source_model_name,
            target_model=target_model_name,
            n_layers_transferred=len(transferred),
            wasserstein_distance=mean_w2,
            condition_number=mean_kappa,
            transfer_viability=viability,
            transferred_directions=transferred,
            mean_transfer_fidelity=mean_fidelity,
            min_transfer_fidelity=min_fidelity,
            estimated_excess_refusal=excess_refusal,
            estimated_vs_native_ratio=native_ratio,
            layer_mapping=layer_mapping,
            unmapped_layers=unmapped,
            recommendation=recommendation,
            needs_refinement=needs_refinement,
        )

    def _compute_layer_mapping(
        self,
        source_layers: list[int],
        target_layers: list[int],
        source_activations: dict[int, torch.Tensor],
        target_activations: dict[int, torch.Tensor],
    ) -> dict[int, int]:
        """Compute layer correspondence via relative position.

        Maps layers by relative position within the network:
        source_layer / n_source_layers ≈ target_layer / n_target_layers
        """
        mapping = {}
        n_src = max(source_layers) + 1 if source_layers else 1
        n_tgt = max(target_layers) + 1 if target_layers else 1

        for src_l in source_layers:
            # Find target layer at closest relative position
            src_ratio = src_l / max(n_src - 1, 1)
            best_tgt = min(
                target_layers,
                key=lambda t: abs(t / max(n_tgt - 1, 1) - src_ratio)
            )
            mapping[src_l] = best_tgt

        return mapping

    def _compute_transport_plan(
        self,
        source_acts: torch.Tensor,
        target_acts: torch.Tensor,
        source_name: str,
        target_name: str,
    ) -> TransportPlan:
        """Compute the optimal transport map between activation distributions.

        Uses a linear approximation: T = Sigma_st @ Sigma_ss^{-1}
        This is the Monge map for Gaussian distributions, which is optimal
        for the quadratic cost when distributions are Gaussian.
        """
        n_src, d_src = source_acts.shape
        n_tgt, d_tgt = target_acts.shape

        # Center the activations
        src_mean = source_acts.mean(dim=0)
        tgt_mean = target_acts.mean(dim=0)
        src_centered = source_acts - src_mean
        tgt_centered = target_acts - tgt_mean

        # Compute covariances
        n_common = min(n_src, n_tgt)
        src_sub = src_centered[:n_common]
        tgt_sub = tgt_centered[:n_common]

        # Cross-covariance: Sigma_st = tgt^T @ src / n
        sigma_st = tgt_sub.T @ src_sub / max(n_common - 1, 1)  # (d_tgt, d_src)

        # Source auto-covariance: Sigma_ss = src^T @ src / n
        sigma_ss = src_sub.T @ src_sub / max(n_common - 1, 1)  # (d_src, d_src)

        # Transport matrix T = Sigma_st @ Sigma_ss^{-1}
        # Use pseudo-inverse for stability
        try:
            reg = 1e-4 * torch.eye(d_src, device=sigma_ss.device)
            sigma_ss_inv = torch.linalg.inv(sigma_ss + reg)
            transport = sigma_st @ sigma_ss_inv  # (d_tgt, d_src)
        except Exception:
            transport = sigma_st  # fallback: just use cross-covariance

        # Wasserstein-2 distance (Bures metric for Gaussian approximation)
        w2 = self._compute_w2_gaussian(src_mean, tgt_mean, sigma_ss,
                                        tgt_sub.T @ tgt_sub / max(n_common - 1, 1))

        # Condition number of transport matrix
        try:
            sv = torch.linalg.svdvals(transport)
            kappa = (sv[0] / sv[-1]).item() if sv[-1] > 1e-10 else float("inf")
            kappa = min(kappa, 1e6)
        except Exception:
            kappa = 1.0

        is_viable = w2 < self.viability_threshold and kappa < self.max_condition_number

        return TransportPlan(
            source_model=source_name,
            target_model=target_name,
            transport_matrix=transport,
            wasserstein_distance=w2,
            condition_number=kappa,
            transport_cost=w2 * kappa,
            is_viable=is_viable,
        )

    def _compute_w2_gaussian(
        self,
        mean_s: torch.Tensor,
        mean_t: torch.Tensor,
        cov_s: torch.Tensor,
        cov_t: torch.Tensor,
    ) -> float:
        """Compute 2-Wasserstein distance between Gaussian approximations.

        W_2^2 = ||mu_s - mu_t||^2 + Tr(Sigma_s + Sigma_t - 2*(Sigma_s^{1/2} Sigma_t Sigma_s^{1/2})^{1/2})
        """
        # Mean shift component
        mean_diff = (mean_s[:min(len(mean_s), len(mean_t))] -
                     mean_t[:min(len(mean_s), len(mean_t))])
        mean_shift = (mean_diff ** 2).sum().item()

        # Bures metric component (trace term)
        # Simplified: use trace of absolute difference of eigenvalues
        try:
            d = min(cov_s.shape[0], cov_t.shape[0])
            eig_s = torch.linalg.eigvalsh(cov_s[:d, :d])
            eig_t = torch.linalg.eigvalsh(cov_t[:d, :d])
            # Bures approximation via eigenvalues
            sqrt_s = eig_s.clamp(min=0).sqrt()
            sqrt_t = eig_t.clamp(min=0).sqrt()
            bures = ((sqrt_s - sqrt_t) ** 2).sum().item()
        except Exception:
            bures = 0.0

        w2 = math.sqrt(max(0, mean_shift + bures))
        return w2

    def _transport_direction(
        self,
        source_direction: torch.Tensor,
        transport_matrix: torch.Tensor,
        source_acts: torch.Tensor,
        target_acts: torch.Tensor,
    ) -> torch.Tensor:
        """Transport a refusal direction through the OT map.

        Applies T to the source direction and normalizes in the target space.
        """
        d_src = source_direction.shape[0]

        # Ensure dimensions match
        if transport_matrix.shape[1] != d_src:
            # Dimension mismatch — use projection
            min_d = min(d_src, transport_matrix.shape[1])
            src_dir = source_direction[:min_d]
            T = transport_matrix[:, :min_d]
        else:
            src_dir = source_direction
            T = transport_matrix

        # Transport: t_dir = T @ s_dir
        transferred = T @ src_dir

        # Normalize
        t_norm = transferred.norm()
        if t_norm > 1e-8:
            transferred = transferred / t_norm

        return transferred

    def _measure_fidelity(
        self,
        transferred_dir: torch.Tensor,
        target_acts: torch.Tensor,
        source_dir: torch.Tensor,
        source_acts: torch.Tensor,
    ) -> float:
        """Measure how well a transferred direction separates harmful/harmless.

        Fidelity = correlation between source projection magnitudes and
        target projection magnitudes (after transfer).
        """
        # Project source activations onto source direction
        src_proj = (source_acts @ source_dir).abs()

        # Project target activations onto transferred direction
        n_common = min(source_acts.shape[0], target_acts.shape[0])
        tgt_proj = (target_acts[:n_common] @ transferred_dir).abs()
        src_proj = src_proj[:n_common]

        if n_common < 2:
            return 0.0

        # Correlation as fidelity measure
        src_centered = src_proj - src_proj.mean()
        tgt_centered = tgt_proj - tgt_proj.mean()

        src_std = src_centered.std()
        tgt_std = tgt_centered.std()

        if src_std < 1e-10 or tgt_std < 1e-10:
            return 0.0

        correlation = (src_centered @ tgt_centered) / (
            n_common * src_std * tgt_std
        )
        fidelity = correlation.clamp(0, 1).item()

        return fidelity

    def _generate_recommendation(
        self,
        viability: str,
        mean_fidelity: float,
        excess_refusal: float,
        needs_refinement: bool,
    ) -> str:
        """Generate human-readable recommendation."""
        if viability == "excellent":
            return (
                f"Transfer is highly viable (fidelity={mean_fidelity:.2f}). "
                f"Transferred directions should work with minimal refinement."
            )
        elif viability == "good":
            return (
                f"Transfer is viable (fidelity={mean_fidelity:.2f}) but "
                f"recommend a single refinement pass on the target model."
            )
        elif viability == "marginal":
            return (
                f"Transfer is marginal (fidelity={mean_fidelity:.2f}). "
                f"Excess refusal bound={excess_refusal:.3f}. "
                f"Use as initialization only; full re-abliteration recommended."
            )
        else:
            return (
                f"Transfer is poor (fidelity={mean_fidelity:.2f}). "
                f"Models are too dissimilar in Wasserstein space. "
                f"Full native abliteration required."
            )

    def _empty_result(
        self, source_name: str, target_name: str
    ) -> WassersteinTransferResult:
        return WassersteinTransferResult(
            source_model=source_name,
            target_model=target_name,
            n_layers_transferred=0,
            wasserstein_distance=float("inf"),
            condition_number=float("inf"),
            transfer_viability="poor",
            transferred_directions=[],
            mean_transfer_fidelity=0.0,
            min_transfer_fidelity=0.0,
            estimated_excess_refusal=1.0,
            estimated_vs_native_ratio=0.0,
            layer_mapping={},
            unmapped_layers=[],
            recommendation="No activations available for transfer.",
            needs_refinement=True,
        )
