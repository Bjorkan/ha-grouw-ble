# Testing Notes

Testing guide for the Grouw Mower Home Assistant custom integration.

Last updated: 2026-07-15.

## Quick Verification

Run these before handing off changes:

```bash
ruff check .
ruff format --check .
pytest -q -p no:cacheprovider
python3 -m compileall -q custom_components/grouw_ble_mower tests
find custom_components tests -type d -name __pycache__ -prune -exec rm -rf {} +
rm -rf .pytest_cache .ruff_cache
```

`-p no:cacheprovider` keeps pytest from creating `.pytest_cache`.

## Local Environment

The lightweight local test environment may not include Home Assistant,
`voluptuous`, `bleak`, or `pygrouw`. Tests that need those packages either use
stubs from `tests/conftest.py`, load the sibling `../pyGrouw/src` checkout when
present, or skip when the full Home Assistant test environment is missing.

The stubs are only for tests. Do not import them from production code.

## CI And Hassfest

Validation runs on both `push` and `pull_request`:

```text
.github/workflows/test_unit.yaml
.github/workflows/validate_hassfest.yaml
.github/workflows/validate_hacs.yaml
```

`test_unit.yaml` installs `requirements-test.txt`, runs Ruff lint and format
checks, runs pytest, and compiles the integration and tests. The CI environment
includes `pytest-homeassistant-custom-component`, so HA setup/unload and config
flow tests run there instead of being skipped.

`validate_hassfest.yaml` runs Home Assistant's custom-component metadata validation.
Treat hassfest failures as blocking unless the issue is clearly temporary
upstream tooling.

When Docker and `act` are available, reproduce the workflows with:

```bash
act -j tests -P ubuntu-latest=catthehacker/ubuntu:act-latest
act -j validate -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

## Test Files

```text
tests/test_config_flow.py      Manual setup, PIN validation, discovery forms
tests/test_coordinator.py      Polling, commands, cooldowns, reauth mapping
tests/test_entity_availability.py  Status/settings-backed entity availability
tests/test_init.py             Config entry setup/unload
tests/test_lawn_mower.py       Activity mapping and mower commands
tests/test_services.py         Service validation/routing and response support
```

## Current Coverage

Protocol and BLE/client coverage now lives in the companion `pyGrouw` library:

- captured DYM status, session/auth, start/resume, pause/stop, and dock
  payloads
- DYM and BlueKey payload encoding/parsing
- PIN/auth response parsing and redaction
- best-effort MTU request behavior
- notification filtering, timeout handling, and client-level request
  serialization

Coordinator/service coverage:

- first-poll failure behavior
- failure backoff after previous state
- poll cooldown after manual command
- skipping background polls while a manual command is pending
- polling and commands delegated to `pygrouw.GrouwMower`
- concurrent raw request serialization
- raw service target resolution failures
- service response support for read and optional debug/write services
- confirmed PIN/auth mismatches mapped to reauth
- `pygrouw` BLE exceptions mapped to HA update/service errors
- settings service handlers delegated to new coordinator methods
- sensor and binary sensor `available` property overrides for status and
  settings-backed entities

Entity/config coverage:

- config entry setup and unload
- manual config flow address validation
- config flow PIN validation
- `MowerState` battery, mode, station, and response-command mapping
- lawn mower activity mapping for mowing `0x00`/`0x01`, returning, docked,
  paused, station override, and unknown station
- lawn mower start behavior when station state is unknown
- compile-time import/platform coverage through `compileall`

## Update Tests When Changing

- DYM or BlueKey constants, payload encoders, parsers, or response-command
  handling in `../pyGrouw`
- PIN validation, auth response parsing, redaction, or reauth behavior
- `MowerState` field mapping
- coordinator polling, cooldowns, exception mapping, or serialization
- BLE connection, write, notify, timeout, or MTU behavior in `../pyGrouw`
- config flow discovery/manual setup/duplicate prevention
- options flow behavior
- service action routing and validation
- entity availability, unique IDs, device info, or state mapping
- lawn mower activity mapping, especially station/docked override behavior

## Hardware Validation Checklist

Use this checklist against a real mower:

1. Confirm discovery by service UUID or by `Robot Mower_DYM*`,
   `RobotMower_DYM*`, or `Robot_Mower*`.
2. Confirm manual setup by BLE address.
3. Confirm setup requires a 4-digit PIN and starts reauth when the stored PIN
   is missing or invalid.
4. Confirm status polling uses the captured DYM status request and does not
   make the mower beep.
5. Confirm polling still works after the app/mower has disconnected, without
   the DYM session/auth prelude.
6. Confirm battery, station, and mode mapping while docked, stopped, mowing,
   and returning.
7. Confirm start/resume, pause/stop, and dock commands execute without the DYM
   session/auth prelude and refresh state through the follow-up status poll.
8. Capture charging, error, lift, and tilt payloads.
9. Treat rain as a settings feature unless a BLE status byte is captured.
10. Confirm unavailable behavior when the mower sleeps or moves out of range.
11. Confirm PIN change via `change_pin` service and that the new PIN is used for
    subsequent authenticated requests.
12. Confirm multi-area read/write via `get_multi_area` / `set_multi_area` services
    and that sensor entities update after reading.
13. Confirm mower settings read/write via `get_mower_settings` / `set_mower_settings`
    services and that binary sensor entities update after reading.
14. Confirm work time read/write via `get_work_times` / `set_work_times` services.
15. Update `README.md`, `DEVELOPMENT.md`, `TESTING.md`, and the companion
    library's `reverse_engineered/` folder with validated facts and remaining
    uncertainty.

Known mode observations from 2026-06-26:

```text
0x00 = mowing
0x01 = mowing/active, exact distinction unknown
0x03 = returning home
0x14 = stopped / standing still
```

Known beep observations from 2026-06-26:

```text
authenticated command: status     -> beeped
unauthenticated command: status   -> quiet
unauthenticated session_start     -> two beeps, then notification timeout
unauthenticated BlueKey queryInfo -> quiet, then notification timeout
unauthenticated resume            -> executed, normal start-warning beeps
unauthenticated dock/pause        -> executed, no extra beeps observed
```

## Debug Logging

During manual validation:

```yaml
logger:
  default: info
  logs:
    custom_components.grouw_ble_mower: debug
    bleak_retry_connector: debug
```

Do not commit logs containing serial numbers, BLE addresses, PINs, credentials,
or other private data unless they are redacted.
