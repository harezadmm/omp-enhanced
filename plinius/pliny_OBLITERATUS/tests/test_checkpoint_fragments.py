"""Producer-neutral tensor-fragment validation and reconstruction oracles."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from hashlib import sha256

import pytest
import torch
from hypothesis import given, strategies as st

from obliteratus.checkpoint_errors import CheckpointContractError
from obliteratus.checkpoint_fragments import (
    FragmentLimits,
    Padding,
    Replica,
    TensorFragment,
    reconstruct_logical_tensor,
    validate_fragments,
)


def _digest(tensor: torch.Tensor) -> str:
    payload = (
        tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
    )
    return f"sha256:{sha256(payload).hexdigest()}"


def _fragment(
    fragment_id: str,
    payload: torch.Tensor,
    *,
    global_shape: tuple[int, ...],
    offset: tuple[int, ...],
    extent: tuple[int, ...] | None = None,
    logical_tensor_id: str = "tensor.weight",
    padding: Padding | None = None,
    replica: Replica | None = None,
    tie_group_id: str | None = None,
    partition_axes: tuple[int, ...] = (0,),
) -> TensorFragment:
    extent = extent if extent is not None else tuple(payload.shape)
    padding = padding or Padding.zeros(len(global_shape))
    replica = replica or Replica.unique()
    return TensorFragment(
        fragment_id=fragment_id,
        component_id="model",
        fqn=logical_tensor_id,
        role="parameter",
        dtype=str(payload.dtype).removeprefix("torch."),
        global_shape=global_shape,
        local_shape=tuple(payload.shape),
        element_offset=offset,
        element_extent=extent,
        padding=padding,
        shard_file_id=f"shard-{fragment_id}",
        shard_digest_ref=f"digest-{fragment_id}",
        fragment_digest=_digest(
            payload[
                tuple(
                    slice(before, before + size)
                    for before, size in zip(padding.before, extent, strict=True)
                )
            ]
            if global_shape
            else payload
        ),
        replica=replica,
        partition_axes=partition_axes if global_shape else (),
        logical_tensor_id=logical_tensor_id,
        tie_group_id=tie_group_id,
        shared_storage_id=None,
        topology_coordinates=(("tp", 0), ("pp", 1)),
        evidence_refs=("evidence-1",),
        payload=payload,
    )


def _assert_refused(fragments: list[TensorFragment], detail: str) -> None:
    with pytest.raises(CheckpointContractError) as caught:
        validate_fragments(fragments)
    assert caught.value.code == "DCI_VALIDATION_FAILED"
    assert caught.value.detail == detail
    assert any(reference.startswith("tensor") for reference in caught.value.affected_refs)


def test_records_are_frozen_and_scalar_round_trips():
    fragment = _fragment(
        "scalar",
        torch.tensor(7.0),
        global_shape=(),
        offset=(),
        partition_axes=(),
    )

    with pytest.raises(FrozenInstanceError):
        fragment.dtype = "float16"  # type: ignore[misc]

    result = validate_fragments([fragment])
    actual = reconstruct_logical_tensor(result, "tensor.weight")

    assert actual.shape == torch.Size([])
    assert actual.item() == 7.0
    assert result.logical_tensors[0].topology_coordinates == (("pp", 1), ("tp", 0))


def test_uneven_fragments_reconstruct_independently_of_record_order():
    expected = torch.arange(15, dtype=torch.float32).reshape(3, 5)
    fragments = [
        _fragment(
            "right",
            expected[:, 2:].clone(),
            global_shape=(3, 5),
            offset=(0, 2),
            partition_axes=(1,),
        ),
        _fragment(
            "left",
            expected[:, :2].clone(),
            global_shape=(3, 5),
            offset=(0, 0),
            partition_axes=(1,),
        ),
    ]

    forward = validate_fragments(fragments)
    reverse = validate_fragments(list(reversed(fragments)))

    assert torch.equal(reconstruct_logical_tensor(forward, "tensor.weight"), expected)
    assert torch.equal(reconstruct_logical_tensor(reverse, "tensor.weight"), expected)
    assert forward.manifest_digest == reverse.manifest_digest
    assert [item.fragment_id for item in forward.logical_tensors[0].fragments] == [
        "left",
        "right",
    ]


def test_two_dimensional_tiles_cover_the_logical_tensor_exactly():
    expected = torch.arange(24, dtype=torch.int64).reshape(4, 6)
    fragments = []
    for row, (start, stop) in enumerate(((0, 1), (1, 4))):
        for column, (left, right) in enumerate(((0, 2), (2, 6))):
            fragments.append(
                _fragment(
                    f"tile-{row}-{column}",
                    expected[start:stop, left:right].clone(),
                    global_shape=(4, 6),
                    offset=(start, left),
                    partition_axes=(0, 1),
                )
            )

    result = validate_fragments(fragments)

    assert torch.equal(reconstruct_logical_tensor(result, "tensor.weight"), expected)


def test_declared_padding_is_removed_before_reconstruction():
    payload = torch.tensor([-1, 10, 11, -2], dtype=torch.int32)
    fragment = _fragment(
        "padded",
        payload,
        global_shape=(2,),
        offset=(0,),
        extent=(2,),
        padding=Padding(before=(1,), after=(1,), semantic="producer_declared"),
    )

    result = validate_fragments([fragment])

    assert torch.equal(
        reconstruct_logical_tensor(result, "tensor.weight"),
        torch.tensor([10, 11], dtype=torch.int32),
    )


def test_explicit_replicas_are_deduplicated_only_after_digest_agreement():
    payload = torch.tensor([1.0, 2.0])
    fragments = [
        _fragment(
            "replica-0",
            payload.clone(),
            global_shape=(2,),
            offset=(0,),
            replica=Replica("dp-0", 0, 2),
        ),
        _fragment(
            "replica-1",
            payload.clone(),
            global_shape=(2,),
            offset=(0,),
            replica=Replica("dp-0", 1, 2),
        ),
    ]

    result = validate_fragments(fragments)

    assert len(result.logical_tensors[0].fragments) == 1
    assert result.logical_tensors[0].replica_members == (("replica-0", "replica-1"),)


@pytest.mark.parametrize(
    ("mutator", "detail"),
    [
        (lambda item: replace(item, element_offset=(-1,)), "negative_integer"),
        (
            lambda item: replace(item, element_offset=((1 << 63) - 1,)),
            "integer_overflow",
        ),
        (lambda item: replace(item, element_offset=(1,)), "fragment_out_of_bounds"),
        (lambda item: replace(item, local_shape=(3,)), "padding_shape_mismatch"),
        (lambda item: replace(item, partition_axes=(1,)), "partition_axis_out_of_bounds"),
    ],
)
def test_invalid_fragment_geometry_fails_closed(mutator, detail):
    valid = _fragment(
        "fragment",
        torch.tensor([1.0, 2.0]),
        global_shape=(2,),
        offset=(0,),
    )

    _assert_refused([mutator(valid)], detail)


def test_gap_and_overlap_are_distinct_refusals():
    left = _fragment("left", torch.tensor([1.0]), global_shape=(3,), offset=(0,))
    right = _fragment("right", torch.tensor([3.0]), global_shape=(3,), offset=(2,))
    _assert_refused([left, right], "coverage_gap")

    overlap = _fragment("overlap", torch.tensor([2.0, 3.0]), global_shape=(3,), offset=(1,))
    _assert_refused([replace(left, payload=torch.tensor([1.0, 2.0]), local_shape=(2,), element_extent=(2,), fragment_digest=None), overlap], "coverage_overlap")


def test_replica_membership_and_content_disagreement_fail_closed():
    payload = torch.tensor([1.0, 2.0])
    first = _fragment(
        "replica-0",
        payload,
        global_shape=(2,),
        offset=(0,),
        replica=Replica("dp-0", 0, 2),
    )
    _assert_refused([first], "replica_members_missing")

    disagreeing = _fragment(
        "replica-1",
        torch.tensor([1.0, 3.0]),
        global_shape=(2,),
        offset=(0,),
        replica=Replica("dp-0", 1, 2),
    )
    _assert_refused([first, disagreeing], "replica_digest_mismatch")


def test_tied_tensors_require_matching_shape_dtype_and_values():
    first = _fragment(
        "embedding",
        torch.tensor([1.0, 2.0]),
        global_shape=(2,),
        offset=(0,),
        logical_tensor_id="model.embed.weight",
        tie_group_id="tie-0",
    )
    second = _fragment(
        "lm-head",
        torch.tensor([1.0, 3.0]),
        global_shape=(2,),
        offset=(0,),
        logical_tensor_id="lm_head.weight",
        tie_group_id="tie-0",
    )

    with pytest.raises(CheckpointContractError) as caught:
        validate_fragments([first, second])

    assert caught.value.detail == "tie_group_content_mismatch"
    assert caught.value.affected_refs == ("lm_head.weight", "model.embed.weight")


def test_fragment_and_overlap_limits_refuse_before_expensive_work():
    first = _fragment("first", torch.tensor([1.0]), global_shape=(2,), offset=(0,))
    second = _fragment("second", torch.tensor([2.0]), global_shape=(2,), offset=(1,))

    with pytest.raises(CheckpointContractError) as count_error:
        validate_fragments([first, second], limits=FragmentLimits(max_fragments=1))
    assert count_error.value.code == "DCI_RESOURCE_LIMIT"
    assert count_error.value.detail == "max_fragments"

    with pytest.raises(CheckpointContractError) as work_error:
        validate_fragments([first, second], limits=FragmentLimits(max_overlap_checks=0))
    assert work_error.value.code == "DCI_RESOURCE_LIMIT"
    assert work_error.value.detail == "max_overlap_checks"


@given(
    size=st.integers(min_value=2, max_value=64),
    split=st.integers(min_value=1, max_value=63),
)
def test_one_dimensional_partition_property(size: int, split: int):
    split = min(split, size - 1)
    expected = torch.arange(size, dtype=torch.int64)
    fragments = [
        _fragment("a", expected[:split].clone(), global_shape=(size,), offset=(0,)),
        _fragment("b", expected[split:].clone(), global_shape=(size,), offset=(split,)),
    ]

    result = validate_fragments(fragments)

    assert torch.equal(reconstruct_logical_tensor(result, "tensor.weight"), expected)


def test_limits_and_top_level_fragment_contracts_fail_closed():
    with pytest.raises(ValueError, match="non-negative integer"):
        FragmentLimits(max_fragments=-1)

    with pytest.raises(CheckpointContractError) as empty:
        validate_fragments([])
    assert empty.value.detail == "fragment_set_empty"

    with pytest.raises(CheckpointContractError) as wrong_type:
        validate_fragments([object()])  # type: ignore[list-item]
    assert wrong_type.value.detail == "fragment_type_invalid"

    valid = _fragment("same", torch.ones(1), global_shape=(1,), offset=(0,))
    with pytest.raises(CheckpointContractError) as duplicate:
        validate_fragments([valid, valid])
    assert duplicate.value.detail == "fragment_id_duplicate"

    result = validate_fragments([valid])
    with pytest.raises(KeyError, match="absent"):
        result.get("absent")


@pytest.mark.parametrize(
    ("mutator", "detail", "code"),
    [
        (lambda item: replace(item, global_shape=[1]), "shape_type_invalid", "DCI_VALIDATION_FAILED"),  # type: ignore[arg-type]
        (
            lambda item: replace(item, global_shape=(1, 1), local_shape=(1,)),
            "dimension_mismatch",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, global_shape=(1, 1)),
            "max_dimensions",
            "DCI_RESOURCE_LIMIT",
        ),
        (lambda item: replace(item, element_extent=(True,)), "integer_type_invalid", "DCI_VALIDATION_FAILED"),
        (
            lambda item: replace(item, global_shape=((1 << 63),)),
            "integer_overflow",
            "DCI_VALIDATION_FAILED",
        ),
        (lambda item: replace(item, component_id=""), "identifier_invalid", "DCI_VALIDATION_FAILED"),
        (lambda item: replace(item, fqn="x" * 4097), "identifier_invalid", "DCI_VALIDATION_FAILED"),
        (lambda item: replace(item, role="unknown"), "role_invalid", "DCI_VALIDATION_FAILED"),  # type: ignore[arg-type]
        (lambda item: replace(item, dtype="string"), "dtype_unsupported", "DCI_VALIDATION_FAILED"),
        (lambda item: replace(item, fragment_digest="bad"), "fragment_digest_invalid", "DCI_VALIDATION_FAILED"),
        (lambda item: replace(item, padding=object()), "padding_type_invalid", "DCI_VALIDATION_FAILED"),  # type: ignore[arg-type]
        (lambda item: replace(item, replica=object()), "replica_type_invalid", "DCI_VALIDATION_FAILED"),  # type: ignore[arg-type]
        (
            lambda item: replace(item, padding=Padding((0,), (0,), "invalid")),  # type: ignore[arg-type]
            "padding_semantic_invalid",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, padding=Padding((1,), (0,), "none"), local_shape=(2,)),
            "undeclared_padding",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, partition_axes=(0, 0)),
            "partition_axis_duplicate",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, replica=Replica(None, 1, 1)),
            "replica_declaration_invalid",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, replica=Replica("group", 0, 1)),
            "replica_declaration_invalid",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, replica=Replica("group", 2, 2)),
            "replica_member_out_of_bounds",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, topology_coordinates=(("tp", -1),)),
            "topology_coordinate_invalid",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, topology_coordinates=(("tp", 0), ("tp", 1))),
            "topology_coordinate_duplicate",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, topology_coordinates=(("tp",),)),
            "topology_coordinate_invalid",
            "DCI_VALIDATION_FAILED",
        ),
        (
            lambda item: replace(item, evidence_refs=(object(),)),
            "evidence_ref_invalid",
            "DCI_VALIDATION_FAILED",
        ),
    ],
)
def test_fragment_metadata_validation_covers_each_fail_closed_family(mutator, detail, code):
    valid = _fragment("fragment", torch.ones(1), global_shape=(1,), offset=(0,))
    limits = FragmentLimits(max_dimensions=1) if detail == "max_dimensions" else FragmentLimits()

    with pytest.raises(CheckpointContractError) as caught:
        validate_fragments([mutator(valid)], limits=limits)

    assert caught.value.code == code
    assert caught.value.detail == detail


@pytest.mark.parametrize(
    ("payload", "local_shape", "dtype", "digest", "detail"),
    [
        (object(), (1,), "float32", None, "payload_type_invalid"),
        (torch.ones(2), (1,), "float32", None, "payload_shape_mismatch"),
        (torch.ones(1), (1,), "float64", None, "payload_dtype_mismatch"),
        (torch.ones(1), (1,), "float32", "sha256:" + "0" * 64, "fragment_digest_mismatch"),
    ],
)
def test_payload_contract_refuses_wrong_type_shape_dtype_and_digest(
    payload,
    local_shape,
    dtype,
    digest,
    detail,
):
    valid = _fragment("fragment", torch.ones(1), global_shape=(1,), offset=(0,))
    candidate = replace(
        valid,
        payload=payload,
        local_shape=local_shape,
        dtype=dtype,
        fragment_digest=digest,
    )
    _assert_refused([candidate], detail)


def test_payload_contract_rejects_non_strided_tensor_layout():
    valid = _fragment("fragment", torch.ones(1), global_shape=(1,), offset=(0,))
    sparse = torch.sparse_coo_tensor(
        torch.tensor([[0]]),
        torch.tensor([1.0]),
        size=(1,),
        check_invariants=True,
    )

    _assert_refused(
        [replace(valid, payload=sparse, fragment_digest=None)],
        "payload_layout_unsupported",
    )


def test_replica_metadata_count_and_digest_availability_are_mandatory():
    payload = torch.ones(1)
    first = _fragment(
        "a",
        payload,
        global_shape=(1,),
        offset=(0,),
        replica=Replica("group", 0, 2),
    )
    second = _fragment(
        "b",
        payload,
        global_shape=(1,),
        offset=(0,),
        replica=Replica("group", 1, 3),
    )
    _assert_refused([first, second], "replica_count_mismatch")

    second = replace(second, replica=Replica("group", 1, 2), component_id="other")
    _assert_refused([first, second], "replica_metadata_mismatch")

    first = replace(first, payload=None, fragment_digest=None)
    second = replace(second, payload=None, fragment_digest=None, component_id="model")
    _assert_refused([first, second], "replica_digest_unavailable")


def test_logical_metadata_resource_zero_and_payload_absence_boundaries():
    first = _fragment("a", torch.ones(1), global_shape=(1,), offset=(0,))
    left = _fragment("left", torch.ones(1), global_shape=(2,), offset=(0,))
    right = _fragment("right", torch.ones(1), global_shape=(2,), offset=(1,))
    _assert_refused([left, replace(right, fqn="other")], "logical_tensor_metadata_mismatch")

    with pytest.raises(CheckpointContractError) as limit:
        validate_fragments([first], limits=FragmentLimits(max_elements_per_tensor=0))
    assert limit.value.code == "DCI_RESOURCE_LIMIT"
    assert limit.value.detail == "max_elements_per_tensor"

    zero_a = _fragment("zero-a", torch.empty(0), global_shape=(0,), offset=(0,))
    zero_b = _fragment("zero-b", torch.empty(0), global_shape=(0,), offset=(0,))
    _assert_refused([zero_a, zero_b], "zero_tensor_representation_ambiguous")

    absent = replace(first, payload=None, fragment_digest=_digest(torch.ones(1)))
    result = validate_fragments([absent])
    with pytest.raises(CheckpointContractError) as unavailable:
        reconstruct_logical_tensor(result, "tensor.weight")
    assert unavailable.value.detail == "payload_unavailable"


def test_tie_groups_require_two_members_and_identical_metadata():
    single = _fragment(
        "single",
        torch.ones(1),
        global_shape=(1,),
        offset=(0,),
        tie_group_id="tie",
    )
    _assert_refused([single], "tie_group_member_missing")

    second = _fragment(
        "second",
        torch.ones(2),
        global_shape=(2,),
        offset=(0,),
        logical_tensor_id="tensor.other",
        tie_group_id="tie",
    )
    with pytest.raises(CheckpointContractError) as mismatch:
        validate_fragments([single, second])
    assert mismatch.value.detail == "tie_group_metadata_mismatch"
