"""Physical NVIDIA Jetson CUDA placement and operation probe."""

from __future__ import annotations

import platform
from pathlib import Path

import pytest
import torch
import torch.nn as nn
from accelerate.hooks import AlignDevicesHook, add_hook_to_module

from obliteratus import device
from obliteratus.abliterate import AbliterationPipeline


pytestmark = pytest.mark.gpu


def test_jetson_cuda_runtime_contract():
    assert platform.machine().lower() in {"aarch64", "arm64"}
    assert Path("/etc/nv_tegra_release").is_file()
    assert torch.version.cuda is not None
    assert torch.cuda.is_available()
    assert torch.cuda.device_count() > 0
    assert device.is_cuda()
    assert device.get_device("auto") == "cuda"
    tensor = torch.arange(16, device="cuda", dtype=torch.float32).reshape(4, 4)
    result = tensor @ tensor.T
    assert result.device.type == "cuda"
    assert torch.isfinite(result).all()


def test_jetson_cuda_offloaded_surgery_contract():
    module = nn.Module()
    module.proj = nn.Linear(4, 4, bias=False)
    original = module.proj.weight.detach().clone()
    hook = AlignDevicesHook(execution_device="cuda", offload=True)
    add_hook_to_module(module.proj, hook)

    count = AbliterationPipeline._project_out_advanced(
        module,
        torch.tensor([[1.0], [0.0], [0.0], [0.0]], device="cuda"),
        ["proj"],
    )
    output = module.proj(torch.ones(1, 4, device="cuda"))

    expected = original.clone()
    expected[:, 0] = 0
    assert count == 1
    assert output.device.type == "cuda"
    assert module.proj.weight.device.type == "meta"
    torch.testing.assert_close(hook.weights_map["weight"], expected)
