---
name: vuln-research-methodology
description: >-
  The vulnerability research discipline. Use during ARM or STRIKE when turning a surface
  inventory into a proven finding: choosing a target, reading code or spec to form a hypothesis,
  the differential and negative-control mindset, building a minimal reproduction, testing
  boundary and type assumptions, separating bug from intended behaviour, responsible disclosure,
  and writing the research note.
---

# SKILL: Vulnerability Research Methodology

> **AI LOAD INSTRUCTION**: Research is not hunting. Hunting is opening a target and trying things;
> research is forming a falsifiable claim about a system and then trying to break that claim. The
> difference matters because most "findings" that die in triage died at hypothesis time — the
> researcher never stated what they expected, so they never noticed they had only observed
> something odd. **Every technique below exists to force a belief to become a prediction, and a
> prediction to become a test.** If you cannot say what result would disprove your hypothesis, you
> are not researching yet.

## 1. CHOOSING A TARGET FROM THE SURFACE INVENTORY

Do not pick a target by feel. Pick from the inventory that [recon-methodology](../recon-methodology/SKILL.md)
produced, scored on research yield per hour rather than on coolness.

| Signal | Why it raises yield |
|---|---|
| **Recently changed** | new code has no hardened-email-history; migrations and rewrites mint new bugs |
| **Not covered by others** | if the surface inventory says "nobody tests this", the duplicate rate is low |
| **Understandable in one sitting** | a component you can read end-to-end beats a platform you can only sample |
| **Reachable control you can see** | a login, a parser, a state machine — something with inputs you control |
| **Custom, not framework** | off-the-shelf libraries are read by thousands; bespoke glue is not |
| **High privilege ceiling behind it** | a bug here reaches data or rights that matter, so it is worth reporting |

**Weight the specification over the implementation.** A spec states what the system *promises*;
the code shows what it *does*. The gap between those two sentences is where findings live, and the
spec is the cheaper document to read first.

Before committing hours, answer three questions in writing: what component, what trust boundary
does it sit on, and what would a successful finding look like? If the third answer is vague, you
have chosen a topic, not a target.

---

## 2. READING THE CODE OR SPEC TO FORM A HYPOTHESIS

A hypothesis is a sentence with a subject, a mechanism, and a predicted observable. Not "the
import path looks unsafe" — rather: *"because the importer resolves the archive path without
normalising it and calls the extractor with the resolved value, a `../` in the entry name should
write outside the extraction root, observable as a file appearing in the parent directory."*

Work in this order. Each step narrows what you have to read next, which is the entire point.

1. **Find the entry points.** Where does untrusted input first arrive? Handlers, parsers, deserialisers, template loaders, message consumers, CLI flags, config files.
2. **Follow the taint by hand, not by tooling.** For the one path you care about, read every function between input and sink. Tooling tells you where sinks are; only reading tells you whether the path is reachable *with your input under your privileges*.
3. **Stop at the first check and interrogate it.** Every validation is a developer's claim about what is dangerous. Read it adversarially: what does it test, on which representation, and at what point relative to decoding?
4. **Write the hypothesis down before testing.** This is non-negotiable. A hypothesis recorded after the fact is a rationalisation, and it will bend to whatever you observed.
5. **Predict the observable, including the error case.** What exactly should you see if you are right? What should you see if you are wrong? If both outcomes look the same from where you sit, your test cannot distinguish them — fix the test before running it.

**Common misreadings that waste days:** confusing a check that *exists* with one that *executes on your path*; assuming normalisation happens before comparison when it happens after; reading a validation as applying to the decoded value when it applies to the raw one. When input and outcome disagree, the disagreement is the finding candidate.

---

## 3. DIFFERENTIAL AND NEGATIVE-CONTROL MINDSET

The single highest-value discipline in research is knowing what *should not* change, and proving
that it does not. A positive result without a negative control is an anecdote.

| Test kind | Question it answers | Example |
|---|---|---|
| **Negative control** | does the behaviour need my input at all? | send the same request with a benign value — if the response matches, you found nothing |
| **Differential** | does the behaviour change *only* when the suspect variable changes? | flip one character; if the output flips with it, the variable is causal |
| **Baseline** | what is normal here, recorded before I touched it? | capture the pre-test state so "after" is comparable |
| **Isolation** | does it still work when unrelated variables are held constant? | same account, same session, same timing, one variable |
| **Repeat** | is it deterministic or a race? | run N times; note variance explicitly rather than once |

