<p align="left">
  <img src="custom_components/grouw_ble_mower/brand/logo.png" alt="Grouw logo" width="200"/>
</p>

# Grouw Mower for Home Assistant

[Svenska](README_sv.md) | [Dansk](README_da.md)

Custom Home Assistant integration for local Bluetooth control of Grouw robotic
lawn mowers that use the Daye Power app (`com.dayepower.dayeappleaf`).

The integration uses Home Assistant's Bluetooth manager to resolve devices by
address. It does not run its own scanner, so the same code path can work with a
local Bluetooth adapter or a connectable Home Assistant Bluetooth proxy. BLE
communication and Daye/Grouw protocol handling are provided by the
`pygrouw` Python library:
[GitHub](https://github.com/Bjorkan/pyGrouw) |
[PyPI](https://pypi.org/project/pygrouw/).

## Current Status

This project currently targets the DYM-era mower generation seen in the Daye
Power APK and in redacted hardware captures.

Confirmed target signals:

- APK version `2.0.1`, version code `117`.
- BLE names: `Robot Mower_DYM*`, `RobotMower_DYM*`, and `Robot_Mower*`.
- Service UUID: `49535343-fe7d-4ae5-8fa9-9fafd205e455`.
- Control characteristic: `49535343-1e4d-4bd9-ba61-23c647249616`.
- HCI-confirmed DYM payloads for status, start/resume, pause/stop, dock, PIN change, multi-area,
  mower settings, and work time schedule.

Not yet treated as supported:

- Grouw 18739/18740 CLEVR / `robotic-mower connect` / `Mower_XXXXXX` devices.
- Cloud or Wi-Fi control.
- Firmware update.

Detailed protocol notes live in the companion library:
[Bjorkan/pyGrouw reverse_engineered/index.md](https://github.com/Bjorkan/pyGrouw/blob/main/reverse_engineered/index.md).

## Features

- Bluetooth discovery and manual setup by BLE address.
- Required 4-digit mower PIN during setup.
- BLE communication through `pygrouw`, including best-effort MTU request after
  connect, matching the Daye app's FlutterBluePlus connection flow.
- Coordinator-based polling and entity availability.
- Lawn mower controls for start/resume, pause/stop, and dock.
- Entities for decoded DYM status fields:
  - mower activity
  - battery
  - raw mode code
  - last response command
  - docked state
- Entities for mower settings (after reading with the get services):
  - multi-area percentages and distances (Area 2, Area 3)
  - rain delay hours and minutes
  - unknown setting byte
  - mow in rain, boundary cut, helix, LED
- Debug service `grouw_ble_mower.send_raw_json` for protocol validation.
- Service `grouw_ble_mower.change_pin` to change the mower PIN.
- Service `grouw_ble_mower.set_multi_area` to configure multi-area mowing.
- Service `grouw_ble_mower.set_mower_settings` to configure rain, boundary cut, helix, and rain delay.
- Service `grouw_ble_mower.set_work_times` to configure the weekly work time schedule.
- Services `grouw_ble_mower.get_multi_area`, `get_mower_settings`, and `get_work_times`
  to read settings from the mower, return response data, and update the
  corresponding sensors.

Normal polling and controls use the HCI-confirmed DYM protocol. APK-derived
BlueKey commands are available only as raw debug probes until hardware captures
prove their exact on-wire behavior for this mower generation.

Settings read/write operations require authentication and are performed on
demand through services. They are not part of the normal polling cycle.
The read services always return Home Assistant service response data. The raw
debug and write services return their pyGrouw response when the action call
requests response data.

## Installation

### HACS

HACS must already be installed in Home Assistant.

Open this repository in HACS:

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bjorkan&repository=ha-grouw-ble&category=integration)

Install the integration in HACS, restart Home Assistant, then add the
integration:

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/redirect/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=grouw_ble_mower)

```text
Settings -> Devices & services -> Add integration -> Grouw Mower
```

### Manual

Copy the custom component into Home Assistant:

```text
config/custom_components/grouw_ble_mower/
```

Restart Home Assistant, then add the integration from Home Assistant's
Devices & services page.

Keep the mower awake and near a Bluetooth adapter or connectable BLE proxy
during first setup.

## Debug Logging

Add this while testing:

```yaml
logger:
  default: info
  logs:
    custom_components.grouw_ble_mower: debug
    pygrouw: debug
    bleak_retry_connector: debug
```

Do not share logs until BLE addresses, serial numbers, PINs, and other private
values are redacted.

## Services

### Raw BLE Validation

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

### Change PIN

```yaml
action: grouw_ble_mower.change_pin
data:
  new_pin: "4321"
```

### Multi-area settings

Read multi-area settings:

```yaml
action: grouw_ble_mower.get_multi_area
response_variable: multi_area
```

Set multi-area settings:

```yaml
action: grouw_ble_mower.set_multi_area
data:
  area2_percentage: 5
  area2_distance: 12
  area3_percentage: 16
  area3_distance: 74
```

### Mower settings

Read mower settings:

```yaml
action: grouw_ble_mower.get_mower_settings
response_variable: mower_settings
```

Set mower settings:

```yaml
action: grouw_ble_mower.set_mower_settings
data:
  mow_in_rain: true
  boundary_cut: false
  helix: true
  rain_delay_hours: 4
  rain_delay_minutes: 13
```

### Work time schedule

Read work time schedule:

```yaml
action: grouw_ble_mower.get_work_times
response_variable: work_times
```

Set work time schedule (7 days, Monday through Sunday):

```yaml
action: grouw_ble_mower.set_work_times
data:
  starts:
    - [18, 0]
    - [11, 13]
    - [11, 21]
    - [4, 7]
    - [18, 0]
    - [10, 1]
    - [17, 50]
  durations:
    - [1, 0]
    - [11, 9]
    - [10, 0]
    - [3, 0]
    - [4, 0]
    - [2, 0]
    - [6, 0]
```

### Targeting a mower

All services accept optional `address` or `entry_id` fields to target a specific
mower when multiple are configured. When only one mower is configured, the
fields are optional.

Record durable findings in the companion library's `reverse_engineered/` folder
as summaries only. Do not commit APKs, decompiled output, raw captures, or logs
with private data.

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
