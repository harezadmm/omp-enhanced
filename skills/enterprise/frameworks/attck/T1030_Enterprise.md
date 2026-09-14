# T1030: Data Transfer Size Limits

**Matrix:** Enterprise | **Type:** Technique

## Description
An adversary may exfiltrate data in fixed size chunks instead of whole files or limit packet sizes below certain thresholds. This approach may be used to avoid triggering network data transfer threshold alerts.

## Tactics
Exfiltration

## Platforms
Linux, macOS, Windows, ESXi

## Procedure
An adversary may exfiltrate data in fixed size chunks instead of whole files or limit packet sizes below certain thresholds. This approach may be used to avoid triggering network data transfer threshold alerts.

**Known users/tools:** APT28, APT41, AppleSeed, C0015, C0026, Carbanak, Cobalt Strike, Helminth, Kessel, Kevin, LuminousMoth, LunarWeb, Mythic, ObliqueRAT, OopsIE

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.

## References
- https://attack.mitre.org/techniques/T1030/
