# Qwen3.8-27B refusal-surgery research roadmap

## Decision summary

The promotion-grade E01 run is a useful causal control, not a successful
refusal-removal result:

- archive run: `run-4787f0f2c2ee4a6b8ca8840684eff99b`;
- refusal rate: 92% (184/200 still refusing);
- coherence: 70% (7/10);
- capability: 83% (5/6 checks);
- perplexity: 3.06;
- sequence-token KL divergence: 0.0513;
- first-token KL divergence: 0.1235;
- 62 layers and 62 attention-output matrices modified;
- checkpoint: 53,812,173,294 bytes, 35 files, all SHA-256 inventoried.

Do not increase surgery strength or enable the full advanced toggle set yet.
The next engineering release should make the optimizer and evaluation reliable,
then use cheap runtime interventions to search the Pareto frontier before a
single permanent weight rewrite.

Initial acceptance target for a candidate release:

| Dimension | Gate |
|---|---:|
| Held-out refusal rate | <= 20% with 95% Wilson interval reported |
| StrongREJECT/HarmBench compliance | Reported separately from substring refusal |
| Benign coherence | >= 90% |
| Reference perplexity ratio | <= 1.25x pristine baseline |
| Sequence KL | <= configured budget, measured in the same units used for optimization |
| Capability suites | <= 2 percentage-point absolute loss per suite |
| Degenerate generations | 0 across deterministic smoke prompts |
| Reproducibility | fixed split IDs, seed, model revision, tokenizer revision, and manifest |

These are research gates, not claims that one universal threshold is correct for
every deployment. The generated checkpoint must retain its full metric vector and
must not be described as successful from refusal rate alone.

## Why the current approach plateaued

### The direction basis is not yet causally selected

Four SVD components explain contrastive activation variance, but that does not
show that each component independently controls refusal. Arditi et al. found a
single causally effective direction across 13 model families, while later ICML
work found multiple directions and concept cones and warned that orthogonality is
not equivalent to independence under intervention. The appropriate next step is
therefore causal prescreening of candidate directions, not blindly increasing
the SVD rank.

### The sample is adequate for a smoke test, not optimization

The run estimated and evaluated directions on only 33 harmful/harmless pairs.
Recent multi-direction work trained on 4,000 harmful and 6,000 harmless prompts,
used a held-out validation set, and searched combinations with 128--512 trials.
The 2026 refusal-taxonomy study commonly used 32/32 samples only as a repeated
subsample, then evaluated stability and behavior on larger held-out pools.
OBLITERATUS should use the full local corpus with disjoint train, tuning, and
test identities rather than treating a single 33-pair sample as all three.

### The current KL optimizer does not optimize its displayed metric

`_kl_optimize_corrections` describes KL co-optimization, captures logits, but
then gates correction on perplexity from three short prompts. It maps the UI's
`kl_budget` to an exponential perplexity ceiling and ranks layers with weight
projection magnitude. The final UI separately reports first-token KL and colors
it with fixed thresholds unrelated to the configured budget. Consequently,
"KL-optimized," `kl_budget=0.5`, and a red `KL=0.2405` do not share one contract.

### The spectral certificate is degenerate at the current dimensions

The observed `bbp_threshold=0.0000` is not evidence of a cleanly estimated noise
bulk. With 20+20 samples and hidden size 5,120, the feature covariance is highly
rank-deficient. The implementation also eigendecomposes a rank-one outer product
for between-class scatter, so it cannot certify a multidimensional refusal
subspace as currently framed. A zero noise threshold must yield `INSUFFICIENT`,
not a definitive red/green certificate.

### Qwen3.8 needs architecture-stratified intervention

Qwen3.8-27B is not a conventional all-attention decoder. Its 64-layer text trunk
repeats three Gated DeltaNet blocks followed by one full-attention block. A single
depth kernel over all layers conflates two different sequence-mixing mechanisms.
The search space must distinguish:

- 48 linear-attention output projections;
- 16 full-attention output projections;
- 64 MLP down projections;
- attention/DeltaNet and MLP strengths independently;
- the four-layer architectural period as a blocking variable.

## Engineering roadmap

### P0 -- metric and optimizer correctness

1. **Create immutable experiment splits.** Stratify the 842-pair corpus by harm
   class and assign stable content IDs to direction-train, optimizer-validation,
   and final-test sets. Reject overlap. Default to at least 400 train pairs,
   100 validation pairs, and 200 final-test pairs where the corpus permits.
