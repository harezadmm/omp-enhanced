"""Tests for normalized retained test and quality evidence."""

from __future__ import annotations

import pytest

from scripts import write_test_evidence


def _coverage(line: float = 80.0, branch: float = 75.0):
    return {
        "totals": {
            "percent_statements_covered": line,
            "percent_branches_covered": branch,
        },
        "files": {
            "obliteratus/example.py": {
                "summary": {
                    "covered_lines": 8,
                    "num_statements": 10,
                    "covered_branches": 3,
                    "num_branches": 4,
                },
            },
        },
    }


def _risk_map():
    return {"modules": [{"path": "obliteratus/example.py"}]}


def test_coverage_snapshot_records_repository_and_risk_module_metrics():
    snapshot = write_test_evidence.coverage_snapshot(_coverage(), _risk_map())

    assert snapshot == {
        "line_percent": 80.0,
        "branch_percent": 75.0,
        "risk_modules": {
            "obliteratus/example.py": {
                "line_percent": 80.0,
                "branch_percent": 75.0,
            },
        },
    }


def test_junit_snapshot_records_failures_skips_and_slowest_tests(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="3" time="0.9">'
        '<testcase classname="tests.test_a" name="test_pass" time="0.1">'
        '<properties><property name="duration_markers" value="cpu"/></properties>'
        '</testcase>'
        '<testcase classname="tests.test_a" name="test_fail" time="0.3">'
        '<properties><property name="duration_markers" value="cpu,integration"/></properties>'
        '<failure message="boom"/></testcase>'
        '<testcase classname="tests.test_b" name="test_skip" time="0.2">'
        '<properties><property name="duration_markers" value="unmarked"/></properties>'
        '<skipped/></testcase></testsuite></testsuites>',
    )

    snapshot = write_test_evidence.junit_snapshot(junit)
    assert snapshot["total"] == 3
    assert snapshot["passed"] == 1
    assert snapshot["failures"] == ["tests.test_a::test_fail"]
    assert snapshot["skipped"] == ["tests.test_b::test_skip"]
    assert snapshot["duration_seconds"] == 0.6
    assert snapshot["suite_duration_seconds"] == 0.9
    assert snapshot["marker_durations"] == {
        "cpu": {"tests": 2, "duration_seconds": 0.4},
        "integration": {"tests": 1, "duration_seconds": 0.3},
        "unmarked": {"tests": 1, "duration_seconds": 0.2},
    }
    assert len(snapshot["durations"]) == 3
    assert snapshot["marker_metadata_complete"] is True
    assert snapshot["missing_marker_nodeids"] == []
    assert snapshot["slowest"][0] == {
        "nodeid": "tests.test_a::test_fail",
        "seconds": 0.3,
        "markers": ["cpu", "integration"],
    }


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "invalid"])
def test_junit_snapshot_rejects_invalid_testcase_durations(tmp_path, value):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="1" time="1">'
        f'<testcase classname="tests.test_a" name="test_bad" time="{value}"/>'
        '</testsuite></testsuites>',
    )

    with pytest.raises(ValueError, match="invalid time"):
        write_test_evidence.junit_snapshot(junit)


def test_junit_snapshot_rejects_invalid_suite_duration(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="1" time="nan">'
        '<testcase classname="tests.test_a" name="test_pass" time="0.1"/>'
        '</testsuite></testsuites>',
    )

    with pytest.raises(ValueError, match="testsuite has invalid time"):
        write_test_evidence.junit_snapshot(junit)


def test_junit_snapshot_exposes_missing_marker_metadata(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="1" time="0.1">'
        '<testcase classname="tests.test_a" name="test_plain" time="0.1"/>'
        '</testsuite></testsuites>',
    )

    snapshot = write_test_evidence.junit_snapshot(junit)
    assert snapshot["marker_metadata_complete"] is False
    assert snapshot["missing_marker_nodeids"] == ["tests.test_a::test_plain"]


def test_junit_snapshot_rejects_duplicate_marker_properties(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="1" time="0.1">'
        '<testcase classname="tests.test_a" name="test_plain" time="0.1">'
        '<properties>'
        '<property name="duration_markers" value="cpu"/>'
        '<property name="duration_markers" value="integration"/>'
        '</properties></testcase></testsuite></testsuites>',
    )

    with pytest.raises(ValueError, match="repeats duration_markers"):
        write_test_evidence.junit_snapshot(junit)


def test_junit_snapshot_normalizes_empty_marker_and_missing_suite_time(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="1">'
        '<testcase classname="tests.test_a" name="test_plain" time="0.1">'
        '<properties><property name="duration_markers" value=""/></properties>'
        '</testcase></testsuite></testsuites>',
    )

    snapshot = write_test_evidence.junit_snapshot(junit)
    assert snapshot["suite_duration_seconds"] == 0.1
    assert snapshot["durations"][0]["markers"] == ["unmarked"]


def test_junit_snapshot_rejects_non_numeric_suite_duration(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="1" time="invalid">'
        '<testcase classname="tests.test_a" name="test_plain" time="0.1"/>'
        '</testsuite></testsuites>',
    )

    with pytest.raises(ValueError, match="testsuite has invalid time"):
        write_test_evidence.junit_snapshot(junit)


def test_evidence_records_base_deltas_repeat_and_mutation():
    evidence = write_test_evidence.build_evidence(
        head_sha="b" * 40,
        base_sha="a" * 40,
        python_version="3.12",
        coverage=_coverage(80, 75),
        base_coverage=_coverage(79, 74),
        risk_map=_risk_map(),
        repeat={"schema_version": 1, "status": "passed", "passes": []},
        mutation={"killed": 8, "total": 10},
        generated_at="2026-08-14T00:00:00+00:00",
    )

    assert evidence["coverage"]["delta"] == {
        "line_percentage_points": 1.0,
        "branch_percentage_points": 1.0,
    }
    assert evidence["repeat"]["status"] == "passed"
    assert evidence["mutation"] == {
        "killed": 8,
        "total": 10,
        "score_percent": 80.0,
    }


def test_evidence_rejects_missing_inputs_and_malformed_measurements():
    with pytest.raises(ValueError, match="at least one"):
        write_test_evidence.build_evidence(
            head_sha="local",
            base_sha="",
            python_version="3.12",
        )

    malformed = _coverage()
    malformed["files"]["obliteratus/example.py"]["summary"]["covered_lines"] = True
    with pytest.raises(ValueError, match="invalid covered_lines"):
        write_test_evidence.coverage_snapshot(malformed, _risk_map())

    malformed = _coverage(line=float("nan"))
    with pytest.raises(ValueError, match="numeric line"):
        write_test_evidence.coverage_snapshot(malformed, _risk_map())


def test_base_snapshot_allows_risk_module_added_by_head():
    snapshot = write_test_evidence.coverage_snapshot(
        {"totals": _coverage()["totals"], "files": {}},
        _risk_map(),
        allow_missing_risk_modules=True,
    )

    assert snapshot["risk_modules"]["obliteratus/example.py"] == {
        "line_percent": None,
        "branch_percent": None,
    }


def test_mutation_snapshot_rejects_impossible_counts():
    with pytest.raises(ValueError, match="valid killed and total"):
        write_test_evidence.mutation_snapshot({"killed": 2, "total": 1})
