"""DataUpdateCoordinator for Grouw Mower."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pygrouw import (
    GrouwBleAuthenticationError,
    GrouwBleError,
    GrouwBleMowerClient,
    GrouwMower,
    MowerState,
)
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
        self.client = GrouwBleMowerClient(
            self.address,
            self.device_name,
            pin,
            device_provider=self._async_ble_device_from_address,
        )
        self.mower = GrouwMower(self.client)
        self._last_state: MowerState | None = None
        self._ble_lock = asyncio.Lock()
        self._pending_commands = 0
        self._last_command_time: datetime | None = None
        self._last_failure_time: datetime | None = None

        self.multi_area: dict | None = None
        self.mower_settings: dict | None = None
        self.work_time_starts: list | None = None
        self.work_time_durations: list | None = None

    def _async_ble_device_from_address(self) -> Any:
        """Resolve the current connectable BLE device through Home Assistant."""
        return bluetooth.async_ble_device_from_address(
            self.hass,
            self.address,
            connectable=True,
        )

    def _record_ble_failure(self) -> datetime:
        """Record a BLE failure timestamp and return it."""
        self._last_failure_time = datetime.now(timezone.utc)
        return self._last_failure_time

    def _async_start_reauth(self) -> None:
        """Start a Home Assistant reauth flow when supported."""
        async_start_reauth = getattr(self.config_entry, "async_start_reauth", None)
        if async_start_reauth is not None:
            async_start_reauth(self.hass)

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
                raise UpdateFailed("Poll deferred for BLE failure backoff")

        if self._pending_commands:
            _LOGGER.debug(
                "[%s] skipping poll: %s manual command(s) pending",
                self.address, self._pending_commands
            )
            if self._last_state is not None:
                return self._last_state
            raise UpdateFailed("No data yet and poll deferred for pending command")

        if self._ble_lock.locked():
            _LOGGER.debug("[%s] skipping poll: BLE transaction already active", self.address)
            if self._last_state is not None:
                return self._last_state
            raise UpdateFailed("No data yet and poll deferred for active BLE transaction")

        try:
            async with self._ble_lock:
                _LOGGER.debug("[%s] BLE lock acquired for poll", self.address)
                if self._last_state is not None:
                    self.mower.state = self._last_state
                state = await self.mower.async_update()
        except GrouwBleAuthenticationError as err:
            self._record_ble_failure()
            raise ConfigEntryAuthFailed(str(err)) from err
        except GrouwBleError as err:
            self._record_ble_failure()
            raise UpdateFailed(str(err)) from err

        self._last_failure_time = None
        self._last_state = state
        return state

    async def async_send_command(self, command: str) -> None:
        """Send a mower command and refresh state."""
        self._pending_commands += 1
        try:
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
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    state = await self.mower.async_command(command)
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            self._last_state = state
            self.async_set_updated_data(state)
        finally:
            self._pending_commands -= 1

    async def async_change_pin(
        self, new_pin: str, old_pin: str | None = None
    ) -> dict[str, Any]:
        """Change the mower PIN."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] change_pin waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug(
                        "[%s] BLE lock acquired for change_pin", self.address
                    )
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    response = await self.client.async_change_pin(new_pin, old_pin)
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            return response
        finally:
            self._pending_commands -= 1

    async def async_get_multi_area(self) -> dict[str, Any]:
        """Read multi-area settings."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] get_multi_area waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug(
                        "[%s] BLE lock acquired for get_multi_area", self.address
                    )
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    response = await self.client.async_get_multi_area()
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            self.multi_area = response.get("multi_area")
            state = self.mower.state
            self._last_state = state
            self.async_set_updated_data(state)
            return response
        finally:
            self._pending_commands -= 1

    async def async_set_multi_area(
        self,
        area2_percentage: int,
        area2_distance: int,
        area3_percentage: int,
        area3_distance: int,
    ) -> dict[str, Any]:
        """Write multi-area settings and verify."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] set_multi_area waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug(
                        "[%s] BLE lock acquired for set_multi_area", self.address
                    )
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    response = await self.client.async_set_multi_area(
                        area2_percentage=area2_percentage,
                        area2_distance=area2_distance,
                        area3_percentage=area3_percentage,
                        area3_distance=area3_distance,
                    )
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            self.multi_area = response.get("multi_area")
            state = self.mower.state
            self._last_state = state
            self.async_set_updated_data(state)
            return response
        finally:
            self._pending_commands -= 1

    async def async_get_mower_settings(self) -> dict[str, Any]:
        """Read mower settings."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] get_mower_settings waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug(
                        "[%s] BLE lock acquired for get_mower_settings", self.address
                    )
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    response = await self.client.async_get_mower_settings()
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            self.mower_settings = response.get("mower_settings")
            state = self.mower.state
            self._last_state = state
            self.async_set_updated_data(state)
            return response
        finally:
            self._pending_commands -= 1

    async def async_set_mower_settings(
        self,
        mow_in_rain: bool,
        boundary_cut: bool,
        helix: bool,
        rain_delay_hours: int,
        rain_delay_minutes: int,
        unknown_setting: bool = False,
    ) -> dict[str, Any]:
        """Write mower settings and verify."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] set_mower_settings waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug(
                        "[%s] BLE lock acquired for set_mower_settings", self.address
                    )
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    response = await self.client.async_set_mower_settings(
                        mow_in_rain=mow_in_rain,
                        boundary_cut=boundary_cut,
                        helix=helix,
                        rain_delay_hours=rain_delay_hours,
                        rain_delay_minutes=rain_delay_minutes,
                        unknown_setting=unknown_setting,
                    )
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            self.mower_settings = response.get("mower_settings")
            state = self.mower.state
            self._last_state = state
            self.async_set_updated_data(state)
            return response
        finally:
            self._pending_commands -= 1

    async def async_get_work_times(self) -> dict[str, Any]:
        """Read work time schedule."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] get_work_times waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug(
                        "[%s] BLE lock acquired for get_work_times", self.address
                    )
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    response = await self.client.async_get_work_times()
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            self.work_time_starts = response.get("work_time_starts")
            self.work_time_durations = response.get("work_time_durations")
            state = self.mower.state
            self._last_state = state
            self.async_set_updated_data(state)
            return response
        finally:
            self._pending_commands -= 1

    async def async_set_work_times(
        self,
        starts: list[tuple[int, int]],
        durations: list[tuple[int, int]],
    ) -> dict[str, Any]:
        """Write work time schedule and verify."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] set_work_times waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug(
                        "[%s] BLE lock acquired for set_work_times", self.address
                    )
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    response = await self.client.async_set_work_times(starts, durations)
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            self.work_time_starts = response.get("work_time_starts")
            self.work_time_durations = response.get("work_time_durations")
            state = self.mower.state
            self._last_state = state
            self.async_set_updated_data(state)
            return response
        finally:
            self._pending_commands -= 1

    async def async_send_raw_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a raw BLE payload for protocol validation."""
        self._pending_commands += 1
        try:
            try:
                if self._ble_lock.locked():
                    _LOGGER.debug(
                        "[%s] raw BLE payload waiting for active BLE transaction",
                        self.address
                    )
                async with self._ble_lock:
                    _LOGGER.debug("[%s] BLE lock acquired for raw BLE payload", self.address)
                    if self._last_state is not None:
                        self.mower.state = self._last_state
                    message = await self.mower.async_send_raw_json(payload)
            except GrouwBleAuthenticationError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                now = datetime.now(timezone.utc)
                self._last_command_time = now
                self._last_failure_time = now
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(timezone.utc)
            self._last_failure_time = None
            state = self.mower.state
            self._last_state = state
            self.async_set_updated_data(state)
            return message
        finally:
            self._pending_commands -= 1
