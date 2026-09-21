---
name: c2-infrastructure-and-channel-design
description: >-
  Command-and-control infrastructure design, channel selection, and operational security. Use
  when planning or reviewing post-exploitation infrastructure for an authorised engagement.
  Covers channel tradeoffs, redirector design, host-based OPSEC, and the detection surface.
---

# SKILL: C2 Infrastructure & Channel Design

> **AI LOAD INSTRUCTION**: C2 design is a tradeoff problem, not a tooling problem. Every channel
> buys resilience at a cost in latency, bandwith, and detection surface. This skill covers the
> **decision framework** — which channel for which environment, how to structure the
> infrastructure, and what the defender sees. Use only within written authorisation: C2
> infrastructure is indistinguishable from criminal infrastructure at the network layer, and
> the difference is entirely documentary.

## 0. RELATED ROUTING

- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) — the payload layer
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) — the defender's view on the wire
- [c2-frameworks-command-control](../../core-subjects/c2-frameworks-command-control.md) — doctrine
- [c2-opsec](../../core-subjects/c2-opsec.md) — operational security doctrine
- [malware-development-pipeline](../../core-subjects/malware-development-pipeline.md) — implant construction doctrine
- [reporting-and-verification](../../core-subjects/reporting-and-verification.md) — documenting infrastructure

---

## 1. CHANNEL SELECTION

Choose by **what the environment permits**, not by what is fashionable. The channel must blend
with the target network's normal traffic profile.

| Channel | Resilience | Bandwidth | Detection surface |
|---|---|---|---|
| **HTTPS to a domain you own** | low — one domain to burn | high | TLS SNI, certificate, JA3, domain reputation |
| **HTTPS to a popular cloud/CDN** | high — riding a trusted domain | high | domain fronting is largely dead; **malleable profiles** replace it |
| **Domain fronting / SNI mismatch** | was high, now mostly blocked at major CDNs | high | CDN-side blocking |
| **WebSocket / long-lived HTTP** | medium | high, interactive | long-duration connections are anomalous |
| **DNS TXT tunneling** | high — DNS is almost always permitted | very low | request volume, entropy in labels, TXT record abuse |
| **DNS over HTTPS** | high | medium | blends with DoH, which is itself the anomaly on a monitored network |
| **Cloud storage / API** (S3, Slack, Teams, GitHub) | high — first-party trusted service | medium | API audit logs on the *service provider's* side |
| **Mail (SMTP/IMAP)** | medium | low | mail-flow anomaly detection |
| **ICMP / raw protocol** | medium | low | almost always filtered; high signal if present |
| **Named-pipe / SMB** | internal only | high | lateral movement detection |
| **P2P / mesh** | very high | medium | very hard to block, very anomalous |

**The core tradeoff:** resilience costs bandwidth and interactivity. A DNS tunnel survives most
egress filtering but is unusable for interactive work. Decide whether the operation needs
*interactive access* or *periodic tasking* — that choice drives the channel, not the reverse.

---

## 2. THE PREFERRED PATTERN

```
    implant ──HTTPS──> redirector ──> team server
                          │              │
                    (attacker-owned     (long-term host,
                     or cloud VPS,       never exposed)
                     cheap to burn)
```

**Why the redirector layer exists:** the team server's address must never appear in target
telemetry. If the redirector is identified and blocked, it is replaced; the team server and the
established implants survive. A typical setup uses several redirectors with different
IPs/providers so that blocking one does not fingerprint the others.

**Redirector hygiene:**
- Filter on the expected beacon profile (user-agent, URI path, header order) and **drop everything else** — a redirector that forwards arbitrary traffic is an open proxy and will be found.
- Never host anything else on a redirector.
- Use a distinct domain per redirector so a single block is contained.
- Keep the team server behind a second authentication layer; never expose it directly.

---

## 3. DOMAIN AND CERTIFICATE HYGIENE

| Concern | Practice |
|---|---|
| Domain categorisation | aged domains with a plausible theme; new domains are flagged fast |
| Certificate | valid TLS — a self-signed cert on a beacon is a signature |
| Certificate transparency | your cert **will** appear in CT logs; assume the defender can enumerate it |
| Reputation | check categorisation before use; a fresh domain scores badly |
| Typosquatting | high detection — used only for specific phishing objectives |
| WHOIS privacy | reduces attribution, does not reduce detection |

