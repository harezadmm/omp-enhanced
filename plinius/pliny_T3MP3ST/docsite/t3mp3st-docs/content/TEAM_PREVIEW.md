---
title: "Team Preview"
summary: "Ten-minute preview path for evaluating the War Room and local-safe flows."
description: "Ten-minute preview path for evaluating the War Room and local-safe flows."
audience: ["operator", "maintainer"]
category: "operator"
status: "current"
source: "T3MP3ST repository"
sourcePath: "docs/TEAM_PREVIEW.md"
updated: "2026-07-20"
---
# T3MP3ST Team Preview

This preview is for prompt engineers, red-teamers, bug bounty operators, cyber researchers, and builders who want to pressure-test T3MP3ST before a broader release.

The useful mental model: T3MP3ST is an evidence-first adversarial AI command center. It is not only a scanner UI. It routes a mission into specialist agent lanes, binds tool output to evidence, promotes evidence into findings, retests claims, and only then proposes durable learning.

## Ten-Minute First Run

```bash
npm install
npm run doctor
npm run server
```

Open `http://127.0.0.1:3333/ui/`.

In the UI:

1. Click `preflight`.
2. Click `sync arsenal`.
3. Click `activation`.
4. Pick a guided start.
5. Run `plan tools`.
6. Log one evidence item, seed a hypothesis, and use the Watch Loop `pulse` to see what is missing.
7. Click Watch Loop `nudge` to split the hypothesis into work orders, complete one task, promote it, and queue one retest.
8. Run `gate` and `bundle`.
9. Run `review run` in the Learning Capsule.

Expected state on a fresh machine:

- The UI should load even without an LLM key.
- LLM calls should fail closed with a clear message.
- The arsenal should distinguish catalog tools, wired adapters, and locally installed tools.
- Missing binaries should be shown as activation work, not hidden as success.

## What Is Real Today

- Express API server and static command-center UI.
- Mission drafts, route previews, mission bundles, and mission gates.
- Resource packs, agent prompt packs, operator runbooks, and forefront pressure lanes.
- Tool adapter catalog with execution modes, evidence kinds, install hints, and receipt gates.
- ScopeGuard approvals for active or networked operations.
- Evidence, hypothesis graph, hunt queue work orders, findings, retests, and accepted-memory proposal flow.
- Watch Loop pulses that surface stale hypotheses, receipt gates, missing disproof, open work orders, retest gaps, and learning proposals.
- Full local smoke scripts for API, arsenal, field drills, exploit-chain simulation, and prompt packs.

## What Is Preview

- Specialist agents are represented by route contracts, prompt packs, runbooks, and orchestration surfaces; production multi-agent execution still needs provider configuration and deeper harness hardening.
- Some Pliny Specials endpoints use synthetic payloads or local-safe demos to validate orchestration shape.
- Catalog-only tools are intentionally modeled but not executable through generic command dispatch.
- Installed tool readiness depends on the local workstation; see `docs/ARSENAL_ACTIVATION_PLAN.md`.

## Demo Missions

Run all local-safe demos:

```bash
npm run field:drill
npm run exploit:smoke
npm run arsenal:smoke
npm run prompt:audit
```

Run one focused field drill:

```bash
npm run field:drill -- --scenario=local-web-api
npm run field:drill -- --scenario=repo-supply-chain
npm run field:drill -- --scenario=ai-agent-boundary
```

Use `examples/demo-missions.json` for plain-language mission seeds that can be copied into the Mission Contract box.

## Feedback We Want

- Where does the UI make the operator feel uncertain?
- Which mission family needs the next real adapter?
- Which prompt pack has the strongest or weakest evidence contract?
- Which hypothesis, work-order, finding, retest, or learning states feel ambiguous?
- Which Watch Loop signals are actionable, noisy, or missing from the always-on hunt?
- Which features look real but should be labeled as preview?
- Which workflow should be one click easier for nontechnical operators?

## Ship Gate For Team Builds

Before pushing a team preview branch, run:

```bash
npm run typecheck
npm test
npm run doctor
npm run arsenal:smoke
```

If the API is not running, `doctor` still checks local files and commands. If the API is running, it also checks health, preflight, arsenal status, and activation metadata.
