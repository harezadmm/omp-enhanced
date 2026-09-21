# Distributed preflight contract

`obliteratus distributed preflight PROFILE.json` is the only distributed entry
point currently implemented. It consumes a worker group that an external
trusted scheduler has already launched. It does not launch `torchrun`, SSH to a
peer, provision hosts, install packages, relay credentials, load model weights,
or perform surgery.

The command is an admission gate, not a supported multi-node workflow. Native
Llama tensor-parallel loading, distributed PROBE/DISTILL/EXCISE/VERIFY, export,
and physical two-host qualification remain unimplemented and unqualified.
NCCL, Gloo, and rendezvous authentication or encryption are not claimed.

## Invocation boundary

The scheduler must provide all of the following to every rank:

- `RANK`, `LOCAL_RANK`, `WORLD_SIZE`, and `LOCAL_WORLD_SIZE`;
- `GROUP_RANK`, `ROLE_RANK`, and `ROLE_WORLD_SIZE`;
- `MASTER_ADDR` and `MASTER_PORT`;
- `TORCHELASTIC_RUN_ID`, `TORCHELASTIC_RESTART_COUNT=0`, and
  `TORCHELASTIC_MAX_RESTARTS=0`;
- a fresh `OBLITERATUS_RUN_ID` distinct from the rendezvous ID; and
- exact `GLOO_SOCKET_IFNAME` and `NCCL_SOCKET_IFNAME` values matching the
  reviewed profile.

Ordinary `run`, `obliterate`, and one-host SSH commands never inspect these
variables to infer distributed intent. The distributed command accepts only
the local profile path and optional `--json`; secrets and operational overrides
are not CLI inputs.

## Closed profile schema

The profile is bounded UTF-8 JSON. Every section and field is required; unknown
or duplicate fields fail closed. The following uses non-operational example
values and is not an accepted physical-host profile:

```json
{
  "schema_version": 1,
  "run": {
    "run_id": "11111111111111111111111111111111",
    "rendezvous_id": "22222222222222222222222222222222",
    "world_size": 2,
    "local_world_size": 1
  },
  "identity": {
    "source_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "model_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "tokenizer_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "commit_sha": "dddddddddddddddddddddddddddddddddddddddd",
    "code_digest": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
  },
  "topology": {
    "tensor_parallel_size": 2,
    "coordinator_rank": 0,
    "placement_plan_digest": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "dimension_divisors": [4096, 11008]
  },
  "network": {
    "master_addr": "10.10.0.10",
    "master_port": 29500,
    "interface": "eth0",
    "allowed_master_cidrs": ["10.10.0.0/24"]
  },
  "source": {"path": "/srv/immutable/model"},
  "staging": {
    "path": "/srv/obliteratus/staging",
    "storage_digest": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
  },
  "resources": {
    "min_free_device_memory_bytes": 8589934592,
    "min_free_host_memory_bytes": 17179869184,
    "min_free_staging_bytes": 107374182400,
    "max_source_files": 10000,
    "max_source_bytes": 1099511627776,
    "max_source_file_bytes": 274877906944
  },
  "timeouts": {
    "source_seconds": 1800,
    "init_seconds": 60,
    "collective_seconds": 60,
    "teardown_seconds": 15
  },
  "software": {
    "python": "3.12.11",
    "platform": "Linux-6.18.0-x86_64-with-glibc2.42",
    "machine": "x86_64",
    "torch": "2.13.0",
    "transformers": "5.15.0",
    "accelerate": "1.12.0",
    "safetensors": "0.7.0",
    "cuda": "13.0",
    "nccl": "2.28.3",
    "driver": "13000"
  },
  "execution": {
    "device_kind": "cuda",
    "device_name": "REVIEWED-EXACT-GPU-NAME",
    "compute_capability": "REVIEWED-EXACT-CAPABILITY",
    "evidence_tier": "candidate_preflight",
    "allowed_environment_keys": ["HOME", "LANG", "PATH", "CUDA_VISIBLE_DEVICES"],
    "local_files_only": true,
    "trust_remote_code": false,
    "allow_runtime_install": false,
    "allow_plugins": false,
    "allow_compilation": false,
    "allow_adapters": false,
    "allow_quantization": false
  },
  "evidence": {"path": "/srv/obliteratus/staging/11111111111111111111111111111111/preflight.json"}
}
```

