"""Home Assistant buttons for on-demand pyGrouw settings reads."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GrouwMowerCoordinator
from .entity import GrouwMowerEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class GrouwButtonEntityDescription(ButtonEntityDescription):
    """Description with the coordinator method invoked on press."""

    read_fn: Callable[[GrouwMowerCoordinator], Awaitable[dict[str, Any]]]


BUTTONS: tuple[GrouwButtonEntityDescription, ...] = (
    GrouwButtonEntityDescription(
        key="read_multi_area",
        translation_key="read_multi_area",
        entity_category=EntityCategory.CONFIG,
        read_fn=lambda coordinator: coordinator.async_get_multi_area(),
    ),
    GrouwButtonEntityDescription(
        key="read_mower_settings",
        translation_key="read_mower_settings",
        entity_category=EntityCategory.CONFIG,
        read_fn=lambda coordinator: coordinator.async_get_mower_settings(),
    ),
    GrouwButtonEntityDescription(
        key="read_work_times",
        translation_key="read_work_times",
        entity_category=EntityCategory.CONFIG,
        read_fn=lambda coordinator: coordinator.async_get_work_times(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-mower settings read buttons."""
    coordinator: GrouwMowerCoordinator = hass.data[entry.domain][entry.entry_id]
    async_add_entities(GrouwMowerButton(coordinator, description) for description in BUTTONS)


class GrouwMowerButton(GrouwMowerEntity, ButtonEntity):
    """Read settings on demand, without an additional background BLE poll."""

    entity_description: GrouwButtonEntityDescription

    def __init__(
        self,
        coordinator: GrouwMowerCoordinator,
        description: GrouwButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Permit a manual read even when the latest status poll failed."""
        return True

    async def async_press(self) -> None:
        """Use the existing serialized, authenticated coordinator read operation."""
        await self.entity_description.read_fn(self.coordinator)
