"""Offline contracts for checkpoint documentation and support claims."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import check_checkpoint_docs


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _matrix() -> dict:
    return json.loads(
        (ROOT / "docs/checkpoints/support-matrix-v1.json").read_text(encoding="utf-8"),
    )


def test_checkpoint_documentation_contract_passes_offline():
    assert check_checkpoint_docs.validate_all() == []


def test_support_matrix_rejects_unknown_fields_and_duplicate_rows(tmp_path):
    matrix = _matrix()
    matrix["unexpected"] = True
    matrix["rows"].append(matrix["rows"][0])
    path = tmp_path / "matrix.json"
    _write_json(path, matrix)

    errors = check_checkpoint_docs.validate_matrix(path)

    assert "support matrix has unknown fields: unexpected" in errors
    assert any("duplicate row id" in error for error in errors)


def test_supported_claim_requires_exact_retained_evidence(tmp_path):
    matrix = _matrix()
    row = matrix["rows"][0]
    row["capabilities"]["detect"]["value"] = "supported"
    row["producer_versions"] = ["Transformers compatible; exact version varies"]
    row["evidence"].update(
        candidate_commit=None,
        fixture_digest=None,
        retained_result=None,
    )
    path = tmp_path / "matrix.json"
    _write_json(path, matrix)

    errors = check_checkpoint_docs.validate_matrix(path)

    assert any("exact producer versions" in error for error in errors)
    assert any("evidence.candidate_commit" in error for error in errors)
    assert any("evidence.fixture_digest" in error for error in errors)
    assert any("evidence.retained_result" in error for error in errors)


def test_local_link_validator_rejects_missing_file_and_anchor(tmp_path):
    docs = tmp_path / "docs/checkpoints"
    docs.mkdir(parents=True)
    (docs / "guide.md").write_text(
        "# Guide\n\n[missing](missing.md) [anchor](target.md#absent)\n",
        encoding="utf-8",
    )
    (docs / "target.md").write_text("# Present\n", encoding="utf-8")

    errors = check_checkpoint_docs.validate_local_links(docs, tmp_path)

    assert any("missing local link" in error for error in errors)
    assert any("missing anchor" in error for error in errors)


def test_documented_cli_examples_stop_before_dispatch(monkeypatch, tmp_path):
    docs = tmp_path / "docs/checkpoints"
    docs.mkdir(parents=True)
    (docs / "guide.md").write_text(
        "Run `python3 -m obliteratus --help` to inspect current syntax.\n",
        encoding="utf-8",
    )
    dispatched = False

    def forbidden_dispatch(_args):
        nonlocal dispatched
        dispatched = True
        raise AssertionError("model command dispatch must not run")

    monkeypatch.setattr("obliteratus.cli._apply_gpu_selection", forbidden_dispatch)

    assert check_checkpoint_docs.validate_cli_examples(docs, tmp_path) == []
    assert dispatched is False


def test_invalid_documented_cli_example_fails_closed(tmp_path):
    docs = tmp_path / "docs/checkpoints"
    docs.mkdir(parents=True)
    (docs / "guide.md").write_text(
        "Run `obliteratus --not-a-real-option` for diagnostics.\n",
        encoding="utf-8",
    )

    errors = check_checkpoint_docs.validate_cli_examples(docs, tmp_path)

    assert len(errors) == 1
    assert "invalid CLI example" in errors[0]
