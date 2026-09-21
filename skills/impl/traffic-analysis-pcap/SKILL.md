---
name: traffic-analysis-pcap
description: >-
  Traffic analysis and PCAP forensics playbook. Use when analyzing network captures including Wireshark filters, protocol analysis (HTTP/DNS/FTP/SMTP/USB/WiFi), data extraction, covert channel detection, PCAP repair, TLS decryption, and tshark command-line analysis.
---

# SKILL: Traffic Analysis & PCAP — Expert Analysis Playbook

> **AI LOAD INSTRUCTION**: Expert traffic analysis and PCAP forensics techniques. Covers PCAP repair, Wireshark essential filters, protocol-specific analysis (HTTP, HTTPS/TLS, DNS, FTP, SMTP, USB HID, WiFi, ICMP), data extraction (file carving, credential harvesting, covert channels), NetworkMiner, and tshark CLI analysis. Base models miss USB keyboard decode patterns, DNS tunneling detection heuristics, and TLS decryption workflows.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [memory-forensics-volatility](../memory-forensics-volatility/SKILL.md) for correlating memory artefacts with network traffic
- [steganography-techniques](../steganography-techniques/SKILL.md) for analyzing files extracted from traffic captures
- [network-protocol-attacks](../network-protocol-attacks/SKILL.md) for understanding attack patterns visible in captures
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) for identifying shell traffic in captures

---

## 1. PCAP REPAIR

```bash
pcapfix corrupted.pcap -o fixed.pcap           # repair corrupted PCAP
# Magic bytes: d4c3b2a1=pcap(LE), a1b2c3d4=pcap(BE), 0a0d0d0a=pcapng
editcap -F pcap capture.pcapng capture.pcap    # convert pcapng→pcap
mergecap -w merged.pcap file1.pcap file2.pcap  # merge captures
```

---

## 2. WIRESHARK ESSENTIAL FILTERS

### IP / Host Filters

```
ip.addr == 10.0.0.1                  # source or destination
ip.src == 10.0.0.1                   # source only
ip.dst == 10.0.0.1                   # destination only
ip.addr == 10.0.0.0/24              # subnet
!(ip.addr == 10.0.0.1)              # exclude host
```

### Protocol Filters

```
http                                  # all HTTP
dns                                   # all DNS
tcp                                   # all TCP
ftp                                   # all FTP
smtp                                  # all SMTP
tls                                   # all TLS/SSL
icmp                                  # all ICMP
arp                                   # all ARP
```

### TCP / Stream

```
tcp.stream eq 5                       # follow specific TCP stream
tcp.port == 80                        # traffic on port 80
tcp.flags.syn == 1 && tcp.flags.ack == 0   # SYN packets (connection starts)
tcp.analysis.retransmission           # retransmitted packets
tcp.len > 0                           # packets with payload
```

### HTTP

```
http.request.method == "POST"         # POST requests
http.request.method == "GET"          # GET requests
http.response.code == 200             # successful responses
http.response.code >= 400             # error responses
http.request.uri contains "login"     # URI contains string
http.host contains "target.com"       # specific host
http.content_type contains "json"     # JSON responses
http.cookie contains "session"        # session cookies
http.request.full_uri                 # show full URIs (column)
```

### DNS

```
dns.qry.name contains "evil.com"     # specific domain queries
dns.qry.type == 1                    # A records
dns.qry.type == 28                   # AAAA records
dns.qry.type == 16                   # TXT records
dns.flags.response == 1              # DNS responses only
dns.resp.len > 100                   # large DNS responses
```

### TLS

```
tls.handshake.type == 1              # Client Hello
tls.handshake.type == 2              # Server Hello
tls.handshake.extensions.server_name  # SNI (hostname)
tls.handshake.type == 11             # Certificate
```

### Content Search

```
frame contains "password"             # search in raw bytes
frame contains "flag{"                # CTF flag pattern
tcp contains "admin"                  # search in TCP payload
```

---

## 3. PROTOCOL ANALYSIS

### HTTP — Follow Stream & Extract

