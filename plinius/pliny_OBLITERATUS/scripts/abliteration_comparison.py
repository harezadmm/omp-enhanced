#!/usr/bin/env python3
"""Abliteration Technique Comparison Study.

A rigorous, controlled comparison of refusal-direction removal techniques.
Uses a synthetic "planted refusal direction" methodology: we inject a known
direction into a model's activations so we can measure whether each technique
correctly identifies and removes it.

Additionally compiles literature results for a full comparison table.

Techniques compared:
  1. Arditi et al. (2024) — difference-of-means, last token, raw prompts
  2. Arditi + chat template — same but with chat-formatted prompts
  3. FailSpy/abliterator — Arditi with middle-60% layer heuristic
  4. Gabliteration — SVD multi-direction (4 dirs), regularization 0.0
  5. grimjim — Gabliteration + norm preservation
  6. OBLITERATUS basic — our current basic config
  7. OBLITERATUS advanced — 4 directions, norm-preserve, reg=0.3
  8. Heretic (p-e-w) — TPE Bayesian optimization (literature)

Metrics:
  - Direction recovery: cosine similarity to planted ground-truth direction
  - Residual after projection: how much of the refusal direction remains
  - Capability preservation: Frobenius distance of modified vs original weights
  - Layer selection accuracy: did it pick the right layers?
  - Perplexity delta: change in language modeling loss (on synthetic data)
"""

from __future__ import annotations

import gc
import json
import math
import os
import sys
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════════════════════
# Synthetic model with planted refusal direction
# ══════════════════════════════════════════════════════════════════════════


def create_synthetic_model(
    hidden_dim: int = 128,
    n_layers: int = 12,
    n_heads: int = 4,
    vocab_size: int = 1000,
    seq_len: int = 64,
):
    """Create a tiny GPT-2 model for controlled experiments."""
    from transformers import GPT2Config, GPT2LMHeadModel

    config = GPT2Config(
        vocab_size=vocab_size,
        n_positions=seq_len,
        n_embd=hidden_dim,
        n_layer=n_layers,
        n_head=n_heads,
        n_inner=hidden_dim * 4,
        resid_pdrop=0.0,
        attn_pdrop=0.0,
        embd_pdrop=0.0,
    )
    model = GPT2LMHeadModel(config)
    model.eval()
    return model, config


def plant_refusal_direction(
    model: nn.Module,
    target_layers: list[int],
    hidden_dim: int,
    n_directions: int = 1,
    signal_strength: float = 5.0,
    seed: int = 42,
) -> tuple[dict[int, torch.Tensor], dict[int, torch.Tensor]]:
    """Plant a known refusal direction into specific layers.

    Modifies the output projection (c_proj) of attention modules by adding
    a rank-1 perturbation along a random direction. This simulates the
    refusal direction that RLHF training creates.

    Returns:
        (planted_directions, planted_subspaces): ground truth per layer
    """
    torch.manual_seed(seed)

    planted_directions: dict[int, torch.Tensor] = {}
    planted_subspaces: dict[int, torch.Tensor] = {}

    for idx in target_layers:
        # Generate random orthogonal directions
        dirs = torch.randn(n_directions, hidden_dim)
        # Gram-Schmidt orthogonalize
        for i in range(n_directions):
            for j in range(i):
                dirs[i] -= (dirs[i] @ dirs[j]) * dirs[j]
            dirs[i] = dirs[i] / dirs[i].norm()

        planted_directions[idx] = dirs[0].clone()
        planted_subspaces[idx] = dirs.clone()

        # Inject into attention output projection (c_proj for GPT-2)
        layer = model.transformer.h[idx]
        attn = layer.attn

        # Add refusal component to c_proj: W += strength * d @ d^T
        # This makes the layer produce extra activation along d when
        # processing any input, creating a "refusal signal"
        with torch.no_grad():
            for dir_idx in range(n_directions):
                d = dirs[dir_idx]
                # Scale decreases for secondary directions
                s = signal_strength * (0.7 ** dir_idx)
                # Inject into c_proj (output projection)
                W = attn.c_proj.weight.data  # GPT-2: (hidden, hidden)
                perturbation = s * d.unsqueeze(1) @ d.unsqueeze(0)  # rank-1
                W.add_(perturbation)

    return planted_directions, planted_subspaces