2. **Measure a pristine baseline once per exact revision.** Cache reference
   logits, token-level losses, deterministic completions, capability results,
   and refusal/compliance results. Bind the cache to model, tokenizer, template,
   dtype, thinking mode, dataset, and generation configuration hashes.
3. **Implement real KL optimization.** Compute token-distribution KL against
   cached pristine logits on held-out harmless prompts. Use the configured KL
   budget directly. Store exact per-component deltas or candidate runtime
   kernels so rollback restores the actual removed component; do not synthesize
   a uniform rank-one approximation from mean projection magnitude.
4. **Unify metric thresholds.** The optimizer, result card, validation gate,
   telemetry, and saved manifest must use the same named metric and units.
   Display both absolute KL and baseline-relative perplexity.
5. **Fail honestly on insufficient spectral samples.** Use a dual-space/SVD
   covariance estimator with shrinkage or a validated low-rank test. If the
   noise estimate is zero/non-finite, `n` is insufficient, or rank assumptions
   fail, return `INSUFFICIENT_DATA` with required sample count. Never emit a
   traffic-light certificate from a zero threshold.
6. **Separate refusal from harmful compliance.** Keep the cheap prefix detector
   as a diagnostic only. Add StrongREJECT and HarmBench-style response scoring,
   plus safety/non-refusal disagreement counts (refuse-then-answer,
   non-refusal-but-non-answer, and degenerate answer).
7. **Persist the complete run manifest.** Include git commit, HF revision,
   architecture manifest, split IDs, seed, direction statistics, candidate
   kernels, exact modified tensors, pre/post metrics, correction history, and
   checkpoint digest.

#### P0 tests

- synthetic distributions with known KL values and budget boundary tests;
- optimizer never reads final-test examples;
- exact rollback restores tensor hashes within declared dtype tolerance;
- UI color/gate agrees with the configured budget at below/equal/above cases;
- zero/rank-deficient covariance returns `INSUFFICIENT_DATA`;
- spectral tests with injected spikes recover known signal rank;
- refusal detector fixtures cover refusal-then-comply and evasive non-answers;
- split leakage and duplicate/paraphrase-family leakage tests;
- Qwen3.8 manifest test asserts 48 DeltaNet, 16 full-attention, and 64 MLP sites.

### P1 -- cheap causal prescreening

Add an activation-hook mode that does not mutate or save weights. Cache
activations once, then evaluate interventions on held-out prompts.

Search dimensions:

1. Direction estimators: difference-in-means, SVD ranks 1--7, LEACE as an
   experimental comparator, and RDO.
2. Layer bands: individual layer sweep, 40--70% depth window, current
   `middle60`, and learned sparse kernels.
3. Architecture groups: DeltaNet-only, full-attention-only, MLP-only,
   DeltaNet+MLP, full-attention+MLP, and all residual writers.
4. Component strengths: independent bounded kernels for DeltaNet/full-attention
   output and MLP down projections.
5. Stability: at least five stratified bootstrap direction estimates; record
   subspace angles/cosines and behavior variance across seeds.

Use multi-objective search over held-out refusal/compliance, sequence KL,
perplexity ratio, and capability loss. Keep the entire nondominated frontier;
do not collapse the study to one scalar score until an operator selects the
tradeoff. Start with 100 trials, then extend the promising family to 256--512.

#### P1 tests

- hook intervention and equivalent weight projection agree on a tiny model;
- cached and uncached evaluation produce the same deterministic metrics;
- architecture-group masks touch only their declared Qwen3.8 layer types;
- seeded search is reproducible and resumes without repeating completed trials;
- Pareto-front calculation retains all and only nondominated candidates;
- bootstrap instability blocks promotion even when mean refusal is low.

### P2 -- model-specific candidate methods

Run these as ablations, in order:

1. **Single-direction causal baseline.** Difference-in-means at candidate layers,
   mirroring the well-established Arditi baseline. This is the control that the
   current four-direction SVD run lacks.
2. **Multi-direction causal selection.** Select SVD/RDO directions by held-out
   causal effect and joint complementarity. Do not assume top singular values
   are the best joint intervention.
3. **RDO.** Optimize ablation, refusal-addition, and harmless-retention losses on
   disjoint train/validation data. Compare one RDO direction and a small
   representationally independent set.
