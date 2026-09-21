---
name: business-logic-vuln
description: >-
  Entry P1 category router for business logic testing. Use when workflow abuse,
  race conditions, pricing flaws, or multi-step state attacks matter more than
  parser-level input injection.
---

# Business Logic Router

This is the routing entry point for business-logic and state-machine issues.

## When to Use

- The target involves coupons, inventory, payment, approvals, quotas, invites, trials, or state transitions
- The issue is not parser-level; it is about when checks happen and which business conditions are checked
- You suspect race conditions, workflow bypass, price tampering, negative values, stacked discounts, or multi-step flaws

## Skill Map

- [Business Logic Vulnerabilities](../business-logic-vulnerabilities/SKILL.md)

## Recommended Flow

1. First map key business states and one-time actions
2. Then check for check-then-act windows, sequence dependencies, or missing cross-step authorization
3. If the chain depends on APIs, uploads, or object permissions, return to the corresponding router skill to complete the path

## Related Categories

- [api-sec](../api-sec/SKILL.md)
- [auth-sec](../auth-sec/SKILL.md)
- [file-access-vuln](../file-access-vuln/SKILL.md)
## 1. CONFIRMING THE ROUTE

A router produces **one** artefact: the correct destination for an observed behaviour. Confirming a route
means the destination was reached by a **resolved link** and that the destination's own dispatch table was
then consulted - never that a technique was recalled from memory.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **observed behaviour** recorded before the route is chosen? | routing is decided by the sink, not by the parameter's name |
| 2 | Is there a **negative control**: a benign value leaving the response unchanged? | the difference is caused by your input, not application noise |
| 3 | Was the destination **loaded by resolving its link**, and did the load succeed? | a route that 404s makes the agent proceed from memory |
| 4 | Was the destination's **own dispatch table** then applied? | the destination re-decides the workflow assumption before a technique is chosen |
| 5 | Is the **interpreter/sink named**, not the payload family? | the technique, severity, and fix all follow from the interpreter |
| 6 | Is **one interpreter at a time** observed, with a probe that distinguishes it? | probing the wrong sink burns the endpoint's error budget and teaches nothing |
| 7 | If no row matches, was the **non-coverage statement** followed? | absence of a route is information |

**A resolved link, a named sink, and a negative control.** A route chosen from the input's appearance rather
than its sink is the single most expensive mistake in this domain, because the wrong subtree is probed, comes
back clean, and the finding is recorded as "no issue".

---

## 2. EVIDENCE STANDARD

The router's evidence is **the route and the observation that justifies it**, plus the dispatch trail.

| Item | Why |
|---|---|
| The observed behaviour, verbatim, before any routing decision | The route is a conclusion about this observation; record the premise |
| The benign request and the probe request, both verbatim, plus both responses | Routing on a difference requires both sides of the difference |
| The negative control value and its unchanged response | Separates your input's effect from "this endpoint fails on everything" |
| The **sink/interpreter identified**, with the observation that established it | The destination is derived from the sink, so the sink is the load-bearing fact |
| The destination domain **actually loaded**, and that its link resolved | A resolved link is the router's own correctness condition |
| The probe that **distinguished** the chosen sink from the neighbouring candidates | the probe that demonstrates the sequence violation, not just a malformed value |
| Any route **not taken** and why it was excluded | The eliminated branches are half the routing argument |
| The return path when nothing matched | the instruction to return to the parent router is present and followed |

### Route failures - how they mislead

| Route failure | How it misleads |
|---|---|
| Routed on the parameter's **name** rather than the sink | The wrong subtree is probed, returns clean, and a real finding is closed as "no issue" |
| Routed on a **500 or an error page** | Many parsers fail on any malformed value; an error is not a reachable sink |
| **Two plausible interpreters**, only one row taken | The untested one is silently marked clean and coverage is claimed for a sink never reached |
| Route followed **from memory** after a dead link | The agent believes it loaded doctrine while proceeding without it |
| **No negative control** | Application noise is reported as input-coupled behaviour |
| **In-band assumption on a blind sink** | Timing and out-of-band channels are never attempted, so a real vulnerability is reported as not reproducible |
| A **destination consolidated away** while its row survives | The router looks complete while dispatching into nothing |
| A **workflow-only domain** routed as a technique | Phantom coverage: the file loaded never describes a testing procedure |

---

---

## 3. DISPATCH VERIFICATION

