"""Smoke-load a quantized checkpoint through the OBLITERATUS loader."""

from __future__ import annotations

import argparse

import torch

from obliteratus.models import quant_dequant as qd
from obliteratus.models.loader import load_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Local checkpoint path or Hugging Face repository")
    parser.add_argument(
        "--revision",
        help="Immutable Hub commit, tag, or branch to load",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Refuse network access and use only locally cached files",
    )
    parser.add_argument(
        "--trust-remote-code",
        action="store_true",
        help=(
            "Explicitly allow checkpoint-provided Python code to execute. "
            "Off by default; review and pin the repository revision first."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    det = qd.detect_quant_scheme(
        args.repo,
        revision=args.revision,
        local_files_only=args.local_files_only,
    )
    print(
        f"[detection] {det.scheme.value} "
        f"(block_inverse={det.scale_is_inverse}, "
        f"global_inverse={det.global_scale_is_inverse}, group={det.group_size})"
    )
    if det.scheme in (qd.QuantScheme.NONE, qd.QuantScheme.UNSUPPORTED):
        raise RuntimeError(det.reason or f"checkpoint is not FP8/NVFP4: {args.repo}")

    handle = load_model(
        args.repo,
        task="causal_lm",
        device="auto",
        dtype="bfloat16",
        trust_remote_code=args.trust_remote_code,
        revision=args.revision,
        local_files_only=args.local_files_only,
    )
    model = handle.model
    print(
        "[load] ok — scheme tag: "
        f"{getattr(model, '_obliteratus_dequantized_scheme', None)}"
    )

    bad = []
    n_params = 0
    for name, param in model.named_parameters():
        n_params += 1
        if param.dtype in qd.FP8_DTYPES or param.dtype == torch.uint8:
            bad.append((name, str(param.dtype)))
        if param.data.is_floating_point() and torch.isnan(param.data).any().item():
            bad.append((name, "NaN"))
    print(f"[check] {n_params} params, quantized/NaN leftovers: {bad[:10] or 'NONE'}")
    if bad:
        raise RuntimeError(f"quantized or non-finite tensors remain: {bad[:10]}")

    if getattr(model.config, "quantization_config", None) is not None:
        raise RuntimeError("quantization_config survived dequantization")

    tokenizer = handle.tokenizer
    prompt = "The capital of France is"
    try:
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    except Exception:
        ids = tokenizer.encode(prompt, return_tensors="pt").to(model.device)
        inputs = {"input_ids": ids}
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=16, do_sample=False)
    text = tokenizer.decode(
        output[0][-16:] if output.dim() > 1 else output[-16:],
        skip_special_tokens=True,
    )
    print(f"[generate] {text!r}")
    print("SMOKE_LOAD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
