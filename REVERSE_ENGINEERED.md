# REVERSE_ENGINEERED.md

Reverse-engineered protocol notes for the Grouw / Daye BLE mower integration.

Last updated: 2026-06-25

## Sources

Only the Daye APK is authoritative for current protocol facts:

- Daye Power robotic mower app (`com.dayepower.dayeappleaf`):
  https://play.google.com/store/apps/details?id=com.dayepower.dayeappleaf
- Local source used on 2026-06-25:
  `/var/home/jesper/Projekt/grouw-mower-apk/`
  - `manifest.json` reports package `com.dayepower.dayeappleaf`, version
    `2.0.1`, version code `117`.
  - `decoded/jadx/resources/lib/arm64-v8a/libapp.so` contains Flutter/Dart
    strings for package `romow_bluetooth`, `flutter_blue_plus`, and user
    guidance to choose BLE device name `RobotMower_DYM`.
- Hardware scan from an iPhone near the mower on 2026-06-25:
  - Local file used as source:
    `/var/home/jesper/Hämtningar/Robot Mower_DYM_A30D43FD-EFDF-A723-E51D-C8B5A0038111.json`
  - The file is not committed; durable findings are summarized below.

Do not use the previous `com.cj.lawnmower` app, old local reverse-engineering
notes, or older APK-derived assumptions as protocol facts for this integration.
Official APK files, extracted APK contents, decompiled Java/smali, native
library dumps, and generated decompiler output must never be upstreamed.

## Confirmed From Daye APK

Confirmed current facts:

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

The app strings include `service_uuid`, `characteristic_uuid`, `writeAndNotify`,
`writeAll`, `writeFinalChunk`, `allow_long_write`,
`blueWriteAndNotification`, `BmWriteCharacteristicRequest`,
`BmSetNotifyValueRequest`, `OnDiscoveredServices`,
`OnCharacteristicReceived`, and `OnCharacteristicWritten`.

The app strings include these UUID values:

```text
49535343-1E4D-4BD9-BA61-23C647249616
49535343-fe7d-4ae5-8fa9-9fafd205e455
00002902-0000-1000-8000-00805f9b34fb
```

`00002902-0000-1000-8000-00805f9b34fb` is the standard Client
Characteristic Configuration descriptor. The two `49535343...` UUIDs are
Daye APK candidates for the mower GATT service/characteristic set, but this
pass did not recover which role each UUID has.

## Confirmed From Hardware Scan

An iPhone BLE scan near the mower confirmed this GATT table:

```text
Device name: Robot Mower_DYM

Service 180A
  Characteristic 2A29 Manufacturer Name String
  Characteristic 2A24 Model Number String
  Characteristic 2A25 Serial Number String
  Characteristic 2A27 Hardware Revision String
  Characteristic 2A26 Firmware Revision String
  Characteristic 2A28 Software Revision String
  Characteristic 2A23 System ID
  Characteristic 2A2A IEEE Regulatory Certification

Service 49535343-5D82-6099-9348-7AAC4D5FBC51
  Characteristic 49535343-026E-3A9B-954C-97DAEF17E26E

Service 49535343-C9D0-CC83-A44A-6FE238D06D33
  Characteristic 49535343-ACA3-481C-91EC-D85E28A60318

Service 49535343-FE7D-4AE5-8FA9-9FAFD205E455
  Characteristic 49535343-1E4D-4BD9-BA61-23C647249616
  Characteristic 49535343-8841-43F4-A8D4-ECBE34729BB3
  Characteristic 49535343-4C8A-39B3-2F49-511CFF073B7E
```

This confirms that `49535343-FE7D-4AE5-8FA9-9FAFD205E455` is a Daye/Grouw
mower GATT service, and that `49535343-1E4D-4BD9-BA61-23C647249616` is a
characteristic under that service. The scan did not include characteristic
properties, so read/notify/write roles are still not confirmed.

The app strings also include `BlueKey`, `ENCRYPTED_SIZE`,
`_isBufferEncrypted`, `get:_checkSum`, `parseStringToBuffer`, `createBuffer`,
and `_makeDatagram`. Treat these as evidence that the Daye app has a framed
payload layer with checksum/encryption-related logic. The exact framing,
checksum, encryption, and command payload format are not yet recovered.

## Home Assistant Discovery

Home Assistant discovery must currently match Daye APK local-name strings:

```text
Service UUID: 49535343-fe7d-4ae5-8fa9-9fafd205e455
Robot Mower_DYM*
RobotMower_DYM*
Robot_Mower*
```

Do not set read/write/notify characteristic constants until characteristic
properties and Daye app usage are confirmed.

## Not Yet Confirmed For Daye

These details are intentionally not treated as facts until confirmed from the
Daye APK or redacted real-hardware captures:

```text
Characteristic properties for the 49535343... characteristics
Notify/read characteristic UUID used by the Daye app
Write characteristic UUID used by the Daye app
Payload framing
Checksum
Status request command
Work/start/stop/dock command IDs and mode numbers
Status response field names and numeric meanings
```

The integration still contains an experimental raw JSON BLE validation surface
so hardware testing can probe candidates, but durable docs and user-facing text
must not present those candidates as Daye protocol facts.

## Validation Checklist

When validating against real hardware, capture and redact:

1. Characteristic properties for all `49535343...` characteristics.
2. Which characteristic the Daye app subscribes to for notifications.
3. Which characteristic the Daye app writes for status refresh and commands.
4. Exact bytes written for status refresh and control commands.
5. Exact notification bytes returned by the mower.
6. Mapping between UI actions in the Daye app and mower behavior.

Record only summarized findings here. Do not commit proprietary APK output or
raw logs containing BLE addresses, serial numbers, credentials, or other private
values.
