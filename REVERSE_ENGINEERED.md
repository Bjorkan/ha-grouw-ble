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
- Android Bluetooth HCI snoop bugreport captured near the mower on 2026-06-25:
  - Local file used as source:
    `/var/home/jesper/Hämtningar/bugreport-m3qxeea-BP4A/FS/data/log/bt/btsnoop_hci.log`
  - User action sequence: connect, enter PIN `1234`, start, stop, start, go
    to base station.
  - The file is not committed; durable findings are summarized below.
- Second Android Bluetooth HCI snoop bugreport captured on 2026-06-25:
  - Local zip used as source:
    `/var/home/jesper/Hämtningar/bugreport-m3qxeea-BP4A(1).zip`
  - User action sequence: start docked mower, stop, start again, go to base
    station.
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
Characteristic Configuration descriptor.

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
characteristic under that service.

## Confirmed From Android HCI Snoop

The Daye app's ATT discovery confirmed the primary control characteristic:

```text
Service 49535343-FE7D-4AE5-8FA9-9FAFD205E455, handles 0x0017-0x0020
  Declaration handle 0x0018
  Value handle       0x0019
  UUID               49535343-1E4D-4BD9-BA61-23C647249616
  Properties         0x1c: write without response, write, notify
  CCCD handle        0x001a
```

The Daye app enables notifications by writing `0100` to handle `0x001a`, then
uses ATT Write Request, not Write Command, to write 24-byte DYM payloads to
handle `0x0019`. Notifications arrive on the same handle.

After each fresh BLE connection, the app sends a session/authentication prelude
before status polling or commands. This matches the observed UI behavior where
the app asks for the PIN again after disconnecting.

Captured Daye write payloads:

```text
Status poll:
44594d00111111111111111100000000000000160601ff0a

Session/auth-related:
44594d02141a0619121c000000000000000000160601ff0a
44594d02141a06191220000000000000000000160601ff0a
44594d0c000000000000000000000000000000160601ff0a

Start mowing from dock/station:
44594d01020000000000000000000000000000160601ff0a

Resume/start after stop on lawn:
44594d01000000000000000000000000000000160601ff0a

Pause/stop:
44594d01010000000000000000000000000000160601ff0a

Go to base station:
44594d01030000000000000000000000000000160601ff0a
```

The second capture clarified that `44594d0100...` is used when the mower is
started again after stop, while `44594d0102...` is used when starting from the
docked/station state.

The `44594d0214...` payload embeds the phone date/time as
`year, month, day, hour, minute`, e.g. `1a 06 19 12 1c` for
2026-06-25 18:28. The integration regenerates this payload on every BLE
transaction, then sends `44594d0c...` before the requested status/command
payload. Auth responses use response type `0x8c` and are ignored while waiting
for status response type `0x80`.

Captured status notifications are 22-byte DYM payloads such as:

```text
44594d8064321b000004000114444100000000160601
44594d8064321b000004000100444100000000160601
44594d8064321b000004000103444100000000160601
```

Observed status field mapping:

```text
byte 0..2  "DYM"
byte 3     response type, 0x80 for status
byte 4     battery percentage candidate, observed 0x64 and 0x32
byte 7     station/docked candidate:
            0x01 docked / at station
            0x00 away from station
byte 12    mode candidate:
            0x00 mowing / active after start
            0x03 returning after go-to-base
            0x14 stopped / docked / idle after stop
byte 19..21 notification trailer: 16 06 01
```

The second capture confirmed byte 7 changes from `0x01` while docked to `0x00`
after starting, and later returns to `0x01` when back at the station. More
captures across charging, error, rain, lift and tilt states are still needed.

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

The integration uses `49535343-1E4D-4BD9-BA61-23C647249616` for both write and
notify.

## Not Yet Confirmed For Daye

These details are intentionally not treated as facts until confirmed from the
Daye APK or redacted real-hardware captures:

```text
Meaning of every status response byte
Whether any checksum exists beyond the fixed ff0a write trailer
Charging, error, rain, lift and tilt status values
Whether byte 12 distinguishes all active, idle, stopped and returning states
```

The integration still contains an experimental raw BLE payload validation
surface so hardware testing can probe additional captures.

## Validation Checklist

When validating against real hardware, capture and redact:

1. Battery, station and mode mapping over more mower states.
2. Charging, error, rain, lift and tilt notification payloads.
3. Exact notification bytes after each newly tested action.
4. Mapping between UI actions in the Daye app and mower behavior.

Record only summarized findings here. Do not commit proprietary APK output or
raw logs containing BLE addresses, serial numbers, credentials, or other private
values.
