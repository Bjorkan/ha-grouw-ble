# Sources

Only the Daye APK and redacted hardware captures are authoritative for current
wire-protocol facts. Local manuals can corroborate product behavior and model
boundaries, but they do not define BLE packet semantics.

- Daye Power robotic mower app (`com.dayepower.dayeappleaf`):
  https://play.google.com/store/apps/details?id=com.dayepower.dayeappleaf
- Local APK tree under `APK/` (jadx-decompiled version, 2026-06-25):
  - `manifest.json` reports package `com.dayepower.dayeappleaf`, version
    `2.0.1`, version code `117`.
  - `decoded/jadx/resources/lib/arm64-v8a/libapp.so` contains Flutter/Dart
    strings for package `romow_bluetooth`, `flutter_blue_plus`, and user
    guidance to choose BLE device name `RobotMower_DYM`.
  - `blutter_out/asm/` was used on 2026-06-25 to inspect Dart AOT symbols for
    `MainLogic`, `MowerStatusLogic`, `BlueKey`, FlutterBluePlus BLE flow,
    `ChangePinLogic`, `MowerSettingLogic`, `MultiAreaMowingLogic`, and
    `WorkingTimeSettingLogic`.
- Hardware scan from an iPhone near the mower on 2026-06-25:
  - Local JSON file (not committed) with the mower's GATT table.
  - Durable findings are summarized in `gatt_table.md`.
- Android Bluetooth HCI snoop bugreport captured near the mower on 2026-06-25:
  - Source: extracted bugreport archive, path `FS/data/log/bt/btsnoop_hci.log`
    (local file, not committed)
  - User action sequence: connect, enter PIN `1234`, start, stop, start, go to base station.
  - Durable findings are summarized in `dym_protocol.md`.
- Second Android Bluetooth HCI snoop bugreport captured on 2026-06-25:
  - Source: bugreport zip archive (local file, not committed)
  - User action sequence: start docked mower, stop, start again, go to base station.
  - Durable findings are summarized in `dym_protocol.md`.
- Local Grouw manuals under `APK/Manuals/` reviewed on 2026-06-26:
  - `libble-eu.pdf` for models 17935/17936/17937.
  - `b74925.pdf` for models 17941/17947.
  - `578ac6.pdf` for models 18739/18740 CLEVR.
  - Durable findings are summarized in `manual_findings.md`.

Do not use the previous `com.cj.lawnmower` app, old local reverse-engineering
notes, or older APK-derived assumptions as protocol facts for this integration.
Official APK files, extracted APK contents, decompiled Java/smali, native
library dumps, generated decompiler output, manuals, and generated manual text
must never be upstreamed.
