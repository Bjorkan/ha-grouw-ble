# Reverse Engineered — Grouw / Daye BLE Mower Protocol

Last updated: 2026-06-26

This directory contains the reverse-engineered protocol notes split by topic
for easier lookup.

## Files

| File | Topic |
|------|-------|
| `sources.md` | Source materials (APK, HCI captures, hardware scans) |
| `app_identity.md` | App identity, BLE names, UUIDs, capabilities, HA discovery |
| `gatt_table.md` | GATT service/characteristic table from hardware scan |
| `dym_protocol.md` | DYM framing from HCI snoop captures |
| `bluekey_commands.md` | BlueKey 48-byte command format, sub-commands, control commands |
| `response_parsing.md` | Response byte parsing, work mode mapping, error memory, battery |
| `ble_write_flow.md` | BLE write/notification flow, state classes |
| `manual_findings.md` | Local Grouw manual findings and generation boundaries |
| `java_kotlin_findings.md` | Decompiled Java/Kotlin (GizPlugin, GizWifiSDKProxy, FlutterBluePlus) |
| `native_crypto.md` | libTelinkCrypto.so, AES.java, key derivation, packet encryption |
| `dart_blutter_analysis.md` | Dart AOT class analysis from blutter |

## Confirmed

```text
AES encryption mechanism:
  - libTelinkCrypto.so implements Telink AES-ATT with software AES
  - aes_att_encryption: reverse(key) → reverse(data) → rijndael_encrypt → reverse(result)
  - aes_att_swap at 0x1254: full 16-byte byte reversal (swap buf[i] ↔ buf[15-i])
  - aes_att_encryption_packet at 0x189c: AES-CTR mode packet encryption
  - aes_att_decryption_packet at 0x1a60: AES-CTR mode packet decryption
  - att_crypto_poly at 0x13040: 0 (poly MIC disabled by default)

LTK derivation (aes_att_get_ltk, 0x16e4):
  buffer = {param3[0..7], 0x0000000000000000}
  temp = param1 XOR param2 XOR buffer
  LTK = aes_att_decrypt(key, temp)

SK derivation (aes_att_get_sk, 0x1644):
  key = param1 XOR param2
  data = {param3[0..7], param4[0..7]}
  SK = aes_att_encrypt(key, data)

BlueKey 48-byte command format:
  [0]=0x88, [1]=0xb2, [2]=0x9a, [3]=sub_cmd, [4..18]=data,
  [19..23]=trailer values [44,12,2,510,20], [24..47]=0
  Sub-commands: 0x00=queryInfo, 0x04=setTime, 0x0c=changePin,
    0x12=mowerSettingWrite, 0x18=queryPin, 0x28=workTime,
    0x32=mowerSettingQuery, 0x3a=multiAreaQuery, 0x3c=errorMemory
  Control: 0=start, 2=stop, 4=goToWork, 6=backToStation
  (0x88 and 0xb2 at indices 0-1 are real wire bytes, not Dart metadata)

Work mode mapping (byte13):
  0x01=Mowing, 0x02=Turn Forward, 0x03=Along Boundary, 0x04=Robot Back,
  0x05=Lift, 0x06=Collision, 0x07=tilt, 0x08=Finding Boundary,
  0x09=tracing Back, 0x0a=Boundary Back, 0x0b=Boundary Cutting,
  0x0c=Partition Work, 0x0d=No Boundary, 0x0e=Charging, 0x0f=Waiting,
  0x10=SPIRAL MOWING, 0x14=stopped, 0x19=Error, 0x29=disconnected

Battery is image-only in app (byte5→25/50/75/100.png thresholds), no numeric sensor
BlueKey queryPin response byte5-byte8 are concatenated PIN digits; app compares
  the entered PIN locally against that returned robotPin
BlueKey changePin response treats byte5 == "0" as success
Mower settings response 0x32 maps byte5=mowInTheRain, byte6=boundaryCut,
  byte7=ultrasound, byte8=helixSet, byte9=hour, byte10=minute, byte12=led
Multi-area response 0x3a maps byte5=area2Per, byte6-byte8=area2Dis,
  byte9=area3Per, byte10-byte12=area3Dis
Working-time response 0x28 uses byte4 as response/display mode, then pairs
  byte5-byte11 with byte12-byte18 for Monday-Sunday schedule values
MainLogic awaits FlutterBluePlus requestMtu before service discovery; the
  bundled requestMtu implementation requests MTU 512 with a 15-second timeout
Lift, tilt, charging are work mode values (byte13), not separate flags
No rain status byte found — rain features are in settings UI, not BLE parsing
Grouw 17941/17947 manual says the app selects `RobotMower_DYM` over Bluetooth;
  Grouw 18739/18740 CLEVR manual instead uses `robotic-mower connect`,
  Wi-Fi, and `Mower_XXXXXX`, so treat that as a separate generation
@14069316 library unit is standard Dart runtime (dart:io/async/collection), NOT custom protocol code
writeAndNotify signature: writeAndNotify(payload, callback, {canBack, errorTip, noLimitNotify, notifyType, showTip})
Seven state classes decoded: MainState, MowerStatusState, DeviceState,
  ChangePinState, MowerSettingState, MultiAreaMowingState, WorkingTimeSettingState
```

## Not Yet Confirmed

```text
Meaning of every status response byte in the DYM 0x80 response
Whether byte-level checksum exists beyond the fixed ff0a write trailer
Whether DYM 0x80 response bytes 4-15 map to the same bytes as BlueKey queryInfo response
Exact LTK initial parameters (PIN format, constants) passed from Dart to native
Which protocol (DYM vs BlueKey) a given firmware generation actually uses on the wire
How the app selects between DYM and BlueKey protocols (device type, firmware version, or auth state)
Whether the 0x22 values at indices 4-11 of queryInfo command are significant
Exact field mapping of DYM 0x8c auth response beyond numeric PIN-looking bytes
Exact on-wire packing for BlueKey settings writes 0x12, working-time writes,
  multi-area distance writes, and change-PIN digit chunks
Units for multi-area distance values
```

## Validation Checklist

When validating against real hardware, capture and redact:
1. Battery, station and mode mapping over more mower states
2. Charging, error, rain, lift and tilt notification payloads
3. Exact notification bytes after each newly tested action
4. Mapping between UI actions in the Daye app and mower behavior
5. Settings-page captures for rain delay, boundary cut, ultrasound, helix,
   LED, multi-area, weekly schedule, and PIN change

Record only summarized findings. Do not commit proprietary APK output or
raw logs containing BLE addresses, serial numbers, credentials, or other private
values.
