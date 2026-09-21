---
title: BT6 Release Readiness Report
description: Pre-tag audit and hardening report for moving a candidate from the bounded PR bar to the exhaustive release bar.
---

# BT6 release readiness: `<candidate>`

## Context

- Repository: `<canonical repository>`
- Candidate commit: `<sha>`
- Comparison base: `<previous release or exact base>`
- Profile: `<path/version>`
- Authorization: `<read-only | repairs authorized>`

## Merged-risk inventory

| Surface | Changed behavior | Relevant tests/evidence | Risk | Status |
| --- | --- | --- | --- | --- |
| `<path/component>` | `<behavior>` | `<tests/artifacts>` | `<high/medium/low>` | `<covered/gap>` |

## Release-depth gates

| Gate | Threshold or expectation | Result | Evidence |
| --- | --- | --- | --- |
| Full validation | `<profile validation.full>` | `<pass/fail/not run>` | `<artifact/log>` |
| Coverage and regression | `<repository/scope/module floors>` | `<pass/fail>` | `<coverage report>` |
| Quality depth | `<repeat/mutation/warnings>` | `<pass/fail/not run>` | `<artifact/log>` |
| Source snapshot and supply chain | `<policy>` | `<pass/fail/not run>` | `<ZIP/evidence/log>` |
| Conditional/platform checks | `<policy>` | `<pass/fail/deferred>` | `<artifact/CI URL>` |

## Repairs

| Finding | Correction | Verification | Residual risk |
| --- | --- | --- | --- |
| `<gap>` | `<code/test/policy change>` | `<command/result>` | `<risk>` |

## Decision

`<ready-to-tag | not-ready | hold>`

This report is pre-tag evidence only. Any candidate, dependency, test, policy,
platform, or release-configuration change invalidates it. Exact-tag
`bt6-release-validation` remains required before artifact promotion.
