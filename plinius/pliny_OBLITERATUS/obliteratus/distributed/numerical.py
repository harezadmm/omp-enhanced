"""Placement-aware projection oracle for the two-rank Gloo prototype."""

from __future__ import annotations

import hashlib
import math

import torch
import torch.distributed as dist

from obliteratus.analysis.numerical_contracts import (
    ProjectionResult,
    project_weight_against_direction,
    select_projection_coefficients,
)
from obliteratus.distributed.consensus import require_consensus_digest
from obliteratus.distributed.contracts import (
    ContractError,
    LogicalPlacement,
    PlacementKind,
    contract_digest,
)


def _tensor_digest(tensor: torch.Tensor) -> str:
    value = tensor.detach().cpu().contiguous()
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def _group_info(group: dist.ProcessGroup | None) -> tuple[int, int]:
    if not dist.is_available() or not dist.is_initialized():
        raise ContractError("distributed projection requires an initialized process group")
    if str(dist.get_backend(group)).lower() != "gloo":
        raise ContractError("the prototype distributed projection requires Gloo")
    return dist.get_rank(group), dist.get_world_size(group)


def _all_reduce_sum(value: torch.Tensor, group: dist.ProcessGroup | None) -> torch.Tensor:
    result = value.clone()
    dist.all_reduce(result, op=dist.ReduceOp.SUM, group=group)
    return result


def _validate_placement_world(
    placement: LogicalPlacement,
    group: dist.ProcessGroup | None,
) -> None:
    rank, world_size = _group_info(group)
    if placement.rank != rank or placement.world_size != world_size:
        raise ContractError("placement rank/world does not match the process group")
    kind_code = {
        PlacementKind.REPLICATED: 0,
        PlacementKind.COLUMN_WISE: 1,
        PlacementKind.ROW_WISE: 2,
    }[placement.kind]
    local = torch.tensor(
        (
            kind_code,
            placement.shard_dim if placement.shard_dim is not None else -1,
            placement.shard_start,
            placement.shard_end,
            placement.direction_axis,
            placement.global_shape[0],
            placement.global_shape[1],
        ),
        dtype=torch.int64,
    )
    gathered = [torch.zeros_like(local) for _ in range(world_size)]
    dist.all_gather(gathered, local, group=group)
    expected_shard_dim = int(local[1])
    expected_invariants = tuple(int(value) for value in local[4:])
    for other_rank, item in enumerate(gathered):
        values = tuple(int(value) for value in item)
        if values[0] != kind_code or values[1] != expected_shard_dim or values[4:] != expected_invariants:
            raise ContractError("rank placement metadata disagrees")
        if placement.kind is PlacementKind.REPLICATED:
            if values[2:4] != (0, 0):
                raise ContractError("replicated rank declared a shard interval")
        else:
            assert placement.shard_dim is not None
            shard_size = placement.global_shape[placement.shard_dim] // world_size
            if values[2:4] != (other_rank * shard_size, (other_rank + 1) * shard_size):
                raise ContractError("rank shard intervals do not exactly tile the logical tensor")
    invariant_digest = contract_digest(
        {
            "logical_name": placement.logical_name,
            "global_shape": placement.global_shape,
            "dtype": placement.dtype,
            "kind": placement.kind,
            "world_size": placement.world_size,
            "direction_axis": placement.direction_axis,
            "shard_dim": placement.shard_dim,
        }
    )
    require_consensus_digest(invariant_digest, group=group)


def _global_finite(local: torch.Tensor, group: dist.ProcessGroup | None) -> bool:
    flag = torch.tensor(int(torch.isfinite(local).all()), dtype=torch.int64)
    dist.all_reduce(flag, op=dist.ReduceOp.MIN, group=group)
    return bool(int(flag))


def _global_norm_sq(local: torch.Tensor, group: dist.ProcessGroup | None) -> float:
    value = local.pow(2).sum().reshape(1)
    return float(_all_reduce_sum(value, group).item())


def _gather_coefficients(local: torch.Tensor, group: dist.ProcessGroup | None) -> torch.Tensor:
    world_size = dist.get_world_size(group)
    gathered = [torch.zeros_like(local) for _ in range(world_size)]
    dist.all_gather(gathered, local, group=group)
    return torch.cat(gathered, dim=0)


