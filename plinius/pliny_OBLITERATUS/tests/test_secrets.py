"""Provider-neutral runtime secret resolution contracts."""

from __future__ import annotations

import os
import subprocess

import pytest

from obliteratus.credential_sources import (
    SecretResolutionError,
    resolve_first,
    resolve_secret,
    secret_available,
)


pytestmark = pytest.mark.cpu

_TEST_ENVIRONMENT = {
    "HF_TOKEN",
    "HF_TOKEN_FILE",
    "HF_PUSH_TOKEN",
    "HF_PUSH_TOKEN_FILE",
    "OPENROUTER_API_KEY",
    "OPENROUTER_API_KEY_FILE",
    "OBLITERATUS_HUB_TOKEN",
    "OBLITERATUS_HUB_TOKEN_FILE",
    "OBLITERATUS_SECRET_DIR",
    "OBLITERATUS_SECRET_COMMAND",
    "OBLITERATUS_SECRET_COMMAND_TIMEOUT",
    "CREDENTIALS_DIRECTORY",
}


@pytest.fixture(autouse=True)
def _clean_secret_environment(monkeypatch):
    for name in _TEST_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)


def test_environment_is_the_default_and_precedes_advanced_sources(monkeypatch, tmp_path):
    missing_file = tmp_path / "not-used"
    monkeypatch.setenv("HF_TOKEN", "environment-value")
    monkeypatch.setenv("HF_TOKEN_FILE", str(missing_file))
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", "relative-command")

    assert resolve_secret("HF_TOKEN") == "environment-value"


def test_explicit_value_precedes_environment(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "environment-value")

    assert resolve_secret("HF_TOKEN", explicit="explicit-value\n") == "explicit-value"


