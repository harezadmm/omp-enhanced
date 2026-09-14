# T1645: Compromise Client Software Binary

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may modify system software binaries to establish persistent access to devices. System software binaries are used by the underlying operating system and users over adb or terminal emulators.
Adversaries may make modifications to client software binaries to carry out malicious tasks when those binaries are executed. For example, malware may come with a pre-compiled malicious binary intended to overwrite the genuine one on the device. Since these binaries may be routinely executed by the system or user, the adversary can leverage this for persistent access to the device.

## Tactics
Persistence

## Platforms
Android, iOS

## Procedure
Adversaries may modify system software binaries to establish persistent access to devices. System software binaries are used by the underlying operating system and users over adb or terminal emulators. Adversaries may make modifications to client software binaries to carry out malicious tasks when those binaries are executed. For example, malware may come with a pre-compiled malicious binary intended to overwrite the genuine one on the device.

**Known users/tools:** BrainTest, BusyGasper, DoubleAgent, Monokle, Pegasus for Android, Pegasus for iOS, ShiftyBug, SpyDealer

## Mitigations
- **System Partition Integrity** — Ensure that Android devices being used include and enable the Verified Boot capability, which cryptographically ensures the integrity of the system partition.
- **Lock Bootloader** — On devices that provide the capability to unlock the bootloader (hence allowing any operating system code to be flashed onto the device), perform periodic checks to ensure that the bootloader is locked.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.
- **Attestation** — Enable remote attestation capabilities when available (such as Android SafetyNet or Samsung Knox TIMA Attestation) and prohibit devices that fail the attestation from accessing enterprise resources.

## References
- https://attack.mitre.org/techniques/T1645/
