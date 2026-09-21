# NVIDIA Jetson support plan

Issue: https://github.com/elder-plinius/OBLITERATUS/issues/31

## Status

Native Jetson AGX support is not claimed yet. OBLITERATUS should treat Jetson
as a dedicated conditional runtime lane, not as part of the default pull-request
gate and not as a generic Linux ARM build.

The current OBLITERATUS CUDA path delegates discovery to PyTorch through
`torch.cuda.is_available()`. If a Jetson AGX host reports no CUDA inside
OBLITERATUS, the first thing to verify is the JetPack/L4T/PyTorch/container
stack, because NVIDIA publishes Jetson-specific PyTorch builds intended for
specified JetPack versions.

## Decision

Support Jetson through a JetPack-pinned runtime contract:

- Keep ordinary PR CI CPU-only, offline, and architecture-neutral.
- Add a Jetson conditional gate once a Jetson runner is available.
- Prefer an NVIDIA-supported Jetson PyTorch container or NVIDIA Jetson PyTorch
  wheel for the exact JetPack release under test.
- Do not use the existing x64 CUDA gate as Jetson evidence.
- Do not treat a generic `linux/arm64` build as evidence that CUDA works on
  Jetson.

## Why generic ARM is insufficient

Jetson support couples at least five moving pieces:

- Jetson hardware family and compute capability.
- JetPack version.
- Jetson Linux/L4T version and Ubuntu base image.
- CUDA, cuDNN, TensorRT, and related NVIDIA libraries.
- PyTorch build or container version.

NVIDIA's Jetson PyTorch documentation says the PyTorch packages are installed
on top of a specified JetPack version, and the compatibility table maps PyTorch
versions to NVIDIA framework containers/wheels and JetPack versions. A generic
ARM build can prove that Python code imports on `aarch64`; it cannot prove that
CUDA, cuDNN, TensorRT, or PyTorch CUDA dispatch works on Jetson.

## Proposed initial support matrix

Start with the hardware reported in issue #31: Jetson AGX devices with 64 GB
unified memory.

This is a planning target, not a current support claim. The implementation must
replace the JetPack family with the exact patch installed on the available
runner before publishing compatibility:

| Tier | Hardware | JetPack | OS / CUDA baseline | Evidence requirement |
| --- | --- | --- | --- | --- |
| Initial candidate | Jetson AGX Orin 64 GB | 6.2.x, exact patch TBD | L4T/CUDA values from the selected patch | Native Jetson runner or pinned compatible container on Jetson hardware |
| Evaluate later | Jetson AGX Thor | 7.x, exact release TBD | Select only after NVIDIA's PyTorch compatibility table covers the release | Separate runner and evidence before claiming support |
| Legacy | Jetson AGX Xavier | 5.1.x | Jetson Linux 35.x / Ubuntu 20.04 / CUDA 11.x family | Defer unless a maintainer/user provides hardware and demand |

Do not collapse these tiers into one "ARM64" support claim.

## Installation shape

The generic local Dockerfile uses `python:3.11-slim` and is not the Jetson
runtime image. A Jetson runtime should use one of these approaches:

1. Start from an NVIDIA Jetson-compatible PyTorch framework container for the
   selected JetPack version, then install OBLITERATUS without replacing the
   container's validated PyTorch stack.
2. On a flashed Jetson host, install the NVIDIA Jetson PyTorch wheel matching
   the installed JetPack release, then install OBLITERATUS in a virtual
   environment without allowing dependency resolution to replace `torch`.

The lock policy should make the Jetson torch source explicit. The existing
Linux PR lock intentionally uses CPU-only PyTorch. A Jetson install path needs
an override or separate constraints file that preserves NVIDIA's Jetson PyTorch
runtime. It must also prevent the generic PyPI Linux-aarch64 bitsandbytes wheel
from being selected: upstream documents that wheel as SBSA/server ARM and says
Jetson L4T/JetPack requires a source build. Until a pinned source build passes
on the selected device, bitsandbytes is unsupported for that tier.

### Experimental contributor bootstrap

Start with NVIDIA's PyTorch wheel or PyTorch iGPU container for the exact
JetPack patch installed on the device. Confirm that `python3 -c 'import torch;
assert torch.cuda.is_available()'` succeeds before installing OBLITERATUS. Then,
from a checkout of the exact commit under test, run:

```bash
python3 -m venv .venv-jetson-tools
.venv-jetson-tools/bin/python -m pip install "uv==0.12.4"
.venv-jetson-tools/bin/python scripts/setup_jetson.py \
  --python python3 \
  --uv-python .venv-jetson-tools/bin/python \
  --venv .venv-jetson
.venv-jetson/bin/python scripts/run_conditional_gate.py jetson-runtime
.venv-jetson/bin/python scripts/jetson_support.py \
  --check \
  --gate-evidence conditional-evidence/jetson-runtime.json \
  --output conditional-evidence/jetson-report.json \
  --issue-body conditional-evidence/jetson-issue.md
```

The bootstrap validates ARM64, L4T, and CUDA before changing the environment.
It creates a virtual environment with `--system-site-packages`, exports the
committed lock, and installs locked OBLITERATUS dependencies without replacing
the vendor `torch`. It also excludes bitsandbytes. The generic bitsandbytes
package is now an explicit `quantization` extra for supported non-Jetson
environments; Jetson quantization remains a separate source-build milestone.

