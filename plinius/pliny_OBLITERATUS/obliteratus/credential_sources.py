"""Provider-neutral runtime credential resolution.

OBLITERATUS does not embed a client for any particular vault.  Instead, each
credential keeps its existing environment-variable name and can be supplied by
an environment value, a mounted file, or a trusted executable broker.  This
works with Vault/OpenBao Agent templates, Kubernetes and Docker secret mounts,
systemd credentials, and other secret managers without adding provider SDKs to
the application.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path


_SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_MAX_SECRET_BYTES = 64 * 1024
_DEFAULT_BROKER_TIMEOUT_SECONDS = 5.0


class SecretResolutionError(RuntimeError):
    """A configured secret source could not be resolved safely."""


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not _SECRET_NAME_RE.fullmatch(name):
        raise ValueError("secret names must use uppercase environment-variable syntax")
    return name


def _normalize_value(raw: str, *, source: str) -> str:
    value = raw.rstrip("\r\n")
    if not value:
        raise SecretResolutionError(f"configured secret source is empty: {source}")
    if "\x00" in value:
        raise SecretResolutionError(f"configured secret source contains a NUL byte: {source}")
    return value


def _read_secret_file(path: Path, *, source: str) -> str:
    try:
        resolved = path.expanduser().resolve(strict=True)
        metadata = resolved.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise SecretResolutionError(f"configured secret source is not a file: {source}")
        if metadata.st_size > _MAX_SECRET_BYTES:
            raise SecretResolutionError(f"configured secret source exceeds 64 KiB: {source}")
        raw = resolved.read_bytes()
        if len(raw) > _MAX_SECRET_BYTES:
            raise SecretResolutionError(f"configured secret source exceeds 64 KiB: {source}")
        return _normalize_value(raw.decode("utf-8"), source=source)
    except SecretResolutionError:
        raise
    except (OSError, UnicodeError) as exc:
        raise SecretResolutionError(f"configured secret source is unreadable: {source}") from exc


def _directory_candidates(directory: str, name: str) -> tuple[Path, ...]:
    root = Path(directory).expanduser()
    normalized = name.lower().replace("_", "-")
    return root / normalized, root / name


def _broker_timeout() -> float:
    raw = os.environ.get("OBLITERATUS_SECRET_COMMAND_TIMEOUT", "").strip()
    if not raw:
        return _DEFAULT_BROKER_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise SecretResolutionError(
            "OBLITERATUS_SECRET_COMMAND_TIMEOUT must be a number",
        ) from exc
    if not 0.1 <= timeout <= 30.0:
        raise SecretResolutionError(
            "OBLITERATUS_SECRET_COMMAND_TIMEOUT must be between 0.1 and 30 seconds",
        )
    return timeout


def _resolve_from_broker(name: str, command: str) -> str | None:
    executable = Path(command).expanduser()
    if not executable.is_absolute():
        raise SecretResolutionError("OBLITERATUS_SECRET_COMMAND must be an absolute path")
    try:
        metadata = executable.stat()
    except OSError as exc:
        raise SecretResolutionError("OBLITERATUS_SECRET_COMMAND is unavailable") from exc
    if not stat.S_ISREG(metadata.st_mode) or not os.access(executable, os.X_OK):
        raise SecretResolutionError(
            "OBLITERATUS_SECRET_COMMAND must be an executable regular file",
        )
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise SecretResolutionError("OBLITERATUS_SECRET_COMMAND must not be group/world writable")

    try:
        completed = subprocess.run(
            [str(executable), name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            close_fds=True,
            timeout=_broker_timeout(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SecretResolutionError("secret broker execution failed") from exc

    # Exit 2 is the normalized "secret not found" result.  Broker stderr is
    # intentionally never included because provider errors may contain secrets.
    if completed.returncode == 2:
        return None
    if completed.returncode != 0:
        raise SecretResolutionError(
            f"secret broker failed for {name} with exit status {completed.returncode}",
        )
    if len(completed.stdout) > _MAX_SECRET_BYTES:
        raise SecretResolutionError("secret broker output exceeds 64 KiB")
    try:
        raw = completed.stdout.decode("utf-8")
    except UnicodeError as exc:
        raise SecretResolutionError("secret broker output is not UTF-8") from exc
    return _normalize_value(raw, source=f"broker:{name}")


def resolve_secret(name: str, *, explicit: str | None = None) -> str | None:
    """Resolve one credential without coupling the app to a vault provider.

    Resolution order is explicit value, existing environment value, ``NAME_FILE``,
    ``OBLITERATUS_SECRET_DIR``, systemd ``CREDENTIALS_DIRECTORY``, then
    ``OBLITERATUS_SECRET_COMMAND``.  A configured but broken source fails closed.
    The broker is executed directly (never through a shell) and receives only the
    normalized credential name as its sole argument.
    """

    name = _validate_name(name)
    if explicit is not None and explicit.rstrip("\r\n"):
        return _normalize_value(explicit, source="explicit value")

    environment_value = os.environ.get(name)
    if environment_value:
        return _normalize_value(environment_value, source=name)

    file_variable = f"{name}_FILE"
    configured_file = os.environ.get(file_variable, "").strip()
    if configured_file:
        return _read_secret_file(Path(configured_file), source=file_variable)

    for directory_variable in ("OBLITERATUS_SECRET_DIR", "CREDENTIALS_DIRECTORY"):
        directory = os.environ.get(directory_variable, "").strip()
        if not directory:
            continue
        for candidate in _directory_candidates(directory, name):
            if candidate.exists():
                return _read_secret_file(candidate, source=directory_variable)

    command = os.environ.get("OBLITERATUS_SECRET_COMMAND", "").strip()
    if command:
        return _resolve_from_broker(name, command)
    return None


def resolve_first(*names: str) -> str | None:
    """Return the first available credential in caller-defined priority order."""

    for name in names:
        value = resolve_secret(name)
        if value is not None:
            return value
    return None


def secret_available(*names: str) -> bool:
    """Return whether any requested credential resolves successfully."""

    return resolve_first(*names) is not None
