"""Contracts for measured KL optimization and exact rollback."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from obliteratus.abliterate import AbliterationPipeline


class _Tokenizer:
    def __call__(self, prompt, **_kwargs):
        length = 2 if prompt == "short" else 3
        return {
            "input_ids": torch.arange(length).unsqueeze(0),
            "attention_mask": torch.ones(1, length, dtype=torch.long),
        }


class _LogitModel(nn.Module):
    def __init__(self, logits_by_length):
        super().__init__()
        self.anchor = nn.Parameter(torch.zeros(1))
        self.logits_by_length = logits_by_length

    def forward(self, input_ids, **_kwargs):
        logits = self.logits_by_length[input_ids.shape[1]].unsqueeze(0)
        return SimpleNamespace(logits=logits)


def _bare_pipeline() -> AbliterationPipeline:
    pipeline = AbliterationPipeline.__new__(AbliterationPipeline)
    pipeline.max_seq_length = 32
    pipeline._quality_metrics = {}
    pipeline._kl_contributions = {}
    pipeline._strong_layers = []
    pipeline._free_gpu_memory = lambda: None
    pipeline.log = lambda _message: None
    return pipeline


def test_sequence_token_kl_matches_hand_computed_forward_kl():
    pristine_short = torch.tensor([[2.0, 0.0], [0.0, 2.0]])
    pristine_long = torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    current_short = torch.tensor([[1.0, 1.0], [0.5, 1.5]])
    current_long = torch.tensor([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])

    pipeline = _bare_pipeline()
    pipeline.handle = SimpleNamespace(
        model=_LogitModel({2: current_short, 3: current_long}),
        tokenizer=_Tokenizer(),
    )
    pipeline._kl_eval_prompts = ["short", "long"]
    pipeline._baseline_token_logits = [pristine_short, pristine_long]

    expected_parts = []
    for pristine, current in (
        (pristine_short, current_short),
        (pristine_long, current_long),
    ):
        log_p = torch.log_softmax(pristine, dim=-1)
        log_q = torch.log_softmax(current, dim=-1)
        expected_parts.append(
            torch.nn.functional.kl_div(
                log_q, log_p, log_target=True, reduction="none",
            ).sum(dim=-1)
        )
    expected = torch.cat(expected_parts).mean().item()
    expected_first = torch.stack([part[-1] for part in expected_parts]).mean().item()

    assert pipeline._measure_sequence_token_kl() == pytest.approx(expected)
    assert pipeline._last_first_token_kl == pytest.approx(expected_first)


@pytest.mark.parametrize("failure", ["missing", "shape", "nonfinite"])
def test_sequence_token_kl_fails_closed_on_invalid_baseline(failure):
    current = torch.zeros(2, 3)
    pipeline = _bare_pipeline()
    pipeline.handle = SimpleNamespace(
        model=_LogitModel({2: current}),
        tokenizer=_Tokenizer(),
    )
    pipeline._kl_eval_prompts = ["short"]
    if failure == "missing":
        pipeline._baseline_token_logits = []
    elif failure == "shape":
        pipeline._baseline_token_logits = [torch.zeros(3, 3)]
    else:
        pipeline._baseline_token_logits = [torch.full((2, 3), float("nan"))]

    with pytest.raises(RuntimeError, match="KL baseline|changed shape|non-finite"):
        pipeline._measure_sequence_token_kl()


def test_layer_snapshot_restore_is_bit_exact():
    layer = nn.Sequential(nn.Linear(3, 4), nn.LayerNorm(4))
    snapshot = AbliterationPipeline._snapshot_layer_state(layer)
    expected = {name: value.clone() for name, value in snapshot.items()}

    with torch.no_grad():
        for value in layer.state_dict(keep_vars=True).values():
            value.add_(torch.randn_like(value))
    AbliterationPipeline._restore_layer_state(layer, snapshot)

    for name, value in layer.state_dict().items():
        assert torch.equal(value.cpu(), expected[name])


def test_optimizer_restores_layers_until_measured_budget_is_met():
    layers = nn.ModuleList([nn.Linear(2, 2, bias=False) for _ in range(2)])
    pristine = {}
    for index, layer in enumerate(layers):
        with torch.no_grad():
            layer.weight.zero_()
        pristine[index] = AbliterationPipeline._snapshot_layer_state(layer)
        with torch.no_grad():
            layer.weight.fill_(1.0)

    pipeline = _bare_pipeline()
    pipeline.kl_budget = 0.5
    pipeline._strong_layers = [0, 1]
    pipeline._measure_sequence_token_kl = lambda: sum(
        layer.weight.abs().sum().item() for layer in layers
    )

    pipeline._kl_optimize_corrections(layers, 2, pristine)

    assert all(torch.equal(layer.weight, torch.zeros_like(layer.weight)) for layer in layers)
    assert pipeline._quality_metrics["kl_divergence"] == 0.0
    assert pipeline._quality_metrics["kl_budget"] == 0.5
    assert set(pipeline._kl_contributions) == {0, 1}
    assert pipeline._strong_layers == []


def test_optimizer_does_not_mutate_layers_at_budget_boundary():
    layer = nn.Linear(2, 2, bias=False)
    pristine = {0: AbliterationPipeline._snapshot_layer_state(layer)}
    expected = layer.weight.detach().clone()
    pipeline = _bare_pipeline()
    pipeline.kl_budget = 0.5
    pipeline._measure_sequence_token_kl = lambda: 0.5

    pipeline._kl_optimize_corrections(nn.ModuleList([layer]), 1, pristine)

    assert torch.equal(layer.weight, expected)


def test_optimizer_fails_when_exact_candidates_cannot_meet_budget():
    layer = nn.Linear(2, 2, bias=False)
    pristine = {0: AbliterationPipeline._snapshot_layer_state(layer)}
    pipeline = _bare_pipeline()
    pipeline.kl_budget = 0.1
    pipeline._measure_sequence_token_kl = lambda: 1.0

    with pytest.raises(RuntimeError, match="could not satisfy"):
        pipeline._kl_optimize_corrections(nn.ModuleList([layer]), 1, pristine)
