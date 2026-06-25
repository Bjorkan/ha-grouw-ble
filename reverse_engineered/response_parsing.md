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

## Helper::tenToHex

`Helper::tenToHex` at address `0x46b1e8` is an APK-specific conversion helper.
It parses a decimal string to an integer, formats that integer as radix-16 text,
then parses the resulting text with radix 32.

For single decimal digits this returns the same numeric value. For values above
15 it is not the same as a normal byte conversion; for example decimal `"20"`
becomes hex text `"14"`, which parses as radix-32 integer `36`.

Treat this as a Daye UI/protocol packing helper, not as a generic
decimal-to-hex conversion.

The Home Assistant integration mirrors this helper as `daye_ten_to_hex()` for
debug parsing of APK-derived BlueKey responses.

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

## BlueKey Change PIN Response (sub-cmd 0x0c)

Parsed by `ChangePinLogic::changePin` callback:

```text
byte5 = "0" means PIN change success
```

On success the app updates `MainState.robotPin` to the new PIN, clears the
change-PIN input controllers, and shows a success toast.

## BlueKey Mower Settings Response (sub-cmd 0x32)

Parsed by `MowerSettingLogic::getMowerSetting` callback:

```text
byte5   = mowInTheRain boolean string ("1" = true)
byte6   = boundaryCut boolean string ("1" = true)
byte7   = ultrasound boolean string ("1" = true)
byte8   = helixSet boolean string ("1" = true)
byte9   = rain-delay hour text
byte10  = rain-delay minute text, left-padded for display when < 10
byte12  = led boolean string ("1" = true)
```

The app default string for missing boolean setting bytes is `"2003"` and the
UI only treats exact string `"1"` as enabled. This reinforces that rain is a
settings field in the Daye app, not a confirmed status byte.

## BlueKey Multi-Area Response (sub-cmd 0x3a)

Parsed by `MultiAreaMowingLogic::getInfo` callback:

```text
byte5       = area2Per text
byte6-byte8 = area2Dis text, assembled as a variable-width decimal value
byte9       = area3Per text
byte10-12   = area3Dis text, assembled as a variable-width decimal value
```

If leading distance bytes are zero, the page displays fewer chunks; otherwise
it concatenates more chunks into the distance field. The distance unit and exact
packing remain unconfirmed without hardware validation.

## BlueKey Working-Time Response (sub-cmd 0x28)

Parsed by `WorkingTimeSettingLogic::initData` callback:

```text
byte4       = response mode, converted through Helper.tenToHex and formatted as 0xXX
byte5-byte11  = one value per weekday, Monday through Sunday
byte12-byte18 = paired value per weekday, Monday through Sunday
```

The page iterates `byte5` through `byte11` and pairs each with the byte seven
positions later. `byte4` controls display parsing: mode `0x85` uses `"."` as
the work-duration delimiter, while other modes use `":"`.

Because `byte4` is a response/display mode in this flow rather than a stable
sub-command byte, Home Assistant's BlueKey debug parser uses the raw-service
request context (`bluekey: work_time`) to decode these fields.

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
