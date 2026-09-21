"""Transactional canonical safetensors writer for validated neutral fragments."""

from __future__ import annotations

import json
import os
import shutil
import stat
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

import torch
from safetensors.torch import load_file, save_file

from obliteratus.checkpoint_errors import CheckpointContractError
from obliteratus.checkpoint_fragments import (
    TensorFragment,
    ValidationResult,
    reconstruct_logical_tensor,
    validate_fragments,
)
from obliteratus.checkpoint_provenance import (
    ProvenanceRecord,
    verify_provenance_record,
)
from obliteratus.persistence_contracts import atomic_checkpoint_directory


_DIGEST_PREFIX = "sha256:"
_INT64_MAX = (1 << 63) - 1
_WRITER_BUFFER_BYTES = 1 << 20
_COPY_KINDS = frozenset({"configuration", "tokenizer"})
_CANONICAL_DTYPES = frozenset(
    {
        "bool",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "int8",
        "int16",
        "int32",
        "int64",
        "float8_e4m3fn",
        "float8_e5m2",
        "float16",
        "bfloat16",
        "float32",
        "float64",
        "complex64",
    }
)


@dataclass(frozen=True)
class WriterLimits:
    """Admission limits applied before a staging directory is created."""

    max_shard_bytes: int = 5 << 30
    max_output_bytes: int = 1 << 40
    max_temp_bytes: int = 1 << 40
    max_peak_ram_bytes: int = 16 << 30
    min_free_headroom_percent: int = 10

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.min_free_headroom_percent > 100:
            raise ValueError("min_free_headroom_percent cannot exceed 100")


@dataclass(frozen=True)
class VerifiedSourceFile:
    """One source artifact whose path and digest are independently rechecked."""

    path: Path
    relative_path: str
    expected_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        _safe_relative(self.relative_path)
        _require_digest(self.expected_sha256, "source digest")


@dataclass(frozen=True)
class ImmutableCopy:
    """A base configuration/tokenizer file copied only after exact hash match."""

    relative_path: str
    source_path: Path
    expected_sha256: str
    kind: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", Path(self.source_path))
        _safe_basename(self.relative_path)
        _require_digest(self.expected_sha256, "copy digest")
        if self.kind not in _COPY_KINDS:
            raise ValueError("copy kind must be configuration or tokenizer")


@dataclass(frozen=True)
class CanonicalWriteResult:
    """Identity and immutable location of a successfully promoted checkpoint."""

    artifact_id: str
    output_path: Path
    weight_files: tuple[str, ...]
    manifest_digest: str


@dataclass(frozen=True)
class _Fingerprint:
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> _Fingerprint:
        return cls(value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns)


@dataclass(frozen=True)
class _Snapshot:
    path: Path
    relative_path: str
    fingerprint: _Fingerprint
    sha256: str

    def file_record(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "size_bytes": self.fingerprint.size,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class _TensorSpec:
    name: str
    logical_tensor_id: str
    size_bytes: int


@dataclass(frozen=True)
class _TensorOracle:
    shape: tuple[int, ...]
    dtype: str
    sha256: str


@dataclass(frozen=True)
class _Admission:
    logical_bytes: int
    estimated_output_bytes: int
    estimated_temp_bytes: int
    estimated_peak_ram_bytes: int


def _safe_relative(value: str) -> None:
    pure = PurePosixPath(value)
    if (
        not isinstance(value, str)
        or not value
        or pure.is_absolute()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or len(value) > 4096
    ):
        raise ValueError("relative path is unsafe")


def _safe_basename(value: str) -> None:
    _safe_relative(value)
    if PurePosixPath(value).name != value:
        raise ValueError("canonical copied artifacts must be root-level files")


def _require_digest(value: str, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith(_DIGEST_PREFIX)
        or len(value) != len(_DIGEST_PREFIX) + 64
        or any(character not in "0123456789abcdef" for character in value[len(_DIGEST_PREFIX) :])
    ):
        raise ValueError(f"{field} must be a sha256 digest")


def _source_changed(reference: str) -> CheckpointContractError:
    return CheckpointContractError(
        "DCI_SOURCE_CHANGED",
        detail="source_digest_or_identity_changed",
        affected_refs=(reference,),
    )


def _open_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)


def _open_snapshot(path: Path, reference: str) -> int:
    try:
        return os.open(path, _open_flags())
    except OSError as error:
        raise _source_changed(reference) from error


