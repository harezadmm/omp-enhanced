"""Tests for the community-standard (Heretics/Arditi) evaluation protocol."""

from __future__ import annotations

import pytest
import torch

from obliteratus.evaluation.heretic_eval import (
    ARDITI_REFUSAL_SUBSTRINGS,
    _DEFAULT_HARMLESS_PROMPTS,
    _HARMBENCH_CLS_TEMPLATE,
    _JAILBREAKBENCH_BUILTIN,
    _extract_score,
    _last_real_token_indices,
    _sanitize_model_path,
    arditi_refusal_rate,
    first_token_kl_on_prompts,
    format_comparison_table,
    HereticComparisonResult,
    LM_EVAL_BENCHMARKS,
    load_jailbreakbench_prompts,
    unload_harmbench_classifier,
)


# ---------------------------------------------------------------------------
# JailbreakBench Prompts
# ---------------------------------------------------------------------------

class TestJailbreakBenchPrompts:
    def test_builtin_has_100_prompts(self):
        assert len(_JAILBREAKBENCH_BUILTIN) == 100

    def test_builtin_all_non_empty(self):
        for i, p in enumerate(_JAILBREAKBENCH_BUILTIN):
            assert isinstance(p, str) and len(p.strip()) > 10, f"Prompt {i} is too short"

    def test_builtin_no_duplicates(self):
        assert len(set(_JAILBREAKBENCH_BUILTIN)) == len(_JAILBREAKBENCH_BUILTIN)

    def test_load_returns_list(self):
        prompts = load_jailbreakbench_prompts()
        assert isinstance(prompts, list)
        assert len(prompts) >= 100

    def test_load_caches(self):
        p1 = load_jailbreakbench_prompts()
        p2 = load_jailbreakbench_prompts()
        assert p1 == p2

    def test_load_returns_copy(self):
        """Loading should return a copy, not the cached list itself."""
        p1 = load_jailbreakbench_prompts()
        p1.append("mutated")
        p2 = load_jailbreakbench_prompts()
        assert "mutated" not in p2


# ---------------------------------------------------------------------------
# Arditi Refusal Rate
# ---------------------------------------------------------------------------

class TestArditiRefusalRate:
    def test_canonical_substring_count(self):
        """Arditi/Zou list has exactly 29 substrings."""
        assert len(ARDITI_REFUSAL_SUBSTRINGS) == 29

    def test_all_refusals(self):
        responses = [
            "I'm sorry, but I cannot help with that.",
            "I apologize for the inconvenience.",
            "As an AI, I don't do that.",
        ]
        assert arditi_refusal_rate(responses) == 1.0

    def test_no_refusals(self):
        responses = [
            "Sure, here is a step-by-step guide.",
            "The answer to your question is 42.",
            "Here you go, this should work.",
        ]
        assert arditi_refusal_rate(responses) == 0.0

    def test_empty_responses_not_refusals(self):
        """Per Zou et al. logic, empty responses have no substring match = not refusals."""
        responses = ["", "  ", ""]
        assert arditi_refusal_rate(responses) == 0.0

    def test_empty_list(self):
        assert arditi_refusal_rate([]) == 0.0

    def test_case_insensitive(self):
        responses = ["i'm sorry, but I can't help."]
        assert arditi_refusal_rate(responses) == 1.0

    def test_mixed(self):
        responses = [
            "I cannot do that.",
            "Sure, here's the info.",
            "My apologies, I'm unable to help.",
            "The capital of France is Paris.",
        ]
        rate = arditi_refusal_rate(responses)
        assert rate == 0.5  # 2/4

    def test_subtle_refusal_not_caught(self):
        """Arditi list is deliberately limited — subtle refusals should not match."""
        responses = [
            "I'd rather not help with that specific request.",
            "Let me redirect you to a more appropriate resource.",
        ]
        # These are NOT in the Arditi 29-substring list
        assert arditi_refusal_rate(responses) == 0.0


# ---------------------------------------------------------------------------
# First-Token KL Divergence
# ---------------------------------------------------------------------------

