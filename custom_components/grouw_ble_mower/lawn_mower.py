"""Lawn mower platform for Grouw BLE Mower."""
from __future__ import annotations

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DOCK_MODE,
    CONF_PAUSE_MODE,
    CONF_START_MODE,
    DEFAULT_DOCK_MODE,
    DEFAULT_NAME,
    DEFAULT_PAUSE_MODE,
    DEFAULT_START_MODE,
    MODE_ERROR,
    MODE_HOME,
    MODE_IDLE,
    MODE_WORK,
)
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
        data = self.coordinator.data
        if data is None:
            return None

        if data.error_type not in (None, 0, -1) or data.mode == MODE_ERROR:
            return LawnMowerActivity.ERROR

        if data.station is True:
            return LawnMowerActivity.DOCKED

        if data.mode == MODE_WORK:
            return LawnMowerActivity.MOWING
        if data.mode == MODE_HOME:
            return LawnMowerActivity.RETURNING
        if data.mode == MODE_IDLE:
            return LawnMowerActivity.PAUSED

        return None

    @property
    def battery_level(self) -> int | None:
        data = self.coordinator.data
        return data.power if data else None

    async def async_start_mowing(self) -> None:
        """Start mowing."""
        mode = self.coordinator.config_entry.options.get(
            CONF_START_MODE,
            self.coordinator.config_entry.data.get(CONF_START_MODE, DEFAULT_START_MODE),
        )
        await self.coordinator.async_send_mode(int(mode))

    async def async_pause(self) -> None:
        """Pause/stop mowing."""
        mode = self.coordinator.config_entry.options.get(
            CONF_PAUSE_MODE,
            self.coordinator.config_entry.data.get(CONF_PAUSE_MODE, DEFAULT_PAUSE_MODE),
        )
        await self.coordinator.async_send_mode(int(mode))

    async def async_dock(self) -> None:
        """Return to dock."""
        mode = self.coordinator.config_entry.options.get(
            CONF_DOCK_MODE,
            self.coordinator.config_entry.data.get(CONF_DOCK_MODE, DEFAULT_DOCK_MODE),
        )
        await self.coordinator.async_send_mode(int(mode))
