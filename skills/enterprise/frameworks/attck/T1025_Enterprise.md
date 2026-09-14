# T1025: Data from Removable Media

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may search connected removable media on computers they have compromised to find files of interest. Sensitive data can be collected from any removable media (optical disk drive, USB memory, etc.) connected to the compromised system prior to Exfiltration. Interactive command shells may be in use, and common functionality within [cmd](https://attack.mitre.org/software/S0106) may be used to gather information.
Some adversaries may also use [Automated Collection](https://attack.mitre.org/techniques/T1119) on removable media.

## Tactics
Collection

## Platforms
Linux, macOS, Windows

## Procedure
Adversaries may search connected removable media on computers they have compromised to find files of interest. Sensitive data can be collected from any removable media (optical disk drive, USB memory, etc.) connected to the compromised system prior to Exfiltration. Interactive command shells may be in use, and common functionality within [cmd](https://attack.mitre.org/software/S0106) may be used to gather information. Some adversaries may also use [Automated Collection](https://attack.mitre.org/techniques/T1119) on removable media.

**Known users/tools:** APT28, AppleSeed, Aria-body, BADNEWS, CosmicDuke, Crimson, Crutch, Explosive, FLASHFLOOD, FunnyDream, Gamaredon Group, GravityRAT, InvisiMole, Machete, MgBot

## Mitigations
- **Data Loss Prevention** — Data Loss Prevention (DLP) involves implementing strategies and technologies to identify, categorize, monitor, and control the movement of sensitive data within an organization. This includes protecting data formats indicative of Personally Identifiable Information (PII), intellectual property, or f

## References
- https://attack.mitre.org/techniques/T1025/
