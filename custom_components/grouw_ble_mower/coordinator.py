"""DataUpdateCoordinator for Grouw / Daye BLE Mower."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
        self._last_state: MowerState | None = MowerState(
            address=self.address,
            name=self.device_name,
        )
        self._ble_lock = asyncio.Lock()

    async def _async_update_data(self) -> MowerState:
        """Fetch latest mower data."""
        try:
            async with self._ble_lock:
                message = await self.client.async_get_all_info()
        except GrouwBleError as err:
            if self._last_state is not None and self._last_state.last_seen is None:
                return self._last_state
            raise UpdateFailed(str(err)) from err

        state = state_from_message(self.address, message, self._last_state)
        self._last_state = state
        return state

    async def async_send_command(self, command: str) -> None:
        """Send a mower command and refresh state."""
        try:
            async with self._ble_lock:
                message = await self.client.async_command(command)
        except GrouwBleError as err:
            raise HomeAssistantError(str(err)) from err

        state = state_from_message(self.address, message, self._last_state)
        self._last_state = state
        self.async_set_updated_data(state)

    async def async_send_raw_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a raw BLE payload for protocol validation."""
        try:
            async with self._ble_lock:
                message = await self.client.async_send_raw_json(payload)
        except GrouwBleError as err:
            raise HomeAssistantError(str(err)) from err

        state = state_from_message(self.address, message, self._last_state)
        self._last_state = state
        self.async_set_updated_data(state)
        return message
