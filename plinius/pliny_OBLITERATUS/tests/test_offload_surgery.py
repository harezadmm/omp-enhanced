"""CPU-only contracts for transactional Accelerate offload surgery."""

from __future__ import annotations

from collections.abc import MutableMapping

import pytest
import torch
import torch.nn as nn
from accelerate.big_modeling import disk_offload
from accelerate.hooks import (
    AlignDevicesHook,
    ModelHook,
    SequentialHook,
    add_hook_to_module,
)
from accelerate.utils.modeling import get_state_dict_offloaded_model

import obliteratus.models.offload_surgery as offload_surgery
from obliteratus.abliterate import _MAX_NORM_RATIO, AbliterationPipeline
from obliteratus.models.offload_surgery import (
    OffloadSurgeryError,
    UnsupportedOffloadLayoutError,
    UnsupportedOffloadedQuantizationError,
    logical_module_device,
    resolve_logical_parameter,
    validate_offloaded_parameters,
)


def _direct_offload(module: nn.Module) -> AlignDevicesHook:
    hook = AlignDevicesHook(execution_device="cpu", offload=True)
    add_hook_to_module(module, hook)
    return hook


def test_direct_align_hook_updates_backing_weight_and_preserves_meta_state():
    module = nn.Linear(3, 2, bias=False)
    original = module.weight.detach().clone()
    hook = _direct_offload(module)
    parameter_identity = id(module.weight)

    transaction = resolve_logical_parameter(module)
    transaction.commit(transaction.tensor + 2)

    assert module.weight.device.type == "meta"
    assert id(module.weight) == parameter_identity
    torch.testing.assert_close(hook.weights_map["weight"], original + 2)


def test_sequential_hook_finds_nested_align_devices_hook():
    module = nn.Linear(3, 2, bias=False)
    original = module.weight.detach().clone()
    align = AlignDevicesHook(execution_device="cpu", offload=True)
    add_hook_to_module(module, SequentialHook(ModelHook(), align))

    transaction = resolve_logical_parameter(module)
    transaction.commit(transaction.tensor - 1)

    assert module.weight.device.type == "meta"
    torch.testing.assert_close(align.weights_map["weight"], original - 1)


def test_parent_prefixed_weight_map_resolves_nested_parameter():
    block = nn.Module()
    block.self_attn = nn.Module()
    block.self_attn.o_proj = nn.Linear(3, 2, bias=False)
    original = block.self_attn.o_proj.weight.detach().clone()
    hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        place_submodules=True,
    )
    add_hook_to_module(block, hook)

    transaction = resolve_logical_parameter(
        block.self_attn.o_proj,
        search_roots=(block,),
    )
    assert transaction.backing_key == "self_attn.o_proj.weight"
    transaction.commit(transaction.tensor * 0.5)

    assert block.self_attn.o_proj.weight.device.type == "meta"
    torch.testing.assert_close(
        hook.weights_map["self_attn.o_proj.weight"],
        original * 0.5,
    )


def test_disk_backed_prefixed_loader_uses_updated_authoritative_value(tmp_path):
    model = nn.Sequential(nn.Linear(3, 2, bias=False))
    original = model[0].weight.detach().clone()
    disk_offload(model, tmp_path, execution_device=torch.device("cpu"))

    transaction = resolve_logical_parameter(model[0], search_roots=(model,))
    transaction.commit(transaction.tensor + 3)

    assert model[0].weight.device.type == "meta"
    hook = model[0]._hf_hook
    torch.testing.assert_close(hook.weights_map["weight"], original + 3)
    gathered = get_state_dict_offloaded_model(model)
    assert all(tensor.device.type != "meta" for tensor in gathered.values())
    torch.testing.assert_close(gathered["0.weight"], original + 3)


def test_save_reload_observes_surgery_instead_of_stale_backing_weight():
    model = nn.Sequential(nn.Linear(3, 2, bias=False))
    original = model[0].weight.detach().clone()
    _direct_offload(model[0])

    transaction = resolve_logical_parameter(model[0], search_roots=(model,))
    transaction.commit(transaction.tensor - 4)
    state_dict = get_state_dict_offloaded_model(model)

    reloaded = nn.Sequential(nn.Linear(3, 2, bias=False))
    reloaded.load_state_dict(state_dict)
    torch.testing.assert_close(reloaded[0].weight, original - 4)
    assert reloaded[0].weight.device.type == "cpu"


