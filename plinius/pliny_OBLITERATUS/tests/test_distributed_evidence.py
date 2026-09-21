"""Redacted, atomic distributed-preflight evidence tests."""

from __future__ import annotations

import json
import stat

import pytest

from obliteratus.distributed.contracts import (
    ContractError,
    RuntimeStage,
    StageMessage,
    Vote,
)
from obliteratus.distributed.evidence import (
    PreflightEvidence,
    read_evidence,
    read_stage_message,
    write_evidence,
    write_stage_message,
)


def test_evidence_is_allowlisted_redacted_and_private(tmp_path):
    hostile = "Bearer hf_secret password=/private/model 10.10.0.10 host.internal"
    evidence = PreflightEvidence.failure(
        run_id="1" * 32,
        config_digest="2" * 64,
        code="LMS_DIAGNOSTIC_REDACTION_FAILED",
        world_size=2,
        evidence_tier="protocol_cpu",
        detail=hostile,
    )
    path = tmp_path / "evidence.json"
    write_evidence(path, evidence)
    raw = path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert parsed["result"] == "failed"
    assert parsed["error_code"] == "LMS_DIAGNOSTIC_REDACTION_FAILED"
    assert hostile not in raw
    assert "10.10.0.10" not in raw
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert read_evidence(path) == evidence


def test_cleanup_failure_is_quarantined():
    evidence = PreflightEvidence.failure(
        run_id="1" * 32,
        config_digest="2" * 64,
        code="LMS_CLEANUP_INCOMPLETE",
        world_size=2,
        evidence_tier="candidate_preflight",
        detail="secret",
    )
    assert evidence.result == "quarantined"
    assert evidence.error_code == "LMS_CLEANUP_INCOMPLETE"


def test_evidence_never_overwrites_an_existing_attempt_record(tmp_path):
    evidence = PreflightEvidence.failure(
        run_id="1" * 32,
        config_digest="2" * 64,
        code="LMS_EVIDENCE_UNAVAILABLE",
        world_size=2,
        evidence_tier="candidate_preflight",
    )
    path = tmp_path / "evidence.json"
    write_evidence(path, evidence)
    with pytest.raises(ContractError, match="already exists"):
        write_evidence(path, evidence)


def test_evidence_parent_must_be_private_and_cannot_be_a_symlink(tmp_path):
    evidence = PreflightEvidence.failure(
        run_id="1" * 32,
        config_digest="2" * 64,
        code="LMS_EVIDENCE_UNAVAILABLE",
        world_size=2,
        evidence_tier="candidate_preflight",
    )
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(ContractError, match="private"):
        write_evidence(public / "evidence.json", evidence)
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(private, target_is_directory=True)
    with pytest.raises(ContractError):
        write_evidence(alias / "evidence.json", evidence)


def test_evidence_decoder_rejects_noncanonical_and_duplicate_json():
    duplicate = b'{"schema_version":1,"schema_version":1,"result":"failed"}\n'
    with pytest.raises(ContractError, match="duplicate"):
        PreflightEvidence.from_bytes(duplicate)


def test_lifecycle_receipt_uses_a_distinct_nonterminal_schema(tmp_path):
    message = StageMessage(
        run_id="1" * 32,
        identity_digest="2" * 64,
        rank=0,
        sequence=1,
        stage=RuntimeStage.PREFLIGHTED,
        vote=Vote.PREPARED,
    )
    path = tmp_path / "prepared.stage.json"
    write_stage_message(path, message)
    assert read_stage_message(path) == message
    with pytest.raises(ContractError):
        read_evidence(path)
