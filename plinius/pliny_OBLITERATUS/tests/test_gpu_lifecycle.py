from __future__ import annotations

from datetime import datetime, timezone
import json
import threading
import time

import pytest

from obliteratus.gpu_lifecycle import (
    AdmissionError,
    GpuLifecyclePublisher,
    MemoryUsage,
    measure_torch_memory,
)


def test_fake_supervisor_observes_order_identity_and_recoverable_state(tmp_path):
    publisher = GpuLifecyclePublisher(
        tmp_path,
        heartbeat_seconds=0.01,
        clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc),
        run_id="run-1",
    )
    def acknowledge():
        while not (tmp_path / "current.json").exists():
            time.sleep(0.001)
        request = json.loads((tmp_path / "current.json").read_text())
        (tmp_path / "ack.json").write_text(json.dumps({
            "schema_version": 1,
            "run_id": "run-1",
            "request_event_id": request["event_id"],
            "decision": "grant",
            "lease_id": "lease-1",
            "granted_vram_bytes": 100,
        }))
    threading.Thread(target=acknowledge).start()
    memory = MemoryUsage(allocated_bytes=10, reserved_bytes=12, device_count=1)
    publisher.loading("org/model")
    publisher.resize(memory)
    publisher.ready(memory)
    time.sleep(1.05)
    publisher.release(reason="test_complete")
    assert publisher.release(reason="duplicate") is None

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [event["event"] for event in events] == [
        "loading", "admission_granted", "allocation_started", "resize",
        "ready", "heartbeat", "release",
    ]
    assert [event["sequence"] for event in events] == list(range(1, 8))
    assert len({event["event_id"] for event in events}) == 7
    assert all(event["run_id"] == "run-1" for event in events)
    assert events[3]["reserved_vram_bytes"] == 12
    current = json.loads((tmp_path / "current.json").read_text())
    assert current["event"] == "release"
    assert current["reason"] == "test_complete"


def test_disabled_publisher_is_noop():
    publisher = GpuLifecyclePublisher(None)
    assert publisher.loading("model") is None
    assert publisher.resize(MemoryUsage()) is None
    assert publisher.ready() is None
    assert publisher.heartbeat() is None
    assert publisher.release() is None


def test_allocation_phase_can_heartbeat_before_ready(tmp_path):
    publisher = GpuLifecyclePublisher(tmp_path, run_id="loading-run")

    def acknowledge():
        while not (tmp_path / "current.json").exists():
            time.sleep(0.001)
        request = json.loads((tmp_path / "current.json").read_text())
        (tmp_path / "ack.json").write_text(json.dumps({
            "schema_version": 1,
            "run_id": "loading-run",
            "request_event_id": request["event_id"],
            "decision": "grant",
            "lease_id": "lease-loading",
            "granted_vram_bytes": 100,
        }))

    thread = threading.Thread(target=acknowledge)
    thread.start()
    publisher.loading("org/model")
    event = publisher.heartbeat()
    publisher.release(reason="test_complete")
    thread.join()

    assert event is not None
    assert event["event"] == "heartbeat"
    assert event["run_id"] == "loading-run"


def test_environment_uses_stable_experiment_run_id(tmp_path, monkeypatch):
    from obliteratus.gpu_lifecycle import from_environment

    monkeypatch.setenv("OBLITERATUS_GPU_LIFECYCLE_DIR", str(tmp_path))
    monkeypatch.setenv("OBLITERATUS_RUN_ID", "run-stable")
    publisher = from_environment()
    assert publisher._run_id == "run-stable"


def test_runtime_directory_must_exist(tmp_path):
    with pytest.raises(ValueError, match="must already exist"):
        GpuLifecyclePublisher(tmp_path / "missing")


def test_runtime_directory_rejects_symlink(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="must not be a symlink"):
        GpuLifecyclePublisher(link)


def test_measure_torch_memory_aggregates_devices():
    class FakeCuda:
        is_available = staticmethod(lambda: True)
        device_count = staticmethod(lambda: 2)
        memory_allocated = staticmethod(lambda index: (index + 1) * 10)
        memory_reserved = staticmethod(lambda index: (index + 1) * 20)

    usage = measure_torch_memory(type("Torch", (), {"cuda": FakeCuda})())
    assert usage == MemoryUsage(allocated_bytes=30, reserved_bytes=60, device_count=2)


