"""Sensor platform for Grouw BLE Mower."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble_protocol import MowerState
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
        value_fn=lambda state: state.power,
    ),
    GrouwSensorEntityDescription(
        key="mode",
        translation_key="mode",
        value_fn=lambda state: state.mode,
    ),
    GrouwSensorEntityDescription(
        key="error_type",
        translation_key="error_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.error_type,
    ),
    GrouwSensorEntityDescription(
        key="wifi_level",
        translation_key="wifi_level",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.wifi_level,
    ),
    GrouwSensorEntityDescription(
        key="rain_delay_left",
        translation_key="rain_delay_left",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda state: state.rain_delay_left,
    ),
    GrouwSensorEntityDescription(
        key="rain_delay_set",
        translation_key="rain_delay_set",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.rain_delay_set,
    ),
    GrouwSensorEntityDescription(
        key="current_runtime",
        translation_key="current_runtime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda state: state.cur_min,
    ),
    GrouwSensorEntityDescription(
        key="last_runtime",
        translation_key="last_runtime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.on_min,
    ),
    GrouwSensorEntityDescription(
        key="total_runtime",
        translation_key="total_runtime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.total_min,
    ),
    GrouwSensorEntityDescription(
        key="current_area",
        translation_key="current_area",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.cur_area,
    ),
    GrouwSensorEntityDescription(
        key="last_area",
        translation_key="last_area",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.on_area,
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
