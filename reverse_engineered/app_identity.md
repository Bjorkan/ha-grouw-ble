# App Identity & BLE Discovery

## Confirmed From Daye APK

```text
Package:      com.dayepower.dayeappleaf
Version:      2.0.1
Version code: 117
Flutter app:  romow_bluetooth
BLE library:  flutter_blue_plus
BLE names:    Robot Mower_DYM, RobotMower_DYM, Robot_Mower-
```

The app contains UI strings and routes for Bluetooth connection, mower control,
mower status, mower settings, firmware update, working-time settings,
multi-area mowing, rain mowing, rain delay, ultrasound, and back-to-station /
go-to-work flows.

## BLE UUIDs

The app strings include these UUID values:

```text
49535343-1E4D-4BD9-BA61-23C647249616
49535343-fe7d-4ae5-8fa9-9fafd205e455
00002902-0000-1000-8000-00805f9b34fb
```

`00002902-0000-1000-8000-00805f9b34fb` is the standard Client
Characteristic Configuration descriptor.

## Flutter Blue Plus Integration

The app strings include:
`service_uuid`, `characteristic_uuid`, `writeAndNotify`,
`writeAll`, `writeFinalChunk`, `allow_long_write`,
`blueWriteAndNotification`, `BmWriteCharacteristicRequest`,
`BmSetNotifyValueRequest`, `OnDiscoveredServices`,
`OnCharacteristicReceived`, and `OnCharacteristicWritten`.

## Home Assistant Discovery

Home Assistant discovery must match Daye APK local-name strings:

```text
Service UUID: 49535343-fe7d-4ae5-8fa9-9fafd205e455
Robot Mower_DYM*
RobotMower_DYM*
Robot_Mower*
```

The integration uses `49535343-1E4D-4BD9-BA61-23C647249616` for both write and
notify.
