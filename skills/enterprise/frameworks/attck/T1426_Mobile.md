# T1426: System Information Discovery

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may attempt to get detailed information about a device’s operating system and hardware, including versions, patches, and architecture. Adversaries may use the information from [System Information Discovery](https://attack.mitre.org/techniques/T1426) during automated discovery to shape follow-on behaviors, including whether or not to fully infects the target and/or attempts specific actions.
On Android, much of this information is programmatically accessible to applications through the `android.os.Build` class. (Citation: Android-Build) iOS is much more restrictive with what information is visible to applications. Typically, applications will only be able to query the device model and which version of iOS it is running.

## Tactics
Discovery

## Platforms
Android, iOS

## Procedure
Adversaries may attempt to get detailed information about a device’s operating system and hardware, including versions, patches, and architecture. Adversaries may use the information from [System Information Discovery](https://attack.mitre.org/techniques/T1426) during automated discovery to shape follow-on behaviors, including whether or not to fully infects the target and/or attempts specific actions. On Android, much of this information is programmatically accessible to applications through the `android.os.Build` class. (Citation: Android-Build) iOS is much more restrictive with what information is visible to applications.

**Known users/tools:** ANDROIDOS_ANSERVER.A, AbstractEmu, AhRat, Android/AdDisplay.Ashas, Android/Chuli.A, Anubis, Asacub, BOULDSPY, BRATA, C0033, CHEMISTGAMES, CarbonSteal, Cerberus, Chameleon, Corona Updates

## References
- https://attack.mitre.org/techniques/T1426/
