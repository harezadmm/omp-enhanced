from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from obliteratus.checkpoint_evaluation import (
    _partition_pairs,
    _verify_checkpoint_inventory,
)


def test_protocol_evaluation_partitions_are_immutable_and_disjoint():
    tune = _partition_pairs("optimizer_tune")
    final = _partition_pairs("final_test")

    assert len(tune) == 142
    assert len(final) == 200
    assert set(tune).isdisjoint(final)
    with pytest.raises(ValueError, match="unsupported"):
        _partition_pairs("training")


def test_checkpoint_inventory_verifies_size_hash_and_managed_path(tmp_path):
    run_dir = tmp_path / ("run-" + "a" * 32)
    checkpoint = run_dir / "checkpoint"
    checkpoint.mkdir(parents=True)
    weights = checkpoint / "weights.bin"
    weights.write_bytes(b"verified weights")
    inventory = run_dir / "artifact-inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "path": "checkpoint/weights.bin",
                        "bytes": weights.stat().st_size,
                        "sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest = {"result": {"checkpoint": str(checkpoint), "inventory": str(inventory)}}

    assert _verify_checkpoint_inventory(run_dir, manifest) == checkpoint.resolve()
    weights.write_bytes(b"tampered weights")
    with pytest.raises(ValueError, match="hash changed"):
        _verify_checkpoint_inventory(run_dir, manifest)


def _inventory_candidate(tmp_path):
    run_dir = tmp_path / ("run-" + "b" * 32)
    checkpoint = run_dir / "checkpoint"
    checkpoint.mkdir(parents=True)
    weights = checkpoint / "weights.bin"
    weights.write_bytes(b"verified weights")
    inventory = run_dir / "artifact-inventory.json"
    artifact = {
        "path": "checkpoint/weights.bin",
        "bytes": weights.stat().st_size,
        "sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
    }
    inventory.write_text(json.dumps({"artifacts": [artifact]}), encoding="utf-8")
    manifest = {"result": {"checkpoint": str(checkpoint), "inventory": str(inventory)}}
    return run_dir, checkpoint, inventory, artifact, manifest


