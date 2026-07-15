"""Tests for Grouw mower coordinator behavior."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from pygrouw import (
    GrouwBleAuthenticationError,
    GrouwBleError,
    MowerState,
)
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


def test_recent_command_does_not_create_a_false_success_poll() -> None:
    """A recent command does not make cached data count as a fresh poll."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        coordinator._last_command_time = datetime.now(timezone.utc)
        expected = MowerState(
            address="AA:BB:CC:DD:EE:FF",
            battery_level=75,
            mode=0,
            station=False,
            last_seen=datetime.now(timezone.utc),
        )

        class Mower:
            async def async_update(self) -> MowerState:
                return expected

        coordinator.mower = Mower()
        assert await coordinator._async_update_data() is expected

    asyncio.run(run())


def test_device_provider_uses_home_assistant_bluetooth_manager(monkeypatch: Any) -> None:
    """pyGrouw should receive devices resolved through Home Assistant Bluetooth."""
    from custom_components.grouw_ble_mower import coordinator as coordinator_module

    hass = _Hass()
    resolved_device = object()
    calls: list[tuple[Any, str, bool]] = []

    def async_ble_device_from_address(hass_arg: Any, address: str, *, connectable: bool) -> object:
        calls.append((hass_arg, address, connectable))
        return resolved_device

    monkeypatch.setattr(
        coordinator_module.bluetooth,
        "async_ble_device_from_address",
        async_ble_device_from_address,
    )

    coordinator = GrouwMowerCoordinator(
        hass, _Entry(), "aa:bb:cc:dd:ee:ff", "Test mower"
    )

    assert coordinator._async_ble_device_from_address() is resolved_device
    assert calls == [(hass, "AA:BB:CC:DD:EE:FF", True)]


def test_initial_poll_failure_raises_update_failed() -> None:
    """Initial poll failure raises UpdateFailed and does not return placeholder state."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Mower:
            async def async_update(self) -> MowerState:
                raise GrouwBleError("not reachable")

        coordinator.mower = Mower()
        with pytest.raises(UpdateFailed, match="not reachable"):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_poll_authentication_failure_raises_config_entry_auth_failed() -> None:
    """PIN/auth failures should trigger Home Assistant reauthentication."""

    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Mower:
            async def async_update(self) -> MowerState:
                raise GrouwBleAuthenticationError("bad pin")

        coordinator.mower = Mower()
        with pytest.raises(ConfigEntryAuthFailed, match="bad pin"):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_poll_unverifiable_auth_response_raises_update_failed() -> None:
    """An auth response without PIN data should not be treated as reauth."""

    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )

        class Mower:
            async def async_update(self) -> MowerState:
                raise GrouwBleError("auth response did not include PIN data")

        coordinator.mower = Mower()
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


def test_poll_is_deferred_when_command_is_pending() -> None:
    """Background polling should not jump ahead of a waiting manual command."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        coordinator._pending_commands = 1

        with pytest.raises(UpdateFailed, match="pending command"):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_pending_command_does_not_republish_cached_state_as_fresh() -> None:
    """A deferred poll preserves cached data without reporting fresh success."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        state = MowerState(
            address="AA:BB:CC:DD:EE:FF",
            battery_level=80,
            last_seen=datetime.now(timezone.utc),
        )
        coordinator._last_state = state
        coordinator._pending_commands = 1

        with pytest.raises(UpdateFailed, match="pending command"):
            await coordinator._async_update_data()
        assert coordinator._last_state is state

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

        class Mower:
            active = 0
            max_active = 0
            state = MowerState(address="AA:BB:CC:DD:EE:FF")

            async def async_send_raw_json(
                self, payload: dict[str, Any]
            ) -> dict[str, Any]:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                await asyncio.sleep(0)
                self.active -= 1
                self.state = MowerState(
                    address="AA:BB:CC:DD:EE:FF",
                    battery_level=payload["battery_level"],
                    raw={"cmd": 0x80, "battery_level": payload["battery_level"]},
                    last_response_cmd=0x80,
                    last_seen=datetime.now(timezone.utc),
                )
                return {"cmd": 0x80, "battery_level": payload["battery_level"]}

        mower = Mower()
        coordinator.mower = mower

        await asyncio.gather(
            coordinator.async_send_raw_json({"battery_level": 41}),
            coordinator.async_send_raw_json({"battery_level": 42}),
        )

        assert mower.max_active == 1
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

        async def fail_command(command: str) -> MowerState:
            raise GrouwBleAuthenticationError("bad pin")

        coordinator._async_write_command = fail_command  # type: ignore[method-assign]
        with pytest.raises(HomeAssistantError, match="reauthentication"):
            await coordinator.async_send_command("pause")

        assert entry.reauth_hass is hass
        assert coordinator._pending_commands == 0

    asyncio.run(run())


def test_change_pin_delegates_with_new_pin_only() -> None:
    """Coordinator lets pyGrouw use its configured current PIN."""

    async def run() -> None:
        class Hass:
            class ConfigEntries:
                def async_update_entry(self, *args: Any, **kwargs: Any) -> None:
                    pass

            config_entries = ConfigEntries()

        coordinator = GrouwMowerCoordinator(
            Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower", "1234"
        )

        class Client:
            called_with: tuple[Any, ...] | None = None

            async def async_change_pin(self, *args: Any) -> dict[str, Any]:
                self.called_with = args
                return {"pin_change_success": True}

        client = Client()
        coordinator.client = client

        await coordinator.async_change_pin("4321")

        assert client.called_with == ("4321",)

    asyncio.run(run())


def test_command_cooldown_starts_after_ble_transaction() -> None:
    """Manual-command cooldown should be measured after the BLE request."""

    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        client_finished_at: datetime | None = None

        async def write_command(command: str) -> MowerState:
            nonlocal client_finished_at
            await asyncio.sleep(0)
            client_finished_at = datetime.now(timezone.utc)
            return MowerState(
                address="AA:BB:CC:DD:EE:FF",
                battery_level=70,
                mode=0x14,
                station=False,
                last_seen=datetime.now(timezone.utc),
            )

        coordinator._async_write_command = write_command  # type: ignore[method-assign]

        await coordinator.async_send_command("pause")

        assert client_finished_at is not None
        assert coordinator._last_command_time is not None
        assert coordinator._last_command_time >= client_finished_at
        assert coordinator._pending_commands == 0

    asyncio.run(run())


def test_settings_update_notifies_after_cache_is_updated() -> None:
    """Settings listeners see the new cache without publishing status data."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        seen: list[dict[str, Any] | None] = []

        class Client:
            async def async_get_multi_area(self) -> dict[str, Any]:
                return {"multi_area": {"area2_percentage": 10}}

        coordinator.client = Client()
        coordinator.async_update_listeners = lambda: seen.append(coordinator.multi_area)
        response = await coordinator.async_get_multi_area()

        assert response["multi_area"]["area2_percentage"] == 10
        assert seen == [{"area2_percentage": 10}]
        assert coordinator.data is None

    asyncio.run(run())