Business logic has the smallest skill map of any router and the largest number of false
entries: many targets *look* like logic problems because they involve money, while the bug is
actually authorization, injection, or a race primitive. Verify the domain before you commit.

| Step | Question | What it proves |
|---|---|---|
| 1 | Can you name the business states and the transition that must not be skippable? | Logic testing requires a state machine; without one there is nothing to violate |
| 2 | Does the bug exist with a *well-formed, expected* input value, correctly parsed and correctly authorized? | Confirms the flaw is in the rules, not in a parser — otherwise route to [injection-checking](../injection-checking/SKILL.md) |
| 3 | Is the same request, sent as a different user, correctly denied? | The subject is entitleable, so this is not an authorization gap → route to [auth-sec](../auth-sec/SKILL.md) |
| 4 | Does the flaw survive being sent once, serially, with no concurrency? | Separates the durable logic bug from a race-only window, which needs its own methodology |
| 5 | Does the operation have a one-time semantic (coupon, invite, reset, trial, stock decrement)? | The replay and concurrency window is the primary route here |
| 6 | Do two steps exist where each is individually valid but the *combination* is not? | Sequence and check-then-act are the core of this domain |
| 7 | Is the affected resource an API object whose identifier you can address? | The chain likely needs object authorization → [api-sec](../api-sec/SKILL.md) |
| 8 | Does the flow involve an uploaded or served file as part of the state (receipt, export, import)? | The chain passes through [file-access-vuln](../file-access-vuln/SKILL.md) |

**"It involves money" is not evidence of a logic bug.** Price fields that accept a discount
code are normal; the finding is that a *state which should be unreachable* was reached. Verify
the reachability claim before writing anything up.

## 4. OUTPUT STANDARD

| Item | Why |
|---|---|
| The state machine as a diagram or ordered list, with the transition that was violated marked | A logic finding is a statement about a state machine; without it the report cannot be verified |
| The exact multi-step sequence, step by step, with each request and response in order | Order is the vulnerability; extracted requests lose the finding |
| The invariant that should have held ("total ≥ 0", "each coupon once", "stock never negative") | States the rule that was broken in the business's own terms |
| The observed state versus the expected state, with the artefact that proves the observed one (balance, order record, inventory count) | Logic bugs are proven by persisted state, not by a response code |
| Whether the flaw is durable or concurrency-only, and if concurrency-only, the number of parallel attempts needed | Changes severity and the fix (idempotency vs. locking) |
| The financial or entitlement impact, quantified where possible | This class is reported on impact, unlike parser bugs |
| Whether the same flaw reproduces with a fresh account and a fresh session | Rules out a stale-cart or cached-price artefact |
| The rule the application *does* enforce correctly, as a control | Proves the application has business rules and that you found the one that is missing |

### Routing failures — how they mislead

| Routing failure | How it misleads |
|---|---|
| A transaction flow involving money routed here when the real bug is missing object authorization | Pricing logic is audited extensively and found correct, while the cross-account order read that carries the actual impact is never tested |
| A malformed-value bug routed here instead of [injection-checking](../injection-checking/SKILL.md) | The flaw is reported as a business rule that should have rejected the value, when the correct fix is parser/validation hardening — wrong owner, wrong severity |
| A serial test concluded from a race-only window | The concurrency requirement is absent from the writeup, so the finding is dismissed as "not reproducible" by the reader |
| A one-time operation tested once, serially, with a single identity | The replay and parallel windows — the highest-yield logic primitive — are never attempted |
| An entitlement bug routed here instead of [auth-sec](../auth-sec/SKILL.md) | The flaw is written as a pricing weakness rather than a broken authorization boundary, which changes the fix entirely |
| Two steps each tested in isolation and each found valid | Combination-only flaws are structurally invisible to step-by-step testing and are reported as "flow behaves correctly" |
| A logic finding written without the persisted state artefact | Only a response code supports the claim; any reviewer re-running the flow sees a normal result and the report is withdrawn |
| A flow whose chain depends on an API or upload treated as complete here | The router's own exit instruction is skipped, so the composite exploit path is never assembled |

## 5. MAINTENANCE REFERENCE — KEEPING THIS ROUTER CORRECT

A router is a **map**, and a map is wrong the moment the terrain moves. Every item below is
a concrete, checkable fix — not advice. Run them after any edit under `skills/impl/`.

1. **Every link resolves.** A route that 404s is worse than no route: the agent believes it
   has loaded doctrine and proceeds from memory, which is precisely what the skill-invocation
   rule forbids. Assert this with a link check, not by reading.
