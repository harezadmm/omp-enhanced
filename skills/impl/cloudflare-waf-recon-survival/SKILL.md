---
name: cloudflare-waf-recon-survival
description: >-
  Working through Cloudflare and managed-WAF anti-automation during reconnaissance. Use when a
  scan is blocked by JS challenges, managed challenge pages, 1020 Access Denied, rate limiting,
  or bot score suppression. Covers diagnosis, the legitimate-client problem, and the escalation
  ladder that keeps recon useful.
---

# SKILL: Cloudflare & WAF — Recon Survival

> **AI LOAD INSTRUCTION**: This is a **diagnosis-first** skill. Most "Cloudflare blocks my recon"
> problems are not WAF bypass problems at all — they are one of five distinct failure modes with
> five different fixes, and applying the wrong one wastes hours. **Run the §1 classifier before
> touching any evasion technique.** The recon you need is usually obtainable without defeating
> anything.
>
> This complements [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) (payload evasion)
> and is itself gated by [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md)
> (the legality/efficiency frame).

## 0. RELATED ROUTING

- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) — when the WAF blocks a *payload*, not your recon
- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) — the ethical/scope frame
- [recon-methodology](../recon-methodology/SKILL.md) — where recon fits
- [osint-target-profiling](../osint-target-profiling/SKILL.md) — the passive-first alternative
- [recon-and-methodology](../recon-and-methodology/SKILL.md) — active probing
- [5-gateway-evasion](../../core-subjects/5-gateway-evasion.md) — doctrine
- [4-anti-fingerprint](../../core-subjects/4-anti-fingerprint.md) — fingerprint reduction doctrine
- [anti-bot-bypass-decision-tree](../../core-subjects/anti-bot-bypass-decision-tree.md) — doctrine

---

## 1. THE CLASSIFIER — DO THIS FIRST

Five failure modes look identical ("Cloudflare blocked me") and need five different responses.
**Read the status code and the body before anything else.**