**Three rules that catch most self-deception:**

1. **Test the negative case as carefully as the positive.** Try to make your own finding fail. If you have not genuinely attempted to disprove it, you do not yet know whether it is real.
2. **Change one variable per attempt** and record what was held constant. Two simultaneous changes produce an uninterpretable result whether or not it "works".
3. **Distrust any result that only appears once.** Non-determinism means either a race, a cache, or an artefact of your own tooling. All three need explaining before the result is reportable.

**A signal is not a finding.** A delay, an unusual status code, a longer response body, a stack trace, a different error string — these are *leads*. Each one costs a hypothesis to explain. "The response was 40 ms slower" is worth pursuing only if you can name a mechanism that predicts it.

---

## 4. MINIMAL REPRODUCTION AND BOUNDARY ASSUMPTIONS

Reduce until removing anything more stops the reproduction. The minimal case is what the triager
will actually run, so it is not tidiness — it is the deliverable.

```bash
# Keep a numbered log as you reduce: each step records what changed and what happened.
#   step 3: removed header X — still reproduces
#   step 4: removed parameter Y — STOPPED reproducing  -> Y is load-bearing
```

**Boundary table.** For every numeric, length, index, or size assumption, walk the edges. Bugs cluster
where a developer's mental model of "normal" meets the edge of the type.

| Boundary | Probe | What a failure looks like |
|---|---|---|
| Zero / empty | empty string, empty array, zero quantity | crash, bypass, default granted |
| One | single element, single byte | off-by-one in loops and slices |
| Max | declared limit, limit+1, max int | truncation, wrap, silent clamp |
| Negative | negatives where unsigned is assumed | reinterpreting, large allocation |
| Overlong | 2× the expected length | truncation *after* validation |
| Unicode / normalisation | lookalikes, combining marks, NUL, RTL | filter bypass via representation |
| Encoding | double-encoded, mixed case, alternate charset | validator sees one value, sink another |

**Type assumptions.** Ask what the code believes the value *is* versus what arrives. A string that
becomes an integer, an object that becomes a string, an array that becomes a scalar, `null` where an
object was assumed — each of these is a place where two subsystems disagree about meaning, and
disagreement is a vulnerability class in itself.

**The validation-vs-use gap is the most productive assumption to attack.** Locate where a value is
checked, then where it is used. If anything transforms it between — decoding, trimming, normalising,
re-parsing, re-serialising — test whether the second representation still satisfies the first check.

---

## 5. FROM SIGNAL TO PROVEN FINDING

A proven finding has four parts. Missing any one of them converts the report into a question the
triager has to answer for you, and most will not.

1. **Reproduction** — exact, minimal steps from a defined starting state, that another person can follow without your environment.
2. **Mechanism** — the code path or specification clause, with a file:line or a quoted sentence, explaining *why* it happens. Without this, a fix is guesswork.
3. **Observable impact** — what the attacker gains, demonstrated rather than asserted. Not "could lead to data access" but "returned records belonging to a different account".
4. **Boundary conditions** — who can reach it, what privileges or prerequisites are required, and what does *not* work. The negatives are part of the finding.

Then answer the question that decides whether it is a bug at all: **what did the system promise?**
Compare the promise to the behaviour.

| Behaviour | Verdict |
|---|---|
| Contradicts documented or implied intent, reachable by a lower-privileged party | **bug** |
| Contradicts intent, but requires the privileges that already grant the impact | **usually not a bug** |
| Matches an explicit, documented design decision ("this endpoint is intentionally public") | **intended — not a bug** |
| Undocumented, surprising, but no party gains anything they did not already have | **hardening note, at most** |
| Matches documented intent but the documentation is dangerous | **misconfiguration / design finding**, report as such |

**Distinguishing bug from intended behaviour** is the step researchers most often skip, and it is the
step triagers perform first. Look for: comments stating the trade-off, tests that assert the current
behaviour, API docs, changelog entries describing it as deliberate, and whether the behaviour
predates the feature that would make it exploitable. If a test asserts it, you are arguing with a
decision, not reporting a defect — you need an impact argument, not a longer reproduction.

**Before writing it up, sweep for siblings.** The same misunderstanding usually appears in every
place that shares the code. One report covering the class is worth more than five duplicate reports,
and it is the difference between a finding and a fix.

---

## 6. RESPONSIBLE DISCLOSURE AND TIMELINES

