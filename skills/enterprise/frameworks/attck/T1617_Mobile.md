# T1617: Hooking

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may utilize hooking to hide the presence of artifacts associated with their behaviors to evade detection. Hooking can be used to modify return values or data structures of system APIs and function calls. This process typically involves using 3rd party root frameworks, such as Xposed or Magisk, with either a system exploit or pre-existing root access. By including custom modules for root frameworks, adversaries can hook system APIs and alter the return value and/or system data structures to alter functionality/visibility of various aspects of the system.

## Tactics
Defense Evasion

## Platforms
Android

## Procedure
Adversaries may utilize hooking to hide the presence of artifacts associated with their behaviors to evade detection. Hooking can be used to modify return values or data structures of system APIs and function calls. This process typically involves using 3rd party root frameworks, such as Xposed or Magisk, with either a system exploit or pre-existing root access. By including custom modules for root frameworks, adversaries can hook system APIs and alter the return value and/or system data structures to alter functionality/visibility of various aspects of the system.

**Known users/tools:** FjordPhantom, GodFather, Monokle

## Mitigations
- **Deploy Compromised Device Detection Method** — A variety of methods exist that can be used to enable enterprises to identify compromised (e.g. rooted/jailbroken) devices, whether using security mechanisms built directly into the device, third-party mobile security applications, enterprise mobility management (EMM)/mobile device management (MDM) 
- **Attestation** — Enable remote attestation capabilities when available (such as Android SafetyNet or Samsung Knox TIMA Attestation) and prohibit devices that fail the attestation from accessing enterprise resources.

## References
- https://attack.mitre.org/techniques/T1617/
