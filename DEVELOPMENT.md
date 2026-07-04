# Development Notes

Durable development notes for the Grouw Mower Home Assistant custom
integration.

Last updated: 2026-06-28.

## Read First

- User setup and feature status: [README.md](README.md)
- Test strategy and commands: [TESTING.md](TESTING.md)
- Protocol map and detailed findings:
  [../pyGrouw/reverse_engineered/index.md](../pyGrouw/reverse_engineered/index.md)
- Agent rules and documentation update policy: [AGENTS.md](AGENTS.md)

## Authoritative Inputs

Use only these sources for protocol facts:

- Daye Power robotic mower app:
  https://play.google.com/store/apps/details?id=com.dayepower.dayeappleaf
- Redacted real-hardware captures from the target mower generation.
- Local manuals only for product behavior and model boundaries, not packet
  semantics.

Keep APKs, decompiler output, manuals, and raw captures under `APK/` or other
local-only paths. Summarize durable findings in the companion library's
`reverse_engineered/` folder instead of committing proprietary or private
artifacts.

Do not reintroduce protocol assumptions from the older `com.cj.lawnmower` app.

## Repository Map

```text
custom_components/grouw_ble_mower/   Home Assistant custom integration
tests/                               Unit tests and HA-style tests
.github/workflows/                   GitHub Actions for tests and hassfest
requirements-test.txt                Test and CI dependencies
README.md                            User-facing setup and current status
DEVELOPMENT.md                       Development and architecture notes
TESTING.md                           Test commands, coverage, hardware checks
../pyGrouw/reverse_engineered/       Durable protocol findings by topic
AGENTS.md                            Instructions for AI agents
```

## Integration Shape

- Domain: `grouw_ble_mower`.
- Integration type: local polling BLE custom component.
- Platforms: `lawn_mower`, `sensor`, `binary_sensor`.
- Config flow: Bluetooth discovery and manual BLE address entry.
- Options flow: not exposed.
- Coordinator: `GrouwMowerCoordinator`.
- BLE/protocol library: `pygrouw` (`GrouwBleMowerClient`, `GrouwMower`,
  `MowerState`, discovery helpers, payload encoding/parsing).
- Debug action: `grouw_ble_mower.send_raw_json`.
- Settings actions: `change_pin`, `set_multi_area`, `set_mower_settings`,
  `set_work_times`, `get_multi_area`, `get_mower_settings`, `get_work_times`.

Discovery matches:

```text
Service UUID: 49535343-fe7d-4ae5-8fa9-9fafd205e455
Local names:  Robot Mower_DYM*, RobotMower_DYM*, Robot_Mower*
```

The app writes and subscribes to characteristic:

```text
49535343-1e4d-4bd9-ba61-23c647249616
```

## Home Assistant Rules

- Use Home Assistant Bluetooth APIs. Do not start a standalone scanner.
- Resolve outgoing connections with
  `async_ble_device_from_address(..., connectable=True)`.
- Pass the HA-resolved connectable BLE device to `pygrouw` through a
  `device_provider`; do not add direct BLE scanner/client logic back to the
  integration.
- Use stable unique IDs based on normalized BLE address.
- Keep `has_entity_name = True`; the lawn mower entity has `_attr_name = None`
  so it becomes the main device entity.
- Use `DataUpdateCoordinator` for shared polling state.
- Temporary BLE failures after setup should become `UpdateFailed`, which makes
  entities unavailable instead of healthy with stale data.
- Preserve config entry unloading and clean up services, callbacks, and runtime
  state.
- Keep diagnostics and normal debug logs redacted.
- Put user-facing text in `translations/`. This repo also has `strings.json`
  for service metadata.

## BLE Runtime Decisions

- Normal polling and controls use `pygrouw`, which owns the HCI-confirmed DYM
  payloads, parsing, BLE writes, notifications, MTU request, and raw debug
  payload encoding.
- APK-derived BlueKey commands are debug probes only until hardware captures
  confirm when and how those 48-value payloads are written on the wire.
- `pygrouw` reconnects for each BLE request. This keeps Bluetooth proxy
  behavior simple, but makes serialization important.
- BLE communication is serialized per mower with the coordinator `_ble_lock`;
  `pygrouw` also serializes requests at client level.
- Manual commands and raw service calls increment a pending-command counter
  before waiting for the BLE lock. Background polls skip while that counter is
  non-zero, so a newly scheduled poll does not jump ahead of a queued user
  command.
- Manual-command cooldown starts after the BLE transaction completes.
- The polling interval is currently 30 seconds. BLE failure backoff is also 30
  seconds.
- The APK requests MTU 512 before service discovery. `pygrouw` mirrors this as
  a best-effort MTU request and continues if the Bleak backend does not support
  it.

## Protocol Decisions In Code

- The config flow uses `pygrouw.is_valid_pin` and requires exactly four ASCII
  decimal PIN digits.
- Normal status and control transactions skip the DYM session/auth prelude
  because real-hardware validation showed the prelude can make the mower beep,
  while unauthenticated DYM status/start/resume/pause/dock payloads work on the
  tested mower. `pygrouw` owns those command transactions.
- Settings read/write operations (multi-area, mower settings, work times, PIN
  change) do require authentication. These are performed on demand through
  services and are not part of the normal polling cycle.
- The auth/PIN path remains available for raw protocol validation and future
  research.
