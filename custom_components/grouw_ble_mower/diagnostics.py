"""Diagnostics support for Grouw Mower."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import GrouwMowerCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: GrouwMowerCoordinator | None = hass.data[entry.domain].get(entry.entry_id)
    data = asdict(coordinator.data) if coordinator and coordinator.data else None
    if data is not None:
        data.pop("address", None)
        data.pop("serial", None)
        data.pop("raw", None)
    return {
        "entry": {
            "title": entry.title,
            "data_keys": sorted(entry.data.keys()),
            "options": dict(entry.options),
        },
        "state": data,
    }
