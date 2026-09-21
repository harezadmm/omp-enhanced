---
name: edr-bypass-techniques
description: >-
  Evading endpoint detection and response. Use in an authorised red-team engagement when a
  payload is being detected, or when validating whether an EDR deployment actually provides
  coverage. Covers the detection layers, the bypass per layer, and the honest limits of each.
---

# SKILL: EDR Bypass Techniques

> **AI LOAD INSTRUCTION**: An EDR is not antivirus. AV matches signatures; EDR correlates
> *behaviour* across process, memory, registry, file and network telemetry, usually with kernel
> visibility. Defeating it is a layered exercise, and **no single technique defeats a mature
> deployment**. This skill maps the detection layers to the bypass per layer, and states honestly
> where each fails. Use only with written authorisation — the techniques are indistinguishable
> from malware at the artefact level.

## 0. RELATED ROUTING

- [windows-av-evasion](../windows-av-evasion/SKILL.md) — signature-level evasion
- [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md) — avoiding custom binaries entirely
- [attack-execution-atomic-tests](../attack-execution-atomic-tests/SKILL.md) — validating detection coverage
- [malware-development-pipeline](../../core-subjects/malware-development-pipeline.md) — implant construction doctrine
- [c2-infrastructure-and-channel-design](../c2-infrastructure-and-channel-design/SKILL.md) — the network half of the problem
- [5-gateway-evasion](../../core-subjects/5-gateway-evasion.md) — perimeter evasion doctrine

---

## 1. THE DETECTION LAYERS

Understand the stack before picking a technique. Each layer has a different bypass and a
different cost.

| Layer | Mechanism | Visibility |
|---|---|---|
| **Static / signature** | file hash, byte pattern, string | file on disk |
| **Heuristic / emulation** | sandbox-execute the file, score behaviour | file, in a VM |
| **Userland API hooks** | EDR DLL injected into every process, hooking `ntdll`/Win32 | API calls from userland |
| **Kernel callbacks** | `PsSetCreateProcessNotifyRoutine`, ObRegisterCallbacks, minifilter | process/thread/file/handle events, **unhookable from userland** |
| **ETW** | Microsoft-Windows-Threat-Intelligence provider | memory, injection, .NET events |
| **AMSI** | scans script content before execution | PowerShell, VBScript, JScript, .NET |
| **Memory scanning** | periodic scan of process memory for known patterns | injected payloads |
| **Telemetry correlation** | central analysis of the above | the whole chain, in aggregate |

**The pivot to understand:** userland hooks are bypassable and kernel callbacks are not. Modern
bypass therefore aims at (a) avoiding the API call entirely, (b) using a path the callback does
not cover, or (c) getting the kernel to not report — which requires a vulnerable driver.

---

## 2. BYPASS PER LAYER

### 2.1 Static signature

| Technique | Note |
|---|---|
| Recompile with changed structure | changes the hash; heuristics remain |
| Encrypt/encode the payload, decrypt at runtime | defeats static match, not emulation |
| Remove strings/imports | `IAT`-less loading |
| Pad / strip metadata | changes hash; cosmetic only |
| Custom loader | the durable approach |

### 2.2 AMSI

AMSI scans script and .NET content **before** execution. Bypasses are version-specific and
fragile — a patch or a signature update kills them.

| Approach | Note |
|---|---|
| Patch by name | `amsi.dll` now often in-memory only; name lookup may fail |
| Patch by content signature | scan for the function pattern in memory |
| Register a "clean" AMSI provider | a documented interface; the EDR's provider still wins |
| Force an error state | make the initialisation fail so no scanning occurs |
| Avoid AMSI entirely | run in a process with no AMSI — a LOLBin, an unmanaged host, a non-scripting loader |

**The reliable approach is the last one.** Any in-memory patch is a race against the next
signature update; not using an AMSI-covered execution path has no such race.

### 2.3 Userland hooks

| Technique | Note |
|---|---|
| Unhook | restore the original `ntdll` from a fresh copy on disk or from a suspended process |
| Direct syscalls | build the syscall stub yourself, never call the hooked export |
| Indirect syscalls | jump to the syscall instruction inside `ntdll` — leaves a clean-looking call stack |
| Call-stack spoofing | manipulate the return address chain to look like a legitimate caller |
| Hardware breakpoints | use debug registers instead of a patched instruction |

**Call-stack inspection defeats naive direct syscalls.** Modern EDRs walk the stack to check
that the syscall originated from a legitimate module. Direct syscalls produce an obviously
wrong stack; indirect syscalls and stack spoofing exist specifically to fix that. If the target
EDR does stack analysis, direct syscalls *increase* your detection probability.