def _validate_ratio(value: object, name: str, *, lower_inclusive: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError(f"{name} must be a finite number")
    normalized = float(value)
    lower_ok = normalized >= 0.0 if lower_inclusive else normalized > 0.0
    if not lower_ok or normalized > 1.0:
        interval = "[0, 1]" if lower_inclusive else "(0, 1]"
        raise ContractError(f"{name} must be in {interval}")
    return normalized


def distributed_project_weight(
    weight: torch.Tensor,
    direction: torch.Tensor,
    placement: LogicalPlacement,
    *,
    group: dist.ProcessGroup | None = None,
    norm_preserve: bool = False,
    regularization: float = 0.0,
    projection_row_fraction: float = 1.0,
    max_norm_ratio: float = 1.10,
) -> ProjectionResult:
    """Project one local shard with complete-logical-tensor semantics."""
    if not isinstance(placement, LogicalPlacement):
        raise ContractError("placement must be a LogicalPlacement")
    _validate_placement_world(placement, group)
    if not isinstance(weight, torch.Tensor) or tuple(weight.shape) != placement.local_shape:
        raise ContractError("local weight shape does not match the placement")
    if not weight.is_floating_point():
        raise ContractError("distributed projection requires floating-point weights")
    if weight.device.type != "cpu":
        raise ContractError("the Gloo semantic oracle requires CPU tensors")
    if str(weight.dtype).removeprefix("torch.") != placement.dtype:
        raise ContractError("local weight dtype does not match the placement")
    if (
        not isinstance(direction, torch.Tensor)
        or direction.ndim != 1
        or direction.numel() != placement.global_shape[placement.direction_axis]
        or not direction.is_floating_point()
    ):
        raise ContractError("direction does not match the declared logical axis")
    if direction.device.type != "cpu":
        raise ContractError("the Gloo semantic oracle requires CPU tensors")
    regularization = _validate_ratio(regularization, "regularization", lower_inclusive=True)
    projection_row_fraction = _validate_ratio(
        projection_row_fraction,
        "projection_row_fraction",
        lower_inclusive=False,
    )
    if (
        isinstance(max_norm_ratio, bool)
        or not isinstance(max_norm_ratio, (int, float))
        or not math.isfinite(max_norm_ratio)
        or max_norm_ratio <= 0
    ):
        raise ContractError("max_norm_ratio must be positive and finite")
    max_norm_ratio = float(max_norm_ratio)

    require_consensus_digest(_tensor_digest(direction), group=group)
    if placement.kind is PlacementKind.REPLICATED:
        require_consensus_digest(_tensor_digest(weight), group=group)
        result = project_weight_against_direction(
            weight,
            direction,
            norm_preserve=norm_preserve,
            regularization=regularization,
            projection_row_fraction=projection_row_fraction,
            max_norm_ratio=max_norm_ratio,
        )
        require_consensus_digest(_tensor_digest(result.weight), group=group)
        return result

    compute_dtype = torch.float64 if torch.float64 in {weight.dtype, direction.dtype} else torch.float32
    work = weight.to(dtype=compute_dtype)
    full_direction = direction.to(dtype=compute_dtype)
    if not _global_finite(work, group) or not torch.isfinite(full_direction).all():
        return ProjectionResult(weight=weight.clone(), projected=False, coefficient_norm_sq=0.0, layout=None)
    direction_norm = full_direction.norm()
    if direction_norm < 1e-8:
        return ProjectionResult(weight=weight.clone(), projected=False, coefficient_norm_sq=0.0, layout=None)
    full_direction = full_direction / direction_norm
    scale = 1.0 - regularization
    direction_axis = placement.direction_axis
    shard_dim = placement.shard_dim
    layout = "standard" if direction_axis == 1 else "transposed"

    if shard_dim == direction_axis:
        local_direction = full_direction[placement.shard_start : placement.shard_end]
        if direction_axis == 1:
            local_coefficient = work @ local_direction.reshape(-1, 1)
            coefficient = _all_reduce_sum(local_coefficient, group)
            selected = select_projection_coefficients(coefficient, projection_row_fraction)
            projected = work - selected * (scale * local_direction.reshape(1, -1))
        else:
            local_coefficient = local_direction.reshape(1, -1) @ work
            coefficient = _all_reduce_sum(local_coefficient, group)
            selected = select_projection_coefficients(coefficient, projection_row_fraction)
            projected = work - (scale * local_direction.reshape(-1, 1)) * selected
        coefficient_norm_sq = float(selected.pow(2).sum().item())
    else:
        if direction_axis == 1:
            local_coefficient = work @ full_direction.reshape(-1, 1)
            combined = _gather_coefficients(local_coefficient, group)
            selected_all = select_projection_coefficients(combined, projection_row_fraction)
            local_count = local_coefficient.shape[0]
            start = placement.rank * local_count
            selected = selected_all[start : start + local_count]
            projected = work - selected * (scale * full_direction.reshape(1, -1))
        else:
            local_coefficient = (full_direction.reshape(1, -1) @ work).T
            combined = _gather_coefficients(local_coefficient, group)
            selected_all = select_projection_coefficients(combined, projection_row_fraction)
            local_count = local_coefficient.shape[0]
            start = placement.rank * local_count
            selected = selected_all[start : start + local_count].T
            projected = work - (scale * full_direction.reshape(-1, 1)) * selected
        coefficient_norm_sq = float(selected_all.pow(2).sum().item())

    if norm_preserve:
        original_norm_sq = _global_norm_sq(work, group)
        new_norm_sq = max(
            0.0,
            original_norm_sq - scale * (2.0 - scale) * coefficient_norm_sq,
        )
        if original_norm_sq > 0 and new_norm_sq > 0:
            projected = projected * min(math.sqrt(original_norm_sq / new_norm_sq), max_norm_ratio)

    return ProjectionResult(
        weight=projected.to(dtype=weight.dtype),
        projected=True,
        coefficient_norm_sq=coefficient_norm_sq if norm_preserve else 0.0,
        layout=layout,
    )
