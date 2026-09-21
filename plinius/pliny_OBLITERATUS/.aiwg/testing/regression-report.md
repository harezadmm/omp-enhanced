# Gate 3 increment 1 regression report

Date: 2026-08-15
Base: `8456e52bf8604a72ec6cfcc1ab71cbf46c90e1e7`
Canonical head: `256c39ea6a492749a4db44146830e9d78fd3fed8`

- Mandatory CPU regressions: none; 1,644 tests pass with no warnings on Python
  3.10–3.12, versus 1,587 selected base tests in the Python 3.12 exact-base
  replay.
- Production regressions: none; the increment changes policy, evidence, tests,
  CI, and documentation without changing `obliteratus` behavior.
- Coverage regressions: none; exact-base Python 3.12 evidence reports 0.00 line
  and branch percentage-point delta and zero touched production modules.
- Determinism regressions: none; 391 tests pass in all three fixed orders and
  hash seeds with no flake candidates or consistent failures.
- Duration regressions: none unowned. Every suite, registered marker, testcase,
  and repeat duration is within policy. The known installed-package cost is
  tracked by issue #100 with a 120s ceiling and 2026-11-13 expiry.
- Mutation regressions: none; the bounded campaign remains 809/886 killed
  (91.31%), above the current 75% floor.
- Packaging and supply-chain regressions: none in wheel, sdist, metadata,
  installed import/CLI, lock, vulnerability, secret, license, or SBOM checks.

All seven canonical post-merge jobs passed at the head above:
https://github.com/elder-plinius/OBLITERATUS/actions/runs/31874768085.

This report closes bounded Gate 3 item 1 only. The overall Gate 3 release
decision remains blocked on items 2–7 and the quantitative exit criteria.
