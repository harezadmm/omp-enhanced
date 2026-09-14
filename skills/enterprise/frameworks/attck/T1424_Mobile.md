# T1424: Process Discovery

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may attempt to get information about running processes on a device. Information obtained could be used to gain an understanding of common software/applications running on devices within a network. Adversaries may use the information from [Process Discovery](https://attack.mitre.org/techniques/T1424) during automated discovery to shape follow-on behaviors, including whether or not the adversary fully infects the target and/or attempts specific actions.
Recent Android security enhancements have made it more difficult to obtain a list of running processes. On Android 7 and later, there is no way for an application to obtain the process list without abusing elevated privileges. This is due to the Android kernel utilizing the `hidepid` mount feature. Prior to Android 7, applications could utilize the `ps` command or examine the `/proc` directory on the device.(Citation: Android-SELinuxChanges)
In iOS, applications have previously been able to use the `sysctl` command to obtain a list of running processes. This functionality has been removed in later iOS versions.

## Tactics
Discovery

## Platforms
Android, iOS

## Procedure
Adversaries may attempt to get information about running processes on a device. Information obtained could be used to gain an understanding of common software/applications running on devices within a network. Adversaries may use the information from [Process Discovery](https://attack.mitre.org/techniques/T1424) during automated discovery to shape follow-on behaviors, including whether or not the adversary fully infects the target and/or attempts specific actions. Recent Android security enhancements have made it more difficult to obtain a list of running processes.

**Known users/tools:** Agent Smith, Anubis, Binary Validator, CherryBlos, GolfSpy, HenBox, LightSpy, Operation Triangulation, Rotexy, SharkBot, TriangleDB, WolfRAT, YiSpecter

## Mitigations
- **Use Recent OS Version** — New mobile operating system versions bring not only patches against discovered vulnerabilities but also often bring security architecture improvements that provide resilience against potential vulnerabilities or weaknesses that have not yet been discovered. They may also bring improvements that bloc
- **Attestation** — Enable remote attestation capabilities when available (such as Android SafetyNet or Samsung Knox TIMA Attestation) and prohibit devices that fail the attestation from accessing enterprise resources.

## References
- https://attack.mitre.org/techniques/T1424/
