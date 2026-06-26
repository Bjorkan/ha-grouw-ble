# DEVELOPMENT.md

Durable development notes for this repository. Keep this file up to date when
implementation details, Home Assistant conventions, or architecture decisions
change.

Last updated: 2026-06-26 (BLE stability)

## Authoritative References

- Home Assistant developer docs:
  https://developers.home-assistant.io/docs/development_index/
- Hassfest for custom components:
  https://developers.home-assistant.io/blog/2020/04/16/hassfest/
- Grouw mower app:
  https://play.google.com/store/apps/details?id=com.dayepower.dayeappleaf

Store APK files and decompiler output in `APK/` (gitignored). These local-only
inputs are for reverse-engineering only. Summarize durable findings here
instead of relying on those paths.

Official APK files, extracted APK trees, and decompiled files must never be
upstreamed. They are local-only reverse-engineering inputs.

Local Grouw manuals under `APK/Manuals/` are also local-only inputs. Summarize
durable findings under `reverse_engineered/` rather than committing PDFs or
generated text extracts.

## Repository Layout

```text
custom_components/grouw_ble_mower/   Home Assistant custom integration
tests/                               Lightweight unit tests and HA stubs
.github/workflows/                   GitHub Actions for tests and hassfest
requirements-test.txt                GitHub Actions test dependencies
README.md                            User-facing setup and protocol notes
DEVELOPMENT.md                       Development and HA integration notes
TESTING.md                           Test strategy and commands
reverse_engineered/                  BLE protocol findings (per-topic files)
AGENTS.md                            Instructions for AI agents
```

## Integration Shape

- Domain: `grouw_ble_mower`
- Integration type: local polling BLE custom component
- Platforms: `lawn_mower`, `sensor`, `binary_sensor`
- Config flow: supports Bluetooth discovery and manual BLE address entry.
  Discovery currently matches confirmed service UUID
  `49535343-fe7d-4ae5-8fa9-9fafd205e455` and local-name strings
  `Robot Mower_DYM*`, `RobotMower_DYM*`, and `Robot_Mower*`.
  Manual setup rejects blank addresses before asking for the mower PIN.
  The app writes and subscribes to characteristic
  `49535343-1e4d-4bd9-ba61-23c647249616`.
- Options flow: not exposed.
- Coordinator: `GrouwMowerCoordinator`
- BLE client: `GrouwBleMowerClient`
- Protocol parser/framer: `ble_protocol.py`
- Debug action: `grouw_ble_mower.send_raw_json`

## Home Assistant Development Notes

- Use Home Assistant's Bluetooth APIs. Do not start a separate BLE scanner.
- Use `async_ble_device_from_address(..., connectable=True)` for outgoing BLE
  connections so local adapters and connectable Bluetooth proxies work.
- Use stable unique IDs. This integration normalizes the BLE address and uses it
  for config entry uniqueness and entity unique IDs.
- Keep `has_entity_name = True` on entities. The lawn mower entity uses
  `_attr_name = None` so it becomes the main device entity.
- Use `DataUpdateCoordinator` for shared polling state.
- The coordinator polls with the captured DYM status request. Before the
  first successful poll, coordinator.data is None and last_update_success
  is False, so entities load as unavailable. On BLE failure the coordinator
  raises UpdateFailed instead of returning placeholder data.
- Each BLE transaction sends the captured session/auth prelude before the
  requested status or command payload, then waits for the captured auth response
  command byte `0x8c`. Keep this unless hardware testing proves the mower no
  longer needs PIN/session setup after reconnect.
- The APK's MainLogic connection-state callback awaits FlutterBluePlus
  `requestMtu` before service discovery. FlutterBluePlus requests MTU 512 in
  that path. The integration mirrors this with a best-effort MTU request after
  connect; unsupported Bleak backends log and continue because the captured DYM
  packets are short.
- Configured PIN handling follows the APK-observed query/compare shape: the
  config flow requires exactly four ASCII decimal digits, and the BLE client
  compares the configured PIN with `mower_pin` parsed from bytes 4-7 of a DYM
  `0x8c` response only when those bytes look like numeric digit bytes. The BLE
  client treats a missing configured PIN as an authentication error. The
  captured DYM auth query does not include the typed PIN in its write payload.
- Config entries with a missing/invalid stored PIN raise
  `ConfigEntryAuthFailed` during setup. Confirmed PIN mismatches raised from
  coordinator polling are also mapped to `ConfigEntryAuthFailed`, which starts
  Home Assistant's linked reauth flow for updating the existing entry's PIN.
  Confirmed PIN mismatches from mower service actions call
  `entry.async_start_reauth(hass)` when available before surfacing a
  `HomeAssistantError` for the action. An auth response without parseable PIN
  data is treated as a BLE/protocol update failure, not as a proven PIN failure.
- The active integration uses the HCI-confirmed DYM payloads on the wire.
  BlueKey commands are documented under `reverse_engineered/` from Dart AOT
  analysis but are not used for normal polling or controls until a hardware
  capture confirms when/how those 48-value payloads are written.
- The APK also contains BlueKey page flows for change PIN, mower settings,
  multi-area mowing, and weekly working-time settings. Current AOT findings map
  those query responses under `reverse_engineered/`, but the integration should
  not expose or write those settings until redacted HCI captures confirm the
  exact on-wire payloads for the target mower firmware.
