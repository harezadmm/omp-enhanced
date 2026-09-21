#!/usr/bin/env python3
"""Validate conditional-gate policy and its CPU-coverage mappings."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path


REQUIRED_GATE_FIELDS = {
    "id", "job", "marker", "runner", "prerequisites", "expected_cost", "coverage_paths"
}
REQUIRED_WAIVER_FIELDS = {
    "gate", "reason", "issue", "opened", "expires", "blocked_claim"
}
SOFTWARE_ONLY_GATES = (
    "model-download-runtime",
    "external-evaluation",
    "network-services",
    "operator-ui",
)
SHA = re.compile(r"^[0-9a-f]{40}$")
ISSUE_URL = re.compile(
    r"^https://github\.com/elder-plinius/OBLITERATUS/issues/[1-9][0-9]*$",
)
MAX_STALE_EXCEPTION_DAYS = 30
MAX_ENVIRONMENT_WAIVER_DAYS = 30


def validate_environment_waivers(
    policy: dict,
    *,
    today: date | None = None,
) -> tuple[dict[str, dict], list[str]]:
    """Return active gate waivers and structural/lifetime errors."""

    errors: list[str] = []
    active: dict[str, dict] = {}
    today = today or date.today()
    gates = policy.get("gates", [])
    gate_ids = {
        gate.get("id")
        for gate in gates
        if isinstance(gate, dict) and isinstance(gate.get("id"), str)
    }
    waivers = policy.get("environment_waivers", [])
    if not isinstance(waivers, list):
        return {}, ["conditional policy environment_waivers must be a list"]

    seen: set[str] = set()
    for index, waiver in enumerate(waivers):
        label = f"environment waiver {index}"
        if not isinstance(waiver, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = REQUIRED_WAIVER_FIELDS - set(waiver)
        if missing:
            errors.append(f"{label} is missing fields: {sorted(missing)}")
            continue

        gate_id = waiver["gate"]
        if not isinstance(gate_id, str) or not gate_id:
            errors.append(f"{label} gate must be a non-empty string")
            continue
        if gate_id in seen:
            errors.append(f"duplicate environment waiver gate: {gate_id}")
            continue
        seen.add(gate_id)
        valid = True
        if gate_id not in gate_ids:
            errors.append(f"environment waiver references unknown gate: {gate_id}")
            valid = False
        if gate_id in SOFTWARE_ONLY_GATES:
            errors.append(f"software-only gate may not use an environment waiver: {gate_id}")
            valid = False

        for field in ("reason", "blocked_claim"):
            value = waiver[field]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"environment waiver {gate_id} {field} must be non-empty")
                valid = False
        issue = waiver["issue"]
        if not isinstance(issue, str) or ISSUE_URL.fullmatch(issue) is None:
            errors.append(f"environment waiver {gate_id} issue must be a canonical issue URL")
            valid = False

        try:
            opened = date.fromisoformat(waiver["opened"])
            expires = date.fromisoformat(waiver["expires"])
        except (TypeError, ValueError):
            errors.append(f"environment waiver {gate_id} opened/expires must be ISO dates")
            continue
        if opened > today:
            errors.append(f"environment waiver {gate_id} opens in the future: {opened}")
            valid = False
        if expires < opened:
            errors.append(f"environment waiver {gate_id} expires before it opens")
            valid = False
        elif expires > opened + timedelta(days=MAX_ENVIRONMENT_WAIVER_DAYS):
            errors.append(
                f"environment waiver {gate_id} exceeds {MAX_ENVIRONMENT_WAIVER_DAYS} days",
            )
            valid = False
        if expires < today:
            errors.append(f"environment waiver {gate_id} expired on {expires}")
            valid = False

        if valid:
            active[gate_id] = waiver
    return active, errors


def validate(
    policy_path: Path,
    quality_path: Path,
    workflow_path: Path,
    *,
    today: date | None = None,
) -> list[str]:
    errors: list[str] = []
    policy = json.loads(policy_path.read_text())
    quality = json.loads(quality_path.read_text())
    workflow = workflow_path.read_text()

    if policy.get("schema_version") != 1:
        errors.append("conditional policy schema_version must be 1")
    for key in ("owner", "cadence", "evidence_retention_days", "maximum_evidence_age_days"):
        if not policy.get(key):
            errors.append(f"conditional policy is missing {key}")

    gates = policy.get("gates")
    if not isinstance(gates, list) or not gates:
        return errors + ["conditional policy gates must be a non-empty list"]

    by_id: dict[str, dict] = {}
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            errors.append(f"gate {index} must be an object")
            continue
        missing = REQUIRED_GATE_FIELDS - set(gate)
        if missing:
            errors.append(f"gate {index} is missing fields: {sorted(missing)}")
            continue
        gate_id = gate["id"]
        if gate_id in by_id:
            errors.append(f"duplicate conditional gate id: {gate_id}")
        by_id[gate_id] = gate
        if not gate["coverage_paths"]:
            errors.append(f"gate {gate_id} has no coverage paths")
        if f"{gate['job']}:" not in workflow:
            errors.append(f"workflow job {gate['job']!r} for {gate_id} was not found")
        for source_path in gate["coverage_paths"]:
            if not Path(source_path).is_file():
                errors.append(f"gate {gate_id} maps missing source path: {source_path}")

    exclusions = quality.get("mature_cpu_scope", {}).get("exclusions", [])
    for exclusion in exclusions:
        gate_id = exclusion.get("conditional_gate")
        source_path = exclusion.get("path")
        if gate_id not in by_id:
            errors.append(f"CPU exclusion {source_path} references unknown gate {gate_id}")
            continue
        if source_path not in by_id[gate_id]["coverage_paths"]:
            errors.append(f"CPU exclusion {source_path} is not mapped by gate {gate_id}")

    required_workflow_tokens = (
        "workflow_dispatch:", "schedule:", "release:", "permissions:", "contents: read",
        "scripts/run_conditional_gate.py", "scripts/conditional_gate_summary.py",
    )
    for token in required_workflow_tokens:
        if token not in workflow:
            errors.append(f"conditional workflow is missing {token!r}")
    _, waiver_errors = validate_environment_waivers(policy, today=today)
    errors.extend(waiver_errors)
    return errors


def _load_json_object(path: Path, label: str, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read {label}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} root must be an object")
        return {}
    return value


def _valid_stale_exception(
    reason: str | None,
    issue: str | None,
    expires: str | None,
    *,
    today: date,
) -> bool:
    if not isinstance(reason, str) or not reason.strip():
        return False
    if not isinstance(issue, str) or ISSUE_URL.fullmatch(issue) is None:
        return False
    if not isinstance(expires, str):
        return False
    try:
        expiry = date.fromisoformat(expires)
    except ValueError:
        return False
    return today <= expiry <= today + timedelta(days=MAX_STALE_EXCEPTION_DAYS)


def validate_evidence(
    policy_path: Path,
    evidence_dir: Path,
    *,
    candidate_sha: str,
    required_gates: list[str] | None = None,
    stale_exception_reason: str | None = None,
    stale_exception_issue: str | None = None,
    stale_exception_expires: str | None = None,
    today: date | None = None,
) -> list[str]:
    """Validate selected software-only conditional evidence against a candidate SHA."""

    errors: list[str] = []
    policy = _load_json_object(policy_path, "conditional policy", errors)
    if errors:
        return errors

    if SHA.fullmatch(candidate_sha) is None:
        errors.append("candidate SHA must be a 40-character lowercase hex commit")

    gates = policy.get("gates")
    policy_gate_ids = {
        gate.get("id")
        for gate in gates
        if isinstance(gates, list) and isinstance(gate, dict)
    } if isinstance(gates, list) else set()
    requested = required_gates or list(SOFTWARE_ONLY_GATES)
    for gate_id in requested:
        if gate_id not in SOFTWARE_ONLY_GATES:
            errors.append(f"hardware or credential gate is not software-only: {gate_id}")
        if gate_id not in policy_gate_ids:
            errors.append(f"conditional policy does not define gate {gate_id}")

    today = today or date.today()
    exception = _valid_stale_exception(
        stale_exception_reason,
        stale_exception_issue,
        stale_exception_expires,
        today=today,
    )
    if (
        stale_exception_reason
        or stale_exception_issue
        or stale_exception_expires
    ) and not exception:
        errors.append(
            "stale evidence exception requires a reason, a canonical OBLITERATUS issue URL, "
            "and an ISO expiry no more than 30 days away",
        )

    for gate_id in requested:
        evidence = _load_json_object(
            evidence_dir / f"{gate_id}.json",
            f"conditional evidence {gate_id}",
            errors,
        )
        if not evidence:
            continue
        if evidence.get("gate") != gate_id:
            errors.append(f"conditional evidence {gate_id} records gate {evidence.get('gate')!r}")
        if evidence.get("status") != "passed":
            errors.append(f"conditional evidence {gate_id} did not pass: {evidence.get('status')!r}")
        evidence_sha = evidence.get("git_sha")
        if evidence_sha != candidate_sha and not exception:
            errors.append(
                f"conditional evidence {gate_id} git_sha {evidence_sha!r} "
                f"does not match candidate {candidate_sha}",
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("ci/conditional-test-policy.json"))
    parser.add_argument("--quality", type=Path, default=Path("ci/test-quality-policy.json"))
    parser.add_argument(
        "--workflow", type=Path, default=Path(".github/workflows/conditional-tests.yml")
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="validate software-only conditional evidence files in this directory",
    )
    parser.add_argument(
        "--candidate-sha",
        help="40-character candidate commit SHA required for evidence freshness validation",
    )
    parser.add_argument(
        "--require-gate",
        action="append",
        default=[],
        help="software-only gate that must have current passed evidence (repeatable)",
    )
    parser.add_argument(
        "--stale-evidence-reason",
        default="",
        help="maintainer reason for accepting older software conditional evidence",
    )
    parser.add_argument(
        "--stale-evidence-issue",
        default="",
        help="OBLITERATUS issue URL approving older software conditional evidence",
    )
    parser.add_argument(
        "--stale-evidence-expires",
        default="",
        help="ISO expiry date for a stale-evidence waiver (maximum 30 days)",
    )
    args = parser.parse_args()
    errors = validate(args.policy, args.quality, args.workflow)
    if args.evidence_dir is not None:
        if not args.candidate_sha:
            errors.append("evidence freshness validation requires --candidate-sha")
        else:
            errors.extend(
                validate_evidence(
                    args.policy,
                    args.evidence_dir,
                    candidate_sha=args.candidate_sha,
                    required_gates=args.require_gate or None,
                    stale_exception_reason=args.stale_evidence_reason or None,
                    stale_exception_issue=args.stale_evidence_issue or None,
                    stale_exception_expires=args.stale_evidence_expires or None,
                ),
            )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("conditional test policy: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
