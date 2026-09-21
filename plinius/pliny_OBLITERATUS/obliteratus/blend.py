#!/usr/bin/env python3
"""Complementary abliteration blending — weight-space interpolation between surgeries.

Novel technique: run two abliterations with different direction-finding methods
(e.g., aggressive/SVD and LEACE), then LERP-blend in weight space. Each method
makes different mistakes in different parts of the weight geometry:

  - Aggressive/SVD: deep refusal removal, but damages capability (greedy variance capture)
  - LEACE: preserves capability (KL-minimizing), but weaker output quality

Blending averages out each method's weaknesses. The 60/40 (LEACE/aggressive) ratio
was found by binary search to be the sweet spot for Qwen3.8-27B, yielding:

  - 0% refusal (from both parents)
  - 100% usable output quality (from aggressive parent)
  - +1.0pp MMLU vs stock (from LEACE parent's capability preservation)

Usage:
    obliteratus blend \\
        --model-a outputs/aggressive-surgery \\
        --model-b outputs/leace-surgery \\
        --alpha 0.6 \\
        --output outputs/blended-model

    # Binary search for optimal ratio
    obliteratus blend \\
        --model-a outputs/aggressive \\
        --model-b outputs/leace \\
        --search 0.3,0.5,0.6,0.7 \\
        --output outputs/blend-search

Alpha controls the interpolation: blended = alpha * model_b + (1 - alpha) * model_a
Higher alpha = more of model_b's character.
"""

from __future__ import annotations

import json
import logging
import math
import shutil
from pathlib import Path
from typing import Any

import torch
from safetensors.torch import load_file, save_file

from obliteratus.persistence_contracts import atomic_checkpoint_directory

logger = logging.getLogger(__name__)

_INDEX_NAME = "model.safetensors.index.json"
_GENERATED_FILES = {_INDEX_NAME, "blend_metadata.json"}


def _read_index(model_dir: Path) -> dict[str, Any]:
    """Read and validate a sharded safetensors index."""

    if not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory does not exist: {model_dir}")
    index_path = model_dir / _INDEX_NAME
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing safetensors index: {index_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid safetensors index JSON: {index_path}") from exc

    weight_map = index.get("weight_map") if isinstance(index, dict) else None
    if not isinstance(weight_map, dict) or not weight_map:
        raise ValueError(f"Safetensors index has no weight_map: {index_path}")
    for key, shard in weight_map.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"Safetensors index contains an invalid tensor key: {key!r}")
        if not isinstance(shard, str) or Path(shard).name != shard:
            raise ValueError(f"Safetensors index contains an unsafe shard path: {shard!r}")
        shard_path = model_dir / shard
        if not shard_path.is_file():
            raise FileNotFoundError(f"Missing safetensors shard: {shard_path}")
    return index


def _load_indexed_shard(
    model_dir: Path,
    shard: str,
    weight_map: dict[str, str],
) -> dict[str, torch.Tensor]:
    tensors = load_file(str(model_dir / shard))
    expected = {key for key, mapped_shard in weight_map.items() if mapped_shard == shard}
    if set(tensors) != expected:
        missing = sorted(expected - set(tensors))
        extra = sorted(set(tensors) - expected)
        raise ValueError(
            f"Safetensors shard/index mismatch in {model_dir / shard}: "
            f"missing={missing[:3]}, extra={extra[:3]}",
        )
    return tensors


def _validate_nonoverlapping_paths(model_a: Path, model_b: Path, output: Path) -> None:
    resolved_a = model_a.resolve()
    resolved_b = model_b.resolve()
    resolved_output = output.resolve()
    if resolved_a == resolved_b:
        raise ValueError("model_a and model_b must be different model directories")
    for source in (resolved_a, resolved_b):
        if resolved_output == source or resolved_output.is_relative_to(source):
            raise ValueError("output must not be a model directory or one of its descendants")
        if source.is_relative_to(resolved_output):
            raise ValueError("output must not contain either source model directory")


def _read_source_model(model_dir: Path) -> str | None:
    metadata_path = model_dir / "abliteration_metadata.json"
    if not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid abliteration metadata JSON: {metadata_path}") from exc
    source_model = metadata.get("source_model") if isinstance(metadata, dict) else None
    if not isinstance(source_model, str) or not source_model.strip():
        raise ValueError(f"Abliteration metadata has no source_model: {metadata_path}")
    return source_model