### 2.4 Kernel callbacks

Not bypassable from userland. The options are narrow:

| Option | Reality |
|---|---|
| Bring Your Own Vulnerable Driver (BYOVD) | load a signed vulnerable driver to kill or blind the EDR from kernel |
| Exploit a driver vulnerability | same, with more risk |
| Avoid the monitored call | the practical choice — use a mechanism the callback does not cover |
| Boot-time persistence | disable the EDR before it starts |

**BYOVD is high-risk and typically out of scope.** It requires an administrative context to
load a driver, and loading a known-vulnerable driver is itself a high-fidelity detection
(and can bugcheck the host — a production outage). Treat it as a documented possibility, not a
default technique.

### 2.5 Memory scanning

| Technique | Note |
|---|---|
| Encrypt the payload in memory | decrypt only at the moment of use |
| Sleep obfuscation | re-encrypt during the idle window; the payload is only plaintext briefly |
| Module stomping / phantom DLL | hide inside a legitimately loaded module |
| Heap/private-memory evasion | avoid `PAGE_EXECUTE_READWRITE` private regions — the classic scanner target |

**`RWX` private memory is the single strongest indicator an EDR has.** Memory allocated
read-write-execute, unbacked by a file, in a process that nobody injected into, is the pattern
the scanner is built to find. Avoid it.

---

## 3. THE ESCALATION LADDER

Work up only as far as needed. Each step costs effort and adds its own signal.

```
1. Don't bring a binary at all     → LOLBin, existing tool, script (see windows-lolbins)
2. Different execution path        → unmanaged process, no AMSI coverage
3. Custom loader, encrypted payload → defeats static + emulation
4. Indirect syscalls + stack spoof → defeats userland hooks + naive stack checks
5. Sleep obfuscation               → defeats periodic memory scan
6. Avoid RWX private memory        → removes the strongest single indicator
7. [not recommended] driver-level  → high risk, high detection, possible outage
```

**Step 1 is the most underrated.** If the objective can be met with a signed Microsoft binary,
no amount of loader engineering is as effective as not having a loader.

---

## 4. WHAT ACTUALLY GETS YOU CAUGHT

Honest failure modes — these are where attempts collapse.

| Signal | Why it happens |
|---|---|
| **Call stack does not match the API** | direct syscalls without spoofing |
| **RWX private memory** | the loader allocated it and never fixed the protection |
| **Payload in plaintext too long** | sleep obfuscation not implemented, or the wrong window |
| **Parent-child anomaly** | `winword.exe` spawning `cmd.exe` — no bypass helps |
| **Command line** | the objective's text is in the command line regardless of the loader |
| **Network beacon** | endpoint evasion done, network ignored entirely |
| **Signature after an update** | a bypass that was clean last week |
| **Telemetry correlation** | each individual event is unremarkable; the sequence is damning |

**The last one is the point.** EDR value is in correlation, not in any single event. A
technique that only considers its own layer will pass its own test and fail the deployment.

---

## 5. VALIDATION, NOT ASSUMPTION

A bypass is a **hypothesis** until tested against the actual target deployment.

```
1. Establish a baseline: does the un-obfuscated payload get caught? How fast?
2. Confirm the EDR is present and which one (product determines the hooks).
3. Test the specific bypass against THAT product and THAT version.
4. Measure time-to-detect, not just detect/no-detect.
5. Re-test after any signature update in the engagement window.
6. Record the product version — the result is only valid for it.
```

**A bypass validated against a different EDR product is not evidence.** Product and version
are part of the finding.

---

## 6. CONFIRMING THE FINDING
EDR bypass has the sharpest false-positive problem in the field: **"it ran" is not "it was not seen",
and "it was not seen" is not "it will not be seen".** This table is the gate.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **exact technique and its tool** recorded, with the EDR product and version? | a bypass is specific to a sensor, a version, and a config |
| 2 | Did the payload **actually execute** - the objective achieved, not merely the process started? | execution is the first half |
| 3 | Was the **EDR's own telemetry checked** for the event, not merely the absence of an alert? | a missing alert may be a missing sensor |
| 4 | Is there a **positive control**: the SAME technique without the bypass, which the EDR DOES see? | proves the sensor is present, armed, and watching that channel |
| 5 | Is the **observation window** stated, and was the event searched for after it? | EDR pipelines are delayed; a check at t+1s proves nothing |
| 6 | Is the bypass **classified**: which layer it targets (static, behavioural, memory, telemetry)? | the layer determines what else it does and does not defeat |
| 7 | Was the technique run against a **known-detecting baseline** for comparison? | the unarguable form of the control |

