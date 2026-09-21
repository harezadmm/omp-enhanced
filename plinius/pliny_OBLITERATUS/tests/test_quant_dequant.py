"""Tests for FP8/NVFP4 checkpoint dequantization (CPU-only, synthetic).

Covers:
- FP8 block-wise (DeepSeek-style) and per-channel round-trips
- NVFP4 round-trips (ModelOpt + compressed-tensors global-scale conventions), native and
  manual nibble-unpack paths agreeing with each other
- detect_quant_scheme classification from config.json metadata
- surgery guards rejecting un-dequantized FP8/NVFP4 weights
- end-to-end load_model() on tiny synthetic quantized checkpoints
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from obliteratus.models import quant_dequant as qd

HAS_FP8 = hasattr(torch, "float8_e4m3fn")
requires_fp8 = pytest.mark.skipif(not HAS_FP8, reason="torch build lacks float8 dtypes")

FP8_MAX = 448.0  # e4m3 max
E2M1_MAX = 6.0


# ---------------------------------------------------------------------------
# Reference quantization helpers (test-side)
# ---------------------------------------------------------------------------

def _quantize_fp8_blockwise(w: torch.Tensor, block=(128, 128)):
    """Float weight → (fp8 tensor, scale_inv) using DeepSeek convention."""
    M, N = w.shape
    bm, bn = block
    scale = torch.zeros((M + bm - 1) // bm, (N + bn - 1) // bn)
    q = torch.zeros_like(w)
    for i in range(0, M, bm):
        for j in range(0, N, bn):
            blk = w[i:i + bm, j:j + bn]
            s = blk.abs().max() / FP8_MAX
            s = max(s, 1e-8)
            scale[i // bm, j // bn] = s
            q[i:i + bm, j:j + bn] = blk / s
    return q.to(torch.float8_e4m3fn), scale


def _quantize_fp8_per_channel(w: torch.Tensor, inverse: bool):
    scale = (w.abs().amax(dim=1, keepdim=True) / FP8_MAX).clamp(min=1e-8)
    q = (w / scale).to(torch.float8_e4m3fn)
    return q, (1.0 / scale if inverse else scale)


def _nearest_e2m1(x: torch.Tensor) -> torch.Tensor:
    """Round to nearest E2M1 value, preserving sign. Returns float codes."""
    lut = torch.tensor(qd.E2M1_POSITIVE, dtype=x.dtype)
    sign = torch.sign(x)
    ax = x.abs().clamp(max=E2M1_MAX)
    idx = (ax.unsqueeze(-1) - lut).abs().argmin(-1)
    return sign * lut[idx]


def _pack_nvfp4(w: torch.Tensor, group: int = 16, global_reciprocal: bool = False):
    """Float (M, N) weight → (packed uint8, e4m3 block scales, fp32 global).

    Follows the ModelOpt convention: w ≈ e2m1 * block_scale * global_scale.
    Compressed-tensors keeps the block scale but stores the reciprocal of
    the global scale.
    """
    M, N = w.shape
    wg = w.reshape(M, N // group, group)
    global_scale = (w.abs().max() / (FP8_MAX * E2M1_MAX)).clamp(min=1e-12)
    bs = (wg.abs().amax(-1) / (E2M1_MAX * global_scale)).clamp(min=1e-8)
    q = _nearest_e2m1(wg / (bs.unsqueeze(-1) * global_scale))
    # values → nibble codes via LUT lookup
    codes = torch.zeros_like(q, dtype=torch.uint8)
    for code, val in enumerate(list(qd.E2M1_POSITIVE) + [-v for v in qd.E2M1_POSITIVE]):
        codes[q == val] = code
    codes = codes.reshape(M, N)
    low = codes[:, 0::2]
    high = codes[:, 1::2]
    packed = (high << 4) | low
    bs_fp8 = bs.to(torch.float8_e4m3fn)
    if global_reciprocal:
        return packed, bs_fp8, 1.0 / global_scale
    return packed, bs_fp8, global_scale.float()


# ---------------------------------------------------------------------------
# FP8 dequantization
# ---------------------------------------------------------------------------

@requires_fp8
def test_fp8_blockwise_roundtrip():
    torch.manual_seed(0)
    w = torch.randn(256, 256)
    q, scale_inv = _quantize_fp8_blockwise(w)
    out = qd.dequantize_fp8_blockwise(q, scale_inv, (128, 128))
    rel = (out - w).norm() / w.norm()
    assert rel < 0.05, f"blockwise FP8 round-trip error {rel:.4f}"


@requires_fp8
def test_fp8_blockwise_non_divisible_dims():
    torch.manual_seed(1)
    w = torch.randn(200, 300)  # not divisible by 128
    q, scale_inv = _quantize_fp8_blockwise(w)
    out = qd.dequantize_fp8_blockwise(q, scale_inv, (128, 128))
    assert out.shape == w.shape
    rel = (out - w).norm() / w.norm()
    assert rel < 0.05


@requires_fp8
@pytest.mark.parametrize("inverse", [False, True])
def test_fp8_per_channel_roundtrip(inverse):
    torch.manual_seed(2)
    w = torch.randn(64, 128)
    q, scale = _quantize_fp8_per_channel(w, inverse)
    out = qd.dequantize_fp8_per_channel(q, scale, scale_is_inverse=inverse)
    rel = (out - w).norm() / w.norm()
    assert rel < 0.05


@requires_fp8
def test_fp8_per_tensor_scalar_scale():
    torch.manual_seed(3)
    w = torch.randn(32, 64)
    scale = w.abs().max() / FP8_MAX
    q = (w / scale).to(torch.float8_e4m3fn)
    out = qd.dequantize_fp8_per_channel(q, scale.reshape(1))
    rel = (out - w).norm() / w.norm()
    assert rel < 0.05


# ---------------------------------------------------------------------------
# NVFP4 dequantization
# ---------------------------------------------------------------------------

@requires_fp8
@pytest.mark.parametrize("global_reciprocal", [False, True])
def test_nvfp4_roundtrip(global_reciprocal):
    torch.manual_seed(4)
    w = torch.randn(64, 128)
    packed, bs, gs = _pack_nvfp4(w, global_reciprocal=global_reciprocal)
    out = qd.dequantize_nvfp4(
        packed,
        bs,
        gs,
        global_scale_is_inverse=global_reciprocal,
        force_manual=True,
    )
    assert out.shape == w.shape
    # NVFP4 is coarse — check correlation and relative error, not equality.
    cos = torch.nn.functional.cosine_similarity(
        w.flatten(), out.flatten(), dim=0,
    )
    rel = (out - w).norm() / w.norm()
    assert cos > 0.995, f"NVFP4 cosine {cos:.4f}"
    assert rel < 0.15, f"NVFP4 relative error {rel:.4f}"


@requires_fp8
def test_nvfp4_native_and_manual_unpack_agree():
    if not qd._native_fp4_upcast_works():
        pytest.skip("torch build lacks a working float4_e2m1fn_x2 upcast")
    torch.manual_seed(5)
    packed = torch.randint(0, 256, (16, 64), dtype=torch.uint8)
    native = qd.unpack_e2m1(packed, force_manual=False)
    manual = qd.unpack_e2m1(packed, force_manual=True)
    assert torch.equal(native, manual)


def test_nvfp4_manual_unpack_known_values():
    # 0x1B: low nibble 0xB (-1.5), high nibble 0x1 (+0.5) — low nibble first.
    # 0x84: low nibble 0x4 (+2.0), high nibble 0x8 (-0.0).
    packed = torch.tensor([[0x1B, 0x84]], dtype=torch.uint8)
    out = qd.unpack_e2m1(packed, force_manual=True)
    assert out.shape == (1, 4)
    assert out[0, 0].item() == -1.5
    assert out[0, 1].item() == 0.5
    assert out[0, 2].item() == 2.0
    assert out[0, 3].item() == 0.0


@requires_fp8
def test_nvfp4_no_global_scale():
    torch.manual_seed(6)
    w = torch.randn(32, 64)
    packed, bs, gs = _pack_nvfp4(w)
    out = qd.dequantize_nvfp4(packed, bs, None, force_manual=True)
    assert out.shape == w.shape


def test_nvfp4_bad_group_size_raises():
    packed = torch.zeros((4, 8), dtype=torch.uint8)  # unpacks to 4x16
    bs = torch.ones((4, 1), dtype=torch.float32)
    with pytest.raises(RuntimeError, match="group_size"):
        qd.dequantize_nvfp4(packed, bs, None, group_size=32)


# ---------------------------------------------------------------------------
# Scheme detection
# ---------------------------------------------------------------------------

def _write_config(tmp_path, cfg: dict):
    with open(os.path.join(tmp_path, "config.json"), "w") as fh:
        json.dump(cfg, fh)


def test_load_json_local_missing_returns_none(tmp_path):
    assert qd._load_json_from_checkpoint(str(tmp_path), "missing.json") is None


def test_load_json_remote_unexpected_download_failure_returns_none(monkeypatch):
    def fail_download(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr("huggingface_hub.hf_hub_download", fail_download)

    assert qd._load_json_from_checkpoint(
        "org/model",
        "config.json",
        revision="immutable-sha",
        local_files_only=True,
    ) is None


def test_safetensors_key_names_reads_single_file_and_index(tmp_path):
    from safetensors.torch import save_file

    save_file({"a.weight": torch.ones(1)}, tmp_path / "model.safetensors")
    assert qd._safetensors_key_names(str(tmp_path), None) == {"a.weight"}
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({
        "weight_map": {"b.weight": "model.safetensors"},
    }))
    assert qd._safetensors_key_names(str(tmp_path), None) == {"b.weight"}


def test_safetensors_key_names_handles_missing_and_invalid_files(tmp_path):
    assert qd._safetensors_key_names(str(tmp_path), None) == set()
    (tmp_path / "model.safetensors").write_text("not safetensors")
    assert qd._safetensors_key_names(str(tmp_path), None) == set()


def test_safetensors_key_names_remote_propagates_hub_policy(tmp_path, monkeypatch):
    from safetensors.torch import save_file

    checkpoint = tmp_path / "remote.safetensors"
    save_file({"remote.weight": torch.ones(1)}, checkpoint)
    monkeypatch.setattr(qd, "_load_json_from_checkpoint", lambda *args, **kwargs: None)
    calls = []

    def fake_download(repo, filename, **kwargs):
        calls.append((repo, filename, kwargs))
        return str(checkpoint)

    monkeypatch.setattr("huggingface_hub.hf_hub_download", fake_download)
    assert qd._safetensors_key_names(
        "org/model",
        None,
        token="token",
        revision="immutable-sha",
        local_files_only=True,
    ) == {"remote.weight"}
    assert calls == [(
        "org/model",
        "model.safetensors",
        {
            "token": "token",
            "revision": "immutable-sha",
            "local_files_only": True,
        },
    )]


def test_safetensors_key_names_remote_download_failure_is_empty(monkeypatch):
    monkeypatch.setattr(qd, "_load_json_from_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "huggingface_hub.hf_hub_download",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    assert qd._safetensors_key_names("org/model", None) == set()


def test_detect_none(tmp_path):
    _write_config(tmp_path, {"model_type": "gpt2"})
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.NONE


def test_detect_fp8_blockwise(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "fp8",
            "weight_block_size": [128, 128],
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.FP8_BLOCKWISE
    assert det.block_size == (128, 128)


def test_detect_fp8_blockwise_via_scale_keys(tmp_path):
    _write_config(tmp_path, {"quantization_config": {"quant_method": "fp8"}})
    with open(os.path.join(tmp_path, "model.safetensors.index.json"), "w") as fh:
        json.dump({"weight_map": {"model.layers.0.mlp.weight_scale_inv": "model.safetensors"}}, fh)
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.FP8_BLOCKWISE


def test_detect_fp8_without_supported_layout_fails_closed(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "fp8",
            "activation_scheme": "static",
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.UNSUPPORTED
    assert "without weight_block_size" in det.reason


def test_detect_fp8_ct(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "compressed-tensors",
            "config_groups": {"group_0": {"weights": {"num_bits": 8, "type": "float"}}},
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.FP8_PER_CHANNEL_CT


def test_detect_nvfp4_ct(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "compressed-tensors",
            "format": "nvfp4-pack-quantized",
            "config_groups": {"group_0": {"weights": {"num_bits": 4, "type": "float", "group_size": 16}}},
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.NVFP4_CT
    assert det.scale_is_inverse is False
    assert det.global_scale_is_inverse is True
    assert det.group_size == 16


def test_detect_nvfp4_ct_without_packed_format_fails_closed(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "compressed-tensors",
            "config_groups": {
                "group_0": {
                    "weights": {"num_bits": 4, "type": "float", "group_size": 16},
                },
            },
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.UNSUPPORTED
    assert "nvfp4-pack-quantized" in det.reason


def test_detect_nvfp4_modelopt(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {"quant_method": "modelopt", "quant_algo": "NVFP4"},
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.NVFP4_MODELOPT


def test_detect_modelopt_mixed_precision(tmp_path):
    """Nemotron-3-Nano NVFP4: FP8 mixer + NVFP4 experts in one checkpoint."""
    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "modelopt",
            "quant_algo": "MIXED_PRECISION",
            "config_groups": {
                "group_0": {"weights": {"num_bits": 8, "type": "float"}},
                "group_1": {"weights": {"num_bits": 4, "type": "float", "group_size": 16}},
            },
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.NVFP4_MODELOPT


def test_detect_modelopt_mixed_fp8_only(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "modelopt",
            "quant_algo": "MIXED_PRECISION",
            "config_groups": {
                "group_0": {"weights": {"num_bits": 8, "type": "float"}},
            },
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.FP8_PER_CHANNEL_CT


def test_detect_modelopt_fp8_and_unknown(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {"quant_method": "modelopt", "quant_algo": "FP8"},
    })
    assert qd.detect_quant_scheme(str(tmp_path)).scheme is qd.QuantScheme.FP8_PER_CHANNEL_CT

    _write_config(tmp_path, {
        "quantization_config": {
            "quant_method": "modelopt",
            "kv_cache_quant_algo": "INT8",
        },
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.UNSUPPORTED
    assert "INT8" in det.reason


def test_detect_unsupported_fbgemm(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {"quant_method": "fbgemm_fp8"},
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.UNSUPPORTED
    assert "fbgemm" in det.reason


def test_detect_nonempty_quant_config_without_method_fails_closed(tmp_path):
    _write_config(tmp_path, {
        "quantization_config": {"bits": 4, "format": "unknown-packed-layout"},
    })
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.UNSUPPORTED
    assert "quant_method ''" in det.reason


@pytest.mark.parametrize("method", ["gptq", "awq", "bitsandbytes"])
def test_detect_passthrough_schemes(tmp_path, method):
    _write_config(tmp_path, {"quantization_config": {"quant_method": method}})
    det = qd.detect_quant_scheme(str(tmp_path))
    assert det.scheme is qd.QuantScheme.NONE


def test_detect_remote_checkpoint_pins_revision_and_offline_mode(
    tmp_path, monkeypatch,
):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "quantization_config": {
            "quant_method": "fp8",
            "weight_block_size": [128, 128],
        },
    }))
    calls = []

    def fake_download(repo, filename, **kwargs):
        calls.append((repo, filename, kwargs))
        return str(config_path)

    monkeypatch.setattr("huggingface_hub.hf_hub_download", fake_download)
    det = qd.detect_quant_scheme(
        "org/model",
        token="token",
        revision="immutable-sha",
        local_files_only=True,
    )

    assert det.scheme is qd.QuantScheme.FP8_BLOCKWISE
    assert calls == [(
        "org/model",
        "config.json",
        {
            "token": "token",
            "revision": "immutable-sha",
            "local_files_only": True,
        },
    )]


def test_loader_propagates_revision_and_offline_mode_to_detection(monkeypatch):
    from obliteratus.models import loader as loader_mod

    captured = {}
    monkeypatch.setattr(
        loader_mod.AutoConfig,
        "from_pretrained",
        staticmethod(lambda *args, **kwargs: SimpleNamespace(quantization_config=None)),
    )

    def fake_detect(model_name, **kwargs):
        captured["model_name"] = model_name
        captured.update(kwargs)
        return qd.QuantDetection(qd.QuantScheme.UNSUPPORTED, reason="test sentinel")

    monkeypatch.setattr(qd, "detect_quant_scheme", fake_detect)
    with pytest.raises(RuntimeError, match="test sentinel"):
        loader_mod.load_model(
            "org/model",
            task="causal_lm",
            device="cpu",
            dtype="float32",
            revision="immutable-sha",
            local_files_only=True,
        )

    assert captured == {
        "model_name": "org/model",
        "token": None,
        "revision": "immutable-sha",
        "local_files_only": True,
    }


def test_materialize_remote_checkpoint_pins_revision_and_offline_mode(
    tmp_path, monkeypatch,
):
    from safetensors.torch import save_file

    source = tmp_path / "source"
    source.mkdir()
    _write_config(source, {
        "model_type": "gpt2",
        "quantization_config": {"quant_method": "fp8"},
    })
    save_file({"plain.weight": torch.ones(2, 2)}, source / "model.safetensors")
    captured = {}

    def fake_snapshot(repo, **kwargs):
        captured["repo"] = repo
        captured.update(kwargs)
        return str(source)

    monkeypatch.setattr("huggingface_hub.snapshot_download", fake_snapshot)
    output, returned_source = qd.materialize_dequantized_checkpoint(
        "org/model",
        qd.QuantDetection(qd.QuantScheme.FP8_BLOCKWISE),
        token="token",
        revision="immutable-sha",
        local_files_only=True,
    )
    try:
        assert returned_source == str(source)
        assert captured["repo"] == "org/model"
        assert captured["token"] == "token"
        assert captured["revision"] == "immutable-sha"
        assert captured["local_files_only"] is True
        assert "*.safetensors" in captured["allow_patterns"]
    finally:
        import shutil

        shutil.rmtree(output)


def test_materialize_failure_removes_partial_checkpoint(tmp_path, monkeypatch):
    import tempfile

    source = tmp_path / "source"
    source.mkdir()
    _write_config(source, {
        "model_type": "gpt2",
        "quantization_config": {"quant_method": "fp8"},
    })
    partial = tmp_path / "partial-output"

    def fake_mkdtemp(*, prefix):
        assert prefix == "obliteratus_dequant_"
        partial.mkdir()
        return str(partial)

    monkeypatch.setattr(tempfile, "mkdtemp", fake_mkdtemp)
    with pytest.raises(RuntimeError, match="no safetensors weights"):
        qd.materialize_dequantized_checkpoint(
            str(source),
            qd.QuantDetection(qd.QuantScheme.FP8_BLOCKWISE),
        )

    assert not partial.exists()


def test_materialize_sharded_checkpoint_rewrites_index_and_copies_metadata(tmp_path):
    import shutil

    from safetensors.torch import load_file, save_file

    save_file({"a.weight": torch.ones(1)}, tmp_path / "part-1.safetensors")
    save_file({"b.weight": torch.ones(1)}, tmp_path / "part-2.safetensors")
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({
        "metadata": {"total_size": 8},
        "weight_map": {
            "a.weight": "part-1.safetensors",
            "b.weight": "part-2.safetensors",
        },
    }))
    _write_config(tmp_path, {
        "model_type": "gpt2",
        "quantization_config": {"quant_method": "fp8"},
    })
    (tmp_path / "tokenizer_config.json").write_text('{"test": true}')
    output, _ = qd.materialize_dequantized_checkpoint(
        str(tmp_path),
        qd.QuantDetection(qd.QuantScheme.FP8_BLOCKWISE),
        out_dtype=torch.float32,
    )
    try:
        index = json.loads(Path(output, "model.safetensors.index.json").read_text())
        assert index["metadata"] == {"total_size": 8}
        assert index["weight_map"] == {
            "a.weight": "part-1.safetensors",
            "b.weight": "part-2.safetensors",
        }
        assert load_file(Path(output, "part-1.safetensors"))["a.weight"].item() == 1
        assert json.loads(Path(output, "tokenizer_config.json").read_text()) == {
            "test": True,
        }
    finally:
        shutil.rmtree(output)


@requires_fp8
def test_materialize_resolves_scale_tensor_across_shard_boundary(tmp_path):
    import shutil

    from safetensors.torch import load_file, save_file

    weight = torch.tensor([[0.5, 1.0]], dtype=torch.float8_e4m3fn)
    save_file({"a.weight": weight}, tmp_path / "part-1.safetensors")
    save_file(
        {
            "a.weight_scale": torch.tensor([2.0]),
            "norm.weight": torch.ones(1),
        },
        tmp_path / "part-2.safetensors",
    )
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({
        "metadata": {"total_size": 6},
        "weight_map": {
            "a.weight": "part-1.safetensors",
            "a.weight_scale": "part-2.safetensors",
            "norm.weight": "part-2.safetensors",
        },
    }))
    _write_config(tmp_path, {
        "model_type": "gpt2",
        "quantization_config": {"quant_method": "modelopt", "quant_algo": "FP8"},
    })

    output, _ = qd.materialize_dequantized_checkpoint(
        str(tmp_path),
        qd.QuantDetection(qd.QuantScheme.FP8_PER_CHANNEL_CT),
        out_dtype=torch.float32,
    )
    try:
        index = json.loads(Path(output, "model.safetensors.index.json").read_text())
        assert index["metadata"]["total_size"] == 12
        assert index["weight_map"] == {
            "a.weight": "part-1.safetensors",
            "norm.weight": "part-2.safetensors",
        }
        assert load_file(Path(output, "part-1.safetensors"))["a.weight"].tolist() == [
            [1.0, 2.0],
        ]
        assert set(load_file(Path(output, "part-2.safetensors"))) == {"norm.weight"}
    finally:
        shutil.rmtree(output)


def test_loader_failure_removes_materialized_checkpoint(tmp_path, monkeypatch):
    from obliteratus.models import loader as loader_mod

    materialized = tmp_path / "materialized"
    materialized.mkdir()
    config = SimpleNamespace(quantization_config=None)
    monkeypatch.setattr(
        loader_mod.AutoConfig,
        "from_pretrained",
        staticmethod(lambda *args, **kwargs: config),
    )
    monkeypatch.setattr(
        qd,
        "detect_quant_scheme",
        lambda *args, **kwargs: qd.QuantDetection(qd.QuantScheme.FP8_BLOCKWISE),
    )
    monkeypatch.setattr(
        qd,
        "materialize_dequantized_checkpoint",
        lambda *args, **kwargs: (str(materialized), "source"),
    )
    monkeypatch.setattr(loader_mod, "_estimate_model_memory_gb", lambda *args: 0.0)

    class FailingModelClass:
        @staticmethod
        def from_pretrained(**kwargs):
            raise OSError("load failed")

    monkeypatch.setattr(loader_mod, "_select_model_class", lambda *args: FailingModelClass)
    with pytest.raises(OSError, match="load failed"):
        loader_mod.load_model(
            "org/model",
            task="causal_lm",
            device="cpu",
            dtype="float32",
        )

    assert not materialized.exists()


def test_smoke_loader_requires_explicit_remote_code_trust():
    from scripts import smoke_load_quant

    parser = smoke_load_quant.build_parser()
    assert parser.parse_args(["org/model"]).trust_remote_code is False
    assert parser.parse_args([
        "org/model", "--trust-remote-code",
    ]).trust_remote_code is True


def test_numerical_fixture_provenance_is_machine_readable():
    provenance = json.loads(
        (Path(__file__).parent / "fixtures" / "quant_dequant_provenance.json").read_text()
    )
    assert provenance["origin"] == "synthetic-runtime-generated"
    assert provenance["external_data"] is False
    assert provenance["torch_manual_seeds"] == list(range(9))
    assert provenance["oracles"]["fp8_relative_l2_max"] == 0.05
    assert provenance["oracles"]["nvfp4_relative_l2_max"] == 0.15


# ---------------------------------------------------------------------------
# State-dict dequantization
# ---------------------------------------------------------------------------


@requires_fp8
def test_upcast_raw_fp8_bytes_and_reject_plain_float():
    fp8 = torch.tensor([0.5, -1.0], dtype=torch.float8_e4m3fn)
    raw = fp8.view(torch.uint8)
    assert torch.equal(qd._upcast_fp8(raw), fp8.float())
    with pytest.raises(RuntimeError, match="cannot upcast"):
        qd._upcast_fp8(torch.ones(2, dtype=torch.float32))


@requires_fp8
def test_fp8_blockwise_rejects_incompatible_scale_shape():
    weight = torch.ones(4, 4, dtype=torch.float8_e4m3fn)
    with pytest.raises(RuntimeError, match="incompatible"):
        qd.dequantize_fp8_blockwise(weight, torch.ones(1, 1), block_size=(2, 2))


def test_unpack_native_failure_falls_back_to_manual(monkeypatch):
    packed = torch.tensor([[0x1B]], dtype=torch.uint8)
    monkeypatch.setattr(qd, "_native_fp4_upcast_works", lambda: True)
    monkeypatch.setattr(
        qd,
        "_unpack_e2m1_native",
        lambda value: (_ for _ in ()).throw(RuntimeError("unsupported")),
    )
    assert qd.unpack_e2m1(packed).tolist() == [[-1.5, 0.5]]


def test_nvfp4_inverse_block_scale_and_output_shape():
    packed = torch.tensor([[0x11] * 8], dtype=torch.uint8)
    output = qd.dequantize_nvfp4(
        packed,
        torch.full((1, 1), 2.0),
        None,
        out_shape=(2, 8),
        scale_is_inverse=True,
        force_manual=True,
    )
    assert output.shape == (2, 8)
    assert torch.all(output == 0.25)

@requires_fp8
def test_dequantize_state_dict_fp8_blockwise():
    torch.manual_seed(7)
    w = torch.randn(256, 128)
    q, scale_inv = _quantize_fp8_blockwise(w)
    sd = {
        "layers.0.mlp.weight": q,
        "layers.0.mlp.weight_scale_inv": scale_inv,
        "layers.0.attn.bias": torch.randn(128),
    }
    det = qd.QuantDetection(qd.QuantScheme.FP8_BLOCKWISE)
    out = qd.dequantize_state_dict(sd, det, out_dtype=torch.bfloat16)
    assert set(out) == {"layers.0.mlp.weight", "layers.0.attn.bias"}
    assert out["layers.0.mlp.weight"].dtype == torch.bfloat16
    rel = (out["layers.0.mlp.weight"].float() - w).norm() / w.norm()
    assert rel < 0.05


@requires_fp8
def test_dequantize_state_dict_nvfp4_modelopt():
    torch.manual_seed(8)
    w = torch.randn(32, 64)
    packed, bs, gs = _pack_nvfp4(w)
    sd = {
        "experts.0.gate_up_proj": packed,
        "experts.0.gate_up_proj_scale": bs,
        "experts.0.gate_up_proj_scale_2": gs,
    }
    # Non-.weight key names (fused MoE style) must also dequantize.
    det = qd.QuantDetection(qd.QuantScheme.NVFP4_MODELOPT)
    out = qd.dequantize_state_dict(sd, det, out_dtype=torch.float32)
    assert set(out) == {"experts.0.gate_up_proj"}
    cos = torch.nn.functional.cosine_similarity(w.flatten(), out["experts.0.gate_up_proj"].flatten(), dim=0)
    assert cos > 0.995


@requires_fp8
def test_dequantize_state_dict_nvfp4_compressed_tensors_contract():
    torch.manual_seed(8)
    w = torch.randn(32, 64)
    packed, bs, gs = _pack_nvfp4(w, global_reciprocal=True)
    sd = {
        "layers.0.mlp.weight_packed": packed,
        "layers.0.mlp.weight_scale": bs,
        "layers.0.mlp.weight_global_scale": gs,
        "layers.0.mlp.input_global_scale": torch.tensor(1.0),
    }
    det = qd.QuantDetection(
        qd.QuantScheme.NVFP4_CT,
        global_scale_is_inverse=True,
    )
    out = qd.dequantize_state_dict(sd, det, out_dtype=torch.float32)
    assert set(out) == {"layers.0.mlp.weight"}
    cos = torch.nn.functional.cosine_similarity(
        w.flatten(), out["layers.0.mlp.weight"].flatten(), dim=0,
    )
    rel = (out["layers.0.mlp.weight"] - w).norm() / w.norm()
    assert cos > 0.995
    assert rel < 0.15


@requires_fp8
def test_materialize_nvfp4_compressed_tensors_checkpoint_contract(tmp_path):
    import shutil

    from safetensors.torch import load_file, save_file

    torch.manual_seed(8)
    w = torch.randn(32, 64)
    packed, bs, gs = _pack_nvfp4(w, global_reciprocal=True)
    save_file({
        "layers.0.mlp.weight_packed": packed,
        "layers.0.mlp.weight_scale": bs,
        "layers.0.mlp.weight_global_scale": gs,
        "layers.0.mlp.input_global_scale": torch.tensor(1.0),
        "layers.0.norm.weight": torch.ones(32),
    }, tmp_path / "model.safetensors")
    _write_config(tmp_path, {
        "model_type": "gpt2",
        "quantization_config": {
            "quant_method": "compressed-tensors",
            "format": "nvfp4-pack-quantized",
        },
    })
    det = qd.QuantDetection(
        qd.QuantScheme.NVFP4_CT,
        global_scale_is_inverse=True,
    )
    output, source = qd.materialize_dequantized_checkpoint(
        str(tmp_path), det, out_dtype=torch.float32,
    )
    try:
        assert source == str(tmp_path)
        state = load_file(os.path.join(output, "model.safetensors"))
        assert set(state) == {"layers.0.mlp.weight", "layers.0.norm.weight"}
        rel = (state["layers.0.mlp.weight"] - w).norm() / w.norm()
        assert rel < 0.15
        materialized_config = json.loads(
            Path(output, "config.json").read_text(encoding="utf-8")
        )
        assert "quantization_config" not in materialized_config
    finally:
        shutil.rmtree(output)


@requires_fp8
def test_dequantize_state_dict_fp8_missing_scale_raises():
    q = torch.randn(16, 16).to(torch.float8_e4m3fn)
    det = qd.QuantDetection(qd.QuantScheme.FP8_BLOCKWISE)
    with pytest.raises(RuntimeError, match="no weight_scale"):
        qd.dequantize_state_dict({"a.weight": q}, det)


@requires_fp8
def test_dequantize_state_dict_fp8_per_channel():
    state = {
        "a.weight": torch.tensor([[0.5, 1.0]], dtype=torch.float8_e4m3fn),
        "a.weight_scale": torch.tensor([2.0]),
    }
    out = qd.dequantize_state_dict(
        state,
        qd.QuantDetection(qd.QuantScheme.FP8_PER_CHANNEL_CT),
        out_dtype=torch.float32,
    )
    assert set(out) == {"a.weight"}
    assert out["a.weight"].tolist() == [[1.0, 2.0]]


def test_dequantize_state_dict_rejects_packed_weight_for_wrong_scheme():
    state = {
        "a.weight": torch.zeros(1, 8, dtype=torch.uint8),
        "a.weight_scale": torch.ones(1, 1),
    }
    with pytest.raises(RuntimeError, match="unsupported layout"):
        qd.dequantize_state_dict(
            state,
            qd.QuantDetection(qd.QuantScheme.FP8_BLOCKWISE),
        )


def test_dequantize_state_dict_rejects_unscaled_packed_weight():
    with pytest.raises(RuntimeError, match="no recognizable scale siblings"):
        qd.dequantize_state_dict(
            {"a.weight_packed": torch.zeros(1, 8, dtype=torch.uint8)},
            qd.QuantDetection(qd.QuantScheme.NVFP4_CT),
        )


def test_scale_key_requires_matching_weight():
    state = {"logit_scale": torch.tensor(1.0)}
    assert qd.is_scale_key("logit_scale", state) is False
    assert qd.is_scale_key("ordinary.weight", state) is False


# ---------------------------------------------------------------------------
# Surgery guards
# ---------------------------------------------------------------------------

@requires_fp8
def test_is_quantized_param_fp8():
    from obliteratus.abliterate import AbliterationPipeline

    p = torch.nn.Parameter(torch.randn(8, 8).to(torch.float8_e4m3fn))
    assert AbliterationPipeline._is_quantized_param(p) is True
    p2 = torch.nn.Parameter(torch.randn(8, 8))
    assert AbliterationPipeline._is_quantized_param(p2) is False


@requires_fp8
def test_dequantize_weight_guard_fp8():
    from obliteratus.abliterate import AbliterationPipeline

    mod = torch.nn.Linear(8, 8)
    mod.weight = torch.nn.Parameter(torch.randn(8, 8).to(torch.float8_e4m3fn))
    with pytest.raises(RuntimeError, match="without dequantization"):
        AbliterationPipeline._dequantize_weight(mod)


def test_dequantize_weight_guard_packed_uint8_with_scales():
    from obliteratus.abliterate import AbliterationPipeline

    mod = torch.nn.Linear(8, 8)
    mod.weight = torch.nn.Parameter(torch.zeros(8, 4, dtype=torch.uint8), requires_grad=False)
    mod.weight_scale = torch.ones(8, 1, dtype=torch.float32)
    with pytest.raises(RuntimeError, match="without dequantization"):
        AbliterationPipeline._dequantize_weight(mod)


def test_dequantize_weight_plain_uint8_still_converts():
    """Pre-existing behavior for scale-less custom uint8 weights is kept."""
    from obliteratus.abliterate import AbliterationPipeline

    mod = torch.nn.Linear(8, 8)
    mod.weight = torch.nn.Parameter(torch.ones(8, 8, dtype=torch.uint8), requires_grad=False)
    w, is_q = AbliterationPipeline._dequantize_weight(mod)
    assert is_q is True
    assert w.is_floating_point()


def test_fused_uint8_guard_requires_quantization_scale_sibling():
    from obliteratus.abliterate import AbliterationPipeline

    container = torch.nn.Module()
    container.w1 = torch.nn.Parameter(
        torch.zeros(2, 4, 2, dtype=torch.uint8), requires_grad=False,
    )
    container.w1_scale = torch.ones(2, 4, 1)
    with pytest.raises(RuntimeError, match="without dequantization"):
        AbliterationPipeline._project_fused_3d(
            container,
            torch.ones(2, 1),
            ["w1"],
            norm_preserve=False,
            scale=1.0,
        )


@requires_fp8
def test_fused_fp8_guard_rejects_raw_storage():
    from obliteratus.abliterate import AbliterationPipeline

    container = torch.nn.Module()
    container.w1 = torch.nn.Parameter(
        torch.zeros(2, 4, 2).to(torch.float8_e4m3fn), requires_grad=False,
    )
    with pytest.raises(RuntimeError, match="without dequantization"):
        AbliterationPipeline._project_fused_3d(
            container,
            torch.ones(2, 1),
            ["w1"],
            norm_preserve=False,
            scale=1.0,
        )


def test_granular_fused_uint8_guard_rejects_packed_storage():
    from obliteratus.abliterate import AbliterationPipeline

    container = torch.nn.Module()
    container.w1 = torch.nn.Parameter(
        torch.zeros(2, 4, 2, dtype=torch.uint8), requires_grad=False,
    )
    container.w1_scale = torch.ones(2, 4, 1)
    with pytest.raises(RuntimeError, match="without dequantization"):
        AbliterationPipeline._project_fused_3d_granular(
            container,
            torch.ones(2),
            {},
            ["w1"],
            norm_preserve=False,
            scale=1.0,
        )


def test_selective_fused_uint8_guard_rejects_packed_storage():
    from obliteratus.abliterate import AbliterationPipeline

    container = torch.nn.Module()
    container.w1 = torch.nn.Parameter(
        torch.zeros(2, 4, 2, dtype=torch.uint8), requires_grad=False,
    )
    container.w1_global_scale = torch.ones(1)
    with pytest.raises(RuntimeError, match="without dequantization"):
        AbliterationPipeline._project_fused_3d_selective_inversion(
            container,
            torch.ones(2),
            ["w1"],
            safety_indices={0},
            reflect_scale=2.0,
            remove_scale=1.0,
            norm_preserve=False,
        )


# ---------------------------------------------------------------------------
# End-to-end loader on tiny synthetic checkpoints
# ---------------------------------------------------------------------------

@requires_fp8
def test_load_model_fp8_blockwise_checkpoint(tmp_path, monkeypatch):
    from obliteratus.models import loader as loader_mod

    captured = {}

    from safetensors.torch import save_file
    from transformers import GPT2Config, GPT2LMHeadModel

    cfg = GPT2Config(n_layer=1, n_head=2, n_embd=256, n_inner=512, vocab_size=128)
    model = GPT2LMHeadModel(cfg)
    sd = model.state_dict()
    out_sd = {}
    for k, v in sd.items():
        if k.endswith(".weight") and v.dim() == 2 and min(v.shape) >= 32:
            q, s = _quantize_fp8_blockwise(v.float())
            out_sd[k] = q
            out_sd[k[: -len(".weight")] + ".weight_scale_inv"] = s
            captured[k] = v.float()
        else:
            out_sd[k] = v
    save_file(out_sd, str(tmp_path / "model.safetensors"))
    cfg_dict = cfg.to_dict()
    cfg_dict["quantization_config"] = {
        "quant_method": "fp8", "weight_block_size": [128, 128],
    }
    with open(tmp_path / "config.json", "w") as fh:
        json.dump(cfg_dict, fh)

    class _FakeTok:
        pad_token = eos_token = "<|endoftext|>"

    monkeypatch.setattr(
        loader_mod.AutoTokenizer, "from_pretrained", staticmethod(lambda *a, **k: _FakeTok()),
    )
    handle = loader_mod.load_model(str(tmp_path), task="causal_lm", device="cpu", dtype="bfloat16")
    loaded = handle.model.state_dict()
    assert getattr(handle.model, "_obliteratus_dequantized_scheme", None) == "fp8_blockwise"
    for k, w in captured.items():
        p = loaded[k].detach().float()
        assert p.is_floating_point()
        rel = (p - w).norm() / w.norm()
        assert rel < 0.05, f"{k}: rel error {rel:.4f}"
    # No scale tensors survived into the loaded model
    assert not any("scale" in n for n in loaded)


@requires_fp8
def test_load_model_nvfp4_checkpoint(tmp_path, monkeypatch):
    from obliteratus.models import loader as loader_mod
    from safetensors.torch import save_file
    from transformers import GPT2Config, GPT2LMHeadModel

    cfg = GPT2Config(n_layer=1, n_head=2, n_embd=256, n_inner=512, vocab_size=128)
    model = GPT2LMHeadModel(cfg)
    sd = model.state_dict()
    out_sd = {}
    captured = {}
    for k, v in sd.items():
        if k.endswith(".weight") and v.dim() == 2 and v.shape[1] % 32 == 0 and min(v.shape) >= 32:
            packed, bs, gs = _pack_nvfp4(v.float())
            base = k[: -len(".weight")]
            out_sd[k] = packed
            out_sd[base + ".weight_scale"] = bs
            out_sd[base + ".weight_scale_2"] = gs
            captured[k] = v.float()
        else:
            out_sd[k] = v
    save_file(out_sd, str(tmp_path / "model.safetensors"))
    cfg_dict = cfg.to_dict()
    cfg_dict["quantization_config"] = {
        "quant_method": "modelopt", "quant_algo": "NVFP4",
    }
    with open(tmp_path / "config.json", "w") as fh:
        json.dump(cfg_dict, fh)

    class _FakeTok:
        pad_token = eos_token = "<|endoftext|>"

    monkeypatch.setattr(
        loader_mod.AutoTokenizer, "from_pretrained", staticmethod(lambda *a, **k: _FakeTok()),
    )
    handle = loader_mod.load_model(str(tmp_path), task="causal_lm", device="cpu", dtype="bfloat16")
    loaded = handle.model.state_dict()
    assert getattr(handle.model, "_obliteratus_dequantized_scheme", None) == "nvfp4_modelopt"
    for k, w in captured.items():
        p = loaded[k].detach().float()
        cos = torch.nn.functional.cosine_similarity(w.flatten(), p.flatten(), dim=0)
        assert cos > 0.99, f"{k}: cosine {cos:.4f}"
    assert not any("scale" in n for n in loaded)


def test_load_model_unsupported_scheme_fails_loudly(tmp_path):
    from obliteratus.models import loader as loader_mod

    _write_config(tmp_path, {
        "model_type": "gpt2",
        "quantization_config": {"quant_method": "fbgemm_fp8"},
    })
    with pytest.raises(RuntimeError, match="Unsupported quantization"):
        loader_mod.load_model(str(tmp_path), task="causal_lm", device="cpu", dtype="bfloat16")
