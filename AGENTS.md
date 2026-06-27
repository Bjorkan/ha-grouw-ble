# AGENTS.md

Guidance for AI agents working on this repository.

## Mandatory Knowledge Files

Keep these files up to date whenever you learn something useful. They are the
durable memory for this Home Assistant integration and its companion BLE
library.

```text
DEVELOPMENT.md
TESTING.md
README.md
README_sv.md
README_da.md
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw) `reverse_engineered/`
```

Use
[Bjorkan/pyGrouw reverse_engineered/index.md](https://github.com/Bjorkan/pyGrouw/blob/main/reverse_engineered/index.md)
as the protocol map before editing detailed reverse-engineering notes. If a
local sibling checkout exists at `../pyGrouw`, agents may use it as a working
copy, but must not assume it exists for every contributor.

Update them in the same change when you:

- confirm or change Home Assistant integration behavior
- find or correct BLE protocol details
- add, remove, or change tests
- add service actions, entities, options, diagnostics, or config flow behavior
- add or change user-facing features that should be documented in every README
- validate behavior on real mower hardware
- discover that previous assumptions were wrong

## Repository Structure

This repository now contains only the Home Assistant custom integration. The
Python BLE/protocol library lives in
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw).

Current responsibilities:

```text
custom_components/grouw_ble_mower/   Home Assistant integration
tests/                               Integration/unit tests for HA behavior
README*.md                           User documentation in English, Swedish, Danish
DEVELOPMENT.md                       Integration architecture notes
TESTING.md                           Test commands and validation notes
Bjorkan/pyGrouw src/pygrouw/         BLE client, protocol, discovery helpers
Bjorkan/pyGrouw reverse_engineered/  Durable protocol findings by topic
```

Do not recreate integration-local BLE client or protocol parser modules. The
integration should consume `pygrouw` for:

- `GrouwBleMowerClient`
- `GrouwMower`
- `MowerState`
- BLE/protocol exceptions
- discovery helpers
- DYM/BlueKey payload encoding and parsing
- redaction helpers

If a change needs new protocol behavior, make that change in
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw), update its
reverse-engineering notes and tests there, then update this integration to
consume the released or local-compatible API.

## Local-Only APK Folder

Store APK files and decompiler output in `APK/` (gitignored). These are
local-only reverse-engineering inputs that must never be upstreamed.

Official APK files, extracted APK contents, and decompiled app files must never
be committed. Commit durable findings as summaries under
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw) `reverse_engineered/`
instead of committing proprietary app artifacts or generated decompiler output.

If an agent finds something useful in the decompiled APK, summarize it in
`DEVELOPMENT.md`, `TESTING.md`, or under
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw) `reverse_engineered/`.

Authoritative external references:

- Home Assistant developer docs:
  https://developers.home-assistant.io/docs/development_index/
- Hassfest for custom components:
  https://developers.home-assistant.io/blog/2020/04/16/hassfest/
- Daye Power robotic mower app:
  https://play.google.com/store/apps/details?id=com.dayepower.dayeappleaf

## Project

This repository contains a Home Assistant custom integration for Grouw BLE
lawn mowers controlled by the Daye Power app (`com.dayepower.dayeappleaf`).
BLE communication is delegated to the published `pygrouw` package.

The integration lives in:

```text
custom_components/grouw_ble_mower/
```

## Home Assistant Rules For This Repo

- Use Home Assistant's Bluetooth manager. Do not create a standalone scanner.
- Resolve connectable devices with
  `bluetooth.async_ble_device_from_address(..., connectable=True)`.
- Pass HA-resolved connectable devices to `pygrouw` through its
  `device_provider` hook.
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
  receive concurrent connect/write/read flows. Preserve the coordinator lock
  even though `pygrouw` also serializes client requests.
- Implement and preserve config entry unloading. Clean up services,
  subscriptions, callbacks, and connections.
- Keep diagnostics useful but redacted. Do not expose serial numbers, addresses,
  credentials, or user-sensitive fields unnecessarily.
- Prefer options for command behavior tweaks; connection-critical values belong
  in config entry data.
- Use translations for user-facing config/options/entity text.

## Current BLE Protocol Facts

The durable protocol summary is under
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw) `reverse_engineered/`.
Use only the Daye app (`com.dayepower.dayeappleaf`) or redacted real-hardware
captures as protocol facts. Do not reintroduce facts from the old
`com.cj.lawnmower` app.

Do not change BLE constants, payload encoders, parsers, or connection flow in
this integration. Those belong in
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw). When protocol facts
change, update the relevant `reverse_engineered/` files and add/update
`pyGrouw` tests there. Then update this integration only for the HA-facing
behavior or API usage.

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
custom_components/grouw_ble_mower/translations/
README.md
README_sv.md
README_da.md
DEVELOPMENT.md
TESTING.md
tests/
```

## Translations And Documentation

- Keep `README.md`, `README_sv.md`, and `README_da.md` aligned when changing
  user-facing setup, features, validation notes, or service examples.
- Add or update files in `custom_components/grouw_ble_mower/translations/`
  for user-facing config, options, entity, and service text.
- Keep `strings.json` aligned with service metadata and English source text.
- Prefer concise translations over literal phrasing when Home Assistant UI
  text would otherwise feel awkward.

## Testing

Run the commands in `TESTING.md` before handing off changes. If commands,
dependencies, or test assumptions change, update `TESTING.md` and
`requirements-test.txt` in the same patch. Keep the GitHub Actions workflows in
`.github/workflows/` working on push and pull request unless the user explicitly
asks to remove CI.

This integration's tests should verify Home Assistant behavior:

- config flow, reauth, and discovery filtering through `pygrouw` helpers
- coordinator cooldowns, serialization, state handling, and exception mapping
- entity availability, unique IDs, device info, and activity mapping
- service routing and validation

BLE transport, notification parsing, DYM/BlueKey protocol behavior, and
client-level request handling should be tested in
[Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw).

## Style

- Keep changes scoped to the integration unless the task says otherwise.
- Prefer small, typed helper functions over broad rewrites.
- Do not hand-roll parsing with fragile string operations when structured JSON
  or byte handling is available.
- Do not introduce network/cloud behavior; this integration is local BLE via
  `pygrouw`.
- Use `rg` for searching.
- Avoid touching decompiled APK output under `APK/` unless needed for protocol
  research, and summarize findings under
  [Bjorkan/pyGrouw](https://github.com/Bjorkan/pyGrouw) `reverse_engineered/`.
- Never commit or upstream APK files, extracted APK trees, decompiled Java,
  smali, native-library dumps, or generated decompiler output.
