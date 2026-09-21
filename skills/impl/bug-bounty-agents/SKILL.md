---
name: bug-bounty-agents
description: "Bug bounty agent design — specialization by vulnerability class, scope guardrails, and validation discipline"
category: "offensive-tooling"
version: "1.1"
author: "cyberstrike-official"
tags:
  - bug-bounty
  - agents
  - automation
  - triage
  - methodology
tech_stack:
  - llm
  - web
cwe_ids: []
chains_with:
  - autopentestx
  - security-reporting-and-documentation
prerequisites: []
severity_boost: {}
---

# Bug Bounty Agents

> **AI LOAD INSTRUCTION**: This skill is about designing **specialised agents for bug bounty
> work** — prompts scoped to one vulnerability class, with an explicit scope guard and a
> validation requirement. The architectural insight is that **specialisation beats
> generalisation**: an agent that knows SSRF deeply will find SSRF classes a general-purpose
> agent walks past, because it carries the specific test matrix rather than a broad checklist.
>
> The failure mode to design against is **the confident hallucination**: an agent that reports
> a finding it has not verified, in a format that looks authoritative. In a bug bounty context
> this is expensive — a false report costs reputation and triager time, and an unverified
> exploit claim against a production target can cause real damage.
>
> Therefore: **every agent prompt must require evidence of reproduction, must forbid testing
> outside the declared scope, and must be able to return "no finding" as a success.** An agent
> that cannot say "I found nothing" will invent something instead.

## 0. RELATED ROUTING

- [autopentestx](../autopentestx/SKILL.md) — the pipeline architecture these agents slot into
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — where agent output must land
- [recon-and-methodology](../recon-and-methodology/SKILL.md) — the scope contract an agent must respect
- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) — the manual depth a specialist agent should carry
- [recon-methodology](../recon-methodology/SKILL.md) — the stage before agent dispatch
- [orchestration](../orchestration/SKILL.md) — coordinating several specialist agents

---

## 1. WHY SPECIALISE

A general "find vulnerabilities" agent produces shallow coverage of everything. A specialised
agent carries a **test matrix** for one class.

| Agent | Carries |
|---|---|
| SSRF specialist | the cloud-metadata endpoints, the redirect chain, the DNS-rebinding sequence, the protocol list |
| API authz specialist | the two-account differential, the ID enumeration ranges, the HTTP-method variations |
| Race specialist | the single-packet technique, the specific endpoint classes, the timing discipline |
| Scope guard | the scope definition and the veto |

**The difference is the test matrix, not the model.** A general agent will try `?url=http://evil.com`.
A specialist knows to try `http://169.254.169.254/latest/meta-data/`, the decimal and octal IP
encodings, the redirect chain, and the DNS-rebinding sequence — in that order, because that is
the order that finds things.

**Specialisation also bounds the blast radius.** A narrowly-scoped agent doing one class of
read-only test against one host is far less dangerous than an agent with broad latitude and an
exploitation tool.

---

## 2. THE SCOPE GUARD

**Every agent must have an explicit scope it cannot leave**, and a separate guard whose only
job is enforcement.

**The guard's rules:**

| Rule | Detail |
|---|---|
| deny beats allow | an excluded host inside an included range is out |
| fail closed | ambiguous scope means out |
| check before every request | not once at the start |
| forbid out-of-scope requests entirely | not "log and continue" |
| refuse destructive actions regardless of scope | DoS, data deletion, mass enumeration |
| enforce rate limits | a slow agent is a good agent |

**The guard should be able to veto another agent's action.** Architecturally, the guard is a
gateway: specialist agents propose requests, the guard approves or denies, and the approved
requests execute. That is a stronger design than trusting each specialist to self-police.

**A guard agent prompt must be able to say "no" and be heard.** If the specialists can bypass
the guard, the guard is decoration.

---

## 3. ANATOMY OF A SPECIALIST PROMPT

Every agent prompt in this family should contain these blocks, in this order.

**1. Identity and single class.** One vulnerability class. Not "web security".

```text
You are an SSRF audit specialist. You test for server-side request forgery only.
You do not test for XSS, SQLi, or authentication issues — another agent covers those.
```

**2. Scope, stated verbatim.** The exact hosts, and the exclusions.