def test_per_secret_file_supports_vault_agent_and_docker_mounts(monkeypatch, tmp_path):
    secret_file = tmp_path / "openrouter"
    secret_file.write_text("mounted-value\n", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY_FILE", str(secret_file))

    assert resolve_secret("OPENROUTER_API_KEY") == "mounted-value"


def test_configured_file_fails_closed_instead_of_falling_through(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_TOKEN_FILE", str(tmp_path / "missing"))
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", "relative-command")

    with pytest.raises(SecretResolutionError, match="unreadable"):
        resolve_secret("HF_TOKEN")


def test_configured_file_must_be_regular(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_TOKEN_FILE", str(tmp_path))

    with pytest.raises(SecretResolutionError, match="not a file"):
        resolve_secret("HF_TOKEN")


@pytest.mark.parametrize("directory_variable", ["OBLITERATUS_SECRET_DIR", "CREDENTIALS_DIRECTORY"])
def test_normalized_mounted_secret_directories(monkeypatch, tmp_path, directory_variable):
    secret_file = tmp_path / "openrouter-api-key"
    secret_file.write_text("directory-value", encoding="utf-8")
    monkeypatch.setenv(directory_variable, str(tmp_path))

    assert resolve_secret("OPENROUTER_API_KEY") == "directory-value"


def test_uppercase_filename_is_supported_for_existing_secret_mounts(monkeypatch, tmp_path):
    secret_file = tmp_path / "HF_TOKEN"
    secret_file.write_text("uppercase-file", encoding="utf-8")
    monkeypatch.setenv("OBLITERATUS_SECRET_DIR", str(tmp_path))

    assert resolve_secret("HF_TOKEN") == "uppercase-file"


@pytest.mark.skipif(os.name == "nt", reason="executable broker fixture is POSIX-specific")
def test_executable_broker_receives_only_normalized_name(monkeypatch, tmp_path):
    broker = tmp_path / "secret-broker"
    broker.write_text(
        "#!/bin/sh\n"
        "[ \"$#\" -eq 1 ] || exit 9\n"
        "[ \"$1\" = OPENROUTER_API_KEY ] || exit 2\n"
        "printf 'broker-value\\n'\n",
        encoding="utf-8",
    )
    broker.chmod(0o700)
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", str(broker))

    assert resolve_secret("OPENROUTER_API_KEY") == "broker-value"
    assert resolve_secret("HF_TOKEN") is None


def test_broker_requires_absolute_executable(monkeypatch):
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", "vault read secret")

    with pytest.raises(SecretResolutionError, match="absolute path"):
        resolve_secret("HF_TOKEN")


def test_broker_timeout_is_bounded(monkeypatch, tmp_path):
    broker = tmp_path / "broker"
    broker.write_text("placeholder", encoding="utf-8")
    broker.chmod(0o700)
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", str(broker))
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND_TIMEOUT", "31")

    with pytest.raises(SecretResolutionError, match="between 0.1 and 30"):
        resolve_secret("HF_TOKEN")


def test_broker_timeout_must_be_numeric(monkeypatch, tmp_path):
    broker = tmp_path / "broker"
    broker.write_text("placeholder", encoding="utf-8")
    broker.chmod(0o700)
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", str(broker))
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND_TIMEOUT", "fast")

    with pytest.raises(SecretResolutionError, match="must be a number"):
        resolve_secret("HF_TOKEN")


def test_missing_and_non_executable_brokers_fail_closed(monkeypatch, tmp_path):
    missing = tmp_path / "missing"
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", str(missing))
    with pytest.raises(SecretResolutionError, match="unavailable"):
        resolve_secret("HF_TOKEN")

    broker = tmp_path / "broker"
    broker.write_text("placeholder", encoding="utf-8")
    broker.chmod(0o600)
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", str(broker))
    with pytest.raises(SecretResolutionError, match="executable regular file"):
        resolve_secret("HF_TOKEN")

    broker.chmod(0o722)
    with pytest.raises(SecretResolutionError, match="group/world writable"):
        resolve_secret("HF_TOKEN")


@pytest.mark.parametrize(
    ("completed", "message"),
    [
        (subprocess.CompletedProcess([], 9, stdout=b"", stderr=b"private"), "exit status 9"),
        (subprocess.CompletedProcess([], 0, stdout=b"x" * (64 * 1024 + 1)), "64 KiB"),
        (subprocess.CompletedProcess([], 0, stdout=b"\xff"), "not UTF-8"),
    ],
)
def test_broker_errors_never_surface_stderr(monkeypatch, tmp_path, completed, message):
    broker = tmp_path / "broker"
    broker.write_text("placeholder", encoding="utf-8")
    broker.chmod(0o700)
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", str(broker))
    monkeypatch.setattr(
        "obliteratus.credential_sources.subprocess.run",
        lambda *_a, **_k: completed,
    )

    with pytest.raises(SecretResolutionError, match=message) as failure:
        resolve_secret("HF_TOKEN")
    assert "private" not in str(failure.value)


def test_broker_execution_failure_is_normalized(monkeypatch, tmp_path):
    broker = tmp_path / "broker"
    broker.write_text("placeholder", encoding="utf-8")
    broker.chmod(0o700)
    monkeypatch.setenv("OBLITERATUS_SECRET_COMMAND", str(broker))
    monkeypatch.setattr(
        "obliteratus.credential_sources.subprocess.run",
        lambda *_a, **_k: (_ for _ in ()).throw(subprocess.TimeoutExpired("broker", 1)),
    )

    with pytest.raises(SecretResolutionError, match="execution failed"):
        resolve_secret("HF_TOKEN")


@pytest.mark.parametrize("payload", ["", "value\x00suffix"])
def test_invalid_file_payloads_are_rejected(monkeypatch, tmp_path, payload):
    secret_file = tmp_path / "invalid"
    secret_file.write_bytes(payload.encode("utf-8"))
    monkeypatch.setenv("HF_TOKEN_FILE", str(secret_file))

    with pytest.raises(SecretResolutionError, match="empty|NUL"):
        resolve_secret("HF_TOKEN")


def test_oversized_secret_file_is_rejected(monkeypatch, tmp_path):
    secret_file = tmp_path / "oversized"
    secret_file.write_bytes(b"x" * (64 * 1024 + 1))
    monkeypatch.setenv("HF_TOKEN_FILE", str(secret_file))

    with pytest.raises(SecretResolutionError, match="64 KiB"):
        resolve_secret("HF_TOKEN")


def test_resolve_first_preserves_caller_priority_and_availability(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "read-token")
    monkeypatch.setenv("HF_PUSH_TOKEN", "push-token")

    assert resolve_first("HF_PUSH_TOKEN", "HF_TOKEN") == "push-token"
    assert secret_available("OPENROUTER_API_KEY", "HF_TOKEN") is True
    assert secret_available("OPENROUTER_API_KEY") is False


@pytest.mark.parametrize("name", ["hf_token", "HF-TOKEN", "", "1TOKEN"])
def test_secret_names_are_normalized_and_not_shell_fragments(name):
    with pytest.raises(ValueError, match="uppercase environment-variable"):
        resolve_secret(name)
