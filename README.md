# Grouw / Daye BLE Mower for Home Assistant

Custom integration for Grouw mowers controlled by the Daye Power Android app (`com.dayepower.dayeappleaf`).

This integration intentionally uses Home Assistant's Bluetooth manager to resolve the device by address. It does not create its own scanner. That means the same code path should work through a local Bluetooth adapter or a connectable Home Assistant Bluetooth proxy.

## What is implemented

- Bluetooth config flow discovery by confirmed Daye service UUID
  `49535343-fe7d-4ae5-8fa9-9fafd205e455` and local-name strings
  `Robot Mower_DYM*`, `RobotMower_DYM*`, and `Robot_Mower*`.
- Manual setup by non-empty BLE address.
- BLE connect through Home Assistant Bluetooth's `async_ble_device_from_address(..., connectable=True)`.
- Best-effort MTU request after connect, matching the Daye app's
  FlutterBluePlus connection flow.
- PIN entry during setup. A blank PIN is allowed for mowers without PIN; a
  configured PIN must be exactly four digits.
- Coordinator-based polling and entity availability.
- Daye status polling over the captured DYM BLE payload.
- Lawn mower controls for captured start, pause/stop and dock payloads.
- Entities for currently decoded DYM status fields from hardware captures:
  mower activity, battery, mode code, last response command, and docked state.
- Debug service `grouw_ble_mower.send_raw_json` for raw BLE payload testing.

## Protocol status

The current authoritative APK is `com.dayepower.dayeappleaf` version `2.0.1` / version code `117`.

Confirmed from that APK so far:

- The app is a Flutter app using `flutter_blue_plus`.
- The Bluetooth setup text tells users to choose `RobotMower_DYM`; the same
  APK also contains `Robot_Mower-`.
- A hardware scan from the mower confirmed the BLE name `Robot Mower_DYM`.
- The hardware scan confirmed service
  `49535343-FE7D-4AE5-8FA9-9FAFD205E455` with characteristic
  `49535343-1E4D-4BD9-BA61-23C647249616`.
- A Bluetooth HCI snoop log from the Daye app confirmed that characteristic
  `49535343-1E4D-4BD9-BA61-23C647249616` is used for both write and notify.
- Dart AOT analysis shows the app requests MTU 512 before service discovery.
  The integration attempts the same after connect and continues when the local
  Bleak backend does not expose MTU negotiation.
- The status poll, start, pause/stop and dock payloads are captured from the
  Daye app. More status field meanings still need validation.
- Two captures show different start payloads: one for starting from station and
  one for resuming after stop on the lawn.
- The integration sends the captured Daye session/auth prelude after each BLE
  reconnect and waits for the captured auth response (`0x8c`) before polling or
  sending a command.
- When a PIN is configured and the auth/PIN response exposes four numeric PIN
  digits, the integration verifies the configured PIN before sending status or
  command payloads. The PIN is redacted from diagnostics and normal debug logs.
- The app has rain, ultrasound, working-time and other settings screens, but no
  DYM status bytes for those features are confirmed yet. The integration does
  not expose them as entities until hardware captures identify the fields.

The raw BLE payload service is still experimental. Do not treat newly decoded
fields as validated until they are confirmed against more Daye app captures or
real hardware observations.

## Installation

Copy the custom component into Home Assistant:

```text
config/custom_components/grouw_ble_mower/
```

Restart Home Assistant.

Then go to:

```text
Settings -> Devices & services -> Add integration -> Grouw / Daye BLE Mower
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

## Raw BLE Payload Validation

Use this only while reverse-engineering the Daye BLE protocol:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    command: status
```

You can also send a captured payload directly:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    raw_hex: "44594d00111111111111111100000000000000160601ff0a"
    expect_cmd: "0x80"
```

Set `authenticate: false` only when deliberately probing the connection prelude
itself.

Capture the raw Home Assistant logs and mower behavior, then update
`reverse_engineered/` with redacted durable findings.

## Expected next validation

1. Confirm Home Assistant discovers the mower by service UUID or as
   `Robot Mower_DYM*` / `RobotMower_DYM*` / `Robot_Mower*`.
2. Confirm battery and mode field meanings across more mower states.
3. Capture additional notification payloads for charging, mowing errors, lift
   and tilt events. Treat rain as a settings feature unless a BLE status byte is
   captured for it.
4. Update code, tests and docs only with facts from the Daye APK or redacted
   hardware captures.
