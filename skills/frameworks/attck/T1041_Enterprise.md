# T1041: Exfiltration Over C2 Channel

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may steal data by exfiltrating it over an existing command and control channel. Stolen data is encoded into the normal communications channel using the same protocol as command and control communications.

## Tactics
Exfiltration

## Platforms
ESXi, Linux, macOS, Windows

## Procedure
Adversaries may steal data by exfiltrating it over an existing command and control channel. Stolen data is encoded into the normal communications channel using the same protocol as command and control communications.

**Known users/tools:** ADVSTORESHELL, APT3, APT32, APT39, Agrius, Amadey, AppleJeus, AppleSeed, ArcaneDoor, AshTag, Astaroth, Attor, AuTo Stealer, BACKSPACE, BADHATCH

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.
- **Data Loss Prevention** — Data Loss Prevention (DLP) involves implementing strategies and technologies to identify, categorize, monitor, and control the movement of sensitive data within an organization. This includes protecting data formats indicative of Personally Identifiable Information (PII), intellectual property, or f

## References
- https://attack.mitre.org/techniques/T1041/