Choose the channel before you are tempted to publish. The right channel is set by the rules that
apply to the work you did.

| Situation | Channel |
|---|---|
| Program with a published policy | that program's platform; follow its scope and rules exactly |
| Client engagement under contract | the engagement's named security contact, in writing |
| Vendor with a security contact or PSIRT | that contact; PGP if offered |
| Vendor with no contact | a coordinated-disclosure body or national CERT as intermediary |
| Your own product or an open-source dependency | upstream maintainer, via the project's stated process |

**Timelines that are conventional, not contractual** — state your own intention rather than quoting these as rights:

- **Acknowledge** the report to the recipient within a few business days.
- **Triage** (accepted, duplicate, or out of scope) typically within two weeks.
- **Fix** for a serious, reachable issue is usually measured in weeks to a few months; complex or cross-team issues run longer.
- **Public disclosure** conventionally follows a fix being available to users, with a grace period for adoption, and is commonly discussed at around 90 days for a vendor that has gone silent.

**Rules that protect you and the recipient:**

1. **Never test beyond what the authorisation covers**, even when the finding invites the next step. Owning the demonstration of impact is not worth invalidating the report.
2. **Never touch real user data.** Prove access with a record you created, or stop at the boundary and say so.
3. **Do not publish before a fix exists** unless the vendor is unresponsive *and* you have given clear notice of your intention.
4. **Do not exaggerate severity to force a response.** Inflated ratings are the fastest route to being disbelieved on the report that matters.
5. **Put the timeline in writing** from the first message, and keep it.
6. **Escalate to an intermediary if the vendor is silent** past the agreed window, and tell the vendor you are doing so.

---

## 7. THE RESEARCH NOTE


The note is the artefact. Everything above exists to produce it, and a finding that is not written
down did not happen. Keep two documents: a running log you write *while* working, and the final note
written from that log.

---

## 8. EVIDENCE STANDARD

**Evidence standard — required fields:**

| Item | Why it must be here |
|---|---|
| Hypothesis as stated *before* testing | proves the result was predicted, not fitted to observation |
| Negated control and its result | distinguishes the finding from baseline noise |
| Minimal reproduction, exact | makes the claim independently checkable |
| Mechanism with file:line or spec clause | converts a symptom into a fixable defect |
| Raw observable (request, response, log line, screenshot) | the primary evidence; never paraphrase it |
| Environment: version, build, config, date | behaviour is version-bound; undated evidence is unusable |
| Impact statement, demonstrated | separates a bug from a curiosity |
| Explicit negatives — what was tried and did not work | pre-empts the triager repeating your dead ends |
| What you did *not* test | honest limits make the rest credible |
| Binary verdict: proven, signal-only, or disproved | a disproof is a result worth recording |

---

## 9. REMEDIATION REFERENCE

**Remediation reference — how to write the fix advice:**

1. **Name the mechanism, not the symptom.** "Normalise the entry name before resolving it against the root" is actionable; "fix path traversal" is not.
2. **Recommend the control at the layer that owns the invariant.** Validating at the edge when the promise belongs to the sink creates a second place to get it wrong.
3. **Allow for defence in depth.** Give the primary fix and one independent second control; do not present a pile of alternatives as if they were equal.
4. **State what the fix must not break.** A validation that rejects legitimate input trades a security bug for an availability incident.
5. **Say when a code change is not enough.** If the exposure already happened, remediation includes rotation, revocation, or notification — not only a patch.
6. **Keep the verdict honest.** If the behaviour is intended, say so and recommend documentation; a hardening note dressed as a vulnerability damages the next report you file.

**Validate every factual claim in the note** — the precise version, the file path, the exact string, the
byte count, the response code. Each unverified detail is a credibility liability. Mark anything you
could not verify as unverified rather than writing it smoothly into the narrative.

**Self-verify** — run from the workspace root; all checks are read-only.

```bash
f=skills/impl/vuln-research-methodology/SKILL.md
wc -c "$f"                                   # expect 11,000-14,000, hard max 15,000
grep -cE '^## [0-9]+\.' "$f"                 # expect exactly 7
grep -q 'AI LOAD INSTRUCTION' "$f" && echo "load block present"
grep -q 'REMEDIATION REFERENCE' "$f" && echo "closing sections present"
grep -oE '\]\(\.\./[^)]+\)' "$f" | sed -E 's/^\]\(\.\.\///; s/\)$//' | sort -u | \
  while read -r p; do [ -e "skills/impl/$p" ] || echo "BROKEN LINK: $p"; done
```

