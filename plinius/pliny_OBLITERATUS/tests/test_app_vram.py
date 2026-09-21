"""Deterministic contracts for the accelerator-memory display."""

from __future__ import annotations

from types import SimpleNamespace

from obliteratus.ui_vram import (
    DEFAULT_VRAM_REFRESH_INTERVAL,
    VRAM_REFRESH_CHOICES,
    render_vram_html,
    resolve_vram_refresh_interval,
)


def _memory(used, reserved, total, name):
    return SimpleNamespace(
        used_gb=used,
        reserved_gb=reserved,
        total_gb=total,
        device_name=name,
    )


def test_vram_html_covers_cpu_single_and_multi_accelerator_topologies():
    device = SimpleNamespace(is_gpu_available=lambda: False)
    html = render_vram_html(device)
    assert "CPU ONLY — NO GPU DETECTED" in html
    assert "data-device-index" not in html

    device = SimpleNamespace(
        is_gpu_available=lambda: True,
        is_cuda=lambda: False,
        get_memory_info=lambda _index=0: _memory(4, 0, 16, "Apple M3 (MPS)"),
    )
    html = render_vram_html(device)
    assert html.count("data-device-index=") == 1
    assert 'data-device-index="single"' in html
    assert "Apple M3 (MPS)" in html
    assert "4.0 / 16.0 GB (25%)" in html
    assert "Automatic sharding" not in html

    memories = [
        _memory(4, 5, 80, "NVIDIA A100"),
        _memory(16, 20, 80, "NVIDIA A100"),
        _memory(72, 74, 80, "NVIDIA A100"),
    ]
    queried = []

    def memory_info(index):
        queried.append(index)
        return memories[index]

    device = SimpleNamespace(
        is_gpu_available=lambda: True,
        is_cuda=lambda: True,
        device_count=lambda: len(memories),
        get_memory_info=memory_info,
    )
    html = render_vram_html(device)
    assert queried == [0, 1, 2]
    assert html.count("data-device-index=") == 3
    assert "GPU 0 · NVIDIA A100" in html
    assert "GPU 1 · NVIDIA A100" in html
    assert "GPU 2 · NVIDIA A100" in html
    assert "Automatic sharding uses additional GPUs" in html

    memories = [
        _memory(2, 3, 24, "NVIDIA RTX 4090"),
        _memory(8, 9, 80, "NVIDIA A100"),
    ]
    device.device_count = lambda: len(memories)
    device.get_memory_info = memories.__getitem__
    html = render_vram_html(device)
    assert "GPU 0 · NVIDIA RTX 4090" in html
    assert "GPU 1 · NVIDIA A100" in html
    assert html.index("GPU 0 · NVIDIA RTX 4090") < html.index("GPU 1 · NVIDIA A100")


def test_vram_html_handles_memory_errors():
    device = SimpleNamespace(
        is_gpu_available=lambda: True,
        is_cuda=lambda: True,
        device_count=lambda: 1,
        get_memory_info=lambda _index: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    assert "Memory: unavailable" in render_vram_html(device)

    device.is_gpu_available = lambda: (_ for _ in ()).throw(RuntimeError("unavailable"))
    assert "Memory: unavailable" in render_vram_html(device)


def test_vram_refresh_interval_contract():
    assert VRAM_REFRESH_CHOICES == (
        ("10 sec", 10.0),
        ("30 sec", 30.0),
        ("1 min", 60.0),
    )
    assert DEFAULT_VRAM_REFRESH_INTERVAL == 30.0
    assert resolve_vram_refresh_interval(10.0) == 10.0
    assert resolve_vram_refresh_interval(30.0) == 30.0
    assert resolve_vram_refresh_interval(60.0) == 60.0
    assert resolve_vram_refresh_interval(15.0) == 30.0
