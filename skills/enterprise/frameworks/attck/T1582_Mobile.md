# T1582: SMS Control

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may delete, alter, or send SMS messages without user authorization. This could be used to hide C2 SMS messages, spread malware, or various external effects.
This can be accomplished by requesting the `RECEIVE_SMS` or `SEND_SMS` permissions depending on what the malware is attempting to do. If the app is set as the default SMS handler on the device, the `SMS_DELIVER` broadcast intent can be registered, which allows the app to write to the SMS content provider. The content provider directly modifies the messaging database on the device, which could allow malicious applications with this ability to insert, modify, or delete arbitrary messages on the device.(Citation: SMS KitKat)(Citation: Android SmsProvider)

## Tactics
Impact

## Platforms
Android

## Procedure
Adversaries may delete, alter, or send SMS messages without user authorization. This could be used to hide C2 SMS messages, spread malware, or various external effects. This can be accomplished by requesting the `RECEIVE_SMS` or `SEND_SMS` permissions depending on what the malware is attempting to do. If the app is set as the default SMS handler on the device, the `SMS_DELIVER` broadcast intent can be registered, which allows the app to write to the SMS content provider.

**Known users/tools:** AhRat, AndroRAT, Anubis, Asacub, BusyGasper, Cerberus, Corona Updates, Crocodilus, Dendroid, Desert Scorpion, Drinik, Escobar, Exobot, FakeSpy, FluBot

## Mitigations
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1582/