---

## 10. CONFIRMING THE FINDING

Sections 3 and 5 already state the differential mindset; this table is the gate a hypothesis must pass
before it becomes a finding. The domain's purpose is that **a researcher's intuition is a hypothesis, and a
finding is a differential with the boundary pinned.**

| Step | Question | What it proves |
|---|---|---|
| 1 | Is there a **negative control** - the same input that does NOT trigger the behaviour? | without it, a coincidental effect is indistinguishable from the flaw |
| 2 | Is the trigger the **minimal** input, with every unnecessary element removed? | a large input hides which element is the cause |
| 3 | Is the **boundary** pinned: the smallest change that makes the flaw disappear? | the boundary is what makes the report actionable |
| 4 | Is the effect **reproducible** from a clean state, by the documented steps alone? | non-reproducible findings are narration |
| 5 | Is the **precondition** stated: the configuration, version, or state the flaw requires? | a flaw needing a non-default state is a different finding |
| 6 | Is the effect **observed**, not inferred from a mechanism? | reasoning about a mechanism is not evidence |
| 7 | Is the **impact** demonstrated at the furthest point reached, and no further claimed? | scope discipline |

**A negative control, a minimal trigger, a pinned boundary, and reproducibility from a clean state.** The
mechanism explains the finding; it is never the finding itself.

---

## 11. EXECUTION PRIMITIVES

This domain is methodology, so the execution is a **harness discipline**: the differential, the minimal
reproduction, and the boundary bisection. Every step below is a procedure, not a command list.

### 8.1 The differential, which is the core tool

```bash
# THE DIFFERENTIAL IS A STRUCTURE, NOT AN OBSERVATION. Build it explicitly.
cat > /tmp/differential.md <<'MD'
## THE DIFFERENTIAL RECORD (sections 3 and 8)
| | CONTROL (no trigger) | TREATMENT (trigger) | OBSERVED DIFFERENCE |
|---|---|---|---|
| input            | | | |
| configuration    | | | |
| observed output  | | | |
| side effects     | | | |
| repeat count     | | | |

## RULES
1. CONTROL AND TREATMENT MUST DIFFER IN EXACTLY ONE VARIABLE. If two differ, the result is uninterpretable.
2. RUN EACH THREE TIMES. A difference that appears once in three is NOISE, and it is the commonest
   false finding in research. RECORD ALL THREE RESULTS, including the failures.
3. THE VARIABLE MUST BE THE ONE YOU CLAIM. If the control and the treatment also differ in timing,
   ordering, or state, the difference may be caused by THOSE.
4. A DIFFERENCE THAT DISAPPEARS ON A CLEAN RESTART is usually STATE from a previous test. ALWAYS
   reproduce from a clean state, and record that you did.
MD
cat /tmp/differential.md
echo
echo "=== THE CLEAN-STATE DISCIPLINE, mechanically ==="
cat <<'CLEAN'
  A HYPOTHESIS IS CONFIRMED ONLY FROM A DEFINED STARTING STATE. RECORD, FOR EVERY RUN:
    the version(s)         : of the target AND of every component on the path
    the configuration      : the relevant settings, and whether they are DEFAULT
    the clean start        : how the state was reset, and what the reset restores
    the prior state        : whether any earlier test left anything behind
  'IT WORKED ON MY MACHINE' IS NOT REPRODUCIBILITY. The steps must reproduce on a machine that has
  never run the earlier tests - and if they do not, THE FINDING IS ENVIRONMENTAL, which is a
  DIFFERENT (and often weaker) finding that must be stated as such.
CLEAN
```

**A difference that appears once in three runs is noise, and a difference that disappears on a clean
restart is usually state from a previous test.** The control and the treatment must differ in exactly one variable.

### 8.2 Minimal reproduction, and boundary bisection