def test_tied_backing_values_retain_identity_and_consistent_values():
    block = nn.Module()
    block.first = nn.Linear(3, 3, bias=False)
    block.second = nn.Linear(3, 3, bias=False)
    shared = block.first.weight.detach().clone()
    shared_meta = nn.Parameter(torch.empty_like(shared, device="meta"))
    block.first.weight = shared_meta
    block.second.weight = shared_meta
    hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        weights_map={"first.weight": shared, "second.weight": shared},
        place_submodules=True,
    )
    block._hf_hook = hook
    live_identity = id(block.first.weight)

    transaction = resolve_logical_parameter(block.first, search_roots=(block,))
    transaction.commit(transaction.tensor + 1)

    first = hook.weights_map["first.weight"]
    second = hook.weights_map["second.weight"]
    assert first is second
    torch.testing.assert_close(first, shared + 1)
    assert block.first.weight is block.second.weight
    assert id(block.first.weight) == live_identity


class _FailOnceAliasMap(MutableMapping[str, torch.Tensor]):
    def __init__(self, shared: torch.Tensor):
        self.values = {"first.weight": shared, "second.weight": shared}
        self.failed = False

    def __getitem__(self, key: str) -> torch.Tensor:
        return self.values[key]

    def __setitem__(self, key: str, value: torch.Tensor) -> None:
        if key == "second.weight" and not self.failed:
            self.failed = True
            raise OSError("simulated backing-store failure")
        self.values[key] = value

    def __delitem__(self, key: str) -> None:
        del self.values[key]

    def __iter__(self):
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)


def test_commit_failure_rolls_back_all_backing_aliases_and_leaves_meta_state():
    block = nn.Module()
    block.first = nn.Linear(3, 3, bias=False)
    original = block.first.weight.detach().clone()
    block.first.weight = nn.Parameter(torch.empty_like(original, device="meta"))
    backing = _FailOnceAliasMap(original)
    block._hf_hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        weights_map=backing,
        place_submodules=True,
    )

    transaction = resolve_logical_parameter(block.first, search_roots=(block,))
    with pytest.raises(OffloadSurgeryError, match="rolled back"):
        transaction.commit(transaction.tensor + 5)

    torch.testing.assert_close(backing["first.weight"], original)
    torch.testing.assert_close(backing["second.weight"], original)
    assert block.first.weight.device.type == "meta"


def test_quantized_offloaded_weight_fails_before_any_mutation():
    module = nn.Linear(3, 2, bias=False, device="meta")
    backing = {"weight": torch.ones(2, 3, dtype=torch.uint8)}
    module._hf_hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        weights_map=backing,
    )

    with pytest.raises(UnsupportedOffloadedQuantizationError):
        resolve_logical_parameter(module)

    assert module.weight.device.type == "meta"
    assert backing["weight"].dtype == torch.uint8
    assert torch.equal(backing["weight"], torch.ones(2, 3, dtype=torch.uint8))


def test_read_only_unknown_mapping_fails_during_resolution():
    module = nn.Linear(3, 2, bias=False, device="meta")

    class MappingOnly:
        def __getitem__(self, key):
            return torch.ones(2, 3)

        def __iter__(self):
            return iter(("weight",))

        def __len__(self):
            return 1

    # Registering through Mapping is deliberately avoided: this object models
    # a future wrapper with read access but no supported write contract.
    hook = AlignDevicesHook(execution_device="cpu", offload=True)
    hook.weights_map = MappingOnly()
    module._hf_hook = hook

    with pytest.raises(UnsupportedOffloadLayoutError, match="read-only"):
        resolve_logical_parameter(module)


def test_validation_resolves_all_meta_parameters_before_surgery():
    block = nn.Module()
    block.proj = nn.Linear(3, 2, bias=False)
    hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        place_submodules=True,
    )
    add_hook_to_module(block, hook)

    validate_offloaded_parameters(block)

    hook.weights_map = {}
    with pytest.raises(UnsupportedOffloadLayoutError, match="attempted keys"):
        validate_offloaded_parameters(block)


