# T1429: Audio Capture

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may capture audio to collect information by leveraging standard operating system APIs of a mobile device. Examples of audio information adversaries may target include user conversations, surroundings, phone calls, or other sensitive information.
Android and iOS, by default, require that applications request device microphone access from the user.
On Android devices, applications must hold the `RECORD_AUDIO` permission to access the microphone or the `CAPTURE_AUDIO_OUTPUT` permission to access audio output. Because Android does not allow third-party applications to hold the `CAPTURE_AUDIO_OUTPUT` permission by default, only privileged applications, such as those distributed by Google or the device vendor, can access audio output.(Citation: Android Permissions) However, adversaries may be able to gain this access after successfully elevating their privileges. With the `CAPTURE_AUDIO_OUTPUT` permission, adversaries may pass the `MediaRecorder.AudioSource.VOICE_CALL` constant to `MediaRecorder.setAudioOutput`, allowing capture of both voice call uplink and downlink.(Citation: Manifest.permission)
On iOS devices, applications must include the `NSMicrophoneUsageDescription` key in their `Info.plist` file to access the microphone.(Citation: Requesting Auth-Media Capture)

## Tactics
Collection

## Platforms
Android, iOS

## Procedure
Adversaries may capture audio to collect information by leveraging standard operating system APIs of a mobile device. Examples of audio information adversaries may target include user conversations, surroundings, phone calls, or other sensitive information. Android and iOS, by default, require that applications request device microphone access from the user. On Android devices, applications must hold the `RECORD_AUDIO` permission to access the microphone or the `CAPTURE_AUDIO_OUTPUT` permission to access audio output.

**Known users/tools:** AbstractEmu, AhRat, AndroRAT, Anubis, BOULDSPY, BusyGasper, C0033, CarbonSteal, Corona Updates, DCHSpy, Dendroid, Desert Scorpion, DocSwap, DoubleAgent, DroidJack

## Mitigations
- **Use Recent OS Version** — New mobile operating system versions bring not only patches against discovered vulnerabilities but also often bring security architecture improvements that provide resilience against potential vulnerabilities or weaknesses that have not yet been discovered. They may also bring improvements that bloc
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1429/
