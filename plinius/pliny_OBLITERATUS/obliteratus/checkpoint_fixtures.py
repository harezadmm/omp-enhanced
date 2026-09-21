"""Strict loader for the tiny project-owned neutral checkpoint fixtures."""

from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from pathlib import Path

import torch
from safetensors.torch import load_file

from obliteratus.checkpoint_fragments import Padding, Replica, TensorFragment


_MAX_FIXTURE_JSON_BYTES = 256 * 1024


@dataclass(frozen=True)
class TensorOracle:
    """Independent expected logical value stored separately from fragments."""

    shape: tuple[int, ...]
    dtype: str
    sha256: str
    values: torch.Tensor


@dataclass(frozen=True)
class FixtureCase:
    """One bounded fixture case ready for neutral validation."""

    case_id: str
    fragments: tuple[TensorFragment, ...]
    tensor_oracles: dict[str, TensorOracle]
    expected_manifest_digest: str


def _regular_file(path: Path) -> None:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise ValueError(f"fixture artifact is not a regular file: {path.name}")


def _load_json(path: Path) -> dict:
    _regular_file(path)
    size = path.stat().st_size
    if size > _MAX_FIXTURE_JSON_BYTES:
        raise ValueError(f"fixture JSON exceeds {_MAX_FIXTURE_JSON_BYTES} bytes: {path.name}")
    value = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture JSON is not an object: {path.name}")
    return value


def _require_safe_name(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or Path(value).name != value:
        raise ValueError(f"unsafe fixture {field}")
    return value


def load_fixture_case(case_root: Path | str) -> FixtureCase:
    """Load one generated JSON+safetensors fixture without pickle or network paths."""
    root = Path(case_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("fixture case root must be a non-symlink directory")
    record = _load_json(root / "case.json")
    if record.get("schema_id") != "obliteratus.checkpoint-fixture-case":
        raise ValueError("unsupported fixture case schema")
    tensor_files: dict[str, dict[str, torch.Tensor]] = {}
    fragments: list[TensorFragment] = []
    fragment_records = record.get("fragments")
    if not isinstance(fragment_records, list) or len(fragment_records) > 64:
        raise ValueError("fixture fragment list is invalid or too large")
    for item in fragment_records:
        if not isinstance(item, dict):
            raise ValueError("fixture fragment must be an object")
        payload_file = _require_safe_name(item["payload_file"], "payload file")
        payload_key = _require_safe_name(item["payload_key"], "payload key")
        if payload_file not in tensor_files:
            payload_path = root / payload_file
            _regular_file(payload_path)
            tensor_files[payload_file] = load_file(payload_path, device="cpu")
        try:
            payload = tensor_files[payload_file][payload_key]
        except KeyError as error:
            raise ValueError("fixture payload key is missing") from error
        padding = item["padding"]
        replica = item["replica"]
        fragments.append(
            TensorFragment(
                fragment_id=item["fragment_id"],
                component_id=item["component_id"],
                fqn=item["fqn"],
                role=item["role"],
                dtype=item["dtype"],
                global_shape=tuple(item["global_shape"]),
                local_shape=tuple(item["local_shape"]),
                element_offset=tuple(item["element_offset"]),
                element_extent=tuple(item["element_extent"]),
                padding=Padding(
                    before=tuple(padding["before"]),
                    after=tuple(padding["after"]),
                    semantic=padding["semantic"],
                ),
                shard_file_id=item["shard_file_id"],
                shard_digest_ref=item["shard_digest_ref"],
                fragment_digest=item["fragment_digest"],
                replica=Replica(
                    group_id=replica["group_id"],
                    member_index=replica["member_index"],
                    member_count=replica["member_count"],
                ),
                partition_axes=tuple(item["partition_axes"]),
                logical_tensor_id=item["logical_tensor_id"],
                tie_group_id=item["tie_group_id"],
                shared_storage_id=item["shared_storage_id"],
                topology_coordinates=tuple(
                    (kind, coordinate) for kind, coordinate in item["topology_coordinates"]
                ),
                evidence_refs=tuple(item["evidence_refs"]),
                payload=payload,
            )
        )
    oracle_file = _require_safe_name(record["oracle_file"], "oracle file")
    oracle_path = root / oracle_file
    _regular_file(oracle_path)
    oracle_values = load_file(oracle_path, device="cpu")
    tensor_oracles: dict[str, TensorOracle] = {}
    for item in record["oracles"]:
        logical_tensor_id = item["logical_tensor_id"]
        payload_key = _require_safe_name(item["payload_key"], "oracle payload key")
        tensor_oracles[logical_tensor_id] = TensorOracle(
            shape=tuple(item["shape"]),
            dtype=item["dtype"],
            sha256=item["sha256"],
            values=oracle_values[payload_key],
        )
    return FixtureCase(
        case_id=record["case_id"],
        fragments=tuple(fragments),
        tensor_oracles=tensor_oracles,
        expected_manifest_digest=record["expected_manifest_digest"],
    )
