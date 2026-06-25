# Grouw / Daye BLE Mower for Home Assistant

Custom integration for Grouw mowers controlled by the Daye Power Android app (`com.dayepower.dayeappleaf`).

This integration intentionally uses Home Assistant's Bluetooth manager to resolve the device by address. It does not create its own scanner. That means the same code path should work through a local Bluetooth adapter or a connectable Home Assistant Bluetooth proxy.

## What is implemented

- Bluetooth config flow discovery by confirmed Daye service UUID
  `49535343-fe7d-4ae5-8fa9-9fafd205e455` and local-name strings
  `Robot Mower_DYM*`, `RobotMower_DYM*`, and `Robot_Mower*`.
- Manual setup by BLE address.
- BLE connect through Home Assistant Bluetooth's `async_ble_device_from_address(..., connectable=True)`.
- Coordinator-based polling and entity availability.
- Lawn mower, sensor and binary sensor entities for the fields being decoded during protocol validation.
- Debug service `grouw_ble_mower.send_raw_json` for protocol testing.

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
- The app contains Bluetooth write/notify concepts and mower-control UI, but
  the exact characteristic properties, payload framing and command IDs still
  need confirmation.

The raw JSON service is therefore experimental. Do not treat default command codes or decoded fields as validated Daye protocol facts until they are confirmed against the new APK or real hardware captures.

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

## Raw command validation

Use this only while reverse-engineering the Daye BLE protocol:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload: {}
```

Capture the raw Home Assistant logs and mower behavior, then update `REVERSE_ENGINEERED.md` with redacted durable findings.

## Expected next validation

1. Confirm Home Assistant discovers the mower by service UUID or as
   `Robot Mower_DYM*` / `RobotMower_DYM*` / `Robot_Mower*`.
2. Confirm characteristic properties for the `49535343...` characteristics so
   read/notify/write roles can be mapped.
3. Confirm the write payloads and notification payloads for status, start, stop and dock.
4. Update code, tests and docs only with facts from the Daye APK or redacted hardware captures.
