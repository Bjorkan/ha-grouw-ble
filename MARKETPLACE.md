# Home Assistant Marketplace release checklist

The installable integration is in `custom_components/grouw_ble_mower/`.
[`pyGrouw`](https://github.com/Bjorkan/pyGrouw) is a separately released
[PyPI library](https://pypi.org/project/pygrouw/), **not** a Marketplace entry.

Official guidance:
- [Publish a custom integration](https://contributors.home-assistant.io/marketplace/guides/integrations/)
- [Marketplace validation](https://contributors.home-assistant.io/marketplace/reference/validation/)
- [Releases and updates](https://contributors.home-assistant.io/marketplace/guides/releases/)
- [Catalog submission](https://contributors.home-assistant.io/marketplace/guides/catalog/)

## Preparation

1. Keep `hacs.json` in the root and the installable manifest, complete
   `translations/en.json`, and `brand/icon.png` inside the integration
   folder. No second integration domain should be added.
2. Keep `pygrouw` pinned to a tested, **published** version on PyPI.
   Release changes to the library before bumping this requirement.
3. Keep versions in `manifest.json`, `pyproject.toml` and `uv.lock`
   aligned. The integration's new GitHub release tag must match its manifest
   version (optionally with a leading `v`).
4. Check the `homeassistant` minimum in `hacs.json` against actual
   supported releases. Do not raise it only because Marketplace starts in
   2026.11: earlier versions can still install through HACS.
5. Ensure GitHub repository settings include a description, topics and
   enabled issues.
6. Run the [HACS action](https://github.com/Bjorkan/ha-grouw-ble/actions/workflows/validate_hacs.yaml)
   without ignored checks, [hassfest](https://github.com/Bjorkan/ha-grouw-ble/actions/workflows/validate_hassfest.yaml),
   unit tests, and (when possible) installation testing on actual hardware.

## Release and public catalog

1. Merge to `main`, then publish a **GitHub Release** with release notes
   using the manifest version. A tag without a published release is not
   sufficient for catalog submission. Verify checks on the released code.
2. To appear in the public Marketplace, open a separate pull request against
   [`hacs/default`](https://github.com/hacs/default) adding
   `Bjorkan/ha-grouw-ble` alphabetically to the `integration` file.
   Complete its template with links to the release and passing HACS/hassfest
   checks. Do not mark checks as passing before they actually pass.
3. Catalog review can take time. Meanwhile users can add the
   [Marketplace custom repository](https://my.home-assistant.io/redirect/marketplace_repository/?owner=Bjorkan&repository=ha-grouw-ble&category=integration)
   directly. The existing [HACS repository link](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bjorkan&repository=ha-grouw-ble&category=integration)
   also works on older Home Assistant and redirects to Marketplace on 2026.11+.

Only `ha-grouw-ble` is submitted to the Marketplace catalog; the protocol
implementation stays in `pyGrouw`.
