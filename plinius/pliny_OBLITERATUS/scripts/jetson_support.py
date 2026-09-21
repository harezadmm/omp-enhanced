#!/usr/bin/env python3
"""Collect privacy-safe Jetson runtime evidence for CI and issue reports."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ISSUE_URL = "https://github.com/elder-plinius/OBLITERATUS/issues/31"
JETSON_RELEASE = Path("/etc/nv_tegra_release")
OS_RELEASE = Path("/etc/os-release")
SHA = re.compile(r"^[0-9a-f]{40}$")


def _read_first_line(path: Path, *, limit: int = 500) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[0][:limit]
    except (OSError, IndexError):
        return None


def _os_release(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if separator and key in {"ID", "VERSION_ID", "PRETTY_NAME"}:
            values[key.lower()] = value.strip().strip('"')[:200]
    return values


def _capture(command: Sequence[str], *, timeout: int = 10) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value[:500] or None


def _candidate_sha() -> str:
    candidate = os.environ.get("GITHUB_SHA", "")
    if SHA.fullmatch(candidate):
        return candidate
    local = _capture(["git", "rev-parse", "HEAD"])
    return local if local is not None and SHA.fullmatch(local) else "local"


def collect_host_facts(
    *,
    tegra_release: Path = JETSON_RELEASE,
    os_release: Path = OS_RELEASE,
) -> dict[str, object]:
    """Return an allow-listed host profile without identity or network data."""

    return {
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "os": _os_release(os_release),
        "l4t_release": _read_first_line(tegra_release),
        "jetpack_package": _capture(
            ["dpkg-query", "-W", "-f=${Version}", "nvidia-jetpack"],
        ),
    }


def collect_runtime_facts() -> dict[str, object]:
    """Return an allow-listed PyTorch/GPU profile without serials or file paths."""

    facts: dict[str, object] = {
        "torch_imported": False,
        "torch_version": None,
        "torch_cuda_version": None,
        "cuda_available": False,
        "cuda_device_count": 0,
        "device_name": None,
        "compute_capability": None,
        "total_memory_gb": None,
        "bitsandbytes_version": None,
    }
    try:
        import torch
    except Exception as exc:  # pragma: no cover - exact vendor loader failures vary
        facts["torch_import_error"] = type(exc).__name__
        return facts

    facts.update({
        "torch_imported": True,
        "torch_version": str(torch.__version__),
        "torch_cuda_version": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_count": int(torch.cuda.device_count()),
    })
    if facts["cuda_available"] and facts["cuda_device_count"]:
        properties = torch.cuda.get_device_properties(0)
        facts.update({
            "device_name": str(properties.name)[:200],
            "compute_capability": list(torch.cuda.get_device_capability(0)),
            "total_memory_gb": round(properties.total_memory / 1024 ** 3, 2),
        })
    try:
        facts["bitsandbytes_version"] = importlib.metadata.version("bitsandbytes")
    except importlib.metadata.PackageNotFoundError:
        pass
    return facts


def validate_report(report: dict[str, object]) -> tuple[list[str], list[str]]:
    """Return blocking errors and non-blocking compatibility warnings."""

    host = report["host"]
    runtime = report["runtime"]
    assert isinstance(host, dict)
    assert isinstance(runtime, dict)
    errors: list[str] = []
    warnings: list[str] = []
    if str(host.get("architecture", "")).lower() not in {"aarch64", "arm64"}:
        errors.append("host architecture is not ARM64")
    if not host.get("l4t_release"):
        errors.append("/etc/nv_tegra_release is unavailable; this is not a Jetson L4T runtime")
    if not runtime.get("torch_imported"):
        errors.append("PyTorch could not be imported from the JetPack-aligned runtime")
    elif not runtime.get("torch_cuda_version"):
        errors.append("PyTorch is not a CUDA build")
    elif not runtime.get("cuda_available"):
        errors.append("PyTorch cannot access the Jetson CUDA device")
    if runtime.get("bitsandbytes_version"):
        warnings.append(
            "bitsandbytes is installed but remains unsupported until its pinned Jetson "
            "source build passes the separate quantization probe",
        )
    return errors, warnings


def _gate_summary(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "unavailable"}
    if not isinstance(value, dict):
        return {"status": "invalid"}
    summary: dict[str, object] = {}
    for key in ("gate", "status"):
        if isinstance(value.get(key), str):
            summary[key] = value[key][:100]
    git_sha = value.get("git_sha")
    if isinstance(git_sha, str) and (SHA.fullmatch(git_sha) or git_sha == "local"):
        summary["git_sha"] = git_sha
    counts = value.get("counts")
    if isinstance(counts, dict):
        summary["counts"] = {
            key: counts[key]
            for key in ("tests", "failures", "errors", "skipped")
            if isinstance(counts.get(key), int) and counts[key] >= 0
        }
    return summary


def build_report(*, gate_evidence: Path | None = None) -> dict[str, object]:
    report: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issue": ISSUE_URL,
        "git_sha": _candidate_sha(),
        "host": collect_host_facts(),
        "runtime": collect_runtime_facts(),
    }
    errors, warnings = validate_report(report)
    report["validation"] = {"errors": errors, "warnings": warnings}
    gate = _gate_summary(gate_evidence)
    if gate is not None:
        report["gate_evidence"] = gate
    return report


def issue_body(report: dict[str, object]) -> str:
    return "\n".join([
        "## Jetson runtime report",
        "",
        "### What happened",
        "<!-- Describe the command, expected result, and actual result. -->",
        "",
        "### Reproduction",
        "<!-- Add the smallest command that reproduces the problem. -->",
        "",
        "### Sanitized environment evidence",
        "",
        "```json",
        json.dumps(report, indent=2, sort_keys=True),
        "```",
        "",
        "This report intentionally excludes environment variables, hostnames, usernames,",
        "network addresses, GPU serials, tokens, and local filesystem paths.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("conditional-evidence/jetson-report.json"),
    )
    parser.add_argument("--gate-evidence", type=Path)
    parser.add_argument("--issue-body", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = build_report(gate_evidence=args.gate_evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.issue_body is not None:
        args.issue_body.parent.mkdir(parents=True, exist_ok=True)
        args.issue_body.write_text(issue_body(report), encoding="utf-8")
    validation = report["validation"]
    assert isinstance(validation, dict)
    errors = validation["errors"]
    warnings = validation["warnings"]
    assert isinstance(errors, list)
    assert isinstance(warnings, list)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(args.output)
    return 2 if args.check and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