class TestFirstTokenKL:
    @pytest.fixture
    def simple_models(self):
        """Create two tiny 'models' with controllable logit distributions."""
        class FakeModel(torch.nn.Module):
            def __init__(self, peak_idx: int = 0):
                super().__init__()
                # A single parameter so next(model.parameters()).device works
                self._param = torch.nn.Parameter(torch.zeros(1))
                self._peak_idx = peak_idx

            def __call__(self, **kwargs):
                batch_size = kwargs["input_ids"].shape[0]
                seq_len = kwargs["input_ids"].shape[1]
                vocab_size = 10
                # Create a non-uniform distribution peaked at _peak_idx
                base = torch.zeros(vocab_size)
                base[self._peak_idx] = 5.0
                logits = base.unsqueeze(0).unsqueeze(0).expand(
                    batch_size, seq_len, vocab_size
                ).clone()
                return type("Output", (), {"logits": logits})()

        class FakeTokenizer:
            pad_token_id = 0
            def __call__(self, texts, return_tensors="pt", **kwargs):
                batch_size = len(texts) if isinstance(texts, list) else 1
                input_ids = torch.ones(batch_size, 5, dtype=torch.long)
                return {"input_ids": input_ids, "attention_mask": torch.ones_like(input_ids)}

        return FakeModel, FakeTokenizer

    def test_identical_models_zero_kl(self, simple_models):
        FakeModel, FakeTokenizer = simple_models
        model_a = FakeModel(peak_idx=0)
        model_b = FakeModel(peak_idx=0)
        tokenizer = FakeTokenizer()

        result = first_token_kl_on_prompts(
            model_a, model_b, tokenizer,
            ["hello", "world"],
        )
        assert abs(result["mean_kl"]) < 1e-5
        assert result["interpretation"] == "excellent (minimal collateral damage)"

    def test_different_models_positive_kl(self, simple_models):
        FakeModel, FakeTokenizer = simple_models
        model_a = FakeModel(peak_idx=0)  # peaked at vocab position 0
        model_b = FakeModel(peak_idx=5)  # peaked at vocab position 5
        tokenizer = FakeTokenizer()

        result = first_token_kl_on_prompts(
            model_a, model_b, tokenizer,
            ["test prompt"],
        )
        assert result["mean_kl"] > 0

    def test_returns_per_prompt_kl(self, simple_models):
        FakeModel, FakeTokenizer = simple_models
        model_a = FakeModel(peak_idx=0)
        model_b = FakeModel(peak_idx=3)
        tokenizer = FakeTokenizer()

        result = first_token_kl_on_prompts(
            model_a, model_b, tokenizer,
            ["a", "b", "c"],
        )
        assert len(result["per_prompt_kl"]) == 3
        assert result["std_kl"] >= 0


# ---------------------------------------------------------------------------
# HereticComparisonResult
# ---------------------------------------------------------------------------

class TestHereticComparisonResult:
    def test_dataclass_fields(self):
        r = HereticComparisonResult(
            model_name="test-model",
            method="OBLITERATUS",
            refusal_rate_arditi=0.05,
            refusal_rate_obliteratus=0.03,
            harmbench_asr=0.85,
            n_jailbreakbench=100,
            n_refusals_remaining=5,
            first_token_kl=0.15,
            kl_interpretation="excellent",
        )
        assert r.model_name == "test-model"
        assert r.method == "OBLITERATUS"
        assert r.refusal_rate_arditi == 0.05
        assert r.harmbench_asr == 0.85
        assert r.first_token_kl == 0.15

    def test_optional_fields_default_none(self):
        r = HereticComparisonResult(
            model_name="test",
            method="test",
            refusal_rate_arditi=0.0,
            refusal_rate_obliteratus=0.0,
            harmbench_asr=None,
            n_jailbreakbench=100,
            n_refusals_remaining=0,
        )
        assert r.mmlu is None
        assert r.gsm8k is None
        assert r.perplexity is None
        assert r.harmbench_per_item == []
        assert r.kl_per_prompt == []


# ---------------------------------------------------------------------------
# Comparison Table Formatting
# ---------------------------------------------------------------------------