def _hash_descriptor(descriptor: int, reference: str) -> str:
    digest = sha256()
    try:
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                return f"sha256:{digest.hexdigest()}"
            digest.update(chunk)
    except OSError as error:
        raise _source_changed(reference) from error


def _read_snapshot(descriptor: int, size: int, reference: str) -> bytes:
    try:
        return os.read(descriptor, size)
    except OSError as error:
        raise _source_changed(reference) from error


def _descriptor_fingerprint(descriptor: int, reference: str) -> _Fingerprint:
    try:
        return _Fingerprint.from_stat(os.fstat(descriptor))
    except OSError as error:
        raise _source_changed(reference) from error


def _snapshot(path: Path, relative_path: str, expected_digest: str) -> _Snapshot:
    try:
        observed = path.lstat()
    except OSError as error:
        raise _source_changed(relative_path) from error
    if not stat.S_ISREG(observed.st_mode):
        raise CheckpointContractError(
            "DCI_SOURCE_BOUNDARY_VIOLATION",
            detail="source_not_regular_file",
            affected_refs=(relative_path,),
        )
    try:
        if path.absolute() != path.resolve(strict=True):
            raise CheckpointContractError(
                "DCI_SOURCE_BOUNDARY_VIOLATION",
                detail="source_symlink",
                affected_refs=(relative_path,),
            )
    except OSError as error:
        raise _source_changed(relative_path) from error
    fingerprint = _Fingerprint.from_stat(observed)
    descriptor = _open_snapshot(path, relative_path)
    try:
        if _descriptor_fingerprint(descriptor, relative_path) != fingerprint:
            raise _source_changed(relative_path)
        digest = _hash_descriptor(descriptor, relative_path)
        if _descriptor_fingerprint(descriptor, relative_path) != fingerprint:
            raise _source_changed(relative_path)
    finally:
        os.close(descriptor)
    if digest != expected_digest:
        raise _source_changed(relative_path)
    try:
        if _Fingerprint.from_stat(path.lstat()) != fingerprint:
            raise _source_changed(relative_path)
    except OSError as error:
        raise _source_changed(relative_path) from error
    return _Snapshot(path, relative_path, fingerprint, digest)


def _revalidate_snapshot(snapshot: _Snapshot) -> None:
    try:
        observed = _Fingerprint.from_stat(snapshot.path.lstat())
    except OSError as error:
        raise _source_changed(snapshot.relative_path) from error
    if observed != snapshot.fingerprint:
        raise _source_changed(snapshot.relative_path)
    descriptor = _open_snapshot(snapshot.path, snapshot.relative_path)
    try:
        if _descriptor_fingerprint(descriptor, snapshot.relative_path) != snapshot.fingerprint:
            raise _source_changed(snapshot.relative_path)
        digest = _hash_descriptor(descriptor, snapshot.relative_path)
    finally:
        os.close(descriptor)
    if digest != snapshot.sha256:
        raise _source_changed(snapshot.relative_path)


def _tensor_bytes(shape: tuple[int, ...], element_size: int, reference: str) -> int:
    elements = 1
    for dimension in shape:
        if dimension and elements > _INT64_MAX // dimension:
            raise CheckpointContractError(
                "DCI_VALIDATION_FAILED",
                detail="integer_overflow",
                affected_refs=(reference,),
            )
        elements *= dimension
    if elements and elements > _INT64_MAX // element_size:
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="integer_overflow",
            affected_refs=(reference,),
        )
    return elements * element_size


def _tensor_specs(validation: ValidationResult) -> tuple[_TensorSpec, ...]:
    names = [logical.fqn for logical in validation.logical_tensors]
    if len(set(names)) != len(names):
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="canonical_tensor_name_duplicate",
            affected_refs=names,
        )
    specs = []
    for logical in validation.logical_tensors:
        if logical.dtype not in _CANONICAL_DTYPES:
            raise CheckpointContractError(
                "DCI_VALIDATION_FAILED",
                detail="canonical_dtype_unsupported",
                affected_refs=(logical.logical_tensor_id,),
            )
        payload = logical.fragments[0].payload
        if payload is None:
            raise CheckpointContractError(
                "DCI_VALIDATION_FAILED",
                detail="payload_unavailable",
                affected_refs=(logical.logical_tensor_id,),
            )
        specs.append(
            _TensorSpec(
                name=logical.fqn,
                logical_tensor_id=logical.logical_tensor_id,
                size_bytes=_tensor_bytes(
                    logical.global_shape,
                    payload.element_size(),
                    logical.logical_tensor_id,
                ),
            )
        )
    return tuple(sorted(specs, key=lambda item: item.name))