**Certificate transparency is the one you cannot avoid.** Any publicly trusted certificate you
issue is published. If the defender monitors CT logs for lookalike domains, they see your
infrastructure before you use it. Plan for discovery: assume the redirector domains will be
known, and design so that knowing them does not compromise the team server.

---

## 4. HOST-SIDE OPSEC

Infrastructure is only half. The implant's behaviour on the host is the other half.

| Signal | Mitigation |
|---|---|
| Process with no parent / wrong parent | spawn from a legitimate process; match the OS's normal parentage |
| Network connection from an unusual process | use a process that normally makes network connections |
| Regular beacon interval | **jitter** — a fixed 60s interval is a detection rule waiting to happen |
| Consistent packet size | pad or vary payload sizes |
| Persistent service / scheduled task | use mechanisms the environment already justifies |
| New binary on disk | fileless or living-off-the-land (see [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md)) |
| Long-lived connection | prefer short polling over a persistent socket where interactive is not needed |
| Predictable URI paths | randomise per-implant paths; a URI pattern is a rule |

**Jitter is the single highest-value host-side control.** Beacon regularity is one of the
easiest and most reliable network detections available to a defender, and it costs nothing to fix.

---

## 5. NETWORK DETECTION REALITY

Assume the network is monitored. Design for it.

| Detection | What it sees |
|---|---|
| JA3/JA4 fingerprint | the TLS client stack — a non-browser JA3 to a browser-looking destination |
| SNI inspection | the destination domain |
| Connection duration/volume | beacon patterns, long-lived sessions |
| DNS query analysis | high-entropy labels, high subdomain-per-domain ratio, unusual TXT volume |
| Domain reputation / categorisation | newly registered, uncategorised destinations |
| Egress filtering | allowed protocol and destination allowlists |
| Beacon interval analysis | periodicity, even with jitter |
| RITA / similar | long connections, beacon scoring |

**Go through the environment first.** If the network allows egress only via a proxy, model the
implant's traffic on that proxy's normal traffic. If everything goes through a cloud SaaS
provider, use the SaaS provider's own API as the channel. The best C2 channel in an environment
is the one that environment already uses.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| every domain, IP, and certificate used, with dates | **the client must be able to find and block your infrastructure afterwards** |
| the channel and why it was chosen for this environment | demonstrates analysis, not preference |
| which infrastructure is still live at report time | an un-decommissioned redirector is a live risk |
| the implant's beacon profile as the defender would see it | lets them write the rule and confirm it works |
| the redirector filtering rule | proves it was not an open proxy |
| decommission confirmation | the engagement is not over until the infrastructure is down |

**Infrastructure that remains live after the engagement is a real and serious finding.**
Enumerate everything, hand it over, and confirm teardown.

---

## 7. REMEDIATION REFERENCE

1. **Egress allowlisting** — the most effective control; C2 requires an outbound channel and most channels die if egress is default-deny.
2. **TLS inspection with JA3/JA4** — catches the client stack even when the domain and certificate look legitimate.
3. **Beacon analysis** — periodic connections, even jittered, are detectable at scale; deploy the scoring and tune it.
4. **DNS monitoring** — high-entropy labels and unusual TXT volume are strong signals; DNS is the channel defenders most often forget.
5. **CT log monitoring** — watch for certificates issued for lookalike domains; it detects infrastructure before use.
6. **Cloud SaaS audit logs** — if the channel is a trusted SaaS provider, the provider's logs are the detection point; enable and review them.
7. **Never rely on blocking a single domain** — the redirector model is designed for exactly that. Detection must be behavioural.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the channel **carry a real session** from the target, not just resolve DNS? | the channel works end to end |
| 2 | Was there a **control** - the same host with the redirector down, which produces no arrival? | the path is the one you built |
| 3 | Is the **certificate chain valid** on the redirector, so no client warning appears? | the domain hygiene is real |
| 4 | Did the domain's fronting **survive a passive check** by the defender's view? | the design goal |
| 5 | Which **profile fingerprint** does the traffic present (JA3, SNI, UA, interval)? | what the defender can pivot on |
| 6 | Is the **redirector disposable** - can you tear it down without touching the target? | the design property |
| 7 | Were **all infrastructure artefacts** recorded and then removed? | engagement integrity |