class TestComparisonTable:
    def test_format_single_result(self):
        r = HereticComparisonResult(
            model_name="Llama-2-7B",
            method="OBLITERATUS",
            refusal_rate_arditi=0.05,
            refusal_rate_obliteratus=0.03,
            harmbench_asr=0.85,
            n_jailbreakbench=100,
            n_refusals_remaining=5,
            first_token_kl=0.15,
            kl_interpretation="excellent",
            mmlu=0.518,
            gsm8k=0.313,
        )
        table = format_comparison_table([r])
        assert "OBLITERATUS" in table
        assert "REFUSAL REMOVAL" in table
        assert "CAPABILITY PRESERVATION" in table
        assert "DISTRIBUTION QUALITY" in table
        assert "5.0%" in table  # arditi refusal rate
        assert "85.0%" in table  # harmbench asr
        assert "5/100" in table  # JBB refusals
        assert "0.1500" in table  # KL divergence

    def test_format_multiple_results(self):
        results = [
            HereticComparisonResult(
                model_name="test", method="OBLITERATUS",
                refusal_rate_arditi=0.05, refusal_rate_obliteratus=0.03,
                harmbench_asr=0.85, n_jailbreakbench=100, n_refusals_remaining=5,
            ),
            HereticComparisonResult(
                model_name="test", method="Heretic",
                refusal_rate_arditi=0.03, refusal_rate_obliteratus=0.03,
                harmbench_asr=0.90, n_jailbreakbench=100, n_refusals_remaining=3,
            ),
        ]
        table = format_comparison_table(results)
        assert "OBLITERATUS" in table
        assert "Heretic" in table

    def test_heretic_reference_numbers_present(self):
        """The comparison table should include Heretic's published reference numbers."""
        table = format_comparison_table([
            HereticComparisonResult(
                model_name="test", method="test",
                refusal_rate_arditi=0.0, refusal_rate_obliteratus=0.0,
                harmbench_asr=None, n_jailbreakbench=100, n_refusals_remaining=0,
            ),
        ])
        assert "p-e-w/heretic" in table
        assert "97/100" in table  # Original model refusal count
        assert "0.16" in table    # Heretic's KL divergence


# ---------------------------------------------------------------------------
# LM-Eval Benchmark Config
# ---------------------------------------------------------------------------

class TestLmEvalBenchmarks:
    def test_five_standard_benchmarks(self):
        assert len(LM_EVAL_BENCHMARKS) == 5

    def test_required_keys(self):
        for key, config in LM_EVAL_BENCHMARKS.items():
            assert "task" in config
            assert "num_fewshot" in config
            assert "description" in config

    def test_expected_benchmarks(self):
        expected = {"mmlu", "gsm8k", "arc_challenge", "hellaswag", "truthfulqa_mc2"}
        assert set(LM_EVAL_BENCHMARKS.keys()) == expected

    def test_fewshot_settings_match_arditi(self):
        """Few-shot settings should match Arditi et al. / Open LLM Leaderboard."""
        assert LM_EVAL_BENCHMARKS["mmlu"]["num_fewshot"] == 5
        assert LM_EVAL_BENCHMARKS["gsm8k"]["num_fewshot"] == 5
        assert LM_EVAL_BENCHMARKS["truthfulqa_mc2"]["num_fewshot"] == 0


# ---------------------------------------------------------------------------
# HarmBench Template
# ---------------------------------------------------------------------------

class TestHarmBenchTemplate:
    def test_template_has_sys_tags(self):
        """Official template requires <<SYS>> / <</SYS>> delimiters."""
        assert "<<SYS>>" in _HARMBENCH_CLS_TEMPLATE
        assert "<</SYS>>" in _HARMBENCH_CLS_TEMPLATE

    def test_template_has_seven_rules(self):
        """Official HarmBench template has exactly 7 rules."""
        rule_count = _HARMBENCH_CLS_TEMPLATE.count("\n- ")
        assert rule_count == 7

    def test_template_has_behavior_placeholder(self):
        assert "{behavior}" in _HARMBENCH_CLS_TEMPLATE

    def test_template_has_generation_placeholder(self):
        assert "{generation}" in _HARMBENCH_CLS_TEMPLATE

    def test_template_ends_with_inst_tag(self):
        assert _HARMBENCH_CLS_TEMPLATE.strip().endswith("[/INST]")

    def test_template_answer_format(self):
        """Official template uses lowercase 'yes' or 'no'."""
        assert '"yes" or "no"' in _HARMBENCH_CLS_TEMPLATE


# ---------------------------------------------------------------------------
# Score Extraction (C3 fix)
# ---------------------------------------------------------------------------

class TestExtractScore:
    def test_normal_score(self):
        assert _extract_score({"acc,none": 0.75}) == 0.75

    def test_zero_score_not_skipped(self):
        """A legitimate score of 0.0 should be returned, not treated as falsy."""
        assert _extract_score({"acc,none": 0.0}) == 0.0

    def test_fallback_to_next_key(self):
        assert _extract_score({"acc_norm,none": 0.65}) == 0.65

    def test_mc2_key(self):
        assert _extract_score({"mc2,none": 0.42}) == 0.42

    def test_no_matching_key(self):
        assert _extract_score({"unknown_metric": 0.99}) == 0.0

    def test_priority_order(self):
        """acc,none should take priority over acc_norm,none."""
        result = _extract_score({"acc,none": 0.5, "acc_norm,none": 0.9})
        assert result == 0.5


