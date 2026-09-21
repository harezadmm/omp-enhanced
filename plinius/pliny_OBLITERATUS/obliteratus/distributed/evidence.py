"""Allowlist-built evidence for distributed preflight attempts."""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
from dataclasses import asdict, dataclass
from pathlib import Path

from obliteratus.distributed.contracts import (
    MAX_CONSENSUS_BYTES,
    ContractError,
    StageMessage,
)


MAX_EVIDENCE_BYTES = 64 * 1024
_RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ERROR_CODES = frozenset(
    {
        "LMS_ATOMIC_PROMOTION_UNAVAILABLE",
        "LMS_ATTEMPT_CANCELLED",
        "LMS_ATTEMPT_IDENTITY_CONFLICT",
        "LMS_CLEANUP_INCOMPLETE",
        "LMS_CLOCK_PROFILE_MISMATCH",
        "LMS_COLLECTIVE_FAILED",
        "LMS_CONSENSUS_RECORD_INVALID",
        "LMS_DIAGNOSTIC_REDACTION_FAILED",
        "LMS_DISTRIBUTED_INTENT_REQUIRED",
        "LMS_ELASTICITY_FORBIDDEN",
        "LMS_EVIDENCE_SCOPE_MISMATCH",
        "LMS_EVIDENCE_UNAVAILABLE",
        "LMS_FORBIDDEN_RUNTIME_CAPABILITY",
        "LMS_IDENTITY_MISMATCH",
        "LMS_LAUNCH_IDENTITY_INVALID",
        "LMS_LIFECYCLE_INVALID",
        "LMS_MEMBERSHIP_INVALID",
        "LMS_MEMBERSHIP_TIMEOUT",
        "LMS_NETWORK_PROFILE_DENIED",
        "LMS_RANK_DEVICE_CONFLICT",
        "LMS_RESOURCE_ADMISSION_DENIED",
        "LMS_RUNTIME_PROFILE_MISMATCH",
        "LMS_SECRET_INPUT_REJECTED",
        "LMS_SECURITY_BASELINE_REVOKED",
        "LMS_SOURCE_BOUNDARY_VIOLATION",
        "LMS_SOURCE_CHANGED",
        "LMS_STAGE_TIMEOUT",
        "LMS_STORAGE_PROFILE_MISMATCH",
        "LMS_TOPOLOGY_UNSUPPORTED",
        "LMS_TRANSPORT_BOUNDARY_UNSATISFIED",
    }
)


@dataclass(frozen=True)
class PreflightEvidence:
    """A bounded public result containing no raw operational values."""

    schema_version: int
    result: str
    run_id: str
    config_digest: str
    world_size: int
    accepted_ranks: int
    evidence_tier: str
    identity_digest: str | None
    error_code: str | None

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ContractError("evidence schema_version must be 1")
        if self.result not in {"preflighted", "failed", "quarantined"}:
            raise ContractError("evidence result is invalid")
        if _RUN_ID_RE.fullmatch(self.run_id) is None:
            raise ContractError("evidence run_id is invalid")
        if _DIGEST_RE.fullmatch(self.config_digest) is None:
            raise ContractError("evidence config_digest is invalid")
        if isinstance(self.world_size, bool) or not 2 <= self.world_size <= 4096:
            raise ContractError("evidence world_size is invalid")
        if isinstance(self.accepted_ranks, bool) or not 0 <= self.accepted_ranks <= self.world_size:
            raise ContractError("evidence accepted_ranks is invalid")
        if self.evidence_tier not in {"protocol_cpu", "candidate_preflight"}:
            raise ContractError("evidence tier is invalid")
        if self.identity_digest is not None and _DIGEST_RE.fullmatch(self.identity_digest) is None:
            raise ContractError("evidence identity_digest is invalid")
        if self.error_code is not None and self.error_code not in _ERROR_CODES:
            raise ContractError("evidence error_code is invalid")
        if self.result == "preflighted":
            if self.accepted_ranks != self.world_size or self.identity_digest is None:
                raise ContractError("successful evidence requires the complete accepted world")
            if self.error_code is not None:
                raise ContractError("successful evidence cannot contain an error")
        elif self.error_code is None:
            raise ContractError("unsuccessful evidence requires a stable error code")

    @classmethod
    def success(
        cls,
        *,
        run_id: str,
        config_digest: str,
        world_size: int,
        evidence_tier: str,
        identity_digest: str,
    ) -> "PreflightEvidence":
        return cls(
            1,
            "preflighted",
            run_id,
            config_digest,
            world_size,
            world_size,
            evidence_tier,
            identity_digest,
            None,
        )

    @classmethod
    def failure(
        cls,
        *,
        run_id: str,
        config_digest: str,
        code: str,
        world_size: int,
        evidence_tier: str,
        detail: str | None = None,
    ) -> "PreflightEvidence":
        del detail  # raw exception and operator context never enter retained evidence
        result = "quarantined" if code == "LMS_CLEANUP_INCOMPLETE" else "failed"
        return cls(1, result, run_id, config_digest, world_size, 0, evidence_tier, None, code)

    def to_bytes(self) -> bytes:
        encoded = (json.dumps(asdict(self), sort_keys=True, separators=(",", ":")) + "\n").encode()
        if len(encoded) > MAX_EVIDENCE_BYTES:
            raise ContractError("preflight evidence exceeds its byte bound")
        return encoded

    @classmethod
    def from_bytes(cls, payload: bytes) -> "PreflightEvidence":
        """Decode only the one canonical, closed evidence representation."""

        if not 1 <= len(payload) <= MAX_EVIDENCE_BYTES or not payload.endswith(b"\n"):
            raise ContractError("preflight evidence has an invalid byte envelope")

        def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ContractError("preflight evidence contains a duplicate field")
                result[key] = value
            return result

        try:
            value = json.loads(payload[:-1].decode("utf-8"), object_pairs_hook=unique_object)
        except ContractError:
            raise
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("preflight evidence is not strict UTF-8 JSON") from exc
        if not isinstance(value, dict) or set(value) != set(cls.__dataclass_fields__):
            raise ContractError("preflight evidence fields do not match the closed schema")
        result = cls(**value)
        if payload != result.to_bytes():
            raise ContractError("preflight evidence is not canonical")
        return result


