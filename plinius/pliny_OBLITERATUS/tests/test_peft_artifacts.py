"""Canonical PEFT LoRA export and truthful legacy-format contracts."""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
import torch
from jsonschema import Draft202012Validator
from safetensors.torch import load_file

from obliteratus.checkpoint_provenance import LineageEvent, ToolIdentity, build_provenance
from obliteratus.lora_ablation import (
    BaseModelIdentity,
    load_lora_adapters,
    save_legacy_pickle_adapters_trusted,
    save_lora_adapters,
    save_unsupported_obliteratus_adapters,
    validate_adapter_base,
)


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
COMMIT = "c" * 40
MANIFEST_SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "docs/checkpoints/schemas/peft-adapter-manifest-v1.schema.json"
    ).read_text()
)


def _base() -> BaseModelIdentity:
    return BaseModelIdentity(
        repo_id="org/exact-base",
        revision="d" * 40,
        weights_digest=DIGEST_A,
        tokenizer_digest=DIGEST_B,
        vocab_size=32000,
        architecture="TinyForCausalLM",
        tied_embeddings=True,
    )


def _adapters():
    return {
        "model.layers.0.self_attn.q_proj": (
            torch.arange(8, dtype=torch.float32).reshape(4, 2),
            torch.arange(6, dtype=torch.float32).reshape(2, 3),
        ),
        "model.layers.1.mlp.down_proj": (
            torch.arange(10, dtype=torch.float32).reshape(5, 2),
            torch.arange(8, dtype=torch.float32).reshape(2, 4),
        ),
    }


def _factory(base: BaseModelIdentity):
    def create(output_digests, adapter_identity):
        return build_provenance(
            sources=(base.to_artifact_identity(),),
            converter=ToolIdentity("obliteratus-peft-export", "1.0.0", COMMIT),
            obliteratus_commit=COMMIT,
            configuration_digest=adapter_identity.config_digest,
            tokenizer=base.tokenizer_artifact_identity(),
            base_model=base.to_artifact_identity(),
            command=("adapter", "export", base.repo_id),
            environment={"python": "test", "platform": "cpu", "packages": {}},
            source_topology={"world_size": 1},
            lineage=(
                LineageEvent(
                    "event-surgery",
                    "surgery",
                    (),
                    "obliteratus-peft-export@1.0.0",
                    ("refusal_direction_ablation",),
                ),
            ),
            input_digests=(base.weights_digest,),
            output_digests=output_digests,
            transformations=("lora_adapter_export", "surgery"),
            observed_scopes=("adapter_weights",),
            lost_state=("optimizer_state", "scheduler_state"),
            adapter=adapter_identity,
            training=None,
            unknowns=("training_dataset",),
        )

    return create


def _tree(root):
    return {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in sorted(item for item in root.iterdir() if item.is_file())
    }


