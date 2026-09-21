---
name: credential-list-engineering
description: >-
  Building and prioritising credential lists for authorised testing. Use when planning
  password-spraying, brute-force, or credential-stuffing campaigns, or when scoping
  authentication testing against lockout and detection. Covers attempt budgets, list
  provenance, the password-policy inverse, lockout arithmetic, and mutation rules.
---

# SKILL: Credential List Engineering

> **AI LOAD INSTRUCTION**: This is a strategy skill, not a wordlist skill. It teaches how to
> build a short, high-yield credential list for a specific target under a specific lockout
> policy — not how to download a bigger dictionary. **A 10-word targeted list beats a
> 10-million-word generic list on any rate-limited target**, because authentication attempts
> are a finite budget and success rate per attempt is the only metric that matters. Use only
> with written authorisation: exceeding the lockout budget locks the client's own users out.

## 0. RELATED ROUTING

- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) — atomic test cases and expected evidence
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) — where the list meets real services
- [osint-target-profiling](../osint-target-profiling/SKILL.md) — harvesting target-derived material
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) — AD authentication attack paths
- [credential-list-engineering](../../core-subjects/credential-list-engineering.md) — parsing, dedup, and scoring doctrine

---

## 1. ATTEMPTS ARE A BUDGET

Every authentication endpoint grants a finite number of guesses before lockout, alert, or
IP ban. Treat that number as a budget and each guess as spend. **The metric is expected
compromises per attempt, not total passwords tested.**

| Mindset | Metric | Failure mode |
|---|---|---|
| Coverage ("try everything") | passwords tested | burns budget on ~0-probability guesses; hits lockout before reaching likely ones |
| **Budget ("spend where it pays most")** | **compromises per attempt** | **forces ranking; only high-probability guesses earn a slot** |

Consequences: sort by expected hit rate, highest first — target-derived guesses and
seasonal patterns (`Spring2026`-class) lead, never `123456`. Set a stop-loss up front
("zero hits in the top N means re-derive, not continue down the generic tail"). Report the
rate ("3 pairs in 120 attempts, 2.5%"), not the count. **A long list is an admission you
do not know the target** — one OSINT hour beats ten thousand appended generic entries.

---

## 2. LIST PROVENANCE TIERS

Rank candidates by provenance — proximity to the target's humans and policies:

| Tier | Source | Value | Cost |
|---|---|---|---|
| **(a) Target-derived** | company/product names, office cities, domain words, employee names, local teams, breach-correlated passwords for the target domain | highest — humans build passwords from their environment | OSINT hours |
| **(b) Policy-derived** | what Section 3 deduces: length floor, complexity, rotation cadence, seasonal shapes | high — shrinks the space by orders of magnitude | one policy disclosure or accept/reject oracle |
| **(c) Cultural / regional** | local-language words, keyboard layout (AZERTY vs QWERTY), date formats (DDMM vs MMDD), regional calendar | medium — beats generics on non-English user bases | locale research; verify, never stereotype |
| **(d) Generic public** | rockyou-style dumps, default-credential compilations, vendor defaults | low per attempt beyond the head | download time |

Build order: cross (a) with (b) first, season with (c), admit (d) only for its head — the
first few dozen entries plus vendor defaults for in-scope products. **If tier (a) yields
fewer than ~20 candidates, do more OSINT before touching (d).**

---

## 3. THE PASSWORD-POLICY INVERSE

The policy is a generator: length floor plus complexity plus rotation history defines the
password distribution. Reason from the policy to the list, never from a list to the target.

| Policy signal | What it tells you | List consequence |
|---|---|---|
| Min 8 + 3-of-4 complexity | users append `1!`/`123!`, capitalise first letter | prioritise `Baseword1!` shapes; drop non-compliant candidates |
| Min 12–14 | `SeasonYear!` constructions dominate | generate seasonal + suffix mutations, not short words |
| 90-day rotation + history | users increment season/digit (`...01→...02`) | include ±1 season/digit neighbours of any known password |
| "Must not contain username" | whether `username123`-class guesses are worth an attempt | drop the class if enforcement is confirmed |
| Known compliance template | the exact composition rule without disclosure | build the generator to the template |

Get the policy from enrolment error messages, AD Group Policy, helpdesk KBs, or the most
honest oracle — one test account's set-password accept/reject responses. **Discard every
candidate the policy would have rejected**: a guess below the length floor is not
low-probability, it is zero-probability spend that still risks lockout.

---

## 4. SPRAY VS BRUTE VS STUFF

Three different attacks with different lockout interactions — pick by the policy, not habit.

