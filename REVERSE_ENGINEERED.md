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
BLE names:    RobotMower_DYM, Robot_Mower-
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

The app strings also include `BlueKey`, `ENCRYPTED_SIZE`,
`_isBufferEncrypted`, `get:_checkSum`, `parseStringToBuffer`, `createBuffer`,
and `_makeDatagram`. Treat these as evidence that the Daye app has a framed
payload layer with checksum/encryption-related logic. The exact framing,
checksum, encryption, and command payload format are not yet recovered.

## Home Assistant Discovery

Home Assistant discovery must currently match Daye APK local-name strings:

```text
RobotMower_DYM*
Robot_Mower*
```

Do not add service UUID discovery matches until the UUID roles are confirmed
from the Daye APK or real hardware captures.

## Not Yet Confirmed For Daye

These details are intentionally not treated as facts until confirmed from the
Daye APK or redacted real-hardware captures:

```text
Whether 49535343-1E4D-4BD9-BA61-23C647249616 is service or characteristic
Whether 49535343-fe7d-4ae5-8fa9-9fafd205e455 is service or characteristic
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

1. Advertised BLE local name and service UUIDs.
2. GATT services and characteristics used by the Daye app.
3. Exact bytes written for status refresh and control commands.
4. Exact notification bytes returned by the mower.
5. Mapping between UI actions in the Daye app and mower behavior.

Record only summarized findings here. Do not commit proprietary APK output or
raw logs containing BLE addresses, serial numbers, credentials, or other private
values.
