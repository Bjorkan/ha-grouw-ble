"""Test support for local and Home Assistant test environments."""
from __future__ import annotations

import importlib.util
from datetime import UTC
import sys
import types
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _install_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules.setdefault(name, module)
    return sys.modules[name]


def _install_lightweight_stubs() -> None:
    """Install small stubs when Home Assistant is not available locally."""
    voluptuous = _install_module("voluptuous")

    class _Schema:
        def __init__(self, schema: Any) -> None:
            self.schema = schema

        def __call__(self, data: Any) -> Any:
            return data

    voluptuous.Schema = _Schema
    voluptuous.Required = lambda key, *args, **kwargs: key
    voluptuous.Optional = lambda key, *args, **kwargs: key

    homeassistant = _install_module("homeassistant")
    homeassistant.__version__ = "test"

    components = _install_module("homeassistant.components")
    bluetooth = _install_module("homeassistant.components.bluetooth")
    components.bluetooth = bluetooth
    bluetooth.async_ble_device_from_address = lambda *args, **kwargs: None

    config_entries = _install_module("homeassistant.config_entries")

    class ConfigEntry:
        """Minimal config entry stub."""

    config_entries.ConfigEntry = ConfigEntry

    const = _install_module("homeassistant.const")
    const.CONF_NAME = "name"

    class Platform:
        LAWN_MOWER = "lawn_mower"
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"

    const.Platform = Platform

    core = _install_module("homeassistant.core")

    class HomeAssistant:
        """Minimal hass stub."""

    class ServiceCall:
        """Minimal service call stub."""

    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall

    exceptions = _install_module("homeassistant.exceptions")

    class ConfigEntryNotReady(Exception):
        """Config entry setup should be retried."""

    class HomeAssistantError(Exception):
        """Base Home Assistant user-facing error."""

    class ServiceValidationError(HomeAssistantError):
        """Service call validation error."""

    exceptions.ConfigEntryNotReady = ConfigEntryNotReady
    exceptions.HomeAssistantError = HomeAssistantError
    exceptions.ServiceValidationError = ServiceValidationError

    helpers = _install_module("homeassistant.helpers")
    config_validation = _install_module("homeassistant.helpers.config_validation")
    helpers.config_validation = config_validation
    config_validation.string = str

    update_coordinator = _install_module("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        """Coordinator update failed."""

    class DataUpdateCoordinator:
        """Small subset of Home Assistant's DataUpdateCoordinator."""

        def __class_getitem__(cls, item: Any) -> type["DataUpdateCoordinator"]:
            return cls

        def __init__(
            self,
            hass: HomeAssistant,
            logger: Any,
            *,
            name: str,
            update_interval: Any = None,
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None
            self.last_update_success = True

        async def async_config_entry_first_refresh(self) -> None:
            self.data = await self._async_update_data()

        def async_set_updated_data(self, data: Any) -> None:
            self.data = data
            self.last_update_success = True

        async def async_request_refresh(self) -> None:
            try:
                self.data = await self._async_update_data()
                self.last_update_success = True
            except Exception:
                self.last_update_success = False
                raise

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed

    bleak = _install_module("bleak")

    class BleakClient:
        """Minimal BleakClient stub."""

    class BleakError(Exception):
        """Minimal BleakError stub."""

    bleak.BleakClient = BleakClient
    bleak.BleakError = BleakError

    bleak_retry_connector = _install_module("bleak_retry_connector")

    async def establish_connection(*args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    bleak_retry_connector.establish_connection = establish_connection


if importlib.util.find_spec("homeassistant") is None:
    _install_lightweight_stubs()


if importlib.util.find_spec("pytest_homeassistant_custom_component") is not None:
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import MockModule, mock_integration

    @pytest.fixture(autouse=True)
    def reset_default_timezone() -> None:
        """Keep Home Assistant's global timezone clean between tests."""
        dt_util.DEFAULT_TIME_ZONE = UTC
        yield
        dt_util.DEFAULT_TIME_ZONE = UTC

    @pytest.fixture
    def expected_lingering_timers() -> bool:
        """Allow Home Assistant's test harness cleanup timers."""
        return True

    @pytest.fixture
    def mock_bluetooth_adapters(
        hass: Any, enable_custom_integrations: Any
    ) -> None:
        """Mock HA's Bluetooth adapter dependency without opening real sockets."""

        async def _async_setup(*args: Any, **kwargs: Any) -> bool:
            return True

        mock_integration(
            hass,
            MockModule("bluetooth_adapters", async_setup=_async_setup),
        )
