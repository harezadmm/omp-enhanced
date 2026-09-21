# Complementary Abliteration Blending

**Date:** 2026-08-20
**Status:** Contributor-reported preliminary results; implementation independently tested
**Authors:** OBLITERATUS contributors and maintainers

---

## Abstract

This document describes **complementary abliteration blending**, which combines two compatible
abliterated checkpoints via weight-space interpolation. PR #127 did not include the raw benchmark
outputs, prompt-level refusal evidence, model revisions, environment capture, or artifact hashes
needed to independently reproduce its numerical results. The tables below therefore preserve the
contributor's preliminary report as context; they are not independently verified project claims.

---

## 1. Motivation

The contributor report frames abliteration as a tradeoff between refusal removal and measured
capability. Single-direction work such as [Arditi et al.][arditi] motivates the approach, while the
reported OBLITERATUS comparison observed lower MMLU for a more aggressive surgery. Raw evidence
for the specific refusal and MMLU figures was not included in PR #127.

We hypothesized that different direction-finding methods damage different parts of the model's
capability geometry, and that blending their outputs could cancel these damages.

---

## 2. Method

### 2.1 Surgery A: Aggressive/SVD

Standard OBLITERATUS aggressive pipeline with SVD-based direction extraction:

```
obliteratus obliterate $BASE --method aggressive --n-directions 3 \
  --regularization 0.08 --residue-weight 3 --refinement-passes 2 \
  --min-layer-fraction 0.45
```

**Contributor-reported properties:** deep refusal removal with measurable capability damage on a
small spot check. The proposed explanation—SVD directions overlapping capability subspaces—is a
hypothesis that requires activation and controlled model-comparison evidence.

### 2.2 Surgery B: LEACE

OBLITERATUS aggressive pipeline with LEACE (Linear Erasure of Concept Embeddings) direction method:

```
obliteratus obliterate $BASE --method aggressive --direction-method leace \
  --n-directions 3 --regularization 0.06 --residue-weight 7 \
  --refinement-passes 3 --min-layer-fraction 0.40
```

LEACE is a closed-form linear concept-erasure method designed to remove linearly available concept
information while minimizing distortion ([Belrose et al.][leace]). The contributor reported
capability retention and weaker output quality for this surgery; the asserted mechanism in the
generation pathway was not evidenced in this PR.

### 2.3 Weight-Space LERP Blend

Simple linear interpolation in weight space:

```python
for key in weight_keys:
    blended[key] = alpha * leace_weights[key] + (1 - alpha) * aggressive_weights[key]
```

The blend ratio `alpha = 0.60` was found by binary search over {0.30, 0.50, 0.55, 0.60, 0.65, 0.70}.

---

## 3. Contributor-Reported Results (Not Independently Reproduced)

No machine-readable benchmark or refusal-evaluation artifacts accompany these tables. Counts,
uncertainty, prompt selection, exact model revisions, and evaluator configuration must be supplied
before the results can support a release or research conclusion.

### 3.1 Blend Ratio Search (15-subject MMLU, 150 questions)

| Blend (% LEACE) | Refuse | Usable | MMLU  | vs Stock |
|------------------|--------|--------|-------|----------|
| 0% (pure SVD)    | 0%     | 100%   | 84.0% | -2.0pp   |
| 30%              | 0%     | 90%    | 83.3% | -2.7pp   |
| 50%              | 0%     | 100%   | 84.0% | -2.0pp   |
| 55%              | 0%     | 80%    | 84.7% | -1.3pp   |
| **60%**          | **0%** |**100%**|**86.0%**|**+0.0pp**|
| 65%              | 0%     | —      | —     | —        |
| 70%              | 0%     | 80%    | 86.7% | +0.7pp   |
| 100% (pure LEACE)| 0%     | 50%    | 86.7% | +0.7pp   |

The contributor selected the 60% blend from this small search. The evidence is insufficient to
establish a unique optimum or distinguish the apparent differences from sampling noise.

### 3.2 Larger Contributor Spot Check (57-subject MMLU, 570 questions)

| Model                | MMLU    | Stderr | vs Stock |
|----------------------|---------|--------|----------|
| Stock Qwen3.8-27B    | 85.26%  | ±0.014 | —        |
| OBLITERATUS V1 (s51) | 81.40%  | —      | -6.0pp   |
| **OBLITERATUS V2 (s78)** | **86.32%** | **±0.014** | **+1.1pp** |

### 3.3 Per-Subject Gains (5 questions/subject)

Capability gains span both safety-adjacent and neutral reasoning topics:

| Subject              | Stock | V2    | Delta  | Type      |
|----------------------|-------|-------|--------|-----------|
| College Mathematics  | 40%   | 80%   | +40pp  | Neutral   |
| Formal Logic         | 40%   | 60%   | +20pp  | Neutral   |
| Jurisprudence        | 60%   | 80%   | +20pp  | Sensitive |
| Business Ethics      | 80%   | 100%  | +20pp  | Sensitive |
| Professional Law     | 80%   | 100%  | +20pp  | Sensitive |

The reported neutral-topic gains motivate a controlled follow-up; five questions per subject are
not sufficient to establish capability improvement or rule out sampling variation.

