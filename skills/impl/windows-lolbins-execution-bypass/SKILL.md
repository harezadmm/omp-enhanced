---
name: windows-lolbins-execution-bypass
description: >-
  Windows Living Off The Land Binaries (LOLBins) for execution, download, AWL bypass,
  UAC bypass and credential dumping. Use when a signed Microsoft binary is available and a
  custom tool would be flagged. Covers category selection and the defensive blind spot.
---

# SKILL: Windows LOLBins — Execution, Download, and Bypass

> **AI LOAD INSTRUCTION**: On a Windows host, the fastest way to run code without tripping
> application allowlisting is to use a **binary Windows already trusts**. There are 273
> documented LOLBins (LOLBAS project) covering 14 functional categories, and ~91 of them abuse
> `T1218` System Binary Proxy Execution alone. This skill covers the category decision tree and
> the specific mechanisms that matter operationally. Read §3 before choosing a binary: picking
> the wrong category is the most common failure.

## 0. RELATED ROUTING

- [windows-postexploit](../windows-postexploit/SKILL.md) — the surrounding post-exploitation flow
- [windows-privilege-escalation](../windows-privilege-escalation/SKILL.md) — local escalation beyond UAC
- [windows-av-evasion](../windows-av-evasion/SKILL.md) — when even a LOLBin is signature-flagged
- [living-off-the-land-lotl](../../core-subjects/living-off-the-land-lotl.md) — doctrine
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) — LOLBins as a lateral transport

---

## 1. WHY THIS WORKS

An application allowlist (AppLocker, WDAC) is built on trust decisions about **binaries**, not
about **behaviour**. `certutil.exe` is signed by Microsoft and present on every Windows host, so
it is allowed. It also downloads files, decodes base64, and writes Alternate Data Streams.

The defensive blind spot: these binaries are legitimate, so blocking them breaks the OS. The
control has to move to behavioural detection, and behavioural detection is where most
environments are weakest.

**The operational consequence:** prefer a LOLBin over your custom tool whenever one exists for
the job. Your tool has a signature; `certutil.exe` does not.

---

## 2. THE 14 CATEGORIES

Selection is by **category**, not by binary name. Establish what you need to do first.

| Category | Documented binaries | What it gives you |
|---|---|---|
| **Execute** | ~265 command entries | run arbitrary code — the core primitive |
| **Download** | ~62 | fetch a file from the internet |
| **AWL Bypass** | ~50 | specifically defeats application allowlisting |
| **ADS** | ~36 | write/read NTFS Alternate Data Streams (hiding) |
| **Dump** | ~21 | extract credentials or memory |
| **Copy** | ~13 | move files in a way that evades copy-based controls |
| **UAC Bypass** | ~9 | escalate from medium to high integrity |
| **Compile** | ~8 | compile code on-target (no toolchain needed on your side) |
| **Tamper** | ~6 | modify logs, AV config, or security settings |
| **Upload** | ~5 | exfiltrate to a remote endpoint |
| **Credentials** | ~5 | credential discovery |
| **Reconnaissance** | ~4 | host/domain enumeration |
| **Decode / Encode / Conceal** | ~4 | payload encoding and hiding |

**Rule:** if the task appears in this table, a LOLBin exists for it. Only fall back to a custom
binary when the task does not.

---

## 3. CATEGORY MECHANICS

### 3.1 System Binary Proxy Execution (`T1218`, 91 entries)

The largest single family: a trusted signed binary loads or executes attacker-controlled
content. Sub-techniques map to specific Windows components — `.011` is the Rundll32 family,
`.015` is `msdt`, `.007` is `msiexec`, `.010` is `regsvr32`, `.009` is the Management Console,
`.005` is `mshta`.

The pattern is always the same: **a Microsoft binary that takes a path or URL and executes it**.
Reason from that pattern rather than memorising the list — for any signed binary that accepts
`/path` or `http://`, check whether it executes rather than merely reads.

### 3.2 Signed Binary Proxy Execution via Interpreters (`T1127`, 56 entries)

