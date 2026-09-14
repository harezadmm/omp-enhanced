# T1012: Query Registry

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may interact with the Windows Registry to gather information about the system, configuration, and installed software.
The Registry contains a significant amount of information about the operating system, configuration, software, and security.(Citation: Wikipedia Windows Registry) Information can easily be queried using the [Reg](https://attack.mitre.org/software/S0075) utility, though other means to access the Registry exist. Some of the information may help adversaries to further their operation within a network. Adversaries may use the information from [Query Registry](https://attack.mitre.org/techniques/T1012) during automated discovery to shape follow-on behaviors, including whether or not the adversary fully infects the target and/or attempts specific actions.

## Tactics
Discovery

## Platforms
Windows

## Procedure
Adversaries may interact with the Windows Registry to gather information about the system, configuration, and installed software. The Registry contains a significant amount of information about the operating system, configuration, software, and security.(Citation: Wikipedia Windows Registry) Information can easily be queried using the [Reg](https://attack.mitre.org/software/S0075) utility, though other means to access the Registry exist. Some of the information may help adversaries to further their operation within a network. Adversaries may use the information from [Query Registry](https://attack.mitre.org/techniques/T1012) during automated discovery to shape follow-on behaviors, including whether or not the adversary fully infects the target and/or attempts specific actions.

**Known users/tools:** ADVSTORESHELL, APT32, APT39, APT41, Attor, Azorult, BACKSPACE, BabyShark, Bankshot, Bazar, BendyBear, Bisonal, BitPaymer, BlackByte, BlackByte Ransomware

## References
- https://attack.mitre.org/techniques/T1012/
