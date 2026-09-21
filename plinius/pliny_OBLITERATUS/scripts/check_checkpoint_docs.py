#!/usr/bin/env python3
"""Validate checkpoint documentation and support claims without network or model work."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import shlex
from pathlib import Path
from typing import Any
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs/checkpoints"
MATRIX_PATH = DOCS_DIR / "support-matrix-v1.json"
SCHEMA_PATH = DOCS_DIR / "schemas/support-matrix-v1.schema.json"
STATUS_VOCABULARY = ["supported", "conditional", "deferred", "out_of_scope"]
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
ROW_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
FENCED_BLOCK = re.compile(r"```(?:bash|console|sh|shell)?\s*\n(.*?)```", re.DOTALL)


def _load_object(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read {label}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} root must be an object")
        return {}
    return value


def _exact_keys(
    value: object,
    *,
    required: set[str],
    label: str,
    errors: list[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    keys = set(value)
    missing = sorted(required - keys)
    unknown = sorted(keys - required)
    if missing:
        errors.append(f"{label} is missing fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"{label} has unknown fields: {', '.join(unknown)}")
    return value


def _nonempty_string(value: object, label: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return False
    return True


def _string_list(
    value: object,
    *,
    label: str,
    errors: list[str],
    nonempty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        errors.append(f"{label} must be a {qualifier}array")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if _nonempty_string(item, f"{label}[{index}]", errors):
            result.append(item)
    return result


def validate_matrix(matrix_path: Path = MATRIX_PATH, schema_path: Path = SCHEMA_PATH) -> list[str]:
    """Validate the strict support-matrix shape and evidence promotion gate."""

    errors: list[str] = []
    schema = _load_object(schema_path, "support-matrix schema", errors)
    matrix = _load_object(matrix_path, "support matrix", errors)
    if errors:
        return errors

    schema_properties = schema.get("properties")
    schema_required = schema.get("required")
    if not isinstance(schema_properties, dict) or not isinstance(schema_required, list):
        return ["support-matrix schema must declare root properties and required fields"]
    root = _exact_keys(
        matrix,
        required=set(schema_required),
        label="support matrix",
        errors=errors,
    )
    if set(schema_properties) != set(schema_required):
        errors.append("support-matrix schema root properties must all be required")
    if root.get("schema_id") != "obliteratus.checkpoint-support-matrix":
        errors.append("support matrix has an unsupported schema_id")
    if root.get("schema_version") != "1.0.0":
        errors.append("support matrix has an unsupported schema_version")
    if not isinstance(root.get("generated_from"), str) or not SHA_PATTERN.fullmatch(
        root["generated_from"],
    ):
        errors.append("support matrix generated_from must be a 40-character commit SHA")
    if root.get("status_vocabulary") != STATUS_VOCABULARY:
        errors.append("support matrix status_vocabulary must match the canonical ordered list")

    definitions = schema.get("$defs")
    if not isinstance(definitions, dict) or not isinstance(definitions.get("row"), dict):
        errors.append("support-matrix schema must declare the row definition")
        return errors
    row_schema = definitions["row"]
    row_required = row_schema.get("required")
    row_properties = row_schema.get("properties")
    if not isinstance(row_required, list) or not isinstance(row_properties, dict):
        errors.append("support-matrix row schema must declare properties and required fields")
        return errors
    if set(row_required) != set(row_properties):
        errors.append("support-matrix row properties must all be required")

    rows = root.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("support matrix rows must be a non-empty array")
        return errors
    seen_ids: set[str] = set()
    capability_names = {
        "detect",
        "safe_inspect",
        "trusted_inspect",
        "weights_canonicalize",
        "topology_reshard",
        "surgery",
        "exact_resume",
        "live_multi_node",
    }
    evidence_names = {
        "references",
        "candidate_commit",
        "fixture_digest",
        "environment",
        "topology",
        "retained_result",
    }
    for index, candidate in enumerate(rows):
        label = f"support matrix row {index}"
        row = _exact_keys(candidate, required=set(row_required), label=label, errors=errors)
        row_id = row.get("id")
        if not isinstance(row_id, str) or not ROW_ID_PATTERN.fullmatch(row_id):
            errors.append(f"{label} has an invalid id")
            row_id = str(index)
        elif row_id in seen_ids:
            errors.append(f"support matrix has duplicate row id: {row_id}")
        seen_ids.add(row_id)
        label = f"support matrix row {row_id}"

        for field in ("subject", "format", "model_mapping", "safety_level"):
            _nonempty_string(row.get(field), f"{label}.{field}", errors)
        for field in ("producer_versions", "state_scopes", "optional_extras", "limits"):
            _string_list(
                row.get(field),
                label=f"{label}.{field}",
                errors=errors,
                nonempty=field == "limits",
            )
        for field in ("adapter", "canonical_output"):
            if row.get(field) is not None and not isinstance(row.get(field), str):
                errors.append(f"{label}.{field} must be a string or null")

        capabilities = _exact_keys(
            row.get("capabilities"),
            required=capability_names,
            label=f"{label}.capabilities",
            errors=errors,
        )
        supported = False
        for name in sorted(capability_names):
            status = _exact_keys(
                capabilities.get(name),
                required={"value", "basis"},
                label=f"{label}.capabilities.{name}",
                errors=errors,
            )
            if status.get("value") not in STATUS_VOCABULARY:
                errors.append(f"{label}.capabilities.{name}.value is not canonical")
            supported = supported or status.get("value") == "supported"
            _nonempty_string(status.get("basis"), f"{label}.capabilities.{name}.basis", errors)

        evidence = _exact_keys(
            row.get("evidence"),
            required=evidence_names,
            label=f"{label}.evidence",
            errors=errors,
        )
        references = _string_list(
            evidence.get("references"),
            label=f"{label}.evidence.references",
            errors=errors,
            nonempty=True,
        )
        candidate_commit = evidence.get("candidate_commit")
        if candidate_commit is not None and (
            not isinstance(candidate_commit, str) or not SHA_PATTERN.fullmatch(candidate_commit)
        ):
            errors.append(f"{label}.evidence.candidate_commit must be a commit SHA or null")
        fixture_digest = evidence.get("fixture_digest")
        if fixture_digest is not None and (
            not isinstance(fixture_digest, str) or not DIGEST_PATTERN.fullmatch(fixture_digest)
        ):
            errors.append(f"{label}.evidence.fixture_digest must be a sha256 digest or null")
        for field in ("environment", "topology", "retained_result"):
            if evidence.get(field) is not None and not isinstance(evidence.get(field), str):
                errors.append(f"{label}.evidence.{field} must be a string or null")

        if supported:
            exact_versions = row.get("producer_versions")
            vague = re.compile(r"\b(?:compatible|varies|unknown|latest|planned)\b", re.IGNORECASE)
            if not isinstance(exact_versions, list) or not exact_versions or any(
                not isinstance(version, str) or vague.search(version) for version in exact_versions
            ):
                errors.append(f"{label} supported claims require exact producer versions")
            required_evidence = {
                "candidate_commit": candidate_commit,
                "fixture_digest": fixture_digest,
                "environment": evidence.get("environment"),
                "topology": evidence.get("topology"),
                "retained_result": evidence.get("retained_result"),
            }
            for field, value in required_evidence.items():
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{label} supported claims require evidence.{field}")
            if not references:
                errors.append(f"{label} supported claims require evidence references")
            if not row.get("limits"):
                errors.append(f"{label} supported claims require limitations")
    return errors


def _heading_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value).strip().lower()
    value = re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE)
    return re.sub(r"[ ]+", "-", value)


def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        base = _heading_slug(match.group(1))
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def validate_local_links(docs_dir: Path = DOCS_DIR, root: Path = ROOT) -> list[str]:
    """Validate repository-local Markdown links and heading anchors."""

    errors: list[str] = []
    for document in sorted(docs_dir.glob("*.md")):
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            path_text, separator, fragment = target.partition("#")
            resolved = (document.parent / unquote(path_text)).resolve() if path_text else document
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{document.relative_to(root)} link escapes the repository: {target}")
                continue
            if not resolved.is_file():
                errors.append(f"{document.relative_to(root)} has missing local link: {target}")
                continue
            if separator:
                if resolved.suffix.lower() != ".md":
                    errors.append(f"{document.relative_to(root)} anchors non-Markdown target: {target}")
                elif unquote(fragment).lower() not in _anchors(resolved):
                    errors.append(f"{document.relative_to(root)} has missing anchor: {target}")
    return errors


def documented_cli_commands(docs_dir: Path = DOCS_DIR) -> list[tuple[Path, str]]:
    """Return actual command examples, excluding prose about planned option names."""

    commands: list[tuple[Path, str]] = []
    for document in sorted(docs_dir.glob("*.md")):
        text = document.read_text(encoding="utf-8")
        candidates = INLINE_CODE.findall(text)
        for block in FENCED_BLOCK.findall(text):
            candidates.extend(line.strip().removeprefix("$ ") for line in block.splitlines())
        for candidate in candidates:
            try:
                parts = shlex.split(candidate)
            except ValueError:
                continue
            if not parts:
                continue
            is_module = (
                len(parts) >= 3
                and re.fullmatch(r"python(?:3(?:\.\d+)?)?", Path(parts[0]).name)
                and parts[1:3] == ["-m", "obliteratus"]
            )
            if parts[0] == "obliteratus" or is_module:
                commands.append((document, candidate))
    return commands


class _ParserCompleted(Exception):
    """Stop CLI execution immediately after argparse accepts an example."""


def _parse_without_dispatch(argv: list[str]) -> None:
    from obliteratus import cli

    original = argparse.ArgumentParser.parse_args

    def stop_after_parse(parser, args=None, namespace=None):
        original(parser, args, namespace)
        raise _ParserCompleted

    argparse.ArgumentParser.parse_args = stop_after_parse
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                cli.main(argv)
            except _ParserCompleted:
                return
            except SystemExit as exc:
                if exc.code in (None, 0):
                    return
                raise ValueError(f"parser exited with status {exc.code}") from exc
        raise ValueError("CLI returned before the parser boundary was captured")
    finally:
        argparse.ArgumentParser.parse_args = original


def validate_cli_examples(docs_dir: Path = DOCS_DIR, root: Path = ROOT) -> list[str]:
    """Parse documentation commands while stopping before command dispatch."""

    errors: list[str] = []
    for document, command in documented_cli_commands(docs_dir):
        parts = shlex.split(command)
        argv = parts[3:] if parts[0] != "obliteratus" else parts[1:]
        try:
            _parse_without_dispatch(argv)
        except ValueError as exc:
            errors.append(f"{document.relative_to(root)} invalid CLI example {command!r}: {exc}")
    return errors


def validate_all(
    *,
    matrix_path: Path = MATRIX_PATH,
    schema_path: Path = SCHEMA_PATH,
    docs_dir: Path = DOCS_DIR,
    root: Path = ROOT,
) -> list[str]:
    return [
        *validate_matrix(matrix_path, schema_path),
        *validate_local_links(docs_dir, root),
        *validate_cli_examples(docs_dir, root),
    ]


def main() -> int:
    errors = validate_all()
    if errors:
        for error in errors:
            print(f"checkpoint docs validation failed: {error}")
        return 1
    print("checkpoint docs validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
