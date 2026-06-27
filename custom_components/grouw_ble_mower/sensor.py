"""Sensor platform for Grouw Mower."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pygrouw import MowerState

from .coordinator import GrouwMowerCoordinator
from .entity import GrouwMowerEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GrouwSensorEntityDescription(SensorEntityDescription):
    """Describes a Grouw mower sensor."""

    value_fn: Callable[[MowerState], Any]


SENSORS: tuple[GrouwSensorEntityDescription, ...] = (
    GrouwSensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda state: state.battery_level,
    ),
    GrouwSensorEntityDescription(
        key="mode",
        translation_key="mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.mode,
    ),
    GrouwSensorEntityDescription(
        key="last_response_cmd",
        translation_key="last_response_cmd",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.last_response_cmd,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: GrouwMowerCoordinator = hass.data[entry.domain][entry.entry_id]
    async_add_entities(GrouwMowerSensor(coordinator, description) for description in SENSORS)


class GrouwMowerSensor(GrouwMowerEntity, SensorEntity):
    """A Grouw mower sensor."""

    entity_description: GrouwSensorEntityDescription

    def __init__(
        self,
        coordinator: GrouwMowerCoordinator,
        description: GrouwSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if data is None:
            return None
        return self.entity_description.value_fn(data)