```text
IN SCOPE: api.target.com, *.api.target.com
OUT OF SCOPE: payments.target.com, any third-party CDN or cloud metadata service you
do not own, and any host not matching the above.
If a discovered host is not in scope, do not send a single request to it. Record it
and move on.
```

**3. The test matrix.** The specific, ordered techniques. This is the value of specialisation.

```text
Test in this order, stopping at the first confirmed finding:
1. Literal cloud metadata endpoints (AWS, GCP, Azure, DigitalOcean, Alibaba)
2. IP encoding variants: decimal, octal, hex, IPv6-mapped
3. Redirect chains to an internal address (301, 302, 307, 308)
4. URL parser discrepancies: @, #, ?, backslash, double-encoding
5. DNS rebinding via a controlled hostname
6. Protocol smuggling: gopher://, dict://, file://
7. Blind confirmation via out-of-band interaction if no inline response
```

**4. The evidence requirement.** What counts as a finding.

```text
A finding REQUIRES: the exact request, the exact response (or an out-of-band callback
log), and a statement of what was reached. A differential (an internal-only header, a
metadata document, a service banner) is required. A reflected URL is NOT a finding.
If you cannot demonstrate the internal access, report NO FINDING.
```

**5. The permission to fail.**

```text
Returning "no finding, tested these 7 techniques, all negative" is a correct and
valuable result. Do not report a candidate you could not verify.
```

**The fifth block is the most important and the most frequently omitted.** Without it, an
agent optimises for producing output rather than accuracy.

---

## 4. VALIDATION DISCIPLINE

**An agent's output is a candidate, not a finding.** Build the validation step into the
workflow, never assume it.

| Agent claim | Validation required |
|---|---|
| "SSRF confirmed" | the internal response body or an out-of-band callback log |
| "IDOR confirmed" | a two-account differential with both requests and both responses |
| "race condition" | the two concurrent requests and the resulting broken invariant |
| "authentication bypass" | the request that succeeded and the access it produced |
| "RCE" | **command output**, with the command named |
| "XSS" | execution demonstrated in a browser, or the exact sink and payload |
| "rate limit bypass" | a baseline showing the limit and the bypass run |

**Three anti-patterns to design out:**

| Anti-pattern | Fix |
|---|---|
| a claim with no request/response pair | require the raw evidence in the output schema |
| "potentially vulnerable" / "may be exploitable" | require a binary confirmed/not-confirmed |
| a finding that assumes a gadget, library, or config | require the gadget be identified and verified |
| a finding generated from a scanner match alone | require manual reproduction |
| a severity with no impact statement | require the concrete consequence |

**Enforce this with the output schema.** A structured output requiring `evidence.request`,
`evidence.response`, and `impact` makes an unsupported claim impossible to emit — the agent
cannot fill the fields, so it reports no finding. **Schema enforcement is more reliable than a
prompt instruction.**

---

## 5. OUTPUT CONTRACT

Define a structured output so results are comparable and machine-consumable.

```json
{
  "agent": "ssrf-specialist",
  "target": "api.target.com",
  "class": "ssrf",
  "confirmed": true,
  "finding": {
    "endpoint": "/api/v1/fetch",
    "technique": "redirect chain to cloud metadata",
    "request": "GET /api/v1/fetch?url=http://169.254.169.254/latest/meta-data/iam/",
    "response_evidence": "HTTP/1.1 200 OK ... <redacted IAM role name>",
    "impact": "Instance IAM credentials reachable; role permits S3 read",
    "severity": "high",
    "severity_rationale": "Credential access to a role with data access"
  },
  "techniques_tested": 7,
  "techniques_negative": 6,
  "out_of_scope_encountered": [],
  "notes": "Redirect required a 307; 301 was blocked. Confirmed twice, 5s apart."
}
```

**Every field is load-bearing:**

| Field | Purpose |
|---|---|
| `confirmed` | binary; false is a valid and useful result |
| `techniques_tested` | proves coverage — an agent that tested nothing is visible |
| `request` / `response_evidence` | the reproduction |
| `impact` | forces the agent to state the consequence |
| `out_of_scope_encountered` | shows the guard worked |
| `notes` | the conditions and the reproducibility detail |

**`techniques_tested` is the anti-hallucination field.** An agent claiming a confirmed finding
after testing one technique is visible; so is one reporting a clean result after testing zero.