def test_advanced_projection_updates_offloaded_logical_weight():
    module = nn.Module()
    module.proj = nn.Linear(3, 2, bias=False)
    original = module.proj.weight.detach().clone()
    hook = _direct_offload(module.proj)
    direction = torch.tensor([[1.0], [0.0], [0.0]])

    count = AbliterationPipeline._project_out_advanced(
        module,
        direction,
        ["proj"],
    )

    assert count == 1
    assert module.proj.weight.device.type == "meta"
    expected = original.clone()
    expected[:, 0] = 0
    torch.testing.assert_close(hook.weights_map["weight"], expected)


def test_advanced_projection_resolves_all_candidates_before_mutation():
    block = nn.Module()
    block.first = nn.Linear(3, 2, bias=False)
    first_original = block.first.weight.detach().clone()
    first_hook = _direct_offload(block.first)
    block.second = nn.Linear(3, 2, bias=False, device="meta")
    block.second._hf_hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        weights_map={"weight": torch.ones(2, 3, dtype=torch.uint8)},
    )

    with pytest.raises(UnsupportedOffloadedQuantizationError):
        AbliterationPipeline._project_out_advanced(
            block,
            torch.tensor([[1.0], [0.0], [0.0]]),
            ["first", "second"],
        )

    torch.testing.assert_close(first_hook.weights_map["weight"], first_original)
    assert block.first.weight.device.type == "meta"


def test_logical_module_device_uses_authoritative_backing_device():
    module = nn.Linear(3, 2, bias=False)
    _direct_offload(module)

    assert logical_module_device(module) == torch.device("cpu")


def test_unknown_accelerate_major_version_fails_closed(monkeypatch):
    module = nn.Linear(3, 2, bias=False)
    original = module.weight.detach().clone()
    hook = _direct_offload(module)
    monkeypatch.setattr(offload_surgery, "version", lambda _name: "2.0.0")

    with pytest.raises(UnsupportedOffloadLayoutError, match="outside the tested"):
        resolve_logical_parameter(module)

    assert module.weight.device.type == "meta"
    torch.testing.assert_close(hook.weights_map["weight"], original)


def test_bias_projection_updates_parent_prefixed_backing_value():
    block = nn.Module()
    block.proj = nn.Linear(3, 3, bias=True)
    original = block.proj.bias.detach().clone()
    hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        place_submodules=True,
    )
    add_hook_to_module(block, hook)

    count = AbliterationPipeline._project_bias(
        block,
        torch.tensor([[1.0], [0.0], [0.0]]),
        ["proj"],
        offload_roots=(block,),
    )

    assert count == 1
    assert block.proj.bias.device.type == "meta"
    expected = original.clone()
    expected[0] = 0
    torch.testing.assert_close(hook.weights_map["proj.bias"], expected)


class _FailSecondParameterMap(MutableMapping[str, torch.Tensor]):
    def __init__(self, first: torch.Tensor, second: torch.Tensor):
        self.values = {"first.weight": first, "second.weight": second}
        self.failed = False

    def __getitem__(self, key: str) -> torch.Tensor:
        return self.values[key]

    def __setitem__(self, key: str, value: torch.Tensor) -> None:
        if key == "second.weight" and not self.failed:
            self.failed = True
            raise OSError("simulated second-parameter failure")
        self.values[key] = value

    def __delitem__(self, key: str) -> None:
        del self.values[key]

    def __iter__(self):
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)


def test_multi_parameter_projection_rolls_back_prior_commits():
    block = nn.Module()
    block.first = nn.Linear(3, 2, bias=False)
    block.second = nn.Linear(3, 2, bias=False)
    first = block.first.weight.detach().clone()
    second = block.second.weight.detach().clone()
    block.first.weight = nn.Parameter(torch.empty_like(first, device="meta"))
    block.second.weight = nn.Parameter(torch.empty_like(second, device="meta"))
    backing = _FailSecondParameterMap(first, second)
    block._hf_hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        weights_map=backing,
        place_submodules=True,
    )

    with pytest.raises(OffloadSurgeryError, match="rolled back"):
        AbliterationPipeline._project_out_advanced(
            block,
            torch.tensor([[1.0], [0.0], [0.0]]),
            ["first", "second"],
            offload_roots=(block,),
        )

    torch.testing.assert_close(backing["first.weight"], first)
    torch.testing.assert_close(backing["second.weight"], second)
    assert block.first.weight.device.type == "meta"
    assert block.second.weight.device.type == "meta"