```
Right-click packet → Follow → TCP Stream
# Shows full HTTP request/response conversation

# File extraction:
# File → Export Objects → HTTP → Save All

# Useful filters for credential hunting:
http.request.method == "POST" && frame contains "password"
http.request.method == "POST" && frame contains "login"
http.authbasic                        # Basic auth (base64 encoded)
```

### HTTPS / TLS Decryption

```bash
# Method 1: SSLKEYLOGFILE (pre-master secrets from browser)
# Set environment variable BEFORE opening browser:
export SSLKEYLOGFILE=/tmp/sslkeys.log
firefox https://target.com

# Wireshark: Edit → Preferences → Protocols → TLS
# → (Pre)-Master-Secret log filename: /tmp/sslkeys.log

# Method 2: Server private key (for RSA key exchange only)
# Wireshark: Edit → Preferences → Protocols → TLS → RSA keys list
# → Add: IP, Port, Protocol, Key file (.pem)
```

### DNS — Tunneling Detection

```bash
# Indicators of DNS tunneling:
# 1. Unusually long subdomain names (>30 chars)
# 2. High volume of TXT record queries/responses
# 3. Consistent query patterns to same domain
# 4. Base32/Base64-like subdomain strings
# 5. High query frequency from single host

# Wireshark filter for suspicious DNS:
dns.qry.name.len > 50                # long query names
dns.qry.type == 16                   # TXT records (common for tunneling)
dns.resp.len > 512                   # large DNS responses

# tshark extraction:
tshark -r capture.pcap -Y "dns.qry.type==16" -T fields -e dns.qry.name
```

### FTP — Credential & File Extraction

```bash
# FTP credentials (plaintext)
# Filter: ftp.request.command == "USER" || ftp.request.command == "PASS"

# FTP file transfer reconstruction:
# FTP uses separate data channel (usually port 20 or dynamic)
# Follow TCP stream of data connection to extract file

# tshark:
tshark -r capture.pcap -Y "ftp.request.command==USER || ftp.request.command==PASS" -T fields -e ftp.request.arg
```

### SMTP — Email Content Extraction

```bash
# Follow TCP stream → MAIL FROM/RCPT TO/DATA sections
# Attachments: base64 in MIME → decode Content-Transfer-Encoding blocks
# Filters:
smtp.req.command == "AUTH"            # authentication (often base64)
smtp contains "Content-Disposition: attachment"   # attachments
```

### USB — Keyboard HID Capture Decode

```bash
# USB HID keyboard traffic: interrupt transfers with 8-byte data
# Filter: usb.transfer_type == 0x01

# Extract keystrokes:
tshark -r usb.pcap -Y "usb.capdata && usb.data_len == 8" -T fields -e usb.capdata > keystrokes.txt

# HID keycode layout: byte[0]=modifier, byte[2]=keycode
# 0x04=a..0x1d=z, 0x1e=1..0x27=0, 0x28=Enter, 0x2c=Space
# Use Python/online HID decoder to convert keycodes → text
```

### WiFi — WPA Handshake

```bash
# Capture: airodump-ng --bssid AP_MAC -w capture wlan0mon
# Convert + crack: hcxpcapngtool -o hash.hc22000 capture.pcap
hashcat -m 22000 hash.hc22000 wordlist.txt
# Deauth detection: wlan.fc.type_subtype == 0x0c
```

### ICMP — Data Exfiltration

```bash
# ICMP payload analysis
# Normal ping: 32 or 64 bytes of pattern data
# Exfiltration: meaningful data in ICMP payload

# Filter:
icmp && data.len > 48                 # unusual ICMP payload size
icmp.type == 8                        # echo requests

# Extract ICMP payloads:
tshark -r capture.pcap -Y "icmp.type==8" -T fields -e data.data
```

---

## 4. DATA EXTRACTION

### File Carving

```bash
# Wireshark: File → Export Objects
# Supported: HTTP, SMB, TFTP, IMF (email), DICOM

# Manual from reassembled stream:
# Follow TCP Stream → Show as Raw → Save As

# binwalk on exported stream data
binwalk -e exported_stream.bin
foremost -i exported_stream.bin -o carved/
```

