# T1398: Boot or Logon Initialization Scripts

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may use scripts automatically executed at boot or logon initialization to establish persistence. Initialization scripts are part of the underlying operating system and are not accessible to the user unless the device has been rooted or jailbroken.

## Tactics
Persistence

## Platforms
Android, iOS

## Procedure
Adversaries may use scripts automatically executed at boot or logon initialization to establish persistence. Initialization scripts are part of the underlying operating system and are not accessible to the user unless the device has been rooted or jailbroken.

**Known users/tools:** AhRat, BOULDSPY, LightSpy, OldBoot

## Mitigations
- **System Partition Integrity** — Ensure that Android devices being used include and enable the Verified Boot capability, which cryptographically ensures the integrity of the system partition.
- **Lock Bootloader** — On devices that provide the capability to unlock the bootloader (hence allowing any operating system code to be flashed onto the device), perform periodic checks to ensure that the bootloader is locked.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.
- **Attestation** — Enable remote attestation capabilities when available (such as Android SafetyNet or Samsung Knox TIMA Attestation) and prohibit devices that fail the attestation from accessing enterprise resources.

## References
- https://attack.mitre.org/techniques/T1398/
