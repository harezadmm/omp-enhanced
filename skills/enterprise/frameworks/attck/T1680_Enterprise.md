# T1680: Local Storage Discovery

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may enumerate local drives, disks, and/or volumes and their attributes like total or free space and volume serial number. This can be done to prepare for ransomware-related encryption, to perform [Lateral Movement](https://attack.mitre.org/tactics/TA0109), or as a precursor to [Direct Volume Access](https://attack.mitre.org/techniques/T1006).
On ESXi systems, adversaries may use [Hypervisor CLI](https://attack.mitre.org/techniques/T1059/012) commands such as `esxcli` to list storage connected to the host as well as `.vmdk` files.(Citation: TrendMicro)(Citation: TrendMicro ESXI Ransomware)
On Windows systems, adversaries can use `wmic logicaldisk get` to find information about local network drives. They can also use `Get-PSDrive` in PowerShell to retrieve drives and may additionally use Windows API functions such as `GetDriveType`.(Citation: Trend Micro MUSTANG PANDA PUBLOAD HIUPAN SEPTEMBER 2024)(Citation: Volexity)
Linux has commands such as `parted`, `lsblk`, `fdisk`, `lshw`, and `df` that can list information about disk partitions such as size, type, file system types, and free space. The command `diskutil` on MacOS can be used to list disks while `system_profiler SPStorageDataType` can additionally show information such as a volume’s mount path, file system, and the type of drive in the system.
Infrastructure as a Service (IaaS) cloud providers also have commands for storage discovery such as `describe volume` in AWS, `gcloud compute disks list` in GCP, and `az disk list` in Azure.(Citation: AWS docs describe volumes)(Citation: GCP gcloud compute disks list)(Citation: azure az disk)

## Tactics
Discovery

## Platforms
ESXi, IaaS, Linux, macOS, Windows

## Procedure
Adversaries may enumerate local drives, disks, and/or volumes and their attributes like total or free space and volume serial number. This can be done to prepare for ransomware-related encryption, to perform [Lateral Movement](https://attack.mitre.org/tactics/TA0109), or as a precursor to [Direct Volume Access](https://attack.mitre.org/techniques/T1006). On ESXi systems, adversaries may use [Hypervisor CLI](https://attack.mitre.org/techniques/T1059/012) commands such as `esxcli` to list storage connected to the host as well as `.vmdk` files.(Citation: TrendMicro)(Citation: TrendMicro ESXI Ransomware)
On Windows systems, adversaries can use `wmic logicaldisk get` to find information about local network drives. They can also use `Get-PSDrive` in PowerShell to retrieve drives and may additionally use Windows API functions such as `GetDriveType`.(Citation: Trend Micro MUSTANG PANDA PUBLOAD HIUPAN SEPTEMBER 2024)(Citation: Volexity)
Linux has commands such as `parted`, `lsblk`, `fdisk`, `lshw`, and `df` that can list information about disk partitions such as size, type, file system types, and free space.

**Known users/tools:** Aria-body, AshTag, AsyncRAT, Attor, Avenger, BLINDINGCAN, Babuk, Bandook, Bankshot, Black Basta, BlackCat, BlackMould, C0017, CORESHELL, Cannon

## References
- https://attack.mitre.org/techniques/T1680/
