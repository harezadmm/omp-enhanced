"""Admission and source-safety tests for the distributed preflight."""

from __future__ import annotations

import json
import socket
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from obliteratus.distributed.contracts import (
    ContractError,
    RuntimeContractError,
    RuntimeStage,
    StageMessage,
    canonical_record,
    contract_digest,
)
from obliteratus.distributed.launcher import validate_network_interface
from obliteratus.distributed.preflight import (
    _validate_stage_messages,
    RankAttestation,
    checkout_code_digest,
    checkout_commit,
    inspect_source,
    storage_mount_digest,
    validate_attestations,
)


def _attestation(rank: int = 0, **overrides) -> RankAttestation:
    values = {
        "rank": rank,
        "local_rank": 0,
        "local_world_size": 1,
        "group_rank": rank,
        "world_size": 2,
        "host_digest": ("1" if rank == 0 else "2") * 64,
        "device_digest": ("3" if rank == 0 else "4") * 64,
        "device_profile_digest": "0" * 64,
        "device_config_digest": contract_digest(
            {"kind": "cuda", "name": "test-device", "compute_capability": "10.0"}
        ),
        "device_kind": "cuda",
        "total_device_memory_bytes": 8192,
        "free_device_memory_bytes": 4096,
        "total_host_memory_bytes": 16384,
        "free_host_memory_bytes": 8192,
        "free_staging_bytes": 8192,
        "software_digest": "5" * 64,
        "storage_digest": "6" * 64,
        "source_digest": "7" * 64,
        "model_digest": "8" * 64,
        "tokenizer_digest": "9" * 64,
        "config_digest": "a" * 64,
        "commit_sha": "b" * 40,
        "code_digest": "f" * 64,
        "placement_plan_digest": "c" * 64,
        "network_interface_digest": "d" * 64,
    }
    values.update(overrides)
    return RankAttestation(**values)


def _validate(records):
    validate_attestations(
        tuple(records),
        world_size=2,
        tensor_parallel_size=2,
        dimension_divisors=(2, 4),
        expected_device_kind="cuda",
        expected_device_config_digest=contract_digest(
            {"kind": "cuda", "name": "test-device", "compute_capability": "10.0"}
        ),
        expected_software_digest="5" * 64,
        expected_source_digest="7" * 64,
        expected_model_digest="8" * 64,
        expected_tokenizer_digest="9" * 64,
        expected_config_digest="a" * 64,
        expected_commit_sha="b" * 40,
        expected_code_digest="f" * 64,
        expected_placement_plan_digest="c" * 64,
        expected_storage_digest="6" * 64,
        expected_network_interface_digest="d" * 64,
        local_world_size=1,
        min_free_device_memory_bytes=4096,
        min_free_host_memory_bytes=8192,
        min_free_staging_bytes=8192,
    )


def test_complete_fixed_inventory_passes_exact_boundaries():
    _validate((_attestation(0), _attestation(1)))


def test_rank_attestation_decoder_requires_exact_canonical_bytes():
    record = _attestation()
    assert RankAttestation.from_bytes(canonical_record(record)) == record
    with pytest.raises(ContractError, match="not canonical"):
        RankAttestation.from_bytes(b" " + canonical_record(record))
    duplicate = canonical_record(record).replace(b'{"code_digest":', b'{"rank":0,"code_digest":', 1)
    with pytest.raises(ContractError, match="duplicate"):
        RankAttestation.from_bytes(duplicate)


def test_lifecycle_validation_rejects_a_record_bound_to_another_run():
    identity_digest = "a" * 64
    records = (
        StageMessage("1" * 32, identity_digest, 0, 0, RuntimeStage.CREATED),
        StageMessage("2" * 32, identity_digest, 1, 0, RuntimeStage.CREATED),
    )
    with pytest.raises(RuntimeContractError) as error:
        _validate_stage_messages(
            records,
            run_id="1" * 32,
            world_size=2,
            stage=RuntimeStage.CREATED,
            sequence=0,
            identity_digest=identity_digest,
            vote=None,
        )
    assert error.value.code == "LMS_LIFECYCLE_INVALID"


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ((_attestation(0),), "exactly one attestation"),
        ((_attestation(0), _attestation(0)), "rank order"),
        (
            (_attestation(0), replace(_attestation(1), device_digest="3" * 64)),
            "device identities",
        ),
        (
            (_attestation(0), replace(_attestation(1), device_profile_digest="e" * 64)),
            "device profiles",
        ),
        (
            (_attestation(0), replace(_attestation(1), local_rank=0, host_digest="1" * 64)),
            "local ranks",
        ),
        (
            (_attestation(0), replace(_attestation(1), software_digest="e" * 64)),
            "software identities",
        ),
        (
            (_attestation(0), replace(_attestation(1), storage_digest="e" * 64)),
            "storage identities",
        ),
        (
            (_attestation(0), replace(_attestation(1), source_digest="e" * 64)),
            "source_digest",
        ),
        (
            (_attestation(0), replace(_attestation(1), free_device_memory_bytes=4095)),
            "device memory headroom",
        ),
        (
            (_attestation(0), replace(_attestation(1), free_host_memory_bytes=8191)),
            "host memory headroom",
        ),
        (
            (_attestation(0), replace(_attestation(1), free_staging_bytes=8191)),
            "staging headroom",
        ),
    ],
)
def test_inventory_disagreement_fails_closed(records, message):
    with pytest.raises(ContractError, match=message):
        _validate(records)


