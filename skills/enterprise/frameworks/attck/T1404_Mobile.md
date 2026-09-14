# T1404: Exploitation for Privilege Escalation

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may exploit software vulnerabilities in order to elevate privileges. Exploitation of a software vulnerability occurs when an adversary takes advantage of a programming error in an application, service, within the operating system software, or kernel itself to execute adversary-controlled code. Security constructions, such as permission levels, will often hinder access to information and use of certain techniques. Adversaries will likely need to perform privilege escalation to include use of software exploitation to circumvent those restrictions.
When initially gaining access to a device, an adversary may be operating within a lower privileged process which will prevent them from accessing certain resources on the system. Vulnerabilities may exist, usually in operating system components and applications running at higher permissions, that can be exploited to gain higher levels of access on the system. This could enable someone to move from unprivileged or user- level permission to root permissions depending on the component that is vulnerable.

## Tactics
Privilege Escalation

## Platforms
Android, iOS

## Procedure
Adversaries may exploit software vulnerabilities in order to elevate privileges. Exploitation of a software vulnerability occurs when an adversary takes advantage of a programming error in an application, service, within the operating system software, or kernel itself to execute adversary-controlled code. Security constructions, such as permission levels, will often hinder access to information and use of certain techniques. Adversaries will likely need to perform privilege escalation to include use of software exploitation to circumvent those restrictions.

**Known users/tools:** AbstractEmu, Agent Smith, BrainTest, DoubleAgent, Dvmap, Exodus, FinFisher, Gooligan, HummingBad, INSOMNIA, LightSpy, Operation Triangulation, Pegasus for Android, Pegasus for iOS, Phenakite

## Mitigations
- **Security Updates** — Install security updates in response to discovered vulnerabilities.
- **Deploy Compromised Device Detection Method** — A variety of methods exist that can be used to enable enterprises to identify compromised (e.g. rooted/jailbroken) devices, whether using security mechanisms built directly into the device, third-party mobile security applications, enterprise mobility management (EMM)/mobile device management (MDM) 
- **Attestation** — Enable remote attestation capabilities when available (such as Android SafetyNet or Samsung Knox TIMA Attestation) and prohibit devices that fail the attestation from accessing enterprise resources.

## References
- https://attack.mitre.org/techniques/T1404/
