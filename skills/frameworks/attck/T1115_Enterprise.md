# T1115: Clipboard Data

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may collect data stored in the clipboard from users copying information within or between applications.
For example, on Windows adversaries can access clipboard data by using <code>clip.exe</code> or <code>Get-Clipboard</code>.(Citation: MSDN Clipboard)(Citation: clip_win_server)(Citation: CISA_AA21_200B) Additionally, adversaries may monitor then replace users’ clipboard with their data (e.g., [Transmitted Data Manipulation](https://attack.mitre.org/techniques/T1565/002)).(Citation: mining_ruby_reversinglabs)
macOS and Linux also have commands, such as <code>pbpaste</code>, to grab clipboard contents.(Citation: Operating with EmPyre)

## Tactics
Collection

## Platforms
Linux, macOS, Windows

## Procedure
Adversaries may collect data stored in the clipboard from users copying information within or between applications. For example, on Windows adversaries can access clipboard data by using <code>clip.exe</code> or <code>Get-Clipboard</code>.(Citation: MSDN Clipboard)(Citation: clip_win_server)(Citation: CISA_AA21_200B) Additionally, adversaries may monitor then replace users’ clipboard with their data (e.g., [Transmitted Data Manipulation](https://attack.mitre.org/techniques/T1565/002)).(Citation: mining_ruby_reversinglabs)
macOS and Linux also have commands, such as <code>pbpaste</code>, to grab clipboard contents.(Citation: Operating with EmPyre)

**Known users/tools:** APT38, APT39, Agent Tesla, Astaroth, Attor, BOOKWORM, CHIMNEYSWEEP, Cadelspy, Catchamas, Clambling, CosmicDuke, DarkComet, DarkGate, DarkTortilla, Empire

## References
- https://attack.mitre.org/techniques/T1115/
