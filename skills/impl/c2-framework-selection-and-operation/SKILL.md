---
name: c2-framework-selection-and-operation
description: >-
  Command-and-control framework selection, deployment and operation. Use when choosing a C2
  platform for an engagement, operating agents across multiple hosts, or assessing whether a
  target's defences would catch a known framework. Covers framework tradeoffs and operational
  discipline.
---

# SKILL: C2 Framework Selection & Operation

> **AI LOAD INSTRUCTION**: This complements
> [c2-infrastructure-and-channel-design](../c2-infrastructure-and-channel-design/SKILL.md) —
> that skill covers the *network* you build, this one covers the *platform* you run. Framework
> choice is driven by two things: what the team already operates competently, and what the
> target's defences are known to catch. A more capable framework that nobody on the team knows
> is a worse choice than a simple one operated well. Read §2 before comparing features.

## 0. RELATED ROUTING

- [c2-infrastructure-and-channel-design](../c2-infrastructure-and-channel-design/SKILL.md) — redirectors, channels, domain hygiene
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) — keeping agents alive
- [malware-development-workflow](../malware-development-workflow/SKILL.md) — custom implants when a framework will not do
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) — moving between agents
- [windows-postexploit](../windows-postexploit/SKILL.md) — what you do once you have a session
- [c2-frameworks-command-control](../../core-subjects/c2-frameworks-command-control.md) — doctrine
- [c2-opsec](../../core-subjects/c2-opsec.md) — operational security doctrine

---

## 1. WHAT A C2 IS FOR

Strip away the feature lists. A C2 platform does four things:

| Function | Why it is hard |
|---|---|
| **Tasking** — deliver instructions to an implant | must survive intermittent connectivity |
| **Collection** — return output reliably | must handle large/slow/binary data over a constrained channel |
| **Session management** — track many hosts, identities, privileges | the operational complexity scales with host count, not with the attack |
| **Team coordination** — shared state across operators | the failure mode is two operators working the same host without knowing |

**The fourth is the one that gets teams caught.** A framework's real value in a team engagement
is that everyone can see what everyone else has done. Two operators independently running
enumeration on the same host at the same time produces a detectable burst — and a confused
report.

---

## 2. SELECTION CRITERIA

Rank frameworks by these, in order. Feature lists are deliberately last.

| Criterion | Why it dominates |
|---|---|
| **Team familiarity** | a framework nobody can debug under pressure fails at the worst moment |
| **Detection profile against the target's stack** | the known frameworks are signatured; a signatured framework gets caught on deploy |
| **Channel flexibility** | can it use the channel that fits *this* network? |
| **Team-server model** | concurrent operators, shared logs, session locking |
| **Post-exploitation depth** | does the built-in capability match the objective, or will you need custom tooling anyway? |
| **OPSEC defaults** | does it beacon too fast, too regularly, too loudly out of the box? |
| **Maturity and support** | a framework that is abandoned mid-engagement is a liability |

**Predictability is the trap.** The popular frameworks are the most signatured. If the target
has a mature EDR, deploying a default agent from a widely used framework is close to a
guaranteed detection — which may be exactly what a *detection validation* engagement wants, and
exactly what a *quiet* engagement does not.

**Be explicit about which of those two engagements you are in.** They need opposite framework
choices, and the report differs accordingly.

---

## 3. FRAMEWORK CATEGORIES

Group by how the agent behaves, not by name.

| Category | Characteristic | Trade |
|---|---|---|
| **Full-featured agent** | rich built-ins, many channels, team server | large on-disk/memory footprint, signatured, best for team operations |
| **Modular / scripting-driven** | small core, post-exploitation loaded on demand | less resident capability, more setup per task |
| **Minimal / custom** | purpose-built for one engagement | no signature, no built-ins — you build everything |
| **Peer-to-peer / mesh** | agents talk to each other, few external connections | excellent against egress filtering, harder to manage and to clean up |
| **Cloud-service C2** | blends into SaaS / first-party traffic | unusual API usage on the provider's side is the detection |
| **Local-only** (named pipe, internal listener) | no egress at all | requires an existing foothold in each segment |