class _FusedExperts(nn.Module):
    """transformers 5 fused expert container (Mixtral / GPT-OSS parameter layout)."""

    def __init__(self, experts: int = 3, hidden: int = 4, intermediate: int = 6):
        super().__init__()
        torch.manual_seed(1234)
        self.gate_up_proj = nn.Parameter(torch.randn(experts, 2 * intermediate, hidden))
        self.down_proj = nn.Parameter(torch.randn(experts, hidden, intermediate))
        self.down_proj_bias = nn.Parameter(torch.randn(experts, hidden))


def _axis_direction(axis: int = 1, hidden: int = 4) -> torch.Tensor:
    direction = torch.zeros(hidden, 1)
    direction[axis, 0] = 1.0
    return direction


def test_fused_3d_projection_updates_offloaded_expert_backing_weights():
    experts = _FusedExperts()
    original_down = experts.down_proj.detach().clone()
    original_gate_up = experts.gate_up_proj.detach().clone()
    hook = _direct_offload(experts)
    direction = _axis_direction()

    count = AbliterationPipeline._project_fused_3d(
        experts,
        direction,
        ["down_proj", "w2"],
        norm_preserve=False,
        scale=1.0,
    )

    assert count == 3
    assert experts.down_proj.device.type == "meta"
    assert experts.gate_up_proj.device.type == "meta"
    updated = hook.weights_map["down_proj"]
    expected = original_down.clone()
    expected[:, 1, :] = 0  # (experts, hidden, intermediate): hidden axis is dim 1
    torch.testing.assert_close(updated, expected)
    torch.testing.assert_close(hook.weights_map["gate_up_proj"], original_gate_up)

    count = AbliterationPipeline._project_fused_3d(
        experts,
        direction,
        ["up_proj", "gate_proj", "gate_up_proj"],
        norm_preserve=False,
        scale=1.0,
    )

    assert count == 3
    expected = original_gate_up.clone()
    expected[:, :, 1] = 0  # (experts, 2*intermediate, hidden): hidden axis is dim 2
    torch.testing.assert_close(hook.weights_map["gate_up_proj"], expected)


def test_fused_3d_projection_preserves_norm_through_offload_backing():
    experts = _FusedExperts()
    original = experts.down_proj.detach().clone()
    hook = _direct_offload(experts)

    count = AbliterationPipeline._project_fused_3d(
        experts,
        _axis_direction(),
        ["down_proj"],
        norm_preserve=True,
        scale=1.0,
    )

    assert count == 3
    updated = hook.weights_map["down_proj"]
    projected = original.clone()
    projected[:, 1, :] = 0
    for expert in range(3):
        # Norm restoration is a bounded rescale of the projected slice: it
        # recovers the original norm unless that needs more than the cap.
        assert torch.count_nonzero(updated[expert, 1]) == 0
        ratio = min(
            original[expert].norm().item() / projected[expert].norm().item(),
            _MAX_NORM_RATIO,
        )
        torch.testing.assert_close(updated[expert], projected[expert] * ratio)


def test_fused_bias_projection_updates_offloaded_backing_value():
    experts = _FusedExperts()
    original = experts.down_proj_bias.detach().clone()
    hook = _direct_offload(experts)

    count = AbliterationPipeline._project_fused_bias(
        experts,
        _axis_direction(),
        ["down_proj_bias", "w2_bias"],
    )

    assert count == 3
    assert experts.down_proj_bias.device.type == "meta"
    expected = original.clone()
    expected[:, 1] = 0
    torch.testing.assert_close(hook.weights_map["down_proj_bias"], expected)


