# Jetson support acceptance and release-validation strategy

Date: 2026-08-21
Scope: OBLITERATUS issue #31
Status: assessment, not implementation

## Executive conclusion

Issue #31 cannot be validated or released on a generic ARM builder alone.
Generic ARM64 CI can cover repository-level portability, importability,
packaging, and CPU-only behavior, but Jetson support depends on the NVIDIA
JetPack software stack and on execution on Jetson-class hardware or a JetPack
container running on that hardware.

The lowest-risk support model is:

1. keep the default PR gate CPU-only and deterministic;
2. add a Jetson-specific conditional gate on a self-hosted ARM64 Jetson runner;
3. treat generic ARM64 CI as a preflight layer, not as acceptance evidence;
4. require real-device smoke evidence before declaring Jetson support.

## What the current repo policy already says

The project context already establishes that the default PR baseline is
CPU-safe, deterministic, and must not require accelerator, network, or remote
credentials. Conditional accelerator checks are explicitly outside the default
CPU job.

The current conditional policy already has:

- a CUDA gate on `self-hosted, linux, x64, cuda`;
- a documented waiver model for unavailable accelerator lanes;
- a GitHub Actions routing model that relies on runner labels and groups.

That means Jetson support should be added as a new conditional lane, not folded
into the standard CPU PR job.

## Evidence-based split: generic ARM64 vs Jetson device

### Generic ARM64 builders can validate

- Python packaging and metadata.
- Pure-Python imports and CLI/help entry points.
- CPU-only unit and boundary tests.
- Static/configuration logic that does not require CUDA or JetPack runtime
  libraries.
- The fact that a workflow can target `ARM64` self-hosted runners.

This is enough for portability regressions, but not enough for Jetson runtime
support.

### Jetson hardware or JetPack container is required for

- CUDA device discovery.
- CUDA execution and memory behavior.
- cuDNN / TensorRT / JetPack-specific library compatibility.
- Any claim that NVIDIA-provided Jetson PyTorch wheels run correctly.
- Any claim that the installed runtime actually sees a Jetson GPU.

NVIDIA’s Jetson PyTorch installation guide says the provided wheels are meant
to be installed on top of a specified JetPack version on a Jetson device, and
verification is done by importing `torch` on the Jetson platform.

NVIDIA’s Jetson Linux validation guide also says CUDA samples can be run
natively on the target or inside the JetPack container, which is the right
acceptance bar for hardware-backed validation.

## Support tiers

### Tier 0: source-only portability

Purpose: prove the codebase does not contain obvious ARM-incompatible
assumptions.

Environment:

- GitHub-hosted Linux or self-hosted ARM64 runner;
- CPU-only;
- no NVIDIA driver, no JetPack, no CUDA.

Checks:

- `python -m build --sdist --wheel`
- install the built wheel into a clean venv
- `python -m obliteratus --help`
- import and module smoke tests
- all CPU-only pytest markers

Acceptance:

- no architecture-specific syntax/runtime breakage;
- no packaging or import regressions.

### Tier 1: Jetson preflight on generic ARM64

Purpose: catch obvious Jetson-adjacent integration mistakes before touching
hardware.

Environment:

- ARM64 Linux runner without JetPack;
- optional cross-check against Jetson-targeted config files and dependency
  pins.

Checks:

- validate Jetson-specific config manifests and workflow wiring;
- verify that Jetson jobs are gated behind dedicated labels and environment
  variables;
- confirm that no Jetson-only dependency is pulled into the default PR job.

Acceptance:

- the repo can express a Jetson lane cleanly;
- default CI remains CPU-only.

### Tier 2: Jetson hardware smoke

Purpose: prove the runtime actually works on a Jetson device.

Environment:

- self-hosted Linux ARM64 Jetson runner with the exact labels `self-hosted`,
  `linux`, `ARM64`, and `jetson`;
- JetPack installed and active;
- NVIDIA runtime / CUDA stack available.

Checks:

- `torch` import from the JetPack-aligned wheel set;
- `torch.cuda.is_available()` and device enumeration;
- a tiny tensor operation on GPU;
- a minimal model-load or model-adapter smoke if the feature requires it;
- a short CUDA sample or equivalent library smoke;
- optional containerized run using the JetPack-compatible container on that
  Jetson hardware.

Acceptance:

- the device is recognized as CUDA-capable;
- the relevant Jetson wheel/container stack works on the intended JetPack
  version;
- the workflow emits logs and artifacts that identify the exact JetPack / CUDA /
  wheel set used.

### Tier 3: release validation

Purpose: certify a tagged release candidate.

Environment:

- Tier 2 Jetson hardware;
- pinned dependency set and reproducible artifacts;
- retained logs and hashes.

Checks:

- Tier 2 smoke;
- the repo’s full release-validation suite;
- supply-chain checks for vendor artifacts;
- any release note or compatibility matrix update.

