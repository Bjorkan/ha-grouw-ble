<p align="left">
  <img src="custom_components/grouw_ble_mower/brand/logo.png" alt="Grouw logo" width="200"/>
</p>

# Grouw Mower for Home Assistant

Custom Home Assistant integration for local Bluetooth control of Grouw robotic
lawn mowers that use the Daye Power app (`com.dayepower.dayeappleaf`).

The integration uses Home Assistant's Bluetooth manager to resolve devices by
address. It does not run its own scanner, so the same code path can work with a
local Bluetooth adapter or a connectable Home Assistant Bluetooth proxy.

## Current Status

This project currently targets the DYM-era mower generation seen in the Daye
Power APK and in redacted hardware captures.

Confirmed target signals:

- APK version `2.0.1`, version code `117`.
- BLE names: `Robot Mower_DYM*`, `RobotMower_DYM*`, and `Robot_Mower*`.
- Service UUID: `49535343-fe7d-4ae5-8fa9-9fafd205e455`.
- Control characteristic: `49535343-1e4d-4bd9-ba61-23c647249616`.
- HCI-confirmed DYM payloads for status, start/resume, pause/stop, and dock.

Not yet treated as supported:

- Grouw 18739/18740 CLEVR / `robotic-mower connect` / `Mower_XXXXXX` devices.
- Cloud or Wi-Fi control.
- Settings writes for rain, boundary cut, ultrasound, helix, LED, multi-area,
  schedules, PIN change, or firmware update.

Detailed protocol notes live in [reverse_engineered/index.md](reverse_engineered/index.md).

## Features

- Bluetooth discovery and manual setup by BLE address.
- Required 4-digit mower PIN during setup.
- Best-effort MTU request after connect, matching the Daye app's
  FlutterBluePlus connection flow.
- Coordinator-based polling and entity availability.
- Lawn mower controls for start/resume, pause/stop, and dock.
- Entities for decoded DYM status fields:
  - mower activity
  - battery
  - raw mode code
  - last response command
  - docked state
- Debug service `grouw_ble_mower.send_raw_json` for protocol validation.

Normal polling and controls use the HCI-confirmed DYM protocol. APK-derived
BlueKey commands are available only as raw debug probes until hardware captures
prove their exact on-wire behavior for this mower generation.

## Installation

Copy the custom component into Home Assistant:

```text
config/custom_components/grouw_ble_mower/
```

Restart Home Assistant, then add the integration:

```text
Settings -> Devices & services -> Add integration -> Grouw Mower
```

Keep the mower awake and near a Bluetooth adapter or connectable BLE proxy
during first setup.

## Debug Logging

Add this while testing:

```yaml
logger:
  default: info
  logs:
    custom_components.grouw_ble_mower: debug
    bleak_retry_connector: debug
```

Do not share logs until BLE addresses, serial numbers, PINs, and other private
values are redacted.

## Raw BLE Validation

Use the raw service only while validating the protocol:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    command: status
```

Captured payloads can be sent directly:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    raw_hex: "44594d00111111111111111100000000000000160601ff0a"
    expect_cmd: "0x80"
```

Set `authenticate: false` only when deliberately testing the connection prelude
or quiet command behavior.

APK-shaped BlueKey probes are available for research:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    bluekey: mower_settings
```

Supported named BlueKey probes are `query_info`, `set_time`, `query_pin`,
`work_time`, `mower_settings`, `multi_area`, and `error_memory`. Generic probes
can use `bluekey_sub_cmd` plus optional `bluekey_data`.

Record durable findings in `reverse_engineered/` as summaries only. Do not
commit APKs, decompiled output, raw captures, or logs with private data.

## Validation Priorities

1. Confirm discovery by service UUID or DYM local name.
2. Confirm status polling remains quiet with unauthenticated DYM status
   requests.
3. Confirm start/resume, pause/stop, and dock execute without the DYM
   session/auth prelude and refresh state through the follow-up status poll.
4. Capture battery, docked, and mode fields across more mower states,
   especially the distinction between DYM mode `0x00` and `0x01`.
5. Capture charging, error, lift, and tilt payloads.
6. Treat rain as a settings feature unless a BLE status byte is captured for it.
