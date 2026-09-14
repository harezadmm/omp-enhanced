# T1102: Web Service

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may use an existing, legitimate external Web service as a means for relaying data to/from a compromised system. Popular websites, cloud services, and social media acting as a mechanism for C2 may give a significant amount of cover due to the likelihood that hosts within a network are already communicating with them prior to a compromise. Using common services, such as those offered by Google, Microsoft, or Twitter, makes it easier for adversaries to hide in expected noise.(Citation: Broadcom BirdyClient Microsoft Graph API 2024) Web service providers commonly use SSL/TLS encryption, giving adversaries an added level of protection.
Use of Web services may also protect back-end C2 infrastructure from discovery through malware binary analysis while also enabling operational resiliency (since this infrastructure may be dynamically changed).

## Tactics
Command And Control

## Platforms
ESXi, Linux, macOS, Windows

## Procedure
Adversaries may use an existing, legitimate external Web service as a means for relaying data to/from a compromised system. Popular websites, cloud services, and social media acting as a mechanism for C2 may give a significant amount of cover due to the likelihood that hosts within a network are already communicating with them prior to a compromise. Using common services, such as those offered by Google, Microsoft, or Twitter, makes it easier for adversaries to hide in expected noise.(Citation: Broadcom BirdyClient Microsoft Graph API 2024) Web service providers commonly use SSL/TLS encryption, giving adversaries an added level of protection. Use of Web services may also protect back-end C2 infrastructure from discovery through malware binary analysis while also enabling operational resiliency (since this infrastructure may be dynamically changed).

**Known users/tools:** APT32, APT41 DUST, APT42, AshTag, BADHATCH, BRICKSTORM, Bazar, BoomBox, Brute Ratel C4, Bumblebee, C0017, C0027, CHIMNEYSWEEP, Carbon, CharmPower

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.
- **Restrict Web-Based Content** — Restricting web-based content involves enforcing policies and technologies that limit access to potentially malicious websites, unsafe downloads, and unauthorized browser behaviors. This can include URL filtering, download restrictions, script blocking, and extension control to protect against explo

## References
- https://attack.mitre.org/techniques/T1102/
