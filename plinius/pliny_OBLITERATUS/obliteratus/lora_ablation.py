"""LoRA-based reversible ablation mode.

Instead of permanent in-place weight surgery, applies ablation via rank-1
LoRA adapters.  This provides:

1. **Reversibility**: LoRA adapters can be removed to restore original model
2. **Composability**: Multiple ablation adapters can be stacked/blended
3. **PEFT compatibility**: Exact-identity exports use standard HuggingFace PEFT

Inspired by Heretic (p-e-w, 2025) which pioneered LoRA-mediated ablation.
OBLITERATUS extends this with:
- Multi-direction rank-k adapters (not just rank-1)
- MoE-aware LoRA targeting (router + expert-specific adapters)
- Integration with EGA per-expert directions
- CoT-aware adapter strength modulation

The mathematical equivalence to in-place projection depends on weight orientation:

    For W of shape (out, hidden) where d is in the hidden dimension:
        In-place:  W' = W - scale * W @ d @ d^T
        LoRA:      W' = W + B @ A  where  B = -scale * (W @ d),  A = d^T

    For W of shape (hidden, out) (e.g., Conv1D layers):
        In-place:  W' = W - scale * d @ d^T @ W
        LoRA:      W' = W + B @ A  where  B = -scale * d,  A = d^T @ W

Both produce identical output, but LoRA stores {B, A} separately.

References:
    - Hu et al. (2022): LoRA: Low-Rank Adaptation of Large Language Models
    - Heretic (p-e-w, 2025): LoRA-mediated directional ablation
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import torch
import torch.nn as nn
from safetensors.torch import load_file, save_file

from obliteratus.checkpoint_provenance import (
    AdapterIdentity,
    ArtifactIdentity,
    ProvenanceRecord,
    verify_provenance_record,
)
from obliteratus.persistence_contracts import atomic_checkpoint_directory

if TYPE_CHECKING:
    from obliteratus.abliterate import AbliterationPipeline

logger = logging.getLogger(__name__)

# Target module name patterns for LoRA adapter placement
_LORA_TARGETS = [
    "o_proj", "q_proj", "k_proj", "v_proj",
    "down_proj", "up_proj", "gate_proj",
    "gate", "router",
]

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMMUTABLE_REVISION = re.compile(r"^[0-9a-f]{40,64}$")
_MODULE_PATH = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$")
_PUBLIC_REPO_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,511}$")
_PUBLIC_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,511}$")
_SECRET_VALUE = re.compile(r"(?i)(?:hf_[a-z0-9]{12,}|bearer\s+[a-z0-9._~+/-]{12,})")


@dataclass(frozen=True)
class BaseModelIdentity:
    """Exact base and tokenizer identity required for a canonical PEFT claim."""

    repo_id: str
    revision: str
    weights_digest: str
    tokenizer_digest: str
    vocab_size: int
    architecture: str
    tied_embeddings: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.repo_id, str)
            or not self.repo_id
            or len(self.repo_id) > 512
            or not _PUBLIC_REPO_ID.fullmatch(self.repo_id)
            or Path(self.repo_id).is_absolute()
            or ".." in self.repo_id.split("/")
            or _SECRET_VALUE.search(self.repo_id)
        ):
            raise ValueError("base repository identity is invalid")
        if not _IMMUTABLE_REVISION.fullmatch(self.revision):
            raise ValueError("base revision must be an immutable commit")
        for value, field in (
            (self.weights_digest, "base weights digest"),
            (self.tokenizer_digest, "tokenizer digest"),
        ):
            if not _DIGEST.fullmatch(value):
                raise ValueError(f"{field} is invalid")
        if type(self.vocab_size) is not int or self.vocab_size <= 0:
            raise ValueError("base vocabulary size is invalid")
        if (
            not isinstance(self.architecture, str)
            or not self.architecture
            or len(self.architecture) > 512
            or not _PUBLIC_NAME.fullmatch(self.architecture)
            or Path(self.architecture).is_absolute()
            or _SECRET_VALUE.search(self.architecture)
        ):
            raise ValueError("base architecture is invalid")
        if type(self.tied_embeddings) is not bool:
            raise ValueError("base tied-embedding declaration is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "revision": self.revision,
            "weights_digest": self.weights_digest,
            "tokenizer_digest": self.tokenizer_digest,
            "vocab_size": self.vocab_size,
            "architecture": self.architecture,
            "tied_embeddings": self.tied_embeddings,
        }

    def to_artifact_identity(self) -> ArtifactIdentity:
        return ArtifactIdentity("hub", self.repo_id, self.revision, self.weights_digest)

    def tokenizer_artifact_identity(self) -> ArtifactIdentity:
        return ArtifactIdentity(
            "hub",
            f"{self.repo_id}#tokenizer",
            self.revision,
            self.tokenizer_digest,
        )


@dataclass(frozen=True)
class AdapterArtifact:
    artifact_id: str
    weights_path: Path
    config_path: Path
    provenance_path: Path


def compute_lora_adapters(
    pipeline: AbliterationPipeline,
    rank: int = 1,
) -> dict[str, tuple[torch.Tensor, torch.Tensor]]:
    """Compute LoRA adapter pairs (B, A) for refusal direction ablation.

    For each target weight matrix W with refusal direction d:
        A = d^T @ W    (rank-1: shape (1, in_features) or (rank, in_features))
        B = -scale * d  (rank-1: shape (out_features, 1) or (out_features, rank))

    So that  W + B @ A  ≈  W - scale * (d @ d^T) @ W

    Args:
        pipeline: Initialized pipeline (post-DISTILL, pre-EXCISE).
        rank: LoRA rank (1 = rank-1 ablation, >1 = multi-direction).

    Returns:
        Dict mapping "layer.{idx}.{module}.{weight}" → (lora_B, lora_A) pairs.
    """
    from obliteratus.strategies.utils import (
        get_attention_module,
        get_ffn_module,
        get_layer_modules,
    )
    from obliteratus.abliterate import (
        _ATTN_OUT_NAMES,
        _ATTN_IN_NAMES,
        _FFN_OUT_NAMES,
        _FFN_IN_NAMES,
        _ROUTER_NAMES,
    )

    if not pipeline.handle or not pipeline._strong_layers:
        return {}

    layers = get_layer_modules(pipeline.handle)
    arch = pipeline.handle.architecture
    module_names = {
        id(module): name
        for name, module in pipeline.handle.model.named_modules()
        if name
    }
    adapters: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}

    for idx in pipeline._strong_layers:
        if idx not in pipeline.refusal_subspaces:
            continue

        subspace = pipeline.refusal_subspaces[idx]
        n_dirs = min(rank, subspace.shape[0])

        # Compute per-layer regularization (mirroring excise logic)
        reg = pipeline.regularization
        if pipeline.layer_adaptive_strength and idx in pipeline._layer_excise_weights:
            weight = pipeline._layer_excise_weights[idx]
            reg = pipeline.regularization + (1.0 - weight) * (1.0 - pipeline.regularization) * 0.15
        if pipeline.float_layer_interpolation and idx in pipeline._float_layer_weights:
            float_w = pipeline._float_layer_weights[idx]
            reg = reg + (1.0 - float_w) * (1.0 - reg) * 0.3

        scale = 1.0 - reg

        # Direction matrix: (n_dirs, hidden_dim)
        D = subspace[:n_dirs].float()

        # Collect target modules and their weight matrices
        targets: list[tuple[str, nn.Module, list[str]]] = []
        try:
            attn = get_attention_module(layers[idx], arch)
            targets.append(("attn", attn, _ATTN_OUT_NAMES + _ATTN_IN_NAMES))
        except (AttributeError, RuntimeError):
            pass
        try:
            ffn = get_ffn_module(layers[idx], arch)
            targets.append(("ffn", ffn, _FFN_OUT_NAMES + _FFN_IN_NAMES + _ROUTER_NAMES))
        except (AttributeError, RuntimeError):
            pass

        for module_label, module, candidate_names in targets:
            for name in candidate_names:
                proj = getattr(module, name, None)
                if proj is None or not hasattr(proj, "weight"):
                    continue

                W = proj.weight.data.float()

                if W.shape[-1] == D.shape[1]:
                    # Standard: W is (out, hidden_dim), direction along last axis
                    # A = D @ W^T → (n_dirs, out) ... no, we need the correct decomposition
                    # W' = W - scale * D^T @ D @ W
                    # LoRA: B @ A where B = -scale * D^T shape (hidden_dim, n_dirs)
                    #                    A = D @ W shape (n_dirs, out)...
                    # Actually for nn.Linear: output = input @ W^T + b
                    # So to affect output: we need delta_W such that input @ delta_W^T
                    # delta_W = -scale * d @ d^T @ W → B = -scale * d, A = d^T @ W
                    # B shape: (out_features, n_dirs) where out_features = W.shape[0]
                    # Wait, let me reconsider. For W shape (out, in):
                    # delta_W = -scale * (d_col @ d_col^T) @ W
                    # where d_col is (in, 1) if direction matches input dim
                    # delta_W = -scale * d_col @ (d_col^T @ W)
                    # = -scale * d_col @ coeff where coeff = d_col^T @ W = (1, out)
                    # So: B = -scale * d_col = (in, 1), A = d_col^T @ W = (1, out)
                    # But LoRA convention: delta_W = B @ A where B is (out, r), A is (r, in)
                    # So we need: delta_W^T = A^T @ B^T
                    # Hmm, let me just store the computed delta and split it

                    # For each direction, compute the rank-1 adapter
                    lora_B_parts = []
                    lora_A_parts = []
                    for di in range(n_dirs):
                        d = D[di]  # (hidden_dim,)
                        d_col = d.unsqueeze(-1)  # (hidden_dim, 1)
                        # coeff = d^T @ W^T = (d @ W^T) → but W is (out, hidden), so:
                        # For W @ d → (out, 1) projection
                        coeff = (W @ d_col).squeeze(-1)  # (out,)
                        # delta_W = -scale * d_col @ coeff.unsqueeze(0) would be (hidden, out)
                        # But we want (out, hidden) to match W shape
                        # delta_W[i,j] = -scale * coeff[i] * d[j]
                        # = B[i,:] @ A[:,j] where B = -scale * coeff.unsqueeze(1) = (out,1)
                        #                         A = d.unsqueeze(0) = (1, hidden)
                        lora_B_parts.append(-scale * coeff.unsqueeze(1))  # (out, 1)
                        lora_A_parts.append(d.unsqueeze(0))  # (1, hidden)

                    lora_B = torch.cat(lora_B_parts, dim=1)  # (out, n_dirs)
                    lora_A = torch.cat(lora_A_parts, dim=0)  # (n_dirs, hidden)

                elif W.shape[0] == D.shape[1]:
                    # Transposed case: W is (hidden_dim, out)
                    lora_B_parts = []
                    lora_A_parts = []
                    for di in range(n_dirs):
                        d = D[di]  # (hidden_dim,)
                        coeff = (d @ W)  # (out,)
                        lora_B_parts.append(-scale * d.unsqueeze(1))  # (hidden, 1)
                        lora_A_parts.append(coeff.unsqueeze(0))  # (1, out)

                    lora_B = torch.cat(lora_B_parts, dim=1)  # (hidden, n_dirs)
                    lora_A = torch.cat(lora_A_parts, dim=0)  # (n_dirs, out)
                else:
                    continue

                key = module_names.get(id(proj), f"layer.{idx}.{module_label}.{name}")
                adapters[key] = (lora_B.half(), lora_A.half())

    pipeline.log(f"Computed {len(adapters)} LoRA adapter pairs (rank={rank})")
    return adapters


def apply_lora_adapters(
    pipeline: AbliterationPipeline,
    adapters: dict[str, tuple[torch.Tensor, torch.Tensor]],
):
    """Apply pre-computed LoRA adapters by modifying weights in-place.

    This is equivalent to merging the LoRA into the base model.
    The adapters dict is stored in pipeline._lora_adapters for potential
    later unmerging.
    """
    from obliteratus.strategies.utils import (
        get_attention_module,
        get_ffn_module,
        get_layer_modules,
    )

    if not pipeline.handle:
        return

    layers = get_layer_modules(pipeline.handle)
    arch = pipeline.handle.architecture
    named_modules = dict(pipeline.handle.model.named_modules())
    applied = 0

    for key, (lora_B, lora_A) in adapters.items():
        proj = named_modules.get(key)
        if proj is None:
            parts = key.split(".")
            if len(parts) != 4 or parts[0] != "layer" or not parts[1].isdigit():
                continue
            _, idx_str, module_label, weight_name = parts
            idx = int(idx_str)
            try:
                if module_label == "attn":
                    module = get_attention_module(layers[idx], arch)
                else:
                    module = get_ffn_module(layers[idx], arch)
            except (AttributeError, RuntimeError):
                continue
            proj = getattr(module, weight_name, None)
        if proj is None or not hasattr(proj, "weight"):
            continue

        W = proj.weight.data
        delta = (lora_B @ lora_A).to(device=W.device, dtype=W.dtype)

        if delta.shape == W.shape:
            W.add_(delta)
            applied += 1

    pipeline._lora_adapters = adapters
    pipeline.log(f"Applied {applied} LoRA adapters (merged into weights)")


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_new(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _digest_bytes(payload: bytes) -> str:
    return f"sha256:{sha256(payload).hexdigest()}"


def _digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _prepare_adapter_state(
    adapters: dict[str, tuple[torch.Tensor, torch.Tensor]],
    *,
    lora_alpha: int | None,
) -> tuple[dict[str, torch.Tensor], list[dict[str, Any]], int, int, float]:
    if not adapters:
        raise ValueError("canonical PEFT export requires at least one adapter")
    ranks = set()
    for module_name, pair in adapters.items():
        if not _MODULE_PATH.fullmatch(module_name):
            raise ValueError(f"adapter module path is invalid: {module_name!r}")
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValueError(f"adapter pair is invalid: {module_name}")
        lora_b, lora_a = pair
        if (
            not isinstance(lora_a, torch.Tensor)
            or not isinstance(lora_b, torch.Tensor)
            or lora_a.ndim != 2
            or lora_b.ndim != 2
            or lora_b.shape[1] != lora_a.shape[0]
            or lora_a.dtype != lora_b.dtype
        ):
            raise ValueError(f"adapter tensor geometry is invalid: {module_name}")
        ranks.add(int(lora_a.shape[0]))
    if len(ranks) != 1 or next(iter(ranks)) <= 0:
        raise ValueError("canonical PEFT export requires one positive rank")
    rank = next(iter(ranks))
    alpha = rank if lora_alpha is None else lora_alpha
    if type(alpha) is not int or alpha <= 0:
        raise ValueError("LoRA alpha must be a positive integer")
    scaling = alpha / rank
    state: dict[str, torch.Tensor] = {}
    key_map: list[dict[str, Any]] = []
    for module_name in sorted(adapters):
        lora_b, lora_a = adapters[module_name]
        a_key = f"base_model.model.{module_name}.lora_A.weight"
        b_key = f"base_model.model.{module_name}.lora_B.weight"
        state[a_key] = lora_a.detach().cpu().contiguous()
        state[b_key] = lora_b.detach().cpu().contiguous() / scaling
        key_map.append(
            {
                "module_name": module_name,
                "target_module": module_name.rsplit(".", 1)[-1],
                "lora_A_key": a_key,
                "lora_B_key": b_key,
                "lora_A_shape": list(lora_a.shape),
                "lora_B_shape": list(lora_b.shape),
                "rank": rank,
            }
        )
    return state, key_map, rank, alpha, scaling


def save_lora_adapters(
    adapters: dict[str, tuple[torch.Tensor, torch.Tensor]],
    output_dir: str | Path,
    *,
    base_model: BaseModelIdentity,
    provenance_factory: Callable[[tuple[str, ...], AdapterIdentity], ProvenanceRecord],
    lora_alpha: int | None = None,
    lora_dropout: float = 0.0,
    modules_to_save: tuple[str, ...] = (),
    adapter_name: str = "default",
) -> AdapterArtifact:
    """Atomically write a standard PEFT LoRA artifact with exact provenance."""
    if not isinstance(base_model, BaseModelIdentity):
        raise ValueError("canonical PEFT export requires an exact base model identity")
    if (
        isinstance(lora_dropout, bool)
        or not isinstance(lora_dropout, (int, float))
        or not math.isfinite(lora_dropout)
        or not 0 <= lora_dropout < 1
    ):
        raise ValueError("LoRA dropout must be in [0, 1)")
    if modules_to_save:
        raise ValueError("modules_to_save is unsupported unless its tensors are supplied")
    if (
        not isinstance(adapter_name, str)
        or not adapter_name
        or len(adapter_name) > 512
        or not _PUBLIC_NAME.fullmatch(adapter_name)
        or Path(adapter_name).is_absolute()
        or _SECRET_VALUE.search(adapter_name)
    ):
        raise ValueError("adapter name is invalid")
    state, key_map, rank, alpha, scaling = _prepare_adapter_state(
        adapters,
        lora_alpha=lora_alpha,
    )
    output_path = Path(output_dir)
    if (
        output_path.is_symlink()
        or output_path.absolute() != output_path.resolve(strict=False)
    ):
        raise ValueError("adapter output directory must not be a symlink")
    if output_path.exists() and (not output_path.is_dir() or any(output_path.iterdir())):
        raise FileExistsError("adapter output directory must be absent or empty")
    config = {
        "base_model_name_or_path": base_model.repo_id,
        "bias": "none",
        "fan_in_fan_out": False,
        "inference_mode": True,
        "init_lora_weights": True,
        "lora_alpha": alpha,
        "lora_dropout": float(lora_dropout),
        "modules_to_save": None,
        "peft_type": "LORA",
        "r": rank,
        "revision": base_model.revision,
        # Full paths prevent PEFT from creating unsupplied adapters on every
        # module that happens to share a leaf name such as ``q_proj``.
        "target_modules": sorted(item["module_name"] for item in key_map),
        "task_type": "CAUSAL_LM",
    }
    config_payload = _json_bytes(config)
    key_map_digest = _digest_bytes(
        json.dumps(key_map, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    adapter_identity = AdapterIdentity(
        adapter_type="lora",
        base_model=base_model.to_artifact_identity(),
        config_digest=_digest_bytes(config_payload),
        key_map_digest=key_map_digest,
    )
    card = (
        "---\n"
        f"base_model: {base_model.repo_id}\n"
        f"base_model_revision: {base_model.revision}\n"
        "library_name: peft\n"
        "tags:\n  - peft\n  - lora\n  - obliteratus\n"
        "---\n\n"
        "# OBLITERATUS LoRA adapter\n\n"
        "This is an unmerged PEFT LoRA artifact representing an OBLITERATUS surgery event.\n\n"
        f"- Exact base: `{base_model.repo_id}@{base_model.revision}`\n"
        f"- Base weights: `{base_model.weights_digest}`\n"
        f"- Tokenizer: `{base_model.tokenizer_digest}`\n"
        "- Scaling: standard PEFT `alpha / rank`; saved B values preserve the exact delta.\n"
    ).encode("utf-8")
    manifest = {
        "schema_id": "obliteratus.peft-adapter-manifest",
        "schema_version": "1.0.0",
        "adapter_name": adapter_name,
        "adapter_type": "lora",
        "adapter_format_version": "peft-lora-v1",
        "base_model": base_model.to_dict(),
        "rank": rank,
        "alpha": alpha,
        "scaling": scaling,
        "dropout": float(lora_dropout),
        "bias": "none",
        "modules_to_save": [],
        "target_modules": config["target_modules"],
        "tie_policy": "base_model_declared",
        "merged": False,
        "key_map_digest": key_map_digest,
        "model_card_digest": _digest_bytes(card),
        "key_map": key_map,
    }
    manifest_payload = _json_bytes(manifest)
    artifact_id = ""

    def validate_staging(staging: Path) -> None:
        expected = {
            "README.md",
            "adapter_config.json",
            "adapter_manifest.json",
            "adapter_model.safetensors",
            "checkpoint-provenance.json",
        }
        paths = tuple(staging.iterdir())
        if {path.name for path in paths} != expected or any(
            path.is_symlink() or not path.is_file() for path in paths
        ):
            raise ValueError("adapter artifact set is incomplete")
        loaded = load_file(staging / "adapter_model.safetensors", device="cpu")
        if set(loaded) != set(state):
            raise ValueError("adapter tensor set does not match the manifest")
        validate_adapter_base(staging, base_model)

    with atomic_checkpoint_directory(output_path, validate=validate_staging) as staging:
        weights_path = staging / "adapter_model.safetensors"
        config_path = staging / "adapter_config.json"
        manifest_path = staging / "adapter_manifest.json"
        provenance_path = staging / "checkpoint-provenance.json"
        card_path = staging / "README.md"
        save_file(dict(sorted(state.items())), weights_path)
        _write_new(config_path, config_payload)
        _write_new(manifest_path, manifest_payload)
        _write_new(card_path, card)
        output_digests = tuple(
            sorted(
                (
                    _digest_file(weights_path),
                    _digest_file(config_path),
                    _digest_file(manifest_path),
                    _digest_file(card_path),
                )
            )
        )
        provenance = provenance_factory(output_digests, adapter_identity)
        provenance_record = provenance.to_dict()
        if (
            provenance_record.get("base_model") != base_model.to_artifact_identity().to_dict()
            or provenance_record.get("adapter") != adapter_identity.to_dict()
            or sorted(provenance_record.get("output_digests", [])) != list(output_digests)
        ):
            raise ValueError("adapter provenance does not match the exact exported artifact")
        artifact_id = provenance.artifact_id
        _write_new(provenance_path, provenance.to_json().encode("utf-8"))
    return AdapterArtifact(
        artifact_id=artifact_id,
        weights_path=output_path / "adapter_model.safetensors",
        config_path=output_path / "adapter_config.json",
        provenance_path=output_path / "checkpoint-provenance.json",
    )


def _read_json_object(path: Path, detail: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 << 20:
        raise ValueError(detail)
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_pairs,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(detail) from error
    if not isinstance(value, dict):
        raise ValueError(detail)
    return value


def _reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_object_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return _digest_bytes(payload)


def _validate_adapter_integrity(
    root: Path,
    config: dict[str, Any],
    manifest: dict[str, Any],
    provenance: dict[str, Any],
) -> None:
    weights = root / "adapter_model.safetensors"
    artifact_paths = (
        root / "README.md",
        root / "adapter_config.json",
        root / "adapter_manifest.json",
        weights,
        root / "checkpoint-provenance.json",
    )
    if any(path.is_symlink() or not path.is_file() for path in artifact_paths):
        raise ValueError("adapter_artifact_file_invalid")
    if weights.stat().st_size == 0:
        raise ValueError("adapter_weights_invalid")
    try:
        verified_provenance = verify_provenance_record(provenance)
    except (TypeError, ValueError) as error:
        if "record digest mismatch" in str(error):
            raise ValueError("adapter_provenance_digest_mismatch") from error
        if "artifact ID mismatch" in str(error):
            raise ValueError("adapter_artifact_identity_mismatch") from error
        raise ValueError("adapter_provenance_invalid") from error
    if verified_provenance != provenance:
        raise ValueError("adapter_provenance_invalid")
    expected_outputs = provenance.get("output_digests")
    if (
        not isinstance(expected_outputs, list)
        or any(not isinstance(value, str) or not _DIGEST.fullmatch(value) for value in expected_outputs)
        or sorted(expected_outputs)
        != sorted(
            _digest_file(path)
            for path in (
                root / "README.md",
                root / "adapter_config.json",
                root / "adapter_manifest.json",
                weights,
            )
        )
    ):
        raise ValueError("adapter_artifact_digest_mismatch")
    record_digest = provenance.get("record_digest")
    record_core = {key: value for key, value in provenance.items() if key != "record_digest"}
    if record_digest != _canonical_object_digest(record_core):
        raise ValueError("adapter_provenance_digest_mismatch")
    artifact_id = provenance.get("artifact_id")
    identity_core = {key: value for key, value in record_core.items() if key != "artifact_id"}
    expected_artifact_id = _canonical_object_digest(identity_core).replace(
        "sha256:",
        "artifact-sha256:",
        1,
    )
    if artifact_id != expected_artifact_id:
        raise ValueError("adapter_artifact_identity_mismatch")
    key_map = manifest.get("key_map")
    adapter = provenance.get("adapter")
    manifest_base = manifest.get("base_model")
    if (
        not isinstance(key_map, list)
        or not isinstance(adapter, dict)
        or not isinstance(manifest_base, dict)
    ):
        raise ValueError("adapter_manifest_integrity_invalid")
    if any(
        not isinstance(item, dict)
        or not isinstance(item.get("module_name"), str)
        or not _MODULE_PATH.fullmatch(item["module_name"])
        for item in key_map
    ):
        raise ValueError("adapter_manifest_integrity_invalid")
    key_map_digest = _canonical_object_digest(key_map)
    target_modules = [
        item.get("module_name") for item in key_map if isinstance(item, dict)
    ]
    rank = manifest.get("rank")
    alpha = manifest.get("alpha")
    scaling = manifest.get("scaling")
    if (
        manifest.get("key_map_digest") != key_map_digest
        or manifest.get("model_card_digest") != _digest_file(root / "README.md")
        or adapter.get("key_map_digest") != key_map_digest
        or adapter.get("config_digest") != _digest_file(root / "adapter_config.json")
        or config.get("base_model_name_or_path") != manifest_base.get("repo_id")
        or config.get("revision") != manifest_base.get("revision")
        or manifest.get("schema_id") != "obliteratus.peft-adapter-manifest"
        or manifest.get("schema_version") != "1.0.0"
        or config.get("peft_type") != "LORA"
        or config.get("target_modules") != sorted(target_modules)
        or manifest.get("target_modules") != sorted(target_modules)
        or type(rank) is not int
        or rank <= 0
        or config.get("r") != rank
        or type(alpha) is not int
        or alpha <= 0
        or config.get("lora_alpha") != alpha
        or not isinstance(scaling, (int, float))
        or isinstance(scaling, bool)
        or not math.isfinite(scaling)
        or scaling != alpha / rank
        or config.get("lora_dropout") != manifest.get("dropout")
        or config.get("bias") != manifest.get("bias")
    ):
        raise ValueError("adapter_manifest_integrity_invalid")


def validate_adapter_base(
    adapter_dir: str | Path,
    base_model: BaseModelIdentity,
) -> dict[str, Any]:
    """Fail before loading weights when exact base/tokenizer facts do not match."""
    root = Path(adapter_dir)
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.absolute() != root.resolve(strict=True)
    ):
        raise ValueError("adapter_directory_invalid")
    config = _read_json_object(root / "adapter_config.json", "adapter_config_invalid")
    manifest = _read_json_object(root / "adapter_manifest.json", "adapter_manifest_invalid")
    provenance = _read_json_object(
        root / "checkpoint-provenance.json",
        "adapter_provenance_invalid",
    )
    _validate_adapter_integrity(root, config, manifest, provenance)
    checks = (
        (config.get("base_model_name_or_path"), base_model.repo_id, "base_model_identity_mismatch"),
        (config.get("revision"), base_model.revision, "base_model_revision_mismatch"),
        (
            manifest.get("base_model", {}).get("weights_digest"),
            base_model.weights_digest,
            "base_model_digest_mismatch",
        ),
        (
            manifest.get("base_model", {}).get("tokenizer_digest"),
            base_model.tokenizer_digest,
            "tokenizer_digest_mismatch",
        ),
        (
            manifest.get("base_model", {}).get("vocab_size"),
            base_model.vocab_size,
            "vocab_size_mismatch",
        ),
        (
            manifest.get("base_model", {}).get("architecture"),
            base_model.architecture,
            "architecture_mismatch",
        ),
        (
            manifest.get("base_model", {}).get("tied_embeddings"),
            base_model.tied_embeddings,
            "tied_embeddings_mismatch",
        ),
    )
    for actual, expected, detail in checks:
        if actual != expected:
            raise ValueError(detail)
    if provenance.get("base_model") != base_model.to_artifact_identity().to_dict():
        raise ValueError("adapter_provenance_base_mismatch")
    return manifest


def load_lora_adapters(
    adapter_dir: str | Path,
    *,
    base_model: BaseModelIdentity,
) -> dict[str, tuple[torch.Tensor, torch.Tensor]]:
    """Load canonical safetensors only; this path never accepts pickle artifacts."""
    root = Path(adapter_dir)
    manifest = validate_adapter_base(root, base_model)
    state = load_file(root / "adapter_model.safetensors", device="cpu")
    validate_adapter_base(root, base_model)
    scaling = manifest.get("scaling")
    if (
        isinstance(scaling, bool)
        or not isinstance(scaling, (int, float))
        or not math.isfinite(scaling)
        or scaling <= 0
    ):
        raise ValueError("adapter_scaling_invalid")
    result: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}
    expected_keys: set[str] = set()
    key_map = manifest.get("key_map")
    if not isinstance(key_map, list):
        raise ValueError("adapter_key_map_invalid")
    for item in key_map:
        if not isinstance(item, dict):
            raise ValueError("adapter_key_map_invalid")
        module_name = item.get("module_name")
        a_key = item.get("lora_A_key")
        b_key = item.get("lora_B_key")
        if (
            not isinstance(module_name, str)
            or not isinstance(a_key, str)
            or not isinstance(b_key, str)
            or not _MODULE_PATH.fullmatch(module_name)
            or module_name in result
            or a_key == b_key
            or a_key in expected_keys
            or b_key in expected_keys
            or a_key not in state
            or b_key not in state
        ):
            raise ValueError("adapter_key_map_invalid")
        lora_a = state[a_key]
        lora_b = state[b_key]
        if (
            lora_a.ndim != 2
            or lora_b.ndim != 2
            or lora_b.shape[1] != lora_a.shape[0]
            or lora_a.dtype != lora_b.dtype
            or item.get("lora_A_shape") != list(lora_a.shape)
            or item.get("lora_B_shape") != list(lora_b.shape)
            or item.get("rank") != lora_a.shape[0]
        ):
            raise ValueError("adapter_tensor_geometry_mismatch")
        expected_keys.update((a_key, b_key))
        result[module_name] = (lora_b * scaling, lora_a)
    if expected_keys != set(state):
        raise ValueError("adapter_tensor_set_mismatch")
    return result


def save_unsupported_obliteratus_adapters(
    adapters: dict[str, tuple[torch.Tensor, torch.Tensor]],
    output_dir: str | Path,
    *,
    reason: str,
) -> Path:
    """Persist safe legacy tensors without making a PEFT compatibility claim."""
    if not adapters:
        raise ValueError("legacy adapter export requires at least one adapter")
    if (
        not isinstance(reason, str)
        or not reason
        or len(reason) > 1024
        or _SECRET_VALUE.search(reason)
        or Path(reason).is_absolute()
    ):
        raise ValueError("legacy adapter reason is invalid")
    output = Path(output_dir)
    if output.is_symlink() or output.absolute() != output.resolve(strict=False):
        raise ValueError("adapter output directory must not be a symlink")
    output.mkdir(parents=True, exist_ok=True)
    state = {}
    key_map = []
    for module_name in sorted(adapters):
        lora_b, lora_a = adapters[module_name]
        b_key = f"{module_name}.B"
        a_key = f"{module_name}.A"
        state[b_key] = lora_b.detach().cpu().contiguous()
        state[a_key] = lora_a.detach().cpu().contiguous()
        key_map.append({"module_name": module_name, "A": a_key, "B": b_key})
    path = output / "obliteratus_unsupported_adapter.safetensors"
    config_path = output / "obliteratus_unsupported_adapter.json"
    if path.exists() or config_path.exists():
        raise FileExistsError("unsupported adapter artifact already exists")
    save_file(dict(sorted(state.items())), path)
    _write_new(
        config_path,
        _json_bytes(
            {
                "schema_id": "obliteratus.unsupported-adapter",
                "schema_version": "1.0.0",
                "support_status": "unsupported_legacy",
                "safe_serialization": True,
                "peft_compatible": False,
                "reason": reason,
                "key_map": key_map,
            }
        ),
    )
    return path


def save_legacy_pickle_adapters_trusted(
    adapters: dict[str, tuple[torch.Tensor, torch.Tensor]],
    output_dir: str | Path,
    *,
    allow_pickle: bool,
) -> Path:
    """Write the historical pickle shape only behind an explicit trust gate."""
    if allow_pickle is not True:
        raise PermissionError("allow_pickle=True is required for unsafe legacy export")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "obliteratus_legacy_adapter_unsafe.pt"
    state = {
        f"{module_name}.{suffix}": tensor
        for module_name, (lora_b, lora_a) in sorted(adapters.items())
        for suffix, tensor in (("lora_B", lora_b), ("lora_A", lora_a))
    }
    torch.save(state, path)
    return path
