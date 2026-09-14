# T1664: Exploitation for Initial Access

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may exploit software vulnerabilities to gain initial access to a mobile device.
This can be accomplished in a variety of ways. Vulnerabilities may be present in the applications, the services, the underlying operating system, or the kernel itself. Several well-known mobile device exploits exist, including FORCEDENTRY, StageFright, and BlueBorne. Furthermore, some exploits may be possible to exploit without any user interaction (i.e. zero-click exploits, see [Exploitation for Client Execution](https://attack.mitre.org/techniques/T1658)), making them particularly dangerous. Mobile operating system vendors are typically very quick to patch such critical bugs, ensuring only a small window where they can be exploited.

## Tactics
Initial Access

## Platforms
Android, iOS

## Procedure
Adversaries may exploit software vulnerabilities to gain initial access to a mobile device. This can be accomplished in a variety of ways. Vulnerabilities may be present in the applications, the services, the underlying operating system, or the kernel itself. Several well-known mobile device exploits exist, including FORCEDENTRY, StageFright, and BlueBorne.

**Known users/tools:** BRATA, Pegasus for iOS

## Mitigations
- **Antivirus/Antimalware** — Mobile security products, such as Mobile Threat Defense (MTD), offer various device-based mitigations against certain behaviors.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.

## References
- https://attack.mitre.org/techniques/T1664/