**A minimal custom agent frequently beats a full framework** when the objective is narrow:
one action on a handful of hosts, no interactivity needed. The framework's feature set is a
liability if you use 5% of it and carry 100% of its signature.

---

## 4. OPERATIONAL DISCIPLINE

The behaviours that keep an engagement from becoming an incident.

| Discipline | Why |
|---|---|
| **Name your sessions meaningfully** | `host-role-user-priv-date`; you will lose track by host 30 |
| **One operator per host at a time** | check the session log before acting |
| **Jitter everything** | fixed intervals are the easiest network detection there is |
| **Log every action with a timestamp** | the report depends on it and the client's timeline will not match yours otherwise |
| **Timebox each host** | a host you have been on for six hours is one you have been detected on |
| **Kill stale sessions** | an orphaned agent on a decommissioned host is a live backdoor you have forgotten |
| **Never run unsanctioned tooling** | every binary you drop is an artefact the client must remove |
| **Snapshot before destructive action** | the client will ask you to undo it |

**Do not confuse the C2's log with the evidence.** The framework records what *you* did; the
report needs what the *defender saw*. Correlate the two — the delta is the finding.

---

## 5. DETECTION — WHAT THE TARGET SEES

Assume the framework's default traffic is known. Plan for it.

| Signal | Cause |
|---|---|
| Named-pipe or named-mutex artefacts | default agent naming — a fingerprint, and trivially triaged |
| Default URI paths and user-agents | the malleable profile was left at default |
| Beacon periodicity | even with jitter, a periodic pattern emerges over hours |
| Parent-child anomaly | default spawn behaviour (an Office process spawning a shell) |
| EDR memory signature for the agent | the agent binary is in every vendor's signature set |
| Team-server TLS certificate | default certs are published and blocklisted |
| Named service / scheduled task | persistence named by default |
| **Correlation across hosts** | the same agent on 30 hosts is a pattern no single host shows |

**The last one is why the framework choice matters at scale.** A single host with an unusual
process is a low-priority alert. Thirty hosts with the same unusual process, same URI, same
interval, is an incident — and the correlation happens at the SIEM, not the endpoint.

**Change the defaults before you deploy.** Default names, paths, certificates and intervals are
where the easy detections live, and they cost nothing to change.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| framework, version, and the agent's configuration | the result is version- and config-specific |
| every host with a session, and the session lifespan | the client must be able to find them all |
| the persistence mechanism per host, if any | an undiscovered persistence is an incident |
| **the delta between the C2 log and the client's telemetry** | this is the detection-coverage finding |
| every artefact the framework created | file paths, service names, registry keys, mutexes |
| teardown confirmation per host | an orphaned agent is a live backdoor |
| which detections fired, and the time-to-detect | the deliverable |

---

## 7. REMEDIATION REFERENCE

1. **Egress allowlisting** — the durable control; a C2 needs an outbound channel and default-deny egress removes most of them.
2. **Detect the framework's fingerprints, not just its behaviour** — default names, paths, and certificates are high-fidelity and cheap to write rules for; blocklist the known team-server certificates.
3. **Correlate across hosts** — the SIEM is where a framework is caught, because the pattern only exists in aggregate.
4. **Beacon analysis with jitter tolerance** — tune the scoring so jitter does not defeat it; periodic-but-irregular is still periodic.
5. **Behavioural endpoint detection, not signature-only** — the agent binary changes; its behaviour (parent-child, memory, persistence) is harder to change.
6. **Named-pipe and mutex monitoring** — a specific, cheap, and reliable signal for default-configured agents.
7. **Decide your posture deliberately** — either you accept that a sophisticated adversary will establish C2 and invest in *detecting and responding* to it, or you invest in *preventing* execution. Assuming the network layer alone will stop it is the failure mode.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the beacon **actually reach the listener** from the target host? | the channel works, not that a config looks right |
| 2 | Was there a **control** - the same host with the listener down, which produces no arrival? | the arrival came from the host |
| 3 | Did the session **survive the profile's own sleep/jitter** for more than one cycle? | it is a stable channel, not one packet |
| 4 | Did the **peer address** at the listener match the target? | attribution, not a third party's scan |
| 5 | Did **any defence alert** during the window, and which one? | the detection result, honest either way |
| 6 | Did the payload stay **inside the authorised scope and the agreed profile**? | engagement discipline |
| 7 | Were the **listener, the infrastructure, and the artefacts** torn down and recorded? | engagement integrity |

