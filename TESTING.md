# TESTING.md

Testing notes for the Grouw / Daye BLE Mower Home Assistant custom integration.

Last updated: 2026-06-25

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

- BLE JSON frame encoding
- chunked BLE notification reassembly
- checksum rejection and resynchronization
- coordinator setup retry behavior before first state
- coordinator update failure behavior after a state exists
- serialization of concurrent raw JSON BLE requests
- raw JSON action validation when no target mower can be resolved
- compile-time coverage for Home Assistant exception imports and platform
  constants through `compileall`

Test files:

```text
tests/test_config_flow.py
tests/test_ble_protocol.py
tests/test_coordinator.py
tests/test_init.py
tests/test_services.py
```

## Add Or Update Tests When Changing

- BLE frame constants, checksum, length handling, chunking, or buffering
- JSON parsing or `MowerState` field mapping
- response command handling
- coordinator exception mapping
- BLE serialization or connection behavior
- config flow discovery/manual setup/duplicate prevention
- options flow behavior
- service action routing and validation
- entity availability, unique IDs, device info, or state mapping

## Hardware Validation Checklist

Use this checklist when testing against a real mower:

1. Confirm Home Assistant discovers the mower by service UUID or by
   `Robot Mower_DYM*` / `RobotMower_DYM*` / `Robot_Mower*` name.
2. Confirm manual setup by BLE address works.
3. Confirm characteristic properties for all `49535343...` characteristics.
4. Confirm which characteristic the Daye app writes and which one it subscribes
   to before treating `grouw_ble_mower.send_raw_json` results as protocol facts.
5. Capture and redact the Daye app status-refresh write and notification
   payloads.
6. Confirm battery, mode, error, docked, runtime, area, Wi-Fi, rain, LED, and
   ultrasonic field mappings only after the Daye status payload is known.
7. Capture and confirm the Daye app payload for start mowing.
8. Capture and confirm the Daye app payload for pause/stop.
9. Capture and confirm the Daye app payload for dock/home.
10. Confirm unavailable behavior when the mower sleeps or moves out of range.
11. Update `README.md`, `DEVELOPMENT.md`, and `REVERSE_ENGINEERED.md` with
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
