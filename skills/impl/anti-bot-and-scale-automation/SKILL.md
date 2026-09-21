---
name: anti-bot-and-scale-automation
description: >-
  Scaling authorised security testing against anti-automation controls. Use when
  an engagement covers more surface than manual testing can reach, or when rate
  limits, CAPTCHAs, WAF scoring, or fingerprinting shape the test plan. Covers
  the control taxonomy, pacing and identity discipline, the ethical line on
  detection-avoidance, handoff points, and scan reliability engineering.
---

# SKILL: Anti-Bot & Scale Automation

> **AI LOAD INSTRUCTION**: This skill is about **testing efficiency inside an authorised
> engagement**, not defeating someone else's defences. Anti-automation controls
> (rate limits, CAPTCHAs, WAF scoring, fingerprinting, lockouts, proof-of-work) raise the
> cost of bulk abuse, and your scanner pays that same cost. **Pacing and identity
> management beat evasion in every authorised test** — negotiate the rate, authenticate
> properly, checkpoint relentlessly, hand off where judgement is required. Disclose
> automation to the SOC so alerts are expected, not suppressed.
## 0. RELATED ROUTING

- [recon-methodology](../recon-methodology/SKILL.md) — breadth-first enumeration doctrine
- [recon-and-methodology](../recon-and-methodology/SKILL.md) — scoping and methodology
- [nuclei-custom-template-authoring](../nuclei-custom-template-authoring/SKILL.md) — the scan payload layer
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) — network-layer testing at scale
- [anti-bot-and-scale-automation](../../core-subjects/anti-bot-and-scale-automation.md) — core doctrine stub
- [grabber-auto-extraction-engine](../../core-subjects/grabber-auto-extraction-engine.md) — extraction-at-scale doctrine

---

## 1. WHY SCALE MATTERS

A manual tester covers ~50 endpoints in depth. A real estate has 50,000: subdomains,
API routes, parameter variants, forgotten staging hosts. The client is not buying 50,000
exploits; they are buying **confidence that nothing in the 50,000 is trivially broken**.

| Effort | What it buys | Where it fails |
|---|---|---|
| Manual depth (50 targets) | chained logic flaws, business-logic abuse | misses the forgotten host entirely |
| Automated breadth (50,000 targets) | every exposed panel, debug route, default credential | cannot judge exploitability or impact |
| Breadth + manual triage | breadth locates, judgement confirms | needs triage discipline; the queue must be ranked |

**Automation's value concentrates in breadth of enumeration, not depth of exploitation.**
A scanner that fingerprints 50,000 hosts and surfaces 40 candidates worth a human hour
each earns its keep. A scanner tuned to "exploit" unattended produces incident reports.
Budget by yield, not requests: a 6-hour scan returning 5 ranked, reproducible
findings beats a 72-hour scan returning 4,000 unranked alerts.

---

## 2. ANTI-AUTOMATION CONTROL TAXONOMY

Classify each control before deciding how the test plan accommodates it. Do not evade;
**classify, then negotiate or pace around**.

| Control | What it keys on | What it breaks in your testing |
|---|---|---|
| **Rate limiting** | requests per key (IP, account, token, route) per window | bulk enumeration, fuzzing, template sweeps |
| **CAPTCHA / Turnstile** | interaction proof at a decision point (login, signup) | unauthenticated bulk flows touching that route |
| **WAF behavioural scoring** | anomaly aggregate: path entropy, velocity, reputation | aggressive fuzz payloads, high-entropy strings |
| **Browser fingerprinting** | canvas, fonts, header order, JS execution | raw-HTTP tooling against protected routes |
| **TLS fingerprinting (JA3/JA4)** | ClientHello shape: ciphers, extensions, ALPN | non-browser TLS stacks; Go/Python defaults stand out |
| **Account lockout** | failed-auth count per account | credential testing, spray validation |
| **Proof-of-work** | client-side CPU per request | throughput; 1s PoW caps you at ~3,600 req/hour/core |

