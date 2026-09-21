"""Strict configuration for the explicit distributed preflight surface."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from obliteratus.distributed.contracts import ContractError, contract_digest


MAX_PROFILE_BYTES = 64 * 1024
MAX_TIMEOUT_SECONDS = 3600
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_INTERFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_SECRET_KEYS = frozenset(
    {"password", "secret", "token", "api_key", "api-key", "credential", "credentials"}
)

_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "run",
        "identity",
        "topology",
        "network",
        "source",
        "staging",
        "resources",
        "timeouts",
        "software",
        "execution",
        "evidence",
    }
)
_SECTION_FIELDS = {
    "run": frozenset({"run_id", "rendezvous_id", "world_size", "local_world_size"}),
    "identity": frozenset(
        {
            "source_digest",
            "model_digest",
            "tokenizer_digest",
            "commit_sha",
            "code_digest",
        }
    ),
    "topology": frozenset(
        {
            "tensor_parallel_size",
            "coordinator_rank",
            "placement_plan_digest",
            "dimension_divisors",
        }
    ),
    "network": frozenset(
        {"master_addr", "master_port", "interface", "allowed_master_cidrs"}
    ),
    "source": frozenset({"path"}),
    "staging": frozenset({"path", "storage_digest"}),
    "resources": frozenset(
        {
            "min_free_device_memory_bytes",
            "min_free_host_memory_bytes",
            "min_free_staging_bytes",
            "max_source_files",
            "max_source_bytes",
            "max_source_file_bytes",
        }
    ),
    "timeouts": frozenset(
        {"source_seconds", "init_seconds", "collective_seconds", "teardown_seconds"}
    ),
    "software": frozenset(
        {
            "python",
            "platform",
            "machine",
            "torch",
            "transformers",
            "accelerate",
            "safetensors",
            "cuda",
            "nccl",
            "driver",
        }
    ),
    "execution": frozenset(
        {
            "device_kind",
            "device_name",
            "compute_capability",
            "evidence_tier",
            "allowed_environment_keys",
            "local_files_only",
            "trust_remote_code",
            "allow_runtime_install",
            "allow_plugins",
            "allow_compilation",
            "allow_adapters",
            "allow_quantization",
        }
    ),
    "evidence": frozenset({"path"}),
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("distributed profile contains a duplicate field")
        result[key] = value
    return result


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be an object")
    return value


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ContractError(f"{name} must be between {minimum} and {maximum}")
    return value


def _text(value: object, name: str, pattern: re.Pattern[str] | None = None) -> str:
    try:
        encoded = value.encode("utf-8") if isinstance(value, str) else b""
    except UnicodeError as exc:
        raise ContractError(f"{name} must be valid UTF-8") from exc
    if not isinstance(value, str) or not value or len(encoded) > 256:
        raise ContractError(f"{name} must be bounded non-empty text")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ContractError(f"{name} has an invalid format")
    return value


def _absolute_path(value: object, name: str) -> Path:
    text = _text(value, name)
    path = Path(text)
    if not path.is_absolute() or "://" in text or "\x00" in text:
        raise ContractError(f"{name} must be an absolute local path")
    return path


def _closed_section(root: dict[str, Any], name: str) -> dict[str, Any]:
    section = _mapping(root.get(name), name)
    unknown = set(section) - _SECTION_FIELDS[name]
    missing = _SECTION_FIELDS[name] - set(section)
    if unknown:
        raise ContractError(f"unknown profile field in {name}")
    if missing:
        raise ContractError(f"required profile field is missing from {name}")
    return section


@dataclass(frozen=True)
class DistributedPreflightConfig:
    """Validated, closed-schema inputs for one non-resumable attempt."""

    run_id: str
    rendezvous_id: str
    world_size: int
    local_world_size: int
    source_digest: str
    model_digest: str
    tokenizer_digest: str
    commit_sha: str
    code_digest: str
    tensor_parallel_size: int
    coordinator_rank: int
    placement_plan_digest: str
    dimension_divisors: tuple[int, ...]
    master_addr: str
    master_port: int
    network_interface: str
    allowed_master_cidrs: tuple[str, ...]
    source_path: Path
    staging_path: Path
    storage_digest: str
    min_free_device_memory_bytes: int
    min_free_host_memory_bytes: int
    min_free_staging_bytes: int
    max_source_files: int
    max_source_bytes: int
    max_source_file_bytes: int
    source_timeout_seconds: int
    init_timeout_seconds: int
    collective_timeout_seconds: int
    teardown_timeout_seconds: int
    software_versions: tuple[tuple[str, str], ...]
    device_kind: str
    device_name: str
    compute_capability: str
    evidence_tier: str
    allowed_environment_keys: tuple[str, ...]
    local_files_only: bool
    trust_remote_code: bool
    allow_runtime_install: bool
    allow_plugins: bool
    allow_compilation: bool
    allow_adapters: bool
    allow_quantization: bool
    evidence_path: Path
    digest: str

    @classmethod
    def from_file(cls, path: str | Path) -> "DistributedPreflightConfig":
        profile_path = Path(path)
        descriptor: int | None = None
        try:
            descriptor = os.open(profile_path, os.O_RDONLY | os.O_NOFOLLOW)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or not 1 <= metadata.st_size <= MAX_PROFILE_BYTES:
                raise ContractError(
                    f"distributed profile must be a 1 through {MAX_PROFILE_BYTES} byte regular file"
                )
            raw = os.read(descriptor, MAX_PROFILE_BYTES + 1)
            final_metadata = os.fstat(descriptor)
            file_identity = lambda item: (
                item.st_dev,
                item.st_ino,
                item.st_size,
                item.st_mtime_ns,
                item.st_mode,
            )
            if len(raw) != metadata.st_size or file_identity(metadata) != file_identity(
                final_metadata
            ):
                raise ContractError("distributed profile changed while it was read")
        except ContractError:
            raise
        except OSError as exc:
            raise ContractError("distributed profile must be a regular non-symlink file") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
        try:
            root = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        except ContractError:
            raise
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ContractError("distributed profile must be strict UTF-8 JSON") from exc
        root = _mapping(root, "profile")
        if any(key.lower() in _SECRET_KEYS for key in root):
            raise ContractError("unknown profile field")
        unknown = set(root) - _ROOT_FIELDS
        missing = _ROOT_FIELDS - set(root)
        if unknown:
            raise ContractError("unknown profile field")
        if missing:
            raise ContractError("required profile section is missing")
        if root["schema_version"] != 1:
            raise ContractError("schema_version must be 1")

        sections = {name: _closed_section(root, name) for name in _SECTION_FIELDS}
        run, identity = sections["run"], sections["identity"]
        topology, network = sections["topology"], sections["network"]
        source, staging = sections["source"], sections["staging"]
        resources, timeouts = sections["resources"], sections["timeouts"]
        software, execution, evidence = (
            sections["software"],
            sections["execution"],
            sections["evidence"],
        )
        cidrs = network["allowed_master_cidrs"]
        if not isinstance(cidrs, list) or not cidrs or len(cidrs) > 16:
            raise ContractError("allowed_master_cidrs must be a non-empty bounded list")
        normalized_cidrs: list[str] = []
        private_ranges = (
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("fc00::/7"),
        )
        for value in cidrs:
            try:
                item = ipaddress.ip_network(_text(value, "allowed master CIDR"), strict=True)
            except ValueError as exc:
                raise ContractError("allowed_master_cidrs contains an invalid network") from exc
            is_private = any(
                (
                    isinstance(item, ipaddress.IPv4Network)
                    and isinstance(private, ipaddress.IPv4Network)
                    and item.subnet_of(private)
                )
                or (
                    isinstance(item, ipaddress.IPv6Network)
                    and isinstance(private, ipaddress.IPv6Network)
                    and item.subnet_of(private)
                )
                for private in private_ranges
            )
            if not is_private:
                raise ContractError("allowed_master_cidrs must contain only private networks")
            normalized_cidrs.append(str(item))
        if len(set(normalized_cidrs)) != len(normalized_cidrs):
            raise ContractError("allowed_master_cidrs cannot contain duplicates")
        divisors = topology["dimension_divisors"]
        if not isinstance(divisors, list) or not divisors or len(divisors) > 256:
            raise ContractError("dimension_divisors must be a non-empty bounded list")
        environment_keys = execution["allowed_environment_keys"]
        if (
            not isinstance(environment_keys, list)
            or len(environment_keys) > 128
            or len(set(environment_keys)) != len(environment_keys)
        ):
            raise ContractError("allowed_environment_keys must be a unique bounded list")

        result = cls(
            run_id=_text(run["run_id"], "run_id", _RUN_ID_RE),
            rendezvous_id=_text(run["rendezvous_id"], "rendezvous_id", _RUN_ID_RE),
            world_size=_integer(run["world_size"], "world_size", 2, 4096),
            local_world_size=_integer(
                run["local_world_size"], "local_world_size", 1, 4096
            ),
            source_digest=_text(identity["source_digest"], "source_digest", _DIGEST_RE),
            model_digest=_text(identity["model_digest"], "model_digest", _DIGEST_RE),
            tokenizer_digest=_text(
                identity["tokenizer_digest"], "tokenizer_digest", _DIGEST_RE
            ),
            commit_sha=_text(identity["commit_sha"], "commit_sha", _COMMIT_RE),
            code_digest=_text(identity["code_digest"], "code_digest", _DIGEST_RE),
            tensor_parallel_size=_integer(
                topology["tensor_parallel_size"], "tensor_parallel_size", 2, 4096
            ),
            coordinator_rank=_integer(
                topology["coordinator_rank"], "coordinator_rank", 0, 4095
            ),
            placement_plan_digest=_text(
                topology["placement_plan_digest"], "placement_plan_digest", _DIGEST_RE
            ),
            dimension_divisors=tuple(
                _integer(item, "dimension divisor", 1, 2**31 - 1) for item in divisors
            ),
            master_addr=_text(network["master_addr"], "master_addr"),
            master_port=_integer(network["master_port"], "master_port", 1, 65535),
            network_interface=_text(
                network["interface"], "network interface", _INTERFACE_RE
            ),
            allowed_master_cidrs=tuple(normalized_cidrs),
            source_path=_absolute_path(source["path"], "source.path"),
            staging_path=_absolute_path(staging["path"], "staging.path"),
            storage_digest=_text(staging["storage_digest"], "storage_digest", _DIGEST_RE),
            min_free_device_memory_bytes=_integer(
                resources["min_free_device_memory_bytes"],
                "min_free_device_memory_bytes",
                1,
                2**63 - 1,
            ),
            min_free_host_memory_bytes=_integer(
                resources["min_free_host_memory_bytes"],
                "min_free_host_memory_bytes",
                1,
                2**63 - 1,
            ),
            min_free_staging_bytes=_integer(
                resources["min_free_staging_bytes"],
                "min_free_staging_bytes",
                1,
                2**63 - 1,
            ),
            max_source_files=_integer(
                resources["max_source_files"], "max_source_files", 1, 1_000_000
            ),
            max_source_bytes=_integer(
                resources["max_source_bytes"], "max_source_bytes", 1, 2**63 - 1
            ),
            max_source_file_bytes=_integer(
                resources["max_source_file_bytes"],
                "max_source_file_bytes",
                1,
                2**63 - 1,
            ),
            source_timeout_seconds=_integer(
                timeouts["source_seconds"], "source_seconds", 1, MAX_TIMEOUT_SECONDS
            ),
            init_timeout_seconds=_integer(
                timeouts["init_seconds"], "init_seconds", 1, MAX_TIMEOUT_SECONDS
            ),
            collective_timeout_seconds=_integer(
                timeouts["collective_seconds"],
                "collective_seconds",
                1,
                MAX_TIMEOUT_SECONDS,
            ),
            teardown_timeout_seconds=_integer(
                timeouts["teardown_seconds"],
                "teardown_seconds",
                1,
                MAX_TIMEOUT_SECONDS,
            ),
            software_versions=tuple(
                (key, _text(value, f"software.{key}")) for key, value in sorted(software.items())
            ),
            device_kind=_text(execution["device_kind"], "device_kind"),
            device_name=_text(execution["device_name"], "device_name"),
            compute_capability=_text(
                execution["compute_capability"], "compute_capability"
            ),
            evidence_tier=_text(execution["evidence_tier"], "evidence_tier"),
            allowed_environment_keys=tuple(
                sorted(
                    _text(item, "allowed environment key", _ENV_NAME_RE)
                    for item in environment_keys
                )
            ),
            local_files_only=execution["local_files_only"],
            trust_remote_code=execution["trust_remote_code"],
            allow_runtime_install=execution["allow_runtime_install"],
            allow_plugins=execution["allow_plugins"],
            allow_compilation=execution["allow_compilation"],
            allow_adapters=execution["allow_adapters"],
            allow_quantization=execution["allow_quantization"],
            evidence_path=_absolute_path(evidence["path"], "evidence.path"),
            digest=contract_digest(root),
        )
        return result.validate()

    def validate(self) -> "DistributedPreflightConfig":
        """Recheck invariants after direct construction or dataclass replacement."""
        if self.run_id == self.rendezvous_id:
            raise ContractError("run_id and rendezvous_id must be distinct")
        if self.world_size % self.local_world_size:
            raise ContractError("world_size must be divisible by local_world_size")
        if self.tensor_parallel_size != self.world_size:
            raise ContractError("version 1 tensor_parallel_size must equal world_size")
        if self.max_source_file_bytes > self.max_source_bytes:
            raise ContractError("max_source_file_bytes cannot exceed max_source_bytes")
        expected_evidence = self.staging_path / self.run_id / "preflight.json"
        if self.evidence_path != expected_evidence:
            raise ContractError(
                "evidence.path must be the run-scoped staging preflight record"
            )
        if not 0 <= self.coordinator_rank < self.world_size:
            raise ContractError("coordinator_rank must be smaller than world_size")
        if self.device_kind not in {"cuda", "cpu"}:
            raise ContractError("device_kind must be cuda or cpu")
        tiers = {"cpu": "protocol_cpu", "cuda": "candidate_preflight"}
        if self.evidence_tier != tiers[self.device_kind]:
            raise ContractError("evidence_tier does not match the configured device kind")
        policies = {
            "local_files_only": self.local_files_only,
            "trust_remote_code": self.trust_remote_code,
            "allow_runtime_install": self.allow_runtime_install,
            "allow_plugins": self.allow_plugins,
            "allow_compilation": self.allow_compilation,
            "allow_adapters": self.allow_adapters,
            "allow_quantization": self.allow_quantization,
        }
        if policies["local_files_only"] is not True:
            raise ContractError("local_files_only must remain true")
        for name in (
            "trust_remote_code",
            "allow_runtime_install",
            "allow_plugins",
            "allow_compilation",
            "allow_adapters",
            "allow_quantization",
        ):
            if policies[name] is not False:
                raise ContractError(f"{name} must remain false")
        sensitive_markers = (
            "TOKEN",
            "SECRET",
            "PASSWORD",
            "PASSWD",
            "API_KEY",
            "ACCESS_KEY",
            "PRIVATE_KEY",
            "CREDENTIAL",
        )
        sensitive_prefixes = ("AWS_", "AZURE_", "GOOGLE_", "HF_", "OPENAI_", "ANTHROPIC_")
        proxy_keys = {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}
        if any(
            name in proxy_keys
            or name.startswith(sensitive_prefixes)
            or any(marker in name for marker in sensitive_markers)
            for name in self.allowed_environment_keys
        ):
            raise ContractError("allowed_environment_keys cannot authorize secret or proxy fields")
        return self

    @property
    def software_digest(self) -> str:
        return contract_digest(dict(self.software_versions))
