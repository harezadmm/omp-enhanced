#!/usr/bin/env python3
"""OBLITERATUS vs SOTA — Head-to-Head Benchmark Comparison.

Runs faithful reproductions of competing abliteration methods against
OBLITERATUS variants on any specified model, producing publication-ready
comparison tables with standardized community metrics.

Baselines included:
  1. FailSpy/abliterator (2024) — Community workhorse baseline
  2. Gabliteration (Gülmez 2026) — SVD multi-direction + ridge regularization
  3. Heretic / p-e-w (2025) — Bayesian TPE auto-tuning (current SOTA for quality)
  4. Wollschlager RDO (ICML 2025) — Gradient-based direction optimization

OBLITERATUS variants:
  5. OBLITERATUS surgical — Full SOTA MoE-aware pipeline
  6. OBLITERATUS informed — Analysis-guided auto-configuration
  7. OBLITERATUS optimized — Bayesian + whitened SVD + SAE (max OBLITERATUS)

Evaluation protocol (Heretic community standard):
  - Refusal rate via substring + prefix detection
  - First-token KL divergence on harmless prompts
  - Capability probes (knowledge, truthfulness, math reasoning)
  - Optional: HarmBench ASR, lm-eval-harness benchmarks

Usage:
    # Quick comparison (small model, few prompts)
    python scripts/benchmark_sota_comparison.py --model Qwen/Qwen2.5-1.5B-Instruct --quick

    # Full comparison on 8B model
    python scripts/benchmark_sota_comparison.py --model meta-llama/Llama-3.1-8B-Instruct

    # Specific baselines only
    python scripts/benchmark_sota_comparison.py --methods failspy heretic surgical

    # Custom prompt count and output
    python scripts/benchmark_sota_comparison.py --prompts 100 --output results.json

    # Include full Heretic evaluation protocol (HarmBench, lm-eval)
    python scripts/benchmark_sota_comparison.py --full-eval
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch

# Ensure the project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from obliteratus.abliterate import (  # noqa: E402
    AbliterationPipeline,
    METHODS,
    HARMFUL_PROMPTS,
    HARMLESS_PROMPTS,
)
from obliteratus.evaluation.benchmarks import BenchmarkRunner  # noqa: E402


# ── All methods available for comparison ──────────────────────────────

# Baselines (reproductions of competing methods)
BASELINE_METHODS = ["failspy", "gabliteration", "heretic", "rdo"]

# OBLITERATUS variants
OBLITERATUS_METHODS = ["surgical", "informed", "optimized"]

# Default comparison set
DEFAULT_METHODS = BASELINE_METHODS + OBLITERATUS_METHODS

# Quick mode: skip slow methods (Bayesian optimization)
QUICK_METHODS = ["failspy", "gabliteration", "rdo", "surgical"]


@dataclass
class MethodResult:
    """Results for a single method run."""
    method: str
    label: str
    refusal_rate: float = 0.0
    kl_divergence: float = 0.0
    knowledge_score: float = 0.0
    truthfulness_score: float = 0.0
    math_score: float = 0.0
    ablation_time_s: float = 0.0
    peak_gpu_mb: float = 0.0
    n_layers_modified: int = 0
    n_projections: int = 0
    error: str | None = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="OBLITERATUS vs SOTA — Head-to-Head Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model", default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Model to benchmark (default: Qwen/Qwen2.5-1.5B-Instruct)",
    )
    parser.add_argument(
        "--methods", nargs="+", default=None,
        help=f"Methods to compare (default: all). Available: {', '.join(DEFAULT_METHODS)}",
    )
    parser.add_argument(
        "--prompts", type=int, default=None,
        help="Number of prompts for abliteration (default: auto based on --quick)",
    )
    parser.add_argument(
        "--eval-prompts", type=int, default=20,
        help="Number of prompts for refusal rate evaluation (default: 20)",
    )
    parser.add_argument(
        "--kl-prompts", type=int, default=10,
        help="Number of harmless prompts for KL divergence (default: 10)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output JSON file for results (default: stdout only)",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: fewer prompts, skip slow methods (Bayesian opt)",
    )
    parser.add_argument(
        "--full-eval", action="store_true",
        help="Run full Heretic evaluation protocol (HarmBench ASR, lm-eval)",
    )
    parser.add_argument(
        "--quantization", default=None, choices=["4bit", "8bit"],
        help="Quantization for model loading (default: auto)",
    )
    parser.add_argument(
        "--device", default="auto",
        help="Device (default: auto)",
    )
    parser.add_argument(
        "--dtype", default="float16",
        help="Data type (default: float16)",
    )
    parser.add_argument(
        "--output-dir", default="/tmp/obliteratus_benchmark",
        help="Directory for abliterated model outputs (default: /tmp/obliteratus_benchmark)",
    )
    parser.add_argument(
        "--keep-models", action="store_true",
        help="Keep abliterated models after benchmark (default: delete to save disk)",
    )
    return parser.parse_args()


def measure_refusal_rate(
    pipeline: AbliterationPipeline,
    prompts: list[str],
    max_new_tokens: int = 128,
) -> float:
    """Measure refusal rate on a set of prompts."""
    from obliteratus.evaluation.advanced_metrics import refusal_rate
    model = pipeline.handle.model
    tokenizer = pipeline.handle.tokenizer

    responses = []
    for prompt in prompts:
        try:
            if pipeline.use_chat_template and hasattr(tokenizer, "apply_chat_template"):
                messages = [{"role": "user", "content": prompt}]
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                )
            else:
                text = prompt

            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    temperature=1.0,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                )
            response = tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
            )
            responses.append(response)
        except Exception as e:
            responses.append(f"[ERROR: {e}]")

    return refusal_rate(responses, mode="combined")


def measure_kl_divergence(
    pipeline: AbliterationPipeline,
    original_logits: dict[int, torch.Tensor],
    prompts: list[str],
) -> float:
    """Measure first-token KL divergence vs original model logits."""
    import torch.nn.functional as F
    model = pipeline.handle.model
    tokenizer = pipeline.handle.tokenizer

    kl_values = []
    for i, prompt in enumerate(prompts):
        if i not in original_logits:
            continue
        try:
            if pipeline.use_chat_template and hasattr(tokenizer, "apply_chat_template"):
                messages = [{"role": "user", "content": prompt}]
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                )
            else:
                text = prompt

            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model(**inputs)
                new_logits = outputs.logits[0, -1, :].float().cpu()

            orig = original_logits[i].float()
            log_p = F.log_softmax(orig, dim=-1)
            log_q = F.log_softmax(new_logits, dim=-1)
            kl = F.kl_div(log_q, log_p.exp(), reduction="sum").item()
            if kl >= 0:  # KL should be non-negative
                kl_values.append(kl)
        except Exception:
            pass

    return sum(kl_values) / len(kl_values) if kl_values else float("nan")


def collect_baseline_logits(
    pipeline: AbliterationPipeline,
    prompts: list[str],
) -> dict[int, torch.Tensor]:
    """Collect first-token logits from the original (pre-abliteration) model."""
    model = pipeline.handle.model
    tokenizer = pipeline.handle.tokenizer
    logits = {}

    for i, prompt in enumerate(prompts):
        try:
            if pipeline.use_chat_template and hasattr(tokenizer, "apply_chat_template"):
                messages = [{"role": "user", "content": prompt}]
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                )
            else:
                text = prompt

            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model(**inputs)
                logits[i] = outputs.logits[0, -1, :].float().cpu()
        except Exception:
            pass

    return logits


def run_single_method(
    model_name: str,
    method: str,
    harmful_prompts: list[str],
    harmless_prompts: list[str],
    eval_harmful: list[str],
    eval_harmless: list[str],
    args: argparse.Namespace,
) -> MethodResult:
    """Run a single abliteration method and collect metrics."""
    label = METHODS.get(method, {}).get("label", method)
    result = MethodResult(method=method, label=label)

    print(f"\n{'='*70}")
    print(f"  Method: {label}")
    print(f"{'='*70}")

    output_dir = Path(args.output_dir) / method

    try:
        # Track GPU memory
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        t0 = time.time()

        # Build pipeline with method-specific config
        # For 'informed', use InformedAbliterationPipeline
        if method == "informed":
            from obliteratus.informed_pipeline import InformedAbliterationPipeline
            pipeline = InformedAbliterationPipeline(
                model_name=model_name,
                output_dir=str(output_dir),
                device=args.device,
                dtype=args.dtype,
                quantization=args.quantization,
                harmful_prompts=harmful_prompts,
                harmless_prompts=harmless_prompts,
                on_log=lambda msg: print(f"    {msg}"),
            )
        else:
            pipeline = AbliterationPipeline(
                model_name=model_name,
                output_dir=str(output_dir),
                device=args.device,
                dtype=args.dtype,
                method=method,
                quantization=args.quantization,
                harmful_prompts=harmful_prompts,
                harmless_prompts=harmless_prompts,
                use_chat_template=True,
                on_log=lambda msg: print(f"    {msg}"),
            )

        # Phase 1: Load model + collect baseline KL logits
        print("  Loading model...")
        pipeline._summon()

        print("  Collecting baseline logits for KL divergence...")
        baseline_logits = collect_baseline_logits(pipeline, eval_harmless)

        # Phase 2: Run abliteration pipeline
        print("  Probing activations...")
        pipeline._probe()
        print("  Extracting refusal directions...")
        pipeline._distill()

        result.n_layers_modified = len(pipeline._strong_layers)

        print(f"  Excising refusal ({result.n_layers_modified} layers)...")
        pipeline._excise()

        result.ablation_time_s = time.time() - t0

        # Track GPU memory
        if torch.cuda.is_available():
            result.peak_gpu_mb = torch.cuda.max_memory_allocated() / 1e6

        # Phase 3: Evaluate
        print(f"  Evaluating refusal rate ({len(eval_harmful)} prompts)...")
        result.refusal_rate = measure_refusal_rate(pipeline, eval_harmful)

        print(f"  Evaluating KL divergence ({len(eval_harmless)} prompts)...")
        result.kl_divergence = measure_kl_divergence(pipeline, baseline_logits, eval_harmless)

        # Capability probes
        print("  Running capability probes...")
        try:
            runner = BenchmarkRunner(
                pipeline.handle.model,
                pipeline.handle.tokenizer,
            )
            bench_result = runner.run_all()
            result.knowledge_score = bench_result.knowledge.accuracy if bench_result.knowledge else 0.0
            result.truthfulness_score = bench_result.truthfulness.accuracy if bench_result.truthfulness else 0.0
            result.math_score = bench_result.math.accuracy if bench_result.math else 0.0
        except Exception as e:
            print(f"    Warning: capability probes failed: {e}")

        # Optional: full Heretic evaluation
        if args.full_eval:
            print("  Running full Heretic evaluation protocol...")
            try:
                from obliteratus.evaluation.heretic_eval import run_full_heretic_eval
                heretic_result = run_full_heretic_eval(
                    model=pipeline.handle.model,
                    tokenizer=pipeline.handle.tokenizer,
                    original_model=None,  # Would need original for full comparison
                )
                print(f"    Heretic eval: ASR={heretic_result.harmbench_asr:.1%}, "
                      f"JB_refusal={heretic_result.jailbreakbench_refusal_rate:.1%}")
            except Exception as e:
                print(f"    Warning: Heretic eval failed: {e}")

        print(f"  ✓ Complete: refusal={result.refusal_rate:.1%}, KL={result.kl_divergence:.4f}, "
              f"time={result.ablation_time_s:.1f}s")

    except Exception as e:
        result.error = str(e)
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up to free GPU memory for next method
        if not args.keep_models and output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    return result


def format_comparison_table(results: list[MethodResult]) -> str:
    """Format results as a publication-ready comparison table."""
    lines = []

    # Header
    lines.append("")
    lines.append("=" * 115)
    lines.append("OBLITERATUS vs SOTA — Head-to-Head Benchmark Comparison")
    lines.append("=" * 115)
    lines.append("")

    # Separator between baselines and OBLITERATUS
    lines.append(f"{'Method':<35} {'Refusal↓':>10} {'KL↓':>10} {'Know↑':>8} {'Truth↑':>8} {'Math↑':>8} {'Time':>8} {'Layers':>7}")
    lines.append("-" * 115)

    # Baselines first
    baseline_results = [r for r in results if r.method in BASELINE_METHODS]
    obliteratus_results = [r for r in results if r.method not in BASELINE_METHODS]

    if baseline_results:
        lines.append("  BASELINES:")
        for r in baseline_results:
            if r.error:
                lines.append(f"  {r.label:<33} {'FAILED':>10}  {r.error[:60]}")
            else:
                lines.append(
                    f"  {r.label:<33} {r.refusal_rate:>9.1%} {r.kl_divergence:>10.4f} "
                    f"{r.knowledge_score:>7.1%} {r.truthfulness_score:>7.1%} {r.math_score:>7.1%} "
                    f"{r.ablation_time_s:>7.1f}s {r.n_layers_modified:>6}"
                )

    if obliteratus_results:
        lines.append("  OBLITERATUS:")
        for r in obliteratus_results:
            if r.error:
                lines.append(f"  {r.label:<33} {'FAILED':>10}  {r.error[:60]}")
            else:
                lines.append(
                    f"  {r.label:<33} {r.refusal_rate:>9.1%} {r.kl_divergence:>10.4f} "
                    f"{r.knowledge_score:>7.1%} {r.truthfulness_score:>7.1%} {r.math_score:>7.1%} "
                    f"{r.ablation_time_s:>7.1f}s {r.n_layers_modified:>6}"
                )

    lines.append("-" * 115)

    # Best values
    successful = [r for r in results if r.error is None]
    if successful:
        best_refusal = min(successful, key=lambda r: r.refusal_rate)
        best_kl = min(successful, key=lambda r: r.kl_divergence if r.kl_divergence == r.kl_divergence else float("inf"))
        best_knowledge = max(successful, key=lambda r: r.knowledge_score)

        lines.append(f"  Best refusal removal: {best_refusal.label} ({best_refusal.refusal_rate:.1%})")
        lines.append(f"  Best quality preservation: {best_kl.label} (KL={best_kl.kl_divergence:.4f})")
        lines.append(f"  Best knowledge retention: {best_knowledge.label} ({best_knowledge.knowledge_score:.1%})")

    lines.append("=" * 115)
    lines.append("")

    # Metric interpretation guide
    lines.append("Metrics:")
    lines.append("  Refusal↓  = fraction of harmful prompts still refused (lower = more effective abliteration)")
    lines.append("  KL↓       = first-token KL divergence on harmless prompts (lower = better quality preservation)")
    lines.append("  Know↑     = MMLU-style knowledge probe accuracy (higher = better capability)")
    lines.append("  Truth↑    = TruthfulQA-style probe accuracy (higher = better calibration)")
    lines.append("  Math↑     = GSM8K-style math reasoning accuracy (higher = better reasoning)")
    lines.append("")

    return "\n".join(lines)


def main():
    args = parse_args()

    print("=" * 70)
    print("  OBLITERATUS vs SOTA — Head-to-Head Benchmark")
    print(f"  Model: {args.model}")
    print("=" * 70)

    # Determine methods to run
    methods = args.methods or (QUICK_METHODS if args.quick else DEFAULT_METHODS)

    # Validate methods
    valid_methods = set(METHODS.keys()) | {"informed"}
    for m in methods:
        if m not in valid_methods:
            print(f"Error: unknown method '{m}'. Available: {sorted(valid_methods)}")
            sys.exit(1)

    print(f"  Methods: {', '.join(methods)}")

    # Determine prompt counts
    n_prompts = args.prompts or (50 if args.quick else 128)
    n_prompts = min(n_prompts, len(HARMFUL_PROMPTS), len(HARMLESS_PROMPTS))

    harmful_prompts = HARMFUL_PROMPTS[:n_prompts]
    harmless_prompts = HARMLESS_PROMPTS[:n_prompts]

    # Evaluation subsets (separate from training prompts for fair comparison)
    eval_harmful = HARMFUL_PROMPTS[n_prompts:n_prompts + args.eval_prompts]
    if len(eval_harmful) < args.eval_prompts:
        # Wrap around if not enough prompts
        eval_harmful = HARMFUL_PROMPTS[:args.eval_prompts]

    eval_harmless = HARMLESS_PROMPTS[n_prompts:n_prompts + args.kl_prompts]
    if len(eval_harmless) < args.kl_prompts:
        eval_harmless = HARMLESS_PROMPTS[:args.kl_prompts]

    print(f"  Abliteration prompts: {n_prompts} harmful + {n_prompts} harmless")
    print(f"  Evaluation prompts: {len(eval_harmful)} harmful, {len(eval_harmless)} harmless")
    print()

    # Run each method
    results: list[MethodResult] = []
    for method in methods:
        result = run_single_method(
            model_name=args.model,
            method=method,
            harmful_prompts=harmful_prompts,
            harmless_prompts=harmless_prompts,
            eval_harmful=eval_harmful,
            eval_harmless=eval_harmless,
            args=args,
        )
        results.append(result)

    # Print comparison table
    table = format_comparison_table(results)
    print(table)

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "model": args.model,
            "n_prompts": n_prompts,
            "n_eval_harmful": len(eval_harmful),
            "n_eval_harmless": len(eval_harmless),
            "methods": [asdict(r) for r in results],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_data, indent=2, default=str))
        print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