def _verify_lineage(model_a: Path, model_b: Path, *, required: bool) -> str | None:
    source_a = _read_source_model(model_a)
    source_b = _read_source_model(model_b)
    if required and (source_a is None or source_b is None):
        raise ValueError(
            "Both checkpoints require abliteration_metadata.json with matching source_model; "
            "use allow_unverified_lineage=True only after independently verifying lineage",
        )
    if source_a is not None and source_b is not None and source_a != source_b:
        raise ValueError(f"Checkpoint source_model values do not match: {source_a!r} != {source_b!r}")
    return source_a if source_a == source_b else None


def _copy_model_support_files(source: Path, destination: Path) -> None:
    for item in source.iterdir():
        if item.name in _GENERATED_FILES or item.suffix == ".safetensors" or item.name == ".git":
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, symlinks=True)
        else:
            shutil.copy2(item, target)


def _validate_blended_checkpoint(checkpoint: Path) -> None:
    index = _read_index(checkpoint)
    if not (checkpoint / "config.json").is_file():
        raise ValueError("Selected config source does not contain config.json")
    if not (checkpoint / "blend_metadata.json").is_file():
        raise ValueError("Blended checkpoint is missing blend_metadata.json")
    for shard in set(index["weight_map"].values()):
        _load_indexed_shard(checkpoint, shard, index["weight_map"])


