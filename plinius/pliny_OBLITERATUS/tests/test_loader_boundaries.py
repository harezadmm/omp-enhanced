"""Offline model-loader contracts at provider, device, and quantization boundaries."""

from __future__ import annotations

import builtins
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
import torch

from obliteratus.models import loader


def _execute_loader_source() -> dict:
    return runpy.run_path(str(Path(loader.__file__).resolve()), run_name="_loader_contract_probe")


def test_compatibility_shims_tolerate_independent_missing_or_broken_imports(monkeypatch):
    original_import = builtins.__import__
    failure_keys = {
        ("transformers", ("AutoModelForImageTextToText",)): ImportError,
        ("transformers", ("PreTrainedModel",)): RuntimeError,
        ("transformers.utils", ("output_capturing",)): ImportError,
        ("transformers.utils.import_utils", ()): RuntimeError,
        ("transformers.utils", ()): RuntimeError,
        ("transformers.pytorch_utils", ()): RuntimeError,
        ("transformers.generation_utils", ()): ModuleNotFoundError,
        ("transformers.generation", ()): RuntimeError,
        ("transformers.deepspeed", ()): ModuleNotFoundError,
        ("transformers.integrations.deepspeed", ()): RuntimeError,
        ("transformers.cache_utils", ("DynamicCache",)): RuntimeError,
        ("transformers.generation.logits_process", ()): RuntimeError,
        ("transformers.processing_utils", ()): RuntimeError,
        ("transformers.file_utils", ()): RuntimeError,
    }

    def rejecting_import(name, globals=None, locals=None, fromlist=(), level=0):
        exception = failure_keys.get((name, tuple(fromlist or ())))
        if exception is not None:
            raise exception(f"injected loader compatibility failure for {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", rejecting_import)
    namespace = _execute_loader_source()

    assert namespace["TASK_MODEL_MAP"]
    assert namespace["AutoModelForImageTextToText"] is None


def test_compatibility_shims_tolerate_missing_generic_module(monkeypatch):
    original_import = builtins.__import__

    def rejecting_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "transformers.utils.generic":
            raise RuntimeError("generic module unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", rejecting_import)
    assert _execute_loader_source()["TASK_MODEL_MAP"]


def test_compatibility_shims_tolerate_top_level_utils_patch_failure(monkeypatch):
    original_import = builtins.__import__

    def rejecting_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "transformers.utils" and not fromlist:
            raise RuntimeError("top-level utils module unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", rejecting_import)
    assert _execute_loader_source()["TASK_MODEL_MAP"]


def test_dynamic_cache_compatibility_alias_is_installed_when_needed(monkeypatch):
    original_import = builtins.__import__

    class LegacyDynamicCache:
        def get_max_cache_shape(self):
            return 7

    cache_module = SimpleNamespace(DynamicCache=LegacyDynamicCache)

    def cache_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "transformers.cache_utils" and tuple(fromlist or ()) == ("DynamicCache",):
            return cache_module
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", cache_import)
    assert _execute_loader_source()["TASK_MODEL_MAP"]
    assert LegacyDynamicCache().get_max_length() == 7


def test_compatibility_shims_tolerate_rejected_generic_attribute_patch(monkeypatch):
    import transformers.utils as transformers_utils

    class RejectWorkingDirectory(ModuleType):
        def __setattr__(self, name, value):
            if name == "working_or_temp_dir":
                raise RuntimeError("read-only compatibility module")
            super().__setattr__(name, value)

    fake_generic = RejectWorkingDirectory("transformers.utils.generic")
    monkeypatch.setitem(sys.modules, "transformers.utils.generic", fake_generic)
    monkeypatch.setattr(transformers_utils, "generic", fake_generic)

    assert _execute_loader_source()["TASK_MODEL_MAP"]


def test_all_tied_weights_compat_aggregates_filters_and_caches():
    class LegacyModel(torch.nn.Module):
        pass

    assert loader._install_all_tied_weights_keys_compat(LegacyModel) is True
    assert loader._install_all_tied_weights_keys_compat(LegacyModel) is False

    model = LegacyModel()
    model.lm_head = torch.nn.Linear(2, 2)
    model._tied_weights_keys = ["lm_head.weight", "missing.weight"]
    child = torch.nn.Module()
    child._tied_weights_keys = {"lm_head.bias": "lm_head.weight"}
    model.child = child

    assert model.all_tied_weights_keys == {
        "lm_head.weight": "lm_head.weight",
        "lm_head.bias": "lm_head.weight",
    }
    model.all_tied_weights_keys = {"cached.weight": "source.weight"}
    assert model.all_tied_weights_keys == {"cached.weight": "source.weight"}


def test_all_tied_weights_compat_prefers_transformers_expansion_contract():
    class ExpandableModel(torch.nn.Module):
        def get_expanded_tied_weights_keys(self, *, all_submodels):
            assert all_submodels is True
            return {"lm_head.weight": "model.embed_tokens.weight"}

    assert loader._install_all_tied_weights_keys_compat(ExpandableModel) is True
    model = ExpandableModel()

    assert model.all_tied_weights_keys == {
        "lm_head.weight": "model.embed_tokens.weight",
    }
    assert model.__dict__["_all_tied_weights_keys_store"] == {
        "lm_head.weight": "model.embed_tokens.weight",
    }