**The positive control — the same technique, without the bypass, that the EDR DOES capture — is what makes
this a finding.** "No alert" without a proven-live sensor is silence, not evasion.

---

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the EDR product and **version** | the result is version-specific |
| the technique, and which detection layer it targets | a layer-unaware claim is untestable |
| time-to-detect for the baseline and for the bypass | quantifies the improvement |
| whether prevention or detection was bypassed | **these are different findings** |
| the exact artefacts produced (memory, process, network) | lets the client verify and rule |
| what remained detectable | honest partial results are more useful than a claim of invisibility |
| for driver-level: whether it was attempted at all and the risk accepted | needs explicit authorisation |

**Never claim "the EDR is bypassed."** The finding is "technique X evaded detection layer Y on
product Z version V for N minutes." Anything broader is unprovable and will be challenged.

---

## 8. REMEDIATION REFERENCE

1. **Enable kernel-level and ETW telemetry** — userland hooks alone are the bypassable layer; the value is in the kernel and the correlation.
2. **Call-stack analysis** — defeats direct syscalls and is available from most vendors; verify it is enabled.
3. **Memory scan with protection-change events** — alert on `PAGE_EXECUTE_READWRITE` allocation in unbacked memory.
4. **AMSI on every scripting host** — and audit which hosts do not have it.
5. **Attack surface reduction rules** — block the parent-child patterns (Office spawning a shell) that no loader can hide.
6. **MDE/EDR in block mode where possible** — detection without prevention leaves the technique viable.
7. **Driver blocklist** — Microsoft's vulnerable-driver blocklist stops the BYOVD class; enable it and audit loaded drivers against known-vulnerable lists.
8. **Assume compromise is possible** — network detection (see [c2-infrastructure-and-channel-design](../c2-infrastructure-and-channel-design/SKILL.md)) is the layer that catches what the endpoint misses.

---

## 9. EXECUTION PRIMITIVES

The layer model in section 1 and the ladder in section 3 are **given meaning only by a detection control
per layer**. A bypass is proven by **an unmodified artefact that IS caught at that layer, the modified
artefact that is not, and the layers above shown to remain**. Sections 6 and 7 stated what to record and
what to fix; this section is how to obtain it.

### 8.1 Establishing the test bed, which is the first falsifiable step

```bash
# THE CONTROL THAT INVALIDATES EVERYTHING IF IT FAILS. Run this before anything else.
# Linux host shown; the Windows equivalent is in windows-av-evasion 10.1.
echo "=== 0. THE LAYER INVENTORY: what is actually watching this host ==="
echo "--- kernel: audit, LSM, and any kernel-resident monitor ---"
cat /sys/kernel/security/lsm 2>/dev/null || echo "  (no /sys/kernel/security/lsm; LSMs may still be active)"
ls /sys/module/ | grep -iE 'audit|selinux|apparmor|yama' 2>/dev/null
grep -o -m1 -E '(selinux|apparmor|audit)' /proc/cmdline 2>/dev/null || echo "  (no LSM flag on the kernel command line)"
echo
echo "--- audit: is it running, and what rules are loaded? ---"
command -v auditctl >/dev/null && { auditctl -s 2>/dev/null | head -4; auditctl -l 2>/dev/null | head -8; } || echo "  auditctl absent"
echo
echo "--- eBPF-based monitors: the KERNEL sees the syscall, so userland tricks do not apply ---"
ls /sys/fs/bpf/ 2>/dev/null | head -8
bpftool prog list 2>/dev/null | head -12 || echo "  bpftool absent - check for a vendor agent's own module"
lsmod 2>/dev/null | grep -iE 'falcon|crowdstrike|sentinel|vectra|cylance|trend' || echo "  no obvious vendor kernel module"
echo
echo "--- the agent processes themselves ---"
ps -eo pid,comm 2>/dev/null | grep -iE 'falcon|csagent|tanium|mdatp|wdavdaemon|osquery|auditd' || echo "  no agent process matched"
echo
echo "=== 1. THE DETECTION CONTROL, PER LAYER ==="
echo "  the control is a KNOWN-DETECTED action at the layer you intend to bypass. Without it,"
echo "  'my tool ran' is equally consistent with 'nothing was watching'."
cat <<'CONTROLS'
  layer                     the control action                                   the expected observation
  -------------------------|----------------------------------------------------|-------------------------
  static on-disk scan      write an EICAR test file (NOT malicious)             removed or flagged within seconds
  script/AMSI-class scan    submit a KNOWN-FLAGGED string in the scripted shell  a block or a logged event
  userland API hooks        read the in-memory .text of a hooked function and    differs from its on-disk copy
                            compare with the on-disk file
  ETW / provider events     perform a benign action the provider logs            the event appears in the log
  kernel callbacks          create any process                                  the callback's event appears
  minifilter                write any file                                      the filter's event appears
  behavioural analytics     run a LOUD but benign sequence                      the console shows an alert
  memory scan               hold a KNOWN signature in a live process            the live scan flags it
CONTROLS
echo
echo "=== 2. THE TELEMETRY EXPORT, WHICH DISTINGUISHES 'not blocked' FROM 'not detected' ==="
echo "  'it ran' supports only 'not blocked'. Export the alerts and cite the window for 'not detected'."
echo "  Linux  : journalctl -u auditd --since '<start>' ; ausearch -ts <start> ; the agent's own CLI"
echo "  Windows: Get-MpThreatDetection ; the Windows Defender/Operational and Sysmon logs"
echo "  vendor : name the product and the console query, with the time window"
echo
echo "=== 3. THE BASELINE, before any evasion ==="
python3 - <<'PY'
import subprocess, datetime
print("=== the baseline: what the host records for a LITERAL, unmodified action ===")
print("  run the tool WITHOUT evasion, capture:")
print("    - whether it was BLOCKED")
print("    - what ALERTED (the exported events)")
print("    - how long the alert took to appear (the detection latency)")
print("  this baseline is the control the evaded run is compared against.")
print("  a baseline run that is NOT blocked means the tool is not detected AT ALL on this host,")
print("  and no evasion is being demonstrated. Change the tool, not the evasion.")
PY
```

