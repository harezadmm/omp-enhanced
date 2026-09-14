# T1125: Video Capture

**Matrix:** Enterprise | **Type:** Technique

## Description
An adversary can leverage a computer's peripheral devices (e.g., integrated cameras or webcams) or applications (e.g., video call services) to capture video recordings for the purpose of gathering information. Images may also be captured from devices or applications, potentially in specified intervals, in lieu of video files.
Malware or scripts may be used to interact with the devices through an available API provided by the operating system or an application to capture video or images. Video or image files may be written to disk and exfiltrated later. This technique differs from [Screen Capture](https://attack.mitre.org/techniques/T1113) due to use of specific devices or applications for video recording rather than capturing the victim's screen.
In macOS, there are a few different malware samples that record the user's webcam such as FruitFly and Proton. (Citation: objective-see 2017 review)

## Tactics
Collection

## Platforms
Linux, macOS, Windows

## Procedure
An adversary can leverage a computer's peripheral devices (e.g., integrated cameras or webcams) or applications (e.g., video call services) to capture video recordings for the purpose of gathering information. Images may also be captured from devices or applications, potentially in specified intervals, in lieu of video files. Malware or scripts may be used to interact with the devices through an available API provided by the operating system or an application to capture video or images. Video or image files may be written to disk and exfiltrated later.

**Known users/tools:** Agent Tesla, AsyncRAT, Bandook, Clambling, Cobian RAT, ConnectWise, Crimson, DarkComet, Derusbi, Ember Bear, Empire, EvilGrab, FIN7, Imminent Monitor, InvisiMole

## References
- https://attack.mitre.org/techniques/T1125/
