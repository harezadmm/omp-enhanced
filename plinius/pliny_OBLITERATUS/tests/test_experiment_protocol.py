from __future__ import annotations

import json

import pytest

from obliteratus.experiment_protocol import (
    build_qwen38_split,
    qwen38_evaluation_pairs,
)


def _corpus(size: int = 842) -> tuple[list[str], list[str]]:
    return (
        [f"harmful-{index}" for index in range(size)],
        [f"harmless-{index}" for index in range(size)],
    )


def test_qwen38_split_is_exact_disjoint_and_reproducible():
    harmful, harmless = _corpus()
    first = build_qwen38_split(harmful, harmless)
    second = build_qwen38_split(list(harmful), list(harmless))

    assert [len(first.train), len(first.tune), len(first.test)] == [500, 142, 200]
    assert first.manifest == second.manifest
    identities = first.manifest["pair_ids"]
    train = set(identities["train"])
    tune = set(identities["tune"])
    test = set(identities["test"])
    assert not train & tune
    assert not train & test
    assert not tune & test
    assert len(train | tune | test) == 842


def test_qwen38_split_manifest_contains_no_prompt_text():
    harmful, harmless = _corpus()
    split = build_qwen38_split(harmful, harmless)
    serialized = json.dumps(split.manifest)

    assert "harmful-0" not in serialized
    assert "harmless-0" not in serialized
    assert len(split.manifest["manifest_sha256"]) == 64


def test_qwen38_experiment_evaluation_partitions_are_fail_closed():
    harmful, harmless = _corpus()
    split = build_qwen38_split(harmful, harmless)

    assert qwen38_evaluation_pairs(split, "E01") is split.test
    assert qwen38_evaluation_pairs(split, "E02") is split.tune
    assert qwen38_evaluation_pairs(split, "E03") is split.tune
    assert not set(split.test) & set(qwen38_evaluation_pairs(split, "E02"))
    assert not set(split.test) & set(qwen38_evaluation_pairs(split, "E03"))
    with pytest.raises(ValueError, match="unregistered Qwen3.8 experiment"):
        qwen38_evaluation_pairs(split, "E04")


def test_qwen38_split_rejects_wrong_size_and_duplicate_pairs():
    harmful, harmless = _corpus(4)
    with pytest.raises(ValueError, match="split sizes total"):
        build_qwen38_split(harmful, harmless)

    harmful, harmless = _corpus()
    harmful[1] = harmful[0]
    harmless[1] = harmless[0]
    with pytest.raises(ValueError, match="duplicate prompt pair"):
        build_qwen38_split(harmful, harmless)