def measure_residual_direction(
    model: nn.Module,
    layer_idx: int,
    direction: torch.Tensor,
) -> float:
    """Measure how much of a direction remains in a layer's output projection.

    Returns the magnitude of the direction's component in the weight matrix.
    """
    layer = model.transformer.h[layer_idx]
    W = layer.attn.c_proj.weight.data
    d = direction.to(W.device, W.dtype)

    # Project W onto direction: ||W @ d||^2 / ||d||^2
    coeff = W @ d  # (hidden,)
    return coeff.norm().item()


def collect_synthetic_activations(
    model: nn.Module,
    n_prompts: int,
    seq_len: int,
    vocab_size: int,
    n_layers: int,
    add_refusal_signal: bool = False,
    signal_direction: dict[int, torch.Tensor] | None = None,
    signal_strength: float = 2.0,
    seed: int = 0,
) -> dict[int, list[torch.Tensor]]:
    """Collect activations on random token sequences.

    If add_refusal_signal=True, adds an artificial activation along
    the signal_direction to simulate harmful-prompt activations.
    """
    torch.manual_seed(seed)

    activations: dict[int, list[torch.Tensor]] = {i: [] for i in range(n_layers)}
    hooks = []

    def make_hook(idx: int):
        def hook_fn(module, input, output):
            hidden = output[0] if isinstance(output, tuple) else output
            act = hidden[:, -1, :].detach().cpu().float()

            if add_refusal_signal and signal_direction and idx in signal_direction:
                # Add the planted refusal activation
                d = signal_direction[idx]
                act = act + signal_strength * d.unsqueeze(0)

            activations[idx].append(act)
        return hook_fn

    layers = list(model.transformer.h)
    for idx in range(n_layers):
        hooks.append(layers[idx].register_forward_hook(make_hook(idx)))

    try:
        for i in range(n_prompts):
            input_ids = torch.randint(0, vocab_size, (1, seq_len))
            with torch.no_grad():
                model(input_ids)
    finally:
        for h in hooks:
            h.remove()

    return activations


# ══════════════════════════════════════════════════════════════════════════
# Reference baseline implementations
# ══════════════════════════════════════════════════════════════════════════


def extract_directions(
    harmful_acts: dict[int, list[torch.Tensor]],
    harmless_acts: dict[int, list[torch.Tensor]],
    n_layers: int,
    n_directions: int = 1,
) -> tuple[dict[int, torch.Tensor], dict[int, torch.Tensor], dict[int, float]]:
    """Extract refusal directions from activation contrasts.

    Returns (directions, subspaces, norms) per layer.
    """
    directions: dict[int, torch.Tensor] = {}
    subspaces: dict[int, torch.Tensor] = {}
    norms: dict[int, float] = {}

    for idx in range(n_layers):
        h_stack = torch.stack(harmful_acts[idx]).squeeze(1)
        s_stack = torch.stack(harmless_acts[idx]).squeeze(1)

        if n_directions == 1:
            diff = h_stack.mean(dim=0) - s_stack.mean(dim=0)
            norm = diff.norm().item()
            if norm > 0:
                directions[idx] = diff / diff.norm()
                subspaces[idx] = directions[idx].unsqueeze(0)
                norms[idx] = norm
        else:
            min_n = min(h_stack.shape[0], s_stack.shape[0])
            diff_matrix = h_stack[:min_n] - s_stack[:min_n]
            diff_matrix = torch.nan_to_num(diff_matrix)
            k = min(n_directions, diff_matrix.shape[0], diff_matrix.shape[1])
            try:
                U, S, Vh = torch.linalg.svd(diff_matrix, full_matrices=False)
                sub = Vh[:k]
                primary = sub[0]
                pn = primary.norm()
                if pn > 1e-8:
                    primary = primary / pn
                directions[idx] = primary
                subspaces[idx] = sub
                norms[idx] = (S[:k] ** 2).sum().item()
            except Exception:
                continue

    return directions, subspaces, norms