The source tree must be an immutable, local, non-symlink directory containing
a structurally valid canonical Hugging Face safetensors checkpoint, immutable
tokenizer metadata, and only closed inert file types. The existing bounded
safe-structure inspector validates safetensors headers and rejects adapters,
pickle formats, aliases, links, and mutable files without deserializing tensor
payloads. Content hashes are streamed without loading tensor data. The
three source digests are canonical hashes of the complete file inventory, the
safetensors subset, and tokenizer-named files respectively.

`commit_sha` binds Git history while `code_digest` independently binds the
Python files actually available to the process, including dirty-tree changes.
`storage_digest` is not a label: each worker derives it from the exact Linux
mountinfo record backing the staging path. The selected interface must own an
address inside the private allowlist, and the coordinator's master address must
be bound to that interface. All inherited environment keys must appear in the
closed allowlist; credential-, cloud-, token-, and proxy-shaped keys can never
be allowlisted.

## Admission and failure behavior

Before returning `preflighted`, every rank must agree on the run, config,
source, model, tokenizer, commit, software, storage, placement, topology, and
network-interface identities. Global devices and per-host local ranks must be
unique. Device, host RAM, and staging capacity must meet the exact integer
floors. Rank zero exclusively reserves `staging/<run_id>` and every rank must
observe an atomic shared marker there.

The selected interface must own an address inside the private allowlist before
Gloo initialization is attempted; the coordinator must also own the configured
numeric rendezvous address on that interface. All local preflight probes are
bounded by the smaller configured source/collective deadline. Source traversal
and structural inspection nest under that same process-level wall-clock timer,
including payload hashing and revalidation. A runtime that cannot enforce that
deadline refuses the attempt.

Any missing rank, disagreement, timeout, backend error, rank loss, or uncertain
cleanup fails the whole attempt. Restarts and in-memory resume are forbidden;
retry requires fresh run and rendezvous IDs and a complete new preflight.
Cleanup uncertainty is `quarantined`.

Evidence is bounded, mode `0600`, atomically created, and never overwritten.
The path is fixed to `staging/<run_id>/preflight.json`. While Gloo is live,
every rank reads and votes on one canonical `PREFLIGHTED/PREPARED` lifecycle
record. This record has a distinct stage-message schema and cannot be decoded
as terminal success evidence. After bounded group destruction, each rank
creates a private `PREFLIGHTED/COMMITTED` teardown acknowledgement; rank zero
publishes terminal success only after validating the complete fixed-rank set.
Failures emit `ABORTING` and then `ABORTED` or `QUARANTINED` lifecycle receipts.
Missing or invalid receipts produce `LMS_CLEANUP_INCOMPLETE`, never success.

An FD-level guard is active across backend initialization, collectives, and
teardown. Raw native/backend stderr is discarded; any emitted bytes fail the
attempt as `LMS_DIAGNOSTIC_REDACTION_FAILED`. Terminal evidence contains only
allowlisted state, counts, stable error codes, the mandatory `protocol_cpu` or
`candidate_preflight` scope label, and opaque digests—not raw endpoints,
hostnames, device identifiers, paths, environment mappings, exceptions,
prompts, tensors, or credentials.

If process-group destruction exceeds its explicit bound, the affected
externally launched worker exits with fixed status `70` before the FD guard is
restored. A Python teardown thread is never allowed to outlive containment.
Missing teardown acknowledgement then forces coordinator-side
`LMS_CLEANUP_INCOMPLETE` and `QUARANTINED`; torchrun restart remains disabled.

The implementation and tests define a fail-closed candidate boundary only. No
exact physical-host profile, residual-risk acceptance, authenticated or encrypted
transport, GPU/NCCL qualification, model payload, or production support claim is
included.