| Attack | Lockout interaction | Detection profile | When to use |
|---|---|---|---|
| **Spray** (few passwords × many accounts) | defeats per-account lockout; each account sees 1–2 attempts | many accounts, few attempts each — the classic spray signature | **default against any lockout policy** |
| **Brute** (many passwords × one account) | trips per-account lockout fast | concentrated failures, loud, auto-remediated | almost never — only exempt high-value accounts with written approval |
| **Stuff** (breach pairs, 1:1) | usually no lockout contact — most pairs fail on username | distributed, low-per-account, but pairs are screenable artefacts | breach-correlated pairs for the target domain; validate offline first |

**Spraying is the correct default against a lockout policy; brute force almost never is.**
Sequence: enumerate valid usernames first (error differentials, Kerberos pre-auth — see
[active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md)), spray
at most 1–3 candidates per cycle, rotate source infrastructure between cycles. Never
escalate a failed spray into impromptu brute force against survivors — that converts a
quiet negative into a lockout event.

---

## 5. LOCKOUT ARITHMETIC

Computing the safe rate is arithmetic, not evasion. `T` = lockout threshold, `W` =
observation window, `R` = lockout duration, `A` = accounts, `P` = passwords per account
per cycle:

```
attempts per account per window ≤ T - 1   (never touch the threshold)
one pass per window, next cycle no sooner than W after the first attempt
total per cycle = A × P, with P ≤ T - 1
```

Example: `T = 5`, `W = 30 min`, `A = 200` → `P ≤ 4`, at most 800 attempts per cycle, next
cycle ≥30 min later. **The difference between 4 and 5 per account here is the difference
between a test and an outage.** Confirm whether counting is per-account, per-source-IP,
or both; whether unlock is time-based or admin-only; never probe the threshold
empirically against production accounts — read the policy or ask the client contact. Log
every attempt (timestamp, account, list index) so defenders can separate your spray from a
real one.

---

## 6. MUTATION RULES THAT ACTUALLY PAY

Mutations multiply a base list; most published rules are folklore. Apply in this order,
stop when the budget says stop:

| Rule | Verdict |
|---|---|
| Year / season suffixes (`2025`, `2026`, `Spring/Summer` + year) | **pays most** — rotation policies manufacture exactly these |
| Case patterns (capitalised first, then all-lower, then all-upper) | pays; interior mixed-case is low-yield |
| Digit / symbol suffix (`1`, `123`, `1!`, `123!`) | pays; matches 3-of-4 compliance behaviour |
| Leetspeak, single substitution (`P@ssword`) | partial — depth-1 pays, full-chain (`P@55w0rd`) is folklore |
| Keyboard walks (`qwerty`, `1qaz`) | narrow but real; use the target's layout, verbatim dozen only |
| Prefix mutations, reversals, doublings, inline specials | folklore — include only if a cracked sample from this target shows it |

**Generate from evidence, not combinatorics.** One cracked `Summer2025!` justifies its
neighbours (`Winter2025!`, `Summer2026!`) more than any rule file justifies ten thousand
entries. Re-derive after every hit.

---

## 7. CONFIRMING THE FINDING
Credential work has a unique property: **a list is a hypothesis until one credential works, and a
working credential is only a finding if it is verified against a real service.** This table is the gate.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **list's provenance** recorded, with its tier and its collection date? | a list of unknown age is a list of dead credentials |
| 2 | Was the **lockout threshold measured** rather than assumed? | the arithmetic that protects real accounts depends on the real number |
| 3 | Was a **successful authentication actually observed** - a session, a token, an artefact? | "the response differed" is not a valid credential |
| 4 | Is there a **control**: a known-bad credential producing the failure shape? | without it you cannot tell success from a different error |
| 5 | Is the **target's own authorisation** confirmed, and the attempt budget respected? | credential testing is the fastest way to lock out an organisation |
| 6 | Is the **credential's privilege level** established, not assumed? | a valid credential with no access is a different finding |
| 7 | Was `STATUS_PASSWORD_EXPIRED` / `MUST_CHANGE` treated as a **hit**? | the password is correct; the account state is the only difference |

**A sourced list, a measured threshold, an observed authenticated session, and a known-bad control.** A
differing response is a candidate; a session is a finding.

---

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the list, or its generation procedure + seed inputs | **without it the result is unreproducible** |
| provenance per entry/block (tiers a–d) | proves the list was engineered, not downloaded |
| the policy built against, and how obtained | justifies every excluded class and mutation |
| lockout parameters (`T`, `W`, `R`) and computed safe rate | proves threshold was respected by design |
| timestamped attempt log (account, list index, source) | separates your traffic from real attacks |
| hit rate + stop-loss decision | the Section 1 metric; a campaign without it cannot be evaluated |
| username-enumeration method and evidence | spray results are meaningless on unvalidated accounts |