**A beacon arriving from the target's own address, across more than one sleep cycle, is the bar.** A
profile that looks correct, a framework that starts, and a listener that binds are all preconditions.

---

## 9. EXECUTION PRIMITIVES

C2 operation is proven by **a beacon arriving from the target with the peer address recorded, sustained
across sleep cycles, with the listener-down control and a teardown record**. Every block ends at an
attributed arrival.

### 9.1 The listener, which is the artefact source

```bash
# a minimal listener that LOGS THE PEER ADDRESS, the user agent, and the timing - the three things
# that turn an arrival into evidence. This is not a full C2; it is the measurement instrument.
MYPORT=8443
python3 - <<'PY'
import http.server, socketserver, threading, datetime, json, os
LOG = "c2-arrivals.jsonl"
class H(http.server.BaseHTTPRequestHandler):
    def _log(self):
        rec = {"t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "peer": self.client_address[0], "peer_port": self.client_address[1],
               "method": self.command, "path": self.path,
               "ua": self.headers.get("User-Agent", ""),
               "host": self.headers.get("Host", ""),
               "len": self.headers.get("Content-Length", "0")}
        with open(LOG, "a") as f: f.write(json.dumps(rec) + "\n")
        print("ARRIVAL:", json.dumps(rec))
    def do_GET(self):
        self._log(); self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream"); self.end_headers()
        self.wfile.write(b"")            # an EMPTY task keeps the profile's protocol honest
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); b = self.rfile.read(n)
        self._log()
        with open(LOG, "a") as f: f.write(json.dumps({"body": b.decode(errors="replace")[:1500]}) + "\n")
        self.send_response(200); self.end_headers()
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("0.0.0.0", 8443), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print("listener on :8443 ->", LOG)
print("THE PEER FIELD IS THE PROOF. An arrival whose peer is not the target is someone else's traffic.")
import time
while True: time.sleep(5)
PY
```

**The peer address is the attribution proof, and the arrival log is the deliverable.** A framework that
"connected successfully" from your own workstation proves nothing about the target.

### 9.2 The listener-down control, and the sleep-cycle test

```bash
# CONTROL 1: the listener is DOWN - the target must produce NO arrival
echo "step 1: stop the listener, wait two sleep intervals, and read the log"
wc -l c2-arrivals.jsonl 2>/dev/null || echo "  (no log yet)"
echo "  -> unchanged line count with the listener down IS the control"
echo
echo "step 2: start the listener and wait at least THREE sleep cycles"
sleep 30
wc -l c2-arrivals.jsonl
echo
echo "step 3: the inter-arrival intervals must MATCH the profile's sleep and jitter"
python3 - <<'PY'
import json, datetime, statistics
rows = [json.loads(l) for l in open("c2-arrivals.jsonl") if l.strip().startswith("{")]
ts = [datetime.datetime.fromisoformat(r["t"]) for r in rows if "t" in r]
gaps = [(b - a).total_seconds() for a, b in zip(ts, ts[1:])]
if gaps:
    print("arrivals:", len(rows), " intervals:", [f"{g:.1f}s" for g in gaps])
    print("median interval %.1fs  min %.1fs  max %.1fs" % (statistics.median(gaps), min(gaps), max(gaps)))
    print()
    print("COMPARE against the profile's declared sleep and jitter. A median inside the jitter band")
    print("means the profile is operating as configured; a fixed interval means jitter is OFF, which")
    print("is itself a finding about the profile's OPSEC.")
else:
    print("NO ARRIVALS - the beacon is not reaching the listener. Do not claim a working channel.")
PY
echo
echo "CONTROL 2: run the same beacon from your own host and confirm the peer differs"
curl -sS "http://127.0.0.1:8443/" >/dev/null && tail -1 c2-arrivals.jsonl
```

**Two arrivals with the listener down and up is the pair.** A single arrival proves a packet; three
arrivals at the configured interval prove a channel.

