"""Bounded deterministic safetensors writer and transactional failure tests."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from jsonschema import Draft202012Validator
from safetensors.torch import load_file

import obliteratus.checkpoint_writer as writer_module
from obliteratus.checkpoint_errors import CheckpointContractError
from obliteratus.checkpoint_fixtures import load_fixture_case
from obliteratus.checkpoint_provenance import (
    ArtifactIdentity,
    LineageEvent,
    ToolIdentity,
    build_provenance,
)
from obliteratus.checkpoint_writer import (
    ImmutableCopy,
    VerifiedSourceFile,
    WriterLimits,
    write_canonical_checkpoint,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/distributed_checkpoints/v1/cases"
MANIFEST_SCHEMA = json.loads(
    (ROOT / "docs/checkpoints/schemas/conversion-manifest-v1.schema.json").read_text()
)
COMMIT = "c" * 40


def _digest_bytes(payload: bytes) -> str:
    return f"sha256:{sha256(payload).hexdigest()}"


def _digest_file(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _digest_file(path)
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def _inputs(
    tmp_path: Path,
    case_name: str = "world1-complete",
    *,
    source_topology: dict | None = None,
):
    case_root = FIXTURES / case_name
    case = load_fixture_case(case_root)
    sources = tuple(
        VerifiedSourceFile(
            path=path,
            relative_path=f"fixture/{case_name}/{path.name}",
            expected_sha256=_digest_file(path),
        )
        for path in sorted(item for item in case_root.iterdir() if item.is_file())
    )
    copy_root = tmp_path / "immutable-base"
    copy_root.mkdir(parents=True)
    config = copy_root / "config.json"
    tokenizer = copy_root / "tokenizer_config.json"
    config.write_text('{"architectures":["TinyModel"],"vocab_size":8}\n')
    tokenizer.write_text('{"model_max_length":128,"tokenizer_class":"Tiny"}\n')
    copies = (
        ImmutableCopy(
            relative_path="config.json",
            source_path=config,
            expected_sha256=_digest_file(config),
            kind="configuration",
        ),
        ImmutableCopy(
            relative_path="tokenizer_config.json",
            source_path=tokenizer,
            expected_sha256=_digest_file(tokenizer),
            kind="tokenizer",
        ),
    )
    input_digests = tuple(item.expected_sha256 for item in sources)

    def provenance_factory(output_digests: tuple[str, ...]):
        return build_provenance(
            sources=(
                ArtifactIdentity(
                    "local",
                    f"synthetic-fixture-{case_name}",
                    "v1",
                    _digest_bytes("".join(sorted(input_digests)).encode()),
                ),
            ),
            converter=ToolIdentity("obliteratus-neutral-writer", "1.0.0", COMMIT),
            obliteratus_commit=COMMIT,
            configuration_digest=copies[0].expected_sha256,
            tokenizer=ArtifactIdentity(
                "generated",
                "fixture-tokenizer",
                "v1",
                copies[1].expected_sha256,
            ),
            base_model=ArtifactIdentity(
                "generated",
                "fixture-base-model",
                "v1",
                copies[0].expected_sha256,
            ),
            command=("checkpoint", "write", f"fixture:{case_name}"),
            environment={"python": "test", "platform": "cpu", "packages": {}},
            source_topology=source_topology or {},
            lineage=(
                LineageEvent(
                    "event-consolidate",
                    "consolidation",
                    (),
                    "obliteratus-neutral-writer@1.0.0",
                    ("canonical_safetensors",),
                ),
            ),
            input_digests=input_digests,
            output_digests=output_digests,
            transformations=("canonical_safetensors", "consolidation"),
            observed_scopes=("model_weights",),
            lost_state=("optimizer_state", "scheduler_state", "rng_state"),
        )

    return case, sources, copies, provenance_factory


def _write(tmp_path: Path, destination: Path, **kwargs):
    source_topology = {"world_size": 1}
    case, sources, copies, provenance_factory = _inputs(
        tmp_path,
        kwargs.pop("case_name", "world1-complete"),
        source_topology=source_topology,
    )
    result = write_canonical_checkpoint(
        destination,
        case.fragments,
        source_files=sources,
        copies=copies,
        descriptor_digest=case.expected_manifest_digest,
        source_topology=source_topology,
        provenance_factory=provenance_factory,
        tie_policy="duplicate_validated",
        **kwargs,
    )
    return case, result


def test_writer_is_deterministic_sharded_reloadable_and_contract_valid(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    case, first_result = _write(
        tmp_path / "one",
        first,
        limits=WriterLimits(max_shard_bytes=32),
    )
    _, second_result = _write(
        tmp_path / "two",
        second,
        limits=WriterLimits(max_shard_bytes=32),
    )

    assert _tree(first) == _tree(second)
    assert first_result.artifact_id == second_result.artifact_id
    assert first_result.output_path == first.resolve()
    assert not (first / "pytorch_model.bin").exists()
    index = json.loads((first / "model.safetensors.index.json").read_text())
    assert list(index["weight_map"]) == sorted(index["weight_map"])
    assert len(set(index["weight_map"].values())) > 1
    loaded = {}
    for shard in sorted(set(index["weight_map"].values())):
        loaded.update(load_file(first / shard, device="cpu"))
    for logical_id, oracle in case.tensor_oracles.items():
        assert torch.equal(loaded[logical_id], oracle.values)
        assert str(loaded[logical_id].dtype).removeprefix("torch.") == oracle.dtype
    manifest = json.loads((first / "conversion-manifest.json").read_text())
    Draft202012Validator(MANIFEST_SCHEMA).validate(manifest)
    provenance = json.loads((first / "checkpoint-provenance.json").read_text())
    metadata = json.loads((first / "abliteration_metadata.json").read_text())
    assert manifest["manifest_id"] == provenance["artifact_id"] == metadata["artifact_id"]
    assert provenance["artifact_id"] == first_result.artifact_id
    assert manifest["validation"] == {
        "coverage": True,
        "replicas": True,
        "ties": True,
        "hashes": True,
        "index": True,
        "safe_reload": True,
        "source_unchanged": True,
        "result": "passed",
    }
    assert manifest["resource_usage"]["actual_peak_ram_bytes"] is None
    assert manifest["resource_usage"]["actual_temp_bytes"] is None


def test_single_shard_uses_canonical_direct_filename(tmp_path):
    case, result = _write(
        tmp_path / "work",
        tmp_path / "output",
        case_name="world2-uneven-1d",
        limits=WriterLimits(max_shard_bytes=1024),
    )

    assert result.weight_files == ("model.safetensors",)
    assert not (result.output_path / "model.safetensors.index.json").exists()
    loaded = load_file(result.output_path / "model.safetensors", device="cpu")
    assert torch.equal(loaded["model.weight"], case.tensor_oracles["model.weight"].values)


def test_writer_refuses_ties_without_an_explicit_validated_policy(tmp_path):
    case, sources, copies, provenance_factory = _inputs(tmp_path)

    with pytest.raises(CheckpointContractError) as caught:
        write_canonical_checkpoint(
            tmp_path / "output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=provenance_factory,
        )

    assert caught.value.code == "DCI_VALIDATION_FAILED"
    assert caught.value.detail == "tie_policy_required"


def test_admission_denial_creates_no_staging_or_output(tmp_path, monkeypatch):
    case, sources, copies, provenance_factory = _inputs(tmp_path)
    destination = tmp_path / "output"

    def forbidden_transaction(*_args, **_kwargs):
        raise AssertionError("staging began before admission")

    monkeypatch.setattr(writer_module, "atomic_checkpoint_directory", forbidden_transaction)
    with pytest.raises(CheckpointContractError) as caught:
        write_canonical_checkpoint(
            destination,
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=provenance_factory,
            tie_policy="duplicate_validated",
            limits=WriterLimits(max_output_bytes=1),
        )

    assert caught.value.code == "DCI_ADMISSION_DENIED"
    assert caught.value.detail == "max_output_bytes"
    assert not destination.exists()
    assert list(tmp_path.glob(".output.staging-*")) == []


def test_copy_and_source_digests_are_verified_before_staging(tmp_path):
    case, sources, copies, provenance_factory = _inputs(tmp_path)
    copies[0].source_path.write_text("changed\n")

    with pytest.raises(CheckpointContractError) as caught:
        write_canonical_checkpoint(
            tmp_path / "output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=provenance_factory,
            tie_policy="duplicate_validated",
        )

    assert caught.value.code == "DCI_SOURCE_CHANGED"
    assert not (tmp_path / "output").exists()


def test_enospc_preserves_source_and_prior_output_and_cleans_staging(tmp_path, monkeypatch):
    case, sources, copies, provenance_factory = _inputs(tmp_path)
    destination = tmp_path / "output"
    destination.mkdir()
    sentinel = destination / "sentinel"
    sentinel.write_text("prior")
    source_before = {item.relative_path: _digest_file(item.path) for item in sources}

    def enospc(_tensors, path):
        path.write_bytes(b"partial")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(writer_module, "_save_safetensors_file", enospc)
    with pytest.raises(CheckpointContractError) as caught:
        write_canonical_checkpoint(
            destination,
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=provenance_factory,
            tie_policy="duplicate_validated",
        )

    assert caught.value.code == "DCI_MATERIALIZE_FAILED"
    assert sentinel.read_text() == "prior"
    assert {item.relative_path: _digest_file(item.path) for item in sources} == source_before
    assert list(tmp_path.glob(".output.staging-*")) == []
    assert list(tmp_path.glob(".output.backup-*")) == []


def test_cancellation_preserves_prior_output_and_cleans_staging(tmp_path, monkeypatch):
    class Cancelled(BaseException):
        pass

    case, sources, copies, provenance_factory = _inputs(tmp_path)
    destination = tmp_path / "output"
    destination.mkdir()
    (destination / "sentinel").write_text("prior")

    def cancel(_tensors, _path):
        raise Cancelled()

    monkeypatch.setattr(writer_module, "_save_safetensors_file", cancel)
    with pytest.raises(Cancelled):
        write_canonical_checkpoint(
            destination,
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=provenance_factory,
            tie_policy="duplicate_validated",
        )

    assert (destination / "sentinel").read_text() == "prior"
    assert list(tmp_path.glob(".output.staging-*")) == []


def test_postwrite_validation_failure_never_promotes(tmp_path, monkeypatch):
    case, sources, copies, provenance_factory = _inputs(tmp_path)
    destination = tmp_path / "output"
    destination.mkdir()
    (destination / "sentinel").write_text("prior")

    def reject(*_args, **_kwargs):
        raise CheckpointContractError(
            "DCI_VALIDATION_FAILED",
            detail="injected_postwrite_failure",
        )

    monkeypatch.setattr(writer_module, "_verify_staging", reject)
    with pytest.raises(CheckpointContractError) as caught:
        write_canonical_checkpoint(
            destination,
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=provenance_factory,
            tie_policy="duplicate_validated",
        )

    assert caught.value.detail == "injected_postwrite_failure"
    assert (destination / "sentinel").read_text() == "prior"
    assert list(tmp_path.glob(".output.staging-*")) == []


@pytest.mark.parametrize("target", ["index", "manifest"])
def test_corrupt_index_or_manifest_is_rejected_before_promotion(
    tmp_path,
    monkeypatch,
    target,
):
    case, sources, copies, provenance_factory = _inputs(
        tmp_path / "inputs",
        source_topology={},
    )
    original = writer_module._write_json

    def corrupt(path, value):
        if target == "index" and path.name == "model.safetensors.index.json":
            value = {"metadata": {"total_size": 0}, "weight_map": value["weight_map"]}
        if target == "manifest" and path.name == "conversion-manifest.json":
            value = {**value, "source_topology": {"tampered": True}}
        return original(path, value)

    monkeypatch.setattr(writer_module, "_write_json", corrupt)
    with pytest.raises(CheckpointContractError) as caught:
        write_canonical_checkpoint(
            tmp_path / "output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=provenance_factory,
            tie_policy="duplicate_validated",
            limits=WriterLimits(max_shard_bytes=32),
        )
    assert caught.value.code == "DCI_VALIDATION_FAILED"
    assert caught.value.detail == (
        "output_index_mismatch" if target == "index" else "output_manifest_mismatch"
    )
    assert not (tmp_path / "output").exists()


def _invoke(tmp_path, *, source_files=None, copies=None, factory=None, **kwargs):
    source_topology = {"world_size": 1}
    case, default_sources, default_copies, default_factory = _inputs(
        tmp_path / "inputs",
        source_topology=source_topology,
    )
    return write_canonical_checkpoint(
        tmp_path / "output",
        case.fragments,
        source_files=default_sources if source_files is None else source_files,
        copies=default_copies if copies is None else copies,
        descriptor_digest=case.expected_manifest_digest,
        source_topology=source_topology,
        provenance_factory=default_factory if factory is None else factory,
        tie_policy="duplicate_validated",
        **kwargs,
    )


def test_writer_limit_and_input_records_validate_before_io(tmp_path):
    with pytest.raises(ValueError, match="positive integer"):
        WriterLimits(max_shard_bytes=0)
    with pytest.raises(ValueError, match="cannot exceed 100"):
        WriterLimits(min_free_headroom_percent=101)
    with pytest.raises(ValueError, match="relative path is unsafe"):
        VerifiedSourceFile(tmp_path / "source", "../source", "sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="sha256 digest"):
        VerifiedSourceFile(tmp_path / "source", "source", "bad")
    with pytest.raises(ValueError, match="root-level"):
        ImmutableCopy("nested/config.json", tmp_path / "config", "sha256:" + "0" * 64, "configuration")
    with pytest.raises(ValueError, match="configuration or tokenizer"):
        ImmutableCopy("config.json", tmp_path / "config", "sha256:" + "0" * 64, "other")


def test_writer_rejects_missing_duplicate_or_incomplete_evidence(tmp_path):
    with pytest.raises(CheckpointContractError) as empty:
        _invoke(tmp_path / "empty", source_files=())
    assert empty.value.detail == "source_inventory_empty"

    case, sources, copies, factory = _inputs(tmp_path / "duplicate-inputs")
    duplicate_source = (*sources, sources[0])
    with pytest.raises(ValueError, match="source relative paths must be unique"):
        write_canonical_checkpoint(
            tmp_path / "duplicate-source-output",
            case.fragments,
            source_files=duplicate_source,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )

    with pytest.raises(ValueError, match="copy output paths must be unique"):
        write_canonical_checkpoint(
            tmp_path / "duplicate-copy-output",
            case.fragments,
            source_files=sources,
            copies=(*copies, copies[0]),
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )

    with pytest.raises(CheckpointContractError) as missing_copy:
        write_canonical_checkpoint(
            tmp_path / "missing-copy-output",
            case.fragments,
            source_files=sources,
            copies=(copies[0],),
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )
    assert missing_copy.value.detail == "canonical_config_or_tokenizer_missing"


@pytest.mark.parametrize(
    ("limits", "detail"),
    [
        (WriterLimits(max_temp_bytes=1), "max_temp_bytes"),
        (WriterLimits(max_peak_ram_bytes=1), "max_peak_ram_bytes"),
    ],
)
def test_every_writer_admission_limit_fails_before_staging(tmp_path, limits, detail):
    with pytest.raises(CheckpointContractError) as caught:
        _invoke(tmp_path, limits=limits)
    assert caught.value.code == "DCI_ADMISSION_DENIED"
    assert caught.value.detail == detail
    assert not (tmp_path / "output").exists()


def test_tensor_larger_than_configured_shard_limit_is_refused(tmp_path):
    with pytest.raises(CheckpointContractError) as caught:
        _invoke(tmp_path, limits=WriterLimits(max_shard_bytes=1))
    assert caught.value.code == "DCI_ADMISSION_DENIED"
    assert caught.value.detail == "tensor_exceeds_max_shard_bytes"
    assert not (tmp_path / "output").exists()


def test_post_write_size_limit_is_rechecked_before_promotion(tmp_path, monkeypatch):
    monkeypatch.setattr(
        writer_module,
        "_admit",
        lambda *_args, **_kwargs: writer_module._Admission(0, 0, 0, 0),
    )
    with pytest.raises(CheckpointContractError) as caught:
        _invoke(
            tmp_path,
            limits=WriterLimits(max_output_bytes=1, max_temp_bytes=1),
        )
    assert caught.value.code == "DCI_ADMISSION_DENIED"
    assert caught.value.detail == "post_write_size_limit"
    assert not (tmp_path / "output").exists()


def test_filesystem_admission_and_destination_symlink_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(writer_module.shutil, "disk_usage", lambda _path: SimpleNamespace(free=0))
    with pytest.raises(CheckpointContractError) as capacity:
        _invoke(tmp_path / "capacity")
    assert capacity.value.detail == "filesystem_free_bytes"

    parent_target = tmp_path / "parent-target"
    parent_target.mkdir()
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(parent_target, target_is_directory=True)
    case, sources, copies, factory = _inputs(tmp_path / "symlink-inputs")
    with pytest.raises(CheckpointContractError) as boundary:
        write_canonical_checkpoint(
            parent_link / "output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )
    assert boundary.value.detail == "destination_symlink"


def test_source_ancestor_symlink_and_open_race_fail_before_staging(tmp_path, monkeypatch):
    actual = tmp_path / "actual"
    case, sources, copies, factory = _inputs(actual)
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    aliased_sources = (
        VerifiedSourceFile(
            alias / copies[0].source_path.relative_to(actual),
            "source/config.json",
            copies[0].expected_sha256,
        ),
    )

    with pytest.raises(CheckpointContractError) as symlink:
        write_canonical_checkpoint(
            tmp_path / "symlink-output",
            case.fragments,
            source_files=aliased_sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )
    assert symlink.value.code == "DCI_SOURCE_BOUNDARY_VIOLATION"
    assert symlink.value.detail == "source_symlink"

    real_open = writer_module.os.open
    blocked_path = sources[0].path

    def fail_observed_open(path, flags):
        if Path(path) == blocked_path:
            raise OSError("injected source replacement")
        return real_open(path, flags)

    monkeypatch.setattr(writer_module.os, "open", fail_observed_open)
    with pytest.raises(CheckpointContractError) as changed:
        write_canonical_checkpoint(
            tmp_path / "race-output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )
    assert changed.value.code == "DCI_SOURCE_CHANGED"
    assert not list(tmp_path.glob(".race-output.staging-*"))


def test_source_missing_and_nonregular_inputs_fail_before_staging(tmp_path):
    case, sources, copies, factory = _inputs(tmp_path / "source-inputs")
    sources = (
        VerifiedSourceFile(
            tmp_path / "missing-source",
            sources[0].relative_path,
            sources[0].expected_sha256,
        ),
        *sources[1:],
    )
    with pytest.raises(CheckpointContractError) as missing:
        write_canonical_checkpoint(
            tmp_path / "missing-output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )
    assert missing.value.code == "DCI_SOURCE_CHANGED"

    case, sources, copies, factory = _inputs(tmp_path / "directory-inputs")
    source_directory = tmp_path / "source-directory"
    source_directory.mkdir()
    sources = (
        VerifiedSourceFile(
            source_directory,
            sources[0].relative_path,
            sources[0].expected_sha256,
        ),
        *sources[1:],
    )
    with pytest.raises(CheckpointContractError) as nonregular:
        write_canonical_checkpoint(
            tmp_path / "directory-output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology={},
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )
    assert nonregular.value.detail == "source_not_regular_file"


@pytest.mark.parametrize(
    ("record", "detail"),
    [
        ({}, "provenance_contract_invalid"),
        (
            {
                "schema_id": "obliteratus.artifact-provenance",
                "output_digests": [],
                "record_digest": "bad",
            },
            "provenance_contract_invalid",
        ),
    ],
)
def test_provenance_contract_failures_never_promote(tmp_path, record, detail):
    fake = SimpleNamespace(artifact_id="artifact-sha256:" + "0" * 64, to_dict=lambda: record)
    with pytest.raises(CheckpointContractError) as caught:
        _invoke(tmp_path, factory=lambda _digests: fake)
    assert caught.value.code == "DCI_EVIDENCE_UNAVAILABLE"
    assert caught.value.detail == detail
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    ("mismatch", "detail"),
    [
        ("input", "provenance_input_digest_mismatch"),
        ("configuration", "provenance_configuration_digest_mismatch"),
        ("topology", "provenance_source_topology_mismatch"),
    ],
)
def test_writer_binds_source_config_and_topology_to_provenance(
    tmp_path,
    mismatch,
    detail,
):
    source_topology = {"world_size": 1}
    case, sources, copies, _ = _inputs(
        tmp_path / "inputs",
        source_topology=source_topology,
    )
    source_digests = tuple(item.expected_sha256 for item in sources)

    def factory(output_digests):
        return build_provenance(
            sources=(ArtifactIdentity("local", "fixture", "v1", source_digests[0]),),
            converter=ToolIdentity("writer", "1", COMMIT),
            obliteratus_commit=COMMIT,
            configuration_digest=(
                "sha256:" + "f" * 64
                if mismatch == "configuration"
                else copies[0].expected_sha256
            ),
            tokenizer=None,
            base_model=None,
            command=("checkpoint", "write"),
            environment={"python": "test", "platform": "cpu", "packages": {}},
            source_topology=(
                {"world_size": 2} if mismatch == "topology" else source_topology
            ),
            lineage=(),
            input_digests=(
                ("sha256:" + "e" * 64,)
                if mismatch == "input"
                else source_digests
            ),
            output_digests=output_digests,
            transformations=("canonical_safetensors",),
            observed_scopes=("model_weights",),
            lost_state=(),
        )

    with pytest.raises(CheckpointContractError) as caught:
        write_canonical_checkpoint(
            tmp_path / "output",
            case.fragments,
            source_files=sources,
            copies=copies,
            descriptor_digest=case.expected_manifest_digest,
            source_topology=source_topology,
            provenance_factory=factory,
            tie_policy="duplicate_validated",
        )
    assert caught.value.code == "DCI_EVIDENCE_UNAVAILABLE"
    assert caught.value.detail == detail
    assert not (tmp_path / "output").exists()


def test_provenance_factory_and_promotion_errors_are_stable(tmp_path, monkeypatch):
    with pytest.raises(CheckpointContractError) as factory_error:
        _invoke(tmp_path / "factory", factory=lambda _digests: (_ for _ in ()).throw(RuntimeError("boom")))
    assert factory_error.value.detail == "provenance_factory_failed"

    def promotion_failure(*_args, **_kwargs):
        raise OSError("promotion unavailable")

    monkeypatch.setattr(writer_module, "atomic_checkpoint_directory", promotion_failure)
    with pytest.raises(CheckpointContractError) as promotion:
        _invoke(tmp_path / "promotion")
    assert promotion.value.code == "DCI_PROMOTION_FAILED"


def test_output_json_and_file_record_validation_rejects_unsafe_artifacts(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(CheckpointContractError, match="output_json_invalid"):
        writer_module._verify_json_object(missing)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(CheckpointContractError, match="output_json_invalid"):
        writer_module._verify_json_object(malformed)

    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")
    with pytest.raises(CheckpointContractError, match="output_json_invalid"):
        writer_module._verify_json_object(array)

    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(CheckpointContractError, match="output_not_regular_file"):
        writer_module._output_record(directory)