**The single most important classification: per-IP controls are negotiated with
infrastructure, per-account with the application owner, per-route with both —
misidentifying which one blocked you wastes the engagement window.**

Accommodation per control: rate limiting → pace and prioritise routes, never rotate
source IPs to defeat it unagreed. CAPTCHA → test the route manually or against a staging
mirror; solving CAPTCHAs at scale tests your solver vendor, not the client. WAF scoring
→ low-entropy discovery pass first, ugly strings only on confirmed candidates. Browser
and TLS fingerprinting → real browser automation per-route, accepting the 10–50x cost.
Lockout → dedicated test accounts with known thresholds; locking out real users is a
self-inflicted DoS. Proof-of-work → parallelise or drop to manual; PoW slowing your
scanner is signal, report it as such.

---

## 3. THE COST OF LEGITIMACY

Legitimate testing at scale costs throughput. Pay it deliberately.

| Identity choice | Throughput | When to use |
|---|---|---|
| Raw HTTP, single session | highest | unprotected enumeration, header checks |
| Raw HTTP, pooled authenticated sessions | high | API testing behind token auth |
| Full browser automation | 10–50x slower | routes gated by fingerprint or JS challenge |
| Dedicated test accounts, known roles | n/a (correctness) | every authenticated pass |

**When a control slows you, the correct move is better identity (authenticated session,
real browser, agreed allowlist), not more concurrency against the same blocked identity.**

Pacing discipline: start at 1–5 req/s per identity and read one full window of response
codes before ramping — 429/403/503 clusters tell you the control's shape. Jitter delays
(±30%) so traffic avoids metronomic periodicity. Separate discovery traffic from attack
traffic into different identities; a burned discovery identity must not take the
exploitation session down. Back off exponentially on 429, and **stop and escalate after
three consecutive blocked windows** — continued pressure is load, not testing.

---

## 4. DETECTION-AVOIDANCE AS AN ETHICAL CONSTRAINT

The line: **efficient testing means client monitoring sees you and recognises you;
evading it robs the client of the detection signal they paid for.**

| Efficient (do this) | Evasive (never unagreed) |
|---|---|
| Declared source IPs / accounts in the ROE | Rotating proxies to hide volume |
| Agreed rate window, SOC on standby | Throttling just under the alert threshold |
| Asking for monitor-only WAF rules for scanner IDs | Encoding payloads to blind the client's WAF |
| Reporting which alerts fired on your traffic | Avoiding alerts, then claiming "undetected" |

Negotiate before any bulk pass: scan window, sources, and peak rate in writing; whether
the SOC wants your alerts forwarded, tagged, or suppressed; lockout-exempt test accounts
and exact thresholds; destructive-route exclusions (reset storms, SMS/email triggers,
mass state-changing POSTs). Log every deviation from the agreed rate.

**If the SOC did not expect your scan, the scan failed operationally even if it found
vulnerabilities — unexpected automation burns incident-response hours.**

---

## 5. WHERE AUTOMATION STOPS BEING USEFUL

Automation locates; judgement concludes. Hand off at these boundaries.

| Boundary | Handoff action |
|---|---|
| Requiring judgement (exploitability, chaining, impact) | human confirms and chains manually |
| Destructive (writes, deletes, fund movement) | one human proof, then stop |
| Stateful (multi-step flows corrupt under concurrency) | single-threaded manual pass, fresh account |
| Authz-subtle (IDOR/BOLA needs ground truth) | human replays both identities and compares |
| Novel (new framework, custom protocol) | human reads docs/JS first, then writes a check |
| Legally adjacent (PII volume, scope blur) | stop, confirm scope in writing, minimise retrieval |

**Scanner output is a suspect list, never a finding list — every automated result is
unconfirmed until a human replays it and writes the impact.**

---

## 6. RELIABILITY ENGINEERING FOR LONG SCANS

Long scans fail. Design for failure, not the happy path.

