#!/usr/bin/env python3
"""Generate the deterministic, synthetic Wave 2 checkpoint fixture corpus."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import torch
from safetensors.torch import save_file

from obliteratus.checkpoint_fragments import (
    Padding,
    Replica,
    TensorFragment,
    reconstruct_logical_tensor,
    validate_fragments,
)


GENERATOR_VERSION = "1.0.0"
CORPUS_LIMITS = {
    "max_case_bytes": 65536,
    "max_cases": 16,
    "max_files_per_case": 16,
    "max_tensors_per_case": 16,
}


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(_json_bytes(value))


def _tensor_digest(tensor: torch.Tensor) -> str:
    raw = tensor.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
    return f"sha256:{sha256(raw).hexdigest()}"


def _fragment(
    fragment_id: str,
    payload: torch.Tensor,
    *,
    payload_file: str,
    global_shape: tuple[int, ...],
    offset: tuple[int, ...],
    extent: tuple[int, ...] | None = None,
    logical_tensor_id: str,
    component_id: str = "model",
    role: str = "parameter",
    padding: Padding | None = None,
    replica: Replica | None = None,
    partition_axes: tuple[int, ...] = (0,),
    tie_group_id: str | None = None,
    topology_coordinates: tuple[tuple[str, int], ...] = (("rank", 0),),
) -> tuple[TensorFragment, str]:
    extent = extent if extent is not None else tuple(payload.shape)
    padding = padding or Padding.zeros(len(global_shape))
    replica = replica or Replica.unique()
    logical_payload = payload
    if global_shape:
        logical_payload = payload[
            tuple(
                slice(before, before + size)
                for before, size in zip(padding.before, extent, strict=True)
            )
        ]
    fragment = TensorFragment(
        fragment_id=fragment_id,
        component_id=component_id,
        fqn=logical_tensor_id,
        role=role,
        dtype=str(payload.dtype).removeprefix("torch."),
        global_shape=global_shape,
        local_shape=tuple(payload.shape),
        element_offset=offset,
        element_extent=extent,
        padding=padding,
        shard_file_id=payload_file,
        shard_digest_ref=f"source-digest:{payload_file}",
        fragment_digest=_tensor_digest(logical_payload),
        replica=replica,
        partition_axes=partition_axes if global_shape else (),
        logical_tensor_id=logical_tensor_id,
        tie_group_id=tie_group_id,
        shared_storage_id=tie_group_id,
        topology_coordinates=topology_coordinates,
        evidence_refs=(f"synthetic:{fragment_id}",),
        payload=payload,
    )
    return fragment, payload_file


def _case_definitions() -> list[dict[str, Any]]:
    world1: list[tuple[TensorFragment, str]] = []
    world1.append(
        _fragment(
            "w1-weight",
            torch.arange(6, dtype=torch.float32).reshape(2, 3),
            payload_file="rank-00000.safetensors",
            global_shape=(2, 3),
            offset=(0, 0),
            logical_tensor_id="model.weight",
            partition_axes=(),
        )
    )
    world1.append(
        _fragment(
            "w1-scalar",
            torch.tensor(3, dtype=torch.int64),
            payload_file="rank-00000.safetensors",
            global_shape=(),
            offset=(),
            logical_tensor_id="model.step",
            role="persistent_buffer",
            partition_axes=(),
        )
    )
    world1.append(
        _fragment(
            "w1-buffer",
            torch.tensor([0.25, 0.5], dtype=torch.float32),
            payload_file="rank-00000.safetensors",
            global_shape=(2,),
            offset=(0,),
            logical_tensor_id="model.running_mean",
            role="persistent_buffer",
            partition_axes=(),
        )
    )
    tied = torch.tensor([1.0, 2.0, 3.0, 4.0])
    for fragment_id, tensor_id in (("w1-embed", "model.embed.weight"), ("w1-head", "lm_head.weight")):
        world1.append(
            _fragment(
                fragment_id,
                tied.clone(),
                payload_file="rank-00000.safetensors",
                global_shape=(4,),
                offset=(0,),
                logical_tensor_id=tensor_id,
                partition_axes=(),
                tie_group_id="tie-embedding-head",
            )
        )
    world1.append(
        _fragment(
            "w1-expert",
            torch.arange(4, dtype=torch.float32).reshape(2, 2),
            payload_file="rank-00000.safetensors",
            global_shape=(2, 2),
            offset=(0, 0),
            logical_tensor_id="model.experts.0.weight",
            partition_axes=(),
            topology_coordinates=(("ep", 0), ("rank", 0)),
        )
    )

    uneven = torch.arange(7, dtype=torch.int64)
    world2 = [
        _fragment(
            "w2-r0",
            torch.cat((uneven[:3], torch.tensor([-1], dtype=torch.int64))),
            payload_file="rank-00000.safetensors",
            global_shape=(7,),
            offset=(0,),
            extent=(3,),
            logical_tensor_id="model.weight",
            padding=Padding((0,), (1,), "producer_declared"),
            topology_coordinates=(("rank", 0), ("tp", 0)),
        ),
        _fragment(
            "w2-r1",
            uneven[3:].clone(),
            payload_file="rank-00001.safetensors",
            global_shape=(7,),
            offset=(3,),
            logical_tensor_id="model.weight",
            topology_coordinates=(("rank", 1), ("tp", 1)),
        ),
    ]

    matrix = torch.arange(35, dtype=torch.float32).reshape(5, 7)
    world4: list[tuple[TensorFragment, str]] = []
    rank = 0
    for row, (top, bottom) in enumerate(((0, 2), (2, 5))):
        for column, (left, right) in enumerate(((0, 3), (3, 7))):
            world4.append(
                _fragment(
                    f"w4-r{rank}",
                    matrix[top:bottom, left:right].clone(),
                    payload_file=f"rank-{rank:05d}.safetensors",
                    global_shape=(5, 7),
                    offset=(top, left),
                    logical_tensor_id="model.weight",
                    partition_axes=(0, 1),
                    topology_coordinates=(("rank", rank), ("tp_row", row), ("tp_col", column)),
                )
            )
            rank += 1

    replica_value = torch.tensor([5.0, 6.0, 7.0])
    replicas = [
        _fragment(
            f"dp-r{rank}",
            replica_value.clone(),
            payload_file=f"rank-{rank:05d}.safetensors",
            global_shape=(3,),
            offset=(0,),
            logical_tensor_id="model.weight",
            partition_axes=(),
            replica=Replica("dp-full", rank, 4),
            topology_coordinates=(("dp", rank), ("rank", rank)),
        )
        for rank in range(4)
    ]

    topology_value = torch.arange(16, dtype=torch.float32).reshape(4, 4)
    tp_pp: list[tuple[TensorFragment, str]] = []
    rank = 0
    for pp, (top, bottom) in enumerate(((0, 2), (2, 4))):
        for tp, (left, right) in enumerate(((0, 2), (2, 4))):
            tp_pp.append(
                _fragment(
                    f"tp-pp-r{rank}",
                    topology_value[top:bottom, left:right].clone(),
                    payload_file=f"rank-{rank:05d}.safetensors",
                    global_shape=(4, 4),
                    offset=(top, left),
                    logical_tensor_id="model.weight",
                    partition_axes=(0, 1),
                    topology_coordinates=(("pp", pp), ("rank", rank), ("tp", tp)),
                )
            )
            rank += 1

    mixed = [
        _fragment(
            "mixed-model",
            torch.arange(4, dtype=torch.float32).reshape(2, 2),
            payload_file="rank-00000.safetensors",
            global_shape=(2, 2),
            offset=(0, 0),
            logical_tensor_id="model.weight",
            component_id="full-model",
            partition_axes=(),
            topology_coordinates=(("rank", 0),),
        ),
        _fragment(
            "mixed-adapter",
            torch.tensor([[0.5, -0.5]], dtype=torch.float32),
            payload_file="rank-00001.safetensors",
            global_shape=(1, 2),
            offset=(0, 0),
            logical_tensor_id="adapter.lora_A.weight",
            component_id="peft-adapter",
            partition_axes=(),
            topology_coordinates=(("rank", 1),),
        ),
    ]

    return [
        {
            "case_id": "world1-complete",
            "world_size": 1,
            "features": ["buffer", "expert", "scalar", "tied_weight"],
            "components": ["full_model"],
            "topology": {"source": {"world_size": 1}, "target": {"world_size": 1}},
            "fragments": world1,
        },
        {
            "case_id": "world2-uneven-1d",
            "world_size": 2,
            "features": ["padding", "uneven_1d"],
            "components": ["full_model"],
            "topology": {"source": {"tp": 2}, "target": {"world_size": 1}},
            "fragments": world2,
        },
        {
            "case_id": "world4-uneven-2d",
            "world_size": 4,
            "features": ["uneven_2d"],
            "components": ["full_model"],
            "topology": {"source": {"tp_rows": 2, "tp_columns": 2}, "target": {"world_size": 1}},
            "fragments": world4,
        },
        {
            "case_id": "world4-dp-replicas",
            "world_size": 4,
            "features": ["dp_replica"],
            "components": ["full_model"],
            "topology": {"source": {"dp": 4}, "target": {"world_size": 1}},
            "fragments": replicas,
        },
        {
            "case_id": "tp2-pp2-to-single",
            "world_size": 4,
            "features": ["pipeline_parallel", "topology_a_to_b"],
            "components": ["full_model"],
            "topology": {"source": {"pp": 2, "tp": 2}, "target": {"world_size": 1}},
            "fragments": tp_pp,
        },
        {
            "case_id": "mixed-model-peft",
            "world_size": 2,
            "features": ["mixed_full_model_peft"],
            "components": ["full_model", "peft_adapter"],
            "topology": {"source": {"world_size": 2}, "target": {"world_size": 1}},
            "fragments": mixed,
        },
    ]


def _write_case(root: Path, definition: dict[str, Any]) -> dict[str, Any]:
    case_id = definition["case_id"]
    case_root = root / "cases" / case_id
    case_root.mkdir(parents=True)
    fragment_pairs: list[tuple[TensorFragment, str]] = definition["fragments"]
    by_file: dict[str, dict[str, torch.Tensor]] = {}
    fragments: list[TensorFragment] = []
    fragment_records: list[dict[str, object]] = []
    for fragment, payload_file in fragment_pairs:
        fragments.append(fragment)
        by_file.setdefault(payload_file, {})[fragment.fragment_id] = fragment.payload
        record = fragment.manifest_record()
        record["payload_file"] = payload_file
        record["payload_key"] = fragment.fragment_id
        fragment_records.append(record)
    for filename, tensors in sorted(by_file.items()):
        save_file(dict(sorted(tensors.items())), case_root / filename)
    validation = validate_fragments(fragments)
    oracle_tensors: dict[str, torch.Tensor] = {}
    oracle_records: list[dict[str, object]] = []
    for index, logical in enumerate(validation.logical_tensors):
        value = reconstruct_logical_tensor(validation, logical.logical_tensor_id)
        payload_key = f"tensor_{index:03d}"
        oracle_tensors[payload_key] = value
        oracle_records.append(
            {
                "logical_tensor_id": logical.logical_tensor_id,
                "payload_key": payload_key,
                "shape": list(value.shape),
                "dtype": str(value.dtype).removeprefix("torch."),
                "sha256": _tensor_digest(value),
            }
        )
    save_file(dict(sorted(oracle_tensors.items())), case_root / "oracles.safetensors")
    _write_json(
        case_root / "case.json",
        {
            "schema_id": "obliteratus.checkpoint-fixture-case",
            "schema_version": "1.0.0",
            "case_id": case_id,
            "world_size": definition["world_size"],
            "features": sorted(definition["features"]),
            "components": definition["components"],
            "topology": definition["topology"],
            "fragments": sorted(fragment_records, key=lambda item: item["fragment_id"]),
            "oracle_file": "oracles.safetensors",
            "oracles": oracle_records,
            "expected_manifest_digest": validation.manifest_digest,
        },
    )
    files = []
    for path in sorted(item for item in case_root.iterdir() if item.is_file()):
        payload = path.read_bytes()
        files.append(
            {
                "relative_path": path.name,
                "size_bytes": len(payload),
                "sha256": f"sha256:{sha256(payload).hexdigest()}",
            }
        )
    if len(files) > CORPUS_LIMITS["max_files_per_case"]:
        raise ValueError(f"fixture case exceeds file limit: {case_id}")
    if sum(item["size_bytes"] for item in files) > CORPUS_LIMITS["max_case_bytes"]:
        raise ValueError(f"fixture case exceeds byte limit: {case_id}")
    return {
        "case_id": case_id,
        "relative_path": f"cases/{case_id}",
        "world_size": definition["world_size"],
        "features": sorted(definition["features"]),
        "files": files,
    }


def _negative_catalog() -> dict[str, object]:
    failures = {
        "dimension_mismatch": "DCI_VALIDATION_FAILED",
        "extra_shard": "DCI_SOURCE_BOUNDARY_VIOLATION",
        "fragment_out_of_bounds": "DCI_VALIDATION_FAILED",
        "integer_overflow": "DCI_VALIDATION_FAILED",
        "missing_shard": "DCI_SOURCE_BOUNDARY_VIOLATION",
        "negative_integer": "DCI_VALIDATION_FAILED",
        "padding_shape_mismatch": "DCI_VALIDATION_FAILED",
        "path_traversal": "DCI_SOURCE_BOUNDARY_VIOLATION",
        "payload_dtype_mismatch": "DCI_VALIDATION_FAILED",
        "payload_shape_mismatch": "DCI_VALIDATION_FAILED",
        "replica_digest_mismatch": "DCI_VALIDATION_FAILED",
        "resource_manifest_bomb": "DCI_RESOURCE_LIMIT",
        "source_special_file": "DCI_SOURCE_BOUNDARY_VIOLATION",
        "source_symlink": "DCI_SOURCE_BOUNDARY_VIOLATION",
        "truncated_shard": "DCI_SOURCE_BOUNDARY_VIOLATION",
        "coverage_gap": "DCI_VALIDATION_FAILED",
        "coverage_overlap": "DCI_VALIDATION_FAILED",
    }
    return {
        "schema_id": "obliteratus.checkpoint-negative-fixtures",
        "schema_version": "1.0.0",
        "cases": [
            {
                "case_id": f"negative-{index:02d}",
                "failure": failure,
                "expected_code": code,
                "mutation": f"deterministic:{failure}",
            }
            for index, (failure, code) in enumerate(sorted(failures.items()), start=1)
        ],
    }


def generate_corpus(destination: Path | str) -> Path:
    """Create a new bounded corpus; existing paths are never overwritten."""
    root = Path(destination)
    if root.exists() or root.is_symlink():
        raise FileExistsError(f"fixture destination already exists: {root}")
    root.mkdir(parents=True)
    definitions = _case_definitions()
    if len(definitions) > CORPUS_LIMITS["max_cases"]:
        raise ValueError("fixture corpus exceeds case limit")
    cases = [_write_case(root, definition) for definition in definitions]
    _write_json(root / "negative-cases.json", _negative_catalog())
    _write_json(
        root / "fixture-corpus.json",
        {
            "schema_id": "obliteratus.checkpoint-fixture-corpus",
            "schema_version": "1.0.0",
            "generator": {
                "path": "scripts/generate_checkpoint_fixtures.py",
                "version": GENERATOR_VERSION,
            },
            "license": "AGPL-3.0-or-later",
            "provenance": {
                "kind": "deterministic_synthetic",
                "seed": 0,
                "third_party_data": False,
                "third_party_weights": False,
            },
            "limits": CORPUS_LIMITS,
            "cases": sorted(cases, key=lambda item: item["case_id"]),
        },
    )
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    generate_corpus(arguments.destination)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI wrapper
    raise SystemExit(main())