def test_topology_dimensions_must_be_divisible():
    with pytest.raises(ContractError, match="dimension divisor"):
        validate_attestations(
            (_attestation(0), _attestation(1)),
            world_size=2,
            tensor_parallel_size=2,
            dimension_divisors=(3,),
            expected_device_kind="cuda",
            expected_device_config_digest=contract_digest(
                {"kind": "cuda", "name": "test-device", "compute_capability": "10.0"}
            ),
            expected_software_digest="5" * 64,
            expected_source_digest="7" * 64,
            expected_model_digest="8" * 64,
            expected_tokenizer_digest="9" * 64,
            expected_config_digest="a" * 64,
            expected_commit_sha="b" * 40,
            expected_code_digest="f" * 64,
            expected_placement_plan_digest="c" * 64,
            expected_storage_digest="6" * 64,
            expected_network_interface_digest="d" * 64,
            local_world_size=1,
            min_free_device_memory_bytes=1,
            min_free_host_memory_bytes=1,
            min_free_staging_bytes=1,
        )


def test_source_inspection_accepts_only_immutable_local_safetensors(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    weights = source / "model.safetensors"
    tokenizer = source / "tokenizer.json"
    header = json.dumps(
        {"weight": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}},
        separators=(",", ":"),
    ).encode()
    weights.write_bytes(len(header).to_bytes(8, "little") + header + b"\0" * 4)
    tokenizer.write_text('{"model":"fixture"}', encoding="utf-8")
    weights.chmod(0o444)
    tokenizer.chmod(0o444)
    source.chmod(0o555)
    first = inspect_source(source)
    second = inspect_source(source)
    assert first == second
    assert first.file_count == 2
    assert len({first.source_digest, first.model_digest, first.tokenizer_digest}) == 3


