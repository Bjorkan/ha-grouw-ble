# Grouw Manual Findings

Reviewed on 2026-06-26 from local PDFs under `APK/Manuals/`. The PDFs and
their extracted text are local-only reference material and must not be
committed.

## Reviewed Manuals

```text
APK/Manuals/libble-eu.pdf  Models 17935/17936/17937
APK/Manuals/b74925.pdf     Models 17941/17947
APK/Manuals/578ac6.pdf     Models 18739/18740 CLEVR
```

## Models 17935/17936/17937

- The manual lists Bluetooth and app control as supported for all three models.
- The factory PIN is `1-2-3-4`.
- The control panel supports daily work-time choices of 4, 6, 8, 10, or 12
  hours. The manual recommends starting at 09:00.
- The app is used for multi-zone setup with fields named `Area2_Per`,
  `Area2_Dis`, `Area3_Per`, and `Area3_Dis`. The distance fields are described
  as metres along the boundary wire to the start point.
- Boundary cut is described as a factory-programmed weekly boundary-wire cut,
  depending on software version.
- Rain behavior is described as returning to the charging station, charging,
  then waiting after the sensor is dry before mowing again. The text describes
  this as product behavior, not a BLE status field.
- Firmware can be updated by USB and, according to the Bluetooth guide,
  wirelessly over Bluetooth. The manual does not expose UUIDs, payloads, or a
  BLE device name in extracted text.

## Models 17941/17947

- The manual explicitly says these models have Bluetooth and can be controlled
  from both the mower panel and the app.
- The app setup section says to tap `Connect Bluetooth` and select
  `RobotMower_DYM` from the Bluetooth device list. This corroborates the Daye
  APK local-name string already used by discovery.
- The app requires the mower PIN after the Bluetooth connection is established.
  The factory PIN is `1-2-3-4`.
- The control-panel menus line up with APK BlueKey page findings:
  `Mow in the rain`, `Set work time`, `Boundary cut`, `Change PIN`, `Alert`,
  and `Time of Machine`.
- `Alert` shows the two most recent error codes, and `Time of Machine` shows
  total operating time. This is useful UI context, but not a confirmed BLE
  status-byte mapping.
- The battery display is graphical; the manual only states that an empty-looking
  battery indicator means remaining capacity is below 30%.
- `Mow in the rain` is a setting with standard value `No`. When rain is not
  allowed, the mower returns to the station and waits until the rain sensor is
  dry before mowing again.
- `Boundary cut` is a setting for cutting along the boundary cable once per
  week.
- The manual lists user-facing error messages such as `Mower trapped`,
  `Mower lifted`, `Boundary signal error`, `Battery temperature abnormal`,
  `Charge error`, and `Hall error`. These are troubleshooting labels, not
  protocol constants unless future captures connect them to notification bytes.

## Models 18739/18740 CLEVR

- These models are a different IoT generation. The manual describes the app
  `robotic-mower connect`, account registration, QR/serial onboarding, 2.4 GHz
  Wi-Fi, and Bluetooth 4.0.
- Manual Bluetooth pairing tells users to select a device named
  `Mower_XXXXXX`, not `RobotMower_DYM`.
- The factory PIN is `0000`, unlike the `1-2-3-4` factory PIN in the DYM-era
  manuals.
- App commands can be delayed until the mower returns to Wi-Fi coverage, and the
  mower can be controlled over Wi-Fi away from home. That behavior is outside
  this local BLE-only integration.
- The app exposes schedules, edge trimming, map/start-point setup, rain delay,
  Wi-Fi settings, device parameters, firmware update, and logs. These may share
  product concepts with the Daye app, but they should not be treated as DYM BLE
  protocol facts.

## Integration Impact

- All reviewed manuals describe a 4-digit mower PIN. DYM-era manuals use
  factory PIN `1-2-3-4`; the 18739/18740 CLEVR generation uses factory PIN
  `0000`.
- The Home Assistant integration should therefore require a stored 4-digit PIN
  and ask for reauthentication when an old entry lacks one or the returned
  auth/PIN digits prove a mismatch. Auth responses without parseable PIN digits
  should remain protocol/update failures until more captures clarify them.
- The 17941/17947 manual supports keeping `RobotMower_DYM*` as a discovery
  local-name match.
- The manuals do not reveal additional BLE UUIDs, DYM payloads, notification
  layouts, checksums, or encryption details.
- Do not add `Mower_XXXXXX` discovery to the current DYM integration without a
  separate hardware scan/capture for the 18739/18740 generation. That line
  appears to belong to a Wi-Fi/IoT product family.
- Treat rain, boundary cut, multi-area, working time, alert history, total
  runtime, and firmware update as product/app settings until redacted hardware
  captures confirm the exact wire behavior for the target mower firmware.
