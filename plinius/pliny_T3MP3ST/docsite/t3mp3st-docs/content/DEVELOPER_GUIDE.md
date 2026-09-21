---
title: "Developer Guide"
summary: "Architecture, local development, scripts, extension points, and release checks."
description: "Architecture, local development, scripts, extension points, and release checks."
audience: ["developer", "maintainer"]
category: "developer"
status: "current"
source: "T3MP3ST repository"
sourcePath: "docs/DEVELOPER_GUIDE.md"
updated: "2026-07-20"
---
# T3MP3ST Developer Guide

This guide maps the codebase to the public surfaces documented for operators and integrators.

## Local Development

```bash
npm install
npm run build
npm test
npm run lint
```

Useful focused checks:

```bash
npm run typecheck
npm run doctor
npm run test:no-phantom-tools
npm run arsenal:smoke
npm run smoke
```

Run the HTTP API and UI during development:

```bash
npm run server
```

Run the CLI from TypeScript:

```bash
npm run dev
```

Run the built CLI:

```bash
npm run build
npm start
```

## Pagenary Docsite

The publishable documentation site is generated with Pagenary from the Markdown docs in this repository.

```bash
npm run docs:sync     # regenerate docsite/t3mp3st-docs from docs/*.md
npm run docs:build    # build dist/t3mp3st-docs
npm run docs:check    # build and verify Pagenary publishing artifacts
npm run docs:serve    # build and serve http://127.0.0.1:5173/t3mp3st-docs/
```

Set `PAGENARY_SITE_URL` before `docs:sync` or `docs:build` when publishing somewhere other than the default GitHub Pages-style URL.

## Source Map

| Path | Responsibility |
|---|---|
| `src/cli.ts` | Commander-based CLI: interactive mode, setup, status, test, and model listing |
| `src/server.ts` | Express API server and static War Room UI host |
| `src/index.ts` | Public SDK exports, `TempestCommand`, factory helpers, and composed `Tempest` instance |
| `src/types/index.ts` | Shared TypeScript contracts for LLMs, operators, targets, findings, tools, missions, and reports |
| `src/config/index.ts` | Persistent configuration, provider defaults, API key helpers, and model registry |
| `src/llm/index.ts` | LLM provider adapters and tool-call normalization |
| `src/net/proxy.ts` | Optional outbound SOCKS5 proxy configuration for test/attack traffic |
| `src/arsenal/` | Built-in tools, external adapter catalog, approval gates, parser helpers, and post-exploitation gatekeeping |
| `src/mission/` | Mission, rules-of-engagement, task queue, and adjudication logic |
| `src/evidence/` | Evidence vault, findings, redaction, integrity checks, and retest support |
| `src/general/` | Autonomous Op General planning and execution orchestration |
| `src/resources/` | Prompt packs, runbooks, resource packs, workflow presets, and playbooks |
| `src/mcp-server.ts` | MCP stdio server exposing `security_recon` |
| `scripts/` | Verification, benchmark, smoke, update, disclosure, and release helper scripts |
| `docs/` | Operator, developer, benchmark, release, and provenance documentation |

## Public SDK

The package exports the main factory functions and core classes from `src/index.ts`.

```ts
import { createTempest, createTestTempest } from 't3mp3st';

const tempest = createTempest({
  name: 'Authorized Lab Run',
  llm: {
    provider: 'mock',
    model: 'mock-model',
    maxTokens: 4096,
    temperature: 0.7,
  },
  opsec: {
    level: 'covert',
    maxDetectionEvents: 3,
    cleanupOnComplete: true,
  },
});

tempest.command.start();
```

For tests, prefer `createTestTempest()` unless the test specifically needs a provider adapter.

## HTTP Server

`src/server.ts` hosts the War Room at `/ui/` and exposes JSON endpoints under `/api/`. It binds to `127.0.0.1:3333` by default. The server includes a localhost CORS/origin guard and a loopback Host-header guard because many endpoints can dispatch local tools.

See [API Reference](#api-reference) for route groups.

Provider state comes from `src/config/index.ts`. Current provider families include hosted OpenAI-compatible APIs, direct Anthropic/OpenAI-style APIs, DeepSeek, LiteLLM proxy, local OpenAI-compatible servers, and connected local coding-agent CLIs.

When adding an endpoint:

1. Keep state-changing methods behind the existing origin guard.
2. Validate request bodies before using them in shell, file, or model calls.
3. Redact secrets before writing evidence, ledgers, reports, logs, or responses.
4. Attach outputs to evidence or status structures instead of returning opaque strings.
5. Add a focused test if the endpoint changes security, persistence, routing, or evidence behavior.

## Arsenal Tools

Built-in tools live in `src/arsenal/index.ts`; external adapter metadata lives in `src/arsenal/catalog.ts`.

Tool additions should define:

- Name, description, parameters, and risk tier
- Scope behavior for active or networked operations
- Evidence kind and output shape
- Availability or install hint for external binaries
- Tests for refusal, parsing, redaction, or scope behavior when applicable

Dangerous tools must not be exposed through generic command execution. Add narrow adapters with explicit approvals and receipt gates.

## MCP Server

`npm run mcp` starts the stdio MCP server from `src/mcp-server.ts`. It currently exposes one tool, `security_recon`, for DNS and nmap reconnaissance against a hostname or IP. See [MCP Guide](#mcp-guide).

## Documentation Sync

Use code-to-docs review when public behavior changes:

```bash
aiwg discover "doc-sync code2doc"
aiwg show skill doc-sync
```

For this repository, the highest-value docs sync scope is:

```text
README.md, docs/, package.json, src/cli.ts, src/server.ts, src/index.ts, src/mcp-server.ts, src/arsenal/
```

Keep claims tied to source, scripts, tests, or committed benchmark artifacts. If a headline metric changes, run `npm run verify-claims` and update the relevant benchmark documentation in the same change.

## Release Gate

Before a release or broad documentation claim change, run:

```bash
npm run typecheck
npm test
npm run doctor
npm run verify-claims
npm run arsenal:smoke
```

If a check cannot run in your environment, document the reason in the PR using [Contribution Receipts](#contribution-receipts).