def _shard_plan(specs: tuple[_TensorSpec, ...], max_shard_bytes: int) -> tuple[tuple[_TensorSpec, ...], ...]:
    oversized = next((spec for spec in specs if spec.size_bytes > max_shard_bytes), None)
    if oversized is not None:
        raise CheckpointContractError(
            "DCI_ADMISSION_DENIED",
            detail="tensor_exceeds_max_shard_bytes",
            affected_refs=(oversized.logical_tensor_id,),
        )
    shards: list[list[_TensorSpec]] = []
    current: list[_TensorSpec] = []
    current_bytes = 0
    for spec in specs:
        if current and current_bytes + spec.size_bytes > max_shard_bytes:
            shards.append(current)
            current = []
            current_bytes = 0
        current.append(spec)
        current_bytes += spec.size_bytes
    if current:
        shards.append(current)
    return tuple(tuple(shard) for shard in shards)


def _admit(
    destination: Path,
    plan: tuple[tuple[_TensorSpec, ...], ...],
    copy_snapshots: tuple[_Snapshot, ...],
    limits: WriterLimits,
) -> _Admission:
    logical_bytes = sum(spec.size_bytes for shard in plan for spec in shard)
    copied_bytes = sum(snapshot.fingerprint.size for snapshot in copy_snapshots)
    header_allowance = (
        sum(len(spec.name.encode("utf-8")) + 256 for shard in plan for spec in shard)
        + 4096 * max(1, len(plan))
        + 8192
    )
    estimated_output = logical_bytes + copied_bytes + header_allowance
    estimated_temp = estimated_output
    largest_shard = max((sum(spec.size_bytes for spec in shard) for shard in plan), default=0)
    largest_tensor = max((spec.size_bytes for shard in plan for spec in shard), default=0)
    peak_ram = largest_shard + largest_tensor + _WRITER_BUFFER_BYTES
    checks = (
        (estimated_output, limits.max_output_bytes, "max_output_bytes"),
        (estimated_temp, limits.max_temp_bytes, "max_temp_bytes"),
        (peak_ram, limits.max_peak_ram_bytes, "max_peak_ram_bytes"),
    )
    for required, maximum, detail in checks:
        if required > maximum:
            raise CheckpointContractError(
                "DCI_ADMISSION_DENIED",
                detail=detail,
                affected_refs=(f"required:{required}", f"available:{maximum}"),
            )
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise CheckpointContractError(
            "DCI_ADMISSION_DENIED",
            detail="destination_parent_unavailable",
            affected_refs=("destination",),
        ) from error
    if destination.parent.is_symlink():
        raise CheckpointContractError(
            "DCI_SOURCE_BOUNDARY_VIOLATION",
            detail="destination_parent_symlink",
            affected_refs=("destination",),
        )
    try:
        available = shutil.disk_usage(destination.parent).free
    except OSError as error:
        raise CheckpointContractError(
            "DCI_ADMISSION_DENIED",
            detail="filesystem_capacity_unavailable",
            affected_refs=("destination",),
        ) from error
    required_with_headroom = estimated_temp * (100 + limits.min_free_headroom_percent)
    required_with_headroom = (required_with_headroom + 99) // 100
    if available < required_with_headroom:
        raise CheckpointContractError(
            "DCI_ADMISSION_DENIED",
            detail="filesystem_free_bytes",
            affected_refs=(f"required:{required_with_headroom}", f"available:{available}"),
        )
    return _Admission(logical_bytes, estimated_output, estimated_temp, peak_ram)


def _copy_snapshot(snapshot: _Snapshot, destination: Path) -> None:
    source = _open_snapshot(snapshot.path, snapshot.relative_path)
    try:
        if _descriptor_fingerprint(source, snapshot.relative_path) != snapshot.fingerprint:
            raise _source_changed(snapshot.relative_path)
        with destination.open("xb") as output:
            while True:
                chunk = _read_snapshot(source, 1 << 20, snapshot.relative_path)
                if not chunk:
                    break
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if _descriptor_fingerprint(source, snapshot.relative_path) != snapshot.fingerprint:
            raise _source_changed(snapshot.relative_path)
    finally:
        os.close(source)
    if _file_digest(destination) != snapshot.sha256:
        raise _source_changed(snapshot.relative_path)