**A session arriving through the designed path, with the redirector-down control and a valid certificate
chain, is the bar.** DNS resolution, a certificate that exists, and a redirector that accepts a
connection are all preconditions.

---

## 9. EXECUTION PRIMITIVES

Channel and infrastructure design is proven by **a session arriving through the designed path, with the
redirector-down control, a valid certificate chain, and a recorded fingerprint**. Every block ends at an
attributed arrival.

### 9.1 The path, and the control at each hop

```bash
# each hop is a separate claim, and each gets its own check
BEACON="beacon.target.example"     # the domain the target will resolve
REDIR="redirect.example"           # your redirector
TEAM="team.example"; TEAM_IP="203.0.113.10"
LOG="channel-arrivals.jsonl"

echo "=== HOP 1: DNS resolution from the target's perspective ==="
dig +short A "$BEACON"; dig +short CNAME "$BEACON"
echo "  -> if this does NOT resolve to your redirector, nothing downstream matters"

echo
echo "=== HOP 2: the redirector accepts TLS with a VALID chain (no warning) ==="
echo | openssl s_client -connect "$REDIR:443" -servername "$REDIR" 2>/dev/null \
  | grep -E 'subject=|issuer=|Verify return code'
echo "  -> 'Verify return code: 0 (ok)' is required. Anything else means the client sees a warning."

echo
echo "=== HOP 3: the redirector forwards to the team server and preserves the request ==="
curl -sS -o /dev/null -w 'via redirector: %{http_code}  redirects=%{num_redirects}  time=%{time_total}s\n' \
  "https://$REDIR/cdn/health.js" -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

echo
echo "=== CONTROL: with the redirector down, the target must produce NO arrival ==="
wc -l "$LOG" 2>/dev/null || echo "  0 $LOG"
echo "  -> stop the redirector, wait two sleep cycles, re-check. The count must NOT change."
echo "  -> an arrival with the redirector down means the beacon is bypassing your path entirely,"
echo "     which is a different (and worse) finding about the target's resolution."
```

**Each hop is a separate claim with its own check.** A valid certificate on the redirector is required,
because a client warning is both an OPSEC failure and a detection event.

### 9.2 The domain and certificate hygiene, measured

```bash
D="beacon.target.example"; REDIR="redirect.example"
echo "=== CERTIFICATE HYGIENE ==="
echo | openssl s_client -connect "$REDIR:443" -servername "$REDIR" 2>/dev/null | openssl x509 -noout \
  -subject -issuer -dates -ext subjectAltName 2>/dev/null
echo "  checks:"
echo "   - the SAN covers the SNI you will present, not a wildcard of a different domain"
echo "   - the validity window is long enough for the engagement, not 90 days into the past"
echo "   - the issuer is a public CA, so no client trusts-anchor warning appears"
echo "   - the serial and the issuing CA match the provisioning record you wrote"
echo
echo "=== DNS HYGIENE ==="
dig +short TXT "$D"; dig +short MX "$D"; dig +short NS "$D"; dig +short SOA "$D"
echo "  checks:"
echo "   - no SPF/DMARC record that contradicts the engagement's mail posture"
echo "   - NS under a registrar you control, with a documented teardown"
echo "   - no wildcard that would expose unrelated names if the domain is discovered"
echo "   - WHOIS privacy is set correctly for the jurisdiction and the engagement"
echo
echo "=== FRONTING / REPUTATION CHECK (the defender's passive view) ==="
curl -sS "https://crt.sh/?q=%25.$D&output=json" 2>/dev/null \
  | python3 -c "
import json,sys
try:
    rows=json.load(sys.stdin); names=sorted({n for e in rows for n in e.get('name_value','').split()})
    print('  certificate transparency shards:', len(names))
    for n in names[:15]: print('   ', n)
    print('  -> more than a handful, or a name that does not match your cover story, is a passive IOC')
except Exception as e: print('  crt.sh unavailable:', e)" 2>/dev/null
echo
echo "  record: the number of CT entries, the WHOIS creation date of the domain, and whether a"
echo "  reputation service already classifies the domain. A domain registered days before the"
echo "  engagement starts is a strong passive signal, whatever the traffic looks like."
```

