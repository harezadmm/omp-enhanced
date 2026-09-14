# PRIVILEGE ESCALATION — LINUX

**Domain:** EXPERTISE — FULL OPERATIONAL ARSENAL

## Overview
> Level: GOD TIER — SUID, sudo, kernel, capabilities, cron, NFS, Docker, PATH
- SUID/GUID: `find / -perm -4000 -o -perm -2000 2>/dev/null`, GTFOBins
- Sudo: `sudo -l`, env_keep, NO_PASSWORD, wildcard abuse
- Kernel: DirtyPipe (CVE-2022-0847), PwnKit (CVE-2021-4034), DirtyCow, overlayfs

## Full Doctrine

> Level: GOD TIER — SUID, sudo, kernel, capabilities, cron, NFS, Docker, PATH

- SUID/GUID: `find / -perm -4000 -o -perm -2000 2>/dev/null`, GTFOBins
- Sudo: `sudo -l`, env_keep, NO_PASSWORD, wildcard abuse
- Kernel: DirtyPipe (CVE-2022-0847), PwnKit (CVE-2021-4034), DirtyCow, overlayfs
- Capabilities: `getcap -r /`, cap_setuid+ep, python/node/perl cap abuse
- Cron: writable scripts, wildcard injection, PATH manipulation
- NFS: no_root_squash, squashing bypass
- Docker group: container escape, mounted socket
- Writable /etc/passwd: hash injection, user creation
- PATH hijack: binaries without absolute path
- Internal services: default creds, admin panels, dev servers

## References
- LTX-QUASAR CORE.md (persona doctrine)
