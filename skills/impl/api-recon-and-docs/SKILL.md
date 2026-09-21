---
name: api-recon-and-docs
description: >-
  API reconnaissance and documentation review playbook. Use first when the target is a
  REST, mobile, or GraphQL API. Covers endpoint enumeration, JS and source-map mining,
  spec and version drift, shadow and internal API discovery, parameter harvesting from
  documentation, and the inventory artefact that makes authorization testing tractable.
---

# SKILL: API Recon and Docs — Endpoints, Schemas, and Version Surface

> **AI LOAD INSTRUCTION**: API recon has one purpose: **produce a complete, deduplicated
> inventory of endpoints, methods, parameters, and versions** before a single exploit is
> attempted. Authorization bugs are per-endpoint; if your inventory is missing an endpoint,
> every downstream test is blind to it. The two highest-yield sources are almost never the
> documented ones — they are **JavaScript bundles** and **older API versions still live**.
> Budget your time accordingly: an hour of inventory beats an hour of guessing paths.

## 0. RELATED ROUTING

- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — the primary consumer of this inventory
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) — when a GraphQL endpoint appears
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — token surfaces found during recon
- [recon-and-methodology](../recon-and-methodology/SKILL.md) — the broader host and service layer
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) — when repos or source maps leak
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — how the inventory is recorded

---

## 1. THE INVENTORY — WHAT YOU ARE BUILDING

A single table. Every row is a testable unit; the row count is your coverage denominator.

| Field | Example | Why it matters downstream |
|---|---|---|
| host | `api.target.com` | different hosts have different middleware |
| base path | `/api/v2/` | version drift is a top finding source |
| method | `GET` `POST` `PUT` `DELETE` | authz is often per-verb |
| route | `/users/{id}` | the object surface |
| parameters | `id`, `role`, `org_id` | mass-assignment candidates |
| auth required | yes / no / optional | finds unauthenticated surface |
| role required | user / admin / none | the authz baseline |
| source | JS bundle / spec / mobile / guess | provenance tells you the reliability |
| status | live / deprecated / dead | deprecated-but-live is high value |

**Parameter column is the one testers omit and later need most.** Fill it while you have the
request in front of you; reconstructing it later means re-running the whole recon.

---

## 2. JAVASCRIPT BUNDLE MINING — THE HIGHEST-YIELD SOURCE

Modern SPAs contain the entire client-side API contract. This is not guessing; it is reading.

**Route extraction:**

