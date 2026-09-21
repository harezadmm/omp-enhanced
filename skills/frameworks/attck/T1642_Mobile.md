# T1642: Endpoint Denial of Service

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may perform Endpoint Denial of Service (DoS) attacks to degrade or block the availability of services to users.
On Android versions prior to 7, apps can abuse Device Administrator access to reset the device lock passcode, preventing the user from unlocking the device. After Android 7, only device or profile owners (e.g. MDMs) can reset the device’s passcode.(Citation: Android resetPassword)
On iOS devices, this technique does not work because mobile device management servers can only remove the screen lock passcode; they cannot set a new passcode. However, on jailbroken devices, malware has been discovered that can lock the user out of the device.(Citation: Xiao-KeyRaider)

## Tactics
Impact

## Platforms
Android, iOS

## Procedure
Adversaries may perform Endpoint Denial of Service (DoS) attacks to degrade or block the availability of services to users. On Android versions prior to 7, apps can abuse Device Administrator access to reset the device lock passcode, preventing the user from unlocking the device. After Android 7, only device or profile owners (e.g. MDMs) can reset the device’s passcode.(Citation: Android resetPassword)
On iOS devices, this technique does not work because mobile device management servers can only remove the screen lock passcode; they cannot set a new passcode.

**Known users/tools:** Charger, Exobot, GPlayed, LightSpy, Xbot

## Mitigations
- **Use Recent OS Version** — New mobile operating system versions bring not only patches against discovered vulnerabilities but also often bring security architecture improvements that provide resilience against potential vulnerabilities or weaknesses that have not yet been discovered. They may also bring improvements that bloc
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1642/
