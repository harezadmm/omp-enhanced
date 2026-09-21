"""Mathematical verification that abliteration actually removes refusal directions.

These tests verify the core linear algebra claims WITHOUT mocks:
  1. Projection removes the target direction from weight matrices
  2. Norm-preserving projection maintains weight magnitude
  3. Multi-direction SVD extracts the correct subspace
  4. Whitened SVD produces orthogonal directions
  5. Random directions do NOT have the same effect (negative control)

Unlike the other test files, these use real tensors and verify mathematical
properties directly — no MagicMock, no mocked tokenizers.
"""

from __future__ import annotations


import torch


class TestProjectionRemovesDirection:
    """Verify that orthogonal projection removes the target direction."""

    def test_single_direction_projection(self):
        """After projecting out direction d from weight W,
        W_proj @ d should be approximately zero."""
        torch.manual_seed(42)
        hidden = 256
        out_dim = 128

        W = torch.randn(out_dim, hidden)
        d = torch.randn(hidden)
        d = d / d.norm()

        # Project out d: W_proj = W - (W @ d) @ d^T
        proj = W @ d  # (out_dim,)
        W_proj = W - proj.unsqueeze(1) * d.unsqueeze(0)

        # Verify: W_proj @ d should be ~0
        residual = W_proj @ d
        assert residual.abs().max().item() < 1e-5, f"Residual too large: {residual.abs().max()}"

    def test_projection_preserves_orthogonal_components(self):
        """Projection should NOT change components orthogonal to d."""
        torch.manual_seed(42)
        hidden = 256
        out_dim = 128

        W = torch.randn(out_dim, hidden)
        d = torch.randn(hidden)
        d = d / d.norm()

        # Create a vector orthogonal to d
        v = torch.randn(hidden)
        v = v - (v @ d) * d  # Gram-Schmidt
        v = v / v.norm()

        # Project out d
        proj = W @ d
        W_proj = W - proj.unsqueeze(1) * d.unsqueeze(0)

        # W @ v should equal W_proj @ v (orthogonal component unchanged)
        original = W @ v
        projected = W_proj @ v
        diff = (original - projected).abs().max().item()
        assert diff < 1e-5, f"Orthogonal component changed by {diff}"

    def test_multi_direction_subspace_removal(self):
        """Projecting out a k-dimensional subspace should remove all k directions."""
        torch.manual_seed(42)
        hidden = 256
        out_dim = 128
        k = 4

        W = torch.randn(out_dim, hidden)
        # Create orthonormal subspace
        Q, _ = torch.linalg.qr(torch.randn(hidden, k))
        subspace = Q.T  # (k, hidden)

        # Project out subspace: W_proj = W - W @ Q @ Q^T
        W_proj = W - (W @ Q) @ Q.T

        # Verify: W_proj @ subspace^T should be ~0 for all directions
        residual = W_proj @ subspace.T  # (out_dim, k)
        assert residual.abs().max().item() < 1e-5, f"Subspace residual: {residual.abs().max()}"

    def test_double_projection_is_idempotent(self):
        """Projecting twice should give the same result as projecting once."""
        torch.manual_seed(42)
        hidden = 256
        out_dim = 128

        W = torch.randn(out_dim, hidden)
        d = torch.randn(hidden)
        d = d / d.norm()

        # Project once
        proj1 = W @ d
        W1 = W - proj1.unsqueeze(1) * d.unsqueeze(0)

        # Project twice
        proj2 = W1 @ d
        W2 = W1 - proj2.unsqueeze(1) * d.unsqueeze(0)

        diff = (W1 - W2).abs().max().item()
        assert diff < 1e-5, f"Second projection changed weights by {diff}"


class TestNormPreservation:
    """Verify that norm-preserving projection maintains weight magnitude."""

    def test_norm_preserving_projection(self):
        """Biprojected norm-preserving abliteration should keep ||W|| constant."""
        torch.manual_seed(42)
        hidden = 256
        out_dim = 128

        W = torch.randn(out_dim, hidden)
        d = torch.randn(hidden)
        d = d / d.norm()

        # Standard projection
        proj_coeff = W @ d
        W_proj = W - proj_coeff.unsqueeze(1) * d.unsqueeze(0)

        # Norm-preserving rescaling (per-row)
        row_norms_orig = W.norm(dim=1, keepdim=True).clamp(min=1e-8)
        row_norms_proj = W_proj.norm(dim=1, keepdim=True).clamp(min=1e-8)
        W_norm_preserved = W_proj * (row_norms_orig / row_norms_proj)

        # Direction is still removed
        residual = W_norm_preserved @ d
        # Norm-preserving can't guarantee zero projection (it rescales),
        # but projection should be significantly reduced
        original_proj = (W @ d).abs().mean().item()
        preserved_proj = residual.abs().mean().item()
        assert preserved_proj < original_proj * 0.5, \
            f"Norm-preserved projection {preserved_proj} not much less than original {original_proj}"

        # Row norms are preserved
        row_diff = (W_norm_preserved.norm(dim=1) - W.norm(dim=1)).abs().max().item()
        assert row_diff < 1e-5, f"Row norms changed by {row_diff}"


