"""DataUpdateCoordinator for Grouw / Daye BLE Mower."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ble_client import GrouwBleError, GrouwBleMowerClient
from .ble_protocol import MowerState, state_from_message
from .const import (
    DEFAULT_BLE_BACKOFF_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

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
        pin: str = "",
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
        self.pin = pin
        self.client = GrouwBleMowerClient(hass, self.address, self.device_name, pin)
        self._last_state: MowerState | None = None
        self._ble_lock = asyncio.Lock()
        self._last_command_time: datetime | None = None
        self._last_failure_time: datetime | None = None

    async def _async_update_data(self) -> MowerState:
        """Fetch latest mower data."""
        now = datetime.now(timezone.utc)

        if self._last_command_time is not None:
            since_command = now - self._last_command_time
            if since_command < DEFAULT_UPDATE_INTERVAL * 0.5:
                _LOGGER.debug(
                    "[%s] skipping poll: manual command %.1fs ago",
                    self.address, since_command.total_seconds()
                )
                if self._last_state is not None:
                    return self._last_state
                raise UpdateFailed("No data yet and poll deferred for command cooldown")

        if self._last_failure_time is not None:
            since_failure = now - self._last_failure_time
            if since_failure < DEFAULT_BLE_BACKOFF_INTERVAL:
                _LOGGER.debug(
                    "[%s] skipping poll: BLE failure %.1fs ago (backoff)",
                    self.address, since_failure.total_seconds()
                )
                if self._last_state is not None:
                    return self._last_state
                raise UpdateFailed("No data yet and poll deferred for failure backoff")

        if self._ble_lock.locked():
            _LOGGER.debug("[%s] skipping poll: BLE transaction already active", self.address)
            if self._last_state is not None:
                return self._last_state
            raise UpdateFailed("No data yet and poll deferred for active BLE transaction")

        try:
            async with self._ble_lock:
                _LOGGER.debug("[%s] BLE lock acquired for poll", self.address)
                message = await self.client.async_get_all_info()
        except GrouwBleError as err:
            self._last_failure_time = now
            raise UpdateFailed(str(err)) from err

        self._last_failure_time = None
        state = state_from_message(self.address, message, self._last_state)
        self._last_state = state
        return state

    async def async_send_command(self, command: str) -> None:
        """Send a mower command and refresh state."""
        self._last_command_time = datetime.now(timezone.utc)
        try:
            if self._ble_lock.locked():
                _LOGGER.debug(
                    "[%s] command %s waiting for active BLE transaction",
                    self.address, command
                )
            async with self._ble_lock:
                _LOGGER.debug(
                    "[%s] BLE lock acquired for command %s",
                    self.address, command
                )
                message = await self.client.async_command(command)
        except GrouwBleError as err:
            self._last_failure_time = datetime.now(timezone.utc)
            raise HomeAssistantError(str(err)) from err

        self._last_failure_time = None
        state = state_from_message(self.address, message, self._last_state)
        self._last_state = state
        self.async_set_updated_data(state)

    async def async_send_raw_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a raw BLE payload for protocol validation."""
        self._last_command_time = datetime.now(timezone.utc)
        try:
            if self._ble_lock.locked():
                _LOGGER.debug(
                    "[%s] raw BLE payload waiting for active BLE transaction",
                    self.address
                )
            async with self._ble_lock:
                _LOGGER.debug("[%s] BLE lock acquired for raw BLE payload", self.address)
                message = await self.client.async_send_raw_json(payload)
        except GrouwBleError as err:
            self._last_failure_time = datetime.now(timezone.utc)
            raise HomeAssistantError(str(err)) from err

        self._last_failure_time = None
        state = state_from_message(self.address, message, self._last_state)
        self._last_state = state
        self.async_set_updated_data(state)
        return message
