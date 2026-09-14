# T1458: Replication Through Removable Media

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may move onto devices by exploiting or copying malware to devices connected via USB. In the case of Lateral Movement, adversaries may utilize the physical connection of a device to a compromised or malicious charging station or PC to bypass application store requirements and install malicious applications directly.(Citation: Lau-Mactans) In the case of Initial Access, adversaries may attempt to exploit the device via the connection to gain access to data stored on the device.(Citation: Krebs-JuiceJacking) Examples of this include:
* Exploiting insecure bootloaders in a Nexus 6 or 6P device over USB and gaining the ability to perform actions including intercepting phone calls, intercepting network traffic, and obtaining the device physical location.(Citation: IBM-NexusUSB)
* Exploiting weakly-enforced security boundaries in Android devices such as the Google Pixel 2 over USB.(Citation: GoogleProjectZero-OATmeal)
* Products from Cellebrite and Grayshift purportedly that can exploit some iOS devices using physical access to the data port to unlock the passcode.(Citation: Computerworld-iPhoneCracking)

## Tactics
Initial Access, Lateral Movement

## Platforms
Android, iOS

## Procedure
Adversaries may move onto devices by exploiting or copying malware to devices connected via USB. In the case of Lateral Movement, adversaries may utilize the physical connection of a device to a compromised or malicious charging station or PC to bypass application store requirements and install malicious applications directly.(Citation: Lau-Mactans) In the case of Initial Access, adversaries may attempt to exploit the device via the connection to gain access to data stored on the device.(Citation: Krebs-JuiceJacking) Examples of this include:
* Exploiting insecure bootloaders in a Nexus 6 or 6P device over USB and gaining the ability to perform actions including intercepting phone calls, intercepting network traffic, and obtaining the device physical location.(Citation: IBM-NexusUSB)
* Exploiting weakly-enforced security boundaries in Android devices such as the Google Pixel 2 over USB.(Citation: GoogleProjectZero-OATmeal)
* Products from Cellebrite and Grayshift purportedly that can exploit some iOS devices using physical access to the data port to unlock the passcode.(Citation: Computerworld-iPhoneCracking)

**Known users/tools:** DualToy, WireLurker

## Mitigations
- **Use Recent OS Version** — New mobile operating system versions bring not only patches against discovered vulnerabilities but also often bring security architecture improvements that provide resilience against potential vulnerabilities or weaknesses that have not yet been discovered. They may also bring improvements that bloc
- **Enterprise Policy** — An enterprise mobility management (EMM), also known as mobile device management (MDM), system can be used to provision policies to mobile devices to control aspects of their allowed behavior.
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.
- **Lock Bootloader** — On devices that provide the capability to unlock the bootloader (hence allowing any operating system code to be flashed onto the device), perform periodic checks to ensure that the bootloader is locked.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.

## References
- https://attack.mitre.org/techniques/T1458/