def _open_private_parent(target: Path) -> int:
    """Open an absolute parent through descriptor-relative, no-symlink traversal."""

    if not target.is_absolute() or target.name in {"", ".", ".."}:
        raise ContractError("evidence target must be an absolute file path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    try:
        for component in target.parent.parts[1:]:
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        metadata = os.fstat(descriptor)
        effective_uid = getattr(os, "geteuid", lambda: metadata.st_uid)()
        if metadata.st_uid != effective_uid or metadata.st_mode & 0o077:
            raise ContractError("evidence parent must be private and owned by the worker")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _write_private_payload(path: str | Path, payload: bytes) -> None:
    """Atomically create one bounded private record without following links."""

    target = Path(path)
    temporary = f".{target.name}.tmp.{os.getpid()}.{secrets.token_hex(8)}"
    parent_descriptor: int | None = None
    descriptor: int | None = None
    try:
        parent_descriptor = _open_private_parent(target)
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_descriptor,
        )
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise ContractError("evidence write did not make progress")
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(
            temporary,
            target.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        os.unlink(temporary, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
    except FileExistsError as exc:
        raise ContractError("evidence target already exists") from exc
    except OSError as exc:
        raise ContractError("evidence sink is unavailable") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            try:
                os.unlink(temporary, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
            os.close(parent_descriptor)


def _read_private_payload(path: str | Path, *, maximum: int) -> bytes:
    """Read one stable bounded private record without pathname races."""

    target = Path(path)
    parent_descriptor: int | None = None
    descriptor: int | None = None
    try:
        parent_descriptor = _open_private_parent(target)
        descriptor = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_descriptor)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not 1 <= before.st_size <= maximum
            or before.st_mode & 0o077
        ):
            raise ContractError("private record file is not private and regular")
        payload = os.read(descriptor, maximum + 1)
        after = os.fstat(descriptor)
        if len(payload) != before.st_size or (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ContractError("private record changed while it was read")
        return payload
    except Exception:
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)


def write_evidence(path: str | Path, evidence: PreflightEvidence) -> None:
    """Atomically create private evidence without following links or overwriting."""

    _write_private_payload(path, evidence.to_bytes())


def read_evidence(path: str | Path) -> PreflightEvidence:
    """Read and validate one private evidence record without pathname races."""

    return PreflightEvidence.from_bytes(_read_private_payload(path, maximum=MAX_EVIDENCE_BYTES))


def write_stage_message(path: str | Path, message: StageMessage) -> None:
    """Persist one private lifecycle receipt using a non-evidence schema."""

    _write_private_payload(path, message.to_bytes())


def read_stage_message(path: str | Path) -> StageMessage:
    """Read one canonical private lifecycle receipt."""

    return StageMessage.from_bytes(_read_private_payload(path, maximum=MAX_CONSENSUS_BYTES))
