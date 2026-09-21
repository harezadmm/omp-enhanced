"""Canonical, content-addressed provenance for checkpoint-derived artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence


_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_ARTIFACT_ID = re.compile(r"^artifact-sha256:[0-9a-f]{64}$")
_SECRET_KEY = re.compile(
    r"(?:^|[_-])(?:token|secret|password|credential|api[-_]?key)(?:$|[_-])",
    re.I,
)
_PROMPT_KEY = re.compile(r"(?:prompt|harmful|harmless|instruction|conversation)", re.I)
_SECRET_VALUE = re.compile(r"(?i)(?:hf_[a-z0-9]{12,}|bearer\s+[a-z0-9._~+/-]{12,})")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_MAX_COLLECTION_ITEMS = 4096
_MAX_COMMAND_ARGUMENTS = 256
_MAX_NESTING_DEPTH = 16
_LINEAGE_TYPES = frozenset(
    {
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
)
_EXACT_RESUME_SCOPES = frozenset(
    {
        "model_weights",
        "optimizer_state",
        "scheduler_state",
        "rng_state",
        "dataloader_state",
        "framework_state",
    }
)


def _require_digest(value: str, field: str) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ValueError(f"{field} must be a sha256 digest")


def _require_commit(value: str, field: str) -> None:
    if not isinstance(value, str) or not _COMMIT.fullmatch(value):
        raise ValueError(f"{field} must be a 40-character lowercase commit")


def _is_absolute(value: str) -> bool:
    return Path(value).is_absolute() or bool(_WINDOWS_ABSOLUTE.match(value))


def _require_public_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError(f"{field} must be non-empty bounded text")
    if _SECRET_VALUE.search(value):
        raise ValueError(f"{field} contains a secret")
    if _is_absolute(value):
        raise ValueError(f"{field} contains a private local path")


@dataclass(frozen=True)
class ArtifactIdentity:
    kind: str
    identity: str
    revision: str | None
    digest: str

    def __post_init__(self) -> None:
        if self.kind not in {"local", "hub", "generated"}:
            raise ValueError("artifact identity kind is invalid")
        _require_public_text(self.identity, "artifact identity")
        if self.revision is not None:
            _require_public_text(self.revision, "artifact revision")
        _require_digest(self.digest, "artifact digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "identity": self.identity,
            "revision": self.revision,
            "digest": self.digest,
        }


@dataclass(frozen=True)
class ToolIdentity:
    name: str
    version: str
    commit: str

    def __post_init__(self) -> None:
        _require_public_text(self.name, "tool name")
        _require_public_text(self.version, "tool version")
        _require_commit(self.commit, "tool commit")

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version, "commit": self.commit}


@dataclass(frozen=True)
class LineageEvent:
    event_id: str
    event_type: str
    parent_artifact_ids: tuple[str, ...]
    tool: str
    transformations: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_public_text(self.event_id, "lineage event ID")
        if self.event_type not in _LINEAGE_TYPES:
            raise ValueError("lineage event type is invalid")
        _require_public_text(self.tool, "lineage tool")
        for parent in self.parent_artifact_ids:
            if not _ARTIFACT_ID.fullmatch(parent):
                raise ValueError("lineage parent artifact ID is invalid")
        for transformation in self.transformations:
            _require_public_text(transformation, "lineage transformation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "parent_artifact_ids": sorted(set(self.parent_artifact_ids)),
            "tool": self.tool,
            "transformations": sorted(set(self.transformations)),
        }


@dataclass(frozen=True)
class AdapterIdentity:
    adapter_type: str
    base_model: ArtifactIdentity
    config_digest: str
    key_map_digest: str

    def __post_init__(self) -> None:
        _require_public_text(self.adapter_type, "adapter type")
        _require_digest(self.config_digest, "adapter config digest")
        _require_digest(self.key_map_digest, "adapter key-map digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_type": self.adapter_type,
            "base_model": self.base_model.to_dict(),
            "config_digest": self.config_digest,
            "key_map_digest": self.key_map_digest,
        }


@dataclass(frozen=True)
class DatasetIdentity:
    identifier: str
    revision: str | None
    digest: str
    split: str | None
    subset: str | None
    record_count: int

    def __post_init__(self) -> None:
        _require_public_text(self.identifier, "dataset identifier")
        for field, value in (
            ("dataset revision", self.revision),
            ("dataset split", self.split),
            ("dataset subset", self.subset),
        ):
            if value is not None:
                _require_public_text(value, field)
        _require_digest(self.digest, "dataset digest")
        if type(self.record_count) is not int or not 0 <= self.record_count <= (1 << 63) - 1:
            raise ValueError("dataset record count is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "revision": self.revision,
            "digest": self.digest,
            "split": self.split,
            "subset": self.subset,
            "record_count": self.record_count,
        }


@dataclass(frozen=True)
class TrainingIdentity:
    method: str
    framework: str | None
    framework_version: str | None
    hyperparameters_digest: str | None

    def __post_init__(self) -> None:
        if self.method not in {"pretrain", "full_finetune", "adapter_train", "unknown"}:
            raise ValueError("training method is invalid")
        for field, value in (
            ("training framework", self.framework),
            ("training framework version", self.framework_version),
        ):
            if value is not None:
                _require_public_text(value, field)
        if self.hyperparameters_digest is not None:
            _require_digest(self.hyperparameters_digest, "training hyperparameters digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "hyperparameters_digest": self.hyperparameters_digest,
        }


@dataclass(frozen=True)
class ProvenanceRecord:
    artifact_id: str
    record_digest: str
    _json: str

    def __post_init__(self) -> None:
        try:
            value = json.loads(self._json, object_pairs_hook=_reject_duplicate_pairs)
        except (TypeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError("provenance JSON is invalid") from error
        canonical = json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ) + "\n"
        if self._json != canonical:
            raise ValueError("provenance JSON is not canonical")
        verified = verify_provenance_record(value)
        if (
            verified["artifact_id"] != self.artifact_id
            or verified["record_digest"] != self.record_digest
        ):
            raise ValueError("provenance record identity fields disagree")

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._json)

    def to_json(self) -> str:
        return self._json


@dataclass(frozen=True)
class LegacyProvenanceFacts:
    _json: str

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._json)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return f"sha256:{sha256(_canonical_bytes(value)).hexdigest()}"


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _exact_mapping(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} fields are invalid")
    return dict(value)


def _artifact_identity_from_record(value: Any, label: str) -> ArtifactIdentity:
    record = _exact_mapping(value, {"kind", "identity", "revision", "digest"}, label)
    try:
        identity = ArtifactIdentity(
            record["kind"],
            record["identity"],
            record["revision"],
            record["digest"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} is invalid") from error
    if identity.revision is not None and len(identity.revision) > 256:
        raise ValueError(f"{label} revision is too large")
    return identity


def _tool_identity_from_record(value: Any) -> ToolIdentity:
    record = _exact_mapping(value, {"name", "version", "commit"}, "converter")
    try:
        return ToolIdentity(record["name"], record["version"], record["commit"])
    except (TypeError, ValueError) as error:
        raise ValueError("converter is invalid") from error


def _lineage_from_record(value: Any) -> LineageEvent:
    record = _exact_mapping(
        value,
        {"event_id", "event_type", "parent_artifact_ids", "tool", "transformations"},
        "lineage event",
    )
    parents = record["parent_artifact_ids"]
    transformations = record["transformations"]
    if not isinstance(parents, list) or not isinstance(transformations, list):
        raise ValueError("lineage event collections are invalid")
    try:
        event = LineageEvent(
            record["event_id"],
            record["event_type"],
            tuple(parents),
            record["tool"],
            tuple(transformations),
        )
    except (TypeError, ValueError) as error:
        raise ValueError("lineage event is invalid") from error
    if event.to_dict() != record:
        raise ValueError("lineage event is not canonical")
    return event


def _adapter_from_record(value: Any) -> AdapterIdentity:
    record = _exact_mapping(
        value,
        {"adapter_type", "base_model", "config_digest", "key_map_digest"},
        "adapter identity",
    )
    base_model = _artifact_identity_from_record(record["base_model"], "adapter base model")
    try:
        return AdapterIdentity(
            record["adapter_type"],
            base_model,
            record["config_digest"],
            record["key_map_digest"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("adapter identity is invalid") from error


def _dataset_from_record(value: Any) -> DatasetIdentity:
    record = _exact_mapping(
        value,
        {"identifier", "revision", "digest", "split", "subset", "record_count"},
        "dataset identity",
    )
    for field in ("revision", "split", "subset"):
        item = record[field]
        if item is not None and (not isinstance(item, str) or len(item) > 256):
            raise ValueError(f"dataset {field} is invalid")
    try:
        return DatasetIdentity(
            record["identifier"],
            record["revision"],
            record["digest"],
            record["split"],
            record["subset"],
            record["record_count"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("dataset identity is invalid") from error


def _training_from_record(value: Any) -> TrainingIdentity:
    record = _exact_mapping(
        value,
        {"method", "framework", "framework_version", "hyperparameters_digest"},
        "training identity",
    )
    for field, maximum in (("framework", 256), ("framework_version", 128)):
        item = record[field]
        if item is not None and (not isinstance(item, str) or len(item) > maximum):
            raise ValueError(f"training {field} is invalid")
    try:
        return TrainingIdentity(
            record["method"],
            record["framework"],
            record["framework_version"],
            record["hyperparameters_digest"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("training identity is invalid") from error


def _verify_canonical_string_set(
    value: Any,
    field: str,
    *,
    nonempty: bool = False,
    digests: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{field} must be a canonical list")
    canonical = _sorted_unique(value, field, digests=digests)
    if value != canonical:
        raise ValueError(f"{field} must be sorted and unique")
    return canonical


def _normalize_public(value: Any, field: str, *, depth: int = 0) -> Any:
    if depth > _MAX_NESTING_DEPTH:
        raise ValueError(f"{field} nesting is too deep")
    if value is None or isinstance(value, bool):
        return value
    if type(value) is int:
        if not -(1 << 63) <= value <= (1 << 63) - 1:
            raise ValueError(f"{field} integer is outside int64")
        return value
    if isinstance(value, str):
        if _SECRET_VALUE.search(value):
            raise ValueError(f"{field} contains a secret")
        if _is_absolute(value):
            raise ValueError(f"{field} contains a private local path")
        if len(value) > 1024:
            raise ValueError(f"{field} text is too large")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise ValueError(f"{field} has too many fields")
        if any(not isinstance(key, str) for key in value):
            raise ValueError(f"{field} has a non-string key")
        if any(not key or len(key) > 512 for key in value):
            raise ValueError(f"{field} has an invalid key")
        result = {}
        for key in sorted(value):
            if _SECRET_KEY.search(key) or _PROMPT_KEY.search(key):
                raise ValueError(f"{field} contains a sensitive key")
            result[key] = _normalize_public(
                value[key],
                f"{field}.{key}",
                depth=depth + 1,
            )
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise ValueError(f"{field} has too many items")
        return [
            _normalize_public(item, field, depth=depth + 1) for item in value
        ]
    raise ValueError(f"{field} contains a non-JSON value")


def verify_provenance_record(value: Mapping[str, Any]) -> dict[str, Any]:
    """Verify canonical identity, public-data hygiene, and state truth."""
    if not isinstance(value, Mapping):
        raise ValueError("provenance record must be an object")
    record = _normalize_public(dict(value), "provenance")
    required = {
        "schema_id",
        "schema_version",
        "artifact_id",
        "record_digest",
        "sources",
        "converter",
        "obliteratus_commit",
        "configuration_digest",
        "tokenizer",
        "base_model",
        "command",
        "environment",
        "source_topology",
        "lineage",
        "input_digests",
        "output_digests",
        "transformations",
        "state",
        "adapter",
        "dataset",
        "training",
        "unknowns",
    }
    if set(record) != required:
        raise ValueError("provenance record fields are invalid")
    if (
        record["schema_id"] != "obliteratus.artifact-provenance"
        or record["schema_version"] != "1.0.0"
        or not isinstance(record["sources"], list)
        or not record["sources"]
        or not isinstance(record["input_digests"], list)
        or not isinstance(record["output_digests"], list)
        or not isinstance(record["command"], list)
        or not isinstance(record["state"], dict)
    ):
        raise ValueError("provenance record structure is invalid")
    if not isinstance(record["artifact_id"], str) or not _ARTIFACT_ID.fullmatch(
        record["artifact_id"]
    ):
        raise ValueError("provenance artifact ID is invalid")
    _require_digest(record["record_digest"], "provenance record digest")
    sources = [
        _artifact_identity_from_record(item, "source identity")
        for item in record["sources"]
    ]
    canonical_sources = sorted(
        {
            json.dumps(item.to_dict(), sort_keys=True): item.to_dict()
            for item in sources
        }.values(),
        key=_canonical_bytes,
    )
    if record["sources"] != canonical_sources or len(sources) > _MAX_COLLECTION_ITEMS:
        raise ValueError("provenance sources are not canonical")
    _tool_identity_from_record(record["converter"])
    _require_commit(record["obliteratus_commit"], "OBLITERATUS commit")
    if record["configuration_digest"] is not None:
        _require_digest(record["configuration_digest"], "configuration digest")
    for field in ("tokenizer", "base_model"):
        if record[field] is not None:
            _artifact_identity_from_record(record[field], field.replace("_", " "))
    command = record["command"]
    if (
        len(command) > _MAX_COMMAND_ARGUMENTS
        or any(not isinstance(item, str) or len(item) > 4096 for item in command)
        or list(sanitize_command(command)) != command
    ):
        raise ValueError("provenance command is invalid or not sanitized")
    environment = _exact_mapping(
        record["environment"],
        {"python", "platform", "packages"},
        "environment",
    )
    for field, maximum in (("python", 128), ("platform", 256)):
        item = environment[field]
        if item is not None and (not isinstance(item, str) or len(item) > maximum):
            raise ValueError(f"environment {field} is invalid")
    packages = environment["packages"]
    if (
        not isinstance(packages, Mapping)
        or len(packages) > _MAX_COLLECTION_ITEMS
        or any(
            not isinstance(name, str)
            or not isinstance(version, str)
            or len(version) > 128
            for name, version in packages.items()
        )
    ):
        raise ValueError("environment packages are invalid")
    if not isinstance(record["source_topology"], dict):
        raise ValueError("source topology must be an object")
    lineage = record["lineage"]
    if not isinstance(lineage, list) or len(lineage) > _MAX_COLLECTION_ITEMS:
        raise ValueError("lineage must be a bounded list")
    lineage_records = [_lineage_from_record(item).to_dict() for item in lineage]
    if lineage_records != sorted(
        lineage_records,
        key=lambda item: (item["event_id"], item["event_type"]),
    ) or len({_canonical_bytes(item) for item in lineage_records}) != len(lineage_records):
        raise ValueError("lineage must be sorted and unique")
    _verify_canonical_string_set(
        record["input_digests"],
        "input digests",
        nonempty=True,
        digests=True,
    )
    _verify_canonical_string_set(
        record["output_digests"],
        "output digests",
        nonempty=True,
        digests=True,
    )
    _verify_canonical_string_set(record["transformations"], "transformations")
    state = record["state"]
    if (
        set(state) != {"classification", "observed_scopes", "lost_state"}
        or not isinstance(state["observed_scopes"], list)
        or not isinstance(state["lost_state"], list)
        or not isinstance(state["classification"], str)
    ):
        raise ValueError("provenance state is invalid")
    _verify_canonical_string_set(state["observed_scopes"], "observed scopes")
    _verify_canonical_string_set(state["lost_state"], "lost state")
    if state["classification"] != classify_resume_state(state["observed_scopes"]):
        raise ValueError("provenance state classification is not evidence-derived")
    if record["adapter"] is not None:
        _adapter_from_record(record["adapter"])
    if record["dataset"] is not None:
        _dataset_from_record(record["dataset"])
    if record["training"] is not None:
        _training_from_record(record["training"])
    _verify_canonical_string_set(record["unknowns"], "unknowns")
    without_record_digest = {
        key: item for key, item in record.items() if key != "record_digest"
    }
    if record["record_digest"] != _digest(without_record_digest):
        raise ValueError("provenance record digest mismatch")
    identity_core = {
        key: item for key, item in without_record_digest.items() if key != "artifact_id"
    }
    expected_artifact_id = _digest(identity_core).replace(
        "sha256:",
        "artifact-sha256:",
        1,
    )
    if record["artifact_id"] != expected_artifact_id:
        raise ValueError("provenance artifact ID mismatch")
    return record


def _local_path_token(value: str) -> str:
    return f"[LOCAL_PATH:sha256:{sha256(value.encode('utf-8')).hexdigest()}]"


def sanitize_command(arguments: Sequence[str]) -> tuple[str, ...]:
    """Remove secret values, raw prompt text, and private local paths from a command."""
    if isinstance(arguments, (str, bytes)) or len(arguments) > _MAX_COMMAND_ARGUMENTS:
        raise ValueError("command argument list is invalid or too large")
    result: list[str] = []
    redact_next = False
    for raw in arguments:
        if not isinstance(raw, str) or len(raw) > 4096:
            raise ValueError("command argument must be bounded text")
        argument = raw
        if redact_next:
            result.append("[REDACTED]")
            redact_next = False
            continue
        if argument.startswith("--") and "=" in argument:
            option, value = argument.split("=", 1)
            if _SECRET_KEY.search(option) or _PROMPT_KEY.search(option):
                result.append(f"{option}=[REDACTED]")
            elif _is_absolute(value):
                result.append(f"{option}={_local_path_token(value)}")
            elif _SECRET_VALUE.search(value):
                result.append(f"{option}=[REDACTED]")
            else:
                result.append(argument)
            continue
        if argument.startswith("--") and (
            _SECRET_KEY.search(argument) or _PROMPT_KEY.search(argument)
        ):
            result.append(argument)
            redact_next = True
        elif _is_absolute(argument):
            result.append(_local_path_token(argument))
        elif _SECRET_VALUE.search(argument):
            result.append("[REDACTED]")
        else:
            result.append(argument)
    return tuple(result)


def classify_resume_state(observed_scopes: Sequence[str]) -> str:
    """Derive the strongest truthful state class; caller claims are never accepted."""
    if (
        isinstance(observed_scopes, (str, bytes))
        or len(observed_scopes) > _MAX_COLLECTION_ITEMS
        or any(not isinstance(scope, str) for scope in observed_scopes)
    ):
        raise ValueError("observed scopes must be a bounded string collection")
    scopes = frozenset(observed_scopes)
    if _EXACT_RESUME_SCOPES <= scopes:
        return "exact_resume"
    if {"model_weights", "optimizer_state"} <= scopes:
        return "model_and_optimizer"
    if "model_weights" in scopes or "adapter_weights" in scopes:
        return "weights_only"
    return "unknown"


def _sorted_unique(values: Sequence[str], field: str, *, digests: bool = False) -> list[str]:
    if isinstance(values, (str, bytes)) or len(values) > _MAX_COLLECTION_ITEMS:
        raise ValueError(f"{field} collection is invalid or too large")
    if any(not isinstance(value, str) for value in values):
        raise ValueError(f"{field} must contain strings")
    result = sorted(set(values))
    for value in result:
        if digests:
            _require_digest(value, field)
        else:
            _require_public_text(value, field)
    return result


def build_provenance(
    *,
    sources: Sequence[ArtifactIdentity],
    converter: ToolIdentity,
    obliteratus_commit: str,
    configuration_digest: str | None,
    tokenizer: ArtifactIdentity | None,
    base_model: ArtifactIdentity | None,
    command: Sequence[str],
    environment: Mapping[str, Any],
    source_topology: Mapping[str, Any],
    lineage: Sequence[LineageEvent],
    input_digests: Sequence[str],
    output_digests: Sequence[str],
    transformations: Sequence[str],
    observed_scopes: Sequence[str],
    lost_state: Sequence[str],
    adapter: AdapterIdentity | None = None,
    dataset: DatasetIdentity | None = None,
    training: TrainingIdentity | None = None,
    unknowns: Sequence[str] = (),
) -> ProvenanceRecord:
    """Build a strict content-addressed record from explicit evidence only."""
    if not sources:
        raise ValueError("at least one source identity is required")
    for field, values in (("sources", sources), ("lineage", lineage)):
        if isinstance(values, (str, bytes)) or len(values) > _MAX_COLLECTION_ITEMS:
            raise ValueError(f"{field} collection is invalid or too large")
    if any(not isinstance(source, ArtifactIdentity) for source in sources):
        raise ValueError("sources must contain artifact identities")
    if any(not isinstance(event, LineageEvent) for event in lineage):
        raise ValueError("lineage must contain lineage events")
    _require_commit(obliteratus_commit, "OBLITERATUS commit")
    if configuration_digest is not None:
        _require_digest(configuration_digest, "configuration digest")
    environment_record = {
        "python": environment.get("python"),
        "platform": environment.get("platform"),
        "packages": environment.get("packages", {}),
    }
    extra_environment = set(environment) - set(environment_record)
    for key in environment:
        if _SECRET_KEY.search(str(key)) or _PROMPT_KEY.search(str(key)):
            raise ValueError("environment contains a sensitive key")
    if extra_environment:
        raise ValueError("environment contains unsupported fields")
    environment_record = _normalize_public(environment_record, "environment")
    topology_record = _normalize_public(source_topology, "source_topology")
    source_records = sorted(
        {json.dumps(source.to_dict(), sort_keys=True): source.to_dict() for source in sources}.values(),
        key=lambda item: _canonical_bytes(item),
    )
    lineage_records = sorted(
        (event.to_dict() for event in lineage),
        key=lambda item: (item["event_id"], item["event_type"]),
    )
    scopes = _sorted_unique(observed_scopes, "observed scope")
    core: dict[str, Any] = {
        "schema_id": "obliteratus.artifact-provenance",
        "schema_version": "1.0.0",
        "sources": source_records,
        "converter": converter.to_dict(),
        "obliteratus_commit": obliteratus_commit,
        "configuration_digest": configuration_digest,
        "tokenizer": tokenizer.to_dict() if tokenizer is not None else None,
        "base_model": base_model.to_dict() if base_model is not None else None,
        "command": list(sanitize_command(command)),
        "environment": environment_record,
        "source_topology": topology_record,
        "lineage": lineage_records,
        "input_digests": _sorted_unique(input_digests, "input digest", digests=True),
        "output_digests": _sorted_unique(output_digests, "output digest", digests=True),
        "transformations": _sorted_unique(transformations, "transformation"),
        "state": {
            "classification": classify_resume_state(scopes),
            "observed_scopes": scopes,
            "lost_state": _sorted_unique(lost_state, "lost state"),
        },
        "adapter": adapter.to_dict() if adapter is not None else None,
        "dataset": dataset.to_dict() if dataset is not None else None,
        "training": training.to_dict() if training is not None else None,
        "unknowns": _sorted_unique(unknowns, "unknown"),
    }
    artifact_id = f"artifact-sha256:{sha256(_canonical_bytes(core)).hexdigest()}"
    with_identity = {**core, "artifact_id": artifact_id}
    record_digest = _digest(with_identity)
    record = {**with_identity, "record_digest": record_digest}
    canonical = json.dumps(
        record,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    return ProvenanceRecord(artifact_id, record_digest, canonical)


def migrate_legacy_metadata(metadata: Mapping[str, Any]) -> LegacyProvenanceFacts:
    """Extract only explicit safe legacy facts and mark absent evidence as unknown."""
    if not isinstance(metadata, Mapping) or len(metadata) > _MAX_COLLECTION_ITEMS:
        raise ValueError("legacy metadata must be a bounded mapping")
    model = metadata.get("model")
    model_identity = (
        model
        if isinstance(model, str)
        and model
        and len(model) <= 512
        and not _is_absolute(model)
        and not _SECRET_VALUE.search(model)
        else None
    )
    revision = metadata.get("model_revision")
    if (
        not isinstance(revision, str)
        or not revision
        or len(revision) > 512
        or _is_absolute(revision)
        or _SECRET_VALUE.search(revision)
    ):
        revision = None
    tokenizer_revision = metadata.get("tokenizer_revision")
    if (
        not isinstance(tokenizer_revision, str)
        or not tokenizer_revision
        or len(tokenizer_revision) > 512
        or _is_absolute(tokenizer_revision)
        or _SECRET_VALUE.search(tokenizer_revision)
    ):
        tokenizer_revision = None
    datasets = []
    dataset_inputs = metadata.get("dataset_inputs", [])
    if not isinstance(dataset_inputs, (list, tuple)):
        dataset_inputs = []
    for item in dataset_inputs[:_MAX_COLLECTION_ITEMS]:
        if not isinstance(item, Mapping):
            continue
        identifier = item.get("identifier")
        digest = item.get("sha256")
        if (
            isinstance(identifier, str)
            and identifier
            and len(identifier) <= 512
            and not _is_absolute(identifier)
            and not _SECRET_VALUE.search(identifier)
            and isinstance(digest, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            datasets.append({"identifier": identifier, "digest": f"sha256:{digest}"})
    unknowns = ["base_model_digest", "tokenizer_digest"]
    known = {"model", "model_revision", "tokenizer_revision", "seed", "dataset_inputs"}
    if set(metadata) - known:
        unknowns.append("unmapped_fields_omitted")
    if model_identity is None:
        unknowns.append("base_model_identity")
    seed = metadata.get("seed")
    if type(seed) is int and -(1 << 63) <= seed <= (1 << 63) - 1:
        seed_value = str(seed)
    elif (
        isinstance(seed, str)
        and seed
        and len(seed) <= 128
        and not _is_absolute(seed)
        and not _SECRET_VALUE.search(seed)
    ):
        seed_value = seed
    else:
        seed_value = None
        if seed is not None:
            unknowns.append("seed")
    record = {
        "schema_id": "obliteratus.legacy-provenance-facts",
        "schema_version": "1.0.0",
        "base_model": {
            "identity": model_identity,
            "revision": revision,
            "digest": None,
        },
        "tokenizer": {"revision": tokenizer_revision, "digest": None},
        "seed": seed_value,
        "datasets": sorted(datasets, key=lambda item: (item["identifier"], item["digest"])),
        "unknowns": sorted(unknowns),
    }
    return LegacyProvenanceFacts(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    )