Trusted developer utilities — the .NET compilers and the like — repurposed to run code. These
matter when the allowlist permits developer tooling but not `cmd.exe`.

### 3.3 Indirect Command Execution (`T1202`, 41 entries)

Windows utilities that spawn a child process. The parent is benign and allowed; the child is
yours. Defenders lose the causality unless they correlate parent-child.

### 3.4 Download (`T1105`, 72 entries)

Includes the classic certificate-utility download, the BITS transfer facility, and the scripting
hosts. Prefer a download channel that matches the host's normal behaviour — a server that should
not be fetching executables is the anomaly, not the tool.

### 3.5 Hidden Artifacts — ADS (`T1564.004`, 33 entries)

NTFS Alternate Data Streams let content live inside a file's metadata. `dir` does not show it by
default. Both the certificate utility and `expand.exe` can write streams.

### 3.6 OS Credential Dumping (`T1003.x`, ~30 entries)

Includes `ntds.dit` extraction and LSASS minidump paths. These are the highest-value and
most-detected operations in the set — see §5.

### 3.7 UAC Bypass (`T1548.002`, 8 entries)

Requires an administrative user in a medium-integrity context. The `fodhelper` and
`computerdefaults` auto-elevating binaries are the canonical routes: they read a registry key
that a medium-integrity user can write, then execute the value at high integrity. The technique
is: write the key, invoke the auto-elevating binary, clean the key.

### 3.8 Compile (`T1127.001`)

.NET compilers shipped with the framework. Code compiled on-target has no external signature,
which is the point.

---

## 4. SELECTION PROCEDURE

```
1. What is the task?                       → map to a §2 category
2. Is that category in the allowlist hole? → the whole point of §3
3. Does the binary exist on this host?     → check Full_Path before assuming
4. What is the detection surface?          → §5, decide before executing
5. Which is quieter: this LOLBin, or my tool?  → pick the quieter one
```

Step 3 matters: a LOLBin entry may list several paths across Windows versions, and a hardened
build may have removed it. Verify presence before building a chain on it.

---

## 5. DETECTION REALITY

These techniques are **not invisible**. Every one leaves a process tree. What they evade is
*static* detection (signatures, allowlists) — not *behavioural* detection.

| Signal | Which categories trip it |
|---|---|
| Signed binary spawning an unexpected child | proxy execution, indirect command execution |
| Download of an executable by a non-browser process | Download |
| LSASS handle open with read access | credential dumping |
| Registry write to a UAC-bypass key followed by process start | UAC bypass |
| Alternate Data Stream creation | ADS |
| Compiler process started outside a developer host | Compile |
| A binary execution that has no corresponding business reason | all |

**Decision point:** if the target environment has EDR with parent-child correlation, a LOLBin is
*quieter than a custom tool but not quiet*. Compare against
[windows-av-evasion](../windows-av-evasion/SKILL.md) and choose deliberately. Document which
signal you expected to trip — that is the finding.

---

## 6. CONFIRMING THE FINDING
LOLBin work has a specific trap: **a signed Microsoft binary being present is not a bypass, and a
command that would run is not a command that ran.** This table is the gate.

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the **command actually executed**, with its output or its effect observed? | the binary's presence proves nothing |
| 2 | Is the **signed binary's path and hash** recorded, and the sub-technique named? | the parent binary and the argument shape are the mechanism |
| 3 | Is the **control**: the same objective via a binary the policy DOES block, refused? | the difference attributable to the LOLBin |
| 4 | Is the **execution context** stated: user, integrity level, and any AppLocker/WDAC policy present? | a LOLBin bypass is policy-specific |
| 5 | Was the **child process or the network effect** observed, not just the exit code? | the objective is what the technique achieved |
| 6 | Is the **detection reality** acknowledged: which layer this is visible to? | command-line auditing and script-block logging see many of these |
| 7 | Is the finding the **policy gap**, not the binary? | the fix is the rule, not removing a Microsoft binary |

**An executed command with its observed effect, and a control binary that the policy blocks.** A LOLBin
list is a reference; the policy gap it demonstrates is the finding.