For JetPack 6.2, NVIDIA publishes the
`nvcr.io/nvidia/pytorch:25.06-py3-igpu` container. Run it only on Jetson hardware
with the NVIDIA runtime, mount a reviewed checkout, and use the same bootstrap
inside the container. Match other JetPack releases through NVIDIA's
compatibility table rather than substituting a `latest` tag.

## Conditional gate

Add a new gate instead of modifying the x64 CUDA gate:

- Gate id: `jetson-runtime`
- Runner labels: `self-hosted`, `linux`, `ARM64`, `jetson`
- Optional labels by tier: `orin`, `jetpack-6` or `thor`, `jetpack-7`
- Trigger: manual dispatch and release/scheduled validation only
- Evidence retention: same 30-day conditional-evidence policy as other hardware
  gates

The job must run only from a trusted ref or reviewed maintainer dispatch. A
persistent self-hosted Jetson must never execute untrusted pull-request code.

### Attaching a contributor-owned runner

Register the runner using GitHub's self-hosted runner instructions, on the
Jetson itself, and add the custom label `jetson`. GitHub supplies the
`self-hosted`, `linux`, and `ARM64` default labels. Verify that the repository
shows exactly these required labels before dispatching the job:

```text
self-hosted, linux, ARM64, jetson
```

Use a dedicated, non-personal runner account and a disposable or resettable
workspace. Do not place Hugging Face, SSH, cloud, or signing credentials on the
runner. Only a maintainer should manually dispatch `Conditional tests` against
a reviewed commit; the Jetson job is deliberately unavailable to pull-request,
scheduled, and release triggers. Remove the runner registration token after
setup and keep the runner offline when it is not being used for reviewed work.

### Reporting results without a project-owned Jetson

Open the [Jetson runtime report](https://github.com/elder-plinius/OBLITERATUS/issues/new?template=jetson-runtime.yml)
issue form and attach `conditional-evidence/jetson-report.json`, or paste the
generated `conditional-evidence/jetson-issue.md`. The collector reports only an
allow-listed architecture, OS/JetPack, PyTorch/CUDA, device-class, test-result,
and commit profile. It excludes environment variables, hostnames, usernames,
network addresses, device serials, tokens, and local filesystem paths. Review
the file yourself before publishing it. A failed report is useful evidence and
does not imply that the contributor must diagnose the compatibility problem.

The gate should verify:

- `platform.machine()` is `aarch64` or equivalent ARM64.
- `torch.cuda.is_available()` is true.
- `torch.version.cuda` is not `None`.
- `torch.cuda.get_device_name(0)` identifies the Jetson GPU class.
- OBLITERATUS resolves `device=auto` to `cuda`.
- A small CUDA tensor operation completes with finite output.
- The existing offloaded-surgery CUDA probe passes.
- A pinned, source-built `bitsandbytes` NF4/4-bit path is proven on that exact
  Jetson stack, or bitsandbytes is documented as unsupported for the tier.
- A tiny Hugging Face model run passes only when the model-download gate is
  explicitly selected and the runner has the required account/cache policy.

## Acceptance criteria

Jetson support can be claimed for a tier only after all of the following are
true:

- The supported Jetson module and JetPack version are named in this document.
- The install instructions pin the JetPack-compatible PyTorch container or
  wheel source.
- The Jetson conditional gate produces non-skipped green evidence on the exact
  commit being claimed.
- The named `jetson-runtime` workflow job uses the documented runner labels and
  retains `conditional-jetson-<run-attempt>` logs and environment metadata for
  30 days.
- The release notes distinguish generic ARM importability from Jetson CUDA
  support.
- The docs state memory expectations for 64 GB unified memory and recommend
  small models for validation before large ablation runs.

## Operational notes

Jetson's unified memory is shared by the OS, CUDA, model weights, activations,
and file cache. Treat "64 GB" as a capacity class, not guaranteed usable model
memory. Use small models for smoke tests, then move larger GPU validation to
dedicated CUDA hosts such as Titan when those resources are available.

The Jetson hardware probe does not require a Hugging Face login. Model download
testing remains the separate, explicitly selected `model-download-runtime`
gate; credentials are relevant only when that selected model itself requires
them.

## Sources

- [NVIDIA: Installing PyTorch for Jetson Platform](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html)
- [NVIDIA: PyTorch for Jetson compatibility table](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform-release-notes/pytorch-jetson-rel.html)
- [NVIDIA: JetPack 6.2 release notes](https://docs.nvidia.com/jetson/archives/jetpack-archived/jetpack-62/release-notes/index.html)
- [NVIDIA: current JetPack downloads and notes](https://developer.nvidia.com/embedded/jetpack/downloads)
- [Astral: Using uv with PyTorch](https://docs.astral.sh/uv/guides/integration/pytorch/)
- [Hugging Face: bitsandbytes installation guide](https://huggingface.co/docs/bitsandbytes/installation)
- [GitHub: secure use of self-hosted runners](https://docs.github.com/en/actions/reference/security/secure-use#hardening-for-self-hosted-runners)
- [GitHub: use self-hosted runner labels](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow)
- [GitHub: hosted ARM64 runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [NVIDIA: PyTorch 25.06 for JetPack 6.2](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-25-06.html)