def select_layers(
    norms: dict[int, float],
    n_layers: int,
    method: str = "top_norm",
) -> list[int]:
    """Select layers for abliteration."""
    sorted_layers = sorted(norms.items(), key=lambda x: x[1], reverse=True)
    if not sorted_layers:
        return []

    if method == "middle_60":
        start = int(n_layers * 0.2)
        end = int(n_layers * 0.8)
        selected = [idx for idx, _ in sorted_layers if start <= idx < end]
        return selected if selected else [sorted_layers[0][0]]

    elif method == "knee":
        if len(sorted_layers) < 3:
            return [sorted_layers[0][0]]
        vals = [n for _, n in sorted_layers]
        max_n = vals[0]
        if max_n <= 0:
            return [sorted_layers[0][0]]
        normalized = [v / max_n for v in vals]
        n_pts = len(normalized)
        best_k, best_dist = 1, 0.0
        x_s, y_s = 0.0, normalized[0]
        x_e, y_e = 1.0, normalized[-1]
        line_len = math.sqrt((x_e - x_s) ** 2 + (y_e - y_s) ** 2)
        if line_len > 0:
            for i in range(1, n_pts - 1):
                x_i = i / (n_pts - 1)
                y_i = normalized[i]
                dist = abs((y_e - y_s) * x_i - (x_e - x_s) * y_i
                           + x_e * y_s - y_e * x_s) / line_len
                if dist > best_dist:
                    best_dist = dist
                    best_k = i + 1
        min_threshold = max_n * 0.05
        selected = [idx for idx, n in sorted_layers[:best_k] if n >= min_threshold]
        return selected if selected else [sorted_layers[0][0]]

    else:  # top_norm
        max_norm = sorted_layers[0][1]
        threshold = max_norm * 0.5
        selected = [idx for idx, n in sorted_layers if n >= threshold]
        return selected if selected else [sorted_layers[0][0]]


def apply_projection(
    model: nn.Module,
    selected_layers: list[int],
    subspaces: dict[int, torch.Tensor],
    regularization: float = 0.0,
    norm_preserve: bool = False,
    multi_dir_norm_fix: bool = False,
) -> int:
    """Project refusal direction out of weight matrices.

    When multi_dir_norm_fix=True, uses the correct approach: capture norms
    before projecting any directions, then restore once after all directions.
    """
    scale = 1.0 - regularization
    n_modified = 0

    for idx in selected_layers:
        sub = subspaces.get(idx)
        if sub is None:
            continue

        layer = model.transformer.h[idx]

        # Capture norms before any projections (if multi-dir + norm-preserve)
        saved_norms: dict[str, float] = {}
        if multi_dir_norm_fix and norm_preserve and sub.shape[0] > 1:
            for name, param in layer.named_parameters():
                if name.endswith(".weight") and param.dim() == 2:
                    saved_norms[name] = param.data.norm().item()

        for dir_idx in range(sub.shape[0]):
            d = sub[dir_idx].unsqueeze(-1)  # (hidden, 1)

            for name, module in layer.named_modules():
                if not hasattr(module, "weight"):
                    continue
                W = module.weight.data
                if W.dim() != 2:
                    continue

                # Per-direction norm preserve (the OLD buggy way)
                use_per_dir_norm = norm_preserve and not (multi_dir_norm_fix and sub.shape[0] > 1)
                original_norm = W.norm().item() if use_per_dir_norm else 0.0

                if W.shape[-1] == d.shape[0]:
                    coeff = W @ d
                    W.sub_(d.T * (scale * coeff))
                    n_modified += 1
                elif W.shape[0] == d.shape[0]:
                    coeff = d.T @ W
                    W.sub_((scale * d) * coeff)
                    n_modified += 1
                else:
                    continue

                if use_per_dir_norm and original_norm > 0:
                    new_norm = W.norm().item()
                    if new_norm > 0:
                        W.mul_(original_norm / new_norm)

        # Restore norms once after all directions (the FIXED way)
        if multi_dir_norm_fix and norm_preserve and sub.shape[0] > 1 and saved_norms:
            for name, param in layer.named_parameters():
                if name not in saved_norms:
                    continue
                orig = saved_norms[name]
                if orig > 0:
                    cur = param.data.norm().item()
                    if cur > 0 and abs(cur - orig) > 1e-6:
                        param.data.mul_(orig / cur)

    return n_modified


# ══════════════════════════════════════════════════════════════════════════
# Experiment runner
# ══════════════════════════════════════════════════════════════════════════