| Mechanism | Minimum implementation |
|---|---|
| **Checkpointing** | persist completed-target offset every ≤100 targets |
| **Resumability** | resume flag reads the checkpoint; never restart from zero |
| **Dedup** | key findings on (host, route, check-ID); merge before reporting |
| **Idempotency** | read-only passes first; state-changing checks singly gated |
| **Loud failure** | non-zero exit + targeted/attempted/completed/failed counts |
| **Result streaming** | append incrementally; never hold results in memory |

**A scan that half-completes silently is worse than one that fails loudly — silent
incompleteness becomes false assurance ("all hosts tested, no findings").**

Record a run manifest per bulk pass: time window, tool + version, check set + versions,
target/attempted/completed/failed counts, rate and identities used, control encounters
(429/403/challenge counts), checkpoint location. Without it the coverage claim is
unverifiable.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| agreed window, rate, source IDs, SOC notification | proves traffic was authorised and expected |
| tool, version, check set with versions | the result is only reproducible against that set |
| universe vs attempted vs completed counts | **coverage claims require a denominator** |
| control encounters with timestamps | explains gaps honestly instead of hiding them |
| checkpoint and resume log for multi-hour passes | proves completeness or bounds incompleteness |
| raw-to-reported finding counts with dedup key | shows the triage funnel, not just output |
| manual replay evidence per reported finding | an unreplayed scanner hit is not a finding |
| routes excluded from automation and why | the client must know what was never bulk-tested |

**Report the denominator or do not claim coverage — "no findings" over an unknown
fraction of the estate is not a result.**

---

## 8. REMEDIATION REFERENCE

1. **Rate limiting: key on the right principal** — per-account stops credential abuse;
per-IP stops dumb floods but punishes shared egress; per-route protects expensive
endpoints (login, search, export). Deploy all three; a single global per-IP limit is
both bypassable and self-DoSing.
2. **CAPTCHA placement: gate the abuse decision point, not the site** — login, signup,
reset, checkout, submission. Progressive escalation (none → invisible score → visible
challenge) stops bulk abuse without taxing every legitimate user.
3. **Lockout without self-DoS** — progressive delays plus CAPTCHA after N failures, not
hard lockout at low N: hard lockout at 5 turns a username list into a DoS weapon. Alert
on distributed spray (many accounts, few attempts each), not just per-account counts.
4. **WAF scoring: score, then act in tiers** — monitor → challenge → block, with decay.
Binary block-on-first-anomaly false-positives on legitimate-but-unusual clients; log
score components so tuning is evidence-driven.
5. **TLS fingerprinting as signal, never sole gate** — middleboxes, old handsets, and
legitimate automation present unusual fingerprints. Combine with behaviour and identity
before denying, or you block real customers.
6. **Proof-of-work calibrated to the abuse margin** — ~0.5–1s per challenge breaks bulk
economics invisibly; 5s+ punishes low-end devices. Adaptive difficulty (up under load,
down at idle) holds the line without permanent UX tax.
7. **Device fingerprinting expects rotation** — any observable client property can be
re-implemented by the client. Use it to raise bulk-abuse cost alongside rate limits and
auth, never as the single control a finding depends on.
8. **Observe the controls themselves** — dashboard block/challenge rates per rule, alert
on sudden shifts. A control nobody watches is either blocking customers silently or dead
silently.

---

## 9. EXECUTION PRIMITIVES

Scale automation is an engineering discipline: measure the limit, then stay under it. These blocks
produce numbers rather than prose, because "slow down" is not actionable and "1 request per 2.4s per
identity" is.

### 9.1 Measure the rate limit empirically