def _save_safetensors_file(tensors: Mapping[str, torch.Tensor], path: Path) -> None:
    save_file(dict(sorted(tensors.items())), path)


def _file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _tensor_digest(tensor: torch.Tensor) -> str:
    raw = tensor.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
    return f"sha256:{sha256(raw).hexdigest()}"


def _write_json(path: Path, value: object) -> None:
    payload = json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _output_record(path: Path) -> dict[str, Any]:
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode):
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="output_not_regular_file",
            affected_refs=(path.name,),
        )
    return {
        "relative_path": path.name,
        "size_bytes": observed.st_size,
        "sha256": _file_digest(path),
    }


def _canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return f"sha256:{sha256(payload).hexdigest()}"


def _manifest(
    *,
    artifact_id: str,
    descriptor_digest: str,
    source_records: list[dict[str, Any]],
    source_topology: Mapping[str, Any],
    validation: ValidationResult,
    output_records: list[dict[str, Any]],
    index_name: str | None,
    admission: _Admission,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    lost_state = provenance["state"]["lost_state"]
    return {
        "schema_id": "obliteratus.conversion-manifest",
        "schema_version": "1.0.0",
        "manifest_id": artifact_id,
        "descriptor": {"schema_version": "1.0.0", "digest": descriptor_digest},
        "source_inventory_digest": _canonical_digest(source_records),
        "source_files": source_records,
        "adapter": {
            "id": "producer-neutral-fragments",
            "version": "1.0.0",
            "capability_digest": validation.manifest_digest,
            "producer": "already-normalized-input",
            "producer_version": "1.0.0",
        },
        "source_topology": dict(source_topology),
        "state": {
            "source_classification": provenance["state"]["classification"],
            "output_classification": "weights_only",
            "observed_scopes": provenance["state"]["observed_scopes"],
        },
        "dropped_scopes": [
            {"scope": scope, "reason": "Canonical Wave 2 output contains weights only."}
            for scope in lost_state
        ],
        "canonical_output": {
            "format": "hf_safetensors",
            "dtype_policy": "preserve_exact",
            "files": output_records,
            "hf_index": index_name,
            "logical_tensor_count": len(validation.logical_tensors),
            "logical_bytes": admission.logical_bytes,
        },
        "resource_usage": {
            "estimated_peak_ram_bytes": admission.estimated_peak_ram_bytes,
            "actual_peak_ram_bytes": None,
            "estimated_temp_bytes": admission.estimated_temp_bytes,
            "actual_temp_bytes": None,
        },
        "validation": {
            "coverage": True,
            "replicas": True,
            "ties": True,
            "hashes": True,
            "index": True,
            "safe_reload": True,
            "source_unchanged": True,
            "result": "passed",
        },
        "provenance": {
            "obliteratus_commit": provenance["obliteratus_commit"],
            "configuration_digest": provenance["configuration_digest"],
            "tokenizer_digest": (
                provenance["tokenizer"]["digest"] if provenance["tokenizer"] else None
            ),
            "base_model": {
                "identity": provenance["base_model"]["identity"] if provenance["base_model"] else None,
                "revision": provenance["base_model"]["revision"] if provenance["base_model"] else None,
                "digest": provenance["base_model"]["digest"] if provenance["base_model"] else None,
            },
            "transformation_log": provenance["transformations"],
            "unknowns": provenance["unknowns"],
        },
        "publication": {
            "staging_validated": True,
            "promoted": True,
            "atomic_strategy": "sibling-stage-fsync-replace",
            "rollback_result": "not_required",
        },
    }


def _verify_provenance(
    record: dict[str, Any],
    *,
    output_digests: tuple[str, ...],
    source_digests: tuple[str, ...],
    configuration_digest: str,
    source_topology: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        verified = verify_provenance_record(record)
    except (TypeError, ValueError) as error:
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="provenance_contract_invalid",
        ) from error
    if sorted(verified["output_digests"]) != sorted(set(output_digests)):
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="provenance_output_digest_mismatch",
        )
    if sorted(verified["input_digests"]) != sorted(set(source_digests)):
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="provenance_input_digest_mismatch",
        )
    if verified["configuration_digest"] != configuration_digest:
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="provenance_configuration_digest_mismatch",
        )
    try:
        topology_matches = dict(source_topology) == verified["source_topology"]
    except (TypeError, ValueError) as error:
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="provenance_source_topology_invalid",
        ) from error
    if not topology_matches:
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="provenance_source_topology_mismatch",
        )
    return verified


