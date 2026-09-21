"""Executable Draft 2020-12 checks for distributed-checkpoint contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs/checkpoints/schemas"
FIXTURES = CONTRACTS / "fixtures/v1"


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _validators() -> dict[str, Draft202012Validator]:
    result = {}
    for path in sorted(CONTRACTS.glob("*.schema.json")):
        schema = _load(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema["properties"]["schema_id"]["const"]
        assert schema_id not in result
        result[schema_id] = Draft202012Validator(schema, format_checker=FormatChecker())
    return result


def test_every_checkpoint_schema_is_valid_and_has_a_unique_contract_id():
    validators = _validators()
    assert {
        "obliteratus.adapter-capability",
        "obliteratus.checkpoint-descriptor",
        "obliteratus.checkpoint-error-registry",
        "obliteratus.checkpoint-support-matrix",
        "obliteratus.checkpoint-trust-policy",
        "obliteratus.conversion-manifest",
        "obliteratus.trusted-worker-message",
    } <= set(validators)


@pytest.mark.parametrize("path", sorted((FIXTURES / "valid").glob("*.json")))
def test_declared_valid_contract_fixture_passes(path):
    instance = _load(path)
    _validators()[instance["schema_id"]].validate(instance)


@pytest.mark.parametrize("path", sorted((FIXTURES / "invalid").glob("*.json")))
def test_declared_invalid_contract_fixture_fails(path):
    instance = _load(path)
    errors = list(_validators()[instance["schema_id"]].iter_errors(instance))
    assert errors


def test_trust_policy_forbids_persisted_environment_or_secret_fields():
    policy = _load(FIXTURES / "valid/trusted-metadata-policy.json")
    policy["environment"] = {"TOKEN": "must-not-persist"}

    errors = list(_validators()[policy["schema_id"]].iter_errors(policy))

    assert any("Additional properties are not allowed" in error.message for error in errors)


def test_support_matrix_and_error_registry_validate_against_their_schemas():
    validators = _validators()
    for path in (
        ROOT / "docs/checkpoints/support-matrix-v1.json",
        CONTRACTS / "checkpoint-error-codes-v1.json",
    ):
        instance = _load(path)
        validators[instance["schema_id"]].validate(instance)


def test_error_registry_covers_every_fail_closed_degraded_mode_once_or_more():
    registry = _load(CONTRACTS / "checkpoint-error-codes-v1.json")
    entries = registry["entries"]
    assert len({entry["code"] for entry in entries}) == len(entries)
    covered = {mode for entry in entries for mode in entry["degraded_modes"]}
    assert covered == {f"F{number:02d}" for number in range(1, 21)}


def test_descriptor_blockers_accept_the_canonical_error_registry_vocabulary():
    descriptor = _load(CONTRACTS / "checkpoint-descriptor-v1.schema.json")
    registry = _load(CONTRACTS / "checkpoint-error-codes-v1.json")
    blocker = descriptor["$defs"]["blocker"]["properties"]

    assert {entry["category"] for entry in registry["entries"]} <= set(
        blocker["category"]["enum"]
    )
    assert {entry["phase"] for entry in registry["entries"]} <= set(blocker["phase"]["enum"])


def test_descriptor_can_name_legacy_hf_pickle_without_treating_it_as_safetensors():
    descriptor = _load(CONTRACTS / "checkpoint-descriptor-v1.schema.json")

    assert "hf_pytorch_pickle" in descriptor["$defs"]["checkpointFormat"]["enum"]
