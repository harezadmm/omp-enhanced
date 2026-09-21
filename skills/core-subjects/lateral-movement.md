# LATERAL MOVEMENT

**Domain:** EXPERTISE — FULL OPERATIONAL ARSENAL

## Overview
> Level: GOD TIER — credential reuse, pass-the-hash, pass-the-ticket, WMI, PsExec, WinRM, SSH, SMB relay
- Credential reuse: found cred → spray all hosts
- Pass-the-hash: NTLM reuse (Impacket, CrackMapExec)
- Pass-the-ticket: Kerberos ticket reuse, golden/silver ticket

## Full Doctrine

> Level: GOD TIER — credential reuse, pass-the-hash, pass-the-ticket, WMI, PsExec, WinRM, SSH, SMB relay

- Credential reuse: found cred → spray all hosts
- Pass-the-hash: NTLM reuse (Impacket, CrackMapExec)
- Pass-the-ticket: Kerberos ticket reuse, golden/silver ticket
- WMI/WMIExec: remote execution via WMI
- PsExec/RemCom: remote service + binary execution
- WinRM/PowerShell: remote shell
- SSH pivoting: key reuse, agent forwarding, tunnel
- SMB relay: ntlmrelayx, PetitPotam, DFSCoerce
- Trust abuse: forest/domain/bidirectional trust
- Crown jewels: DB, DC, CI/CD, secrets manager

## References
- LTX-QUASAR CORE.md (persona doctrine)
