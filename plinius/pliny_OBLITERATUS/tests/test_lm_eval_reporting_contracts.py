"""Pure contracts for the lm-eval adapter and public report boundary."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import matplotlib.pyplot as plt
import pytest

from obliteratus.reporting.report import (
    AblationReport,
    AblationResult,
    _sanitize_public_value,
)
from obliteratus.evaluation import lm_eval_integration as LM_EVAL


def test_lm_eval_missing_dependency_has_actionable_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "lm_eval", None)
    with pytest.raises(ImportError, match="pip install lm-eval>=0.4.0"):
        LM_EVAL.run_benchmarks("model")


def test_lm_eval_preserves_measured_zero_and_falls_back_to_numeric_metric(monkeypatch):
    simple_evaluate = Mock(return_value={
        "results": {
            "zero": {"acc,none": 0.0, "acc_norm,none": 0.75},
            "normalized": {"acc_norm,none": 0.6},
            "fallback": {"alias": "name", "stderr": 0.02, "score": 0.4},
            "empty": {"alias": "empty"},
        }
    })
    monkeypatch.setitem(sys.modules, "lm_eval", SimpleNamespace(simple_evaluate=simple_evaluate))

    scores = LM_EVAL.run_benchmarks(
        "org/model",
        tasks=["zero", "normalized", "fallback", "empty"],
        device="cpu",
        batch_size=3,
        num_fewshot=2,
        limit=5,
    )

    assert scores == {"zero": 0.0, "normalized": 0.6, "fallback": 0.02}
    simple_evaluate.assert_called_once_with(
        model="hf",
        model_args="pretrained=org/model,device=cpu",
        tasks=["zero", "normalized", "fallback", "empty"],
        batch_size=3,
        num_fewshot=2,
        limit=5,
    )


def test_lm_eval_defaults_and_model_comparison(monkeypatch):
    simple_evaluate = Mock(return_value={"results": {"task": {"acc,none": 0.5}}})
    monkeypatch.setitem(sys.modules, "lm_eval", SimpleNamespace(simple_evaluate=simple_evaluate))
    assert LM_EVAL.run_benchmarks("model", tasks=["task"]) == {"task": 0.5}
    assert simple_evaluate.call_args.kwargs["model_args"] == "pretrained=model"

    responses = iter([{"a": 0.8, "shared": 0.5}, {"b": 0.4, "shared": 0.7}])
    monkeypatch.setattr(
        LM_EVAL,
        "run_benchmarks",
        lambda *_args, **_kwargs: next(responses),
    )
    assert LM_EVAL.compare_models("original", "abliterated") == {
        "a": {"original": 0.8, "abliterated": 0.0, "delta": -0.8},
        "b": {"original": 0.0, "abliterated": 0.4, "delta": 0.4},
        "shared": {"original": 0.5, "abliterated": 0.7, "delta": pytest.approx(0.2)},
    }


def test_report_sanitizes_sequences_objects_windows_paths_and_long_labels():
    custom = SimpleNamespace(value="/private/path/item")
    sanitized = _sanitize_public_value({
        "items": ("C:\\private\\model.bin", custom),
        "api-key": "must disappear",
        "finite": 1.5,
        "infinite": float("inf"),
    })
    assert "api-key" not in sanitized
    assert sanitized["finite"] == 1.5
    assert sanitized["infinite"] is None
    assert sanitized["items"][0] == "model.bin"
    assert "private/path" not in sanitized["items"][1]

    report = AblationReport(model_name="x" * 100)
    assert report.to_dict()["model_name"].endswith("...")
    assert len(report.to_dict()["model_name"]) == 80


def test_report_summary_empty_and_populated(capsys):
    AblationReport("empty").print_summary()
    assert "No ablation results" in capsys.readouterr().out

    report = AblationReport("model")
    report.add_baseline({"score": 0.0, "missing": None})
    report.add_result(AblationResult("s", "c", "d", {"score": 1.0, "missing": None}))
    report.print_summary()
    output = capsys.readouterr().out
    assert "Ablation Results: model" in output
    assert "unavailable" in output


def test_report_plot_boundaries(monkeypatch, tmp_path):
    report = AblationReport("model")
    report.add_baseline({"score": 2.0})
    report.add_result(AblationResult("s", "positive", "d", {"score": 3.0}))
    report.add_result(AblationResult("s", "negative", "d", {"score": 1.0}))

    impact = tmp_path / "nested" / "impact.png"
    impact.parent.mkdir()
    report.plot_impact(output_path=impact)
    assert impact.stat().st_size > 0

    heatmap = tmp_path / "heatmap.png"
    report.plot_heatmap(heatmap)
    assert heatmap.stat().st_size > 0

    show = Mock()
    monkeypatch.setattr(plt, "show", show)
    report.plot_impact(metric="score")
    report.plot_heatmap()
    assert show.call_count == 2

    no_delta = AblationReport("model", baseline_metrics={"score": None})
    no_delta.add_result(AblationResult("s", "c", "d", {"score": 1.0}))
    with pytest.raises(ValueError, match="No delta column"):
        no_delta.plot_impact("score")
    no_delta.plot_heatmap()
