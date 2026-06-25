# Dart AOT — Blutter Analysis

Analyzed from `libapp.so` using blutter. Source files in `romow_bluetooth`
package.

## Library Units

### @14069316 — Standard Dart Runtime Library

This library unit is **standard Dart runtime code** (`dart:io`, `dart:async`,
`dart:collection`), NOT custom protocol code. Contains classes like:
`_StreamSinkImpl`, `_Socket`, `_File`, `_RandomAccessFileOps`, etc.

Functions found in this unit (`_sendData`, `_makeDatagram`, `_checkForErrorResponse`,
`_checkSum`, `_isBufferEncrypted`, `_onData`, `_raw`) are standard Dart runtime
internals, not custom BLE protocol framing helpers. **Do not use these as evidence
of protocol structure.**

### @8050071 — Binary Data Serialization Library

Full set of typed store/load functions for data point parsing:

```text
_storeUint8    _storeUint16   _storeUint32   _storeUint64
_storeInt8     _storeInt16    _storeInt32    _storeInt64
_loadUint8     _loadUint16    _loadUint32    _loadUint64
_loadInt8      _loadInt16     _loadInt32     _loadInt64
```

### @3220832 — Checksum Library

Contains `_checkSum` function used for verifying data integrity.

### @10003594 — Buffer Creation

Contains `_createBuffer` function.

## BlueKey — Command Definitions

The `BlueKey` class at `package:romow_bluetooth/common/config/blue_key.dart`
defines 48-byte authenticated command payloads. Commands are constructed as
plain `List<int>` and sent through `writeAndNotify` → `blueWriteAndNotification`
→ `BluetoothCharacteristic::write`.

No Dart-side encryption, DYM framing, or checksum logic is visible for BlueKey
commands. Encryption (AES-CTR via `libTelinkCrypto.so`) happens at the native
layer or is transparent to the Dart write path.

## MainLogic — BLE Write/Notification Controller

`MainLogic` at `pages/main/logic.dart`, class size 0x20:

```text
0x461eb4  writeAndNotify              — Entry point: forwards to blueWriteAndNotification
0x461fa4  blueWriteAndNotification    — Core BLE write: subscribes to notifications, writes to char
0x46ac3c  <anonymous closure> (onDone) — Toast "toast_secsecondary_true"
0x46aca4  <anonymous closure> (onError) — Error toast, dialog close
0x46ad84  <anonymous closure> (onData)  — Parse result, call back
0x46b580  changePIN                   — Update robotPin in state
0x46f4b4  resetPinInput               — Clear PIN text field
0x46f720  openDevice                  — Validate PIN length (≥4), verify against robotPin
0x47086c  setDevice                   — Set connected device, handle duplicate connection
```

## MowerStatusLogic — Status Display Controller

`MowerStatusLogic` at `pages/mower_status/logic.dart`, class size 0x24:

```text
0x46db00  changeMoverControl        — Update state.mowerControl, notify
0x46db6c  stateDisConnect           — Check disconnection and error state
0x470510  <anonymous>               — Navigate back on disconnect dialog
0x470584  <anonymous>               — Call disConnect on confirm
0x4705e4  disConnect                — Full disconnect: disconnect BLE, navigate
0x480bc0  changeConnectStatus       — Toggle connect/disconnect, cancel timer
0x4dd444  addListen                 — Start periodic Timer for polling
0x4dd534  <anonymous> (timer cb)    — Timer callback: calls changeWorkType
0x4dd594  changeWorkType            — Sends BlueKey::queryInfo, parses work mode from byte13
0x4dd66c  <anonymous> (response)    — Parses byte13 → work mode string, updates UI
0x51b6a0  manageDevice              — Sends BlueKey cmd for start/stop/back/go-to-work
0x51c39c  errorMemory               — Sends BlueKey cmd with sub-cmd 0x3c, parses error
0x51c4f4  <anonymous> (error data)  — Parses byte5/byte12 for error code letter + ASCII
```

## DeviceLogic — Initial Device Info Query

`DeviceLogic` at `pages/device/logic.dart`:

```text
0x47ff9c  onReady                    — Calls initDeviceInfo
0x47fff0  initDeviceInfo             — Sends BlueKey::queryInfo once at init
0x480164  <anonymous> (response)     — Parses byte5 (battery), byte9-12 (version), byte14-15 (model)
```

## Helper — Utility Functions

`Helper` at `common/util/helper.dart`:

```text
0x42f7f0  cloudCallback             — Cloud operation callback (async)
0x461c44  writeAndNotify            — Static wrapper: resolves MainLogic, calls writeAndNotify
0x46b01c  parseBlueResult           — Map byte list → {"byte1":..., "byte2":..., ...}
0x46b1e8  tenToHex                  — Parse string to int, convert to hex string
0x47830c  diyPicker                 — UI picker widget builder
```

## BlueKey — Command Definitions

`BlueKey` at `common/config/blue_key.dart`:

```text
Static fields:
  0xfa4  queryPin   — PIN query command (late)
  0xfa8  setTime    — Set clock command (late)
  0xfac  queryInfo  — Status query command (late, used by both changeWorkType and initDeviceInfo)
  0xfb0  workTime   — Working time query command (late)

Static methods:
  0x4719c0  setTime()     → List<int> of 48 bytes, sub-cmd 0x04
  0x47e78c  queryPin()    → List<int> of 48 bytes, sub-cmd 0x18
  0x4808e0  queryInfo()   → List<int> of 48 bytes, sub-cmd 0x00, fields=8×0x22
  0x678ce4  workTime()    → List<int> of 48 bytes, sub-cmd 0x28
```

## Package Structure

Dart source files identified from `libapp.so` strings (package paths):

```text
common/services/gizwits_service.dart
common/config/blue_key.dart
common/util/pop_scope_util.dart
common/util/dialog/dialog_util.dart
pages/device/state.dart
pages/main/view.dart
pages/add_robot_model/{binding,logic,state,view}.dart
pages/add_robot_model/widget/robot_type_{1,2,3,4}.dart
pages/add_robot_finish/state.dart
pages/mower_firmware_update/{binding,logic,state,view}.dart
pages/multi_area_mowing/widget/input_card.dart
pages/language_setting/state.dart
pages/forgot_password/view.dart
pages/privacy_policy/view.dart
multi_area_mowing
```
