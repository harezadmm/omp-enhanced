---
name: security-reporting-and-documentation
description: >-
  Producing the penetration test deliverable: audience-modelled findings, argued
  severity, evidence discipline, kill-chain narratives, testable remediation,
  and the verification and retest cycle. Use when writing, reviewing, or
  retesting any security report whose value depends on verified, actionable claims.
---

# SKILL: Security Reporting & Documentation

> **AI LOAD INSTRUCTION**: The report IS the engagement output — no finding exists until it is written so that someone else can reproduce it, understand its risk, and fix it. A brilliant engagement with an unverified, unexplained report is a failed engagement. **Every claim must trace to captured evidence, and every finding must be actionable by the person who has to fix it.**

## 0. RELATED ROUTING

- [c2-infrastructure-and-channel-design](../c2-infrastructure-and-channel-design/SKILL.md) — infrastructure to enumerate and confirm torn down
- [attack-execution-atomic-tests](../attack-execution-atomic-tests/SKILL.md) — validating coverage claims before they enter the report
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) — the network findings this report must render
- [reporting-and-verification](../../core-subjects/reporting-and-verification.md) — evidence-first doctrine and claim grading
- [standard-report-template](../../core-subjects/standard-report-template.md) — the structural template this skill fills with judgement

---

## 1. THE AUDIENCE MODEL

One finding, three renderings. The executive resources the fix, the responder triages it, the developer writes it.

| Audience | What they need | What to omit |
|---|---|---|
| **Executive reader** | business risk in plain language, scope, cost of inaction, next spend | exploit mechanics, payloads, tool flags, CVSS vectors |
| **Technical responder** | exact assets, exploitability conditions, detection and containment steps | strategic framing, fix-verification detail |
| **Developer / fixer** | precise location, reproduction, root cause, exact patch plus verification | risk narrative, severity justification, business impact |

**A finding that the fixer cannot act on is not a deliverable.** If the developer closes the report unable to name the file, the change, and the test proving it fixed, the finding failed no matter how accurate the analysis.

Write the developer rendering first, then derive the other two by summarisation — never the reverse. Detail compresses upward; executive prose does not expand downward into a patch.

---

## 2. FINDING ANATOMY

Nine fields per finding. Missing fields are the most common review rejection.

| Field | Contents |
|---|---|
| **Title** | vulnerability class + location, one line ("Stored XSS in ticket subject, admin view") |
| **Severity** | technical score AND business severity, both argued (see §3) |
| **Affected asset** | exact host/URL/version; "the app" is not an asset |
| **Evidence** | requests, responses, screenshots, timestamps (see §4) |
| **Reproduction** | numbered steps from a clean state, accounts and preconditions stated |
| **Impact** | what an attacker gains, demonstrated or honestly bounded |
| **Root cause** | the defect class and why it exists, not just where |
| **Remediation** | specific, testable, prioritised (see §6) |
| **References** | CVE/CWE/advisory where applicable |

**ROOT CAUSE and IMPACT are the two sections most often skipped and most often requested — because they convert a bug into a decision.** Impact tells the executive why to pay; root cause tells the developer what to change. Everything else supports those two judgements.

Spend root-cause effort on highs and criticals; for lows, a defect class plus a pointer suffices. Never spend zero — a finding with no stated cause invites the wrong patch.

---

## 3. SEVERITY MUST BE ARGUED, NOT ASSERTED

A severity label with no reasoning is a negotiation opener, and the client will negotiate it down. Argue it with two numbers.

| Number | Measures | Divergence example |
|---|---|---|
| **Technical (CVSS)** | exploitability and impact in a vacuum | CVSS 9.8 SQLi on an isolated lab database |
| **Business severity** | risk to THIS client: data, exposure, compliance, chaining | same SQLi is Critical on payments, Low on a disposable tenant |

**Technical CVSS and business severity are two different numbers that must both appear — conflating them hides real risk behind a defensible formula.** CVSS does not know which database holds cardholder data or which three mediums chain to domain admin. Publish the vector string, state business severity with a one-paragraph justification, and explain any divergence over one level explicitly. For chains (§5), severity belongs to the chain outcome with per-step scores in the sub-findings. Never inflate a low to force attention — one caught inflation discredits every critical in the report.

---

## 4. EVIDENCE DISCIPLINE

