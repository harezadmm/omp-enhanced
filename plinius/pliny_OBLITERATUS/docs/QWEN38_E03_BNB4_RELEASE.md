# Qwen3.8-27B E03 BitsAndBytes NF4 release

This document records the conversion, qualification, and single-GPU deployment
contract for the public 4-bit derivative of the qualified E03 checkpoint. It is
the execution record for issue #191 and supplements
`QWEN38_27B_RESEARCH_ROADMAP.md`.

## Artifacts and provenance

- BF16 source: `manitcor/Qwen3.8-27B-Obliterated-E03`
- Immutable BF16 revision: `56bbc4a80c17353254c0ed0f31828e3980970495`
- Upstream Qwen revision: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- 4-bit release: `manitcor/Qwen3.8-27B-Obliterated-E03-bnb-4bit`
- Immutable 4-bit revision: `2656024da794bba206a202ce9dfa7836a4fe26e8`
- E03 run archive: `run-c18babdb7be34396a07fbb994c23d4cb`

Before conversion, all 28 local BF16 shard sizes and SHA-256 digests were
matched against the immutable Hub revision's LFS object metadata. The BF16
source and its run archive were not modified.

## Conversion contract

The model was converted on one broker-reserved NVIDIA A100 80 GB using:

| Component | Version or value |
|---|---|
| PyTorch | 2.10.0 |
| Transformers | 5.8.1 |
| BitsAndBytes | 0.50.0 |
| Accelerate | 1.14.0 |
| Hugging Face Hub | 1.28.0 |
| Quantization | NF4, 4-bit |
| Double quantization | enabled |
| Compute dtype | BF16 |
| Quantized storage | UINT8 |
| CPU offload | disabled |

The saved candidate contains nine model shards and 496 BitsAndBytes
`Linear4bit` modules. Its inventory totals 17,674,101,612 bytes before the final
public metadata update. Conversion completed in 216 seconds.

The final public revision contains 38 files totaling 17,674,131,869 bytes,
including the conversion evidence and the independent Titan qualification
reports. It is public, ungated, and licensed under Apache-2.0.

### A100 resource envelope

- model memory footprint: 17,266,162,944 bytes;
- steady CUDA allocation after conversion: 17,669,476,352 bytes;
- peak CUDA allocation: 22,755,069,952 bytes;
- peak CUDA reservation: 23,030,923,264 bytes.

The conversion and every evaluator load used a scoped GPU-broker lease. An
initial placement canary was aborted before a material load when `sudo -u`
removed the broker-provided visibility environment. The accepted run explicitly
set and asserted `CUDA_VISIBLE_DEVICES` to the leased UUID before loading. The
aborted candidate directory contained no model artifact and is retained as
failure evidence.

## Independent qualification

The saved 4-bit artifact was loaded in a fresh process. It retained all 496
expected `Linear4bit` modules, placed zero parameters on CPU, and produced
finite logits. The evaluator then ran the complete 200-prompt final-test
partition, corrected full-output coherence checks, and the six extended
capability checks.

| Gate | Required | BF16 E03 | NF4 result | Status |
|---|---:|---:|---:|---|
| Refusal rate | <=3% | 1.0% | 0.5% | pass |
| Coherence | >=90% | 100% | 100% | pass |
| Capability | >=83% | 83.3% | 83.3% | pass |
| Harmful degeneracy | <=5% | 3.0% | 2.5% | pass |
| Perplexity increase | <=15% | 3.2099 | 3.4106 (6.25%) | pass |
| Finite logits | required | yes | yes | pass |
| Fresh-process reload | required | yes | yes | pass |
| CPU offload | prohibited | none | none | pass |

An additional isolated comparison captured first-token logits on 33 prompts:

- mean first-token KL against BF16 E03: 0.0194261;
- maximum first-token KL: 0.3652223;
- deterministic 64-token exact-string matches: 0/10.

The deterministic pairs retain the tested task intent but are not byte-for-byte
equivalent. This is a disclosed quantization difference, not an exact parity
claim. The public artifact contains the pairwise outputs and KL values. The raw
33 by 248,320 BF16 reference-logit tensor remains in the private qualification
archive and is excluded from the model repository.

## Titan runtime contract

