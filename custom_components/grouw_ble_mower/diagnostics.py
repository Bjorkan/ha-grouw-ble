"""Diagnostics support for Grouw Mower."""
from __future__ import annotations

from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import GrouwMowerCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-safe state, routing, and failure diagnostics."""
    coordinator: GrouwMowerCoordinator | None = hass.data[entry.domain].get(entry.entry_id)
    data = asdict(coordinator.data) if coordinator and coordinator.data else None
    if data is not None:
        data.pop("address", None)
        data.pop("serial", None)
        data.pop("raw", None)

    candidates: list[dict[str, Any]] = []
    discovered = getattr(bluetooth, "async_discovered_service_info", None)
    if discovered is not None and coordinator is not None:
        for info in discovered(hass, connectable=True):
            if str(getattr(info, "address", "")).upper() != coordinator.address:
                continue
            candidates.append(
                {
                    "source": getattr(info, "source", None),
                    "rssi": getattr(info, "rssi", None),
                    "connectable": getattr(info, "connectable", None),
                }
            )

    reachability = None
    reachability_fn = getattr(bluetooth, "async_address_reachability_diagnostics", None)
    intent_type = getattr(bluetooth, "BluetoothReachabilityIntent", None)
    if reachability_fn is not None and intent_type is not None and coordinator is not None:
        reachability = reachability_fn(
            hass, coordinator.address, intent_type.CONNECTION
        )

    try:
        pygrouw_version = version("pygrouw")
    except PackageNotFoundError:
        pygrouw_version = "unknown"

    return {
        "pygrouw_version": pygrouw_version,
        "entry": {
            "title": entry.title,
            "data_keys": sorted(entry.data.keys()),
            "options": dict(entry.options),
        },
        "state": data,
        "bluetooth": {
            "candidates": candidates,
            "reachability": reachability,
        },
        "coordinator": coordinator.diagnostics_snapshot() if coordinator else None,
    }
