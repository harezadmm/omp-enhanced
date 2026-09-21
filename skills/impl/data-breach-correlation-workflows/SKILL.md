---
name: data-breach-correlation-workflows
description: >-
  Breach data correlation for authorisation-controlled testing. Use when assessing whether
  employee credentials are exposed through historical breaches, or building a credential strategy
  from breach intelligence. Covers the provenance hierarchy, validity assessment, and the legal
  constraints on using third-party breach data.
---

# SKILL: Data Breach Correlation Workflows

> **AI LOAD INSTRUCTION**: Breach data is the most legally fraught input in an assessment. Its
> value is **pattern intelligence**, not credential material — the overwhelming majority of
> historical breach credentials no longer work anywhere. This skill covers the provenance
> hierarchy, how to judge validity, and the constraints that keep the activity lawful. Read §1
> before querying anything.

## 0. RELATED ROUTING

- [credential-list-engineering](../credential-list-engineering/SKILL.md) — where the output goes
- [osint-target-profiling](../osint-target-profiling/SKILL.md) — identity harvesting
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) — attacking the live estate
- [grabber-auto-extraction-engine](../grabber-auto-extraction-engine/SKILL.md) — extracting secrets from what you find
- [breach-correlation-workflows](../../core-subjects/breach-correlation-workflows.md) — doctrine

---

## 1. THE LEGAL FRAME — READ FIRST

Breach data is **third-party personal data**. Possessing and querying it is regulated activity
in most jurisdictions, independent of who you are testing.

| Constraint | Practice |
|---|---|
| **Authorization must name breach-data use** | a generic pentest authorisation does not cover this |
| Query only **corporate identifiers** | the client's domains and their employees' work addresses — never personal addresses |
| **Never download bulk corpora** | query an API and record the result; do not possess the dataset |
| Never store the returned credentials | record *that* a match exists, and which breach, not the value |
| Never use the credentials **outside the scope** | a match against the target is in scope; the same credential against the target's SaaS is not, unless named |
| Document the source for every query | provenance is the defence if the activity is questioned |
| Prefer licensed/consented services | a service with data-subject consent is legally cleaner than an anonymous dump |

**The practical rule: query, do not collect.** A correlation API that returns "this address
appeared in breach X" gives you the intelligence without the liability. Downloading a
multi-gigabyte dump gives you the liability without much more intelligence.

---

## 2. THE PROVENANCE HIERARCHY

Not all breach data is equal. Rank sources before trusting any of them.

