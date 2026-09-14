# T1663: Remote Access Software

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may use legitimate remote access software, such as `VNC`, `TeamViewer`, `AirDroid`, `AirMirror`, etc., to establish an interactive command and control channel to target mobile devices.
Remote access applications may be installed and used post-compromise as an alternate communication channel for redundant access or as a way to establish an interactive remote session with the target device. They may also be used as a component of malware to establish a reverse connection to an adversary-controlled system or service. Installation of remote access tools may also include persistence.

## Tactics
Command And Control

## Platforms
Android, iOS

## Procedure
Adversaries may use legitimate remote access software, such as `VNC`, `TeamViewer`, `AirDroid`, `AirMirror`, etc., to establish an interactive command and control channel to target mobile devices. Remote access applications may be installed and used post-compromise as an alternate communication channel for redundant access or as a way to establish an interactive remote session with the target device. They may also be used as a component of malware to establish a reverse connection to an adversary-controlled system or service. Installation of remote access tools may also include persistence.

**Known users/tools:** BRATA, Escobar

## Mitigations
- **Enterprise Policy** — An enterprise mobility management (EMM), also known as mobile device management (MDM), system can be used to provision policies to mobile devices to control aspects of their allowed behavior.
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1663/