def test_all_tied_weights_compat_falls_back_when_expansion_is_legacy():
    class LegacyExpandableModel(torch.nn.Module):
        def get_expanded_tied_weights_keys(self, *, all_submodels):
            raise TypeError("legacy list contract")

    assert loader._install_all_tied_weights_keys_compat(LegacyExpandableModel) is True
    model = LegacyExpandableModel()
    model.lm_head = torch.nn.Linear(2, 2)
    model._tied_weights_keys = ["lm_head.weight"]

    assert model.all_tied_weights_keys == {"lm_head.weight": "lm_head.weight"}


def test_flash_attention_config_helpers_recurse_into_transformers_subconfigs():
    from transformers import PretrainedConfig

    outer = PretrainedConfig()
    inner = PretrainedConfig()
    outer.inner = inner
    inner._attn_implementation = "flash_attention_2"

    assert loader._config_uses_flash_attention_2(outer) is True
    loader._force_eager_config(outer)
    assert inner._attn_implementation == "eager"
    assert loader._config_uses_flash_attention_2(outer) is False


def _config(**overrides):
    values = {
        "model_type": "gpt2",
        "architectures": ["GPT2LMHeadModel"],
        "num_hidden_layers": 2,
        "num_attention_heads": 4,
        "hidden_size": 8,
        "intermediate_size": 16,
        "vocab_size": 32,
        "quantization_config": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _model():
    model = MagicMock()
    model.to.return_value = model
    model.state_dict.return_value = {"weight": torch.ones(2)}
    model.parameters.return_value = iter([torch.ones(2), torch.ones(3)])
    return model


@pytest.fixture
def loader_boundary(monkeypatch):
    config = _config()
    model = _model()
    tokenizer = SimpleNamespace(pad_token=None, eos_token="<eos>")
    model_class = SimpleNamespace(from_pretrained=Mock(return_value=model))
    monkeypatch.setattr(loader.AutoConfig, "from_pretrained", Mock(return_value=config))
    monkeypatch.setattr(loader.AutoTokenizer, "from_pretrained", Mock(return_value=tokenizer))
    monkeypatch.setitem(loader.TASK_MODEL_MAP, "causal_lm", model_class)
    monkeypatch.setitem(loader.TASK_MODEL_MAP, "classification", model_class)
    monkeypatch.setattr(loader.dev, "get_device", lambda preference="auto": "cpu" if preference == "auto" else preference)
    monkeypatch.setattr(loader.dev, "supports_device_map_auto", lambda _device=None: False)
    monkeypatch.setattr(loader.dev, "supports_bitsandbytes", lambda _device=None: False)
    monkeypatch.setattr(loader.dev, "supports_bfloat16", lambda _device=None: True)
    monkeypatch.setattr(loader.dev, "get_total_free_gb", lambda: 0.0)
    monkeypatch.setattr(loader.dev, "empty_cache", Mock())
    monkeypatch.setattr(loader.dev, "is_cuda", lambda: False)
    return SimpleNamespace(config=config, model=model, tokenizer=tokenizer, model_class=model_class)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model_name": ""}, "model_name must be"),
        ({"model_name": "x", "task": "embedding"}, "Unknown task"),
        ({"model_name": "x", "dtype": "int9"}, "Unknown dtype"),
        ({"model_name": "x", "quantization": "3bit"}, "Unknown quantization"),
        ({"model_name": "x", "gpu_memory_utilization": 0}, "gpu_memory_utilization"),
        ({"model_name": "x", "gpu_memory_utilization": -0.1}, "gpu_memory_utilization"),
        ({"model_name": "x", "gpu_memory_utilization": 1.1}, "gpu_memory_utilization"),
        ({"model_name": "x", "gpu_memory_utilization": float("nan")}, "gpu_memory_utilization"),
        ({"model_name": "x", "gpu_memory_utilization": float("inf")}, "gpu_memory_utilization"),
        ({"model_name": "x", "gpu_memory_utilization": True}, "gpu_memory_utilization"),
        ({"model_name": "x", "gpu_memory_utilization": "0.8"}, "gpu_memory_utilization"),
    ],
)
def test_invalid_requests_fail_before_provider_access(loader_boundary, monkeypatch, kwargs, message):
    config_load = Mock(side_effect=AssertionError("provider should not be called"))
    monkeypatch.setattr(loader.AutoConfig, "from_pretrained", config_load)
    with pytest.raises(ValueError, match=message):
        loader.load_model(**kwargs)
    config_load.assert_not_called()


def test_revision_trust_and_offline_flags_reach_every_provider(loader_boundary):
    handle = loader.load_model(
        "local/model",
        revision="deadbeef",
        trust_remote_code=True,
        local_files_only=True,
        skip_snapshot=True,
    )
    expected = {
        "trust_remote_code": True,
        "token": None,
        "revision": "deadbeef",
        "local_files_only": True,
    }
    loader.AutoConfig.from_pretrained.assert_called_once_with("local/model", **expected)
    loader_boundary.model_class.from_pretrained.assert_called_once()
    for key, value in expected.items():
        assert loader_boundary.model_class.from_pretrained.call_args.kwargs[key] == value
    loader.AutoTokenizer.from_pretrained.assert_called_once_with("local/model", **expected)
    assert handle.tokenizer.pad_token == "<eos>"
    loader_boundary.model.eval.assert_called_once_with()
    loader.dev.empty_cache.assert_called_once_with()


