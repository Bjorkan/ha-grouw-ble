# BLE Write/Notification Flow

Confirmed from `MainLogic::writeAndNotify` (0x461eb4) and
`blueWriteAndNotification` (0x461fa4).

## Sequence

1. `Helper::writeAndNotify` (0x461c44) resolves `MainLogic` via GetIt,
   forwards all parameters.
2. `MainLogic::writeAndNotify` checks `connectType` sentinel, calls
   `blueWriteAndNotification`.
3. `blueWriteAndNotification`:
   - Cancels existing `resultListen` subscription
   - Subscribes to `onValueReceived` on the `writeCharacteristic`
   - Writes the command bytes to `BluetoothCharacteristic::write`
   - On notification: calls `Helper::parseBlueResult` (0x46b01c) on the
     received bytes
   - Passes the parsed map to the callback closure

## State Classes

### MainState (pages/main/state.dart, size 0x30)

```text
0x08  connectType (int, late)     — BLE connection type (0=disconnected, 2=connected?)
0x0c  area (String, late)         — Device area label
0x10  robotPin (String, late)     — Stored PIN for verification
0x14  type (int, late)            — Device type
0x18  deviceName (String, late)   — Device display name
0x1c  deviceAddress (String, late) — BLE MAC
0x20  loading (bool)              — Loading indicator
0x24  startTime (DateTime?)       — Mowing start time
0x28  isOpenAuto (bool)           — Auto-open flag
0x2c  haveBlueControll (bool)     — Has Bluetooth control
```

### MowerStatusState (pages/mower_status/state.dart, size 0x18)

```text
0x08  disConnect (bool, late)      — Disconnection flag
0x0c  workType (String, late)      — Display string for current work mode
0x10  mowerControl (bool, late)    — Whether mower control buttons are shown
0x14  timer (Timer?, late)         — Polling timer reference
```

### DeviceState (pages/device/state.dart, size 0x20)

```text
0x08  connectType (int, late)         — BLE connection type
0x0c  currentIndex (int, late)        — Page tab index
0x10  pageController (PageController) — Tab controller
0x14  deviceInfo (Map<String,String>?) — Device info map
0x18  batteryImage (String, late)     — Asset path for battery icon
0x1c  timer (Timer?, late)            — Timer reference
```
