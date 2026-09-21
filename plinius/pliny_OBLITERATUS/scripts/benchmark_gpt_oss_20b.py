#!/usr/bin/env python3
"""OBLITERATUS GPT-OSS 20B Benchmark — Full Method Comparison.

Runs all abliteration methods on openai/gpt-oss-20b and produces a
comprehensive comparison table with:
  - Refusal rate (primary metric)
  - KL divergence / perplexity (capability preservation)
  - Capability probes (knowledge, truthfulness, math reasoning)
  - MoE-specific metrics (EGA expert directions, router stability)
  - Timing and GPU memory usage

Usage:
    python scripts/benchmark_gpt_oss_20b.py
    python scripts/benchmark_gpt_oss_20b.py --methods basic surgical optimized nuclear
    python scripts/benchmark_gpt_oss_20b.py --prompts 50 --output results.json
    python scripts/benchmark_gpt_oss_20b.py --quick  # fast mode: 20 prompts, skip slow methods

Designed for T4 16GB (auto 4-bit quantization) or A10G+ (float16).
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import sys
import time
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
from obliteratus.evaluation.benchmarks import BenchmarkRunner, format_benchmark_report  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="OBLITERATUS GPT-OSS 20B Benchmark")
    parser.add_argument(
        "--model", default="openai/gpt-oss-20b",
        help="Model to benchmark (default: openai/gpt-oss-20b)",
    )
    parser.add_argument(
        "--methods", nargs="+",
        default=["basic", "advanced", "surgical", "optimized", "inverted", "nuclear"],
        help="Methods to compare",
    )
    parser.add_argument(
        "--prompts", type=int, default=33,
        help="Number of prompts per side (harmful/harmless)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Save results JSON to this path",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: 20 prompts, skip aggressive/inverted",
    )
    parser.add_argument(
        "--skip-benchmarks", action="store_true",
        help="Skip capability benchmark probes (faster)",
    )
    parser.add_argument(
        "--output-dir", default="/tmp/obliteratus_bench",
        help="Directory for temporary model outputs",
    )
    parser.add_argument(
        "--bayesian-trials", type=int, default=30,
        help="Number of Bayesian optimization trials for 'optimized' method",
    )
    return parser.parse_args()


def gpu_info() -> dict:
    """Get GPU information."""
    if not torch.cuda.is_available():
        return {"gpu": "CPU only", "total_gb": 0, "free_gb": 0}
    return {
        "gpu": torch.cuda.get_device_name(0),
        "total_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1),
        "free_gb": round(torch.cuda.mem_get_info(0)[0] / 1e9, 1),
    }


def cleanup():
    """Force GPU memory cleanup."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()


def run_single_method(
    model_name: str,
    method: str,
    harmful: list[str],
    harmless: list[str],
    output_dir: str,
    run_benchmarks: bool = True,
    bayesian_trials: int = 30,
) -> dict:
    """Run a single abliteration method and collect metrics."""
    cleanup()

    outdir = f"{output_dir}/{method}"
    t0 = time.time()
    pipeline = None
    result = {
        "model": model_name,
        "method": method,
        "label": METHODS.get(method, {}).get("label", method),
    }

    try:
        # For the optimized method, we might want to control trial count
        if method == "optimized":
            # Temporarily patch bayesian_trials in the method config
            METHODS["optimized"]["bayesian_trials"] = bayesian_trials

        pipeline = AbliterationPipeline(
            model_name=model_name,
            output_dir=outdir,
            device="auto",
            dtype="float16",
            method=method,
            harmful_prompts=harmful,
            harmless_prompts=harmless,
            on_log=lambda msg: print(f"  {msg}"),
        )
        pipeline.run()
        elapsed = time.time() - t0

        result.update({
            "time_seconds": round(elapsed, 1),
            "quality": dict(pipeline._quality_metrics),
            "strong_layers": pipeline._strong_layers,
            "n_strong_layers": len(pipeline._strong_layers),
            "n_directions": pipeline.n_directions,
        })

        # MoE-specific metrics
        if pipeline._expert_directions:
            n_expert_dirs = sum(len(d) for d in pipeline._expert_directions.values())
            result["ega_expert_dirs"] = n_expert_dirs
            result["ega_layers"] = len(pipeline._expert_directions)

        if pipeline._expert_safety_scores:
            result["expert_classified_layers"] = len(pipeline._expert_safety_scores)

        if pipeline._cot_preserve_directions:
            result["cot_preserved_layers"] = len(pipeline._cot_preserve_directions)

        if pipeline._float_layer_weights:
            result["float_layer_weights"] = {
                str(k): round(v, 3) for k, v in pipeline._float_layer_weights.items()
            }

        if pipeline._kl_contributions:
            result["kl_contributions"] = {
                str(k): round(v, 6) for k, v in pipeline._kl_contributions.items()
            }

        if pipeline._lora_adapters:
            result["lora_adapters"] = len(pipeline._lora_adapters)

        if pipeline._steering_hooks:
            result["steering_hooks"] = len(pipeline._steering_hooks)

        # GPU memory
        if torch.cuda.is_available():
            result["peak_gpu_mb"] = round(torch.cuda.max_memory_allocated() / 1e6, 1)

        # Capability benchmarks (optional)
        if run_benchmarks:
            print("\n  Running capability benchmarks...")
            try:
                runner = BenchmarkRunner(
                    pipeline.handle.model,
                    pipeline.handle.tokenizer,
                )
                bench_results = runner.run_all()
                result["benchmarks"] = {
                    name: {
                        "score": round(br.score, 3),
                        "n_correct": br.n_correct,
                        "n_total": br.n_total,
                        "per_category": {
                            k: round(v, 3) for k, v in br.per_category.items()
                        },
                    }
                    for name, br in bench_results.items()
                }
                report = format_benchmark_report(bench_results)
                print(f"\n{report}")
            except Exception as e:
                print(f"  Benchmark probes failed: {e}")
                result["benchmarks"] = {"error": str(e)}

        print(f"\n  === {method} complete in {elapsed:.1f}s ===")
        print(f"  Quality: {json.dumps(pipeline._quality_metrics, default=str)}")

    except Exception as e:
        elapsed = time.time() - t0
        result.update({
            "time_seconds": round(elapsed, 1),
            "error": str(e),
        })
        print(f"\n  === {method} FAILED after {elapsed:.1f}s: {e} ===")
        import traceback
        traceback.print_exc()

    # Cleanup saved model to free disk
    shutil.rmtree(outdir, ignore_errors=True)

    if pipeline is not None:
        del pipeline
    cleanup()

    return result


