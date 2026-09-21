# T1037: Boot or Logon Initialization Scripts

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may use scripts automatically executed at boot or logon initialization to establish persistence.(Citation: Mandiant APT29 Eye Spy Email Nov 22)(Citation: Anomali Rocke March 2019) Initialization scripts can be used to perform administrative functions, which may often execute other programs or send information to an internal logging server. These scripts can vary based on operating system and whether applied locally or remotely.
Adversaries may use these scripts to maintain persistence on a single system. Depending on the access configuration of the logon scripts, either local credentials or an administrator account may be necessary.
An adversary may also be able to escalate their privileges since some boot or logon initialization scripts run with higher privileges.

## Tactics
Persistence, Privilege Escalation

## Platforms
ESXi, Linux, macOS, Network Devices, Windows

## Procedure
Adversaries may use scripts automatically executed at boot or logon initialization to establish persistence.(Citation: Mandiant APT29 Eye Spy Email Nov 22)(Citation: Anomali Rocke March 2019) Initialization scripts can be used to perform administrative functions, which may often execute other programs or send information to an internal logging server. These scripts can vary based on operating system and whether applied locally or remotely. Adversaries may use these scripts to maintain persistence on a single system. Depending on the access configuration of the logon scripts, either local credentials or an administrator account may be necessary.

**Known users/tools:** APT29, APT41, ArcaneDoor, Rocke, RotaJakiro, SPAWNCHIMERA, UNC3886, VIRTUALPITA

## Mitigations
- **Restrict File and Directory Permissions** — Restricting file and directory permissions involves setting access controls at the file system level to limit which users, groups, or processes can read, write, or execute files. By configuring permissions appropriately, organizations can reduce the attack surface for adversaries seeking to access s
- **Restrict Registry Permissions** — Restricting registry permissions involves configuring access control settings for sensitive registry keys and hives to ensure that only authorized users or processes can make modifications. By limiting access, organizations can prevent unauthorized changes that adversaries might use for persistence,

## References
- https://attack.mitre.org/techniques/T1037/