**The per-layer control table is the finding's foundation.** A baseline run that is not blocked means the
tool was never detected, and no evasion is being demonstrated.

### 8.2 Per-layer bypass, each with its own control

```bash
cat <<'LAYERS'
USERLAND API HOOKS  (the layer most "EDR bypass" claims address)
  technique : restore the function's original prologue from a clean copy of the DLL/so
  artefact  : BEFORE/AFTER byte comparison of the function's in-memory .text vs its on-disk copy
  control   : (a) a function you did NOT restore must STILL show a mismatch
              (b) the unmodified tool must still be BLOCKED afterwards
  DOES NOT DEFEAT : kernel callbacks, ETW-TI, minifilters, a hypervisor monitor. Say so.

ETW / ETW-TI
  technique : provider-specific patching (userland ETW providers only)
  artefact  : the TARGET provider's events CEASE
  control   : a DIFFERENT, untouched provider's events CONTINUE
  DOES NOT DEFEAT : ETW-TI, which is kernel-side and cannot be patched from userland.
  trap      : if ALL providers stop, you broke the service - louder, and a different finding.

AMSI-CLASS SCRIPT SCANNING
  technique : prevent the script block from being submitted, or submit it unrecognisably
  artefact  : the SAME flagged string is flagged BEFORE and NOT AFTER, same host
  control   : the control string, submitted twice, once before and once after the bypass
  DOES NOT DEFEAT : ScriptBlockLogging (event 4104), which logs the script regardless of scanning.
                    Export 4104 and show whether the script survived the bypass. Often it did.

BEHAVIOURAL ANALYTICS  (server-side)
  technique : pacing, living-off-the-land, mimicking an admin's tooling
  artefact  : the altered TELEMETRY, exported and compared with the baseline
  control   : the UNPACED version, which must alert
  DOES NOT DEFEAT : the fact that the events still exist. The claim is "not correlated as malicious",
                    which is a WEAKER claim than "not detected", and must be worded as such.

MEMORY SCANNING
  technique : encryption at rest, in-memory-only execution, evasive sleep
  artefact  : the live-process scan result, compared with the unencrypted control
  control   : the UNENCRYPTED payload in memory, which MUST be flagged
  trap      : a sleep past the scan window is a TIMING evasion. Measure the window and report it as
              a timing evasion, not as scanner evasion.
LAYERS
echo
echo "=== THE ESCALATION LADDER IN SECTION 3, now with its evidence requirement ==="
echo "  each rung is only 'reached' when its control has been run. An unreached rung reported as"
echo "  reached is this family's standard overclaim."
```

**Each rung of the ladder is reached only when its control has run.** The behavioural-analytics rung
supports only "not correlated as malicious", which is weaker than "not detected" and must be worded so.

### 8.3 The layer-stack proof

