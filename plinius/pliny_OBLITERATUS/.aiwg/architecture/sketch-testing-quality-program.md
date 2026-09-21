# Architecture sketch: layered verification

The verification system has four explicit layers:

1. **Mandatory PR gate** — CPU-only, offline unit and boundary-contract tests,
   package build, lint, branch/line coverage, warnings, JUnit, and artifacts.
2. **Offline integration gate** — tiny local model/config fixtures exercise
   pipeline composition, checkpoint/save/reload, evaluation, and reporting.
3. **Quality-depth gate** — property tests, repeat tests, and selective mutation
   testing for high-consequence pure modules.
4. **Conditional environment gates** — accelerator, optional backend, download,
   network, and remote-service jobs with explicit prerequisites.

pytest markers form the selection contract between layers. GitHub Actions jobs
produce retained evidence and never silently convert a required failure into a
success. Tool versions remain project-controlled. The default gate must not
access external services, inherit user model caches, or require credentials.

The initial coverage waves and Gate 2 are complete:

- measurement wave: preserve the 49% line floor and establish branch baseline;
- boundary wave: repository line coverage at least 55%, changed lines at least
  90%, and touched critical modules at least 70%;
- integration wave: repository line coverage at least 60%;
- Gate 1: at least 70% repository line and 55% branch coverage, with at least
  90% line and 78% branch coverage for the mature CPU-testable scope;
- Gate 2: at least 75% repository line and 60% branch coverage, with at least
  92% line and 80% branch coverage for the mature CPU-testable scope and an
  installed-package CLI/config-to-report vertical slice;
- exclusions remain limited to documented conditional environment code.

Wave A locks that baseline by generating exact-base coverage in the same CI run,
rejecting per-module line or branch regressions, validating a machine-readable
source-to-test and conditional-gate graph, retaining normalized trend evidence
for 90 days, and enforcing owner/issue/expiry requirements for repeated flaky
tests. The exact thresholds and exclusion graph remain owned by
`ci/test-quality-policy.json`; `ci/test-risk-map.json` owns test responsibility.
Software-only conditional evidence must match the candidate commit. A stale
evidence exception requires a reason, a canonical numeric OBLITERATUS issue,
and an expiry no more than 30 days away.

Gate 3 adds duration ownership to the existing normalized evidence path. Pytest
attaches the registered test-layer markers to each JUnit testcase; the evidence
normalizer retains the suite wall time, every testcase duration, the slowest
summary, and marker aggregates without changing schema version 1 consumers.
The quality-policy gate enforces per-Python suite, per-marker, individual-test,
and fixed repeat-campaign budgets. GitHub Actions independently caps each
mandatory Python test job at ten minutes.
