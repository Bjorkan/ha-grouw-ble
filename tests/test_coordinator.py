"""Tests for Grouw mower coordinator behavior."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError

from custom_components.grouw_ble_mower.ble_client import (
    GrouwBleAuthenticationError,
    GrouwBleError,
)
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


def test_poll_authentication_failure_raises_config_entry_auth_failed() -> None:
    """PIN/auth failures should trigger Home Assistant reauthentication."""

    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Client:
            async def async_get_all_info(self) -> dict[str, Any]:
                raise GrouwBleAuthenticationError("bad pin")

        coordinator.client = Client()
        with pytest.raises(ConfigEntryAuthFailed, match="bad pin"):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_poll_unverifiable_auth_response_raises_update_failed() -> None:
    """An auth response without PIN data should not be treated as reauth."""

    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Client:
            async def async_get_all_info(self) -> dict[str, Any]:
                raise GrouwBleError("auth response did not include PIN data")

        coordinator.client = Client()
        with pytest.raises(UpdateFailed, match="did not include PIN data"):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_poll_is_deferred_when_ble_transaction_is_active() -> None:
    """Background polling does not wait behind an active BLE transaction."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        await coordinator._ble_lock.acquire()
        try:
            with pytest.raises(UpdateFailed, match="active BLE transaction"):
                await coordinator._async_update_data()
        finally:
            coordinator._ble_lock.release()

    asyncio.run(run())


def test_failure_backoff_after_state_raises_update_failed() -> None:
    """Backoff after a BLE failure should keep entities unavailable."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        coordinator._last_state = MowerState(
            address="AA:BB:CC:DD:EE:FF",
            last_seen=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        coordinator._last_failure_time = datetime.now(timezone.utc)

        with pytest.raises(UpdateFailed, match="failure backoff"):
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
                return {"cmd": 0x80, "battery_level": payload["battery_level"]}

        client = Client()
        coordinator.client = client

        await asyncio.gather(
            coordinator.async_send_raw_json({"battery_level": 41}),
            coordinator.async_send_raw_json({"battery_level": 42}),
        )

        assert client.max_active == 1
        assert coordinator.data.raw in (
            {"cmd": 0x80, "battery_level": 41},
            {"cmd": 0x80, "battery_level": 42},
        )
        assert coordinator.data.battery_level in {41, 42}

    asyncio.run(run())


def test_command_authentication_failure_starts_reauth() -> None:
    """Service-triggered auth failures should ask HA for reauthentication."""

    async def run() -> None:
        hass = _Hass()

        class Entry(_Entry):
            reauth_hass: Any = None

            def async_start_reauth(self, reauth_hass: Any) -> None:
                self.reauth_hass = reauth_hass

        entry = Entry()
        coordinator = GrouwMowerCoordinator(
            hass, entry, "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Client:
            async def async_command(self, command: str) -> dict[str, Any]:
                raise GrouwBleAuthenticationError("bad pin")

        coordinator.client = Client()
        with pytest.raises(HomeAssistantError, match="reauthentication"):
            await coordinator.async_send_command("pause")

        assert entry.reauth_hass is hass

    asyncio.run(run())


def test_command_cooldown_starts_after_ble_transaction() -> None:
    """Manual-command cooldown should be measured after the BLE request."""

    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        client_finished_at: datetime | None = None

        class Client:
            async def async_command(self, command: str) -> dict[str, Any]:
                nonlocal client_finished_at
                await asyncio.sleep(0)
                client_finished_at = datetime.now(timezone.utc)
                return {"cmd": 0x80, "battery_level": 70}

        coordinator.client = Client()

        await coordinator.async_send_command("pause")

        assert client_finished_at is not None
        assert coordinator._last_command_time is not None
        assert coordinator._last_command_time >= client_finished_at

    asyncio.run(run())