### 3.4 Real-World Practical Tasks

| Test Suite          | Stock | V2  | Tasks                                    |
|---------------------|-------|-----|------------------------------------------|
| Basic (8 tasks)     | 5/8   | 6/8 | Code, SQL, tool calling, JSON, math      |
| Advanced (8 tasks)  | 7/8   | 7/8 | ReAct agents, async refactor, K8s debug, |
|                     |       |     | security review, system design           |

The contributor reported comparable outcomes on this small practical-task set. The tasks and raw
outputs were not included, so maintainers have not independently verified that comparison.

---

## 4. Why It Works

### 4.1 Complementary Error Cancellation

One hypothesis is that SVD and LEACE make different errors in weight space:

- **SVD** greedily captures maximum variance directions. Some captured variance encodes
  capability, not just refusal. This damages specific weight regions.
- **LEACE** minimizes a linear erasure objective. Whether it leaves specific residue in attention
  heads or output projections must be measured rather than inferred from output behavior.

Weight-space interpolation may average complementary errors:
- Where SVD damaged capability, LEACE's intact weights dilute the damage
- Where LEACE left refusal residue, SVD's clean weights dilute the residue

### 4.2 Theoretical Connection to Model Merging

This technique is related to model-merging work such as [Model Soups][model-soups] and
[TIES-Merging][ties], but is applied within the abliteration domain. PR #127 does not measure
task-vector orthogonality or error anti-correlation, so those remain testable explanations rather
than established properties.

### 4.3 Capacity Hypothesis

The contributor-reported MMLU difference raises several competing hypotheses. A separate,
provenance-gated experiment framework is tracked in [issue #132][capacity-issue]:

1. **Activation Rank Analysis** — Does effective dimensionality increase after abliteration?
2. **Topic Cluster Analysis** — Do gains cluster on sensitive topics (hedging) or spread broadly (capacity)?
3. **Blend Control** — Does blending two identical SVD surgeries also gain MMLU? (Tests regularization hypothesis)
4. **Learning Absorption** — Does the abliterated model learn new information faster? (Tests freed capacity directly)

The small per-subject report does not distinguish these hypotheses.

---

## 5. Reproducibility

```bash
# Step 1: Aggressive surgery
obliteratus obliterate $BASE --method aggressive --n-directions 3 \
  --regularization 0.08 --residue-weight 3 --refinement-passes 2 \
  --min-layer-fraction 0.45 --output-dir surgery_a

# Step 2: LEACE surgery
obliteratus obliterate $BASE --method aggressive --direction-method leace \
  --n-directions 3 --regularization 0.06 --residue-weight 7 \
  --refinement-passes 3 --min-layer-fraction 0.40 --output-dir surgery_b

# Step 3: Blend
obliteratus blend --model-a surgery_a --model-b surgery_b --alpha 0.6 \
  --config-source a --output blended_model

# Step 4: Validate
lm_eval --model hf --model_args pretrained=blended_model --tasks mmlu
```

The command requires matching `source_model` values in both checkpoints'
`abliteration_metadata.json`, identical tensor keys, compatible shapes/dtypes, floating-point
weights, and sharded safetensors indexes. For legacy checkpoints whose common lineage was verified
out of band, `--allow-unverified-lineage` is an explicit escape hatch. Output is staged and
validated before atomically replacing any existing destination.

---

## 6. Limitations

- Contributor measurements cover only Qwen3.8-27B; independent validation is pending
- MMLU is a multiple-choice benchmark; gains may not transfer to all downstream tasks
- The 60/40 blend ratio may be model-specific
- `repetition_penalty=1.15` is still required for clean generation
- System prompts still reintroduce refusals
- Full 842-corpus validation in progress at time of writing
- The numerical results lack committed raw evidence and independent reproduction
- Single-file and quantized/integer checkpoints are not supported by the current blender
- Atomic promotion temporarily requires space for the complete staged output and any prior output

---

## 7. Future Work

- **Cross-architecture validation** on Llama, Gemma, Mistral
- **SLERP blending** instead of LERP (spherical interpolation may better preserve weight norms)
- **Three-way blends** with additional direction methods (diff_means, SOM)
- **Post-blend recovery**, tracked separately in [issue #133][recovery-issue]
- **Formal capacity-hypothesis validation**, tracked in [issue #132][capacity-issue]

## References

- [Arditi et al., *Refusal in Language Models Is Mediated by a Single Direction*][arditi]
- [Belrose et al., *LEACE: Perfect Linear Concept Erasure in Closed Form*][leace]
- [Wortsman et al., *Model Soups*][model-soups]
- [Yadav et al., *TIES-Merging*][ties]

[arditi]: https://arxiv.org/abs/2406.11717
[leace]: https://arxiv.org/abs/2306.03819
[model-soups]: https://proceedings.mlr.press/v162/wortsman22a.html
[ties]: https://arxiv.org/abs/2306.01708
[capacity-issue]: https://github.com/elder-plinius/OBLITERATUS/issues/132
[recovery-issue]: https://github.com/elder-plinius/OBLITERATUS/issues/133