---

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the binary, full path, and exact command line | reproducibility |
| the category and the MITRE technique ID it maps to | lets the client check their own coverage |
| `whoami /priv` and integrity level before/after | proves the privilege outcome |
| whether the technique tripped a detection, and which | **the most valuable item** |
| the allowlist policy in force, if obtainable | proves the bypass was real and not a misconfiguration |

---

## 8. REMEDIATION REFERENCE

1. **Do not block the binaries** — the OS needs them. Move the control to behaviour.
2. **Parent-child correlation** — alert when a signed system binary spawns a process it has no business spawning.
3. **Command-line logging** — enable and forward it; most of these techniques are only visible there.
4. **Restrict interpreters on servers** — a server has no business running the scripting hosts or the .NET compilers; remove or block them.
5. **WDAC over AppLocker** — signature- and attribute-based policy narrows the `T1218` family considerably.
6. **Registry protection** — monitor the auto-elevating binary keys; a write there by a non-installer process is a high-fidelity UAC-bypass signal.
7. **LSASS protection** — enable RunAsPPL; it converts §3.6 from trivial to a driver-level problem.

---

## 9. EXECUTION PRIMITIVES

Section 2 gives the 14 categories and section 4 the selection procedure; this section is **how to prove a
lolbin finding on the host**. The claim "lolbins bypass application control" is unverifiable without an
**allowed-control** and a **blocked-control** on the same host, and a **telemetry export** that shows what
the execution actually produced.

### 8.1 The two controls that define the finding

```powershell
# A LOLBIN FINDING IS A PAIR OF RESULTS ON ONE HOST. Neither alone is a finding.
$ErrorActionPreference = "Continue"

Write-Host "=== 0. WHAT IS ENFORCING? (WDAC, AppLocker, or nothing) ==="
$wdac = Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard -ErrorAction SilentlyContinue
Write-Host "  WDAC CodeIntegrityPolicyEnforcementStatus: $($wdac.CodeIntegrityPolicyEnforcementStatus)"
Write-Host "  0 = off, 1 = audit only, 2 = ENFORCED. 'Enforced' is the only interesting case."
Write-Host "  CodeIntegrityPoliciesPresent: $($wdac.CodeIntegrityPolicyEnforcementStatus -ne 0)"
Write-Host ""
try {
  Write-Host "=== AppLocker policy in effect ==="
  Get-AppLockerPolicy -Effective -ErrorAction Stop | Select-Object -ExpandProperty RuleCollections |
    ForEach-Object { Write-Host ("  {0}: {1} rule(s), enforcement {2}" -f $_.CollectionType, $_.Count, $_.EnforcementMode) }
} catch { Write-Host "  AppLocker: not configured, or the module is unavailable" }
Write-Host ""
Write-Host "=== THE TWO CONTROLS ==="
Write-Host "  BLOCKED control : a RANDOMLY-NAMED, unsigned executable     -> MUST be blocked"
Write-Host "  ALLOWED control : a signed Microsoft binary (e.g. notepad)  -> MUST be allowed"
Write-Host "  If the BLOCKED control is NOT blocked, application control is off and there is NO finding."
Write-Host "  If the ALLOWED control is blocked, you are testing the wrong policy and nothing below applies."
Write-Host ""
Write-Host "=== 1. THE BLOCKED CONTROL, mechanically ==="
$probeDir = Join-Path $env:TEMP "ac-probe"; New-Item -ItemType Directory -Force -Path $probeDir | Out-Null
$probe = Join-Path $probeDir ("probe-" + [guid]::NewGuid().ToString('N').Substring(0,8) + ".exe")
Copy-Item "$env:SystemRoot\System32\notepad.exe" $probe -ErrorAction SilentlyContinue
Write-Host "  copied notepad to a RandomName.exe at: $probe"
Write-Host "  THE TEST: run it."
Write-Host "    a policy violation (Event 3077/8004, or a block dialog) = the control WORKS"
Write-Host "    it just runs                                                   = application control is OFF"
Write-Host ""
Write-Host "=== 2. THE ALLOWED CONTROL ==="
Write-Host "  the ORIGINAL $env:SystemRoot\System32\notepad.exe must RUN. If it does not, your test"
Write-Host "  environment is broken rather than the policy bypassed."
Write-Host ""
Write-Host "=== 3. THEN THE LOLBIN ==="
Write-Host "  only with both controls established does the lolbin's execution mean anything:"
Write-Host "  it means the policy allows THIS binary to perform THIS action."
```

