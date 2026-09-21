"""Local, credential-free GPU lifecycle publication for host supervisors."""

from __future__ import annotations

import atexit
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import threading
import time
import uuid
from typing import Callable


SCHEMA_VERSION = 1
logger = logging.getLogger(__name__)


class AdmissionError(RuntimeError):
    """The local supervisor did not grant correlated GPU admission."""

    def __init__(
        self,
        message: str,
        *,
        reason: str = "admission_failed",
        run_id: str | None = None,
        request_event_id: str | None = None,
        elapsed_seconds: float | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.run_id = run_id
        self.request_event_id = request_event_id
        self.elapsed_seconds = elapsed_seconds
        self.timeout_seconds = timeout_seconds

    def diagnostic_message(self) -> str:
        """Return operator-safe correlated details without lease credentials."""
        fields = [f"reason={self.reason}"]
        if self.run_id:
            fields.append(f"run_id={self.run_id}")
        if self.request_event_id:
            fields.append(f"request_event_id={self.request_event_id}")
        if self.elapsed_seconds is not None:
            fields.append(f"elapsed={self.elapsed_seconds:.1f}s")
        if self.timeout_seconds is not None:
            fields.append(f"deadline={self.timeout_seconds:.1f}s")
        return ", ".join(fields)

    def user_message(self) -> str:
        """Return an actionable UI message for a safe admission failure."""
        if self.reason == "ack_timeout":
            return (
                "GPU admission timed out before the host supervisor responded. "
                "No model weights were loaded or modified. The GPU broker may still "
                "be draining another workload; retry after it becomes available."
            )
        if self.reason.startswith("broker_admission_"):
            return (
                "The host GPU supervisor denied this run because it could not reserve "
                "the requested GPU capacity. No model weights were loaded or modified."
            )
        return f"GPU admission failed: {self}"


@dataclass(frozen=True)
class MemoryUsage:
    """Process-visible accelerator memory in bytes."""

    allocated_bytes: int = 0
    reserved_bytes: int = 0
    device_count: int = 0


class GpuLifecyclePublisher:
    """Publish ordered lifecycle events into an operator-owned runtime directory."""

    def __init__(
        self,
        runtime_dir: str | Path | None,
        *,
        heartbeat_seconds: float = 15.0,
        admission_timeout_seconds: float = 30.0,
        admission_poll_seconds: float = 0.05,
        clock: Callable[[], datetime] | None = None,
        run_id: str | None = None,
    ) -> None:
        configured_dir = Path(runtime_dir) if runtime_dir else None
        if configured_dir is not None and configured_dir.is_symlink():
            raise ValueError("GPU lifecycle runtime directory must not be a symlink")
        self._dir = configured_dir.resolve() if configured_dir else None
        self._heartbeat_seconds = max(1.0, float(heartbeat_seconds))
        self._admission_timeout_seconds = max(0.01, float(admission_timeout_seconds))
        self._admission_poll_seconds = max(0.001, float(admission_poll_seconds))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._run_id = run_id or str(uuid.uuid4())
        self._lock = threading.RLock()
        self._sequence = 0
        self._model_id: str | None = None
        self._phase = "released"
        self._last_memory = MemoryUsage()
        self._lease_id: str | None = None
        self._granted_vram_bytes = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if self._dir is not None:
            if not self._dir.is_dir():
                raise ValueError("GPU lifecycle runtime directory must already exist")
        atexit.register(self.release, reason="process_exit")

    @property
    def enabled(self) -> bool:
        return self._dir is not None

    def loading(self, model_id: str) -> dict | None:
        with self._lock:
            self._model_id = str(model_id)
            self._phase = "intent_published"
            request = self._publish("loading")
            if request is None:
                return None
            self._wait_for_admission(request)
            self._phase = "admission_granted"
            self._publish("admission_granted")
            self._phase = "allocation_started"
            event = self._publish("allocation_started")
            self._start_heartbeat()
            return event

    def resize(self, memory: MemoryUsage) -> dict | None:
        with self._lock:
            if self.enabled and memory.reserved_bytes > self._granted_vram_bytes:
                self._phase = "admission_lost"
                self._publish("admission_lost", reason="reservation_exceeded")
                raise AdmissionError("measured VRAM exceeds the supervisor grant")
            self._last_memory = memory
            return self._publish("resize")

    def ready(self, memory: MemoryUsage | None = None) -> dict | None:
        with self._lock:
            if memory is not None:
                self._last_memory = memory
            self._phase = "ready"
            event = self._publish("ready")
            self._start_heartbeat()
            return event

    def heartbeat(self) -> dict | None:
        with self._lock:
            if self._phase in {"released", "intent_published"}:
                return None
            return self._publish("heartbeat")

    def release(self, *, reason: str = "unload") -> dict | None:
        with self._lock:
            if self._phase == "released":
                return None
            self._phase = "released"
            self._stop.set()
            event = self._publish("release", reason=reason)
            self._model_id = None
            self._last_memory = MemoryUsage()
            self._lease_id = None
            self._granted_vram_bytes = 0
            return event

    def _wait_for_admission(self, request: dict) -> None:
        acknowledgement = self._dir / "ack.json"  # type: ignore[operator]
        deadline = threading.Event()
        remaining = self._admission_timeout_seconds
        started_at = time.monotonic()
        logger.info(
            "GPU admission requested run_id=%s request_event_id=%s timeout=%.1fs",
            self._run_id,
            request["event_id"],
            self._admission_timeout_seconds,
        )
        while remaining > 0:
            started = datetime.now(timezone.utc)
            try:
                payload = json.loads(acknowledgement.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, json.JSONDecodeError):
                payload = None
            if self._valid_ack(payload, request):
                if payload["decision"] == "deny":
                    reason = str(payload.get("reason", "denied"))
                    self._phase = "admission_denied"
                    self._publish("admission_denied", reason=reason)
                    elapsed = time.monotonic() - started_at
                    logger.warning(
                        "GPU admission denied run_id=%s request_event_id=%s "
                        "reason=%s elapsed=%.1fs",
                        self._run_id,
                        request["event_id"],
                        reason,
                        elapsed,
                    )
                    raise AdmissionError(
                        "GPU admission denied by local supervisor",
                        reason=reason,
                        run_id=self._run_id,
                        request_event_id=request["event_id"],
                        elapsed_seconds=elapsed,
                        timeout_seconds=self._admission_timeout_seconds,
                    )
                lease_id = payload.get("lease_id")
                granted = payload.get("granted_vram_bytes")
                if not isinstance(lease_id, str) or not lease_id:
                    raise AdmissionError(
                        "GPU admission ACK has no lease identity",
                        reason="invalid_lease_identity",
                        run_id=self._run_id,
                        request_event_id=request["event_id"],
                        elapsed_seconds=time.monotonic() - started_at,
                        timeout_seconds=self._admission_timeout_seconds,
                    )
                if self._lease_id is not None and lease_id != self._lease_id:
                    raise AdmissionError(
                        "GPU admission ownership changed",
                        reason="lease_ownership_changed",
                        run_id=self._run_id,
                        request_event_id=request["event_id"],
                        elapsed_seconds=time.monotonic() - started_at,
                        timeout_seconds=self._admission_timeout_seconds,
                    )
                if isinstance(granted, bool) or not isinstance(granted, int) or granted < 0:
                    raise AdmissionError(
                        "GPU admission ACK has an invalid VRAM grant",
                        reason="invalid_vram_grant",
                        run_id=self._run_id,
                        request_event_id=request["event_id"],
                        elapsed_seconds=time.monotonic() - started_at,
                        timeout_seconds=self._admission_timeout_seconds,
                    )
                self._lease_id = lease_id
                self._granted_vram_bytes = granted
                logger.info(
                    "GPU admission granted run_id=%s request_event_id=%s "
                    "elapsed=%.1fs granted_vram_bytes=%d",
                    self._run_id,
                    request["event_id"],
                    time.monotonic() - started_at,
                    granted,
                )
                return
            waited = (datetime.now(timezone.utc) - started).total_seconds()
            pause = min(self._admission_poll_seconds, remaining)
            deadline.wait(pause)
            remaining -= max(pause, waited)
        self._phase = "admission_denied"
        self._publish("admission_denied", reason="ack_timeout")
        elapsed = time.monotonic() - started_at
        error = AdmissionError(
            "timed out waiting for GPU admission ACK",
            reason="ack_timeout",
            run_id=self._run_id,
            request_event_id=request["event_id"],
            elapsed_seconds=elapsed,
            timeout_seconds=self._admission_timeout_seconds,
        )
        logger.error("GPU admission timeout %s", error.diagnostic_message())
        raise error

    def _valid_ack(self, payload: object, request: dict) -> bool:
        return bool(
            isinstance(payload, dict)
            and payload.get("schema_version") == SCHEMA_VERSION
            and payload.get("run_id") == self._run_id
            and payload.get("request_event_id") == request["event_id"]
            and payload.get("decision") in {"grant", "deny"}
        )

    def _start_heartbeat(self) -> None:
        if not self.enabled or (self._thread is not None and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name="obliteratus-gpu-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self._heartbeat_seconds):
            self.heartbeat()

    def _publish(self, event: str, *, reason: str | None = None) -> dict | None:
        if not self.enabled:
            return None
        self._sequence += 1
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_id": f"{self._run_id}:{self._sequence}",
            "sequence": self._sequence,
            "event": event,
            "phase": self._phase,
            "run_id": self._run_id,
            "model_id": self._model_id,
            "pid": os.getpid(),
            "timestamp": self._clock().isoformat(),
            "allocated_vram_bytes": self._last_memory.allocated_bytes,
            "reserved_vram_bytes": self._last_memory.reserved_bytes,
            "device_count": self._last_memory.device_count,
        }
        if reason is not None:
            payload["reason"] = reason
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        events = self._dir / "events.jsonl"  # type: ignore[operator]
        current = self._dir / "current.json"  # type: ignore[operator]
        temporary = self._dir / f".current.{os.getpid()}.tmp"  # type: ignore[operator]
        with events.open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
            stream.flush()
        temporary.write_text(encoded + "\n", encoding="utf-8")
        os.replace(temporary, current)
        return payload


def from_environment() -> GpuLifecyclePublisher:
    """Build the process publisher; an unset directory yields a no-op publisher."""
    interval = os.environ.get("OBLITERATUS_GPU_HEARTBEAT_SECONDS", "15")
    timeout = os.environ.get("OBLITERATUS_GPU_ADMISSION_TIMEOUT_SECONDS", "30")
    try:
        heartbeat_seconds = float(interval)
    except ValueError:
        heartbeat_seconds = 15.0
    try:
        admission_timeout_seconds = float(timeout)
    except ValueError:
        admission_timeout_seconds = 30.0
    return GpuLifecyclePublisher(
        os.environ.get("OBLITERATUS_GPU_LIFECYCLE_DIR"),
        heartbeat_seconds=heartbeat_seconds,
        admission_timeout_seconds=admission_timeout_seconds,
        run_id=os.environ.get("OBLITERATUS_RUN_ID"),
    )


def measure_torch_memory(torch_module) -> MemoryUsage:
    """Measure this process' CUDA allocator without initializing CUDA on CPU hosts."""
    cuda = getattr(torch_module, "cuda", None)
    if cuda is None or not cuda.is_available():
        return MemoryUsage()
    count = cuda.device_count()
    return MemoryUsage(
        allocated_bytes=sum(int(cuda.memory_allocated(index)) for index in range(count)),
        reserved_bytes=sum(int(cuda.memory_reserved(index)) for index in range(count)),
        device_count=count,
    )
