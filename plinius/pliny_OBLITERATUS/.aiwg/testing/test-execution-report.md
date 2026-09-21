# Gate 3 increment 1 test execution report

Date: 2026-08-15
Canonical commit: `256c39ea6a492749a4db44146830e9d78fd3fed8`
Scope: mandatory offline CPU baseline, duration policy, quality depth, packaging,
and supply chain
Status: PASS

## Results

| Gate | Result |
|---|---|
| Mandatory CPU | 1,644 passed, 9 conditional deselections, 0 failures/skips/warnings on Python 3.10–3.12 |
| Repository coverage | Python 3.12: 75.68% statements, 61.72% branches |
| Mature CPU scope | Python 3.12: 92.71% statements, 81.55% branches |
| Changed executable lines | Production: not applicable; focused policy/evidence scripts: 242/242 (100%) |
| Repeat | 391 tests x 3 orders/seeds; 51.085s total; no flakes or consistent failures |
| Mutation | 809/886 killed (91.31%); 72 survived; 5 timed out |
| Duration evidence | Complete marker metadata; every testcase retained; all suite, marker, testcase, and repeat budgets pass |
| Package | Wheel and sdist build, metadata, isolated imports, and both CLI paths pass |
| Supply chain | Vulnerability, secret, license, lock, and bound-SBOM policies pass |
| Hosted CI | All seven post-merge jobs pass on Python 3.10–3.12 |

## Hosted duration evidence

| Python | Pytest suite | Complete job | CPU marker | Integration marker | Unmarked |
|---|---:|---:|---:|---:|---:|
| 3.10 | 154.051s | 2m55s | 94.259s | 93.778s | 24.187s |
| 3.11 | 129.534s | 2m37s | 76.812s | 76.395s | 19.360s |
| 3.12 | 158.989s | 5m41s | 93.549s | 93.087s | 24.709s |

Python 3.12 is the slowest complete job because it also regenerates coverage at
the exact base commit. It remains 4m19s inside the ten-minute job cap. The
slowest individual testcase is the installed-package offline
checkpoint-to-report slice at 80.119s. It retains the general 15s testcase
floor through a narrow 120s owner budget linked to issue #100 and expiring
2026-11-13; no permanent or implicit exception was introduced.

## Contracts added

1. The changed-line floor is immutable at 95% unless the existing reviewed,
   issue-linked, time-bounded threshold exception contract is satisfied.
2. JUnit normalization retains suite wall time, every testcase duration,
   registered test-layer markers, marker aggregates, and missing-marker state.
3. Policy enforcement rejects malformed or inconsistent evidence, missing
   marker metadata, unbudgeted markers, suite/test/marker overruns, and repeat
   total or pass overruns.
4. Deliberately slow tests require an owner, reason, repository issue, explicit
   ceiling, and expiring review window.

The exact post-merge run is
https://github.com/elder-plinius/OBLITERATUS/actions/runs/31874768085. Conditional
hardware, remote, model-download, network, and operator-UI environments were
not changed or rerun by this increment; their freshness and support-claim
reconciliation remains Gate 3 item 8.
