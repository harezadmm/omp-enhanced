"""Deterministic orchestration contracts for hyperparameter sweeps."""

from __future__ import annotations

import json

from obliteratus.sweep import SweepConfig, _param_grid, run_sweep


def test_param_grid_is_stable_and_crosses_sorted_keys():
    assert _param_grid({"zeta": [1, 2], "alpha": ["a", "b"]}) == [
        {"alpha": "a", "zeta": 1},
        {"alpha": "a", "zeta": 2},
        {"alpha": "b", "zeta": 1},
        {"alpha": "b", "zeta": 2},
    ]


def test_run_sweep_records_success_failure_seeds_and_incremental_json(
    tmp_path,
    monkeypatch,
):
    created = []

    class Pipeline:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self._quality_metrics = {"score": kwargs["seed"]}
            self._stage_durations = {"probe": 0.25}
            self._strong_layers = [1, 3]
            created.append(self)

        def run(self):
            if self.kwargs["strength"] == 2 and self.kwargs["seed"] == 11:
                raise RuntimeError("intentional sweep failure")

    monkeypatch.setattr("obliteratus.abliterate.AbliterationPipeline", Pipeline)
    output = tmp_path / "sweep"
    config = SweepConfig(
        model_name="fixture/model",
        sweep_params={"strength": [1, 2]},
        fixed_params={"method": "basic"},
        output_dir=str(output),
        seed=10,
        n_seeds=2,
    )

    results = run_sweep(config)

    assert len(results) == 4
    assert [result.seed for result in results] == [10, 11, 10, 11]
    assert results[0].params == {"strength": 1}
    assert results[0].quality_metrics == {"score": 10}
    assert results[0].stage_durations == {"probe": 0.25}
    assert results[0].strong_layers == [1, 3]
    assert results[-1].error == "intentional sweep failure"
    assert results[-1].quality_metrics == {}
    assert [item.kwargs["output_dir"] for item in created] == [
        str(output / f"run_{index:03d}") for index in range(4)
    ]
    assert all(item.kwargs["model_name"] == "fixture/model" for item in created)
    assert all(item.kwargs["method"] == "basic" for item in created)

    saved = json.loads((output / "sweep_results.json").read_text())
    assert len(saved) == 4
    assert saved[0]["quality_metrics"] == {"score": 10}
    assert saved[-1]["error"] == "intentional sweep failure"
