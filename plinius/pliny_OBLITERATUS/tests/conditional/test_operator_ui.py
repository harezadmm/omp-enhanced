"""Construct the optional Gradio UI without opening a listener."""

from __future__ import annotations

import subprocess
import sys

import pytest


pytestmark = pytest.mark.operator_ui


def test_gradio_application_constructs_without_public_listener():
    pytest.importorskip("gradio", reason="install the locked spaces extra")
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app, gradio; "
            "assert type(app.demo).__name__ == 'Blocks'; "
            "assert app.demo.local_url is None; "
            "assert int(gradio.__version__.split('.')[0]) >= 6; "
            "print('operator UI constructed without a listener')",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.strip() == "operator UI constructed without a listener"
    assert probe.stderr == ""


def test_gpu_memory_refresh_controls_have_one_configurable_polling_loop():
    """Exercise the rendered Gradio graph rather than relying on source shape."""
    pytest.importorskip("gradio", reason="install the locked spaces extra")
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            r'''
import asyncio
import app

config = app.demo.get_config_file()
components = config["components"]
timers = [item for item in components if item["type"] == "timer"]
assert len(timers) == 1
timer = timers[0]
assert timer["props"]["value"] == 30.0
assert timer["props"]["active"] is True

selectors = [
    item for item in components
    if "vram-refresh-control" in item["props"].get("elem_classes", [])
]
assert len(selectors) == 1
selector = selectors[0]
assert selector["type"] == "dropdown"
assert selector["props"]["label"] == "GPU refresh"
assert selector["props"]["choices"] == [
    ("10 sec", 10.0), ("30 sec", 30.0), ("1 min", 60.0)
]
assert selector["props"]["value"] == 30.0
assert selector["props"]["filterable"] is False
assert selector["props"]["allow_custom_value"] is False
assert selector["props"]["min_width"] == 96

timer_ticks = [
    dependency for dependency in config["dependencies"]
    if (timer["id"], "tick") in dependency["targets"]
]
assert len(timer_ticks) == 1
assert timer_ticks[0]["queue"] is False
assert timer_ticks[0]["outputs"] == [app.vram_display._id]

interval_changes = [
    dependency for dependency in config["dependencies"]
    if (selector["id"], "change") in dependency["targets"]
    and dependency["outputs"] == [timer["id"]]
]
assert len(interval_changes) == 1
assert interval_changes[0]["queue"] is False

async def verify_interval_changes():
    for seconds in (10.0, 30.0, 60.0):
        result = await app.demo.process_api(
            interval_changes[0]["id"], [seconds], state=None
        )
        assert result["data"] == [seconds]

asyncio.run(verify_interval_changes())
''',
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
