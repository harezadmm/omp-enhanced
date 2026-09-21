"""Regression test for unload, cleanup, and lazy chat model lifecycle."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.operator_ui
def test_active_checkpoint_survives_cleanup_and_remains_chat_recoverable(tmp_path):
    """Exercise app state in isolation from Gradio's import-time worker sockets."""
    script = r'''
import pathlib
import os
import sys

import app

assert app._pipeline_timeout_seconds() == 2700
os.environ["OBLITERATUS_PIPELINE_TIMEOUT_SECONDS"] = "7200"
assert app._pipeline_timeout_seconds() == 7200
os.environ["OBLITERATUS_PIPELINE_TIMEOUT_SECONDS"] = "invalid"
try:
    app._pipeline_timeout_seconds()
except ValueError as error:
    assert "must be an integer" in str(error)
else:
    raise AssertionError("invalid pipeline timeout was accepted")
os.environ.pop("OBLITERATUS_PIPELINE_TIMEOUT_SECONDS")

theme = app.THEME.to_dict()["theme"]
assert theme["body_background_fill"] != theme["body_background_fill_dark"]
assert theme["body_text_color"] != theme["body_text_color_dark"]
assert theme["background_fill_secondary"] == "#ffffff"
assert theme["background_fill_secondary_dark"] == "#0d0d14"
assert ".chatbot .message.bot" in app.CSS
assert "color: var(--body-text-color) !important" in app.CSS

root = pathlib.Path(sys.argv[1])
active = root / "obliterated_1"
stale = root / "obliterated_2"
cache = root / "model-cache"
for directory in (active, stale, cache):
    directory.mkdir()
    (directory / "weights.bin").write_bytes(b"model")

app.dev.free_gpu_memory = lambda: None
app._state.update({
    "model": object(), "tokenizer": object(), "model_name": "org/model",
    "method": "advanced", "status": "ready", "output_dir": str(active),
})
app._session_models.clear()
app._session_models.update({
    "active": {"output_dir": str(active)},
    "stale": {"output_dir": str(stale)},
})

message = app._cleanup_disk(cache_roots=[cache], temp_root=root)
assert active.is_dir()
assert not stale.exists()
assert not cache.exists()
assert list(app._session_models) == ["active"]
assert app._state["model"] is None and app._state["tokenizer"] is None
assert app._state["status"] == "ready"
assert "will reload it automatically" in message
header = app.get_chat_header()
assert "unloaded from GPU" in header and "load automatically" in header

active.rename(root / "removed")
header = app.get_chat_header()
assert header.startswith("No model loaded")
assert app._state["status"] == "idle"
assert app._state["model_name"] is None
assert app._state["output_dir"] is None
'''

    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.operator_ui
def test_pipeline_cancellation_and_local_checkpoint_reload_contracts(tmp_path):
    """Cover timeout grace outcomes and local-only reload classification."""
    script = r'''
import pathlib
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import app
from obliteratus.models import loader

root = pathlib.Path(sys.argv[1])
checkpoint = root / "completed"
checkpoint.mkdir()
(checkpoint / "abliteration_metadata.json").write_text("{}", encoding="utf-8")
(checkpoint / "config.json").write_text("{}", encoding="utf-8")
(checkpoint / "tokenizer_config.json").write_text("{}", encoding="utf-8")
(checkpoint / "model.safetensors").write_bytes(b"weights")
assert app._resolve_local_checkpoint(checkpoint) == checkpoint.resolve()

calls = []
model = Mock()
model.to.return_value = model
tokenizer = Mock(pad_token=None, eos_token="<eos>")
app.AutoModelForCausalLM.from_pretrained = Mock(
    side_effect=lambda source, **kwargs: (calls.append((source, kwargs)), model)[1]
)
app.AutoTokenizer.from_pretrained = Mock(return_value=tokenizer)
app.AutoConfig.from_pretrained = Mock(
    return_value=SimpleNamespace(model_type="gpt2"),
)
app.dev.supports_device_map_auto = lambda: True
app._load_model_to_device(checkpoint, local_files_only=True)
assert calls[0][0] == checkpoint
assert calls[0][1]["local_files_only"] is True

app.AutoConfig.from_pretrained.return_value = SimpleNamespace(
    model_type="qwen3_5_text",
)
loader._require_qwen_hybrid_kernels = Mock()
loader._estimate_model_memory_gb = Mock(return_value=54.0)
loader._qwen_single_device = Mock(return_value=2)
app._load_model_to_device(checkpoint, local_files_only=True)
assert calls[-1][1]["attn_implementation"] == "sdpa"
assert calls[-1][1]["device_map"] == {"": 2}
assert calls[-1][1]["device_map"] != "auto"
app.AutoConfig.from_pretrained.return_value = SimpleNamespace(model_type="gpt2")

quantization = object()
loaded_model, loaded_tokenizer = app._reload_local_checkpoint(
    checkpoint,
    trust_remote_code=True,
    model_kwargs={"quantization_config": quantization},
)
assert loaded_model is model and loaded_tokenizer is tokenizer
assert calls[-1][1]["quantization_config"] is quantization
assert calls[-1][1]["local_files_only"] is True
assert tokenizer.pad_token == "<eos>"

app._reload_local_checkpoint(
    checkpoint,
    trust_remote_code=True,
    model_kwargs={"offload_folder": str(root / "offload")},
)
assert calls[-1][1]["offload_folder"] == str(root / "offload")
assert calls[-1][1]["local_files_only"] is True

assert app._format_checkpoint_reload_error(FileNotFoundError("gone")).startswith(
    "Saved checkpoint is missing"
)
assert app._format_checkpoint_reload_error(ValueError("Checkpoint has no model weights")).startswith(
    "Saved checkpoint is incomplete"
)
assert app._format_checkpoint_reload_error(ValueError("Checkpoint metadata is corrupt")).startswith(
    "Saved checkpoint is corrupt"
)
assert app._format_checkpoint_reload_error(ValueError("Repo id is invalid")).startswith(
    "Checkpoint Hub resolution failed"
)

def run_cooperative(cancel, delay):
    cancel.wait()
    time.sleep(delay)

cancel = threading.Event()
worker = threading.Thread(target=run_cooperative, args=(cancel, 0.02))
worker.start()
assert app._cancel_pipeline_worker(worker, cancel, grace_seconds=1.0) is True
assert cancel.is_set()

cancel = threading.Event()
release = threading.Event()
worker = threading.Thread(target=lambda: release.wait())
worker.start()
assert app._cancel_pipeline_worker(worker, cancel, grace_seconds=0.01) is False
assert cancel.is_set() and worker.is_alive()
release.set()
worker.join(timeout=1.0)
assert not worker.is_alive()
'''

    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