Capture evidence during the test, not after — memory is not evidence. Record the exact request and response, timestamps with timezone, accounts and privilege levels used, copy-pasteable commands with output, scope confirmation, and tool versions.

**Never include live credentials, customer PII, or data your test was not scoped to read.** Redaction rules are non-negotiable: rotate any credential appearing in evidence and confirm rotation; mask PII beyond the minimum proving impact (one record proves access, a thousand-row dump proves recklessness); on out-of-scope contact, stop, disclose to the engagement lead, delete the copy, and describe the boundary without reproducing data; crop and annotate screenshots since full desktops leak tokens and hostnames. If evidence cannot be shown within these rules, describe its existence and handling instead.

---

## 5. THE CHAIN PROBLEM

Three mediums — stored XSS on the admin panel, predictable session tokens, a missing authorisation check — read as three acceptable risks and combine into administrative takeover. Reported separately, the chain never appears.

Structure it as one narrative finding with sub-findings:

```
FINDING C-1 (High): Admin takeover via XSS → session control → export abuse
  C-1.1 (Medium): Stored XSS in ticket subject — initial foothold
  C-1.2 (Medium): Predictable session token after logout — session control
  C-1.3 (Medium): Missing authorisation on /admin/export — objective
  Narrative: XSS as admin, hold the session, exfiltrate. End-to-end reproduced.
```

Severity sits at the chain level; sub-findings keep per-step scores and remain individually fixable, since breaking any link kills the chain. State which link is cheapest to break for fastest risk reduction. **Attackers do not file findings one at a time, and a report that does understates every engagement.** If no chain was found, distinguish "no chaining attempted" from "attempted, none succeeded" — different claims, different evidence burdens.

---

## 6. REMEDIATION QUALITY

| Bad (unactionable) | Good (testable) |
|---|---|
| "Patch the server" | "Upgrade Apache 2.4.49 to ≥2.4.51; verify `/cgi-bin/.%2e/` returns 404" |
| "Validate input" | "Allowlist `order_id` (alphanumeric, ≤32) server-side at `orders.py:118`; `'` must return 400, not 500" |
| "Enable MFA" | "Require phishing-resistant MFA for admin before Q4; TOTP accepted for standard users" |

Every recommendation must be specific (named component, version, location), testable (include the verification proving the fix), and prioritised by risk reduction per effort — quick wins separated from structural fixes. When a fix is infeasible (legacy dependency, vendor appliance), give compensating controls instead — WAF rule, segmentation, monitoring signature, review date — and label it containment, not cure. **A remediation without a verification step is a wish.**

---

## 7. THE VERIFICATION AND RETEST CYCLE

Findings change state only through evidence.

| Status | Requires |
|---|---|
| **Open** | nothing further; the default |
| **Closed** | re-executed reproduction fails; fresh evidence captured |
| **Partially closed** | original PoC fails but a variant succeeds — new evidence attached |
| **Disputed** | counter-evidence or a written accepted-risk statement |
| **Accepted risk** | named owner, expiry date, recorded compensating controls |

A retest proves the exact reproduction no longer succeeds in the stated environment (build hash, date, staging vs production) — not that the defect class is gone elsewhere, so sample siblings and state the reach. A variant bypass reopens the finding as a partially-closed continuation, preserving history. **An unverified closure is a liability: once a critical is marked closed, the client stops defending against it.** Never close on a patch note or developer assertion — close on re-executed evidence dated after the fix.

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| scope statement with dates, targets, exclusions | bounds what the report's claims cover |
| every finding mapped to captured evidence | a claim without an artefact is opinion |
| CVSS vector plus argued business severity per finding | lets any reviewer recompute the rating |
| reproduction steps executable from a clean state | the client must confirm and later retest |
| root cause and impact on every high/critical | the sections driving resourcing and patching |
| chains executed end-to-end, not assembled from parts | unexecuted chains are speculation with a severity |
| redaction confirmation: no live credentials, excess PII, or out-of-scope data | leaked data in the report is itself an incident |
| dated retest evidence behind every status change | unverified closure transfers risk silently |
| infrastructure inventory with teardown confirmation | live test infrastructure after delivery is an exposure |
| reviewer sign-off on critical findings | single-reviewer criticals carry uncaught error |