def test_granular_and_selective_fused_projection_update_offloaded_backing():
    experts = _FusedExperts()
    original_down = experts.down_proj.detach().clone()
    original_gate_up = experts.gate_up_proj.detach().clone()
    hook = _direct_offload(experts)
    shared = _axis_direction().squeeze()
    per_expert = {0: _axis_direction(axis=0).squeeze()}

    count = AbliterationPipeline._project_fused_3d_granular(
        experts,
        shared,
        per_expert,
        ["down_proj"],
        norm_preserve=False,
        scale=1.0,
    )

    assert count == 3
    assert experts.down_proj.device.type == "meta"
    granular = hook.weights_map["down_proj"]
    assert torch.count_nonzero(granular[0, 0]) == 0
    torch.testing.assert_close(granular[0, 1], original_down[0, 1])
    for expert in (1, 2):
        assert torch.count_nonzero(granular[expert, 1]) == 0
        torch.testing.assert_close(granular[expert, 0], original_down[expert, 0])

    count = AbliterationPipeline._project_fused_3d_selective_inversion(
        experts,
        shared,
        ["gate_up_proj"],
        safety_indices={2},
        reflect_scale=2.0,
        remove_scale=1.0,
        norm_preserve=False,
    )

    assert count == 3
    assert experts.gate_up_proj.device.type == "meta"
    selective = hook.weights_map["gate_up_proj"]
    for expert in (0, 1):
        assert torch.count_nonzero(selective[expert, :, 1]) == 0
    torch.testing.assert_close(selective[2, :, 1], -original_gate_up[2, :, 1])
    torch.testing.assert_close(selective[:, :, 0], original_gate_up[:, :, 0])


def test_fused_projection_resolves_parent_prefixed_expert_backing():
    layer = nn.Module()
    layer.mlp = nn.Module()
    layer.mlp.experts = _FusedExperts()
    original = layer.mlp.experts.down_proj.detach().clone()
    hook = AlignDevicesHook(execution_device="cpu", offload=True, place_submodules=True)
    add_hook_to_module(layer, hook)

    count = AbliterationPipeline._project_fused_3d(
        layer.mlp.experts,
        _axis_direction(),
        ["down_proj"],
        norm_preserve=False,
        scale=1.0,
        offload_roots=(layer,),
    )

    assert count == 3
    assert layer.mlp.experts.down_proj.device.type == "meta"
    expected = original.clone()
    expected[:, 1, :] = 0
    torch.testing.assert_close(hook.weights_map["mlp.experts.down_proj"], expected)


def test_offloaded_quantized_fused_expert_fails_before_mutation():
    experts = nn.Module()
    experts.down_proj = nn.Parameter(
        torch.empty(2, 4, 6, dtype=torch.uint8, device="meta"),
        requires_grad=False,
    )
    backing = {"down_proj": torch.ones(2, 4, 6, dtype=torch.uint8)}
    experts._hf_hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        weights_map=backing,
    )

    with pytest.raises(UnsupportedOffloadedQuantizationError):
        AbliterationPipeline._project_fused_3d(
            experts,
            _axis_direction(),
            ["down_proj"],
            norm_preserve=False,
            scale=1.0,
        )

    assert experts.down_proj.device.type == "meta"
    assert torch.equal(backing["down_proj"], torch.ones(2, 4, 6, dtype=torch.uint8))


class _ReadOnlyFusedMap(MutableMapping[str, torch.Tensor]):
    def __init__(self, tensor: torch.Tensor):
        self.values = {"down_proj": tensor}

    def __getitem__(self, key: str) -> torch.Tensor:
        return self.values[key]

    def __setitem__(self, key: str, value: torch.Tensor) -> None:
        raise OSError("simulated fused backing-store failure")

    def __delitem__(self, key: str) -> None:
        del self.values[key]

    def __iter__(self):
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)


def test_fused_projection_commit_failure_leaves_backing_and_meta_state_intact():
    torch.manual_seed(99)
    original = torch.randn(2, 4, 6)
    experts = nn.Module()
    experts.down_proj = nn.Parameter(
        torch.empty_like(original, device="meta"),
        requires_grad=False,
    )
    backing = _ReadOnlyFusedMap(original.clone())
    experts._hf_hook = AlignDevicesHook(
        execution_device="cpu",
        offload=True,
        weights_map=backing,
    )

    with pytest.raises(OffloadSurgeryError, match="rolled back"):
        AbliterationPipeline._project_fused_3d(
            experts,
            _axis_direction(),
            ["down_proj"],
            norm_preserve=False,
            scale=1.0,
        )

    # The projection worked on a private copy, so the authoritative value is
    # byte-identical and the live parameter is still offloaded.
    torch.testing.assert_close(backing["down_proj"], original)
    assert experts.down_proj.device.type == "meta"