# ---------------------------------------------------------------------------
# Padding-Aware Last-Token Indices
# ---------------------------------------------------------------------------

class TestLastRealTokenIndices:
    def test_no_padding(self):
        mask = torch.ones(3, 5, dtype=torch.long)
        indices = _last_real_token_indices(mask)
        assert indices.tolist() == [4, 4, 4]

    def test_with_padding(self):
        mask = torch.tensor([
            [1, 1, 1, 1, 1],  # length 5, last real = index 4
            [1, 1, 1, 0, 0],  # length 3, last real = index 2
            [1, 0, 0, 0, 0],  # length 1, last real = index 0
        ])
        indices = _last_real_token_indices(mask)
        assert indices.tolist() == [4, 2, 0]

    def test_single_token(self):
        mask = torch.tensor([[1]])
        indices = _last_real_token_indices(mask)
        assert indices.tolist() == [0]


# ---------------------------------------------------------------------------
# Model Path Sanitization
# ---------------------------------------------------------------------------

class TestSanitizeModelPath:
    def test_normal_path(self):
        assert _sanitize_model_path("/tmp/my-model") == "/tmp/my-model"

    def test_hf_model_id(self):
        assert _sanitize_model_path("meta-llama/Llama-2-7b-hf") == "meta-llama/Llama-2-7b-hf"

    def test_rejects_commas(self):
        with pytest.raises(ValueError, match="commas"):
            _sanitize_model_path("evil,trust_remote_code=True")


# ---------------------------------------------------------------------------
# Classifier Unload
# ---------------------------------------------------------------------------

class TestClassifierUnload:
    def test_unload_when_not_loaded(self):
        """Unloading when nothing is loaded should not raise."""
        unload_harmbench_classifier()  # should be a no-op


# ---------------------------------------------------------------------------
# Default Harmless Prompts
# ---------------------------------------------------------------------------

class TestDefaultHarmlessPrompts:
    def test_has_100_unique_prompts(self):
        assert len(_DEFAULT_HARMLESS_PROMPTS) == 100

    def test_no_duplicates(self):
        assert len(set(_DEFAULT_HARMLESS_PROMPTS)) == len(_DEFAULT_HARMLESS_PROMPTS)

    def test_all_non_empty(self):
        for i, p in enumerate(_DEFAULT_HARMLESS_PROMPTS):
            assert isinstance(p, str) and len(p) > 10, f"Prompt {i} is too short"


# ---------------------------------------------------------------------------
# KL Divergence Non-Negativity
# ---------------------------------------------------------------------------

class TestKLNonNegativity:
    @pytest.fixture
    def models_and_tokenizer(self):
        class FakeModel(torch.nn.Module):
            def __init__(self, peak_idx: int = 0):
                super().__init__()
                self._param = torch.nn.Parameter(torch.zeros(1))
                self._peak_idx = peak_idx

            def __call__(self, **kwargs):
                batch_size = kwargs["input_ids"].shape[0]
                seq_len = kwargs["input_ids"].shape[1]
                vocab_size = 10
                base = torch.zeros(vocab_size)
                base[self._peak_idx] = 5.0
                logits = base.unsqueeze(0).unsqueeze(0).expand(
                    batch_size, seq_len, vocab_size
                ).clone()
                return type("Output", (), {"logits": logits})()

        class FakeTokenizer:
            pad_token_id = 0
            def __call__(self, texts, return_tensors="pt", **kwargs):
                batch_size = len(texts) if isinstance(texts, list) else 1
                input_ids = torch.ones(batch_size, 5, dtype=torch.long)
                return {"input_ids": input_ids, "attention_mask": torch.ones_like(input_ids)}

        return FakeModel, FakeTokenizer

    def test_all_kl_values_non_negative(self, models_and_tokenizer):
        FakeModel, FakeTokenizer = models_and_tokenizer
        model_a = FakeModel(peak_idx=0)
        model_b = FakeModel(peak_idx=3)
        tokenizer = FakeTokenizer()

        result = first_token_kl_on_prompts(
            model_a, model_b, tokenizer,
            ["a", "b", "c", "d", "e"],
        )
        for val in result["per_prompt_kl"]:
            assert val >= 0.0, f"KL value {val} is negative"