```bash
# find the threshold: fire increasing bursts of a benign, idempotent endpoint and watch for the wall
URL="https://target.tld/api/public/health"
for N in 5 10 20 40 80 160; do
  START=$(date +%s.%N)
  for i in $(seq 1 "$N"); do
    curl -s -o /dev/null -w '%{http_code} ' "$URL" &
  done > /tmp/codes 2>&1
  wait
  END=$(date +%s.%N)
  BLOCKED=$(tr ' ' '\n' </tmp/codes | grep -cE '^(429|403|503)$' || true)
  OK=$(tr ' ' '\n' </tmp/codes | grep -c '^200$' || true)
  printf 'burst=%3d ok=%3d blocked=%3d elapsed=%.2fs\n' "$N" "$OK" "$BLOCKED" "$(echo "$END-$START"|bc)"
  sleep 30   # let the window reset
done
```

The burst where `blocked` first becomes non-zero, divided by the window, is your ceiling. **Always
sleep between bursts** - without the reset you are measuring cumulative counters, not the rate.

### 9.2 Read the limiter's signals, not your guess

```bash
curl -sS -D- -o /dev/null "https://target.tld/api/public/health" | grep -iE \
  '^(x-ratelimit|ratelimit|retry-after|x-rate|cf-ray|server-timing|cache-control)'
```

Headers like `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `RateLimit-Limit`,
and `Retry-After` tell you the budget and the reset. **A `Retry-After` you ignored is the most common
cause of a self-inflicted block**; parse it and honour it rather than retrying blind.

### 9.3 Token-bucket client with backoff that actually backs off

```bash
python3 - <<'PY'
import time, random, urllib.request, urllib.error
RATE, BURST = 0.4, 3          # measured in 9.1: 0.4 req/s sustained, burst 3
tokens, last, backoff = BURST, time.time(), 1.0
def take():
    global tokens, last
    now = time.time(); tokens = min(BURST, tokens + (now - last) * RATE); last = now
    if tokens < 1:
        time.sleep((1 - tokens) / RATE); tokens = 0
    else: tokens -= 1
for url in open("queue.txt").read().split():
    take()
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            print(r.status, url); backoff = 1.0
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            print("throttled", e.code, "sleeping", backoff, "s")
            time.sleep(backoff + random.uniform(0, 0.5)); backoff = min(backoff * 2, 120)
        else:
            print("error", e.code, url)
PY
```

Jitter matters: without it, every worker retries in lockstep and you recreate the burst that caused
the block. Cap the backoff so a stale queue does not sleep for hours.

### 9.4 Concurrency that matches the measured ceiling

```bash
# run a scanner at a concurrency derived from the measured rate, not its default
ffuf -u "https://target.tld/FUZZ" -w words.txt \
     -rate 2 -p 0.5 -t 2 -timeout 20 -mc 200,204,301,302,401,403 \
     -o out.json -of json
# nuclei: -rate-limit is global, -concurrency is per-host; both are needed for politeness
nuclei -u https://target.tld -t http/ -rate-limit 5 -concurrency 2 -timeout 20 \
       -retries 1 -stats -stats-interval 30
```

`-rate 2 -p 0.5` means two requests per second with a half-second pause between them. **Set
concurrency to 1-2 while measuring**, then raise it only if the error rate stays at zero.

### 9.5 Distinguish a block from a network failure

```bash
URL="https://target.tld/api/public/health"
for i in $(seq 1 6); do
  R=$(curl -sS -o /tmp/b -w '%{http_code}|%{time_total}|%{size_download}' --max-time 25 "$URL" 2>&1)
  BODY=$(head -c 120 /tmp/b | tr -d '\n' | tr -s ' ')
  printf '%d  %s  %s\n' "$i" "$R" "$BODY"
  sleep 3
done
```

A `429` with a JSON body is a limiter. A `403` with a challenge page is a WAF. A timeout with
`size_download=0` is a network or defensive drop. A `200` with an empty body is an application
problem. **Record which one you hit** - "the scan failed" is not a finding, and these four causes
have four different responses.

### 9.6 Session and identity rotation, with a hard cap

```bash
# rotate identities ONLY within your own authorized accounts, and cap the total
i=0
for ID in $(cat identities.txt); do        # accounts you own or are authorized to use
  i=$((i+1))
  [ "$i" -gt 5 ] && { echo "cap reached, stopping"; break; }
  curl -sS -o /dev/null -w "id$i=%{http_code} " -H "Authorization: Bearer $ID" "$TARGET"
  sleep 3
