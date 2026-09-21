"""Deterministic, project-owned distributed-checkpoint fixture corpus."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import shutil

import pytest
import torch

from obliteratus.checkpoint_fixtures import load_fixture_case
from obliteratus.checkpoint_fragments import reconstruct_logical_tensor, validate_fragments
from scripts.generate_checkpoint_fixtures import generate_corpus


ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "tests/fixtures/distributed_checkpoints/v1"


def _tree_digest(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _manifest(root: Path = COMMITTED) -> dict:
    value = json.loads((root / "fixture-corpus.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_generator_is_byte_deterministic_and_committed_corpus_is_current(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    generate_corpus(first)
    generate_corpus(second)

    assert _tree_digest(first) == _tree_digest(second)
    assert _tree_digest(first) == _tree_digest(COMMITTED)


def test_manifest_is_project_owned_self_hashing_and_bounded():
    manifest = _manifest()

    assert manifest["schema_id"] == "obliteratus.checkpoint-fixture-corpus"
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["generator"] == {
        "path": "scripts/generate_checkpoint_fixtures.py",
        "version": "1.0.0",
    }
    assert manifest["license"] == "AGPL-3.0-or-later"
    assert manifest["provenance"] == {
        "kind": "deterministic_synthetic",
        "seed": 0,
        "third_party_data": False,
        "third_party_weights": False,
    }
    assert manifest["limits"] == {
        "max_case_bytes": 65536,
        "max_cases": 16,
        "max_files_per_case": 16,
        "max_tensors_per_case": 16,
    }
    assert len(manifest["cases"]) <= manifest["limits"]["max_cases"]
    for case in manifest["cases"]:
        case_root = COMMITTED / case["relative_path"]
        assert len(case["files"]) <= manifest["limits"]["max_files_per_case"]
        assert sum(item["size_bytes"] for item in case["files"]) <= manifest["limits"][
            "max_case_bytes"
        ]
        for item in case["files"]:
            payload = (case_root / item["relative_path"]).read_bytes()
            assert len(payload) == item["size_bytes"]
            assert f"sha256:{sha256(payload).hexdigest()}" == item["sha256"]


def test_valid_cases_cover_wave_two_neutral_topologies_and_features():
    cases = _manifest()["cases"]

    assert {case["world_size"] for case in cases} == {1, 2, 4}
    assert {case["case_id"] for case in cases} == {
        "mixed-model-peft",
        "tp2-pp2-to-single",
        "world1-complete",
        "world2-uneven-1d",
        "world4-dp-replicas",
        "world4-uneven-2d",
    }
    features = {feature for case in cases for feature in case["features"]}
    assert {
        "buffer",
        "dp_replica",
        "expert",
        "mixed_full_model_peft",
        "padding",
        "pipeline_parallel",
        "scalar",
        "tied_weight",
        "topology_a_to_b",
        "uneven_1d",
        "uneven_2d",
    } <= features


def test_every_valid_case_reconstructs_the_independent_value_oracle():
    for case_record in _manifest()["cases"]:
        case = load_fixture_case(COMMITTED / case_record["relative_path"])
        result = validate_fragments(case.fragments)

        assert result.manifest_digest == case.expected_manifest_digest
        assert len(result.logical_tensors) <= _manifest()["limits"]["max_tensors_per_case"]
        for logical_tensor_id, oracle in case.tensor_oracles.items():
            tensor = reconstruct_logical_tensor(result, logical_tensor_id)
            assert tuple(tensor.shape) == oracle.shape
            assert str(tensor.dtype).removeprefix("torch.") == oracle.dtype
            assert torch.equal(tensor, oracle.values)
            raw = tensor.contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
            assert f"sha256:{sha256(raw).hexdigest()}" == oracle.sha256


def test_negative_catalog_covers_each_required_corruption_family():
    catalog = json.loads((COMMITTED / "negative-cases.json").read_text(encoding="utf-8"))

    assert catalog["schema_id"] == "obliteratus.checkpoint-negative-fixtures"
    assert {case["failure"] for case in catalog["cases"]} == {
        "dimension_mismatch",
        "extra_shard",
        "fragment_out_of_bounds",
        "integer_overflow",
        "missing_shard",
        "negative_integer",
        "padding_shape_mismatch",
        "path_traversal",
        "payload_dtype_mismatch",
        "payload_shape_mismatch",
        "replica_digest_mismatch",
        "resource_manifest_bomb",
        "source_special_file",
        "source_symlink",
        "truncated_shard",
        "coverage_gap",
        "coverage_overlap",
    }
    assert all(case["expected_code"].startswith("DCI_") for case in catalog["cases"])


def _mutable_case(tmp_path: Path) -> Path:
    destination = tmp_path / "case"
    shutil.copytree(COMMITTED / "cases/world1-complete", destination)
    return destination


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda record: record.update(schema_id="unknown"), "unsupported fixture case schema"),
        (lambda record: record.update(fragments={}), "fragment list is invalid"),
        (lambda record: record.update(fragments=[None]), "fragment must be an object"),
        (
            lambda record: record["fragments"][0].update(payload_file="../escape"),
            "unsafe fixture payload file",
        ),
        (
            lambda record: record["fragments"][0].update(payload_key="missing"),
            "fixture payload key is missing",
        ),
    ],
)
def test_fixture_loader_rejects_invalid_case_contracts(tmp_path, mutate, message):
    case = _mutable_case(tmp_path)
    record = json.loads((case / "case.json").read_text(encoding="utf-8"))
    mutate(record)
    (case / "case.json").write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_fixture_case(case)


def test_fixture_loader_rejects_non_object_oversized_and_nonregular_json(tmp_path):
    case = _mutable_case(tmp_path)
    (case / "case.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="not an object"):
        load_fixture_case(case)

    (case / "case.json").write_bytes(b" " * (256 * 1024 + 1))
    with pytest.raises(ValueError, match="exceeds"):
        load_fixture_case(case)

    (case / "case.json").unlink()
    (case / "case.json").mkdir()
    with pytest.raises(ValueError, match="not a regular file"):
        load_fixture_case(case)


def test_fixture_loader_rejects_symlink_root(tmp_path):
    link = tmp_path / "linked"
    link.symlink_to(COMMITTED / "cases/world1-complete", target_is_directory=True)

    with pytest.raises(ValueError, match="non-symlink directory"):
        load_fixture_case(link)
