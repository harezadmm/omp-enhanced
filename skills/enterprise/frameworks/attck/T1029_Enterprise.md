# T1029: Scheduled Transfer

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may schedule data exfiltration to be performed only at certain times of day or at certain intervals. This could be done to blend traffic patterns with normal activity or availability.
When scheduled exfiltration is used, other exfiltration techniques likely apply as well to transfer the information out of the network, such as [Exfiltration Over C2 Channel](https://attack.mitre.org/techniques/T1041) or [Exfiltration Over Alternative Protocol](https://attack.mitre.org/techniques/T1048).

## Tactics
Exfiltration

## Platforms
Linux, macOS, Windows

## Procedure
Adversaries may schedule data exfiltration to be performed only at certain times of day or at certain intervals. This could be done to blend traffic patterns with normal activity or availability. When scheduled exfiltration is used, other exfiltration techniques likely apply as well to transfer the information out of the network, such as [Exfiltration Over C2 Channel](https://attack.mitre.org/techniques/T1041) or [Exfiltration Over Alternative Protocol](https://attack.mitre.org/techniques/T1048).

**Known users/tools:** ADVSTORESHELL, Chrommme, Cobalt Strike, ComRAT, Dipsind, Flagpro, Higaisa, Kazuar, LightNeuron, Linfo, Machete, Ninja, POWERSTATS, ShadowPad, Shark

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.

## References
- https://attack.mitre.org/techniques/T1029/