def test_canonical_export_is_deterministic_standard_named_and_fully_identified(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    base = _base()

    first_artifact = save_lora_adapters(
        _adapters(),
        first,
        base_model=base,
        provenance_factory=_factory(base),
        lora_alpha=4,
    )
    second_artifact = save_lora_adapters(
        dict(reversed(list(_adapters().items()))),
        second,
        base_model=base,
        provenance_factory=_factory(base),
        lora_alpha=4,
    )

    assert _tree(first) == _tree(second)
    assert first_artifact.artifact_id == second_artifact.artifact_id
    assert set(_tree(first)) == {
        "README.md",
        "adapter_config.json",
        "adapter_manifest.json",
        "adapter_model.safetensors",
        "checkpoint-provenance.json",
    }
    assert not list(first.glob("*.pt"))
    config = json.loads((first / "adapter_config.json").read_text())
    assert config["peft_type"] == "LORA"
    assert config["base_model_name_or_path"] == base.repo_id
    assert config["revision"] == base.revision
    assert config["r"] == 2
    assert config["lora_alpha"] == 4
    assert config["target_modules"] == [
        "model.layers.0.self_attn.q_proj",
        "model.layers.1.mlp.down_proj",
    ]
    manifest = json.loads((first / "adapter_manifest.json").read_text())
    Draft202012Validator(MANIFEST_SCHEMA).validate(manifest)
    assert manifest["base_model"] == base.to_dict()
    assert manifest["scaling"] == 2.0
    assert manifest["merged"] is False
    assert manifest["bias"] == "none"
    assert manifest["modules_to_save"] == []
    assert manifest["tie_policy"] == "base_model_declared"
    assert "exact-base" in (first / "README.md").read_text()
    assert first_artifact.weights_path == first / "adapter_model.safetensors"


def test_saved_peft_scaling_reproduces_each_exact_internal_delta(tmp_path):
    base = _base()
    adapters = _adapters()
    save_lora_adapters(
        adapters,
        tmp_path,
        base_model=base,
        provenance_factory=_factory(base),
        lora_alpha=4,
    )
    state = load_file(tmp_path / "adapter_model.safetensors", device="cpu")
    manifest = json.loads((tmp_path / "adapter_manifest.json").read_text())

    for mapping in manifest["key_map"]:
        original_b, original_a = adapters[mapping["module_name"]]
        saved_a = state[mapping["lora_A_key"]]
        saved_b = state[mapping["lora_B_key"]]
        actual_delta = saved_b @ saved_a * manifest["scaling"]
        assert torch.equal(actual_delta, original_b @ original_a)

    loaded = load_lora_adapters(tmp_path, base_model=base)
    assert set(loaded) == set(adapters)
    for key in adapters:
        loaded_b, loaded_a = loaded[key]
        original_b, original_a = adapters[key]
        assert torch.equal(loaded_b @ loaded_a, original_b @ original_a)


@pytest.mark.parametrize(
    ("field", "value", "detail"),
    [
        ("repo_id", "other/base", "base_model_identity_mismatch"),
        ("revision", "e" * 40, "base_model_revision_mismatch"),
        ("weights_digest", "sha256:" + "f" * 64, "base_model_digest_mismatch"),
        ("tokenizer_digest", "sha256:" + "f" * 64, "tokenizer_digest_mismatch"),
        ("vocab_size", 32001, "vocab_size_mismatch"),
        ("architecture", "OtherModel", "architecture_mismatch"),
    ],
)
def test_wrong_base_or_tokenizer_is_rejected_before_adapter_loading(
    tmp_path,
    field,
    value,
    detail,
):
    base = _base()
    save_lora_adapters(
        _adapters(),
        tmp_path,
        base_model=base,
        provenance_factory=_factory(base),
    )

    with pytest.raises(ValueError, match=detail):
        validate_adapter_base(tmp_path, replace(base, **{field: value}))


def test_missing_or_malformed_canonical_artifact_fails_before_loading(tmp_path):
    base = _base()
    save_lora_adapters(
        _adapters(),
        tmp_path,
        base_model=base,
        provenance_factory=_factory(base),
    )
    (tmp_path / "adapter_config.json").write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="adapter_config_invalid"):
        load_lora_adapters(tmp_path, base_model=base)


@pytest.mark.parametrize(
    "relative_path",
    [
        "README.md",
        "adapter_model.safetensors",
        "adapter_config.json",
        "adapter_manifest.json",
    ],
)
def test_tampered_peft_artifact_fails_digest_check_before_weight_loading(
    tmp_path,
    monkeypatch,
    relative_path,
):
    import obliteratus.lora_ablation as lora_ablation

    base = _base()
    save_lora_adapters(
        _adapters(),
        tmp_path,
        base_model=base,
        provenance_factory=_factory(base),
    )
    artifact = tmp_path / relative_path
    if relative_path.endswith(".json"):
        record = json.loads(artifact.read_text(encoding="utf-8"))
        record["tampered"] = True
        artifact.write_text(json.dumps(record), encoding="utf-8")
    else:
        artifact.write_bytes(artifact.read_bytes() + b"tampered")
    monkeypatch.setattr(
        lora_ablation,
        "load_file",
        lambda *_args, **_kwargs: pytest.fail("weights loaded before integrity check"),
    )

    with pytest.raises(ValueError, match="adapter_artifact_digest_mismatch"):
        validate_adapter_base(tmp_path, base)


