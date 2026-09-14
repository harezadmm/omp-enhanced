# T1603: Scheduled Task/Job

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may abuse task scheduling functionality to facilitate initial or recurring execution of malicious code. On Android and iOS, APIs and libraries exist to facilitate scheduling tasks to execute at a specified date, time, or interval.
On Android, the `WorkManager` API allows asynchronous tasks to be scheduled with the system. `WorkManager` was introduced to unify task scheduling on Android, using `JobScheduler`, `GcmNetworkManager`, and `AlarmManager` internally. `WorkManager` offers a lot of flexibility for scheduling, including periodically, one time, or constraint-based (e.g. only when the device is charging).(Citation: Android WorkManager)
On iOS, the `NSBackgroundActivityScheduler` API allows asynchronous tasks to be scheduled with the system. The tasks can be scheduled to be repeating or non-repeating, however, the system chooses when the tasks will be executed. The app can choose the interval for repeating tasks, or the delay between scheduling and execution for one-time tasks.(Citation: Apple NSBackgroundActivityScheduler)

## Tactics
Execution, Persistence

## Platforms
Android, iOS

## Procedure
Adversaries may abuse task scheduling functionality to facilitate initial or recurring execution of malicious code. On Android and iOS, APIs and libraries exist to facilitate scheduling tasks to execute at a specified date, time, or interval. On Android, the `WorkManager` API allows asynchronous tasks to be scheduled with the system. `WorkManager` was introduced to unify task scheduling on Android, using `JobScheduler`, `GcmNetworkManager`, and `AlarmManager` internally.

**Known users/tools:** Chameleon, GPlayed, GodFather, TERRACOTTA, Tiktok Pro

## References
- https://attack.mitre.org/techniques/T1603/