**The passive view is the design constraint.** Certificate transparency, WHOIS age, and reputation are
visible without touching the traffic, and the report should state what a defender could see.

### 9.3 The fingerprint, which is what the defender pivots on

```python
# the channel's fingerprint is the deliverable for the blue side. Measure it, do not assume it.
import json, subprocess, re
FINGERPRINT = {
 "sni":                 "the SNI presented on the wire",
 "ja3":                 "the TLS client fingerprint (ciphers, extensions, curves, order)",
 "ja3s":                "the server-side fingerprint the defender may also match",
 "http_user_agent":     "the UA string carried by the beacon",
 "http_uri_shape":      "the URI pattern and its entropy",
 "interval_seconds":    "the sleep with its jitter band",
 "payload_size_band":   "the size distribution of the requests",
 "dns_query_pattern":   "the query name shape and any DGA-like pattern",
 "destination_reputation": "the ASN, the domain age, and any existing classification",
}
print("%-24s %s" % ("dimension", "what to record for the report"))
for k, v in FINGERPRINT.items(): print("%-24s %s" % (k, v))
print()
print("HOW TO MEASURE JA3 without special tooling:")
print("  1. capture the beacon's ClientHello on the redirector (tcpdump/tshark on your own host)")
print("  2. compute ja3 from the cipher list, extensions, curves, and their ORDER")
print("  3. record it, because it is stable per client library and it is what a defender blocks on")
print()
print("python3 -c \"import hashlib; print('ja3 = md5 of the ','-'.join(fields))\"" )
print("  fields = tls_version, cipher_list, extension_list, elliptic_curves, ec_point_formats")
print()
print("THE DESIGN RULE: every dimension above must be plausible for the cover story. A browser UA")
print("with a python-requests JA3 is the single most common contradiction in this family.")
```

**Every dimension must be plausible for the cover story.** A browser user agent with a
`python-requests` JA3 is the contradiction that gets a channel blocked, and the report should show the
measurement rather than the intention.

### 9.4 The redirector design, and its disposability

```python
# the design property that matters: the redirector is disposable, and the team server is not.
DESIGN = {
 "layer 1 - target":       "resolves your beacon domain; nothing else about it changes",
 "layer 2 - DNS":          "your authoritative zone; the only layer you must change to move",
 "layer 3 - redirector":   "a cheap, replaceable host that terminates TLS and filters",
 "layer 4 - team server":  "reachable ONLY from the redirector, never from the internet",
 "layer 5 - data":         "off the team server, encrypted, and outside the engagement window",
}
print("%-24s %s" % ("layer", "property"))
for k, v in DESIGN.items(): print("%-24s %s" % (k, v))
print()
print("THE FIVE CONTROLS the redirector must provide, and how to verify each:")
CHECKS = [
 ("IP filter",          "curl the redirector from an unexpected IP and confirm it is dropped"),
 ("URI filter",         "curl a wrong path and confirm a decoy response, not a 404 from your stack"),
 ("UA filter",          "curl with an unexpected UA and confirm the decoy"),
 ("rate limit",         "burst the redirector and confirm the excess is dropped, not queued"),
 ("no direct team path", "curl the team server from the public internet and confirm it is unreachable"),
]
for name, how in CHECKS: print("  %-22s %s" % (name, how))
print()
print("VERIFY THE DISPOSABILITY: the redirector's replacement must be a DNS change and nothing else.")
print("  if moving the redirector requires touching the target, the design has failed that property.")
```

**The IP, URI, and UA filters are the redirector's job.** A wrong path returning your team server's own
`404` discloses the stack, and the decoy response is the control that also tells you the filter works.

### 9.5 The teardown, layer by layer