### Credential Harvesting

```bash
# Plaintext: ftp || telnet || http.authbasic || smtp || pop || imap
# NTLM: ntlmssp.auth.username → extract challenge/response from NTLMSSP messages
# Hash format: user::domain:challenge:NTProofStr:blob → hashcat -m 5600
```

### Covert Channel Detection

Indicators: DNS with long subdomains, ICMP with large payloads, HTTP with encoded headers, regular beacon intervals (C2). Use `tshark -q -z io,stat,1` and `-z conv,tcp` for statistical anomaly detection.

---

## 5. NETWORKMINER

```bash
# Automated PCAP analysis: sudo apt install networkminer
# Open PCAP → auto-extracts: Files, Images, Credentials, Sessions, DNS
# Files tab: carved from HTTP/SMB/FTP | Credentials tab: plaintext creds
```

---

## 6. TSHARK COMMAND-LINE ANALYSIS

```bash
tshark -r capture.pcap -Y "http.request" -T fields -e http.host -e http.request.uri
tshark -r capture.pcap -Y "dns.flags.response==0" -T fields -e dns.qry.name | sort -u
tshark -r capture.pcap -Y "http.request.method==POST" -T fields -e http.file_data
tshark -r capture.pcap -q -z io,stat,1                # I/O graph
tshark -r capture.pcap -q -z conv,tcp                  # TCP conversations
tshark -r capture.pcap -q -z endpoints,ip              # IP endpoints
tshark -r capture.pcap -q -z io,phs                    # protocol hierarchy
tshark -r capture.pcap -q -z follow,tcp,ascii,0        # follow stream 0
tshark -r capture.pcap --export-objects http,/tmp/exported/
```

---

## 7. DECISION TREE

```
PCAP file for analysis
│
├── File won't open?
│   ├── Check magic bytes: xxd | head (§1)
│   ├── Repair: pcapfix (§1)
│   └── Convert: editcap pcapng→pcap (§1)
│
├── What's in the capture? (Quick overview)
│   ├── tshark -q -z io,phs (protocol hierarchy) (§6)
│   ├── tshark -q -z conv,tcp (conversations) (§6)
│   └── tshark -q -z endpoints,ip (endpoints) (§6)
│
├── HTTP traffic?
│   ├── Export objects: File → Export Objects → HTTP (§4)
│   ├── Credential hunt: POST + password/login filters (§3)
│   ├── Follow streams: interesting request/response pairs (§3)
│   └── Encrypted (HTTPS)? → need SSLKEYLOGFILE or RSA key (§3)
│
├── DNS traffic?
│   ├── Long subdomains? → DNS tunneling (§3)
│   ├── High TXT record volume? → DNS exfiltration (§3)
│   ├── Extract all queries: tshark -Y dns -T fields -e dns.qry.name (§6)
│   └── DNS rebinding? → check for alternating A record responses
│
├── FTP / Telnet / SMTP?
│   ├── Extract credentials (plaintext) (§3)
│   ├── Reconstruct file transfers (follow data stream) (§3)
│   └── Email content and attachments (base64 decode) (§3)
│
├── USB traffic?
│   ├── Keyboard HID → decode keystrokes (§3)
│   ├── Storage → extract transferred files
│   └── Check transfer_type and data_len fields
│
├── WiFi traffic?
│   ├── WPA handshake → crack with hashcat (§3)
│   ├── Deauth frames → detect attack (§3)
│   └── Probe requests → device fingerprinting
│
├── ICMP traffic?
│   ├── Large/variable payloads → data exfiltration (§3)
│   ├── Regular pattern → ICMP tunnel (§3)
│   └── Extract payloads: tshark -Y icmp -T fields -e data.data
│
├── Suspicious patterns?
│   ├── Regular beacon interval → C2 communication (§4)
│   ├── Unusual port/protocol combos → covert channel (§4)
│   ├── High volume to single external IP → data exfil (§4)
│   └── Encrypted traffic without SNI → suspicious tunnel
│
└── Need automated extraction?
    ├── NetworkMiner for files/creds/images (§5)
    ├── tshark --export-objects for HTTP/SMB files (§6)
    └── binwalk/foremost on exported streams (§4)
```

