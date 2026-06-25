"""Grouw / Daye BLE Mower integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv

from .ble_protocol import redact_daye_message
from .const import CONF_ADDRESS, CONF_PIN, DEFAULT_NAME, DOMAIN, SERVICE_SEND_RAW_JSON
from .coordinator import GrouwMowerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LAWN_MOWER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

SERVICE_SEND_RAW_JSON_SCHEMA = vol.Schema(
    {
        vol.Required("payload"): dict,
        vol.Optional("address"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grouw / Daye BLE Mower from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = GrouwMowerCoordinator(
        hass,
        entry,
        entry.data[CONF_ADDRESS],
        entry.data.get(CONF_NAME, DEFAULT_NAME),
        entry.data.get(CONF_PIN, ""),
    )
    hass.data[DOMAIN][entry.entry_id] = coordinator

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        _LOGGER.debug("Initial BLE refresh failed, continuing with unavailable entities")
        coordinator.data = None
        coordinator.last_update_success = False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _async_register_services(hass)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN] and hass.services.has_service(
            DOMAIN, SERVICE_SEND_RAW_JSON
        ):
            hass.services.async_remove(DOMAIN, SERVICE_SEND_RAW_JSON)
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_JSON):
        return

    async def _handle_send_raw_json(call: ServiceCall) -> None:
        payload: dict[str, Any] = call.data["payload"]
        entry_id = call.data.get("entry_id")
        address = call.data.get("address")

        coordinators: dict[str, GrouwMowerCoordinator] = hass.data.get(DOMAIN, {})
        coordinator: GrouwMowerCoordinator | None = None

        if entry_id:
            coordinator = coordinators.get(entry_id)
        elif address:
            address_upper = address.upper()
            coordinator = next(
                (item for item in coordinators.values() if item.address == address_upper),
                None,
            )
        elif len(coordinators) == 1:
            coordinator = next(iter(coordinators.values()))

        if coordinator is None:
            raise ServiceValidationError(
                "Could not determine target mower. Provide address or entry_id."
            )

        result = await coordinator.async_send_raw_json(payload)
        _LOGGER.info(
            "Raw BLE response from %s: %s",
            coordinator.address,
            redact_daye_message(result),
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_RAW_JSON,
        _handle_send_raw_json,
        schema=SERVICE_SEND_RAW_JSON_SCHEMA,
    )
