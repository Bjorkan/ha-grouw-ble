"""Lawn mower platform for Grouw / Daye BLE Mower."""
from __future__ import annotations

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DAYE_MODE_MOWING, DAYE_MODE_RETURNING, DAYE_MODE_STOPPED
from .coordinator import GrouwMowerCoordinator
from .entity import GrouwMowerEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lawn mower entity."""
    coordinator: GrouwMowerCoordinator = hass.data[entry.domain][entry.entry_id]
    async_add_entities([GrouwBleLawnMower(coordinator)])


class GrouwBleLawnMower(GrouwMowerEntity, LawnMowerEntity):
    """Grouw BLE lawn mower entity."""

    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    def __init__(self, coordinator: GrouwMowerCoordinator) -> None:
        super().__init__(coordinator, None)
        self._attr_name = None

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return mower activity from the captured Daye status mode byte."""
        data = self.coordinator.data
        if data is None:
            return None
        if data.mode == DAYE_MODE_MOWING:
            return LawnMowerActivity.MOWING
        if data.mode == DAYE_MODE_RETURNING:
            return LawnMowerActivity.RETURNING
        if data.mode == DAYE_MODE_STOPPED:
            if data.station is True:
                return LawnMowerActivity.DOCKED
            if data.station is False:
                return LawnMowerActivity.PAUSED
            return None
        return None

    @property
    def battery_level(self) -> int | None:
        data = self.coordinator.data
        return data.power if data else None

    async def async_start_mowing(self) -> None:
        """Start mowing."""
        data = self.coordinator.data
        if data is None or data.station is None:
            await self.coordinator.async_request_refresh()
            data = self.coordinator.data

        if data is None or data.station is None:
            raise HomeAssistantError(
                "Cannot determine mower station state before starting. "
                "Ensure the mower is reachable, then try again."
            )

        command = "start" if data.station is True else "resume"
        await self.coordinator.async_send_command(command)

    async def async_pause(self) -> None:
        """Pause/stop mowing."""
        await self.coordinator.async_send_command("pause")

    async def async_dock(self) -> None:
        """Return to dock."""
        await self.coordinator.async_send_command("dock")
