"""Immutable prompt splits for promotion-grade refusal experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


PROTOCOL_VERSION = "qwen38-v1"
DEFAULT_SEED = "obliteratus:qwen38:v1"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PromptSplit:
    """Disjoint prompt identities and materialized pairs for one experiment."""

    train: tuple[tuple[str, str], ...]
    tune: tuple[tuple[str, str], ...]
    test: tuple[tuple[str, str], ...]
    manifest: dict[str, object]


def qwen38_evaluation_pairs(
    split: PromptSplit,
    experiment: str,
) -> tuple[tuple[str, str], ...]:
    """Return the only evaluation partition authorized for an experiment."""
    partitions = {
        "E01": split.test,
        "E02": split.tune,
        "E03": split.tune,
    }
    try:
        return partitions[experiment]
    except KeyError as exc:
        raise ValueError(f"unregistered Qwen3.8 experiment: {experiment}") from exc


def build_qwen38_split(
    harmful: list[str],
    harmless: list[str],
    *,
    train_size: int = 500,
    tune_size: int = 142,
    test_size: int = 200,
    strata: int = 7,
    seed: str = DEFAULT_SEED,
) -> PromptSplit:
    """Build a stable, position-stratified split without exposing prompt text."""
    if len(harmful) != len(harmless):
        raise ValueError("experiment split requires paired harmful/harmless prompts")
    requested = train_size + tune_size + test_size
    if requested != len(harmful):
        raise ValueError(
            f"split sizes total {requested}, but dataset contains {len(harmful)} pairs"
        )
    if strata < 1:
        raise ValueError("strata must be positive")

    records: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, (bad, good) in enumerate(zip(harmful, harmless, strict=True)):
        pair_id = _digest(f"harmful\0{bad}\0harmless\0{good}")
        if pair_id in seen_ids:
            raise ValueError(f"duplicate prompt pair identity at source index {index}")
        seen_ids.add(pair_id)
        records.append(
            {
                "id": pair_id,
                "stratum": min(strata - 1, index * strata // len(harmful)),
                "pair": (bad, good),
                "key": _digest(f"{seed}\0{pair_id}"),
            }
        )

    quotas = {"train": train_size, "tune": tune_size, "test": test_size}
    assigned: dict[str, list[dict[str, object]]] = {name: [] for name in quotas}
    by_stratum = {
        value: sorted(
            (record for record in records if record["stratum"] == value),
            key=lambda record: str(record["key"]),
        )
        for value in range(strata)
    }
    while any(by_stratum.values()):
        for stratum in range(strata):
            if not by_stratum[stratum]:
                continue
            eligible = [name for name, remaining in quotas.items() if remaining > 0]
            target = max(eligible, key=lambda name: (quotas[name], name))
            assigned[target].append(by_stratum[stratum].pop(0))
            quotas[target] -= 1

    def materialize(name: str) -> tuple[tuple[str, str], ...]:
        return tuple(record["pair"] for record in assigned[name])  # type: ignore[arg-type]

    identities = {
        name: [str(record["id"]) for record in assigned[name]]
        for name in ("train", "tune", "test")
    }
    manifest_core = {
        "protocol": PROTOCOL_VERSION,
        "seed": seed,
        "strata": strata,
        "counts": {name: len(values) for name, values in identities.items()},
        "pair_ids": identities,
    }
    manifest = {
        **manifest_core,
        "manifest_sha256": _digest(
            json.dumps(manifest_core, sort_keys=True, separators=(",", ":"))
        ),
    }
    return PromptSplit(
        train=materialize("train"),
        tune=materialize("tune"),
        test=materialize("test"),
        manifest=manifest,
    )
