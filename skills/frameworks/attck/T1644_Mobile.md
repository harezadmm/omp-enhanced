# T1644: Out of Band Data

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may communicate with compromised devices using out of band data streams. This could be done for a variety of reasons, including evading network traffic monitoring, as a backup method of command and control, or for data exfiltration if the device is not connected to any Internet-providing networks (i.e. cellular or Wi-Fi). Several out of band data streams exist, such as SMS messages, NFC, and Bluetooth.
On Android, applications can read push notifications to capture content from SMS messages, or other out of band data streams. This requires that the user manually grant notification access to the application via the settings menu. However, the application could launch an Intent to take the user directly there.
On iOS, there is no way to programmatically read push notifications.

## Tactics
Command And Control

## Platforms
Android, iOS

## Procedure
Adversaries may communicate with compromised devices using out of band data streams. This could be done for a variety of reasons, including evading network traffic monitoring, as a backup method of command and control, or for data exfiltration if the device is not connected to any Internet-providing networks (i.e. cellular or Wi-Fi). Several out of band data streams exist, such as SMS messages, NFC, and Bluetooth.

**Known users/tools:** Android/Chuli.A, BOULDSPY, BusyGasper, CarbonSteal, Desert Scorpion, Gustuff, Monokle, Pegasus for Android, Pegasus for iOS, RCSAndroid, Rotexy, SharkBot, Skygofree, SpyC23, SpyDealer

## Mitigations
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1644/