---

## 8. CONFIRMING THE FINDING

A packet capture is the most over-claimed evidence in security work, because **a viewer's display is not
the wire and a decoded field is not a fact.** This table is the discipline.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **capture point** recorded, and is it on the path you claim? | a capture off-path proves nothing about the path |
| 2 | Was the capture **complete** before repair, and what was lost? | snaplen, drops, and gaps change conclusions |
| 3 | Are the **timestamps** trustworthy, and what is their resolution and offset? | ordering must be anchored, not assumed |
| 4 | Is the claim **reproducible from the bytes**, by a second tool? | a display is an interpretation |
| 5 | Is there a **control flow** that behaves differently? | a differential, not a single stream |
| 6 | Are **reassembled artefacts** hashed before and after extraction? | extraction must not alter the evidence |
| 7 | Does the claim name the **protocol layer** it lives at? | L2 and L7 claims have different proofs |

**A capture point recorded, a completeness statement, honest timestamps, and a second tool reproducing the
reading from the raw bytes.** A Wireshark display is an interpretation of bytes, and the bytes are the evidence.

---

## 9. EXECUTION PRIMITIVES

This domain's central hazard is that **the tool's display becomes the finding**. Every claim below reduces
to: the capture's provenance, the raw bytes, and a second tool reading them the same way.

### 8.1 The capture's provenance, before any analysis

```bash
# THE CAPTURE POINT IS THE FIRST FINDING. Without it, no reading is attributable.
PCAP="${PCAP:?the capture file}"
echo "=== 1. what the file actually is, from its own headers ==="
capinfos "$PCAP" 2>&1 | tee /tmp/capinfos.txt
cat <<'PROV'
  RECORD FROM capinfos, AND PUT IN THE REPORT:
    the capture TYPE and the LINK TYPE  -> Ethernet, Linux cooked (any), raw IP, a tunnel... a
                                          WRONG link type silently misaligns EVERY frame
    the packet count, the duration, and the start/end times
    the SNAPLEN                          -> a snaplen below the frame size TRUNCATED the bytes, and
                                            a conclusion about content MAY BE WRONG
    the INTERFACE, if recorded
  AND THE QUESTION NOBODY ASKS: WHERE WAS THE CAPTURE TAKEN?
    on the endpoint (a host's own NIC) -> it sees that host's traffic, and NOT the switch's other ports
    on a SPAN/mirror port             -> it sees what the mirror was CONFIGURED to send, which may
                                          drop frames under load or omit VLAN tags
    on a TAP                          -> it sees the full duplex link, which is the strongest position
    on a FIREWALL or a proxy's log    -> it is NOT a capture; it is the device's own event record
    IN A VM's virtual switch          -> it sees only that VM's traffic
  A CLAIM ABOUT A PATH FROM A CAPTURE NOT ON THAT PATH IS THE FAMILY'S MAIN ERROR.
PROV
echo
echo "=== 2. completeness, before repair ==="
tshark -r "$PCAP" -q -z io,stat,0 2>/dev/null | head -20
echo "  and the drop counters, if the capture recorded them:"
capinfos -a "$PCAP" 2>/dev/null | grep -iE 'drop|truncat|error' || \
  echo "  (the file does not record drops; SAY SO - a capture is not automatically complete)"
echo
echo "=== 3. the timestamps, which decide every ordering claim ==="
capinfos -a -e "$PCAP" 2>/dev/null | grep -iE 'time|duration' | head -10
cat <<'TIME'
  THE TIMESTAMP DISCIPLINE - get this wrong and every timeline is wrong:
    RESOLUTION : a capture at microsecond resolution cannot order two events that the log
                 timestamps at second resolution. STATE THE FINEST RESOLUTION PRESENT.
    OFFSET     : the capture host's clock, the endpoint's clock, and the device's clock are
                 THREE DIFFERENT CLOCKS. An event ordering ACROSS them is a hypothesis until
                 the offsets are established from a shared event.
    THE ANCHOR : find an event present in BOTH the capture AND the other source, and use it as
                 the anchor. THAT is what makes a cross-source timeline valid.
  A TIMELINE BUILT BY SORTING TIMESTAMPS FROM DIFFERENT CLOCKS IS NOT A TIMELINE.
TIME
```