**Never log plaintext guesses for uncompromised accounts** — reference list indices; only
compromised credentials appear in full, and only in the agreed secure channel.

---

## 9. REMEDIATION REFERENCE

1. **MFA everywhere it matters** — the control that makes the list irrelevant; phishing-resistant factors (FIDO2/WebAuthn) end spraying outright. Exposed and privileged accounts first.
2. **Lockout without lockout-DoS** — threshold with time-based auto-unlock, progressive delays, rate-limiting before hard lockout; alert on mass-lockout as its own attack signal.
3. **Breached-password screening at set-time** — kill tier-(d) material and stuffing pairs at creation; re-screen on breach publication, not only at rotation.
4. **Monitor spray patterns, not just brute patterns** — alert on horizontal failures (many accounts, few attempts each), distinct from concentrated single-account failures.
5. **Kill rotation-for-rotation's-sake** — forced 90-day rotation manufactures the `SeasonYear` increment this skill exploits; rotate on suspected compromise per current NIST guidance.
6. **Remove the policy oracle** — generic enrolment errors, no policy in helpdesk KBs, no username-enumeration differentials.
7. **Default-credential elimination** — inventory vendor defaults per product, force change at deployment, rescan; the head of tier (d) works only because defaults survive.

---

## 10. EXECUTION PRIMITIVES

Sections 1 and 5 give the budget arithmetic and the lockout maths; this section is **how to spend the
budget without destroying it**. Every claim in this file reduces to three numbers: **the attempts spent,
the lockout threshold observed, and the hits found**. A spray with no lockout observation is not a spray;
it is a guess about a policy.

### 9.1 The policy, measured rather than assumed

```bash
# THE LOCKOUT THRESHOLD IS A MEASUREMENT. Sections 3 and 5 give the arithmetic; this is how to get
# the inputs without locking out the estate.
echo "=== 1. THE POLICY, if it is readable ==="
echo "--- the domain policy via an authenticated session ---"
nxc smb "$DC" -u "$USER" -p "$PASS" --pass-pol 2>&1 | tee /tmp/passpol.txt
cat <<'READ'
  the fields that matter:
    Minimum password length      -> which candidate words are even eligible
    Password history             -> whether a recent password can be reused
    Maximum password age         -> how stale the list should be
    Lockout threshold            -> THE ONE THAT DESTROYS YOUR BUDGET. 0 = no lockout.
    Lockout observation window   -> how long an attempt stays counted
    Lockout duration             -> how long a locked account stays locked
READ
echo
echo "=== 2. THE FINEGRAINED POLICIES, which OVERRIDE the domain policy per group ==="
nxc smb "$DC" -u "$USER" -p "$PASS" --pass-pol 2>&1 | grep -i -A2 'fine' || \
  echo "  (fine-grained policies are per-PSO; enumerate them with the ACL path in the directory skill)"
echo "  A SINGLE PSO on a privileged group can have a threshold of 5 while the domain says 0."
echo "  THAT is the most common way a spray locks out an executive account."
echo
echo "=== 3. THE OBSERVATION, when the policy is NOT readable ==="
cat <<'OBSERVE'
  if you cannot read the policy, MEASURE it on an account you are permitted to lock:
    1. pick a HONEY/test account you control (or an explicitly scoped one) - NEVER a real user first
    2. attempt N authentications with a WRONG password, incrementing N, and WATCH the response
    3. the transition from 'logon failure' to 'account locked out' IS the threshold
    4. re-check after the observation window to learn the window's length
  RECORD: the threshold, the observation window, and the duration.
  IF YOU CANNOT DO THIS, your spray's max-attempts-per-account MUST be 1 or 2, and you must SAY
  that the threshold is unknown. A spray with an unknown threshold and 5 attempts is negligence.
OBSERVE
```

**A single fine-grained policy on a privileged group can have a threshold of five while the domain policy
says zero.** That is the most common way a spray locks out an executive account, and an unknown threshold
means a maximum of one or two attempts per account.

### 9.2 The budget arithmetic, and the spray that spends it

