# T1421: System Network Connections Discovery

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may attempt to get a listing of network connections to or from the compromised device they are currently accessing or from remote systems by querying for information over the network.
This is typically accomplished by utilizing device APIs to collect information about nearby networks, such as Wi-Fi, Bluetooth, and cellular tower connections. On Android, this can be done by querying the respective APIs:
* `WifiInfo` for information about the current Wi-Fi connection, as well as nearby Wi-Fi networks. Querying the `WiFiInfo` API requires the application to hold the `ACCESS_FINE_LOCATION` permission.
* `BluetoothAdapter` for information about Bluetooth devices, which also requires the application to hold several permissions granted by the user at runtime.
* For Android versions prior to Q, applications can use the `TelephonyManager.getNeighboringCellInfo()` method. For Q and later, applications can use the `TelephonyManager.getAllCellInfo()` method. Both methods require the application hold the `ACCESS_FINE_LOCATION` permission.

## Tactics
Discovery

## Platforms
Android

## Procedure
Adversaries may attempt to get a listing of network connections to or from the compromised device they are currently accessing or from remote systems by querying for information over the network. This is typically accomplished by utilizing device APIs to collect information about nearby networks, such as Wi-Fi, Bluetooth, and cellular tower connections. On Android, this can be done by querying the respective APIs:
* `WifiInfo` for information about the current Wi-Fi connection, as well as nearby Wi-Fi networks. Querying the `WiFiInfo` API requires the application to hold the `ACCESS_FINE_LOCATION` permission.

**Known users/tools:** C0033, Exodus, FakeSpy, FlexiSpy, LightSpy, Monokle, Pallas, Pegasus for iOS, ViperRAT

## References
- https://attack.mitre.org/techniques/T1421/
