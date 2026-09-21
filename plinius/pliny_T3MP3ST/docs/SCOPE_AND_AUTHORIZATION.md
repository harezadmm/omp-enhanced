# Scope And Authorization Model

T3MP3ST is built for authorized security research, owned assets, labs, bug bounty scopes, internal red-team work, and evidence-backed defensive reporting.

The core rule is simple: a mission can be imaginative, aggressive, and adversarial, but the system must preserve scope, evidence, and operator accountability.

## Authority Layers

| Layer | Purpose | Example |
| --- | --- | --- |
| Human intent | The plain-language mission contract | "We own this staging API. Find high-impact risks and produce a fix plan." |
| Scope receipt | Proof that a target and action class are allowed | `command_execution` on `local-host`, or `network_request` for a named range |
| Tool gate | Adapter execution mode | `safe_command`, `receipt_required`, `catalog_only`, `import_only` |
| Evidence ledger | Durable proof before claims | command output, screenshot, report, note, receipt |
| Finding ledger | Claim plus impact and fix | severity, confidence, evidence IDs, acceptance criteria |
| Retest | Validation before promotion | queued, passed, failed, blocked |
| Memory proposal | Human-reviewed durable learning | no silent self-modification |

## Execution Modes

- `safe_command`: local-read or lab-safe command, still logged and evidence-oriented.
- `receipt_required`: active, networked, credential-adjacent, or otherwise risky command.
- `catalog_only`: known capability that should not run through generic command execution.
- `import_only`: evidence can be imported, but collection stays outside generic execution.

## Non-Negotiables

- No third-party target without explicit scope.
- No production writes without a named approval.
- No copying raw secrets, tokens, credentials, private keys, or recovered passwords into evidence.
- No generic execution surface for broad exploitation or credential tooling.
- Findings need evidence and retests before they become confident claims.
- Memory needs operator acceptance before it becomes durable.

## Reviewer Checklist

- Can I tell what target is in scope?
- Can I tell which action class is approved?
- Can I tell which tool output supports each claim?
- Can I retest the claim?
- Can a nontechnical stakeholder understand the risk and next action?
- Can a technical stakeholder reproduce the evidence?
