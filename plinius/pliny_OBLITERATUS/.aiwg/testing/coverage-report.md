# Gate 3 increment 1 coverage report

Date: 2026-08-15
Canonical commit: `256c39ea6a492749a4db44146830e9d78fd3fed8`
Exact base: `8456e52bf8604a72ec6cfcc1ab71cbf46c90e1e7`
Coverage format: coverage.py branch JSON v3

| Scope | Measured on Python 3.12 | Enforced floor | Gate 3 exit | Status |
|---|---:|---:|---:|---|
| Repository statements | 75.68% | 75% | 80% | PASS floor; exit open |
| Repository branches | 61.72% | 60% | 65% | PASS floor; exit open |
| Mature CPU statements | 92.71% | 92% | 94% | PASS floor; exit open |
| Mature CPU branches | 81.55% | 80% | 84% | PASS floor; exit open |
| Changed production lines | Not applicable (policy/test/docs only) | 95% | 95% | PASS |
| Changed policy-script lines | 100% (242/242 focused local audit) | 95% | 95% | PASS |

The Python-version measurements vary slightly because version-specific branches
are exercised: repository coverage spans 75.68–75.78% statements and
61.72–61.81% branches. Exact-base replay on Python 3.12 reports a zero-point
line and branch delta and zero touched production modules, as expected for this
test-infrastructure-only increment.

Gate 3 increment 1 raises the immutable changed-line floor from 90% to 95%.
The value is consistent in `ci/test-quality-policy.json`,
`scripts/check_quality_policy.py`, `.github/workflows/ci.yml`, tests, and
operator documentation. The normal repository coverage gate measures
`obliteratus`; the audit therefore also measured the changed executable lines
in the two modified policy/evidence scripts directly and covered all 242.

The quantitative Gate 3 exit remains open. Later bounded increments must add
named production contracts to reach 80% repository statements, 65% repository
branches, 94% mature CPU statements, and 84% mature CPU branches without
weakening these floors. Canonical evidence is retained by CI run
https://github.com/elder-plinius/OBLITERATUS/actions/runs/31874768085.