def test_checkpoint_inventory_rejects_unmanaged_empty_and_noncheckpoint_records(tmp_path):
    run_dir, checkpoint, inventory, artifact, manifest = _inventory_candidate(tmp_path)

    manifest["result"]["checkpoint"] = str(tmp_path / "outside")
    with pytest.raises(ValueError, match="outside its managed"):
        _verify_checkpoint_inventory(run_dir, manifest)

    manifest["result"]["checkpoint"] = str(checkpoint)
    for value, message in (([], "empty"), ([{"path": "notes.md"}], "no checkpoint")):
        inventory.write_text(json.dumps({"artifacts": value}), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            _verify_checkpoint_inventory(run_dir, manifest)

    artifact["path"] = "checkpoint/../notes.md"
    inventory.write_text(json.dumps({"artifacts": [artifact]}), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid checkpoint artifact"):
        _verify_checkpoint_inventory(run_dir, manifest)


def test_checkpoint_inventory_rejects_size_change(tmp_path):
    run_dir, _checkpoint, inventory, artifact, manifest = _inventory_candidate(tmp_path)
    artifact["bytes"] += 1
    inventory.write_text(json.dumps({"artifacts": [artifact]}), encoding="utf-8")

    with pytest.raises(ValueError, match="size changed"):
        _verify_checkpoint_inventory(run_dir, manifest)


class _FakeLifecycle:
    def __init__(self):
        self.events = []

    def loading(self, checkpoint):
        self.events.append(("loading", checkpoint))

    def resize(self, memory):
        self.events.append(("resize", memory))

    def ready(self, memory):
        self.events.append(("ready", memory))

    def release(self, *, reason):
        self.events.append(("release", reason))


class _FakeArchive:
    def __init__(self, run_dir: Path, manifest):
        self.run_dir = run_dir
        self.manifest = manifest
        self.finishes = []

    def begin_evaluation(self, run_id, *, partition, evaluator):
        assert run_id == self.manifest["run_id"]
        self.reservation = (partition, evaluator)
        return {"evaluation_id": "eval-" + "c" * 32}

    def result(self, run_id):
        assert run_id == self.manifest["run_id"]
        return self.manifest

    def _run_dir(self, run_id):
        assert run_id == self.manifest["run_id"]
        return self.run_dir

    def finish_evaluation(self, run_id, evaluation_id, **kwargs):
        self.finishes.append((run_id, evaluation_id, kwargs))


@pytest.mark.parametrize(
    ("refusal_rate", "coherence", "expected"),
    [(0.2, 0.9, 0), (0.3, 0.9, 2), (0.2, 0.79, 2)],
)
def test_evaluate_reloads_verifies_and_records_objective(
    tmp_path,
    monkeypatch,
    refusal_rate,
    coherence,
    expected,
):
    import obliteratus.checkpoint_evaluation as checkpoint_evaluation

    run_dir, checkpoint, _inventory, _artifact, manifest = _inventory_candidate(tmp_path)
    run_id = run_dir.name
    manifest["run_id"] = run_id
    manifest["result"]["metrics"] = {
        "baseline_perplexity": 3.5,
        "baseline_coherence": 0.95,
    }
    archive = _FakeArchive(run_dir, manifest)
    lifecycle = _FakeLifecycle()
    pipelines = []

    class FakePipeline:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self._quality_metrics = {
                "refusal_rate": refusal_rate,
                "coherence": coherence,
            }
            self.cleaned = False
            pipelines.append(self)

        def _summon(self):
            self.kwargs["on_log"]("loaded")

        def _verify(self):
            self.kwargs["on_log"]("verified")

        def cleanup_failed_run(self):
            self.cleaned = True

    memory = SimpleNamespace(reserved_bytes=1)
    monkeypatch.setattr(checkpoint_evaluation, "RunArchive", lambda _root: archive)
    monkeypatch.setattr(checkpoint_evaluation, "from_environment", lambda: lifecycle)
    monkeypatch.setattr(checkpoint_evaluation, "AbliterationPipeline", FakePipeline)
    monkeypatch.setattr(checkpoint_evaluation, "_partition_pairs", lambda _part: (("h", "s"),))
    monkeypatch.setattr(checkpoint_evaluation, "measure_torch_memory", lambda _torch: memory)

    assert checkpoint_evaluation.evaluate(run_id, "optimizer_tune", str(tmp_path)) == expected
    assert archive.reservation == (
        "optimizer_tune",
        checkpoint_evaluation.EVALUATOR_VERSION,
    )
    assert pipelines[0].kwargs["model_name"] == str(checkpoint.resolve())
    assert pipelines[0]._stock_baseline == {"perplexity": 3.5, "coherence": 0.95}
    assert pipelines[0].cleaned is True
    metrics = archive.finishes[0][2]["metrics"]
    assert metrics["passes_objective"] is (expected == 0)
    assert archive.finishes[0][2]["log"] == ["loaded", "verified"]
    assert lifecycle.events[-1] == ("release", "evaluation_optimizer_tune_complete")


def test_evaluate_records_failure_and_releases_lifecycle(tmp_path, monkeypatch):
    import obliteratus.checkpoint_evaluation as checkpoint_evaluation

    run_dir, _checkpoint, _inventory, _artifact, manifest = _inventory_candidate(tmp_path)
    run_id = run_dir.name
    manifest["run_id"] = run_id
    manifest["result"]["metrics"] = {
        "baseline_perplexity": 3.5,
        "baseline_coherence": 0.95,
    }
    archive = _FakeArchive(run_dir, manifest)
    lifecycle = _FakeLifecycle()

    class FailedPipeline:
        _quality_metrics = {}

        def __init__(self, **_kwargs):
            pass

        def _summon(self):
            raise RuntimeError("summon failed")

        def cleanup_failed_run(self):
            self.cleaned = True

    monkeypatch.setattr(checkpoint_evaluation, "RunArchive", lambda _root: archive)
    monkeypatch.setattr(checkpoint_evaluation, "from_environment", lambda: lifecycle)
    monkeypatch.setattr(checkpoint_evaluation, "AbliterationPipeline", FailedPipeline)
    monkeypatch.setattr(checkpoint_evaluation, "_partition_pairs", lambda _part: (("h", "s"),))

    with pytest.raises(RuntimeError, match="summon failed"):
        checkpoint_evaluation.evaluate(run_id, "final_test", str(tmp_path))

    assert isinstance(archive.finishes[0][2]["failure"], RuntimeError)
    assert lifecycle.events[-1] == ("release", "evaluation_final_test_complete")


def test_main_delegates_parsed_evaluation_arguments(monkeypatch):
    import obliteratus.checkpoint_evaluation as checkpoint_evaluation

    observed = []
    monkeypatch.setattr(
        "sys.argv",
        [
            "checkpoint-evaluation",
            "--archive-root",
            "/archive",
            "--run-id",
            "run-" + "d" * 32,
            "--partition",
            "final_test",
        ],
    )
    monkeypatch.setattr(
        checkpoint_evaluation,
        "evaluate",
        lambda *args: observed.append(args) or 2,
    )

    assert checkpoint_evaluation.main() == 2
    assert observed == [("run-" + "d" * 32, "final_test", "/archive")]