def test_source_inspection_rejects_arbitrary_bytes_with_safetensors_suffix(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    weights = source / "model.safetensors"
    tokenizer = source / "tokenizer.json"
    weights.write_bytes(b"not-a-safetensors-file")
    tokenizer.write_text("{}", encoding="utf-8")
    weights.chmod(0o444)
    tokenizer.chmod(0o444)
    source.chmod(0o555)
    with pytest.raises(ContractError, match="safe-structure inspection"):
        inspect_source(source)


def test_source_inspection_rejects_executable_serialization(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    weights = source / "model.safetensors"
    pickle_file = source / "pytorch_model.bin"
    weights.write_bytes(b"safe")
    pickle_file.write_bytes(b"not-executed")
    weights.chmod(0o444)
    pickle_file.chmod(0o444)
    source.chmod(0o555)
    with pytest.raises(ContractError, match="outside the safetensors envelope"):
        inspect_source(source)


def test_source_inspection_rejects_symlinked_directories(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "tokenizer.json").write_text("{}", encoding="utf-8")
    source = tmp_path / "source"
    source.mkdir()
    weights = source / "model.safetensors"
    weights.write_bytes(b"safe")
    (source / "linked").symlink_to(outside, target_is_directory=True)
    weights.chmod(0o444)
    source.chmod(0o555)
    with pytest.raises(RuntimeContractError, match="symbolic links") as error:
        inspect_source(source)
    assert error.value.code == "LMS_SOURCE_BOUNDARY_VIOLATION"


def test_source_inspection_enforces_byte_bounds_before_hashing(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    weights = source / "model.safetensors"
    tokenizer = source / "tokenizer.json"
    weights.write_bytes(b"12345")
    tokenizer.write_bytes(b"{}")
    weights.chmod(0o444)
    tokenizer.chmod(0o444)
    source.chmod(0o555)
    with pytest.raises(RuntimeContractError, match="configured byte bound") as error:
        inspect_source(source, max_file_bytes=4, max_total_bytes=10)
    assert error.value.code == "LMS_RESOURCE_ADMISSION_DENIED"


def test_source_inspection_enforces_exact_file_and_total_bounds(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    header = json.dumps(
        {"weight": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}},
        separators=(",", ":"),
    ).encode()
    weights = source / "model.safetensors"
    tokenizer = source / "tokenizer.json"
    weights.write_bytes(len(header).to_bytes(8, "little") + header + b"\0" * 4)
    tokenizer.write_text("{}", encoding="utf-8")
    total = weights.stat().st_size + tokenizer.stat().st_size
    weights.chmod(0o444)
    tokenizer.chmod(0o444)
    source.chmod(0o555)
    assert (
        inspect_source(source, max_files=2, max_total_bytes=total, max_file_bytes=total).file_count
        == 2
    )
    with pytest.raises(ContractError, match="file count"):
        inspect_source(source, max_files=1, max_total_bytes=total, max_file_bytes=total)
    with pytest.raises(ContractError, match="total-byte"):
        inspect_source(
            source,
            max_files=2,
            max_total_bytes=total - 1,
            max_file_bytes=total - 1,
        )


def test_source_inspection_timeout_is_deterministic_before_io(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    source.chmod(0o555)
    moments = iter((0.0, 0.0, 2.0))
    monkeypatch.setattr("obliteratus.distributed.preflight.time.monotonic", lambda: next(moments))
    with pytest.raises(RuntimeContractError, match="explicit timeout") as error:
        inspect_source(source, timeout_seconds=1)
    assert error.value.code == "LMS_STAGE_TIMEOUT"


def test_source_inspection_hard_deadline_interrupts_the_structural_inspector(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    weights = source / "model.safetensors"
    tokenizer = source / "tokenizer.json"
    weights.write_bytes(b"bounded")
    tokenizer.write_text("{}", encoding="utf-8")
    weights.chmod(0o444)
    tokenizer.chmod(0o444)
    source.chmod(0o555)

    def block(*args, **kwargs):
        time.sleep(5)
        raise AssertionError("deadline did not interrupt the inspector")

    monkeypatch.setattr("obliteratus.distributed.preflight.inspect_checkpoint", block)
    started = time.monotonic()
    with pytest.raises(RuntimeContractError) as error:
        inspect_source(source, timeout_seconds=1)
    assert error.value.code == "LMS_STAGE_TIMEOUT"
    assert time.monotonic() - started < 2


def test_checkout_commit_resolves_a_worktree_reference_without_a_child_process(tmp_path):
    checkout = tmp_path / "checkout"
    git_dir = tmp_path / "common" / "worktrees" / "candidate"
    common = tmp_path / "common"
    reference = common / "refs" / "heads" / "candidate"
    checkout.mkdir()
    git_dir.mkdir(parents=True)
    reference.parent.mkdir(parents=True)
    (checkout / ".git").write_text(f"gitdir: {git_dir}\n", encoding="utf-8")
    (git_dir / "HEAD").write_text("ref: refs/heads/candidate\n", encoding="utf-8")
    (git_dir / "commondir").write_text("../..\n", encoding="utf-8")
    reference.write_text("a" * 40 + "\n", encoding="utf-8")
    assert checkout_commit(checkout) == "a" * 40


def test_checkout_code_digest_changes_with_executable_source(tmp_path):
    package = tmp_path / "obliteratus"
    package.mkdir()
    module = package / "module.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")
    first = checkout_code_digest(tmp_path)
    module.write_text("VALUE = 2\n", encoding="utf-8")
    assert checkout_code_digest(tmp_path) != first


def test_storage_mount_digest_is_measured_and_stable(tmp_path):
    assert storage_mount_digest(tmp_path) == storage_mount_digest(tmp_path)


def test_network_interface_requires_allowlisted_address_and_coordinator_binding(
    monkeypatch,
):
    addresses = {"eth0": [SimpleNamespace(family=socket.AF_INET, address="10.10.0.10")]}
    monkeypatch.setattr("psutil.net_if_addrs", lambda: addresses)
    validate_network_interface("eth0", ("10.10.0.0/24",), "10.10.0.10", coordinator=True)
    with pytest.raises(ContractError, match="not bound"):
        validate_network_interface("eth0", ("10.10.0.0/24",), "10.10.0.11", coordinator=True)
