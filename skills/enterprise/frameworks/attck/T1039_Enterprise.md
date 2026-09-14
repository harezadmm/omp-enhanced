# T1039: Data from Network Shared Drive

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may search network shares on computers they have compromised to find files of interest. Sensitive data can be collected from remote systems via shared network drives (host shared directory, network file server, etc.) that are accessible from the current system prior to Exfiltration. Interactive command shells may be in use, and common functionality within [cmd](https://attack.mitre.org/software/S0106) may be used to gather information.

## Tactics
Collection

## Platforms
Linux, macOS, Windows

## Procedure
Adversaries may search network shares on computers they have compromised to find files of interest. Sensitive data can be collected from remote systems via shared network drives (host shared directory, network file server, etc.) that are accessible from the current system prior to Exfiltration. Interactive command shells may be in use, and common functionality within [cmd](https://attack.mitre.org/software/S0106) may be used to gather information.

**Known users/tools:** APT28, BADNEWS, BRONZE BUTLER, C0015, Chimera, CosmicDuke, Egregor, Fox Kitten, Gamaredon Group, Ramsay, RedCurl, Sowbug, menuPass

## References
- https://attack.mitre.org/techniques/T1039/