```bash
curl -s https://target/static/app.js | grep -oE '["'\''](/api|/rest|/v[0-9]|/graphql|/gql)[^"'\'' ]*' | sort -u
curl -s https://target/static/app.js | grep -oE '(get|post|put|delete|patch)\(["'\''`][^"'\''`]+' | sort -u
```

**Framework-aware extraction** — the patterns differ, so match the framework:

| Framework | Pattern to grep |
|---|---|
| Axios | `axios.get(`, `axios.post(`, `baseURL:` |
| fetch | `fetch("`, backtick template strings |
| Angular | `HttpClient`, environment files |
| React Query | `queryKey:`, `mutationFn` |
| OpenAPI-generated clients | `operationId`, generated method names |
| GraphQL clients | full `query` / `mutation` strings |

**Template literals are where the object IDs hide** — the recon value is not just the path but
the substitution:

```javascript
`/api/v1/orders/${orderId}/items/${itemId}`   →  two object surfaces, one route
```

**Source maps are the jackpot.** A deployed `.map` file returns original source:

```bash
curl -sI https://target/static/app.js.map            # check existence first
curl -s https://target/static/app.js.map | jq -r '.sources[]' | head -50
curl -s https://target/static/app.js.map | jq -r '.sourcesContent[]?' | grep -iE 'api|endpoint|secret|token' | head -40
```

Source maps frequently retain **internal-only comments**, **staging hostnames**, and
**API keys inlined at build time**. Treat a reachable `.map` as a finding in itself —
see [insecure-source-code-management](../insecure-source-code-management/SKILL.md).

**Also harvest:** HTML comments, inline `<script>` blocks, `robots.txt`, `sitemap.xml`,
service worker manifests (`sw.js` caches API routes), and `manifest.json`.

---

## 3. DOCUMENTATION AND SPEC DISCOVERY

Specs are the densest recon source when present, and their *absence* is informative too.

**Canonical spec paths:**

```text
/swagger.json        /swagger/v1/swagger.json    /swagger-ui.html
/openapi.json        /openapi.yaml               /openapi/v3/api-docs
/api-docs            /api-docs.json              /v2/api-docs
/docs                /redoc                     /docs/openapi.json
/.well-known/openapi.json
```

**Framework-specific giveaways:**

| Signal | Framework | Spec location |
|---|---|---|
| `/v2/api-docs` | Springfox / Spring Boot | often unauthenticated by default |
| `/swagger-ui/index.html` | Springdoc | spec at `/v3/api-docs` |
| `/api/schema/` | Django REST Framework | browsable API |
| `?format=api` | DRF | alternate representation |
| `/graphiql` | GraphQL | interactive console |

**What to extract, in priority order:**

1. **Every path and method** — the raw inventory.
2. **`additionalProperties: true`** — the spec telling you extra fields are accepted.
3. **Optional and undocumented fields** — mass assignment candidates.
4. **Admin-only examples** — request bodies you were never meant to see.
5. **Deprecated endpoints** — often still routed and unmaintained.
6. **Parameter names** — especially tenancy, role, filter, and sort keys.
7. **Security definitions** — which endpoints declare auth and, more usefully, which do not.

**The highest-value extraction is the diff.** Fetch the spec twice — once unauthenticated,
once as a low-privilege user. Endpoints appearing in only one view reveal both
unauthenticated surface and role-gated surface in a single step.

---

## 4. VERSION AND PRODUCT DRIFT

**The single most reliable API finding: an old version still serving requests.**

```text
/api/v1/     /api/v2/      /api/v3/
/api/beta/   /api/alpha/   /api/legacy/   /api/internal/
/api/mobile/v1/   /api/app/v1/   /api/partner/v1/
/v1/   /v2/   /v0/   /v0.1/
```

**Why old versions are high-value:** they predate the authorization fix. A BOLA patched in
`/api/v2/` is frequently still live in `/api/v1/`.

**Test the same object across every version you find**, with two accounts. This is a mechanical
check that produces critical findings regularly:

```bash
for v in v1 v2 v3 beta legacy; do
  curl -s -o /dev/null -w "$v %{http_code}\n" \
    -H "Authorization: Bearer $TOKEN_B" "https://target/api/$v/orders/$A_ORDER_ID"
done
```

**Other drift signals:**

| Signal | Test |
|---|---|
| `X-Api-Version` header | send `1`, `2`, `legacy`, and an empty value |
| `Accept: application/vnd.api+json;version=1` | media-type versioning bypasses path routing |
| subdomain versioning | `api-v1.`, `api-old.`, `beta-api.` |
| mobile clients | hit a different, often less-hardened deployment |
| BFF / gateway paths | `/bff/`, `/gateway/`, `/edge/` route to backends |

**Absent version preflight is itself a finding** — an API that ignores the version header
rather than rejecting it is silently serving the default version regardless of client intent.

---

## 5. SHADOW AND INTERNAL API DISCOVERY

Endpoints that exist but appear in no documentation and no UI. Common origins: internal
tooling promoted to production, microservices exposed through a gateway, and debug routes.

| Technique | Detail |
|---|---|
| admin-route mirroring | derive `/api/admin/*` from known `/api/*` routes |
| pluralisation and casing | `/user` ↔ `/users`, `/User`, `/USER` |
| noun guessing | `/internal/`, `/debug/`, `/test/`, `/staging/`, `/private/` |
| Kubernetes / cloud metadata naming | `/health`, `/metrics`, `/actuator/*` |
| gateway path leakage | error messages naming the upstream service |
| CORS misconfiguration | `Access-Control-Allow-Origin` on a guessable path |
| SSL SAN entries | certificate transparency logs list sibling hosts |
| mobile APK strings | the mobile API surface |

**Spring Boot Actuator deserves a dedicated check** — it exposes environment variables,
heap dumps, and route maps when unsecured:

```text
/actuator          /actuator/env       /actuator/health
/actuator/mappings /actuator/beans     /actuator/heapdump
/actuator/configprops  /actuator/httptrace
```

`/actuator/mappings` is a **complete route inventory** — it is the recon goal delivered by
the target itself. `/actuator/env` frequently leaks credentials.

---

## 6. PARAMETER HARVESTING

Parameters define the attack surface. Collect them from every source and merge into the
inventory table.

| Source | Yield |
|---|---|
| spec request bodies | complete, typed, authoritative |
| JS bundle call sites | real values including defaults |
| GraphQL type definitions | every field is an argument |
| admin requests vs user requests | **the mass-assignment diff** |
| error messages | expected field names |
| mobile bundle | tenancy and feature-flag fields |
| OpenAPI examples | admin-only shapes |
| Postman / Insomnia collections in public repos | real-world usage |

**Priority parameter classes to hunt for explicitly:**

```text
identity:    id user_id owner_id account_id member_id created_by
tenancy:     org_id tenant_id workspace_id team_id company_id
privilege:   role roles is_admin admin permission permissions scope
state:       verified approved active enabled status tier plan
commerce:    price amount discount currency credits balance quantity
process:     debug test preview bypass internal legacy feature_flag
```

**Merge duplicates by route.** The same endpoint discovered from three sources must collapse
to one row with a union of parameters — a parameter found in the mobile bundle but missing
from the spec is precisely the one worth testing.

---

## 7. EVIDENCE STANDARD

Recon produces an artefact, not a finding. What you must be able to show:

| Item | Why |
|---|---|
| the inventory table with provenance per row | proves coverage; shows which sources were mined |
| endpoint count per host and per version | the coverage denominator for later testing |
| specs obtained, and any spec path requiring no auth | unauthenticated spec exposure is itself reportable |
| source maps reachable, with the URL | a standalone finding |
| version drift matrix (route × version × status) | directly evidences the "old version live" finding |
| unauthenticated endpoints discovered | surface reduction is an immediate finding |
| admin/internal routes found and how | proves discovery method, not guessing |
| parameters list per route | the input to mass-assignment and authz testing |

**When recon produces a finding directly**, report it on its own terms — unauthenticated spec
exposure, reachable source maps, and exposed actuator endpoints are all findings with no
further exploitation required.

**State your coverage honestly.** "Enumerated 412 endpoints from JS bundle, OpenAPI spec, and
mobile APK; versions v1–v3 live; v1 lacks the v2 authorization fix" is a usable result. "Tested
the API" is not.

---

## 8. REMEDIATION REFERENCE

1. **Do not serve API specs in production** — or serve them only behind authentication. OpenAPI and Swagger UI are development artefacts.
2. **Disable source maps in production builds** — set the build to omit `.map` emission; a reachable map is equivalent to leaking source.
3. **Retire old API versions on a schedule** — deprecate, then *return 410 Gone*. A route that still resolves is a route that still has its old bugs.
4. **Reject unknown API version headers** — fail closed on `X-Api-Version` or media-type versioning rather than falling through to a default.
5. **Secure management endpoints** — bind `/actuator/*`, `/metrics`, and `/health` to an internal interface or require authentication; exclude `env`, `heapdump`, and `mappings` from production entirely.
6. **Keep one internal route registry** — the gateway or service mesh should hold an authoritative route list and alert when a route is publicly reachable but absent from that list.
7. **Emit no route information in errors** — 404 and 500 bodies must not name upstream services, frameworks, or internal paths.
8. **Audit legacy and shadow surfaces continuously** — the endpoints that matter are the ones nobody remembers deploying.

---

## 9. EXECUTION PRIMITIVES

API recon produces an **inventory with a source for every entry**. An endpoint list without provenance
is a guess, and a guessed endpoint produces a hallucinated finding.

### 9.1 Harvest the JavaScript bundles and extract endpoints

```bash
T="https://target.tld"
# 1) collect every script the app loads
curl -sS "$T/" -o /tmp/index.html
grep -oE 'src="[^"]+\.js[^"]*"' /tmp/index.html | sed 's/src="//;s/"$//' | sort -u > /tmp/js.txt
# include the next.js / modern manifest forms
grep -oE '/_next/static/[^"]+\.js|/assets/[^"]+\.js|/static/js/[^"]+\.js' /tmp/index.html | sort -u >> /tmp/js.txt
sort -u /tmp/js.txt -o /tmp/js.txt; wc -l < /tmp/js.txt
mkdir -p /tmp/bundles
while read -r U; do
  case "$U" in http*) F="/tmp/bundles/$(echo "$U" | md5sum | cut -c1-10).js";; *) F="/tmp/bundles/$(echo "$U" | tr '/' '_')";; esac
  curl -sS "$T$U" -o "$F" 2>/dev/null || curl -sS "$U" -o "$F" 2>/dev/null
done < /tmp/js.txt
ls -la /tmp/bundles | head -5
```

Fetch every bundle, not just the ones the landing page loads - **lazy-loaded route chunks contain the
interesting endpoints**. A bundle you never fetched is an endpoint you will never find.

### 9.2 Extract paths, parameters, and methods from the bundles

```bash
# path-like strings
grep -hoE '"/[a-zA-Z0-9_./{}:$-]{2,60}"' /tmp/bundles/* 2>/dev/null | tr -d '"' | sort -u > /tmp/paths.txt
# versioned API roots, which are the highest-signal paths
grep -hoE '/(api|v[0-9]+|rest|graphql|internal|admin|_next)/[a-zA-Z0-9_./{}:$-]{0,60}' /tmp/bundles/* 2>/dev/null | sort -u > /tmp/api.txt
# template literals and concatenations reveal parameters the literal form hides
grep -hoE '`[^`]{0,80}(\$\{[^}]+\})[^`]{0,80}`' /tmp/bundles/* 2>/dev/null | sort -u | head -30 > /tmp/template.txt
# query parameter names
grep -hoE '[?&][a-zA-Z_][a-zA-Z0-9_]{1,30}=' /tmp/bundles/* 2>/dev/null | tr -d '?&=' | sort -u > /tmp/params.txt
wc -l /tmp/paths.txt /tmp/api.txt /tmp/params.txt
head -20 /tmp/api.txt
```

**Template literals are where the parameters live** - a literal `"/api/users/1"` in a bundle is a known
endpoint, but `` `/api/users/${id}` `` tells you the identifier position. Extract both forms.

### 9.3 Source maps, when they are exposed

```bash
# a source map turns a minified bundle back into readable source, including comments and route tables
for B in $(ls /tmp/bundles | head -20); do
  U=$(grep -F "$B" /tmp/js.txt | head -1)   # adjust if your naming differs
  for SM in "$T$U.map" "${U%.js}.js.map"; do
    C=$(curl -sS -o /tmp/sm -w '%{http_code}' "$SM")
    [ "$C" = "200" ] && echo "SOURCE MAP: $SM ($(wc -c < /tmp/sm) bytes)" && cp /tmp/sm "/tmp/bundles/$B.map"
  done
done
ls /tmp/bundles/*.map 2>/dev/null | wc -l
```

A source map is an **information disclosure in its own right** and often exposes internal route names,
comments, and feature flags. Decode one and search it for route definitions and TODO comments.

### 9.4 Documentation and specification discovery

```bash
for P in /openapi.json /openapi.yaml /swagger.json /swagger.yaml /api-docs /api-docs.json \
         /v2/api-docs /v3/api-docs /swagger-ui.html /swagger-ui/ /redoc /docs /api/docs \
         /graphql /graphiql /.well-known/openapi.json /api/v1/openapi.json ; do
  R=$(curl -sS -o /tmp/d -w '%{http_code} %{size_download} %{content_type}' "$T$P")
  printf '%-32s %s\n' "$P" "$R"
  case "$R" in 200*) cp /tmp/d "/tmp/spec-$(echo "$P" | tr '/' '_')";; esac
done
ls -la /tmp/spec-* 2>/dev/null
```

A found specification is the **best possible inventory**, because it is authoritative. Parse it rather
than grepping it:

```bash
python3 - <<'PY'
import json,glob
for f in glob.glob('/tmp/spec-*'):
    try: d=json.load(open(f))
    except Exception: continue
    paths=d.get('paths',{})
    print(f, "paths:", len(paths))
    for p,ops in list(paths.items())[:40]:
        for m in ops:
            if m in {'get','post','put','patch','delete','head','options'}:
                print(f"  {m.upper():7} {p}")
PY
```

### 9.5 Version and shadow API discovery

```bash
# version roots and shadow deployments
for V in v1 v2 v3 v4 beta alpha internal private legacy dev test staging uat; do
  for R in "/api/$V" "/$V/api" "/$V" ; do
    C=$(curl -sS -o /dev/null -w '%{http_code}' "$T$R/")
    [ "$C" != "404" ] && printf '%-24s %s\n' "$R" "$C"
  done
done
# and the same path on the alternate hosts the DNS and certificates reveal
for H in api-api.target.tld api.target.tld api-dev.target.tld api-staging.target.tld \
         api-internal.target.tld internal.target.tld admin.target.tld ; do
  C=$(curl -sS -o /dev/null -w '%{http_code}' -k "https://$H/" 2>/dev/null)
  [ -n "$C" ] && printf '%-34s %s\n' "$H" "$C"
done
```

An old version root that still responds is the highest-yield finding in this domain: **it is an
API without the fixes applied to the current one**. Test the deprecated path against the same
vulnerability classes you test the current one.

### 9.6 Verify every endpoint you intend to report

```bash
# a probe function that records the evidence for each candidate
probe() { curl -sS -o /tmp/pr -w '%{http_code} %{size_download} %{content_type}' "$@" ; }
while read -r P; do
  case "$P" in *'${'*|*'{}'*) continue;; esac      # skip template placeholders
  R=$(probe "$T$P")
  printf '%-46s %s\n' "$P" "$R"
done < /tmp/api.txt | sort -u
# and the method on a known-good endpoint, since some only answer to POST
curl -sS -o /dev/null -w 'OPTIONS %{http_code}\n' -X OPTIONS "$T/api/users"
curl -sS -D- -o /dev/null -X OPTIONS "$T/api/users" | grep -i '^allow'
```

**Every entry in the inventory needs a live status code and a size.** An endpoint that 404s is not in
the inventory, and an endpoint you extracted but never requested is not evidence.

### 9.7 Harvest parameters from behaviour, not just text

```bash
# if the app uses a validation library, unknown parameters often produce a distinct error
curl -sS -o /tmp/pp -w 'baseline %{http_code} %{size_download}\n' "$T/api/search?q=test"
for P in limit offset page per_page sort order filter fields expand include embed select q all debug \$top \$skip; do
  R=$(curl -sS -o /tmp/pp2 -w '%{http_code} %{size_download}' "$T/api/search?q=test&$P=1")
  D=$(diff <(head -c 200 /tmp/pp) <(head -c 200 /tmp/pp2) >/dev/null && echo same || echo DIFF)
  printf '%-14s %s %s\n' "$P" "$R" "$D"
done
```

A parameter that **changes the response size or triggers a validation error** is a real parameter. This
is how you find undocumented filters, pagination controls, and expansion parameters that the
documentation omits.

### 9.8 Build the inventory as a file, with provenance

```bash
# one row per endpoint: method, path, source, status, size, auth-required
{
  echo "method,path,source,status,size,auth"
  while read -r P; do
    [ -z "$P" ] && continue
    R=$(curl -sS -o /tmp/i -w '%{http_code},%{size_download}' -H "Authorization: Bearer $TOK" "$T$P")
    R2=$(curl -sS -o /dev/null -w '%{http_code}' "$T$P")
    echo "GET,$P,js-bundle,$R,$([ "${R%%,*}" != "$R2" ] && echo yes || echo no)"
  done < /tmp/api.txt
} > /tmp/inventory.csv
wc -l < /tmp/inventory.csv; head -8 /tmp/inventory.csv
```

**The provenance column is what makes the inventory trustworthy.** A path with a source (bundle,
spec, historical request, DNS) can be reproduced by the reader; a path with no source is a guess.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the endpoint **actually respond** - live status and a body? | it exists, rather than being a string in a bundle |
| 2 | Is there **documentation, a bundle reference, or a historical request** that names it? | provenance, so the reader can reproduce |
| 3 | Does it require **authentication**, and at what level? | scope and impact |
| 4 | Is it a **shadow or deprecated version** that responds while the current one does not? | the highest-value finding in this domain |
| 5 | Are the **parameters** confirmed by a behaviour change, not just inferred? | the input surface |
| 6 | Does the response **confirm the data model** (fields, identifiers)? | establishes what the endpoint is for |
| 7 | Is the discovery itself an **exposure** (a public spec or source map)? | a finding in its own right |

**A live, sourced endpoint is the unit of evidence.** Everything downstream depends on this; an
inventory entry that does not respond is a fabrication risk, not a lead.

---

## 11. EVIDENCE STANDARD — SOURCED INVENTORY

| Item | Why |
|---|---|
| The **endpoint inventory** with method, path, and **provenance for each entry** | reproducibility; an unsourced path is a guess |
| The **raw source** for each discovery - the bundle, the spec, or the request that named it | the reader must be able to verify |
| The **live response** for each endpoint you report on, with status and size | existence |
| The **specification file** where one exists, with its location and access level | authoritative, and its exposure is itself a finding |
| The **authentication requirement** for each endpoint, established by an unauthenticated and an authenticated request | scope |
| The **shadow or deprecated endpoints** that respond, with the difference from the current one | the impact |
| The **parameter set** per endpoint, with the observation that confirmed each parameter | the input surface |
| **Negative control** - a path that does 404, showing the endpoint set is not a catch-all | rules out a wildcard route |
| The **harvesting method** (a reproducible command or script) | the inventory can be regenerated |
| A statement that no **exploitation** was performed - this phase is discovery | scope discipline |

Report the **inventory with provenance and the live endpoints**: "the bundle
`/static/js/app.4f2a1c.js` references `/api/internal/users/export`, `/api/v2/orders` and
`/api/graphql`; `/api/v2/orders` returns `200` with 4,120 bytes while the documented `/api/v3/orders`
requires an elevated scope; `/openapi.json` is publicly readable and documents 84 paths, 11 of which
are absent from the developer documentation", never "the API has many undocumented endpoints".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A path extracted from a bundle that returns `404` | it is not deployed |
| A route that only exists in the front-end router | no server-side endpoint |
| A documented public endpoint | not shadow or undocumented |
| A generic handler that returns `200` for every path | no distinct endpoint |
| A deprecated endpoint that requires the same authorization as the current one | no additional exposure |
| A parameter inferred from a variable name with no behavioural change | unconfirmed |
| A source map on an intentionally public CDN asset with no sensitive content | not an exposure |
| An internal hostname from a certificate with no responding service | not reachable |
| An endpoint you found but never requested | not evidence |
| A path in a third-party library's bundle | not the target's endpoint |
| A specification file behind authentication | not publicly exposed |
| A discovery with no provenance | unreproducible |

**Sourced and live.** Both conditions are required before an endpoint enters the inventory you report.

---

## 12. REMEDIATION REFERENCE — DISCLOSURE REDUCTION

1. **Do not ship internal endpoint references to unauthenticated bundles** - the primary disclosure is the front-end build, so split internal and public API clients and keep the internal one server-side.
2. **Disable source maps in production** - a source map returns readable source and comments, and disabling the build flag is a one-line change.
3. **Require authentication for API specifications** - a public OpenAPI document is a complete attack map; serve it to authenticated developers only.
4. **Enforce the same authorization on every API version** - shadow and deprecated versions are the highest-yield recon finding, so retire old versions and apply policy uniformly.
5. **Decommission deprecated versions rather than leaving them running** - an old version that still responds is an API without the last two years of fixes.
6. **Return `404` consistently for unknown paths and unknown parameters** - a distinct error for an unknown parameter confirms it exists, which is parameter-discovery-as-a-service.
7. **Do not leak internal hostnames through certificates or DNS** - internal names in a public certificate transparently reveal the internal topology and give an attacker their first SSRF target.
8. **Keep an authoritative, reviewed inventory of your own endpoints** - you cannot protect or version what you have not enumerated, and the attacker's inventory will be better than yours otherwise.
9. **Log and alert on requests to internal-only paths from external clients** - a request to `/api/internal/...` arriving at the edge is high-signal and cheap to detect.
10. **Rate-limit and monitor enumeration patterns** - systematic path probing is distinguishable from normal traffic, and the pattern is a useful early warning.
11. **Re-run the bundle scan in CI on every build** - it detects an accidental inclusion of an internal client or a source map at the moment it is introduced rather than after disclosure.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the testing this inventory enables
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) - the GraphQL half of the same discovery work
- [recon-and-methodology](../recon-and-methodology/SKILL.md) - the broader enumeration methodology
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) - the exposure class a leaked spec or source map represents
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) - the authentication layer the inventory scopes against