---

## 6. WHAT MAKES AN AGENT RESULT TRUSTWORTHY

| Signal | Meaning |
|---|---|
| a request/response pair for every claim | reproduced, not inferred |
| an explicit count of techniques tested | coverage is measurable |
| a "no finding" result appears regularly | the agent is not optimising for volume |
| severity rationales are specific | the agent reasoned about impact |
| out-of-scope hosts recorded but not tested | the guard held |
| the same finding reproduces on re-run | deterministic |
| claims are falsifiable | you can check them independently |

**A specialist agent that returns "no finding" on most targets is working correctly.** SSRF
is not present on most endpoints, and an agent that finds it everywhere has a false-positive
problem, not a discovery rate.

**Track precision, not volume.** Ten confirmed findings from ten dispatches is a working system.
Fifty claims needing manual rejection is a broken one.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the agent prompt used, verbatim | the output is only interpretable against the instructions |
| the scope it was given | provenance and safety |
| every request/response pair it produced | reproduction |
| the technique count and the negative list | coverage |
| the out-of-scope hosts it encountered and skipped | the guard worked |
| the model and version, if relevant | behaviour varies and findings must be attributable |
| a **control**: a re-run of the same dispatch | determinism |
| the human validation decision per claim | separates candidates from findings |

**Attribute findings to the agent and the prompt that produced them.** A finding that cannot be
traced back to the instructions is not reproducible.

**Failure modes:**

| Symptom | Cause |
|---|---|
| a finding with no request/response | no schema enforcement |
| "potentially vulnerable" language | no binary confirmed field |
| testing outside scope | a guard that can be bypassed |
| volume without precision | no human validation stage |
| the same claim repeated from a scanner | no reproduction requirement |
| severity inflation | no impact statement required |

---

## 8. REMEDIATION REFERENCE

For hardening a bug bounty agent setup:

1. **One vulnerability class per agent** — carry the specific test matrix; that is the entire advantage over a general agent.
2. **State scope verbatim in every prompt** and deny out-of-scope requests absolutely, not conditionally.
3. **Make the scope guard a gateway, not an instruction** — specialists propose, the guard approves, execution follows. Self-policing is not enforcement.
4. **Require a request/response pair for every claim** and enforce it with the output schema rather than with prose.
5. **Make "no finding" a first-class result** — an agent that cannot fail will fabricate.
6. **Require a technique count and a negative list** — this makes coverage measurable and hallucination visible.
7. **Never let an agent perform destructive or state-changing actions** — read-only testing for all automated agents; exploitation is manual and reviewed.
8. **Validate every claim before reporting it** — an agent's output is a candidate; a human confirms before it reaches a triager.
9. **Measure precision per agent** — retire or re-prompt any specialist whose claims are mostly rejected.
10. **Log every request an agent made, with the prompt that produced it** — attribution and reproducibility are what make agent-assisted work defensible.

---

## 9. CONFIRMING THE FINDING

An agent-assisted bounty produces **submissions**, and a submission is not a finding until a triager
accepts it. This table is what stands between a plausible report and a duplicate or an informative.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **programme's scope and rules** captured verbatim, including the out-of-scope list? | a report outside scope is closed, and repeated ones get you banned |
| 2 | Is the asset **owned by the programme** rather than a third party it merely serves? | shared infrastructure is the canonical scope trap |
| 3 | Was the **impact demonstrated**, not inferred from a scanner or a version banner? | triagers close version-only reports as informative |
| 4 | Is there a **control**: the same action succeeding without the flaw, or a benign input not triggering it? | the difference is the vulnerability |
| 5 | Was the **duplicate check** run - public reports, changelogs, the programme's own disclosures? | a duplicate is worth nothing and costs reputation |
| 6 | Is the **severity argument** tied to the programme's own rubric, not a generic CVSS? | each programme weights differently |
| 7 | Is the **reproduction exact** enough for a triager with no context to repeat it? | the triager's reproduction is the acceptance event |

**A scoped asset, a demonstrated impact, a duplicate check, and a reproduction a stranger can follow.**
An agent can produce volume; only these turn volume into accepted submissions.

---

## 10. EXECUTION PRIMITIVES