def print_summary_table(results: list[dict]):
    """Print a formatted comparison table."""
    print(f"\n{'='*90}")
    print("BENCHMARK RESULTS SUMMARY")
    print(f"{'='*90}")

    # Header
    header = (
        f"{'Method':<12} {'Time':>7} {'PPL':>8} {'Coher':>7} "
        f"{'Refusal':>8} {'Know':>6} {'Truth':>6} {'Math':>6} "
        f"{'EGA':>5} {'CoT':>4} {'GPU MB':>7}"
    )
    print(header)
    print("-" * len(header))

    for r in results:
        method = r["method"]
        time_s = f"{r['time_seconds']:.0f}s" if "time_seconds" in r else "N/A"

        if "error" in r:
            print(f"{method:<12} {time_s:>7} {'FAILED':>8}")
            continue

        q = r.get("quality", {})
        ppl = q.get("perplexity")
        coh = q.get("coherence")
        ref = q.get("refusal_rate")
        gpu = r.get("peak_gpu_mb")

        # Benchmark scores
        bench = r.get("benchmarks", {})
        know = bench.get("knowledge", {}).get("score")
        truth = bench.get("truthfulness", {}).get("score")
        math = bench.get("math_reasoning", {}).get("score")

        # MoE metrics
        ega = r.get("ega_expert_dirs", "")
        cot = r.get("cot_preserved_layers", "")

        ppl_s = f"{ppl:.1f}" if ppl is not None else "N/A"
        coh_s = f"{coh:.0%}" if coh is not None else "N/A"
        ref_s = f"{ref:.0%}" if ref is not None else "N/A"
        know_s = f"{know:.0%}" if know is not None else "N/A"
        truth_s = f"{truth:.0%}" if truth is not None else "N/A"
        math_s = f"{math:.0%}" if math is not None else "N/A"
        gpu_s = f"{gpu:.0f}" if gpu is not None else "N/A"
        ega_s = str(ega) if ega else "-"
        cot_s = str(cot) if cot else "-"

        print(
            f"{method:<12} {time_s:>7} {ppl_s:>8} {coh_s:>7} "
            f"{ref_s:>8} {know_s:>6} {truth_s:>6} {math_s:>6} "
            f"{ega_s:>5} {cot_s:>4} {gpu_s:>7}"
        )

    print(f"{'='*90}")

    # Legend
    print("\nLegend:")
    print("  PPL     = Perplexity (lower = better capability preservation)")
    print("  Coher   = Coherence score (higher = more coherent text)")
    print("  Refusal = Refusal rate on harmful prompts (lower = more abliterated)")
    print("  Know    = MMLU-style knowledge probe")
    print("  Truth   = TruthfulQA-style truthfulness probe")
    print("  Math    = GSM8K-style math reasoning probe")
    print("  EGA     = Expert-Granular Abliteration directions computed")
    print("  CoT     = Layers where CoT reasoning was preserved")
    print("  GPU MB  = Peak GPU memory usage")


def main():
    args = parse_args()

    if args.quick:
        args.prompts = 20
        args.methods = [m for m in args.methods if m not in ("aggressive", "inverted")]
        args.bayesian_trials = 15

    gpu = gpu_info()
    harmful = HARMFUL_PROMPTS[:args.prompts]
    harmless = HARMLESS_PROMPTS[:args.prompts]

    print("=" * 60)
    print("  OBLITERATUS GPT-OSS 20B BENCHMARK")
    print("=" * 60)
    print(f"  Model:     {args.model}")
    print(f"  Methods:   {args.methods}")
    print(f"  Prompts:   {args.prompts} per side")
    print(f"  GPU:       {gpu['gpu']} ({gpu['total_gb']} GB total, {gpu['free_gb']} GB free)")
    print(f"  Benchmarks: {'skip' if args.skip_benchmarks else 'enabled'}")
    if "optimized" in args.methods:
        print(f"  Bayesian:  {args.bayesian_trials} trials")
    print("=" * 60)

    all_results = []

    for method in args.methods:
        if method not in METHODS:
            print(f"\nSKIP: unknown method '{method}'")
            continue

        print(f"\n{'━'*60}")
        print(f"  METHOD: {method} — {METHODS[method]['label']}")
        print(f"{'━'*60}")

        result = run_single_method(
            model_name=args.model,
            method=method,
            harmful=harmful,
            harmless=harmless,
            output_dir=args.output_dir,
            run_benchmarks=not args.skip_benchmarks,
            bayesian_trials=args.bayesian_trials,
        )
        all_results.append(result)

    # Summary
    print_summary_table(all_results)

    # Save JSON
    output_path = args.output or f"benchmark_gpt_oss_{int(time.time())}.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nFull results saved to: {output_path}")


if __name__ == "__main__":
    main()
