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

The Home Assistant integration's raw debug encoder can build BlueKey probe
payloads, but Python/BLE writes require byte values. It currently emits each
APK `List<int>` value as `value & 0xff`, so trailer value `510` becomes byte
`0xfe`. Treat this as a validation helper until hardware captures confirm the
platform/native conversion.

**Note:** `0x88` and `0xb2` at indices 0-1 are raw wire bytes stored directly in
the array by the Dart constructors. They are NOT Dart internal array metadata.

## Sub-Commands (from blue_key.dart and page logic)

```text
0x00 = queryInfo          — query mower information/status
0x04 = setTime            — set mower clock
0x0c = changePin          — write changed PIN
0x12 = mowerSettingWrite  — save mower settings
0x18 = queryPin           — PIN query/authentication
0x28 = workTime           — query/set working time
0x32 = mowerSettingQuery  — query mower settings
0x3a = multiAreaQuery     — query multi-area mowing settings
0x3c = errorMemory        — query error memory
```

`0x0c`, `0x12`, `0x32`, and `0x3a` are constructed dynamically by page logic
rather than exposed as `BlueKey` static fields.

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

## Settings And PIN Page Commands

Additional page controllers build BlueKey payloads directly instead of calling
static `BlueKey` fields.

### Change PIN

`ChangePinLogic::changePin` (0x461584) validates that the old PIN matches
`MainState.robotPin`, that the new PIN is repeated, and that the new PIN is at
least four characters long. It then builds a 48-byte BlueKey payload:

```text
[0]=0x88  [1]=0xb2  [2]=0x9a  [3]=0x0c
[4..7]    current/old PIN chunks after Helper.tenToHex
[8..11]   new PIN chunks after Helper.tenToHex
[12..18]  0
[19..23]  [44, 12, 2, 510, 20]
[24..47]  0
```

The response callback treats `byte5 == "0"` as success, updates
`MainState.robotPin`, clears the PIN input controllers, and shows a success
toast. The exact substring boundaries used for the PIN chunks are odd in the
AOT output and still need source-level or hardware confirmation before
implementing this write path.

`ChangePinLogic::getChangePIN` builds the same shape as `queryPin`
(`sub_cmd = 0x18`) and refreshes `MainState.robotPin` from `byte5` through
`byte8`.

### Mower Settings

`MowerSettingLogic::getMowerSetting` (0x6640fc) builds a 48-byte query with
`sub_cmd = 0x32`.

`MowerSettingLogic::saveSetting` (0x48217c) builds a settings write beginning
with `[0x88, 0xb2, 0x9a, 0x12]`. The Dart logic appends setting blocks for:

```text
mowInTheRain, boundaryCut, ultrasound, helixSet, hour, minute, led
```

Boolean settings are encoded by the Dart page logic before the shared BlueKey
trailer/zero padding is appended. The exact final on-wire bytes are not yet
confirmed by HCI capture.

The settings page gates some options by model/version strings including:

```text
DY002, DY052, DY012, DY112, DY022, DY122, DY142, DY162,
GY002, GY052, GY012, GY112, GY022, GY122, GY142, GY162
```

### Multi-Area Mowing

`MultiAreaMowingLogic::getInfo` (0x664e44) builds a 48-byte query with
`sub_cmd = 0x3a`.

`MultiAreaMowingLogic::setInfo` validates non-empty area 2/3 percentage and
distance input fields, then writes a BlueKey payload built from:

```text
area2Per, area2Dis, area3Per, area3Dis
```

The page uses `Helper.tenToHex` while packing the numeric text fields. The
distance unit and exact multi-byte packing still need hardware validation.

### Working Time

`WorkingTimeSettingLogic::initData` (0x678288) queries working time by writing
the static `BlueKey.workTime` payload (`sub_cmd = 0x28`) with
`noLimitNotify = true`.

The working-time state starts each day with default UI values:

```text
start="09:00", work="3.0"
```

`WorkingTimeSettingLogic::getSetList` converts the seven day maps into fourteen
values: one 2-value start/work pair per weekday response byte group. Save logic
branches on the response mode (`byte4`, especially mode `0x85`) before writing
the updated schedule.

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

## Integration Debug Support

`grouw_ble_mower.send_raw_json` supports named BlueKey probe payloads through
the raw debug service:

```json
{"bluekey": "query_info"}
{"bluekey": "query_pin"}
{"bluekey": "work_time"}
{"bluekey": "mower_settings"}
{"bluekey": "multi_area"}
{"bluekey": "error_memory"}
```

Generic probes can use `bluekey_sub_cmd` with optional `bluekey_data`. This is
for protocol validation only; normal Home Assistant polling and controls still
use the HCI-confirmed DYM payloads.
