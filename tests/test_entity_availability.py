"""Tests for entity availability behavior."""

from __future__ import annotations

from typing import Any


class _Coord:
    def __init__(self) -> None:
        self.address = "AA:BB:CC:DD:EE:FF"
        self.data = None
        self.last_update_success = False
        self.multi_area: dict[str, Any] | None = None
        self.mower_settings: dict[str, Any] | None = None


def test_multi_area_sensor_available_from_cache_after_status_failure() -> None:
    """Settings-backed sensors are available when their cache has data."""
    from custom_components.grouw_ble_mower.sensor import SENSORS, GrouwMowerSensor

    coord = _Coord()
    coord.multi_area = {"area2_percentage": 5}
    description = next(item for item in SENSORS if item.key == "area2_percentage")

    sensor = GrouwMowerSensor(coord, description)

    assert sensor.available is True
    assert sensor.native_value == 5


def test_mower_settings_binary_sensor_available_from_cache_after_status_failure() -> (
    None
):
    """Settings-backed binary sensors are available when their cache has data."""
    from custom_components.grouw_ble_mower.binary_sensor import (
        BINARY_SENSORS,
        GrouwMowerBinarySensor,
    )

    coord = _Coord()
    coord.mower_settings = {"mow_in_rain": True}
    description = next(item for item in BINARY_SENSORS if item.key == "mow_in_rain")

    sensor = GrouwMowerBinarySensor(coord, description)

    assert sensor.available is True
    assert sensor.is_on is True