### 9.3 The profile validation, before deployment

```python
# validate the profile's declared behaviour against what actually happens
import re, json, subprocess, os
PROFILE = "profile.json"    # or the framework's own config
def show(path):
    try: d = json.load(open(path))
    except Exception as e: return print("profile unreadable:", e)
    keys = ["sleep_time","jitter","useragent","spawnto_x86","spawnto_x64",
            "callback_host","callback_port","uri","http_get_metadata","http_post_metadata",
            "data_jitter","kill_date","max_retry","crypto_scheme"]
    print("%-22s %s" % ("setting","value"))
    for k in keys:
        if k in d: print("%-22s %s" % (k, str(d[k])[:70]))
    print()
    CHECKS = [
     ("jitter",        "jitter is 0 or absent" in [] or float(d.get("jitter",0) or 0) == 0,
      "a fixed interval is trivially detectable by interval analysis"),
     ("sleep_time",    float(d.get("sleep_time",0) or 0) < 30,
      "sub-30s sleep multiplies the traffic and the detection surface by an order of magnitude"),
     ("useragent",     str(d.get("useragent","")).strip() == "" or "Mozilla" not in str(d.get("useragent","")),
      "an empty or non-browser UA is the single most common beacon signature"),
     ("callback",      "http" not in str(d.get("callback_host","")).lower(),
      "verify the callback domain is one YOU control and that its certificate matches"),
     ("kill_date",     d.get("kill_date") in (None, "", "0"),
      "a kill date is the safety net: without it the beacon outlives the engagement"),
    ]
    print("%-14s %-8s %s" % ("check","verdict","why"))
    for name, bad, why in CHECKS:
        print("%-14s %-8s %s" % (name, "RISK" if bad else "ok", why))
show(PROFILE)
print()
print("SUBMISSION CHECK, before the profile is ever deployed:")
for r in ["the profile is under version control and its hash is recorded in the report",
          "the callback domain and certificate are ones you control and can take down",
          "the kill date is set and documented, and the teardown procedure is written down",
          "the sleep and jitter are within the engagement's agreed traffic budget",
          "the artefacts directory is OUTSIDE the target's filesystem, ideally in-memory or a temp path",
          "the profile contains no real credential, no real domain, and no real operator identifier"]:
    print("  -", r)
```

**The profile's declared interval must match the observed interval.** A profile with jitter off is a
finding about the engagement's own OPSEC, and the output should say so.

### 9.4 The detection measurement, which is the other half of the value

```python
# a C2 exercise that records no detection result has answered only half the question
import json, datetime
WINDOW = ("2026-09-12T09:00:00Z", "2026-09-12T11:00:00Z")
QUERIES = {
 "network - dns":       "dns where query in (callback_host)",
 "network - tls ja3":   "tls where ja3_hash in (<beacon ja3>)",
 "network - interval":  "proxy where dest_domain = <callback_host>  |  stats count() by src_ip, round(interval)",
 "endpoint - process":  "process where image ends with <spawnto_x64 basename> and parent.image ends with <spawn parent>",
 "endpoint - thread":   "thread where remote_address = <callback_ip> and is_remote_created = true",
 "identity - access":   "cloud_audit where principal = <target principal> and action in (sts:GetCallerIdentity)",
}
print("%-22s %s" % ("telemetry source","query intent"))
for k, v in QUERIES.items(): print("%-22s %s" % (k, v))
print()
print("FOR EACH source record: fired? rule name? latency? and THE NEGATIVE CONTROL -")
print("did a benign process that resolves the same domain on the same schedule also fire?")
print("A rule that fires on the negative control is unusable, and saying so is the finding.")
print()
print("the artefact set for the report, per beacon cycle:")
for a in ["the arrival's timestamp, peer address, and user agent",
          "the inter-arrival interval, against the profile's declared sleep and jitter",
          "the process tree on the target that produced it (host-side, authorised)",
          "the detection result per telemetry source, or an explicit 'no telemetry'",
          "the negative control's result per source",
          "any IOC the defender would need: the domain, the ja3, the uri, the interval"]:
    print("  -", a)
```

