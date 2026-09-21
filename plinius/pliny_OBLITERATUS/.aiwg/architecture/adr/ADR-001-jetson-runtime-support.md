# ADR-001: Use a JetPack-pinned runtime for Jetson support

Status: Proposed
Date: 2026-08-21
Issue: https://github.com/elder-plinius/OBLITERATUS/issues/31
Public plan: [docs/platforms/jetson.md](../../../docs/platforms/jetson.md)

Implementation status: generic ARM64 preflight, vendor-PyTorch-preserving
bootstrap, physical-device gate, sanitized evidence collector, manual runner
workflow, and contributor issue form are implemented. The ADR remains Proposed
until physical-device evidence fixes the initial supported matrix.

## Context

OBLITERATUS currently resolves CPU-only PyTorch for Linux through its default
uv lock. Its hardware CUDA gate is explicitly x64 and replaces that locked
package with an upstream cu130 build. Application device discovery already
delegates to `torch.cuda.is_available()`.

Jetson is therefore not primarily an application detection change. It is a
platform-runtime problem: the Jetson module, JetPack/L4T release, Python,
CUDA-family libraries, and PyTorch build or container must be compatible. A
generic ARM64 build can detect Python packaging defects but cannot establish
that this runtime works on Jetson hardware.

## Options considered

| Option | Benefit | Limitation | Decision |
| --- | --- | --- | --- |
| Generic ARM64 build only | Cheap packaging and CPU portability signal | Exercises no Jetson CUDA, L4T, or device memory behavior | Keep as preflight only |
| Native Jetson virtual environment | Direct and simple hardware validation | Host packages drift and the default lock can replace vendor PyTorch | Supported fallback |
| JetPack-compatible container on Jetson hardware | Reproducible runtime boundary and retained image provenance | Requires per-JetPack maintenance and a physical Jetson runner | Preferred |
| Build PyTorch and the complete CUDA stack from source | Maximum version control | High build cost and long-term platform maintenance burden | Reject for the initial tier |

`jetson-containers` may accelerate prototyping, but it is a community project,
not the project's vendor trust anchor. A supported image must ultimately pin
audited base-image and package provenance.

## Decision

1. Keep the default PR environment and lock CPU-only.
2. Treat generic ARM64 CI as packaging preflight, never Jetson support evidence.
3. Define one exact initial matrix only after a runner is available: Jetson
   module, JetPack patch, L4T, Python, PyTorch image or wheel, CUDA, cuDNN,
   TensorRT, and bitsandbytes status.
4. Prefer an image derived from a JetPack-compatible NVIDIA PyTorch runtime and
   run it on physical Jetson hardware. Preserve the image digest and binary
   hashes in release evidence.
5. Add a separate `jetson-runtime` conditional gate. Its exact base labels are
   `self-hosted`, `linux`, `ARM64`, and `jetson`; tier labels identify the module
   and JetPack major version.
6. Run the hardware lane only by trusted manual, scheduled, or release
   dispatch. Never execute untrusted pull-request code on the persistent
   self-hosted Jetson runner.
7. Do not install the generic PyPI Linux-aarch64 bitsandbytes wheel on Jetson.
   Upstream documents that wheel as SBSA/server ARM and requires a Jetson source
   build. Quantization remains unsupported until a pinned source build passes
   the exact hardware gate.

## Consequences

- Jetson support will have a narrower, explicit matrix rather than a broad ARM
  claim.
- The implementation needs a Jetson-specific constraints/profile boundary so
  `uv sync` cannot replace vendor PyTorch or select an incompatible
  bitsandbytes wheel.
- Cross-building an ARM64 image may shorten image assembly, but only an
  on-device run supplies CUDA support evidence.
- Vendor upgrades become release-affecting changes and must produce fresh gate
  evidence.

## Delivery and migration

1. Inventory the available Jetson and record its exact JetPack/L4T stack.
2. Select and pin the initial Orin/JetPack 6.2.x matrix at an exact patch.
3. Add generic ARM64 package/import preflight without changing default PR
   dependencies. (Implemented.)
4. Add the Jetson constraints/profile and preferred container recipe. (The
   native/container bootstrap boundary is implemented; an exact image remains
   dependent on the selected hardware matrix.)
5. Add the `jetson-runtime` policy entry, test probe, trusted workflow job, and
   retained evidence artifact. (Implemented.)
6. Validate CUDA discovery, device selection, a tiny CUDA operation, and the
   offloaded-surgery probe. Validate source-built bitsandbytes separately.
7. Claim support only for matrices with fresh green evidence on the exact
   release commit.

## Rollback

If the Jetson lane regresses, disable the affected matrix entry and remove its
support claim while retaining the generic ARM64 preflight. Revert the
Jetson-specific image/profile independently; do not change or weaken the
default CPU lock or x64 CUDA gate. Restore a matrix only after fresh physical
Jetson evidence passes.

## Review record

The 2026-08-21 review panel covered NVIDIA/platform compatibility,
build/maintainability, test/release evidence, and security/supply chain. It
required the Jetson-specific bitsandbytes source-build rule, physical-hardware
container evidence, one canonical public plan, exact gate naming, and an
untrusted-code restriction for the self-hosted runner.
