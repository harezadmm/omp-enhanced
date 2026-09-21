"""Evaluation APIs with lazy imports for optional and heavyweight boundaries."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS = {
    "Evaluator": ("obliteratus.evaluation.evaluator", "Evaluator"),
    "perplexity": ("obliteratus.evaluation.metrics", "perplexity"),
    "accuracy": ("obliteratus.evaluation.metrics", "accuracy"),
    "f1_score_metric": ("obliteratus.evaluation.metrics", "f1_score_metric"),
    "refusal_rate": ("obliteratus.evaluation.advanced_metrics", "refusal_rate"),
    "refusal_rate_with_ci": (
        "obliteratus.evaluation.advanced_metrics",
        "refusal_rate_with_ci",
    ),
    "token_kl_divergence": (
        "obliteratus.evaluation.advanced_metrics",
        "token_kl_divergence",
    ),
    "first_token_kl_divergence": (
        "obliteratus.evaluation.advanced_metrics",
        "first_token_kl_divergence",
    ),
    "effective_rank": ("obliteratus.evaluation.advanced_metrics", "effective_rank"),
    "effective_rank_change": (
        "obliteratus.evaluation.advanced_metrics",
        "effective_rank_change",
    ),
    "activation_cosine_similarity": (
        "obliteratus.evaluation.advanced_metrics",
        "activation_cosine_similarity",
    ),
    "linear_cka": ("obliteratus.evaluation.advanced_metrics", "linear_cka"),
    "refusal_projection_magnitude": (
        "obliteratus.evaluation.advanced_metrics",
        "refusal_projection_magnitude",
    ),
    "AbliterationEvalResult": (
        "obliteratus.evaluation.advanced_metrics",
        "AbliterationEvalResult",
    ),
    "format_eval_report": (
        "obliteratus.evaluation.advanced_metrics",
        "format_eval_report",
    ),
    "random_direction_ablation": (
        "obliteratus.evaluation.baselines",
        "random_direction_ablation",
    ),
    "direction_specificity_test": (
        "obliteratus.evaluation.baselines",
        "direction_specificity_test",
    ),
    "arditi_refusal_rate": ("obliteratus.evaluation.heretic_eval", "arditi_refusal_rate"),
    "harmbench_asr": ("obliteratus.evaluation.heretic_eval", "harmbench_asr"),
    "unload_harmbench_classifier": (
        "obliteratus.evaluation.heretic_eval",
        "unload_harmbench_classifier",
    ),
    "first_token_kl_on_prompts": (
        "obliteratus.evaluation.heretic_eval",
        "first_token_kl_on_prompts",
    ),
    "run_lm_eval": ("obliteratus.evaluation.heretic_eval", "run_lm_eval"),
    "load_jailbreakbench_prompts": (
        "obliteratus.evaluation.heretic_eval",
        "load_jailbreakbench_prompts",
    ),
    "run_full_heretic_eval": (
        "obliteratus.evaluation.heretic_eval",
        "run_full_heretic_eval",
    ),
    "format_comparison_table": (
        "obliteratus.evaluation.heretic_eval",
        "format_comparison_table",
    ),
    "HereticComparisonResult": (
        "obliteratus.evaluation.heretic_eval",
        "HereticComparisonResult",
    ),
    "LM_EVAL_BENCHMARKS": (
        "obliteratus.evaluation.heretic_eval",
        "LM_EVAL_BENCHMARKS",
    ),
    "run_benchmarks": (
        "obliteratus.evaluation.lm_eval_integration",
        "run_benchmarks",
    ),
    "compare_models": (
        "obliteratus.evaluation.lm_eval_integration",
        "compare_models",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