**A claim about a path from a capture not on that path is the family's main error**, and a timeline built by
sorting timestamps from different clocks is not a timeline — it needs a shared anchor event.

### 8.2 The reading, reproducibly, from the bytes

```bash
echo "=== THE TWO-TOOL RULE: every claim reproduced from the raw bytes ==="
cat <<'TWOTOOL'
  WIRESHARK'S DISPLAY IS AN INTERPRETATION, AND THE DISSECTOR CAN BE WRONG OR MISLED.
  THE RULE: any structural claim is re-derived with a SECOND, INDEPENDENT tool on the SAME bytes.
    - a field value      -> re-extract with tshark's -T fields, or with python/scapy, from the file
    - a reassembled payload -> re-carve it a second way and COMPARE HASHES
    - a "the protocol is X" -> confirm from the transcript bytes, not from the dissector's label
  AND THE DISSECTOR-FAILURE CASES THAT MATTER HERE:
    - a NON-STANDARD PORT carrying a protocol: the dissector may label it wrongly, and "Decode As"
      is a HYPOTHESIS. Read the bytes.
    - a MALFORMED or deliberately odd frame: a dissector may DESYNCHRONISE and show garbage after it.
    - ENCAPSULATION the dissector does not know: the payload appears as raw bytes.
  IN EACH CASE THE RAW HEX IS THE TRUTH AND THE DISPLAY IS A PROPOSAL.
TWOTOOL
echo
echo "=== the extraction, with the hash-before and hash-after ==="
mkdir -p /tmp/ex && cd /tmp/ex
tshark -r "$PCAP" -T fields -e data.data -Y 'frame.number==1' 2>/dev/null | head -1 > /tmp/ex/probe.hex
echo "  record: the FRAME NUMBER, the byte OFFSET within it, the LENGTH, and the SHA256 of the bytes."
echo "  an extracted artefact whose hash CHANGES between runs is not reproducible, and that must be"
echo "  investigated before the artefact is reported."
echo
echo "=== OBJECT EXPORT, and what 'follow stream' actually gives you ==="
cat <<'STREAM'
  'Follow TCP Stream' shows the REASSEMBLED application data as the dissector reconstructed it.
  IT IS NOT A FILE, and the following must be recorded for any exported artefact:
    - the stream index, the endpoints, and the SEQUENCE ranges covered
    - whether the reassembly was CONTIGUOUS or had GAPS (a gap means the artefact is INCOMPLETE)
    - retransmissions: a stream with retransmissions may have DUPLICATE bytes, and a naive carve
      will corrupt the artefact
    - the direction: a stream is BIDIRECTIONAL, and the request and the response are different
      artefacts
  THE CONTROL: if the artefact is a file, its hash must match the hash obtained by ANY other
  legitimate acquisition of the same file. A mismatch means the reassembly altered it.
STREAM
```

**The raw hex is the truth and the display is a proposal**, and an exported artefact needs its stream
index, coverage, gaps, and direction recorded — plus a hash that a second acquisition reproduces.

### 8.3 The differential, and the goal

