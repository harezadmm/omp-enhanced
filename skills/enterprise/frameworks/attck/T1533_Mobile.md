# T1533: Data from Local System

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may search local system sources, such as file systems or local databases, to find files of interest and sensitive data prior to exfiltration.
Access to local system data, which includes information stored by the operating system, often requires escalated privileges. Examples of local system data include authentication tokens, the device keyboard cache, Wi-Fi passwords, and photos. On Android, adversaries may also attempt to access files from external storage which may require additional storage-related permissions.

## Tactics
Collection

## Platforms
Android, iOS

## Procedure
Adversaries may search local system sources, such as file systems or local databases, to find files of interest and sensitive data prior to exfiltration. Access to local system data, which includes information stored by the operating system, often requires escalated privileges. Examples of local system data include authentication tokens, the device keyboard cache, Wi-Fi passwords, and photos. On Android, adversaries may also attempt to access files from external storage which may require additional storage-related permissions.

**Known users/tools:** AbstractEmu, AhRat, Anubis, BOULDSPY, BRATA, Binary Validator, BusyGasper, CHEMISTGAMES, Chameleon, Concipit1248, Corona Updates, DCHSpy, Dendroid, Desert Scorpion, DocSwap

## References
- https://attack.mitre.org/techniques/T1533/
