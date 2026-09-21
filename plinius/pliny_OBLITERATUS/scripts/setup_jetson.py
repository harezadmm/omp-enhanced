#!/usr/bin/env python3
"""Create an OBLITERATUS venv without replacing JetPack's PyTorch runtime."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


EXCLUDED_PACKAGES = {"bitsandbytes", "torch"}
NORMALIZE = re.compile(r"[-_.]+")


def _run(command: Sequence[str], *, cwd: Path) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def _require_new_or_reusable_venv(venv: Path, *, reuse: bool) -> None:
    if not venv.exists():
        return
    if not reuse:
        raise ValueError(f"virtual environment already exists: {venv}; pass --reuse to use it")
    config = venv / "pyvenv.cfg"
    try:
        contents = config.read_text(encoding="utf-8").lower()
    except OSError as exc:
        raise ValueError(f"existing path is not a reusable virtual environment: {venv}") from exc
    if "include-system-site-packages = true" not in contents:
        raise ValueError(f"existing virtual environment does not expose JetPack packages: {venv}")


def _require_safe_target(venv: Path, project: Path) -> None:
    resolved = venv.resolve()
    forbidden = {Path("/").resolve(), Path.home().resolve(), project.resolve()}
    if resolved in forbidden:
        raise ValueError(f"refusing unsafe virtual environment target: {resolved}")


def _require_exclusions(requirements: Path) -> None:
    emitted: set[str] = set()
    for raw_line in requirements.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "--")):
            continue
        name = re.split(r"[<>=!~;@\[]", line, maxsplit=1)[0].strip()
        emitted.add(NORMALIZE.sub("-", name).lower())
    unexpected = sorted(EXCLUDED_PACKAGES & emitted)
    if unexpected:
        raise RuntimeError(f"Jetson export contains forbidden packages: {unexpected}")


def prepare(
    *,
    project: Path,
    venv: Path,
    python: str,
    uv_python: str,
    reuse: bool,
) -> None:
    project = project.resolve()
    support_script = project / "scripts" / "jetson_support.py"
    if not support_script.is_file() or not (project / "uv.lock").is_file():
        raise ValueError(f"not an OBLITERATUS checkout: {project}")
    _require_safe_target(venv, project)
    _require_new_or_reusable_venv(venv, reuse=reuse)

    with tempfile.TemporaryDirectory(prefix="obliteratus-jetson-") as temp_value:
        temp = Path(temp_value)
        _run(
            [python, str(support_script), "--check", "--output", str(temp / "host.json")],
            cwd=project,
        )
        _run([uv_python, "-m", "uv", "--version"], cwd=project)
        if not venv.exists():
            _run([python, "-m", "venv", "--system-site-packages", str(venv)], cwd=project)

        target_python = venv / "bin" / "python"
        _run(
            [
                str(target_python),
                str(support_script),
                "--check",
                "--output",
                str(temp / "venv.json"),
            ],
            cwd=project,
        )
        requirements = temp / "requirements-jetson.txt"
        _run(
            [
                uv_python,
                "-m",
                "uv",
                "export",
                "--locked",
                "--no-default-groups",
                "--extra",
                "dev",
                "--no-emit-project",
                "--no-emit-package",
                "torch",
                "--no-emit-package",
                "bitsandbytes",
                "--no-annotate",
                "--no-header",
                "--no-hashes",
                "--output-file",
                str(requirements),
            ],
            cwd=project,
        )
        _require_exclusions(requirements)
        _run(
            [
                uv_python,
                "-m",
                "uv",
                "pip",
                "install",
                "--python",
                str(target_python),
                "--no-deps",
                "--requirements",
                str(requirements),
            ],
            cwd=project,
        )
        _run(
            [
                uv_python,
                "-m",
                "uv",
                "pip",
                "install",
                "--python",
                str(target_python),
                "--no-deps",
                "--editable",
                str(project),
            ],
            cwd=project,
        )
        _run(
            [uv_python, "-m", "uv", "pip", "check", "--python", str(target_python)],
            cwd=project,
        )

    print("Jetson environment prepared without replacing vendor PyTorch.")
    print(f"Run: {target_python} scripts/run_conditional_gate.py jetson-runtime")
    print(
        f"Then: {target_python} scripts/jetson_support.py --check "
        "--gate-evidence conditional-evidence/jetson-runtime.json "
        "--issue-body conditional-evidence/jetson-issue.md",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--venv", type=Path, default=Path(".venv-jetson"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--uv-python",
        default=sys.executable,
        help="interpreter containing the pinned uv module (defaults to this interpreter)",
    )
    parser.add_argument("--reuse", action="store_true")
    args = parser.parse_args()
    try:
        prepare(
            project=args.project,
            venv=args.venv,
            python=args.python,
            uv_python=args.uv_python,
            reuse=args.reuse,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
