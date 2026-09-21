"""Pure, bounded records for distributed runtime identity and lifecycle."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any


MAX_CONSENSUS_BYTES = 64 * 1024
MAX_TEXT_BYTES = 256
MAX_WORLD_SIZE = 4096
MAX_RECORD_DEPTH = 16
MAX_RECORD_ITEMS = 4096
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_ERROR_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class ContractError(ValueError):
    """A distributed record violates a bounded, fail-closed contract."""


class RuntimeContractError(ContractError):
    """A sanitized runtime refusal with one stable degraded-mode code."""

    def __init__(self, code: str, message: str) -> None:
        _require_text(code, "error_code", pattern=_ERROR_RE)
        super().__init__(message)
        self.code = code


class RuntimeStage(str, Enum):
    CREATED = "created"
    PREFLIGHTED = "preflighted"
    LOADED = "loaded"
    PROBED = "probed"
    DISTILLED = "distilled"
    PREPARED = "prepared"
    MUTATING = "mutating"
    VERIFIED = "verified"
    STAGED = "staged"
    PUBLISHED = "published"
    ABORTING = "aborting"
    ABORTED = "aborted"
    QUARANTINED = "quarantined"


class Vote(str, Enum):
    PREPARED = "prepared"
    COMMITTED = "committed"
    ABORT = "abort"


class PlacementKind(str, Enum):
    COLUMN_WISE = "column_wise"
    ROW_WISE = "row_wise"
    REPLICATED = "replicated"


_SUPPORTED_DTYPES = frozenset({"float16", "bfloat16", "float32", "float64"})


_ALLOWED_TRANSITIONS: dict[RuntimeStage, frozenset[RuntimeStage]] = {
    RuntimeStage.CREATED: frozenset({RuntimeStage.PREFLIGHTED, RuntimeStage.ABORTING}),
    RuntimeStage.PREFLIGHTED: frozenset({RuntimeStage.LOADED, RuntimeStage.ABORTING}),
    RuntimeStage.LOADED: frozenset({RuntimeStage.PROBED, RuntimeStage.ABORTING}),
    RuntimeStage.PROBED: frozenset({RuntimeStage.DISTILLED, RuntimeStage.ABORTING}),
    RuntimeStage.DISTILLED: frozenset({RuntimeStage.PREPARED, RuntimeStage.ABORTING}),
    RuntimeStage.PREPARED: frozenset({RuntimeStage.MUTATING, RuntimeStage.ABORTING}),
    RuntimeStage.MUTATING: frozenset({RuntimeStage.VERIFIED, RuntimeStage.ABORTING}),
    RuntimeStage.VERIFIED: frozenset({RuntimeStage.STAGED, RuntimeStage.ABORTING}),
    RuntimeStage.STAGED: frozenset({RuntimeStage.PUBLISHED, RuntimeStage.ABORTING}),
    RuntimeStage.ABORTING: frozenset({RuntimeStage.ABORTED, RuntimeStage.QUARANTINED}),
    RuntimeStage.PUBLISHED: frozenset(),
    RuntimeStage.ABORTED: frozenset(),
    RuntimeStage.QUARANTINED: frozenset(),
}


def _require_int(value: object, name: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ContractError(f"{name} must be between {minimum} and {maximum}")
    return value


def _require_text(value: object, name: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} must be non-empty text")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ContractError(f"{name} must be valid UTF-8") from exc
    if len(encoded) > MAX_TEXT_BYTES:
        raise ContractError(f"{name} exceeds {MAX_TEXT_BYTES} UTF-8 bytes")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ContractError(f"{name} has an invalid format")
    return value


def _require_digest(value: object, name: str) -> str:
    return _require_text(value, name, pattern=_DIGEST_RE)


@dataclass(frozen=True)
class RunIdentity:
    """Immutable identity shared by every rank in one non-resumable attempt."""

    run_id: str
    config_digest: str
    source_digest: str
    model_digest: str
    tokenizer_digest: str
    commit_sha: str
    world_size: int

    def __post_init__(self) -> None:
        _require_text(self.run_id, "run_id", pattern=_RUN_ID_RE)
        _require_digest(self.config_digest, "config_digest")
        _require_digest(self.source_digest, "source_digest")
        _require_digest(self.model_digest, "model_digest")
        _require_digest(self.tokenizer_digest, "tokenizer_digest")
        _require_text(self.commit_sha, "commit_sha", pattern=_COMMIT_RE)
        _require_int(self.world_size, "world_size", minimum=2, maximum=MAX_WORLD_SIZE)


@dataclass(frozen=True)
class RankInventory:
    """Redaction-safe rank, host, device, software, and storage identity."""

    rank: int
    local_rank: int
    world_size: int
    host_digest: str
    device_digest: str
    device_kind: str
    total_memory_bytes: int
    free_memory_bytes: int
    software_digest: str
    storage_digest: str

    def __post_init__(self) -> None:
        _require_int(self.world_size, "world_size", minimum=2, maximum=MAX_WORLD_SIZE)
        _require_int(self.rank, "rank", minimum=0, maximum=self.world_size - 1)
        _require_int(self.local_rank, "local_rank", minimum=0, maximum=self.world_size - 1)
        _require_digest(self.host_digest, "host_digest")
        _require_digest(self.device_digest, "device_digest")
        if self.device_kind not in {"cpu", "cuda"}:
            raise ContractError("device_kind must be 'cpu' or 'cuda'")
        total = _require_int(
            self.total_memory_bytes,
            "total_memory_bytes",
            minimum=1,
            maximum=2**63 - 1,
        )
        free = _require_int(
            self.free_memory_bytes,
            "free_memory_bytes",
            minimum=0,
            maximum=2**63 - 1,
        )
        if free > total:
            raise ContractError("free_memory_bytes cannot exceed total_memory_bytes")
        _require_digest(self.software_digest, "software_digest")
        _require_digest(self.storage_digest, "storage_digest")


@dataclass(frozen=True)
class TopologyPlan:
    """Fixed process-group topology accepted before model allocation."""

    world_size: int
    coordinator_rank: int
    backend: str
    placement_plan_digest: str

    def __post_init__(self) -> None:
        _require_int(self.world_size, "world_size", minimum=2, maximum=MAX_WORLD_SIZE)
        _require_int(
            self.coordinator_rank,
            "coordinator_rank",
            minimum=0,
            maximum=self.world_size - 1,
        )
        if self.backend not in {"gloo", "nccl"}:
            raise ContractError("backend must be 'gloo' or 'nccl'")
        _require_digest(self.placement_plan_digest, "placement_plan_digest")


@dataclass(frozen=True)
class LogicalPlacement:
    """One exact, even 2-D parameter shard placement for the prototype."""

    logical_name: str
    global_shape: tuple[int, int]
    dtype: str
    kind: PlacementKind
    rank: int
    world_size: int
    direction_axis: int
    shard_dim: int | None = None
    shard_start: int = 0
    shard_end: int = 0

    def __post_init__(self) -> None:
        _require_text(self.logical_name, "logical_name", pattern=_NAME_RE)
        if not isinstance(self.global_shape, tuple) or len(self.global_shape) != 2:
            raise ContractError("global_shape must be a positive two-dimensional integer tuple")
        for size in self.global_shape:
            if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 2**63 - 1:
                raise ContractError("global_shape must be a positive two-dimensional integer tuple")
        _require_text(self.dtype, "dtype", pattern=_NAME_RE)
        if self.dtype not in _SUPPORTED_DTYPES:
            raise ContractError("dtype is not supported by the distributed semantic oracle")
        if not isinstance(self.kind, PlacementKind):
            raise ContractError("kind must be a PlacementKind")
        _require_int(self.world_size, "world_size", minimum=2, maximum=MAX_WORLD_SIZE)
        _require_int(self.rank, "rank", minimum=0, maximum=self.world_size - 1)
        _require_int(self.direction_axis, "direction_axis", minimum=0, maximum=1)

        if self.kind is PlacementKind.REPLICATED:
            if self.shard_dim is not None or self.shard_start != 0 or self.shard_end != 0:
                raise ContractError("replicated placement cannot declare a shard interval")
            return

        expected_dim = 0 if self.kind is PlacementKind.COLUMN_WISE else 1
        if self.shard_dim != expected_dim:
            raise ContractError(f"{self.kind.value} placement requires shard_dim={expected_dim}")
        extent = self.global_shape[expected_dim]
        if extent % self.world_size != 0:
            raise ContractError("prototype placements require equal shard extents")
        shard_size = extent // self.world_size
        expected_start = self.rank * shard_size
        expected_end = expected_start + shard_size
        if (self.shard_start, self.shard_end) != (expected_start, expected_end):
            raise ContractError("shard interval does not match the fixed rank partition")

    @property
    def local_shape(self) -> tuple[int, int]:
        if self.kind is PlacementKind.REPLICATED:
            return self.global_shape
        result = list(self.global_shape)
        assert self.shard_dim is not None
        result[self.shard_dim] = self.shard_end - self.shard_start
        return result[0], result[1]


@dataclass(frozen=True)
class StageMessage:
    """Sequenced lifecycle evidence emitted by one rank."""

    run_id: str
    identity_digest: str
    rank: int
    sequence: int
    stage: RuntimeStage
    vote: Vote | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.run_id, "run_id", pattern=_RUN_ID_RE)
        _require_digest(self.identity_digest, "identity_digest")
        _require_int(self.rank, "rank", minimum=0, maximum=MAX_WORLD_SIZE - 1)
        _require_int(self.sequence, "sequence", minimum=0, maximum=2**63 - 1)
        if not isinstance(self.stage, RuntimeStage):
            raise ContractError("stage must be a RuntimeStage")
        if self.vote is not None and not isinstance(self.vote, Vote):
            raise ContractError("vote must be a Vote")
        if self.error_code is not None:
            _require_text(self.error_code, "error_code", pattern=_ERROR_RE)
        if self.vote is Vote.ABORT and self.error_code is None:
            raise ContractError("an abort vote requires an error_code")
        if self.error_code is not None and self.vote is not Vote.ABORT:
            raise ContractError("error_code is valid only with an abort vote")

    def to_bytes(self) -> bytes:
        """Encode one lifecycle record in its sole canonical representation."""

        return canonical_record(self)

    @classmethod
    def from_bytes(cls, payload: bytes) -> "StageMessage":
        """Decode a closed lifecycle record and reject alternate JSON."""

        def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ContractError("lifecycle message contains a duplicate field")
                result[key] = value
            return result

        try:
            value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
            if not isinstance(value, dict) or set(value) != set(cls.__dataclass_fields__):
                raise ContractError("lifecycle message fields do not match the closed schema")
            converted = dict(value)
            converted["stage"] = RuntimeStage(converted["stage"])
            if converted["vote"] is not None:
                converted["vote"] = Vote(converted["vote"])
            result = cls(**converted)
        except ContractError:
            raise
        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ContractError("lifecycle message must be canonical UTF-8 JSON") from exc
        if payload != result.to_bytes():
            raise ContractError("lifecycle message is not canonical")
        return result


def advance_stage(current: RuntimeStage, requested: RuntimeStage) -> RuntimeStage:
    """Validate one lifecycle transition without performing side effects."""
    if not isinstance(current, RuntimeStage) or not isinstance(requested, RuntimeStage):
        raise ContractError("current and requested stages must be RuntimeStage values")
    if requested not in _ALLOWED_TRANSITIONS[current]:
        raise ContractError(
            f"invalid distributed stage transition: {current.value} -> {requested.value}"
        )
    return requested


def _json_value(
    value: Any,
    *,
    depth: int,
    active: set[int],
    item_count: list[int],
    max_bytes: int,
) -> Any:
    if depth > MAX_RECORD_DEPTH:
        raise ContractError(f"canonical record exceeds nesting depth {MAX_RECORD_DEPTH}")
    item_count[0] += 1
    if item_count[0] > MAX_RECORD_ITEMS:
        raise ContractError(f"canonical record exceeds {MAX_RECORD_ITEMS} items")
    if isinstance(value, Enum):
        return _json_value(
            value.value,
            depth=depth + 1,
            active=active,
            item_count=item_count,
            max_bytes=max_bytes,
        )
    if is_dataclass(value) and not isinstance(value, type):
        identity = id(value)
        if identity in active:
            raise ContractError("canonical record contains a reference cycle")
        active.add(identity)
        try:
            return {
                field.name: _json_value(
                    getattr(value, field.name),
                    depth=depth + 1,
                    active=active,
                    item_count=item_count,
                    max_bytes=max_bytes,
                )
                for field in fields(value)
            }
        finally:
            active.remove(identity)
    if isinstance(value, dict):
        identity = id(value)
        if identity in active:
            raise ContractError("canonical record contains a reference cycle")
        active.add(identity)
        converted: dict[str, Any] = {}
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ContractError("canonical record keys must be strings")
                if len(key.encode("utf-8", errors="strict")) > max_bytes:
                    raise ContractError(f"canonical record exceeds {max_bytes} bytes")
                converted[key] = _json_value(
                    item,
                    depth=depth + 1,
                    active=active,
                    item_count=item_count,
                    max_bytes=max_bytes,
                )
            return converted
        except UnicodeError as exc:
            raise ContractError("canonical record key must be valid UTF-8") from exc
        finally:
            active.remove(identity)
    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in active:
            raise ContractError("canonical record contains a reference cycle")
        active.add(identity)
        try:
            return [
                _json_value(
                    item,
                    depth=depth + 1,
                    active=active,
                    item_count=item_count,
                    max_bytes=max_bytes,
                )
                for item in value
            ]
        finally:
            active.remove(identity)
    if isinstance(value, str):
        try:
            if len(value.encode("utf-8", errors="strict")) > max_bytes:
                raise ContractError(f"canonical record exceeds {max_bytes} bytes")
        except UnicodeError as exc:
            raise ContractError("canonical record string must be valid UTF-8") from exc
        return value
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -(2**63) <= value <= 2**63 - 1:
            raise ContractError("canonical record integer exceeds the signed 64-bit bound")
        return value
    raise ContractError(f"canonical record contains unsupported type {type(value).__name__}")


def canonical_record(value: Any, *, max_bytes: int = MAX_CONSENSUS_BYTES) -> bytes:
    """Serialize a record deterministically, rejecting floats and oversized data."""
    _require_int(max_bytes, "max_bytes", minimum=1, maximum=MAX_CONSENSUS_BYTES)
    try:
        encoded = json.dumps(
            _json_value(
                value,
                depth=0,
                active=set(),
                item_count=[0],
                max_bytes=max_bytes,
            ),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", errors="strict")
    except ContractError:
        raise
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("record is not canonical JSON") from exc
    if len(encoded) > max_bytes:
        raise ContractError(f"canonical record exceeds {max_bytes} bytes")
    return encoded


def contract_digest(value: Any) -> str:
    """Return the SHA-256 identity of one canonical bounded record."""
    return hashlib.sha256(canonical_record(value)).hexdigest()


def validate_inventory_consensus(
    identity: RunIdentity,
    inventories: tuple[RankInventory, ...],
) -> None:
    """Validate a complete homogeneous fixed-world inventory."""
    if not isinstance(identity, RunIdentity):
        raise ContractError("identity must be a RunIdentity")
    if not isinstance(inventories, tuple) or len(inventories) != identity.world_size:
        raise ContractError("inventory must contain exactly one record per rank")
    if any(not isinstance(item, RankInventory) for item in inventories):
        raise ContractError("inventory contains an invalid rank record")
    if {item.rank for item in inventories} != set(range(identity.world_size)):
        raise ContractError("inventory ranks do not exactly cover the fixed world")
    if any(item.world_size != identity.world_size for item in inventories):
        raise ContractError("inventory world_size disagrees with the run identity")
    devices = {(item.host_digest, item.device_digest) for item in inventories}
    if len(devices) != identity.world_size:
        raise ContractError("each rank must own a unique host/device pair")
    host_local_ranks = {(item.host_digest, item.local_rank) for item in inventories}
    if len(host_local_ranks) != identity.world_size:
        raise ContractError("local ranks must be unique within each host")
    if len({item.software_digest for item in inventories}) != 1:
        raise ContractError("rank software identities disagree")
    if len({item.storage_digest for item in inventories}) != 1:
        raise ContractError("rank storage identities disagree")
