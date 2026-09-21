"""Producer-neutral tensor fragment validation and bounded reconstruction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

import torch

from obliteratus.checkpoint_errors import CheckpointContractError


_INT64_MAX = (1 << 63) - 1
_MAX_IDENTIFIER_BYTES = 4096
_ROLES = frozenset({"parameter", "persistent_buffer"})
_PADDING_SEMANTICS = frozenset({"none", "producer_declared", "model_mapping_declared"})
_SAFE_DTYPES = frozenset(
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
        "float16",
        "bfloat16",
        "float32",
        "float64",
        "float8_e4m3fn",
        "float8_e5m2",
        "complex64",
        "complex128",
    }
)


@dataclass(frozen=True)
class FragmentLimits:
    """Explicit CPU-safe limits applied before combinatorial validation work."""

    max_fragments: int = 4096
    max_dimensions: int = 32
    max_elements_per_tensor: int = _INT64_MAX
    max_overlap_checks: int = 2_000_000

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class Padding:
    """Declared non-logical values surrounding a fragment payload."""

    before: tuple[int, ...]
    after: tuple[int, ...]
    semantic: Literal["none", "producer_declared", "model_mapping_declared"] = "none"

    @classmethod
    def zeros(cls, dimensions: int) -> Padding:
        return cls(before=(0,) * dimensions, after=(0,) * dimensions)


@dataclass(frozen=True)
class Replica:
    """An explicit replica declaration; absent grouping means unique content."""

    group_id: str | None
    member_index: int
    member_count: int

    @classmethod
    def unique(cls) -> Replica:
        return cls(group_id=None, member_index=0, member_count=1)


@dataclass(frozen=True)
class TensorFragment:
    """Typed logical geometry plus an optional already-normalized CPU payload."""

    fragment_id: str
    component_id: str
    fqn: str
    role: Literal["parameter", "persistent_buffer"]
    dtype: str
    global_shape: tuple[int, ...]
    local_shape: tuple[int, ...]
    element_offset: tuple[int, ...]
    element_extent: tuple[int, ...]
    padding: Padding
    shard_file_id: str
    shard_digest_ref: str
    fragment_digest: str | None
    replica: Replica
    partition_axes: tuple[int, ...]
    logical_tensor_id: str
    tie_group_id: str | None
    shared_storage_id: str | None
    topology_coordinates: tuple[tuple[str, int], ...]
    evidence_refs: tuple[str, ...]
    payload: torch.Tensor | None = None

    def manifest_record(self) -> dict[str, object]:
        """Return deterministic neutral metadata; tensor bytes are never embedded."""
        return {
            "fragment_id": self.fragment_id,
            "component_id": self.component_id,
            "fqn": self.fqn,
            "role": self.role,
            "dtype": self.dtype,
            "global_shape": list(self.global_shape),
            "local_shape": list(self.local_shape),
            "element_offset": list(self.element_offset),
            "element_extent": list(self.element_extent),
            "padding": {
                "before": list(self.padding.before),
                "after": list(self.padding.after),
                "semantic": self.padding.semantic,
            },
            "shard_file_id": self.shard_file_id,
            "shard_digest_ref": self.shard_digest_ref,
            "fragment_digest": self.fragment_digest,
            "replica": {
                "group_id": self.replica.group_id,
                "member_index": self.replica.member_index,
                "member_count": self.replica.member_count,
            },
            "partition_axes": list(self.partition_axes),
            "logical_tensor_id": self.logical_tensor_id,
            "tie_group_id": self.tie_group_id,
            "shared_storage_id": self.shared_storage_id,
            "topology_coordinates": [list(item) for item in sorted(self.topology_coordinates)],
            "evidence_refs": sorted(self.evidence_refs),
        }


@dataclass(frozen=True)
class ValidatedLogicalTensor:
    """One exactly covered logical tensor after explicit replica deduplication."""

    logical_tensor_id: str
    fqn: str
    dtype: str
    global_shape: tuple[int, ...]
    fragments: tuple[TensorFragment, ...]
    replica_members: tuple[tuple[str, ...], ...]
    partition_axes: tuple[int, ...]
    topology_coordinates: tuple[tuple[str, int], ...]
    tie_group_id: str | None


@dataclass(frozen=True)
class ValidationResult:
    """Deterministic result used by independent oracles and the canonical writer."""

    logical_tensors: tuple[ValidatedLogicalTensor, ...]
    manifest_digest: str
    logical_elements: int

    def get(self, logical_tensor_id: str) -> ValidatedLogicalTensor:
        for tensor in self.logical_tensors:
            if tensor.logical_tensor_id == logical_tensor_id:
                return tensor
        raise KeyError(logical_tensor_id)


def _refuse(detail: str, *references: str) -> CheckpointContractError:
    return CheckpointContractError(
        "DCI_VALIDATION_FAILED",
        detail=detail,
        affected_refs=references,
    )


def _resource(detail: str, *references: str) -> CheckpointContractError:
    return CheckpointContractError(
        "DCI_RESOURCE_LIMIT",
        detail=detail,
        affected_refs=references,
    )


def _checked_shape(
    value: tuple[int, ...],
    *,
    name: str,
    dimensions: int | None,
    limits: FragmentLimits,
    reference: str,
) -> tuple[int, ...]:
    if not isinstance(value, tuple):
        raise _refuse("shape_type_invalid", reference)
    if len(value) > limits.max_dimensions:
        raise _resource("max_dimensions", reference)
    if dimensions is not None and len(value) != dimensions:
        raise _refuse("dimension_mismatch", reference)
    for item in value:
        if type(item) is not int:
            raise _refuse("integer_type_invalid", reference)
        if item < 0:
            raise _refuse("negative_integer", reference)
        if item > _INT64_MAX:
            raise _refuse("integer_overflow", reference)
    return value


def _checked_add(left: int, right: int, reference: str) -> int:
    if left > _INT64_MAX - right:
        raise _refuse("integer_overflow", reference)
    return left + right


def _checked_product(shape: tuple[int, ...], reference: str) -> int:
    result = 1
    for item in shape:
        if item and result > _INT64_MAX // item:
            raise _refuse("integer_overflow", reference)
        result *= item
    return result


def _valid_text(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        return len(value.encode("utf-8")) <= _MAX_IDENTIFIER_BYTES
    except UnicodeEncodeError:
        return False


def _valid_optional_text(value: object) -> bool:
    return value is None or _valid_text(value)


def _payload_view(fragment: TensorFragment) -> torch.Tensor | None:
    payload = fragment.payload
    if payload is None:
        return None
    if not isinstance(payload, torch.Tensor):
        raise _refuse("payload_type_invalid", fragment.logical_tensor_id, fragment.fragment_id)
    if payload.device.type != "cpu":
        raise _refuse("payload_device_not_cpu", fragment.logical_tensor_id, fragment.fragment_id)
    if payload.layout != torch.strided or payload.is_quantized:
        raise _refuse("payload_layout_unsupported", fragment.logical_tensor_id, fragment.fragment_id)
    if tuple(payload.shape) != fragment.local_shape:
        raise _refuse("payload_shape_mismatch", fragment.logical_tensor_id, fragment.fragment_id)
    if str(payload.dtype).removeprefix("torch.") != fragment.dtype:
        raise _refuse("payload_dtype_mismatch", fragment.logical_tensor_id, fragment.fragment_id)
    if not fragment.global_shape:
        return payload
    slices = tuple(
        slice(before, before + extent)
        for before, extent in zip(
            fragment.padding.before,
            fragment.element_extent,
            strict=True,
        )
    )
    return payload[slices]


def _tensor_digest(tensor: torch.Tensor) -> str:
    raw = tensor.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
    return f"sha256:{sha256(raw).hexdigest()}"


def _observed_digest(fragment: TensorFragment) -> str | None:
    payload = _payload_view(fragment)
    if payload is None:
        return fragment.fragment_digest
    actual = _tensor_digest(payload)
    if fragment.fragment_digest is not None and fragment.fragment_digest != actual:
        raise _refuse(
            "fragment_digest_mismatch",
            fragment.logical_tensor_id,
            fragment.fragment_id,
        )
    return actual


def _validate_fragment(fragment: TensorFragment, limits: FragmentLimits) -> None:
    reference = fragment.logical_tensor_id
    identifiers = (
        fragment.fragment_id,
        fragment.component_id,
        fragment.fqn,
        fragment.dtype,
        fragment.shard_file_id,
        fragment.shard_digest_ref,
        fragment.logical_tensor_id,
    )
    if any(not _valid_text(value) for value in identifiers):
        raise _refuse("identifier_invalid", reference)
    if fragment.dtype not in _SAFE_DTYPES:
        raise _refuse("dtype_unsupported", reference, fragment.fragment_id)
    if not _valid_optional_text(fragment.tie_group_id) or not _valid_optional_text(
        fragment.shared_storage_id
    ):
        raise _refuse("identifier_invalid", reference, fragment.fragment_id)
    if fragment.fragment_digest is not None and (
        not isinstance(fragment.fragment_digest, str)
        or not fragment.fragment_digest.startswith("sha256:")
        or len(fragment.fragment_digest) != 71
        or any(
            character not in "0123456789abcdef"
            for character in fragment.fragment_digest[7:]
        )
    ):
        raise _refuse("fragment_digest_invalid", reference, fragment.fragment_id)
    if not isinstance(fragment.padding, Padding):
        raise _refuse("padding_type_invalid", reference, fragment.fragment_id)
    if not isinstance(fragment.replica, Replica):
        raise _refuse("replica_type_invalid", reference, fragment.fragment_id)
    if fragment.role not in _ROLES:
        raise _refuse("role_invalid", reference, fragment.fragment_id)
    dimensions = len(
        _checked_shape(
            fragment.global_shape,
            name="global_shape",
            dimensions=None,
            limits=limits,
            reference=reference,
        )
    )
    local = _checked_shape(
        fragment.local_shape,
        name="local_shape",
        dimensions=dimensions,
        limits=limits,
        reference=reference,
    )
    offset = _checked_shape(
        fragment.element_offset,
        name="element_offset",
        dimensions=dimensions,
        limits=limits,
        reference=reference,
    )
    extent = _checked_shape(
        fragment.element_extent,
        name="element_extent",
        dimensions=dimensions,
        limits=limits,
        reference=reference,
    )
    before = _checked_shape(
        fragment.padding.before,
        name="padding.before",
        dimensions=dimensions,
        limits=limits,
        reference=reference,
    )
    after = _checked_shape(
        fragment.padding.after,
        name="padding.after",
        dimensions=dimensions,
        limits=limits,
        reference=reference,
    )
    if fragment.padding.semantic not in _PADDING_SEMANTICS:
        raise _refuse("padding_semantic_invalid", reference, fragment.fragment_id)
    if fragment.padding.semantic == "none" and any((*before, *after)):
        raise _refuse("undeclared_padding", reference, fragment.fragment_id)
    for axis in range(dimensions):
        logical_end = _checked_add(offset[axis], extent[axis], reference)
        if logical_end > fragment.global_shape[axis]:
            raise _refuse("fragment_out_of_bounds", reference, fragment.fragment_id)
        padded = _checked_add(_checked_add(before[axis], extent[axis], reference), after[axis], reference)
        if padded != local[axis]:
            raise _refuse("padding_shape_mismatch", reference, fragment.fragment_id)
    global_elements = _checked_product(fragment.global_shape, reference)
    if global_elements > limits.max_elements_per_tensor:
        raise _resource("max_elements_per_tensor", reference)
    if not isinstance(fragment.partition_axes, tuple):
        raise _refuse("partition_axis_type_invalid", reference, fragment.fragment_id)
    if len(set(fragment.partition_axes)) != len(fragment.partition_axes):
        raise _refuse("partition_axis_duplicate", reference, fragment.fragment_id)
    for axis in fragment.partition_axes:
        if type(axis) is not int or axis < 0 or axis >= dimensions:
            raise _refuse("partition_axis_out_of_bounds", reference, fragment.fragment_id)
    if fragment.replica.group_id is None:
        if fragment.replica != Replica.unique():
            raise _refuse("replica_declaration_invalid", reference, fragment.fragment_id)
    else:
        if (
            not _valid_text(fragment.replica.group_id)
            or type(fragment.replica.member_count) is not int
            or fragment.replica.member_count < 2
            or fragment.replica.member_count > _INT64_MAX
            or type(fragment.replica.member_index) is not int
        ):
            raise _refuse("replica_declaration_invalid", reference, fragment.fragment_id)
        if not 0 <= fragment.replica.member_index < fragment.replica.member_count:
            raise _refuse("replica_member_out_of_bounds", reference, fragment.fragment_id)
    if not isinstance(fragment.topology_coordinates, tuple) or any(
        not isinstance(item, tuple)
        or len(item) != 2
        or not _valid_text(item[0])
        or type(item[1]) is not int
        or item[1] < 0
        or item[1] > _INT64_MAX
        for item in fragment.topology_coordinates
    ):
        raise _refuse("topology_coordinate_invalid", reference, fragment.fragment_id)
    if len({kind for kind, _ in fragment.topology_coordinates}) != len(
        fragment.topology_coordinates
    ):
        raise _refuse("topology_coordinate_duplicate", reference, fragment.fragment_id)
    if not isinstance(fragment.evidence_refs, tuple) or any(
        not _valid_text(item) for item in fragment.evidence_refs
    ):
        raise _refuse("evidence_ref_invalid", reference, fragment.fragment_id)
    _observed_digest(fragment)


def _replica_metadata(fragment: TensorFragment) -> tuple[object, ...]:
    return (
        fragment.component_id,
        fragment.fqn,
        fragment.role,
        fragment.dtype,
        fragment.global_shape,
        fragment.local_shape,
        fragment.element_offset,
        fragment.element_extent,
        fragment.padding,
        fragment.partition_axes,
        fragment.logical_tensor_id,
        fragment.tie_group_id,
        fragment.shared_storage_id,
    )


def _deduplicate_replicas(
    fragments: list[TensorFragment],
) -> tuple[list[TensorFragment], tuple[tuple[str, ...], ...]]:
    representatives = [item for item in fragments if item.replica.group_id is None]
    groups: dict[tuple[object, ...], list[TensorFragment]] = {}
    for item in fragments:
        if item.replica.group_id is None:
            continue
        key = (
            item.logical_tensor_id,
            item.replica.group_id,
            item.element_offset,
            item.element_extent,
        )
        groups.setdefault(key, []).append(item)
    memberships: list[tuple[str, ...]] = []
    for group in groups.values():
        ordered = sorted(group, key=lambda item: (item.replica.member_index, item.fragment_id))
        expected_count = ordered[0].replica.member_count
        indices = [item.replica.member_index for item in ordered]
        if any(item.replica.member_count != expected_count for item in ordered):
            raise _refuse("replica_count_mismatch", ordered[0].logical_tensor_id)
        if indices != list(range(expected_count)):
            raise _refuse("replica_members_missing", ordered[0].logical_tensor_id)
        if len({_replica_metadata(item) for item in ordered}) != 1:
            raise _refuse("replica_metadata_mismatch", ordered[0].logical_tensor_id)
        digests = [_observed_digest(item) for item in ordered]
        if any(digest is None for digest in digests):
            raise _refuse("replica_digest_unavailable", ordered[0].logical_tensor_id)
        if len(set(digests)) != 1:
            raise _refuse("replica_digest_mismatch", ordered[0].logical_tensor_id)
        representative = min(ordered, key=lambda item: item.fragment_id)
        representatives.append(representative)
        memberships.append(tuple(sorted(item.fragment_id for item in ordered)))
    return representatives, tuple(sorted(memberships))


def _fragments_overlap(left: TensorFragment, right: TensorFragment) -> bool:
    if not left.global_shape:
        return True
    return all(
        left_start < right_start + right_size and right_start < left_start + left_size
        for left_start, left_size, right_start, right_size in zip(
            left.element_offset,
            left.element_extent,
            right.element_offset,
            right.element_extent,
            strict=True,
        )
    )


def _logical_tensor(
    logical_tensor_id: str,
    fragments: list[TensorFragment],
    limits: FragmentLimits,
) -> ValidatedLogicalTensor:
    first = fragments[0]
    identity = {(item.fqn, item.dtype, item.global_shape, item.tie_group_id) for item in fragments}
    if len(identity) != 1:
        raise _refuse("logical_tensor_metadata_mismatch", logical_tensor_id)
    representatives, replica_members = _deduplicate_replicas(fragments)
    representatives.sort(
        key=lambda item: (item.element_offset, item.element_extent, item.fragment_id)
    )
    checks = len(representatives) * (len(representatives) - 1) // 2
    if checks > limits.max_overlap_checks:
        raise _resource("max_overlap_checks", logical_tensor_id)
    for index, left in enumerate(representatives):
        for right in representatives[index + 1 :]:
            if _fragments_overlap(left, right):
                raise _refuse("coverage_overlap", logical_tensor_id)
    global_elements = _checked_product(first.global_shape, logical_tensor_id)
    if global_elements > limits.max_elements_per_tensor:
        raise _resource("max_elements_per_tensor", logical_tensor_id)
    covered = sum(_checked_product(item.element_extent, logical_tensor_id) for item in representatives)
    if covered != global_elements:
        raise _refuse("coverage_gap" if covered < global_elements else "coverage_mismatch", logical_tensor_id)
    if global_elements == 0 and len(representatives) != 1:
        raise _refuse("zero_tensor_representation_ambiguous", logical_tensor_id)
    return ValidatedLogicalTensor(
        logical_tensor_id=logical_tensor_id,
        fqn=first.fqn,
        dtype=first.dtype,
        global_shape=first.global_shape,
        fragments=tuple(representatives),
        replica_members=replica_members,
        partition_axes=tuple(sorted({axis for item in fragments for axis in item.partition_axes})),
        topology_coordinates=tuple(
            sorted({coordinate for item in fragments for coordinate in item.topology_coordinates})
        ),
        tie_group_id=first.tie_group_id,
    )


def reconstruct_logical_tensor(
    result: ValidationResult,
    logical_tensor_id: str,
) -> torch.Tensor:
    """Materialize one validated tensor from already-normalized CPU payloads."""
    logical = result.get(logical_tensor_id)
    first_payload = _payload_view(logical.fragments[0])
    if first_payload is None:
        raise _refuse("payload_unavailable", logical_tensor_id)
    output = torch.empty(logical.global_shape, dtype=first_payload.dtype, device="cpu")
    for fragment in logical.fragments:
        payload = _payload_view(fragment)
        if payload is None:
            raise _refuse("payload_unavailable", logical_tensor_id, fragment.fragment_id)
        if not logical.global_shape:
            output.copy_(payload)
            continue
        destination = tuple(
            slice(offset, offset + extent)
            for offset, extent in zip(
                fragment.element_offset,
                fragment.element_extent,
                strict=True,
            )
        )
        output[destination].copy_(payload)
    return output


def _validate_ties(result: ValidationResult) -> None:
    groups: dict[str, list[ValidatedLogicalTensor]] = {}
    for logical in result.logical_tensors:
        if logical.tie_group_id is not None:
            groups.setdefault(logical.tie_group_id, []).append(logical)
    for tensors in groups.values():
        if len(tensors) < 2:
            raise _refuse("tie_group_member_missing", tensors[0].logical_tensor_id)
        references = tuple(sorted(item.logical_tensor_id for item in tensors))
        if len({(item.dtype, item.global_shape) for item in tensors}) != 1:
            raise _refuse("tie_group_metadata_mismatch", *references)
        if all(all(fragment.payload is not None for fragment in item.fragments) for item in tensors):
            digests = {
                _tensor_digest(reconstruct_logical_tensor(result, item.logical_tensor_id))
                for item in tensors
            }
            if len(digests) != 1:
                raise _refuse("tie_group_content_mismatch", *references)


def validate_fragments(
    fragments: list[TensorFragment] | tuple[TensorFragment, ...],
    *,
    limits: FragmentLimits | None = None,
) -> ValidationResult:
    """Validate exact logical coverage with explicit, agreement-checked replicas."""
    active_limits = limits or FragmentLimits()
    if not isinstance(fragments, (list, tuple)) or not fragments:
        raise _refuse("fragment_set_empty")
    if len(fragments) > active_limits.max_fragments:
        raise _resource("max_fragments")
    if any(not isinstance(item, TensorFragment) for item in fragments):
        raise _refuse("fragment_type_invalid")
    fragment_ids = [item.fragment_id for item in fragments]
    if len(set(fragment_ids)) != len(fragment_ids):
        raise _refuse("fragment_id_duplicate")
    grouped: dict[str, list[TensorFragment]] = {}
    for fragment in fragments:
        _validate_fragment(fragment, active_limits)
        grouped.setdefault(fragment.logical_tensor_id, []).append(fragment)
    logical_tensors = tuple(
        _logical_tensor(logical_id, grouped[logical_id], active_limits)
        for logical_id in sorted(grouped)
    )
    records = [item.manifest_record() for item in sorted(fragments, key=lambda item: item.fragment_id)]
    manifest_payload = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    result = ValidationResult(
        logical_tensors=logical_tensors,
        manifest_digest=f"sha256:{sha256(manifest_payload).hexdigest()}",
        logical_elements=sum(_checked_product(item.global_shape, item.logical_tensor_id) for item in logical_tensors),
    )
    _validate_ties(result)
    return result