def _verify_json_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 << 20:
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="output_json_invalid",
            affected_refs=(path.name,),
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="output_json_invalid",
            affected_refs=(path.name,),
        ) from error
    if not isinstance(value, dict):
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="output_json_invalid",
            affected_refs=(path.name,),
        )
    return value


def _verify_staging(
    staging: Path,
    *,
    weight_map: dict[str, str],
    oracles: dict[str, _TensorOracle],
    expected_files: set[str],
    snapshots: tuple[_Snapshot, ...],
    source_snapshots: tuple[_Snapshot, ...],
    configuration_digest: str,
    descriptor_digest: str,
    validation_digest: str,
    artifact_id: str,
    limits: WriterLimits,
) -> None:
    actual_files = {path.name for path in staging.iterdir() if path.is_file() and not path.is_symlink()}
    if actual_files != expected_files or any(path.is_symlink() or not path.is_file() for path in staging.iterdir()):
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="output_file_set_mismatch",
        )
    actual_bytes = sum((staging / name).lstat().st_size for name in expected_files)
    if actual_bytes > limits.max_output_bytes or actual_bytes > limits.max_temp_bytes:
        raise CheckpointContractError(
            "DCI_ADMISSION_DENIED",
            detail="post_write_size_limit",
            affected_refs=(f"required:{actual_bytes}",),
        )
    loaded_names: set[str] = set()
    loaded_bytes = 0
    for shard_name in sorted(set(weight_map.values())):
        shard = load_file(staging / shard_name, device="cpu")
        for name, tensor in shard.items():
            if weight_map.get(name) != shard_name or name not in oracles:
                raise CheckpointContractError(
                    "DCI_VALIDATION_FAILED",
                    detail="output_index_mismatch",
                    affected_refs=(name,),
                )
            oracle = oracles[name]
            if (
                tuple(tensor.shape) != oracle.shape
                or str(tensor.dtype).removeprefix("torch.") != oracle.dtype
                or _tensor_digest(tensor) != oracle.sha256
            ):
                raise CheckpointContractError(
                    "DCI_VALIDATION_FAILED",
                    detail="output_tensor_mismatch",
                    affected_refs=(name,),
                )
            loaded_names.add(name)
            loaded_bytes += tensor.numel() * tensor.element_size()
    if loaded_names != set(weight_map) or loaded_names != set(oracles):
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="output_tensor_set_mismatch",
        )
    index_name = (
        "model.safetensors.index.json"
        if "model.safetensors.index.json" in expected_files
        else None
    )
    if index_name is not None:
        index = _verify_json_object(staging / index_name)
        if index != {
            "metadata": {"total_size": loaded_bytes},
            "weight_map": dict(sorted(weight_map.items())),
        }:
            raise CheckpointContractError(
                "DCI_VALIDATION_FAILED",
                detail="output_index_mismatch",
            )
    for name in ("config.json", "tokenizer_config.json"):
        _verify_json_object(staging / name)
    provenance = _verify_json_object(staging / "checkpoint-provenance.json")
    manifest = _verify_json_object(staging / "conversion-manifest.json")
    metadata = _verify_json_object(staging / "abliteration_metadata.json")
    evidence_files = {
        "checkpoint-provenance.json",
        "conversion-manifest.json",
        "abliteration_metadata.json",
    }
    output_records = [
        _output_record(staging / name)
        for name in sorted(expected_files - evidence_files)
    ]
    output_digests = tuple(record["sha256"] for record in output_records)
    verified_provenance = _verify_provenance(
        provenance,
        output_digests=output_digests,
        source_digests=tuple(snapshot.sha256 for snapshot in source_snapshots),
        configuration_digest=configuration_digest,
        source_topology=provenance.get("source_topology", {}),
    )
    canonical_output = manifest.get("canonical_output")
    adapter = manifest.get("adapter")
    descriptor = manifest.get("descriptor")
    if (
        not isinstance(canonical_output, dict)
        or not isinstance(adapter, dict)
        or not isinstance(descriptor, dict)
        or canonical_output.get("files") != output_records
        or canonical_output.get("hf_index") != index_name
        or adapter.get("capability_digest") != validation_digest
        or descriptor.get("digest") != descriptor_digest
        or manifest.get("source_files")
        != [snapshot.file_record() for snapshot in source_snapshots]
        or manifest.get("source_topology") != verified_provenance["source_topology"]
    ):
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="output_manifest_mismatch",
        )
    if not (
        provenance.get("artifact_id")
        == manifest.get("manifest_id")
        == metadata.get("artifact_id")
        == artifact_id
    ):
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="artifact_identity_mismatch",
        )
    for snapshot in snapshots:
        _revalidate_snapshot(snapshot)


