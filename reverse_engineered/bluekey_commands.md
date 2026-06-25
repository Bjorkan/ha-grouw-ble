# BlueKey Commands

The BlueKey system constructs 48-byte authenticated command payloads.
Confirmed from blutter decompilation of `common/config/blue_key.dart` and
`pages/mower_status/logic.dart::manageDevice`.

## Byte Layout (48 bytes total)

```text
[0]    0x88          — prefix byte 0 (constant, part of wire format)
[1]    0xb2          — prefix byte 1 (constant, part of wire format)
[2]    0x9a          — command marker
[3]    sub_cmd       — sub-command byte
[4..18] data payload — 15 bytes of command-specific data
[19]   0x2c (44)     — trailer value 0
[20]   0x0c (12)     — trailer value 1
[21]   0x02 (2)      — trailer value 2
[22]   0x1fe (510)   — trailer value 3, stored as Dart int 510
[23]   0x14 (20)     — trailer value 4
[24..47] 0x00        — zero padding
```

All BlueKey commands share five trailer `List<int>` values
`[44, 12, 2, 0x1fe, 20]` at fixed offsets 19-23. The APK stores integer
`510` at index 22; exactly how that value is converted before/inside the BLE
write path is not wire-confirmed.

**Note:** `0x88` and `0xb2` at indices 0-1 are raw wire bytes stored directly in
the array by the Dart constructors. They are NOT Dart internal array metadata.

## Sub-Commands (from blue_key.dart)

```text
0x00 = queryInfo   — query mower information/status
0x04 = setTime     — set mower clock
0x18 = queryPin    — PIN query/authentication
0x28 = workTime    — query/set working time
0x3c = errorMemory — query error memory
```

## Control Commands (from MowerStatusLogic::manageDevice)

```text
0 = start mowing
2 = stop
4 = go to work
6 = back to station
```

## Static Command Payloads

All four static commands allocate a 48-byte array with prefix `[0x88, 0xb2]`
and the same trailer:

```text
queryPin (sub-cmd 0x18):  [0x88, 0xb2, 0x9a, 0x18, zeros[4-18], trailer[19-23], zeros[24-47]]
setTime   (sub-cmd 0x04):  [0x88, 0xb2, 0x9a, 0x04, 0x28,   zeros[5-18], trailer[19-23], zeros[24-47]]
queryInfo (sub-cmd 0x00):  [0x88, 0xb2, 0x9a, 0x00, 0x22×8, zeros[12-18], trailer[19-23], zeros[24-47]]
workTime  (sub-cmd 0x28):  [0x88, 0xb2, 0x9a, 0x28, zeros[4-18], trailer[19-23], zeros[24-47]]
```

The `queryInfo` command has 8 bytes of `0x22` at indices 4-11 (confirmed unique to
this sub-command; never compared against response bytes. Likely a firmware-required
fixed pattern or a request mask — exact purpose unknown.)

## BlueKey Definition (from blue_key.dart)

```text
Static fields (late):
  queryPin  (offset 0xfa4) — PIN query command
  setTime   (offset 0xfa8) — Set clock command
  queryInfo (offset 0xfac) — Status query command
  workTime  (offset 0xfb0) — Working time query command

Static methods (all allocate 48-byte arrays with [0x88, 0xb2] prefix):
  0x4719c0  setTime()     → sub-cmd 0x04, data[4]=0x28
  0x47e78c  queryPin()    → sub-cmd 0x18
  0x4808e0  queryInfo()   → sub-cmd 0x00, data[4..11]=8×0x22
  0x678ce4  workTime()    → sub-cmd 0x28
```

## ManageDevice — Dynamic Command Construction

`MowerStatusLogic::manageDevice` (0x51b6a0) builds BlueKey commands at runtime
for control operations (start/stop/back/go-to-work). It allocates 48 bytes and
sets:
```text
[0]=0x88  [1]=0xb2  [2]=0x9a  [3]=sub_cmd  [19]=44  [20]=12  [21]=2  [22]=510  [23]=20
```
The sub_cmd at index 3 is the control code (0=start, 2=stop, 4=goToWork, 6=backToStation).

## Encryption Context

Commands are constructed in Dart and passed through
`writeAndNotify` → `blueWriteAndNotification` → `BluetoothCharacteristic::write`
without visible Dart-side encryption. Encryption occurs in native
`libTelinkCrypto.so` via `aes_att_encryption_packet` at 0x189c (AES-CTR mode).

## Relationship to DYM Protocol

BlueKey (48 bytes) and DYM (24 bytes with `"DYM"` ASCII prefix) are two distinct
protocols in the same APK. The app constructs BlueKey commands via `BlueKey` static
methods and `manageDevice`, while HCI captures show only DYM packets on the wire.

Possible explanations (unconfirmed):
- **Pre-auth vs post-auth**: DYM framing is used before authentication, BlueKey
  after PIN verification
- **Different firmware generations**: BlueKey for newer Telink firmware, DYM for older
- **Native-layer wrapping**: `libTelinkCrypto.so` AES-CTR may transform the 48-byte
  BlueKey payload into the 24-byte DYM format
- **Device type**: The app may select protocol per device based on GATT service UUIDs
