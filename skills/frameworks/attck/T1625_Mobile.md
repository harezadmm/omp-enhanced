# T1625: Hijack Execution Flow

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may execute their own malicious payloads by hijacking the way operating systems run applications. Hijacking execution flow can be for the purposes of persistence since this hijacked execution may reoccur over time.
There are many ways an adversary may hijack the flow of execution. A primary way is by manipulating how the operating system locates programs to be executed. How the operating system locates libraries to be used by a program can also be intercepted. Locations where the operating system looks for programs or resources, such as file directories, could also be poisoned to include malicious payloads.

## Tactics
Persistence

## Platforms
Android

## Procedure
Adversaries may execute their own malicious payloads by hijacking the way operating systems run applications. Hijacking execution flow can be for the purposes of persistence since this hijacked execution may reoccur over time. There are many ways an adversary may hijack the flow of execution. A primary way is by manipulating how the operating system locates programs to be executed.

**Known users/tools:** YiSpecter

## Mitigations
- **System Partition Integrity** — Ensure that Android devices being used include and enable the Verified Boot capability, which cryptographically ensures the integrity of the system partition.
- **Attestation** — Enable remote attestation capabilities when available (such as Android SafetyNet or Samsung Knox TIMA Attestation) and prohibit devices that fail the attestation from accessing enterprise resources.

## References
- https://attack.mitre.org/techniques/T1625/
