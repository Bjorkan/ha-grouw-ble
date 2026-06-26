# DYM Protocol

Based on HCI snoop captures, the DYM protocol is:

## Outbound Packets (24 bytes)

```text
DYM prefix (3 bytes)
Command byte
Command-specific data (variable)
Zero padding
Trailer: 16 06 01 ff 0a
```

## Inbound Notifications (22 bytes)

```text
DYM prefix (3 bytes)
Response type byte (0x80 = status, 0x8c = auth)
Status data fields
Trailer: 16 06 01
```

## Auth Flow

1. Session payload (type `0x02`, embeds date/time)
2. Auth query (type `0x0c`)
3. Auth response (type `0x8c`) — PIN/auth response
4. After auth: status polling or commands

After each fresh BLE connection, the app sends a session/authentication prelude
before status polling or commands. This matches the observed UI behavior where
the app asks for the PIN again after disconnecting.

The captured auth query after entering PIN `1234` is all zeros after the
command byte, so the typed PIN is not sent in that DYM write. The APK's BlueKey
PIN flow instead sends a query and compares the returned digit bytes locally.
For DYM auth responses, treat bytes 4-7 as a PIN only when they are four numeric
digit bytes (`0x00` through `0x09`); exact DYM auth response field semantics are
still not fully captured.

## Captured Daye Write Payloads

```text
Status poll:
44594d00111111111111111100000000000000160601ff0a

Session/auth-related:
44594d02141a0619121c000000000000000000160601ff0a
44594d02141a06191220000000000000000000160601ff0a
44594d0c000000000000000000000000000000160601ff0a

Start mowing from dock/station:
44594d01020000000000000000000000000000160601ff0a

Resume/start after stop on lawn:
44594d01000000000000000000000000000000160601ff0a

Pause/stop:
44594d01010000000000000000000000000000160601ff0a

Go to base station:
44594d01030000000000000000000000000000160601ff0a
```

The `44594d0100...` is used when the mower is started again after stop,
while `44594d0102...` is used when starting from the docked/station state.

The `44594d0214...` payload embeds the phone date/time as
`year, month, day, hour, minute`, e.g. `1a 06 19 12 1c` for
2026-06-25 18:28.

## Captured Status Notifications

22-byte DYM payloads:

```text
44594d8064321b000004000114444100000000160601
44594d8064321b000004000100444100000000160601
44594d8064321b000004000103444100000000160601
```

## Observed Status Field Mapping (from HCI)

```text
byte 0..2  "DYM"
byte 3     response type, 0x80 for status
byte 4     battery percentage candidate, observed 0x64 and 0x32
byte 7     station/docked candidate:
            0x01 docked / at station
            0x00 away from station
byte 12    mode candidate:
            0x00 mowing / active after start
            0x03 returning after go-to-base
            0x14 stopped / standing still / docked / idle after stop
byte 19..21 notification trailer: 16 06 01
```

The second capture confirmed byte 7 changes from `0x01` while docked to `0x00`
after starting, and later returns to `0x01` when back at the station.
Real-hardware observation on 2026-06-26 while the mower was running confirmed:
mode `0x00` = mowing, mode `0x03` = returning home, and decimal mode `20`
(`0x14`) = standing still. The dock/station byte must take precedence when
mapping Home Assistant lawn mower activity because the mower can still expose
mode `0x00` while the station byte reports docked.

Home Assistant raw-service validation on 2026-06-26 showed that an
authenticated `command: status` poll beeps, while `command: status` with
`authenticate: false` does not beep. A direct `session_start` write with
`authenticate: false` produced two beeps and then timed out waiting for a
notification. A BlueKey `query_info` probe with `authenticate: false` did not
beep but also timed out. This points to the DYM session/auth prelude,
especially `session_start`, as the audible polling trigger rather than the DYM
status request itself.

Normal Home Assistant status polling should therefore use the captured DYM
status request without the session/auth prelude.

Follow-up raw-service validation on 2026-06-26 showed that unauthenticated DYM
`resume`, `dock`, and `pause` payloads execute successfully. Those command
writes timed out when called directly because the mower did not send the
expected `0x80` notification for the command write itself. `resume` produced
three beeps, matching the mower's normal manual start warning; `dock` and
`pause` produced no extra beep. Normal Home Assistant command handling should
therefore skip the session/auth prelude, write the command, and send the quiet
DYM status request as a follow-up before waiting for state.
More captures across charging, error, rain, lift and tilt states are still needed.

## Encryption

- Uses Telink AES-ATT packet encryption
- Keys derived during PIN/auth handshake
- BlueKey system manages keys and encryption state
- AES/ECB/NoPadding with byte-reversed keys
- A static `Security` toggle can disable encryption

## Comparison: DYM vs BlueKey

These are two distinct protocols in the same APK:

| Feature | DYM | BlueKey |
|---------|-----|---------|
| Packet size | 24 bytes | 48 bytes |
| Prefix | `"DYM"` (ASCII 0x44 0x59 0x4d) | `[0x88, 0xb2, 0x9a]` (binary) |
| Trailer | `[0x16, 0x06, 0x01, 0xff, 0x0a]` | `[44, 12, 2, 510, 20]` |
| Control byte | cmd byte (0x00/0x01/0x02/0x0c) | sub_cmd at index 3 |
| Observable in | HCI snoop captures | Dart blutter decompilation |
| Source | Wire-level capture | APK `blue_key.dart` + `manageDevice` |

**Hypothesis:** DYM is the pre-auth or unencrypted command layer; BlueKey is the
post-auth encrypted command layer. HCI captures only show DYM because the tested
session never completed authentication (or the specific firmware uses DYM exclusively).

## Serialization

- Status bytes are parsed using typed load functions
- `_storeUint8/16/32/64` and `_loadUint8/16/32/64` handle multi-byte integer fields