@pytest.mark.parametrize("decision", ["deny", "timeout", "stale"])
def test_admission_failures_never_enter_allocation(tmp_path, decision):
    publisher = GpuLifecyclePublisher(
        tmp_path,
        admission_timeout_seconds=0.05,
        admission_poll_seconds=0.005,
        run_id="current-run",
    )
    allocation_entered = False

    def acknowledge():
        nonlocal allocation_entered
        while not (tmp_path / "current.json").exists():
            time.sleep(0.001)
        request = json.loads((tmp_path / "current.json").read_text())
        if decision != "timeout":
            (tmp_path / "ack.json").write_text(json.dumps({
                "schema_version": 1,
                "run_id": "stale-run" if decision == "stale" else "current-run",
                "request_event_id": request["event_id"],
                "decision": "deny" if decision == "deny" else "grant",
                "lease_id": "lease-1",
                "granted_vram_bytes": 100,
            }))

    worker = threading.Thread(target=acknowledge)
    worker.start()
    with pytest.raises(AdmissionError):
        publisher.loading("org/model")
        allocation_entered = True
    worker.join()
    assert allocation_entered is False
    events = [json.loads(line)["event"] for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert "allocation_started" not in events


def test_timeout_error_contains_safe_correlated_diagnostics(tmp_path):
    publisher = GpuLifecyclePublisher(
        tmp_path,
        admission_timeout_seconds=0.02,
        admission_poll_seconds=0.002,
        run_id="diagnostic-run",
    )

    with pytest.raises(AdmissionError) as captured:
        publisher.loading("org/model")

    error = captured.value
    assert error.reason == "ack_timeout"
    assert error.run_id == "diagnostic-run"
    assert error.request_event_id == "diagnostic-run:1"
    assert error.elapsed_seconds is not None
    assert error.timeout_seconds == 0.02
    assert "No model weights were loaded or modified" in error.user_message()
    assert "run_id=diagnostic-run" in error.diagnostic_message()
    assert "lease" not in error.diagnostic_message()


def test_supervisor_denial_reason_is_preserved(tmp_path):
    publisher = GpuLifecyclePublisher(
        tmp_path,
        admission_timeout_seconds=0.2,
        admission_poll_seconds=0.002,
        run_id="denied-run",
    )

    def deny():
        while not (tmp_path / "current.json").exists():
            time.sleep(0.001)
        request = json.loads((tmp_path / "current.json").read_text())
        (tmp_path / "ack.json").write_text(json.dumps({
            "schema_version": 1,
            "run_id": "denied-run",
            "request_event_id": request["event_id"],
            "decision": "deny",
            "reason": "broker_admission_failed",
        }))

    threading.Thread(target=deny).start()
    with pytest.raises(AdmissionError) as captured:
        publisher.loading("org/model")

    assert captured.value.reason == "broker_admission_failed"
    assert "could not reserve" in captured.value.user_message()


def test_delayed_ack_blocks_until_granted(tmp_path):
    publisher = GpuLifecyclePublisher(
        tmp_path, admission_timeout_seconds=1, admission_poll_seconds=0.005, run_id="run",
    )
    entered = threading.Event()

    def load():
        publisher.loading("model")
        entered.set()

    worker = threading.Thread(target=load)
    worker.start()
    time.sleep(0.03)
    assert not entered.is_set()
    request = json.loads((tmp_path / "current.json").read_text())
    (tmp_path / "ack.json").write_text(json.dumps({
        "schema_version": 1, "run_id": "run", "request_event_id": request["event_id"],
        "decision": "grant", "lease_id": "lease", "granted_vram_bytes": 1,
    }))
    worker.join(timeout=1)
    assert entered.is_set()


def test_grant_ceiling_and_lease_identity_fail_closed(tmp_path):
    publisher = GpuLifecyclePublisher(
        tmp_path, admission_timeout_seconds=0.2, admission_poll_seconds=0.002, run_id="run",
    )

    def grant(request_id, lease_id="lease-a", granted=20):
        (tmp_path / "ack.json").write_text(json.dumps({
            "schema_version": 1, "run_id": "run", "request_event_id": request_id,
            "decision": "grant", "lease_id": lease_id, "granted_vram_bytes": granted,
        }))

    def acknowledge_first():
        while not (tmp_path / "current.json").exists():
            time.sleep(0.001)
        grant(json.loads((tmp_path / "current.json").read_text())["event_id"])

    threading.Thread(target=acknowledge_first).start()
    publisher.loading("first")
    with pytest.raises(AdmissionError, match="exceeds"):
        publisher.resize(MemoryUsage(reserved_bytes=21))

    def acknowledge_changed_owner():
        seen = None
        while seen != "loading":
            current = json.loads((tmp_path / "current.json").read_text())
            seen = current["event"]
            time.sleep(0.001)
        grant(current["event_id"], lease_id="lease-b")

    threading.Thread(target=acknowledge_changed_owner).start()
    with pytest.raises(AdmissionError, match="ownership changed"):
        publisher.loading("second")