done; echo
```

Rotation multiplies your footprint by the number of identities. **The cap is not optional** - this is
the technique that turns a disciplined test into an abusive one, and it must be bounded by the
engagement's rules, not by what the target tolerates.

### 9.7 Resumable queue for long runs

```bash
: > done.txt
while IFS= read -r line; do
  grep -qxF "$line" done.txt && continue          # resume after an interruption
  curl -sS -o /dev/null --max-time 20 "$line" && echo "$line" >> done.txt
  sleep 2
done < queue.txt
wc -l < done.txt
```

A long run that cannot resume will be restarted from zero, which doubles your request volume for no
additional coverage. Checkpoint as you go.

### 9.8 Honest coverage accounting

```bash
{
  echo "scope_domains=$({ wc -l < scope.txt; })"
  echo "attempted=$({ wc -l < queue.txt; })"
  echo "completed=$({ wc -l < done.txt; })"
  echo "blocked=$(grep -c BLOCKED log.txt || true)"
  echo "errors=$(grep -c ERROR log.txt || true)"
} > coverage.txt
cat coverage.txt
```

Report `completed` and `blocked` separately. A scan that stopped 40% in because of a block did **not**
cover the target, and presenting it as complete is the failure mode this whole domain exists to
prevent.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the control hit with a **measured, repeatable** trigger (burst size + window)? | turns "it blocked me" into a characterised limit |
| 2 | Did the control **stop** the action, or merely slow it (a challenge that can be solved)? | a solvable challenge mitigates nothing permanently |
| 3 | Is the control applied **per identity**, or is it global (and therefore a DoS vector against users)? | a global limiter is a denial-of-service finding, not a protection |
| 4 | Can the limit be bypassed by a **documented, reproducible** technique you can show? | the bypass is the finding; suspicion is not |
| 5 | Did you test **only accounts you own** and stay within the engagement's stated volume? | an out-of-scope volume test is an incident |
| 6 | Does the limitation affect the **security control** or only the **convenience** (a rate on a public endpoint)? | impact scoping; not every limiter gap matters |
| 7 | Can you show the **same action succeeding** just under the limit? | proves the limit is the cause, not an unrelated error |

**A block you caused is not a finding.** The finding is either (a) a control that is absent or
trivially bypassable for a security-relevant action, or (b) a control so aggressive it denies
legitimate users. Both need the same evidence discipline: the trigger, the boundary, and the impact.

---

## 11. EVIDENCE STANDARD — MEASURED LIMIT EVIDENCE

| Item | Why |
|---|---|
| The **measured threshold** (burst size, window length, and the reset behaviour observed) | the number is the finding; "it rate-limits" is not |
| The **limiter's own headers** (`Retry-After`, `X-RateLimit-*`) at the moment of the block | shows the control's declared policy versus its behaviour |
| Your **request rate and concurrency settings**, with the tool and version | makes the run reproducible and shows you stayed within scope |
| The **authorization** for the volume you generated, with the rules-of-engagement reference | volume testing without authorization is an incident |
| The **distinction** between block, WAF challenge, network drop, and application error, for each symptom observed | four causes, four different conclusions |
| The **coverage accounting** - attempted, completed, blocked, errored | a partial run must not be presented as complete |
| For a bypass: the **exact technique and the response proving it worked** | the bypass is the finding; the sequence is the evidence |
| For an over-aggressive control: a **legitimate request being denied**, with the account and the impact | availability findings need a real user harmed |
| Confirmation that **only accounts you own** were used and the total volume generated | the blast radius must be stated explicitly |

Report the **measured boundary and the impact**: "the login endpoint permits 10 attempts per 60s per
IP, returns `429` with `Retry-After: 60`, and remains blocked for a further 60s; the limit is keyed on
the socket address and resets when `X-Forwarded-For` is rotated, which is a client-controlled value -
so a credential-stuffing run can sustain 10 attempts/minute per spoofed address", never "there is a
rate limit".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| You were blocked after exceeding a limit you measured yourself | the control working as designed |
| A `429` on a public, unauthenticated endpoint | availability is not a security boundary; rate here protects the service, not data |
| A challenge (CAPTCHA) you did not attempt to solve | requires proof of a bypass to be reportable |
| A WAF `403` caused by your scanner's default user-agent | your configuration, not a target weakness |
| Timeouts under high concurrency you chose | self-inflicted; reduce concurrency and re-measure |
| A limiter that resets after its documented window | designed behaviour |
| "The scan was slow" with no measurement | no number, no finding |
| A block on an account you do not own | out of scope; an incident |
| Absence of a limiter on a low-risk read endpoint | hardening note, not a vulnerability |
| A bypass demonstrated with 2-3 requests where no limit was ever reached | the limit was never the obstacle |
| A block that also hit your legitimate traffic and you call it DoS | you caused the load; DoS requires harm to others |

**Volume is the risk in this domain.** Cap the run, checkpoint it, and report coverage honestly.

---

## 12. REMEDIATION REFERENCE — AUTOMATION OPERATIONS

*This domain's "remediation" is as much about operational honesty as about controls. The first
group is for defenders reading the finding; the second is for the operator of the automation.*

1. **Rate-limit on server-derived identity and the socket peer, never on a client-supplied header** - `X-Forwarded-For` and friends are attacker-controlled unless they come from your own trusted proxy; strip inbound values at the edge and key on the socket address plus the authenticated principal.
2. **Apply limits per account as well as per address** - address-only limiting is defeated by distributing across hosts, and account-only limiting lets one attacker lock out every user; both are required.
3. **Return machine-readable limiter headers** (`RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`, and `Retry-After`) - a well-behaved client can then comply, which reduces both accidental load and the incentive to evade.
4. **Prefer graduated responses over hard blocks** - a delay, then a challenge, then a block, with the escalation logged; a hard block on a shared address (NAT, corporate egress) denies legitimate users and becomes a denial-of-service.
5. **Make the control stateful across the whole request path** - limits enforced only at one edge node (or only in the application) are bypassed by hitting a different node or path; enforce in a shared store with the window defined explicitly.
6. **Do not treat the limiter as the security control** - a rate limit slows credential stuffing; it does not replace MFA, breached-credential checks, or anomaly detection. Report the layer you actually relied on.
7. **Alert on distributed low-rate patterns** - one request per second across a thousand addresses never trips a per-address limiter; detect by aggregate failures, username breadth, and ASN diversity.
8. **Log and review denials** - a control with no telemetry is either blocking customers silently or has failed silently; dashboard the block rate per rule and alert on shifts.
9. **For the operator: measure before you scale** - derive concurrency from an empirical ceiling (section 9.1), never from a tool default, and re-measure after any change in the target's behaviour.
10. **Cap total volume in the engagement plan and honour the cap** - write the maximum request budget, the allowed rate, and the stop condition into the rules of engagement, and make the tooling refuse to exceed it.
11. **Report coverage honestly** - state attempted, completed, and blocked counts separately. A run that was cut short by a control has not covered the target, and presenting it otherwise misleads the very decision the test exists to inform.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [recon-and-methodology](../recon-and-methodology/SKILL.md) - the asset discovery this scales up
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - recon when a WAF blocks the obvious path
- [401-403-bypass-techniques](../401-403-bypass-techniques/SKILL.md) - the access-control side of a `403` you meet at scale
- [web-scraping-and-data-extraction](../web-scraping-and-data-extraction/SKILL.md) - extraction at the rate you measured
- [burp-scan](../burp-scan/SKILL.md) - configuring a scanner's rate and concurrency correctly
