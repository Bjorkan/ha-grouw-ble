# DEVELOPMENT.md

Durable development notes for this repository. Keep this file up to date when
implementation details, Home Assistant conventions, or architecture decisions
change.

Last updated: 2026-06-25

## Authoritative References

- Home Assistant developer docs:
  https://developers.home-assistant.io/docs/development_index/
- Hassfest for custom components:
  https://developers.home-assistant.io/blog/2020/04/16/hassfest/
- Daye Power robotic mower app:
  https://play.google.com/store/apps/details?id=com.dayepower.dayeappleaf

Local APK/decompiler folders such as `APK/` or
`/var/home/jesper/Projekt/grouw-mower-apk/` are intentionally not part of the
git repo. Summarize durable findings here instead of relying on those paths.

Official APK files, extracted APK trees, and decompiled files must never be
upstreamed. They are local-only reverse-engineering inputs.

## Repository Layout

```text
custom_components/grouw_ble_mower/   Home Assistant custom integration
tests/                               Lightweight unit tests and HA stubs
.github/workflows/                   GitHub Actions for tests and hassfest
requirements-test.txt                GitHub Actions test dependencies
README.md                            User-facing setup and protocol notes
DEVELOPMENT.md                       Development and HA integration notes
TESTING.md                           Test strategy and commands
REVERSE_ENGINEERED.md                BLE protocol findings
AGENTS.md                            Instructions for AI agents
```

## Integration Shape

- Domain: `grouw_ble_mower`
- Integration type: local polling BLE custom component
- Platforms: `lawn_mower`, `sensor`, `binary_sensor`
- Config flow: supports Bluetooth discovery and manual BLE address entry.
  Discovery currently matches confirmed service UUID
  `49535343-fe7d-4ae5-8fa9-9fafd205e455` and Daye local-name strings
  `Robot Mower_DYM*`, `RobotMower_DYM*`, and `Robot_Mower*`.
  Do not set read/write/notify characteristic constants until characteristic
  properties and Daye app usage are confirmed.
- Options flow: not exposed while Daye command payloads are unconfirmed.
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
- A missing BLE device before first data should behave like setup-not-ready.
  Once state exists, temporary BLE loss should be an update failure so entities
  become unavailable without resetting setup.
- BLE communication is serialized per mower with an `asyncio.Lock`; do not
  remove this without a real concurrency-safe replacement.
- Config entry unloading must continue to work. Clean up services and callbacks
  when the last entry unloads.
- Diagnostics must be redacted. Avoid exposing BLE address, serial number, raw
  secrets, or personal/user-specific values unnecessarily.
- User-facing text belongs in `strings.json` and translations under
  `translations/`.

## Current Implementation Notes

- Initial setup stores the coordinator before first refresh, then attempts an
  initial BLE refresh. If the mower is asleep or temporarily unreachable, setup
  continues with unavailable entities instead of blocking the config entry.
- The debug action routes to a coordinator by `entry_id`, by normalized
  `address`, or by the sole loaded coordinator.
- The debug action raises `ServiceValidationError` when the target mower cannot
  be determined, and `HomeAssistantError` for BLE communication failures.
- The integration intentionally reconnects for each BLE request. This keeps the
  code compatible with Home Assistant Bluetooth proxies, but makes request
  serialization important.
- The polling interval is currently 60 seconds.
- `sensor` and `binary_sensor` set `PARALLEL_UPDATES = 0` because coordinator
  polling centralizes reads. `lawn_mower` sets `PARALLEL_UPDATES = 1` because it
  exposes command actions.

## When Adding Features

Update all applicable files:

```text
README.md
DEVELOPMENT.md
TESTING.md
REVERSE_ENGINEERED.md
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