**A blocked control and an allowed control on the same host.** If the blocked control is not blocked,
application control is off and the lolbin finding does not exist; if the allowed control is blocked, the
test environment is broken.

### 8.2 The telemetry, which is the actual finding

```powershell
Write-Host "=== THE TELEMETRY IS THE FINDING, and it is why lolbins matter ==="
Write-Host "  A lolbin is not interesting because it runs. It is interesting because of WHICH EVENTS it"
Write-Host "  produces, and whether the SOC can distinguish it from abuse. MEASURE THE EVENTS."
Write-Host ""
Write-Host "=== the event sources that record a process execution, in order of what they add ==="
$sources = @(
  @{n='Security 4688';    d='process creation, with the command line IF auditing is on'; what='the parent chain and the arguments'},
  @{n='Sysmon 1';         d='process create, with the full command line and hashes';      what='the argument detail'},
  @{n='Sysmon 3 / 22';    d='network connect / DNS query';                                what='whether it reached out, and to where'},
  @{n='Sysmon 11';        d='file create';                                                what='what it dropped, and where'},
  @{n='Sysmon 8 / 10';    d='CreateRemoteThread / process access';                        what='whether it injected'},
  @{n='PowerShell 4104';  d='script block logging';                                       what='the script, even when AMSI is bypassed'},
  @{n='module load 7';    d='image load';                                                 what='an unusual DLL in an unusual process'}
)
Write-Host ("{0,-20} {1,-52} {2}" -f 'source','what it records','what it uniquely adds')
foreach ($s in $sources) { Write-Host ("{0,-20} {1,-52} {2}" -f $s.n, $s.d, $s.wh) }
Write-Host ""
Write-Host "=== THE MEASUREMENT: run the lolbin and EXPORT ITS EVENTS ==="
Write-Host "  before: Get-WinEvent -LogName 'Microsoft-Windows-Sysmon/Operational' -MaxEvents 1 -> note the RecordId"
Write-Host "  run the lolbin with the action you are demonstrating"
Write-Host "  after : re-query and show the events the run PRODUCED"
Write-Host "  THE FINDING IS THE EVENT SET, not the execution. A lolbin that produces a clean,
Write-Host "  well-attributed event is a LESS interesting finding than one that produces none."
Write-Host ""
Write-Host "=== THE DETECTION REALITY, from section 5, made falsifiable ==="
Write-Host "  the claim 'this evades detection' must be tested by EXPORTING the alerts, and stating"
Write-Host "  the time window. Without the export, the claim supported is only 'it ran'."
```

**The finding is the event set, not the execution.** A lolbin producing a clean, well-attributed event is
less interesting than one producing none, and "evades detection" needs an exported alert set.

### 8.3 The category matrix as a proof grid

