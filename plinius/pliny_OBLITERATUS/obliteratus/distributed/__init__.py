"""Fail-closed contracts for the opt-in distributed runtime prototype."""

from obliteratus.distributed.config import DistributedPreflightConfig
from obliteratus.distributed.consensus import require_record_consensus
from obliteratus.distributed.contracts import (
    ContractError,
    LogicalPlacement,
    PlacementKind,
    RankInventory,
    RunIdentity,
    RuntimeStage,
    RuntimeContractError,
    StageMessage,
    TopologyPlan,
    Vote,
    advance_stage,
    canonical_record,
    contract_digest,
    validate_inventory_consensus,
)
from obliteratus.distributed.evidence import PreflightEvidence
from obliteratus.distributed.launcher import TorchrunEnvironment
from obliteratus.distributed.preflight import PreflightResult, RankAttestation

__all__ = [
    "ContractError",
    "DistributedPreflightConfig",
    "LogicalPlacement",
    "PlacementKind",
    "PreflightEvidence",
    "PreflightResult",
    "RankInventory",
    "RunIdentity",
    "RankAttestation",
    "RuntimeStage",
    "RuntimeContractError",
    "StageMessage",
    "TopologyPlan",
    "TorchrunEnvironment",
    "Vote",
    "advance_stage",
    "canonical_record",
    "contract_digest",
    "require_record_consensus",
    "validate_inventory_consensus",
]