**The detection result, positive or negative, is half the deliverable.** "No alert" is a valid and
important finding, and the negative control is what makes it credible.

### 9.5 The teardown, which must be recorded

```text
# the teardown is part of the evidence, not an afterthought
cat > teardown-checklist.txt <<'TXT'
TEARDOWN - record the timestamp of each line, and keep this file in the report bundle
[ ] stop the listener and record the final arrival-log line count
[ ] collect the arrival log, the profile, and the framework version into the bundle
[ ] on the target: kill the beacon process and verify with the platform's process listing
[ ] on the target: remove every dropped artefact, and the profile's staging path
[ ] on the target: remove any persistence the exercise installed, and verify the removal
[ ] revoke any credential, token, or access the exercise created
[ ] tear down the redirector, the domain, and the certificate you provisioned
[ ] confirm the callback domain no longer resolves to your infrastructure
[ ] record the final state of every cloud resource the exercise created
[ ] state in the report every artefact that COULD NOT be removed, and why
TXT
echo "written. Every unchecked line belongs in the report as an open item."
echo
echo "verify the listener is down and the domain is gone:"
curl -sS -m 5 -o /dev/null -w 'callback reachable after teardown: %{http_code}\n' "https://<callback_host>/" 2>/dev/null || echo "callback unreachable (expected)"
dig +short CNAME <callback_host> ; dig +short A <callback_host>
```

**Every unremoved artefact is an open item in the report.** A C2 exercise that leaves infrastructure
running is the most common way this work becomes an incident.

### 9.6 The end-to-end harness

```bash
python3 - <<'PY'
import json, datetime, statistics, os, subprocess
LOG = "c2-arrivals.jsonl"
def rows():
    if not os.path.exists(LOG): return []
    return [json.loads(l) for l in open(LOG) if l.strip().startswith("{") and '"peer"' in l]

def summarise(tag):
    r = rows()
    ts = [datetime.datetime.fromisoformat(x["t"]) for x in r]
    gaps = [(b-a).total_seconds() for a, b in zip(ts, ts[1:])]
    peers = sorted({x["peer"] for x in r})
    uas = sorted({x.get("ua","")[:50] for x in r})
    print("%-22s arrivals=%-3d peers=%s" % (tag, len(r), peers))
    if gaps:
        print("   intervals: median %.1fs min %.1fs max %.1fs  n=%d" %
              (statistics.median(gaps), min(gaps), max(gaps), len(gaps)))
    if uas: print("   user agents:", uas)
    return len(r)

print("=== THE PAIR ===")
print("run this once with the listener DOWN, then once with it UP, and compare the counts:")
print("  listener DOWN  -> the count must NOT change")
print("  listener UP    -> the count must grow once per sleep cycle")
print()
summarise("current state")
print()
print("=== VERDICT RULES ===")
for r in ["an arrival whose peer is NOT the target is not your beacon",
          "fewer than three arrivals does not demonstrate a channel, only a packet",
          "an interval far outside the declared jitter band means the profile is not what it claims",
          "a fixed interval means jitter is off, which is an OPSEC finding in itself",
          "no arrival at all means the channel is unproven - do not report the profile as working",
          "an arrival with no detection result is an incomplete deliverable"]:
    print("  -", r)
print()
print("BUNDLE: the arrival log, the profile and its hash, the framework version, the process tree,")
print("        the detection results with their negative controls, and the teardown record.")
PY
```

**The pair and the interval distribution.** A count that grows with the listener up and holds with it
down, at the configured interval, is a demonstrated channel; anything less is labelled as such.

---

## 10. EVIDENCE STANDARD — C2 OPERATION ARTEFACTS

| Item | Why |
|---|---|
| The **arrival log**, with the peer address per arrival | attribution; an arrival from any other peer is not your beacon |
| The **listener-down control's count** | proves the arrivals came from the target's beacon |
| The **inter-arrival intervals**, against the declared sleep and jitter | proves the profile operates as configured |
| The **user agent and the URI** actually used | the indicators a defender needs |
| The **profile**, with its hash, and the framework version | reproducibility |
| The **process tree on the target** that produced the beacon | the host-side half of the evidence |
| The **detection result per telemetry source**, positive or negative | half the deliverable |
| The **negative control per source** | makes a "no alert" claim credible |
| The **teardown record**, with timestamps and the unremoved items | engagement integrity |
| Confirmation that the **callback domain and certificate are gone** | bounds the exposure after the engagement |

