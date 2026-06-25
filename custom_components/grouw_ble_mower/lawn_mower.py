"""Lawn mower platform for Grouw / Daye BLE Mower."""
from __future__ import annotations

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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

    # Daye command payloads are not confirmed yet; keep controls hidden until
    # start/pause/dock writes are validated from the Daye APK or hardware logs.
    _attr_supported_features = LawnMowerEntityFeature(0)

    def __init__(self, coordinator: GrouwMowerCoordinator) -> None:
        super().__init__(coordinator, None)
        self._attr_name = None

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return no activity until Daye status fields are mapped."""
        return None

    @property
    def battery_level(self) -> int | None:
        data = self.coordinator.data
        return data.power if data else None

    async def async_start_mowing(self) -> None:
        """Start mowing."""
        await self.coordinator.async_send_mode()

    async def async_pause(self) -> None:
        """Pause/stop mowing."""
        await self.coordinator.async_send_mode()

    async def async_dock(self) -> None:
        """Return to dock."""
        await self.coordinator.async_send_mode()