```bash
echo "=== THE CONTROL FLOW: a capture claim needs a DIFFERENTIAL, not one stream ==="
cat <<'DIFF'
  A SINGLE INTERESTING STREAM IS A CURIOSITY. THE FINDING IS THE DIFFERENCE:
    the SAME request that SUCCEEDED vs the one that FAILED
    the SAME flow before and after a configuration change
    a normal session vs the suspect session, differing in ONE observable
  AND THE FILTERS THAT PRODUCE IT MUST BE RECORDED EXACTLY, because a display filter that
  accidentally excludes the control's packets produces a FALSE differential - the commonest
  analysis error here.
  RECORD: the filter string, the frame numbers matched, and the frame numbers the CONTROL matched.
DIFF
echo
echo "=== the three-layer discipline: say which layer the claim lives at ==="
python3 - <<'PY'
L = [("L2 (frames, MAC, VLAN)", "the capture point's own visibility", "a claim about a host NOT on the capture path is invalid"),
     ("L3 (IP)",              "routing and addressing",           "a NAT device means the addresses differ per side"),
     ("L4 (TCP/UDP)",         "the flow",                        "retransmissions and resets indicate path behaviour"),
     ("L7 (application)",     "the payload",                      "reassembly, encoding, and compression apply - read the bytes twice")]
print("%-24s %-34s %s" % ("layer","what it evidences","the trap"))
for a,b,c in L: print("%-24s %-34s %s" % (a,b,c))
print()
print("  A CAPTURE ALSO HAS ITS OWN LAYER-0 CAVEAT: if the capture point is BEHIND a NAT, a proxy, or")
print("  a load balancer, the addresses and the payload seen may differ from what the SERVER processed.")
print("  STATE WHERE YOU CAPTURED, AND THEREFORE WHAT YOU CAN AND CANNOT CONCLUDE.")
PY
echo
echo "=== THE GOAL, and the evidence each needs ==="
cat <<'GOAL'
  'we saw suspicious traffic'              -> NOT a finding; it names no observable
  'a protocol ran on a non-standard port'  -> a protocol-identification finding (bytes required)
  'a credential was transmitted'           -> a CREDENTIAL-EXPOSURE finding (the transcript, and
                                              WHETHER the channel was protected)
  'a file was transferred'                 -> a DATA-TRANSFER finding (the artefact + its hash +
                                              the stream's coverage)
  'a host contacted a known-bad endpoint'  -> an ATTRIBUTION finding (the resolution chain, and
                                              WHETHER it resolved through a shared or CDN address -
                                              a shared CDN IP is NOT attribution)
  'a timeline shows a sequence'           -> a TIMELINE finding (the anchor event across clocks)
  NAME IT, and give the evidence that class needs.
GOAL
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== PCAP / TRAFFIC ANALYSIS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the CAPTURE POINT is recorded, and it lies on the path the claim concerns",
  "a claim about a path from an off-path capture is the main error in this family"),
 ("capinfos was read: the link type, the snaplen, the counts, and the duration",
  "a wrong link type misaligns every frame; a short snaplen truncates content"),
 ("the SNAPLEN was checked against the frame sizes, and truncation is stated if present",
  "a content conclusion may be unsound with truncated bytes"),
 ("completeness is stated: drops, gaps, or an explicit admission that they cannot be determined",
  "a capture is not automatically complete"),
 ("timestamp RESOLUTION, OFFSET, and the ANCHOR EVENT across sources are recorded",
  "sorting timestamps from different clocks is not a timeline"),
 ("every structural claim was reproduced with a SECOND, independent tool on the same bytes",
  "a dissector's display is an interpretation"),
 ("for a protocol on a non-standard port, the BYTES were read, not the dissector's label",
  "'Decode As' is a hypothesis"),
 ("any exported artefact has its stream index, coverage, gaps, direction, and a stable hash",
  "reassembly can alter or duplicate bytes"),
 ("the artefact's hash matches a second legitimate acquisition of the same file",
  "the control that extraction did not change it"),
 ("a DIFFERENTIAL is present: a control flow differing in one observable",
  "a single interesting stream is a curiosity, not a finding"),
 ("the display filters for both the finding and the control are recorded exactly",
  "an accidental exclusion produces a false differential"),
 ("the claim's LAYER is named, and NAT/proxy/LB positions are stated as caveats",
  "the addresses seen may differ from what the server processed"),
 ("a CDN or shared address is NOT treated as attribution",
  "many hosts share a CDN IP"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  provenance : the capture point, the link type, the snaplen, the completeness")
print("  time       : resolution, offsets, and the anchor event across clocks")
print("  reading    : the raw bytes, the second tool's agreement, the filters used")
print("  artefact   : the stream, the coverage, the gaps, the direction, the hash")
print("  differential: the control flow, and the one observable that differs")
print("  layer      : which layer the claim lives at, with NAT/proxy caveats")
PY
```
---

