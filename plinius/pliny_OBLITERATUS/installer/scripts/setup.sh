#!/usr/bin/env bash
set -euo pipefail
set +x

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

uv sync --locked --extra spaces --extra dev --no-editable

enable_cuda="${ENABLE_CUDA:-auto}"
if [[ "$enable_cuda" != "false" ]] && command -v nvidia-smi >/dev/null 2>&1; then
  torch_version="$(.venv/bin/python -c 'import torch; print(torch.__version__.split("+", 1)[0])')"
  UV_TORCH_BACKEND=cu130 uv pip install \
    --python .venv/bin/python \
    --reinstall-package torch \
    "torch==$torch_version"
fi

uv pip check --python .venv/bin/python
.venv/bin/python - <<'PY'
import shutil
import torch

if torch.cuda.is_available():
    probe = torch.arange(16, device="cuda", dtype=torch.float32).square().sum()
    assert probe.device.type == "cuda"
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
elif shutil.which("nvidia-smi"):
    raise SystemExit("NVIDIA hardware detected but the installed PyTorch runtime cannot use CUDA")
PY
