"""Stable, sanitized failures for checkpoint inspection and conversion contracts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


_ERROR_CONTRACTS = {
    "DCI_UNSUPPORTED_FORMAT_OR_VERSION": (
        "unsupported",
        "classification",
        False,
        "Provide an identified supported format or a safe canonical export.",
    ),
    "DCI_TRUST_POLICY_REQUIRED": (
        "trust",
        "policy",
        False,
        "Use structural inspection or obtain separate approval for an exact trust profile.",
    ),
    "DCI_TRUST_POLICY_MISMATCH": (
        "trust",
        "policy",
        False,
        "Use the exact approved policy identity or stop the trusted operation.",
    ),
    "DCI_SOURCE_BOUNDARY_VIOLATION": (
        "source",
        "source",
        False,
        "Repair the immutable local source boundary and inspect it again.",
    ),
    "DCI_SOURCE_CHANGED": (
        "source",
        "source",
        True,
        "Retry with an immutable source snapshot.",
    ),
    "DCI_TRUST_RUNTIME_UNAVAILABLE": (
        "runtime",
        "preflight",
        True,
        "Provision the exact approved disposable runtime before retrying.",
    ),
    "DCI_RUNTIME_IDENTITY_MISMATCH": (
        "runtime",
        "preflight",
        False,
        "Use the exact approved runtime identity and verify it again.",
    ),
    "DCI_FORBIDDEN_READER_CAPABILITY": (
        "runtime",
        "reader",
        False,
        "Remove the forbidden capability; do not weaken the reader policy.",
    ),
    "DCI_RESOURCE_LIMIT": (
        "resource",
        "reader",
        False,
        "Reduce the source or raise a reviewed explicit safety limit.",
    ),
    "DCI_TRUSTED_READER_FAILED": (
        "runtime",
        "reader",
        True,
        "Retain the failure evidence and retry only in the exact approved runtime.",
    ),
    "DCI_WORKER_PROTOCOL_INVALID": (
        "protocol",
        "protocol",
        False,
        "Reject the worker result and correct the versioned protocol implementation.",
    ),
    "DCI_VALIDATION_FAILED": (
        "validation",
        "validation",
        False,
        "Correct the producer-neutral records and validate them again.",
    ),
    "DCI_ADMISSION_DENIED": (
        "resource",
        "admission",
        True,
        "Select sufficient capacity or lower an explicit output bound.",
    ),
    "DCI_MATERIALIZE_FAILED": (
        "output",
        "materialization",
        True,
        "Correct the output failure and retry from the unchanged source.",
    ),
    "DCI_PROMOTION_FAILED": (
        "output",
        "promotion",
        True,
        "Correct the promotion failure and retry from the unchanged source.",
    ),
    "DCI_EVIDENCE_UNAVAILABLE": (
        "evidence",
        "evidence",
        False,
        "Regenerate complete evidence without bypassing validation.",
    ),
    "DCI_DIAGNOSTIC_REDACTION_FAILED": (
        "evidence",
        "evidence",
        False,
        "Suppress the diagnostic and repair redaction before disclosure.",
    ),
    "DCI_CLEANUP_INCOMPLETE": (
        "cleanup",
        "cleanup",
        True,
        "Quarantine the owned scratch path and complete verified cleanup.",
    ),
    "DCI_CONCURRENT_OPERATION_CONFLICT": (
        "concurrency",
        "admission",
        True,
        "Wait for the owning operation or select a distinct destination.",
    ),
    "DCI_HOST_TRUST_UNSATISFIED": (
        "trust",
        "preflight",
        False,
        "Move the operation to an approved isolated host.",
    ),
    "DCI_SECURITY_BASELINE_REVOKED": (
        "runtime",
        "preflight",
        False,
        "Stop and obtain a newly approved security baseline.",
    ),
}


class CheckpointContractError(ValueError):
    """A fail-closed checkpoint refusal with a stable public contract."""

    def __init__(
        self,
        code: str,
        *,
        detail: str,
        affected_refs: Iterable[str] = (),
    ) -> None:
        try:
            category, phase, retryable, next_action = _ERROR_CONTRACTS[code]
        except KeyError as error:  # pragma: no cover - programmer error
            raise ValueError(f"Unknown checkpoint error code: {code}") from error
        references = tuple(sorted({str(reference) for reference in affected_refs}))
        self.code = code
        self.category = category
        self.phase = phase
        self.retryable = retryable
        self.next_action = next_action
        self.detail = detail
        self.affected_refs = references
        super().__init__(f"{code}: {detail}")

    def to_blocker(self) -> dict[str, Any]:
        """Return the strict blocker shape accepted by descriptor contract v1."""
        return {
            "code": self.code,
            "category": self.category,
            "phase": self.phase,
            "affected_refs": list(self.affected_refs),
            "retryable": self.retryable,
            "next_action": self.next_action,
        }

    def to_diagnostic(self) -> dict[str, Any]:
        """Return a deterministic diagnostic without exception chains or local paths."""
        return {**self.to_blocker(), "detail": self.detail}