def blend_models(
    model_a_path: str | Path,
    model_b_path: str | Path,
    output_path: str | Path,
    alpha: float = 0.6,
    config_source: str = "a",
    allow_unverified_lineage: bool = False,
) -> dict:
    """LERP-blend two models in weight space.

    blended[key] = alpha * model_b[key] + (1 - alpha) * model_a[key]

    Args:
        model_a_path: First model directory (e.g., aggressive surgery).
        model_b_path: Second model directory (e.g., LEACE surgery).
        output_path: Where to save the blended model.
        alpha: Blend ratio. 0.0 = pure model_a, 1.0 = pure model_b.
        config_source: Which model's config files to use ("a" or "b").
        allow_unverified_lineage: Permit checkpoints without matching OBLITERATUS
            source metadata. Tensor compatibility is still enforced.

    Returns:
        dict with tensor counts and blend metadata.
    """
    if not isinstance(alpha, (int, float)) or not math.isfinite(float(alpha)):
        raise ValueError("alpha must be a finite number between 0 and 1")
    alpha = float(alpha)
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0 and 1 inclusive")
    if config_source not in {"a", "b"}:
        raise ValueError("config_source must be 'a' or 'b'")

    model_a = Path(model_a_path)
    model_b = Path(model_b_path)
    output = Path(output_path)
    _validate_nonoverlapping_paths(model_a, model_b, output)
    source_model = _verify_lineage(
        model_a,
        model_b,
        required=not allow_unverified_lineage,
    )

    index_a = _read_index(model_a)
    index_b = _read_index(model_b)
    map_a = index_a["weight_map"]
    map_b = index_b["weight_map"]
    if set(map_a) != set(map_b):
        missing_from_b = sorted(set(map_a) - set(map_b))
        missing_from_a = sorted(set(map_b) - set(map_a))
        raise ValueError(
            "Model tensor keys do not match: "
            f"missing_from_b={missing_from_b[:3]}, missing_from_a={missing_from_a[:3]}",
        )

    shards = sorted(set(map_a.values()))
    total_tensors = 0
    blended_tensors = 0

    logger.info("Blending: %.0f%% model_b + %.0f%% model_a", alpha * 100, (1 - alpha) * 100)
    logger.info("Shards: %d", len(shards))

    metadata: dict[str, Any]
    source = model_a if config_source == "a" else model_b
    with atomic_checkpoint_directory(output, validate=_validate_blended_checkpoint) as staging:
        for shard_idx, shard in enumerate(shards):
            tensors_a = _load_indexed_shard(model_a, shard, map_a)
            needed_b_shards = {map_b[key] for key in tensors_a}
            tensors_b: dict[str, torch.Tensor] = {}
            for b_shard in needed_b_shards:
                tensors_b.update(_load_indexed_shard(model_b, b_shard, map_b))

            merged: dict[str, torch.Tensor] = {}
            for key, tensor_a in tensors_a.items():
                tensor_b = tensors_b[key]
                if tensor_a.shape != tensor_b.shape:
                    raise ValueError(
                        f"Tensor shape mismatch for {key}: {tensor_a.shape} != {tensor_b.shape}",
                    )
                if tensor_a.dtype != tensor_b.dtype:
                    raise ValueError(
                        f"Tensor dtype mismatch for {key}: {tensor_a.dtype} != {tensor_b.dtype}",
                    )
                if not torch.is_floating_point(tensor_a):
                    raise TypeError(f"Tensor {key} has non-floating dtype {tensor_a.dtype}")
                merged[key] = alpha * tensor_b + (1.0 - alpha) * tensor_a
                total_tensors += 1
                blended_tensors += 1

            save_file(merged, str(staging / shard))
            if (shard_idx + 1) % 5 == 0 or shard_idx == len(shards) - 1:
                logger.info("  [%d/%d] shards processed", shard_idx + 1, len(shards))

        (staging / _INDEX_NAME).write_text(
            json.dumps(index_a, indent=2) + "\n",
            encoding="utf-8",
        )
        _copy_model_support_files(source, staging)
        metadata = {
            "blend_method": "lerp",
            "alpha": alpha,
            "config_source": config_source,
            "lineage_verified": source_model is not None,
            "source_model": source_model,
            "model_a": str(model_a),
            "model_b": str(model_b),
            "formula": f"blended = {alpha} * model_b + {1.0 - alpha} * model_a",
            "total_tensors": total_tensors,
            "blended_tensors": blended_tensors,
        }
        (staging / "blend_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )

    logger.info("Blend complete: %d tensors blended", blended_tensors)

    return metadata


def blend_search(
    model_a_path: str | Path,
    model_b_path: str | Path,
    output_dir: str | Path,
    alphas: list[float] | None = None,
    config_source: str = "a",
    allow_unverified_lineage: bool = False,
) -> list[dict]:
    """Create multiple blends for binary-search evaluation.

    Args:
        model_a_path: First model directory.
        model_b_path: Second model directory.
        output_dir: Parent directory for blend outputs.
        alphas: List of blend ratios to try. Default: [0.3, 0.5, 0.6, 0.7].

    Returns:
        list of blend metadata dicts.
    """
    if alphas is None:
        alphas = [0.3, 0.5, 0.6, 0.7]
    if not alphas:
        raise ValueError("alphas must contain at least one blend ratio")
    normalized = [float(alpha) for alpha in alphas]
    if len(set(normalized)) != len(normalized):
        raise ValueError("alphas must not contain duplicate blend ratios")

    output_dir = Path(output_dir)
    results = []

    for alpha in normalized:
        percentage = f"{alpha * 100:g}".replace(".", "p")
        label = f"blend_{percentage}"
        output = output_dir / label
        logger.info("\n=== %s (alpha=%.2f) ===", label, alpha)
        meta = blend_models(
            model_a_path,
            model_b_path,
            output,
            alpha=alpha,
            config_source=config_source,
            allow_unverified_lineage=allow_unverified_lineage,
        )
        meta["label"] = label
        results.append(meta)

    return results


def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    p = argparse.ArgumentParser(
        description="Complementary abliteration blending — interpolate two surgeries in weight space."
    )
    p.add_argument("--model-a", required=True, help="First model (e.g., aggressive surgery)")
    p.add_argument("--model-b", required=True, help="Second model (e.g., LEACE surgery)")
    p.add_argument("--alpha", type=float, default=0.6, help="Blend ratio (0=pure A, 1=pure B)")
    p.add_argument("--config-source", choices=["a", "b"], default="a")
    p.add_argument("--allow-unverified-lineage", action="store_true")
    p.add_argument("--search", type=str, default=None,
                   help="Comma-separated alphas for binary search (e.g., 0.3,0.5,0.6,0.7)")
    p.add_argument("--output", required=True, help="Output directory")
    args = p.parse_args()

    if args.search:
        alphas = [float(a) for a in args.search.split(",")]
        results = blend_search(
            args.model_a,
            args.model_b,
            args.output,
            alphas,
            config_source=args.config_source,
            allow_unverified_lineage=args.allow_unverified_lineage,
        )
        print(f"\nCreated {len(results)} blends in {args.output}/")
        for r in results:
            print(f"  {r['label']}: alpha={r['alpha']}")
    else:
        result = blend_models(
            args.model_a,
            args.model_b,
            args.output,
            alpha=args.alpha,
            config_source=args.config_source,
            allow_unverified_lineage=args.allow_unverified_lineage,
        )
        print(f"\nBlend complete: {result['blended_tensors']} tensors blended at alpha={args.alpha}")


if __name__ == "__main__":
    main()