**A report failing this table goes back for rework before delivery, regardless of schedule pressure.** A slipped deadline is recoverable; a discredited engagement is not.

---

## 9. REMEDIATION REFERENCE

1. **Report review process** — findings checked against evidence, severities against argument, reproductions for completeness, before delivery. Schedule it as delivery work, not overhead.
2. **The two-reviewer rule for critical findings** — one reviewer re-executes the reproduction from the written steps alone, another challenges the severity argument. A critical nobody else could reproduce is a draft.
3. **Retention and handling of sensitive evidence** — encrypted storage, access limited to the team, destruction on the contractual date with destruction recorded. Custody outlives the engagement if you keep copies.
4. **Post-engagement teardown confirmation** — enumerate every redirector, domain, implant, test account, and persistence mechanism (see [c2-infrastructure-and-channel-design](../c2-infrastructure-and-channel-design/SKILL.md)); confirm each decommissioned with dates for client verification.
5. **Accepted-risk discipline** — every deferral gets a named owner, expiry date, and compensating controls. Without an owner it is an orphaned vulnerability with paperwork.
6. **Lessons-learned capture** — feed review catches (disputed severities, missing evidence, late chains) back into scoping and testing checklists for the next engagement.

---

## 10. CONFIRMING THE FINDING

This domain's subject is **the report as an artefact**, so confirming means: does the document itself
survive a hostile reader? This table is the gate the report passes before it is delivered.

| Step | Question | What it proves |
|---|---|---|
| 1 | Can a reader **reproduce the finding from the document alone**? | the report is the only surviving evidence |
| 2 | Is the **severity argued from a stated impact**, not asserted? | section 3's rule, applied |
| 3 | Does every **evidence item** have its provenance and its integrity? | a screenshot is not provenance |
| 4 | Is the **chain** (section 5) stated as links, each with its own evidence? | a chain is only as strong as its weakest link |
| 5 | Does the **remediation** name a verifiable end state? | section 6's rule, applied |
| 6 | Is there a **retest** plan with a defined pass condition? | section 7's rule, applied |
| 7 | Is the **audience** (section 1) satisfied: does each reader get what they need? | a report for everyone serves no one |

**A reader can reproduce the finding from the document alone, and the severity is argued from a stated
impact.** The report is the only part of the engagement that survives, and it is judged on its own.

---

## 11. EXECUTION PRIMITIVES

The report is a document, so the execution is a **lint discipline**: mechanical checks that a claim is
supported, a link is complete, and a remediation is verifiable. Every check below is a procedure.

### 10.1 The claim-to-evidence lint

```bash
# A CLAIM WITHOUT ITS EVIDENCE IS NARRATION. LINT THE DOCUMENT FOR THE PAIRS.
cat > /tmp/report_lint.py <<'PY'
import re, sys
from pathlib import Path
doc = Path(sys.argv[1]).read_text(encoding="utf-8")
CHECKS = [
 ("CLAIM WITHOUT EVIDENCE",
  r'(?i)\b(is vulnerable to|can be exploited|allows an attacker|results in (rce|code execution|data loss))\b',
  "each such sentence needs an adjacent reference: a request/response, a file with its hash, or a log line"),
 ("ASSERTED SEVERITY",
  r'(?i)\b(critical|high|severe) (severity|risk|vulnerability)\b',
  "severity must cite the impact it derives from, not the label"),
 ("UNSOURCED EVIDENCE",
  r'(?i)(attached screenshot|see the screenshot|as shown in the image)',
  "a screenshot needs a caption naming the HOST, the TIME, and WHAT it demonstrates"),
 ("UNVERIFIABLE REMEDIATION",
  r'(?i)\b(be more secure|improve security|harden the|follow best practices|ensure that)\b',
  "the fix must name a CONFIGURATION or a CODE CHANGE whose end state is checkable"),
 ("MISSING CHAIN LINK",
  r'(?i)\b(then|subsequently|after which|this allowed)\b',
  "a chain step needs its OWN evidence, because the chain is only as strong as its weakest link"),
 ("HEDGED IMPACT",
  r'(?i)\b(could potentially|may possibly|might allow an attacker|it is possible that)\b',
  "state what was DEMONSTRATED and name the step beyond it as a claim, separately"),
 ("UNSCOPED FINDING",
  r'(?i)\b(affects all (users|hosts|servers)|every instance|the entire)\b',
  "a scope claim needs the population that was TESTED and the part that was not"),
]
hits = 0
for name, pat, why in CHECKS:
    for m in re.finditer(pat, doc):
        hits += 1
        line = doc[:m.start()].count("\n") + 1
        print(f"  [{name}] line {line}: {m.group(0)[:70]}")
        print(f"      -> {why}")
print(f"\n  TOTAL FLAGS: {hits}")
print("  EACH FLAG IS A QUESTION, NOT A VERDICT: 'is this claim backed in the document?'")
print("  A flagged sentence WITH an adjacent reference is FINE - the lint finds the candidates.")
PY
python3 /tmp/report_lint.py "$1" 2>/dev/null || echo "  usage: python3 /tmp/report_lint.py <report.md>"
echo
echo "=== THE EVIDENCE ITEM'S MINIMUM SHAPE ==="
cat <<'EVID'
  EACH EVIDENCE ITEM MUST NAME, IN THE DOCUMENT:
    the HOST / the ASSET   : which system, identified unambiguously
    the TIME               : when, with the timezone and the clock's source (see traffic-analysis-pcap)
    the ACTION             : what was done, reproducibly
    the RESULT             : what came back, verbatim or referenced
    the INTEGRITY          : a hash for a file, the tool and version for a reading
  AND THE ANONYMISATION CAVEAT: if the report is redacted, the REDACTION must not remove the
  element a reader needs to reproduce the finding. A report redacted below reproducibility is a
  summary, and it must be labelled as one.
EVID
```

