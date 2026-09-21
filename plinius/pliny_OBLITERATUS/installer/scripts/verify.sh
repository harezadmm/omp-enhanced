#!/usr/bin/env bash
set -euo pipefail
set +x

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

.venv/bin/python - <<'PY'
import os
import shutil
import torch

from obliteratus.credential_sources import secret_available

assert torch.ones(1).add(1).item() == 2
if shutil.which("nvidia-smi"):
    assert torch.cuda.is_available(), "NVIDIA GPU detected but CUDA is unavailable"
    assert torch.ones(1, device="cuda").device.type == "cuda"
    torch.backends.cudnn.enabled = False
    torch.backends.cuda.enable_cudnn_sdp(False)
    conv_input = torch.randn(1, 8, 32, device="cuda", dtype=torch.float16)
    conv_weight = torch.randn(8, 8, 3, device="cuda", dtype=torch.float16)
    convolution = torch.nn.functional.conv1d(conv_input, conv_weight)
    q = torch.randn(1, 2, 32, 16, device="cuda", dtype=torch.float16)
    attention = torch.nn.functional.scaled_dot_product_attention(q, q, q, is_causal=True)
    torch.cuda.synchronize()
    assert convolution.device.type == "cuda" and torch.isfinite(convolution).all()
    assert attention.device.type == "cuda" and torch.isfinite(attention).all()

broker = os.environ.get("OBLITERATUS_SECRET_COMMAND")
if broker:
    assert os.path.isabs(broker)
    assert secret_available("HF_TOKEN")
    assert secret_available("OPENROUTER_API_KEY")
PY

.venv/bin/pytest -q --no-cov tests/test_device_boundaries.py tests/test_secrets.py \
  tests/test_abliterate.py::TestCoherenceScoring
