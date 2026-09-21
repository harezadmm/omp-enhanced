"""GPU admission and cleanup contracts for application benchmark paths."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from obliteratus.benchmark_lifecycle import (
    MAX_RELEASABLE_ALLOCATOR_RESIDUE_BYTES,
    admit_benchmark,
    mark_benchmark_ready,
    release_benchmark_pipeline,
)
from obliteratus.gpu_lifecycle import MemoryUsage


class _LifecycleRecorder:
    def __init__(self, *, loading_error=None):
        self.events = []
        self.loading_error = loading_error

    def loading(self, model_id):
        self.events.append(("loading", model_id))
        if self.loading_error:
            raise self.loading_error

    def resize(self, memory):
        self.events.append(("resize", memory))

    def ready(self, memory):
        self.events.append(("ready", memory))

    def release(self, *, reason):
        self.events.append(("release", reason))


def test_benchmark_entrypoints_use_lifecycle_helpers_before_worker_start():
    source = Path("app.py").read_text(encoding="utf-8")
    for marker in ("def benchmark(", "def benchmark_multi_model("):
        body = source[source.index(marker) :]
        assert body.index("admit_benchmark(_gpu_lifecycle, model_id)") < body.index(
            "worker.start()"
        )
        assert "mark_benchmark_ready(_gpu_lifecycle, torch)" in body
        assert "release_benchmark_pipeline(" in body


def test_admission_success_allows_worker_start():
    lifecycle = _LifecycleRecorder()
    assert admit_benchmark(lifecycle, "org/model") is None
    assert lifecycle.events == [("loading", "org/model")]


def test_admission_failure_releases_and_returns_error():
    error = RuntimeError("denied")
    lifecycle = _LifecycleRecorder(loading_error=error)
    assert admit_benchmark(lifecycle, "org/model") is error
    assert lifecycle.events == [
        ("loading", "org/model"),
        ("release", "benchmark_admission_failed"),
    ]


def test_ready_publishes_measured_memory(monkeypatch):
    memory = MemoryUsage(allocated_bytes=3, reserved_bytes=4, device_count=1)
    monkeypatch.setattr(
        "obliteratus.benchmark_lifecycle.measure_torch_memory", lambda _torch: memory
    )
    lifecycle = _LifecycleRecorder()
    mark_benchmark_ready(lifecycle, object())
    assert lifecycle.events == [("resize", memory), ("ready", memory)]


def test_cleanup_releases_only_after_cuda_is_gone(monkeypatch):
    lifecycle = _LifecycleRecorder()
    monkeypatch.setattr(
        "obliteratus.benchmark_lifecycle.measure_torch_memory",
        lambda _torch: MemoryUsage(),
    )
    calls = []
    torch_module = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            synchronize=lambda: calls.append("synchronize"),
        )
    )
    device_module = SimpleNamespace(empty_cache=lambda: calls.append("empty_cache"))
    handle = SimpleNamespace(model=object(), tokenizer=object())

    release_benchmark_pipeline(
        [SimpleNamespace(handle=handle)],
        reason="benchmark_complete",
        lifecycle=lifecycle,
        torch_module=torch_module,
        device_module=device_module,
    )

    assert handle.model is None and handle.tokenizer is None
    assert calls == ["synchronize", "empty_cache"]
    assert lifecycle.events == [("release", "benchmark_complete")]


def test_cleanup_releases_with_bounded_cuda_context_residue(monkeypatch):
    lifecycle = _LifecycleRecorder()
    memory = MemoryUsage(
        allocated_bytes=25_559_040,
        reserved_bytes=62_914_560,
        device_count=3,
    )
    assert memory.reserved_bytes < MAX_RELEASABLE_ALLOCATOR_RESIDUE_BYTES
    monkeypatch.setattr(
        "obliteratus.benchmark_lifecycle.measure_torch_memory", lambda _torch: memory
    )

    release_benchmark_pipeline(
        [SimpleNamespace(handle=SimpleNamespace(model=object(), tokenizer=object()))],
        reason="benchmark_complete",
        lifecycle=lifecycle,
        torch_module=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
        device_module=SimpleNamespace(empty_cache=lambda: None),
    )

    assert lifecycle.events == [("release", "benchmark_complete")]


def test_cleanup_retains_lease_when_cuda_remains(monkeypatch):
    lifecycle = _LifecycleRecorder()
    memory = MemoryUsage(
        allocated_bytes=MAX_RELEASABLE_ALLOCATOR_RESIDUE_BYTES + 1,
        reserved_bytes=MAX_RELEASABLE_ALLOCATOR_RESIDUE_BYTES + 1,
        device_count=1,
    )
    monkeypatch.setattr(
        "obliteratus.benchmark_lifecycle.measure_torch_memory", lambda _torch: memory
    )
    torch_module = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    device_module = SimpleNamespace(empty_cache=lambda: None)

    with pytest.raises(RuntimeError, match="retaining GPU lease"):
        release_benchmark_pipeline(
            [SimpleNamespace(handle=SimpleNamespace(model=object(), tokenizer=object()))],
            reason="benchmark_complete",
            lifecycle=lifecycle,
            torch_module=torch_module,
            device_module=device_module,
        )

    assert lifecycle.events == [("resize", memory)]