```python
print("=== THE PROOF SHAPE THAT MAKES AN EDR CLAIM REVIEWABLE ===")
print("  An EDR finding is not 'I bypassed the EDR'. It is a MATRIX: one row per layer, with a")
print("  result and a control for each, and the layers you did NOT address marked as such.")
print()
LAYERS = ["static on-disk scan", "script / AMSI-class", "userland API hooks", "ETW userland",
          "ETW-TI (kernel)", "kernel callbacks", "minifilter", "behavioural analytics",
          "memory scan", "hypervisor / hardware"]
for l in LAYERS:
    print(f"  {l:26} | result: __________ | control: __________ | status: bypassed/addressed/n/a")
print()
print("=== THE ROWS THAT CANNOT BE MARKED 'bypassed' FROM USERLAND ===")
for l in ["ETW-TI (kernel)", "kernel callbacks", "minifilter", "hypervisor / hardware"]:
    print(f"  {l:26} -> these require a KERNEL or hypervisor primitive. A userland tool cannot")
    print(f"  {'':26}    reach them, so the row must read 'not addressed' and the report must say so.")
print()
print("=== AND THE GOAL, which the matrix does not provide ===")
print("  a matrix of bypasses with no beacon or captured output is an intermediate result.")
print("  the finding's top line is the OBJECTIVE achieved, and the matrix is how it was achieved.")
print()
print("=== THE RELIABILITY DIMENSION, which EDR claims routinely omit ===")
print("  detections are not always deterministic: run the evaded path N >= 10 times and record the")
print("  rate. An evasion that works 7 in 10 is a finding about a RACE, and the defender's luck")
print("  is the gap. State the rate.")
```

**A userland tool cannot reach the kernel and hypervisor layers, so those rows must read "not
addressed".** The matrix is how the objective was achieved; the objective is the finding's top line.

### 8.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== EDR BYPASS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the LAYER INVENTORY was established, including kernel-resident monitors (LSM, audit, eBPF, modules)",
  "a host with a kernel monitor cannot be bypassed from userland"),
 ("a PER-LAYER DETECTION CONTROL was run, and it WAS detected",
  "if the control is not detected, nothing is watching that layer"),
 ("a BASELINE unmodified run was captured: blocked?, alerted?, latency",
  "a baseline that is not blocked means no evasion is being demonstrated"),
 ("the layer bypassed is NAMED, and the layers ABOVE are shown to still be present",
  "userland unhooking does not touch kernel callbacks"),
 ("for a userland unhook: the BEFORE/AFTER .text comparison, plus an un-restored control function",
  "if everything matches, nothing was hooked"),
 ("for an ETW claim: the target provider stopped and a control provider continued",
  "if all ETW stopped you broke the service"),
 ("for an AMSI-class claim: the same string flagged before and not after, same host",
  "one result is not a bypass"),
 ("telemetry was EXPORTED with a time window before claiming 'not detected'",
  "'it ran' supports only 'not blocked'"),
 ("a sleep-past-the-window is classified as a TIMING evasion, with the window measured",
  "scanner evasion and timing evasion are different claims"),
 ("the rows for ETW-TI, kernel callbacks, minifilters, and hypervisors read 'not addressed'",
  "a userland tool cannot reach them"),
 ("the reliability was measured over N >= 10 runs",
  "a 7-in-10 evasion is a finding about a race"),
 ("the GOAL was proven by a beacon or a captured command output",
  "a matrix of bypasses is not an objective"),
]
for n, how in CHECKS: print("  [ ] %-72s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  layer matrix : one row per layer, with result / control / status")
print("  control      : the per-layer detection control, and the baseline run")
print("  telemetry    : the exported events, with the time window")
print("  goal         : the beacon or the command output")
print("  rate         : N of M, because detections are not always deterministic")
print("  not addressed: the kernel-side and hypervisor rows, explicitly")
PY
```

**Layer matrix, control, telemetry, goal, rate, not-addressed rows.** The last line is what separates a
reviewable EDR claim from a slogan.

---

## 10. RELATED SIBLINGS - LOAD TOGETHER

- [windows-av-evasion](../windows-av-evasion/SKILL.md) - the product-specific controls for these layers
- [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md) - the vehicle that produces the telemetry
- [linux-security-bypass](../linux-security-bypass/SKILL.md) - the Linux equivalent of the layer model
- [sandbox-escape-techniques](../sandbox-escape-techniques/SKILL.md) - when the confinement is a container rather than an agent
- [malware-development-workflow](../malware-development-workflow/SKILL.md) - where the payload's form is built