def test_duplicate_active_commands_share_one_ble_write() -> None:
    """Repeated identical clicks are coalesced while the first is active."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        writes = 0
        release = asyncio.Event()

        async def write_command(command: str) -> MowerState:
            nonlocal writes
            writes += 1
            await release.wait()
            return MowerState(
                address=coordinator.address,
                mode=0x14,
                station=False,
                last_seen=datetime.now(timezone.utc),
            )

        coordinator._async_write_command = write_command  # type: ignore[method-assign]
        first = asyncio.create_task(coordinator.async_send_command("pause"))
        await asyncio.sleep(0)
        second = asyncio.create_task(coordinator.async_send_command("pause"))
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)

        assert writes == 1
        assert coordinator._pending_commands == 0

    asyncio.run(run())


def test_newer_command_supersedes_older_unsent_command() -> None:
    """A newer desired action prevents an older queued action from being sent."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        await coordinator._ble_lock.acquire()
        sent: list[str] = []

        async def write_command(command: str) -> MowerState:
            sent.append(command)
            return MowerState(
                address=coordinator.address,
                mode=0x03 if command == "dock" else 0x14,
                station=False,
                last_seen=datetime.now(timezone.utc),
            )

        coordinator._async_write_command = write_command  # type: ignore[method-assign]
        old = asyncio.create_task(coordinator.async_send_command("pause"))
        await asyncio.sleep(0)
        newest = asyncio.create_task(coordinator.async_send_command("dock"))
        await asyncio.sleep(0)
        coordinator._ble_lock.release()

        with pytest.raises(HomeAssistantError, match="superseded"):
            await old
        await newest
        assert sent == ["dock"]

    asyncio.run(run())


def test_successful_settings_read_does_not_clear_status_failure() -> None:
    """Settings communication cannot make stale status available again."""
    async def run() -> None:
        coordinator = GrouwMowerCoordinator(
            _Hass(), _Entry(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        failure_time = datetime.now(timezone.utc)
        coordinator._last_failure_time = failure_time

        class Client:
            async def async_get_mower_settings(self) -> dict[str, Any]:
                return {"mower_settings": {"unknown_setting": True}}

        coordinator.client = Client()
        await coordinator.async_get_mower_settings()
        assert coordinator._last_failure_time is failure_time
        assert coordinator.data is None

    asyncio.run(run())
