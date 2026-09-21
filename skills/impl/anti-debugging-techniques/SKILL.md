---
name: anti-debugging-techniques
description: >-
  Anti-debugging detection and bypass playbook. Use when reversing protected
  binaries that detect debuggers via ptrace, PEB flags, timing checks, or
  signal/exception handlers on Linux and Windows.
---

# SKILL: Anti-Debugging Techniques — Detection & Bypass Playbook

> **AI LOAD INSTRUCTION**: Expert anti-debug techniques across Linux and Windows. Covers ptrace, PEB flags, NtQueryInformationProcess, timing attacks, signal-based detection, TLS callbacks, VEH tricks, and all corresponding bypass methods. Base models often miss the distinction between user-mode and kernel-mode detection and the correct patching strategy for each.

## 0. RELATED ROUTING

- [code-obfuscation-deobfuscation](../code-obfuscation-deobfuscation/SKILL.md) when the binary also uses control flow flattening, VM protection, or string encryption
- [vm-and-bytecode-reverse](../vm-and-bytecode-reverse/SKILL.md) when the anti-debug sits inside a custom VM dispatcher
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) when you want to symbolically skip anti-debug checks entirely

### Advanced Reference

Also load [ANTI_DEBUG_MATRIX.md](./ANTI_DEBUG_MATRIX.md) when you need:
- Complete cross-reference matrix of technique × OS × detection method × bypass method
- Per-technique reliability ratings and false-positive notes
- Tool compatibility chart (GDB, x64dbg, WinDbg, Frida, ScyllaHide)

### Quick bypass picks

| Detection Class | First Bypass | Backup |
|---|---|---|
| ptrace-based (Linux) | `LD_PRELOAD` hook `ptrace()` → return 0 | Kernel module to hide tracer |
| PEB.BeingDebugged (Windows) | Patch PEB byte at `fs:[0x30]+0x2` | ScyllaHide auto-patch |
| Timing check (rdtsc) | Conditional BP after rdtsc, fix registers | Frida hook `rdtsc` return |
| IsDebuggerPresent | NOP the call / hook return 0 | x64dbg built-in hide |
| INT 2D / UD2 exception | Set VEH to handle gracefully | TitanHide driver |

---

## 1. LINUX ANTI-DEBUG TECHNIQUES

### 1.1 ptrace(PTRACE_TRACEME)

The classic self-attach: a process calls `ptrace(PTRACE_TRACEME, 0, 0, 0)`. If a debugger is already attached, the call fails (returns -1).

```c
if (ptrace(PTRACE_TRACEME, 0, 0, 0) == -1) {
    exit(1); // debugger detected
}
```

**Bypass methods**:

| Method | How |
|---|---|
| `LD_PRELOAD` shim | Compile shared lib: `long ptrace(int r, ...) { return 0; }` and set `LD_PRELOAD` |
| Binary patch | NOP the `ptrace` call or patch return value check |
| GDB catch | `catch syscall ptrace` → modify `$rax` to 0 on return |
| Kernel module | Hook `sys_ptrace` to allow multiple tracers |

### 1.2 /proc/self/status — TracerPid

```c
FILE *f = fopen("/proc/self/status", "r");
// parse TracerPid: if non-zero → debugger attached
```

**Bypass**: Mount a FUSE filesystem over `/proc/self`, or `LD_PRELOAD` hook `fopen`/`fread` to filter `TracerPid` to 0.

### 1.3 Timing Checks (rdtsc / clock_gettime)

Measures elapsed time between two points; debugger single-stepping causes noticeable delay.

```asm
rdtsc
mov ebx, eax       ; save low 32 bits
; ... protected code ...
rdtsc
sub eax, ebx
cmp eax, 0x1000    ; threshold
ja  debugger_detected
```

**Bypass**: Set hardware breakpoint after second `rdtsc`, modify `eax` to pass the comparison. Or use Frida to replace the timing function.

### 1.4 Signal-Based Detection (SIGTRAP)