def write_canonical_checkpoint(
    destination: Path | str,
    fragments: Sequence[TensorFragment],
    *,
    source_files: Sequence[VerifiedSourceFile],
    copies: Sequence[ImmutableCopy],
    descriptor_digest: str,
    source_topology: Mapping[str, Any],
    provenance_factory: Callable[[tuple[str, ...]], ProvenanceRecord],
    tie_policy: str | None = None,
    limits: WriterLimits | None = None,
) -> CanonicalWriteResult:
    """Write validated CPU fragments without invoking a producer reader or adapter."""
    _require_digest(descriptor_digest, "descriptor digest")
    active_limits = limits or WriterLimits()
    validation = validate_fragments(tuple(fragments))
    if any(logical.tie_group_id is not None for logical in validation.logical_tensors):
        if tie_policy != "duplicate_validated":
            raise CheckpointContractError(
                "DCI_VALIDATION_FAILED",
                detail="tie_policy_required",
                affected_refs=(
                    logical.logical_tensor_id
                    for logical in validation.logical_tensors
                    if logical.tie_group_id is not None
                ),
            )
    if not source_files:
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="source_inventory_empty",
        )
    source_paths = [item.relative_path for item in source_files]
    if len(set(source_paths)) != len(source_paths):
        raise ValueError("source relative paths must be unique")
    copy_paths = [item.relative_path for item in copies]
    if len(set(copy_paths)) != len(copy_paths):
        raise ValueError("copy output paths must be unique")
    if not {"config.json", "tokenizer_config.json"} <= set(copy_paths):
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="canonical_config_or_tokenizer_missing",
        )
    copy_kinds = {item.relative_path: item.kind for item in copies}
    if (
        copy_kinds["config.json"] != "configuration"
        or copy_kinds["tokenizer_config.json"] != "tokenizer"
    ):
        raise CheckpointContractError(
            "DCI_EVIDENCE_UNAVAILABLE",
            detail="canonical_config_or_tokenizer_kind_mismatch",
        )
    source_snapshots = tuple(
        sorted(
            (
                _snapshot(item.path, item.relative_path, item.expected_sha256)
                for item in source_files
            ),
            key=lambda snapshot: snapshot.relative_path,
        )
    )
    copy_snapshots = tuple(
        _snapshot(item.source_path, item.relative_path, item.expected_sha256) for item in copies
    )
    specs = _tensor_specs(validation)
    plan = _shard_plan(specs, active_limits.max_shard_bytes)
    output_path = Path(destination)
    try:
        destination_unsafe = (
            output_path.is_symlink()
            or output_path.absolute() != output_path.resolve(strict=False)
        )
    except OSError as error:
        raise CheckpointContractError(
            "DCI_SOURCE_BOUNDARY_VIOLATION",
            detail="destination_unresolvable",
            affected_refs=("destination",),
        ) from error
    if destination_unsafe:
        raise CheckpointContractError(
            "DCI_SOURCE_BOUNDARY_VIOLATION",
            detail="destination_symlink",
            affected_refs=("destination",),
        )
    admission = _admit(output_path, plan, copy_snapshots, active_limits)
    shard_names = (
        ("model.safetensors",)
        if len(plan) == 1
        else tuple(
            f"model-{index:05d}-of-{len(plan):05d}.safetensors"
            for index in range(1, len(plan) + 1)
        )
    )
    weight_map = {
        spec.name: shard_name
        for shard_name, shard in zip(shard_names, plan, strict=True)
        for spec in shard
    }
    oracles: dict[str, _TensorOracle] = {}
    index_name = "model.safetensors.index.json" if len(plan) > 1 else None
    artifact_id = ""
    manifest_digest = ""
    all_snapshots = (*source_snapshots, *copy_snapshots)

    def verify(staging: Path) -> None:
        expected = {
            *copy_paths,
            *shard_names,
            "checkpoint-provenance.json",
            "conversion-manifest.json",
            "abliteration_metadata.json",
        }
        if index_name is not None:
            expected.add(index_name)
        _verify_staging(
            staging,
            weight_map=weight_map,
            oracles=oracles,
            expected_files=expected,
            snapshots=all_snapshots,
            source_snapshots=source_snapshots,
            configuration_digest=next(
                snapshot.sha256
                for snapshot in copy_snapshots
                if snapshot.relative_path == "config.json"
            ),
            descriptor_digest=descriptor_digest,
            validation_digest=validation.manifest_digest,
            artifact_id=artifact_id,
            limits=active_limits,
        )

    try:
        with atomic_checkpoint_directory(output_path, validate=verify) as staging:
            try:
                for copy, snapshot in zip(copies, copy_snapshots, strict=True):
                    _copy_snapshot(snapshot, staging / copy.relative_path)
                for shard_name, shard in zip(shard_names, plan, strict=True):
                    tensors: dict[str, torch.Tensor] = {}
                    for spec in shard:
                        tensor = reconstruct_logical_tensor(validation, spec.logical_tensor_id)
                        tensors[spec.name] = tensor
                        oracles[spec.name] = _TensorOracle(
                            shape=tuple(tensor.shape),
                            dtype=str(tensor.dtype).removeprefix("torch."),
                            sha256=_tensor_digest(tensor),
                        )
                    _save_safetensors_file(tensors, staging / shard_name)
                del tensors
                if index_name is not None:
                    _write_json(
                        staging / index_name,
                        {
                            "metadata": {"total_size": admission.logical_bytes},
                            "weight_map": dict(sorted(weight_map.items())),
                        },
                    )
                output_names = [*copy_paths, *shard_names]
                if index_name is not None:
                    output_names.append(index_name)
                output_records = [
                    _output_record(staging / name) for name in sorted(output_names)
                ]
                output_digests = tuple(sorted(item["sha256"] for item in output_records))
                try:
                    provenance_record = provenance_factory(output_digests)
                    provenance = _verify_provenance(
                        provenance_record.to_dict(),
                        output_digests=output_digests,
                        source_digests=tuple(
                            snapshot.sha256 for snapshot in source_snapshots
                        ),
                        configuration_digest=next(
                            snapshot.sha256
                            for snapshot in copy_snapshots
                            if snapshot.relative_path == "config.json"
                        ),
                        source_topology=source_topology,
                    )
                except CheckpointContractError:
                    raise
                except Exception as error:
                    raise CheckpointContractError(
                        "DCI_EVIDENCE_UNAVAILABLE",
                        detail="provenance_factory_failed",
                    ) from error
                artifact_id = provenance["artifact_id"]
                if getattr(provenance_record, "artifact_id", None) != artifact_id:
                    raise CheckpointContractError(
                        "DCI_EVIDENCE_UNAVAILABLE",
                        detail="provenance_artifact_identity_mismatch",
                    )
                _write_json(staging / "checkpoint-provenance.json", provenance)
                source_records = [snapshot.file_record() for snapshot in source_snapshots]
                manifest = _manifest(
                    artifact_id=artifact_id,
                    descriptor_digest=descriptor_digest,
                    source_records=source_records,
                    source_topology=provenance["source_topology"],
                    validation=validation,
                    output_records=output_records,
                    index_name=index_name,
                    admission=admission,
                    provenance=provenance,
                )
                _write_json(staging / "conversion-manifest.json", manifest)
                manifest_digest = _file_digest(staging / "conversion-manifest.json")
                _write_json(
                    staging / "abliteration_metadata.json",
                    {
                        "schema_version": 2,
                        "artifact_id": artifact_id,
                        "checkpoint_provenance": "checkpoint-provenance.json",
                        "conversion_manifest": "conversion-manifest.json",
                        "state_classification": "weights_only",
                        "lost_state": provenance["state"]["lost_state"],
                    },
                )
            except CheckpointContractError:
                raise
            except Exception as error:
                raise CheckpointContractError(
                    "DCI_MATERIALIZE_FAILED",
                    detail="canonical_write_failed",
                ) from error
    except CheckpointContractError:
        raise
    except Exception as error:
        raise CheckpointContractError(
            "DCI_PROMOTION_FAILED",
            detail="canonical_promotion_failed",
        ) from error
    return CanonicalWriteResult(
        artifact_id=artifact_id,
        output_path=output_path.resolve(),
        weight_files=shard_names,
        manifest_digest=manifest_digest,
    )