```bash
# teardown in reverse order, and record the timestamp of each step
cat > infra-teardown.txt <<'TXT'
TEARDOWN - reverse order, timestamp every line, keep the file in the report bundle
[ ] stop the beacon session and record the final arrival count
[ ] remove the data from the team server and verify the deletion
[ ] destroy the team server and confirm the host is unreachable
[ ] destroy the redirector and confirm the host is unreachable
[ ] remove the DNS records and confirm the names no longer resolve
[ ] release the certificate and confirm the chain no longer serves
[ ] deregister the domain, or park it per the engagement's instruction
[ ] revoke every cloud credential, token, and API key the exercise created
[ ] confirm the beacon domain no longer resolves anywhere
[ ] record every artefact that could NOT be removed, and why
TXT
echo "written."
echo
echo "=== VERIFY THE TEARDOWN FROM OUTSIDE ==="
for H in beacon.target.example redirect.example team.example; do
  printf '%-28s ' "$H"
  A=$(dig +short A "$H")
  C=$(curl -sS -m 5 -o /dev/null -w '%{http_code}' "https://$H/" 2>/dev/null)
  echo "dns=${A:-<none>}  http=${C:-<unreachable>}"
done
echo "  -> every line must show no DNS and no reachable service before the engagement closes"
```

**Teardown in reverse order, verified from outside.** A redirector or domain left live is the exposure that
outlives the engagement, and the outside check is what proves it is gone.

### 9.6 The end-to-end harness

```bash
python3 - <<'PY'
import subprocess, json, os, re
def sh(*a, t=15):
    try: return subprocess.run(a, capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as e: return f"ERR:{type(e).__name__}"

HOSTS = {"beacon": "beacon.target.example", "redirector": "redirect.example", "team": "team.example"}
print("=== LAYER REACHABILITY MATRIX ===")
print("%-12s %-30s %-10s %s" % ("layer","host","dns","https"))
mat = {}
for layer, h in HOSTS.items():
    a = sh("dig","+short","A",h)
    c = sh("curl","-sS","-m","6","-o","/dev/null","-w","%{http_code}",f"https://{h}/")
    mat[layer] = (a, c)
    print("%-12s %-30s %-10s %s" % (layer, h, a or "<none>", c or "<unreachable>"))
print()
print("EXPECTED:")
print("  beacon     -> resolves, and reaches the redirector")
print("  redirector -> reachable from the internet, certificate valid")
print("  team       -> NOT reachable from the internet (the control)")
print()
if mat.get("team",("", ""))[1] not in ("", "000") and not mat["team"][1].startswith("ERR"):
    print("  FAIL: the team server answers from the internet. The design property is broken.")
else:
    print("  ok: the team server is not directly reachable.")
print()
print("=== CERTIFICATE CHAIN ===")
out = sh("bash","-c","echo | openssl s_client -connect redirect.example:443 "
                        "-servername redirect.example 2>/dev/null | grep -E 'Verify return code|subject='")
print(" ", out or "<no TLS response>")
print()
print("=== CONTROL ===")
print("  stop the redirector, wait two sleep cycles, and confirm the arrival log does not grow.")
print("  a growing log with the redirector down means the path is not the one you designed.")
print()
print("REPORT = the reachability matrix, the certificate verification code, the fingerprint set,")
print("         the redirector filter checks, and the verified teardown.")
PY
```

**The reachability matrix and the certificate code.** The non-reachability of the team server is the
design property under test, and a `Verify return code` other than `0` invalidates the hygiene claim.

---

## 10. EVIDENCE STANDARD — CHANNEL DESIGN ARTEFACTS

| Item | Why |
|---|---|
| The **reachability matrix** per layer, with DNS and HTTPS results | shows the design works and the team server is not exposed |
| The **redirector-down control** and the arrival count | proves the path is the designed one |
| The **certificate chain verification code** and the SAN | a non-zero code means a client warning |
| The **domain's CT entries, WHOIS age, and reputation** | the passive view the defender has |
| The **fingerprint set**: SNI, JA3, UA, URI shape, interval, size band | what the defender pivots on |
| The **redirector's filter checks**: IP, URI, UA, rate | each is a separate control with its own result |
| The **team server's public unreachability** | the core design property |
| The **disposability test**: the move is a DNS change and nothing else | the design property that bounds the loss |
| The **layer-by-layer teardown**, with timestamps and the outside verification | engagement integrity |
| Every artefact that **could not be removed** | an open item, not a footnote |

