"""HTML rendering for accelerator-memory status."""

from __future__ import annotations

from typing import Any


VRAM_REFRESH_CHOICES = (("10 sec", 10.0), ("30 sec", 30.0), ("1 min", 60.0))
DEFAULT_VRAM_REFRESH_INTERVAL = 30.0


def resolve_vram_refresh_interval(value: float) -> float:
    """Return a supported VRAM polling interval, falling back to the default."""
    allowed = {interval for _label, interval in VRAM_REFRESH_CHOICES}
    return value if value in allowed else DEFAULT_VRAM_REFRESH_INTERVAL


def render_vram_html(device: Any) -> str:
    """Return per-device GPU/accelerator memory usage as styled bars."""
    try:
        if not device.is_gpu_available():
            return (
                '<div style="text-align:center;color:#4a5568;font-size:0.72rem;'
                'letter-spacing:1px;margin-top:6px;">CPU ONLY — NO GPU DETECTED</div>'
            )
        cuda_count = device.device_count() if device.is_cuda() else 0
        device_indices = range(cuda_count) if cuda_count else (None,)
        rows = []
        for device_index in device_indices:
            query_index = 0 if device_index is None else device_index
            device_key = "single" if device_index is None else device_index
            mem = device.get_memory_info(query_index)
            used = mem.used_gb
            total = mem.total_gb
            pct = (used / total * 100) if total > 0 else 0
            if pct < 50:
                bar_color = "#00ff41"
            elif pct < 80:
                bar_color = "#ffcc00"
            else:
                bar_color = "#ff003c"
            device_name = (
                f"GPU {device_index} · {mem.device_name}"
                if device_index is not None
                else mem.device_name
            )
            reserved_html = (
                f'<span style="color:#4a5568;">reserved: {mem.reserved_gb:.1f} GB</span>'
                if mem.reserved_gb > 0
                else '<span style="color:#4a5568;">unified memory</span>'
            )
            rows.append(
                f'<div data-device-index="{device_key}" '
                f'style="margin:6px auto 0;max-width:480px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:0.68rem;'
                f'color:#4a5568;letter-spacing:1px;margin-bottom:2px;">'
                f'<span>{device_name}</span>'
                f'<span>{used:.1f} / {total:.1f} GB ({pct:.0f}%)</span></div>'
                f'<div style="background:#0a0a0f;border:1px solid #1a1f2e;border-radius:3px;'
                f'height:10px;overflow:hidden;">'
                f'<div style="width:{min(pct, 100):.1f}%;height:100%;background:{bar_color};'
                f'box-shadow:0 0 6px {bar_color};transition:width 0.5s ease;"></div></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:0.6rem;'
                f'color:#333;margin-top:1px;">'
                f'{reserved_html}</div>'
                f'</div>'
            )
        if cuda_count > 1:
            rows.append(
                '<div style="text-align:center;color:#4a5568;font-size:0.6rem;'
                'margin-top:4px;">Automatic sharding uses additional GPUs as model size '
                'requires; smaller models may remain on GPU 0.</div>'
            )
        return "".join(rows)
    except Exception:
        return '<div style="text-align:center;color:#4a5568;font-size:0.72rem;">Memory: unavailable</div>'