The agent layer changes the economics, not the discipline: **more candidates, the same proof bar.** Every
step below is a procedure, and the control pair is the vulnerable behaviour against the same request with
the flaw absent.

### 9.1 Scope and rules, captured before any agent runs

```bash
echo "=== 1. capture the programme's terms VERBATIM before an agent touches anything ==="
cat > programme.md <<'MD'
## IDENTITY
programme URL:
programme HANDLE:
date captured:            # the terms CHANGE; a dated copy is your defence

## IN SCOPE (verbatim from the programme)
assets:
  -                       # an apex domain, a wildcard, an app, an API, a source repo
asset value:              # the bounty table, per asset class

## OUT OF SCOPE (verbatim - THIS LIST IS THE ONE THAT GETS PEOPLE BANNED)
excluded:
  - third-party services the programme merely USES (a payment provider, a CDN, a support desk)
  - shared infrastructure, marketing sites, and status pages (often excluded)
  - social engineering, physical, DoS (almost always excluded)

## RULES
automated scanning permitted: yes/no/when
rate limits / user-agents required:
disclosure policy:            # coordinated? a fixed window?
duplicate policy:             # first reporter wins? does a partial report count?
MD
echo
cat <<'RULES'
  THE FOUR KILLERS, CHECKED BEFORE EVERY REPORT:
    1. THE ASSET IS THIRD-PARTY. A subdomain that CNAMEs to a vendor's SaaS is usually the VENDOR's
       asset, not the programme's. RESOLVE IT, and if it points off-programme, STOP.
    2. THE BEHAVIOUR IS INTENDED. A feature that the programme documents is not a bug. Check the docs.
    3. THE IMPACT IS THEORETICAL. 'An attacker could...' without a demonstrated step is informative.
    4. THE REPORT IS OUT OF SCOPE OR A KNOWN DUPLICATE. Cheapest to check, most expensive to skip.
RULES
```

**Resolve the asset and check it is the programme's** — a subdomain CNAMEing to a vendor's SaaS is usually
the vendor's asset, and that is the trap that gets reporters banned.

### 9.2 The agent layer, and where it is allowed to help

```bash
echo "=== THE AGENT BOUNDARY: what an agent may do, and what stays human ==="
python3 - <<'PY'
A = [("enumerate and correlate public data", "ALLOWED",  "volume work, no target impact"),
     ("draft a report from your notes",        "ALLOWED",  "structure and prose, your evidence"),
     ("suggest likely vulnerability classes",  "ALLOWED",  "a hypothesis to test, never a claim"),
     ("run an exploit against the target",     "HUMAN",    "impact and authorisation cannot be delegated"),
     ("decide the impact is critical",         "HUMAN",    "the severity argument is yours"),
     ("submit the report",                     "HUMAN",    "the account, and the reputation, are yours"),
     ("probe a third-party asset it inferred", "NEVER",    "scope is decided by the programme, not the agent")]
print("%-42s %-9s %s" % ("agent action","status","why"))
for a,b,c in A: print("%-42s %-9s %s" % (a,b,c))
print()
print("  THE RULE: AN AGENT MAY PRODUCE CANDIDATES; IT MAY NOT PRODUCE IMPACT. Everything that")
print("  touches the target, decides severity, or submits is a HUMAN ACTION, and the record must show")
print("  which human did it.")
print("  AND THE HALLUCINATION GUARD, which is specific to this domain: an agent asked to 'find")
print("  vulnerabilities' will produce a PLAUSIBLE FINDING WITH NO EVIDENCE, because that is what the")
print("  prompt asks for. EVERY agent claim must be re-derived by hand BEFORE it goes in a report,")
print("  and any claim you could not re-derive is deleted, not softened.")
PY
```

**An agent may produce candidates; it may not produce impact** — and every agent claim must be re-derived by
hand, then deleted if it cannot be.

### 9.3 The report, the severity argument, and the end-to-end harness

