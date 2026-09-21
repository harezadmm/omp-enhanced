"""Tests for software-only conditional evidence freshness policy."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from scripts import check_conditional_policy


ROOT = Path(__file__).parents[1]
SHA = "0123456789abcdef0123456789abcdef01234567"
OLD_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TODAY = date(2026, 8, 15)


def _write_evidence(path: Path, gate: str, *, git_sha: str = SHA, status: str = "passed") -> None:
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "gate": gate,
            "status": status,
            "git_sha": git_sha,
        }),
        encoding="utf-8",
    )


def test_software_evidence_accepts_exact_candidate_sha(tmp_path):
    _write_evidence(tmp_path / "network-services.json", "network-services")

    assert check_conditional_policy.validate_evidence(
        ROOT / "ci" / "conditional-test-policy.json",
        tmp_path,
        candidate_sha=SHA,
        required_gates=["network-services"],
    ) == []


def test_software_evidence_rejects_stale_failed_or_mismatched_records(tmp_path):
    _write_evidence(tmp_path / "network-services.json", "wrong-gate", git_sha=OLD_SHA)
    _write_evidence(tmp_path / "operator-ui.json", "operator-ui", status="failed")

    errors = check_conditional_policy.validate_evidence(
        ROOT / "ci" / "conditional-test-policy.json",
        tmp_path,
        candidate_sha=SHA,
        required_gates=["network-services", "operator-ui"],
    )

    assert "conditional evidence network-services records gate 'wrong-gate'" in errors
    assert (
        "conditional evidence network-services git_sha "
        f"'{OLD_SHA}' does not match candidate {SHA}"
    ) in errors
    assert "conditional evidence operator-ui did not pass: 'failed'" in errors


def test_maintainer_exception_only_allows_sha_mismatch(tmp_path):
    _write_evidence(tmp_path / "external-evaluation.json", "external-evaluation", git_sha=OLD_SHA)

    assert check_conditional_policy.validate_evidence(
        ROOT / "ci" / "conditional-test-policy.json",
        tmp_path,
        candidate_sha=SHA,
        required_gates=["external-evaluation"],
        stale_exception_reason="Gate reviewed against equivalent conditional surface.",
        stale_exception_issue="https://github.com/elder-plinius/OBLITERATUS/issues/123",
        stale_exception_expires="2026-08-30",
        today=TODAY,
    ) == []


def test_exception_requires_reason_and_issue_url(tmp_path):
    _write_evidence(tmp_path / "external-evaluation.json", "external-evaluation", git_sha=OLD_SHA)

    errors = check_conditional_policy.validate_evidence(
        ROOT / "ci" / "conditional-test-policy.json",
        tmp_path,
        candidate_sha=SHA,
        required_gates=["external-evaluation"],
        stale_exception_reason="reviewed",
    )

    assert (
        "stale evidence exception requires a reason, a canonical OBLITERATUS issue URL, "
        "and an ISO expiry no more than 30 days away"
    ) in errors
    assert (
        "conditional evidence external-evaluation git_sha "
        f"'{OLD_SHA}' does not match candidate {SHA}"
    ) in errors


def test_evidence_freshness_does_not_make_hardware_lanes_mandatory(tmp_path):
    _write_evidence(tmp_path / "cuda-runtime.json", "cuda-runtime")

    assert check_conditional_policy.validate_evidence(
        ROOT / "ci" / "conditional-test-policy.json",
        tmp_path,
        candidate_sha=SHA,
        required_gates=["cuda-runtime"],
    ) == ["hardware or credential gate is not software-only: cuda-runtime"]


def test_exception_rejects_noncanonical_issue_and_unbounded_expiry(tmp_path):
    _write_evidence(tmp_path / "network-services.json", "network-services", git_sha=OLD_SHA)

    errors = check_conditional_policy.validate_evidence(
        ROOT / "ci" / "conditional-test-policy.json",
        tmp_path,
        candidate_sha=SHA,
        required_gates=["network-services"],
        stale_exception_reason="reviewed",
        stale_exception_issue="https://github.com/elder-plinius/OBLITERATUS/issues/not-a-number",
        stale_exception_expires="2027-01-01",
        today=TODAY,
    )

    assert errors[0].startswith("stale evidence exception requires a reason")
    assert "does not match candidate" in errors[1]
