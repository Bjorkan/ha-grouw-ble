# Response Parsing

## parseBlueResult

`Helper::parseBlueResult` at address `0x46b01c` converts a byte list
`[b0, b1, b2, ...]` into a `Map<String, String>` using one-based key names.
The loop counter starts at 1 but reads `payload[counter - 1]`, so no payload
byte is skipped:

```text
result["byte1"] = string(b0)
result["byte2"] = string(b1)
result["byte3"] = string(b2)
...
```

This map is returned to the callback closure, where the receiver accesses
specific keys.

## BlueKey::queryInfo Response (sub-cmd 0x00)

Parsed by both `MowerStatusLogic::changeWorkType` and
`DeviceLogic::initDeviceInfo`:

```text
byte5   = battery percentage (0-100, parsed as int for image selection)
byte9   = device info string segment (ASCII)
byte10  = model prefix (2→"DY", 3/4→"DM", else "")
byte11  = device info string segment (ASCII)
byte12  = device info string segment (ASCII)
byte13  = work type hex string (see mapping below)
byte14  = area code / firmware version prefix (parsed as int)
byte15  = firmware version suffix (parsed as int)
```

## BlueKey::queryPin Response (sub-cmd 0x18)

Parsed by `MainLogic::pinToDevice`:

```text
byte5   = PIN digit 1
byte6   = PIN digit 2
byte7   = PIN digit 3
byte8   = PIN digit 4
byte9   = area code string, defaulting to "0" when absent
```

The app concatenates `byte5` through `byte8` as strings and stores the result
as `MainState.robotPin`. `MainLogic::openDevice` then checks that the user's
entered `pinCode` is at least 4 characters and equals `robotPin`. No separate
Dart write containing the typed PIN was found in this flow.

## BlueKey::errorMemory Response (sub-cmd 0x3c)

```text
byte5   = error type letter code (B/N/L/T/R/X/C/S/P/A)
byte6   = (unknown, part of error data)
byte7   = error code hex prefix
byte8   = error code hex separator
byte9   = error code hex suffix
byte10  = error data after colon
byte11  = error data suffix
byte12  = ASCII decoded → alert letter (AsciiDecoder.convert on 2 bytes)
```

Error letter codes map to translation keys: `alert_b`, `alert_n`, `alert_l`,
`alert_t`, `alert_r`, `alert_x`, `alert_c`, `alert_s`, `alert_p`, `alert_a`.

## Work Mode Mapping (byte13)

From `MowerStatusLogic::changeWorkType` callback at `0x4dd66c`, byte13
(parsed as hex via `Helper::tenToHex`) maps to work mode strings:

```text
0x01 = "Mowing"
0x02 = "Turn Forward"
0x03 = "Along Boundary"
0x04 = "Robot Back"
0x05 = "Lift"
0x06 = "Collision"
0x07 = "tilt"
0x08 = "Finding Boundary"
0x09 = "tracing Back"
0x0a = "Boundary Back"
0x0b = "Boundary Cutting"
0x0c = "Partition Work"
0x0d = "No Boundary"
0x0e = "Charging"
0x0f = "Waiting"
0x10 = "SPIRAL MOWING"
0x14 = "label_stopped" (translated via Trans.tr())
0x19 = "Error"
0x29 = "--" (disconnected, triggers changeConnectStatus(true))
```

## Battery Handling

The app handles battery via image assets only — no numeric battery percentage
sensor entity exists:

- `byte5` (0-100) → selects image: ≤25=battery25.png, 26-50=battery50.png,
  51-75=battery75.png, >75=battery100.png
- Stored in `DeviceState.batteryImage` as asset path string
- Displayed via `"label_battery_capacity"` translation key in the status view

## Status Polling Flow

1. `MowerStatusLogic.addListen()` starts a periodic Timer
2. Timer fires → calls `changeWorkType()`
3. `changeWorkType` → `Helper.writeAndNotify(BlueKey::queryInfo, callback)`
4. BLE response → `parseBlueResult` → `{"byte1":..., "byte5":..., "byte13":..., ...}`
5. Callback looks at `"byte13"` → hex string → work type name → updates
   `MowerStatusState.workType`
6. On initial connection, `DeviceLogic.initDeviceInfo()` does the same query but
   also parses byte5 (battery), byte9/10/11/12 (device version), byte14/15
   (firmware version)

Note: Lift (0x05), tilt (0x07), and charging (0x0e) are all work mode values
from byte13 — not separate flag bytes. No rain status byte has been found;
rain features appear only in the settings UI.
