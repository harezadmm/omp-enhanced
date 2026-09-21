"""Pure tests for bounded distributed runtime records and frames."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from enum import Enum

import pytest
import torch

from obliteratus.distributed.consensus import (
    assert_rank_order,
    decode_frame,
    encode_frame,
    gloo_all_gather_records,
    require_consensus_digest,
    require_record_consensus,
    unanimous_vote,
)
from obliteratus.distributed.contracts import (
    MAX_CONSENSUS_BYTES,
    ContractError,
    LogicalPlacement,
    PlacementKind,
    RankInventory,
    RunIdentity,
    RuntimeStage,
    StageMessage,
    TopologyPlan,
    Vote,
    advance_stage,
    canonical_record,
    contract_digest,
    validate_inventory_consensus,
)
from obliteratus.distributed.numerical import distributed_project_weight


def _digest(character: str = "a") -> str:
    return character * 64


def _identity(**overrides: object) -> RunIdentity:
    values: dict[str, object] = {
        "run_id": "1" * 32,
        "config_digest": _digest("a"),
        "source_digest": _digest("b"),
        "model_digest": _digest("c"),
        "tokenizer_digest": _digest("d"),
        "commit_sha": "e" * 40,
        "world_size": 2,
    }
    values.update(overrides)
    return RunIdentity(**values)  # type: ignore[arg-type]


def _inventory(rank: int = 0, **overrides: object) -> RankInventory:
    values: dict[str, object] = {
        "rank": rank,
        "local_rank": rank,
        "world_size": 2,
        "host_digest": _digest(str(rank + 1)),
        "device_digest": _digest(chr(ord("a") + rank)),
        "device_kind": "cpu",
        "total_memory_bytes": 1024,
        "free_memory_bytes": 512,
        "software_digest": _digest("e"),
        "storage_digest": _digest("f"),
    }
    values.update(overrides)
    return RankInventory(**values)  # type: ignore[arg-type]


def test_contract_records_are_immutable_and_canonical():
    identity = _identity()
    with pytest.raises(FrozenInstanceError):
        identity.world_size = 3  # type: ignore[misc]
    first = canonical_record({"z": 1, "identity": identity, "items": (Vote.ABORT,)})
    second = canonical_record({"items": ["abort"], "identity": identity, "z": 1})
    assert first == second
    assert contract_digest({"value": 1}) == contract_digest({"value": 1})
    assert len(contract_digest(identity)) == 64


def test_identity_and_topology_fields_are_digest_bound():
    identity = _identity()
    for field, value in (
        ("run_id", "2" * 32),
        ("config_digest", _digest("1")),
        ("source_digest", _digest("2")),
        ("model_digest", _digest("3")),
        ("tokenizer_digest", _digest("4")),
    ):
        assert contract_digest(identity) != contract_digest(_identity(**{field: value}))
    topology = TopologyPlan(2, 0, "gloo", _digest("5"))
    assert contract_digest(topology) != contract_digest(TopologyPlan(2, 1, "gloo", _digest("5")))
    assert contract_digest(topology) != contract_digest(TopologyPlan(2, 0, "nccl", _digest("5")))


def test_public_records_reject_unknown_fields():
    with pytest.raises(TypeError, match="unexpected keyword"):
        _identity(unknown="value")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"run_id": "not-a-run"}, "run_id has an invalid format"),
        ({"config_digest": "A" * 64}, "config_digest has an invalid format"),
        ({"commit_sha": "e" * 39}, "commit_sha has an invalid format"),
        ({"world_size": True}, "world_size must be an integer"),
        ({"world_size": 1}, "world_size must be between 2 and 4096"),
    ],
)
def test_run_identity_rejects_malformed_or_single_rank_values(overrides, message):
    with pytest.raises(ContractError, match=message):
        _identity(**overrides)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"rank": 2}, "rank must be between 0 and 1"),
        ({"local_rank": -1}, "local_rank must be between 0 and 1"),
        ({"device_kind": "mps"}, "device_kind must be 'cpu' or 'cuda'"),
        ({"free_memory_bytes": 2048}, "free_memory_bytes cannot exceed"),
        ({"total_memory_bytes": 0}, "total_memory_bytes must be between"),
        ({"host_digest": "x" * 64}, "host_digest has an invalid format"),
    ],
)
def test_rank_inventory_is_bounded(overrides, message):
    with pytest.raises(ContractError, match=message):
        _inventory(**overrides)


def test_complete_homogeneous_inventory_is_accepted():
    validate_inventory_consensus(_identity(), (_inventory(0), _inventory(1)))


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ((_inventory(0),), "exactly one record per rank"),
        ((_inventory(0), _inventory(0)), "ranks do not exactly cover"),
        (
            (_inventory(0), _inventory(1, world_size=3)),
            "world_size disagrees",
        ),
        (
            (_inventory(0), _inventory(1, host_digest=_digest("1"), device_digest=_digest("a"))),
            "unique host/device pair",
        ),
        (
            (_inventory(0), _inventory(1, host_digest=_digest("1"), local_rank=0)),
            "local ranks must be unique",
        ),
        (
            (_inventory(0), _inventory(1, software_digest=_digest("0"))),
            "software identities disagree",
        ),
        (
            (_inventory(0), _inventory(1, storage_digest=_digest("0"))),
            "storage identities disagree",
        ),
    ],
)
def test_inventory_consensus_rejects_missing_duplicate_or_divergent_records(records, message):
    with pytest.raises(ContractError, match=message):
        validate_inventory_consensus(_identity(), records)


def test_inventory_consensus_rejects_wrong_record_types():
    with pytest.raises(ContractError, match="identity must"):
        validate_inventory_consensus(object(), ())  # type: ignore[arg-type]
    with pytest.raises(ContractError, match="invalid rank record"):
        validate_inventory_consensus(_identity(), (_inventory(0), object()))  # type: ignore[arg-type]


@pytest.mark.parametrize("backend", ["gloo", "nccl"])
def test_topology_accepts_declared_backends(backend):
    assert TopologyPlan(2, 0, backend, _digest()).backend == backend


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ((1, 0, "gloo", _digest()), "world_size"),
        ((2, 2, "gloo", _digest()), "coordinator_rank"),
        ((2, 0, "mpi", _digest()), "backend must"),
        ((2, 0, "gloo", "bad"), "placement_plan_digest"),
    ],
)
def test_topology_rejects_unqualified_values(args, message):
    with pytest.raises(ContractError, match=message):
        TopologyPlan(*args)


def _placement(kind: PlacementKind, rank: int, **overrides: object) -> LogicalPlacement:
    shard_dim = (
        None
        if kind is PlacementKind.REPLICATED
        else (0 if kind is PlacementKind.COLUMN_WISE else 1)
    )
    start, end = (0, 0) if shard_dim is None else (rank * 2, (rank + 1) * 2)
    values: dict[str, object] = {
        "logical_name": "model.layers.0.weight",
        "global_shape": (4, 4),
        "dtype": "float32",
        "kind": kind,
        "rank": rank,
        "world_size": 2,
        "direction_axis": 1,
        "shard_dim": shard_dim,
        "shard_start": start,
        "shard_end": end,
    }
    values.update(overrides)
    return LogicalPlacement(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (PlacementKind.COLUMN_WISE, (2, 4)),
        (PlacementKind.ROW_WISE, (4, 2)),
        (PlacementKind.REPLICATED, (4, 4)),
    ],
)
def test_logical_placements_report_exact_local_shapes(kind, expected):
    assert _placement(kind, 0).local_shape == expected


@pytest.mark.parametrize(
    ("kind", "overrides", "message"),
    [
        (PlacementKind.COLUMN_WISE, {"shard_dim": 1}, "requires shard_dim=0"),
        (PlacementKind.ROW_WISE, {"shard_dim": 0}, "requires shard_dim=1"),
        (PlacementKind.REPLICATED, {"shard_dim": 0}, "cannot declare"),
        (PlacementKind.COLUMN_WISE, {"shard_start": 1}, "does not match"),
        (PlacementKind.COLUMN_WISE, {"global_shape": (5, 4)}, "equal shard"),
        (PlacementKind.COLUMN_WISE, {"global_shape": (4,)}, "two-dimensional"),
        (PlacementKind.COLUMN_WISE, {"logical_name": "bad name"}, "invalid format"),
        (PlacementKind.COLUMN_WISE, {"direction_axis": 2}, "direction_axis"),
    ],
)
def test_logical_placement_fails_closed_for_unknown_or_uneven_layouts(kind, overrides, message):
    with pytest.raises(ContractError, match=message):
        _placement(kind, 0, **overrides)


def test_logical_placement_rejects_unknown_dtype():
    with pytest.raises(ContractError, match="dtype is not supported"):
        _placement(PlacementKind.COLUMN_WISE, 0, dtype="float8_e4m3fn")


def test_lifecycle_accepts_only_the_documented_happy_path_and_abort_path():
    happy = [
        RuntimeStage.CREATED,
        RuntimeStage.PREFLIGHTED,
        RuntimeStage.LOADED,
        RuntimeStage.PROBED,
        RuntimeStage.DISTILLED,
        RuntimeStage.PREPARED,
        RuntimeStage.MUTATING,
        RuntimeStage.VERIFIED,
        RuntimeStage.STAGED,
        RuntimeStage.PUBLISHED,
    ]
    for current, requested in zip(happy, happy[1:]):
        assert advance_stage(current, requested) is requested
    assert advance_stage(RuntimeStage.LOADED, RuntimeStage.ABORTING) is RuntimeStage.ABORTING
    assert advance_stage(RuntimeStage.ABORTING, RuntimeStage.ABORTED) is RuntimeStage.ABORTED
    assert (
        advance_stage(RuntimeStage.ABORTING, RuntimeStage.QUARANTINED) is RuntimeStage.QUARANTINED
    )


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        (RuntimeStage.CREATED, RuntimeStage.LOADED),
        (RuntimeStage.MUTATING, RuntimeStage.STAGED),
        (RuntimeStage.PUBLISHED, RuntimeStage.ABORTING),
        (RuntimeStage.ABORTED, RuntimeStage.CREATED),
        (RuntimeStage.QUARANTINED, RuntimeStage.PUBLISHED),
    ],
)
def test_lifecycle_rejects_skipped_or_post_terminal_transitions(current, requested):
    with pytest.raises(ContractError, match="invalid distributed stage transition"):
        advance_stage(current, requested)
    with pytest.raises(ContractError, match="must be RuntimeStage"):
        advance_stage(current.value, requested)  # type: ignore[arg-type]


def test_stage_message_requires_sequenced_typed_abort_evidence():
    message = StageMessage(
        run_id="1" * 32,
        identity_digest=_digest(),
        rank=1,
        sequence=7,
        stage=RuntimeStage.ABORTING,
        vote=Vote.ABORT,
        error_code="LMS_TEST_FAILURE",
    )
    assert contract_digest(message)
    assert StageMessage.from_bytes(message.to_bytes()) == message
    with pytest.raises(ContractError, match="not canonical"):
        StageMessage.from_bytes(b" " + message.to_bytes())
    duplicate = message.to_bytes().replace(b'{"error_code":', b'{"rank":0,"error_code":', 1)
    with pytest.raises(ContractError, match="duplicate"):
        StageMessage.from_bytes(duplicate)
    with pytest.raises(ContractError, match="requires an error_code"):
        StageMessage("1" * 32, _digest(), 0, 1, RuntimeStage.ABORTING, Vote.ABORT)
    with pytest.raises(ContractError, match="valid only with an abort vote"):
        StageMessage("1" * 32, _digest(), 0, 1, RuntimeStage.LOADED, None, "LMS_FAIL")
    with pytest.raises(ContractError, match="error_code has an invalid format"):
        StageMessage("1" * 32, _digest(), 0, 1, RuntimeStage.ABORTING, Vote.ABORT, "bad")


@pytest.mark.parametrize(
    "value",
    [1.5, {1: "bad key"}, {"nested": object()}],
)
def test_canonical_record_rejects_ambiguous_types(value):
    with pytest.raises(ContractError):
        canonical_record(value)


def test_canonical_record_rejects_enum_type_bypass_cycles_and_resource_abuse():
    class FloatEnum(Enum):
        VALUE = 1.5

    with pytest.raises(ContractError, match="unsupported type float"):
        canonical_record(FloatEnum.VALUE)
    cyclic: dict[str, object] = {}
    cyclic["cycle"] = cyclic
    with pytest.raises(ContractError, match="reference cycle"):
        canonical_record(cyclic)
    nested: object = None
    for _ in range(18):
        nested = [nested]
    with pytest.raises(ContractError, match="nesting depth"):
        canonical_record(nested)
    with pytest.raises(ContractError, match="4096 items"):
        canonical_record([None] * 4097)
    with pytest.raises(ContractError, match="signed 64-bit"):
        canonical_record(2**63)


def test_record_gather_rejects_noncanonical_raw_bytes_before_group_use():
    with pytest.raises(ContractError, match="unsupported type bytes"):
        gloo_all_gather_records(b"not-a-canonical-record")


def test_canonical_record_enforces_size_before_collective_allocation():
    with pytest.raises(ContractError, match="exceeds 16 bytes"):
        canonical_record({"value": "x" * 20}, max_bytes=16)
    with pytest.raises(ContractError, match="max_bytes"):
        canonical_record({}, max_bytes=MAX_CONSENSUS_BYTES + 1)


def test_fixed_frame_round_trip_and_zero_padding():
    frame = encode_frame(b"record", capacity=16)
    assert frame.dtype == torch.uint8
    assert frame.numel() == 20
    assert decode_frame(frame) == b"record"


@pytest.mark.parametrize(
    ("payload", "capacity", "message"),
    [
        ("not bytes", 16, "payload must be bytes"),
        (b"too long", 2, "exceeds 2 bytes"),
        (b"ok", 0, "capacity must be between"),
        (b"ok", MAX_CONSENSUS_BYTES + 1, "capacity must be between"),
    ],
)
def test_fixed_frame_rejects_invalid_input(payload, capacity, message):
    with pytest.raises(ContractError, match=message):
        encode_frame(payload, capacity=capacity)  # type: ignore[arg-type]


def test_frame_decoder_rejects_type_shape_length_and_padding_corruption():
    with pytest.raises(ContractError, match="one-dimensional uint8"):
        decode_frame(torch.zeros((2, 2)))
    with pytest.raises(ContractError, match="invalid capacity"):
        decode_frame(torch.zeros(4, dtype=torch.uint8))
    too_long = encode_frame(b"a", capacity=2)
    too_long[:4] = torch.tensor(list((3).to_bytes(4, "big")), dtype=torch.uint8)
    with pytest.raises(ContractError, match="length exceeds"):
        decode_frame(too_long)
    bad_padding = encode_frame(b"a", capacity=2)
    bad_padding[-1] = 1
    with pytest.raises(ContractError, match="padding must be zero"):
        decode_frame(bad_padding)


def test_collective_helpers_refuse_without_a_gloo_group():
    with pytest.raises(ContractError, match="must be initialized"):
        gloo_all_gather_records({"rank": 0})
    with pytest.raises(ContractError, match="64 lowercase"):
        require_consensus_digest("BAD")
    with pytest.raises(ContractError, match="must be initialized"):
        require_record_consensus(_identity())
    with pytest.raises(ContractError, match="vote sequence"):
        unanimous_vote(-1, True)
    with pytest.raises(ContractError, match="accepted must"):
        unanimous_vote(1, 1)  # type: ignore[arg-type]
    with pytest.raises(ContractError, match="initialized process group"):
        distributed_project_weight(
            torch.eye(4),
            torch.ones(4),
            _placement(PlacementKind.REPLICATED, 0),
        )
    with pytest.raises(ContractError, match="placement must"):
        distributed_project_weight(torch.eye(4), torch.ones(4), object())  # type: ignore[arg-type]


def test_rank_order_rejects_missing_duplicate_and_reordered_records():
    records = (_inventory(0), _inventory(1))
    assert_rank_order(records, world_size=2)
    with pytest.raises(ContractError, match="record count"):
        assert_rank_order(records[:1], world_size=2)
    with pytest.raises(ContractError, match="global-rank order"):
        assert_rank_order(tuple(reversed(records)), world_size=2)