```python
print("=== THE 14 CATEGORIES AS A PROOF GRID, one row per candidate ===")
CATS = ["script interpreters", "compiled-with-known-signature", "command-line utilities",
        "signed binaries with a scripting flag", "installers and updaters", "archivers",
        "backup and recovery tools", "credential-adjacent tools", "wmic/wmi",
        "management frameworks", "office macros", "browsers", "developer tools", "file-transfer clients"]
for c in CATS:
    print(f"  {c:34} | policy allows? ____ | parent chain ____ | events produced ____ | goal ____")
print()
print("=== THE ROWS MUST BE FILLED BY RUNNING, NOT BY READING SECTION 3 ===")
print("  'wmic executes X' is a claim about a build. wmic is DEPRECATED and REMOVED from recent")
print("  Windows 11 builds, and 'certutil -urlcache' behaves differently across versions.")
print("  EVERY cell is a measurement on THIS host, and the report must say which build.")
print()
print("=== THE PARENT-CHAIN DIMENSION, which is what makes a lolbin suspicious or not ===")
print("  a signed binary is allowed by policy; what the SOC sees is (parent -> child, and the args)")
for a, b in [("winword.exe -> cmd.exe", "the classic macro chain; well-detected"),
             ("explorer.exe -> rundll32.exe", "user-initiated; moderately suspicious"),
             ("svchost.exe -> certutil.exe", "almost never benign; highly suspicious"),
             ("services.exe -> powershell.exe", "a service spawning PowerShell; highly suspicious"),
             ("your-agent.exe -> xcopy.exe", "the AV context matters; a benign parent is not blanket cover")]:
    print("  %-38s -> %s" % (a, b))
print()
print("=== THE GOAL, which the grid's last column must carry ===")
print("  'the lolbin ran' is not a goal. The goal is: a payload's EXECUTION, a FILE's download or")
print("  upload, a QUERY against a directory, or a CREDENTIAL operation. Name which.")
print()
print("=== THE RELIABILITY AND THE VERSION SCOPE ===")
print("  run each candidate N >= 5 times; some depend on the parent's integrity level or on a")
print("  race. And record the exact Windows BUILD: wmic's removal and the various PowerShell")
print("  version differences make 'it works' meaningless without the build number.")
```

**Every cell is a measurement on this host, and the build number is part of the result.** `wmic`'s removal
from recent Windows 11 builds is the concrete example.

### 8.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== LOLBIN ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the ENFORCEMENT state was established: WDAC status and AppLocker's effective policy",
  "with enforcement off there is no policy to bypass"),
 ("a BLOCKED control (a randomly-named unsigned executable) WAS blocked",
  "if not, application control is off and there is no finding"),
 ("an ALLOWED control (a signed system binary under its real name) WAS allowed",
  "if not, the test environment is broken"),
 ("the exact WINDOWS BUILD number is recorded",
  "wmic is removed from recent builds and behaviour differs by version"),
 ("the lolbin's execution was shown, with the PARENT CHILD chain and the full arguments",
  "the parent chain is what a SOC keys on"),
 ("the EVENTS the run produced were EXPORTED, with the time window",
  "the event set IS the finding, not the execution"),
 ("the claim 'evades detection' is supported by an exported alert set, not by 'it ran'",
  "'it ran' supports only 'not blocked'"),
 ("the category matrix's cells were filled by RUNNING each candidate, not by quoting section 3",
  "each cell is a measurement on this host"),
 ("the GOAL is named: payload execution, file transfer, a directory query, or a credential operation",
  "'the lolbin ran' is not a goal"),
 ("reliability was measured over N >= 5 runs per candidate",
  "some depend on the parent's integrity level or on a race"),
 ("the finding is scoped to the Windows build and the policy tested",
  "the remediation depends on both"),
]
for n, how in CHECKS: print("  [ ] %-70s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  enforcement : WDAC status, the AppLocker policy, the Windows build")
print("  controls    : the blocked control's block, and the allowed control's allowance")
print("  lolbin      : the binary, the parent chain, the arguments")
print("  events      : the exported event set, with the time window")
print("  goal        : what the lolbin achieved")
print("  scope       : build and policy, and the parent-chain context")
PY
```

**Controls, build, parent chain, exported events, goal, scope.** The parent chain is what a SOC keys on,
and the exports are what make "evades detection" a statement rather than a slogan.

---

## 10. RELATED SIBLINGS - LOAD TOGETHER

- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the layer model these events feed
- [windows-av-evasion](../windows-av-evasion/SKILL.md) - the product-specific controls for the same host
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the credential operations a lolbin is often used for
- [active-directory-certificate-services](../active-directory-certificate-services/SKILL.md) - a directory-side goal a lolbin may serve
- [malware-development-workflow](../malware-development-workflow/SKILL.md) - where the delivered payload is built