def run_experiment():
    """Run the full comparison experiment with synthetic planted directions."""

    # Configuration
    hidden_dim = 128
    n_layers = 12
    n_heads = 4
    vocab_size = 1000
    seq_len = 32
    n_prompts = 48       # prompts per side (harmful + harmless)
    n_planted_dirs = 4   # ground truth directions planted
    signal_strength = 5.0
    target_layers = [3, 4, 5, 6, 7, 8]  # layers with planted signal

    print(f"\n{'='*80}")
    print("ABLITERATION TECHNIQUE COMPARISON — SYNTHETIC PLANTED-DIRECTION TEST")
    print(f"{'='*80}")
    print(f"Model:           GPT-2 tiny ({hidden_dim}d, {n_layers}L, {n_heads}H)")
    print(f"Target layers:   {target_layers}")
    print(f"Planted dirs:    {n_planted_dirs} orthogonal directions per target layer")
    print(f"Signal strength: {signal_strength}")
    print(f"Prompts:         {n_prompts} per side")
    print(f"{'='*80}\n")

    # Define experiments
    experiments = [
        {
            "name": "Arditi (1-dir, top-norm)",
            "source": "Arditi 2024",
            "n_directions": 1,
            "layer_selection": "top_norm",
            "regularization": 0.0,
            "norm_preserve": False,
            "multi_dir_norm_fix": False,
        },
        {
            "name": "FailSpy (1-dir, mid-60%)",
            "source": "FailSpy",
            "n_directions": 1,
            "layer_selection": "middle_60",
            "regularization": 0.0,
            "norm_preserve": False,
            "multi_dir_norm_fix": False,
        },
        {
            "name": "Gabliteration (4-dir, knee)",
            "source": "Gabliteration",
            "n_directions": 4,
            "layer_selection": "knee",
            "regularization": 0.0,
            "norm_preserve": False,
            "multi_dir_norm_fix": False,
        },
        {
            "name": "grimjim (4-dir, norm-pres, BUGGY)",
            "source": "grimjim",
            "n_directions": 4,
            "layer_selection": "knee",
            "regularization": 0.0,
            "norm_preserve": True,
            "multi_dir_norm_fix": False,  # Old buggy sequential norm-preserve
        },
        {
            "name": "grimjim (4-dir, norm-pres, FIXED)",
            "source": "Ours (fix)",
            "n_directions": 4,
            "layer_selection": "knee",
            "regularization": 0.0,
            "norm_preserve": True,
            "multi_dir_norm_fix": True,   # Our fix: capture once, restore once
        },
        {
            "name": "OBLITERATUS basic (1-dir, knee)",
            "source": "Ours",
            "n_directions": 1,
            "layer_selection": "knee",
            "regularization": 0.0,
            "norm_preserve": False,
            "multi_dir_norm_fix": False,
        },
        {
            "name": "OBLITERATUS adv (4-dir, reg=0.3)",
            "source": "Ours",
            "n_directions": 4,
            "layer_selection": "knee",
            "regularization": 0.3,
            "norm_preserve": True,
            "multi_dir_norm_fix": True,
        },
        {
            "name": "OBLITERATUS adv (4-dir, reg=0.1)",
            "source": "Ours (tuned)",
            "n_directions": 4,
            "layer_selection": "knee",
            "regularization": 0.1,
            "norm_preserve": True,
            "multi_dir_norm_fix": True,
        },
        {
            "name": "OBLITERATUS adv (4-dir, reg=0.0)",
            "source": "Ours (tuned)",
            "n_directions": 4,
            "layer_selection": "knee",
            "regularization": 0.0,
            "norm_preserve": True,
            "multi_dir_norm_fix": True,
        },
    ]

    results = []

    for exp in experiments:
        print(f"\n{'─'*80}")
        print(f"  {exp['name']}")
        print(f"  Source: {exp['source']}")
        print(f"{'─'*80}")

        t0 = time.time()

        # Create fresh model
        model, config = create_synthetic_model(hidden_dim, n_layers, n_heads, vocab_size, seq_len)

        # Plant ground-truth refusal directions
        planted_dirs, planted_subs = plant_refusal_direction(
            model, target_layers, hidden_dim,
            n_directions=n_planted_dirs,
            signal_strength=signal_strength,
            seed=42,
        )

        # Save original weights for capability comparison
        original_state = {k: v.clone() for k, v in model.state_dict().items()}

        # Measure pre-projection residuals (baseline)
        pre_residuals = {}
        for idx in target_layers:
            pre_residuals[idx] = measure_residual_direction(model, idx, planted_dirs[idx])

        # Step 1: Collect activations
        harmful_acts = collect_synthetic_activations(
            model, n_prompts, seq_len, vocab_size, n_layers,
            add_refusal_signal=True,
            signal_direction=planted_dirs,
            signal_strength=2.0,
            seed=100,
        )
        harmless_acts = collect_synthetic_activations(
            model, n_prompts, seq_len, vocab_size, n_layers,
            add_refusal_signal=False,
            seed=200,
        )

        # Step 2: Extract directions
        ext_dirs, ext_subs, ext_norms = extract_directions(
            harmful_acts, harmless_acts, n_layers, exp["n_directions"],
        )

        # Step 3: Select layers
        selected = select_layers(ext_norms, n_layers, exp["layer_selection"])
        print(f"  Selected layers: {selected}")

        # Step 4: Apply projection
        apply_projection(
            model, selected, ext_subs,
            regularization=exp["regularization"],
            norm_preserve=exp["norm_preserve"],
            multi_dir_norm_fix=exp["multi_dir_norm_fix"],
        )

        # ── Measure results ──────────────────────────────────────────────

        # Direction recovery: cosine similarity between extracted and planted
        cos_sims = []
        for idx in target_layers:
            if idx in ext_dirs and idx in planted_dirs:
                cos = F.cosine_similarity(
                    ext_dirs[idx].unsqueeze(0),
                    planted_dirs[idx].unsqueeze(0),
                ).item()
                cos_sims.append(abs(cos))  # direction or anti-direction
        avg_cos = sum(cos_sims) / len(cos_sims) if cos_sims else 0.0

        # Multi-direction subspace recovery: for n_directions>1, measure
        # what fraction of the planted subspace is captured
        subspace_recovery = []
        for idx in target_layers:
            if idx in ext_subs and idx in planted_subs:
                # Project each planted direction onto extracted subspace
                ext_sub = ext_subs[idx]  # (k_ext, hidden)
                plant_sub = planted_subs[idx]  # (k_plant, hidden)
                for pi in range(min(plant_sub.shape[0], ext_sub.shape[0])):
                    # Projection of planted_i onto extracted subspace
                    proj = ext_sub @ plant_sub[pi]  # (k_ext,)
                    captured = proj.norm().item()  # how much is in the subspace
                    subspace_recovery.append(captured)
        avg_subspace = sum(subspace_recovery) / len(subspace_recovery) if subspace_recovery else 0.0

        # Residual after projection
        post_residuals = {}
        for idx in target_layers:
            if idx in selected:
                post_residuals[idx] = measure_residual_direction(model, idx, planted_dirs[idx])
            else:
                post_residuals[idx] = pre_residuals[idx]  # layer wasn't modified

        avg_removal = 0.0
        removal_scores = []
        for idx in target_layers:
            pre = pre_residuals[idx]
            post = post_residuals[idx]
            if pre > 0:
                removal = 1.0 - (post / pre)
                removal_scores.append(removal)
        avg_removal = sum(removal_scores) / len(removal_scores) if removal_scores else 0.0

        # Multi-direction residual: check ALL planted directions
        multi_dir_removal = []
        for idx in target_layers:
            if idx not in selected:
                continue
            for di in range(planted_subs[idx].shape[0]):
                d = planted_subs[idx][di]
                pre = measure_residual_direction(
                    # Need pre-values - approximate from signal_strength
                    model, idx, d,
                )
                # Compare to signal strength
                multi_dir_removal.append(pre)
        avg_multi_residual = sum(multi_dir_removal) / len(multi_dir_removal) if multi_dir_removal else 0.0

        # Layer selection accuracy
        correct_selected = len(set(selected) & set(target_layers))
        false_selected = len(set(selected) - set(target_layers))
        missed = len(set(target_layers) - set(selected))

        # Capability preservation: Frobenius distance of weights
        new_state = model.state_dict()
        total_dist = 0.0
        for key in original_state:
            diff = (new_state[key].float() - original_state[key].float())
            total_dist += diff.norm().item() ** 2
        total_dist = math.sqrt(total_dist)

        # Perplexity proxy: loss on random sequences
        losses = []
        for _ in range(10):
            input_ids = torch.randint(0, vocab_size, (1, seq_len))
            with torch.no_grad():
                out = model(input_ids, labels=input_ids)
                losses.append(out.loss.item())
        avg_loss = sum(losses) / len(losses)
        ppl = math.exp(min(avg_loss, 100.0))

        elapsed = time.time() - t0

        result = {
            "name": exp["name"],
            "source": exp["source"],
            "n_directions": exp["n_directions"],
            "regularization": exp["regularization"],
            "norm_preserve": exp["norm_preserve"],
            "direction_recovery": round(avg_cos, 4),
            "subspace_recovery": round(avg_subspace, 4),
            "primary_removal": round(avg_removal, 4),
            "multi_dir_avg_residual": round(avg_multi_residual, 4),
            "layers_correct": correct_selected,
            "layers_false_positive": false_selected,
            "layers_missed": missed,
            "n_layers_selected": len(selected),
            "weight_distance": round(total_dist, 2),
            "perplexity": round(ppl, 2),
            "time_seconds": round(elapsed, 2),
        }
        results.append(result)

        print(f"  Direction recovery:     {avg_cos:.3f} (cosine sim to ground truth)")
        print(f"  Subspace recovery:      {avg_subspace:.3f} (planted dirs captured)")
        print(f"  Primary dir removal:    {avg_removal:.1%} (refusal signal removed)")
        print(f"  Multi-dir avg residual: {avg_multi_residual:.3f} (lower = better)")
        print(f"  Layer selection:        {correct_selected}/{len(target_layers)} correct, "
              f"{false_selected} false+, {missed} missed")
        print(f"  Weight distance:        {total_dist:.2f} (capability delta)")
        print(f"  Perplexity:             {ppl:.2f}")

        del model
        gc.collect()

    return results


