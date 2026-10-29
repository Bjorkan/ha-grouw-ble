# Marketplace publishing audit — Grouw Mower

**Audited 2026-10-29.** This repository installs a single Home Assistant
custom integration, `grouw_ble_mower`, through Marketplace or legacy HACS.
The separate [pyGrouw](https://github.com/Bjorkan/pyGrouw) repository provides
the `pygrouw` PyPI BLE library, **not** a Marketplace catalog entry.

## Documentation reviewed

- [Marketplace overview](https://contributors.home-assistant.io/marketplace/)
- [How it works and HACS migration](https://contributors.home-assistant.io/marketplace/how-it-works/)
- [Custom integrations guide](https://contributors.home-assistant.io/marketplace/guides/integrations/)
- [Repository structure](https://contributors.home-assistant.io/marketplace/reference/repository-structure/)
- [hacs.json key reference](https://contributors.home-assistant.io/marketplace/reference/hacs-json/)
- [Validation checks](https://contributors.home-assistant.io/marketplace/reference/validation/)
- [Releases and updates](https://contributors.home-assistant.io/marketplace/guides/releases/)
- [Public catalog submission](https://contributors.home-assistant.io/marketplace/guides/catalog/)
- [Core manifest specification](https://contributors.home-assistant.io/core/integrations/manifest/)
- [Integration categories](https://contributors.home-assistant.io/core/integrations/categories/)
- [Brand image requirements](https://contributors.home-assistant.io/core/integrations/brands/)
- [Custom translation requirements](https://contributors.home-assistant.io/core/integrations/translations/)
- [HACS publishing](https://hacs.xyz/docs/publish/start/) and
  [integration packaging](https://hacs.xyz/docs/publish/integration/)

Marketplace docs for dashboard plugins, themes, templates and blueprints were
also checked for applicability; those **do not apply** to this BLE integration.
This is not a security or quality audit of *all* Home Assistant Core APIs or
the mower BLE protocol.

## Requirements verified in the repository

| Topic | Verified choice / requirement |
| --- | --- |
| Single component | `custom_components/grouw_ble_mower/` with Python code and assets; no secondary Marketplace domain |
| Domain continuity | `grouw_ble_mower` unchanged to preserve existing HA installations and entity identifiers |
| Installable package | `__init__.py`, manifest, config flow, platforms, locales and brand images inside installable folder |
| `hacs.json` | Root name and minimum HA version 2024.9.0; no irrelevant layout flags or ignored legacy key `render_readme` |
| Version | Manifest `1.3.1` matches `pyproject.toml` and `uv.lock`; publish GitHub Release with same tag |
| Required manifest | HTTPS documentation, issue tracker, code owner, domain/name, version, sorted manifest keys |
| Integration type | `device`: one Grouw BLE mower per config entry |
| IoT class | `local_polling` consistent with BLE coordinator polling |
| Category | `garden_plants` is the documented category for robotic lawn mowers |
| BLE discovery | Service UUID/name matchers and connectable support via HA Bluetooth manager |
| Library dependency | Published `pygrouw==0.1.4.1` from PyPI; keep BLE protocol in pyGrouw |
| Debug log association | `loggers=["pygrouw"]` for dependency logs |
| Translations | Complete `translations/en.json` with Swedish/Danish locales, not built from Lokalise |
| Brand icon | `brand/icon.png` 256×256 and `icon@2x.png` 512×512, PNG RGBA |
| Brand logo | `brand/logo.png` 512×171 and `logo@2x.png` 1024×341; both short sides in documented range |
| User file updates | Integration does not write persistent user-owned files into its own install tree; no `persistent_directory` |
| Standard releases | No `zip_release`, `filename` or `content_in_root` needed; default source archive layout |
| My Home Assistant links | Marketplace custom repository link, backward-compatible HACS link, and config flow start |
| Restarts | Config-flow first install can load immediately; loaded integration updates/removals require restart |
| Country | No Sweden-only cloud dependency; removed `country=SE` HACS catalog filter |
| GitHub | Repository public, not archived, MIT license, description/topics, issues enabled, README |
| Core namespace collision | Checked `grouw_ble_mower` is not a built-in integration in the examined Home Assistant Core branch |
| Marketplace vs HACS | Existing HACS installations should retain the same domain and default source archive layout |

`strings.json` exists for contributors but is **not required** by Marketplace
and must not be relied on as the installed integration's translation source;
Home Assistant reads the included `translations/*.json` files.

## Required CI and manual checks

- [ ] [HACS action](https://github.com/Bjorkan/ha-grouw-ble/actions/workflows/validate_hacs.yaml) succeeds on **final commit**, `category: integration`, **no ignored checks**. Its ten checks cover repository issues, info, topics, description, archive status, license, manifest, brand images, integration categories and `hacs.json`.
- [ ] [Hassfest](https://github.com/Bjorkan/ha-grouw-ble/actions/workflows/validate_hassfest.yaml) succeeds on **final commit**, including metadata and translations.
- [ ] [Unit tests, Ruff and package regression tests](https://github.com/Bjorkan/ha-grouw-ble/actions/workflows/test_unit.yaml) succeed on **final commit**.
- [ ] Test fresh Marketplace installation **from a published GitHub Release**, automatic PyPI dependency installation, Bluetooth discovery and manual setup on a real supported mower.
- [ ] Verify `homeassistant: 2024.9.0` with a **real runtime** before claiming full backwards compatibility. The former `2024.1.0` minimum was invalid: this integration imports `LawnMowerActivity.RETURNING`, introduced in [Core 2024.9](https://developers.home-assistant.io/blog/2024/08/23/lawn-mower-activity-returning/). Confirmed absent in Core 2024.1 and present in Core 2024.9 source.
- [ ] Test integration compatibility with an upcoming Home Assistant beta; monitor core API deprecation announcements.

## Publishing GitHub Release 1.3.1

1. Merge the integration PR after validating the final commit; do not merge
   just because an earlier revision passed.
2. Publish a **full GitHub Release** for `1.3.1` (or `v1.3.1`), with notes,
   from the merged commit. A tag without a published release is **insufficient**
   for the public catalog. `pygrouw==0.1.4.1` must be available from PyPI.
3. Verify the published release's source archive includes both `hacs.json` and
   the complete `custom_components/grouw_ble_mower/` subtree. No ZIP asset is
   needed with the default repository layout.
4. Verify green HACS and hassfest checks on the **published SHA**, not only on
   a PR merge ref. Test update behavior with an existing HACS-installed copy.

## Submitting to the public Marketplace catalog — separate PR

1. Only the owner or a major contributor should submit. Fork
   [`hacs/default`](https://github.com/hacs/default) into a **personal**
   account; branch from `master`.
2. Add **`Bjorkan/ha-grouw-ble`** (not pyGrouw) alphabetically to the JSON list
   in the `integration` file, without deleting/reordering existing entries.
3. Complete the upstream PR template with truthful checkboxes and links to the
   **published release**, a passing HACS action with no `ignore`, and a passing
   hassfest run. **Do not request reviewers.** Incomplete/incorrect templates
   can be closed without notice.
4. Upstream review checks: brands, manifest, HACS action, `hacs.json`, archive
   status, releases, ownership, GitHub metadata and sorted/valid JSON.
5. Review may take months. Until catalog acceptance, users can install with
   [Marketplace repository My link](https://my.home-assistant.io/redirect/marketplace_repository/?owner=Bjorkan&repository=ha-grouw-ble&category=integration).
   The older [HACS repository My link](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bjorkan&repository=ha-grouw-ble&category=integration)
   opens HACS on older HA and Marketplace on HA 2026.11+.
6. If later renamed, transferred, archived or removed, use the published
   catalog update/removal procedure; do not just delete a listed repository.

**Still unverified:** Home Assistant Marketplace installation on a running HA
instance, physical BLE mower operation, claimed 2024.9 version floor, new
GitHub Release 1.3.1 (not yet published) and upstream catalog approval.
Automated passing checks alone cannot prove any of these.
