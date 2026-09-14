# T1658: Exploitation for Client Execution

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may exploit software vulnerabilities in client applications to execute code. Vulnerabilities can exist in software due to insecure coding practices that can lead to unanticipated behavior. Adversaries may take advantage of certain vulnerabilities through targeted exploitation for the purpose of arbitrary code execution. Oftentimes the most valuable exploits to an offensive toolkit are those that can be used to obtain code execution on a remote system because they can be used to gain access to that system. Users will expect to see files related to the applications they commonly used to do work, so they are a useful target for exploit research and development because of their high utility.
Adversaries may use device-based zero-click exploits for code execution. These exploits are powerful because there is no user interaction required for code execution.
### SMS/iMessage Delivery
SMS and iMessage in iOS are common targets through [Drive-By Compromise](https://attack.mitre.org/techniques/T1456), [Phishing](https://attack.mitre.org/techniques/T1660), etc. Adversaries may use embed malicious links, files, etc. in SMS messages or iMessages. Mobile devices may be compromised through one-click exploits, where the victim must interact with a text message, or zero-click exploits, where no user interaction is required.
### AirDrop
Unique to iOS, AirDrop is a network protocol that allows iOS users to transfer files between iOS devices. Before patches from Apple were released, on iOS 13.4 and earlier, adversaries may force the Apple Wireless Direct Link (AWDL) interface to activate, then exploit a buffer overflow to gain access to the device and run as root without interaction from the user.

## Tactics
Execution

## Platforms
Android, iOS

## Procedure
Adversaries may exploit software vulnerabilities in client applications to execute code. Vulnerabilities can exist in software due to insecure coding practices that can lead to unanticipated behavior. Adversaries may take advantage of certain vulnerabilities through targeted exploitation for the purpose of arbitrary code execution. Oftentimes the most valuable exploits to an offensive toolkit are those that can be used to obtain code execution on a remote system because they can be used to gain access to that system.

**Known users/tools:** LightSpy, Operation Triangulation, Pegasus for iOS

## Mitigations
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.

## References
- https://attack.mitre.org/techniques/T1658/