```bash
echo "=== MINIMISATION (section 4): remove until the flaw disappears, then put ONE element back ==="
cat > /tmp/minimise.md <<'MD'
## MINIMISATION PROCEDURE
1. Start from the reproducing input.
2. Remove ONE element (a parameter, a header, a field, a step) and re-test.
3. If it STILL reproduces -> the element was unnecessary. DISCARD IT PERMANENTLY.
4. If it STOPS reproducing -> the element is REQUIRED. RESTORE IT and mark it as a precondition.
5. Repeat until no element can be removed. THE RESULT IS THE MINIMAL REPRODUCTION.
6. RECORD THE LIST OF REQUIRED ELEMENTS - each one is either part of the flaw or a stated precondition.
MD
cat /tmp/minimise.md
echo
echo "=== BOUNDARY BISECTION: the smallest change that makes the flaw disappear ==="
cat <<'BISECT'
  THE REPRODUCTION GIVES YOU THE SMALLEST INPUT THAT FAILS. THE BOUNDARY GIVES YOU THE SMALLEST
  INPUT THAT SUCCEEDS, AND THE DISTANCE BETWEEN THEM IS WHAT THE REPORT QUANTIFIES.

  PROCEDURE:
    1. take the required element identified in minimisation (e.g. an input length, a count, a value)
    2. FIND THE VALUE WHERE THE FLAW STOPS: bisect between the working and the failing values
    3. RECORD THE EXACT THRESHOLD and the exact comparison that produces it (a length check, a
       numeric limit, a type coercion, an off-by-one)
    4. THE BOUNDARY IS THE FINDING'S ACTIONABLE PART: a developer cannot fix 'it crashes with a big
       input', but they CAN fix 'the length check permits 256 and the buffer is 255'.

  AND THE OFF-BY-ONE PROOF, which is the canonical shape: show the input at the boundary SUCCEEDING
  and the input ONE STEP BEYOND FAILING. THAT PAIR IS THE FINDING, and it is unarguable.
BISECT
echo
echo "=== THE ASSUMPTION AUDIT (section 4), which turns a hunch into a hypothesis ==="
python3 - <<'PY'
A = [("the input is validated at THIS layer", "validate at an EARLIER layer", "a predecessor already rejected it -> no finding"),
     ("the caller sends what I send",         "an intermediary REWRITES the input", "the rewrite is the finding, not the flaw"),
     ("the default configuration is in use",  "the default is DIFFERENT than assumed", "the flaw needs a non-default state"),
     ("the check compares the whole value",   "the check compares a PREFIX or a CAST", "the truncation/coercion IS the flaw"),
     ("the operation is atomic",              "an interleaving is possible",        "the race is the finding, not the logic"),
     ("the function is reachable from the frontend", "an authorisation gate precedes it", "the flaw is real but UNREACHABLE -> scope caveat"),
     ("the version I tested is deployed",     "the vulnerable version is not",      "a version-scoped finding, and it must say so")]
print("%-44s %-40s %s" % ("assumption to audit","the opposite, which is often true","consequence if it is"))
for a,b,c in A: print("%-44s %-40s %s" % (a,b,c))
print()
print("  THE PROCEDURE: for each row, PERFORM THE TEST that distinguishes the two assumptions.")
print("  That test IS the negative control for that assumption, and recording it is what separates")
print("  research from speculation.")
PY
```

**The off-by-one pair — the value at the boundary succeeding and one step beyond failing — is the finding.**
And each assumption must be audited with a test that distinguishes it from its opposite.

### 8.3 Reachability and impact, and the goal

