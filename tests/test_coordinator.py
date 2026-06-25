"""Tests for Grouw mower coordinator behavior."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest

from custom_components.grouw_ble_mower.ble_client import GrouwBleError
from custom_components.grouw_ble_mower.ble_protocol import MowerState
from custom_components.grouw_ble_mower.const import CONF_ADDRESS
from custom_components.grouw_ble_mower.coordinator import (
    GrouwMowerCoordinator,
    UpdateFailed,
)


class _Entry:
    entry_id = "entry-1"
    domain = "grouw_ble_mower"
    options: dict[str, Any] = {}
    data = {CONF_ADDRESS: "AA:BB:CC:DD:EE:FF", "name": "Test mower"}


class _Hass:
    pass


def test_initial_poll_cooldown_after_command() -> None:
    """Poll is skipped when a manual command happened recently."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        coordinator._last_command_time = datetime.now(timezone.utc)

        from custom_components.grouw_ble_mower.coordinator import UpdateFailed
        with pytest.raises(UpdateFailed, match="cooldown"):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_initial_poll_failure_raises_update_failed() -> None:
    """Initial poll failure raises UpdateFailed and does not return placeholder state."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Client:
            async def async_get_all_info(self) -> dict[str, Any]:
                raise GrouwBleError("not reachable")

        coordinator.client = Client()
        with pytest.raises(UpdateFailed, match="not reachable"):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_raw_payload_requests_are_serialized() -> None:
    """Concurrent service calls do not create overlapping BLE transactions."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Client:
            active = 0
            max_active = 0

            async def async_send_raw_json(
                self, payload: dict[str, Any]
            ) -> dict[str, Any]:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                await asyncio.sleep(0)
                self.active -= 1
                return {"cmd": 0x80, "power": payload["power"]}

        client = Client()
        coordinator.client = client

        await asyncio.gather(
            coordinator.async_send_raw_json({"power": 41}),
            coordinator.async_send_raw_json({"power": 42}),
        )

        assert client.max_active == 1
        assert coordinator.data.raw in (
            {"cmd": 0x80, "power": 41},
            {"cmd": 0x80, "power": 42},
        )
        assert coordinator.data.power in {41, 42}

    asyncio.run(run())
