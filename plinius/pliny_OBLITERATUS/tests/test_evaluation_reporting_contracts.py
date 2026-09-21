"""Boundary contracts for evaluation baselines, adapters, and public reports."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch
from torch import nn

from obliteratus.evaluation.baselines import (
    direction_specificity_test,
    random_direction_ablation,
)
from obliteratus.evaluation.evaluator import Evaluator


class _Encoding(dict):
    def to(self, _device):
        return self


class _ClassificationDataset:
    def __init__(self, texts, labels):
        self.texts = list(texts)
        self.labels = list(labels)
        self.selected = None

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return {"text": self.texts[key], "label": self.labels[key]}
        return {"text": self.texts[key], "label": self.labels[key]}

    def select(self, indices):
        indices = list(indices)
        self.selected = indices
        return _ClassificationDataset(
            [self.texts[index] for index in indices],
            [self.labels[index] for index in indices],
        )


class _ClassificationModel(nn.Module):
    def __init__(self, batches):
        super().__init__()
        self.anchor = nn.Parameter(torch.zeros(()))
        self.batches = list(batches)

    def forward(self, **_encodings):
        return SimpleNamespace(logits=torch.tensor(self.batches.pop(0)))


def test_evaluator_dispatches_classification_and_rejects_unknown_tasks():
    dataset = _ClassificationDataset(["a", "b", "ignored"], [1, 0, 1])
    tokenizer = Mock(return_value=_Encoding(input_ids=torch.ones((2, 1), dtype=torch.long)))
    model = _ClassificationModel([[[0.0, 2.0], [3.0, 0.0]]])
    handle = SimpleNamespace(model=model, tokenizer=tokenizer, task="classification")

    result = Evaluator(
        handle,
        dataset,
        metrics=["accuracy", "f1"],
        batch_size=2,
        max_samples=2,
    ).evaluate()

    assert dataset.selected == [0, 1]
    assert result == {"accuracy": 1.0, "f1": 1.0}
    tokenizer.assert_called_once()

    handle.task = "unsupported"
    with pytest.raises(ValueError, match="Unsupported task: unsupported"):
        Evaluator(handle, dataset).evaluate()


def test_classification_returns_only_requested_metrics():
    dataset = _ClassificationDataset(["a"], [0])
    tokenizer = Mock(return_value=_Encoding(input_ids=torch.ones((1, 1), dtype=torch.long)))
    model = _ClassificationModel([[[2.0, 0.0]]])
    handle = SimpleNamespace(model=model, tokenizer=tokenizer, task="classification")

    assert Evaluator(handle, dataset, metrics=["accuracy"]).evaluate() == {"accuracy": 1.0}


def _pipeline(**overrides):
    values = {
        "_strong_layers": [0, 1],
        "refusal_directions": {0: torch.tensor([1.0, 0.0]), 1: torch.tensor([0.0, 1.0])},
        "_harmful_means": {0: torch.tensor([2.0, 0.0]), 1: torch.tensor([0.0, 4.0])},
        "_harmless_means": {0: torch.tensor([0.5, 0.0]), 1: torch.tensor([0.0, 1.0])},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_random_direction_baseline_handles_missing_and_cleared_activations():
    missing = _pipeline(_strong_layers=[], refusal_directions={})
    assert "no directions" in random_direction_ablation(missing).details["error"].lower()

    cleared = _pipeline(_harmful_means={})
    assert "activations cleared" in random_direction_ablation(cleared).details["error"]


def test_random_direction_baseline_is_seeded_and_reports_trial_statistics():
    first = random_direction_ablation(_pipeline(), n_trials=4, seed=17)
    second = random_direction_ablation(_pipeline(), n_trials=4, seed=17)

    assert first == second
    assert first.baseline_name == "random_direction"
    assert first.n_trials == 4
    assert len(first.refusal_rates) == 4
    assert first.refusal_rate == first.mean_refusal_rate
    assert first.std_refusal_rate >= 0
    assert first.details == {"hidden_dim": 2, "n_strong_layers": 2}


def test_direction_specificity_covers_missing_partial_and_complete_inputs():
    assert direction_specificity_test(_pipeline(_strong_layers=[], refusal_directions={})) == {
        "error": "No directions available"
    }
    partial = _pipeline(_harmless_means={})
    assert "activations cleared" in direction_specificity_test(partial)["error"]

    result = direction_specificity_test(_pipeline())
    assert result["harmful_projection"] == 3.0
    assert result["harmless_projection"] == 0.75
    assert result["specificity_ratio"] == 4.0