| Symptom | Actual failure mode | Correct response |
|---|---|---|
| **403** + HTML challenge page (`Just a moment...`, `cf-chl`) | **JS/managed challenge** — bot-scored you | §3 — legitimate client, not a bypass |
| **403** + `1020` or "Access denied" flat text | **Firewall rule** (IP/ASN/country/path) | §5 — change source or path, not technique |
| **429** + `Retry-After` | **Rate limit** — you are too fast | §4 — slow down; this is not a block |
| **200** but content is a placeholder / empty | **Silent challenge** or served a decoy | §2 — verify you got real content |
| Connection reset / timeout | **TLS fingerprint** or IP reputation | §6 — the handshake itself is the signal |
| **503** with "Checking your browser" | Under **attack mode** (Cloudflare's own DDoS response) | Stop — you are now contributing to an incident |

**The 429 case is the most common misdiagnosis.** A rate limit is not a WAF block; it is a
pacing problem, and reaching for evasion tooling makes it worse. Slow down first.

**The 503/attack-mode case is a stop condition.** If your scanning has pushed the target into
Cloudflare's under-attack mode, you have caused an availability impact on the client. Stop,
notify them, and document it — this is a scope incident, not a recon problem.

---

## 2. VERIFY YOU ACTUALLY GOT BLOCKED

Many "blocks" are silent: a 200 response carrying a challenge page, an empty shell, or
Cloudflare's decoy content.

```
Checks that catch a silent challenge:
  · body length vs. a known-good page
  · presence of `cf-chl`, `challenge-platform`, `__cf_chl` in the HTML
  · `cf-mitigated: challenge` response header
  · absence of data you know the real page contains
  · a Set-Cookie for `cf_clearance` on a page that should not need it
```

**Never build a bypass on the assumption that a 200 means success.** A recon dataset silently
full of challenge pages is worse than a blocked scan, because it looks like it worked.

---

## 3. THE JS CHALLENGE — THE HONEST ANSWER

A managed challenge is Cloudflare asking "prove you are a real browser". There are only three
defensible responses.

### 3.1 Use a real browser (correct and usually sufficient)

A real Chromium driven properly passes the challenge **because it is what the challenge is
designed to admit**. This is not evasion; it is using the client the site expects.

```
Requirements for this to work:
  · a real browser engine, not an HTTP library with spoofed headers
  · JavaScript executed, not merely parsed
  · a persistent profile so cf_clearance survives between requests
  · the challenge solved ONCE, then the cookie reused
```

**The cookie is the prize.** Solve the challenge once, persist `cf_clearance` plus the user-agent
it was issued to, then reuse both for the remainder of the session. Re-solving per request is
what makes people think this "doesn't work".

**The user-agent and the clearance cookie are bound together.** Reusing the cookie with a
different UA invalidates it. Store them as a pair.

### 3.2 Ask the client to allowlist you (fastest and most professional)

For an authorised engagement, the client can add a WAF rule to bypass for your source IP, a
header you send, or a time window.

**This is the correct answer more often than people expect.** It removes the entire problem,
it is legitimate, and it produces a *better* assessment because you are testing the application
rather than the CDN. Ask early — before you spend a day on evasion.

### 3.3 Don't (the wrong answers)

| Approach | Why it fails |
|---|---|
| Rotating proxies + spoofed UAs at high rate | raises the bot score; escalates you from challenge to block |
| Headless browser with default automation flags | `navigator.webdriver` and the automation fingerprint are trivially detected |
| CAPTCHA-solving services | outsources a judgement call you should be making yourself; often outside the engagement terms |
| Firing more requests at the challenge | turns a soft block into a hard block and into a rate limit |

---

## 4. RATE LIMITING — THIS IS PACING, NOT BYPASS

Cloudflare's rate limiting is per-route, per-IP, or per-session, and it will tell you.

| Signal | Response |
|---|---|
| `429` + `Retry-After: N` | **wait N seconds.** The header is an instruction, not a suggestion |
| `cf-ray` + sustained 429s | reduce concurrency to 1 and add a fixed delay |
| 429 only on one path | the limit is route-specific — spread across paths |
| 429 only under authentication | the limit is per-account — slow down far more |

**Compute your rate from the target's limits, not from your patience.** If the header says 10
requests per minute, that is your ceiling. Exceeding it is a denial-of-service against the
client's actual users, who are now also blocked.

**A slower scan that completes beats a fast scan that gets your IP banned and the client's
users rate-limited.** The tradeoff is not close.

---

## 5. FIREWALL RULES (403 / 1020)

A flat 403 with `1020` is a rule decision, not a bot score. Rules key on IP, ASN, country,
user-agent, path, or header.

| Cause | Legitimate fix |
|---|---|
| Your IP or ASN is blocked | client allowlist, or a different authorised egress |
| Your cloud provider's range is blocked wholesale | very common — provider ranges are blocked preemptively |
| Country block | comes from your egress location; the client must allowlist or you must relocate |
| Path block | the path is protected — this may *be* the finding; note it |
| User-agent block | use the UA the client expects (coordinate with them) |

**A 1020 that persists across techniques is usually an infrastructure block, not a technical
one.** No amount of header manipulation fixes an ASN block. Escalate to the client.

---

## 6. TLS AND CONNECTION-LEVEL FAILURES

If the connection resets before any HTTP response, the handshake itself is the signal.

| Signal | Meaning |
|---|---|
| Immediate RST on connect | IP reputation block |
| RST after ClientHello | TLS fingerprint (JA3/JA4) rejection |
| Hang then timeout | TCP-level filtering |
| Works in a browser, not in your tool | **JA3 fingerprint** — your HTTP client's TLS stack is not browser-like |

**A tool that works in `curl` but fails in your scanner (or vice versa) is a fingerprint
difference, not a WAF rule.** Compare JA3 between the working and failing client before doing
anything else.

---

## 7. THE ESCALATION LADDER — USE THE LOWEST RUNG

```
1. Passive sources only        → CT logs, passive DNS, archives. ZERO requests to the target.
                                 Unaffected by any WAF, ever. Exhaust this first.
2. Ask the client to allowlist → removes the problem entirely; best evidence quality.
3. Real browser + cookie reuse → passes managed challenges legitimately.
4. Slow down to the published limit → fixes all rate-limit cases.
5. Change infrastructure       → fixes IP/ASN/country blocks.
6. Payload-level evasion       → waf-bypass-techniques; only when a *payload* is blocked.
7. Never: high-rate rotation   → escalates, impacts availability, and is reportable as an incident.
```

**Rung 1 is dramatically underused.** Certificate transparency and passive DNS give you
subdomains, and historical archives give you content, with **zero packets to the target** — no
WAF involvement at all. If your recon is being blocked, the first question is whether you needed
to make that request in the first place.

**Rung 2 is the one professionals skip out of pride.** Asking the client costs an email. Evading
their own security control costs a day, may breach the engagement terms, and produces weaker
evidence.

---

## 8. WHAT NOT TO DO

| Anti-pattern | Consequence |
|---|---|
| Rotating proxies to defeat rate limits | availability impact on the client's real users; frequently out of scope |
| Solving CAPTCHAs via a third-party service | sends the client's challenge to an unrelated third party; often a terms breach |
| Disabling TLS verification to "make it work" | hides a real certificate finding and is never the fix for a WAF block |
| Firing harder at a challenge | challenge → block → rate limit → under-attack mode |
| Reporting challenge pages as content | silently invalidates the entire recon dataset |
| Treating a CDN as the application | you end up assessing Cloudflare, not the client's app |

**The last one is the most damaging to the deliverable.** If the site is behind a CDN, the
finding "the WAF blocked my payload" says nothing about the application's actual security. Get
behind the edge (rung 2) or assess what the edge exposes and say which you did.

---

## 9. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the exact status code and response body of the block | distinguishes the five §1 failure modes |
| which failure mode you classified it as, and how | shows the diagnosis, not a guess |
| the rung of the §7 ladder you used | proves the response was proportionate |
| **whether the client allowlisted you, and when** | a scope-relevant change in testing conditions |
| the rate you ran at, and the rate the target published | shows pacing discipline |
| whether any real content was retrieved from the target | proves the recon dataset is valid |
| **any availability impact observed (429s, 503s, attack mode)** | this is an incident and must be reported even if minor |

---

## 10. REMEDIATION REFERENCE

1. **WAF in front of everything is the right default** — the blocking is working as designed; the engagement should not treat it as a defect.
2. **Tune challenge vs block by path** — challenging static assets and login pages alike breaks accessibility tools and legitimate automation while barely inconveniencing an attacker.
3. **Rate limits should be per-identity, not per-IP** — per-IP limits punish shared NAT users and are bypassed by rotation; per-account limits scale.
4. **Separate bot management from WAF rules in policy** — conflating them makes both undiagnosable and produces the flat-403 ambiguity in §5.
5. **Allowlist known testing and monitoring ranges** deliberately, with a time bound, rather than discovering them during an engagement.
6. **Monitor for under-attack escalation** — a mode change driven by a single source is a signal; it currently only fires once availability is already affected.
7. **Do not treat the WAF as the application's security control** — parameterised queries, output encoding, and correct authorization are the actual fixes; the WAF is the layer that buys time.

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the **classifier run**, and what was its **verdict** for the request in question? | you must know you were blocked |
| 2 | Is the verdict a **block**, a **challenge**, or **rate limiting**? | three different things, three different reports |
| 3 | Was the SAME request **without** the adjustment also blocked? | the control |
| 4 | Did the adjustment change the **verdict**, or only the **timing**? | pacing is not bypass |
| 5 | Did the **origin** actually receive the request? | the origin saw it, not just Cloudflare |
| 6 | Did the response body come from the **origin**, not from the edge? | an edge page is not origin data |
| 7 | Was any limit **recorded** rather than assumed? | the threshold is the finding |

**The classifier's verdict, with the unmodified request as the control.** "It worked" without a verdict
cannot distinguish a bypass from a request that was never blocked, and that is this family's central error.

---

## 12. EXECUTION PRIMITIVES

This domain is unusual: **the artefact is a classifier verdict, and the finding is a change in that verdict
with everything else held constant**. Every claim here reduces to the verdict before, the verdict after, and
what changed between them.

### 12.1 The classifier, and its verdict

```bash
# THE FIRST SCRIPT (section 1) IS THE FOUNDATION. It must classify EVERY response.
cat > /tmp/cf_classify.sh <<'SH'
#!/usr/bin/env bash
# classify <url> [curl args...]  -> prints a VERDICT line, always
classify() {
  local url="$1"; shift
  local out; out="$(curl -sS -D /tmp/cf_hdr -o /tmp/cf_body -w '%{http_code} %{size_download} %{time_total}' \
                    "$@" "$url" 2>/tmp/cf_err)" || { echo "VERDICT=transport-error detail=$(cat /tmp/cf_err)"; return; }
  local code size time; read -r code size time <<<"$out"
  local server; server="$(grep -i '^server:' /tmp/cf_hdr | tr -d '\r' | cut -d' ' -f2-)"
  local v="UNKNOWN"
  grep -qi 'cf-mitigated: challenge' /tmp/cf_hdr && v="CHALLENGE"
  grep -qi '^cf-ray:' /tmp/cf_hdr && [ "$v" = "UNKNOWN" ] && v="EDGE-RESPONSE"
  case "$code" in
    403) grep -q '1020' /tmp/cf_body && v="BLOCK-1020(firewall-rule)" || v="BLOCK-403" ;;
    429) v="RATE-LIMITED" ;;
    503) v="BLOCK-503(edge)" ;;
    200) grep -qi '^cf-ray:' /tmp/cf_hdr || v="ORIGIN-200(NO-CF-RAY)"; [ "$v" = "UNKNOWN" ] && v="ORIGIN-200" ;;
  esac
  echo "VERDICT=$v code=$code size=$size time=$time server=$server"
}
classify "$@"
SH
chmod +x /tmp/cf_classify.sh
echo "  USAGE: /tmp/cf_classify.sh https://target.example/path"
echo "  THE VERDICT IS THE ARTEFACT. 'curl returned 200' is not a verdict: it may be an edge page."
echo
echo "=== THE VERDICTS, and what each one MEANS ==="
python3 - <<'PY'
V = [("BLOCK-403",            "a firewall rule matched; if the body contains 1020 it is a custom rule", "the rule's existence"),
     ("BLOCK-1020",           "a Cloudflare firewall rule by ID; the ID is quoted in the body",       "the specific rule"),
     ("CHALLENGE",            "a managed challenge or a JS challenge was served",                     "not a block; a challenge"),
     ("RATE-LIMITED",         "a rate-limit rule matched; the timing is the variable",                "pacing, NOT a bypass"),
     ("BLOCK-503(edge)",      "an edge-level block, often under a DDoS or security-level action",      "an origin-protection control"),
     ("ORIGIN-200",           "the request REACHED the origin and it replied",                         "the origin saw it"),
     ("ORIGIN-200(NO-CF-RAY)","no CF-Ray header: THE REQUEST LIKELY DID NOT GO THROUGH CLOUDFLARE",    "NOT a bypass - a DIFFERENT ROUTE"),
     ("transport-error",      "no HTTP layer at all: TLS, connection, or DNS",                         "a lower-layer failure")]
print("%-24s %-58s %s" % ("verdict","meaning","what it evidences"))
for a,b,c in V: print("%-24s %-58s %s" % (a,b,c))
print()
print("  THE MOST IMPORTANT LINE ABOVE IS ORIGIN-200(NO-CF-RAY): a direct-to-origin hit is NOT a WAF")
print("  bypass. It is a SEPARATE FINDING about the origin's exposure, and the two must not be merged.")
PY
```

**The verdict is the artefact, and `ORIGIN-200(NO-CF-RAY)` is not a WAF bypass — it is a separate origin-exposure
finding.** `curl returned 200` may just be an edge page.

### 12.2 The control, which is the unmodified request

```bash
echo "=== THE CONTROL: THE SAME REQUEST WITHOUT THE ADJUSTMENT ==="
cat <<'CONTROL'
  EVERY claim in this domain needs THIS PAIR:
    A. the UNMODIFIED request   -> the verdict, e.g. BLOCK-403
    B. the ADJUSTED request     -> the verdict, e.g. ORIGIN-200
  AND NOTHING ELSE MAY DIFFER: same URL, same method, same body, same headers except the one
  variable under test, same source, and CLOSE IN TIME (a security-level or a rule may change).

  WITHOUT PAIR A YOU HAVE NOTHING. 'It worked with a different User-Agent' is uninterpretable,
  because the original request may never have been blocked at all.

  AND RUN THE PAIR THREE TIMES EACH: Cloudflare's decisions are partly stateful (the IP's reputation,
  the current security level, the rate-limit counters). A verdict that flaps is NOT a bypass; it is
  an unstable classifier, and THAT is the finding.
CONTROL
echo
echo "=== THE ONE-VARIABLE DISCIPLINE, mechanically enforced ==="
echo "  record the FULL request, both times, and the DIFF between them:"
echo "    curl -sS -o /dev/null -D - 'https://target.example/p' | tee /tmp/a.hdr"
echo "    curl -sS -o /dev/null -D - -A 'Mozilla/5.0 ...' 'https://target.example/p' | tee /tmp/b.hdr"
echo "    diff <(sort /tmp/a.hdr) <(sort /tmp/b.hdr)   <- the ONLY differences must be your variable"
echo "  and the VERDICT for each must be recorded SIDE BY SIDE, in the report, as a table."
echo
echo "=== THE RATE-LIMIT MEASUREMENT (section 4), which is a measurement not a bypass ==="
python3 - <<'PY'
import urllib.request, time
url = "https://target.example/path"
N   = 30
print(f"  measuring N={N} sequential requests; recording code + latency for each")
print("  the THRESHOLD IS WHERE THE CODE CHANGES, and the WINDOW is how long the block lasts.")
for i in range(1, N+1):
    t0 = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"rate-probe"}), timeout=10)
        code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = f"ERR {type(e).__name__}"
    print(f"    request {i:3}  -> {code}   {time.time()-t0:.3f}s")
print()
print("  INTERPRET THE RESULT CORRECTLY:")
print("    a transition at request K        -> the limit is K (approximately) per window")
print("    a sustained block                -> you are still inside the window; MEASURE its length")
print("    alternating codes                -> a per-second or token-bucket limit, not a fixed count")
print("    NO transition at N               -> you did not reach the limit; RAISE N, do not claim a bypass")
print("  THIS IS PACING. Slow the requests and the SAME requests succeed: that proves NOTHING about")
print("  the rules - it proves the limit's shape. LABEL IT AS PACING IN THE REPORT, ALWAYS.")
PY
```

**Pacing is not a bypass: slowing the requests and having the same requests succeed proves only the limit's
shape.** And the pair must be run three times each, because a verdict that flaps is an unstable classifier
rather than a bypass.

### 12.3 The challenge, the edge, and the origin

```bash
echo "=== THE JS CHALLENGE (section 3), and the ONLY honest answer ==="
cat <<'CHALLENGE'
  A MANAGED CHALLENGE IS NOT A BLOCK, AND SOLVING IT IS NOT A BYPASS IN THE SENSE THIS DOMAIN CLAIMS.
  What is legitimately reportable:
    - the challenge's TYPE (managed, interactive, JS, Turnstile) and how it was identified
    - whether a REAL browser (section 7's escalation ladder, the browser rung) obtained a clearance
      cookie, and WHAT THAT COOKIE GRANTS (a token, scoped how, valid for how long)
    - WHETHER the clearance is REUSED for the requests of interest, with the verdict recorded
  WHAT IS NOT REPORTABLE AS A BYPASS:
    - 'we solved the challenge'  -> the challenge WORKED. The control did its job.
    - 'the challenge is bypassable' without the clearance, the scope, and its lifetime
  THE FINDING, WHEN THERE IS ONE, IS USUALLY ABOUT SCOPE: a clearance issued for one path and
  accepted on another, or a clearance that outlives its intended session, or a clearance that is
  not bound to the client. THAT is a control weakness, and it is provable.
CHALLENGE
echo
echo "=== THE ESCALATION LADDER (section 7), and the rung you used ==="
echo "  record which RUNG: user-agent, header, TLS fingerprint, HTTP/2 fingerprint, pacing,"
echo "  residential proxy, a real browser. THE LOWEST RUNG THAT WORKS IS THE FINDING, because a"
echo "  higher rung implies a weaker control and a DIFFERENT remediation."
echo
echo "=== THE ORIGIN CHECK, which separates a WAF finding from an origin-exposure finding ==="
cat <<'ORIGIN'
  THE QUESTION: DID THE REQUEST ACTUALLY REACH THE ORIGIN, AND DID THE ORIGIN ANSWER?
  the checks:
    1. cf-ray present      -> it went through Cloudflare. ABSENT -> it did NOT (a different route).
    2. the response BODY  -> an edge page (a block page, a challenge page) vs the ORIGIN'S OWN content.
       the giveaway: a block page has Cloudflare's markup and often a ray ID in the body; the
       origin's page has the application's markup. READ THE BODY, do not trust the status code.
    3. a marker you controlled: request a path you know the ORIGIN serves uniquely, and confirm
       that content - or a cache-busting query, and check the caching behaviour.
  IF THE REQUEST DID NOT GO THROUGH CLOUDFLARE AT ALL, it is an ORIGIN-EXPOSURE finding
  (a DNS record pointing directly at the origin, an alternative hostname, a non-proxied subdomain),
  and reporting it as a 'WAF bypass' is WRONG. The control was never engaged.
ORIGIN
echo
echo "=== the cache-status reading, which distinguishes an edge answer from an origin answer ==="
echo "  curl -sS -D - 'https://target.example/p' | grep -iE '^(cf-cache-status|age|cf-ray|server):'"
echo "    cf-cache-status: HIT   -> the EDGE served it; the origin was NOT consulted"
echo "    cf-cache-status: MISS  -> the edge forwarded; the origin answered (confirm the body)"
echo "    cf-cache-status: DYNAMIC -> not cached; the origin answered"
echo "  a cached HIT is NOT evidence the origin was reached - and this is a common misreading."
```

**A managed challenge doing its job is the control working, not a bypass** — the reportable finding is
usually about clearance scope. And a cached `HIT` is not evidence the origin was reached.

### 12.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== CLOUDFLARE WAF / RECON ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the CLASSIFIER script ran and produced a VERDICT for every request reported",
  "'curl returned 200' is not a verdict; it may be an edge page"),
 ("the verdict is classified as BLOCK, CHALLENGE, or RATE-LIMITED, and named as such",
  "three different things with three different reports"),
 ("the CONTROL was run: the same request WITHOUT the adjustment, and its verdict recorded",
  "without the pair, the adjustment is uninterpretable"),
 ("the pair differed in EXACTLY THE ONE VARIABLE, and the header diff is recorded",
  "two changes prove nothing about either"),
 ("the pair was run THREE TIMES each, and any flapping is itself reported",
  "a flapping verdict is an unstable classifier, not a bypass"),
 ("for rate limiting: the THRESHOLD and the WINDOW were MEASURED, and it is labelled PACING",
  "slowing the requests and succeeding proves the limit's shape, not the rules"),
 ("no transition was observed => N was raised, NOT a bypass claimed",
  "the limit was simply not reached"),
 ("for a challenge: the TYPE is recorded, and a clearance's SCOPE and LIFETIME are the finding",
  "solving a challenge is the control working"),
 ("the ESCALATION RUNG used is recorded, and the lowest working rung is the finding",
  "a higher rung implies a weaker control and a different remediation"),
 ("cf-ray presence/absence is recorded for the decisive request",
  "absent cf-ray means the request did not go through Cloudflare"),
 ("the RESPONSE BODY was read to distinguish an edge page from the origin's own content",
  "a status code does not say who answered"),
 ("cf-cache-status was read: a HIT is not proof the origin was reached",
  "a cached answer never consulted the origin"),
 ("if the request did not traverse Cloudflare, it is reported as ORIGIN EXPOSURE, not a WAF bypass",
  "the control was never engaged; the two findings differ"),
 ("the TLS/connection failures (section 6) are classified as transport, not as blocks",
  "a handshake failure is not a rule"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  request  : the full request, and the one variable changed")
print("  verdicts : the control's verdict and the adjusted verdict, side by side, three runs each")
print("  class    : BLOCK / CHALLENGE / RATE-LIMITED / ORIGIN-EXPOSURE, named explicitly")
print("  measurement: the rate limit's threshold and window, if relevant (labelled PACING)")
print("  rung     : the lowest escalation rung that worked")
print("  origin   : cf-ray, cf-cache-status, and the body's provenance")
PY
```

**The verdict pair with one variable, run three times, classed explicitly, with the origin's provenance.**
Without the control the adjustment means nothing.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) - the same boundary logic, at the internal segment
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) - the callback an edge may or may not permit
- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) - how a request may reach an origin by another route
- [recon-methodology](../recon-methodology/SKILL.md) - the enumeration this domain's classifier feeds
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a verdict table is reported
