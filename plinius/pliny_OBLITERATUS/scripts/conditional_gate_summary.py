#!/usr/bin/env python3
"""Build a final conditional-workflow result and freshness summary."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

try:
    from scripts.check_conditional_policy import validate_environment_waivers
except ModuleNotFoundError:  # Direct execution adds scripts/, not the repository root.
    from check_conditional_policy import validate_environment_waivers


def summarize(
    policy: dict,
    results: dict,
    selected: dict,
    *,
    today: date | None = None,
) -> tuple[list[dict], list[str]]:
    """Return per-gate rows and selected-job failures."""
    waivers, waiver_errors = validate_environment_waivers(policy, today=today)
    failures = [f"waiver policy: {error}" for error in waiver_errors]
    rows: list[dict] = []
    failed_jobs: set[str] = set()
    for gate in policy["gates"]:
        job = gate["job"]
        is_selected = bool(selected.get(job, False))
        result = results.get(job, "unknown")
        waiver = waivers.get(gate["id"])
        if is_selected:
            status = result
        elif waiver is not None:
            status = "waived_no_support_claim"
        else:
            status = "not_selected_no_fresh_evidence"
        if is_selected and result != "success" and job not in failed_jobs:
            failures.append(f"{job}: selected but result was {result}")
            failed_jobs.add(job)
        row = {"gate": gate["id"], "job": job, "selected": is_selected, "status": status}
        if not is_selected and waiver is not None:
            row["waiver"] = {
                "issue": waiver["issue"],
                "expires": waiver["expires"],
                "blocked_claim": waiver["blocked_claim"],
            }
        rows.append(row)
    return rows, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("ci/conditional-test-policy.json"))
    parser.add_argument("--output", type=Path, default=Path("conditional-evidence/summary.json"))
    parser.add_argument("--results-json", default=os.environ.get("CONDITIONAL_RESULTS", "{}"))
    parser.add_argument("--selected-json", default=os.environ.get("CONDITIONAL_SELECTED", "{}"))
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    results = json.loads(args.results_json)
    selected = json.loads(args.selected_json)
    rows, failures = summarize(policy, results, selected)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": os.environ.get("GITHUB_SHA", "local"),
        "maximum_evidence_age_days": policy["maximum_evidence_age_days"],
        "gates": rows,
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [
            "## Conditional test evidence",
            "",
            "| Gate | Job | Status | Constraint |",
            "|---|---|---|---|",
        ]
        for row in rows:
            waiver = row.get("waiver")
            constraint = ""
            if waiver is not None:
                constraint = (
                    f"No support claim; expires {waiver['expires']}; "
                    f"[tracker]({waiver['issue']})"
                )
            lines.append(
                f"| {row['gate']} | {row['job']} | {row['status']} | {constraint} |",
            )
        lines.extend(["", f"Evidence becomes stale after {policy['maximum_evidence_age_days']} days."])
        with Path(summary_path).open("a") as handle:
            handle.write("\n".join(lines) + "\n")
    for failure in failures:
        print(f"ERROR: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