4. **SOM/concept-cone candidate search.** Only after the evaluator is stable;
   use the published multi-direction setup as a methodological reference, not
   as a promise that Qwen3.8 behaves like Qwen2.5.
5. **LEACE comparator.** Treat as experimental because its formal guarantee is
   linear concept removal with minimum representation change, not specifically
   refusal removal or capability preservation in this hybrid architecture.
6. **SAE-denoised directions.** Defer until a validated Qwen3.8 layer-specific
   SAE exists or is trained. Rank features by causal output influence, not
   activation contrast alone. Generic/unvalidated SAE masking must remain
   blocked for promotion runs.

Do not combine RDO, SAE masking, head surgery, inversion, spectral cascade,
embedding projection, and activation steering in one experiment. Each candidate
method needs an isolated ablation and an interaction test before composition.

### P3 -- permanent write and release qualification

1. Choose a Pareto candidate from P1/P2.
2. Apply it once in FP32 math to the pristine BF16 checkpoint.
3. Verify runtime-hook equivalence before saving.
4. Run the final untouched evaluation suite.
5. Save atomically with sufficient disk headroom and an experiment manifest.
6. Reload from the saved local path and repeat deterministic smoke, refusal,
   capability, and hash/architecture checks.
7. Quantize only after the BF16 checkpoint passes. Evaluate quantization delta
   as a separate experiment rather than attributing it to refusal surgery.

## Experiment suite

| ID | Question | Train/tune setup | Intervention | Promotion criterion |
|---|---|---|---|---|
| E00 | Is the pristine evaluator stable? | final-test only, 3 seeds | none | metric variance and baselines recorded |
| E01 | Does the Arditi control work? | 400/100 | DIM, one layer/direction sweep | lower refusal with <=1.25x PPL |
| E02 | Does a low-rank writer intervention improve E01? | 500/142; final test prohibited | SVD-4 + RDO, middle-60% residual writers, KL rollback | tune refusal <30% and coherence >=80% |
| E03 | Can slight attenuation recover E02 coherence? | 500/142; final test prohibited | E02 kernel with 0.10 regularization | tune refusal <30% and coherence >=80% |
| E04 | Does SVD rank help? | 400/100 | k=1..7, joint held-out selection | nondominated gain over E01 |
| E05 | Does RDO improve targeting? | 400/100 | one and multiple RDO directions | held-out gain over E01/E04 |
| E06 | Do concept-cone combinations help? | large corpus + 128--512 trials | SOM/independent combinations | reproducible gain over E05 |
| E07 | Does LEACE preserve utility better? | same split as E04 | LEACE comparator | lower KL at matched refusal |
| E08 | Are SAE features causal? | only with validated SAE | output-score-filtered features | gain over raw activation features |
| E09 | Does permanent surgery match hooks? | winning kernel | FP32 weight write | metric equivalence within tolerance |
| E10 | Does quantization preserve the result? | untouched final test | BF16 vs FP8/4-bit | separately declared delta passes |

For every experiment, report confidence intervals and per-stratum results. A
single aggregate refusal percentage is insufficient: the current run ranged
from 60% refusal in S2 to 100% in several other strata.

## Evaluation suite

### Refusal and compliance

- internal corpus final-test split, stratified and held out;
- JailbreakBench for standardized behaviors and templates;
- HarmBench classifier-based harmful-compliance scoring;
- StrongREJECT for answer usefulness rather than empty compliance;
- SORRY-Bench for fine-grained refusal styles;
- XSTest safe/unsafe pairs for over-refusal calibration;
- WildGuard or an equivalent validated classifier as a secondary scorer;
- a blinded human audit sample for scorer disagreement.

### Capability preservation

- pristine-relative perplexity on a larger, immutable text sample;
- sequence-level KL, not first token alone;
- deterministic factual/coherence prompts;
- MMLU/ARC-style knowledge subset;
- GSM8K-style reasoning subset with thinking mode explicitly controlled;
- HumanEval/MBPP-style coding subset;
- JSON schema, tool calling, and instruction-following checks;
- long-context and recurrent-state checks specific to Gated DeltaNet;
- text-only regression plus a separate multimodal smoke test so text surgery
  does not silently break the native vision-language wrapper.

## Operational qualification result

E02 completed on the optimizer-tune partition as run
`run-efb2f334197e48fb82587f39a84fe6c9`: refusal fell to 1% (1/142), but its
original preview-truncated coherence score was 70% and 6/142 harmful responses
were degenerate. Its checkpoint and full archive are retained.