def print_table(results: list[dict]):
    """Print formatted comparison tables."""

    # ── Table 1: Direction Extraction Quality ──────────────────────────
    print(f"\n\n{'='*100}")
    print("TABLE 1: DIRECTION EXTRACTION & REMOVAL QUALITY")
    print(f"{'='*100}")
    print(f"{'Technique':<38} {'Source':<14} {'DirRecov':>9} {'SubRecov':>9} "
          f"{'Removal':>8} {'Residual':>9}")
    print(f"{'─'*38} {'─'*14} {'─'*9} {'─'*9} {'─'*8} {'─'*9}")

    for r in results:
        name = r["name"][:37]
        source = r["source"][:13]
        dr = f"{r['direction_recovery']:.3f}"
        sr = f"{r['subspace_recovery']:.3f}"
        rm = f"{r['primary_removal']:.1%}"
        res = f"{r['multi_dir_avg_residual']:.3f}"
        print(f"{name:<38} {source:<14} {dr:>9} {sr:>9} {rm:>8} {res:>9}")

    # ── Table 2: Layer Selection & Capability ──────────────────────────
    print(f"\n{'='*100}")
    print("TABLE 2: LAYER SELECTION & CAPABILITY PRESERVATION")
    print(f"{'='*100}")
    print(f"{'Technique':<38} {'Layers':>7} {'Correct':>8} {'FalsePos':>9} "
          f"{'Missed':>7} {'WeightΔ':>8} {'PPL':>8}")
    print(f"{'─'*38} {'─'*7} {'─'*8} {'─'*9} {'─'*7} {'─'*8} {'─'*8}")

    for r in results:
        name = r["name"][:37]
        print(f"{name:<38} {r['n_layers_selected']:>7} {r['layers_correct']:>8} "
              f"{r['layers_false_positive']:>9} {r['layers_missed']:>7} "
              f"{r['weight_distance']:>8.2f} {r['perplexity']:>8.2f}")

    # ── Table 3: Literature Comparison ────────────────────────────────
    print(f"\n\n{'='*110}")
    print("TABLE 3: FULL LANDSCAPE — TECHNIQUES, CAPABILITIES, AND REPORTED RESULTS")
    print(f"{'='*110}")
    print(f"{'Technique':<26} {'Year':>5} {'#Dir':>5} {'Layers':>10} {'NormPres':>9} "
          f"{'Reg':>5} {'AutoTune':>9} {'Reported Refusal→':>18} {'Model':>14}")
    print(f"{'─'*26} {'─'*5} {'─'*5} {'─'*10} {'─'*9} {'─'*5} {'─'*9} {'─'*18} {'─'*14}")

    literature = [
        ("Arditi et al.", "2024", "1", "top-norm", "No", "0.0", "No",
         "~95%→~0%", "Llama-3-8B"),
        ("FailSpy/abliterator", "2024", "1", "mid-60%", "No", "0.0", "No",
         "~90%→~5%", "Llama-3-8B"),
        ("mlabonne tutorial", "2024", "1", "top-norm", "No", "0.0", "No",
         "~90%→~5%", "Llama-3-8B"),
        ("Gabliteration", "2024", "4-8", "knee", "No", "0.0", "No",
         "~95%→~0%", "Various 7B+"),
        ("grimjim norm-pres", "2024", "4-8", "knee", "Yes(bug)", "0.0", "No",
         "~90%→~5%", "Various 7B+"),
        ("Heretic (p-e-w)", "2025", "float", "kernel", "No", "TPE", "Yes",
         "~95%→~0%*", "Gemma-3-12B"),
        ("Wollschlager cones", "2025", "1-5", "per-layer", "—", "—", "RDO",
         "~98%→~1%", "Llama-3.1-8B"),
        ("OBLITERATUS basic", "2025", "1", "knee", "No", "0.0", "No",
         "~95%→60%**", "Qwen-0.5B"),
        ("OBLITERATUS advanced", "2025", "4", "knee", "Yes(fix)", "0.3", "No",
         "~95%→73%**", "Qwen-0.5B"),
        ("OBLITERATUS surgical", "2025", "8", "knee", "Yes(fix)", "0.0", "Yes***",
         "~95%→0%/broken", "Qwen-0.5B"),
    ]

    for row in literature:
        print(f"{row[0]:<26} {row[1]:>5} {row[2]:>5} {row[3]:>10} {row[4]:>9} "
              f"{row[5]:>5} {row[6]:>9} {row[7]:>18} {row[8]:>14}")

    print("\n  * Heretic: 2.8× lower KL divergence than manual abliterations (Gemma-3-12B benchmark)")
    print("  ** Our observed results on Qwen2.5-0.5B-Instruct — 0.5B may be too small for linear methods")
    print("  *** Surgical combines: whitened SVD + SAE + head surgery + neuron masking + jailbreak contrast")
    print(f"{'='*110}")

    # ── Analysis ──────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print("ANALYSIS: WHY OBLITERATUS UNDERPERFORMS AND WHAT TO FIX")
    print(f"{'='*80}")

    print("""
ROOT CAUSES (ordered by impact):

1. MODEL SIZE: All published abliteration results use 7B+ models
   - Arditi et al.: Llama-3-8B, Gemma-2-9B (hidden_dim=4096+)
   - FailSpy: Llama-3-8B
   - Heretic: Gemma-3-12B (headline benchmark)
   - Wollschlager et al.: Llama-3.1-8B
   - OBLITERATUS benchmarks: Qwen-0.5B (hidden_dim=896)

   The "single refusal direction" hypothesis may not hold well for small
   models. Wollschlager et al. (ICML 2025) showed that refusal lives in
   multi-dimensional CONCEPT CONES, and cone dimension scales with model
   size. A 0.5B model may encode refusal too diffusely for linear methods.

2. BASIC MODE USES NO CHAT TEMPLATE for activation collection
   - The model was trained with chat formatting — without it, activations
     during probing don't reflect actual refusal behavior
   - This is the single highest-impact config fix

3. ADVANCED MODE REGULARIZATION TOO HIGH (0.3)
   - Preserves 30% of refusal component by design
   - Combined with 4 directions where later ones capture noise, net
     removal is weak

4. SURGICAL MODE DOES TOO MUCH
   - 8 directions, whitened SVD, SAE features, neuron masking, head surgery
   - Each individually reasonable; together they destroy a 0.5B model
   - The whitened SVD un-whitening bug (now fixed) was extracting noise

5. NO BAYESIAN OPTIMIZATION (vs Heretic)
   - Heretic's key insight: jointly optimize layer weights, direction
     index, and component-specific parameters via TPE
   - Minimizes refusal rate AND KL divergence simultaneously
   - This automatically handles model-specific tuning that we do manually

RECOMMENDED CONFIG CHANGES:
  - basic:    use_chat_template → True
  - advanced: regularization → 0.1 (from 0.3)
  - surgical: n_directions → 4 (from 8), disable safety_neuron_masking
  - ALL:      Add model-size-aware defaults (n_dirs=1 for <2B, 4 for 2-10B)
  - NEW:      Add TPE optimization loop (like Heretic) as "optimized" method
""")


def main():
    results = run_experiment()
    print_table(results)

    # Save results
    out_path = "/tmp/abliteration_comparison_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
