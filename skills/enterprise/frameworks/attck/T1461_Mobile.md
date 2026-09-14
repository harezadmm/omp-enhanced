# T1461: Lockscreen Bypass

**Matrix:** Mobile | **Type:** Technique

## Description
An adversary with physical access to a mobile device may seek to bypass the device’s lockscreen. Several methods exist to accomplish this, including:
* Biometric spoofing: If biometric authentication is used, an adversary could attempt to spoof a mobile device’s biometric authentication mechanism. Both iOS and Android partly mitigate this attack by requiring the device’s passcode rather than biometrics to unlock the device after every device restart, and after a set or random amount of time.(Citation: SRLabs-Fingerprint)(Citation: TheSun-FaceID)
* Unlock code bypass: An adversary could attempt to brute-force or otherwise guess the lockscreen passcode (typically a PIN or password), including physically observing (“shoulder surfing”) the device owner’s use of the lockscreen passcode. Mobile OS vendors partly mitigate this by implementing incremental backoff timers after a set number of failed unlock attempts, as well as a configurable full device wipe after several failed unlock attempts.
* Vulnerability exploit: Techniques have been periodically demonstrated that exploit mobile devices to bypass the lockscreen. The vulnerabilities are generally patched by the device or OS vendor once disclosed.(Citation: Wired-AndroidBypass)(Citation: Kaspersky-iOSBypass)

## Tactics
Initial Access

## Platforms
Android, iOS

## Procedure
An adversary with physical access to a mobile device may seek to bypass the device’s lockscreen. Several methods exist to accomplish this, including:
* Biometric spoofing: If biometric authentication is used, an adversary could attempt to spoof a mobile device’s biometric authentication mechanism. Both iOS and Android partly mitigate this attack by requiring the device’s passcode rather than biometrics to unlock the device after every device restart, and after a set or random amount of time.(Citation: SRLabs-Fingerprint)(Citation: TheSun-FaceID)
* Unlock code bypass: An adversary could attempt to brute-force or otherwise guess the lockscreen passcode (typically a PIN or password), including physically observing (“shoulder surfing”) the device owner’s use of the lockscreen passcode. Mobile OS vendors partly mitigate this by implementing incremental backoff timers after a set number of failed unlock attempts, as well as a configurable full device wipe after several failed unlock attempts.

**Known users/tools:** BRATA, Chameleon, Escobar, VajraSpy

## Mitigations
- **Enterprise Policy** — An enterprise mobility management (EMM), also known as mobile device management (MDM), system can be used to provision policies to mobile devices to control aspects of their allowed behavior.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.

## References
- https://attack.mitre.org/techniques/T1461/
