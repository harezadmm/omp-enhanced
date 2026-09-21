# Use cases: testing quality program

## UC-TQ-01 — Contributor verifies a pull request offline

Given a clean checkout on Python 3.10–3.12 without a GPU, network access, model
cache, or service credentials, a contributor can run the canonical commands and
receive deterministic pass/fail results plus retained JUnit and coverage data.

## UC-TQ-02 — Maintainer evaluates changed-code risk

A maintainer can see line and branch coverage, changed-line evidence, warnings,
packaging validity, and the exact test layer exercised before merging a change.

## UC-TQ-03 — Release operator verifies installed distributions

A release operator can build both distribution formats, validate their metadata,
install each in isolation, import the package, read its version, and execute the
public CLI without relying on the source tree.

## UC-TQ-04 — Developer exercises model boundaries without downloads

A developer can verify loader, device, quantization, architecture, pipeline,
checkpoint, evaluation, and reporting contracts with local deterministic fakes
and a tiny offline model fixture.

## UC-TQ-05 — Operator validates conditional environments

An operator can intentionally run clearly documented CUDA, bitsandbytes, MPS,
MLX, model-download, network, and remote checks without weakening or surprising
the default pull-request gate. Software-only evidence records the exact
candidate commit; any stale-evidence exception is reasoned, issue-linked, and
expires within 30 days.

## UC-TQ-06 — Maintainer verifies the installed vertical contract

A maintainer can exercise a non-editable installed distribution with a local
deterministic tiny model through CLI/config parsing, loader/device selection,
pipeline execution, checkpoint save/reload, evaluation, and JSON/CSV report
generation without external services or accelerator hardware.

## UC-TQ-07 — Maintainer detects unowned test-runtime growth

A maintainer can inspect retained suite, testcase, registered-marker, and repeat
durations for the exact candidate commit. CI rejects a suite, marker, repeat
pass, or testcase that exceeds its project-owned budget. A deliberately slow
test requires a repository issue, owner, reason, explicit ceiling, and expiring
review window rather than an implicit or permanent exemption.
