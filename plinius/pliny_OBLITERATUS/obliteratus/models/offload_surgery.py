"""Transactional access to Accelerate-offloaded logical parameters.

Accelerate represents an offloaded parameter with a live ``meta`` tensor and
keeps the logical value in an ``AlignDevicesHook.weights_map``.  Surgery must
therefore update that backing map without leaving a materialized live tensor or
silently depending on an unknown hook layout.

This module is the only OBLITERATUS compatibility boundary allowed to write to
Accelerate backing stores.  Callers receive a detached logical tensor and commit
the completed update atomically; exceptions before commit leave both the live
module and the backing store unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import torch
import torch.nn as nn

from obliteratus.runtime_contracts import classify_weight_storage


class OffloadSurgeryError(RuntimeError):
    """Base error for unsupported or inconsistent offloaded surgery state."""


class UnsupportedOffloadLayoutError(OffloadSurgeryError):
    """Accelerate exposed a layout that this compatibility adapter cannot write."""


class UnsupportedOffloadedQuantizationError(OffloadSurgeryError):
    """An offloaded packed or quantized parameter cannot be updated safely."""


def _accelerate_release() -> tuple[int, int, int]:
    try:
        raw = version("accelerate").split("+", 1)[0]
    except PackageNotFoundError as exc:  # pragma: no cover - dependency contract
        raise UnsupportedOffloadLayoutError(
            "Accelerate is required to resolve a meta-resident parameter"
        ) from exc

    numeric: list[int] = []
    for part in raw.split(".")[:3]:
        digits = "".join(character for character in part if character.isdigit())
        numeric.append(int(digits or 0))
    while len(numeric) < 3:
        numeric.append(0)
    release = tuple(numeric)
    if not ((release[0] == 0 and release[1] >= 24) or release[0] == 1):
        raise UnsupportedOffloadLayoutError(
            f"Accelerate {raw} is outside the tested offload-surgery range "
            "(>=0.24,<2); refusing compatibility access"
        )
    return release


def _align_hooks(hook: Any) -> list[Any]:
    """Return supported offloading hooks from direct or sequential layouts."""
    from accelerate.hooks import AlignDevicesHook, SequentialHook

    if isinstance(hook, AlignDevicesHook):
        return [hook] if hook.offload else []
    if isinstance(hook, SequentialHook):
        hooks: list[Any] = []
        for child in hook.hooks:
            hooks.extend(_align_hooks(child))
        return hooks
    return []


def _relative_module_path(owner: nn.Module, target: nn.Module) -> str | None:
    for name, candidate in owner.named_modules():
        if candidate is target:
            return name
    return None


@dataclass(frozen=True)
class _WriteTarget:
    """A validated readable/writable view of one backing-store key."""

    container: Any
    key: str
    loader: bool = False

    def read(self) -> torch.Tensor:
        value = self.container[self.key]
        if not isinstance(value, torch.Tensor):
            raise UnsupportedOffloadLayoutError(
                f"Accelerate backing value {self.key!r} is not a tensor"
            )
        return value

    def write(self, value: torch.Tensor) -> None:
        if self.loader:
            self.container.state_dict[self.key] = value
            if self.key not in self.container.all_keys:
                self.container.all_keys.append(self.key)
            return
        self.container[self.key] = value


def _write_target(weights_map: Mapping[str, torch.Tensor], key: str) -> _WriteTarget:
    """Resolve public mappings and the two version-gated Accelerate wrappers."""
    from accelerate.utils.offload import OffloadedWeightsLoader, PrefixedDataset

    if isinstance(weights_map, PrefixedDataset):
        return _write_target(weights_map.dataset, f"{weights_map.prefix}{key}")
    if isinstance(weights_map, OffloadedWeightsLoader):
        return _WriteTarget(weights_map, key, loader=True)
    if isinstance(weights_map, MutableMapping):
        return _WriteTarget(weights_map, key)
    raise UnsupportedOffloadLayoutError(
        "Accelerate weights_map is read-only and has no supported writable "
        f"backing store ({type(weights_map).__module__}.{type(weights_map).__name__})"
    )


def _same_storage(left: torch.Tensor, right: torch.Tensor) -> bool:
    if left is right:
        return True
    if left.device.type == "meta" or right.device.type == "meta":
        return False
    return (
        left.shape == right.shape
        and left.dtype == right.dtype
        and left.data_ptr() == right.data_ptr()
    )


def _alias_targets(primary: _WriteTarget, source: torch.Tensor) -> list[_WriteTarget]:
    """Find inexpensive in-memory aliases so tied backing values stay tied."""
    targets = [primary]
    if primary.loader:
        candidates = primary.container.state_dict.items()
    elif isinstance(primary.container, MutableMapping):
        candidates = primary.container.items()
    else:  # pragma: no cover - construction guarantees one of the above
        candidates = ()

    for key, value in candidates:
        if key == primary.key or not isinstance(value, torch.Tensor):
            continue
        if _same_storage(value, source):
            targets.append(_WriteTarget(primary.container, key, loader=primary.loader))
    return targets


@dataclass
class LogicalParameterTransaction:
    """A detached logical parameter with an atomic commit operation."""

    module: nn.Module
    parameter_name: str
    tensor: torch.Tensor
    offloaded: bool
    backing_key: str | None = None
    _targets: list[_WriteTarget] = field(default_factory=list, repr=False)
    _parameter_identity: int = field(init=False, repr=False)
    _committed: bool = field(default=False, init=False, repr=False)
    _rollback_values: list[tuple[_WriteTarget | None, torch.Tensor]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._parameter_identity = id(getattr(self.module, self.parameter_name))

    def commit(self, updated: torch.Tensor) -> None:
        """Commit a complete logical value without exposing partial mutation."""
        parameter = getattr(self.module, self.parameter_name)
        if id(parameter) != self._parameter_identity:
            raise OffloadSurgeryError(
                f"{self.parameter_name} identity changed during logical surgery"
            )
        if updated.shape != self.tensor.shape:
            raise OffloadSurgeryError(
                f"logical update changed shape from {tuple(self.tensor.shape)} "
                f"to {tuple(updated.shape)}"
            )
        if not updated.is_floating_point():
            raise UnsupportedOffloadedQuantizationError(
                "logical surgery requires a floating-point result"
            )

        if not self.offloaded:
            original = parameter.data.detach().clone()
            with torch.no_grad():
                parameter.data.copy_(updated.to(parameter.device, parameter.dtype))
            self._rollback_values = [(None, original)]
            self._committed = True
            return

        if parameter.device.type != "meta":
            raise OffloadSurgeryError(
                "offloaded parameter was unexpectedly materialized before commit"
            )

        committed = updated.detach().to(device="cpu", dtype=self.tensor.dtype).clone()
        originals = [(target, target.read()) for target in self._targets]
        try:
            for target, _original in originals:
                target.write(committed)
        except Exception as exc:
            for target, original in reversed(originals):
                try:
                    target.write(original)
                except Exception:
                    pass
            raise OffloadSurgeryError(
                f"failed to commit logical parameter {self.backing_key!r}; "
                "the backing store was rolled back"
            ) from exc

        if parameter.device.type != "meta" or id(parameter) != self._parameter_identity:
            for target, original in reversed(originals):
                target.write(original)
            raise OffloadSurgeryError(
                "offload invariant changed during commit; backing update rolled back"
            )
        self._rollback_values = originals
        self._committed = True

    def rollback(self) -> None:
        """Restore the value captured by the most recent successful commit."""
        if not self._committed:
            return
        parameter = getattr(self.module, self.parameter_name)
        if id(parameter) != self._parameter_identity:
            raise OffloadSurgeryError(
                f"cannot roll back changed {self.parameter_name} identity"
            )
        if self.offloaded:
            for target, original in reversed(self._rollback_values):
                if target is not None:
                    target.write(original)
            if parameter.device.type != "meta":
                raise OffloadSurgeryError(
                    "offloaded parameter was materialized during rollback"
                )
        else:
            original = self._rollback_values[0][1]
            with torch.no_grad():
                parameter.data.copy_(original)
        self._rollback_values = []
        self._committed = False


def resolve_logical_parameter(
    module: nn.Module,
    parameter_name: str = "weight",
    *,
    search_roots: Sequence[nn.Module] = (),
) -> LogicalParameterTransaction:
    """Resolve a live or Accelerate-offloaded parameter for safe surgery.

    ``search_roots`` supplies known ancestors such as the decoder layer.  This
    is required when Accelerate attaches one ``place_submodules`` hook to a
    parent and stores keys such as ``self_attn.o_proj.weight``.
    """
    parameter = getattr(module, parameter_name, None)
    if parameter is None or not isinstance(parameter, (nn.Parameter, torch.Tensor)):
        raise OffloadSurgeryError(
            f"module has no tensor parameter named {parameter_name!r}"
        )
    if parameter.device.type != "meta":
        return LogicalParameterTransaction(
            module=module,
            parameter_name=parameter_name,
            tensor=parameter.data,
            offloaded=False,
        )

    _accelerate_release()
    roots: list[nn.Module] = []
    for root in (module, *search_roots):
        if all(root is not existing for existing in roots):
            roots.append(root)

    candidates: list[tuple[int, nn.Module, str, Any]] = []
    inspected_hooks = 0
    for root in roots:
        for _owner_name, owner in root.named_modules():
            relative = _relative_module_path(owner, module)
            if relative is None:
                continue
            hook = getattr(owner, "_hf_hook", None)
            if hook is None:
                continue
            align_hooks = _align_hooks(hook)
            inspected_hooks += len(align_hooks)
            key = f"{relative}.{parameter_name}" if relative else parameter_name
            for align_hook in align_hooks:
                candidates.append((relative.count("."), owner, key, align_hook))

    # A hook closest to the target has the shortest relative key and is the
    # least ambiguous source of truth.
    candidates.sort(key=lambda candidate: candidate[0])
    attempted: list[str] = []
    for _depth, _owner, key, hook in candidates:
        weights_map = getattr(hook, "weights_map", None)
        if weights_map is None:
            continue
        attempted.append(key)
        try:
            source = weights_map[key]
        except (KeyError, IndexError):
            continue
        if not isinstance(source, torch.Tensor):
            raise UnsupportedOffloadLayoutError(
                f"Accelerate backing value {key!r} is not a tensor"
            )

        storage_kind = classify_weight_storage(
            module_class_name=module.__class__.__name__,
            parameter_class_name=parameter.__class__.__name__,
            has_quant_state=hasattr(parameter, "quant_state"),
            data_is_floating_point=source.is_floating_point(),
        )
        if storage_kind != "float":
            raise UnsupportedOffloadedQuantizationError(
                f"offloaded {storage_kind} parameter {key!r} cannot be "
                "safely updated before supported quantized write-back exists"
            )

        primary = _write_target(weights_map, key)
        return LogicalParameterTransaction(
            module=module,
            parameter_name=parameter_name,
            tensor=source,
            offloaded=True,
            backing_key=key,
            _targets=_alias_targets(primary, source),
        )

    attempted_text = ", ".join(dict.fromkeys(attempted)) or parameter_name
    if inspected_hooks == 0:
        raise UnsupportedOffloadLayoutError(
            f"meta-resident parameter {parameter_name!r} has no supported "
            "offloading AlignDevicesHook in the supplied module roots"
        )
    raise UnsupportedOffloadLayoutError(
        f"no authoritative Accelerate backing value found for meta parameter; "
        f"attempted keys: {attempted_text}"
    )


def validate_offloaded_parameters(root: nn.Module) -> None:
    """Fail closed on every meta parameter before a surgery pass mutates data."""
    seen: set[int] = set()
    for _module_name, module in root.named_modules():
        for parameter_name, parameter in module.named_parameters(recurse=False):
            if parameter.device.type != "meta" or id(parameter) in seen:
                continue
            resolve_logical_parameter(module, parameter_name, search_roots=(root,))
            seen.add(id(parameter))


def logical_module_device(root: nn.Module) -> torch.device:
    """Return a usable compute device even when a layer starts on ``meta``."""
    for _module_name, module in root.named_modules():
        for parameter_name, parameter in module.named_parameters(recurse=False):
            if parameter.device.type != "meta":
                return parameter.device
            return resolve_logical_parameter(
                module,
                parameter_name,
                search_roots=(root,),
            ).tensor.device
    raise OffloadSurgeryError("module has no parameters from which to select a device")
