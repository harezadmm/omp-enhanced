"""Stable runtime failures remain aligned with the accepted error registry."""

from __future__ import annotations

import json
from pathlib import Path

from obliteratus.checkpoint_errors import CheckpointContractError


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_error_contract_covers_every_registered_code_exactly():
    registry = json.loads(
        (
            ROOT / "docs/checkpoints/schemas/checkpoint-error-codes-v1.json"
        ).read_text()
    )

    for entry in registry["entries"]:
        error = CheckpointContractError(
            entry["code"],
            detail="bounded_detail",
            affected_refs=("b", "a", "a"),
        )
        assert error.code == entry["code"]
        assert error.category == entry["category"]
        assert error.phase == entry["phase"]
        assert error.affected_refs == ("a", "b")
        assert set(error.to_blocker()) == {
            "code",
            "category",
            "phase",
            "affected_refs",
            "retryable",
            "next_action",
        }
