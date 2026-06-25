# Grouw BLE Mower for Home Assistant

Custom integration scaffold for Grouw / `robotic-mower connect` BLE lawn mowers.

This integration intentionally uses Home Assistant's Bluetooth manager to resolve the device by address. It does not create its own scanner. That means the same code path should work through a local Bluetooth adapter or a connectable Home Assistant Bluetooth proxy.

## What is implemented

- Bluetooth config flow discovery by service UUID `0000fff0-0000-1000-8000-00805f9b34fb` or local name `Mower_*`.
- BLE connect through Home Assistant Bluetooth's `async_ble_device_from_address(..., connectable=True)`.
- Framing and parsing from the Android APK:
  - Header byte `0xA4`.
  - Little-endian payload length at bytes 1-2.
  - XOR checksum at byte 3.
  - UTF-8 JSON payload.
  - 20-byte BLE write chunks.
- Service UUIDs from the APK:
  - Service: `0000fff0-0000-1000-8000-00805f9b34fb`
  - Notify/read characteristic: `0000fff1-0000-1000-8000-00805f9b34fb`
  - Write characteristic: `0000fff2-0000-1000-8000-00805f9b34fb`
- Polling command: `{"cmd": 200}`.
- Parsed status fields from responses `cmd=500`, `cmd=501` and `cmd=201`.
- Lawn mower entity with start, pause/stop and dock.
- Sensors for battery, mode code, error code, runtime, area, Wi-Fi level and rain delay.
- Binary sensors for docked, rain enabled, LED enabled, ultrasonic enabled and last command result.
- Debug service `grouw_ble_mower.send_raw_json` for protocol testing.

## Important limitations

The Android APK shows that work commands are sent as:

```json
{"cmd": 0, "mode": 1}
```

The app's mode mapping is:

- `0` = idle / stop
- `1` = working
- `2` = return home
- `3` = charging
- `4` = error in status display, and also used by the UI for edge/trim command
- `5` = lock in status display, and also used by the UI for start-point command
- `6` = OTA update
- `7` = trimming / edge in status display

Default command mappings in this integration:

- Start mowing: `{"cmd":0,"mode":1}`
- Pause/stop: `{"cmd":0,"mode":0}`
- Return to dock: `{"cmd":0,"mode":2}`

The command mode codes are configurable under the integration's options.

## Installation

Copy the custom component into Home Assistant:

```text
config/custom_components/grouw_ble_mower/
```

Restart Home Assistant.

Then go to:

```text
Settings → Devices & services → Add integration → Grouw BLE Mower
```

Keep the mower awake and close to a Bluetooth adapter or a connectable BLE proxy during first setup.

## Debug logging

Add this to `configuration.yaml` while testing:

```yaml
logger:
  default: info
  logs:
    custom_components.grouw_ble_mower: debug
    bleak_retry_connector: debug
```

## Raw command examples

Request all info:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    cmd: 200
```

Start mowing:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    cmd: 0
    mode: 1
```

Return home:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    cmd: 0
    mode: 2
```

Stop/pause:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    cmd: 0
    mode: 0
```

## Expected next validation

1. Confirm that setup discovers your mower or accepts its BLE address manually.
2. Confirm that `cmd: 200` returns status.
3. Confirm mode commands on the real mower.
4. Send Home Assistant logs and raw responses if any field mapping needs adjustment.
