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

    value_fn: Callable[[GrouwMowerCoordinator], Any]


SENSORS: tuple[GrouwSensorEntityDescription, ...] = (
    GrouwSensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda coord: coord.data.battery_level if coord.data else None,
    ),
    GrouwSensorEntityDescription(
        key="mode",
        translation_key="mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coord: coord.data.mode if coord.data else None,
    ),
    GrouwSensorEntityDescription(
        key="last_response_cmd",
        translation_key="last_response_cmd",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coord: coord.data.last_response_cmd if coord.data else None,
    ),
    GrouwSensorEntityDescription(
        key="area2_percentage",
        translation_key="area2_percentage",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda coord: coord.multi_area.get("area2_percentage") if coord.multi_area else None,
    ),
    GrouwSensorEntityDescription(
        key="area2_distance",
        translation_key="area2_distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="m",
        value_fn=lambda coord: coord.multi_area.get("area2_distance") if coord.multi_area else None,
    ),
    GrouwSensorEntityDescription(
        key="area3_percentage",
        translation_key="area3_percentage",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda coord: coord.multi_area.get("area3_percentage") if coord.multi_area else None,
    ),
    GrouwSensorEntityDescription(
        key="area3_distance",
        translation_key="area3_distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="m",
        value_fn=lambda coord: coord.multi_area.get("area3_distance") if coord.multi_area else None,
    ),
    GrouwSensorEntityDescription(
        key="rain_delay_hour",
        translation_key="rain_delay_hour",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
        value_fn=lambda coord: coord.mower_settings.get("rain_delay_hour") if coord.mower_settings else None,
    ),
    GrouwSensorEntityDescription(
        key="rain_delay_minute",
        translation_key="rain_delay_minute",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="min",
        value_fn=lambda coord: coord.mower_settings.get("rain_delay_minute") if coord.mower_settings else None,
    ),
    GrouwSensorEntityDescription(
        key="unknown_setting",
        translation_key="unknown_setting",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coord: coord.mower_settings.get("unknown_setting") if coord.mower_settings else None,
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
        return self.entity_description.value_fn(self.coordinator)

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return (
            self.coordinator.last_update_success
            and data is not None
            and data.last_seen is not None
        )
