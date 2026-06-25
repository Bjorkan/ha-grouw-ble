# AGENTS.md

Guidance for AI agents working on this repository.

## Mandatory Knowledge Files

Keep these files up to date whenever you learn something useful. They are the
repo's durable memory because local reference folders are not committed.

```text
DEVELOPMENT.md
TESTING.md
REVERSE_ENGINEERED.md
README.md
```

Update them in the same change when you:

- confirm or change Home Assistant integration behavior
- find or correct BLE protocol details
- add, remove, or change tests
- add service actions, entities, options, diagnostics, or config flow behavior
- validate behavior on real mower hardware
- discover that previous assumptions were wrong

## Local-Only Reference Folders

These folders may exist on a developer machine but must not be relied on as
committed project documentation:

```text
APK/
```

Official APK files, extracted APK contents, and decompiled app files must never
be upstreamed. They may only be used locally as source material for reverse
engineering. Commit durable findings as summaries in `REVERSE_ENGINEERED.md`
instead of committing proprietary app artifacts or generated decompiler output.

Do not add committed docs that only point into those folders. If an agent finds
something useful there, summarize it in `DEVELOPMENT.md`, `TESTING.md`, or
`REVERSE_ENGINEERED.md`.

Authoritative external references:

- Home Assistant developer docs:
  https://developers.home-assistant.io/docs/development_index/
- Hassfest for custom components:
  https://developers.home-assistant.io/blog/2020/04/16/hassfest/
- Grouw / robotic-mower connect app:
  https://play.google.com/store/apps/details?id=com.cj.lawnmower

## Project

This repository contains a Home Assistant custom integration for Grouw /
`robotic-mower connect` BLE lawn mowers.

The integration lives in:

```text
custom_components/grouw_ble_mower/
```

## Home Assistant Rules For This Repo

- Use Home Assistant's Bluetooth manager. Do not create a standalone scanner.
- Resolve connectable devices with
  `bluetooth.async_ble_device_from_address(..., connectable=True)`.
- Manual setup and Bluetooth discovery must both use stable unique IDs based on
  the normalized BLE address.
- Keep device and entity unique IDs stable. Entity ID churn breaks user
  dashboards and automations.
- Use `DataUpdateCoordinator` for polling and shared state.
- Raise `ConfigEntryNotReady` only before the first successful state when setup
  should retry. After the integration has state, temporary BLE failures should
  become `UpdateFailed`.
- Mark entities unavailable through coordinator update failures; avoid keeping
  stale state looking healthy.
- BLE transactions must be serialized per mower. These devices should not
  receive concurrent connect/write/read flows.
- Implement and preserve config entry unloading. Clean up services,
  subscriptions, callbacks, and connections.
- Keep diagnostics useful but redacted. Do not expose serial numbers, addresses,
  credentials, or user-sensitive fields unnecessarily.
- Prefer options for command behavior tweaks; connection-critical values belong
  in config entry data.
- Use translations for user-facing config/options/entity text.

## Current BLE Protocol Facts

The durable protocol summary is in `REVERSE_ENGINEERED.md`. Do not change BLE
constants or parsers without updating that file and adding/updating tests.

## Service Actions

The debug action is:

```text
grouw_ble_mower.send_raw_json
```

This is for protocol validation. It should raise `ServiceValidationError` when
the service call cannot be mapped to a mower, and `HomeAssistantError` when BLE
communication fails.

If adding new actions, update:

```text
custom_components/grouw_ble_mower/services.yaml
custom_components/grouw_ble_mower/strings.json
custom_components/grouw_ble_mower/translations/sv.json
README.md
DEVELOPMENT.md
TESTING.md
tests/
```

## Testing

Run the commands in `TESTING.md` before handing off changes. If commands,
dependencies, or test assumptions change, update `TESTING.md` and
`requirements-test.txt` in the same patch. Keep the GitHub Actions workflows in
`.github/workflows/` working on push and pull request unless the user explicitly
asks to remove CI.

## Style

- Keep changes scoped to the integration unless the task says otherwise.
- Prefer small, typed helper functions over broad rewrites.
- Do not hand-roll parsing with fragile string operations when structured JSON
  or byte handling is available.
- Do not introduce network/cloud behavior; this integration is local BLE.
- Use `rg` for searching.
- Avoid touching local decompiled APK output under `APK/` unless needed for protocol
  research, and summarize findings in `REVERSE_ENGINEERED.md`.
- Never commit or upstream APK files, extracted APK trees, decompiled Java,
  smali, native-library dumps, or generated decompiler output.
