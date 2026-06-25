# REVERSE_ENGINEERED.md

Reverse-engineered protocol notes for the Grouw / `robotic-mower connect` BLE
mower integration.

Last updated: 2026-06-25

## Sources

- Grouw / robotic-mower connect app:
  https://play.google.com/store/apps/details?id=com.cj.lawnmower
- Local decompiled APK output may exist in `APK/`, but that folder is
  not part of the git repo.
- Durable code references:
  - `custom_components/grouw_ble_mower/const.py`
  - `custom_components/grouw_ble_mower/ble_protocol.py`
  - `custom_components/grouw_ble_mower/ble_client.py`

Official APK files, extracted APK contents, decompiled Java/smali, native
library dumps, and generated decompiler output must never be upstreamed. Use
them only locally as reverse-engineering source material.

When local APK output is used, summarize the finding here with enough detail
that future agents do not need the local folder to understand the protocol.

## BLE UUIDs

```text
Service:     0000fff0-0000-1000-8000-00805f9b34fb
Notify/read: 0000fff1-0000-1000-8000-00805f9b34fb
Write:       0000fff2-0000-1000-8000-00805f9b34fb
```

Home Assistant discovery matches either the service UUID or local names matching
`Mower_*`.

## Frame Format

The Android app's BLE frame format has been mapped as:

```text
byte 0      header: 0xA4
byte 1      payload length low byte
byte 2      payload length high byte
byte 3      XOR checksum of the UTF-8 JSON payload
bytes 4..   UTF-8 JSON payload
```

Payload length is little-endian. The checksum is XOR over the payload only, not
the header or length bytes.

BLE writes are split into 20-byte chunks. The first chunk includes the 4-byte
frame header plus up to 16 payload bytes. Later chunks carry remaining payload
bytes.

## Commands

### Poll all info

```json
{"cmd":200}
```

Expected status responses currently parsed by the integration:

```text
cmd=500  all info
cmd=501  work status
cmd=201  machine status
```

### Work mode

```json
{"cmd":0,"mode":1}
```

Known/default mode mapping:

```text
0 = idle / stop
1 = working
2 = return home / dock
3 = charging
4 = error in status display; also edge/trim command in app UI
5 = lock in status display; also start-point command in app UI
6 = OTA update
7 = trimming / edge in status display
```

Default integration command mapping:

```text
Start mowing:   {"cmd":0,"mode":1}
Pause/stop:     {"cmd":0,"mode":0}
Return to dock: {"cmd":0,"mode":2}
```

The command mode codes are configurable through the integration options.

## Parsed Fields

Current `MowerState` fields are populated from JSON keys including:

```text
name
model
sn
deviceSn
version
version 
power
mode
errortype
station
wifi_lv
rain_en
rain_status
rain_delay_left
rain_delay_set
on_min
total_min
on_area
cur_min
cur_area
led_en
ultra_en
result
command
cmd
```

The key `version ` with a trailing space is intentionally handled because it was
seen in the Android parser.

## Response/Ack Commands

Known response command constants currently represented in code:

```text
400    generic ack
500    all info
501    work status
201    machine status
10100  stop result
10101  work result
10102  home result
```

## Validation Status

Confirmed from APK/code analysis:

- UUIDs
- frame header, length, checksum, and chunking
- poll command `cmd=200`
- work mode command shape `cmd=0, mode=<mode>`
- mode values for work, home, trim, and start-point behavior

Still requiring real hardware validation:

- exact meaning of every parsed field for all mower firmware versions
- whether stop mode `0` behaves as pause or full stop on every model
- whether `cmd=400` or result-specific responses are always emitted for commands
- whether all listed sensors are available on every Grouw mower variant
- edge/trim and start-point behavior through Home Assistant actions

Record new packet captures or raw JSON responses here after redacting addresses,
serial numbers, and other private values.
