# Distributed checkpoint intake source register

**Artifact ID:** RESEARCH-DCI-001
**Version:** 0.3.0
**Status:** Reviewed technical evidence
**Accessed:** 2026-09-02
**Repository baseline:** `5cc43c6e52903497574d80e08dff856028bc47f7`

This register is the citation authority for the distributed-checkpoint feature
documentation. It records what each source supports and the limits on how the source may
be used. Vendor documentation establishes upstream behavior; it does not by
itself prove OBLITERATUS compatibility. Project support claims require exact-head
tests, immutable fixtures, and retained evidence at an exact candidate commit.

## Primary and upstream sources

| ID | Source | Evidence class | Supported use | Required qualification |
|---|---|---|---|---|
| R01 | [PyTorch Distributed Checkpoint API](https://docs.pytorch.org/docs/stable/distributed.checkpoint.html) | Primary project documentation; moderate confidence | DCP save/load planning, multi-rank storage, load-time resharding, preallocated state | DCP documents no general saved-state backward-compatibility guarantee; version-gate adapters |
| R02 | [PyTorch DCP recipe](https://docs.pytorch.org/tutorials/recipes/distributed_checkpoint_recipe.html) | Primary project tutorial; moderate confidence | Multi-rank examples and topology-change behavior | Tutorial behavior is illustrative, not a universal format contract |
| R03 | [PyTorch FSDP API](https://docs.pytorch.org/docs/stable/fsdp.html) | Primary project documentation; moderate confidence | Full/local/sharded state-dict distinctions and rank-zero CPU-offload semantics | FSDP state mode is not synonymous with DCP serialization |
| R04 | [Megatron Core sharded-tensor mapping](https://docs.nvidia.com/megatron-core/developer-guide/latest/apidocs/core/core.dist_checkpointing.mapping.html) | Primary vendor API documentation; moderate confidence | `global_offset`, `rank_offsets`, replica identity, element-coordinate semantics | Offsets establish placement, not model-family semantic mapping |
| R05 | [Megatron Core distributed checkpointing](https://docs.nvidia.com/megatron-core/developer-guide/latest/api-guide/core/dist_checkpointing.html) | Primary vendor documentation; moderate confidence | Model-weight resharding across supported topology changes | Optimizer resharding is format/version-dependent and must be separately qualified |
| R06 | [Megatron Core parallelism guide](https://docs.nvidia.com/megatron-core/developer-guide/latest/user-guide/parallelism-guide.html) | Primary vendor documentation; moderate confidence | TP, PP, DP, CP, EP, ETP, FSDP terminology | Axis products and parameter sharding behavior must follow the producer contract, not inference |
| R07 | [Megatron Bridge AutoBridge](https://docs.nvidia.com/nemo/megatron-bridge/latest/apidocs/bridge/bridge.models.conversion.auto_bridge.html) | Primary vendor API documentation; moderate confidence | Model-aware bidirectional conversion and provider mapping | Bridge availability does not imply every model family or checkpoint version is supported |
| R08 | [DeepSpeed model checkpointing](https://deepspeed.readthedocs.io/en/stable/model-checkpointing.html) | Primary project documentation; moderate confidence | ZeRO-2/3 fp32 consolidation, CPU-memory warning, `safe_serialization` output option | Input consolidation uses framework serialization and belongs behind the explicit trust gate |
| R09 | [DeepSpeed Universal Checkpointing](https://www.deepspeed.ai/tutorials/universal-checkpointing/) | Primary project tutorial; moderate confidence | Topology-neutral DeepSpeed model/optimizer representation for compatible mappings | Universal Checkpointing is neither HF safetensors nor a generic architecture converter |
| R10 | [DeepSpeed `zero_to_fp32.py`](https://github.com/deepspeedai/DeepSpeed/blob/master/deepspeed/utils/zero_to_fp32.py) | Upstream implementation; moderate confidence, version-volatile | Confirms current consolidation path and `weights_only=False` input loading | Pin the exact source revision used by an adapter qualification |
| R11 | [safetensors metadata parsing](https://huggingface.co/docs/safetensors/metadata_parsing) | Primary project documentation; moderate confidence | Header dtype, shape, and half-open `data_offsets` relative to the tensor data buffer | Safe parsing does not establish authenticity, path safety, or provenance |
| R12 | [Hugging Face serialization helpers](https://huggingface.co/docs/huggingface_hub/en/package_reference/serialization) | Primary project documentation; moderate confidence | Sharded safetensors writing, indexes, tied/shared-tensor handling | Atomic publication is an OBLITERATUS responsibility, not an upstream guarantee |
| R13 | [Transformers model loading and sharded checkpoints](https://huggingface.co/docs/transformers/main/models) | Primary project documentation; moderate confidence | Named tensors distributed across files and index-based loading | A file-shard index contains no rank-fragment coordinate contract |
| R14 | [Accelerate big-model inference](https://huggingface.co/docs/accelerate/main/en/concept_guides/big_model_inference) | Primary project documentation; moderate confidence | Single-process module placement and CPU/disk offload via `device_map` | `device_map` is not checkpoint topology or a multi-node launcher |
| R15 | [Accelerate multi-node launch](https://huggingface.co/docs/accelerate/main/en/basic_tutorials/launch) | Primary project documentation; moderate confidence | Per-node machine rank, common rendezvous, launcher invocation on every node | Launch documentation does not prove OBLITERATUS has a distributed runtime |
| R16 | [PEFT checkpoint format](https://huggingface.co/docs/peft/main/developer_guides/checkpoint) | Primary project documentation; moderate confidence | Standard adapter files, adapter-only state, dependency on a base model | Immutable base revision/digest is an OBLITERATUS provenance rule and may be absent upstream |
| R17 | [PyTorch serialization notes](https://docs.pytorch.org/docs/main/notes/serialization.html) and [`torch.load`](https://docs.pytorch.org/docs/stable/generated/torch.load.html) | Primary project documentation; moderate confidence | Serialization trust warning and `weights_only` behavior | `weights_only` narrows risk but does not turn arbitrary input into verified data |
| R18 | [PyTorch issue: DCP `.metadata` uses pickle](https://github.com/pytorch/pytorch/issues/189308) | Upstream issue and source-linked observation; low-to-moderate confidence | Establishes a concrete reason default inspection must not treat `.metadata` as inert | Recheck against the exact PyTorch version before implementing a trusted reader |
| R19 | [Transformers Trainer resume recipes](https://huggingface.co/docs/transformers/main/trainer_recipes) | Primary project documentation; moderate confidence | Resume includes more than model weights, such as optimizer/scheduler/RNG state | Exact state varies by trainer/framework/version |
| R20 | [Accelerate training migration](https://huggingface.co/docs/accelerate/basic_tutorials/migration) | Primary project documentation; moderate confidence | Accelerator state can include model, optimizer, scheduler, RNG, and data position | This does not define a portable cross-framework resume format |

## Security and containment sources

| ID | Source | Evidence class | Supported use | Required qualification |
|---|---|---|---|---|
| R27 | [Python `pickle` documentation](https://docs.python.org/3/library/pickle.html) | Primary language documentation; high confidence | Establishes that malicious pickle can execute arbitrary code and untrusted/tampered data must not be unpickled | A signature or digest establishes integrity only under a separately trusted provenance/key decision; it does not make arbitrary objects semantically safe |
| R28 | [PyTorch security policy](https://github.com/pytorch/pytorch/blob/main/SECURITY.md) | Primary project security guidance; high confidence | Treat untrusted models as programs, prefer isolated execution, validate even safer formats, and do not expose distributed primitives to untrusted networks | Security guidance is not proof that a container or any individual loader/profile is safe; qualify the exact runtime and isolation |
| R29 | [PyTorch advisory GHSA-63cw-57p8-fm3p / CVE-2026-24747](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p) | Primary project advisory; high confidence | Demonstrates code-execution risk in affected `weights_only=True` loading and supports rejecting it as a permanent safe-plane boundary | A patched version fixes the named defect only; future/parser/resource risks and trust requirements remain |
| R30 | [NIST SP 800-190, Application Container Security Guide](https://csrc.nist.gov/pubs/sp/800/190/final) | Primary government security guidance; high confidence | Container-specific threat/mitigation context and the need to secure images, registries, orchestrators, hosts, and runtime configuration | Published in 2017; apply principles to the exact current runtime and do not equate containers with complete sandboxing |
| R31 | [Linux kernel `no_new_privs` documentation](https://docs.kernel.org/userspace-api/no_new_privs.html) | Primary kernel documentation; high confidence | Prevent privilege gains through `execve` and support unprivileged seccomp-filter use | The flag does not prevent all privilege changes or provide filesystem/network/resource isolation by itself |
| R32 | [Linux kernel seccomp-filter documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html) | Primary kernel documentation; high confidence | Reduce the syscall surface of a constrained worker and layer filters after `no_new_privs` | Syscall filtering is one containment layer, not a semantic validator or full sandbox |
| R33 | [Linux kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html) | Primary kernel documentation; high confidence | Bound and observe worker memory/CPU/process resource use | Controller availability/configuration and kernel behavior must be preflighted and recorded on the exact host/profile |
| R34 | [OWASP Deserialization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html) | Primary security-community guidance; moderate-to-high confidence | Prefer pure data formats, avoid native deserialization for untrusted data, and validate before object construction | General guidance; project controls must follow the Python/PyTorch and exact adapter/runtime behavior |
| R35 | [Linux `openat2(2)` manual](https://man7.org/linux/man-pages/man2/openat2.2.html) | Authoritative Linux interface documentation; high confidence | Root-relative path resolution with `RESOLVE_BENEATH`, `RESOLVE_NO_SYMLINKS`, and `RESOLVE_NO_MAGICLINKS` for untrusted paths | Linux-specific and kernel-version-dependent; other platforms need reviewed equivalent semantics or must refuse trusted-reader use |

## Project evidence

| ID | Source | Supported use | Limitation |
|---|---|---|---|
| R21 | OBLITERATUS `origin/main` at `5cc43c6e52903497574d80e08dff856028bc47f7`; see `obliteratus/models/loader.py`, `obliteratus/models/offload_surgery.py`, `obliteratus/abliterate.py`, `obliteratus/persistence_contracts.py`, `obliteratus/remote.py`, and `README.md` | Establishes current local loader, process-local placement/offload, complete-state export, atomic helper, one-host remote runner, and documentation boundary | Line references must be refreshed when implementation changes |

## Claim rules

1. Use “documents,” “defines,” or “currently implements” for vendor behavior;
   do not convert vendor documentation into an OBLITERATUS support claim.
2. Mark project interpretations explicitly, especially the distinction between
   `device_map` and checkpoint-rank topology.
3. A `supported` matrix row requires an exact producer version, adapter version,
   immutable fixture digest, candidate commit, environment, topology, and retained
   result at the exact candidate commit.
4. Archived/versioned documentation remains historical evidence only. Current
   contracts use the latest cited primary documentation plus exact-version source.
5. Security claims remain bounded: subprocess isolation and resource limits are
   containment controls, not proof that vendor deserialization is safe.
6. `weights_only=True`, a checksum, and a recognized local filename are never
   represented as sufficient trust or authenticity controls [R27–R29].
7. OS controls are cited as exact-profile containment mechanisms, not a portable
   universal sandbox claim [R30–R35].
