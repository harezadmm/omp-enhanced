# T1668: Exclusive Control

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries who successfully compromise a system may attempt to maintain persistence by “closing the door” behind them  – in other words, by preventing other threat actors from initially accessing or maintaining a foothold on the same system.
For example, adversaries may patch a vulnerable, compromised system(Citation: Mandiant-iab-control)(Citation: CERT AT Fortinent Ransomware 2025) to prevent other threat actors from leveraging that vulnerability in the future. They may “close the door” in other ways, such as disabling vulnerable services(Citation: sophos-multiple-attackers), stripping privileges from accounts(Citation: aquasec-postgres-processes), or removing other malware already on the compromised device.(Citation: fsecure-netsky)
Hindering other threat actors may allow an adversary to maintain sole access to a compromised system or network. This prevents the threat actor from needing to compete with or even being removed themselves by other threat actors. It also reduces the “noise” in the environment, lowering the possibility of being caught and evicted by defenders. Finally, in the case of [Resource Hijacking](https://attack.mitre.org/techniques/T1496), leveraging a compromised device’s full power allows the threat actor to maximize profit.(Citation: sophos-multiple-attackers)

## Tactics
Persistence

## Platforms
Linux, macOS, Windows

## Procedure
Adversaries who successfully compromise a system may attempt to maintain persistence by “closing the door” behind them  – in other words, by preventing other threat actors from initially accessing or maintaining a foothold on the same system. For example, adversaries may patch a vulnerable, compromised system(Citation: Mandiant-iab-control)(Citation: CERT AT Fortinent Ransomware 2025) to prevent other threat actors from leveraging that vulnerability in the future. They may “close the door” in other ways, such as disabling vulnerable services(Citation: sophos-multiple-attackers), stripping privileges from accounts(Citation: aquasec-postgres-processes), or removing other malware already on the compromised device.(Citation: fsecure-netsky)
Hindering other threat actors may allow an adversary to maintain sole access to a compromised system or network. This prevents the threat actor from needing to compete with or even being removed themselves by other threat actors.

## References
- https://attack.mitre.org/techniques/T1668/