- DYM response command `0x80` is treated as status. DYM response command
  `0x8c` is treated as auth/PIN.
- DYM mode `0x00` and `0x01` are both mapped to mowing activity. The exact
  distinction remains unknown.
- DYM mode `0x03` maps to returning home. DYM mode `0x14` maps to stopped or
  standing still.
- The dock/station byte overrides mode when deriving Home Assistant lawn mower
  activity because the mower can report docked while the mode byte still looks
  active.
- Exposed entities include fields from DYM status notifications (battery, mode,
  last response command, docked state, lawn mower activity) and cached values
  from on-demand settings reads (multi-area percentages/distances, rain delay,
  mow in rain, boundary cut, helix, LED, unknown setting).

The detailed evidence behind these decisions is in:

- [../pyGrouw/reverse_engineered/dym_protocol.md](../pyGrouw/reverse_engineered/dym_protocol.md)
- [../pyGrouw/reverse_engineered/response_parsing.md](../pyGrouw/reverse_engineered/response_parsing.md)
- [../pyGrouw/reverse_engineered/ble_write_flow.md](../pyGrouw/reverse_engineered/ble_write_flow.md)

## Debug Service

`grouw_ble_mower.send_raw_json` routes to a coordinator by `entry_id`,
normalized `address`, or the sole loaded coordinator.

It should raise:

- `ServiceValidationError` when the target mower cannot be resolved.
- `HomeAssistantError` when BLE communication fails.

The service can send named DYM commands, raw hex payloads, and APK-shaped
BlueKey probes. BlueKey probe payloads convert APK `List<int>` values to BLE
bytes with `value & 0xff`; the APK trailer value `510` is therefore emitted as
`0xfe` until captures prove the native/platform conversion.

## Settings Services

The following services are registered for on-demand settings operations:

- `change_pin` — delegates to `client.async_change_pin(new_pin)` and relies on
  the configured PIN as the current PIN. The HA service schema still accepts a
  legacy `old_pin` field for existing automations, but ignores it.
- `set_multi_area` — delegates to `client.async_set_multi_area(...)`.
- `set_mower_settings` — delegates to `client.async_set_mower_settings(...)`.
- `set_work_times` — delegates to `client.async_set_work_times(...)`.
- `get_multi_area` — reads settings and caches them in `coordinator.multi_area`.
- `get_mower_settings` — reads settings and caches them in `coordinator.mower_settings`.
- `get_work_times` — reads settings and caches them in `coordinator.work_time_starts`
  and `coordinator.work_time_durations`.

All settings services follow the same pattern as `async_send_command`:
they acquire `_ble_lock`, increment `_pending_commands`, handle auth and BLE
errors, and update coordinator state on success.

Settings sensors and binary sensors display cached values from the coordinator.
They show `None` until the corresponding get or set service is called.
Their availability follows the pyGrouw data source they use: normal status
entities require a status `MowerState.last_seen`, while settings entities become
available once their corresponding settings cache has been read or written,
even if the latest normal status poll failed.

## Implementation Notes

- Setup stores the coordinator before first refresh. If the first refresh
  fails because the mower is asleep or unreachable, entities load unavailable
  rather than blocking the config entry with placeholder data.
- The coordinator creates a `pygrouw.GrouwBleMowerClient` with a
  Home Assistant Bluetooth `device_provider`, wraps it in `pygrouw.GrouwMower`,
  and stores `pygrouw.MowerState` in coordinator data.
- The debug action and coordinator redact PIN/auth response bytes before
  storing or logging state by using `pygrouw.redact_daye_message` and
  redacted `MowerState.raw` values.
- BLE errors are classified by `pygrouw` as connection, GATT, timeout, auth, or
  generic BLE errors. The integration maps those exceptions to HA reauth,
  `UpdateFailed`, or `HomeAssistantError`.
- `sensor` and `binary_sensor` set `PARALLEL_UPDATES = 0`. `lawn_mower` sets
  `PARALLEL_UPDATES = 1` because it exposes command actions.
- Coordinator resolves the target mower for service calls using
  `_resolve_coordinator()` helper which checks `entry_id`, `address`, or falls
  back to the sole configured coordinator.
- Services are registered from `async_setup` so Home Assistant can validate
  actions even when no config entry is loaded. Handlers raise
  `ServiceValidationError` when no loaded coordinator can be resolved.
- Read, debug, and write services use `SupportsResponse.OPTIONAL` and return
  pyGrouw response data only when the action call requests a response. On Home
  Assistant versions without service-response support, services are registered
  without the `supports_response` keyword.

## When Adding Features

Update every relevant durable file in the same change:

```text
README.md
DEVELOPMENT.md
TESTING.md
../pyGrouw/reverse_engineered/
custom_components/grouw_ble_mower/services.yaml
custom_components/grouw_ble_mower/strings.json
custom_components/grouw_ble_mower/translations/
tests/
```

Add or update tests for:

- protocol constants and parsers in `../pyGrouw`
- entity state mapping and availability
- config flow and reauth behavior
- service routing and validation
- integration-level serialization, cooldowns, and pyGrouw exception mapping
- diagnostics and redaction

## Known Improvement Areas

- Add broader Home Assistant integration tests as dependency coverage improves.
- Extend discovery/manual config flow tests for duplicate prevention.
- Consider `ConfigEntry.runtime_data` when the supported Home Assistant
  baseline is modern enough.
- Add user-facing troubleshooting once more real-hardware logs are available.
