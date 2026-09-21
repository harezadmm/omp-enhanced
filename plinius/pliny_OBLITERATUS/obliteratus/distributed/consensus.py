"""Bounded Gloo consensus primitives for the CPU protocol test lane."""

from __future__ import annotations

from collections.abc import Sequence

import torch
import torch.distributed as dist

from obliteratus.distributed.contracts import (
    MAX_CONSENSUS_BYTES,
    MAX_WORLD_SIZE,
    ContractError,
    canonical_record,
    contract_digest,
)


_LENGTH_BYTES = 4


def encode_frame(payload: bytes, *, capacity: int = MAX_CONSENSUS_BYTES) -> torch.Tensor:
    """Encode bytes into one fixed-size uint8 frame with zero padding."""
    if isinstance(capacity, bool) or not isinstance(capacity, int) or not 1 <= capacity <= MAX_CONSENSUS_BYTES:
        raise ContractError(f"capacity must be between 1 and {MAX_CONSENSUS_BYTES}")
    if not isinstance(payload, bytes):
        raise ContractError("frame payload must be bytes")
    if len(payload) > capacity:
        raise ContractError(f"frame payload exceeds {capacity} bytes")
    frame = bytearray(_LENGTH_BYTES + capacity)
    frame[:_LENGTH_BYTES] = len(payload).to_bytes(_LENGTH_BYTES, byteorder="big")
    frame[_LENGTH_BYTES : _LENGTH_BYTES + len(payload)] = payload
    return torch.frombuffer(frame, dtype=torch.uint8).clone()


def decode_frame(frame: torch.Tensor) -> bytes:
    """Decode a canonical fixed-size frame and reject non-zero padding."""
    if not isinstance(frame, torch.Tensor) or frame.dtype != torch.uint8 or frame.ndim != 1:
        raise ContractError("frame must be a one-dimensional uint8 tensor")
    capacity = frame.numel() - _LENGTH_BYTES
    if not 1 <= capacity <= MAX_CONSENSUS_BYTES:
        raise ContractError("frame has an invalid capacity")
    raw = bytes(frame.detach().cpu().tolist())
    size = int.from_bytes(raw[:_LENGTH_BYTES], byteorder="big")
    if size > capacity:
        raise ContractError("frame length exceeds its capacity")
    if any(raw[_LENGTH_BYTES + size :]):
        raise ContractError("frame padding must be zero")
    return raw[_LENGTH_BYTES : _LENGTH_BYTES + size]


def _require_gloo(group: dist.ProcessGroup | None) -> tuple[int, int]:
    if not dist.is_available() or not dist.is_initialized():
        raise ContractError("a Gloo process group must be initialized")
    backend = str(dist.get_backend(group)).lower()
    if backend != "gloo":
        raise ContractError("CPU protocol consensus requires the Gloo backend")
    rank, world_size = dist.get_rank(group), dist.get_world_size(group)
    if not 2 <= world_size <= MAX_WORLD_SIZE:
        raise ContractError(f"Gloo world_size must be between 2 and {MAX_WORLD_SIZE}")
    return rank, world_size


def gloo_all_gather_records(
    record: object,
    *,
    group: dist.ProcessGroup | None = None,
    capacity: int = MAX_CONSENSUS_BYTES,
) -> tuple[bytes, ...]:
    """Gather bounded canonical records without Python object collectives."""
    payload = canonical_record(record, max_bytes=capacity)
    _rank, world_size = _require_gloo(group)
    frame = encode_frame(payload, capacity=capacity)
    gathered = [torch.zeros_like(frame) for _ in range(world_size)]
    dist.all_gather(gathered, frame, group=group)
    return tuple(decode_frame(item) for item in gathered)


def require_consensus_digest(
    digest: str,
    *,
    group: dist.ProcessGroup | None = None,
) -> str:
    """Require every rank to supply the same lowercase SHA-256 digest."""
    if not isinstance(digest, str) or len(digest) != 64:
        raise ContractError("digest must be 64 lowercase hexadecimal characters")
    try:
        payload = bytes.fromhex(digest)
    except ValueError as exc:
        raise ContractError("digest must be 64 lowercase hexadecimal characters") from exc
    if digest != digest.lower() or payload.hex() != digest:
        raise ContractError("digest must be 64 lowercase hexadecimal characters")
    _rank, world_size = _require_gloo(group)
    local = torch.tensor(tuple(payload), dtype=torch.uint8)
    gathered = [torch.zeros_like(local) for _ in range(world_size)]
    dist.all_gather(gathered, local, group=group)
    if any(not torch.equal(local, item) for item in gathered):
        raise ContractError("rank digests disagree")
    return digest


def require_record_consensus(
    record: object,
    *,
    group: dist.ProcessGroup | None = None,
) -> str:
    """Require every rank to present the same bounded canonical record."""
    return require_consensus_digest(contract_digest(record), group=group)


def unanimous_vote(
    sequence: int,
    accepted: bool,
    *,
    group: dist.ProcessGroup | None = None,
) -> bool:
    """Return true only when every rank votes yes for the same sequence."""
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ContractError("vote sequence must be a non-negative integer")
    if not isinstance(accepted, bool):
        raise ContractError("accepted must be a boolean")
    _rank, world_size = _require_gloo(group)
    local = torch.tensor((sequence, int(accepted)), dtype=torch.int64)
    gathered = [torch.zeros_like(local) for _ in range(world_size)]
    dist.all_gather(gathered, local, group=group)
    if any(int(item[0]) != sequence for item in gathered):
        raise ContractError("rank vote sequences disagree")
    return all(bool(int(item[1])) for item in gathered)


def assert_rank_order(records: Sequence[object], *, world_size: int) -> None:
    """Reject missing, duplicate, or reordered rank-bearing records."""
    if len(records) != world_size:
        raise ContractError("record count does not match world_size")
    ranks = [getattr(record, "rank", None) for record in records]
    if ranks != list(range(world_size)):
        raise ContractError("records must appear once in global-rank order")
