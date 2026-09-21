"""Integration with EleutherAI's lm-evaluation-harness for real benchmarks.

The built-in benchmark probes in benchmarks.py are fast screening tools
(~25 items each). For publication-quality evaluation, use this module to
run standard benchmarks: MMLU, HellaSwag, TruthfulQA, GSM8K, Winogrande.

Requirements:
    pip install lm-eval>=0.4.0

Usage:
    from obliteratus.evaluation.lm_eval_integration import run_benchmarks

    results = run_benchmarks(
        model_path="./abliterated",
        tasks=["mmlu", "hellaswag", "truthfulqa_mc2"],
        device="cuda",
    )
    for task, score in results.items():
        print(f"  {task}: {score:.1%}")

For pre/post comparison:
    original = run_benchmarks("meta-llama/Llama-3.1-8B-Instruct", ...)
    abliterated = run_benchmarks("./abliterated", ...)
    for task in original:
        delta = abliterated[task] - original[task]
        print(f"  {task}: {original[task]:.1%} -> {abliterated[task]:.1%} ({delta:+.1%})")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Standard benchmark suite for abliteration evaluation
DEFAULT_TASKS = [
    "mmlu",           # Knowledge (Hendrycks et al. 2021)
    "hellaswag",      # Commonsense (Zellers et al. 2019)
    "truthfulqa_mc2", # Truthfulness (Lin et al. 2022)
    "gsm8k",          # Math (Cobbe et al. 2021) — most sensitive to abliteration
    "winogrande",     # Coreference (Sakaguchi et al. 2020)
]


def run_benchmarks(
    model_path: str | Path,
    tasks: list[str] | None = None,
    device: str = "cuda",
    batch_size: int | str = "auto",
    num_fewshot: int | None = None,
    limit: int | None = None,
) -> dict[str, float]:
    """Run lm-evaluation-harness benchmarks on a model.

    Args:
        model_path: HuggingFace model name or local path.
        tasks: Benchmark tasks to run (default: MMLU + HellaSwag + TruthfulQA + GSM8K + Winogrande).
        device: Device for inference.
        batch_size: Batch size ("auto" for automatic).
        num_fewshot: Override few-shot count (None = use task default).
        limit: Max samples per task (None = full benchmark, set lower for quick screening).

    Returns:
        Dict mapping task name to accuracy score (0-1).

    Raises:
        ImportError: If lm-eval is not installed.
    """
    try:
        import lm_eval
    except ImportError:
        raise ImportError(
            "lm-evaluation-harness is required for real benchmarks.\n"
            "Install with: pip install lm-eval>=0.4.0\n"
            "Or use obliteratus.evaluation.benchmarks for fast screening probes."
        )

    tasks = tasks or DEFAULT_TASKS
    model_path = str(model_path)

    logger.info("Running benchmarks: %s on %s", tasks, model_path)

    model_args = f"pretrained={model_path}"
    if device != "cuda":
        model_args += f",device={device}"

    kwargs: dict[str, Any] = {
        "model": "hf",
        "model_args": model_args,
        "tasks": tasks,
        "batch_size": batch_size,
    }
    if num_fewshot is not None:
        kwargs["num_fewshot"] = num_fewshot
    if limit is not None:
        kwargs["limit"] = limit

    results = lm_eval.simple_evaluate(**kwargs)

    # Extract accuracy from each task
    scores: dict[str, float] = {}
    for task_name, task_result in results.get("results", {}).items():
        # lm-eval uses "acc" or "acc_norm" depending on the task
        acc = task_result.get("acc,none")
        if acc is None:
            acc = task_result.get("acc_norm,none")
        if acc is not None:
            scores[task_name] = acc
        else:
            # Fall back to first numeric metric
            for key, val in task_result.items():
                if isinstance(val, (int, float)) and not key.startswith("alias"):
                    scores[task_name] = val
                    break

    return scores


def compare_models(
    original_path: str | Path,
    abliterated_path: str | Path,
    tasks: list[str] | None = None,
    **kwargs,
) -> dict[str, dict[str, float]]:
    """Run benchmarks on original and abliterated models and compare.

    Returns:
        Dict with per-task results: {"task": {"original": x, "abliterated": y, "delta": y-x}}.
    """
    original = run_benchmarks(original_path, tasks=tasks, **kwargs)
    abliterated = run_benchmarks(abliterated_path, tasks=tasks, **kwargs)

    comparison: dict[str, dict[str, float]] = {}
    all_tasks = set(original.keys()) | set(abliterated.keys())
    for task in sorted(all_tasks):
        orig = original.get(task, 0.0)
        abli = abliterated.get(task, 0.0)
        comparison[task] = {
            "original": orig,
            "abliterated": abli,
            "delta": abli - orig,
        }

    return comparison
