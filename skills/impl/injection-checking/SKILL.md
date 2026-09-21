---
name: injection-checking
description: >-
  Entry P1 category router for injection testing. Use when routing between XSS,
  SQLi, SSRF, XXE, SSTI, command injection, and NoSQL injection workflows based
  on how attacker-controlled input is consumed.
---

# Injection Testing Router

This is the routing entry point when input reaches a dangerous interpreter or execution environment.

After confirming this is an injection-class issue, use it to decide whether it is mainly browser context, database, template engine, server-side requests, XML parsing, or system commands.

## When to Use

- Input reaches HTML, JS, SQL, templates, URL fetchers, XML parsers, or shell
- You have not yet decided whether to start with XSS, SQLi, SSRF, XXE, SSTI, CMDi, or NoSQL
- You need to choose the correct deep-topic skill based on input flow

## Skill Map

- [XSS Cross Site Scripting](../xss-cross-site-scripting/SKILL.md)
- [SQLi SQL Injection](../sqli-sql-injection/SKILL.md)
- [SSRF Server Side Request Forgery](../ssrf-server-side-request-forgery/SKILL.md)
- [XXE XML External Entity](../xxe-xml-external-entity/SKILL.md)
- [SSTI Server Side Template Injection](../ssti-server-side-template-injection/SKILL.md)
- [CMDi Command Injection](../cmdi-command-injection/SKILL.md)
- [NoSQL Injection](../nosql-injection/SKILL.md)
- [Deserialization Insecure](../deserialization-insecure/SKILL.md)
- [JNDI Injection](../jndi-injection/SKILL.md)
- [Expression Language Injection](../expression-language-injection/SKILL.md)
- [CRLF Injection](../crlf-injection/SKILL.md)
- [Extra Injection Types (SSI, LDAP, XPath)](./EXTRA_INJECTION_TYPES.md)
- [Request Smuggling](../request-smuggling/SKILL.md)
- [Prototype Pollution](../prototype-pollution/SKILL.md)
- [Type Juggling](../type-juggling/SKILL.md)
- [HTTP Parameter Pollution](../http-parameter-pollution/SKILL.md)
- [XSLT Injection](../xslt-injection/SKILL.md)
- [CSV Formula Injection](../csv-formula-injection/SKILL.md)

## Recommended Flow

1. First identify the final sink of the input
2. Then choose the topic skill that best matches that interpreter
3. Small payload samples and quick triage are merged into each main skill; no extra payload router is needed

## Related Categories

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
| 4 | Was the destination's **own dispatch table** then applied? | the destination re-decides the sink among its own subtree before a technique is chosen |
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
| The probe that **distinguished** the chosen sink from the neighbouring candidates | the probe that separates this interpreter from its nearest neighbour |
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

Injection is decided by the **final interpreter**, not by the parameter's name. Verify the
sink before choosing a technique — a dispatch made on input appearance is the single most
expensive mistake in this domain.

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the input reach a *sink* whose output you can observe (response body, error, timing, out-of-band callback)? | You have a testable channel at all; without one this is not yet injection work |
| 2 | Does the input travel through a fetch/HTTP client constructed server-side (`curl`, `requests`, webhook, image proxy)? | SSRF → [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) |
| 3 | Does the value appear in the response in HTML, an attribute, or inline JS — *rendered* rather than echoed? | Browser interpreter → [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) |
| 4 | Does a quote break the statement *or* does the database shape its response (boolean/length/time) to injected subexpressions? | SQL interpreter → [sqli-sql-injection](../sqli-sql-injection/SKILL.md) |
| 5 | Is the body a query document / JSON-shaped filter rather than SQL text? | Document store → [nosql-injection](../nosql-injection/SKILL.md) |
| 6 | Does a template expression (`{{7*7}}`, `${7*7}`, `<%= 7*7 %>`) evaluate where literal text was expected? | Template engine → [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) |
| 7 | Is the body XML/SVG/Office-derived, or does it contain a DTD/`DOCTYPE` reference? | XML parser → [xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) |
| 8 | Does the value reach `sh -c`, `exec`, a filename argument, or a CLI flag? | OS interpreter → [cmdi-command-injection](../cmdi-command-injection/SKILL.md) |
| 9 | Does the value enter a `Runtime.exec`, `LDAP` filter, EL expression, JNDI lookup, or a native-deserialization stream? | Non-SQL interpreter → [jndi-injection](../jndi-injection/SKILL.md), [expression-language-injection](../expression-language-injection/SKILL.md), [deserialization-insecure](../deserialization-insecure/SKILL.md) |
| 10 | Do you have a *negative control* — a benign value that leaves the response byte-identical? | Proves the difference you are seeing is caused by your input and not by application noise |

**A 500 is not proof of injection.** Many parsers 500 on any malformed value. The proof is
**input-coupled response change**: a benign value produces output A, a probe produces output
B, and B varies monotonically with the probe. Timing-based channels need repeated sampling
before they count.

**One interpreter at a time.** If you send an XSS probe at an SQL sink, you learn nothing and
burn the endpoint's error budget. Identify the sink, then dispatch.

## 4. OUTPUT STANDARD