- Local Grouw manuals reviewed on 2026-06-26 corroborate product UI concepts
  such as rain mowing, boundary cut, weekly work time, multi-zone/start-point
  setup, alert history, total runtime, and firmware update. These manuals also
  confirm `RobotMower_DYM` for models 17941/17947, but they do not provide BLE
  UUIDs or packet payloads. Keep protocol constants tied to the Daye APK and
  redacted hardware captures.
- The Grouw 18739/18740 CLEVR manual describes a separate IoT generation using
  `robotic-mower connect`, 2.4 GHz Wi-Fi, Bluetooth 4.0, default PIN `0000`,
  and BLE pairing name `Mower_XXXXXX`. Do not add those assumptions to this
  local DYM BLE integration without separate captures and design work.
- `grouw_ble_mower.send_raw_json` can build APK-shaped BlueKey probe payloads
  with `bluekey` or `bluekey_sub_cmd`, and parses BlueKey notifications into
  APK-style `byte1`, `byte2`, ... fields plus known settings/PIN helper maps.
  This is debug/protocol-validation support only; normal polling and control
  still use HCI-confirmed DYM packets.
- The BlueKey debug encoder converts APK `List<int>` values to BLE bytes with
  `value & 0xff`. That means the APK trailer value `510` is emitted as `0xfe`
  for probe payloads. Keep this assumption documented until hardware captures
  prove the exact native/platform conversion.
- Expose only fields decoded from HCI-confirmed DYM status notifications as
  entities. Current extra entities are: battery percentage, raw mode code, last
  response command, and docked state. Do not re-add rain, Wi-Fi, runtime, LED,
  ultrasonic, error-memory, or command-result entities until their response
  bytes are confirmed from the APK plus redacted hardware captures.
- BLE communication is serialized per mower with both the coordinator
  `_ble_lock` and the BLE client's `_request_lock`; do not remove these without
  a real concurrency-safe replacement. The client-level lock protects direct
  debug/test call paths in addition to normal coordinator traffic.
- Config entry unloading must continue to work. Clean up services and callbacks
  when the last entry unloads.
- Diagnostics must be redacted. Avoid exposing BLE address, serial number, raw
  secrets, or personal/user-specific values unnecessarily.
- User-facing text belongs in `translations/` directory. Custom integrations
  must use `translations/en.json`, not `strings.json`, which is only for
  Home Assistant core components processed by the build-time pipeline.

## Current Implementation Notes

- Initial setup stores the coordinator before first refresh, then attempts an
  initial BLE refresh. If the mower is asleep or temporarily unreachable before
  any successful poll, setup continues with coordinator.data = None and
  last_update_success = False so entities load as unavailable instead of
  blocking the config entry or showing stale placeholder data.
- The coordinator defers background polling after a manual command (cooldown)
  and after a BLE failure (backoff) to avoid competing with user actions and
  to let the mower/Bluetooth stack settle. Manual-command cooldown may return
  the latest state, but BLE failure backoff raises `UpdateFailed` even after a
  previous successful state so entities become unavailable instead of looking
  healthy with stale data.
- The debug action routes to a coordinator by `entry_id`, by normalized
  `address`, or by the sole loaded coordinator.
- The debug action raises `ServiceValidationError` when the target mower cannot
  be determined, and `HomeAssistantError` for BLE communication failures.
- The integration intentionally reconnects for each BLE request. This keeps the
  code compatible with Home Assistant Bluetooth proxies, but makes request
  serialization important.
- The polling interval is currently 60 seconds with a 30-second BLE failure
  backoff interval.
- `sensor` and `binary_sensor` set `PARALLEL_UPDATES = 0` because coordinator
  polling centralizes reads. `lawn_mower` sets `PARALLEL_UPDATES = 1` because it
  exposes command actions.
- Every BLE transaction is logged with a per-request transaction ID, phase
  labels (connect, start_notify, session_start write, auth_query write, command
  write, follow-up write), notification hex values, and the selected response.
- Notification waits use one overall deadline per phase. Unexpected
  notifications are ignored, but they must not extend the auth/status timeout.
- The notification queue is drained after the `0x8c` auth response to prevent
  stale notifications from being returned as command responses. For command
  transactions with a follow-up status poll, the queue is drained again
  immediately before writing that status poll so the selected `0x80` response
  belongs to the follow-up request boundary.
- PIN/auth responses are redacted before being stored in coordinator state or
  written to normal debug/service logs.
- BLE errors are classified into GrouwBleConnectionError (connect timeout),
  GrouwBleGattError (GATT write/notify failure), and GrouwBleTimeout
  (notification timeout) for clearer logging and troubleshooting. Bleak,
  timeout, and OS backend exceptions are mapped into these categories where the
  failing phase is known.
- Manual-command cooldown is timestamped after the BLE transaction finishes, so
  a command that waited behind another transaction still suppresses immediate
  follow-up polling for the intended interval.

## When Adding Features

Update all applicable files:

```text
README.md
DEVELOPMENT.md
TESTING.md
reverse_engineered/
custom_components/grouw_ble_mower/services.yaml
custom_components/grouw_ble_mower/strings.json
custom_components/grouw_ble_mower/translations/sv.json
tests/
```

Add tests for new parsing, entity behavior, config flow behavior, service action
routing, and error handling.

## Known Improvement Areas

- Add Home Assistant based tests when a HA test environment is available.
- Extend config flow tests for discovery/manual setup and duplicate prevention.
- Consider moving runtime coordinator storage to typed `ConfigEntry.runtime_data`
  when targeting a modern Home Assistant baseline consistently.
- Consider more user-facing troubleshooting detail once real hardware logs are
  available.
