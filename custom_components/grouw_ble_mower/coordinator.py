"""DataUpdateCoordinator for Grouw / Daye BLE Mower."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ble_client import GrouwBleError, GrouwBleMowerClient
from .ble_protocol import MowerState, state_from_message
from .const import DEFAULT_NAME, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class GrouwMowerCoordinator(DataUpdateCoordinator[MowerState]):
    """Coordinates polling and BLE command responses."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        address: str,
        name: str | None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{address}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.config_entry = config_entry
        self.address = address.upper()
        self.device_name = name or DEFAULT_NAME
        self.client = GrouwBleMowerClient(hass, self.address, self.device_name)
        self._last_state: MowerState | None = None
        self._ble_lock = asyncio.Lock()

    async def _async_update_data(self) -> MowerState:
        """Fetch latest mower data once the Daye status protocol is known."""
        if self._last_state is not None:
            raise UpdateFailed("Daye BLE status protocol is not confirmed yet")
        raise ConfigEntryNotReady("Daye BLE status protocol is not confirmed yet")

    async def async_send_mode(self) -> None:
        """Reject mode commands until Daye command payloads are confirmed."""
        raise HomeAssistantError(
            "Daye start, pause, and dock command payloads are not confirmed yet"
        )

    async def async_send_raw_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send raw JSON over BLE for protocol validation."""
        try:
            async with self._ble_lock:
                message = await self.client.async_send_raw_json(payload)
        except GrouwBleError as err:
            raise HomeAssistantError(str(err)) from err

        state = state_from_message(self.address, message, self._last_state)
        self._last_state = state
        self.async_set_updated_data(state)
        return message