Report the **arrival and the controls**: "with the listener stopped the arrival log stayed at 0 lines for
two sleep cycles, which is the control. With it running, three arrivals came from `10.20.4.31`, which is
the target host, at intervals of `62.1s`, `58.4s`, and `71.0s` against a profile declaring
`sleep_time: 60` and `jitter: 20`, so the median of `62.1s` is inside the declared band and the channel is
operating as configured. The arrivals used the profile's configured user agent and URI, and the
`Sysmon` event `3` on the target records the same destination at the same timestamps. `Zeek` emitted a
`ssl` record with ja3 `...`, which the SIEM's rule `C2-BEACON-07` matched in 3 of 3 cycles, while the
negative control - a benign `curl` to the same domain on a fixed 60-second schedule - matched nothing,
so the rule is measuring the periodicity rather than the domain", never "the C2 channel works".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **framework that starts** and reports a session, with no arrival at the listener | a client-side claim; the arrival is the evidence |
| An arrival whose **peer is your own host** | you tested your own infrastructure |
| A **single arrival** | a packet, not a channel |
| An arrival from an **internet scanner** hitting the same port | verify the peer and the user agent before attributing it |
| A **`kill_date` absent** from the profile | an OPSEC defect to report, not a channel result |
| A detection result with **no negative control** | an unmeasured claim about the rule |
| A profile that "works" with **protections disabled** | report the conditions, not the technique |
| An interval far outside the jitter band, **unexplained** | an untested hypothesis about the profile |
| A finding where **the listener, the domain, or the certificate is still live** | an incident you caused |
| An exercise run **outside the authorised scope or window** | out of scope |
| A **third-party C2 SaaS** used without written authorisation | out of scope and a data-protection issue |

**An attributed arrival across three cycles, with the listener-down control and the detection result.**
Single arrivals and client-side session claims are this family's two standard non-findings.

---

## 11. REMEDIATION REFERENCE — C2 OPERATION DISCIPLINE

1. **Set a kill date in every profile and treat its absence as a blocker for deployment** - the beacon outliving the engagement is the most common way this work becomes an incident.
2. **Configure jitter explicitly and never run a fixed interval; interval analysis is the cheapest and most reliable beacon detection** - it is the single highest-value OPSEC control.
3. **Match a real user agent and a plausible URI from the target's own environment, and serve real-looking responses rather than empty ones** - an empty `200` to an unusual URI is a signature.
4. **Record the arrival log, the peer address, and the interval distribution as the primary artefact, not the framework's session list** - client-side session state is not evidence.
5. **Measure detection honestly per telemetry source and run a negative control for every claim** - a "no alert" result without a control is not usable by the defender.
6. **Keep the profile under version control and record its hash with the results, so a later run is attributable to a known state** - the profile is the experiment, and it must be pinned.
7. **Run the callback infrastructure on domains and certificates you own and can take down, and verify the teardown before closing the engagement** - a live callback is a live exposure.
8. **Keep every artefact on the target outside the target's filesystem where the framework permits, and record what could not be kept out** - the dropped artefact is what a forensic review finds.
9. **Sequence the exercise to answer a specific detection question, and state that question before deployment** - an exercise with no question produces no usable result.
10. **Record every telemetry source that was SILENT, because the gap is the finding the defender needs** - the absence of a log is the highest-value output of this work.
11. **Complete the teardown checklist with timestamps, and list every unremoved item as an open item in the report** - the report is not finished until the infrastructure is down.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [c2-infrastructure-and-channel-design](../c2-infrastructure-and-channel-design/SKILL.md) - the infrastructure this operates
- [red-team-infrastructure](../attack-execution-atomic-tests/SKILL.md) - the test-execution discipline this shares
- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) - the channel inside the target network
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - when the beacon is blocked host-side
- [windows-postexploit](../windows-postexploit/SKILL.md) - the post-exploitation context the beacon serves
