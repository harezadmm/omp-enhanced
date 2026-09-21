# PRIVILEGE ESCALATION — LINUX

> Level: GOD TIER — SUID, sudo, kernel, capabilities, cron, NFS, Docker, PATH
> Extracted from CORE.md — load on-demand when Linux privesc tasks arrive.

## SUID/GUID
- `find / -perm -4000 -o -perm -2000 2>/dev/null`, GTFOBins

## Sudo
- `sudo -l`, env_keep, NO_PASSWORD, wildcard abuse

## Kernel
- DirtyPipe (CVE-2022-0847), PwnKit (CVE-2021-4034), DirtyCow, overlayfs

## Capabilities
- `getcap -r /`, cap_setuid+ep, python/node/perl cap abuse

## Cron
- Writable scripts, wildcard injection, PATH manipulation

## NFS
- no_root_squash, squashing bypass

## Docker Group
- Container escape, mounted socket

## Writable /etc/passwd
- Hash injection, user creation

## PATH Hijack
- Binaries without absolute path

## Internal Services
- Default creds, admin panels, dev servers