| Tier | Source | Validity | Use |
|---|---|---|---|
| **1** | Credential-stealer logs (recent, from the target's own users) | **highest** — current session credentials | directly actionable; the single most valuable source |
| **2** | Recent, verified, well-processed breach corpora | high — real, recent, clean | strong candidate list |
| **3** | Older major breaches with reliably parsed structure | medium — real but stale | pattern intelligence: password style, email format |
| **4** | Aggregated "combo lists" of unknown provenance | **low** | volume only — high false-positive rate |
| **5** | Scraped/derived datasets of unverifiable origin | **worthless and risky** | do not use |

**Tier 1 changes the assessment.** A credential-stealer log for the target's domain contains
credentials for systems that were *live at capture time* — often including SSO sessions,
which makes password rotation insufficient. If tier 1 material exists for the target, it
outranks everything else in this document.

**Tier 4 and 5 are traps.** Combo lists are full of synthetic entries, already-rotated
credentials, and data from unrelated organisations. Their volume creates the illusion of value
while producing mostly failed authentication attempts and noise.

---

## 3. THE VALIDITY PROBLEM

The central question for any match: **is this credential still valid?**

| Factor | Effect on validity |
|---|---|
| Age of the breach | the dominant factor — most credentials die within months |
| Password rotation policy | a policy with history enforcement invalidates old material fast |
| Whether the breach was public | public breaches trigger mass resets |
| Account status | departed employees' accounts may be disabled or reassigned |
| Domain type | corporate SSO credentials are reset more aggressively than a forum login |
| Reuse | **independent of validity** — an old credential may still be valid on an unrelated site |

**Reuse is the finding, not the credential.** A 2016 credential is useless against the target's
SSO. The same password, reused on a personal service that the employee then used for work, may
not be. That is a finding about password reuse *behaviour* and belongs in the report as a
policy finding.

**Test validity with the minimum possible attempt.** Query the authentication endpoint once for
a confirmed identity, at a rate the lockout policy allows, with authorisation. Do not spray a
hundred candidates and then discover you locked out the estate.

---

## 4. THE WORKFLOW

```
1. Scope check        → is breach-data use authorised, and for which identifiers?
2. Identifier set     → corporate domains and employee work addresses only
3. Query (tiered)     → stealer logs → recent corpora → historical corpora
4. Record matches     → identity, source, date — NOT the credential value
5. Rank for validity  → age, domain, rotation policy, account status
6. Derive patterns    → email format, password structure, common themes
7. Build the list     → hand to credential-list-engineering
8. Report             → exposure findings + reuse-policy findings, separately
```

**Step 6 is the durable output.** The password patterns revealed by breach data — corporate
themes, seasonal rotation, complexity requirements visible in the structure — generate better
candidates than the leaked passwords themselves. The pattern survives rotation; the password
does not.

---

## 5. WHAT YOU REPORT

| Finding | Severity signal |
|---|---|
| **Active credentials exposed (tier 1)** | critical — includes session material; rotation alone may not suffice |
| Recent breach exposure | high — indicates a compromise or a reuse pattern |
| Historical exposure | medium — largely a hygiene and policy finding |
| **Email format confirmed by breach data** | low alone, but it enables the credential strategy |
| Password-reuse pattern | medium — a policy finding, needs MFA as the mitigating control |
| No matches found | **a positive finding — state it** |

**"No matches" is a real result and should be reported.** Absence of exposure is what the client
paid to learn. Omitting it makes the assessment look incomplete and deprives them of a
demonstrable control.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the authorisation clause covering breach-data use | the activity is unlawful without it |
| the identifier set queried | proves the query stayed inside scope |
| the source tier and name for each match | provenance is the defence |
| **that a match exists, not the credential** | never place a live credential in a report |
| the breach date, for validity reasoning | an undated match cannot be assessed |
| whether the credential was tested, and the outcome | distinguishes exposure from access |
| the derived patterns | the actionable output |
| **the disposal point for any data held** | a date, in writing |

---

## 7. REMEDIATION REFERENCE

1. **MFA is the only control that makes breach data largely irrelevant** — a leaked password without the second factor fails. This is the single highest-value recommendation.
2. **Breached-password screening at set-time** — check new passwords against known-breached lists; cheap, effective, and addresses reuse at the source.
3. **Monitor stealer logs for your domain** — tier 1 material is the dangerous class; detecting its appearance is a real-time control, not an annual review exercise.
4. **Session revocation on credential change** — rotation that leaves valid sessions intact does not remediate a stealer-log exposure.
5. **Password managers to make reuse structurally hard** — reuse policy fails on human behaviour; tooling does not.
6. **Do not rely on rotation alone** — a rotation policy with a long period does not limit the window that matters, because the credential is used immediately after capture.
7. **Report the pattern, not just the exposure** — the client needs to know *why* their users' passwords appear in breaches (reuse, theme, weak policy), not only that they do.

---

## 8. CONFIRMING THE FINDING

Correlation's failure mode is **a matching value treated as a match of identity**. A record and an
observation agreeing on a string is a candidate; a correlation is an argument that the same entity produced
both, and this table is that argument's structure.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **legal frame** (section 1) established: whose data, under what authority? | the prerequisite, not a formality |
| 2 | Is the **provenance** of every source recorded with its collection method? | section 2's hierarchy |
| 3 | Is the match **corroborated by more than one field**, or by a field unique to the entity? | a shared email is not a shared person |
| 4 | Were **collisions excluded**: shared names, shared addresses, shared identifiers? | the commonest false correlation |
| 5 | Is the **temporal** claim anchored (section 3)? | correlation across clocks needs an anchor |
| 6 | Is the **negative** recorded: which candidate entities were eliminated, and how? | elimination is half the work |
| 7 | Does the claim name **the confidence and its basis**, not a bare assertion? | a correlation without its basis is an accusation |

**A legally framed dataset, a multi-field corroborated match, excluded collisions, and a stated confidence.**
A matching string is a candidate; a correlation is an argument that one entity produced both observations.

---

## 9. EXECUTION PRIMITIVES

This domain executes as a **collision-exclusion and provenance discipline**. Every correlation below reduces
to: the sources' provenance, the fields used, the collisions excluded, and the stated confidence.

### 8.1 Provenance, and the legal frame as a gate

```bash
# THE LEGAL FRAME IS STEP ZERO. Without it, nothing below may be performed at all.
cat <<'LEGAL'
  BEFORE CORRELATING ANYTHING, ESTABLISH AND RECORD:
    WHOSE data is this    : the data subjects, and the categories (identifiers, credentials, content)
    UNDER WHAT AUTHORITY  : a contract, a legal request, a regulatory obligation, an internal policy -
                            and the DOCUMENT that grants it
    THE PURPOSE LIMIT     : correlation is often PERMITTED for one purpose and PROHIBITED for another.
                            THE PURPOSE MUST BE WRITTEN DOWN BEFORE THE ANALYSIS, because a purpose
                            chosen after the fact is not a purpose limit.
    THE RETENTION LIMIT   : how long the correlated result may be kept, and who must delete it
    WHO MAY SEE IT        : the audience, and the handling caveat on every output
  IF ANY OF THESE IS ABSENT, THE CORRECT ACTION IS TO STOP AND OBTAIN IT.
  AND THE ANONYMISATION LINE: a dataset described as 'anonymised' may be RE-IDENTIFIABLE by
  correlation itself - which is exactly what this domain does. THAT is a legal fact, and it belongs
  in the record: 'the sources are individually anonymised, and the correlation re-identifies them.'
LEGAL
echo
echo "=== THE PROVENANCE HIERARCHY (section 2), applied per source ==="
python3 - <<'PY'
P = [("the source's OWN record (a provider's log, a platform's export)", "T1", "authoritative for its own platform"),
     ("the data subject's own statement",                                "T1/T2", "authoritative for THEIR facts; not for others'"),
     ("a regulator's or a court's record",                               "T1", "authoritative, and slow"),
     ("a vendor's aggregated dataset",                                   "T2", "method unknown; treat as a lead"),
     ("a scraped or repackaged dataset",                                 "T3", "provenance unknown; CORROBORATE before use"),
     ("an inference from another source in this very analysis",          "T4", "NEVER a source for its own corroboration")]
print("%-62s %-6s %s" % ("source type","tier","what it is authoritative for"))
for a,b,c in P: print("%-62s %-6s %s" % (a,b,c))
print()
print("  THE RULE THAT MATTERS: TIER 4 IS NEVER USED TO CORROBORATE A CLAIM DERIVED FROM TIER 4.")
print("  A correlation that cites its own inference as a second source is CIRCULAR, and it is the")
print("  commonest structural defect in this domain's reports.")
print("  AND: record each source's COLLECTION DATE and its METHOD. A dataset's date bounds every")
print("  temporal claim derived from it.")
PY
```

**A correlation that cites its own inference as a second source is circular** — tier 4 is never used to
corroborate a claim derived from tier 4. And the purpose limit must be written down before the analysis.

### 8.2 The match: fields, collisions, and elimination

```bash
echo "=== THE MATCH STRENGTH TABLE: WHICH FIELDS CORROBORATE AND WHICH ARE CANDIDATES ==="
python3 - <<'PY'
F = [("a unique account identifier on the SAME platform", "STRONG",   "still shared: a family or a business account"),
     ("a credential (a password hash, a reused password)",  "STRONG",   "shared credentials exist, and a reused password links ACCOUNTS, not necessarily PEOPLE"),
     ("a device identifier / fingerprint",                  "STRONG",   "fingerprints collide; a shared device is common"),
     ("a verified phone number",                            "MODERATE", "ports, disposables, and business numbers"),
     ("a verified email address",                           "MODERATE", "shared inboxes, aliases, forwarding"),
     ("a full name plus a locality",                        "WEAK",     "the canonical collision"),
     ("a username string",                                  "WEAK",     "reused across unrelated people"),
     ("an IP address",                                      "WEAK",     "NAT, CGNAT, a VPN, a corporate egress, a MOBILE carrier - MANY people share one"),
     ("a writing style / behavioural pattern",              "WEAK-ONLY", "NEVER sufficient alone; may SUPPORT other evidence"),
     ("a photo or a biometric",                             "STRONG",   "needs a lawful basis and a qualified examiner")]
print("%-46s %-10s %s" % ("field","strength","the collision that must be excluded"))
for a,b,c in F: print("%-46s %-10s %s" % (a,b,c))
print()
print("  THE CORRELATION RULE: A CORRELATION STANDS ON ONE STRONG FIELD OR TWO INDEPENDENT MODERATE")
print("  FIELDS. ANY NUMBER OF WEAK FIELDS DO NOT ADD UP TO A STRONG ONE - 'the name matches and the")
print("  username matches and the IP matches' is still THREE WEAK COINCIDENCES that a shared household")
print("  or a shared carrier NAT explains.")
print("  THE ANTI-PATTERN: 'the IP matches, therefore the same person' is THE canonical false")
print("  correlation in breach work, and CGNAT makes it wrong far more often than it is right.")
PY
echo
echo "=== THE ELIMINATION RECORD, which is half the work and almost always omitted ==="
cat > /tmp/elimination.md <<'MD'
## ELIMINATION TABLE - the negative side of every correlation
| CANDIDATE ENTITY | WHY IT WAS CONSIDERED | THE TEST APPLIED | ELIMINATED? | BASIS |
|---|---|---|---|---|
| | | | | |

## RULES
1. EVERY CANDIDATE CONSIDERED IS LISTED, INCLUDING THE ELIMINATED ONES. A report that lists only
   the surviving match has not shown that the others were considered.
2. EACH ELIMINATION NAMES ITS TEST: a field that did not match, a timeframe that did not align, a
   source that contradicted. 'It seemed unlikely' is not an elimination.
3. THE COLLISION CLASSES MUST EACH BE ADDRESSED: a shared name, a shared device, a shared
   address, a shared credential, and a shared ACCOUNT (a family or a business account).
4. IF A COLLISION CLASS CANNOT BE EXCLUDED, THE CORRELATION'S CONFIDENCE DROPS, AND THE REPORT SAYS
   SO EXPLICITLY rather than omitting the class.
MD
cat /tmp/elimination.md
echo
echo "=== the temporal claim, anchored (section 3) ==="
cat <<'TEMP'
  A TEMPORAL CORRELATION ACROSS SOURCES NEEDS AN ANCHOR, EXACTLY AS IN PACKET ANALYSIS:
    the CLOCKS differ between a provider's log, a device's own timestamps, and a platform's export
    the RESOLUTIONS differ (a provider may record to the hour; a device to the millisecond)
    the TIMEZONES differ, and a 'date only' record can be off by a day at the boundary
  THE PROCEDURE:
    1. find an event present in BOTH sources (the anchor)
    2. compute the OFFSET from the anchor
    3. apply the offset, and record its magnitude - a large offset is itself worth reporting
    4. if there is NO anchor, THE ORDERING IS A HYPOTHESIS, and the report must say so
  AND: a correlation that requires two events to be SIMULTANEOUS across unanchored clocks with
  second-level resolution is NOT SUPPORTED by that evidence. State the required precision and the
  available precision side by side.
TEMP
```

**Any number of weak fields does not add up to a strong one**, and "the IP matches, therefore the same
person" is the canonical false correlation that CGNAT makes wrong far more often than right.

### 8.3 Confidence, and the end-to-end harness

```bash
echo "=== THE CONFIDENCE SCALE, with its basis stated in every case ==="
python3 - <<'PY'
C = [("ESTABLISHED", "one strong field, or two independent moderate fields, with all collision classes excluded",
      "may be stated as a finding"),
     ("PROBABLE",    "one strong field with an unexcluded collision, OR two moderate fields with one excluded",
      "stated as a probable correlation, with the gap named"),
     ("POSSIBLE",    "one moderate field, or several weak fields that a specific shared context explains",
      "stated as a LEAD, never as a finding"),
     ("ELIMINATED",  "a test that contradicts the correlation", "recorded as an elimination, with the test"),
     ("UNDETERMINED","the evidence does not distinguish",       "stated as such - NOT as a weak correlation")]
print("%-13s %-96s %s" % ("level","basis","how it is reported"))
for a,b,c in C: print("%-13s %-96s %s" % (a,b,c))
print()
print("  THE RULE: THE BASIS IS PART OF THE CLAIM. 'Established' without the fields and the excluded")
print("  collisions is an assertion, and in this domain an assertion is a defamatory risk.")
print("  AND: THE LEVEL APPLIES TO THE SPECIFIC CORRELATION, NOT TO THE ENGAGEMENT. Different")
print("  correlations in one report will sit at different levels, and that is expected.")
PY
echo
echo "=== THE RE-IDENTIFICATION WARNING (section 1), stated in the output ==="
cat <<'REDID'
  A CORRELATION'S OUTPUT IS ITSELF SENSITIVE DATA, and often MORE sensitive than any single input:
    it LINKS the sources, so it is a new dataset with a new, higher sensitivity
    an 'anonymised' input may become IDENTIFIABLE through the correlation
    the output's RETENTION and AUDIENCE must follow the strictest input's rules, not the loosest
  THEREFORE EVERY OUTPUT CARRIES:
    the purpose it was produced for, the authority, the retention limit, and the handling caveat
  AND THE MINIMISATION RULE: the output contains ONLY the fields the purpose requires. A
  correlation table that carries every field from every source is itself a disclosure, and the
  least-privilege discipline applies to the ANALYST'S OWN ARTEFACTS as much as to the subjects'.
REDID
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== DATA BREACH CORRELATION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the LEGAL FRAME is recorded: whose data, under what authority, the purpose, the retention, the audience",
  "the purpose must predate the analysis, and an absent frame means STOP"),
 ("the re-identification property of the correlation itself is recorded as a legal fact",
  "an anonymously-sourced correlation may re-identify, and that is a fact about the output"),
 ("every source's TIER, collection METHOD, and collection DATE are recorded",
  "provenance bounds every claim, and the date bounds every temporal one"),
 ("no claim is corroborated by an inference derived from the same analysis",
  "tier 4 as a second source is circular, the commonest structural defect here"),
 ("the match's FIELDS are listed with their STRENGTH, and the rule is satisfied",
  "one strong or two independent moderate; any number of weak fields does not add up"),
 ("every COLLISION CLASS is addressed: shared name, device, address, credential, and ACCOUNT",
  "a shared family or business account is the class most often missed"),
 ("an ELIMINATION TABLE lists the candidates considered AND eliminated, each with its test",
  "a report listing only the survivor has not shown the others were considered"),
 ("any collision class that could NOT be excluded is stated, with the confidence reduced",
  "omitting the class is what makes a report misleading"),
 ("temporal claims are ANCHORED, with the offset computed and its magnitude recorded",
  "unanchored cross-source ordering is a hypothesis"),
 ("the required precision and the available precision are stated side by side",
  "simultaneity cannot be supported beyond the coarsest resolution present"),
 ("the CORRELATION LEVEL is one of ESTABLISHED / PROBABLE / POSSIBLE / UNDETERMINED, with its basis",
  "an assertion in this domain is a defamatory risk"),
 ("the output carries its purpose, authority, retention limit, and handling caveat",
  "the output is a new dataset with its own, higher sensitivity"),
 ("the output contains ONLY the fields the purpose requires",
  "least privilege applies to the analyst's own artefacts"),
]
for n, how in CHECKS: print("  [ ] %-76s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  frame      : authority, purpose, retention, audience, and the re-identification note")
print("  sources    : each with its tier, method, and date")
print("  match      : the fields, their strength, and the rule satisfied")
print("  collisions : the classes addressed, and any that could not be excluded")
print("  elimination: the candidates and the tests")
print("  temporal   : the anchor, the offset, and the precision comparison")
print("  level      : the correlation level and its basis; the output's handling caveat")
PY
```

---

## 10. RELATED SIBLINGS - LOAD TOGETHER

- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) - the wire-level provenance a correlation may draw on
- [memory-forensics-volatility](../memory-forensics-volatility/SKILL.md) - the endpoint evidence and its non-atomic caveat
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a confidence level is written
- [recon-methodology](../recon-methodology/SKILL.md) - the passive/active line the legal frame enforces
- [steganography-techniques](../steganography-techniques/SKILL.md) - the carrier provenance the same source discipline covers
