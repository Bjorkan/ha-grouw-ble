"""Tests for native Home Assistant access to published pyGrouw features."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.grouw_ble_mower import PLATFORMS
from custom_components.grouw_ble_mower.button import BUTTONS, GrouwMowerButton
from custom_components.grouw_ble_mower.sensor import SENSORS, GrouwMowerSensor
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError

DAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


class _Coordinator:
    """Only the coordinator features used by the new entity platforms."""

    def __init__(self) -> None:
        self.address = "AA:BB:CC:DD:EE:FF"
        self.calls: list[str] = []
        self.data = None
        self.work_time_starts: list[dict[str, Any]] | None = None
        self.work_time_durations: list[dict[str, Any]] | None = None

    def status_is_fresh(self) -> bool:
        return False

    async def async_get_multi_area(self) -> dict[str, Any]:
        self.calls.append("multi_area")
        return {"multi_area": {}}

    async def async_get_mower_settings(self) -> dict[str, Any]:
        self.calls.append("mower_settings")
        return {"mower_settings": {}}

    async def async_get_work_times(self) -> dict[str, Any]:
        self.calls.append("work_times")
        return {"work_time_starts": [], "work_time_durations": []}


def test_settings_buttons_use_published_pygrouw_coordinator_api() -> None:
    """Each button reads its own settings without waiting for a status poll."""

    async def run() -> None:
        coord = _Coordinator()
        for description in BUTTONS:
            button = GrouwMowerButton(coord, description)
            assert button.available is True
            assert button._attr_unique_id == f"{coord.address}_{description.key}"
            await button.async_press()

        assert coord.calls == ["multi_area", "mower_settings", "work_times"]

    asyncio.run(run())


def test_settings_button_propagates_ble_errors() -> None:
    """Authenticated BLE errors are not silently swallowed."""

    async def run() -> None:
        coord = _Coordinator()

        async def failed_read() -> dict[str, Any]:
            raise HomeAssistantError("BLE unavailable")

        coord.async_get_multi_area = failed_read  # type: ignore[method-assign]
        button = GrouwMowerButton(coord, BUTTONS[0])
        with pytest.raises(HomeAssistantError, match="BLE unavailable"):
            await button.async_press()

    asyncio.run(run())


def test_weekly_schedule_sensors_only_available_after_read() -> None:
    """Work-time sensors keep a stable unique ID and do not show fake defaults."""
    coord = _Coordinator()
    descriptions = [item for item in SENSORS if item.key.startswith("work_time_")]
    assert len(descriptions) == 7

    monday = next(item for item in descriptions if item.key == "work_time_monday")
    sensor = GrouwMowerSensor(coord, monday)
    assert sensor.available is False
    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None
    assert sensor._attr_unique_id == f"{coord.address}_work_time_monday"

    coord.work_time_starts = [
        {"day": day, "hour": 8 + i, "minute": i}
        for i, day in enumerate(reversed(DAYS))
    ]
    assert sensor.available is False  # Require both response packets.
    coord.work_time_durations = [
        {"day": day, "hours": i, "tenths": i}
        for i, day in enumerate(reversed(DAYS))
    ]
    assert sensor.available is True
    assert sensor.native_value == "14:06"
    assert sensor.extra_state_attributes == {"duration_hours": 6, "duration_tenths": 6}

    tuesday = next(item for item in descriptions if item.key == "work_time_tuesday")
    assert GrouwMowerSensor(coord, tuesday).native_value == "13:05"


def test_schedule_sensors_ignore_incomplete_or_invalid_data() -> None:
    """Do not invent a time when pyGrouw has not returned valid day details."""
    coord = _Coordinator()
    monday = next(item for item in SENSORS if item.key == "work_time_monday")
    sensor = GrouwMowerSensor(coord, monday)
    coord.work_time_starts = [{"day": "monday", "hour": 7, "minute": 75}]
    coord.work_time_durations = [{"day": "monday", "hours": 2, "tenths": 3}]
    assert sensor.available is False
    assert sensor.native_value is None

    coord.work_time_starts[0]["minute"] = 45
    coord.work_time_durations[0]["tenths"] = 10
    assert sensor.available is False

    coord.work_time_durations[0]["tenths"] = 5
    assert sensor.available is True
    assert sensor.native_value == "07:45"
    assert sensor.extra_state_attributes == {"duration_hours": 2, "duration_tenths": 5}


def test_button_platform_and_translations() -> None:
    """New entities are registered and fully translated in all shipped locales."""
    assert Platform.BUTTON in PLATFORMS

    root = Path(__file__).resolve().parents[1]
    for language in ("en", "sv", "da"):
        path = root / "custom_components" / "grouw_ble_mower" / "translations"
        labels = json.loads((path / f"{language}.json").read_text(encoding="utf-8"))
        for button in BUTTONS:
            assert labels["entity"]["button"][button.translation_key]["name"]
        for day in DAYS:
            assert labels["entity"]["sensor"][f"work_time_{day}"]["name"]