**Each flag is a question, not a verdict** — a flagged sentence with an adjacent reference is fine. And a
report redacted below reproducibility is a summary, and must be labelled as one.

### 10.2 The chain, and the remediation's end state

```bash
echo "=== THE CHAIN (section 5): EACH LINK NEEDS ITS OWN EVIDENCE ==="
cat > /tmp/chain.md <<'MD'
## CHAIN TABLE - the report's spine
| # | STEP | PRECONDITION | EVIDENCE FOR THIS STEP | WHAT IT ENABLES NEXT |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

## RULES
1. EVERY STEP HAS ITS OWN EVIDENCE. A chain written as prose with one screenshot at the end has
   one link's evidence and several links' claims.
2. EVERY STEP'S PRECONDITION IS NAMED. If step 3 needs step 2's result, SAY SO - because a fix at
   step 2 breaks the chain, and that is the remediation's justification.
3. THE CHAIN'S WEAKEST STEP IS THE FINDING'S REAL SEVERITY. Ask: which step, if it failed, would
   collapse the whole chain? THAT step determines the argued severity, not the last one.
4. 'WHAT IT ENABLES' IS NOT 'WHAT I DID'. State the demonstrated end, then name the further steps
   as CLAIMS if you did not perform them.
MD
cat /tmp/chain.md
echo
echo "=== THE REMEDIATION'S END STATE (section 6), which must be CHECKABLE ==="
cat <<'REMED'
  EACH REMEDIATION NAMES A VERIFIABLE END STATE. THE STRUCTURE:
    the CHANGE     : the configuration or the code, named precisely (the file, the setting, the value)
    the END STATE  : what is TRUE once the change is made, expressed as an OBSERVABLE
    the VERIFY     : the command or the request that demonstrates the end state
    the ALTERNATIVE: if the primary fix is not feasible, the compensating control, AND what it does
                     NOT cover

  THE TEST OF A GOOD REMEDIATION: A SECOND ENGINEER CAN APPLY IT AND DETERMINE, WITHOUT ASKING YOU,
  WHETHER IT WORKED. 'Harden the configuration' fails this test. 'Set X to Y in file Z; the end
  state is that request R returns 403; the compensating control (the WAF rule) does not cover the
  internal path' passes it.

  AND THE SCOPE OF THE FIX: does it fix the INSTANCE, the CLASS, or neither? Say which. A fix for
  one endpoint that leaves the shared library vulnerable fixes an instance, and the report must say so.
REMED
```

**The chain's weakest step determines the real severity** — not the last one — and each remediation must be
checkable by a second engineer without asking the author.

### 10.3 The retest, and the end-to-end harness