def test_tampered_provenance_digest_fails_before_weight_loading(tmp_path, monkeypatch):
    import obliteratus.lora_ablation as lora_ablation

    base = _base()
    save_lora_adapters(
        _adapters(),
        tmp_path,
        base_model=base,
        provenance_factory=_factory(base),
    )
    provenance_path = tmp_path / "checkpoint-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["record_digest"] = DIGEST_A
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    monkeypatch.setattr(
        lora_ablation,
        "load_file",
        lambda *_args, **_kwargs: pytest.fail("weights loaded before integrity check"),
    )

    with pytest.raises(ValueError, match="adapter_provenance_digest_mismatch"):
        validate_adapter_base(tmp_path, base)


def test_provenance_failure_preserves_prior_destination_and_leaks_no_staging(tmp_path):
    destination = tmp_path / "adapter"
    destination.mkdir()
    sentinel = destination / "prior.txt"
    sentinel.write_text("prior", encoding="utf-8")

    def fail_provenance(_digests, _adapter_identity):
        raise RuntimeError("injected provenance failure")

    with pytest.raises(FileExistsError, match="absent or empty"):
        save_lora_adapters(
            _adapters(),
            destination,
            base_model=_base(),
            provenance_factory=fail_provenance,
        )

    assert sentinel.read_text(encoding="utf-8") == "prior"
    assert not list(tmp_path.glob(".adapter.staging-*"))

    empty_destination = tmp_path / "empty"
    empty_destination.mkdir()
    with pytest.raises(RuntimeError, match="injected provenance failure"):
        save_lora_adapters(
            _adapters(),
            empty_destination,
            base_model=_base(),
            provenance_factory=fail_provenance,
        )

    assert empty_destination.is_dir()
    assert not list(empty_destination.iterdir())
    assert not list(tmp_path.glob(".empty.staging-*"))


def test_safe_loader_never_calls_torch_load(tmp_path, monkeypatch):
    base = _base()
    save_lora_adapters(
        _adapters(),
        tmp_path,
        base_model=base,
        provenance_factory=_factory(base),
    )
    monkeypatch.setattr(torch, "load", lambda *_args, **_kwargs: pytest.fail("pickle loaded"))

    loaded = load_lora_adapters(tmp_path, base_model=base)

    assert loaded


def test_unknown_base_uses_truthful_safe_legacy_format_not_peft_or_pickle(tmp_path):
    artifact = save_unsupported_obliteratus_adapters(
        _adapters(),
        tmp_path,
        reason="exact base digest unavailable",
    )

    assert artifact.name == "obliteratus_unsupported_adapter.safetensors"
    assert not (tmp_path / "adapter_config.json").exists()
    assert not list(tmp_path.glob("*.pt"))
    record = json.loads((tmp_path / "obliteratus_unsupported_adapter.json").read_text())
    assert record["support_status"] == "unsupported_legacy"
    assert record["safe_serialization"] is True
    assert record["peft_compatible"] is False
    assert record["reason"] == "exact base digest unavailable"

    for unsafe_reason in ("Bearer abcdefghijklmnop", "/private/model/path"):
        with pytest.raises(ValueError, match="reason is invalid"):
            save_unsupported_obliteratus_adapters(
                _adapters(),
                tmp_path / "unsafe",
                reason=unsafe_reason,
            )


def test_pickle_legacy_export_requires_an_explicit_trust_gate(tmp_path, monkeypatch):
    with pytest.raises(PermissionError, match="allow_pickle"):
        save_legacy_pickle_adapters_trusted(_adapters(), tmp_path, allow_pickle=False)

    observed = []
    monkeypatch.setattr(torch, "save", lambda state, path: observed.append((state, path)))
    path = save_legacy_pickle_adapters_trusted(_adapters(), tmp_path, allow_pickle=True)

    assert path.name == "obliteratus_legacy_adapter_unsafe.pt"
    assert observed and observed[0][1] == path
