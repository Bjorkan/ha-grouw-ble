"""Base entities for Grouw/Daye BLE Mower."""
from __future__ import annotations

from homeassistant.const import CONF_NAME, Platform
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import GrouwMowerCoordinator


class GrouwMowerEntity(CoordinatorEntity[GrouwMowerCoordinator]):
    """Base class for all Grouw mower entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GrouwMowerCoordinator, suffix: str | None = None) -> None:
        super().__init__(coordinator)
        self._suffix = suffix
        key = suffix.lower().replace(" ", "_") if suffix else "mower"
        self._attr_unique_id = f"{coordinator.address}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.address)},
            connections={(CONNECTION_BLUETOOTH, self.coordinator.address)},
            manufacturer="Grouw / Daye Power",
            model=data.model if data else None,
            name=(data.name if data and data.name else self.coordinator.config_entry.data.get(CONF_NAME, DEFAULT_NAME)),
            serial_number=data.serial if data else None,
            sw_version=data.firmware_version if data else None,
        )

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return (
            self.coordinator.last_update_success
            and data is not None
            and data.last_seen is not None
        )