```bash
echo "=== THE RETEST PLAN (section 7), with its PASS CONDITION ==="
python3 - <<'PY'
print("  each finding needs a retest entry with:")
for s in ["the EXACT procedure to re-run (the minimal reproduction, from a clean state)",
          "the PASS condition: the OBSERVABLE that proves the fix (not 'the issue is resolved')",
          "the FAIL condition, and what a partial fix looks like",
          "the SCOPE of the retest: which instances and which variants were re-tested",
          "the DATE and the version fixed, so the result is bounded to that version"]:
    print("    [ ] " + s)
print()
print("  AND THE PARTIAL-FIX CATEGORY, WHICH REPORTS ALMOST ALWAYS OMIT:")
print("    FIXED           : the reproduction no longer produces the effect")
print("    PARTIALLY FIXED : the effect is reduced or requires a new precondition - SAY WHICH")
print("    NOT FIXED       : the reproduction still produces the effect")
print("    NOT RETESTED    : no retest was performed - and SAY THAT, because silence implies success")
PY
echo
echo "=== THE AUDIENCE DELIVERY CHECK (section 1) ==="
python3 - <<'PY'
A = [("the executive", "impact, the risk's shape, and the decision they must make", "no exploit detail, no tool names"),
     ("the engineer",   "the reproduction, the evidence, and the fix's end state",     "no risk framing they cannot act on"),
     ("the auditor",    "the scope, the coverage, the method, and the exclusions",     "no conclusions without the coverage statement"),
     ("the vendor",     "the minimal reproduction and the boundary",                   "no impact speculation beyond the demonstration")]
print("%-18s %-58s %s" % ("audience","what they must be able to do after reading","what to leave out"))
for a,b,c in A: print("%-18s %-58s %s" % (a,b,c))
print()
print("  THE TEST: for each audience, name the ONE QUESTION they will ask first, and check the report")
print("  answers it in the first page. THAT is what 'written for the audience' means, mechanically.")
PY
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== REPORTING ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("a reader can REPRODUCE the finding from the document alone, with no other context",
  "the report is the only part of the engagement that survives"),
 ("the report_lint was run, and every flag was answered or the claim amended",
  "claims without adjacent evidence are narration"),
 ("each EVIDENCE item names the host, the time (with its source), the action, the result, and its integrity",
  "a screenshot without a caption proves nothing about a host"),
 ("redactions do not remove the element a reader needs to reproduce the finding",
  "a report redacted below reproducibility is a summary and must be labelled one"),
 ("SEVERITY is argued from a stated impact, with the reasoning in the document",
  "an asserted label is not a finding"),
 ("the CHAIN is a table with each step's OWN evidence and its precondition",
  "a chain's weakest step is its real severity, not its last step"),
 ("nothing beyond the demonstrated step is stated as a result",
  "further steps are claims, and are labelled as such"),
 ("each REMEDIATION names a checkable end state and a verifier command",
  "a second engineer must be able to determine success without asking the author"),
 ("the fix's SCOPE is stated: instance, class, or neither",
  "a fix for one endpoint that leaves the shared library vulnerable is an instance fix"),
 ("each finding has a RETEST entry with a PASS and a FAIL condition",
  "'the issue is resolved' is not a pass condition"),
 ("the retest result uses FIXED / PARTIALLY FIXED / NOT FIXED / NOT RETESTED explicitly",
  "silence implies success, and that is a false statement"),
 ("the audience split delivers what each reader needs, and omits what they do not",
  "a report for everyone serves no one"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  summary    : the impact, for the decision-maker, in their language")
print("  findings   : severity argued, evidence referenced, scope stated")
print("  chain      : the table, each step with its own evidence and its weakest link identified")
print("  remediation: the change, the end state, the verifier, and the compensating control's gaps")
print("  retest     : the pass condition, the result category, and the version bound")
print("  coverage   : the scope statement, the exclusions, and the method's limits")
PY
```

**Silence about a retest implies success, and that is a false statement** — the result categories must be
explicit, including `NOT RETESTED`. And the chain's weakest link is the argued severity.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) - the research this domain writes up
- [recon-methodology](../recon-methodology/SKILL.md) - the coverage claim a report must defend
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - the provenance discipline the same evidence shares
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) - the wire-level evidence a finding cites
- [memory-forensics-volatility](../memory-forensics-volatility/SKILL.md) - the endpoint evidence a chain may include
