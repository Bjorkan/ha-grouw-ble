"""Test Marketplace package metadata and brand assets without optional dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import tomllib

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "grouw_ble_mower"


def _load_json(path: Path) -> dict:
    """Load checked-in JSON data."""
    return json.loads(path.read_text(encoding="utf-8"))


def _png_size(name: str) -> tuple[int, int]:
    """Read the PNG dimensions directly from IHDR."""
    data = (INTEGRATION / "brand" / name).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    assert data[24:26] == b"\x08\x06"  # RGBA 8-bit
    return struct.unpack(">II", data[16:24])


def test_marketplace_metadata() -> None:
    """One installable device integration with versioned PyPI dependency."""
    hacs = _load_json(ROOT / "hacs.json")
    manifest = _load_json(INTEGRATION / "manifest.json")

    assert hacs["name"] == manifest["name"] == "Grouw Mower"
    assert hacs["homeassistant"] == "2024.9.0"
    assert set(hacs) == {"name", "homeassistant"}
    assert manifest["domain"] == INTEGRATION.name
    assert manifest["config_flow"] is True
    assert manifest["integration_type"] == "device"
    assert manifest["iot_class"] == "local_polling"
    assert manifest["codeowners"] == ["@Bjorkan"]
    assert manifest["categories"] == ["garden_plants"]
    assert manifest["requirements"] == ["pygrouw==0.1.4.1"]
    assert "pygrouw" in manifest["loggers"]
    assert manifest["documentation"].startswith(
        "https://github.com/Bjorkan/ha-grouw-ble"
    )
    assert manifest["issue_tracker"] == "https://github.com/Bjorkan/ha-grouw-ble/issues"
    assert (INTEGRATION / "__init__.py").is_file()

    with (ROOT / "pyproject.toml").open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    assert manifest["version"] == version == "1.3.1"


def test_marketplace_brand_dimensions() -> None:
    """Standard and high-resolution images match Home Assistant's brand spec."""
    assert _png_size("icon.png") == (256, 256)
    assert _png_size("icon@2x.png") == (512, 512)
    logo = _png_size("logo.png")
    hidpi = _png_size("logo@2x.png")
    assert logo == (512, 171)
    assert hidpi == (1024, 341)
    assert 128 <= min(logo) <= 256
    assert 256 <= min(hidpi) <= 512


def test_english_fallback_translation() -> None:
    """Custom integrations install precompiled translations, not Lokalise sources."""
    locales = INTEGRATION / "translations"
    english = _load_json(locales / "en.json")
    assert english["config"]
    assert english["entity"]
    for name in ("da.json", "sv.json"):
        assert _load_json(locales / name)["config"]