```bash
echo "=== REACHABILITY: A FLAW BEHIND AN AUTHORISATION GATE IS A DIFFERENT FINDING ==="
cat <<'REACH'
  THE CHAIN, STATED EXPLICITLY AND PROVEN AT EACH STEP:
    the ENTRY POINT     : what the attacker can invoke, and with what privileges
    the PATH            : the calls between the entry point and the flaw, each one shown to pass
                          the input through UNMODIFIED (or to modify it in a recorded way)
    the GATE            : any authorisation, authentication, or validation BETWEEN them, and
                          whether the attacker's position SATISFIES it
    the PRE-CONDITION   : the state the flaw needs, and whether an attacker can establish it
  A FLAW WITH AN UNSATISFIED GATE IS NOT EXPLOITABLE, and reporting it as such is overreach. The
  correctly-reported finding says: 'the flaw exists at L, the gate at G requires condition C, and
  the attacker's position does/does not satisfy C.' THAT STATEMENT IS COMPLETE AND DEFENSIBLE.
REACH
echo
echo "=== IMPACT: DEMONSTRATE TO THE FURTHEST POINT REACHED, CLAIM NOTHING BEYOND ==="
cat > /tmp/impact.md <<'MD'
## IMPACT LADDER - climb only as far as you actually demonstrated
1. the behaviour differs from the specification        <- a SPECIFICATION finding
2. the difference is reachable without satisfying the gate  <- an EXPLOITABILITY finding
3. a memory read/write or a logic bypass was DEMONSTRATED   <- a MEMORY/LOGIC finding
4. control of a pointer, a value, or a decision was shown   <- a CONTROL-FLOW finding
5. code execution, a file read, or an account was obtained  <- a full-IMPACT finding

## THE RULE: STOP AT THE HIGHEST NUMBERED STEP YOU DEMONSTRATED, AND SAY WHICH. 
## Every step ABOVE it is a CLAIM, not a result, and a report that infers 5 from 2 is the exact
## defect this domain exists to prevent. ("It should be exploitable" is not a finding.)
MD
cat /tmp/impact.md
echo
echo "=== THE DISCLOSURE TIMELINE (section 6), as a tracked artefact ==="
python3 - <<'PY'
print("  record, with dates and a channel for each:")
for s in ["the discovery date, and the reproducible steps' final state",
          "the vendor's first-contact attempt(s), with the channel and the acknowledgement",
          "the vendor's acknowledgement, and any reference/ticket identifier",
          "the agreed or policy-derivable disclosure deadline, and its basis",
          "any extension, requested or granted, with the reason",
          "the fix's version, and the date it was verified",
          "the publication date, and what was published (the advisory, the reproducer, both)"]:
    print("    [ ] " + s)
print()
print("  AND THE CONTROL: the fix was RE-TESTED against the minimal reproduction, from a clean state,")
print("  and is reported as FIXED, PARTIALLY FIXED, or NOT FIXED. A disclosure without the retest has")
print("  established nothing about whether the report was actioned.")
PY
```

**Stop at the highest impact step actually demonstrated** — "it should be exploitable" is not a finding. And a
disclosure without the retest has established nothing about whether the report was actioned.

### 8.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== VULN RESEARCH ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("a NEGATIVE CONTROL exists: the same input without the trigger, showing no difference",
  "without it a coincidental effect is indistinguishable from the flaw"),
 ("control and treatment differ in EXACTLY ONE variable",
  "two differing variables make the result uninterpretable"),
 ("each was run THREE times, and all results including the failures are recorded",
  "a difference appearing once in three is noise"),
 ("reproduction is from a CLEAN state, and the reset procedure is documented",
  "a difference vanishing on restart is usually leftover state"),
 ("the target's version and the DEFAULT-status of its configuration are recorded",
  "a flaw needing a non-default state is a different finding"),
 ("each core ASSUMPTION was audited with a test distinguishing it from its opposite",
  "the audit is the negative control for the assumption"),
 ("the reproduction was MINIMISED, and the required elements plus preconditions are listed",
  "a large input hides which element is the cause"),
 ("the BOUNDARY was bisected, with the value at the boundary succeeding and one step beyond failing",
  "the off-by-one pair is the actionable, unarguable finding"),
 ("REACHABILITY is proven step by step: entry point, path, gate, precondition",
  "a flaw behind an unsatisfied gate is not exploitable"),
 ("the IMPACT LADDER step is named, and nothing above it is claimed",
  "'it should be exploitable' is not a finding"),
 ("the effect was OBSERVED, not inferred from a mechanism",
  "reasoning about a mechanism is not evidence"),
 ("the disclosure timeline is tracked with dates, channels, and the final state",
  "a disclosure without the retest establishes nothing"),
 ("the FIX was retested against the minimal reproduction from a clean state",
  "FIXED / PARTIALLY FIXED / NOT FIXED, evidenced"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  hypothesis : the claim, in one sentence, falsifiable")
print("  differential: control vs treatment, one variable, three runs each")
print("  minimal    : the smallest reproduction, with required elements and preconditions")
print("  boundary   : the threshold, the comparison, and the off-by-one pair")
print("  reachability: entry point, path, gate, precondition")
print("  impact     : the ladder step demonstrated, and nothing above it")
print("  disclosure : the timeline, the fix, and the retest")
PY
```

**Hypothesis, differential, minimal reproduction, boundary, reachability, impact step, disclosure.** The
differential with one variable and three runs is the gate everything else passes through.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [recon-methodology](../recon-methodology/SKILL.md) - the surface inventory a target is chosen from
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how the finding is written for a reader
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - the provenance discipline the same evidence shares
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) - the wire-level evidence for a protocol claim
- [code-review](../code-review/SKILL.md) - the code-reading practice a hypothesis starts from
