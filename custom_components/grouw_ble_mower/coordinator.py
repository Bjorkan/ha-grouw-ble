"""DataUpdateCoordinator for Grouw Mower."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import logging
from typing import Any, TypeVar

from pygrouw import (
    GrouwBleAuthenticationError,
    GrouwBleError,
    GrouwBleMowerClient,
    GrouwMower,
    MowerState,
    state_from_message,
)

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COMMAND_CONFIRM_INTERVAL,
    COMMAND_CONFIRM_TIMEOUT,
    COMMAND_MAX_QUEUE_AGE,
    COMMAND_QUEUE_TIMEOUT,
    CONF_PIN,
    DAYE_MODE_IDLE,
    DAYE_MODE_RETURNING,
    DAYE_MOWING_MODE_CODES,
    DEFAULT_BLE_BACKOFF_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    HANDOFF_REFRESH_DELAY,
    STATUS_MAX_AGE,
)

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T")


class GrouwMowerCoordinator(DataUpdateCoordinator[MowerState]):
    """Coordinate status polling, settings traffic, and manual commands."""

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
        self._command_guard = asyncio.Lock()
        self._command_generation = 0
        self._active_command: str | None = None
        self._active_command_task: asyncio.Task[None] | None = None
        self._pending_commands = 0
        self._last_command_time: datetime | None = None
        self._last_command_outcome: str | None = None
        self._last_failure_time: datetime | None = None
        self._last_failure_phase: str | None = None
        self._last_failure_type: str | None = None
        self._last_failure_message: str | None = None
        self._last_communication_time: datetime | None = None
        self._last_route_source: str | None = None
        self._last_route_rssi: int | None = None
        self._route_changed_at: datetime | None = None
        self._handoff_refresh_task: asyncio.Task[None] | None = None
        self._settings_updated_at: dict[str, datetime] = {}

        self.multi_area: dict | None = None
        self.mower_settings: dict | None = None
        self.work_time_starts: list | None = None
        self.work_time_durations: list | None = None

    def _create_task(self, coroutine: Awaitable[_T]) -> asyncio.Task[_T]:
        """Create a tracked Home Assistant task when that API is available."""
        create_task = getattr(self.hass, "async_create_task", None)
        if create_task is not None:
            return create_task(coroutine)
        return asyncio.create_task(coroutine)

    def _async_ble_device_from_address(self) -> Any:
        """Resolve the current connectable BLE device through Home Assistant."""
        device = bluetooth.async_ble_device_from_address(
            self.hass,
            self.address,
            connectable=True,
        )
        if device is not None:
            details = getattr(device, "details", None)
            source: str | None = None
            if isinstance(details, dict):
                value = details.get("source") or details.get("scanner")
                source = str(value) if value is not None else None
            if source is not None and source != self._last_route_source:
                self._last_route_source = source
                self._route_changed_at = datetime.now(UTC)
        return device

    def async_start_bluetooth_tracking(self) -> None:
        """React to mower reappearance and receiver handoff when HA supports it."""
        register_callback = getattr(bluetooth, "async_register_callback", None)
        matcher_type = getattr(bluetooth, "BluetoothCallbackMatcher", None)
        scanning_mode = getattr(bluetooth, "BluetoothScanningMode", None)
        if register_callback is not None and matcher_type is not None and scanning_mode:
            try:
                unsubscribe = register_callback(
                    self.hass,
                    self._async_handle_bluetooth_update,
                    matcher_type(address=self.address),
                    scanning_mode.PASSIVE,
                )
            except RuntimeError:
                _LOGGER.debug(
                    "[%s] Bluetooth manager is not ready; runtime tracking disabled",
                    self.address,
                )
            else:
                async_on_unload = getattr(self.config_entry, "async_on_unload", None)
                if async_on_unload is not None:
                    async_on_unload(unsubscribe)

        track_unavailable = getattr(bluetooth, "async_track_unavailable", None)
        if track_unavailable is not None:
            try:
                unsubscribe = track_unavailable(
                    self.hass,
                    self._async_handle_bluetooth_unavailable,
                    self.address,
                )
            except RuntimeError:
                _LOGGER.debug(
                    "[%s] Bluetooth unavailable tracking could not be registered",
                    self.address,
                )
            else:
                async_on_unload = getattr(self.config_entry, "async_on_unload", None)
                if async_on_unload is not None:
                    async_on_unload(unsubscribe)

    def _async_handle_bluetooth_update(self, service_info: Any, _change: Any) -> None:
        """Debounce a refresh when reachability or the selected source changes."""
        source = getattr(service_info, "source", None)
        rssi = getattr(service_info, "rssi", None)
        source_value = str(source) if source is not None else None
        source_changed = (
            source_value is not None and source_value != self._last_route_source
        )
        if source_value is not None:
            self._last_route_source = source_value
        if isinstance(rssi, int):
            self._last_route_rssi = rssi
        if source_changed:
            self._route_changed_at = datetime.now(UTC)

        if not source_changed and self._last_failure_time is None:
            return
        self._last_failure_time = None
        if self._handoff_refresh_task is None or self._handoff_refresh_task.done():
            self._handoff_refresh_task = self._create_task(
                self._async_refresh_after_handoff()
            )

    def _async_handle_bluetooth_unavailable(self, _service_info: Any) -> None:
        """Record that Home Assistant no longer has a current BLE route."""
        self._record_ble_failure("unavailable", UpdateFailed("Mower not advertising"))

    async def _async_refresh_after_handoff(self) -> None:
        """Refresh once after advertisements have stabilized on a new receiver."""
        await asyncio.sleep(HANDOFF_REFRESH_DELAY)
        try:
            await self.async_request_refresh()
        except (ConfigEntryAuthFailed, UpdateFailed):
            _LOGGER.debug("[%s] handoff-triggered refresh failed", self.address)

    def _record_ble_failure(self, phase: str, error: BaseException) -> datetime:
        """Record a BLE failure with phase and typed diagnostic metadata."""
        now = datetime.now(UTC)
        self._last_failure_time = now
        self._last_failure_phase = phase
        self._last_failure_type = type(error).__name__
        self._last_failure_message = str(error)
        return now

    def _record_communication(self) -> None:
        self._last_communication_time = datetime.now(UTC)

    def _async_start_reauth(self) -> None:
        """Start a Home Assistant reauth flow when supported."""
        async_start_reauth = getattr(self.config_entry, "async_start_reauth", None)
        if async_start_reauth is not None:
            async_start_reauth(self.hass)

    def status_is_fresh(self, max_age=STATUS_MAX_AGE) -> bool:
        """Return whether a validated status response is recent enough."""
        state = self.data
        if state is None or state.last_seen is None or not self.last_update_success:
            return False
        return datetime.now(UTC) - state.last_seen <= max_age

    async def _async_update_data(self) -> MowerState:
        """Fetch a fresh status packet from the mower."""
        now = datetime.now(UTC)
        if self._last_failure_time is not None:
            since_failure = now - self._last_failure_time
            if since_failure < DEFAULT_BLE_BACKOFF_INTERVAL:
                raise UpdateFailed("Poll deferred for BLE failure backoff")
        if self._pending_commands:
            raise UpdateFailed("Poll deferred for pending command")
        if self._ble_lock.locked():
            raise UpdateFailed("Poll deferred for active BLE transaction")

        try:
            async with self._ble_lock:
                if self._last_state is not None:
                    self.mower.state = self._last_state
                state = await self.mower.async_update()
        except GrouwBleAuthenticationError as err:
            self._record_ble_failure("poll_auth", err)
            raise ConfigEntryAuthFailed(str(err)) from err
        except GrouwBleError as err:
            self._record_ble_failure("poll", err)
            raise UpdateFailed(str(err)) from err

        self._last_failure_time = None
        self._last_failure_phase = None
        self._last_failure_type = None
        self._last_failure_message = None
        self._record_communication()
        self._last_state = state
        return state

    async def async_send_command(self, command: str) -> None:
        """Send the latest desired command with bounded queue semantics."""
        async with self._command_guard:
            if (
                self._active_command == command
                and self._active_command_task is not None
                and not self._active_command_task.done()
            ):
                task = self._active_command_task
            else:
                self._command_generation += 1
                generation = self._command_generation
                queued_at = asyncio.get_running_loop().time()
                task = self._create_task(
                    self._async_execute_command(command, generation, queued_at)
                )
                self._active_command = command
                self._active_command_task = task

        try:
            await asyncio.shield(task)
        finally:
            async with self._command_guard:
                if self._active_command_task is task and task.done():
                    self._active_command = None
                    self._active_command_task = None

    async def _async_write_command(self, command: str) -> MowerState:
        """Write a command using the richest pyGrouw API available."""
        result_method = getattr(self.client, "async_command_result", None)
        if result_method is None:
            return await self.mower.async_command(command)
        result = await result_method(command)
        state = state_from_message(self.address, result.status, self.mower.state)
        self.mower.state = state
        return state

    async def _async_execute_command(
        self, command: str, generation: int, queued_at: float
    ) -> None:
        self._pending_commands += 1
        lock_acquired = False
        try:
            try:
                async with asyncio.timeout(COMMAND_QUEUE_TIMEOUT):
                    await self._ble_lock.acquire()
                lock_acquired = True
            except TimeoutError as err:
                self._last_command_outcome = "queue_timeout"
                raise HomeAssistantError(
                    f"Command {command} expired while waiting for Bluetooth"
                ) from err

            age = asyncio.get_running_loop().time() - queued_at
            if age > COMMAND_MAX_QUEUE_AGE:
                self._last_command_outcome = "expired"
                raise HomeAssistantError(
                    f"Command {command} expired before it was sent"
                )
            if generation != self._command_generation:
                self._last_command_outcome = "superseded"
                raise HomeAssistantError(
                    f"Command {command} was superseded by a newer request"
                )

            if self._last_state is not None:
                self.mower.state = self._last_state
            try:
                state = await self._async_write_command(command)
                self._record_communication()
                self._last_state = state
                self.async_set_updated_data(state)
                state = await self._async_confirm_command(command, state)
            except GrouwBleAuthenticationError as err:
                self._record_ble_failure("command_auth", err)
                self._async_start_reauth()
                raise HomeAssistantError(
                    "Mower PIN authentication failed; reauthentication is required"
                ) from err
            except GrouwBleError as err:
                self._record_ble_failure("command", err)
                raise HomeAssistantError(str(err)) from err

            self._last_command_time = datetime.now(UTC)
            self._last_command_outcome = "confirmed"
            self._last_failure_time = None
            self._last_state = state
            self.async_set_updated_data(state)
        finally:
            if lock_acquired:
                self._ble_lock.release()
            self._pending_commands -= 1

    def _command_is_confirmed(self, command: str, state: MowerState) -> bool:
        if command in {"start", "resume"}:
            return state.mode in DAYE_MOWING_MODE_CODES and state.station is not True
        if command == "pause":
            return state.mode == DAYE_MODE_IDLE
        if command == "dock":
            return state.station is True or state.mode == DAYE_MODE_RETURNING
        return False

    async def _async_confirm_command(
        self, command: str, state: MowerState
    ) -> MowerState:
        """Poll until the requested action is observed or the deadline expires."""
        if self._command_is_confirmed(command, state):
            return state
        deadline = asyncio.get_running_loop().time() + COMMAND_CONFIRM_TIMEOUT
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(COMMAND_CONFIRM_INTERVAL)
            state = await self.mower.async_update()
            self._record_communication()
            self._last_state = state
            self.async_set_updated_data(state)
            if self._command_is_confirmed(command, state):
                return state
        self._last_command_time = datetime.now(UTC)
        self._last_command_outcome = "unconfirmed"
        raise HomeAssistantError(
            f"Command {command} was written, but the requested mower state "
            "was not confirmed"
        )

    async def _async_run_non_status_operation(
        self,
        phase: str,
        operation: Callable[[], Awaitable[_T]],
    ) -> _T:
        """Run a settings operation without publishing stale status as fresh."""
        self._pending_commands += 1
        try:
            try:
                async with asyncio.timeout(COMMAND_QUEUE_TIMEOUT):
                    await self._ble_lock.acquire()
            except TimeoutError as err:
                raise HomeAssistantError(
                    f"{phase} timed out while waiting for Bluetooth"
                ) from err
            try:
                result = await operation()
            finally:
                self._ble_lock.release()
        except GrouwBleAuthenticationError as err:
            self._record_ble_failure(f"{phase}_auth", err)
            self._async_start_reauth()
            raise HomeAssistantError(
                "Mower PIN authentication failed; reauthentication is required"
            ) from err
        except GrouwBleError as err:
            self._record_ble_failure(phase, err)
            raise HomeAssistantError(str(err)) from err
        finally:
            self._pending_commands -= 1

        self._record_communication()
        self._settings_updated_at[phase] = datetime.now(UTC)
        return result

    def _async_notify_non_status_update(self) -> None:
        """Notify settings entities without publishing status as fresh."""
        update_listeners = getattr(self, "async_update_listeners", None)
        if update_listeners is not None:
            update_listeners()

    async def async_change_pin(self, new_pin: str) -> dict[str, Any]:
        response = await self._async_run_non_status_operation(
            "change_pin", lambda: self.client.async_change_pin(new_pin)
        )
        self.pin = new_pin
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_PIN: new_pin},
        )
        self._async_notify_non_status_update()
        return response

    async def async_get_multi_area(self) -> dict[str, Any]:
        response = await self._async_run_non_status_operation(
            "get_multi_area", self.client.async_get_multi_area
        )
        self.multi_area = response.get("multi_area")
        self._async_notify_non_status_update()
        return response

    async def async_set_multi_area(
        self,
        area2_percentage: int,
        area2_distance: int,
        area3_percentage: int,
        area3_distance: int,
    ) -> dict[str, Any]:
        response = await self._async_run_non_status_operation(
            "set_multi_area",
            lambda: self.client.async_set_multi_area(
                area2_percentage=area2_percentage,
                area2_distance=area2_distance,
                area3_percentage=area3_percentage,
                area3_distance=area3_distance,
            ),
        )
        self.multi_area = response.get("multi_area")
        self._async_notify_non_status_update()
        return response

    async def async_get_mower_settings(self) -> dict[str, Any]:
        response = await self._async_run_non_status_operation(
            "get_mower_settings", self.client.async_get_mower_settings
        )
        self.mower_settings = response.get("mower_settings")
        self._async_notify_non_status_update()
        return response

    async def async_set_mower_settings(
        self,
        mow_in_rain: bool,
        boundary_cut: bool,
        helix: bool,
        rain_delay_hours: int,
        rain_delay_minutes: int,
        unknown_setting: bool | None = None,
    ) -> dict[str, Any]:
        if unknown_setting is None:
            current = self.mower_settings
            if current is None or not isinstance(current.get("unknown_setting"), bool):
                current_response = await self.async_get_mower_settings()
                current = current_response.get("mower_settings")
            if not isinstance(current, dict) or not isinstance(
                current.get("unknown_setting"), bool
            ):
                raise HomeAssistantError(
                    "Cannot preserve the mower's unknown setting without a valid read"
                )
            unknown_setting = current["unknown_setting"]

        response = await self._async_run_non_status_operation(
            "set_mower_settings",
            lambda: self.client.async_set_mower_settings(
                mow_in_rain=mow_in_rain,
                boundary_cut=boundary_cut,
                helix=helix,
                rain_delay_hours=rain_delay_hours,
                rain_delay_minutes=rain_delay_minutes,
                unknown_setting=unknown_setting,
            ),
        )
        self.mower_settings = response.get("mower_settings")
        self._async_notify_non_status_update()
        return response

    async def async_get_work_times(self) -> dict[str, Any]:
        response = await self._async_run_non_status_operation(
            "get_work_times", self.client.async_get_work_times
        )
        self.work_time_starts = response.get("work_time_starts")
        self.work_time_durations = response.get("work_time_durations")
        self._async_notify_non_status_update()
        return response

    async def async_set_work_times(
        self,
        starts: list[tuple[int, int]],
        durations: list[tuple[int, int]],
    ) -> dict[str, Any]:
        response = await self._async_run_non_status_operation(
            "set_work_times",
            lambda: self.client.async_set_work_times(starts, durations),
        )
        self.work_time_starts = response.get("work_time_starts")
        self.work_time_durations = response.get("work_time_durations")
        self._async_notify_non_status_update()
        return response

    async def async_send_raw_json(
        self, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        before = self.mower.state.last_seen
        response = await self._async_run_non_status_operation(
            "raw", lambda: self.mower.async_send_raw_json(payload)
        )
        state = self.mower.state
        if (
            response is not None
            and state.last_seen is not None
            and state.last_seen != before
        ):
            self._last_state = state
            self.async_set_updated_data(state)
        else:
            self._async_notify_non_status_update()
        return response

    def diagnostics_snapshot(self) -> dict[str, Any]:
        """Return privacy-safe coordinator routing and transaction metadata."""
        return {
            "selected_source": self._last_route_source,
            "selected_rssi": self._last_route_rssi,
            "route_changed_at": self._route_changed_at,
            "pending_commands": self._pending_commands,
            "active_command": self._active_command,
            "last_command_time": self._last_command_time,
            "last_command_outcome": self._last_command_outcome,
            "last_communication_time": self._last_communication_time,
            "last_failure_time": self._last_failure_time,
            "last_failure_phase": self._last_failure_phase,
            "last_failure_type": self._last_failure_type,
            "last_failure_message": self._last_failure_message,
            "settings_updated_at": dict(self._settings_updated_at),
        }