def test_unavailable_flash_attention_falls_back_to_eager(
    loader_boundary, monkeypatch,
):
    import transformers.utils

    loader_boundary.config._attn_implementation = "flash_attention_2"
    monkeypatch.setattr(
        transformers.utils,
        "is_flash_attn_2_available",
        lambda: False,
    )
    monkeypatch.setattr(
        loader.qd,
        "detect_quant_scheme",
        lambda *args, **kwargs: loader.qd.QuantDetection(loader.qd.QuantScheme.NONE),
    )

    loader.load_model("local/model", skip_snapshot=True)

    assert loader_boundary.config._attn_implementation == "eager"


def test_broken_flash_attention_probe_falls_back_to_eager(
    loader_boundary, monkeypatch,
):
    loader_boundary.config._attn_implementation = "flash_attention_2"
    real_import = builtins.__import__

    def rejecting_import(name, globals=None, locals=None, fromlist=(), level=0):
        if (
            name == "transformers.utils"
            and "is_flash_attn_2_available" in tuple(fromlist or ())
        ):
            raise RuntimeError("flash-attention availability probe failed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", rejecting_import)
    loader.load_model("local/model", skip_snapshot=True)

    assert loader_boundary.config._attn_implementation == "eager"


def test_available_flash_attention_preserves_requested_implementation(
    loader_boundary, monkeypatch,
):
    import transformers.utils

    loader_boundary.config._attn_implementation = "flash_attention_2"
    monkeypatch.setattr(
        transformers.utils,
        "is_flash_attn_2_available",
        lambda: True,
    )

    loader.load_model("local/model", skip_snapshot=True)

    assert loader_boundary.config._attn_implementation == "flash_attention_2"