class TestSVDDirectionExtraction:
    """Verify that SVD on the difference matrix extracts the refusal direction."""

    def test_planted_direction_recovery(self):
        """Plant a known direction in the difference and verify SVD recovers it."""
        torch.manual_seed(42)
        n_samples = 50
        hidden = 256

        # Plant a known refusal direction
        true_direction = torch.randn(hidden)
        true_direction = true_direction / true_direction.norm()

        # Harmful activations = harmless + signal along true_direction + noise
        harmless = torch.randn(n_samples, hidden) * 0.5
        signal_strength = 5.0
        harmful = harmless + signal_strength * true_direction.unsqueeze(0) + torch.randn(n_samples, hidden) * 0.1

        # Extract via SVD on difference
        diff = harmful - harmless
        U, S, Vh = torch.linalg.svd(diff, full_matrices=False)
        extracted = Vh[0]
        extracted = extracted / extracted.norm()

        # The extracted direction should align with the true direction
        cosine = (extracted @ true_direction).abs().item()
        assert cosine > 0.95, f"Cosine similarity {cosine:.3f} too low (expected > 0.95)"

    def test_multi_direction_recovery(self):
        """Plant k directions and verify SVD recovers the subspace."""
        torch.manual_seed(42)
        n_samples = 200
        hidden = 256
        k = 3

        # Plant k orthogonal directions with varying per-sample strength
        Q, _ = torch.linalg.qr(torch.randn(hidden, k))
        true_subspace = Q.T  # (k, hidden)

        # Each sample gets a random mix of the k planted directions
        harmless = torch.randn(n_samples, hidden) * 0.01
        coefficients = torch.randn(n_samples, k).abs() * 5.0
        signal = coefficients @ true_subspace  # (n_samples, hidden)
        harmful = harmless + signal

        diff = harmful - harmless
        U, S, Vh = torch.linalg.svd(diff, full_matrices=False)
        extracted_subspace = Vh[:k]  # (k, hidden)

        # Check subspace overlap: project true directions into extracted subspace
        for i in range(k):
            proj = extracted_subspace @ true_subspace[i]
            captured_variance = proj.norm().item()
            assert captured_variance > 0.9, \
                f"Direction {i}: captured variance {captured_variance:.3f} too low"


class TestRandomDirectionBaseline:
    """Verify that random directions do NOT have the same effect as learned ones."""

    def test_random_direction_has_lower_projection(self):
        """Random directions should project much less on harmful activations
        than the true refusal direction."""
        torch.manual_seed(42)
        n_samples = 50
        hidden = 256

        # Create structured harmful vs harmless difference
        true_dir = torch.randn(hidden)
        true_dir = true_dir / true_dir.norm()

        harmless = torch.randn(n_samples, hidden) * 0.5
        harmful = harmless + 3.0 * true_dir.unsqueeze(0)

        harmful_mean = harmful.mean(dim=0)

        # True direction projection
        true_proj = (harmful_mean @ true_dir).abs().item()

        # Random direction projections (seeds far from 42 to avoid collision)
        random_projs = []
        for i in range(100):
            rng = torch.Generator().manual_seed(10000 + i)
            rand_dir = torch.randn(hidden, generator=rng)
            rand_dir = rand_dir / rand_dir.norm()
            random_projs.append((harmful_mean @ rand_dir).abs().item())

        mean_random = sum(random_projs) / len(random_projs)

        # True direction should project MUCH more than random average
        assert true_proj > mean_random * 3.0, \
            f"True projection ({true_proj:.3f}) not much larger than random mean ({mean_random:.3f})"


class TestWhitenedSVD:
    """Verify whitened SVD properties."""

    def test_whitened_directions_are_orthogonal(self):
        """Whitened SVD should produce orthogonal directions."""
        torch.manual_seed(42)
        n_samples = 80
        hidden = 128
        k = 4

        H = torch.randn(n_samples, hidden) + torch.randn(1, hidden) * 2
        B = torch.randn(n_samples, hidden)

        mu_B = B.mean(dim=0, keepdim=True)
        B_centered = B - mu_B
        cov_B = (B_centered.T @ B_centered) / (n_samples - 1)
        cov_B += 1e-4 * torch.eye(hidden)

        eigenvalues, eigenvectors = torch.linalg.eigh(cov_B)
        eigenvalues = eigenvalues.clamp(min=0)
        inv_sqrt_eig = 1.0 / torch.sqrt(eigenvalues + 1e-4)
        whiten_proj = eigenvectors * inv_sqrt_eig.unsqueeze(0)

        H_whitened = (H - mu_B) @ whiten_proj
        B_whitened = B_centered @ whiten_proj
        D_whitened = H_whitened - B_whitened

        U, S, Vh = torch.linalg.svd(D_whitened, full_matrices=False)
        directions = Vh[:k]

        # Check orthogonality: directions @ directions^T should be ~identity
        gram = directions @ directions.T
        identity = torch.eye(k)
        off_diag = (gram - identity).abs().max().item()
        assert off_diag < 1e-4, f"Directions not orthogonal: max off-diagonal = {off_diag}"


class TestReproducibility:
    """Verify that seed setting produces deterministic results."""

    def test_set_seed_determinism(self):
        """Same seed should produce identical random tensors."""
        from obliteratus.reproducibility import set_seed

        set_seed(123, deterministic=False)
        a = torch.randn(100)

        set_seed(123, deterministic=False)
        b = torch.randn(100)

        assert torch.equal(a, b), "Same seed produced different tensors"

    def test_different_seeds_differ(self):
        """Different seeds should produce different tensors."""
        from obliteratus.reproducibility import set_seed

        set_seed(123, deterministic=False)
        a = torch.randn(100)

        set_seed(456, deterministic=False)
        b = torch.randn(100)

        assert not torch.equal(a, b), "Different seeds produced identical tensors"
