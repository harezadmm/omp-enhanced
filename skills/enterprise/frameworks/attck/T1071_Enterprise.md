# T1071: Application Layer Protocol

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may communicate using OSI application layer protocols to avoid detection/network filtering by blending in with existing traffic. Commands to the remote system, and often the results of those commands, will be embedded within the protocol traffic between the client and server.
Adversaries may utilize many different protocols, including those used for web browsing, transferring files, electronic mail, DNS, or publishing/subscribing. For connections that occur internally within an enclave (such as those between a proxy or pivot node and other nodes), commonly used protocols are SMB, SSH, or RDP.(Citation: Mandiant APT29 Eye Spy Email Nov 22)

## Tactics
Command And Control

## Platforms
Linux, macOS, Windows, Network Devices, ESXi

## Procedure
Adversaries may communicate using OSI application layer protocols to avoid detection/network filtering by blending in with existing traffic. Commands to the remote system, and often the results of those commands, will be embedded within the protocol traffic between the client and server. Adversaries may utilize many different protocols, including those used for web browsing, transferring files, electronic mail, DNS, or publishing/subscribing. For connections that occur internally within an enclave (such as those between a proxy or pivot node and other nodes), commonly used protocols are SMB, SSH, or RDP.(Citation: Mandiant APT29 Eye Spy Email Nov 22)

**Known users/tools:** Clambling, Duqu, FrostyGoop Incident, Hildegard, INC Ransom, Lucifer, Magic Hound, NETEAGLE, Nightdoor, QUIETEXIT, Raspberry Robin, Rocke, Siloscape, Sliver, TeamTNT

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.
- **Filter Network Traffic** — Employ network appliances and endpoint software to filter ingress, egress, and lateral network traffic. This includes protocol-based filtering, enforcing firewall rules, and blocking or restricting traffic based on predefined conditions to limit adversary movement and data exfiltration. This mitigat

## References
- https://attack.mitre.org/techniques/T1071/
