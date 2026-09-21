"""Versioned checkpoint provenance, lineage, and resume-state truth tests."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from obliteratus.checkpoint_provenance import (
    AdapterIdentity,
    ArtifactIdentity,
    DatasetIdentity,
    LineageEvent,
    ProvenanceRecord,
    ToolIdentity,
    TrainingIdentity,
    build_provenance,
    classify_resume_state,
    migrate_legacy_metadata,
    sanitize_command,
    verify_provenance_record,
)
from obliteratus.run_archive import RunArchive


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "docs/checkpoints/schemas/artifact-provenance-v1.schema.json").read_text()
)
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
COMMIT = "c" * 40


def _record(*, output_digests=(DIGEST_B,), command=("checkpoint", "convert")):
    base = ArtifactIdentity("hub", "org/base", "0123456789abcdef", DIGEST_A)
    return build_provenance(
        sources=(ArtifactIdentity("local", "content-addressed-source", None, DIGEST_A),),
        converter=ToolIdentity("obliteratus-neutral-writer", "1.0.0", COMMIT),
        obliteratus_commit=COMMIT,
        configuration_digest=DIGEST_A,
        tokenizer=ArtifactIdentity("hub", "org/base", "0123456789abcdef", DIGEST_B),
        base_model=base,
        command=command,
        environment={"python": "3.12.7", "platform": "linux", "packages": {"torch": "2.5"}},
        source_topology={"world_size": 4, "tp": 2, "pp": 2},
        lineage=(
            LineageEvent(
                event_id="event-consolidation",
                event_type="consolidation",
                parent_artifact_ids=("artifact-sha256:" + "d" * 64,),
                tool="obliteratus-neutral-writer@1.0.0",
                transformations=("deduplicate_declared_replicas",),
            ),
        ),
        input_digests=(DIGEST_A,),
        output_digests=output_digests,
        transformations=("consolidation", "canonical_safetensors"),
        observed_scopes=("model_weights",),
        lost_state=("optimizer_state", "scheduler_state"),
        adapter=AdapterIdentity(
            adapter_type="lora",
            base_model=base,
            config_digest=DIGEST_B,
            key_map_digest=DIGEST_A,
        ),
        dataset=DatasetIdentity(
            identifier="dataset/name",
            revision="rev-1",
            digest=DIGEST_A,
            split="train",
            subset=None,
            record_count=42,
        ),
        training=TrainingIdentity(
            method="adapter_train",
            framework="transformers",
            framework_version="4.60.0",
            hyperparameters_digest=DIGEST_B,
        ),
        unknowns=("optimizer_producer_version",),
    )


def test_provenance_is_strict_versioned_canonical_and_content_addressed():
    record = _record()
    payload = record.to_dict()

    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["schema_id"] == "obliteratus.artifact-provenance"
    assert payload["schema_version"] == "1.0.0"
    assert payload["artifact_id"].startswith("artifact-sha256:")
    assert payload["record_digest"].startswith("sha256:")
    assert json.loads(record.to_json()) == payload
    assert record.artifact_id == _record().artifact_id
    assert record.to_json() == _record().to_json()


def test_canonical_sets_and_maps_do_not_depend_on_caller_order():
    first = _record(output_digests=(DIGEST_A, DIGEST_B))
    second = _record(output_digests=(DIGEST_B, DIGEST_A))

    assert first.artifact_id == second.artifact_id
    assert first.to_json() == second.to_json()


@pytest.mark.parametrize(
    ("scopes", "expected"),
    [
        (("model_weights",), "weights_only"),
        (("model_weights", "optimizer_state"), "model_and_optimizer"),
        (
            (
                "model_weights",
                "optimizer_state",
                "scheduler_state",
                "rng_state",
                "dataloader_state",
                "framework_state",
            ),
            "exact_resume",
        ),
        (("optimizer_state",), "unknown"),
        ((), "unknown"),
    ],
)
def test_resume_classification_is_derived_only_from_observed_state(scopes, expected):
    assert classify_resume_state(scopes) == expected


def test_lineage_vocabulary_keeps_surgery_distinct_from_finetuning():
    allowed = {
        "consolidation",
        "reshard",
        "pretrain",
        "full_finetune",
        "adapter_train",
        "adapter_merge",
        "quantization",
        "dequantization",
        "surgery",
    }

    for event_type in allowed:
        assert LineageEvent("event", event_type, (), "tool@1", ()).event_type == event_type
    with pytest.raises(ValueError, match="lineage event type"):
        LineageEvent("event", "finetuning_surgery", (), "tool@1", ())


def test_command_redacts_secrets_prompts_and_private_paths():
    sanitized = sanitize_command(
        (
            "checkpoint",
            "convert",
            "/home/alice/private/model",
            "--token",
            "hf_abcdefghijklmnopqrstuvwxyz",
            "--prompt=raw private prompt",
        )
    )
    rendered = json.dumps(sanitized)

    assert "/home/alice" not in rendered
    assert "hf_" not in rendered
    assert "raw private prompt" not in rendered
    assert "[REDACTED]" in sanitized
    assert any(value.startswith("[LOCAL_PATH:sha256:") for value in sanitized)


def test_legacy_migration_preserves_declared_facts_and_never_invents_digests():
    facts = migrate_legacy_metadata(
        {
            "model": "org/base",
            "model_revision": "rev-1",
            "tokenizer_revision": None,
            "seed": "42",
            "dataset_inputs": [{"identifier": "builtin", "sha256": "e" * 64}],
            "unmapped_private_field": "must not leak",
        }
    )
    payload = facts.to_dict()

    assert payload["base_model"] == {
        "identity": "org/base",
        "revision": "rev-1",
        "digest": None,
    }
    assert payload["tokenizer"] == {"revision": None, "digest": None}
    assert payload["seed"] == "42"
    assert payload["datasets"] == [
        {"identifier": "builtin", "digest": "sha256:" + "e" * 64}
    ]
    assert "unmapped_private_field" not in json.dumps(payload)
    assert "base_model_digest" in payload["unknowns"]
    assert "tokenizer_digest" in payload["unknowns"]


def test_run_archive_attaches_same_artifact_identity_without_raw_sensitive_data(tmp_path):
    archive = RunArchive(tmp_path)
    run_id = archive.begin(["org/base"])
    record = _record(
        command=("convert", "/home/alice/private/model", "--token", "hf_secretsecretsecret")
    )

    manifest = archive.attach_checkpoint_provenance(run_id, record)
    provenance_path = tmp_path / run_id / "checkpoint-provenance.json"
    raw = provenance_path.read_text(encoding="utf-8")

    assert manifest["artifact_id"] == record.artifact_id
    assert manifest["checkpoint_provenance"]["artifact_id"] == record.artifact_id
    assert json.loads(raw)["artifact_id"] == record.artifact_id
    assert "/home/alice" not in raw
    assert "hf_secret" not in raw


def test_provenance_rejects_secret_bearing_environment_keys():
    with pytest.raises(ValueError, match="sensitive key"):
        build_provenance(
            sources=(ArtifactIdentity("local", "source", None, DIGEST_A),),
            converter=ToolIdentity("writer", "1", COMMIT),
            obliteratus_commit=COMMIT,
            configuration_digest=None,
            tokenizer=None,
            base_model=None,
            command=("convert",),
            environment={"API_TOKEN": "secret"},
            source_topology={},
            lineage=(),
            input_digests=(DIGEST_A,),
            output_digests=(DIGEST_B,),
            transformations=(),
            observed_scopes=("model_weights",),
            lost_state=(),
        )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: ArtifactIdentity("other", "source", None, DIGEST_A), "kind is invalid"),
        (lambda: ArtifactIdentity("local", "", None, DIGEST_A), "non-empty bounded"),
        (
            lambda: ArtifactIdentity("local", "hf_abcdefghijklmnopqrstuvwxyz", None, DIGEST_A),
            "contains a secret",
        ),
        (lambda: ArtifactIdentity("local", "/private/source", None, DIGEST_A), "private local path"),
        (lambda: ArtifactIdentity("local", "source", None, "bad"), "sha256 digest"),
        (lambda: ToolIdentity("tool", "1", "A" * 40), "40-character lowercase commit"),
        (
            lambda: LineageEvent("event", "surgery", ("bad-parent",), "tool@1", ()),
            "parent artifact ID",
        ),
        (
            lambda: DatasetIdentity("dataset", None, DIGEST_A, None, None, -1),
            "record count",
        ),
        (lambda: TrainingIdentity("invalid", None, None, None), "training method"),
        (lambda: TrainingIdentity("unknown", None, None, "bad"), "sha256 digest"),
    ],
)
def test_identity_records_reject_unverifiable_or_sensitive_fields(factory, message):
    with pytest.raises(ValueError, match=message):
        factory()


def _minimal_provenance(**overrides):
    values = {
        "sources": (ArtifactIdentity("local", "source", None, DIGEST_A),),
        "converter": ToolIdentity("writer", "1", COMMIT),
        "obliteratus_commit": COMMIT,
        "configuration_digest": None,
        "tokenizer": None,
        "base_model": None,
        "command": ("convert",),
        "environment": {"python": "3.12", "platform": "linux", "packages": {}},
        "source_topology": {},
        "lineage": (),
        "input_digests": (DIGEST_A,),
        "output_digests": (DIGEST_B,),
        "transformations": (),
        "observed_scopes": ("model_weights",),
        "lost_state": (),
    }
    values.update(overrides)
    return build_provenance(**values)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"sources": ()}, "at least one source"),
        ({"configuration_digest": "bad"}, "sha256 digest"),
        ({"environment": {"python": "3", "platform": "linux", "packages": {}, "extra": 1}}, "unsupported fields"),
        ({"source_topology": {"rank": 1 << 64}}, "outside int64"),
        ({"source_topology": {"path": "/private/checkpoint"}}, "private local path"),
        ({"source_topology": {"note": "hf_abcdefghijklmnopqrstuvwxyz"}}, "contains a secret"),
        ({"source_topology": {1: "value"}}, "non-string key"),
        ({"source_topology": {"prompt_text": "value"}}, "sensitive key"),
        ({"source_topology": {"opaque": object()}}, "non-JSON value"),
        ({"input_digests": ("bad",)}, "sha256 digest"),
    ],
)
def test_provenance_builder_rejects_incomplete_or_unsafe_evidence(overrides, message):
    with pytest.raises(ValueError, match=message):
        _minimal_provenance(**overrides)


def test_normalization_accepts_explicit_json_scalars_and_sequences():
    record = _minimal_provenance(
        source_topology={"active": True, "optional": None, "ranks": [0, 1]},
    ).to_dict()

    assert record["source_topology"] == {
        "active": True,
        "optional": None,
        "ranks": [0, 1],
    }


def test_command_redaction_covers_equals_and_bare_sensitive_values():
    sanitized = sanitize_command(
        (
            "convert",
            "--output=/private/output",
            "--note=ok",
            "--credential=secret-value",
            "bearer abcdefghijklmnop",
        )
    )

    assert sanitized[1].startswith("--output=[LOCAL_PATH:sha256:")
    assert sanitized[2] == "--note=ok"
    assert sanitized[3] == "--credential=[REDACTED]"
    assert sanitized[4] == "[REDACTED]"


def test_legacy_migration_marks_invalid_identity_and_ignores_invalid_dataset_rows():
    payload = migrate_legacy_metadata(
        {
            "model": "/private/model",
            "model_revision": "hf_abcdefghijklmnopqrstuvwxyz",
            "tokenizer_revision": 42,
            "dataset_inputs": ["invalid", {"identifier": "/private", "sha256": "a" * 64}],
        }
    ).to_dict()

    assert payload["base_model"] == {"identity": None, "revision": None, "digest": None}
    assert payload["tokenizer"]["revision"] is None
    assert payload["datasets"] == []
    assert "base_model_identity" in payload["unknowns"]


def test_provenance_verifier_rejects_tampering_and_constructor_identity_disagreement():
    record = _record()
    tampered = record.to_dict()
    tampered["unknowns"] = ["changed"]

    with pytest.raises(ValueError, match="record digest mismatch"):
        verify_provenance_record(tampered)
    with pytest.raises(ValueError, match="identity fields disagree"):
        ProvenanceRecord(
            "artifact-sha256:" + "f" * 64,
            record.record_digest,
            record.to_json(),
        )
    with pytest.raises(ValueError, match="JSON is not canonical"):
        ProvenanceRecord(
            record.artifact_id,
            record.record_digest,
            json.dumps(record.to_dict()),
        )


def test_public_metadata_bounds_mixed_keys_and_legacy_sensitive_values_fail_closed():
    with pytest.raises(ValueError, match="non-string key"):
        _minimal_provenance(source_topology={"rank": 0, 1: "invalid"})
    with pytest.raises(ValueError, match="invalid key"):
        _minimal_provenance(source_topology={"x" * 513: "invalid"})
    deeply_nested = {}
    cursor = deeply_nested
    for _ in range(18):
        cursor["next"] = {}
        cursor = cursor["next"]
    with pytest.raises(ValueError, match="nesting is too deep"):
        _minimal_provenance(source_topology=deeply_nested)
    with pytest.raises(ValueError, match="command argument"):
        _minimal_provenance(command=(object(),))

    legacy = migrate_legacy_metadata(
        {
            "model": "org/base",
            "model_revision": "/private/revision",
            "tokenizer_revision": "hf_abcdefghijklmnopqrstuvwxyz",
            "seed": "/private/seed",
            "dataset_inputs": None,
        }
    ).to_dict()
    rendered = json.dumps(legacy)
    assert "/private" not in rendered
    assert "hf_" not in rendered
    assert legacy["seed"] is None
    assert "seed" in legacy["unknowns"]


def test_public_provenance_parsers_reject_boundedness_and_structure_attacks():
    record = _record()
    with pytest.raises(ValueError, match="provenance JSON is invalid"):
        ProvenanceRecord(record.artifact_id, record.record_digest, '{"a": 1, "a": 2}')
    with pytest.raises(ValueError, match="text is too large"):
        _minimal_provenance(source_topology={"note": "x" * 1025})
    with pytest.raises(ValueError, match="too many fields"):
        _minimal_provenance(
            source_topology={f"field-{index}": index for index in range(4097)},
        )
    with pytest.raises(ValueError, match="too many items"):
        _minimal_provenance(source_topology={"items": [None] * 4097})
    with pytest.raises(ValueError, match="must be an object"):
        verify_provenance_record([])
    with pytest.raises(ValueError, match="bounded string collection"):
        classify_resume_state("model_weights")
    with pytest.raises(ValueError, match="collection is invalid"):
        _minimal_provenance(input_digests=DIGEST_A)
    with pytest.raises(ValueError, match="must contain strings"):
        _minimal_provenance(input_digests=(1,))
    with pytest.raises(ValueError, match="sources collection"):
        _minimal_provenance(sources="source")
    with pytest.raises(ValueError, match="artifact identities"):
        _minimal_provenance(sources=(object(),))
    with pytest.raises(ValueError, match="lineage events"):
        _minimal_provenance(lineage=(object(),))
    with pytest.raises(ValueError, match="bounded mapping"):
        migrate_legacy_metadata([])


def test_provenance_verifier_rejects_each_identity_and_state_layer():
    payload = _record().to_dict()

    malformed = {**payload, "sources": []}
    with pytest.raises(ValueError, match="structure is invalid"):
        verify_provenance_record(malformed)

    malformed = {**payload, "artifact_id": "invalid"}
    with pytest.raises(ValueError, match="artifact ID is invalid"):
        verify_provenance_record(malformed)

    malformed = {**payload, "state": {}}
    with pytest.raises(ValueError, match="state is invalid"):
        verify_provenance_record(malformed)

    malformed = json.loads(json.dumps(payload))
    malformed["state"]["classification"] = "unknown"
    with pytest.raises(ValueError, match="classification is not evidence-derived"):
        verify_provenance_record(malformed)

    malformed = {**payload, "artifact_id": "artifact-sha256:" + "f" * 64}
    digest_input = {key: value for key, value in malformed.items() if key != "record_digest"}
    encoded = json.dumps(
        digest_input,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    malformed["record_digest"] = f"sha256:{sha256(encoded).hexdigest()}"
    with pytest.raises(ValueError, match="artifact ID mismatch"):
        verify_provenance_record(malformed)


def test_command_and_legacy_scalar_paths_remain_public_and_canonical():
    assert sanitize_command(("convert", f"--note=hf_{'a' * 20}")) == (
        "convert",
        "--note=[REDACTED]",
    )
    assert migrate_legacy_metadata({"seed": 7}).to_dict()["seed"] == "7"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["sources"][0].update(kind="invalid"), "source identity"),
        (lambda value: value["converter"].update(commit="invalid"), "converter"),
        (lambda value: value["command"].append("/private/source"), "command"),
        (lambda value: value["environment"].update(packages=[]), "packages"),
        (lambda value: value.update(source_topology=[]), "source topology"),
        (lambda value: value["lineage"][0].update(extra=True), "lineage event fields"),
        (lambda value: value.update(input_digests=[]), "input digests"),
        (
            lambda value: value.update(output_digests=[DIGEST_B, DIGEST_B]),
            "output digests",
        ),
        (lambda value: value["transformations"].reverse(), "transformations"),
        (
            lambda value: value["state"].update(
                observed_scopes=["model_weights", "model_weights"]
            ),
            "observed scopes",
        ),
        (lambda value: value["adapter"].update(config_digest="invalid"), "adapter identity"),
        (lambda value: value["dataset"].update(record_count=True), "dataset identity"),
        (lambda value: value["training"].update(framework=[]), "training framework"),
        (lambda value: value.update(unknowns=["duplicate", "duplicate"]), "unknowns"),
    ],
)
def test_provenance_verifier_rejects_noncanonical_nested_records(mutation, message):
    payload = deepcopy(_record().to_dict())
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        verify_provenance_record(payload)


def test_builder_cannot_emit_schema_invalid_environment_or_duplicate_lineage():
    with pytest.raises(ValueError, match="environment python"):
        _minimal_provenance(
            environment={"python": [], "platform": "linux", "packages": {}},
        )

    event = LineageEvent("event", "consolidation", (), "writer@1", ())
    with pytest.raises(ValueError, match="sorted and unique"):
        _minimal_provenance(lineage=(event, event))
