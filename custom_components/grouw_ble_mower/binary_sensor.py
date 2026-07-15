"""Binary sensors for Grouw Mower."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GrouwMowerCoordinator
from .entity import GrouwMowerEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GrouwBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Grouw mower binary sensor."""

    value_fn: Callable[[GrouwMowerCoordinator], bool | None]
    available_fn: Callable[[GrouwMowerCoordinator], bool]


def _has_status_state(coord: GrouwMowerCoordinator) -> bool:
    """Return true when normal status polling has produced a usable state."""
    return coord.status_is_fresh()


def _has_mower_settings(coord: GrouwMowerCoordinator) -> bool:
    """Return true when mower settings have been read or written."""
    return coord.mower_settings is not None


BINARY_SENSORS: tuple[GrouwBinarySensorEntityDescription, ...] = (
    GrouwBinarySensorEntityDescription(
        key="docked",
        translation_key="docked",
        value_fn=lambda coord: coord.data.station if coord.data else None,
        available_fn=_has_status_state,
    ),
    GrouwBinarySensorEntityDescription(
        key="mow_in_rain",
        translation_key="mow_in_rain",
        entity_category=None,
        icon="mdi:weather-pouring",
        value_fn=lambda coord: (
            coord.mower_settings.get("mow_in_rain") if coord.mower_settings else None
        ),
        available_fn=_has_mower_settings,
    ),
    GrouwBinarySensorEntityDescription(
        key="boundary_cut",
        translation_key="boundary_cut",
        entity_category=None,
        icon="mdi:border-all",
        value_fn=lambda coord: (
            coord.mower_settings.get("boundary_cut") if coord.mower_settings else None
        ),
        available_fn=_has_mower_settings,
    ),
    GrouwBinarySensorEntityDescription(
        key="helix",
        translation_key="helix",
        entity_category=None,
        icon="mdi:spiral",
        value_fn=lambda coord: (
            coord.mower_settings.get("helix") if coord.mower_settings else None
        ),
        available_fn=_has_mower_settings,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: GrouwMowerCoordinator = hass.data[entry.domain][entry.entry_id]
    async_add_entities(
        GrouwMowerBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


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
        return self.entity_description.value_fn(self.coordinator)

    @property
    def available(self) -> bool:
        return self.entity_description.available_fn(self.coordinator)
