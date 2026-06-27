"""Binary sensors for Grouw Mower."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pygrouw import MowerState

from .coordinator import GrouwMowerCoordinator
from .entity import GrouwMowerEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GrouwBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Grouw mower binary sensor."""

    value_fn: Callable[[MowerState], bool | None]


BINARY_SENSORS: tuple[GrouwBinarySensorEntityDescription, ...] = (
    GrouwBinarySensorEntityDescription(
        key="docked",
        translation_key="docked",
        value_fn=lambda state: state.station,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: GrouwMowerCoordinator = hass.data[entry.domain][entry.entry_id]
    async_add_entities(GrouwMowerBinarySensor(coordinator, description) for description in BINARY_SENSORS)


class GrouwMowerBinarySensor(GrouwMowerEntity, BinarySensorEntity):
    """A Grouw mower binary sensor."""

    entity_description: GrouwBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: GrouwMowerCoordinator,
        description: GrouwBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None:
            return None
        return self.entity_description.value_fn(data)
