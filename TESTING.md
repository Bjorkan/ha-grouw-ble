# TESTING.md

Testing notes for the Grouw / Daye BLE Mower Home Assistant custom integration.

Last updated: 2026-06-25 (Daye APK/DYM protocol alignment)

## Current Local Test Environment

The local Python environment used while creating this file had `pytest`
available but did not have Home Assistant, `voluptuous`, `bleak`, or
`bleak-retry-connector` installed.

Because of that, the current unit tests use lightweight stubs in:

```text
tests/conftest.py
```

Those stubs are only for tests. Do not import them from production code.

## Standard Verification Commands

Run these before handing off changes:

```bash
pytest -q -p no:cacheprovider
python3 -m compileall -q custom_components/grouw_ble_mower tests
find custom_components tests -type d -name __pycache__ -prune -exec rm -rf {} +
rm -rf .pytest_cache
```

The `-p no:cacheprovider` flag keeps pytest from creating `.pytest_cache`.

When Docker and `act` are available, reproduce the GitHub Actions test workflow
with:

```bash
act -j tests -P ubuntu-latest=catthehacker/ubuntu:act-latest
act -j validate -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

That path installs the full `requirements-test.txt` environment, including
Home Assistant's test helpers and Bluetooth import dependencies such as
`aiousbwatcher` and `pyserial`. Tests mock Home Assistant's
`bluetooth_adapters` dependency so CI never tries to open a real Bluetooth
socket.

## GitHub Actions

This repository runs validation on both `push` and `pull_request`:

```text
.github/workflows/tests.yaml
.github/workflows/hassfest.yaml
```

`tests.yaml` installs dependencies from `requirements-test.txt`, runs pytest,
and compiles the integration and tests. The CI environment installs
`pytest-homeassistant-custom-component`, so the Home Assistant setup/unload and
config flow tests run there instead of being skipped.

## Hassfest

Hassfest is Home Assistant's static validation tool for integration metadata and
integration data. Home Assistant's developer blog documents custom-component
hassfest validation with the GitHub Action
`home-assistant/actions/hassfest@master`:

```text
https://developers.home-assistant.io/blog/2020/04/16/hassfest/
```

This repository includes:

```text
.github/workflows/hassfest.yaml
```

That workflow runs on pushes, pull requests, and nightly schedule. It is the
preferred hassfest path for this repo because a standalone custom integration
does not normally include Home Assistant Core's local `script.hassfest` module.

If working inside a Home Assistant Core development checkout with this custom
component available to hassfest, the equivalent local command is:

```bash
python -m script.hassfest
```

Treat hassfest failures as blocking unless the failure is clearly caused by a
temporary upstream tooling issue.

## Home Assistant Fixture Tests

This repo includes HA-style tests that use
`pytest-homeassistant-custom-component` when it is installed:

```text
tests/test_init.py
tests/test_config_flow.py
```

They cover config entry setup/unload and the UI config flow form. In the
lightweight local environment they are skipped, while the protocol and
coordinator unit tests still run against stubs.

## Current Test Coverage

Current tests cover:

- captured DYM command encoding
- captured DYM session/auth prelude encoding
- DYM notification parsing for the confirmed 22-byte status shape
- parsing and redaction of PIN-looking DYM `0x8c` auth/PIN responses
- configured PIN verification against mower auth/PIN response data
- draining queued notifications at auth/follow-up request boundaries
- ignoring non-DYM notifications and avoiding state decoding from short packets
- `MowerState` updates for confirmed DYM battery, mode, station and response
  command fields
- BLE client response filtering by DYM command byte
- raw debug service option coercion/validation for hex `expect_cmd` and string
  booleans
- coordinator first-poll failure raises UpdateFailed instead of returning placeholder
- coordinator BLE failure backoff raises UpdateFailed even after a previous state
- coordinator poll cooldown after manual command
- serialization of concurrent raw BLE payload requests
- raw BLE payload action validation when no target mower can be resolved
- manual config flow address validation rejects blank addresses
- lawn mower activity mapping (mowing, returning, docked, paused, unknown station)
- lawn mower start command refreshes state when station is unknown
- compile-time coverage for Home Assistant exception imports and platform
  constants through `compileall`

Test files:

```text
tests/test_config_flow.py
tests/test_ble_client.py
tests/test_ble_protocol.py
tests/test_coordinator.py
tests/test_init.py
tests/test_services.py
tests/test_lawn_mower.py
```

## Add Or Update Tests When Changing

- DYM command constants, session/auth prelude, status notification parsing, or
  response command handling
- PIN validation, auth response parsing, or PIN redaction
- JSON parsing or `MowerState` field mapping
- coordinator exception mapping
- BLE serialization or connection behavior
- config flow discovery/manual setup/duplicate prevention
- options flow behavior
- service action routing and validation
- entity availability, unique IDs, device info, or state mapping
- lawn mower activity mapping from mode+station bytes
- start command refresh-choosing logic

## Hardware Validation Checklist

Use this checklist when testing against a real mower:

1. Confirm Home Assistant discovers the mower by service UUID or by
   `Robot Mower_DYM*` / `RobotMower_DYM*` / `Robot_Mower*` name.
2. Confirm manual setup by BLE address works.
3. Confirm Home Assistant can read status with the captured DYM status poll.
4. Confirm polling still works after the mower/app has disconnected and the
   integration performs the captured session/auth prelude itself.
5. With a configured PIN, confirm the integration verifies the PIN against the
   auth/PIN response and refuses commands with a deliberately wrong PIN.
6. Confirm battery, station and mode mapping during docked, stopped, mowing and
   returning states.
7. Confirm start mowing sends the station-start payload while docked and the
   resume payload after pause/stop.
8. Confirm pause/stop sends the captured stop payload and the mower stops.
9. Confirm dock/home sends the captured dock payload and the mower returns.
10. Capture additional charging, error, lift and tilt status payloads. Treat rain
   as a settings feature unless a BLE status byte is captured for it.
11. Confirm unavailable behavior after a successful poll when the mower sleeps or
   moves out of range.
12. Update `README.md`, `DEVELOPMENT.md`, and `reverse_engineered/` with
    validated facts and any remaining uncertainty.

## Useful Debug Logging

During manual validation, add this to Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.grouw_ble_mower: debug
    bleak_retry_connector: debug
```

Do not commit logs containing serial numbers, BLE addresses, credentials, or
other private data unless they are redacted.