```c
volatile int caught = 0;
void handler(int sig) { caught = 1; }
signal(SIGTRAP, handler);
raise(SIGTRAP);
if (!caught) exit(1); // debugger swallowed the signal
```

When a debugger is attached, `SIGTRAP` is consumed by the debugger rather than delivered to the handler. **Bypass**: In GDB, use `handle SIGTRAP nostop pass` to forward the signal.

### 1.5 /proc/self/maps & LD_PRELOAD Detection

Checks for injected libraries or memory regions characteristic of debuggers/instrumentation.

```c
FILE *f = fopen("/proc/self/maps", "r");
while (fgets(buf, sizeof(buf), f)) {
    if (strstr(buf, "frida") || strstr(buf, "LD_PRELOAD"))
        exit(1);
}
```

**Bypass**: Hook `fopen("/proc/self/maps")` to return a filtered version, or rename Frida's agent library.

### 1.6 Environment Variable Checks

Some protections check for `LD_PRELOAD`, `LINES`, `COLUMNS` (set by GDB's terminal), or debugger-specific env vars.

**Bypass**: Unset suspicious env vars before launch, or hook `getenv()`.

---

## 2. WINDOWS ANTI-DEBUG TECHNIQUES

### 2.1 IsDebuggerPresent / CheckRemoteDebuggerPresent

```c
if (IsDebuggerPresent()) ExitProcess(1);

BOOL debugged = FALSE;
CheckRemoteDebuggerPresent(GetCurrentProcess(), &debugged);
if (debugged) ExitProcess(1);
```

**Bypass**: Hook `kernel32!IsDebuggerPresent` to return 0, or patch PEB directly.

### 2.2 PEB Flags

| Field | Offset (x64) | Debugged Value | Normal Value |
|---|---|---|---|
| `BeingDebugged` | `PEB+0x02` | 1 | 0 |
| `NtGlobalFlag` | `PEB+0xBC` | `0x70` (FLG_HEAP_*) | 0 |
| `ProcessHeap.Flags` | Heap+0x40 | `0x40000062` | `0x00000002` |
| `ProcessHeap.ForceFlags` | Heap+0x44 | `0x40000060` | 0 |

```asm
mov rax, gs:[0x60]    ; PEB
movzx eax, byte [rax+0x02]  ; BeingDebugged
test eax, eax
jnz debugger_detected
```

**Bypass**: Zero all four fields. ScyllaHide does this automatically.

### 2.3 NtQueryInformationProcess

| InfoClass | Value | Debugged Return |
|---|---|---|
| `ProcessDebugPort` | 0x07 | Non-zero port |
| `ProcessDebugObjectHandle` | 0x1E | Valid handle |
| `ProcessDebugFlags` | 0x1F | 0 (inverted!) |

**Bypass**: Hook `ntdll!NtQueryInformationProcess` to return clean values per info class.

### 2.4 Hardware Breakpoint Detection

```c
CONTEXT ctx;
ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
GetThreadContext(GetCurrentThread(), &ctx);
if (ctx.Dr0 || ctx.Dr1 || ctx.Dr2 || ctx.Dr3)
    ExitProcess(1);
```

**Bypass**: Hook `GetThreadContext` to zero DR0–DR3, or use `NtSetInformationThread(ThreadHideFromDebugger)` preemptively (ironically, the anti-debug technique itself).

### 2.5 INT 2D / INT 3 / UD2 Exception Tricks

`INT 2D` is the kernel debug service interrupt. Without a debugger, it raises `STATUS_BREAKPOINT`; with a debugger, behavior differs (byte skipping).

```asm
xor eax, eax
int 2dh
nop          ; debugger may skip this byte
; ... divergent execution path ...
```

**Bypass**: Handle in VEH or patch the interrupt instruction.

### 2.6 TLS Callbacks

TLS callbacks execute before `main()` / `WinMain()`. Anti-debug checks placed here run before the debugger's initial break.

**Bypass**: In x64dbg, set "Break on TLS Callbacks" option. In WinDbg, use `sxe ld` to break on module load.

### 2.7 NtSetInformationThread(ThreadHideFromDebugger)

```c
NtSetInformationThread(GetCurrentThread(), ThreadHideFromDebugger, NULL, 0);
```

After this call, the thread becomes invisible to the debugger — breakpoints and single-stepping stop working silently.

**Bypass**: Hook `NtSetInformationThread` to NOP when `ThreadInfoClass == 0x11`.

### 2.8 VEH-Based Detection

Registers a Vectored Exception Handler that checks `EXCEPTION_RECORD` for debugger-specific behavior (single-step flag, guard page violations with debugger semantics).

**Bypass**: Understand the VEH logic and ensure the exception chain behaves identically to non-debugged execution.

---

## 3. ADVANCED MULTI-LAYER TECHNIQUES

### 3.1 Self-Debugging (fork + ptrace)

The process forks a child that attaches to the parent via ptrace. If an external debugger is already attached, the child's ptrace fails.

```c
pid_t child = fork();
if (child == 0) {
    if (ptrace(PTRACE_ATTACH, getppid(), 0, 0) == -1)
        kill(getppid(), SIGKILL);
    else
        ptrace(PTRACE_DETACH, getppid(), 0, 0);
    _exit(0);
}
wait(NULL);
```

**Bypass**: Patch the `fork()` return or kill/detach the watchdog child.

### 3.2 Multi-Process Debugging Detection

Parent and child cooperatively check each other's debug state, creating a mutual-watch pattern.

**Bypass**: Attach to both processes (GDB `follow-fork-mode`, or two debugger instances).

### 3.3 Timing-Based with Multiple Checkpoints

Distributes timing checks across multiple functions, comparing cumulative drift. Single patches fail because the total still exceeds threshold.

**Bypass**: Frida `Interceptor.replace` all timing sources (`rdtsc`, `clock_gettime`, `QueryPerformanceCounter`) to return controlled values.

### 3.4 Nanomite / INT3 Patching

Original conditional jumps are replaced with `INT3` (0xCC). A parent debugger process handles each `INT3`, evaluates the condition, and sets the child's EIP accordingly.

**Bypass**: Reconstruct the original jump table by tracing all `INT3` handlers, then patch the binary.

---

## 4. COUNTERMEASURE TOOLS

| Tool | Platform | Capability |
|---|---|---|
| **ScyllaHide** | Windows (x64dbg/IDA/OllyDbg) | Auto-patches PEB, hooks NtQuery*, hides threads, fixes timing |
| **TitanHide** | Windows (kernel driver) | Kernel-level hiding for all user-mode checks |
| **Frida** | Cross-platform | Script-based hooking of any function, timing spoofing |
| **LD_PRELOAD shims** | Linux | Replace ptrace, getenv, fopen at load time |
| **GDB scripts** | Linux | `catch syscall`, conditional BP, register fixup |
| **Qiling** | Cross-platform | Full-system emulation, bypass all hardware checks |

---

## 5. SYSTEMATIC BYPASS METHODOLOGY

```
Step 1: Static analysis — identify anti-debug calls
  └─ Search for: ptrace, IsDebuggerPresent, NtQuery, rdtsc,
     GetTickCount, SIGTRAP, INT 2D, TLS directory entries

Step 2: Classify each check
  ├─ API-based → hook or patch the call
  ├─ Flag-based → patch PEB/proc fields
  ├─ Timing-based → spoof time source
  ├─ Exception-based → forward/handle exception correctly
  └─ Multi-process → handle both processes

Step 3: Apply bypass (order matters)
  1. Load ScyllaHide / set LD_PRELOAD (covers 80% of checks)
  2. Handle TLS callbacks (break before main)
  3. Patch remaining custom checks (Frida or binary patch)
  4. Verify: run with breakpoints, confirm no premature exit

Step 4: Validate bypass completeness
  └─ Set BP on ExitProcess/exit/_exit — if hit unexpectedly,
     a check was missed → trace back from exit call
```

---

## 6. DECISION TREE

```
Binary exits/crashes under debugger?
│
├─ Crashes immediately before main?
│  └─ TLS callback anti-debug
│     └─ Enable TLS callback breaking in debugger
│
├─ Crashes at startup?
│  ├─ Linux: check for ptrace(TRACEME)
│  │  └─ LD_PRELOAD hook or NOP patch
│  └─ Windows: check IsDebuggerPresent / PEB
│     └─ ScyllaHide or manual PEB patch
│
├─ Crashes after some execution?
│  ├─ Consistent crash point → API-based check
│  │  ├─ NtQueryInformationProcess → hook return values
│  │  ├─ /proc/self/status → filter TracerPid
│  │  └─ Hardware BP detection → hook GetThreadContext
│  │
│  ├─ Variable crash point → timing-based check
│  │  └─ Hook rdtsc / QueryPerformanceCounter
│  │
│  └─ Crash on breakpoint hit → exception-based check
│     ├─ INT 2D / INT 3 trick → handle in VEH
│     └─ SIGTRAP handler → GDB: handle SIGTRAP pass
│
├─ Debugger loses control silently?
│  └─ ThreadHideFromDebugger
│     └─ Hook NtSetInformationThread
│
├─ Child process detects and kills parent?
│  └─ Self-debugging (fork+ptrace)
│     └─ Patch fork() or handle both processes
│
└─ All basic bypasses applied but still detected?
   └─ Multi-layer / custom checks
      ├─ Use Frida for comprehensive API hooking
      ├─ Full emulation with Qiling
      └─ Trace all calls to exit/abort to find remaining checks
```

---

## 7. CTF & REAL-WORLD PATTERNS

### Common CTF Anti-Debug Patterns

| Pattern | Frequency | Quick Bypass |
|---|---|---|
| Single `ptrace(TRACEME)` | Very common | `LD_PRELOAD` one-liner |
| `IsDebuggerPresent` + `NtGlobalFlag` | Common | ScyllaHide |
| rdtsc timing in loop | Moderate | Patch comparison threshold |
| signal(SIGTRAP) + raise | Moderate | GDB signal forwarding |
| fork + ptrace watchdog | Rare but tricky | Kill child or patch fork |
| Nanomite INT3 replacement | Rare (advanced) | Reconstruct jump table |

### Real-World Protections

| Protector | Primary Anti-Debug | Recommended Tool |
|---|---|---|
| VMProtect | PEB + timing + driver-level | TitanHide + ScyllaHide |
| Themida | Multi-layer PEB + SEH + timing | ScyllaHide + manual patches |
| Enigma Protector | IsDebuggerPresent + CRC checks | x64dbg + ScyllaHide |
| UPX (custom) | Usually none (just packing) | Standard unpack |
| Custom (malware) | Varies widely | Frida + Qiling for analysis |

---

## 8. QUICK REFERENCE — BYPASS CHEAT SHEET

### Linux One-Liners

```text
# LD_PRELOAD anti-ptrace
echo 'long ptrace(int r, ...) { return 0; }' > /tmp/ap.c
gcc -shared -o /tmp/ap.so /tmp/ap.c
LD_PRELOAD=/tmp/ap.so ./target

# GDB: catch and bypass ptrace
(gdb) catch syscall ptrace
(gdb) commands
> set $rax = 0
> continue
> end
```

### Frida Anti-Debug Bypass (Cross-Platform)

```javascript
// Hook IsDebuggerPresent (Windows)
Interceptor.replace(
  Module.getExportByName('kernel32.dll', 'IsDebuggerPresent'),
  new NativeCallback(() => 0, 'int', [])
);

// Hook ptrace (Linux)
Interceptor.replace(
  Module.getExportByName(null, 'ptrace'),
  new NativeCallback(() => 0, 'long', ['int', 'int', 'pointer', 'pointer'])
);

// Timing spoof
Interceptor.attach(Module.getExportByName(null, 'clock_gettime'), {
  onLeave(retval) {
    // manipulate timespec to hide debugger delay
  }
});
```

### x64dbg ScyllaHide Quick Setup

1. Plugins → ScyllaHide → Options
2. Check: PEB BeingDebugged, NtGlobalFlag, HeapFlags
3. Check: NtQueryInformationProcess (all classes)
4. Check: NtSetInformationThread (HideFromDebugger)
5. Check: GetTickCount, QueryPerformanceCounter
6. Apply → restart debugging session

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **technique** fired, at which **address**, and by which detection mechanism? | the finding is a site, not a binary |
| 2 | Does the binary run **correctly without a debugger**? | the baseline the technique degrades |
| 3 | Does the **technique itself** cause the difference, or something else? | attribution |
| 4 | Was there a **control binary** with the check removed/patched? | the technique is causal |
| 5 | Does the workaround let the analysis **proceed to the goal**? | bypassing a check is not completing the task |
| 6 | Is the finding **sample-specific** or a **scheme** replicable across the family? | severity and scope |
| 7 | What **else** breaks when the check is neutralised? | the anti-debug often guards integrity too |

**A named detection site, a non-debugged baseline, and a control binary the technique was removed from.**
"Anti-debugging present" is not a finding; the address and the mechanism are.

---

## 10. EXECUTION PRIMITIVES

An anti-debugging finding is proven by **a named check at a named address whose removal changes the
binary's behaviour, against a non-debugged baseline and a patched control**. Presence of a `ptrace` call
is not a finding.

### 10.1 The non-debugged baseline, which must come first

```bash
# the BASELINE: how the binary behaves with no debugger attached. Everything else is a delta.
BIN="./target"
echo "=== 1. the no-debugger baseline ==="
"$BIN" < /dev/null > base.out 2> base.err; echo "  exit=$? stdout=$(wc -c < base.out)B stderr=$(wc -c < base.err)B"
sha256sum base.out
echo
echo "=== 2. THE CONTROL: run under gdb and record the FIRST divergence ==="
gdb -q -batch -ex "set pagination off" -ex run -ex "bt" -ex quit --args "$BIN" < /dev/null 2>&1 | tail -25
echo "  -> the exit code, the signal, or the missing output IS the divergence. Record it verbatim."
echo
echo "=== 3. WHICH signal/timeout, which identifies the mechanism ==="
for s in SIGTRAP SIGSEGV SIGILL SIGKILL; do
  printf '  %-8s ' "$s"
  timeout 10 gdb -q -batch -ex "handle $s stop print" -ex run -ex "info registers rip" -ex quit --args "$BIN" < /dev/null 2>&1 \
    | grep -cE "Program received|SIG" || true
done
echo "  -> SIGTRAP immediately at start = a ptrace self-attach; SIGSEGV/SIGILL in a known function"
echo "     = a checksum or timing check; SIGKILL = a watchdog thread."
echo "  A binary that exits 0 with NO output under gdb is the clearest form: record both."
```

**The non-debugged run is the baseline, and the first divergence under a debugger is the finding's
locus.** The signal and the timing together identify the mechanism.

### 10.2 The Linux detection sites, with the bypass and its control

```bash
# each site: the detection, the evidence, the bypass, and the CONTROL that proves causality
cat <<'SITES'
PTRACE_SELF_ATTACH   ptrace(PTRACE_TRACEME) fails with EPERM when already traced
  detect  : strace -f -e trace=ptrace ./target 2>&1 | grep TRACEME
  bypass  : the return value is a register; break after the syscall and set it to 0
  gdb     : catch syscall ptrace
            commands
            silent
            set $rax = 0
            continue
            end
  control : run the SAME gdb session with the syscall allow-through - it must fail again
  trap    : a second, independent check usually reads the same result; patch all call sites

PTRACE_ATTACH_SCAN   the process scans /proc/self/status for TracerPid != 0
  detect  : grep TracerPid /proc/self/status ; strings -a ./target | grep -E 'TracerPid|/proc/self'
  bypass  : break on the open/read of /proc/self/status and zero the buffer, or patch the compare
  control : the unmodified run under gdb must still take the anti-debug branch
  trap    : the file may be read via openat, or mmapped; check both syscalls

TIMING_DELTA         rdtsc / clock_gettime around a region; a debugger slows it
  detect  : strace -e trace=clock_gettime,gettimeofday ./target ; or ltrace rdtsc use
  bypass  : break after the second read and equalise the registers, or patch the threshold cmp
  control : run with the patch but WITHOUT gdb - the behaviour must be unchanged
  trap    : THE STANDARD ERROR - a machine with high load trips this too. Run the control 3x on
            an idle host and 3x under load before calling the threshold a debugger check.

SIGNAL_HANDLER_CHECK installed SIGTRAP/SIGSEGV handlers that inspect ucontext for a debugger
  detect  : the handler address from `info signals`; objdump -d around it
  bypass  : patch the handler to return without the check, or neutralise the raise
  control : with the handler patched and no debugger, behaviour must be unchanged
  trap    : the handler may be installed lazily by an init routine; find the installer

INT3_PATCHING        the binary writes 0xCC over itself and detects the modified byte
  detect  : strace -e trace=mprotect ; look for a PROT_WRITE|PROT_EXEC region
  bypass  : mask the byte comparison, or let the write complete and restore after the check
  control : the unmodified binary must detect the INT3
  trap    : this often pairs with a checksum over the same region; patch the checksum too

PROCESS_COUNT_SCAN   counts processes, or reads /proc/*/cmdline looking for gdb/strace
  detect  : strace -e trace=openat ./target 2>&1 | grep -E '/proc/[0-9]+/cmdline'
  bypass  : hide the tracer (a gdb namespace or a patched read), or rename the tracer
  control : the same scan run in an environment with no tracer must NOT fire
SITES
echo
echo "=== the UNIVERSAL control: patch the check OUT of a COPY and diff the behaviour ==="
cp "$BIN" "$BIN.nocheck"
python3 - "$BIN.nocheck" <<'PY'
import sys
p = sys.argv[1]
d = bytearray(open(p,"rb").read())
# EXAMPLE: neutralise a `jne` after a call (0f 85 -> 90 90 is a no-op pair; adjust to the site)
# locate the site first with objdump, then apply the smallest possible patch here.
print("target:", p, "size:", len(d))
print("APPLY THE MINIMAL PATCH: a jump that is never taken, or a return value of 0.")
print("Then run BOTH binaries with no debugger. The nocheck copy must behave like the")
print("debugged original - that equivalence is the proof the SITE is the cause.")
PY
```

**The patched copy run without a debugger is the decisive control.** If the unpatched binary and the
patched copy behave identically, the site you patched does not cause the divergence.

### 10.3 The Windows detection sites

```bash
cat <<'WIN'
IsDebuggerPresent          reads the PEB's BeingDebugged byte
  detect  : x64dbg `bp IsDebuggerPresent` ; or inspect PEB+0x02 in the dump
  bypass  : set PEB->BeingDebugged = 0, or patch the call to return 0
  control : with the PEB byte left intact, the branch must be taken
CheckRemoteDebuggerPresent  queries the debug object
  detect  : bp CheckRemoteDebuggerPresent ; the out-param is the result
  bypass  : zero the out-parameter after the call returns
NtQueryInformationProcess   ProcessDebugPort (7), ProcessDebugObjectHandle (0x1E),
                            ProcessDebugFlags (0x1F) - THE ONES THAT BYPASS THE PEB TRICK
  detect  : bp ntdll!NtQueryInformationProcess, inspect the ProcessInformationClass argument
  bypass  : patch the return to STATUS_PORT_NOT_SET, or break AFTER the call and zero the buffer
  control : a PEB-patch-only session MUST still be caught by class 7/0x1E. That is the control
            that shows the PEB trick is insufficient on this sample.
NtSetInformationThread    ThreadHideFromDebugger (0x11) - hides the thread instead of detecting
  detect  : bp NtSetInformationThread ; argument 0x11
  bypass  : skip the call, or re-show the thread
  trap    : this SILENTLY breaks your stepping rather than raising. If stepping stops without a
            signal, suspect this call - it is the one people misdiagnose as a gdb/x64dbg failure.
OutputDebugString          GetLastError() != 0 when no debugger is present
  detect  : the call site and the immediately following GetLastError comparison
  bypass  : force GetLastError() to 0 after the call
Hardware breakpoint reset  DR0-DR3 / DR7 cleared by a thread that scans them
  detect  : a tight loop reading the thread context, or SetThreadContext on itself
  bypass  : patch the clearing code, or use a software breakpoint elsewhere
  trap    : the reset often runs on a separate thread - find it before patching
WIN
echo
echo "=== the Windows control, which is the same equivalence test ==="
echo "  1. patch ONLY the PEB byte -> run -> if it still detects, a second site exists (record it)"
echo "  2. patch EVERY site -> run -> must behave like the undebugged original"
echo "  3. run the fully patched copy WITHOUT a debugger -> the equivalence is the proof"
```

**The PEB patch alone failing is itself the finding.** The presence of a second site is proven by the
first patch not working, and that sequence belongs in the report.

### 10.4 The end-to-end harness

```bash
python3 - <<'PY'
import os, subprocess, hashlib, json
print("=== ANTI-DEBUG FINDING ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("a NON-DEBUGGED baseline was captured",
  "the exit code, stdout, and stderr with no debugger - the thing the check degrades"),
 ("the FIRST divergence under a debugger is recorded verbatim",
  "the signal, the address, the missing output, or the hang"),
 ("the MECHANISM is identified, not just the symptom",
  "ptrace self-attach, TracerPid scan, timing, signal handler, INT3, or process scan"),
 ("the SITE has an ADDRESS",
  "'anti-debug present' is not a finding; the offset or symbol is"),
 ("a MINIMAL PATCH was applied to a COPY",
  "not to the original - the original must remain bit-identical to what was delivered"),
 ("the patched copy was run WITHOUT a debugger and behaved like the original",
  "THE CONTROL: this equivalence is what proves the site is causal"),
 ("the timing family was re-run 3x idle and 3x under load",
  "a load-induced trip is the standard false positive for rdtsc checks"),
 ("the workaround reached the ANALYSIS GOAL",
  "bypassing a check is not the same as completing the analysis"),
 ("the scope is stated: this sample, or this protector family",
  "severity depends on the scheme, not the instance"),
 ("what else the check guarded is recorded",
  "anti-debug frequently shares a code path with integrity verification"),
]
for n, how in CHECKS: print("  [ ] %-56s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  baseline : the non-debugged run, verbatim")
print("  site     : the address and the mechanism")
print("  evidence : the divergence under a debugger")
print("  control  : the patched copy, run without a debugger, behaving like the original")
print("  bypass   : the minimal patch, quoted")
print("  reach    : whether the analysis goal was reached through the bypass")
PY
```

**Baseline, site, divergence, control, bypass, reach.** A bypass that does not reach the analysis goal is
an intermediate result, and the report must say so.

---

## 11. EVIDENCE STANDARD — ANTI-DEBUG ARTEFACTS

| Item | Why |
|---|---|
| The **non-debugged baseline**: exit code, stdout, stderr, hashes | the behaviour the check degrades |
| The **first divergence** under a debugger, verbatim | the finding's locus |
| The **signal** and the **timing** of the divergence | identifies the mechanism family |
| The **mechanism**: ptrace, TracerPid, timing, handler, INT3, process scan, PEB, NT query | the technique, not the symptom |
| The **address** or symbol of the check | the finding is a site |
| The **minimal patch**, quoted | reproducibility |
| The **patched copy's behaviour without a debugger**, compared with the baseline | the causal control |
| The **raw binary's SHA-256**, and the patched copy's | the analysis artefact identity |
| The **timing test's idle and loaded runs** (3 each) | rules out the load false positive |
| Whether the **analysis goal was reached** through the bypass | the workaround's actual value |
| Whether the check is **sample-specific or a scheme** | severity |

Report the **site and the control**: "`./target` with no debugger exits `0` and writes a
`1,024`-byte `base.out` whose SHA-256 is `3f9c…`. Under `gdb` the process receives `SIGTRAP` before the
first output byte, and `catch syscall ptrace` shows a `PTRACE_TRACEME` at `0x0000000000401a30` whose
return value is `-1 EPERM`, which is the mechanism. Nothing else in the binary reads `/proc/self/status`
or `/proc/*/cmdline`, so this is a single-site check. Setting `$rax = 0` after the syscall in the same
`gdb` session lets the run proceed to the same `1,024`-byte output, and a copy patched at `0x401a30` with
the same neutralisation, run with no debugger attached, produces the identical output, so the site is
causal. The timing check at `0x4021c0` was NOT reported: it tripped in `0 of 3` idle runs and `2 of 3`
runs on a loaded host, so its threshold is load-sensitive rather than debugger-specific, and the
distinction is recorded", never "the binary uses anti-debugging techniques".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `ptrace` string or import present but **never called** | a static string is not a check |
| A **timing check** that trips under load but not under a debugger | the load false positive; test it |
| A binary that behaves the same **with and without** a debugger | there is no check |
| A crash under a debugger **because of the debugger** | the debugger's fault, not the sample's |
| A **single debugger** failing while another succeeds | a tool limitation; try a second tool |
| A check whose bypass **does not reach the goal** | an intermediate result, not a solved finding |
| The technique described from **documentation** rather than observed | a hypothesis |
| A patch applied to the **original** rather than a copy | the artefact is modified; the original is lost |
| A "**hardened**"/"**obfuscated**" label without a named site | a vendor claim |
| A check that also fires on a **non-debugger** process inspection | it may be an integrity check, not anti-debug |

**A named site, a non-debugged baseline, and a patched-copy equivalence.** A `ptrace` import and a
load-sensitive timing trip are this family's two standard non-findings.

---

## 12. REMEDIATION REFERENCE — ANTI-ANALYSIS HARDENING

1. **Layer the checks and use independent mechanisms, because a single check is a single patch** - a `ptrace` self-attach alone is neutralised in one breakpoint, and the layers are what raise the cost.
2. **Use the NT query classes (`ProcessDebugPort`, `ProcessDebugObjectHandle`, `ProcessDebugFlags`) rather than the PEB byte alone** - the PEB trick is the first thing any analyst applies, and the query path is the control against it.
3. **For timing checks, calibrate the threshold against load, or normalise with a fast baseline measurement** - an uncalibrated `rdtsc` threshold is the mechanic that produces the load false positive.
4. **Verify the check's result a second time at the point of use, rather than caching a boolean** - a single cached decision is a single patch point.
5. **Share code paths between anti-debug and integrity verification, so neutralising one is observable through the other** - the coupling is what makes a partial patch insufficient.
6. **Detect the analysis tools' fingerprints rather than assuming their presence** - `TracerPid`, the debug object handle, and the loaded module list are independent signals.
7. **Do not exclude the checker from your own test matrix: run the binary under the debuggers you expect the analyst to use, and record which mechanisms they miss** - the instrumentation test is the only way to know which layer carries the cost.
8. **Prefer a silent failure to a crash: a check that hangs, misbehaves, or returns plausible wrong data costs more than one that aborts** - a crash tells the analyst exactly where the check is.
9. **Treat `ThreadHideFromDebugger` and similar thread-level tricks as silent breakers, and test them explicitly** - the failure mode is a stepping failure that is misdiagnosed as a tool bug.
10. **Document each mechanism's stated purpose, so the check is defensible as a product decision rather than only as an obstruction** - a documented integrity rationale survives review better than a bare detection.
11. **Assume the analyst has your binary, an unlimited time budget, and a patcher; the goal is cost, not impossibility** - anti-debugging raises the effort of the first hour, and the honest framing is cost.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [code-obfuscation-deobfuscation](../code-obfuscation-deobfuscation/SKILL.md) - the transformations these checks accompany
- [vm-and-bytecode-reverse](../vm-and-bytecode-reverse/SKILL.md) - the protector family that bundles both
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the wider hardening-bypass methodology
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) - when the check must be solved rather than patched
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) - the analysis-goal context for a protected sample
