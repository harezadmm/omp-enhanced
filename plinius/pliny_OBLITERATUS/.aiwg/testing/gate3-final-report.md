# Gate 3 final baseline and release report

Date: 2026-08-16
Exact measured canonical commit:
`42b30f7e5b8ee596b3b0b039b10af16f01deec1e`
Integration: PR #111, signature-preserving fast-forward
Status: measured criteria PASS; final report PR audit and canonical
reconciliation remain required before ordinary feature work resumes

## Exit-criterion results

| Gate | Canonical result |
|---|---|
| Mandatory Python 3.12 lane | 2,119 selected tests passed, 9 conditional tests deselected by policy, and 0 failed, errored, or skipped in 123.069s |
| Repository coverage | 83.49% statements / 71.04% branches; floors are 80% / 65% |
| Mature CPU coverage | 94.02% statements / 84.54% branches; immutable floors are 94% / 84% |
| Changed executable lines | 95% blocking floor; Gate 3 production increments met the floor, including 58/58 on item 7 |
| Selected mutation | 1,844/2,057 killed (89.65%); 208 survived and 5 timed out; blocking floor is 85% |
| Repeatability | 702 tests passed in each of three order/hash-seed runs; 0 flakes, failures, or skips; 50.907s total |
| Duration | Complete Python 3.12 suite 123.069s, repeat gate 50.907s, mutation 1,872.35s; all within their 10m/5m/45m budgets |
| Portability and delivery | Python 3.10/3.11/3.12, Windows checkpoint contracts, package, Ruff/actionlint, and supply chain all passed |
| Software conditional evidence | Exact-head run 31950226930 and canonical run 31952128889 passed policy, pinned model, external evaluation, loopback network, operator UI, and final freshness summary |
| Accelerator operator evidence | Titan RTX 4090 passed CUDA and bitsandbytes; Mutsu Apple M4 / 16 GB passed MPS and MLX at signed implementation head `fa233fd8c97d2a1463141535f2a288b264abe93b` |
| Unscheduled environments | GitHub accelerator-runner registration and remote execution remain explicit no-support/no-correctness/no-performance waivers through 2026-09-15 under issue #110 |
| Review integrity | PR #111 was audited at immutable head, had no findings or review threads, passed all eight mandatory jobs, and preserved four publish-key signatures on `main` |

The canonical mandatory run for the measured commit is
https://github.com/elder-plinius/OBLITERATUS/actions/runs/31952112615.
It passed all eight mandatory jobs on the first attempt. The result above also
matches the successful exact-merge candidate run
https://github.com/elder-plinius/OBLITERATUS/actions/runs/31950217640.

## Delivered increments

| Item | Canonical commit | Delivery and protected behavior |
|---:|---|---|
| 1 | `256c39ea6a492749a4db44146830e9d78fd3fed8` | Adopted quantitative Gate 3 policy, duration budgets, and initial measurements |
| 2 | `2c2b38b501f94af46ffac3a772f7bf9475154dc5` | Added independent numerical, property, and metamorphic oracles (PR #102) |
| 3 | `c1b34503ddd3cb797e5d70671c47afcabfe73832` | Added loader, architecture, dtype, quantization, and shared-weight decision contracts (PR #103) |
| 4 | `d7d2ad566af778b1d315616bbea8b8a3c4dd2191` | Added checkpoint failure injection, atomicity, retry, cleanup, concurrency, and Windows contracts (PR #104) |
| 5 | `aa182cc44883890c019c393f17602e2e2702e7d7` | Added BESTIARY, model-client, transport, and watchtower state contracts (PR #105) |
| 6 | `9683e0be4d892e6a6a134b45a065e591e139da3c` | Added tournament, interactive, and UI decision-seam contracts (PR #108) |
| 7 | `b961623513a0e137b959f608ce31511d59e85888` | Added the tiny-model vertical slice and safe quantized/tied-weight restoration semantics (PR #109) |
| 8 | `42b30f7e5b8ee596b3b0b039b10af16f01deec1e` | Added conditional evidence governance, expiring claim waivers, and a functional same-version CUDA Torch overlay (PR #111) |

The AIWG workspace and CI contract were also refreshed and reconciled at
`e8ac3b65670d696ed5b68f06adf14706bc2ff865` (PR #107). The deployed AIWG
version is 2026.8.11, and the generated provider context continues to route
tracker and delivery authority through `.aiwg/aiwg.config`.

## Evidence integrity and claim boundary

The mandatory CI run tests the GitHub pull-request merge candidate; separate
manual conditional runs bind their JSON and JUnit evidence to the exact source
commit. Every selected software conditional record for item 8 names
`42b30f7e5b8ee596b3b0b039b10af16f01deec1e`, reports zero failures, errors,
or skips, and the summary has an empty failure list.

The Titan and Mutsu probes used isolated temporary directories,
checksum-verified uv 0.12.4 binaries, managed Python 3.12.13, the exact signed
source archive, and the committed dependency lock. Their temporary remote
directories were removed after evidence retrieval. These probes establish only
the recorded operations. They do not replace scheduled GitHub lanes or create
a broad accelerator support, compatibility, correctness, or performance claim.

Issue https://github.com/elder-plinius/OBLITERATUS/issues/110 remains open for
durable GitHub runner registration and least-privileged remote-execution
coverage. Waivers fail closed if malformed, expired, longer than 30 days, or
detached from that canonical tracker.

## Evidence locations

- PR #111 audit:
  https://github.com/elder-plinius/OBLITERATUS/pull/111#issuecomment-5307860827
- Exact-head conditional run:
  https://github.com/elder-plinius/OBLITERATUS/actions/runs/31950226930
- Canonical conditional run:
  https://github.com/elder-plinius/OBLITERATUS/actions/runs/31952128889
- Downloaded exact-head conditional artifacts:
  `/tmp/obliteratus-item8-final-head-eJ79m7`
- Downloaded exact-head quality artifacts:
  `/tmp/obliteratus-item8-quality-au2hsV`
- Downloaded canonical CI and conditional artifacts:
  `/tmp/obliteratus-item8-canonical-b7MJu4`
- Exact-head hardware JSON/JUnit evidence:
  `/tmp/obliteratus-item8-hardware-evidence-GqqBSm`
- Hardware evidence and waiver tracker comment:
  https://github.com/elder-plinius/OBLITERATUS/issues/110#issuecomment-5307675226
- Per-increment detail:
  `gate3-increment-2-report.md` through `gate3-increment-8-report.md`

Canonical SHA-256 anchors are `143c42b579c91f5dc6d1d82fd74d10c0295056dd913986da178eb22b4e491275`
for mutation statistics, `11038dbd3f27c152cf057a3ae806a845cefab8dec9b55fbd26b5fe94c4cf21bb`
for the quality trend, `3b69fe70763b0c8fc82875a4bc9febca203a7b4c384be4605c7d1746ae0ab230`
for Python 3.12 coverage, and
`bc72408d88b4d2c480ebfaeae958a4ad0db0d13790adaa1ac52aee1f92e48671`
for the conditional summary.

## Release decision

The measured canonical commit satisfies every quantitative Gate 3 CPU,
coverage, mutation, repeatability, portability, delivery, and fresh-software
conditional criterion. There are no active flaky quarantines and no selected
gate was converted to green through a skip or retry.

The remaining accelerator and remote gaps are visible, owned, expiring, and
claim-blocking rather than silently treated as support evidence. Subject to a
clean exact-head audit, mandatory CI, signed integration, and post-merge
reconciliation for this report-only item 9, the testing-depth pause may end and
the contributor merge train may resume one immutable PR head at a time.
