# T1571: Non-Standard Port

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may communicate using a protocol and port pairing that are typically not associated. For example, HTTPS over port 8088(Citation: Symantec Elfin Mar 2019) or port 587(Citation: Fortinet Agent Tesla April 2018) as opposed to the traditional port 443. Adversaries may make changes to the standard port used by a protocol to bypass filtering or muddle analysis/parsing of network data.
Adversaries may also make changes to victim systems to abuse non-standard ports. For example, Registry keys and other configuration settings can be used to modify protocol and port pairings.(Citation: change_rdp_port_conti)

## Tactics
Command And Control

## Platforms
ESXi, Linux, macOS, Windows

## Procedure
Adversaries may communicate using a protocol and port pairing that are typically not associated. For example, HTTPS over port 8088(Citation: Symantec Elfin Mar 2019) or port 587(Citation: Fortinet Agent Tesla April 2018) as opposed to the traditional port 443. Adversaries may make changes to the standard port used by a protocol to bypass filtering or muddle analysis/parsing of network data. Adversaries may also make changes to victim systems to abuse non-standard ports.

**Known users/tools:** 2025 Poland Wiper Attacks, APT-C-36, APT32, APT33, BADCALL, Bankshot, BeaverTail, BendyBear, C0018, C0032, Contagious Interview, Covenant, Cyclops Blink, DarkVishnya, Derusbi

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.
- **Network Segmentation** — Network segmentation involves dividing a network into smaller, isolated segments to control and limit the flow of traffic between devices, systems, and applications. By segmenting networks, organizations can reduce the attack surface, restrict lateral movement by adversaries, and protect critical as

## References
- https://attack.mitre.org/techniques/T1571/