2. **Every domain in the routing table exists on disk.** A domain can be renamed or
   consolidated away while its row survives, producing a dead route. Domains named here:
   `business-logic-vulnerabilities`.

3. **No duplicate routes.** The same observed behaviour must not appear twice with two
   different destinations. Where two domains genuinely overlap (the short `attack-*`
   methodology files and their long-form playbooks), the row must say so and instruct the
   agent to load both, rather than leaving two identical-looking entries.
4. **Coverage counts stay accurate.** Any count stated here must match the number of distinct
   deep topic skills actually routed. Counting prose mentions inflates coverage; counting only
   links that resolve to an existing `SKILL.md` is the correct denominator.
5. **Re-verify when a domain is added or removed.** Adding a domain under `skills/impl/` is an
   incomplete change until this router routes it or records it as deliberately unrouted.
   Removal is the same change in reverse — prune the row *and* the count in one commit.
6. **Prune dead domains.** A scheduled or CI link check that resolves every destination here
   prevents the slow rot where routes point at skills that were consolidated away and the
   router looks complete while dispatching into nothing.
7. **Workflow-only domains stay excluded.** CORE.md records 36 of the 199 `impl/` domains as
   agent-workflow and meta-tooling skills (handoff, writing, TDD, setup) that are not
   kill-chain techniques. Routing them manufactures phantom coverage: the agent loads a file
   that never describes a testing procedure.
8. **Ordering and phase stay consistent with CORE.md.** This router is reached from the phase
   table and dispatch block in `CORE.md`. If phases are re-cut there, the recommended flow
   here must move with them, or the router will dispatch into a phase the kill chain no
   longer contains.
9. **A self-check script exists.** `sv_check.sh` at the repository root is the existing
   precedent: it asserts size, section count, a fenced block, link liveness, and topic
   keywords. A router check is the same shape — link resolution, domain existence, domain
   count, fence parity, and presence of the three closing sections.

    ```bash
    # router self-check — run from the repository root
    f=skills/impl/business-logic-vuln/SKILL.md
    echo "bytes: $(wc -c <"$f")  numbered sections: $(grep -c '^## [0-9]' "$f")"
    d=$(dirname "$f")
    # 1. every relative link must resolve to a real file
    grep -oE '\]\(\.\./[^)]+\)' "$f" | tr -d '](' | sed 's/)$//' | sort -u |
      while read -r p; do [ -f "$d/$p" ] || echo "DEAD LINK $p"; done
    # 2. fence parity must be even
    n=$(grep -c '^\x60\x60\x60' "$f"); [ $((n % 2)) -eq 0 ] || echo "ODD FENCE COUNT: $n"
    # 3. the three closing sections must be present and numbered
    for s in 'DISPATCH VERIFICATION' 'OUTPUT STANDARD' 'MAINTENANCE REFERENCE'; do
      grep -q "^## [0-9]*\. $s" "$f" || echo "MISSING SECTION: $s"; done
    ```

10. **The router states what it does NOT cover.** Absence of a route is information; silence
    is not. A target that reaches this domain and matches no technique here must be told to
    return to the P0 router rather than told nothing. Update the non-coverage statement
    whenever the boundary moves.

---

## 6. REMEDIATION REFERENCE - CONFORMANCE OF THE ROUTE

1. **Fix the row when the workflow assumption changes.** A sequence violation is proven by a state
   transition, not by a malformed value, and a row that routes on input shape misses the whole class.
2. **Require the sequence probe in the row.** State the observation that demonstrates the violation -
   the order of steps, the state at each one, and the state that should have been impossible.
3. **Route race conditions to their own row.** Concurrency and sequencing are different findings with
   different proofs.
4. **Prune removed destinations with their counts.**
5. **Keep the return path to the parent router current.**
6. **Re-run the link check after any `skills/impl/` edit.**

---

## 7. RELATED ROUTERS
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — The deep playbook this router dispatches to
- [api-sec](../api-sec/SKILL.md) — When the logic chain runs through API objects and identifiers
- [auth-sec](../auth-sec/SKILL.md) — When the missing check is authorization, not a business rule
- [file-access-vuln](../file-access-vuln/SKILL.md) — When the flow passes through an upload or served artefact
- [hack](../hack/SKILL.md) — the P0 master router; return here when no route above matches
- [CORE.md](../../../CORE.md) — the kill-chain phases this router dispatches into