Titan has an RTX 4090 with 24,564 MiB VRAM, 64 GiB host RAM, and a dedicated
model path under `/mnt/sata-data/models/manitcor/`. The pinned runtime is an
isolated virtual environment at:

```text
/home/roctinam/.venvs/qwen38-e03-bnb4
```

It uses the same PyTorch, Transformers, BitsAndBytes, Accelerate, and Hub
versions as conversion. Titan does not currently expose the Basilisk
`docker gpu` broker. Therefore standalone qualification must stop Ollama before
the first CUDA allocation, verify that Ollama released the GPU, supervise one
model process, free all CUDA allocations, and restore Ollama afterward. Static
free-VRAM observation is diagnostic only and must not be represented as broker
admission.

Start at batch size 1 and validate 2K, 4K, then 8K context lengths. Record load
time, peak VRAM, peak host RAM, prompt throughput, decode throughput, power,
temperature, and output checks for every level. A failed 2K load blocks longer
contexts.

### Titan qualification results

The immutable Hub revision was downloaded directly to Titan. Its 33 initial
release files (17,674,127,214 bytes) were independently checked before load:
all 10 LFS objects matched their Hub SHA-256 digests and all 23 non-LFS files
matched byte-for-byte. The five Titan evidence files were added in the final
public revision named above.

Ollama was stopped before the first CUDA allocation and each context test ran
in a separate process. All three tests found exactly 496 `Linear4bit` modules,
zero CPU parameters, finite logits, and a non-empty deterministic completion.

| Context | Load | Prompt throughput | 32-token generation | Load peak allocated | Peak reserved | Host max RSS | Power / temp sample | Status |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2,048 | 10.46 s | 1,360 tok/s | 13.25 tok/s | 22.74 GB | 22.76 GB | 15.57 GiB | 246 W / 46 C | pass |
| 4,096 | 8.89 s | 1,542 tok/s | 8.60 tok/s | 22.74 GB | 22.77 GB | 16.75 GiB | 238 W / 47 C | pass |
| 8,192 | 2.85 s | 1,542 tok/s | 5.11 tok/s | 22.74 GB | 22.77 GB | 17.49 GiB | 253 W / 50 C | pass |

Load-time variation reflects the warm host page cache after the first isolated
load. The 4090 margin is narrow: the runtime observed only about 1.08 GB free
while resident. These measurements therefore support batch size 1 through 8K;
they do not justify concurrent GPU workloads or a larger context. The optional
Flash Linear Attention and causal-conv1d fast paths were not installed, so the
measured runtime used Transformers' Torch fallback.

After the final process exited, CUDA returned to the pre-test 12 MiB desktop
allocation. Ollama was restarted on its configured `172.17.0.1:11434`
listener, returned all 55 registered models, completed a real
`smollm2:135m` generation, and unloaded that smoke-test runner successfully.

## Deployment sequence

1. Resolve and record the immutable public 4-bit Hub revision
   `2656024da794bba206a202ce9dfa7836a4fe26e8`.
2. Download that revision into the dedicated Titan model path.
3. Compare the downloaded tree, file sizes, and small-file hashes with the Hub
   revision and conversion inventory.
4. Stop Ollama and prove that its CUDA process is gone.
5. Load the model in a supervised foreground process with `device_map={"": 0}`.
6. Assert 496 `Linear4bit` modules, no CPU parameters, finite logits, and the
   measured VRAM envelope.
7. Run the staged context/performance matrix and smoke/quality checks.
8. Release CUDA, verify no test process remains, and restore Ollama.
9. Register a persistent supervisor only after all standalone gates pass.

## Rollback

Rollback does not delete either model artifact:

1. Stop the NF4 inference unit or foreground test process.
2. Wait for process exit, synchronize CUDA when possible, and verify that its
   NVIDIA compute allocation is gone.
3. Disable the NF4 unit if it was enabled.
4. Start the pre-existing Ollama service.
5. Confirm Ollama health and a successful known-model request.
6. Retain the NF4 model directory, qualification reports, and service logs for
   diagnosis.

## Evidence retention

The A100 candidate, raw evaluator log, aggregate reports, conversion manifest,
artifact inventories, BF16 comparison tensor, deterministic outputs, and
failed placement-canary note are retained beneath the protected OBLITERATUS
service storage. Large failed candidates may be deleted only after their notes,
manifests, and relevant logs are preserved.
