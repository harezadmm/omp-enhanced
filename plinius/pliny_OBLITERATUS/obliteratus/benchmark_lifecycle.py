"""GPU admission helpers shared by the UI benchmark entry points."""

from __future__ import annotations

import gc

from obliteratus.gpu_lifecycle import measure_torch_memory


# PyTorch keeps a small allocator/driver context alive in a long-running UI
# process after every model tensor has been freed.  The root supervisor remains
# authoritative and independently refuses release above 2 GiB of process VRAM.
MAX_RELEASABLE_ALLOCATOR_RESIDUE_BYTES = 128 * 1024 * 1024


def admit_benchmark(lifecycle, model_id: str) -> Exception | None:
    """Request admission before a benchmark worker may allocate CUDA memory."""
    try:
        lifecycle.loading(model_id)
    except Exception as error:
        lifecycle.release(reason="benchmark_admission_failed")
        return error
    return None


def mark_benchmark_ready(lifecycle, torch_module) -> None:
    """Publish measured residency after the pipeline finishes model loading."""
    memory = measure_torch_memory(torch_module)
    lifecycle.resize(memory)
    lifecycle.ready(memory)


def release_benchmark_pipeline(
    pipeline_ref,
    *,
    reason: str,
    lifecycle,
    torch_module,
    device_module,
) -> None:
    """Free a benchmark-local model before releasing supervisor ownership."""
    pipeline = pipeline_ref[0]
    if pipeline is not None and getattr(pipeline, "handle", None):
        pipeline.handle.model = None
        pipeline.handle.tokenizer = None
    gc.collect()
    if torch_module.cuda.is_available():
        torch_module.cuda.synchronize()
    device_module.empty_cache()
    memory = measure_torch_memory(torch_module)
    if (
        memory.allocated_bytes > MAX_RELEASABLE_ALLOCATOR_RESIDUE_BYTES
        or memory.reserved_bytes > MAX_RELEASABLE_ALLOCATOR_RESIDUE_BYTES
    ):
        lifecycle.resize(memory)
        raise RuntimeError(
            "benchmark CUDA allocations remain after cleanup; retaining GPU lease"
        )
    lifecycle.release(reason=reason)