E03 (`run-c18babdb7be34396a07fbb994c23d4cb`) changed only regularization from
0.00 to 0.10. The saved 53.8 GB BF16 checkpoint was independently reloaded for
each evaluation after verifying all 35 checkpoint inventory entries by size and
SHA-256. With the corrected full-completion coherence scorer, the immutable
optimizer-tune split produced 1.41% refusal (2/142), 100% coherence, 83.3%
capability, 3.21 perplexity (1.02x pristine), and 1/142 degenerate harmful
responses. It therefore earned exactly one evaluation on the untouched final
split. That final saved-checkpoint reload produced 1.0% refusal (2/200), 100%
coherence, 83.3% capability, 3.21 perplexity, and 6/200 degenerate harmful
responses. Both durable evaluation records are hashed in the run manifest.

E03 passes the declared promotion gates of refusal below 30% and coherence of
at least 80%. The 3% final harmful-output degeneracy rate remains a follow-up
quality concern and should be included in downstream human and classifier
audits rather than hidden by the aggregate promotion result.

The qualified BF16 checkpoint is published as
[`manitcor/Qwen3.8-27B-Obliterated-E03`](https://huggingface.co/manitcor/Qwen3.8-27B-Obliterated-E03)
at immutable Hub revision `56bbc4a80c17353254c0ed0f31828e3980970495`.
Conversion and independent qualification of a separate BitsAndBytes NF4
artifact for a 24 GB RTX 4090 is tracked in
[#191](https://github.com/elder-plinius/OBLITERATUS/issues/191); it must not
replace or mutate this BF16 release.

The conversion and deployment evidence is recorded in
[`QWEN38_E03_BNB4_RELEASE.md`](QWEN38_E03_BNB4_RELEASE.md).

## Evidence base

Local corpus sources consulted:

- REF-188, *Refusal in Language Models Is Mediated by a Single Direction*
  (GRADE HIGH, NeurIPS 2024).
- REF-233, *Representation Engineering* (corpus grade VERY HIGH).
- REF-217, *Contrastive Activation Addition* (corpus grade HIGH).
- REF-228, *Activation Addition* (corpus grade HIGH).
- REF-535, *HarmBench* (corpus grade HIGH).
- REF-366, *Denoising Concept Vectors with SAEs* (corpus grade HIGH, preprint).
- REF-367, *SAEs Are Good for Steering--If You Select the Right Features*
  (corpus grade HIGH, preprint).

Primary external sources:

- [Arditi et al., Refusal in Language Models Is Mediated by a Single Direction](https://arxiv.org/abs/2406.11717)
- [Wollschlaeger et al., The Geometry of Refusal in Large Language Models](https://proceedings.mlr.press/v267/wollschlager25a.html)
- [Pan et al., SOM Directions Are Better than One](https://ojs.aaai.org/index.php/AAAI/article/view/40551)
- [Joad et al., There Is More to Refusal in Large Language Models than a Single Direction](https://arxiv.org/abs/2602.02132)
- [Belrose et al., LEACE](https://arxiv.org/abs/2306.03819)
- [Mazeika et al., HarmBench](https://arxiv.org/abs/2402.04249)
- [Souly et al., StrongREJECT](https://arxiv.org/abs/2402.10260)
- [Chao et al., JailbreakBench](https://arxiv.org/abs/2404.01318)
- [Xie et al., SORRY-Bench](https://arxiv.org/abs/2406.14598)
- [Roettger et al., XSTest](https://arxiv.org/abs/2308.01263)
- [Han et al., WildGuard](https://arxiv.org/abs/2406.18495)
- [Qwen/Qwen3.8-27B official model card](https://huggingface.co/Qwen/Qwen3.8-27B)

## Evidence limits

- No cited refusal-surgery paper evaluates Qwen3.8-27B specifically; all
  architecture-specific recommendations are hypotheses to test.
- The multi-direction and 2026 refusal-taxonomy papers are recent; independent
  replication is limited.
- LEACE guarantees linear erasure under its assumptions, not behavioral
  success or preservation of all downstream capabilities.
- SAE findings depend on model- and layer-specific dictionaries. They do not
  validate OBLITERATUS's generic SAE masking on Qwen3.8.
- Refusal removal and harmful-response usefulness are different outcomes;
  benchmark scorers can disagree and require human audit.