Acceptance:

- tagged releases declare Jetson support only when Tier 2 and Tier 3 pass
  against the exact tagged commit.

## Recommended runner labels

Use separate labels so the workflow can route cleanly and fail obviously if the
hardware is absent.

- `self-hosted, linux, ARM64, jetson`
- optional refinement: `self-hosted, linux, ARM64, jetson, orin`
- optional refinement: `self-hosted, linux, ARM64, jetson, jetpack-<major>`

Keep the generic ARM64 preflight on a separate label such as:

- `self-hosted, linux, ARM64, arm64-preflight`

This avoids accidentally treating a generic ARM machine as a Jetson target.

GitHub’s self-hosted runner routing is label-based, and jobs remain queued if
no matching runner is online. That makes an explicit Jetson label the right
mechanism for a physical-device lane.

## Exact acceptance gates

Jetson support should be considered ready only when all of these are true:

1. The default PR gate still passes with no Jetson dependency.
2. A dedicated `jetson-runtime` job passes on physical Jetson hardware, either
   natively or inside the pinned JetPack-compatible container.
3. The exact supported JetPack version is documented.
4. The exact NVIDIA wheel/container provenance is pinned and hashed.
5. The repo has a regression test that fails if Jetson detection or the CUDA
   smoke is broken.
6. The release notes state the supported JetPack / CUDA / TensorRT matrix.
7. The workflow retains the named `conditional-jetson-<run-attempt>` log and
   environment artifact for 30 days against the exact candidate commit.

## Memory and thermal constraints

Jetson support should assume small-device variability, even on higher-memory
SKUs.

Practical guardrails:

- use tiny models and short sequences for smoke tests;
- cap wall time tightly;
- assert memory-sensitive paths with low-footprint fixtures;
- avoid benchmark-length runs on the Jetson lane;
- collect `nvidia-smi`-equivalent or device telemetry only if the platform
  exposes it;
- do not rely on long repeated sweeps for acceptance.

If a test is intended to validate memory pressure, it should do so with a
deterministic threshold and a short timeout, not with a human-observed
benchmark.

## Rollback and waiver policy

If Jetson hardware is unavailable, the repo should:

- keep the Jetson lane optional and separately labeled;
- preserve the generic ARM64 preflight;
- publish a time-bounded waiver in the existing conditional-policy pattern;
- avoid claiming Jetson support in release notes.

If a Jetson regression is found after support is published:

- revert or patch the exact regression on the supported branch;
- keep the Jetson lane red until the hardware smoke passes again;
- do not widen the default PR gate to hide the failure.

## Supply-chain and security considerations

Jetson support increases supply-chain risk because the runtime depends on vendor
wheels and platform-specific system packages.

Controls to require:

- pin exact NVIDIA wheel URLs and versions;
- verify hashes for every downloaded binary artifact;
- prefer official JetPack / NVIDIA container images over ad hoc mixed library
  stacks;
- do not mix arbitrary patched CUDA/TensorRT libraries into the supported
  matrix;
- record the exact JetPack release, CUDA version, and TensorRT version in the
  evidence trail;
- treat any vendor wheel update as a release-affecting change.
- build bitsandbytes from a pinned source revision for Jetson, record the build
  inputs and hash, and never substitute the generic SBSA Linux-aarch64 wheel;
- never execute untrusted pull-request code on the persistent self-hosted
  Jetson runner.

NVIDIA’s TensorRT documentation explicitly notes that JetPack deployments must
remain on a TensorRT 10.x release supported by the JetPack version. That means
the Jetson compatibility matrix must be version-pinned, not “latest by default.”

## Recommended implementation path

Repository status as of 2026-08-21: steps 2 through 4 are implemented with a
manual-only physical runner, a hosted ARM64 preflight, CPU-testable policy
contracts, and a sanitized contributor evidence flow. Physical Jetson results
are still required before completing steps 5 and 6 or publishing support.

1. Keep issue #31 open as a feature/specification item until the acceptance
   matrix is merged.
2. Add a Jetson conditional policy entry and workflow job with an explicit
   `jetson` runner label.
3. Add a minimal Jetson smoke test that checks import, CUDA discovery, and one
   tiny GPU operation.
4. Add a generic ARM64 preflight job to catch packaging and configuration
   regressions early.
5. Document the supported JetPack / CUDA / TensorRT matrix in the repo docs.
6. Promote Jetson claims only after a real-device run has passed on the exact
   release candidate.

## Source URLs

- https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html
- https://docs.nvidia.com/jetson/archives/r36.5/DeveloperGuide/SD/TestPlanValidation.html
- https://docs.nvidia.com/deeplearning/tensorrt/latest/installing-tensorrt/installing.html
- https://docs.github.com/en/actions/reference/runners/self-hosted-runners
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
