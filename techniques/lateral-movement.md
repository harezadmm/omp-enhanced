# LATERAL MOVEMENT

> Level: GOD TIER — credential reuse, pass-the-hash, pass-the-ticket, WMI, PsExec, WinRM, SSH, SMB relay
> Extracted from CORE.md — load on-demand when lateral movement tasks arrive.

## Credential Reuse
- Found cred -> spray all hosts

## Pass-the-Hash
- NTLM reuse (Impacket, CrackMapExec)

## Pass-the-Ticket
- Kerberos ticket reuse, golden/silver ticket

## Remote Execution
- WMI/WMIExec: remote execution via WMI
- PsExec/RemCom: remote service + binary execution
- WinRM/PowerShell: remote shell

## SSH Pivoting
- Key reuse, agent forwarding, tunnel

## SMB Relay
- ntlmrelayx, PetitPotam, DFSCoerce

## Trust Abuse
- Forest/domain/bidirectional trust

## Crown Jewels
- DB, DC, CI/CD, secrets manager