Report the **design and its measurements**: "`beacon.target.example` resolves via a CNAME to the
redirector, which presents a certificate whose `Verify return code` is `0 (ok)` with a SAN covering the
SNI, issued by a public CA 34 days ago. `crash` shows 2 certificate transparency entries for the domain
and the WHOIS creation date is 41 days before the engagement, so the passive footprint is small but not
zero. The redirector forwards to the team server, and `curl https://team.example/` from the public
internet returns no response, which is the design control, while `curl` with an unexpected user agent
returns the decoy page rather than the stack's own `404`. The beacon presents a JA3 of `...` matching the
configured client, an interval of 58-71 seconds against a declared 60-second sleep with 20 percent jitter,
and the arrival log did not grow across two cycles with the redirector stopped, which is the control.
Teardown was completed in reverse order at `2026-09-12T16:40Z`, and all three names now return no DNS
record and no reachable service from outside", never "the infrastructure is well designed".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **domain that resolves** to your redirector | a precondition; the session arrival is the result |
| A **certificate that exists**, with a non-zero verify code | the client sees a warning; the hygiene claim fails |
| A **redirector that accepts a connection**, with no filters verified | none of the five controls was tested |
| A **team server that answers from the internet** | the design property is broken; report it as a defect |
| A **fingerprint you assumed rather than measured** | an untested hypothesis |
| A **browser UA with a non-browser JA3** | the contradiction is the finding, not the UA |
| A **CT entry count you did not check** | the passive footprint is unmeasured |
| A design where **moving the redirector requires touching the target** | the disposability property fails |
| A finding where **any layer is still live after teardown** | an incident you caused |
| An exercise run **outside the authorised scope or window** | out of scope |
| A **commercial fronting service** used without written authorisation | out of scope and a terms-of-service issue |

**A session arriving through the designed path, with the controls, the measured fingerprint, and the
verified teardown.** DNS resolution and certificate existence are this family's two standard
non-findings.

---

## 11. REMEDIATION REFERENCE — CHANNEL DESIGN DISCIPLINE

1. **Make the layout layered and disposable: the redirector is replaceable by a DNS change alone, and the team server is never internet-reachable** - the two properties that bound the loss when a layer is discovered.
2. **Verify the certificate chain returns `Verify return code: 0 (ok)` before the channel is used, and check the SAN covers the SNI you present** - a client warning is both an OPSEC failure and a detection event.
3. **Measure the fingerprint set rather than assuming it: SNI, JA3, UA, URI shape, interval, and size band must all be consistent with the cover story** - the contradiction is what the defender pivots on.
4. **Record the passive footprint: certificate transparency entries, WHOIS age, and any existing reputation classification** - a domain registered days before the engagement is a signal whatever the traffic looks like.
5. **Implement all five redirector controls and verify each one: IP filter, URI filter, UA filter, rate limit, and no direct team path** - an unverified control is an unverified claim.
6. **Serve a decoy response for a wrong path or UA rather than letting the stack return its own error page** - your stack's `404` discloses the framework, and the decoy also confirms the filter works.
7. **Keep the data off the team server and outside the engagement window, encrypted** - it is the only layer whose loss is unrecoverable.
8. **Write the teardown procedure before the deployment, in reverse layer order, with an owner per line** - the teardown is designed, not improvised.
9. **Verify the teardown from outside the infrastructure: no DNS, no reachable service, no live certificate** - an inside check proves nothing about what the internet can still see.
10. **Set an engagement kill date and record it in the design document, alongside the teardown owner** - the channel outliving the engagement is the most common way this work becomes an incident.
11. **Carry the reachability matrix, the certificate code, the fingerprint set, and the teardown verification into the report** - the design claims are only usable if they are measured.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [c2-framework-selection-and-operation](../c2-framework-selection-and-operation/SKILL.md) - the operation this infrastructure carries
- [red-team-infrastructure](../attack-execution-atomic-tests/SKILL.md) - the surrounding engagement discipline
- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) - the inside-network channel
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the edge layer a redirector may sit behind
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the host-side counterpart