| Item | Why |
|---|---|
| The identified sink, named as an interpreter (SQL, template, OS shell, XML parser, browser DOM), and the evidence that established it | The technique, severity, and fix all follow from the interpreter; a finding without it cannot be reviewed |
| The exact benign request and the exact probe request, both verbatim, plus both responses | Injection claims are difference claims; both sides of the difference are the evidence |
| The negative control value and its byte-identical response | Proves the change was caused by the probe and not by "this endpoint 500s on everything" |
| Whether execution is confirmed, inferred, or theoretical | Confirmed execution and a stack trace are different severities and must never be merged |
| The channel used when it is not the response body (OOB callback, timing, error text, log entry) | Blind injection is only reportable with an out-of-band artefact |
| What data or capability the interpreter actually reached (table, file, command, key material) | Turns "injection exists" into an impact statement |
| The parameter *and* its location (path, query, JSON body field, header, filename, template name) | The same value in a header often has a different sink than in the body |
| Whether the payload survived a WAF and which encoding was required | Determines exploitability for the reporter and the fix for the defender |

### Routing failures — how they mislead

| Routing failure | How it misleads |
|---|---|
| Input appearance used instead of the sink (a `'` in the body routed to SQLi) | SQL is probed at a template sink and vice versa; both come back clean and the finding is recorded as "no injection" |
| A reflected parameter routed to XSS before the output context is known | Attribute/JS/URL-sink contexts are mutated in the wrong place; the payload is escaped by a sanitiser that does not apply, and real exploitability is never established |
| A server-side URL fetch routed to SSRF without checking for a redirect/`Location` follow | Client-side open redirect is misreported as SSRF, inflating severity and misdirecting the fix |
| XML accepted but routed to generic SQLi | Entities, DTDs, and file reads are never attempted; the parser is treated as a data format rather than an interpreter |
| A binary deserialization sink routed to `cmdi` | The gadget chain, not the shell, is the exploitation path; the test returns nothing and the highest-severity class in the subtree is closed |
| A JSON body routed to SQLi when the store is document-based | Operator injection (`$gt`, `$where`) is never tried; the finding is dismissed as "ORM-protected" |
| Two interpreters both plausible, only one row taken | The untested one is silently marked clean; coverage is claimed for a sink that was never reached |
| An in-band-only assumption made on a blind sink | Timing and OOB channels are never used, so a real vulnerability is reported as not reproducible |

## 5. MAINTENANCE REFERENCE — KEEPING THIS ROUTER CORRECT

A router is a **map**, and a map is wrong the moment the terrain moves. Every item below is
a concrete, checkable fix — not advice. Run them after any edit under `skills/impl/`.

1. **Every link resolves.** A route that 404s is worse than no route: the agent believes it
   has loaded doctrine and proceeds from memory, which is precisely what the skill-invocation
   rule forbids. Assert this with a link check, not by reading.
2. **Every domain in the routing table exists on disk.** A domain can be renamed or
   consolidated away while its row survives, producing a dead route. Domains named here:
   `xss-cross-site-scripting` `sqli-sql-injection` `ssrf-server-side-request-forgery` `xxe-xml-external-entity` `ssti-server-side-template-injection` `cmdi-command-injection` `nosql-injection` `deserialization-insecure` `jndi-injection` `expression-language-injection` `crlf-injection` `request-smuggling` `prototype-pollution` `type-juggling` `http-parameter-pollution` `xslt-injection` `csv-formula-injection`.

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
    f=skills/impl/injection-checking/SKILL.md
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

1. **Fix the row, not the probe.** When the sink's interpreter changes, the row's signal text changes with
   it; a row matching input *appearance* routes every `'` to SQLi and closes real findings as "no issue".
2. **Keep one interpreter per row.** A row that spans two sinks is untestable; split it so the probe that
   distinguishes them is explicit.
3. **Record the negative-control requirement in the row.** A route taken without a benign control inverts
   the whole subtree's confidence.
4. **Prune a destination and its count together.** A row pointing at a consolidated domain dispatches into
   nothing while the table looks complete.
5. **Keep the return path current.** Where no row matches, the router must send the agent back to the P0
   router, not leave it to invent a category.
6. **Re-verify links after any `skills/impl/` change.** A 404 route is worse than no route.

---

## 7. RELATED ROUTERS
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) — Browser interpreter — HTML, attribute, and JS sinks
- [sqli-sql-injection](../sqli-sql-injection/SKILL.md) — SQL interpreter — quote break, boolean, time, and error channels
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) — Server-side fetch primitive
- [xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) — XML parser — entities, DTDs, and file reads
- [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) — Template engine evaluation
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — OS shell and CLI argument sinks
- [nosql-injection](../nosql-injection/SKILL.md) — Document stores and JSON operator injection
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — Native deserialization and gadget chains
- [jndi-injection](../jndi-injection/SKILL.md) — JNDI lookups and remote class loading
- [expression-language-injection](../expression-language-injection/SKILL.md) — EL and expression evaluation sinks
- [crlf-injection](../crlf-injection/SKILL.md) — Header and response-splitting sinks
- [request-smuggling](../request-smuggling/SKILL.md) — Request-layer framing mismatch
- [prototype-pollution](../prototype-pollution/SKILL.md) — Object prototype sinks and client-side chains
- [type-juggling](../type-juggling/SKILL.md) — Loose comparison and weak-type sinks
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) — Duplicate-parameter parsing mismatch
- [xslt-injection](../xslt-injection/SKILL.md) — XSLT processing sinks
- [csv-formula-injection](../csv-formula-injection/SKILL.md) — Spreadsheet export sinks
- [hack](../hack/SKILL.md) — the P0 master router; return here when no route above matches
- [CORE.md](../../../CORE.md) — the kill-chain phases this router dispatches into
