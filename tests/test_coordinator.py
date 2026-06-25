"""Tests for Grouw mower coordinator behavior."""
from __future__ import annotations

import asyncio
from typing import Any

from custom_components.grouw_ble_mower.ble_client import GrouwBleDeviceNotFound
from custom_components.grouw_ble_mower.ble_protocol import MowerState
from custom_components.grouw_ble_mower.const import CONF_ADDRESS
from custom_components.grouw_ble_mower.coordinator import GrouwMowerCoordinator
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed


class _Entry:
    entry_id = "entry-1"
    domain = "grouw_ble_mower"
    options: dict[str, Any] = {}
    data = {CONF_ADDRESS: "AA:BB:CC:DD:EE:FF", "name": "Test mower"}


class _Hass:
    pass


def test_missing_ble_device_retries_setup_before_first_state() -> None:
    """A never-seen BLE device keeps setup retry semantics."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Client:
            async def async_get_all_info(self) -> dict[str, Any]:
                raise GrouwBleDeviceNotFound("not found")

        coordinator.client = Client()

        try:
            await coordinator._async_update_data()
        except ConfigEntryNotReady:
            return
        raise AssertionError("Expected ConfigEntryNotReady")

    asyncio.run(run())


def test_missing_ble_device_is_update_failure_after_state_exists() -> None:
    """A temporary BLE disappearance after setup does not look like setup retry."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        coordinator._last_state = MowerState(address="AA:BB:CC:DD:EE:FF")

        class Client:
            async def async_get_all_info(self) -> dict[str, Any]:
                raise GrouwBleDeviceNotFound("not found")

        coordinator.client = Client()

        try:
            await coordinator._async_update_data()
        except UpdateFailed:
            return
        raise AssertionError("Expected UpdateFailed")

    asyncio.run(run())


def test_raw_json_requests_are_serialized() -> None:
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
                return {"cmd": 500, "power": payload["power"]}

        client = Client()
        coordinator.client = client

        await asyncio.gather(
            coordinator.async_send_raw_json({"power": 41}),
            coordinator.async_send_raw_json({"power": 42}),
        )

        assert client.max_active == 1
        assert coordinator.data.power in {41, 42}

    asyncio.run(run())