```bash
# THE ONLY HONEST SPRAY: one attempt per account per window, and the arithmetic shown.
cat <<'ARITH'
  THE ARITHMETIC THAT MUST APPEAR IN THE PLAN BEFORE THE RUN:
    accounts          = A
    threshold         = T   (measured or conservatively assumed)
    safety margin     = M   (use T-1, never T)
    observable window = W   (the lockout observation window)
    attempts allowed  = A * (T - 1) per W
    attempts per run  = A * 1        (one per account, the standard safe spray)
    runs per window   = T - 1
    wall-clock per round = the target's response time * A  (measure it: a slow DC changes everything)

  THE FUNCTIONAL CHECK: if A * (T-1) is smaller than your list, THE LIST IS TOO BIG for one window,
  and the answer is a LONGER campaign, not more attempts per account.
ARITH
echo
echo "=== the mechanical spray, with the safety limit as a hard stop ==="
python3 - <<'PY'
import subprocess, time, sys
A = 50            # accounts this round
T = 5             # MEASURED threshold (do not guess; use 1 if unknown)
SAFE = max(1, T - 1)
print(f"accounts={A} threshold={T} attempts-per-account-this-window={SAFE}")
print("HARD STOP: if any account shows 'locked out' or 'STATUS_ACCOUNT_LOCKED_OUT', ABORT.")
print()
print("=== the per-account attempt loop, with the abort condition ===")
print("  for user in accounts:")
print("      r = attempt(user, password)          # ONE attempt, never a loop per user")
print("      if 'LOCKED' in r: ABORT()            # the threshold assumption was WRONG")
print("      if 'SUCCESS' in r: record_hit(user); continue   # a hit does NOT mean stop the round")
print()
print("=== the responses that mean STOP, and their exact strings ===")
for s, d in [("STATUS_ACCOUNT_LOCKED_OUT", "the account is ALREADY locked; your threshold is wrong or someone else is spraying"),
             ("STATUS_ACCOUNT_DISABLED",     "the account is disabled; it is not a candidate, and it does not count"),
             ("STATUS_PASSWORD_EXPIRED",     "the PASSWORD IS CORRECT and expired - THIS IS A HIT"),
             ("STATUS_PASSWORD_MUST_CHANGE", "the PASSWORD IS CORRECT and must change - THIS IS A HIT"),
             ("STATUS_LOGON_FAILURE",        "an ordinary failure; continue"),
             ("STATUS_ACCOUNT_RESTRICTION",  "a logon-hours or workstation restriction; the password may be correct")]:
    print("  %-30s -> %s" % (s, d))
print()
print("=== THE HITS THAT ARE EASILY MISSED, and they are the ones that matter ===")
print("  PASSWORD_EXPIRED and PASSWORD_MUST_CHANGE are SUCCESSES, not failures. A tool that counts")
print("  only 'logon success' MISSES them, and these are frequently the most valuable hits because")
print("  an expired password often belongs to a service or a dormant privileged account.")
PY
```

**`PASSWORD_EXPIRED` and `PASSWORD_MUST_CHANGE` are hits, not failures, and tools that count only "logon
success" miss them.** An `ACCOUNT_LOCKED_OUT` response means the threshold assumption was wrong and the
round must abort.

### 9.3 The list's provenance, and the mutation that pays

```bash
cat <<'PROV'
  THE FOUR PROVENANCE TIERS (section 2), with the hit rate each actually delivers:
    T1  the organisation's OWN breach exposure       -> the highest hit rate, and the most defensible
    T2  the same industry and locale, and the org's language  -> the second highest
    T3  a generic global list, trimmed by the policy's minimum length -> a baseline
    T4  a bare common-passwords list                 -> the lowest, and the loudest per hit

  THE ORDER IS THE BUDGET'S: spend T1 first, because every attempt costs the same and T1 pays best.
  A campaign that spends its budget on T4 while T1 is unspent has allocated the budget wrongly.

  THE MUTATIONS THAT ACTUALLY PAY, in the order of measured benefit (section 6):
    base word
    + a season and year  (Spring2024, Winter24)      <- the single highest-yield pattern
    + the org name, or a product name
    + 1!/123!/!  suffix                              <- the commonest suffix family
    + a capitalisation swap (P@ssword style)         <- lower yield than the above, but cheap
  MEASURE YOUR OWN YIELD: track hits per mutation rule, and report the rules that paid. That
  measurement is the finding's own evidence, and it is what makes the list ENGINEERING rather
  than a dump.
PROV'
echo
echo "=== THE PASSWORD-SPRAY'S MOST IMPORTANT CONTROL: THE POLICY-COMPLIANT FALLBACK ==="
echo "  if the policy's minimum length is 12, then a candidate shorter than 12 CANNOT be a current"
echo "  password. FILTER THE LIST BY THE POLICY BEFORE SPENDING. A list that violates the policy"
echo "  is spending attempts on impossible candidates, and that is a measurable waste."
echo
echo "=== THE LOCKOUT ARITHMETIC CHECK, mechanically ==="
python3 - <<'PY'
A=50; T=5; W=30      # accounts, threshold, observation window in minutes
M=T-1
print(f"accounts={A}  threshold={T}  window={W}min")
print(f"  safe attempts per account per window : {M}")
print(f"  total attempts available per window  : {A*M}")
print(f"  rounds per window at 1 attempt each  : {M}")
print(f"  estimated wall clock per round       : {A} x the measured per-attempt latency")
print()
print("  IF the list is longer than A*M, the correct response is MORE WINDOWS, not more attempts.")
print("  AND IF T IS UNKNOWN: set attempts-per-account to 1, and state that the threshold is unknown.")
PY
```

