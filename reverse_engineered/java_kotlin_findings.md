# Decompiled Java/Kotlin Findings

Decompiled with jadx from the APK at `decoded/jadx/sources/`.

## DayeGizPlugin

`DayeGizPlugin.java` — Flutter MethodChannel plugin at `daye_giz_plugin`:

- Registers method channel `daye_giz_plugin` and event channel
  `daye_giz_event_channel`.
- Routes calls to the `GizWifiSDKProxy` Kotlin singleton.
- Known Flutter channel method names uncovered from `libapp.so` strings:
  - `bt_control_mower`
  - `bt_rain_delay_setting`
  - `changeMowerControl`
  - `getMowerSetting`
  - `mowerControl`
  - `didReceiveData`
  - `didReceiveAttrStatus`
  - `didSetSubscribe`
  - `deviceList`
  - `getDeviceStatus`
  - `write` (writes binary byte array to Gizwits device)

## GizWifiSDKProxy

`GizWifiSDKProxy.kt` — Bridges the Gizwits SDK to Flutter:

- User management: register, login, logout, change/reset password.
- Device management: bind, unbind, getBoundDevices, setSubscribe,
  getDeviceStatus, setCustomInfo.
- Device `write` method sends byte arrays via
  `GizWifiDevice.write(ConcurrentHashMap)`, keyed by `"binary"`.
- Responses come back via `didReceiveAttrStatus` callback with the
  raw binary data converted to `List<Integer>` (unsigned byte values).
- `device2Json` serializes `GizWifiDevice` fields (mac, did, productKey,
  ipAddress, isLAN, netStatus, netType, etc.).

## AppConfig

Gizwits cloud credentials (confirmed, but not used in BLE-only integration):

```text
appId:        01f37cba4e304eae8370ccd2feeaa53a
appSecret:    ad380615f8af4788927e98c221894581
productKey:   b50da224cd6745ababa0274c5607c4ad
productSecret: 989817f3ea0548d7b3c0ba9d21d7090e
```

## FlutterBluePlusPlugin

`FlutterBluePlusPlugin.java` — Standard `flutter_blue_plus` Android plugin:

- Handles scan, connect, disconnect, discover services, read/write
  characteristic, set notify, request MTU.
- Callbacks: `OnConnectionStateChanged`, `OnDiscoveredServices`,
  `OnCharacteristicReceived`, `OnCharacteristicWritten`,
  `OnDescriptorWritten`, `OnMtuChanged`, `OnReadRssi`.
- `onCharacteristicReceived` sends hex string value in the `"value"` field.
- Uses semaphore mutex to serialize BLE operations.
- Supports scan filters by service UUID, device address, device name,
  manufacturer data, and service data.
