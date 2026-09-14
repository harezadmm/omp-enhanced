# T1630: Indicator Removal on Host

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may delete, alter, or hide generated artifacts on a device, including files, jailbreak status, or the malicious application itself. These actions may interfere with event collection, reporting, or other notifications used to detect intrusion activity. This may compromise the integrity of mobile security solutions by causing notable events or information to go unreported.

## Tactics
Defense Evasion

## Platforms
iOS, Android

## Procedure
Adversaries may delete, alter, or hide generated artifacts on a device, including files, jailbreak status, or the malicious application itself. These actions may interfere with event collection, reporting, or other notifications used to detect intrusion activity. This may compromise the integrity of mobile security solutions by causing notable events or information to go unreported.

**Known users/tools:** Chameleon, GodFather, Operation Triangulation

## Mitigations
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.
- **Attestation** — Enable remote attestation capabilities when available (such as Android SafetyNet or Samsung Knox TIMA Attestation) and prohibit devices that fail the attestation from accessing enterprise resources.

## References
- https://attack.mitre.org/techniques/T1630/