**Filtering the list by the policy before spending is a measurable saving**, and the correct response to a
list larger than `A*(T-1)` is more windows rather than more attempts per account.

### 9.4 The hit must be used, and the end-to-end harness

```bash
echo "=== A HIT IS A CREDENTIAL, AND IT FOLLOWS THE SAME LOOP AS EVERY OTHER CREDENTIAL ==="
cat <<'USE'
  1. the hit's PLAINTEXT is confirmed by a successful authentication (the spray itself may be it)
  2. USE it against the target, and READ SOMETHING BACK
  3. THE CONTROL: the SAME read with a WRONG password must FAIL
  and for a spray hit, TWO ADDITIONAL checks:
    a. record the ATTEMPTS SPENT to obtain it  -> that is the finding's cost, and it belongs in the report
    b. record the MUTATION RULE that produced it -> that is the reusable intelligence

  AND THE SCOPE: a spray hit is a USER credential. State what that user can reach, which requires
  the same read-back as any other credential. 'We sprayed and got 4 hits' is a step, not a finding.
USE
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== CREDENTIAL LIST / SPRAY ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the LOCKOUT THRESHOLD was measured, or the report states it was unknown and why the attempt count is 1",
  "an unmeasured threshold with 5 attempts is negligence"),
 ("FINE-GRAINED (PSO) policies were checked, because one can override the domain policy per group",
  "the most common cause of locking out an executive account"),
 ("a HONEY or scoped test account was used for the measurement, never a real user first",
  "the measurement itself must not cause the incident"),
 ("the BUDGET ARITHMETIC appears in the plan: accounts, threshold, window, and attempts available",
  "the arithmetic is what makes the campaign bounded"),
 ("the list was FILTERED BY THE PASSWORD POLICY's minimum length before spending",
  "shorter candidates cannot be current passwords"),
 ("the list's PROVENANCE TIERS were ordered, and the highest-yield tier was spent first",
  "every attempt costs the same; the order is the budget's"),
 ("the spray used ONE attempt per account per window, with a hard ABORT on any locked-out response",
  "the abort is what preserves the estate"),
 ("PASSWORD_EXPIRED and PASSWORD_MUST_CHANGE were counted as HITS",
  "they are successes, and they are frequently the most valuable"),
 ("a hit was USED and something was READ BACK, with a wrong-password control",
  "a spray hit is a credential, not a finding"),
 ("the ATTEMPTS SPENT and the MUTATION RULE for each hit were recorded",
  "the cost and the reusable intelligence are the finding's substance"),
 ("the campaign's wall clock and per-attempt latency were measured",
  "a slow DC changes the arithmetic entirely"),
 ("the GOAL is named: what the compromised user could reach",
  "'we got 4 hits' is a step, not an impact"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  policy    : the threshold, the window, the duration, and any PSO override")
print("  budget    : accounts, attempts available, windows used, attempts spent per hit")
print("  list      : the provenance tiers, the filter applied, and the mutation rules that paid")
print("  hits      : the accounts, the mutation rule for each, and the attempts spent")
print("  use       : the read-back, with the wrong-password control")
print("  goal      : what the compromised identities reached")
PY
```

**Attempts spent and the mutation rule per hit are the finding's substance**, and a hit follows the same
use-and-prove loop as every other credential in this domain.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the acquisition families a spray complements
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) - an alternative acquisition path for the same accounts
- [active-directory-certificate-services](../active-directory-certificate-services/SKILL.md) - where a hit's identity leads
- [linux-privesc-gtfobins-master](../linux-privesc-gtfobins-master/SKILL.md) - the use-it-not-possess-it rule these share
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a spray's cost and yield are reported