def test_multimodal_unwrap_generation_cache_and_legacy_ties(
    loader_boundary, monkeypatch,
):
    class FakeLanguageModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.config = _config(tie_word_embeddings=False)
            self._tied_weights_keys = ["lm_head.weight"]
            self.last_cache_position = None

        def prepare_inputs_for_generation(
            self, input_ids, *args, cache_position=None, **kwargs,
        ):
            self.last_cache_position = cache_position
            return {"input_ids": input_ids, "cache_position": cache_position}

    class MultimodalWrapper(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.language_model = FakeLanguageModel()

        def forward(self, input_ids, pixel_values):
            return input_ids, pixel_values

    wrapper = MultimodalWrapper()
    loader_boundary.model_class.from_pretrained.return_value = wrapper
    monkeypatch.setattr(loader, "PreTrainedModel", FakeLanguageModel)
    monkeypatch.setattr(
        loader.qd,
        "detect_quant_scheme",
        lambda *args, **kwargs: loader.qd.QuantDetection(loader.qd.QuantScheme.NONE),
    )

    handle = loader.load_model("local/model", skip_snapshot=True)

    assert handle.model is wrapper.language_model
    assert handle.model._tied_weights_keys == {}
    input_ids = torch.ones(1, 2, dtype=torch.long)

    class Cache:
        @staticmethod
        def get_seq_length():
            return 4

    prepared = handle.model.prepare_inputs_for_generation(
        input_ids, past_key_values=Cache(),
    )
    assert prepared["cache_position"].tolist() == [4, 5]

    legacy_cache = ((torch.zeros(1, 1, 3, 1),),)
    prepared = handle.model.prepare_inputs_for_generation(
        input_ids, past_key_values=legacy_cache,
    )
    assert prepared["cache_position"].tolist() == [3, 4]

    prepared = handle.model.prepare_inputs_for_generation(
        input_ids, past_key_values=object(),
    )
    assert prepared["cache_position"].tolist() == [0, 1]

    prepared = handle.model.prepare_inputs_for_generation(input_ids)
    assert prepared["cache_position"].tolist() == [0, 1]

    explicit = torch.tensor([7, 8])
    prepared = handle.model.prepare_inputs_for_generation(
        input_ids, cache_position=explicit,
    )
    assert prepared["cache_position"] is explicit


def test_multimodal_signature_probe_failure_preserves_wrapper(
    loader_boundary, monkeypatch,
):
    class FakeLanguageModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.config = _config()

    class WrapperWithUninspectableForward(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.language_model = FakeLanguageModel()
            self.forward = object()

    wrapper = WrapperWithUninspectableForward()
    loader_boundary.model_class.from_pretrained.return_value = wrapper
    monkeypatch.setattr(loader, "PreTrainedModel", FakeLanguageModel)

    handle = loader.load_model("local/model", skip_snapshot=True)

    assert handle.model is wrapper


def test_hf_token_is_forwarded_without_logging_value(loader_boundary, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "secret-token")
    loader.load_model("x", skip_snapshot=True)
    assert loader.AutoConfig.from_pretrained.call_args.kwargs["token"] == "secret-token"
    assert loader_boundary.model_class.from_pretrained.call_args.kwargs["token"] == "secret-token"
    assert loader.AutoTokenizer.from_pretrained.call_args.kwargs["token"] == "secret-token"


def test_device_and_dtype_failures_precede_provider_access(loader_boundary, monkeypatch):
    provider = Mock(side_effect=AssertionError("provider should not be called"))
    monkeypatch.setattr(loader.AutoConfig, "from_pretrained", provider)
    monkeypatch.setattr(loader.dev, "get_device", Mock(side_effect=RuntimeError("CUDA unavailable")))
    with pytest.raises(RuntimeError, match="CUDA unavailable"):
        loader.load_model("x", device="cuda")
    provider.assert_not_called()

    monkeypatch.setattr(loader.dev, "get_device", lambda _preference="auto": "mps")
    monkeypatch.setattr(loader.dev, "supports_bfloat16", lambda _device=None: False)
    with pytest.raises(RuntimeError, match="bfloat16 is not supported on 'mps'"):
        loader.load_model("x", device="mps", dtype="bfloat16")
    provider.assert_not_called()


def test_config_permission_error_retries_in_temp_cache(loader_boundary, monkeypatch, tmp_path):
    monkeypatch.setattr(loader.tempfile, "gettempdir", lambda: str(tmp_path))
    loader.AutoConfig.from_pretrained.side_effect = [PermissionError("cache"), loader_boundary.config]
    loader.load_model("x", skip_snapshot=True)
    assert loader.AutoConfig.from_pretrained.call_count == 2
    assert loader.AutoConfig.from_pretrained.call_args.kwargs["cache_dir"] == str(tmp_path / "hf_home" / "hub")
    assert (tmp_path / "hf_home" / "hub").is_dir()


@pytest.mark.parametrize("message", ["Gated repo denied", "Access to model is restricted"])
def test_config_gated_repo_failure_is_actionable(loader_boundary, monkeypatch, message):
    loader.AutoConfig.from_pretrained.side_effect = OSError(message)
    with pytest.raises(RuntimeError, match=r"(?s)Accept the license.*HF_TOKEN"):
        loader.load_model("owner/gated", skip_snapshot=True)


def test_non_gated_config_oserror_is_preserved(loader_boundary):
    loader.AutoConfig.from_pretrained.side_effect = OSError("offline cache miss")
    with pytest.raises(OSError, match="offline cache miss"):
        loader.load_model("x", local_files_only=True)


@pytest.mark.parametrize("exc", [ValueError("unknown"), KeyError("model_type")])
def test_malformed_or_unknown_config_has_stable_guidance(loader_boundary, exc):
    loader.AutoConfig.from_pretrained.side_effect = exc
    with pytest.raises(RuntimeError, match=r"(?s)not recognized by transformers.*trust_remote_code=True"):
        loader.load_model("new/model")


def test_task_model_selection_and_gemma_contract(monkeypatch):
    causal = object()
    classification = object()
    image_text = object()
    monkeypatch.setitem(loader.TASK_MODEL_MAP, "causal_lm", causal)
    monkeypatch.setitem(loader.TASK_MODEL_MAP, "classification", classification)
    monkeypatch.setattr(loader, "AutoModelForImageTextToText", image_text)
    assert loader._select_model_class("causal_lm", _config()) is causal
    assert loader._select_model_class("classification", _config()) is classification
    assert loader._select_model_class("causal_lm", _config(model_type="gemma4")) is image_text
    assert loader._select_model_class(
        "causal_lm",
        _config(model_type="unknown", architectures=["Gemma4ForConditionalGeneration"]),
    ) is image_text
    monkeypatch.setattr(loader, "AutoModelForImageTextToText", None)
    with pytest.raises(RuntimeError, match="Upgrade transformers"):
        loader._select_model_class("causal_lm", _config(model_type="gemma4"))
    with pytest.raises(ValueError, match="Unknown task"):
        loader._select_model_class("embedding", _config())


def test_mistral3_load_uses_image_text_class_and_keeps_remote_code_disabled(
    loader_boundary, monkeypatch,
):
    loader_boundary.config.model_type = "mistral3"
    loader_boundary.config.architectures = ["Mistral3ForConditionalGeneration"]
    image_text = SimpleNamespace(
        from_pretrained=Mock(return_value=loader_boundary.model),
    )
    monkeypatch.setattr(loader, "AutoModelForImageTextToText", image_text)

    handle = loader.load_model("local/mistral3", skip_snapshot=True)

    assert handle.config is loader_boundary.config
    assert handle.architecture == "mistral3"
    assert loader.AutoConfig.from_pretrained.call_args.kwargs["trust_remote_code"] is False
    assert image_text.from_pretrained.call_args.kwargs["trust_remote_code"] is False
    assert loader.AutoTokenizer.from_pretrained.call_args.kwargs["trust_remote_code"] is False
    loader_boundary.model_class.from_pretrained.assert_not_called()


def test_qwen35_load_is_explicit_text_only_sdpa(
    loader_boundary, caplog, monkeypatch,
):
    caplog.set_level("INFO")
    loader_boundary.config.model_type = "qwen3_5"
    loader_boundary.config.architectures = ["Qwen3_5ForConditionalGeneration"]
    monkeypatch.setattr(loader, "_require_qwen_hybrid_kernels", Mock())
    monkeypatch.setattr(loader, "_qwen_single_device", Mock(return_value=2))

    handle = loader.load_model("Qwen/Qwen3.8-27B", skip_snapshot=True)

    assert handle.architecture == "qwen3_5"
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert kwargs["attn_implementation"] == "sdpa"
    assert kwargs["device_map"] == {"": 2}
    assert "device_map" not in kwargs or kwargs["device_map"] != "auto"
    assert "text-only derivative" in caplog.text


def test_qwen35_missing_fast_kernels_fails_before_weight_load(
    loader_boundary, monkeypatch,
):
    loader_boundary.config.model_type = "qwen3_5"
    monkeypatch.setattr(
        loader,
        "_require_qwen_hybrid_kernels",
        Mock(side_effect=RuntimeError("missing or incompatible: causal-conv1d")),
    )

    with pytest.raises(RuntimeError, match="causal-conv1d"):
        loader.load_model("Qwen/Qwen3.8-27B", skip_snapshot=True)

    loader_boundary.model_class.from_pretrained.assert_not_called()


def test_qwen_kernel_probe_reports_each_incompatible_extension(monkeypatch):
    def import_module(name):
        if name == "fla":
            raise ImportError("missing")
        raise OSError("ABI mismatch")

    monkeypatch.setattr(loader.importlib, "import_module", import_module)

    with pytest.raises(RuntimeError, match="flash-linear-attention, causal-conv1d"):
        loader._require_qwen_hybrid_kernels()


def test_qwen_single_device_uses_per_device_free_memory(monkeypatch):
    monkeypatch.setattr(loader.dev, "is_cuda", lambda: True)
    monkeypatch.setattr(loader.torch.cuda, "device_count", lambda: 3)
    free = [40, 76, 72]
    monkeypatch.setattr(
        loader.torch.cuda,
        "mem_get_info",
        lambda index: (free[index] * 1024 ** 3, 80 * 1024 ** 3),
    )

    assert loader._qwen_single_device(54.0, None) == 1
    assert loader._qwen_single_device(216.0, "4bit") == 1


def test_qwen_saved_text_derivative_reuses_single_device_runtime(monkeypatch):
    config = _config(model_type="qwen3_5_text")
    monkeypatch.setattr(loader, "_require_qwen_hybrid_kernels", Mock())
    monkeypatch.setattr(loader, "_estimate_model_memory_gb", Mock(return_value=54.0))
    monkeypatch.setattr(loader, "_qwen_single_device", Mock(return_value=2))

    assert loader.qwen_hybrid_runtime_overrides(
        config,
        torch.bfloat16,
    ) == {
        "attn_implementation": "sdpa",
        "device_map": {"": 2},
    }


def test_model_handle_metadata_snapshot_restore_summary_and_cleanup(tmp_path):
    model = _model()
    nested = SimpleNamespace(
        num_hidden_layers=3,
        num_attention_heads=6,
        hidden_size=12,
        intermediate_size=24,
    )
    config = _config(
        num_hidden_layers=0,
        num_attention_heads=0,
        hidden_size=0,
        intermediate_size=0,
        text_config=nested,
    )
    offload = tmp_path / "offload"
    offload.mkdir()
    (offload / "weight").write_text("x")
    handle = loader.ModelHandle(
        model,
        SimpleNamespace(),
        config,
        "x",
        "causal_lm",
        _offload_dir=str(offload),
        _owns_offload_dir=True,
    )
    assert (handle.num_layers, handle.num_heads, handle.hidden_size, handle.intermediate_size) == (3, 6, 12, 24)
    with pytest.raises(RuntimeError, match="call .snapshot"):
        handle.restore()
    handle.snapshot()
    model.load_state_dict.return_value = SimpleNamespace(missing_keys=[], unexpected_keys=[])
    handle.restore()
    model.load_state_dict.assert_called_once()
    restored = model.load_state_dict.call_args.args[0]
    assert torch.equal(restored["weight"], torch.ones(2))
    assert model.load_state_dict.call_args.kwargs == {"strict": False}
    assert handle.summary() == {
        "model_name": "x",
        "architecture": "gpt2",
        "task": "causal_lm",
        "num_layers": 3,
        "num_heads": 6,
        "hidden_size": 12,
        "intermediate_size": 24,
        "total_params": 5,
    }
    handle.cleanup()
    assert not offload.exists()
    assert handle._offload_dir is None


def test_model_handle_restore_tolerates_quantization_metadata():
    model = _model()
    handle = loader.ModelHandle(model, SimpleNamespace(), _config(), "x", "causal_lm")
    handle._original_state = {"weight": torch.ones(2)}
    model.load_state_dict.return_value = SimpleNamespace(
        missing_keys=["layer.weight.absmax"],
        unexpected_keys=["layer.weight.bitsandbytes__nf4"],
    )
    handle.restore()


@pytest.mark.parametrize(
    ("missing", "unexpected", "message"),
    [
        (["layer.bias"], [], "missing keys: \\['layer.bias'\\]"),
        ([], ["layer.other_weight"], "unexpected keys: \\['layer.other_weight'\\]"),
        (
            ["layer.bias"],
            ["layer.other_weight"],
            r"missing keys: \['layer.bias'\].*unexpected keys: \['layer.other_weight'\]",
        ),
    ],
)
def test_model_handle_restore_rejects_parameter_mismatches(missing, unexpected, message):
    model = _model()
    handle = loader.ModelHandle(model, SimpleNamespace(), _config(), "x", "causal_lm")
    handle._original_state = {"weight": torch.ones(2)}
    model.load_state_dict.return_value = SimpleNamespace(
        missing_keys=missing,
        unexpected_keys=unexpected,
    )
    with pytest.raises(RuntimeError, match=message):
        handle.restore()


def test_model_handle_restore_preserves_loader_shape_failures():
    model = _model()
    handle = loader.ModelHandle(model, SimpleNamespace(), _config(), "x", "causal_lm")
    handle._original_state = {"weight": torch.ones(2)}
    model.load_state_dict.side_effect = RuntimeError("size mismatch for weight")
    with pytest.raises(RuntimeError, match="size mismatch for weight"):
        handle.restore()


def test_model_memory_estimation_handles_dense_moe_nested_and_unknown():
    dense = loader._estimate_model_memory_gb(_config(), torch.float32)
    moe = loader._estimate_model_memory_gb(_config(num_local_experts=4), torch.float32)
    assert dense > 0
    assert moe > dense
    nested = _config(hidden_size=0, num_hidden_layers=0, intermediate_size=0, vocab_size=0)
    nested.text_config = _config(hidden_size=8, num_hidden_layers=2, intermediate_size=16, vocab_size=32)
    assert loader._estimate_model_memory_gb(nested, torch.float16) > 0
    assert loader._estimate_model_memory_gb(_config(hidden_size=0), torch.float16) == 0


@pytest.mark.parametrize("quantization", ["4bit", "8bit"])
def test_quantization_rejects_non_cuda_instead_of_silent_degradation(loader_boundary, quantization):
    with pytest.raises(RuntimeError, match="requires an available NVIDIA CUDA device"):
        loader.load_model("x", quantization=quantization)
    loader_boundary.model_class.from_pretrained.assert_not_called()


def test_quantization_requires_bitsandbytes(loader_boundary, monkeypatch):
    monkeypatch.setattr(loader.dev, "get_device", lambda _preference="auto": "cuda")
    monkeypatch.setattr(loader.dev, "supports_bitsandbytes", lambda _device=None: True)
    real_import = builtins.__import__

    def reject_bitsandbytes(name, *args, **kwargs):
        if name == "bitsandbytes":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_bitsandbytes)
    with pytest.raises(RuntimeError, match="pip install -U bitsandbytes"):
        loader.load_model("x", quantization="4bit")


@pytest.mark.parametrize("quantization", ["4bit", "8bit"])
def test_cuda_quantization_builds_explicit_config(loader_boundary, monkeypatch, quantization):
    made = []

    def fake_bnb(**kwargs):
        made.append(kwargs)
        return kwargs

    monkeypatch.setattr(loader.dev, "get_device", lambda _preference="auto": "cuda")
    monkeypatch.setattr(loader.dev, "supports_bitsandbytes", lambda _device=None: True)
    monkeypatch.setitem(sys.modules, "bitsandbytes", ModuleType("bitsandbytes"))
    monkeypatch.setattr("transformers.BitsAndBytesConfig", fake_bnb)
    handle = loader.load_model("x", quantization=quantization, skip_snapshot=True)
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert kwargs["device_map"] == "auto"
    assert kwargs["quantization_config"] == made[0]
    assert made[0][f"load_in_{quantization}"] is True
    assert made[0]["llm_int8_enable_fp32_cpu_offload"] is True
    handle.cleanup()


def test_native_quantization_wins_and_skips_dtype(loader_boundary):
    loader_boundary.config.quantization_config = SimpleNamespace()
    handle = loader.load_model("x", quantization="4bit", skip_snapshot=True)
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert "torch_dtype" not in kwargs
    assert kwargs["device_map"] == "auto"
    assert "quantization_config" not in kwargs
    handle.cleanup()


def test_cuda_auto_map_has_bounded_memory_and_requested_offload(loader_boundary, monkeypatch, tmp_path):
    gib = 1024**3
    monkeypatch.setattr(loader.dev, "get_device", lambda _preference="auto": "cuda")
    monkeypatch.setattr(loader.dev, "supports_device_map_auto", lambda _device=None: True)
    monkeypatch.setattr(loader.dev, "is_cuda", lambda: True)
    monkeypatch.setattr(loader.dev, "device_count", lambda: 2)
    monkeypatch.setattr(loader.dev, "_system_memory_gb", lambda: (64.0, 40.0))
    monkeypatch.setattr(
        loader.torch.cuda,
        "get_device_properties",
        lambda _index: SimpleNamespace(total_memory=20 * gib),
    )
    handle = loader.load_model("x", offload_folder=str(tmp_path), skip_snapshot=True)
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert kwargs["offload_folder"] == str(tmp_path)
    assert kwargs["max_memory"] == {0: "17408MiB", 1: "17408MiB", "cpu": "54GiB"}
    handle.cleanup()
    assert tmp_path.exists(), "cleanup must not remove an operator-owned directory"


def test_explicit_gpu_memory_utilization_overrides_default_headroom(
    loader_boundary, monkeypatch,
):
    gib = 1024**3
    monkeypatch.setattr(loader.dev, "get_device", lambda _preference="auto": "cuda")
    monkeypatch.setattr(loader.dev, "supports_device_map_auto", lambda _device=None: True)
    monkeypatch.setattr(loader.dev, "is_cuda", lambda: True)
    monkeypatch.setattr(loader.dev, "device_count", lambda: 1)
    monkeypatch.setattr(loader.dev, "_system_memory_gb", lambda: (64.0, 40.0))
    monkeypatch.setattr(
        loader.torch.cuda,
        "get_device_properties",
        lambda _index: SimpleNamespace(total_memory=20 * gib),
    )
    handle = loader.load_model(
        "x", gpu_memory_utilization=0.95, skip_snapshot=True,
    )
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert kwargs["max_memory"] == {0: "19456MiB", "cpu": "54GiB"}
    handle.cleanup()


@pytest.mark.parametrize("device", ["cpu", "mps"])
def test_gpu_memory_utilization_is_safe_when_accelerate_auto_map_is_unavailable(
    loader_boundary, monkeypatch, device,
):
    monkeypatch.setattr(loader.dev, "get_device", lambda _preference="auto": device)
    handle = loader.load_model(
        "x", device=device, gpu_memory_utilization=0.95, skip_snapshot=True,
    )
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert "device_map" not in kwargs
    assert "max_memory" not in kwargs
    loader_boundary.model.to.assert_called_once_with(device)
    handle.cleanup()


def _enable_cuda_quantization(monkeypatch, estimate_gb: float) -> None:
    gib = 1024**3
    monkeypatch.setattr(loader, "_estimate_model_memory_gb", lambda *_args: estimate_gb)
    monkeypatch.setattr(loader.dev, "get_device", lambda _preference="auto": "cuda")
    monkeypatch.setattr(loader.dev, "supports_bitsandbytes", lambda _device=None: True)
    monkeypatch.setattr(loader.dev, "supports_device_map_auto", lambda _device=None: True)
    monkeypatch.setattr(loader.dev, "get_total_free_gb", lambda: 16.0)
    monkeypatch.setattr(loader.dev, "is_cuda", lambda: True)
    monkeypatch.setattr(loader.dev, "device_count", lambda: 1)
    monkeypatch.setattr(loader.dev, "_system_memory_gb", lambda: (64.0, 40.0))
    monkeypatch.setattr(
        loader.torch.cuda,
        "get_device_properties",
        lambda _index: SimpleNamespace(total_memory=16 * gib),
    )
    monkeypatch.setitem(sys.modules, "bitsandbytes", ModuleType("bitsandbytes"))
    monkeypatch.setattr("transformers.BitsAndBytesConfig", lambda **kwargs: kwargs)


@pytest.mark.parametrize(
    ("quantization", "estimate_gb", "expects_budget"),
    [
        ("4bit", 40.0, False),
        ("4bit", 48.0, True),
        ("8bit", 20.0, False),
        ("8bit", 24.0, True),
    ],
)
def test_quantized_single_gpu_memory_budget_uses_effective_weight_size(
    loader_boundary, monkeypatch, quantization, estimate_gb, expects_budget,
):
    _enable_cuda_quantization(monkeypatch, estimate_gb)
    handle = loader.load_model("x", quantization=quantization, skip_snapshot=True)
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert ("max_memory" in kwargs) is expects_budget
    if expects_budget:
        assert kwargs["max_memory"] == {0: "13926MiB", "cpu": "54GiB"}
    handle.cleanup()


def test_explicit_gpu_budget_overrides_quantized_fit_shortcut(loader_boundary, monkeypatch):
    _enable_cuda_quantization(monkeypatch, estimate_gb=40.0)
    handle = loader.load_model(
        "x",
        quantization="4bit",
        gpu_memory_utilization=0.5,
        skip_snapshot=True,
    )
    kwargs = loader_boundary.model_class.from_pretrained.call_args.kwargs
    assert kwargs["max_memory"] == {0: "8192MiB", "cpu": "54GiB"}
    handle.cleanup()


@pytest.mark.parametrize(
    ("quantization", "estimate_gb", "snapshots"),
    [("4bit", 16.0, 1), ("4bit", 40.0, 0), ("8bit", 8.0, 1), ("8bit", 20.0, 0)],
)
def test_quantized_snapshot_policy_uses_effective_weight_size(
    loader_boundary, monkeypatch, quantization, estimate_gb, snapshots,
):
    _enable_cuda_quantization(monkeypatch, estimate_gb)
    snapshot = Mock()
    monkeypatch.setattr(loader.ModelHandle, "snapshot", snapshot)
    handle = loader.load_model("x", quantization=quantization)
    assert snapshot.call_count == snapshots
    handle.cleanup()


def test_model_permission_error_retries_and_explicit_device_moves(loader_boundary, monkeypatch, tmp_path):
    monkeypatch.setattr(loader.tempfile, "gettempdir", lambda: str(tmp_path))
    loader_boundary.model_class.from_pretrained.side_effect = [PermissionError("cache"), loader_boundary.model]
    loader.load_model("x", device="cpu", skip_snapshot=True)
    assert loader_boundary.model_class.from_pretrained.call_count == 2
    assert loader_boundary.model_class.from_pretrained.call_args.kwargs["cache_dir"].endswith("hf_home/hub")
    loader_boundary.model.to.assert_called_once_with("cpu")


def test_model_gated_and_unknown_architecture_errors_are_actionable(loader_boundary):
    loader_boundary.model_class.from_pretrained.side_effect = OSError("gated repo")
    with pytest.raises(RuntimeError, match="Accept the license"):
        loader.load_model("owner/gated")

    loader_boundary.model_class.from_pretrained.side_effect = ValueError("does not recognize this architecture")
    with pytest.raises(RuntimeError, match="pip install --upgrade transformers"):
        loader.load_model("new/model")

    loader_boundary.model_class.from_pretrained.side_effect = KeyError("unrelated")
    with pytest.raises(KeyError, match="unrelated"):
        loader.load_model("x")


def test_tokenizer_permission_retry_and_forced_snapshot(loader_boundary, monkeypatch, tmp_path):
    monkeypatch.setattr(loader.tempfile, "gettempdir", lambda: str(tmp_path))
    loader.AutoTokenizer.from_pretrained.side_effect = [PermissionError("cache"), loader_boundary.tokenizer]
    handle = loader.load_model("x", skip_snapshot=False)
    assert loader.AutoTokenizer.from_pretrained.call_count == 2
    assert loader.AutoTokenizer.from_pretrained.call_args.kwargs["cache_dir"].endswith("hf_home/hub")
    assert handle._original_state is not None


@pytest.mark.parametrize(
    ("native", "initial_free", "remaining_free", "snapshots"),
    [
        (True, 10.0, 3.0, 0),
        (True, 10.0, 6.0, 1),
        (False, 0.000001, 0.0, 0),
        (False, 0.0, 0.0, 1),
    ],
)
def test_automatic_snapshot_memory_policy(
    loader_boundary, monkeypatch, native, initial_free, remaining_free, snapshots,
):
    if native:
        loader_boundary.config.quantization_config = SimpleNamespace()
    monkeypatch.setattr(loader.dev, "get_total_free_gb", Mock(side_effect=[initial_free, remaining_free]))
    snapshot = Mock()
    monkeypatch.setattr(loader.ModelHandle, "snapshot", snapshot)
    handle = loader.load_model("x")
    assert snapshot.call_count == snapshots
    handle.cleanup()


def test_classification_load_sets_requested_label_count(loader_boundary):
    handle = loader.load_model(
        "x",
        task="classification",
        num_labels=7,
        skip_snapshot=True,
    )
    assert loader_boundary.config.num_labels == 7
    assert loader_boundary.model_class.from_pretrained.call_args.kwargs["config"] is loader_boundary.config
    handle.cleanup()


def test_non_gated_model_oserror_is_preserved(loader_boundary):
    loader_boundary.model_class.from_pretrained.side_effect = OSError("offline weight cache miss")
    with pytest.raises(OSError, match="offline weight cache miss"):
        loader.load_model("x", local_files_only=True)


def test_cached_path_compatibility_resolves_local_hub_and_fallback(monkeypatch, tmp_path):
    local = tmp_path / "weights.bin"
    local.write_bytes(b"weights")
    assert loader._cached_path_shim(local) == str(local)

    download = Mock(return_value="/cache/config.json")
    monkeypatch.setattr("huggingface_hub.hf_hub_download", download)
    assert loader._cached_path_shim("owner/model/config.json", cache_dir="/cache") == "/cache/config.json"
    download.assert_called_once_with(
        repo_id="owner/model",
        filename="config.json",
        cache_dir="/cache",
    )

    download.side_effect = RuntimeError("network unavailable")
    assert loader._cached_path_shim("owner/model/config.json") == "owner/model/config.json"
    download.reset_mock(side_effect=True)
    assert loader._cached_path_shim("single-name") == "single-name"
    download.assert_not_called()


def test_working_or_temp_dir_compatibility_preserves_and_cleans_paths(tmp_path):
    with loader._working_or_temp_dir(tmp_path) as selected:
        assert selected == tmp_path

    with loader._working_or_temp_dir() as generated:
        generated_path = Path(generated)
        assert generated_path.is_dir()
    assert not generated_path.exists()


def test_deferred_transformers_shims_are_additive_and_idempotent(monkeypatch):
    fake_transformers = SimpleNamespace(_objects={})
    monkeypatch.setitem(loader._sys.modules, "transformers", fake_transformers)
    monkeypatch.setattr(loader, "_DEFERRED_SHIMS_APPLIED", False)
    loader._apply_deferred_shims()

    assert fake_transformers.LogitsWarper is fake_transformers._objects["LogitsWarper"]
    assert fake_transformers.is_tf_available() is False
    assert fake_transformers.is_flax_available() is False
    assert fake_transformers.is_safetensors_available() is True
    before = dict(fake_transformers.__dict__)
    loader._apply_deferred_shims()
    assert fake_transformers.__dict__ == before


def test_deferred_transformers_shims_tolerate_missing_module(monkeypatch):
    monkeypatch.delitem(loader._sys.modules, "transformers", raising=False)
    monkeypatch.setattr(loader, "_DEFERRED_SHIMS_APPLIED", False)
    loader._apply_deferred_shims()
    assert loader._DEFERRED_SHIMS_APPLIED is True


def test_deferred_transformers_shims_isolate_lazy_module_failures(monkeypatch):
    class BrokenLazyModule:
        def __getattribute__(self, name):
            if name in {"LogitsWarper", "is_tf_available"}:
                raise RuntimeError("lazy import failed")
            return object.__getattribute__(self, name)

    monkeypatch.setitem(loader._sys.modules, "transformers", BrokenLazyModule())
    monkeypatch.setattr(loader, "_DEFERRED_SHIMS_APPLIED", False)
    loader._apply_deferred_shims()
    assert loader._DEFERRED_SHIMS_APPLIED is True


def test_image_text_input_compatibility_shim_preserves_argument_order():
    images = object()
    text = object()
    assert loader._validate_images_text_input_order(
        images=images,
        text=text,
        ignored="compatibility",
    ) == (images, text)


def test_cleanup_is_best_effort_when_directory_removal_fails(monkeypatch, tmp_path):
    offload = tmp_path / "offload"
    offload.mkdir()
    handle = loader.ModelHandle(
        _model(),
        SimpleNamespace(),
        _config(),
        "x",
        "causal_lm",
        _offload_dir=str(offload),
        _owns_offload_dir=True,
    )
    monkeypatch.setattr("shutil.rmtree", Mock(side_effect=OSError("busy")))
    handle.cleanup()
    assert handle._offload_dir is None
    assert handle._owns_offload_dir is False
    assert offload.exists()
