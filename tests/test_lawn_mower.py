"""Tests for Grouw mower lawn mower entity."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from pygrouw import MowerState
from custom_components.grouw_ble_mower.const import (
    CONF_ADDRESS,
    DAYE_MODE_IDLE,
    DAYE_MODE_MOWING,
    DAYE_MODE_MOWING_ALTERNATE,
    DAYE_MODE_RETURNING,
)


def _make_state(mode: int | None, station: bool | None) -> MowerState:
    return MowerState(
        address="AA:BB:CC:DD:EE:FF",
        name="Test mower",
        battery_level=80,
        mode=mode,
        station=station,
    )


class _Coord:
    def __init__(self, data: Any = None, last_update_success: bool = True) -> None:
        self.data = data
        self.last_update_success = last_update_success
        self.address = "AA:BB:CC:DD:EE:FF"


def test_activity_mowing() -> None:
    """Mowing mode returns MOWING activity."""
    from homeassistant.components.lawn_mower import LawnMowerActivity
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(_Coord(_make_state(DAYE_MODE_MOWING, False)))
    assert mower.activity is LawnMowerActivity.MOWING


def test_activity_mowing_alternate_mode_code() -> None:
    """Observed alternate mowing mode code returns MOWING activity."""
    from homeassistant.components.lawn_mower import LawnMowerActivity
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(
        _Coord(_make_state(DAYE_MODE_MOWING_ALTERNATE, False))
    )
    assert mower.activity is LawnMowerActivity.MOWING


def test_activity_docked_overrides_mowing_mode() -> None:
    """Station flag wins when the mower reports docked while mode is mowing."""
    from homeassistant.components.lawn_mower import LawnMowerActivity
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(_Coord(_make_state(DAYE_MODE_MOWING, True)))
    assert mower.activity is LawnMowerActivity.DOCKED


def test_activity_returning() -> None:
    """Returning mode returns RETURNING activity."""
    from homeassistant.components.lawn_mower import LawnMowerActivity
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(_Coord(_make_state(DAYE_MODE_RETURNING, False)))
    assert mower.activity is LawnMowerActivity.RETURNING


def test_activity_docked() -> None:
    """Stopped + station=True returns DOCKED."""
    from homeassistant.components.lawn_mower import LawnMowerActivity
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(_Coord(_make_state(DAYE_MODE_IDLE, True)))
    assert mower.activity is LawnMowerActivity.DOCKED


def test_activity_paused() -> None:
    """Stopped + station=False returns PAUSED."""
    from homeassistant.components.lawn_mower import LawnMowerActivity
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(_Coord(_make_state(DAYE_MODE_IDLE, False)))
    assert mower.activity is LawnMowerActivity.PAUSED


def test_activity_idle_unknown_station() -> None:
    """Idle + station=None returns PAUSED."""
    from homeassistant.components.lawn_mower import LawnMowerActivity
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(_Coord(_make_state(DAYE_MODE_IDLE, None)))
    assert mower.activity is LawnMowerActivity.PAUSED


def test_activity_none_data() -> None:
    """None data returns None."""
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    mower = GrouwBleLawnMower(_Coord(None))
    assert mower.activity is None


def test_start_mowing_refreshes_when_station_unknown() -> None:
    """Start command refreshes state when station is None."""
    from custom_components.grouw_ble_mower.lawn_mower import GrouwBleLawnMower

    refresh_called = False
    send_command_called = False

    class _CoordWithRefresh:
        data = _make_state(DAYE_MODE_IDLE, None)
        last_update_success = True
        address = "AA:BB:CC:DD:EE:FF"

        def status_is_fresh(self) -> bool:
            return self.data.station is not None

        async def async_request_refresh(self) -> None:
            nonlocal refresh_called
            refresh_called = True
            self.data = _make_state(DAYE_MODE_IDLE, False)

        async def async_send_command(self, command: str) -> None:
            nonlocal send_command_called
            send_command_called = True
            assert command == "resume"

    async def run() -> None:
        mower = GrouwBleLawnMower(_CoordWithRefresh())
        await mower.async_start_mowing()

        assert refresh_called, "async_request_refresh should be called when station is None"
        assert send_command_called, "async_send_command should be called after refresh"

    asyncio.run(run())