## 10. EVIDENCE STANDARD
| Item | Why |
|---|---|
| The **capture point** and the interface, with the direction | a capture off-path proves nothing about the path you claim |
| The **snaplen**, the timestamp resolution, and the NIC's offload state | a truncated frame and an offloaded checksum both change what a decode means |
| The **two-tool reproduction**: the same fact read from the same bytes by a second parser | Wireshark's display is an interpretation, and the bytes are the evidence |
| The **stream or frame index**, and the filter that isolated it | a claim about a stream must name which one |
| The **field's raw bytes** where a decoded value is cited | a decoded field is the dissector's opinion of the bytes |
| The **time anchor** across any two captures, with its offset | unanchored cross-capture timing is a hypothesis |
| What the capture **cannot show** (encrypted payload, a mid-stream start, dropped frames) | the negative bound is part of the finding |

### Interpretation failures — how they mislead

| Failure | How it misleads |
|---|---|
| A **display filter** treated as the observed data | the filter hides everything else; the absence is the filter's, not the network's |
| A **reassembled stream** read as a single packet | segmentation and retransmission are invisible in the reassembly |
| A **decoded field** cited without its bytes | the dissector version changes the decode |
| **TCP retransmission** read as a duplicate request | the application sent one request; the network delivered it twice |
| A **checksum error** taken as corruption | NIC offload writes a placeholder; the wire checksum was valid |
| **Timestamp-based ordering** across two captures | two clocks, and no anchor |
| An **absent packet** treated as a blocked packet | dropped by the capture, dropped by the kernel, or never sent |

| Item | Why |
|---|---|
| The capture's provenance: where, when, on what, with what snaplen | the four facts that make a packet claim reproducible |
| The **exact filter** and the frame/stream index behind every claim | a claim about traffic must name the traffic |
| The **raw bytes** for any decoded field that carries the finding | the dissector is an interpretation |
| The **second parser's** agreement, from the same bytes | the reproduction that separates the tool's display from the evidence |
| The **time anchor** and offset for any cross-capture timing | clock skew makes the ordering a claim |
| The **negative bound**: what the capture structurally cannot show | encryption, a mid-stream start, and drop are limits, not absences |
| The **capture point's position** relative to the claimed path | an off-path capture proves nothing about the path |

**The display is an interpretation and the bytes are the evidence** — every decoded value that carries the
finding gets reproduced from the raw bytes by a second parser, and the capture's point, snaplen, and time
anchor are recorded with it.

---

## 11. REMEDIATION REFERENCE

Fix advice for a packet-level claim is about **what the capture can and cannot establish**, and what the
defender should change.

1. **Do not remediate from a display.** A finding derived from Wireshark's reassembled view must be
   restated in bytes before it becomes a fix requirement, or the fix addresses the tool's rendering.
2. **Fix at the layer that owns the property.** A decryptable credential in transit is a TLS-configuration
   problem, not a "capture" problem; a missing segmentation control is a network-policy problem.
3. **State the control point.** "Isolate the segment" is actionable; "monitor the traffic" is not.
4. **Note what the fix does not cover.** Full-path encryption does not remove metadata; segmentation does
   not remove an endpoint that already holds the credential.
5. **Keep the negative bound.** Where the capture could not see the payload, say so, and do not let the
   absence be read as an assurance.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER
- [memory-forensics-volatility](../memory-forensics-volatility/SKILL.md) - the endpoint-side acquisition that anchors a timeline
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - the provenance discipline the same evidence feeds
- [steganography-techniques](../steganography-techniques/SKILL.md) - where a covered channel hides the payload a capture shows
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the edge layer a capture may or may not see
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) - the channel whose capture is this domain's subject
