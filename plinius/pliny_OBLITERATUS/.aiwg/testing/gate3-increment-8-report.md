# Gate 3 increment 8 conditional-evidence and waiver report

Date: 2026-08-16
Exact base: `b961623513a0e137b959f608ce31511d59e85888`
Exact policy implementation head: `fa233fd8c97d2a1463141535f2a288b264abe93b`
Exact canonical head: `42b30f7e5b8ee596b3b0b039b10af16f01deec1e`
Canonical mandatory run:
https://github.com/elder-plinius/OBLITERATUS/actions/runs/31952112615
Canonical conditional run:
https://github.com/elder-plinius/OBLITERATUS/actions/runs/31952128889
Status: PASS; PR #111 was exact-head audited, signature-preserving merged, and
canonically reconciled

## Results

| Gate | Result |
|---|---|
| Focused policy contracts | 17 conditional-policy, summary, CUDA-overlay, and evidence-freshness tests passed |
| Policy regression set | 110 policy and CI-contract tests passed |
| Mandatory CPU lane | Python 3.12: 2,122 passed and 6 environment-dependent tests skipped in 81.44s; repository coverage 83.51% statements |
| Policy validation | Committed conditional policy passes direct CLI validation on 2026-08-16 |
| Software conditional gates | Exact final-head run 31950226930 and canonical run 31952128889 passed pinned-model runtime, external evaluation, loopback network, operator UI, policy, and final summary |
| Canonical mandatory gates | Run 31952112615 passed Python 3.10/3.11/3.12, Windows, package, Ruff/actionlint, supply chain, repeatability, and mutation depth |
| CUDA and bitsandbytes | Titan RTX 4090: Torch 2.13.0+cu130 / CUDA 13.0; both gate invocations passed 2/2 at exact head; GitHub runner registration remains waived through 2026-09-15 under issue #110 |
| Apple MPS | Mutsu Apple M4 / 16 GB: native Torch 2.13.0 reports MPS built and available; gate passed 1/1 at exact head; GitHub runner registration remains waived through 2026-09-15 |
| Apple MLX | Mutsu Apple M4 / 16 GB: MLX 0.32.0 and MLX-LM 0.31.3; gate passed 1/1 at exact head; GitHub runner registration remains waived through 2026-09-15 |
| Remote execution | Required repository variables and secrets are unset; waived through 2026-09-15 under issue #110; no support, compatibility, correctness, or performance claim |
| Runner inventory | Titan exposes Gitea GPU/host runners only; Mutsu exposes a Colima builder but no runner process; the GitHub token also receives HTTP 403 from the repository-runner inventory API |
| Signing | All four item-8 commits are signed and verified with publish-key fingerprint `62297562B1C7053088F405DB0117DAAA677A5BF2` |

## Contracts added

1. Every unavailable conditional lane has one
   versioned waiver naming its gate, canonical issue, reason, opening date,
   expiry date, and the exact claim that is blocked.
2. A waiver may last at most 30 days. Missing fields, non-object records,
   duplicate gates, unknown gates, software-only gates, invalid issue URLs,
   invalid or future dates, reversed dates, overlong lifetimes, and expired
   records fail policy validation.
3. An unselected gate with an active waiver is emitted as
   `waived_no_support_claim` with its tracker, expiry, and blocked claim.
   Unselected gates without a waiver remain
   `not_selected_no_fresh_evidence`.
4. Selecting and successfully executing a waived gate produces `success` and
   therefore uses real evidence instead of the waiver. Selected failures remain
   failures, including shared CUDA/bitsandbytes job failures.
5. An expired or malformed waiver also fails the final summary, preventing a
   stale record from becoming a silent green result after the policy job.
6. Mandatory Linux CI remains CPU-only. The selected CUDA lane derives the
   exact locked Torch base version, replaces only Torch with the same-version
   official `cu130` build, asserts that the resulting build exposes CUDA, and
   runs `uv pip check` before the hardware probe.

## Availability findings and claim boundary

`gh variable list` and `gh secret list` for the canonical repository returned
no configured entries on 2026-08-16. The runner inventory endpoint returned
HTTP 403 because the current maintainer token lacks repository-runner read
permission. Live read-only inspection then confirmed that Titan has an RTX
4090 and active Gitea runners, while Mutsu is a 16 GB Apple M4 builder. Neither
host exposes a GitHub Actions runner process, so the waivers now cover GitHub
runner registration and scheduled automation rather than hardware absence.

Equivalent operator runs used isolated temporary directories, checksum-verified
uv 0.12.4 binaries, a managed Python 3.12.13 runtime, the exact signed source
archive, and the committed dependency lock. Titan installed the official
same-version CUDA overlay and passed CUDA/bitsandbytes. Mutsu installed the
native macOS lock plus the MLX group and passed MPS/MLX. The evidence was copied
off-host and hashed before both remote temporary directories were removed.

The waivers are tracked by
https://github.com/elder-plinius/OBLITERATUS/issues/110. They expire on
2026-09-15, 30 days after opening. Before expiry, maintainers must either
configure and run the matching gate or review and replace the waiver under the
tracker. The fresh probes establish only the recorded operations on Titan and
Mutsu at the exact candidate. They do not create a broad support, compatibility,
correctness, or performance claim, and they do not replace the open work to
register maintainable GitHub runners.

## Verification and evidence

- Exact-head software conditional run:
  https://github.com/elder-plinius/OBLITERATUS/actions/runs/31950226930
- Canonical software conditional run:
  https://github.com/elder-plinius/OBLITERATUS/actions/runs/31952128889
- Canonical mandatory run:
  https://github.com/elder-plinius/OBLITERATUS/actions/runs/31952112615
- Downloaded software JSON/JUnit evidence:
  `/tmp/obliteratus-item8-final-head-eJ79m7`
- Downloaded canonical CI and conditional evidence:
  `/tmp/obliteratus-item8-canonical-b7MJu4`
- Exact-head hardware JSON/JUnit and SHA-256 evidence:
  `/tmp/obliteratus-item8-hardware-evidence-GqqBSm`
- Focused local command:
  `/tmp/obliteratus-item8-py312-env/bin/python -m pytest -q --no-cov
  tests/test_conditional_gate_scripts.py
  tests/test_conditional_evidence_freshness.py`
- Mandatory local environment: `/tmp/obliteratus-item8-py312-env`
- Local generated summary: `/tmp/obliteratus-item8-summary.json`
- Waiver tracker:
  https://github.com/elder-plinius/OBLITERATUS/issues/110
- Hardware-evidence tracker comment:
  https://github.com/elder-plinius/OBLITERATUS/issues/110#issuecomment-5307675226
- Exact-head audit:
  https://github.com/elder-plinius/OBLITERATUS/pull/111#issuecomment-5307860827

## Scope and release decision

This increment changes conditional-test governance and CUDA environment setup.
It does not alter production behavior or weaken mandatory CPU, package,
coverage, repeat, mutation, Windows, or supply-chain gates. Gate 3 item 9 and
its final report audit and canonical reconciliation remain required before the
contributor merge train resumes.