```bash
echo "=== THE REPORT, in the shape triagers accept ==="
cat <<'REPORT'
  title        : the asset, the flaw class, and the impact - in one line
  severity     : per the PROGRAMME'S rubric, with the programme's own terms
  asset        : the exact asset, and evidence it is in scope
  steps        : NUMBERED, from zero, reproducible by someone with no context
  evidence     : the raw request/response, or the POC video, with timestamps
  impact       : THE STEP DEMONSTRATED, and what an attacker gains from it
  remediation  : a specific fix, not 'sanitise input'
  and the honest section: WHAT YOU DID NOT TEST, and any assumption you made
REPORT
echo
echo "=== THE DUPLICATE AND NOVELTY CHECK, before writing ==="
cat <<'DUP'
  RUN ALL FIVE, AND RECORD THE RESULT OF EACH:
    1. the programme's OWN disclosed reports (HackerOne/Bugcrowd hacktivity, public reports)
    2. the CHANGELOG and security advisories of the target software and its dependencies
    3. the CVE database for the component and version
    4. a search for the exact behaviour, not the class ('the X parameter accepts Y')
    5. THE PROGRAMME'S OWN DOCS - a documented feature is not a finding
  IF IT IS A KNOWN ISSUE, SAY SO IN THE REPORT AND EXPLAIN WHAT IS NEW (a new vector, a new impact, a
  bypass of the published fix). 'Known issue, but here is what is different' is often accepted;
  silence followed by a duplicate tag is not.
DUP
echo
echo "=== the severity argument, tied to the programme's rubric ==="
cat <<'SEV'
  DO NOT PASTE A GENERIC CVSS VECTOR. DO THIS INSTEAD:
    - find the programme's severity table and QUOTE the row that applies
    - name the factors the programme weighs: authentication required? user interaction? data
      sensitivity? and the number of affected users or the value at stake
    - state the factor you are UNSURE about, and give both severities with the condition
  A PROGRAMME THAT WEIGHTS 'accounts affected' WILL RATE A LOW-CVSS MASS ISSUE ABOVE A HIGH-CVSS
  SINGLE-USER ONE. Your generic vector will read as naive.
SEV
echo
echo "=== end-to-end harness ==="
python3 - <<'PY'
print("=== BUG BOUNTY AGENT ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the programme's SCOPE and RULES were captured VERBATIM and dated",
  "the terms change, and a dated copy is your defence"),
 ("each asset was RESOLVED and confirmed to belong to the programme, not a third party",
  "a CNAME to a vendor's SaaS is usually the vendor's asset"),
 ("the behaviour was confirmed INTENDED-OR-NOT against the programme's own documentation",
  "a documented feature is not a finding"),
 ("a CONTROL exists: the same action without the flaw, or a benign input not triggering it",
  "the difference is the vulnerability"),
 ("the DUPLICATE CHECK ran all five checks and its results are recorded",
  "a duplicate is worth nothing and costs reputation"),
 ("the IMPACT is a step that was DEMONSTRATED, with the raw request/response as its evidence",
  "'an attacker could' without a demonstrated step is informative"),
 ("every AGENT-PRODUCED claim was re-derived by hand, and unverifiable ones were DELETED",
  "an agent asked to find vulns will produce plausible findings with no evidence"),
 ("all target-touching actions were performed by a HUMAN, and the record names which",
  "impact and authorisation cannot be delegated to an agent"),
 ("the SEVERITY is argued from the PROGRAMME'S rubric, with the applicable row quoted",
  "a generic CVSS vector reads as naive to a triager"),
 ("the report's steps are NUMBERED and reproducible by a triager with no context",
  "the triager's reproduction is the acceptance event"),
 ("the 'what was NOT tested' section is present",
  "honest limits make the rest credible"),
 ("no third-party or shared infrastructure was probed, including anything an agent inferred",
  "scope is decided by the programme, not by the agent"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE SUBMISSION SHAPE ===")
print("  scope    : the programme, the asset, and the evidence it is in scope")
print("  novelty  : the five duplicate checks and their results")
print("  control  : the same action without the flaw, or the benign input")
print("  impact   : the demonstrated step, with raw evidence")
print("  severity : the programme's own rubric row, and any factor you are unsure of")
print("  limits   : what was not tested, and every assumption")
PY
```

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - the submission's shape and its claim-to-evidence lint
- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) - the minimal reproduction a triager will re-run
- [recon-methodology](../recon-methodology/SKILL.md) - the surface inventory a bounty session starts from
- [attack-graphql](../attack-graphql/SKILL.md) - a high-yield bounty class the agent layer must not over-claim
- [attack-idor-automation](../attack-idor-automation/SKILL.md) - the automated candidate class and its false-positive rate
