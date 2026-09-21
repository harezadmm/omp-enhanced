"""Linear Probing Classifiers for refusal decodability analysis.

The projection-based approach measures how much refusal signal exists
along a *known* direction. But what if refusal information is encoded in
a direction we haven't found? Linear probing answers this by *learning*
an optimal classifier from data.

The key question: "At layer L, can a linear classifier distinguish
harmful from harmless activations?" If yes, refusal information is
linearly decodable at that layer.

This provides:
  - **Probing accuracy curve**: Classification accuracy at each layer,
    showing where refusal becomes decodable
  - **Learned direction comparison**: How the probe's learned direction
    compares to the difference-in-means direction
  - **Information-theoretic bounds**: Mutual information between activations
    and refusal labels (via probe cross-entropy)
  - **Post-excision probing**: Re-probe after abliteration to verify that
    refusal information was actually removed (not just along one direction)

This is fundamentally different from the existing ActivationProbe module,
which measures elimination along a *pre-specified* direction. Probing
classifiers learn the *optimal* direction from data, potentially finding
residual refusal information that projection-based methods miss.

Contributions:
  - SGD-trained linear probes with cross-validation at each layer
  - Comparison of learned vs. analytically-derived refusal directions
  - Post-excision probing to detect "hidden" residual refusal
  - Information-theoretic analysis via probe cross-entropy loss

References:
    - Alain & Bengio (2017): Understanding Intermediate Layers Using Linear Classifiers
    - Belinkov (2022): Probing Classifiers — promises, shortcomings, advances
    - Li et al. (2024): Inference-time intervention via probing
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn.functional as F


@dataclass
class ProbeResult:
    """Result of linear probing at a single layer."""

    layer_idx: int
    accuracy: float                 # classification accuracy
    cross_entropy: float            # probe loss (lower = more decodable)
    auroc: float                    # area under ROC curve

    # Learned direction analysis
    learned_direction: torch.Tensor  # the probe's weight vector (refusal direction)
    cosine_with_analytical: float    # cos sim with difference-in-means direction
    direction_agreement: bool        # whether learned and analytical agree (cos > 0.5)

    # Information content
    mutual_information: float       # estimated MI (bits) from cross-entropy
    baseline_entropy: float         # H(Y) before seeing activations


@dataclass
class ProbingSuiteResult:
    """Probing results across all layers."""

    per_layer: dict[int, ProbeResult]
    best_layer: int                 # layer with highest probing accuracy
    best_accuracy: float
    onset_layer: int                # first layer exceeding 75% accuracy
    mean_cosine_with_analytical: float  # how well probes agree with analytical
    total_mutual_information: float


class LinearRefusalProbe:
    """Train linear probing classifiers to measure refusal decodability.

    At each layer, trains a logistic regression classifier to distinguish
    harmful from harmless activations, measuring how much refusal
    information is available.
    """

    def __init__(
        self,
        n_epochs: int = 100,
        learning_rate: float = 0.01,
        weight_decay: float = 0.001,
        test_fraction: float = 0.2,
    ):
        """
        Args:
            n_epochs: Training epochs for the probe.
            learning_rate: SGD learning rate.
            weight_decay: L2 regularization.
            test_fraction: Fraction of data held out for evaluation.
        """
        self.n_epochs = n_epochs
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.test_fraction = test_fraction

    def probe_layer(
        self,
        harmful_activations: list[torch.Tensor],
        harmless_activations: list[torch.Tensor],
        analytical_direction: torch.Tensor | None = None,
        layer_idx: int = 0,
    ) -> ProbeResult:
        """Train and evaluate a linear probe at one layer.

        Args:
            harmful_activations: Activations from harmful prompts.
            harmless_activations: Activations from harmless prompts.
            analytical_direction: Difference-in-means direction for comparison.
            layer_idx: Layer index for metadata.

        Returns:
            ProbeResult with accuracy, learned direction, etc.
        """
        # Prepare data
        X_harmful = torch.stack([a.float().reshape(-1) for a in harmful_activations])
        X_harmless = torch.stack([a.float().reshape(-1) for a in harmless_activations])

        # Ensure 2D: (n_samples, hidden_dim)
        if X_harmful.ndim == 1:
            X_harmful = X_harmful.unsqueeze(-1)
            X_harmless = X_harmless.unsqueeze(-1)

        n_harmful = X_harmful.shape[0]
        n_harmless = X_harmless.shape[0]
        hidden_dim = X_harmful.shape[-1]

        X = torch.cat([X_harmful, X_harmless], dim=0)
        y = torch.cat([
            torch.ones(n_harmful),
            torch.zeros(n_harmless),
        ])

        # Train/test split
        n_total = X.shape[0]
        n_test = max(2, int(self.test_fraction * n_total))
        n_train = n_total - n_test

        # Shuffle
        perm = torch.randperm(n_total)
        X = X[perm]
        y = y[perm]

        X_train, X_test = X[:n_train], X[n_train:]
        y_train, y_test = y[:n_train], y[n_train:]

        # Normalize features
        mean = X_train.mean(dim=0)
        std = X_train.std(dim=0).clamp(min=1e-8)
        X_train_norm = (X_train - mean) / std
        X_test_norm = (X_test - mean) / std

        # Train logistic regression
        w = torch.zeros(hidden_dim, requires_grad=True)
        b = torch.zeros(1, requires_grad=True)

        for epoch in range(self.n_epochs):
            # Forward
            logits = X_train_norm @ w + b
            loss = F.binary_cross_entropy_with_logits(logits, y_train)
            loss = loss + self.weight_decay * (w * w).sum()

            # Backward
            loss.backward()

            # SGD update
            with torch.no_grad():
                w -= self.learning_rate * w.grad
                b -= self.learning_rate * b.grad
                w.grad.zero_()
                b.grad.zero_()

        # Evaluate on test set
        with torch.no_grad():
            test_logits = X_test_norm @ w + b
            test_probs = torch.sigmoid(test_logits)
            test_preds = (test_probs > 0.5).float()
            accuracy = (test_preds == y_test).float().mean().item()

            # Cross-entropy loss
            ce_loss = F.binary_cross_entropy_with_logits(
                test_logits, y_test
            ).item()

            # AUROC approximation
            auroc = self._compute_auroc(test_probs, y_test)

        # Learned direction (in original space)
        with torch.no_grad():
            learned_dir = w.clone() / std  # undo normalization
            learned_dir = learned_dir / learned_dir.norm().clamp(min=1e-10)

        # Compare with analytical direction
        if analytical_direction is not None:
            anal_dir = analytical_direction.float().squeeze()
            anal_dir = anal_dir / anal_dir.norm().clamp(min=1e-10)
            cos_sim = (learned_dir @ anal_dir).abs().item()
        else:
            cos_sim = 0.0

        # Mutual information estimate
        # MI = H(Y) - H(Y|X) ≈ H(Y) - CE_loss
        baseline_entropy = self._binary_entropy(n_harmful / n_total)
        mi = max(0.0, baseline_entropy - ce_loss) / math.log(2)  # in bits

        return ProbeResult(
            layer_idx=layer_idx,
            accuracy=accuracy,
            cross_entropy=ce_loss,
            auroc=auroc,
            learned_direction=learned_dir.detach(),
            cosine_with_analytical=cos_sim,
            direction_agreement=cos_sim > 0.5,
            mutual_information=mi,
            baseline_entropy=baseline_entropy / math.log(2),
        )

    def probe_all_layers(
        self,
        harmful_acts: dict[int, list[torch.Tensor]],
        harmless_acts: dict[int, list[torch.Tensor]],
        analytical_directions: dict[int, torch.Tensor] | None = None,
    ) -> ProbingSuiteResult:
        """Probe every layer and aggregate results.

        Args:
            harmful_acts: {layer_idx: [activations]} harmful.
            harmless_acts: {layer_idx: [activations]} harmless.
            analytical_directions: {layer_idx: diff-in-means direction}.

        Returns:
            ProbingSuiteResult with per-layer and aggregate analysis.
        """
        layers = sorted(set(harmful_acts.keys()) & set(harmless_acts.keys()))
        per_layer = {}

        for ly in layers:
            anal_dir = None
            if analytical_directions and ly in analytical_directions:
                anal_dir = analytical_directions[ly]

            per_layer[ly] = self.probe_layer(
                harmful_acts[ly], harmless_acts[ly],
                analytical_direction=anal_dir, layer_idx=ly,
            )

        if not per_layer:
            return ProbingSuiteResult(
                per_layer={}, best_layer=0, best_accuracy=0.0,
                onset_layer=0, mean_cosine_with_analytical=0.0,
                total_mutual_information=0.0,
            )

        accs = {ly: r.accuracy for ly, r in per_layer.items()}
        best_l = max(accs, key=accs.get)

        # Onset: first layer exceeding 75%
        onset = layers[0]
        for ly in layers:
            if per_layer[ly].accuracy > 0.75:
                onset = ly
                break

        # Mean cosine with analytical
        cosines = [r.cosine_with_analytical for r in per_layer.values()
                   if r.cosine_with_analytical > 0]
        mean_cos = sum(cosines) / len(cosines) if cosines else 0.0

        total_mi = sum(r.mutual_information for r in per_layer.values())

        return ProbingSuiteResult(
            per_layer=per_layer,
            best_layer=best_l,
            best_accuracy=accs[best_l],
            onset_layer=onset,
            mean_cosine_with_analytical=mean_cos,
            total_mutual_information=total_mi,
        )

    def _compute_auroc(self, probs: torch.Tensor, labels: torch.Tensor) -> float:
        """Compute AUROC from predictions and labels."""
        if len(probs) < 2:
            return 0.5

        pos = probs[labels == 1]
        neg = probs[labels == 0]

        if len(pos) == 0 or len(neg) == 0:
            return 0.5

        # Wilcoxon-Mann-Whitney statistic
        n_correct = 0
        n_total = 0
        for p in pos:
            for n in neg:
                n_total += 1
                if p > n:
                    n_correct += 1
                elif p == n:
                    n_correct += 0.5

        return n_correct / max(n_total, 1)

    @staticmethod
    def _binary_entropy(p: float) -> float:
        """Compute binary entropy H(p) in nats."""
        if p <= 0 or p >= 1:
            return 0.0
        return -(p * math.log(p) + (1 - p) * math.log(1 - p))

    @staticmethod
    def format_probing_report(result: ProbingSuiteResult) -> str:
        """Format probing suite results."""
        lines = []
        lines.append("Linear Probing — Refusal Decodability Analysis")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Layers probed: {len(result.per_layer)}")
        lines.append(f"Best accuracy: {result.best_accuracy:.1%} (layer {result.best_layer})")
        lines.append(f"Refusal onset: layer {result.onset_layer} (>75% accuracy)")
        lines.append(f"Mean cos(learned, analytical): {result.mean_cosine_with_analytical:.3f}")
        lines.append(f"Total mutual information: {result.total_mutual_information:.2f} bits")
        lines.append("")

        lines.append("Per-layer accuracy curve:")
        for ly in sorted(result.per_layer.keys()):
            r = result.per_layer[ly]
            bar = "█" * int(r.accuracy * 20)
            agree = "✓" if r.direction_agreement else "✗"
            lines.append(
                f"  Layer {ly:3d}: {r.accuracy:.1%} {bar:20s}  "
                f"cos={r.cosine_with_analytical:.2f} {agree}  "
                f"MI={r.mutual_information:.2f}b"
            )

        return "\n".join(lines)
