"""Real CUDA and bitsandbytes placement/operation probes."""

from __future__ import annotations

import pytest
import torch
import torch.nn as nn
from accelerate.hooks import AlignDevicesHook, add_hook_to_module

from obliteratus import device
from obliteratus.abliterate import AbliterationPipeline


pytestmark = pytest.mark.gpu


def test_cuda_discovery_dtype_placement_and_operation():
    if not torch.cuda.is_available():
        pytest.skip("requires a CUDA runner; set ENABLE_CUDA_GATE and attach the cuda label")
    assert device.is_cuda()
    assert device.get_device("auto") == "cuda"
    assert device.default_dtype("cuda") is torch.float16
    tensor = torch.arange(16, device="cuda", dtype=torch.float32).reshape(4, 4)
    result = tensor @ tensor.T
    assert result.device.type == "cuda"
    assert torch.isfinite(result).all()


def test_cuda_execution_observes_offloaded_surgery_and_restores_meta_state():
    if not torch.cuda.is_available():
        pytest.skip("requires a CUDA runner; set ENABLE_CUDA_GATE and attach the cuda label")

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


def test_bitsandbytes_quantization_operation():
    if not torch.cuda.is_available():
        pytest.skip("requires a CUDA runner; set ENABLE_CUDA_GATE and attach the cuda label")
    bnb = pytest.importorskip("bitsandbytes", reason="install locked bitsandbytes>=0.46.1")
    assert device.supports_bitsandbytes("cuda")
    source = torch.randn(16, 16, device="cuda", dtype=torch.float16)
    quantized, state = bnb.functional.quantize_4bit(source, quant_type="nf4")
    restored = bnb.functional.dequantize_4bit(quantized, state)
    assert restored.device.type == "cuda"
    assert restored.shape == source.shape
    assert torch.isfinite(restored).all()
